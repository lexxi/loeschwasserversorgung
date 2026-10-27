#!/usr/bin/env python3
"""Reproduzierbare BEV-ALS DSM/DTM-Kachelauswahl und optionaler Download.

Nutzt offiziell publizierte HTTPS-Datei-URLs (50-km-Kacheln, EPSG:3035).
Standard: nur Plan und Manifest. --download: lade beide Modelle im Vollformat.
Ein Lockfile verhindert unbemerktes Ersetzen bereits bezogener Quelldaten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import geopandas as gpd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
BEV_ROOT = "https://data.bev.gv.at/download/ALS"
GRID = 50000
DATE_RE = re.compile(r"^20[0-9]{6}$")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def required_tiles(geometry, padding_m):
    geom = geometry.buffer(padding_m)
    minx, miny, maxx, maxy = geom.bounds
    tiles = []
    for e in range(math.floor(minx / GRID) * GRID,
                   math.floor(maxx / GRID) * GRID + GRID, GRID):
        for n in range(math.floor(miny / GRID) * GRID,
                       math.floor(maxy / GRID) * GRID + GRID, GRID):
            if geom.intersects(box(e, n, e + GRID, n + GRID)):
                tiles.append((n, e))
    return sorted(tiles)


def make_entry(stamp, kind, n, e, folder):
    file = f"ALS_{kind}_CRS3035RES50000mN{n}E{e}.tif"
    url = f"{BEV_ROOT}/{kind}/{stamp}/{file}"
    return {"model": kind, "tile_n": n, "tile_e": e,
            "url": url, "file": str(folder / kind / file)}


def download_one(url, destination, max_gb, expected_hash=None):
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        digest = sha256(dest)
        if expected_hash and expected_hash != digest:
            raise ValueError(f"Lokale Datei weicht vom gespeicherten SHA256 ab: {dest}")
        print(f"[OK] Vorhanden: {dest} SHA256={digest}", flush=True)
        return digest, dest.stat().st_size
    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        raise RuntimeError(f"Unvollstaendiger Download vorhanden: {tmp}. "
                           "Bitte erst pruefen und loeschen; kein automatisches Ueberschreiben.")
    req = Request(url, headers={"User-Agent": "loeschwasserversorgung-bev-als/0.1"})
    try:
        with urlopen(req, timeout=90) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} fuer {url}")
            length = response.headers.get("Content-Length")
            if length and int(length) > max_gb * 1024**3:
                raise RuntimeError(f"Einzeldatei groesser als Downloadlimit ({max_gb:g} GiB): {url}")
            h = hashlib.sha256()
            size = 0
            try:
                with tmp.open("xb") as out:
                    while True:
                        chunk = response.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > max_gb * 1024**3:
                            raise RuntimeError(f"Abbruch: Datei groesser als {max_gb:g} GiB")
                        out.write(chunk)
                        h.update(chunk)
            except Exception:
                tmp.unlink(missing_ok=True)
                raise
        if length and size != int(length):
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Download unvollstaendig: {url}, {size} statt {length} Byte")
        digest = h.hexdigest()
        if expected_hash and expected_hash != digest:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Quelle hat sich gegenueber Lockfile veraendert: {url}")
        os.replace(tmp, dest)
        print(f"[OK] {dest} ({size / 1024**3:.2f} GiB), SHA256={digest}", flush=True)
        return digest, size
    except HTTPError as ex:
        raise RuntimeError(f"HTTP {ex.code} fuer {url}: Dateiname, Datum und Kachel "
                           "anhand der BEV-Kachelübersicht pruefen") from ex
    except URLError as ex:
        raise RuntimeError(f"Download von {url} fehlgeschlagen: {ex}") from ex


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde", default="20619")
    p.add_argument("--stichtag", default="20250915", help="Fester BEV-Stichtag, JJJJMMTT")
    p.add_argument("--padding-m", type=float, default=50)
    p.add_argument("--download", action="store_true", help="Gesamte benoetigte BEV-Kacheln herunterladen")
    p.add_argument("--max-file-gb", type=float, default=8, help="Sicherheitsgrenze pro Quelldatei")
    p.add_argument("--source", choices=("buildings", "boundary"), default="buildings",
                   help="Kacheln fuer alle OSM-Gebaeude oder gesamte Gemeindegrenze")
    args = p.parse_args()
    mid = args.gemeinde
    if not (mid.isdigit() and len(mid) == 5 and mid.startswith("2")):
        p.error("ungueltige Kaerntner Gemeindekennzahl")
    if not DATE_RE.fullmatch(args.stichtag):
        p.error("Stichtag muss YYYYMMDD sein")
    if args.padding_m < 0 or args.max_file_gb <= 0:
        p.error("ungueltiger Puffer oder Dateigroessen-Limit")
    base = ROOT / "data" / "processed" / mid
    geometry_file = (base / "osm" / "buildings.geojson" if args.source == "buildings"
                     else base / "boundary.geojson")
    if not geometry_file.is_file():
        p.error(f"GeoJSON fehlt: {geometry_file}")
    shapes = gpd.read_file(geometry_file)
    if shapes.empty or shapes.crs is None or shapes.geometry.isna().any():
        raise ValueError("Ungültige Eingabegeometrie oder CRS fehlt")
    geometry = shapes.to_crs(3035).geometry.union_all()
    tiles = required_tiles(geometry, args.padding_m)
    if not tiles:
        raise ValueError("Keine BEV-Kacheln ermittelt")
    target = ROOT / "data" / "raw" / "bev" / args.stichtag
    entries = [make_entry(args.stichtag, kind, n, e, target)
               for n, e in tiles for kind in ("DSM", "DTM")]
    locks = target / f"bev_als_{mid}_{args.source}_lock.json"
    if locks.exists():
        old = json.loads(locks.read_text(encoding="utf-8"))
        identity = ("municipality_id", "stichtag", "source", "padding_m", "tile_grid", "urls")
        request = {"municipality_id": mid, "stichtag": args.stichtag,
                   "source": args.source, "padding_m": args.padding_m,
                   "tile_grid": GRID, "urls": [item["url"] for item in entries]}
        for key in identity:
            if old.get(key) != request[key]:
                raise ValueError(f"Lockfile passt nicht zur aktuellen Auswahl ({key}); "
                                 "Aenderungen nicht stillschweigend uebernehmen.")
    else:
        old = {}
        request = {"municipality_id": mid, "stichtag": args.stichtag,
                   "source": args.source, "padding_m": args.padding_m,
                   "tile_grid": GRID, "urls": [item["url"] for item in entries]}
    if args.stichtag == "20210915":
        href = "AdriaTriest"
    else:
        href = "EVRF2000"
    print(f"[INFO] GKZ {mid} | Quelle {args.source} | {len(tiles)} Kacheln "
          f"({len(entries)} GeoTIFFs) | BEV-Stichtag {args.stichtag}", flush=True)
    print(f"[INFO] BEV-Hoehenbezug gemaess Serienmetadaten: {href}")
    prior_hashes = {e["url"]: e.get("sha256") for e in old.get("files", [])}
    records = []
    for entry in entries:
        print(f"[PLAN] {entry['model']} N{entry['tile_n']} E{entry['tile_e']}: {entry['url']}",
              flush=True)
        saved = dict(entry)
        dest = Path(entry["file"])
        if args.download:
            digest, size = download_one(entry["url"], dest, args.max_file_gb,
                                       expected_hash=prior_hashes.get(entry["url"]))
            saved.update(sha256=digest, bytes=size)
        elif dest.is_file():
            digest = sha256(dest)
            if prior_hashes.get(entry["url"]) and prior_hashes[entry["url"]] != digest:
                raise ValueError(f"Vorhandene Datei weicht vom Lockfile ab: {dest}")
            saved.update(sha256=digest, bytes=dest.stat().st_size)
        records.append(saved)
        # Save progress following each successful completed file.
        if args.download:
            target.mkdir(parents=True, exist_ok=True)
            manifest = {**request, "generated_utc": datetime.now(timezone.utc).isoformat(),
                        "horizontal_crs": "EPSG:3035", "height_reference": href,
                        "selection_note": "50-km-Raster anhand Geometrie; kein Nachweis der tatsaechlichen BEV-Abdeckung",
                        "files": records}
            temp = locks.with_suffix(".tmp")
            temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temp, locks)
    if not args.download:
        print("[HINWEIS] Nur Downloadplan. Mit --download alle oben genannten Dateien beziehen.")
        print(f"[INFO] Zielordner: {target}")
    else:
        print(f"[OK] Download und Lockfile: {locks}")
        print("[HINWEIS] Originale 50-km-Raster koennen gross sein. "
              "Vor Hoehenanalyse passende kleine, gleich ausgerichtete Ausschnitte erzeugen.")
        print("[HINWEIS] BEV-Stichtag ist nicht das Aufnahmejahr jedes einzelnen Gebaeudes.")


if __name__ == "__main__":
    main()
