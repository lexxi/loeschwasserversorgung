#!/usr/bin/env python3
"""Kleine ALS DSM/DTM-Ausschnitte direkt aus BEV-COG per HTTPS Range Requests.

Kein Vollkacheldownload. Ein gemeinsames Rastergitter fuer beide Modelle.
Pilot: 1 Gebaeude (explizit oder automatisch zentral gewaehlt) + Radius.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.windows import Window

from download_bev_als import BEV_ROOT, GRID, DATE_RE

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde", default="20619")
    p.add_argument("--stichtag", default="20250915")
    p.add_argument("--osm-id", help="Gebaeude-ID z.B. way/1234; ohne ID: naechstes Gebaeude am Schwerpunkt")
    p.add_argument("--radius-m", type=int, default=1000)
    p.add_argument("--max-mb", type=int, default=80, help="Obergrenze fuer je einen unkomprimierten lokalen Ausschnitt")
    args = p.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        p.error("Ungueltige Gemeindenummer")
    if not DATE_RE.fullmatch(args.stichtag):
        p.error("Ungueltiger BEV-Stichtag YYYYMMDD")
    if args.radius_m < 100 or args.max_mb < 5:
        p.error("Radius mindestens 100 m, Groessenlimit mindestens 5 MiB")
    buildings_file = ROOT / "data" / "processed" / mid / "osm" / "buildings.geojson"
    if not buildings_file.is_file():
        p.error(f"OSM-Gebaeude fehlen: {buildings_file}")
    frame = gpd.read_file(buildings_file)
    if frame.empty or frame.crs is None or "osm_id" not in frame:
        raise ValueError("Gebaeude fehlen oder CRS/OSM-ID ungueltig")
    g = frame.to_crs(3035).copy()
    ids = g["osm_id"].astype(str)
    if args.osm_id:
        found = g.loc[ids == args.osm_id]
        if len(found) != 1:
            p.error(f"OSM-ID nicht genau einmal gefunden: {args.osm_id}")
        selected = found.iloc[0]
    else:
        # Deterministic: select building nearest to the centre of all centroids.
        centres = g.geometry.centroid
        cx = float(centres.x.mean())
        cy = float(centres.y.mean())
        selected = g.iloc[int(((centres.x-cx)**2 + (centres.y-cy)**2).argmin())]
    osm_id = str(selected["osm_id"])
    centre = selected.geometry.centroid
    x, y = float(centre.x), float(centre.y)
    e = math.floor(x / GRID) * GRID
    n = math.floor(y / GRID) * GRID
    # Keep the pilot inside one source tile. The complete municipality can cross tiles.
    # Align to 1m source grid whose origin is the integer BEV 50km tile corner.
    x0, x1 = math.floor(x-args.radius_m), math.ceil(x+args.radius_m)
    y0, y1 = math.floor(y-args.radius_m), math.ceil(y+args.radius_m)
    if not (e <= x0 < x1 <= e+GRID and n <= y0 < y1 <= n+GRID):
        p.error("Ausschnitt ueberschreitet eine BEV-Kachelgrenze: kleineren Radius/anderes Gebaeude waehlen")
    planned_width, planned_height = x1-x0, y1-y0
    if planned_width*planned_height*4 > args.max_mb*1024*1024:
        p.error(f"Unkomprimierter Ausschnitt pro Modell etwa {planned_width*planned_height*4/1024**2:.1f} MiB > Limit")
    outdir = ROOT / "data" / "raw" / "bev" / args.stichtag / "subsets" / mid
    outdir.mkdir(parents=True, exist_ok=True)
    urls = {}
    outputs = {}
    hashes = {}
    out_transform = None
    aligned_bounds = None
    width = height = None
    nodata = -9999.0
    # Rasterio/GDAL uses HTTPS range requests for source COG blocks.
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MAX_RETRY="2",
        GDAL_HTTP_RETRY_DELAY="2",
    ):
        for kind, basename in (("DSM", "dom_malta.tif"), ("DTM", "dgm_malta.tif")):
            filename = f"ALS_{kind}_CRS3035RES50000mN{n}E{e}.tif"
            url = f"{BEV_ROOT}/{kind}/{args.stichtag}/{filename}"
            urls[kind] = url
            dest = outdir / basename
            if dest.exists():
                raise FileExistsError(f"{dest} existiert schon. Keine stille Datenueberschreibung.")
            print(f"[INFO] {kind} Ausschnitt per HTTPS-Range: {url}", flush=True)
            try:
                with rasterio.open("/vsicurl/" + url) as src:
                    if src.crs is None or src.crs.to_epsg() != 3035:
                        raise ValueError(f"{kind}: erwartetes CRS EPSG:3035 fehlt")
                    if (not np.allclose(src.res, (1.0, 1.0), atol=1e-8)
                            or src.transform.b != 0 or src.transform.d != 0):
                        raise ValueError(f"{kind}: Raster hat nicht 1m Aufloesung oder ist gedreht")
                    win = rasterio.windows.from_bounds(x0, y0, x1, y1, transform=src.transform)
                    # Snap the requested physical bounds OUTWARDS to actual BEV pixel boundaries.
                    # BEV COG raster origin need not be aligned to whole-number metre values.
                    if kind == "DSM":
                        left = math.floor(win.col_off + 1e-7)
                        top = math.floor(win.row_off + 1e-7)
                        right = math.ceil(win.col_off + win.width - 1e-7)
                        bottom = math.ceil(win.row_off + win.height - 1e-7)
                        if left < 0 or top < 0 or right > src.width or bottom > src.height:
                            raise ValueError("DSM Ausschnitt ausserhalb des Kachelrasters")
                        win = Window(left, top, right-left, bottom-top)
                        out_transform = src.window_transform(win)
                        width, height = int(win.width), int(win.height)
                        aligned_bounds = rasterio.windows.bounds(win, src.transform)
                        print(f"[INFO] Am echten BEV-Raster ausgerichtet: {width}x{height} Pixel, "
                              f"Ursprung {out_transform.c:.3f}/{out_transform.f:.3f}", flush=True)
                    else:
                        # Both outputs MUST use one pixel grid for subsequent DOM-DGM subtraction.
                        win = rasterio.windows.from_bounds(*aligned_bounds, transform=src.transform)
                        vals = (win.col_off, win.row_off, win.width, win.height)
                        if any(abs(v-round(v)) > 1e-5 for v in vals):
                            raise ValueError(
                                "DSM und DTM verwenden unterschiedliche Pixelurspruenge. "
                                "Kein stilles Resampling; zuerst Quellenraster vergleichen.")
                        win = Window(*(int(round(v)) for v in vals))
                        if (win.col_off < 0 or win.row_off < 0 or
                                win.col_off+win.width > src.width or
                                win.row_off+win.height > src.height or
                                win.width != width or win.height != height):
                            raise ValueError("DTM Rastergrenzen passen nicht zum DSM-Ausschnitt")
                        if not src.window_transform(win).almost_equals(out_transform, precision=1e-6):
                            raise ValueError("DTM Rastertransform passt nicht zum DSM")
                    if width * height * 4 > args.max_mb * 1024**2:
                        raise ValueError("Am Raster ausgerichteter Ausschnitt zu gross")
                    arr = src.read(1, window=win, masked=True, boundless=False)
                    data = np.asarray(arr.filled(nodata), dtype=np.float32)
                    if not np.isfinite(data).all():
                        raise ValueError(f"{kind}: NaN/Inf in Rasterdaten")
                    if int(np.count_nonzero(~np.ma.getmaskarray(arr))) == 0:
                        raise ValueError(f"{kind}: nur NoData im gewaehlten Ausschnitt")
                    profile = {
                        "driver":"GTiff","height":height,"width":width,
                        "count":1,"dtype":"float32","crs":"EPSG:3035",
                        "transform":out_transform,"nodata":nodata,
                        "tiled":True,"blockxsize":256,"blockysize":256,
                        "compress":"deflate","predictor":3
                    }
                    with rasterio.open(dest, "w", **profile) as dst:
                        dst.write(data, 1)
            except (RasterioIOError, OSError) as ex:
                raise RuntimeError(f"Remote COG kann nicht ausschnittweise gelesen werden: {url}. "
                                   "Bitte BEV-/GDAL-HTTP-Range-Unterstuetzung pruefen.") from ex
            outputs[kind] = str(dest)
            hashes[kind] = sha(dest)
            print(f"[OK] {dest} ({dest.stat().st_size/1024**2:.1f} MiB)",flush=True)
    manifest = {
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "municipality_id":mid,"selected_osm_id":osm_id,
        "stichtag":args.stichtag,"radius_m":args.radius_m,
        "tile":{"n":n,"e":e},"requested_bounds_epsg3035":[x0,y0,x1,y1],
        "aligned_bounds_epsg3035":list(aligned_bounds),
        "urls":urls,"output_files":outputs,"sha256":hashes,
        "height_reference_claim":"AdriaTriest" if args.stichtag=="20210915" else "EVRF2000",
        "warning":"Nur technischer Testausschnitt. BEV Stichtag ist nicht ALS Befliegungsdatum.",
    }
    manifest_path=outdir/"subset_manifest.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[OK] Rastergitter {width} x {height}, 1m, EPSG:3035. Manifest: {manifest_path}")
    print("[HINWEIS] Hoehenmodell nur indikativ, kein baurechtliches Fluchtniveau.")


if __name__=="__main__":
    main()
