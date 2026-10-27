#!/usr/bin/env python3
"""AP2: BEV-ALS-Hoehen fuer alle OSM-Gebaeude via kleine COG-Teilabrufe.

--plan (Standard): Nur Bedarf und Kacheln zeigen, kein Netz.
--download: Ausgewaehlte DSM/DTM-Teilfenster laden, pruefen, lokal cachen.
--analyze: Alle Gebaeude mit vorhandenen gecachten Fenstern auswerten.
Ausgabe ist kein OIB-Fluchtniveau und keine GK-Klassifikation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds, bounds as window_bounds

from analyze_buildings_als_height import HEADERS, sample_building
from download_bev_als import BEV_ROOT, DATE_RE

ROOT = Path(__file__).resolve().parent.parent
BEV_GRID = 50000
NODATA = -9999.0


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def source_url(kind, date, tile_n, tile_e):
    filename = f"ALS_{kind}_CRS3035RES50000mN{tile_n}E{tile_e}.tif"
    return f"{BEV_ROOT}/{kind}/{date}/{filename}"


def plan_groups(frame, size, margin):
    groups = defaultdict(list)
    excluded = {}
    for i, row in frame.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
            excluded[i] = "invalid_geometry"
            continue
        centre = geom.centroid
        e = math.floor(centre.x / BEV_GRID) * BEV_GRID
        n = math.floor(centre.y / BEV_GRID) * BEV_GRID
        # A complete building footprint must fit the same BEV source tile.
        xmin, ymin, xmax, ymax = geom.bounds
        if xmin < e or ymin < n or xmax >= e+BEV_GRID or ymax >= n+BEV_GRID:
            excluded[i] = "crosses_bev_tile"
            continue
        gx = math.floor((centre.x-e)/size)
        gy = math.floor((centre.y-n)/size)
        groups[(n, e, gy, gx)].append(i)
    result = []
    for (n,e,gy,gx), indices in sorted(groups.items()):
        bb = frame.loc[indices].total_bounds
        # Tight envelope across owned buildings plus small sampling clearance.
        x0 = max(e, math.floor(bb[0]-margin))
        y0 = max(n, math.floor(bb[1]-margin))
        x1 = min(e+BEV_GRID, math.ceil(bb[2]+margin))
        y1 = min(n+BEV_GRID, math.ceil(bb[3]+margin))
        if x1 <= x0 or y1 <= y0:
            for i in indices:
                excluded[i] = "invalid_bounds"
            continue
        group_id = f"N{n}_E{e}_Y{gy:02d}_X{gx:02d}"
        result.append({"id":group_id,"n":n,"e":e,"indices":indices,
                       "bounds":[x0,y0,x1,y1]})
    return result, excluded


def cache_valid(folder, group, date):
    metadata_file = folder / "manifest.json"
    dom = folder / "dom.tif"
    dgm = folder / "dgm.tif"
    existing = [f.exists() for f in (metadata_file, dom, dgm)]
    if not any(existing):
        return False
    if not all(existing):
        raise RuntimeError(f"Unvollstaendiger Kachel-Cache: {folder}. "
                           "Bitte betroffene Dateien manuell pruefen; kein blindes Ueberschreiben.")
    meta = json.loads(metadata_file.read_text(encoding="utf-8"))
    if (meta.get("stichtag") != date or meta.get("requested_bounds") != group["bounds"]
            or meta.get("tile_id") != group["id"]):
        raise RuntimeError(f"Cache-Metadaten passen nicht zur Kachelplanung: {folder}")
    if (meta.get("urls") != {k:source_url(k,date,group["n"],group["e"])
                            for k in ("DSM","DTM")}):
        raise RuntimeError(f"Quell-URLs weichen vom Cache ab: {folder}")
    for kind, path in (("DSM",dom),("DTM",dgm)):
        if checksum(path) != meta.get("sha256",{}).get(kind):
            raise RuntimeError(f"Checksumme stimmt nicht: {path}")
    with rasterio.open(dom) as a, rasterio.open(dgm) as b:
        if (a.crs != b.crs or a.crs is None or a.crs.to_epsg() != 3035
                or a.transform != b.transform or a.width != b.width or a.height != b.height):
            raise RuntimeError(f"DOM/DGM nicht pixelgleich im Cache: {folder}")
    return True


def obtain(group, folder, date, limit_mb):
    if cache_valid(folder, group, date):
        print(f"[CACHE] {group['id']}: SHA256 geprueft", flush=True)
        return
    folder.mkdir(parents=True, exist_ok=True)
    bounds = group["bounds"]
    urls = {kind:source_url(kind,date,group["n"],group["e"]) for kind in ("DSM","DTM")}
    tmp = {kind:folder / f"{kind.lower()}.part.tif" for kind in ("DSM","DTM")}
    if any(p.exists() for p in tmp.values()):
        raise RuntimeError(f"Unvollstaendige .part.tif in {folder}; vor erneutem Start pruefen.")
    same_bounds, same_transform, width, height = None, None, None, None
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                          GDAL_HTTP_MAX_RETRY="2", GDAL_HTTP_RETRY_DELAY="2"):
            for kind in ("DSM","DTM"):
                url = urls[kind]
                print(f"[DOWNLOAD] {group['id']} {kind}: {url}", flush=True)
                with rasterio.open("/vsicurl/"+url) as src:
                    if (src.crs is None or src.crs.to_epsg()!=3035 or src.count!=1
                            or not np.allclose(src.res,(1.0,1.0),atol=1e-8)
                            or src.transform.b != 0 or src.transform.d != 0):
                        raise ValueError(f"Unerwartetes BEV-Rasterformat: {url}")
                    w = from_bounds(*bounds,transform=src.transform)
                    if kind == "DSM":
                        left = math.floor(w.col_off+1e-7)
                        top = math.floor(w.row_off+1e-7)
                        right = math.ceil(w.col_off+w.width-1e-7)
                        bottom = math.ceil(w.row_off+w.height-1e-7)
                        if left < 0 or top < 0 or right > src.width or bottom > src.height:
                            raise ValueError(f"BEV-Rasterrand erreicht: {group['id']}")
                        w = Window(left,top,right-left,bottom-top)
                        same_bounds = window_bounds(w,src.transform)
                        same_transform = src.window_transform(w)
                        width,height = int(w.width),int(w.height)
                    else:
                        w = from_bounds(*same_bounds, transform=src.transform)
                        values = [w.col_off,w.row_off,w.width,w.height]
                        if any(abs(v-round(v))>1e-5 for v in values):
                            raise ValueError(f"DSM/DTM-Pixelgitter verschieden: {group['id']}")
                        w = Window(*(int(round(v)) for v in values))
                        if (w.col_off<0 or w.row_off<0 or w.col_off+w.width>src.width
                                or w.row_off+w.height>src.height
                                or int(w.width)!=width or int(w.height)!=height
                                or not src.window_transform(w).almost_equals(
                                    same_transform,precision=1e-6)):
                            raise ValueError(f"DSM/DTM-Ausrichtung verschieden: {group['id']}")
                    if width*height*4 > limit_mb*1024**2:
                        raise RuntimeError(
                            f"{group['id']} braucht {width*height*4/1024**2:.1f} MiB "
                            f"ungepackt pro Modell; Limit {limit_mb} MiB")
                    masked = src.read(1,window=w,masked=True)
                    pixels = np.asarray(masked.filled(NODATA),dtype=np.float32)
                    if pixels.shape!=(height,width) or not np.isfinite(pixels).all():
                        raise ValueError(f"Rasterlesefehler: {group['id']}/{kind}")
                    if not np.ma.count(masked):
                        raise ValueError(f"Kein gueltiger Pixel: {group['id']}/{kind}")
                    profile = {"driver":"GTiff","width":width,"height":height,
                               "count":1,"dtype":"float32","crs":"EPSG:3035",
                               "transform":same_transform,"nodata":NODATA,
                               "compress":"deflate","predictor":3,
                               "tiled":True,"blockxsize":256,"blockysize":256}
                    with rasterio.open(tmp[kind],"w",**profile) as dest:
                        dest.write(pixels,1)
        for kind,path in (("DSM",folder/"dom.tif"),("DTM",folder/"dgm.tif")):
            os.replace(tmp[kind],path)
        metadata = {
            "generated_utc":datetime.now(timezone.utc).isoformat(),
            "tile_id":group["id"],"stichtag":date,
            "requested_bounds":bounds,"actual_bounds":list(same_bounds),
            "crs":"EPSG:3035","width":width,"height":height,
            "urls":urls,
            "sha256":{"DSM":checksum(folder/"dom.tif"),"DTM":checksum(folder/"dgm.tif")},
            "source_warning":"Datenstichtag ist nicht zwingend Befliegungsdatum; vertikalen Bezug separat pruefen.",
        }
        pending=folder/"manifest.json.part"
        pending.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(pending,folder/"manifest.json")
    finally:
        # Temporary files are disposable; completed, manifest-pinned files are never overwritten.
        for path in tmp.values():
            path.unlink(missing_ok=True)


def analyze(frame, groups, excluded, root, date, mid, inset=1.0, min_pixels=5):
    quality=Counter()
    results={}
    for i,why in excluded.items():
        results[i]={"quality":why}
    for group in groups:
        folder=root/group["id"]
        if not cache_valid(folder,group,date):
            for i in group["indices"]:
                results[i]={"quality":"not_downloaded"}
            continue
        with rasterio.open(folder/"dom.tif") as dom, rasterio.open(folder/"dgm.tif") as dgm:
            for i in group["indices"]:
                measured,status=sample_building(frame.loc[i].geometry,dom,dgm,inset,min_pixels)
                results[i]={"quality":status,**(measured or {})}
    areas=frame.to_crs(31287).geometry.area
    rows=[]
    for i,row in frame.iterrows():
        item={"osm_id":str(row["osm_id"]),"building":str(row.get("building") or ""),
              "footprint_m2":round(float(areas.loc[i]),1),
              "height_median_m":"","height_p90_m":"","height_max_m":"",
              "valid_pixels":0,"footprint_pixels":0,"valid_ratio":0,
              "quality":"not_assessed",
              "note":"ALS DOM-DGM Objekthoehe, kein OIB-Fluchtniveau oder GK"}
        item.update(results.get(i,{}))
        quality[item["quality"]]+=1
        rows.append(item)
    out=ROOT/"reports"/mid/"gk_inventory"
    out.mkdir(parents=True,exist_ok=True)
    csv_path=out/"gebaeude_als_hoehen_gemeinde.csv"
    with csv_path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=HEADERS,delimiter=";")
        w.writeheader()
        w.writerows(sorted(rows,key=lambda r:r["osm_id"]))
    summary={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "municipality_id":mid,"buildings":len(frame),"groups":len(groups),
        "quality_counts":dict(quality),"estimated":quality["estimated"],
        "stichtag":date,"source":"BEV ALS DSM/DTM COG Range Reads",
        "vertical_reference_note":"Hoehenreferenz nur aus externen BEV-Serienmetadaten abzuleiten.",
        "limitation":"Objekthoehen-Indizien, keine Geschosszahl, kein Fluchtniveau, keine GK.",
    }
    js_path=out/"als_hoehen_gemeinde_summary.json"
    js_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[OK] Gebaeude: {len(rows)}; Hoehe geschaetzt: {quality['estimated']}",flush=True)
    print(f"[INFO] Qualitaet: {json.dumps(dict(quality),ensure_ascii=False)}",flush=True)
    print(f"[OK] {csv_path}\n[OK] {js_path}",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde",default="20619")
    parser.add_argument("--stichtag",default="20250915")
    parser.add_argument("--cell-m",type=int,default=2000,help="Zellenbreite, Teiler von 50000")
    parser.add_argument("--margin-m",type=int,default=5,help="Randpuffer um Gebaeudeumrisse")
    parser.add_argument("--max-tile-mb",type=int,default=80)
    parser.add_argument("--max-tiles",type=int,default=0,help="0=alle; beim Download zuerst z.B. 3")
    parser.add_argument("--download",action="store_true",help="Fehlende Rasterfenster downloaden")
    parser.add_argument("--analyze",action="store_true",help="Hoehen aus Cache fuer alle Gebaeude auswerten")
    args=parser.parse_args()
    if not (len(args.gemeinde)==5 and args.gemeinde.isdigit() and args.gemeinde.startswith("2")):
        parser.error("Ungueltige Gemeindekennzahl")
    if not DATE_RE.fullmatch(args.stichtag):
        parser.error("Stichtag muss YYYYMMDD sein")
    if (args.cell_m<100 or BEV_GRID % args.cell_m or args.margin_m<1 or
            args.max_tile_mb<5 or args.max_tiles<0):
        parser.error("cell-m muss Teiler von 50000 sein; Margin, Limit und Anzahl pruefen")
    building_file=ROOT/"data"/"processed"/args.gemeinde/"osm"/"buildings.geojson"
    if not building_file.is_file():
        parser.error(f"Gebaeude fehlen: {building_file}")
    raw=gpd.read_file(building_file)
    if raw.empty or raw.crs is None or "osm_id" not in raw:
        raise ValueError("OSM-Gebaeudedaten ungueltig")
    if raw["osm_id"].astype(str).duplicated().any():
        raise ValueError("Doppelte OSM-ID")
    frame=raw.to_crs(3035)
    groups,excluded=plan_groups(frame,args.cell_m,args.margin_m)
    root=ROOT/"data"/"raw"/"bev"/args.stichtag/"municipality_tiles"/args.gemeinde
    print(f"[PLAN] {len(frame)} Gebaeude; {len(groups)} belegte {args.cell_m}m-Zellen; "
          f"{len(excluded)} Rand-/Geometrieprueffaelle",flush=True)
    print(f"[PLAN] Rastercache {root}",flush=True)
    for g in groups:
        print(f"[PLAN] {g['id']}: {len(g['indices'])} Gebaeude, "
              f"Fenster {g['bounds']}",flush=True)
    if args.download:
        candidates=groups[:args.max_tiles] if args.max_tiles else groups
        print(f"[INFO] Bearbeite {len(candidates)} von {len(groups)} Zellen",flush=True)
        for j,g in enumerate(candidates,1):
            obtain(g,root/g["id"],args.stichtag,args.max_tile_mb)
            print(f"[FORTSCHRITT] {j}/{len(candidates)}",flush=True)
    if args.analyze:
        analyze(frame,groups,excluded,root,args.stichtag,args.gemeinde)
    if not args.download and not args.analyze:
        print("[HINWEIS] Nur Planung; --download zum Bezug; --analyze zur Auswertung.",flush=True)
    print("[HINWEIS] Keine OIB-GK-Klassifikation oder Loeschwasserbedarfsbewertung.",flush=True)


if __name__=="__main__":
    main()
