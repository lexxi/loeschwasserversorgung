#!/usr/bin/env python3
"""Compare two zoning snapshots spatially (tolerant of CRS / GeoJSON rounding).

This is a data comparison, not a determination of legally effective zoning.
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

FIELDS = ("KATEGORIE", "WIDMUNG", "WIDCODE", "CODE", "BEZEICHNUNG",
          "ZUSAETZLICHE_FESTLEGUNG", "NAEHERE_BESCHREIBUNG")
IGNORE = {"LAST_EXPORT", "GEMNR_INT"}

def value(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()

def load(path):
    g = gpd.read_file(path)
    if g.empty or g.crs is None:
        raise ValueError(f"Missing features/CRS: {path}")
    if g.geometry.isna().any() or g.geometry.is_empty.any():
        raise ValueError(f"Missing geometries: {path}")
    if not g.geometry.is_valid.all():
        raise ValueError(f"Invalid geometries: {path}")
    return g.to_crs(epsg=31287).reset_index(drop=True)

def signature(g, i):
    row = g.iloc[i]
    return {field: value(row[field]) for field in FIELDS if field in g.columns}

def diff_fields(a, ai, b, bi):
    sa, sb = signature(a, ai), signature(b, bi)
    return [field for field in FIELDS if sa.get(field, "") != sb.get(field, "")]

def details(g, idx):
    row = g.iloc[idx]
    return {"index": int(idx), "OBJECTID": value(row.get("OBJECTID")),
            "KATEGORIE": value(row.get("KATEGORIE")),
            "WIDMUNG": value(row.get("WIDMUNG")),
            "area_m2": round(float(row.geometry.area), 2)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("previous", type=Path)
    p.add_argument("current", type=Path)
    p.add_argument("--out", type=Path, default=Path("data/processed/zoning_comparison"))
    p.add_argument("--match-min-iou", type=float, default=0.5,
                   help="Minimum intersection-over-union for candidate matching")
    p.add_argument("--geometry-equal-iou", type=float, default=0.9999,
                   help="Tolerance for considering polygons geometrically unchanged")
    args = p.parse_args()
    if not 0 < args.match_min_iou < args.geometry_equal_iou <= 1:
        p.error("Require 0 < --match-min-iou < --geometry-equal-iou <= 1")
    old, new = load(args.previous), load(args.current)
    candidates = []
    sindex = new.sindex
    for i, geom in enumerate(old.geometry):
        for j in sindex.query(geom, predicate="intersects"):
            other = new.geometry.iloc[int(j)]
            overlap = geom.intersection(other).area
            if overlap <= 0:
                continue
            union = geom.area + other.area - overlap
            iou = overlap / union if union else 0.0
            if iou < args.match_min_iou:
                continue
            changed = diff_fields(old, i, new, int(j))
            # Prefer same semantic designation if geometry ties (duplicate areas).
            candidates.append((iou, not changed, int(i), int(j), changed))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    used_old, used_new, matches = set(), set(), []
    for iou, same_attrs, i, j, changed in candidates:
        if i in used_old or j in used_new:
            continue
        used_old.add(i)
        used_new.add(j)
        matches.append((i, j, iou, changed))
    changes = []
    unchanged = 0
    geom_only = 0
    attr_only = 0
    both = 0
    for i, j, iou, changed in matches:
        geom_changed = iou < args.geometry_equal_iou
        if not geom_changed and not changed:
            unchanged += 1
            continue
        if geom_changed and changed:
            both += 1
        elif geom_changed:
            geom_only += 1
        else:
            attr_only += 1
        changes.append({"previous_index": i, "current_index": j,
                        "previous_OBJECTID": details(old, i)["OBJECTID"],
                        "current_OBJECTID": details(new, j)["OBJECTID"],
                        "geometry_iou": round(iou, 8),
                        "geometry_changed": geom_changed,
                        "changed_fields": ",".join(changed),
                        "previous_KATEGORIE": details(old, i)["KATEGORIE"],
                        "current_KATEGORIE": details(new, j)["KATEGORIE"],
                        "previous_WIDMUNG": details(old, i)["WIDMUNG"],
                        "current_WIDMUNG": details(new, j)["WIDMUNG"]})
    added = [details(new, j) for j in range(len(new)) if j not in used_new]
    removed = [details(old, i) for i in range(len(old)) if i not in used_old]
    # Unmatched current features are candidates for new/changed geometries,
    # not automatically newly zoned land. Compare against ALL previous polygons.
    new_indices = [j for j in range(len(new)) if j not in used_new]
    overlap_rows = []
    old_spatial = old.sindex
    added_geometries = new.iloc[new_indices].copy()
    for j in new_indices:
        geom = new.geometry.iloc[j]
        prior_geometries = []
        for i in old_spatial.query(geom, predicate="intersects"):
            i = int(i)
            intersection = geom.intersection(old.geometry.iloc[i])
            overlap_area = float(intersection.area)
            if overlap_area <= 0:
                continue
            prior_geometries.append(intersection)
            overlap_rows.append({
                "new_index": j,
                "new_OBJECTID": details(new, j)["OBJECTID"],
                "new_KATEGORIE": details(new, j)["KATEGORIE"],
                "new_WIDMUNG": details(new, j)["WIDMUNG"],
                "previous_index": i,
                "previous_OBJECTID": details(old, i)["OBJECTID"],
                "previous_KATEGORIE": details(old, i)["KATEGORIE"],
                "previous_WIDMUNG": details(old, i)["WIDMUNG"],
                "overlap_m2": round(overlap_area, 2),
                "fraction_of_new": round(overlap_area / geom.area, 6),
            })
        from shapely.ops import unary_union
        covered = geom.intersection(unary_union(prior_geometries)).area if prior_geometries else 0.0
        added_geometries.loc[j, "previous_coverage_m2"] = round(covered, 2)
        added_geometries.loc[j, "previous_coverage_pct"] = round(100 * covered / geom.area, 2)
        added_geometries.loc[j, "not_previously_covered_m2"] = round(max(0, geom.area - covered), 2)
    # The GeoJSON retains the source attributes and adds coverage fields.
    # GeoJSON in WGS84 is convenient for QGIS and other map viewers.
    if not added_geometries.empty:
        added_geometries.to_crs(epsg=4326).to_file(
            args.out / "unmatched_current.geojson", driver="GeoJSON"
        )
    else:
        (args.out / "unmatched_current.geojson").write_text(
            '{"type":"FeatureCollection","features":[]}\\n', encoding="utf-8"
        )
    overlap_columns = [
        "new_index", "new_OBJECTID", "new_KATEGORIE", "new_WIDMUNG",
        "previous_index", "previous_OBJECTID", "previous_KATEGORIE",
        "previous_WIDMUNG", "overlap_m2", "fraction_of_new",
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(changes, columns=[
        "previous_index","current_index","previous_OBJECTID","current_OBJECTID",
        "geometry_iou","geometry_changed","changed_fields",
        "previous_KATEGORIE","current_KATEGORIE","previous_WIDMUNG","current_WIDMUNG"
    ]).to_csv(args.out / "matched_changes.csv", sep=";", index=False, encoding="utf-8-sig")
    cols = ["index", "OBJECTID", "KATEGORIE", "WIDMUNG", "area_m2"]
    pd.DataFrame(added, columns=cols).to_csv(args.out / "unmatched_current.csv", sep=";", index=False, encoding="utf-8-sig")
    pd.DataFrame(removed, columns=cols).to_csv(args.out / "unmatched_previous.csv", sep=";", index=False, encoding="utf-8-sig")
    pd.DataFrame(overlap_rows, columns=overlap_columns).to_csv(
        args.out / "previous_zoning_overlaps.csv", sep=";", index=False, encoding="utf-8-sig"
    )
    summary = {
        "previous_features": len(old), "current_features": len(new),
        "matched_pairs": len(matches), "unchanged_semantic_and_geometry": unchanged,
        "geometry_only_changes": geom_only, "attributes_only_changes": attr_only,
        "geometry_and_attribute_changes": both,
        "unmatched_previous": len(removed), "unmatched_current": len(added),
        "unmatched_current_overlap_pairs": len(overlap_rows),
        "unmatched_current_previously_covered_m2": round(float(added_geometries.get("previous_coverage_m2", pd.Series(dtype=float)).sum()), 2),
        "unmatched_current_not_previously_covered_m2": round(float(added_geometries.get("not_previously_covered_m2", pd.Series(dtype=float)).sum()), 2),
        "match_min_iou": args.match_min_iou,
        "geometry_equal_iou": args.geometry_equal_iou,
        "note": "One-to-one spatial matching with overlap tolerance. Splits/merges, overlapping records and borderline polygons require manual GIS review. This is not a legal-change detector. Overlaps may involve multiple previous zoning records; sum of pairwise overlap areas can double count."
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
