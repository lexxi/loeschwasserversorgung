#!/usr/bin/env python3
"""Run the complete municipality analysis from an Austrian municipality code.

Designed for Carinthia's zoning source. No firewater demand is inferred.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys


def execute(script: str, *args: str) -> None:
    cmd = [sys.executable, str(Path(__file__).with_name(script)), *map(str, args)]
    print("[RUN]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Kärntner Gemeinde-ID, z. B. 20619")
    parser.add_argument("--zoning-gpkg", type=Path, help="Bereits vorhandenes landesweites KAGIS-GeoPackage")
    parser.add_argument("--boundary-zip", type=Path, default=Path("data/raw/gemeinden_2026.zip"))
    parser.add_argument("--zoning-zip", type=Path, default=Path("data/raw/flawi_ktn_gpkg.zip"))
    parser.add_argument("--download-geodata", action="store_true", help="Amtliche ZIP-Dateien neu laden")
    parser.add_argument("--repair-invalid", action="store_true", help="Ungültige KAGIS-Geometrie explizit reparieren")
    osm = parser.add_mutually_exclusive_group(required=True)
    osm.add_argument("--osm-download", action="store_true", help="OSM-Gebäude aktuell herunterladen")
    osm.add_argument("--osm-input", type=Path, help="Vorhandenes OSM-GeoJSON als Vergleichsstand einlesen")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("--gemeinde muss eine fünfstellige Kärntner Gemeinde-ID sein")
    base = Path("data/processed") / mid

    geo_args = ["--gemeinde", mid, "--output-dir", str(base),
                "--boundary-zip", str(args.boundary_zip),
                "--zoning-zip", str(args.zoning_zip)]
    if args.zoning_gpkg:
        geo_args += ["--zoning-gpkg", str(args.zoning_gpkg)]
    if args.download_geodata:
        geo_args.append("--download")
    if args.repair_invalid:
        geo_args.append("--repair-invalid")
    execute("import_geodata.py", *geo_args)
    execute("import_osm.py", "--gemeinde", mid,
            * (["--download"] if args.osm_download else ["--input", str(args.osm_input)]))
    execute("join_buildings_zoning.py",
            "--buildings", str(base / "osm" / "buildings.geojson"),
            "--zoning", str(base / "zoning.geojson"),
            "--out", str(base / "building_zoning"))
    execute("classify_buildings.py",
            "--input", str(base / "building_zoning" / "buildings_with_zoning.geojson"),
            "--out", str(base / "building_classification"))
    execute("generate_municipality_report.py", "--base", str(base))

    manifest = json.loads((base / "import_manifest.json").read_text(encoding="utf-8"))
    print(f"[OK] {manifest['municipality_name']} ({mid}): reports/{mid}/gemeindebericht.md")


if __name__ == "__main__":
    main()
