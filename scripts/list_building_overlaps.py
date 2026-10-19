#!/usr/bin/env python3
"""Lokaler Katalog aller Gebäude mit mindestens zwei positiven Widmungsschnitten.

Erzeugt CSV, durchsuchbares HTML-Verzeichnis und anklickbare Einzelansichten.
Keine Hausnummern, Straßennamen, personenbezogenen OSM-Namen oder Internetdienste.
"""
from __future__ import annotations

import argparse
import csv
from html import escape
import json
from pathlib import Path
from urllib.parse import quote
import webbrowser

from municipality_text import readable_name
from show_building_zoning import load_data, matching_zones, draw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="5-stellige Kärntner Gemeindenummer")
    parser.add_argument("--out", type=Path, help="Ausgabeordner; Standard: reports/<gemeinde>/ueberlappungen")
    parser.add_argument("--open", action="store_true", help="HTML-Liste im Browser öffnen")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("Ungültige Kärntner Gemeindenummer")
    base = Path("data/processed") / mid
    buildings, zoning = load_data(base)
    manifest = base / "import_manifest.json"
    municipality = mid
    if manifest.is_file():
        info = json.loads(manifest.read_text(encoding="utf-8"))
        if str(info.get("municipality_id")) != mid:
            parser.error("Gemeinde-Manifest stimmt nicht mit --gemeinde überein")
        municipality = readable_name(str(info.get("municipality_name", mid)))

    out = args.out or Path("reports") / mid / "ueberlappungen"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for _, building in buildings.iterrows():
        footprint = building.geometry
        zones = matching_zones(footprint, zoning)
        if len(zones) < 2:
            continue
        osm_id = str(building["osm_id"])
        # Nur bekannte OSM-ID-Formate erlauben: kein Dateipfad aus OSM-Attributen.
        element, sep, identifier = osm_id.partition("/")
        if element not in ("way", "relation") or not sep or not identifier.isdecimal():
            raise ValueError(f"Unerwartete OSM-ID: {osm_id!r}")
        filename = f"haus_{element}_{identifier}.html"
        records.append({
            "osm_id": osm_id,
            "building": str(building.get("building") or "–"),
            "building_area_m2": round(footprint.area, 2),
            "zone_count": len(zones),
            "dominant_pct": round(zones[0][2], 2),
            "second_pct": round(zones[1][2], 2),
            "total_pct": round(sum(z[2] for z in zones), 2),
            "categories": " / ".join(sorted({str(z[0].get("KATEGORIE") or "?") for z in zones})),
            "objectids": " / ".join(str(z[0].get("OBJECTID") or "–") for z in zones),
            "detail": filename,
        })
        (out / filename).write_text(
            draw(osm_id, footprint, zoning, municipality, building),
            encoding="utf-8",
        )

    records.sort(key=lambda r: (abs(r["dominant_pct"] - 50), r["osm_id"]))
    headers = ["osm_id", "building", "building_area_m2", "zone_count",
               "dominant_pct", "second_pct", "total_pct", "categories", "objectids", "detail"]
    with (out / "ueberlappungen.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers, delimiter=";")
        writer.writeheader()
        writer.writerows(records)

    table_rows = []
    for r in records:
        href = quote(r["detail"])
        table_rows.append(
            "<tr>"
            f'<td><a href="{href}">{escape(r["osm_id"])}</a></td>'
            f'<td>{escape(r["building"])}</td>'
            f'<td data-sort="{r["building_area_m2"]}">{r["building_area_m2"]:.2f}</td>'
            f'<td>{r["zone_count"]}</td>'
            f'<td data-sort="{r["dominant_pct"]}">{r["dominant_pct"]:.2f} %</td>'
            f'<td>{r["second_pct"]:.2f} %</td>'
            f'<td>{escape(r["categories"])}</td>'
            f'<td>{escape(r["objectids"])}</td>'
            "</tr>"
        )
    title = escape(municipality)
    page = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gebäude mit Widmungsüberschneidungen – {title}</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;background:#f7f8fa;color:#192634;margin:0;padding:24px}}
main{{max-width:1300px;margin:auto}}h1{{font-size:1.6rem}}
input{{padding:10px;width:min(560px,95%);border:1px solid #bcc7d0;border-radius:7px;font-size:1rem}}
.note{{color:#586472}}.tablewrap{{overflow:auto;background:white;border:1px solid #dbe1e8;border-radius:9px;margin-top:15px}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:9px;border-bottom:1px solid #e8edf1;white-space:nowrap}}
th{{position:sticky;top:0;background:#edf2f6}}a{{color:#145b9d}}tr:hover td{{background:#f0f6fb}}
</style></head><body><main><h1>Gebäude mit mehreren Widmungsschnitten</h1>
<p>{title} ({mid}) · <strong>{len(records)} Gebäude</strong> mit mindestens zwei positiven Flächenschnitten.</p>
<p class="note">Einträge nach Nähe der größten Überdeckung zu 50 % sortiert. OSM-ID anklicken, um Gebäude,
Widmungspolygone und Attribute grafisch anzuzeigen. Keine rechtliche Priorisierung oder Feststellung eines Datenfehlers.</p>
<label for="search">Gebäude/OSM-ID/Widmung suchen:</label><p><input id="search" type="search" placeholder="z. B. way/ oder Bauland" oninput="filterRows()"></p>
<p class="note" id="count">{len(records)} Einträge sichtbar</p>
<div class="tablewrap"><table id="records"><thead><tr>
<th>OSM-ID</th><th>building</th><th>Gebäudefläche m²</th><th>Polygone</th>
<th>Größter Schnitt</th><th>Zweitgrößter</th><th>Kategorien</th><th>OBJECTIDs</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table></div>
<p class="note">CSV: ueberlappungen.csv · Dateiformat: UTF-8, Trennzeichen Semikolon.
Ausschließlich lokale OSM-/KAGIS-Daten; keine Hausnummern oder externen Kartendienste.</p></main>
<script>
function filterRows() {{
  const term = document.getElementById("search").value.toLocaleLowerCase("de");
  let visible = 0;
  document.querySelectorAll("#records tbody tr").forEach(row => {{
    const match = row.textContent.toLocaleLowerCase("de").includes(term);
    row.hidden = !match;
    if (match) visible++;
  }});
  document.getElementById("count").textContent = visible + " Einträge sichtbar";
}}
</script></body></html>"""
    index = out / "index.html"
    index.write_text(page, encoding="utf-8")
    print(f"[OK] {len(records)} Gebäude mit Mehrfachschnitt")
    print(f"[OK] HTML-Katalog: {index.resolve()}")
    print(f"[OK] CSV: {(out / 'ueberlappungen.csv').resolve()}")
    if args.open:
        webbrowser.open(index.resolve().as_uri())


if __name__ == "__main__":
    main()
