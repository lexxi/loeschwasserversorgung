#!/usr/bin/env python3
"""Lokaler HTML-Einstieg fuer vorhandene Gemeindeberichte und Offline-Karten.

Erzeugt reports/index.html und reports/<GKZ>/index.html.
Nur tatsaechlich existierende lokale Dateien werden verlinkt. Keine Netzaufrufe.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from html import escape
from pathlib import Path
from urllib.parse import quote
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REFERENCES = REPORTS / "references"
SOURCE_CATALOG = ROOT / "config" / "reference_documents.json"

PAGES = (
    ("Karten", (
        ("BEV/OSM – 41 Gebäude-Prüffälle", "addresses/bev_osm_pruefkarte.html",
         "Amtliche BEV-Gebäudepunkte ohne eindeutigen OSM-Innentreffer, mit Straßen und Gebäudekandidaten."),
        ("Gebäudehöhen – interaktive Karte", "gk_inventory/gebaeude_als_hoehenkarte.html",
         "Gebäudeflächen, geschätzte BEV-Höhen, Gemeindegrenze und OSM-Straßen."),
        ("Gebäude – ODB-Luftlinienabstände", "gebaeude_odb_abstandskarte.html",
         "Interaktive Karte mit lokalen ODB-Wasserentnahmestellen und Abstandsklassen."),
        ("ODB-Wasserentnahmestellen", "odb_wasserentnahmestellen.html",
         "Lokale ODB-Bestandskarte – vertrauliche Standortinformationen."),
        ("Mehrfachwidmungen – Prüfverzeichnis", "building_overlaps/index.html",
         "Übersicht mit anklickbaren Gebäudeprüfungen."),
    )),
    ("Berichte und Auswertungen", (
        ("BEV/OSM – Rückfragen an die Gemeinde (CSV)", "addresses/gemeinde_rueckfragen_bev_osm.csv",
         "Offene Prüffälle mit Rückmeldefeldern; keine automatische Übermittlung."),
        ("BEV/OSM – Zuordnungsprüfung CSV", "addresses/bev_gebaeudepunkte_osm_zuordnung.csv",
         "BEV-Subcodes mit OSM-Kandidaten, Status und gemessenen Abständen."),
        ("BEV/OSM – Zuordnungszusammenfassung", "addresses/bev_osm_zuordnung_summary.json",
         "Fallzahlen und nachvollziehbare Herkunft des amtlichen Gebäudepunktabgleichs."),
        ("Gebäudehöhen – Qualität und Auffälligkeiten", "gk_inventory/als_hoehen_qualitaet.json",
         "Median, Perzentile und Prüfhinweise."),
        ("Gebäudehöhen – gemeinsame Merkmaltabelle", "gk_inventory/gebaeude_gk_merkmale_mit_als.csv",
         "OSM-Attribute und geschätzte Höhen je Gebäude."),
        ("Gebäudehöhen – Gemeindedaten", "gk_inventory/gebaeude_als_hoehen_gemeinde.csv",
         "Ergebnis für alle analysierten Gebäude."),
        ("Gebäudehöhen – Zusammenfassung", "gk_inventory/als_hoehen_gemeinde_summary.json",
         "Qualität der gemeindeweiten BEV-Analyse."),
        ("GK-Merkmalsinventur", "gk_inventory/gebaeude_gk_merkmale.csv",
         "Vorhandene und fehlende Merkmale für eine spätere GK-Bewertung."),
        ("GK-Merkmalsstatistik", "gk_inventory/summary.json",
         "Anzahl der OSM-Attribute im Gebäudebestand."),
        ("Gebäudeabstände – CSV", "gebaeude_odb_abstaende.csv",
         "Luftlinienentfernungen zur nächsten verwendbaren ODB-Quelle."),
        ("Gebäudeabstände – JSON", "gebaeude_odb_abstaende.json",
         "Zusammenfassung der geometrischen Abstände."),
        ("ODB-Bestandsanalyse – CSV", "odb_bestandsanalyse.csv",
         "Auswertung der lokal erfassten ODB-Quellen."),
        ("ODB-Bestandsanalyse – JSON", "odb_bestandsanalyse.json",
         "Kennzahlen zu Typ, Status und Bestand."),
        ("Gemeindebericht", "gemeindebericht.md",
         "Zusammenfassender GIS-Bestandsbericht als Markdown."),
        ("Gemeindebericht – Daten", "gemeindebericht.json",
         "Maschinenlesbare Berichtsdaten."),
    )),
)


GLOSSARY = [["BEV","Bundesamt für Eich- und Vermessungswesen; amtliches Adressregister und Gebäudereferenzpunkte."],["OSM","OpenStreetMap; gemeinschaftlich gepflegte Gebäudegrundrisse, Straßen und Wege. Nicht amtlich identisch mit BEV."],["ODB","Kärntner Objektdatenbank; im Projekt lokale autorisierte Daten der Wasserentnahmestellen."],["ALS","Airborne Laserscanning; flugzeuggestützte Lasermessungen für geschätzte Gebäudehöhen."],["DOM","Digitales Oberflächenmodell: Höhen inklusive Dächer und Vegetation."],["DGM","Digitales Geländemodell: angenäherte Geländeoberfläche."],["GIS","Geoinformationssystem für räumliche Daten und Analysen."],["GPKG","GeoPackage: Datei mit räumlichen Daten und Tabellen."],["GeoJSON","Textformat für Geometrien und Attribute."],["EPSG","Kennnummer für Koordinatenreferenzsysteme, z. B. 3035, 31287 oder 4326."],["GKZ","Gemeindekennzahl; Malta: 20619."],["INSPIRE","EU-Rahmen für interoperable Geodaten."],["GK","Gebäudeklasse nach anwendbarem Baurecht; nicht automatisch aus Geometrie abzuleiten."],["OIB","Österreichisches Institut für Bautechnik; Begriffsbestimmungen und Richtlinien."],["TRVB","Technische Richtlinien Vorbeugender Brandschutz; die gültige Fassung muss fachlich geprüft werden."],["ÖBFV","Österreichischer Bundesfeuerwehrverband."],["RIS","Rechtsinformationssystem des Bundes."],["Luftlinie","Geometrisch kürzester Abstand; keine Schlauchstrecke oder befahrbare Route."],["ADRCD","BEV-Adresscode zur Identifikation einer amtlichen Adresse."],["ADRCD_SUBCD","BEV-Gebäude-Subcode; keine OSM-Gebäude-ID."],["OSM-ID","Technischer Bezeichner eines OpenStreetMap-Objekts."],["inside_unique","BEV-Gebäudepunkt liegt streng innerhalb genau eines OSM-Gebäudegrundrisses."],["boundary_tolerance","BEV-Gebäudepunkt liegt außerhalb, maximal 2 m von genau einem Gebäude: vorläufiger geometrischer Zuordnungskandidat."],["near_review","BEV-Punkt außerhalb, ein Kandidat im 15-m-Radius, aber keine eindeutige 2-m-Zuordnung."],["unmatched","Kein OSM-Grundriss innerhalb 15 m. Das tatsächliche Gebäude kann dennoch existieren."],["multiple_or_boundary","Punkt auf Polygonkante oder mehrere Gebäudegrundrisse berührt: Prüffall."],["2 m / 15 m","Projektinterne Toleranz beziehungsweise Suchradius; keine gesetzlichen Grenzwerte oder Genauigkeitsnachweise."],["OEM / BSM","Im aktuellen Projekt nicht eindeutig definierte Kürzel. Falls OEM eigentlich OSM meint: siehe OSM. BSM bleibt bis zur fachlichen Klärung offen."]]


def glossary_body():
    blocks=['<div class="note"><strong>Leseschlüssel:</strong> Projektbegriffe und Statuswerte; '
            'keine fachliche oder rechtliche Freigabe von Löschwasserbedarf und Gebäudeklassen.</div>']
    for abbr,meaning in GLOSSARY:
        blocks.append('<div class="tile"><strong>'+escape(abbr)+'</strong><span>'
                      +escape(meaning)+'</span></div>')
    return '<h2>Abkürzungen und Erläuterungen</h2><div class="grid">' + ''.join(blocks) + '</div>'


STYLE = """
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;color:#21344a;background:#f3f6fa}
*{box-sizing:border-box}body{max-width:1180px;margin:0 auto;padding:24px}
header{background:#203e56;color:#fff;padding:24px;border-radius:14px}
h1{margin:0 0 6px;font-size:1.6rem}h2{font-size:1.12rem;margin:28px 0 12px}
header p{color:#d9e7f0;margin:0}.note{background:#fff7e9;border-left:4px solid #dca045;
padding:12px 14px;border-radius:6px;line-height:1.5;margin:18px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
a.tile{display:block;padding:16px;background:#fff;border-radius:11px;border:1px solid #dce5ec;
box-shadow:0 1px 2px #24384b0d;text-decoration:none;color:inherit}
a.tile:hover,a.tile:focus{border-color:#417997;box-shadow:0 2px 10px #24466320}
.tile strong{display:block;margin-bottom:7px;color:#164d6b}
.tile span{font-size:.87rem;color:#586b7b;line-height:1.4;display:block}
footer{margin-top:28px;color:#667987;font-size:.84rem}
a.back{display:inline-block;margin:0 0 14px;color:#235d80}
.empty{padding:14px;background:white;border:1px dashed #bccbd5;border-radius:9px}
"""


def link_target(base: Path, relative: str) -> Path:
    """Reject absolute or escaping paths; links must remain under this municipality."""
    pure = Path(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsicherer Link: {relative}")
    path = (base / pure).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"Link ausserhalb des Berichtsordners: {relative}")
    return path


def href(relative: str) -> str:
    return "/".join(quote(p) for p in Path(relative).parts)


def tile(title: str, relative: str, description: str) -> str:
    return (f'<a class="tile" href="{escape(href(relative), quote=True)}">'
            f'<strong>{escape(title)}</strong><span>{escape(description)}</span></a>')


def document(title: str, body: str, back: str | None = None) -> str:
    back_link = (f'<a class="back" href="{escape(back, quote=True)}">'
                 '← Zur Gemeindeübersicht</a>') if back else ""
    stamp = escape(datetime.now().strftime("%d.%m.%Y %H:%M"))
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{STYLE}</style></head><body>'
            f'{back_link}<header><h1>{escape(title)}</h1>'
            '<p>Lokaler Berichtsnavigator – nur vorhandene Dateien</p></header>'
            f'{body}<footer>Erzeugt am {stamp}. Ohne Internetverbindung nutzbar.</footer>'
            '</body></html>')


def references_section(relative_prefix: str) -> str:
    """Build dual offline/online links from the explicit versioned catalog."""
    if not SOURCE_CATALOG.is_file():
        return ""
    data = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    groups = {}
    for source in data["documents"]:
        group = source.get("category", "Weitere Dokumente")
        groups.setdefault(group, []).append(source)
    blocks = ['<section><h2>Rechtsgrundlagen und Fachquellen – offline / online</h2>',
              '<p>Offline-Dokumente bleiben lokal gespeichert. Externe Links benötigen Internet. '
              'Die jeweilige Fassung und die Anwendbarkeit sind gesondert zu prüfen.</p>']
    for title, items in groups.items():
        blocks.append(f'<h2>{escape(title)}</h2><div class="grid">')
        for source in items:
            filename = source["filename"]
            if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
                raise ValueError(f"Unsicherer Dateiname in Quellenkatalog: {filename}")
            target = REFERENCES / filename
            offline = (f'<a href="{escape(href(relative_prefix+"references/"+filename),quote=True)}">'
                       'Offline öffnen</a>') if target.is_file() else (
                       '<span>Offline noch nicht vorhanden</span>')
            online = (f'<a href="{escape(source["online_url"],quote=True)}" '
                      'target="_blank" rel="noopener noreferrer">Online öffnen</a>')
            alternate = source.get("additional_online_url")
            if alternate:
                online += (f' · <a href="{escape(alternate,quote=True)}" '
                           'target="_blank" rel="noopener noreferrer">Weitere Originalquelle</a>')
            blocks.append(
                f'<div class="tile"><strong>{escape(source["title"])}</strong>'
                f'<span>{escape(source.get("edition",""))}</span>'
                f'<p>{offline} · {online}</p>'
                f'<span>{escape(source.get("usage_note",""))}</span></div>'
            )
        blocks.append('</div>')
    blocks.append('</section>')
    return "".join(blocks)


def generate_municipality(mid: str, folder: Path) -> tuple[Path, int]:
    sections = []
    count = 0
    known = set()
    for heading, items in PAGES:
        active = []
        for title, relative, description in items:
            file = link_target(folder, relative)
            if file.is_file():
                active.append(tile(title, relative, description))
                known.add(file.resolve())
        if active:
            sections.append(f'<section><h2>{escape(heading)}</h2>'
                            f'<div class="grid">{"".join(active)}</div></section>')
            count += len(active)
    # Capture further generated HTML views, e.g. overlapping building detail pages,
    # without exposing raw private GeoJSON or non-report directories.
    extras = []
    for file in sorted(folder.rglob("*.html")):
        if file.name.lower() == "index.html" or file.resolve() in known or file.is_symlink():
            continue
        relative = file.relative_to(folder).as_posix()
        if len(extras) >= 80:
            break
        extras.append(tile(file.stem.replace("_", " "), relative,
                           "Weitere lokal vorhandene HTML-Unterseite"))
    if extras:
        sections.append(f'<section><h2>Weitere HTML-Seiten</h2><div class="grid">'
                        f'{"".join(extras)}</div></section>')
        count += len(extras)
    body = ('<div class="note"><strong>Hinweis:</strong> Die Karten und Berichte '
            'sind Bestands- bzw. Auswertungsdaten, <strong>kein</strong> rechtlicher '
            'Nachweis der Löschwasserversorgung oder einer Gebäudeklasse. '
            'Insbesondere die ODB-Karten enthalten nichtöffentliche Standortdaten; '
            'diese Seite und ihre Unterseiten nur lokal verwenden.</div>')
    body += '<section><h2>Erläuterungen</h2><div class="grid">' + tile(
        "Glossar und Abkürzungen", "../glossar.html",
        "BEV, OSM, ODB, ALS, GK sowie Kartensymbole und Prüfstatus."
    ) + '</div></section>'
    body += references_section("../")
    body += "".join(sections) if sections else (
        '<p class="empty">Noch keine Karten oder Berichte gefunden. '
        'Zuerst die entsprechenden Analyseskripte ausführen.</p>')
    out = folder / "index.html"
    out.write_text(document(f"Gemeinde {mid} – Karten und Berichte", body,
                            back="../index.html"), encoding="utf-8")
    return out, count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", help="Nur diese GKZ aktualisieren, z. B. 20619")
    parser.add_argument("--open", action="store_true", help="Index im Browser öffnen")
    args = parser.parse_args()
    if args.gemeinde and not (
        len(args.gemeinde) == 5 and args.gemeinde.isdigit() and
        args.gemeinde.startswith("2")
    ):
        parser.error("--gemeinde muss eine fünfstellige Kärntner GKZ sein")
    REPORTS.mkdir(parents=True, exist_ok=True)
    directories = ([REPORTS / args.gemeinde] if args.gemeinde else
                   [p for p in sorted(REPORTS.iterdir()) if p.is_dir()
                    and p.name.isdigit() and len(p.name) == 5])
    entries = []
    selected = None
    for folder in directories:
        if not folder.is_dir():
            print(f"[INFO] Keine Reports für Gemeinde {folder.name}: {folder}")
            continue
        target, count = generate_municipality(folder.name, folder)
        entries.append(tile(f"Gemeinde {folder.name}", f"{folder.name}/index.html",
                            f"{count} verfügbare Unterseiten und Auswertungen"))
        selected = target
        print(f"[OK] {target} ({count} Links)")
    # Regenerate root index from all available municipality indexes; keep
    # previously generated municipalities when --gemeinde is used.
    entries = []
    for folder in sorted(REPORTS.iterdir()):
        if (folder.is_dir() and folder.name.isdigit() and len(folder.name) == 5
                and (folder / "index.html").is_file()):
            entries.append(tile(f"Gemeinde {folder.name}", f"{folder.name}/index.html",
                                "Karten, Berichte und lokale Auswertungen öffnen"))
    body = ('<div class="note">Die Inhalte werden nur aus den lokal vorhandenen '
            'Berichten verlinkt. <strong>Nicht auf einen öffentlichen Webserver '
            'kopieren:</strong> einzelne Karten enthalten ODB-Fachdaten.</div>'
            '<h2>Gemeinden</h2>')
    body += '<div class="grid">' + "".join(entries) + '</div>' if entries else (
        '<p class="empty">Keine Gemeindeberichte vorhanden.</p>')
    body += references_section("")
    glossary_file = REPORTS / "glossar.html"
    glossary_file.write_text(document("Glossar – Löschwasserversorgung", glossary_body(),
                                     back="index.html"),encoding="utf-8")
    print(f"[OK] {glossary_file}")
    body += '<section><h2>Hilfe und Erläuterungen</h2><div class="grid">' + tile(
        "Glossar und Abkürzungen", "glossar.html",
        "BEV, OSM, ODB, ALS, Gebäudeklassen und Zuordnungsstatus."
    ) + '</div></section>'
    root_index = REPORTS / "index.html"
    root_index.write_text(document("Löschwasserversorgung – Berichtszentrale", body),
                          encoding="utf-8")
    print(f"[OK] {root_index} ({len(entries)} Gemeinden)")
    if args.open:
        webbrowser.open((selected or root_index).resolve().as_uri())


if __name__ == "__main__":
    main()
