#!/usr/bin/env python3
"""Alle erfassten Gebaeude gegen lokale ODB-Wasserentnahmestellen auswerten.

Gebaeudegrundflaeche bis Wasserentnahmestellen-Punkt (Luftlinie EPSG:31287).
Keine OSM-Wasserquellen; OSM dient hier ausschliesslich als Gebaeudeinventar.
Keine normative Versorgungs- oder Leistungsbewertung.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median

import geopandas as gpd
from shapely.geometry import Point, shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = (
    "building_osm_id", "building_type", "nearest_usable_odb_id",
    "nearest_usable_odb_type", "distance_usable_m",
    "nearest_restricted_odb_id", "distance_restricted_m",
    "distance_band",
)


def load_sources(path):
    if not path.is_file():
        raise FileNotFoundError(f"ODB-Quellen fehlen: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("ODB-Quellen enthalten keine FeatureCollection")
    project = Transformer.from_crs(4326, 31287, always_xy=True).transform
    sources = []
    for item in data.get("features", []):
        props = item.get("properties") or {}
        geom = shape(item.get("geometry"))
        if not isinstance(geom, Point) or geom.is_empty:
            raise ValueError("ODB-Quelle ohne gueltige Punktgeometrie")
        sources.append({
            "id": str(props.get("odb_id") or ""),
            "type": str(props.get("type") or ""),
            "status": str(props.get("status_raw") or ""),
            "geom": transform(project, geom),
        })
    return sources


def nearest(geometry, sources):
    if not sources:
        return None, None
    source = min(sources, key=lambda s: (geometry.distance(s["geom"]), s["id"]))
    return source, geometry.distance(source["geom"])


def band(distance):
    if distance is None:
        return "keine_verwendbare_Quelle"
    for limit in (100, 250, 500, 1000):
        if distance <= limit:
            return f"bis_{limit}m"
    return "ueber_1000m"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Kärntner GKZ, z. B. 20619")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("Ungültige Kärntner GKZ")

    base = ROOT / "data" / "processed" / mid
    building_path = base / "osm" / "buildings.geojson"
    source_path = base / "odb_water_sources" / "odb_water_sources.geojson"
    boundary_path = base / "boundary.geojson"
    for file in (building_path, source_path, boundary_path):
        if not file.is_file():
            parser.error(f"Benötigte Eingabedatei fehlt: {file}")

    buildings = gpd.read_file(building_path)
    boundary = gpd.read_file(boundary_path)
    if buildings.crs is None or boundary.crs is None:
        raise ValueError("Gebaeude/Gemeindegrenze ohne CRS")
    if buildings.empty or "osm_id" not in buildings or "building" not in buildings:
        raise ValueError("Gebaeudeinventar ist leer oder hat kein osm_id/building-Feld")
    buildings = buildings.to_crs(31287)
    border = boundary.to_crs(31287).geometry.union_all()
    # Gebaeude an der Gemeindegrenze werden nicht ausgeschlossen.
    buildings = buildings.loc[buildings.geometry.intersects(border)].copy()
    if buildings["osm_id"].isna().any() or buildings["osm_id"].astype(str).duplicated().any():
        raise ValueError("Fehlende oder doppelte Gebaeude-OSM-IDs")
    sources = load_sources(source_path)
    usable = [s for s in sources if s["status"] == "1"]
    restricted = [s for s in sources if s["status"] == "2"]
    rows = []
    for _, b in buildings.iterrows():
        geom = b.geometry
        if geom is None or geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Ungueltige Gebaeudegrundflaeche: {b['osm_id']}")
        u, ud = nearest(geom, usable)
        r, rd = nearest(geom, restricted)
        rows.append({
            "building_osm_id": str(b["osm_id"]),
            "building_type": str(b["building"]) if b["building"] is not None else "",
            "nearest_usable_odb_id": u["id"] if u else "",
            "nearest_usable_odb_type": u["type"] if u else "",
            "distance_usable_m": round(ud, 1) if ud is not None else "",
            "nearest_restricted_odb_id": r["id"] if r else "",
            "distance_restricted_m": round(rd, 1) if rd is not None else "",
            "distance_band": band(ud),
        })
    rows.sort(key=lambda r: r["building_osm_id"])
    distances = [float(r["distance_usable_m"]) for r in rows if r["distance_usable_m"] != ""]
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "building_count": len(rows),
        "odb_sources_total": len(sources),
        "odb_sources_usable": len(usable),
        "odb_sources_restricted": len(restricted),
        "odb_sources_not_usable": sum(s["status"] == "3" for s in sources),
        "odb_sources_unknown_status": sum(s["status"] not in ("1", "2", "3") for s in sources),
        "distance_band_counts": dict(sorted(Counter(r["distance_band"] for r in rows).items())),
        "nearest_usable_distance_min_m": round(min(distances), 1) if distances else None,
        "nearest_usable_distance_median_m": round(median(distances), 1) if distances else None,
        "nearest_usable_distance_max_m": round(max(distances), 1) if distances else None,
        "method": "Minimaler Luftlinienabstand Gebaeudegrundflaeche -> ODB-Punkt im EPSG:31287.",
        "limitations": [
            "Alle im lokalen Inventar erfassten Gebaeude, unabhaengig von der Widmung.",
            "OSM wird nur fuer Gebaeudegeometrien verwendet. Vier archivierte OSM-Hydranten ausgeschlossen.",
            "Status 1 wird als verwendbar gefuehrt; Status 2 nur separat als eingeschraenkt dokumentiert.",
            "Keine Leistungs-/Hydraulikpruefung, Schlauchstrecke, Wegfuehrung oder Feuerwehrzufahrt.",
            "100/250/500/1000m sind rein deskriptive Klassen, keine Versorgungsgrenzwerte.",
            "Die Gebaeudeinventarisierung aus OSM kann unvollstaendig sein.",
        ],
    }
    out = ROOT / "reports" / mid
    out.mkdir(parents=True, exist_ok=True)
    csv_file = out / "gebaeude_odb_abstaende.csv"
    summary_file = out / "gebaeude_odb_abstaende.json"
    with csv_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gemeinde {mid}: {len(rows)} Gebaeude; ODB: {len(sources)} Quellen ({len(usable)} verwendbar)")
    print("Abstandsklassen:", json.dumps(summary["distance_band_counts"], ensure_ascii=False))
    print("Minimal/Median/Maximal (m):", summary["nearest_usable_distance_min_m"],
          summary["nearest_usable_distance_median_m"], summary["nearest_usable_distance_max_m"])
    print(f"[OK] {csv_file}")
    print(f"[OK] {summary_file}")


if __name__ == "__main__":
    main()
