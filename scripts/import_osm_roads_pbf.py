#!/usr/bin/env python3
"""OSM-Strassen und -Wege fuer den Offline-Kartenhintergrund aus einem lokalen PBF.

Nur Visualisierung: highway-Tag ist kein Nachweis von Befahrbarkeit, Zugang,
Schlauchverlegbarkeit oder Eignung als Feuerwehrzufahrt.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

from import_osm import sha256

ROAD_TYPES = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "living_street", "service",
    "track", "path", "footway", "pedestrian", "steps", "cycleway",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link", "road",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="GKZ, z. B. 20619")
    parser.add_argument("--pbf", type=Path, default=Path("data/raw/austria-latest.osm.pbf"))
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit() or not mid.startswith("2"):
        parser.error("Ungueltige Kaerntner Gemeindenummer")
    if not args.pbf.is_file():
        parser.error(f"Lokales OSM-PBF fehlt: {args.pbf}")
    base = Path("data/processed") / mid
    boundary_path = base / "boundary.geojson"
    if not boundary_path.is_file():
        parser.error(f"Gemeindegrenze fehlt: {boundary_path}")
    try:
        import osmium
    except ImportError as exc:
        raise SystemExit("Bitte python -m pip install osmium ausfuehren") from exc

    bounds = gpd.read_file(boundary_path)
    if bounds.empty or bounds.crs is None:
        raise ValueError("Gemeindegrenze leer oder ohne CRS")
    border = bounds.to_crs(31287).geometry.union_all()
    # Extra 300m display buffer so roads/paths close to the municipal border show.
    display_area = border.buffer(300)
    minx, miny, maxx, maxy = gpd.GeoSeries([display_area], crs=31287).to_crs(4326).total_bounds
    rows = []
    counters = Counter()

    class Collector(osmium.SimpleHandler):
        def way(self, way):
            category = way.tags.get("highway")
            if category not in ROAD_TYPES:
                return
            counters["tagged_highways"] += 1
            try:
                coords = [(n.location.lon, n.location.lat) for n in way.nodes]
            except (ValueError, RuntimeError):
                counters["invalid_location"] += 1
                return
            if len(coords) < 2:
                counters["short_way"] += 1
                return
            if max(x for x, _ in coords) < minx or min(x for x, _ in coords) > maxx:
                return
            if max(y for _, y in coords) < miny or min(y for _, y in coords) > maxy:
                return
            rows.append({
                "osm_id": f"way/{way.id}",
                "highway": category,
                "name": way.tags.get("name", ""),
                "surface": way.tags.get("surface", ""),
                "access": way.tags.get("access", ""),
                "motor_vehicle": way.tags.get("motor_vehicle", ""),
                "geometry": LineString(coords),
            })

    print("[INFO] Lese Strassen und Wege aus dem lokalen OSM-PBF ...", flush=True)
    Collector().apply_file(str(args.pbf), locations=True)
    if not rows:
        raise ValueError("Keine OSM-Strassen im Gemeinde-Bounding-Box-Bereich gefunden")
    frame = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326).to_crs(31287)
    frame = frame.loc[frame.geometry.intersects(display_area)].copy()
    if frame.empty:
        raise ValueError("Keine Strassen schneiden das Gemeindegebiet")
    frame["geometry"] = frame.geometry.intersection(display_area)
    frame = frame.loc[~frame.geometry.is_empty].to_crs(4326).copy()
    folder = base / "osm"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "roads.geojson"
    frame.to_file(output, driver="GeoJSON")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "source": "© OpenStreetMap contributors, ODbL 1.0",
        "source_mode": "local_osm_pbf_highways",
        "input_file": str(args.pbf),
        "input_sha256": sha256(args.pbf),
        "boundary_sha256": sha256(boundary_path),
        "buffer_m": 300,
        "output_file": str(output),
        "output_sha256": sha256(output),
        "features": len(frame),
        "types": dict(sorted(frame["highway"].value_counts().to_dict().items())),
        "diagnostics": dict(counters),
        "limitations": [
            "Visualisierung ohne Routing und ohne Zugangsbewertung.",
            "OSM-Wege sind nicht zwingend oeffentlich zugaenglich oder fuer die Feuerwehr befahrbar.",
            "Gefaelle, Zugangssperren und Schlauchverlegebarkeit nicht bewertet.",
        ],
    }
    manifest_path = folder / "roads_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Strassen/Wege: {len(frame)} | Typen: {json.dumps(manifest['types'], ensure_ascii=False)}")
    print(f"[OK] {output}")
    print(f"[OK] {manifest_path}")


if __name__ == "__main__":
    main()
