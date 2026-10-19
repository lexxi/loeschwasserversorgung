#!/usr/bin/env python3
"""OSM-Gebäude mit Flächenwidmung verknüpfen – ohne stille Priorisierung von Überlappungen."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import geopandas as gpd
import pandas as pd

FIELDS = ["OBJECTID", "KATEGORIE", "WIDMUNG", "BEZEICHNUNG", "KURZBEZEICHNUNG", "CODE", "WIDCODE", "GEMNR"]

def load_buildings(path: Path, epsg: int):
    g = gpd.read_file(path)
    if g.empty or g.crs is None:
        raise ValueError(f"Gebäude fehlen oder haben kein CRS: {path}")
    if "osm_id" not in g:
        if "@id" not in g:
            raise ValueError("osm_id bzw. @id fehlt")
        g["osm_id"] = g["@id"].astype(str)
    if g["osm_id"].isna().any() or g["osm_id"].duplicated().any():
        raise ValueError("OSM-IDs fehlen oder sind doppelt")
    if g.geometry.isna().any() or g.geometry.is_empty.any() or not g.geometry.is_valid.all():
        raise ValueError("Gebäudegeometrie fehlt, ist leer oder ungültig")
    if not g.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Gebäude enthalten Nicht-Polygon-Geometrien")
    return g.to_crs(epsg=epsg).reset_index(drop=True)

def load_zoning(path: Path, epsg: int):
    g = gpd.read_file(path)
    if g.empty or g.crs is None:
        raise ValueError(f"Widmungen fehlen oder haben kein CRS: {path}")
    if not {"KATEGORIE", "WIDMUNG"}.issubset(g.columns):
        raise ValueError("Widmung enthält nicht KATEGORIE und WIDMUNG")
    if g.geometry.isna().any() or g.geometry.is_empty.any() or not g.geometry.is_valid.all():
        raise ValueError("Widmungsgeometrie fehlt, ist leer oder ungültig")
    if not g.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Widmung enthält Nicht-Polygon-Geometrien")
    return g.to_crs(epsg=epsg).reset_index(drop=True)

def value(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v)

def join(buildings, zoning):
    # Phase 1: existing representative-point assignment, with no zone priority.
    points = gpd.GeoDataFrame({"building_idx": range(len(buildings))},
                              geometry=buildings.geometry.representative_point(), crs=buildings.crs)
    z = zoning[[c for c in FIELDS if c in zoning.columns] + [zoning.geometry.name]].copy()
    z["zone_idx"] = range(len(zoning))
    hits = gpd.sjoin(points, z, how="left", predicate="within")
    matches, candidates = {}, []
    for _, row in hits.iterrows():
        i = int(row["building_idx"])
        if pd.isna(row["zone_idx"]):
            continue
        j = int(row["zone_idx"])
        matches.setdefault(i, set()).add(j)
        record = {"osm_id": str(buildings.iloc[i]["osm_id"]), "building_idx": i, "zone_idx": j}
        record.update({field: value(zoning.iloc[j][field]) if field in zoning else None for field in FIELDS})
        candidates.append(record)

    # Phase 2: inspect actual footprint intersections (only positive-area overlaps).
    # A footprint overlap is never an automatic legal designation.
    spatial = zoning.sindex
    overlap_rows, overlaps_by_building = [], {}
    for i, footprint in enumerate(buildings.geometry):
        footprint_area = float(footprint.area)
        if footprint_area <= 0:
            raise ValueError(f"Gebaeude ohne Flaeche: {buildings.iloc[i]['osm_id']}")
        zone_ids = []
        for j in spatial.query(footprint, predicate="intersects"):
            j = int(j)
            intersection_area = float(footprint.intersection(zoning.geometry.iloc[j]).area)
            if intersection_area <= 0:
                continue
            zone_ids.append(j)
            record = {
                "osm_id": str(buildings.iloc[i]["osm_id"]),
                "building_idx": i,
                "zone_idx": j,
                "building_area_m2": round(footprint_area, 4),
                "overlap_m2": round(intersection_area, 4),
                "overlap_pct": round(intersection_area / footprint_area * 100, 4),
                "point_match": j in matches.get(i, set()),
            }
            record.update({field: value(zoning.iloc[j][field]) if field in zoning else None for field in FIELDS})
            overlap_rows.append(record)
        overlaps_by_building[i] = zone_ids

    out = buildings.copy()
    selected, statuses, counts, overlap_counts = [], [], [], []
    for i in range(len(out)):
        ids = sorted(matches.get(i, set()))
        area_ids = overlaps_by_building[i]
        counts.append(len(ids))
        overlap_counts.append(len(area_ids))
        if len(ids) == 1:
            statuses.append("unique")
            selected.append(ids[0])
        elif len(ids) > 1:
            statuses.append("multiple_review")
            selected.append(None)
        elif area_ids:
            statuses.append("overlap_review")
            selected.append(None)
        else:
            statuses.append("unassigned")
            selected.append(None)
    out["zoning_status"] = statuses
    out["zoning_match_count"] = counts
    out["zoning_footprint_overlap_count"] = overlap_counts
    out["zoning_boundary_review"] = [
        (len(overlaps_by_building[i]) > 1 or
         (len(matches.get(i, set())) == 1 and set(overlaps_by_building[i]) != matches[i]))
        for i in range(len(out))
    ]
    for field in FIELDS:
        out["zone_" + field.lower()] = [
            value(zoning.iloc[j][field]) if j is not None and field in zoning else None
            for j in selected
        ]
    candidate_columns = ["osm_id", "building_idx", "zone_idx", *FIELDS]
    overlap_columns = [
        "osm_id", "building_idx", "zone_idx", "building_area_m2",
        "overlap_m2", "overlap_pct", "point_match", *FIELDS
    ]
    return (out, pd.DataFrame(candidates, columns=candidate_columns),
            pd.DataFrame(overlap_rows, columns=overlap_columns))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--buildings", type=Path, default=Path("data/processed/current/osm/buildings_malta.geojson"))
    p.add_argument("--zoning", type=Path, default=Path("data/processed/current/malta_zoning.geojson"))
    p.add_argument("--out", type=Path, default=Path("data/processed/current/building_zoning"))
    p.add_argument("--epsg", type=int, default=31287)
    args = p.parse_args()
    buildings = load_buildings(args.buildings, args.epsg)
    zoning = load_zoning(args.zoning, args.epsg)
    result, candidates, overlaps = join(buildings, zoning)
    args.out.mkdir(parents=True, exist_ok=True)
    result.to_crs(4326).to_file(args.out / "buildings_with_zoning.geojson", driver="GeoJSON", index=False)
    candidates.to_csv(args.out / "zoning_candidates.csv", sep=";", index=False, encoding="utf-8-sig")
    overlaps.to_csv(args.out / "zoning_footprint_overlaps.csv", sep=";", index=False, encoding="utf-8-sig")
    result.loc[result["zoning_status"] != "unique", ["osm_id", "zoning_status", "zoning_match_count", "zoning_footprint_overlap_count", "zoning_boundary_review"]].to_csv(
        args.out / "zoning_review.csv", sep=";", index=False, encoding="utf-8-sig"
    )
    counts = result["zoning_status"].value_counts().to_dict()
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "buildings_input": len(buildings), "zoning_input": len(zoning), "buildings_output": len(result),
        "unique": counts.get("unique", 0), "unassigned": counts.get("unassigned", 0),
        "multiple_review": counts.get("multiple_review", 0),
        "overlap_review": counts.get("overlap_review", 0),
        "boundary_review": int(result["zoning_boundary_review"].sum()),
        "footprint_overlap_pairs": len(overlaps), "candidate_matches": len(candidates),
        "rule": "representative_point within; positive-area building footprint intersections for review; no automatic priority",
        "warning": "Einzelpunkt- und Flaechenzuordnungen sind keine Feststellung der Rechtswirksamkeit. Ueberlappende Widmungen und Grenzfaelle sind zu pruefen."
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
