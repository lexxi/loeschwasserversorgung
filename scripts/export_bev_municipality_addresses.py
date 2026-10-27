#!/usr/bin/env python3
"""Export BEV INSPIRE Malta address and building reference points, preserving relations.

Reads municipality rows and referenced features from the original GeoPackage
using sqlite3; does not load the 1.66 GB national dataset into memory.
Outputs address points and building points SEPARATELY (WGS84 GeoJSON).
Does not match either point layer to OSM footprint polygons.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

from pyproj import Transformer
from shapely import wkb
from shapely.geometry import Point, mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data/raw/bev/addresses/AT-INSPIRE_AD_Address_20261001.gpkg"
OUT = ROOT / "data/processed"
EXPECTED_SRS = 3035


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def point_from_gpkg(blob):
    """Decode OGC GeoPackage standard header + WKB, without external GDAL."""
    if blob is None:
        return None
    b=bytes(blob)
    if len(b)<9 or b[:2]!=b"GP":
        raise ValueError("Not a GeoPackage binary geometry")
    version=b[2]
    flags=b[3]
    if version!=0 or flags & 0b00010000:
        raise ValueError("Unsupported or empty GeoPackage geometry")
    little=bool(flags & 1)
    srs=int.from_bytes(b[4:8],"little" if little else "big",signed=True)
    if srs!=EXPECTED_SRS:
        raise ValueError(f"GeoPackage embedded SRS {srs}, expected {EXPECTED_SRS}")
    envelope=(flags>>1)&7
    offsets={0:0,1:32,2:48,3:48,4:64}
    if envelope not in offsets:
        raise ValueError(f"Unsupported GeoPackage envelope indicator {envelope}")
    geometry=wkb.loads(b[8+offsets[envelope]:])
    if geometry.is_empty:
        return None
    if not isinstance(geometry,Point):
        raise ValueError(f"Expected Point geometry, got {geometry.geom_type}")
    return geometry


def fetch_by_keys(conn,table,key,codes,attributes):
    """Return all rows for address codes, preserving 1:n relations."""
    result=[]
    for index in range(0,len(codes),400):
        subset=codes[index:index+400]
        sql=f"SELECT {','.join(attributes)} FROM {table} WHERE {key} IN ("+",".join("?"*len(subset))+")"
        result.extend(dict(row) for row in conn.execute(sql,subset))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde",default="20619")
    p.add_argument("--input",type=Path,default=DEFAULT)
    p.add_argument("--output-dir",type=Path)
    args=p.parse_args()
    if not(args.gemeinde.isdecimal() and len(args.gemeinde)==5):
        p.error("Expected five-digit GKZ")
    source=args.input.resolve(strict=True)
    target=args.output_dir or (OUT/args.gemeinde/"bev_addresses")
    target.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect("file:"+source.as_posix()+"?mode=ro",uri=True,timeout=45)
    con.row_factory=sqlite3.Row
    try:
        key="AT.BEV.AD.GKZ."+args.gemeinde
        matching=[dict(r) for r in con.execute(
            "SELECT localId_ADRCD,inspireId_GKZ,addressIdentifierGeneral,"
            "locatorLevelValue,inspireId_SKZ,inspireId_ZO,inspireId_PLZ,inspireId_OKZ "
            "FROM AD_AddressLocatorMatchingTable WHERE inspireId_GKZ = ?",(key,))]
        if not matching:
            raise ValueError(f"No address records for {key}")
        codes=[str(m["localId_ADRCD"]) for m in matching]
        if len(codes)!=len(set(codes)):
            raise ValueError("Multiple matching-table rows for an address code; revise export instead of overwriting")
        for item in matching:
            if not item["localId_ADRCD"] or not item["addressIdentifierGeneral"]:
                raise ValueError("Missing address code or house number; check dataset")
        print(f"[INFO] {key}: {len(codes)} unique addresses",flush=True)
        addr=fetch_by_keys(con,"AD_AddressGeometry","localId_ADRCD",codes,
                           ["localId_ADRCD","geom","EPSG","RW","HW"])
        building=fetch_by_keys(con,"AD_BuildingGeometry","localId_ADRCD",codes,
                               ["localId_ADRCD","localId_ADRCD_SUBCD","buildingIdentifier",
                                "buildingNumber","geometrySpecification","geom"])
        print(f"[INFO] AddressGeometry rows: {len(addr)}, BuildingGeometry rows: {len(building)}",flush=True)
        # Exact INSPIRE reference joins; names may come from either thoroughfare
        # or address-area name, and a missing name stays explicitly blank.
        skz=list({m["inspireId_SKZ"] for m in matching if m["inspireId_SKZ"]})
        zo=list({m["inspireId_ZO"] for m in matching if m["inspireId_ZO"]})
        streets=fetch_by_keys(con,"AD_ThoroughfareName","inspireId_SKZ",skz,
                              ["inspireId_SKZ","text"]) if skz else []
        areas=fetch_by_keys(con,"AD_AddressAreaName","inspireId_ZO",zo,
                            ["inspireId_ZO","text"]) if zo else []
        def names(records,field):
            lookup=defaultdict(set)
            for r in records:
                if r["text"]:
                    lookup[str(r[field])].add(str(r["text"]).strip())
            return {key:" | ".join(sorted(value)) for key,value in lookup.items()}
        street_names=names(streets,"inspireId_SKZ")
        area_names=names(areas,"inspireId_ZO")
        src_to_wgs=Transformer.from_crs(3035,4326,always_xy=True)
        source_addresses={m["localId_ADRCD"]:m for m in matching}
        address_geometries=defaultdict(list)
        for row in addr:
            address_geometries[str(row["localId_ADRCD"])].append(row)
        building_per_address=Counter(str(r["localId_ADRCD"]) for r in building)
        address_features=[]
        table=[]
        for m in sorted(matching,key=lambda r:str(r["localId_ADRCD"])):
            ident=str(m["localId_ADRCD"])
            properties={
                "address_id":ident,"housenumber":str(m["addressIdentifierGeneral"]),
                "street":street_names.get(str(m["inspireId_SKZ"] or ""),""),
                "address_area":area_names.get(str(m["inspireId_ZO"] or ""),""),
                "locator_level":m["locatorLevelValue"] or "",
                "inspireId_SKZ":m["inspireId_SKZ"] or "",
                "inspireId_ZO":m["inspireId_ZO"] or "",
                "inspireId_PLZ":m["inspireId_PLZ"] or "",
                "building_point_count":building_per_address[ident],
            }
            items=address_geometries.get(ident,[])
            table.append({**properties,"address_geometry_count":len(items)})
            for i,row in enumerate(items,1):
                point=point_from_gpkg(row["geom"])
                if point is not None:
                    projected=transform(src_to_wgs.transform,point)
                    address_features.append({"type":"Feature","properties":{**properties,"geometry_row":i},
                                             "geometry":mapping(projected)})
        building_features=[]
        building_ids=[]
        for row in building:
            code=str(row["localId_ADRCD"])
            m=source_addresses[code]
            point=point_from_gpkg(row["geom"])
            subcode=str(row["localId_ADRCD_SUBCD"] or "")
            building_ids.append(subcode)
            if point is None:
                continue
            projected=transform(src_to_wgs.transform,point)
            props={
                "address_id":code,"building_subcode":subcode,
                "housenumber":str(m["addressIdentifierGeneral"]),
                "street":street_names.get(str(m["inspireId_SKZ"] or ""),""),
                "address_area":area_names.get(str(m["inspireId_ZO"] or ""),""),
                "building_number":str(row["buildingNumber"] or ""),
                "building_identifier":str(row["buildingIdentifier"] or ""),
                "geometry_specification":str(row["geometrySpecification"] or "")
            }
            building_features.append({"type":"Feature","properties":props,"geometry":mapping(projected)})
    finally:
        con.close()
    def write_geojson(name,features):
        path=target/name
        path.write_text(json.dumps({"type":"FeatureCollection","features":features},
                                   ensure_ascii=False)+"\n",encoding="utf-8")
        return path
    address_file=write_geojson("bev_adresspunkte.geojson",address_features)
    building_file=write_geojson("bev_gebaeudepunkte.geojson",building_features)
    table_file=target/"bev_adressen.csv"
    with table_file.open("w",newline="",encoding="utf-8-sig") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(table[0]),delimiter=";")
        writer.writeheader()
        writer.writerows(table)
    summary={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "gemeinde":args.gemeinde,
        "source_file":str(source),"source_sha256":sha256(source),
        "source_edition":"2026-10-01" if source.name.endswith("_20261001.gpkg") else "unverified_filename",
        "address_codes":len(codes),
        "address_geometry_rows":len(addr),
        "address_point_features":len(address_features),
        "building_geometry_rows":len(building),
        "building_point_features":len(building_features),
        "distinct_address_codes_with_building_rows":len(building_per_address),
        "missing_building_rows":len(codes)-len(building_per_address),
        "addresses_with_multiple_building_rows":sum(n>1 for n in building_per_address.values()),
        "distinct_building_subcodes":len(set(building_ids)),
        "address_records_without_geometry":sum(not address_geometries.get(k) for k in codes),
        "crs_original":"EPSG:3035","crs_export":"EPSG:4326",
        "purpose":"BEV official reference points only; no OSM footprint association"
    }
    summary_file=target/"bev_adressen_summary.json"
    summary_file.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for path in (address_file,building_file,table_file,summary_file):
        print(f"[OK] {path}")
    print("[INFO]",json.dumps({k:v for k,v in summary.items() if isinstance(v,int)},ensure_ascii=False))
    print("[HINWEIS] BEV-BuildingGeometry are point features; not OSM building footprints.")


if __name__=="__main__":
    main()
