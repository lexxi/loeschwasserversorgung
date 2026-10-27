#!/usr/bin/env python3
"""AP2: ALS-Hoehenqualitaet, gemeinsame OSM-Merkmale und Offline-Gebaeudekarte.

Die Klassengrenzen visualisieren Objekthoehen; sie sind KEINE OIB-Gebaeudeklassen.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from html import escape
import json
import math
from pathlib import Path
from statistics import median
import webbrowser

import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
HEIGHT_FIELDS = ("height_median_m", "height_p90_m", "height_max_m")
ATTRIBUTES = ("building", "addr:street", "addr:housenumber", "addr:city",
              "building:levels", "height", "roof:levels",
              "building:use", "building:flats", "building:units",
              "amenity", "tourism", "shop")
BANDS = [
    ("under_3", "Unter 3 m", "#6b9dad"),
    ("3_to_6", "3 bis unter 6 m", "#47a37c"),
    ("6_to_9", "6 bis unter 9 m", "#b1bf53"),
    ("9_to_12", "9 bis unter 12 m", "#e5a04b"),
    ("12_to_18", "12 bis unter 18 m", "#d96f4f"),
    ("18_plus", "Ab 18 m", "#994a78"),
    ("review", "Prueffall / keine ausreichenden Pixel", "#85858c"),
]


def safe_text(value):
    if value is None:
        return ""
    try:
        if math.isnan(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def number(value):
    try:
        val = float(safe_text(value))
    except (ValueError, TypeError):
        return None
    return val if math.isfinite(val) else None


def band(value):
    if value is None:
        return "review"
    if value < 3:
        return "under_3"
    if value < 6:
        return "3_to_6"
    if value < 9:
        return "6_to_9"
    if value < 12:
        return "9_to_12"
    if value < 18:
        return "12_to_18"
    return "18_plus"


def polygons_svg(geom):
    polygons = [geom] if geom.geom_type == "Polygon" else (
        geom.geoms if geom.geom_type == "MultiPolygon" else []
    )
    parts = []
    for polygon in polygons:
        for ring in (polygon.exterior, *polygon.interiors):
            parts.append("M " + " L ".join(
                f"{x:.2f},{-y:.2f}" for x, y in ring.coords
            ) + " Z")
    return " ".join(parts)


def lines_svg(geom):
    if geom is None or geom.is_empty:
        return ""
    lines = [geom] if geom.geom_type == "LineString" else (
        geom.geoms if geom.geom_type == "MultiLineString" else []
    )
    return " ".join(
        "M " + " L ".join(f"{x:.2f},{-y:.2f}" for x, y in line.coords)
        for line in lines if len(line.coords) > 1
    )


def road_class(kind):
    if kind in ("motorway", "trunk", "primary", "secondary", "tertiary",
                "motorway_link", "trunk_link", "primary_link", "secondary_link",
                "tertiary_link"):
        return "major"
    if kind in ("residential", "unclassified", "living_street", "service", "road"):
        return "local"
    return "path"


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct / 100
    lo = math.floor(index)
    hi = math.ceil(index)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", default="20619")
    parser.add_argument("--open", action="store_true", help="HTML im Browser oeffnen")
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit() or not mid.startswith("2"):
        parser.error("Ungueltige Gemeindenummer")
    buildings_path = ROOT / "data" / "processed" / mid / "osm" / "buildings.geojson"
    heights_path = ROOT / "reports" / mid / "gk_inventory" / "gebaeude_als_hoehen_gemeinde.csv"
    for p in (buildings_path, heights_path):
        if not p.is_file():
            parser.error(f"Eingabe fehlt: {p}")
    boundary_path = ROOT / "data" / "processed" / mid / "boundary.geojson"
    roads_path = ROOT / "data" / "processed" / mid / "osm" / "roads.geojson"
    if not boundary_path.is_file():
        parser.error(f"Gemeindegrenze fehlt: {boundary_path}")
    boundary = gpd.read_file(boundary_path)
    if boundary.empty or boundary.crs is None:
        raise ValueError("Gemeindegrenze leer oder ohne Koordinatensystem")
    border = boundary.to_crs(31287).geometry.union_all()
    if border.is_empty:
        raise ValueError("Gemeindegrenze ohne Geometrie")
    roads_markup = []
    if roads_path.is_file():
        roads = gpd.read_file(roads_path)
        if roads.crs is None:
            raise ValueError("OSM-Strassen ohne Koordinatensystem")
        for _, road in roads.to_crs(31287).iterrows():
            road_svg = lines_svg(road.geometry)
            if road_svg:
                kind = safe_text(road.get("highway"))
                roads_markup.append(
                    f'<path class="road {road_class(kind)}" d="{escape(road_svg, quote=True)}">'
                    f'<title>{escape(safe_text(road.get("name")) or kind)}</title></path>'
                )
    frame = gpd.read_file(buildings_path)
    if frame.empty or frame.crs is None or "osm_id" not in frame:
        raise ValueError("Ungueltiger OSM-Gebaeudebestand")
    frame = frame.to_crs(31287)
    ids = frame["osm_id"].astype(str)
    if ids.duplicated().any() or ids.eq("").any():
        raise ValueError("Leere oder doppelte OSM-ID")
    measured = {}
    with heights_path.open("r", encoding="utf-8-sig", newline="") as file:
        for entry in csv.DictReader(file, delimiter=";"):
            osm_id = safe_text(entry.get("osm_id"))
            if not osm_id or osm_id in measured:
                raise ValueError(f"Doppelte oder leere Hoehen-OSM-ID: {osm_id}")
            measured[osm_id] = entry
    extra = set(measured) - set(ids)
    missing = set(ids) - set(measured)
    if extra or missing:
        raise ValueError(f"OSM-/Hoeheninventar nicht deckungsgleich: "
                         f"{len(missing)} fehlen, {len(extra)} zusaetzlich. "
                         "Höhenanalyse mit aktuellem OSM-Stand erneut ausfuehren.")
    official_by_id = {}
    official_file = ROOT / "reports" / mid / "addresses" / "gebaeude_adressen.csv"
    if official_file.is_file():
        with official_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for entry in csv.DictReader(handle, delimiter=";"):
                oid = safe_text(entry.get("osm_id"))
                if not oid or oid in official_by_id:
                    raise ValueError(f"Doppelte oder leere OSM-ID bei amtlichen Adressen: {oid}")
                official_by_id[oid] = entry
        if set(official_by_id) != set(ids):
            raise ValueError("Hausnummern-Zuordnung passt nicht zum aktuellen OSM-Gebaeudestand. "
                             "join_buildings_addresses.py erneut ausfuehren.")
        print(f"[INFO] Amtliche Hausnummernzuordnung eingebunden: {official_file}")
    else:
        print("[INFO] Keine amtliche Hausnummernzuordnung vorhanden; nur OSM-Adressen.")
    rows = []
    plotted = []
    counts = Counter()
    plausible = []
    flags = Counter()
    for _, feature in frame.iterrows():
        osm_id = str(feature["osm_id"])
        h = measured[osm_id]
        status = safe_text(h.get("quality")) or "unknown"
        median_m = number(h.get("height_median_m"))
        p90 = number(h.get("height_p90_m"))
        max_m = number(h.get("height_max_m"))
        ratio = number(h.get("valid_ratio"))
        pixel_count = int(number(h.get("valid_pixels")) or 0)
        issues = []
        if status != "estimated":
            issues.append(status)
        if status == "estimated":
            if median_m is None or p90 is None or max_m is None:
                issues.append("missing_height_values")
            else:
                plausible.append(median_m)
                if median_m < 1:
                    issues.append("very_low_under_1m")
                if median_m >= 25:
                    issues.append("high_at_least_25m")
                if max_m - median_m >= 10:
                    issues.append("large_roof_spread_at_least_10m")
                if max_m < median_m or p90 < median_m:
                    issues.append("inconsistent_percentiles")
            if ratio is not None and ratio < 0.85:
                issues.append("coverage_below_85pct")
        for issue in issues:
            flags[issue] += 1
        category = band(median_m) if status == "estimated" else "review"
        counts[category] += 1
        record = {
            "osm_id": osm_id,
            "building": safe_text(feature.get("building")),
            "footprint_m2": round(float(feature.geometry.area), 1),
            **{field:safe_text(feature.get(field)) for field in ATTRIBUTES if field != "building"},
            "official_address": safe_text(official_by_id.get(osm_id, {}).get("official_addresses")),
            "official_address_count": safe_text(official_by_id.get(osm_id, {}).get("address_count")),
            "official_address_status": safe_text(official_by_id.get(osm_id, {}).get("address_status")) or "not_imported",
            "height_median_m": median_m if median_m is not None else "",
            "height_p90_m": p90 if p90 is not None else "",
            "height_max_m": max_m if max_m is not None else "",
            "valid_pixels": pixel_count,
            "valid_ratio": ratio if ratio is not None else "",
            "height_quality": status,
            "height_review_flags": ",".join(issues),
            "height_band": category,
            "gk_actual": "unknown",
            "gk_status": "unassessed",
        }
        rows.append(record)
        path = polygons_svg(feature.geometry)
        if path:
            plotted.append((path,record))
    outdir = ROOT / "reports" / mid / "gk_inventory"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "gebaeude_gk_merkmale_mit_als.csv"
    cols = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=cols, delimiter=";")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r:r["osm_id"]))
    stats = {
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "municipality_id":mid,
        "source_als":str(heights_path),"source_osm":str(buildings_path),
        "buildings":len(rows),
        "quality_counts":dict(Counter(r["height_quality"] for r in rows)),
        "height_bands":dict(counts),
        "review_flags":dict(flags),
        "median_height_m":round(median(plausible),2) if plausible else None,
        "p05_height_m":percentile(plausible,5),
        "p95_height_m":percentile(plausible,95),
        "minimum_height_m":min(plausible) if plausible else None,
        "maximum_height_m":max(plausible) if plausible else None,
        "note":"Hoehenstatistik nur fuer quality=estimated. Flags sind heuristische Sichtpruefungen; "
               "keine GK, Geschosszahl oder OIB-Fluchtniveau.",
    }
    json_path = outdir / "als_hoehen_qualitaet.json"
    json_path.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    bounds = border.bounds
    xmin, ymin, xmax, ymax = map(float,bounds)
    pad=max(30.0,(xmax-xmin)*0.035,(ymax-ymin)*0.035)
    vb = [xmin-pad,-ymax-pad,(xmax-xmin)+2*pad,(ymax-ymin)+2*pad]
    outline_path = polygons_svg(border)
    svg_paths = []
    for path,r in plotted:
        attrs = json.dumps({
            "id":r["osm_id"],"building":r["building"],
            "area":r["footprint_m2"],"median":r["height_median_m"],
            "p90":r["height_p90_m"],"max":r["height_max_m"],
            "quality":r["height_quality"],"flags":r["height_review_flags"],
            "street":r.get("addr:street",""),"number":r.get("addr:housenumber",""),
            "city":r.get("addr:city",""),
            "official_address":r.get("official_address",""),
            "official_count":r.get("official_address_count",""),
            "official_status":r.get("official_address_status",""),
            "levels":r.get("building:levels",""),
            "osm_height":r.get("height",""),"use":r.get("building:use",""),
            "tourism":r.get("tourism",""),"amenity":r.get("amenity",""),
        },ensure_ascii=False,separators=(",",":"))
        # JSON goes inside a single quoted HTML attribute: encode all quotes/apostrophes.
        svg_paths.append(
            f'<path d="{escape(path,quote=True)}" '
            f'fill="{dict((k,c) for k,_,c in BANDS)[r["height_band"]]}" '
            f'data-band="{r["height_band"]}" '
            f'data-info="{escape(attrs,quote=True)}" class="building"><title>'
            f'{escape(r["osm_id"])}</title></path>')
    legend = "\n".join(
        f'<label><input type="checkbox" class="toggle" value="{key}" checked>'
        f'<span class="swatch" style="background:{color}"></span>{escape(title)} '
        f'({counts[key]})</label>' for key,title,color in BANDS
    )
    template = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Malta – BEV-Gebäudehöhen (geschätzt)</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui,Arial;color:#203247;background:#f5f7fa}
header{background:#193b51;color:white;padding:12px 18px}h1{font-size:19px;margin:0 0 5px}
header p{margin:0;color:#d2e5ed}.layout{display:grid;grid-template-columns:310px 1fr;height:calc(100vh - 75px)}
aside{padding:15px;overflow:auto;background:white;border-right:1px solid #d3dce2}
main{min-width:0;position:relative}svg{width:100%;height:100%;touch-action:none;cursor:grab;background:#eaf1f4}
svg.drag{cursor:grabbing}
#boundary{fill:#f4f8f1;stroke:#537b61;stroke-width:2;vector-effect:non-scaling-stroke;pointer-events:none}
.road{fill:none;pointer-events:none;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.road.major{stroke:#d4a370;stroke-width:2.4}
.road.local{stroke:#b7bfc8;stroke-width:1.65}
.road.path{stroke:#9bab9a;stroke-width:1;stroke-dasharray:3 3}
path.building{stroke:#43555c;stroke-width:1;vector-effect:non-scaling-stroke;cursor:pointer}
path.building:hover,path.building.selected{stroke:#092d53;stroke-width:2.5}
label{display:flex;align-items:center;gap:8px;margin:9px 0}.swatch{width:13px;height:13px;display:inline-block;border-radius:3px}
input[type=text]{width:100%;padding:9px;border:1px solid #cad5df;border-radius:6px}
#detail{white-space:pre-wrap;line-height:1.55;padding:10px;background:#f1f5f8;border-radius:6px;min-height:120px}
button{padding:7px 11px;background:#244b67;color:#fff;border:0;border-radius:5px;cursor:pointer}
.tools{position:absolute;right:12px;top:12px;display:flex;gap:6px}small{color:#596f7f}
@media(max-width:740px){.layout{grid-template-columns:1fr;grid-template-rows:255px 1fr;height:calc(100vh - 75px)}
aside{overflow:auto}main{min-height:300px}}
</style></head><body><header><h1>Malta – Geschätzte Gebäudehöhen (BEV ALS)</h1>
<p>__COUNT__ OSM-Gebäude · __ESTIMATED__ mit geschätzter Höhe · Nur Offline-GIS-Indizien – keine Gebäudeklassen</p></header>
<div class="layout"><aside><strong>Höhenklassen: Median DOM − DGM</strong>
<p><small>Filter zeigen rein geometrische Objekthöhen, keine Geschosszahlen oder OIB-Fluchtniveaus.</small></p>
__LEGEND__<hr>
<strong>Kartenebenen</strong>
<label><input type="checkbox" id="show-boundary" checked> Gemeindegrenze</label>
<label><input type="checkbox" id="show-roads" checked> OSM-Straßen und Wege (__ROADCOUNT__)</label>
<hr><label for="search">OSM-ID suchen</label><input type="text" id="search" placeholder="z. B. way/12345">
<p><button id="find">Suchen</button></p><strong>Gebäudedetails</strong><div id="detail">Gebäude auf der Karte anklicken.</div>
<p><small>Farben und Prüfflag-Schwellen sind visuelle Hilfen. Die Hintergrundkarte hat keine Online-Kacheln.</small></p>
</aside><main><svg id="map" xmlns="http://www.w3.org/2000/svg" viewBox="__VIEWBOX__"
preserveAspectRatio="xMidYMid meet">
<path id="boundary" d="__OUTLINE__" fill-rule="evenodd"/>
<g id="roads">__ROADS__</g>
<g id="shapes">__PATHS__</g></svg>
<div class="tools"><button id="plus">+</button><button id="minus">−</button><button id="reset">Zurücksetzen</button></div>
</main></div><script>
(()=>{const map=document.getElementById('map'), paths=[...document.querySelectorAll('.building')];
const initial=map.viewBox.baseVal;const origin=[initial.x,initial.y,initial.width,initial.height];
let selected=null,drag=null;
function moveTo(el){if(selected)selected.classList.remove('selected');selected=el;el.classList.add('selected');
const x=JSON.parse(el.dataset.info);const fmt=(v)=>v===''?'—':v;
document.getElementById('detail').textContent=
'OSM-ID: '+x.id+'\\nAdresse: '+([x.street,x.number].filter(Boolean).join(' ')||'—')+
'\\nOrt: '+fmt(x.city)+
'\\nAmtliche Adresse(n): '+fmt(x.official_address)+
'\\nAdresszuordnung: '+fmt(x.official_status)+
'\\nAnzahl: '+fmt(x.official_count)+
'\\nGebäudetyp: '+fmt(x.building)+'\\nGrundriss: '+x.area+' m²'+
'\\nHöhe Median: '+fmt(x.median)+' m\\nP90: '+fmt(x.p90)+' m\\nMaximum: '+fmt(x.max)+' m'+
'\\nQualität: '+x.quality+'\\nPrüfhinweise: '+fmt(x.flags)+
'\\nOSM-Geschosse: '+fmt(x.levels)+'\\nOSM-Höhe: '+fmt(x.osm_height)+
'\\nOSM-Nutzung: '+fmt(x.use)+'\\nTourismus: '+fmt(x.tourism)+'\\nEinrichtung: '+fmt(x.amenity)+
'\\nGK: unbekannt (noch nicht bewertet)';
}
paths.forEach(p=>p.addEventListener('click',()=>moveTo(p)));
function filters(){const enabled=new Set([...document.querySelectorAll('.toggle:checked')].map(x=>x.value));
paths.forEach(p=>p.style.display=enabled.has(p.dataset.band)?'':'none');}
document.querySelectorAll('.toggle').forEach(x=>x.addEventListener('change',filters));
document.getElementById('show-boundary').addEventListener('change',ev=>{
document.getElementById('boundary').style.display=ev.target.checked?'':'none';});
document.getElementById('show-roads').addEventListener('change',ev=>{
document.getElementById('roads').style.display=ev.target.checked?'':'none';});
document.getElementById('find').onclick=()=>{let query=document.getElementById('search').value.trim().toLowerCase();
if(!query)return;let p=paths.find(el=>JSON.parse(el.dataset.info).id.toLowerCase()===query);
if(!p){document.getElementById('detail').textContent='OSM-ID nicht gefunden.';return;}
p.style.display='';moveTo(p);const bb=p.getBBox(),v=map.viewBox.baseVal;
let ww=Math.max(bb.width*12,120),hh=Math.max(bb.height*12,120);
v.x=bb.x+bb.width/2-ww/2;v.y=bb.y+bb.height/2-hh/2;v.width=ww;v.height=hh;};
document.getElementById('reset').onclick=()=>{const v=map.viewBox.baseVal;
[v.x,v.y,v.width,v.height]=origin;};
function zoom(scale){let v=map.viewBox.baseVal;const cx=v.x+v.width/2,cy=v.y+v.height/2;
v.width*=scale;v.height*=scale;v.x=cx-v.width/2;v.y=cy-v.height/2;}
document.getElementById('plus').onclick=()=>zoom(.7);
document.getElementById('minus').onclick=()=>zoom(1.4);
map.addEventListener('wheel',ev=>{ev.preventDefault();zoom(ev.deltaY<0?.8:1.25);},{passive:false});
map.addEventListener('pointerdown',ev=>{if(ev.target.closest('.building'))return;
drag={x:ev.clientX,y:ev.clientY,view:[map.viewBox.baseVal.x,map.viewBox.baseVal.y]};
map.setPointerCapture(ev.pointerId);map.classList.add('drag');});
map.addEventListener('pointermove',ev=>{if(!drag)return;let v=map.viewBox.baseVal;
v.x=drag.view[0]-(ev.clientX-drag.x)*v.width/map.clientWidth;
v.y=drag.view[1]-(ev.clientY-drag.y)*v.height/map.clientHeight;});
map.addEventListener('pointerup',()=>{drag=null;map.classList.remove('drag');});
map.addEventListener('pointercancel',()=>{drag=null;map.classList.remove('drag');});
})();
</script></body></html>"""
    html = (template.replace("__COUNT__",str(len(rows)))
            .replace("__ESTIMATED__",str(sum(r["height_quality"]=="estimated" for r in rows)))
            .replace("__LEGEND__",legend)
            .replace("__ROADCOUNT__",str(len(roads_markup)))
            .replace("__ROADS__","\n".join(roads_markup))
            .replace("__OUTLINE__",escape(outline_path,quote=True))
            .replace("__VIEWBOX__"," ".join(f"{v:.2f}" for v in vb))
            .replace("__PATHS__","\n".join(svg_paths)))
    map_path=outdir/"gebaeude_als_hoehenkarte.html"
    map_path.write_text(html,encoding="utf-8")
    print(f"[OK] {len(rows)} Gebaeude; {sum(r['height_quality']=='estimated' for r in rows)} Hoehenschaetzungen")
    print("[INFO] Qualitätsflags:",json.dumps(dict(flags),ensure_ascii=False))
    print("[INFO] Hoehenstatistik: Median",stats["median_height_m"],"m, P95",stats["p95_height_m"],"m")
    print(f"[OK] {csv_path}\n[OK] {json_path}\n[OK] {map_path}")
    print("[HINWEIS] Keine GK-Einstufung; geschätzte Objekthoehen und heuristische Pruefflags.")
    if args.open:
        webbrowser.open(map_path.resolve().as_uri())


if __name__=="__main__":
    main()
