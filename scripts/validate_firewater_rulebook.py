#!/usr/bin/env python3
"""Prueft ausschliesslich Struktur/Konsistenz des AP1-Regelwerks.

Keine automatische GK-Einstufung und kein normativer Versorgungsnachweis.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "config" / "firewater_rulebook.json"


def validate(data):
    errors = []
    if data.get("schema_version") != 1:
        errors.append("schema_version muss 1 sein")
    if data.get("status") != "draft_review_required":
        errors.append("Regelwerk muss bis zur fachlichen Freigabe draft_review_required bleiben")
    if data.get("auto_assignment_enabled") is not False:
        errors.append("Automatische Zuordnung darf nicht aktiviert sein")
    refs = data.get("source_refs")
    if not isinstance(refs, dict) or not refs:
        errors.append("source_refs fehlen")
        refs = {}
    classes = data.get("building_classes", [])
    if not isinstance(classes, list) or {x.get("id") for x in classes if isinstance(x, dict)} != {"GK1", "GK2", "GK3", "GK4", "GK5"}:
        errors.append("GK1 bis GK5 muessen jeweils genau einmal vorkommen")
    for item in classes:
        if not isinstance(item, dict):
            errors.append("Ungueltiger GK-Eintrag")
            continue
        if item.get("conditions_complete") is not False or item.get("variant_review_required") is not True:
            errors.append(f"{item.get('id')}: unvollstaendige Regeln duerfen nicht freigegeben sein")
        if item.get("reference") not in refs:
            errors.append(f"{item.get('id')}: unbekannte Quelle")
    levels = data.get("water_demand_levels", [])
    if not isinstance(levels, list) or len(levels) != 6:
        errors.append("Es werden sechs dokumentierte Orientierungsniveaus erwartet")
        levels = []
    seen = set()
    for item in levels:
        if not isinstance(item, dict):
            errors.append("Ungueltige Bedarfsstufe")
            continue
        rid = item.get("id")
        if not rid or rid in seen:
            errors.append(f"Leere oder doppelte Regel-ID: {rid}")
        seen.add(rid)
        rate, minutes, volume = item.get("rate_l_min"), item.get("duration_min"), item.get("volume_m3")
        if (not isinstance(rate, int) or rate <= 0 or
                not isinstance(minutes, int) or minutes <= 0 or
                not isinstance(volume, (int, float)) or volume != rate * minutes / 1000):
            errors.append(f"{rid}: l/min, Dauer und Volumen sind inkonsistent")
        if item.get("conditions_complete") is not False or item.get("scope") != "ground_protection":
            errors.append(f"{rid}: nur ungepruefte Grundschutz-Orientierungswerte zugelassen")
        if item.get("source") not in refs:
            errors.append(f"{rid}: Quellenverweis ungueltig")
    distance = data.get("distance_reference", {})
    if distance.get("partial_flow_conditions_encoded") is not False:
        errors.append("Entfernungs-/Teilratenregeln sind noch nicht implementiert")
    special = data.get("object_protection", {})
    if special.get("status") != "not_encoded":
        errors.append("Objektschutz ist noch nicht codiert")
    safe = data.get("safety_rules", {})
    for key in ("never_derive_gk_from_osm_tag", "never_assign_level_from_gk_alone",
                "planning_gk_separate_from_actual_gk", "requires_full_conditions_and_professional_review"):
        if safe.get(key) is not True:
            errors.append(f"Schutzregel fehlt: {key}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT)
    args = parser.parse_args()
    data = json.loads(args.file.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print("[FEHLER]", error)
        raise SystemExit(1)
    print(f"[OK] AP1-Regelwerk {data['rulebook_version']}: {len(data['building_classes'])} GK-Definitionseintraege, "
          f"{len(data['water_demand_levels'])} Grundschutz-Orientierungsniveaus")
    print("[HINWEIS] Nur formale Validierung. Keine GK-Klassifikation oder Bedarfszuordnung freigegeben.")


if __name__ == "__main__":
    main()
