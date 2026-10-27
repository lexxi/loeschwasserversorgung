#!/usr/bin/env python3
"""AP1/AP2: Datenvollstaendigkeit fuer GK-Eingangsmerkmale; niemals GK berechnen.

Verknuepft das lokale OSM-Merkmalsinventar optional mit BEV-Adresskandidaten
und ALS-Objekthoehen anhand technischer OSM-ID. Eine geometrische BEV-Zuordnung
ist kein amtlicher Identitaetsnachweis; ALS-Objekthoehe ist kein Fluchtniveau.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_EVIDENCE = {
    "fluchtniveau": "escape_level_m_verified",
    "oberirdische_geschosse": "above_ground_storeys_verified",
    "gesamt_bgf_oberirdisch": "total_above_ground_gross_floor_area_m2_verified",
    "nutzungseinheiten": "dwelling_business_units_verified",
    "nutzflaeche_je_einheit": "usable_area_per_unit_verified",
    "gebaeudeanordnung": "building_arrangement_verified",
    "feuerwehr_zugaenglichkeit": "fire_access_sides_verified",
    "nutzung_und_sondernutzung": "use_and_special_use_verified",
}
CSV_COLUMNS = [
    "osm_id", "building", "footprint_m2", "osm_levels_hint",
    "osm_height_hint", "osm_use_hint", "osm_units_hint",
    "bev_address_candidate_status", "bev_address_candidate_count",
    "bev_geometric_match_method", "als_object_height_m",
    "als_quality", "evidence_verified_count", "evidence_required_count",
    "missing_verified_evidence", "available_indications",
    "gk_actual", "gk_status", "next_action",
]


def load_csv(path, *, required=(), optional=False):
    if not path.is_file():
        if optional:
            return None
        raise FileNotFoundError(f"Eingabe fehlt: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
            raise ValueError(f"Fehlende CSV-Spalten in {path}: {set(required) - set(reader.fieldnames or [])}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"Leere CSV: {path}")
    return rows


def keyed(rows, label):
    by_id = {}
    for row in rows:
        oid = (row.get("osm_id") or "").strip()
        if not oid or oid in by_id:
            raise ValueError(f"{label}: leere oder doppelte osm_id {oid!r}")
        by_id[oid] = row
    return by_id


def yes(v):
    return bool(str(v or "").strip()) and str(v).strip().lower() not in ("nan", "none", "null")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde", default="20619")
    p.add_argument("--expected-count", type=int)
    p.add_argument("--out-dir", type=Path, help="Alternativer Zielordner (Standard reports/<GKZ>/gk_inventory)")
    a = p.parse_args()
    if len(a.gemeinde) != 5 or not a.gemeinde.isdigit() or not a.gemeinde.startswith("2"):
        p.error("Ungueltige Kaerntner Gemeindekennzahl")
    mid = a.gemeinde
    base = ROOT / "reports" / mid
    inventory_file = base / "gk_inventory" / "gebaeude_gk_merkmale.csv"
    bev_file = base / "addresses" / "gebaeude_adressen.csv"
    als_file = base / "gk_inventory" / "gebaeude_als_hoehen.csv"
    inventory = keyed(load_csv(inventory_file, required=["osm_id", "building", "footprint_m2"]), "OSM-Inventar")
    if a.expected_count is not None and len(inventory) != a.expected_count:
        raise ValueError(f"Erwartet {a.expected_count} Gebaeude, gefunden {len(inventory)}")
    bev_rows = load_csv(bev_file, required=["osm_id", "address_count", "match_method"], optional=True)
    als_rows = load_csv(als_file, required=["osm_id", "height_median_m", "quality"], optional=True)
    bev = keyed(bev_rows, "BEV") if bev_rows is not None else {}
    als = keyed(als_rows, "ALS") if als_rows is not None else {}
    for label, other in (("BEV", bev), ("ALS", als)):
        unknown = set(other) - set(inventory)
        if unknown:
            raise ValueError(f"{label}: {len(unknown)} OSM-IDs fehlen im Inventar; Quelldatenstand pruefen")
    counters = Counter()
    output = []
    for oid in sorted(inventory):
        source = inventory[oid]
        b = bev.get(oid)
        h = als.get(oid)
        hints = []
        def mark(name, val):
            if yes(val):
                hints.append(name)
                counters["hint_" + name] += 1

        mark("osm_levels", source.get("building:levels"))
        mark("osm_height", source.get("height"))
        mark("osm_use", source.get("building:use") or source.get("amenity") or source.get("tourism") or source.get("shop"))
        mark("osm_units", source.get("building:flats") or source.get("building:units"))
        count = int(b["address_count"]) if b else 0
        method = (b.get("match_method") or "").strip() if b else ""
        if b is None:
            bev_status = "not_loaded"
        elif count == 0:
            bev_status = "no_geometric_candidate"
        elif method == "bev_building_point_inside_unique_osm_polygon":
            bev_status = "inside_unique_geometric_candidate"
            counters["bev_inside_unique_buildings"] += 1
            hints.append("bev_geometric_address_candidate")
        else:
            bev_status = "includes_review_tolerance"
            counters["bev_tolerance_buildings"] += 1
            hints.append("bev_review_candidate")
        if h and yes(h.get("height_median_m")):
            hints.append("als_object_height")
            counters["als_height_value"] += 1
        if h and h.get("quality") == "estimated":
            counters["als_quality_estimated"] += 1
        counters["total"] += 1
        # No independently verified building-class evidence is supplied by these
        # three inputs. Therefore completeness is zero for every actual GK.
        missing = list(REQUIRED_EVIDENCE)
        output.append({
            "osm_id": oid,
            "building": source.get("building", ""),
            "footprint_m2": source.get("footprint_m2", ""),
            "osm_levels_hint": source.get("building:levels", ""),
            "osm_height_hint": source.get("height", ""),
            "osm_use_hint": source.get("building:use") or source.get("amenity") or source.get("tourism") or source.get("shop") or "",
            "osm_units_hint": source.get("building:flats") or source.get("building:units") or "",
            "bev_address_candidate_status": bev_status,
            "bev_address_candidate_count": count if b is not None else "",
            "bev_geometric_match_method": method,
            "als_object_height_m": h.get("height_median_m", "") if h else "",
            "als_quality": h.get("quality", "") if h else "",
            "evidence_verified_count": 0,
            "evidence_required_count": len(missing),
            "missing_verified_evidence": " | ".join(missing),
            "available_indications": " | ".join(hints),
            "gk_actual": "unknown",
            "gk_status": "insufficient_verified_evidence",
            "next_action": "Gemeinde/Bauakt: Fluchtniveau, Geschosse, BGF, Nutzungseinheiten, Nutzflaechen, Anordnung, Zugang und Nutzung pruefen",
        })
    dest = a.out_dir if a.out_dir else base / "gk_inventory"
    dest.mkdir(parents=True, exist_ok=True)
    result_csv = dest / "gk_datenvollstaendigkeit.csv"
    with result_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(output)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "buildings": len(output),
        "source_files": {
            "osm_inventory": str(inventory_file),
            "bev_geometric_candidates": str(bev_file) if bev_rows is not None else None,
            "als_object_heights": str(als_file) if als_rows is not None else None,
        },
        "verified_gk_assignments": 0,
        "buildings_with_complete_verified_gk_evidence": 0,
        "buildings_with_unknown_gk": len(output),
        "mandatory_evidence": REQUIRED_EVIDENCE,
        "indicator_counts": dict(sorted(counters.items())),
        "limitations": [
            "Dieses Skript importiert keine bestaetigten Bauaktmerkmale. Daher kann es keine vollstaendige GK-Evidenz feststellen.",
            "Acht aufgezaehlte Prueffelder sind ein Erhebungsraster, keine universell fuer jede GK identischen Tatbestandsvoraussetzungen.",
            "Keine GK1-GK5-Zuordnung und keine Aussagen zu moeglichen GK-Kandidaten.",
            "OSM-Kennzeichen, Fussabdruck, BEV-Geometriekandidaten und ALS-Objekthoehe sind keine gesicherten OIB-Merkmale.",
            "BEV-Punkte zu OSM sind nur geometrisch zugeordnet, Toleranzkandidaten sind ungeprueft.",
            "Fehlende optionale BEV-/ALS-CSV wird als not_loaded behandelt, nicht als Abwesenheit am Gebaeude.",
            "Keine Ermittlung von Loeschwasserbedarf oder rechtlicher Versorgungsdeckung.",
            "Private CSV/JSON-Ausgaben verbleiben unter reports/ und werden nicht ins oeffentliche Repository geladen.",
        ],
    }
    result_json = dest / "gk_datenvollstaendigkeit_summary.json"
    result_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] GK-Datenvollstaendigkeit fuer {len(output)} Gebaeude")
    print(f"[INFO] BEV: {'geladen' if bev_rows is not None else 'fehlt'}; ALS: {'geladen' if als_rows is not None else 'fehlt'}")
    print(f"[INFO] Gebaeude mit vollstaendig verifizierten GK-Merkmalen: 0 / {len(output)} (keine amtliche Merkmalsquelle eingebunden)")
    print(f"[OK] {result_csv}")
    print(f"[OK] {result_json}")
    print("[HINWEIS] Datenverfuegbarkeit ist nicht GK-Einstufbarkeit. Keine automatische GK-Zuordnung.")


if __name__ == "__main__":
    main()
