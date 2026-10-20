#!/usr/bin/env python3
"""Read-only Projektcheck: Python, Git und lokale Gemeindedaten.

Funktioniert mit Python-Standardbibliothek, auch vor pip install.
Ohne Downloads, Datenänderungen oder Netzwerkanfragen.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from importlib.util import find_spec
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
PACKAGES = [
    ("geopandas", "geopandas", "Gemeinde- und GIS-Daten"),
    ("osmnx", "osmnx", "OSM-Download"),
    ("truststore", "truststore", "Windows-HTTPS-Zertifikate"),
    ("osmium", "osmium", "Offline-PBF-Import (optional)"),
]


def run_git(*args):
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=8)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_file(path):
    return {"exists": path.is_file(), "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": path.stat().st_size if path.is_file() else None}


def check_json(path, mid=None):
    if not path.is_file():
        return {"valid": False, "detail": "Datei fehlt"}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        return {"valid": False, "detail": f"JSON fehlerhaft: {exc}"}
    if not isinstance(content, dict):
        return {"valid": False, "detail": "JSON ist kein Objekt"}
    if mid and str(content.get("municipality_id", "")) != mid:
        return {"valid": False, "detail": f"Gemeinde-ID stimmt nicht: {content.get('municipality_id')!r}"}
    return {"valid": True, "detail": "OK", "content": content}


def stage(label, paths, json_checks=None):
    json_checks = json_checks or {}
    checks = {name: check_file(path) for name, path in paths.items()}
    for key, mid in json_checks.items():
        if checks[key]["exists"]:
            checks[key]["manifest"] = check_json(paths[key], mid)
    good = all(c["exists"] and c.get("manifest", {"valid": True})["valid"]
               for c in checks.values())
    return {"name": label, "ok": good, "files": checks}


def municipality(mid):
    base = PROCESSED / mid
    out = REPORTS / mid
    stages = [
        stage("Amtliche Geodaten", {
            "Gemeindegrenze": base / "boundary.geojson",
            "Widmung": base / "zoning.geojson",
            "Bauland": base / "bauland.geojson",
            "Import-Manifest": base / "import_manifest.json",
        }, {"Import-Manifest": mid}),
        stage("OSM-Gebäude", {
            "Gebäude": base / "osm" / "buildings.geojson",
            "OSM-Manifest": base / "osm" / "osm_manifest.json",
        }, {"OSM-Manifest": mid}),
        stage("Gebäude/Widmungs-Join", {
            "Flächenschnitte": base / "building_zoning" / "zoning_footprint_overlaps.csv",
            "Join-Zusammenfassung": base / "building_zoning" / "summary.json",
        }),
        stage("Gebäudeklassifikation", {
            "Klassifikation": base / "building_classification" / "summary.json",
        }),
        stage("Gemeindebericht", {
            "Markdown": out / "gemeindebericht.md",
            "JSON": out / "gemeindebericht.json",
        }),
        stage("HTML-Überlappungen", {
            "Übersicht": out / "ueberlappungen" / "index.html",
            "CSV": out / "ueberlappungen" / "ueberlappungen.csv",
        }),
        stage("OSM-Löschwasserquellen", {
            "CSV": base / "water_sources" / "water_sources.csv",
            "GeoJSON": base / "water_sources" / "water_sources.geojson",
            "Manifest": base / "water_sources" / "water_sources_manifest.json",
        }, {"Manifest": mid}),
    ]
    water = check_json(base / "water_sources" / "water_sources_manifest.json", mid)
    osm_count = (water["content"].get("count") if water["valid"] else None)
    return {"id": mid, "stages": stages, "water_source_count": osm_count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", action="append", dest="gemeinden",
                        help="Gemeinde prüfen; mehrfach angeben (Standard: 20619 und 20608)")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe auf stdout")
    args = parser.parse_args()
    mids = list(dict.fromkeys(args.gemeinden or ["20619", "20608"]))
    if any(len(mid) != 5 or not mid.isdigit() or not mid.startswith("2") for mid in mids):
        parser.error("Gemeinde muss eine fünfstellige Kärntner GKZ sein")

    packages = []
    for module, package, purpose in PACKAGES:
        try:
            installed = find_spec(module) is not None
        except (ImportError, ValueError):
            installed = False
        packages.append({"name": package, "installed": installed, "purpose": purpose})

    branch = run_git("branch", "--show-current")
    git = {"available": run_git("--version") is not None,
           "branch": branch, "commit": run_git("rev-parse", "--short", "HEAD"),
           "remote": run_git("remote", "get-url", "origin"),
           "changes": run_git("status", "--porcelain"),
           "ahead_behind": None}
    # Vergleich nur mit bereits lokal bekannten Remote-Refs; kein git fetch.
    upstream = run_git("rev-parse", "--verify", "origin/main")
    if upstream:
        ahead = run_git("rev-list", "--left-right", "--count", "HEAD...origin/main")
        git["ahead_behind"] = ahead

    raw = {
        "Gemeindegrenzen-ZIP": check_file(RAW / "gemeinden_2026.zip"),
        "KAGIS-Widmungs-ZIP": check_file(RAW / "flawi_ktn_gpkg.zip"),
        "OSM-Austria-PBF": check_file(RAW / "austria-latest.osm.pbf"),
    }
    municipalities = [municipality(mid) for mid in mids]
    actions = []
    def suggest(command):
        if command not in actions:
            actions.append(command)

    missing_required = [p["name"] for p in packages if not p["installed"] and p["name"] != "osmium"]
    if missing_required:
        suggest("python -m pip install -r requirements.txt")
    if not git["available"]:
        suggest("Git installieren bzw. PATH prüfen")
    elif git["ahead_behind"] and git["ahead_behind"].split()[-1] != "0":
        suggest("git status; git pull --ff-only origin main  # erst lokale Änderungen prüfen")

    for town in municipalities:
        mid = town["id"]
        by_stage = {s["name"]: s for s in town["stages"]}
        if not by_stage["Amtliche Geodaten"]["ok"]:
            option = ("--download " if not (raw["Gemeindegrenzen-ZIP"]["exists"] and
                                           raw["KAGIS-Widmungs-ZIP"]["exists"]) else "")
            suggest(f"python scripts\\import_geodata.py --gemeinde {mid} {option}--repair-invalid")
            continue  # Ohne Gemeindegrenze sind Folgeimporte blockiert.
        if not by_stage["OSM-Löschwasserquellen"]["ok"]:
            if raw["OSM-Austria-PBF"]["exists"]:
                if not next(p for p in packages if p["name"] == "osmium")["installed"]:
                    suggest("python -m pip install osmium")
                suggest(f"python scripts\\import_water_sources.py --gemeinde {mid} --pbf data\\raw\\austria-latest.osm.pbf")
            else:
                suggest("OSM-Austria-PBF herunterladen: https://download.geofabrik.de/europe/austria.html")
                suggest(f"python scripts\\import_water_sources.py --gemeinde {mid} --pbf data\\raw\\austria-latest.osm.pbf")
        if not by_stage["OSM-Gebäude"]["ok"]:
            suggest(f"python scripts\\run_municipality.py --gemeinde {mid} --skip-geodata --osm-download")
        elif not all(by_stage[name]["ok"] for name in (
            "Gebäude/Widmungs-Join", "Gebäudeklassifikation", "Gemeindebericht")):
            suggest(f"Gemeinde-Pipeline fuer {mid} pruefen/erneut ausfuehren (OSM-Download oder vorhandener Export)")
        elif not by_stage["HTML-Überlappungen"]["ok"]:
            suggest(f"python scripts\\list_building_overlaps.py --gemeinde {mid} --open")

    result = {"generated_local": datetime.now().astimezone().isoformat(),
              "project_root": str(ROOT), "python": sys.version.split()[0],
              "executable": sys.executable, "git": git, "packages": packages,
              "raw_data": raw, "municipalities": municipalities, "next_steps": actions}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    def mark(value):
        return "[OK]" if value else "[FEHLT]"
    print("=== LOESCHWASSERVERSORGUNG: LOKALER PROJEKTCHECK ===")
    print(f"Projekt: {ROOT}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Git: {git['branch'] or '?'} @ {git['commit'] or '?'}")
    if git["ahead_behind"]:
        print(f"Git lokal vs. origin/main (letzter bekannter Stand): {git['ahead_behind']} (ahead behind)")
    print("Hinweis: Git-Remote-Stand wird NICHT online aktualisiert.")
    if git["changes"]:
        print("[HINWEIS] Lokale Git-Aenderungen vorhanden.")
    print("\nPython-Pakete:")
    for item in packages:
        print(f"  {mark(item['installed'])} {item['name']} ({item['purpose']})")
    print("\nRohdaten:")
    for label, value in raw.items():
        print(f"  {mark(value['exists'])} {label} - {value['path']}")
    for town in municipalities:
        print(f"\nGemeinde {town['id']}:")
        for item in town["stages"]:
            missing = [name for name, value in item["files"].items()
                       if not value["exists"] or not value.get("manifest", {"valid": True})["valid"]]
            print(f"  {mark(item['ok'])} {item['name']}" +
                  (f" (Problem: {', '.join(missing)})" if missing else ""))
        if town["water_source_count"] is not None:
            print(f"  OSM-Quellen im Manifest: {town['water_source_count']} (ungeprueft)")
    print("\nNaechste Schritte (Vorschlaege, werden NICHT ausgefuehrt):")
    if actions:
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action}")
    else:
        print("  Keine fehlenden Artefakte erkannt. Fachliche Datenvalidierung bleibt ausstehend.")
    print("\nNur Existenz-/Manifestchecks; keine GIS-, Aktualitaets- oder Leistungsvalidierung.")


if __name__ == "__main__":
    main()
