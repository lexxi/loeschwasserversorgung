#!/usr/bin/env python3
"""OSM buildings for a municipality: local GeoJSON or OSMnx/Overpass download.

The output is a building inventory, NOT a residential or firewater classification.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import geopandas as gpd

FIELDS = ["osm_id", "building", "name", "amenity", "tourism", "shop",
          "addr:city", "addr:postcode", "addr:street", "addr:housenumber",
          "building:use", "building:levels", "building:levels:underground",
          "height", "min_height", "roof:height", "roof:levels",
          "building:flats", "building:units", "building:part",
          "start_date", "landuse", "geometry"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_boundary(path):
    frame = gpd.read_file(path)
    if frame.empty or frame.crs is None:
        raise ValueError("Gemeindegrenze leer oder ohne CRS")
    geom = frame.to_crs(4326).geometry.union_all()
    if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Gemeindegrenze ist kein gültiges Polygon")
    return gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")


def download_buildings(boundary, overpass_url=None, retries=2):
    try:
        import osmnx as ox
    except ImportError as exc:
        raise SystemExit("Für --download: python -m pip install osmnx") from exc
    ox.settings.requests_timeout = 300
    if overpass_url:
        if not overpass_url.startswith("https://"):
            raise ValueError("Overpass-URL muss HTTPS verwenden")
        ox.settings.overpass_url = overpass_url.rstrip("/")
    for attempt in range(retries + 1):
        try:
            result = ox.features_from_polygon(boundary.geometry.iloc[0], tags={"building": True})
            break
        except Exception as exc:
            # Nur vorübergehende HTTP-Überlastung erneut versuchen.
            message = str(exc).lower()
            temporary = any(code in message for code in
                            ("429", "too many requests", "502", "bad gateway",
                             "503", "service unavailable", "504", "gateway timeout",
                             "currently at capacity"))
            if not temporary or attempt >= retries:
                raise
            delay = min(15 * (2 ** attempt), 60)
            print(f"[WARN] Overpass überlastet ({type(exc).__name__}); "
                  f"neuer Versuch {attempt + 2}/{retries + 1} in {delay} s",
                  flush=True)
            time.sleep(delay)
    if result.empty:
        raise ValueError("Overpass lieferte keine Gebäude")
    result = result.reset_index()
    if "element" in result and "id" in result:
        result["osm_id"] = result["element"].astype(str) + "/" + result["id"].astype(str)
    elif "element_type" in result and "osmid" in result:
        result["osm_id"] = result["element_type"].astype(str) + "/" + result["osmid"].astype(str)
    else:
        raise ValueError(f"Unbekanntes OSMnx-ID-Schema: {list(result.columns)}")
    return gpd.GeoDataFrame(result, geometry="geometry", crs="EPSG:4326")


def prepare(raw, boundary):
    if raw.crs is None:
        raise ValueError("OSM-Daten ohne CRS")
    if "osm_id" not in raw:
        if "@id" in raw:
            raw["osm_id"] = raw["@id"].astype(str)
        elif "id" in raw and raw["id"].astype(str).str.contains("/").all():
            raw["osm_id"] = raw["id"].astype(str)
        else:
            raise ValueError("OSM-Element-ID fehlt (@id/id/osm_id)")
    if "building" not in raw:
        raise ValueError("Spalte 'building' fehlt")
    raw = raw.to_crs(4326)
    raw = raw.loc[raw.geometry.notna() & ~raw.geometry.is_empty].copy()
    raw = raw.loc[raw.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    raw = raw.loc[raw["building"].notna() & raw["building"].astype(str).str.strip().ne("")].copy()
    if raw.empty:
        raise ValueError("Keine Gebäude-Polygone")
    if not raw.geometry.is_valid.all():
        raise ValueError(f"{int((~raw.geometry.is_valid).sum())} ungültige OSM-Gebäudegeometrien")
    chosen = raw.loc[raw.intersects(boundary.geometry.iloc[0])].copy()
    if chosen.empty:
        raise ValueError("Keine Gebäude im Gemeindegebiet")
    if chosen["osm_id"].duplicated().any():
        raise ValueError("Doppelte OSM-Element-IDs")
    for field in FIELDS:
        if field not in chosen:
            chosen[field] = None
    chosen = chosen[FIELDS].copy().sort_values("osm_id").reset_index(drop=True)
    stats = {
        "input_polygon_buildings": len(raw),
        "buildings_selected": len(chosen),
        "malta_buildings": len(chosen),  # Legacy field for existing Malta reports
        "buildings_with_housenumber": int(chosen["addr:housenumber"].notna().sum()),
        "building_tag_counts": {str(k): int(v) for k, v in chosen["building"].value_counts().items()},
    }
    return chosen, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true", help="Fresh OSMnx/Overpass query")
    mode.add_argument("--input", type=Path, help="Existing Overpass GeoJSON")
    parser.add_argument("--overpass-url", help="Alternativer vertrauenswürdiger Overpass HTTPS-Endpunkt")
    parser.add_argument("--overpass-retries", type=int, default=2,
                        help="Zusätzliche Versuche bei HTTP 429/502/503/504 (Standard: 2)")
    parser.add_argument("--gemeinde", type=str, default=None, help="5-stellige Gemeindenummer; muss zum amtlichen Import passen")
    parser.add_argument("--boundary", type=Path, default=Path("data/processed/current/malta_boundary_2026.geojson"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/current/osm"))
    args = parser.parse_args()
    if not 0 <= args.overpass_retries <= 5:
        parser.error('--overpass-retries muss zwischen 0 und 5 liegen')
    generic_mode = args.gemeinde is not None
    if generic_mode:
        if not (len(args.gemeinde) == 5 and args.gemeinde.isdigit() and args.gemeinde.startswith("2")):
            parser.error("--gemeinde muss eine 5-stellige Kärntner Gemeindenummer sein")
        base = Path("data/processed") / args.gemeinde
        if args.boundary == Path("data/processed/current/malta_boundary_2026.geojson"):
            args.boundary = base / "boundary.geojson"
        if args.out == Path("data/processed/current/osm"):
            args.out = base / "osm"
        official_manifest = base / "import_manifest.json"
        if not official_manifest.is_file():
            parser.error(f"Der amtliche Import fehlt: {official_manifest}")
        metadata = json.loads(official_manifest.read_text(encoding="utf-8"))
        if str(metadata.get("municipality_id")) != args.gemeinde:
            parser.error("Gemeinde-ID und Import-Manifest stimmen nicht ueberein")
    municipality_id = args.gemeinde if generic_mode else "20619"

    boundary = read_boundary(args.boundary)
    raw = download_buildings(boundary, args.overpass_url, args.overpass_retries) if args.download else gpd.read_file(args.input)
    buildings, stats = prepare(raw, boundary)
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / ("buildings.geojson" if generic_mode else "buildings_malta.geojson")
    buildings.to_file(output, driver="GeoJSON")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": municipality_id,
        "boundary_file": str(args.boundary),
        "boundary_sha256": sha256(args.boundary),
        "source": "OpenStreetMap contributors (ODbL)",
        "source_mode": "osmnx_overpass" if args.download else "local_geojson",
        "input_file": str(args.input) if args.input else None,
        "input_sha256": sha256(args.input) if args.input else None,
        "source_snapshot_date": "download time" if args.download else "unknown (historical export)",
        "output_file": str(output),
        "output_sha256": sha256(output),
        "statistics": stats,
        "warning": "Building polygons do not prove residential use or firewater requirements.",
    }
    (args.out / "osm_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"[OK] {output}")


if __name__ == "__main__":
    main()
