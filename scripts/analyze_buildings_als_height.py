#!/usr/bin/env python3
"""AP2: Schaetzung der Gebaeude-Objekthoehe aus lokalem BEV ALS-DOM und ALS-DGM.

Nur gleiches Rastergitter, gleicher Datenstand und gleicher Hoehenbezug erlaubt.
Kein Fluchtniveau, keine Geschosszahl und keine baurechtliche GK.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, transform as window_transform

ROOT = Path(__file__).resolve().parent.parent
HEADERS = (
    "osm_id", "building", "footprint_m2", "height_median_m", "height_p90_m",
    "height_max_m", "valid_pixels", "footprint_pixels", "valid_ratio",
    "quality", "note",
)


def sample_building(geom, dom, dtm, inset, minimum_pixels):
    if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
        return None, "invalid_geometry"
    # Avoid mixed pixels from trees, walls and surrounding terrain at roof edges.
    sampling = geom.buffer(-inset) if inset > 0 else geom
    if sampling.is_empty:
        sampling = geom
    bounds_window = from_bounds(*sampling.bounds, transform=dom.transform)
    col0, row0 = bounds_window.col_off, bounds_window.row_off
    col1, row1 = col0 + bounds_window.width, row0 + bounds_window.height
    left, top = max(0, int(np.floor(min(col0, col1)))), max(0, int(np.floor(min(row0, row1))))
    right, bottom = min(dom.width, int(np.ceil(max(col0, col1)))), min(dom.height, int(np.ceil(max(row0, row1))))
    if right <= left or bottom <= top:
        return None, "outside_raster"
    # Guard against accidental giant polygon/window.
    if (right-left)*(bottom-top) > 250000:
        return None, "oversized_geometry"
    win = Window(left, top, right-left, bottom-top)
    dsm = dom.read(1, window=win, masked=True).astype("float64")
    dem = dtm.read(1, window=win, masked=True).astype("float64")
    interior = geometry_mask([sampling], out_shape=dsm.shape,
                             transform=window_transform(win, dom.transform), invert=True)
    total = int(interior.sum())
    valid = interior & ~np.ma.getmaskarray(dsm) & ~np.ma.getmaskarray(dem)
    valid &= np.isfinite(dsm.data) & np.isfinite(dem.data)
    # Negative residuals can arise from mismatch or normal ALS noise; do not silently clip.
    values = (dsm.data-dem.data)[valid]
    n = len(values)
    result = {
        "height_median_m": round(float(np.median(values)), 2) if n else "",
        "height_p90_m": round(float(np.percentile(values, 90)), 2) if n else "",
        "height_max_m": round(float(np.max(values)), 2) if n else "",
        "valid_pixels": n,
        "footprint_pixels": total,
        "valid_ratio": round(n/total, 3) if total else 0,
    }
    if n < minimum_pixels:
        return result, "too_few_pixels"
    if total and n/total < 0.7:
        return result, "low_coverage"
    if result["height_median_m"] < -1 or result["height_median_m"] > 100:
        return result, "implausible_height"
    return result, "estimated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", default="20619")
    parser.add_argument("--dom", type=Path, required=True, help="Lokal gespeichertes BEV ALS-DOM GeoTIFF")
    parser.add_argument("--dgm", type=Path, required=True, help="Passendes BEV ALS-DGM GeoTIFF")
    parser.add_argument("--dom-height-reference", required=True, choices=("EVRF2000", "AdriaTriest"))
    parser.add_argument("--dgm-height-reference", required=True, choices=("EVRF2000", "AdriaTriest"))
    parser.add_argument("--dom-snapshot", required=True, help="BEV-Datenstand, z. B. 2025")
    parser.add_argument("--dgm-snapshot", required=True, help="BEV-Datenstand, z. B. 2025")
    parser.add_argument("--minimum-pixels", type=int, default=5)
    parser.add_argument("--inset-m", type=float, default=1.0)
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit() or not mid.startswith("2"):
        parser.error("Ungueltige Kaerntner Gemeinde-ID")
    if args.dom_height_reference != args.dgm_height_reference:
        parser.error("DOM und DGM haben unterschiedliche Hoehenbezugssysteme: keine Subtraktion!")
    if args.dom_snapshot != args.dgm_snapshot:
        parser.error("Unterschiedliche BEV-Datenstaende: bitte passendes Paar benutzen")
    if args.minimum_pixels < 1 or args.inset_m < 0:
        parser.error("Parameter fuer Mindestpixel und Innenpuffer muessen gueltig sein")
    buildings_path = ROOT / "data" / "processed" / mid / "osm" / "buildings.geojson"
    if not buildings_path.is_file():
        parser.error(f"Gebaeudedaten fehlen: {buildings_path}")
    for name, file in (("DOM", args.dom), ("DGM", args.dgm)):
        if not file.is_file():
            parser.error(f"{name} GeoTIFF fehlt: {file}")
    frame = gpd.read_file(buildings_path)
    if frame.empty or frame.crs is None or "osm_id" not in frame:
        raise ValueError("Gebaeudedaten leer oder ungueltig")
    if frame["osm_id"].astype(str).duplicated().any():
        raise ValueError("Doppelte OSM-IDs")
    with rasterio.open(args.dom) as dom, rasterio.open(args.dgm) as dtm:
        if dom.crs is None or dtm.crs is None:
            raise ValueError("Raster ohne CRS")
        if dom.crs != dtm.crs or dom.transform != dtm.transform or dom.width != dtm.width or dom.height != dtm.height:
            raise ValueError("DOM und DGM muessen exakt auf demselben Rastergitter liegen. "
                             "Bitte zuerst passende gleich ausgerichtete Ausschnitte erzeugen.")
        if dom.count != 1 or dtm.count != 1:
            raise ValueError("Nur einbandige Hoehenraster werden unterstuetzt")
        if dom.transform.b != 0 or dom.transform.d != 0:
            raise ValueError("Gedrehte Raster werden derzeit nicht unterstuetzt")
        projected = frame.to_crs(dom.crs)
        area_frame = frame.to_crs(31287)
        results = []
        quality = Counter()
        for i, row in projected.iterrows():
            measured, status = sample_building(row.geometry, dom, dtm, args.inset_m, args.minimum_pixels)
            item = {
                "osm_id": str(row["osm_id"]),
                "building": str(row.get("building") or ""),
                "footprint_m2": round(float(area_frame.loc[i].geometry.area), 1),
                "height_median_m": "", "height_p90_m": "", "height_max_m": "",
                "valid_pixels": 0, "footprint_pixels": 0, "valid_ratio": 0,
                "quality": status,
                "note": "Nur DOM-DGM-Objekthoehe, kein Fluchtniveau oder GK",
            }
            if measured:
                item.update(measured)
            quality[status] += 1
            results.append(item)
    outdir = ROOT / "reports" / mid / "gk_inventory"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "gebaeude_als_hoehen.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: r["osm_id"]))
    metadata = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "buildings": len(results),
        "estimated": quality["estimated"],
        "quality_counts": dict(quality),
        "dom_file": str(args.dom),
        "dgm_file": str(args.dgm),
        "snapshot": args.dom_snapshot,
        "height_reference": args.dom_height_reference,
        "crs_match_and_grid_alignment_checked": True,
        "inset_m": args.inset_m,
        "minimum_pixels": args.minimum_pixels,
        "limitations": [
            "Nur ungepruefte relative Objekthoehen aus ALS-Rasterdaten.",
            "Georeferenzierung und Differenz der vertikalen Bezugssysteme nur ueber Benutzerangaben geprueft.",
            "Bewuchs, Dachgeometrie, Datenalter und Pixelgroesse koennen Ergebnisse verfaelschen.",
            "Nicht mit OIB-Fluchtniveau oder Anzahl der Geschosse gleichzusetzen.",
            "Keine GK und kein Loeschwasserbedarf ableitbar.",
        ],
    }
    json_path = outdir / "als_hoehen_summary.json"
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"[OK] {len(results)} Gebaeude; Hoehe geschaetzt: {quality['estimated']}")
    print("[INFO] Qualitaet:", json.dumps(dict(quality), ensure_ascii=False))
    print(f"[OK] {csv_path}")
    print(f"[OK] {json_path}")
    print("[HINWEIS] Keine GK-Zuordnung und kein baurechtlicher Hoehennachweis.")


if __name__ == "__main__":
    main()
