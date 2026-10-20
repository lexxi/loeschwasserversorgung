#!/usr/bin/env python3
"""Offline-Gebaeudeimport aus Geofabrik-OSM-PBF; keine Overpass-Anfrage.

Erfasst getaggte Gebaeude-Ways als Polygone und filtert sie mit der amtlichen
Gemeindegrenze. OSM-Multipolygon-Relationen ohne eigene Way-Geometrie
werden derzeit nur gezaehlt und nicht rekonstruiert.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from import_osm import FIELDS, prepare, read_boundary, sha256


def read_pbf_buildings(pbf, boundary):
    try:
        import osmium
    except ImportError as exc:
        raise SystemExit("Fehlendes Paket: python -m pip install osmium") from exc

    if not pbf.is_file():
        raise FileNotFoundError(f"OSM-PBF nicht gefunden: {pbf}")
    xmin, ymin, xmax, ymax = boundary.geometry.iloc[0].bounds
    rows = []
    counts = {
        "tagged_building_ways": 0,
        "outside_bbox": 0,
        "invalid_or_unclosed_ways": 0,
        "tagged_building_relations_not_imported": 0,
    }

    class Collector(osmium.SimpleHandler):
        def way(self, way):
            building = way.tags.get("building")
            if not building or building == "no":
                return
            counts["tagged_building_ways"] += 1
            nodes = way.nodes
            if len(nodes) < 4 or nodes[0].ref != nodes[-1].ref:
                counts["invalid_or_unclosed_ways"] += 1
                return
            try:
                coordinates = [(n.location.lon, n.location.lat) for n in nodes]
            except (ValueError, RuntimeError, osmium.InvalidLocationError):
                counts["invalid_or_unclosed_ways"] += 1
                return
            poly_minx = min(p[0] for p in coordinates)
            poly_maxx = max(p[0] for p in coordinates)
            poly_miny = min(p[1] for p in coordinates)
            poly_maxy = max(p[1] for p in coordinates)
            if poly_maxx < xmin or poly_minx > xmax or poly_maxy < ymin or poly_miny > ymax:
                counts["outside_bbox"] += 1
                return
            polygon = Polygon(coordinates)
            if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                counts["invalid_or_unclosed_ways"] += 1
                return
            row = {"osm_id": f"way/{way.id}", "geometry": polygon}
            for field in FIELDS:
                if field not in row and field != "geometry":
                    row[field] = way.tags.get(field)
            rows.append(row)

        def relation(self, relation):
            if relation.tags.get("building") and relation.tags.get("building") != "no":
                counts["tagged_building_relations_not_imported"] += 1

    handler = Collector()
    handler.apply_file(str(pbf), locations=True)
    if not rows:
        raise ValueError("Keine gueltigen Gebaeude-Ways im Gemeinde-Bounding-Box-Bereich gefunden")
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326"), counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Kärntner GKZ, z. B. 20619")
    parser.add_argument("--pbf", type=Path, default=Path("data/raw/austria-latest.osm.pbf"))
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("Ungueltige Kärntner Gemeinde-GKZ")

    base = Path("data/processed") / mid
    boundary_file = base / "boundary.geojson"
    official_manifest = base / "import_manifest.json"
    if not boundary_file.is_file() or not official_manifest.is_file():
        parser.error("Amtliche Gemeindegrenze/Import-Manifest fehlen")
    official = json.loads(official_manifest.read_text(encoding="utf-8"))
    if str(official.get("municipality_id")) != mid:
        parser.error("Gemeinde-ID stimmt nicht mit amtlichem Manifest ueberein")

    boundary = read_boundary(boundary_file)
    print("[INFO] Lese OSM-PBF lokal. Kann einige Minuten dauern ...", flush=True)
    raw, skipped = read_pbf_buildings(args.pbf, boundary)
    buildings, stats = prepare(raw, boundary)
    folder = base / "osm"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "buildings.geojson"
    buildings.to_file(output, driver="GeoJSON")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "boundary_file": str(boundary_file),
        "boundary_sha256": sha256(boundary_file),
        "source": "OpenStreetMap contributors (ODbL)",
        "source_mode": "local_osm_pbf_building_ways",
        "input_file": str(args.pbf),
        "input_sha256": sha256(args.pbf),
        "output_file": str(output),
        "output_sha256": sha256(output),
        "statistics": stats,
        "pbf_diagnostics": skipped,
        "warning": (
            "Gebaeude-Ways, keine Rekonstruktion reiner Multipolygon-Relationen. "
            "OSM-Gebaeudeinventar kann unvollstaendig sein. Keine Aussage zur Nutzung "
            "oder zum Loeschwasserbedarf."
        ),
    }
    (folder / "osm_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[OK] Gebaeude innerhalb/auf Gemeindegrenze: {len(buildings)}")
    print(f"[INFO] PBF-Diagnose: {json.dumps(skipped, ensure_ascii=False)}")
    print(f"[OK] {output}")
    print(f"[OK] {folder / 'osm_manifest.json'}")


if __name__ == "__main__":
    main()
