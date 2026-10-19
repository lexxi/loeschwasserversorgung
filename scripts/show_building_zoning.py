#!/usr/bin/env python3
"""Ein einzelnes OSM-Gebäude und seine geschnittenen Widmungspolygone als Offline-HTML.

Keine rechtliche Priorisierung: die Prozentwerte beschreiben geometrische
Flächenschnitte der OSM-Gebäudegrundfläche mit amtlichen Widmungspolygonen.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import webbrowser

import geopandas as gpd
from shapely.geometry import box

from municipality_text import readable_name


COLORS = ["#4f82bd", "#e6a34a", "#4b9b75", "#b37ac5", "#d17b81", "#8c9b4d"]
EPSG = 31287


def geom_paths(geometry, project):
    if geometry.is_empty:
        return ""
    if geometry.geom_type == "Polygon":
        polygons = [geometry]
    elif geometry.geom_type == "MultiPolygon":
        polygons = list(geometry.geoms)
    elif geometry.geom_type == "GeometryCollection":
        return " ".join(geom_paths(g, project) for g in geometry.geoms)
    else:
        return ""
    paths = []
    for poly in polygons:
        rings = [poly.exterior, *poly.interiors]
        for ring in rings:
            points = [project(x, y) for x, y in ring.coords]
            paths.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z")
    return " ".join(paths)


def load_data(base):
    building_file = base / "osm" / "buildings.geojson"
    zoning_file = base / "zoning.geojson"
    for p in (building_file, zoning_file):
        if not p.is_file():
            raise FileNotFoundError(f"Datei fehlt: {p}; zuerst die Gemeinde-Pipeline ausführen")
    buildings = gpd.read_file(building_file)
    zoning = gpd.read_file(zoning_file)
    if buildings.crs is None or zoning.crs is None:
        raise ValueError("Gebäude/Widmung ohne ausgewiesenes CRS")
    if "osm_id" not in buildings or "KATEGORIE" not in zoning:
        raise ValueError("Erwartete Felder fehlen (osm_id bzw. KATEGORIE)")
    return buildings.to_crs(EPSG), zoning.to_crs(EPSG)


def matching_zones(footprint, zoning):
    area = footprint.area
    if area <= 0 or not footprint.is_valid:
        raise ValueError("Gebäudegrundfläche leer oder ungültig")
    result = []
    for idx in zoning.sindex.query(footprint, predicate="intersects"):
        z = zoning.iloc[int(idx)]
        inter = footprint.intersection(z.geometry)
        if inter.area <= 0:
            continue
        result.append((z, inter, inter.area / area * 100))
    result.sort(key=lambda x: x[2], reverse=True)
    return result


def choose_building(buildings, zoning, limit):
    candidates = []
    for _, row in buildings.iterrows():
        zones = matching_zones(row.geometry, zoning)
        if len(zones) < 2:
            continue
        candidates.append((str(row.osm_id), len(zones), zones[0][2], zones[1][2]))
    candidates.sort(key=lambda r: (abs(r[2] - 50), r[0]))
    print(f"Gebäude mit >= 2 positiven Widmungs-Flächenschnitten: {len(candidates)}")
    if not candidates:
        raise SystemExit("Keine Mehrfachschnitte vorhanden")
    print("Beispiele (nach Nähe zu 50 % größter Flächenanteil sortiert):")
    for i, (osm, count, first, second) in enumerate(candidates[:limit], start=1):
        print(f"{i:>3}  {osm:<22} {count} Polygone  {first:.2f} % / {second:.2f} %")
    choice = input("Nummer oder vollständige OSM-ID eingeben: ").strip()
    if choice.isdecimal() and 1 <= int(choice) <= min(limit, len(candidates)):
        return candidates[int(choice) - 1][0]
    return choice


def draw(osm_id, footprint, zoning, name, building_data=None):
    zones = matching_zones(footprint, zoning)
    if not zones:
        raise ValueError("Gebäude hat keinen positiven Flächenschnitt mit Widmungen")
    center = footprint.centroid
    x0, y0, x1, y1 = footprint.bounds
    span = max(x1 - x0, y1 - y0, 18.0)
    radius = max(span * 1.8, 28.0)
    view = box(center.x - radius, center.y - radius,
               center.x + radius, center.y + radius)
    width, height = 900, 680
    def project(x, y):
        return ((x - view.bounds[0]) / (2 * radius) * width,
                (view.bounds[3] - y) / (2 * radius) * height)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Gebäude und geschnittene Widmungsflächen">',
           '<rect width="900" height="680" fill="#f5f6f8"/>']
    # Nur die Widmungspolygone zeigen, die das gewählte Haus positiv schneiden.
    # Für die Darstellung auf den Kartenausschnitt beschränken.
    for i, (zone, intersection, pct) in enumerate(zones):
        color = COLORS[i % len(COLORS)]
        shape = zone.geometry.intersection(view)
        path = geom_paths(shape, project)
        svg.append(f'<path d="{path}" fill="{color}" fill-opacity=".20" stroke="{color}" stroke-width="2" fill-rule="evenodd"/>')
    # Einfärbung der tatsächlichen Schnitte INNERHALB der Gebäudegrundfläche.
    for i, (zone, intersection, pct) in enumerate(zones):
        path = geom_paths(intersection, project)
        svg.append(f'<path d="{path}" fill="{COLORS[i % len(COLORS)]}" fill-opacity=".80" stroke="none" fill-rule="evenodd"/>')
    building_path = geom_paths(footprint, project)
    svg.append(f'<path d="{building_path}" fill="none" stroke="#202b38" stroke-width="4" fill-rule="evenodd"/>')
    cx, cy = project(center.x, center.y)
    svg.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4" fill="#202b38"/>')
    svg.append('</svg>')


    def display(value):
        if value is None:
            return "–"
        string = str(value).strip()
        return escape(string) if string and string.lower() not in ("nan", "none") else "–"

    allowed_building_fields = (
        ("OSM-Gebäudetyp", "building"),
        ("Gebäudenutzung laut OSM", "building:use"),
        ("Stockwerke laut OSM", "building:levels"),
        ("Einrichtung", "amenity"),
        ("Tourismus", "tourism"),
        ("Geschäft", "shop"),
        ("Flächennutzung", "landuse"),
    )
    building_rows = []
    if building_data is not None:
        for label, field in allowed_building_fields:
            shown = display(building_data.get(field))
            if shown != "–":
                building_rows.append(f"<tr><th>{escape(label)}</th><td>{shown}</td></tr>")
    building_rows.append(f"<tr><th>OSM-ID</th><td>{escape(osm_id)}</td></tr>")
    building_rows.append(f"<tr><th>Grundfläche (OSM)</th><td>{footprint.area:.2f} m²</td></tr>")
    building_rows.append(f"<tr><th>Geometrietyp</th><td>{escape(footprint.geom_type)}</td></tr>")
    building_rows.append(f"<tr><th>Widmungsschnitte</th><td>{len(zones)}</td></tr>")

    zone_details = []
    zone_fields = ("OBJECTID", "KATEGORIE", "WIDMUNG", "BEZEICHNUNG",
                   "KURZBEZEICHNUNG", "CODE", "WIDCODE", "GEMNR")
    for i, (zone, intersection, pct) in enumerate(zones):
        rows = []
        for field in zone_fields:
            if field in zone.index:
                rows.append(f"<tr><th>{escape(field)}</th><td>{display(zone[field])}</td></tr>")
        rows.extend((
            f"<tr><th>Gesamtfläche Widmungspolygon</th><td>{zone.geometry.area:.2f} m²</td></tr>",
            f"<tr><th>Schnittfläche mit Gebäude</th><td>{intersection.area:.2f} m²</td></tr>",
            f"<tr><th>Anteil am Gebäude</th><td>{pct:.2f} %</td></tr>",
        ))
        color = COLORS[i % len(COLORS)]
        zone_details.append(f'<section class="attr"><h3><span class="swatch" style="background:{color}"></span>'
                            f'Widmungspolygon {i + 1}</h3><table>{"".join(rows)}</table></section>')

    table = []
    for i, (zone, intersection, pct) in enumerate(zones):
        category = escape(str(zone.get("KATEGORIE") or "Unbekannt"))
        designation = escape(str(zone.get("WIDMUNG") or "–"))
        object_id = escape(str(zone.get("OBJECTID") or "–"))
        color = COLORS[i % len(COLORS)]
        table.append(f'<tr><td><span class="swatch" style="background:{color}"></span>{i+1}</td>'
                     f'<td>{category}</td><td>{designation}</td><td>{object_id}</td>'
                     f'<td class="num">{intersection.area:.2f}</td><td class="num"><b>{pct:.2f} %</b></td></tr>')

    title = escape(readable_name(name))
    osm_label = escape(osm_id)
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Widmungsgrenze – {osm_label}</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;background:#f7f8fa;color:#172536;margin:0;padding:25px}}
main{{max-width:1100px;margin:auto}}h1{{font-size:1.6rem;margin-bottom:4px}}
h2{{font-size:1.2rem;padding:12px;margin:0}}h3{{font-size:1rem;margin:8px 0}}
.attrs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px;padding:12px}}
.attr{{padding:8px;border:1px solid #e0e5eb;border-radius:8px;overflow-wrap:anywhere}}
.attr table th{{width:48%;font-weight:600}}
.note{{color:#546173}}.panel{{background:white;border:1px solid #dce2e7;border-radius:10px;overflow:hidden;margin-top:16px}}
svg{{width:100%;height:auto;display:block}}table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:10px;border-bottom:1px solid #e8edf0}}.num{{text-align:right;white-space:nowrap}}
.swatch{{display:inline-block;width:14px;height:14px;margin-right:8px;vertical-align:middle;border-radius:3px}}
@media(max-width:720px){{body{{padding:10px}}table{{font-size:.78rem}}th,td{{padding:5px}}}}
</style></head><body><main>
<h1>Gebäude {osm_label}</h1>
<div class="note">{title} · Gebäudegrundfläche: {footprint.area:.2f} m² · {len(zones)} Widmungspolygone mit positivem Flächenschnitt</div>
<div class="panel">{''.join(svg)}</div>
<div class="panel"><table><thead><tr><th>Nr.</th><th>Kategorie</th><th>Widmung</th><th>OBJECTID</th><th class="num">Schnitt m²</th><th class="num">Anteil</th></tr></thead>
<tbody>{''.join(table)}</tbody></table></div>
<div class="panel"><h2>OSM-Gebäudeattribute</h2><div class="attrs"><section class="attr"><table>{''.join(building_rows)}</table></section></div></div>
<div class="panel"><h2>Attribute der geschnittenen Widmungsflächen</h2><div class="attrs">{''.join(zone_details)}</div></div>
<p class="note">Das Gebäude ist schwarz umrandet. Helle Farben zeigen die geschnittenen Widmungspolygone im Ausschnitt;
kräftige Farben zeigen den jeweiligen Flächenschnitt <strong>innerhalb</strong> der Gebäudegrundfläche.
Der dunkle Punkt markiert den geometrischen Schwerpunkt (nicht den für den GIS-Join verwendeten Repräsentativpunkt).</p>
<p class="note">Anteile beziehen sich auf die gesamte OSM-Gebäudegrundfläche. Sie müssen bei Datenlücken oder geometrischen
Überlagerungen nicht exakt 100 % ergeben. Keine automatische rechtliche Priorisierung, keine Prüfung der Rechtswirksamkeit.
Keine Hausnummern und keine Kartendienste eingebunden; HTML/SVG funktioniert offline.</p>
</main></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Fünfstellige Kärntner Gemeindenummer")
    parser.add_argument("--osm-id", help="OSM-Element-ID, z. B. way/371120663; ohne Angabe interaktive Auswahl")
    parser.add_argument("--limit", type=int, default=25, help="Anzahl Beispiele im Auswahlmenü")
    parser.add_argument("--out", type=Path, help="Ziel-HTML; Standard reports/<gemeinde>/haus_<osm-id>.html")
    parser.add_argument("--open", action="store_true", help="Ergebnis im Standardbrowser öffnen")
    args = parser.parse_args()
    if not (args.gemeinde.isdigit() and len(args.gemeinde) == 5 and args.gemeinde.startswith("2")):
        parser.error("Ungültige Kärntner Gemeindenummer")
    base = Path("data/processed") / args.gemeinde
    buildings, zoning = load_data(base)
    osm_id = args.osm_id or choose_building(buildings, zoning, max(1, args.limit))
    matched = buildings.loc[buildings["osm_id"].astype(str).eq(osm_id)]
    if len(matched) != 1:
        parser.error(f"OSM-ID nicht eindeutig vorhanden: {osm_id!r}")
    municipality = args.gemeinde
    manifest = base / "import_manifest.json"
    if manifest.is_file():
        municipality = json.loads(manifest.read_text(encoding="utf-8")).get("municipality_name", municipality)
    result = draw(osm_id, matched.geometry.iloc[0], zoning, municipality, matched.iloc[0])
    safe_id = osm_id.replace("/", "_").replace("\\", "_")
    out = args.out or Path("reports") / args.gemeinde / f"haus_{safe_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    print(f"[OK] {out.resolve()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
