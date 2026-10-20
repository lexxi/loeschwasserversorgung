#!/usr/bin/env python3
"""Vergleicht lokale OSM- und ODB-Wasserentnahmestellen räumlich.

Schreibt nur lokale Vergleichsdaten. Nähe ist ein Prüfhinweis und niemals
ein automatischer Nachweis, dass zwei Objekte dieselbe Einrichtung sind.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
METRIC_CRS = "EPSG:31287"
OSM_GROUPS = {
    "Hydrant": "hydrant",
    "Saugstelle": "suction",
    "Löschwasserteich": "pond",
    "Löschwasserbehälter": "tank",
}
ODB_GROUPS = {
    "Überflurhydrant": "hydrant",
    "Unterflurhydrant": "hydrant",
    "Saugstelle": "suction",
    "Bach mit Stau": "natural_water",
    "Löschwasserteich": "pond",
}
COLUMNS = (
    "osm_id", "osm_type", "osm_position_method",
    "nearest_odb_id", "nearest_odb_type", "nearest_odb_status",
    "distance_m", "type_relation", "review_priority",
    "nearest_compatible_odb_id", "nearest_compatible_odb_type",
    "nearest_compatible_distance_m",
)


def load_points(path, id_field, type_field):
    if not path.is_file():
        raise FileNotFoundError(f"Datenbestand fehlt: {path}")
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"Kein CRS angegeben: {path}")
    if not {id_field, type_field}.issubset(gdf.columns):
        raise ValueError(f"ID/Typ-Felder fehlen in {path}")
    if not gdf.empty and (gdf.geometry.isna().any()
                           or not gdf.geometry.geom_type.eq("Point").all()):
        raise ValueError(f"Erwartet ausschließlich Point-Geometrien: {path}")
    if gdf[id_field].isna().any() or gdf[id_field].astype(str).duplicated().any():
        raise ValueError(f"Fehlende/doppelte Objekt-ID: {path}")
    return gdf.to_crs(METRIC_CRS)


def nearest(point, candidates):
    if candidates.empty:
        return None, None
    distances = candidates.geometry.distance(point)
    idx = distances.idxmin()
    return candidates.loc[idx], float(distances.loc[idx])


def relation(osm_type, odb_type):
    og = OSM_GROUPS.get(str(osm_type))
    dg = ODB_GROUPS.get(str(odb_type))
    if og is None or dg is None:
        return "unbekannt"
    if og == dg:
        return "typ_kompatibel"
    if {og, dg} == {"suction", "natural_water"}:
        return "fachlich_pruefen"  # Saugstelle kann zu Bach gehören.
    return "typ_abweichend"


def priority(meters, type_relation):
    if meters is None:
        return "kein_odb_objekt"
    if meters <= 10:
        return "nah_0_10m_pruefen"
    if meters <= 30:
        return "nah_10_30m_pruefen"
    if meters <= 100:
        return "umfeld_30_100m_pruefen"
    return "weiter_als_100m"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="GKZ, z. B. 20619")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("Ungültige Kärntner Gemeinde-GKZ")

    base = ROOT / "data" / "processed" / mid
    osm = load_points(base / "water_sources" / "water_sources.geojson", "osm_id", "type")
    odb = load_points(base / "odb_water_sources" / "odb_water_sources.geojson", "odb_id", "type")

    records = []
    for _, item in osm.iterrows():
        osm_type = str(item["type"])
        closest, dist = nearest(item.geometry, odb)
        matching_group = OSM_GROUPS.get(osm_type)
        compatible = odb.loc[odb["type"].map(ODB_GROUPS) == matching_group] if matching_group else odb.iloc[:0]
        closest_comp, dist_comp = nearest(item.geometry, compatible)
        row = {
            "osm_id": str(item["osm_id"]),
            "osm_type": osm_type,
            "osm_position_method": str(item.get("position_method", "")),
            "nearest_odb_id": str(closest["odb_id"]) if closest is not None else "",
            "nearest_odb_type": str(closest["type"]) if closest is not None else "",
            "nearest_odb_status": str(closest.get("status_label", closest.get("status_raw", ""))) if closest is not None else "",
            "distance_m": round(dist, 1) if dist is not None else "",
            "type_relation": relation(osm_type, closest["type"]) if closest is not None else "",
            "review_priority": priority(dist, relation(osm_type, closest["type"]) if closest is not None else ""),
            "nearest_compatible_odb_id": str(closest_comp["odb_id"]) if closest_comp is not None else "",
            "nearest_compatible_odb_type": str(closest_comp["type"]) if closest_comp is not None else "",
            "nearest_compatible_distance_m": round(dist_comp, 1) if dist_comp is not None else "",
        }
        records.append(row)
    records.sort(key=lambda row: row["osm_id"])

    out = base / "water_sources_comparison"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "osm_odb_nearest.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(records)

    counts_priority = dict(sorted(Counter(row["review_priority"] for row in records).items()))
    counts_relation = dict(sorted(Counter(row["type_relation"] for row in records).items()))
    close_compatible = [r for r in records
                        if isinstance(r["nearest_compatible_distance_m"], (float, int))
                        and r["nearest_compatible_distance_m"] <= 30]
    data = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "osm_count": len(osm),
        "odb_count": len(odb),
        "sum_before_duplicate_review": len(osm) + len(odb),
        "osm_count_by_type": dict(sorted(Counter(osm["type"]).items())),
        "odb_count_by_type": dict(sorted(Counter(odb["type"]).items())),
        "review_priority": counts_priority,
        "nearest_type_relation": counts_relation,
        "osm_with_compatible_odb_within_30m": len(close_compatible),
        "unverified_potential_matches_only": True,
        "notes": [
            "Alle Entfernungen sind geradlinige Näherungen im metrischen EPSG:31287.",
            "Ein ODB-Objekt darf mehreren OSM-Einträgen am nächsten liegen; keine 1:1-Zuordnung.",
            "Hydrant (OSM) ist mit Ober-/Unterflurhydrant (ODB) kompatibel; Untertyp unbekannt.",
            "Bach mit Stau und Saugstelle werden nur als fachlich zu prüfen bewertet.",
            "Linien-/Flächenobjekte in OSM haben einen repräsentativen Punkt statt realer Entnahmeposition.",
            "Ein Treffer unter 10m/30m ist nur ein Prüfhinweis, keine bestätigte Dublette.",
            "ODB-Status wird nicht auf OSM-Quellen übertragen.",
            "Keine zusätzlichen Quellen oder bereinigten Gesamtzahlen ohne manuelle Prüfung behaupten.",
        ],
    }
    json_path = out / "comparison_summary.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Gemeinde {mid}: OSM {len(osm)}, ODB {len(odb)}")
    print("OSM-Typen:", json.dumps(data["osm_count_by_type"], ensure_ascii=False))
    print("ODB-Typen:", json.dumps(data["odb_count_by_type"], ensure_ascii=False))
    print("\nNächster ODB-Nachbar je OSM-Eintrag (unbestätigte Kandidaten):")
    for row in records:
        d = f'{row["distance_m"]} m' if row["distance_m"] != "" else "—"
        dc = f'{row["nearest_compatible_distance_m"]} m' if row["nearest_compatible_distance_m"] != "" else "—"
        print(f'  {row["osm_id"]} ({row["osm_type"]}): {d} -> '
              f'{row["nearest_odb_type"]} [{row["type_relation"]}]; '
              f'passender Typ: {dc}')
    print(f"Potenzielle typkompatible Kandidaten bis 30m: {len(close_compatible)} / {len(osm)}")
    print(f"[OK] {csv_path}")
    print(f"[OK] {json_path}")


if __name__ == "__main__":
    main()
