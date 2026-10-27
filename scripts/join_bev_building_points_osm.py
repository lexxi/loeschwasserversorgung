#!/usr/bin/env python3
"""AP3: BEV building reference points vs OSM building footprints (offline).

Only a unique BEV building POINT strictly inside one OSM polygon is assigned.
Boundary/overlap and nearby matches are review candidates, never assignments.
Keeps address code + building subcode and aggregates multiple BEV entries per OSM
building without treating a building point as an OSM footprint identity proof.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parent.parent


def text(value):
    if value is None:
        return ""
    value=str(value).strip()
    return "" if value.casefold() in ("nan","none","<na>","null") else value


def write_csv(path,rows,columns):
    with path.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde",default="20619")
    p.add_argument("--near-m",type=float,default=15.0,
                   help="Review search radius in meters for points outside OSM buildings (default 15)")
    p.add_argument("--overwrite",action="store_true",
                   help="Explicitly replace existing local address-link reports")
    args=p.parse_args()
    if not(args.gemeinde.isdecimal() and len(args.gemeinde)==5):
        p.error("Expected five-digit GKZ")
    if not 0<=args.near_m<=100:
        p.error("--near-m must be 0..100")
    base=ROOT/"data"/"processed"/args.gemeinde
    bev_path=base/"bev_addresses"/"bev_gebaeudepunkte.geojson"
    osm_path=base/"osm"/"buildings.geojson"
    bev_summary=base/"bev_addresses"/"bev_adressen_summary.json"
    for path in (bev_path,osm_path,bev_summary):
        if not path.is_file():
            p.error(f"Missing input: {path}")
    out=ROOT/"reports"/args.gemeinde/"addresses"
    outputs=[out/"bev_gebaeudepunkte_osm_zuordnung.csv",
             out/"gebaeude_adressen.csv",
             out/"bev_osm_zuordnung_summary.json"]
    if any(x.exists() for x in outputs) and not args.overwrite:
        p.error("Existing matching reports. Review them first; use --overwrite to replace explicitly.")
    bev=gpd.read_file(bev_path)
    osm=gpd.read_file(osm_path)
    if bev.empty or osm.empty or bev.crs is None or osm.crs is None:
        raise ValueError("Missing data or CRS")
    required={"address_id","building_subcode","housenumber","street"}
    if not required.issubset(bev.columns):
        raise ValueError(f"BEV input missing attributes {sorted(required-set(bev.columns))}")
    if "osm_id" not in osm.columns:
        raise ValueError("OSM input missing osm_id")
    osm=osm.to_crs(31287).reset_index(drop=True)
    bev=bev.to_crs(31287).reset_index(drop=True)
    if not bev.geometry.geom_type.eq("Point").all() or bev.geometry.isna().any() or bev.geometry.is_empty.any():
        raise ValueError("BEV geometry must contain only nonempty points")
    if not osm.geometry.geom_type.isin(["Polygon","MultiPolygon"]).all() or osm.geometry.isna().any():
        raise ValueError("OSM building geometry must contain only polygons")
    if not osm.geometry.is_valid.all() or not bev.geometry.is_valid.all():
        raise ValueError("Invalid geometry: inspect source before matching")
    osm_ids=[text(v) for v in osm["osm_id"]]
    if any(not v for v in osm_ids) or len(set(osm_ids))!=len(osm_ids):
        raise ValueError("Missing/duplicate OSM IDs")
    subcodes=[text(v) for v in bev["building_subcode"]]
    if any(not v for v in subcodes) or len(set(subcodes))!=len(subcodes):
        raise ValueError("Missing/duplicate BEV building subcodes")
    src=json.loads(bev_summary.read_text(encoding="utf-8"))
    if src.get("gemeinde")!=args.gemeinde or src.get("building_point_features")!=len(bev):
        raise ValueError("BEV summary does not match source dataset")
    idx=osm.sindex
    results=[]
    per_osm=defaultdict(list)
    counts=Counter()
    for i,feature in bev.iterrows():
        point=feature.geometry
        intersections=sorted({int(j) for j in idx.query(point,predicate="intersects")})
        inner=[j for j in intersections if osm.geometry.iloc[j].contains(point)]
        if len(inner)==1 and len(intersections)==1:
            chosen=inner[0]
            status="inside_unique"
            candidates=intersections
            distance=0.0
        elif intersections:
            chosen=None
            status="multiple_or_boundary"
            candidates=intersections
            distance=0.0
        else:
            indices=idx.query(point.buffer(args.near_m),predicate="intersects") if args.near_m else []
            near=sorted((float(osm.geometry.iloc[int(j)].distance(point)),int(j)) for j in set(indices))
            near=[(d,j) for d,j in near if d<=args.near_m]
            chosen=None
            status="near_review" if near else "unmatched"
            candidates=[j for d,j in near]
            distance=near[0][0] if near else None
        oid=osm_ids[chosen] if chosen is not None else ""
        row={
            "building_subcode":text(feature["building_subcode"]),
            "address_id":text(feature["address_id"]),
            "housenumber":text(feature["housenumber"]),
            "street":text(feature["street"]),
            "address_area":text(feature.get("address_area")),
            "building_number":text(feature.get("building_number")),
            "building_identifier":text(feature.get("building_identifier")),
            "status":status,
            "osm_id":oid,
            "candidate_osm_ids":" | ".join(osm_ids[j] for j in candidates),
            "distance_to_candidate_m":round(distance,2) if distance is not None else "",
        }
        results.append(row)
        counts[status]+=1
        if chosen is not None:
            per_osm[oid].append(row)
    building_rows=[]
    for oid in osm_ids:
        matches=per_osm[oid]
        address_codes=sorted({r["address_id"] for r in matches})
        named={}
        for r in matches:
            named[r["address_id"]]=" ".join(v for v in (r["street"] or r["address_area"],
                                                   r["housenumber"]) if v).strip()
        building_rows.append({
            "osm_id":oid,
            "address_count":len(address_codes),
            "bev_point_count":len(matches),
            "address_status":"none" if not matches else
                              "single_address" if len(address_codes)==1 else "multiple_addresses",
            "official_addresses":" | ".join(named[c] for c in sorted(named)),
            "address_ids":" | ".join(address_codes),
            "building_subcodes":" | ".join(sorted(r["building_subcode"] for r in matches)),
            "match_method":"bev_building_point_inside_unique_osm_polygon" if matches else "",
        })
    summary={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "gemeinde":args.gemeinde,
        "bev_source_file":str(bev_path),
        "bev_original_source_sha256":src.get("source_sha256"),
        "osm_source_file":str(osm_path),
        "bev_building_points":len(bev),
        "osm_buildings":len(osm),
        "status_counts":dict(counts),
        "assigned_osm_buildings":sum(bool(per_osm[oid]) for oid in osm_ids),
        "buildings_with_multiple_address_codes":sum(r["address_count"]>1 for r in building_rows),
        "assigned_distinct_address_codes":len({r["address_id"] for r in results if r["osm_id"]}),
        "near_review_radius_m":args.near_m,
        "method":"BEV building reference Point inside exactly one OSM footprint: geometrically unambiguous only",
        "caveats":[
            "No official BEV-to-OSM identity mapping; geometry-only candidate association.",
            "BEV address access point is NOT the geometry used for this join.",
            "Nearby/overlapping/boundary points never assigned.",
            "Buildings without a BEV address point are not necessarily unused.",
            "No automatic OIB building class or fire-water needs derived."
        ],
    }
    out.mkdir(parents=True,exist_ok=True)
    write_csv(outputs[0],results,list(results[0]))
    write_csv(outputs[1],building_rows,list(building_rows[0]))
    outputs[2].write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[OK] BEV-Gebaeudepunkte: {len(bev)} | OSM-Gebaeude: {len(osm)}")
    print("[INFO] Geometrische Zuordnung:",json.dumps(dict(counts),ensure_ascii=False))
    print("[INFO] OSM-Gebaeude mit BEV-Innen-Treffer:",summary["assigned_osm_buildings"])
    print("[INFO] Eindeutige BEV-Adresscodes in Zuordnungen:",summary["assigned_distinct_address_codes"])
    for path in outputs:
        print(f"[OK] {path}")
    print("[HINWEIS] Eindeutiger Innen-Treffer ist geometrisch, keine amtlich bestaetigte OSM-Identitaet.")


if __name__=="__main__":
    main()
