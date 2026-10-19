#!/usr/bin/env python3
"""OSM-Löschwasser-Objekte für eine Kärntner Gemeinde erfassen.

Bestandsinventar, KEIN Nachweis von Durchfluss, Kapazität, Betrieb oder
feuerwehrtechnischer Eignung. Ausschließlich explizite emergency-Tags.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, LineString

from import_osm import read_boundary

TYPES = {
    "fire_hydrant": "Hydrant",
    "suction_point": "Saugstelle",
    "water_tank": "Löschwasserbehälter",
    "fire_water_pond": "Löschwasserteich",
}
FIELDS = (
    "emergency", "fire_hydrant:type", "fire_hydrant:diameter",
    "fire_hydrant:pressure", "fire_hydrant:position",
    "water_source", "water_tank:volume", "capacity", "volume",
    "ref", "access", "operator", "survey:date", "check_date",
)
TABLE = ("osm_id", "type", "osm_emergency", "latitude", "longitude",
         "geometry_type", "position_method", *FIELDS[1:],
         "quality_status")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    try:
        if bool(pd.isna(value)):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value).strip()


def osm_download(boundary, overpass_url=None, retries=2):
    import osmnx as ox

    # OSMnx nutzt diesen Wert auch als TCP-Connect-Timeout. Lange Hänger vermeiden.
    ox.settings.requests_timeout = 90
    if overpass_url:
        if not overpass_url.startswith("https://"):
            raise ValueError("Overpass-Endpunkt muss HTTPS verwenden")
        ox.settings.overpass_url = overpass_url.rstrip("/")

    for attempt in range(retries + 1):
        try:
            # Enger Filter. OSMnx verknüpft mehrere Werte desselben Keys mit OR.
            return ox.features_from_polygon(
                boundary.geometry.iloc[0],
                tags={"emergency": list(TYPES)},
            )
        except Exception as exc:
            # Leere Treffer sind kein Defekt der Quelle.
            if type(exc).__name__ == "InsufficientResponseError":
                return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=4326)
            message = str(exc).lower()
            temporary = any(v in message for v in (
                "429", "too many requests", "502", "bad gateway", "503",
                "service unavailable", "504", "gateway timeout",
                "currently at capacity", "connecttimeout", "readtimeout",
                "connection timed out", "timed out", "winerror 10060",
            ))
            if not temporary or attempt >= retries:
                raise
            delay = min(15 * (2 ** attempt), 60)
            print(f"[WARN] Overpass nicht erreichbar/überlastet ({type(exc).__name__}); neuer Versuch "
                  f"{attempt + 2}/{retries + 1} in {delay} s", flush=True)
            time.sleep(delay)
    raise AssertionError("Unreachable")



def pbf_import(path):
    """Liest nur explizit markierte Nodes/Ways aus einem regionalen OSM-PBF.

    pyosmium loest Way-Knotenkoordinaten aus dem selben PBF auf. OSM-Relationen
    bleiben in dieser ersten Offline-Version ausgeschlossen und werden gemeldet.
    """
    try:
        import osmium
    except ImportError as exc:
        raise SystemExit("Fuer --pbf bitte installieren: python -m pip install osmium") from exc
    if not path.is_file():
        raise FileNotFoundError(f"OSM-PBF fehlt: {path}")

    rows = []
    skipped = {"invalid_way_geometry": 0, "tagged_relations": 0}

    class Collector(osmium.SimpleHandler):
        def add_object(self, kind, item, geometry):
            tags = item.tags
            kind_tag = tags.get("emergency")
            if kind_tag not in TYPES:
                return
            data = {"osm_id": f"{kind}/{item.id}", "emergency": kind_tag,
                    "geometry": geometry}
            for field in FIELDS[1:]:
                data[field] = tags.get(field)
            rows.append(data)

        def node(self, n):
            if n.tags.get("emergency") not in TYPES or not n.location.valid():
                return
            self.add_object("node", n, Point(n.location.lon, n.location.lat))

        def way(self, w):
            if w.tags.get("emergency") not in TYPES:
                return
            try:
                coords = [(node.location.lon, node.location.lat) for node in w.nodes if node.location.valid()]
                if len(coords) < 2:
                    skipped["invalid_way_geometry"] += 1
                    return
                geom = Polygon(coords) if len(coords) >= 4 and coords[0] == coords[-1] else LineString(coords)
                if geom.is_empty or not geom.is_valid:
                    skipped["invalid_way_geometry"] += 1
                    return
                self.add_object("way", w, geom)
            except (ValueError, RuntimeError):
                skipped["invalid_way_geometry"] += 1

        def relation(self, r):
            if r.tags.get("emergency") in TYPES:
                skipped["tagged_relations"] += 1

    handler = Collector()
    handler.apply_file(str(path), locations=True)
    print(f"[INFO] PBF: {len(rows)} markierte Nodes/Ways vor Gemeindefilter", flush=True)
    if any(skipped.values()):
        print(f"[WARN] PBF: ausgelassene Geometrien/Relationen: {skipped}", flush=True)
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "emergency", "geometry"], geometry="geometry", crs="EPSG:4326"), skipped
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326"), skipped


def prepare(raw, boundary):
    if raw.crs is None:
        raise ValueError("OSM-Daten ohne Koordinatenreferenzsystem")
    raw = raw.reset_index()
    if "osm_id" not in raw.columns:
        if {"element", "id"}.issubset(raw.columns):
            raw["osm_id"] = raw["element"].astype(str) + "/" + raw["id"].astype(str)
        elif {"element_type", "osmid"}.issubset(raw.columns):
            raw["osm_id"] = raw["element_type"].astype(str) + "/" + raw["osmid"].astype(str)
        elif "@id" in raw:
            raw["osm_id"] = raw["@id"].astype(str)
        elif "id" in raw and raw["id"].astype(str).str.contains("/").all():
            raw["osm_id"] = raw["id"].astype(str)
        elif not raw.empty:
            raise ValueError("OSM-ID fehlt (osm_id, @id oder element/id)")
    if "emergency" not in raw.columns:
        if not raw.empty:
            raise ValueError("Feld emergency fehlt")
        raw["emergency"] = pd.Series(dtype="str")

    raw = raw.loc[raw.geometry.notna() & ~raw.geometry.is_empty].copy()
    raw = raw.to_crs(epsg=31287)
    raw = raw.loc[raw["emergency"].isin(TYPES)].copy()
    boundary_m = boundary.to_crs(epsg=31287).geometry.iloc[0]

    records = []
    points = []
    for _, row in raw.iterrows():
        geom = row.geometry
        if not geom.is_valid:
            continue
        # Punkte innen; Flächen anhand repräsentativem Punkt im Gebiet.
        point = geom if geom.geom_type == "Point" else geom.representative_point()
        if point.geom_type != "Point" or not boundary_m.covers(point):
            continue
        osm_id = clean(row.get("osm_id"))
        if not osm_id:
            raise ValueError("OSM-Objekt ohne Element-ID")
        wgs = gpd.GeoSeries([point], crs=31287).to_crs(epsg=4326).iloc[0]
        data = {
            "osm_id": osm_id,
            "type": TYPES[clean(row["emergency"])],
            "osm_emergency": clean(row["emergency"]),
            "latitude": round(wgs.y, 7),
            "longitude": round(wgs.x, 7),
            "geometry_type": geom.geom_type,
            "position_method": "original_node" if geom.geom_type == "Point" else "representative_point",
            "quality_status": "OSM-Eintrag; ungeprüft",
        }
        for field in FIELDS[1:]:
            data[field] = clean(row.get(field))
        records.append(data)
        points.append(point)
    if len(set(r["osm_id"] for r in records)) != len(records):
        raise ValueError("Doppelte OSM-Element-IDs in der Auswahl")
    order = sorted(range(len(records)), key=lambda i: records[i]["osm_id"])
    ordered = [records[i] for i in order]
    geometries = [points[i] for i in order]
    frame = gpd.GeoDataFrame(ordered, geometry=geometries, crs=31287).to_crs(4326)
    return frame, ordered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Kärntner GKZ, z. B. 20619")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true", help="Aktueller Overpass-Import")
    mode.add_argument("--input", type=Path, help="Lokaler OSM-GeoJSON-Export")
    mode.add_argument("--pbf", type=Path, help="Offline-OSM-PBF, z. B. Geofabrik Austria")
    parser.add_argument("--overpass-url", help="Alternativer HTTPS-Endpunkt")
    parser.add_argument("--overpass-retries", type=int, default=2)
    args = parser.parse_args()
    if not (len(args.gemeinde) == 5 and args.gemeinde.isdigit()
            and args.gemeinde.startswith("2")):
        parser.error("Ungültige Kärntner Gemeindenummer")
    if not 0 <= args.overpass_retries <= 5:
        parser.error("--overpass-retries muss zwischen 0 und 5 liegen")

    base = Path("data/processed") / args.gemeinde
    boundary_path = base / "boundary.geojson"
    manifest = base / "import_manifest.json"
    if not boundary_path.is_file() or not manifest.is_file():
        parser.error("Gemeindegrenze/Manifest fehlen; zuerst Gemeinde-Pipeline ausführen")
    identity = json.loads(manifest.read_text(encoding="utf-8"))
    if str(identity.get("municipality_id")) != args.gemeinde:
        parser.error("Import-Manifest stimmt nicht zur Gemeinde")
    boundary = read_boundary(boundary_path)
    pbf_skipped = None
    if args.pbf:
        raw, pbf_skipped = pbf_import(args.pbf)
    elif args.download:
        raw = osm_download(boundary, args.overpass_url, args.overpass_retries)
    else:
        raw = gpd.read_file(args.input)
    frame, records = prepare(raw, boundary)

    out = base / "water_sources"
    out.mkdir(parents=True, exist_ok=True)
    csv_file = out / "water_sources.csv"
    geojson_file = out / "water_sources.geojson"
    manifest_file = out / "water_sources_manifest.json"
    with csv_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TABLE, delimiter=";")
        writer.writeheader()
        writer.writerows(records)
    # GeoJSON nur mit zuvor kuratierten Feldern (keine OSM-Namen/Adressen).
    if frame.empty:
        geojson_file.write_text('{"type":"FeatureCollection","features":[]}\\n', encoding="utf-8")
    else:
        frame.to_file(geojson_file, driver="GeoJSON")
    counts = {label: sum(r["type"] == label for r in records) for label in TYPES.values()}
    metadata = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": args.gemeinde,
        "municipality_name": identity.get("municipality_name"),
        "source": "OpenStreetMap contributors (ODbL)",
        "source_mode": "overpass" if args.download else ("local_osm_pbf" if args.pbf else "local_geojson"),
        "pbf_file": str(args.pbf) if args.pbf else None,
        "pbf_sha256": sha256(args.pbf) if args.pbf else None,
        "pbf_skipped": pbf_skipped,
        "input_sha256": sha256(args.input) if args.input else None,
        "boundary_sha256": sha256(boundary_path),
        "filter": {"emergency": list(TYPES)},
        "count": len(records),
        "counts_by_type": counts,
        "csv_sha256": sha256(csv_file),
        "geojson_sha256": sha256(geojson_file),
        "limitations": [
            "OSM-Daten können unvollständig oder veraltet sein.",
            "Punktlage nicht amtlich verifiziert.",
            "Druck, Durchfluss, Tankvolumen und Wasserverfügbarkeit nicht geprüft.",
            "OSM-Attribute wie pressure/capacity sind Rohwerte und kein Leistungsnachweis.",
            "Linien/Flächen werden als repräsentativer Punkt dargestellt.",
            "Natürliche Gewässer ohne explizite Feuerwehr-Entnahmetags sind nicht erfasst.",
            "Im PBF-Modus werden Relationsobjekte nicht ausgewertet (im Manifest gezaehlt).",
        ],
    }
    manifest_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gemeinde": args.gemeinde, "gesamt": len(records), "typen": counts}, ensure_ascii=False, indent=2))
    print(f"[OK] {csv_file}")
    print(f"[OK] {geojson_file}")
    print(f"[OK] {manifest_file}")


if __name__ == "__main__":
    main()
