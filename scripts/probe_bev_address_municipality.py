#!/usr/bin/env python3
"""Probe BEV INSPIRE address relationships for one municipality without loading the 1.6 GB GPKG.

Read-only inspection. No full address export, no OSM building matching, no guessing
whether the address point or building geometry corresponds to an OSM footprint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data/raw/bev/addresses/AT-INSPIRE_AD_Address_20261001.gpkg"


def quote(identifier):
    return '"' + identifier.replace('"','""') + '"'


def columns(conn, table):
    return {row[1] for row in conn.execute("PRAGMA table_info(" + quote(table) + ")")}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=DEFAULT)
    parser.add_argument("--gemeinde",default="20619",help="Five-digit GKZ")
    parser.add_argument("--sample",type=int,default=8)
    parser.add_argument("--check-building-links",action="store_true",
                        help="Additional aggregate scan to count building geometries linked by address code")
    args=parser.parse_args()
    if not (args.gemeinde.isdigit() and len(args.gemeinde)==5):
        parser.error("Expected five-digit GKZ")
    if not 1 <= args.sample <= 40:
        parser.error("--sample must be 1..40")
    path=args.input.resolve()
    if not path.is_file():
        parser.error(f"No file: {path}")
    con=sqlite3.connect("file:"+path.as_posix()+"?mode=ro",uri=True,timeout=45)
    con.row_factory=sqlite3.Row
    try:
        required={
            "AD_AddressLocatorMatchingTable":{"localId_ADRCD","inspireId_GKZ",
                                                "addressIdentifierGeneral","locatorLevelValue",
                                                "inspireId_SKZ","inspireId_ZO"},
            "AD_BuildingGeometry":{"localId_ADRCD","localId_ADRCD_SUBCD",
                                   "buildingIdentifier","buildingNumber","geometrySpecification"},
            "AD_AddressGeometry":{"localId_ADRCD","EPSG","RW","HW"},
            "AD_Municipality":{"localId_GKZ","text"},
        }
        for layer,fields in required.items():
            found=columns(con,layer)
            if not found:
                raise ValueError(f"Missing layer {layer}")
            missing=fields-found
            if missing:
                raise ValueError(f"Fields missing in {layer}: {sorted(missing)}")
        print("[INFO] Read-only BEV INSPIRE relational probe; no geometry coordinates exported")
        print("[INFO] GKZ:",args.gemeinde,"| file:",path)
        print("[INFO] Municipality examples:",
              json.dumps([dict(r) for r in con.execute(
                  "SELECT localId_GKZ,text FROM AD_Municipality "
                  "WHERE CAST(localId_GKZ AS TEXT) LIKE ? LIMIT 5",
                  ("%"+args.gemeinde+"%",))],ensure_ascii=False))
        print("[INFO] GKZ value examples (first rows):",
              json.dumps([r[0] for r in con.execute(
                  "SELECT inspireId_GKZ FROM AD_AddressLocatorMatchingTable LIMIT 4")],
                  ensure_ascii=False))
        # Exact INSPIRE municipality reference confirmed for Malta (20619).
        term="AT.BEV.AD.GKZ."+args.gemeinde
        sql=("SELECT localId_ADRCD,inspireId_GKZ,addressIdentifierGeneral,"
             "locatorLevelValue,inspireId_SKZ,inspireId_ZO "
             "FROM AD_AddressLocatorMatchingTable WHERE inspireId_GKZ = ?")
        rows=[dict(r) for r in con.execute(sql+" LIMIT ?",(term,args.sample))]
        print("[INFO] Address records (exact INSPIRE municipality reference):")
        print(json.dumps(rows,ensure_ascii=False,indent=2))
        if not rows:
            print("[WARN] No matching GKZ. Verify municipality reference syntax and input snapshot.")
            return
        value_sample={r["inspireId_GKZ"] for r in rows}
        if len(value_sample)>1:
            print("[WARN] More than one GKZ reference format/value present:",sorted(value_sample))
        total=con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT localId_ADRCD),"
            "SUM(CASE WHEN localId_ADRCD IS NULL THEN 1 ELSE 0 END) "
            "FROM AD_AddressLocatorMatchingTable WHERE inspireId_GKZ = ?",(term,)
        ).fetchone()
        print("[INFO] Exact municipality matching-table rows:",total[0],
              "| distinct address codes:",total[1],"| null address codes:",total[2])
        print("[HINWEIS] These are matching-table rows, not necessarily unique house numbers or buildings.")
        if args.check_building_links:
            sample_sql = (
                "SELECT bg.localId_ADRCD,bg.localId_ADRCD_SUBCD,"
                "bg.buildingIdentifier,bg.buildingNumber,bg.geometrySpecification "
                "FROM AD_BuildingGeometry bg WHERE bg.localId_ADRCD IN ("
                "SELECT DISTINCT m.localId_ADRCD FROM AD_AddressLocatorMatchingTable m "
                "WHERE m.inspireId_GKZ = ?) LIMIT ?"
            )
            examples=[dict(row) for row in con.execute(sample_sql,(term,args.sample))]
            print("[INFO] BuildingGeometry matching-code examples:")
            print(json.dumps(examples,ensure_ascii=False,indent=2))
            # Address-code relationship only: NOT a mapping to OSM footprint IDs.
            query=("SELECT COUNT(*),COUNT(DISTINCT bg.localId_ADRCD),"
                   "COUNT(DISTINCT bg.localId_ADRCD_SUBCD) "
                   "FROM AD_BuildingGeometry bg "
                   "WHERE bg.localId_ADRCD IN ("
                   "SELECT DISTINCT m.localId_ADRCD FROM AD_AddressLocatorMatchingTable m "
                   "WHERE m.inspireId_GKZ = ?)")
            r=con.execute(query,(term,)).fetchone()
            print("[INFO] BuildingGeometry rows associated with candidate address codes:",r[0],
                  "| distinct ADRCD:",r[1],"| distinct ADRCD_SUBCD:",r[2])
            print("[HINWEIS] This is a relational-key association, NOT an established OSM building join.")
    finally:
        con.close()


if __name__=="__main__":
    main()
