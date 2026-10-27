#!/usr/bin/env python3
"""Offline-HTML-Karte der ODB-Wasserentnahmestellen (ohne OSM).

Enthaelt ausschliesslich die lokal importierten ODB-Daten. Keine externen
Kartenkacheln, Netzwerkanfragen oder API-Schluessel.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import webbrowser

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent
COLORS = {
    "Überflurhydrant": "#2573b8",
    "Unterflurhydrant": "#8357bb",
    "Bach mit Stau": "#119b9b",
    "Saugstelle": "#dd852b",
    "Löschwasserteich": "#386fbb",
}
STATUS = {
    "1": ("verwendbar", "#229653"),
    "2": ("eingeschränkt verwendbar", "#d6a324"),
    "3": ("nicht verwendbar", "#d64747"),
}


def polygon_path(geom, project):
    if geom.is_empty:
        return ""
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    else:
        return ""
    result = []
    for poly in polygons:
        for ring in (poly.exterior, *poly.interiors):
            coords = [project(x, y) for x, y in ring.coords]
            result.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in coords) + " Z")
    return " ".join(result)


def road_path(geom, project):
    if geom is None or geom.is_empty:
        return ""
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
    parser.add_argument("--gemeinde", required=True, help="GKZ, z.B. 20619")
    parser.add_argument("--open", action="store_true", help="HTML im Browser oeffnen")
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit():
        parser.error("Bitte eine fuenfstellige Gemeinde-GKZ angeben.")

    base = ROOT / "data" / "processed" / mid
    odb_path = base / "odb_water_sources" / "odb_water_sources.geojson"
    boundary_path = base / "boundary.geojson"
    roads_path = base / "osm" / "roads.geojson"
    for path in (odb_path, boundary_path):
        if not path.is_file():
            parser.error(f"Datei fehlt: {path}")

    data = json.loads(odb_path.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        parser.error("ODB-GeoJSON ist keine FeatureCollection.")
    boundary = gpd.read_file(boundary_path)
    if boundary.empty or boundary.crs is None:
        parser.error("Amtliche Gemeindegrenze fehlt oder hat kein CRS.")
    bounds = boundary.to_crs(epsg=31287)
    merged = bounds.geometry.union_all()
    x0, y0, x1, y1 = merged.bounds

    width, height = 1100, 800
    padx = max(300, (x1-x0)*0.035)
    pady = max(300, (y1-y0)*0.035)
    x0, x1 = x0-padx, x1+padx
    y0, y1 = y0-pady, y1+pady
    # Beide Achsen im selben Massstab darstellen.
    scale = max((x1-x0)/width, (y1-y0)/height)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    x0, x1 = cx-scale*width/2, cx+scale*width/2
    y0, y1 = cy-scale*height/2, cy+scale*height/2

    def project(x, y):
        return (x-x0)/scale, (y1-y)/scale

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:31287", always_xy=True)
    outline = polygon_path(merged, project)
    road_drawings = []
    if roads_path.is_file():
        roads = gpd.read_file(roads_path)
        if roads.crs is None:
            raise ValueError("OSM-Strassen ohne Koordinatensystem")
        for _, road in roads.to_crs(31287).iterrows():
            road_svg = road_path(road.geometry, project)
            if not road_svg:
                continue
            kind = str(road.get("highway") or "")
            name = str(road.get("name") or kind)
            road_drawings.append(
                f'<path class="road {road_class(kind)}" d="{escape(road_svg, quote=True)}">'
                f'<title>{escape(name)}</title></path>'
            )
    markers = []
    type_counts, status_counts = Counter(), Counter()
    for pos, f in enumerate(data.get("features", []), 1):
        props = f.get("properties") or {}
        geom = shape(f.get("geometry"))
        if not isinstance(geom, Point) or geom.is_empty:
            raise ValueError(f"ODB-Feature {pos} hat keine Punktgeometrie")
        typ = str(props.get("type", "unbekannt"))
        status = str(props.get("status_raw", ""))
        ident = str(props.get("odb_id", pos))
        name = str(props.get("name") or "").strip()
        xm, ym = transformer.transform(geom.x, geom.y)
        x, y = project(xm, ym)
        label, status_color = STATUS.get(status, ("Status ungeklärt", "#818892"))
        type_color = COLORS.get(typ, "#66717f")
        type_counts[typ] += 1
        status_counts[label] += 1
        tip = escape(f"{name or typ} | {typ} | {label} | ODB {ident}")
        markers.append(
            f'<g class="marker" data-type="{escape(typ, quote=True)}" '
            f'data-status="{escape(status, quote=True)}" data-id="{escape(ident, quote=True)}" '
            f'data-name="{escape(name, quote=True)}">'
            f'<title>{tip}</title>'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="{type_color}" '
            f'stroke="{status_color}" stroke-width="2"/>'
            f'</g>'
        )

    toggles = "".join(
        f'<label><input type="checkbox" class="filter-type" value="{escape(typ, quote=True)}" checked> '
        f'<span class="swatch" style="background:{COLORS.get(typ, "#66717f")}"></span>'
        f'{escape(typ)} ({count})</label>'
        for typ, count in sorted(type_counts.items())
    )
    status_toggles = "".join(
        f'<label><input type="checkbox" class="filter-status" value="{status}" checked>'
        f'<span class="ring" style="border-color:{color}"></span>'
        f'{escape(name)} ({sum(1 for f in data["features"] if str((f.get("properties") or {}).get("status_raw", "")) == status)})</label>'
        for status, (name, color) in STATUS.items()
    )
    output = ROOT / "reports" / mid / "odb_wasserentnahmestellen.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    document = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ODB-Wasserentnahmestellen Gemeinde __GKZ__</title>
<style>
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;color:#233044;background:#f4f6f9}
body{max-width:1400px;margin:0 auto;padding:18px}
h1{font-size:1.45rem;margin:0 0 5px}p{margin:5px 0 14px;color:#576476}
main{display:grid;grid-template-columns:minmax(230px,285px) minmax(0,1fr);gap:14px}
aside,.mapbox{background:white;border:1px solid #dce3eb;border-radius:12px;padding:14px}
aside h2{font-size:1rem;margin:12px 0 8px}label{display:flex;align-items:center;gap:7px;margin:9px 0;font-size:.88rem}
.swatch{height:12px;width:12px;border-radius:3px;display:inline-block}
.ring{height:11px;width:11px;border-radius:50%;border:3px solid;display:inline-block}
input[type=search]{width:100%;box-sizing:border-box;padding:9px;border:1px solid #c8d1de;border-radius:8px}
.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:9px}
button{border:1px solid #c8d1de;border-radius:7px;background:#fff;padding:6px 12px;cursor:pointer}
#map{width:100%;height:min(74vh,750px);min-height:390px;background:#f7fafc;border:1px solid #edf1f5;border-radius:8px;touch-action:none}
.road{fill:none;pointer-events:none;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.road.major{stroke:#d4a370;stroke-width:2.4}
.road.local{stroke:#b7bfc8;stroke-width:1.65}
.road.path{stroke:#9bab9a;stroke-width:1;stroke-dasharray:3 3}
.marker{cursor:crosshair}.marker circle{vector-effect:non-scaling-stroke}
.marker:hover circle{stroke-width:3}
.marker.selected circle{stroke:#ed3434;stroke-width:3.5}
small{color:#596b7e}
@media(max-width:770px){main{grid-template-columns:1fr}#map{height:55vh}}
</style></head><body>
<h1>Wasserentnahmestellen - Gemeinde __GKZ__</h1>
<p>Kärntner Objektdatenbank (ODB) · __COUNT__ Objekte · amtliche Gemeindegrenze · ausschließlich lokale ODB-Quellen; OSM-Straßen und Wege nur als Hintergrund</p>
<main><aside>
<h2>Kategorien</h2>__TOGGLES__
<h2>Status</h2>__STATUSES__
<h2>Kartenebenen</h2>
<label><input type="checkbox" id="show-roads" checked> OSM-Straßen und Wege (__ROADCOUNT__)</label>
<h2>Objektsuche</h2><input type="search" id="search" placeholder="Titel oder ODB-ID filtern">
<p><strong id="visible">__COUNT__</strong> sichtbare Entnahmestellen</p>
<small>Farbe innen = Quellentyp; Umrandung = Status. Punkt mit der Maus berühren oder anklicken für Titel und Details. Status ist kein Nachweis der Entnahmeleistung.</small>
</aside><div class="mapbox"><div class="controls">
<button id="zoom-in" type="button">+</button><button id="zoom-out" type="button">−</button>
<button id="reset" type="button">Gesamtansicht</button>
<small>Mausrad: Zoom · Ziehen: Verschieben</small></div>
<svg id="map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 800" role="img" aria-label="Gemeindegrenze und ODB-Wasserentnahmestellen">
<rect width="1100" height="800" fill="#f7fafc"/>
<path d="__OUTLINE__" fill="#e6efe8" fill-rule="evenodd" stroke="#416a52" stroke-width="1.8"/>
<g id="roads">__ROADS__</g>
<g id="markers">__MARKERS__</g>
</svg><p id="detail">ODB-Punkt anklicken für ID, Typ und Status.</p></div></main>
<script>
(() => {
 const svg=document.getElementById('map'), markers=[...document.querySelectorAll('.marker')];
 const search=document.getElementById('search'), visible=document.getElementById('visible');
 const full={x:0,y:0,w:1100,h:800}; let view={...full},drag=null;
 function resizeMarkers(){
   // Match the ODB distance map: marker diameter remains stable in screen pixels.
   const box=svg.getBoundingClientRect();
   if(!box.width)return;
   const radius=5.5*view.w/box.width;
   for(const circle of svg.querySelectorAll('.marker circle'))circle.setAttribute('r',String(radius));
 }
 const setView=()=>{svg.setAttribute('viewBox',[view.x,view.y,view.w,view.h].join(' '));resizeMarkers()};
 const selected=cls=>new Set([...document.querySelectorAll(cls)].filter(c=>c.checked).map(c=>c.value));
 function update(){
   const types=selected('.filter-type'),statuses=selected('.filter-status'),term=search.value.trim().toLowerCase();
   let shown=0;
   for(const m of markers){
     const ok=types.has(m.dataset.type)&&statuses.has(m.dataset.status)&&(m.dataset.id.toLowerCase().includes(term)||m.dataset.name.toLowerCase().includes(term));
     m.style.display=ok?'':'none';if(ok)shown++;
   }
   visible.textContent=shown;
   document.getElementById('roads').style.display=
     document.getElementById('show-roads').checked?'':'none';
 }
 function zoom(factor,mouseX=view.x+view.w/2,mouseY=view.y+view.h/2){
   const w=Math.max(30,Math.min(full.w*10,view.w*factor)), h=w*full.h/full.w;
   view={x:mouseX-(mouseX-view.x)*w/view.w,y:mouseY-(mouseY-view.y)*h/view.h,w,h};setView();
 }
 function svgPoint(ev){
   const p=svg.createSVGPoint();p.x=ev.clientX;p.y=ev.clientY;
   const matrix=svg.getScreenCTM();return matrix?p.matrixTransform(matrix.inverse()):null;
 }
 document.querySelectorAll('input[type=checkbox]').forEach(x=>x.addEventListener('change',update));
 search.addEventListener('input',update);
 document.getElementById('zoom-in').onclick=()=>zoom(.7);
 document.getElementById('zoom-out').onclick=()=>zoom(1.4);
 document.getElementById('reset').onclick=()=>{view={...full};setView()};
 svg.addEventListener('wheel',ev=>{ev.preventDefault();const p=svgPoint(ev);if(p)zoom(ev.deltaY<0?.85:1.18,p.x,p.y)},{passive:false});
 svg.addEventListener('pointerdown',ev=>{if(ev.target.closest('.marker'))return;drag={x:ev.clientX,y:ev.clientY,v:{...view}};svg.setPointerCapture(ev.pointerId)});
 svg.addEventListener('pointermove',ev=>{if(!drag)return;const b=svg.getBoundingClientRect();view.x=drag.v.x-(ev.clientX-drag.x)*drag.v.w/b.width;view.y=drag.v.y-(ev.clientY-drag.y)*drag.v.h/b.height;setView()});
 svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);
 let active=null;
 function describe(m){
   if(active)active.classList.remove('selected');
   active=m;m.classList.add('selected');
   const label=({'1':'verwendbar','2':'eingeschränkt verwendbar','3':'nicht verwendbar'})[m.dataset.status]||'unbekannt';
   document.getElementById('detail').textContent=(m.dataset.name||'Ohne Titel')+' | ODB-ID: '+m.dataset.id+' | '+m.dataset.type+' | '+label;
 }
 for(const m of markers){
   m.addEventListener('mouseenter',()=>describe(m));
   m.addEventListener('focus',()=>describe(m));
   m.addEventListener('click',()=>describe(m));
 }
 update();setView();window.addEventListener('resize',resizeMarkers);
})();
</script></body></html>"""
    document = (document.replace("__GKZ__", escape(mid)).replace("__COUNT__", str(len(markers)))
                .replace("__TOGGLES__", toggles).replace("__STATUSES__", status_toggles)
                .replace("__OUTLINE__", outline).replace("__MARKERS__", "\n".join(markers))
                .replace("__ROADCOUNT__", str(len(road_drawings)))
                .replace("__ROADS__", "\n".join(road_drawings)))
    output.write_text(document, encoding="utf-8")
    print(f"[OK] ODB-Objekte: {len(markers)}")
    print("Typen:", dict(sorted(type_counts.items())))
    print("Status:", dict(sorted(status_counts.items())))
    print(f"[INFO] OSM-Strassen/Wege: {len(road_drawings)} (Hintergrund {'aktiv' if roads_path.is_file() else 'fehlt'})")
    print(f"[OK] Offline-Karte: {output}")
    print("[HINWEIS] Lokale ODB-Daten nicht oeffentlich weitergeben.")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
