#!/usr/bin/env python3
"""AP3: Amtliche Adresspunkte konservativ mit OSM-Gebaeudegrundrissen verknuepfen.

Nur eindeutiger geometrischer Innen-Treffer wird als 'inside_unique' ausgegeben.
Mehrfach- und Randtreffer sowie Nachbarschaftspunkte bleiben Review-Faelle.
Keine Aussage zu Eigentum, Wohnnutzung, OIB-GK oder postalischer Gueltigkeit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
NAME_FIELDS = ("street", "strasse", "straße", "strassenname", "straßenname",
               "strname", "adr_strasse", "addr:street")
NUMBER_FIELDS = ("housenumber", "hausnummer", "hausnr", "hnr", "nummer",
                 "adr_hnr", "addr:housenumber")
CITY_FIELDS = ("city", "ort", "ortsname", "gemeinde", "addr:city")
ID_FIELDS = ("address_id", "adresse_id", "adress_id", "adr_id", "objectid", "id")


def field(frame, wanted, override):
    columns = {str(c).casefold():c for c in frame.columns if c != frame.geometry.name}
    if override:
        if override not in frame.columns:
            raise ValueError(f"Feld {override!r} nicht vorhanden; Felder: {list(frame.columns)}")
        return override
    return next((columns[k.casefold()] for k in wanted if k.casefold() in columns), None)


def clean(value):
    if value is None:
        return ""
    try:
        if math.isnan(value):
            return ""
    except (ValueError, TypeError):
        pass
    value = str(value).strip()
    return "" if value.casefold() in ("nan", "none", "null", "<na>") else value


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde", default="20619")
    p.add_argument("--addresses", type=Path, required=True,
                   help="Lokales amtliches GeoJSON/GPKG mit Punktgeometrien und EPSG-CRS")
    p.add_argument("--layer", help="Layername bei GPKG")
    p.add_argument("--street-field")
    p.add_argument("--number-field")
    p.add_argument("--city-field")
    p.add_argument("--id-field")
    p.add_argument("--near-m", type=float, default=15.0,
                   help="Pruefradius ausserhalb eines Gebaeudes; kein automatischer Match")
    p.add_argument("--inspect", action="store_true",
                   help="Spalten und CRS der Adressen zeigen, ohne Ergebnisdateien zu erzeugen")
    args = p.parse_args()
    if not (len(args.gemeinde)==5 and args.gemeinde.isdigit() and args.gemeinde.startswith("2")):
        p.error("Ungueltige Kaerntner GKZ")
    if not args.addresses.is_file():
        p.error(f"Adressdatei fehlt: {args.addresses}")
    if args.near_m < 0 or args.near_m > 100:
        p.error("--near-m muss zwischen 0 und 100 liegen")
    kwargs = {"layer":args.layer} if args.layer else {}
    addresses = gpd.read_file(args.addresses, **kwargs)
    if addresses.empty or addresses.crs is None:
        raise ValueError("Adressdatei leer oder ohne CRS; kein CRS raten")
    print(f"[INFO] Amtliche Quelle: {args.addresses} | {len(addresses)} Eintraege | CRS {addresses.crs}")
    print(f"[INFO] Felder: {', '.join(map(str,addresses.columns))}")
    if args.inspect:
        print("[INFO] Geometrietypen:",dict(Counter(addresses.geometry.geom_type)))
        return

    street_col = field(addresses, NAME_FIELDS, args.street_field)
    number_col = field(addresses, NUMBER_FIELDS, args.number_field)
    city_col = field(addresses, CITY_FIELDS, args.city_field)
    id_col = field(addresses, ID_FIELDS, args.id_field)
    if not number_col:
        raise ValueError("Kein Hausnummernfeld erkannt. Bitte --inspect und --number-field nutzen.")
    if not addresses.geometry.geom_type.eq("Point").all() or addresses.geometry.isna().any():
        raise ValueError("Adressquelle muss ausschliesslich gueltige Point-Geometrien enthalten")
    if not addresses.geometry.is_valid.all():
        raise ValueError("Ungueltige Adresspunktgeometrie")
    if not addresses[number_col].map(clean).ne("").all():
        raise ValueError(f"Leere Hausnummern im Feld {number_col}; Quelle zuerst bereinigen")
    base=ROOT/"data"/"processed"/args.gemeinde
    buildings_path=base/"osm"/"buildings.geojson"
    if not buildings_path.is_file():
        raise FileNotFoundError(buildings_path)
    buildings=gpd.read_file(buildings_path)
    if buildings.empty or buildings.crs is None or "osm_id" not in buildings:
        raise ValueError("Gebaeudedaten ungueltig")
    if buildings["osm_id"].map(clean).eq("").any() or buildings["osm_id"].astype(str).duplicated().any():
        raise ValueError("OSM-IDs fehlen oder sind nicht eindeutig")
    buildings=buildings.to_crs(epsg=31287).reset_index(drop=True)
    addresses=addresses.to_crs(epsg=31287).reset_index(drop=True)
    if not buildings.geometry.geom_type.isin(("Polygon","MultiPolygon")).all():
        raise ValueError("Gebaeudegrundrisse muessen Polygon-/MultiPolygon sein")
    if not buildings.geometry.is_valid.all():
        raise ValueError("Ungueltige Gebaeudegeometrien: bitte Import pruefen")
    index=buildings.sindex
    per_building=defaultdict(list)
    output=[]
    counters=Counter()
    for i, address in addresses.iterrows():
        geom=address.geometry
        if not isinstance(geom,Point) or geom.is_empty:
            raise ValueError(f"Kein gueltiger Adresspunkt in Zeile {i}")
        idvalue=clean(address[id_col]) if id_col else f"row_{i+1}"
        candidates=sorted(set(int(j) for j in index.query(geom,predicate="intersects")))
        interior=[j for j in candidates if buildings.geometry.iloc[j].contains(geom)]
        if len(interior)==1 and len(candidates)==1:
            status="inside_unique"
            chosen=interior[0]
            distance=0.0
        elif candidates:
            status="multiple_or_boundary"
            chosen=None
            distance=0.0
        else:
            nearby=sorted((float(buildings.geometry.iloc[j].distance(geom)),int(j))
                          for j in set(int(k) for k in index.query(geom.buffer(args.near_m),
                                                                      predicate="intersects")))
            nearby=[(d,j) for d,j in nearby if d<=args.near_m]
            status="near_review" if nearby else "unmatched"
            chosen=None
            candidates=[j for _,j in nearby]
            distance=nearby[0][0] if nearby else None
        b_id=clean(buildings.iloc[chosen]["osm_id"]) if chosen is not None else ""
        record={
            "address_id":idvalue,
            "street":clean(address[street_col]) if street_col else "",
            "housenumber":clean(address[number_col]),
            "city":clean(address[city_col]) if city_col else "",
            "status":status,
            "osm_id":b_id,
            "candidate_osm_ids":",".join(clean(buildings.iloc[j]["osm_id"]) for j in candidates),
            "distance_m":round(distance,2) if distance is not None else "",
            "source_row":i+1
        }
        if chosen is not None:
            per_building[b_id].append(record)
        counters[status]+=1
        output.append(record)

    if id_col and len(set(r["address_id"] for r in output))!=len(output):
        raise ValueError(f"IDs in Quellfeld {id_col} nicht eindeutig; Ergebnis nicht gespeichert")
    building_rows=[]
    for _,b in buildings.iterrows():
        osm_id=clean(b["osm_id"])
        assigned=per_building.get(osm_id,[])
        status=("none" if not assigned else
                "single_address" if len(assigned)==1 else "multiple_addresses")
        building_rows.append({
            "osm_id":osm_id,
            "address_count":len(assigned),
            "address_status":status,
            "official_addresses":" | ".join(
                " ".join(p for p in [a["street"],a["housenumber"]] if p)
                for a in assigned),
            "address_ids":" | ".join(a["address_id"] for a in assigned)
        })
    out=ROOT/"reports"/args.gemeinde/"addresses"
    write_csv(out/"adresspunkte_zuordnung.csv",output,list(output[0]))
    write_csv(out/"gebaeude_adressen.csv",building_rows,list(building_rows[0]))
    summary={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "municipality_id":args.gemeinde,
        "source_file":str(args.addresses),
        "address_records":len(output),
        "buildings":len(buildings),
        "address_statuses":dict(counters),
        "buildings_by_address_status":dict(Counter(r["address_status"] for r in building_rows)),
        "near_review_radius_m":args.near_m,
        "method":"Strict unique point-in-polygon matching; near points only as review candidates",
        "limitations":["Keine Ableitung der Hausnummer aus naechstem Gebaeude",
                       "Mehrere Adressen je Gebaeude bleiben einzeln erhalten",
                       "Amtliche Quelle und Stichtag muessen ausserhalb dieses Skripts dokumentiert werden",
                       "Keine GK-/Nutzungs-/Loeschwasserbedarfsklassifikation"]
    }
    (out/"adresszuordnung_summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[OK] {len(output)} Adresspunkte auf {len(buildings)} Gebaeude untersucht")
    print("[INFO] Zuordnung:",json.dumps(dict(counters),ensure_ascii=False))
    print("[INFO] Gebaeude:",json.dumps(summary["buildings_by_address_status"],ensure_ascii=False))
    for name in ("adresspunkte_zuordnung.csv","gebaeude_adressen.csv","adresszuordnung_summary.json"):
        print(f"[OK] {out/name}")
    print("[HINWEIS] Einmaliger Innen-Treffer ist geometrisch, nicht automatisch amtlich zugeordnet.")


if __name__=="__main__":
    main()
