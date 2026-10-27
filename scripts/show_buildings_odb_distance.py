#!/usr/bin/env python3
"""Offlinekarte: alle OSM-Gebaeude nach Abstand zur naechsten verwendbaren ODB-Quelle."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from html import escape
import json
from pathlib import Path
import webbrowser

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import nearest_points

ROOT = Path(__file__).resolve().parent.parent
BANDS = [
    ("bis_100m", "Bis 100 m", "#248a54"),
    ("bis_250m", "100–250 m", "#86bd51"),
    ("bis_500m", "250–500 m", "#e5c94b"),
    ("bis_1000m", "500–1.000 m", "#ed9642"),
    ("ueber_1000m", "Über 1.000 m", "#c74d49"),
    ("keine_verwendbare_Quelle", "Keine verwendbare Quelle", "#8a8f9a"),
]
COLORS = {key: color for key, _, color in BANDS}
STATUS = {"1": "verwendbar", "2": "eingeschränkt verwendbar", "3": "nicht verwendbar"}


def polygon_path(geom, project):
    polygons = [geom] if geom.geom_type == "Polygon" else (
        geom.geoms if geom.geom_type == "MultiPolygon" else []
    )
    parts = []
    for polygon in polygons:
        for ring in (polygon.exterior, *polygon.interiors):
            parts.append("M " + " L ".join(
                f"{project(x, y)[0]:.2f},{project(x, y)[1]:.2f}"
                for x, y in ring.coords
            ) + " Z")
    return " ".join(parts)


def road_path(geom, project):
    """Draw only genuine linear geometry, never interpret a path as routing."""
    if geom.geom_type == "LineString":
        lines = [geom]
    elif geom.geom_type == "MultiLineString":
        lines = geom.geoms
    else:
        return ""
    return " ".join(
        "M " + " L ".join(f"{project(x, y)[0]:.2f},{project(x, y)[1]:.2f}" for x, y in line.coords)
        for line in lines if len(line.coords) >= 2
    )


def road_class(kind):
    if kind in ("motorway", "trunk", "primary", "secondary", "tertiary",
                "motorway_link", "trunk_link", "primary_link", "secondary_link",
                "tertiary_link"):
        return "major"
    if kind in ("residential", "unclassified", "living_street", "service", "road"):
        return "local"
    return "path"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Fuenfstellige Gemeindenummer, z. B. 20619")
    parser.add_argument("--open", action="store_true", help="HTML nach Erstellung im Browser oeffnen")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (mid.isdigit() and len(mid) == 5 and mid.startswith("2")):
        parser.error("Ungueltige Kaerntner GKZ")
    base = ROOT / "data" / "processed" / mid
    building_file = base / "osm" / "buildings.geojson"
    odb_file = base / "odb_water_sources" / "odb_water_sources.geojson"
    boundary_file = base / "boundary.geojson"
    distances_file = ROOT / "reports" / mid / "gebaeude_odb_abstaende.csv"
    roads_file = base / "osm" / "roads.geojson"
    for path in (building_file, odb_file, boundary_file, distances_file):
        if not path.is_file():
            parser.error(f"Datei fehlt: {path}. Zuerst die jeweiligen Importe und die Abstandsanalyse ausfuehren.")

    buildings = gpd.read_file(building_file)
    boundary = gpd.read_file(boundary_file)
    if any(f.crs is None or f.empty for f in (buildings, boundary)):
        raise ValueError("Gebaeude/Gemeindegrenze leer oder ohne Koordinatensystem")
    if "osm_id" not in buildings or "building" not in buildings:
        raise ValueError("OSM-Gebaeudedaten ohne osm_id / building")
    with distances_file.open(encoding="utf-8-sig", newline="") as stream:
        distance_rows = list(csv.DictReader(stream, delimiter=";"))
    if len(distance_rows) != len({r["building_osm_id"] for r in distance_rows}):
        raise ValueError("Doppelte Gebaeude-IDs in der Abstandstabelle")
    distances = {r["building_osm_id"]: r for r in distance_rows}
    buildings = buildings.to_crs(31287)
    border = boundary.to_crs(31287).geometry.union_all()
    buildings = buildings.loc[buildings.geometry.intersects(border)].copy()
    if buildings["osm_id"].astype(str).duplicated().any():
        raise ValueError("Doppelte OSM-Gebaeude-IDs")
    building_ids = set(buildings["osm_id"].astype(str))
    if building_ids != set(distances):
        raise ValueError("Abstandstabelle und Gebaeudeinventar unterscheiden sich! "
                         "Bitte scripts/analyze_buildings_odb_distance.py erneut ausfuehren.")
    x0, y0, x1, y1 = border.bounds
    width, height = 1150, 800
    pad = max(250, (x1-x0)*.035, (y1-y0)*.035)
    x0, y0, x1, y1 = x0-pad, y0-pad, x1+pad, y1+pad
    scale = max((x1-x0)/width, (y1-y0)/height)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    x0, x1 = cx-scale*width/2, cx+scale*width/2
    y0, y1 = cy-scale*height/2, cy+scale*height/2

    def project(x, y):
        return ((x-x0)/scale, (y1-y)/scale)

    road_drawings = []
    if roads_file.is_file():
        roads = gpd.read_file(roads_file)
        if roads.crs is None:
            raise ValueError("OSM-Strassen ohne Koordinatensystem")
        roads = roads.to_crs(31287)
        for _, road in roads.iterrows():
            kind = str(road.get("highway") or "")
            geom = road.geometry
            if geom is None or geom.is_empty:
                continue
            road_svg = road_path(geom, project)
            if road_svg:
                road_drawings.append(
                    f'<path class="road {road_class(kind)}" d="{road_svg}">'
                    f'<title>{escape(str(road.get("name") or kind))}</title></path>'
                )

    # Resolve source coordinates before rendering buildings. Use the actual
    # shortest building-footprint-to-source segment, not a centroid line.
    data = json.loads(odb_file.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("ODB-Datensatz ist keine FeatureCollection")
    transformer = Transformer.from_crs(4326, 31287, always_xy=True)
    source_points = {}
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        oid = str(props.get("odb_id") or "")
        point = shape(feature["geometry"])
        if not isinstance(point, Point) or point.is_empty:
            raise ValueError(f"Ungueltige ODB-Punktgeometrie: {oid}")
        if not oid or oid in source_points:
            raise ValueError(f"Fehlende oder doppelte ODB-ID: {oid!r}")
        source_points[oid] = (
            Point(*transformer.transform(point.x, point.y)),
            str(props.get("status_raw") or ""),
        )

    summary = Counter()
    drawings = []
    for _, building in buildings.iterrows():
        osm_id = str(building["osm_id"])
        geom = building.geometry
        if geom is None or geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Ungueltige Gebaeudegeometrie: {osm_id}")
        entry = distances[osm_id]
        key = entry["distance_band"]
        if key not in COLORS:
            raise ValueError(f"Unbekannte Abstandsklasse: {key}")
        value = entry["distance_usable_m"]
        value_label = f"{float(value):,.1f} m".replace(",", "X").replace(".", ",").replace("X", ".") if value else "kein Wert"
        typ = str(building["building"] or "")
        label = f"{osm_id} | {typ} | {value_label}"
        source_id = entry["nearest_usable_odb_id"]
        segment_attrs = ""
        if source_id:
            if source_id not in source_points or source_points[source_id][1] != "1":
                raise ValueError(f"Verwendbare ODB-Quelle in Abstandstabelle nicht gefunden: {source_id}")
            source_point = source_points[source_id][0]
            foot_point, end_point = nearest_points(geom, source_point)
            start_x, start_y = project(foot_point.x, foot_point.y)
            end_x, end_y = project(end_point.x, end_point.y)
            segment_attrs = (f' data-line-x1="{start_x:.4f}" data-line-y1="{start_y:.4f}"'
                             f' data-line-x2="{end_x:.4f}" data-line-y2="{end_y:.4f}"')
        drawings.append(
            f'<path class="building" d="{polygon_path(geom, project)}" fill="{COLORS[key]}" '
            f'fill-rule="evenodd" data-band="{escape(key, quote=True)}" '
            f'data-id="{escape(osm_id, quote=True)}" data-type="{escape(typ, quote=True)}" '
            f'data-distance="{escape(value_label, quote=True)}" '
            f'data-source="{escape(entry["nearest_usable_odb_id"], quote=True)}" '
            f'data-source-type="{escape(entry["nearest_usable_odb_type"], quote=True)}"'
            f'{segment_attrs}>'
            f'<title>{escape(label)}</title></path>'
        )
        summary[key] += 1

    markers = []
    for idx, feature in enumerate(data.get("features", []), 1):
        geom = shape(feature["geometry"])
        if not isinstance(geom, Point) or geom.is_empty:
            raise ValueError(f"ODB-Punkt {idx} ohne gueltige Punktgeometrie")
        props = feature.get("properties") or {}
        ident = str(props.get("odb_id") or idx)
        name = str(props.get("name") or "")
        typ = str(props.get("type") or "Unbekannt")
        status = str(props.get("status_raw") or "")
        px, py = project(*transformer.transform(geom.x, geom.y))
        markers.append(
            f'<g class="source-marker" data-id="{escape(ident, quote=True)}" '
            f'data-name="{escape(name, quote=True)}" data-type="{escape(typ, quote=True)}" '
            f'data-status="{escape(status, quote=True)}">'
            f'<title>{escape(name or typ)} | {escape(STATUS.get(status, "Status unbekannt"))}</title>'
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="5.5" fill="{"#278a59" if status == "1" else "#e1a13d" if status == "2" else "#999"}" '
            f'stroke="#132f48" stroke-width="1.6"/></g>'
        )
    toggles = "".join(
        f'<label class="filterline"><input class="band-toggle" type="checkbox" value="{escape(key, quote=True)}" checked>'
        f'<span class="swatch" style="background:{color}"></span>{escape(title)} <strong>{summary[key]}</strong></label>'
        for key, title, color in BANDS if summary[key]
    )
    template = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gebäude / ODB-Luftlinienabstände – __MID__</title>
<style>
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;color:#1e3349;background:#f3f6fa}
body{margin:0 auto;padding:20px;max-width:1600px}
h1{font-size:1.5rem;margin:0 0 6px}h2{font-size:1rem;margin:14px 0 9px}
p{color:#52657b;line-height:1.42}main{display:grid;grid-template-columns:270px minmax(0,1fr);gap:16px}
aside,.map-panel{background:white;border:1px solid #dce4ed;border-radius:12px;padding:16px}
.filterline{display:flex;align-items:center;gap:8px;margin:12px 0;font-size:.88rem}
.filterline strong{margin-left:auto}.swatch{width:15px;height:15px;display:inline-block;border-radius:3px}
input[type=search]{box-sizing:border-box;width:100%;padding:9px;border:1px solid #b9c9d8;border-radius:7px}
button{border:1px solid #bdcbd9;border-radius:7px;background:white;padding:7px 12px;cursor:pointer}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:10px}
#map{display:block;width:100%;height:min(74vh,820px);min-height:420px;touch-action:none;border-radius:8px;background:#f9fbfd}
.road{fill:none;pointer-events:none;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.road.major{stroke:#d4a370;stroke-width:2.4}
.road.local{stroke:#b7bfc8;stroke-width:1.65}
.road.path{stroke:#9bab9a;stroke-width:1;stroke-dasharray:3 3}
.building{stroke:#33485a;stroke-width:.32;cursor:pointer;vector-effect:non-scaling-stroke}
.building:hover{stroke:#081a2a;stroke-width:2;stroke-opacity:1}
.source-marker{cursor:pointer}.source-marker circle{vector-effect:non-scaling-stroke}.source-marker:hover circle{stroke-width:3}
.source-marker.selected circle{stroke:#ed3434;stroke-width:3.5}
#selected-link{pointer-events:none;stroke:#a51d36;stroke-width:2.6;stroke-dasharray:8 5;vector-effect:non-scaling-stroke}
.building.selected{stroke:#071e36;stroke-width:2.5}
#detail{padding:10px;background:#edf3f9;border-radius:8px;min-height:25px;font-size:.91rem;overflow-wrap:anywhere}
.note{font-size:.79rem;color:#627286}.credit{font-size:.78rem;color:#435c77}
@media(max-width:850px){main{grid-template-columns:1fr}#map{height:62vh}}
</style></head><body>
<h1>Gebäudeabstände zu ODB-Wasserentnahmestellen – Gemeinde __MID__</h1>
<p>__NUM__ OSM-Gebäude · __SOURCES__ ODB-Entnahmestellen · Luftlinie von der Gebäudegrundfläche zur nächsten ODB-Quelle mit Status 1.</p>
<main><aside><h2>Abstandsklassen</h2>__TOGGLES__
<h2>Gebäude suchen</h2>
<input id="search" type="search" placeholder="OSM-ID oder Gebäudetyp">
<p><strong id="visible">__NUM__</strong> sichtbare Gebäude</p>
<label class="filterline"><input type="checkbox" id="show-sources" checked> ODB-Wasserentnahmestellen zeigen</label>
<label class="filterline"><input type="checkbox" id="show-roads" checked> OSM-Straßen und Wege (__ROADCOUNT__) anzeigen</label>
<p class="note">ODB-Punkte: grün = verwendbar, orange = eingeschränkt verwendbar, grau = nicht verwendbar / unbekannt.</p>
<p class="note">Die Klassen beschreiben geometrische Luftlinienabstände; sie sind keine normativen Versorgungsgrenzen. Keine Aussage über Entnahmeleistung, Hydraulik, Schlauchwege oder Erreichbarkeit.</p>
</aside><section class="map-panel">
<div class="controls"><button id="plus">+</button><button id="minus">−</button><button id="reset">Gesamtansicht</button>
<span class="note">Mausrad: Zoom · Ziehen: verschieben · Gebäude anklicken: kürzeste Luftlinie zur ODB-Quelle</span></div>
<svg id="map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 800" role="img" aria-label="Gebäude nach Luftlinienabstand und ODB-Wasserentnahmestellen">
<rect width="1150" height="800" fill="#f7fafc"/>
<path d="__OUTLINE__" fill="#f0f5f1" stroke="#48775f" stroke-width="1.7" fill-rule="evenodd"/>
<g id="roads">__ROADS__</g><g id="buildings">__BUILDINGS__</g><line id="selected-link" style="display:none"/><g id="sources">__MARKERS__</g></svg>
<div id="detail" aria-live="polite">Gebäude oder ODB-Punkt anklicken, um Details anzuzeigen.</div>
<p class="credit">Gebäudegrundflächen: © OpenStreetMap-Mitwirkende · ODbL 1.0 ·
<a href="https://www.openstreetmap.org/copyright">openstreetmap.org/copyright</a>.<br>
Gemeindegrenze: Statistik Austria, Gebietsstand 01.01.2026, CC BY 4.0.<br>
Wasserentnahmestellen: Kärntner Objektdatenbank – lokale, berechtigte Verwendung; nicht zur öffentlichen Weitergabe freigegeben.</p>
</section></main>
<script>
(()=>{
const svg=document.getElementById('map'),bs=[...document.querySelectorAll('.building')],ms=[...document.querySelectorAll('.source-marker')];
const search=document.getElementById('search'),counter=document.getElementById('visible'),detail=document.getElementById('detail');
const full={x:0,y:0,w:1150,h:800};let v={...full},drag=null;
function resizeMarkers(){
 // SVG circle radii are in map coordinates. Convert a fixed screen-pixel size
 // into viewBox units, so zooming enlarges buildings but not ODB markers.
 const rect=svg.getBoundingClientRect();
 if(!rect.width)return;
 const r=5.5*v.w/rect.width;
 for(const circle of svg.querySelectorAll('.source-marker circle')){
   circle.setAttribute('r',String(r));
 }
}
function setV(){svg.setAttribute('viewBox',[v.x,v.y,v.w,v.h].join(' '));resizeMarkers()}
function update(){const bands=new Set([...document.querySelectorAll('.band-toggle:checked')].map(i=>i.value));const q=search.value.trim().toLocaleLowerCase();let n=0;
 for(const b of bs){const ok=bands.has(b.dataset.band)&&(b.dataset.id.toLocaleLowerCase().includes(q)||b.dataset.type.toLocaleLowerCase().includes(q));b.style.display=ok?'':'none';if(ok)n++}
 counter.textContent=n;document.getElementById('sources').style.display=document.getElementById('show-sources').checked?'':'none';
 document.getElementById('roads').style.display=document.getElementById('show-roads').checked?'':'none';
}
function point(ev){const m=svg.getScreenCTM();if(!m)return null;const p=svg.createSVGPoint();p.x=ev.clientX;p.y=ev.clientY;return p.matrixTransform(m.inverse())}
function zoom(f,px=v.x+v.w/2,py=v.y+v.h/2){const w=Math.max(2,Math.min(full.w*10,v.w*f));const h=w*full.h/full.w;v={x:px-(px-v.x)*w/v.w,y:py-(py-v.y)*h/v.h,w,h};setV()}
document.querySelectorAll('.band-toggle').forEach(i=>i.addEventListener('change',update));search.addEventListener('input',update);document.getElementById('show-sources').addEventListener('change',update);document.getElementById('show-roads').addEventListener('change',update);
document.getElementById('plus').onclick=()=>zoom(.65);document.getElementById('minus').onclick=()=>zoom(1.5);document.getElementById('reset').onclick=()=>{v={...full};setV()};
svg.addEventListener('wheel',ev=>{ev.preventDefault();const p=point(ev);if(p)zoom(ev.deltaY<0?.8:1.25,p.x,p.y)},{passive:false});
svg.addEventListener('pointerdown',ev=>{if(ev.target.closest('.building,.source-marker'))return;drag={x:ev.clientX,y:ev.clientY,v:{...v}};svg.setPointerCapture(ev.pointerId)});
svg.addEventListener('pointermove',ev=>{if(!drag)return;const b=svg.getBoundingClientRect();v.x=drag.v.x-(ev.clientX-drag.x)*drag.v.w/b.width;v.y=drag.v.y-(ev.clientY-drag.y)*drag.v.h/b.height;setV()});
svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);
const selectedLink=document.getElementById('selected-link');
function clearSelection(){
 bs.forEach(b=>b.classList.remove('selected'));
 ms.forEach(m=>m.classList.remove('selected'));
 selectedLink.style.display='none';
}
bs.forEach(b=>b.addEventListener('click',()=>{
 clearSelection();b.classList.add('selected');
 const source=ms.find(m=>m.dataset.id===b.dataset.source && m.dataset.status==='1');
 if(source && b.dataset.lineX1){
   source.classList.add('selected');
   selectedLink.setAttribute('x1',b.dataset.lineX1);
   selectedLink.setAttribute('y1',b.dataset.lineY1);
   selectedLink.setAttribute('x2',b.dataset.lineX2);
   selectedLink.setAttribute('y2',b.dataset.lineY2);
   selectedLink.style.display='';
 }
 detail.textContent='OSM-Gebäude: '+b.dataset.id+' | Typ: '+b.dataset.type+
  ' | Kürzeste Luftlinie ab Gebäudegrundfläche: '+b.dataset.distance+
  ' | Nächste verwendbare ODB-Quelle: '+(b.dataset.source||'keine')+
  ' ('+(b.dataset.sourceType||'–')+')'+(source?' | Quelle rot markiert':'');
}));
ms.forEach(m=>m.addEventListener('click',()=>{
 clearSelection();m.classList.add('selected');
 detail.textContent='ODB: '+m.dataset.id+' | '+(m.dataset.name||'ohne Titel')+' | '+m.dataset.type+
  ' | Status: '+({'1':'verwendbar','2':'eingeschränkt verwendbar','3':'nicht verwendbar'}[m.dataset.status]||'unbekannt');
}));
update();setV();window.addEventListener('resize',resizeMarkers);
})();
</script></body></html>"""
    html = (template.replace("__MID__", escape(mid))
            .replace("__NUM__", str(len(drawings)))
            .replace("__SOURCES__", str(len(markers)))
            .replace("__TOGGLES__", toggles)
            .replace("__ROADCOUNT__", str(len(road_drawings)))
            .replace("__ROADS__", "\n".join(road_drawings))
            .replace("__OUTLINE__", polygon_path(border, project))
            .replace("__BUILDINGS__", "\n".join(drawings))
            .replace("__MARKERS__", "\n".join(markers)))
    out = ROOT / "reports" / mid / "gebaeude_odb_abstandskarte.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Gemeinde {mid}: {len(drawings)} Gebaeude, {len(markers)} ODB-Quellen")
    print(f"[INFO] OSM-Strassen/Wege: {len(road_drawings)} (Hintergrund {'aktiv' if roads_file.is_file() else 'fehlt, bitte importieren'})")
    print("[INFO] Klassen:", json.dumps(dict(summary), ensure_ascii=False))
    print(f"[OK] {out}")
    print("[HINWEIS] Die HTML-Karte enthaelt lokale Fachdaten und darf nicht oeffentlich eingecheckt werden.")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
