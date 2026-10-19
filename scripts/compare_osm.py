#!/usr/bin/env python3
"""Compare historical and current Malta OSM buildings using stable OSM element IDs.

Geometry comparisons are tolerance-based; output is descriptive, not a land-use assessment.
"""
import argparse
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd

TAGS = ["building", "name", "amenity", "tourism", "shop", "addr:housenumber",
        "addr:street", "addr:city", "building:use", "building:levels"]

def normalized(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value).strip()

def read(path):
    data = gpd.read_file(path)
    if data.crs is None:
        raise ValueError(f"Missing CRS: {path}")
    if "osm_id" in data:
        identifiers = data["osm_id"].astype(str)
    elif "@id" in data:
        identifiers = data["@id"].astype(str)
    elif "id" in data:
        identifiers = data["id"].astype(str)
    else:
        raise ValueError(f"No OSM element ID in {path}")
    if not identifiers.str.match(r"^(way|relation)/[0-9]+$").all():
        raise ValueError(f"Unexpected OSM identifiers in {path}; expected way/123 or relation/123")
    data = data.copy()
    data["osm_id"] = identifiers
    if data["osm_id"].duplicated().any():
        raise ValueError(f"Duplicate IDs in {path}")
    if data.geometry.isna().any() or data.geometry.is_empty.any():
        raise ValueError(f"Missing geometry in {path}")
    return data.set_index("osm_id", drop=False).to_crs(31287)

def attr(frame, item, field):
    return normalized(frame.at[item, field]) if field in frame.columns else ""

def detail(frame, item):
    row = {"osm_id": item, "area_m2": round(float(frame.at[item, "geometry"].area), 2)}
    row.update({field: attr(frame, item, field) for field in TAGS})
    return row

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("previous", type=Path)
    p.add_argument("current", type=Path)
    p.add_argument("--out", type=Path, default=Path("data/processed/osm_comparison"))
    p.add_argument("--geometry-tolerance-m", type=float, default=0.20,
                   help="Max Hausdorff distance before marking geometry as changed")
    args = p.parse_args()
    if args.geometry_tolerance_m < 0:
        p.error("Geometry tolerance must not be negative")
    previous, current = read(args.previous), read(args.current)
    old_ids, new_ids = set(previous.index), set(current.index)
    added_ids, removed_ids = sorted(new_ids - old_ids), sorted(old_ids - new_ids)
    shared_ids = sorted(old_ids & new_ids)
    changed = []
    for item in shared_ids:
        different_tags = [field for field in TAGS if attr(previous, item, field) != attr(current, item, field)]
        distance = previous.at[item, "geometry"].hausdorff_distance(current.at[item, "geometry"])
        geom_changed = distance > args.geometry_tolerance_m
        if different_tags or geom_changed:
            changed.append({
                "osm_id": item,
                "changed_tags": ",".join(different_tags),
                "geometry_changed": geom_changed,
                "hausdorff_distance_m": round(float(distance), 4),
                "old_building": attr(previous, item, "building"),
                "new_building": attr(current, item, "building"),
            })
    args.out.mkdir(parents=True, exist_ok=True)
    detail_cols = ["osm_id", "area_m2", *TAGS]
    pd.DataFrame([detail(current, item) for item in added_ids], columns=detail_cols).to_csv(
        args.out / "added_buildings.csv", sep=";", index=False, encoding="utf-8-sig")
    pd.DataFrame([detail(previous, item) for item in removed_ids], columns=detail_cols).to_csv(
        args.out / "removed_buildings.csv", sep=";", index=False, encoding="utf-8-sig")
    pd.DataFrame(changed, columns=["osm_id", "changed_tags", "geometry_changed",
        "hausdorff_distance_m", "old_building", "new_building"]).to_csv(
        args.out / "changed_buildings.csv", sep=";", index=False, encoding="utf-8-sig")
    if added_ids:
        current.loc[added_ids].reset_index(drop=True).to_crs(4326).to_file(args.out / "added_buildings.geojson", driver="GeoJSON", index=False)
    summary = {
        "previous": len(previous), "current": len(current),
        "common_ids": len(shared_ids),
        "new_ids": len(added_ids), "removed_ids": len(removed_ids),
        "changed_common_ids": len(changed),
        "unchanged_common_ids": len(shared_ids) - len(changed),
        "geometry_tolerance_m": args.geometry_tolerance_m,
        "note": "Only selected OSM tags compared. Geometry changes use Hausdorff tolerance; completeness and residential use are not established.",
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
