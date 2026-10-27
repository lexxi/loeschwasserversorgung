#!/usr/bin/env python3
"""Export offene BEV/OSM-Zuordnungen als CSV zur fachlichen Weitergabe.

Standardmaessig nur near_review und unmatched (ohne 2-m-Toleranzfaelle).
Keine Aenderung an BEV-/OSM-Daten und kein automatischer Versand.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OPEN={"near_review","unmatched","multiple_or_boundary"}
OPTIONAL={"boundary_tolerance"}
COLUMNS=[
    "fall_id","gemeinde","bev_subcode","bev_adresscode",
    "strasse","ortsteil","hausnummer","bev_gebaeudenummer","bev_gebaeudebezeichnung",
    "pruefstatus","osm_kandidaten","abstand_naechster_kandidat_m",
    "frage_an_gemeinde","pruefer","pruefdatum","rueckmeldung","entscheidung","nachweis"
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde",default="20619")
    p.add_argument("--include-tolerance",action="store_true",
                   help="Vorlaeufige 2-m-Toleranzfaelle ebenfalls zur Rueckfrage aufnehmen")
    p.add_argument("--overwrite",action="store_true",
                   help="Vorhandene weiterzugebende CSV-Datei ausdruecklich ersetzen")
    args=p.parse_args()
    if not(len(args.gemeinde)==5 and args.gemeinde.isdecimal()):
        p.error("Ungueltige Gemeindenummer")
    directory=ROOT/"reports"/args.gemeinde/"addresses"
    source=directory/"bev_gebaeudepunkte_osm_zuordnung.csv"
    summary=directory/"bev_osm_zuordnung_summary.json"
    if not source.is_file() or not summary.is_file():
        p.error("Zuordnungsdateien fehlen; zuerst join_bev_building_points_osm.py ausfuehren.")
    target=directory/"gemeinde_rueckfragen_bev_osm.csv"
    if target.exists() and not args.overwrite:
        p.error("Rueckfrageliste existiert bereits und kann Antworten enthalten. "
                "Nur nach Sicherung mit --overwrite neu erstellen.")
    metadata=json.loads(summary.read_text(encoding="utf-8"))
    if metadata.get("gemeinde")!=args.gemeinde:
        raise ValueError("Gemeindezuordnung in Summary stimmt nicht")
    with source.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f,delimiter=";"))
    if len(rows)!=metadata.get("bev_building_points"):
        raise ValueError("CSV-/Summary-Zahlen inkonsistent")
    allowed=OPEN|(OPTIONAL if args.include_tolerance else set())
    selected=[r for r in rows if r["status"] in allowed]
    counts=Counter(r["status"] for r in rows)
    if dict(counts)!=metadata.get("status_counts"):
        raise ValueError("Statusverteilung entspricht nicht der aktuellen Summary")
    if len({r["building_subcode"] for r in selected})!=len(selected):
        raise ValueError("Doppelte BEV-Subcodes in Rueckfragen")
    questions={
        "near_review":"Bitte Zuordnung des BEV-Gebaeudepunkts zu einem konkreten Gebaeude bzw. abweichende Geometrie pruefen.",
        "unmatched":"Bitte bestaetigen, ob das Gebaeude existiert und der amtliche Gebaeudepunkt korrekt liegt.",
        "multiple_or_boundary":"Bitte bei Polygon-Grenzlage bzw. mehreren Kandidaten die Gebaeudezuordnung klaeren.",
        "boundary_tolerance":"Bitte vorlaeufige Zuordnung innerhalb der projektinternen 2-m-Toleranz plausibilisieren."
    }
    output=[]
    for r in sorted(selected,key=lambda r:(r["status"],r["building_subcode"])):
        output.append({
            "fall_id":args.gemeinde+"-"+r["building_subcode"],
            "gemeinde":args.gemeinde,
            "bev_subcode":r["building_subcode"],
            "bev_adresscode":r["address_id"],
            "strasse":r["street"],
            "ortsteil":r.get("address_area",""),
            "hausnummer":r["housenumber"],
            "bev_gebaeudenummer":r.get("building_number",""),
            "bev_gebaeudebezeichnung":r.get("building_identifier",""),
            "pruefstatus":r["status"],
            "osm_kandidaten":r.get("candidate_osm_ids",""),
            "abstand_naechster_kandidat_m":r.get("distance_to_candidate_m",""),
            "frage_an_gemeinde":questions[r["status"]],
            "pruefer":"","pruefdatum":"","rueckmeldung":"","entscheidung":"","nachweis":""
        })
    directory.mkdir(parents=True,exist_ok=True)
    with target.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS,delimiter=";")
        writer.writeheader()
        writer.writerows(output)
    print(f"[OK] {target}")
    print("[INFO] Rueckfragefaelle:",len(output),dict(Counter(r["pruefstatus"] for r in output)))
    print("[HINWEIS] Keine automatische Uebermittlung. Vor Versand Datenfreigabe und Inhalt pruefen.")
    print("[HINWEIS] Antworten in der Rueckfrageliste sichern; keine Originalquellen ueberschreiben.")


if __name__=="__main__":
    main()
