#!/usr/bin/env python3
"""AP2: GK-Merkmalsinventur ohne automatische Klassifikation oder Bedarfszuordnung."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIELDS = (
    "building", "building:use", "building:levels", "height",
    "roof:height", "roof:levels", "building:flats", "building:units",
    "amenity", "tourism", "shop", "building:part",
)
CRITICAL = (
    "above_ground_storeys_verified", "escape_level_m",
    "total_above_ground_gross_floor_area_m2", "dwelling_business_units_verified",
    "detached_verified", "fire_access_sides_verified", "special_use_verified",
)
COLUMNS = (
    "osm_id", "building", "footprint_m2",
    *FIELDS[1:], "has_address", "present_osm_indicators",
    "missing_required_gk_evidence", "gk_actual", "gk_status",
)


def safe_value(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", default="20619")
    parser.add_argument("--expected-count", type=int, help="Abbruch bei abweichender Gebaeudeanzahl")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("Ungueltige Kaerntner Gemeindekennzahl")
    path = ROOT / "data" / "processed" / mid / "osm" / "buildings.geojson"
    if not path.is_file():
        parser.error(f"Gebaeude fehlen: {path}")
    frame = gpd.read_file(path)
    if frame.empty or frame.crs is None or "osm_id" not in frame or "building" not in frame:
        raise ValueError("Gebaeudedaten fehlen oder sind unvollstaendig")
    ids = frame["osm_id"].map(safe_value)
    if ids.eq("").any() or ids.duplicated().any():
        raise ValueError("Leere oder doppelte OSM-ID")
    if args.expected_count is not None and len(frame) != args.expected_count:
        raise ValueError(f"Erwartet {args.expected_count}, gefunden {len(frame)} – bitte Import vergleichen")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Ungueltige Geometrien")
    projected = frame.to_crs(31287)
    out_dir = ROOT / "reports" / mid / "gk_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)
    counters = Counter()
    building_tags = Counter()
    output_rows = []
    for index, building in frame.iterrows():
        info = {field: safe_value(building[field]) if field in frame.columns else "" for field in FIELDS}
        for field, value in info.items():
            if value:
                counters[field] += 1
        building_tags[info["building"] or "(leer)"] += 1
        row = {
            "osm_id": safe_value(building["osm_id"]),
            "building": info["building"],
            "footprint_m2": round(float(projected.loc[index].geometry.area), 1),
        }
        row.update({key: info[key] for key in FIELDS[1:]})
        row["has_address"] = bool(
            ("addr:housenumber" in frame and safe_value(building["addr:housenumber"]))
        )
        row["present_osm_indicators"] = ",".join(k for k, v in info.items() if v)
        row["missing_required_gk_evidence"] = ",".join(CRITICAL)
        row["gk_actual"] = "unknown"
        row["gk_status"] = "unassessed"
        output_rows.append(row)
    output_rows.sort(key=lambda r: r["osm_id"])
    csv_path = out_dir / "gebaeude_gk_merkmale.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(output_rows)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "buildings": len(frame),
        "source_file": str(path),
        "availability_counts": dict(sorted(counters.items())),
        "building_tag_counts": dict(sorted(building_tags.items())),
        "gk_actual_assigned": 0,
        "gk_unknown": len(frame),
        "required_independent_evidence": list(CRITICAL),
        "limitations": [
            "Nur OSM-Rohmerkmale und berechnete Grundrissflaeche; keine GK-Zuordnung.",
            "Footprint ist nicht gesamte oberirdische BGF.",
            "OSM building:levels und height sind keine gesicherten Geschoss-/Fluchtniveaudaten.",
            "Keine Beurteilung der erreichbaren Loeschwasserleistung.",
            "Belegbare Merkmale fuer Sondernutzungen, Einheiten, Zugang und Planungsrecht fehlen.",
        ],
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] GK-Merkmalsinventur: {len(frame)} Gebaeude, GK unbekannt: {len(frame)}")
    for field in FIELDS:
        print(f"[INFO] {field}: {counters[field]} / {len(frame)}")
    print(f"[OK] {csv_path}")
    print(f"[OK] {summary_path}")
    print("[HINWEIS] Keine automatische GK- oder Loeschwasserbedarfszuordnung.")


if __name__ == "__main__":
    main()
