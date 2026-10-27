#!/usr/bin/env python3
"""Interaktive Offline-Pruefkarte: BEV-Gebaeudepunkte ohne sicheren OSM-Innen-Treffer.

Verwendet den bereits berechneten BEV/OSM-Abgleich; ändert dessen Bewertungen nicht.
Keine externen Kartenkacheln, keine Online-Abfrage, keine automatische Korrektur.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from html import escape
import json
from pathlib import Path
import webbrowser

import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ("near_review", "unmatched", "multiple_or_boundary")
COLORS = {"near_review":"#e7a12e","unmatched":"#d64e50","multiple_or_boundary":"#9352bd"}


def polygon_path(geom):
    polys = [geom] if geom.geom_type == "Polygon" else (
        list(geom.geoms) if geom.geom_type == "MultiPolygon" else [])
    parts=[]
    for poly in polys:
        for ring in (poly.exterior,*poly.interiors):
            parts.append("M "+" L ".join(f"{x:.2f},{-y:.2f}" for x,y in ring.coords)+" Z")
    return " ".join(parts)


def line_path(geom):
    if geom is None or geom.is_empty:
        return ""
    lines=[geom] if geom.geom_type=="LineString" else (
        list(geom.geoms) if geom.geom_type=="MultiLineString" else [])
    return " ".join("M "+" L ".join(f"{x:.2f},{-y:.2f}" for x,y in line.coords)
                    for line in lines if len(line.coords)>=2)


def road_class(value):
    if value in {"motorway","trunk","primary","secondary","tertiary","motorway_link",
                 "trunk_link","primary_link","secondary_link","tertiary_link"}:
        return "major"
    if value in {"residential","unclassified","living_street","service","road"}:
        return "local"
    return "path"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gemeinde",default="20619")
    p.add_argument("--open",action="store_true",help="Karte nach Erzeugung im Browser oeffnen")
    args=p.parse_args()
    mid=args.gemeinde
    if not(len(mid)==5 and mid.isdecimal() and mid.startswith("2")):
        p.error("Bitte gueltige Kaerntner GKZ angeben")
    base=ROOT/"data"/"processed"/mid
    report=ROOT/"reports"/mid/"addresses"
    match_path=report/"bev_gebaeudepunkte_osm_zuordnung.csv"
    osm_path=base/"osm"/"buildings.geojson"
    bev_path=base/"bev_addresses"/"bev_gebaeudepunkte.geojson"
    boundary_path=base/"boundary.geojson"
    roads_path=base/"osm"/"roads.geojson"
    summary_path=report/"bev_osm_zuordnung_summary.json"
    for f in (match_path,osm_path,bev_path,boundary_path,summary_path):
        if not f.is_file():
            p.error(f"Eingabe fehlt: {f}. Zuerst join_bev_building_points_osm.py ausfuehren.")
    with match_path.open(encoding="utf-8-sig",newline="") as f:
        matches=list(csv.DictReader(f,delimiter=";"))
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("gemeinde")!=mid or len(matches)!=summary.get("bev_building_points"):
        raise ValueError("Zuordnungs-CSV und Summary widersprechen sich")
    lookup={}
    for row in matches:
        key=row["building_subcode"].strip()
        if not key or key in lookup:
            raise ValueError(f"Fehlender/doppelter BEV-Subcode: {key}")
        lookup[key]=row
    bev=gpd.read_file(bev_path)
    osm=gpd.read_file(osm_path)
    boundary=gpd.read_file(boundary_path)
    if any(f.empty or f.crs is None for f in (bev,osm,boundary)):
        raise ValueError("GIS-Daten leer oder CRS fehlt")
    bev=bev.to_crs(31287)
    osm=osm.to_crs(31287)
    border=boundary.to_crs(31287).geometry.union_all()
    if len(bev)!=len(lookup) or set(bev["building_subcode"].astype(str))!=set(lookup):
        raise ValueError("BEV-Gebaeudepunkte und Zuordnung passen nicht zusammen: Abgleich erneut ausfuehren")
    expected={k:v for k,v in summary["status_counts"].items() if k in REVIEW}
    actual=Counter(row["status"] for row in matches if row["status"] in REVIEW)
    if dict(expected)!=dict(actual):
        raise ValueError("Statuszahlen stimmen nicht mit Zuordnungs-Summary ueberein")
    if not any(actual.values()):
        print("[INFO] Keine offenen BEV/OSM-Prueffaelle, Karte enthaelt keine Markierungen")
    shapes=[]
    for _,r in osm.iterrows():
        geom=r.geometry
        if geom is None or geom.is_empty:
            continue
        d=polygon_path(geom)
        if d:
            shapes.append(
                f'<path class="building" data-id="{escape(str(r["osm_id"]),quote=True)}" '
                f'd="{escape(d,quote=True)}"><title>{escape(str(r["osm_id"]))}</title></path>')
    road_shapes=[]
    if roads_path.is_file():
        roads=gpd.read_file(roads_path)
        if roads.crs is None:
            raise ValueError("Straßendaten ohne CRS")
        for _,r in roads.to_crs(31287).iterrows():
            d=line_path(r.geometry)
            if d:
                road_shapes.append(
                    f'<path class="road {road_class(str(r.get("highway") or ""))}" '
                    f'd="{escape(d,quote=True)}"/>')
    points=[]
    for _,r in bev.iterrows():
        sub=str(r["building_subcode"])
        row=lookup[sub]
        status=row["status"]
        if status not in REVIEW:
            continue
        pt=r.geometry
        if pt is None or pt.is_empty or pt.geom_type!="Point":
            raise ValueError(f"Ungueltiger BEV-Pruefpunkt: {sub}")
        info={
            "subcode":sub,"address_id":row["address_id"],"number":row["housenumber"],
            "street":row["street"],"area":row.get("address_area",""),
            "building_number":row.get("building_number",""),
            "building_identifier":row.get("building_identifier",""),
            "status":status,"candidates":row.get("candidate_osm_ids",""),
            "distance":row.get("distance_to_candidate_m",""),
        }
        points.append((pt.x,-pt.y,info))
    points.sort(key=lambda v:(REVIEW.index(v[2]["status"]),v[2]["subcode"]))
    xmin,ymin,xmax,ymax=border.bounds
    pad=max(150,(xmax-xmin)*.035,(ymax-ymin)*.035)
    view=(xmin-pad,-ymax-pad,(xmax-xmin)+2*pad,(ymax-ymin)+2*pad)
    markers=[]
    options=[]
    for i,(x,y,info) in enumerate(points):
        color=COLORS[info["status"]]
        raw=json.dumps(info,ensure_ascii=False,separators=(",",":"))
        markers.append(
            f'<g class="marker" data-index="{i}" data-status="{info["status"]}" '
            f'data-info="{escape(raw,quote=True)}">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="50" fill="{color}" '
            f'stroke="#233447" stroke-width="2" vector-effect="non-scaling-stroke"/>'
            f'<title>{escape(info["subcode"]+" | "+info["status"])}</title></g>')
        title=f'{info["subcode"]} · {info["street"] or info["area"]} {info["number"]} · {info["status"]}'
        options.append(f'<option value="{i}">{escape(title)}</option>')
    html= r'''<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BEV/OSM – offene Gebäudezuordnungen – __MID__</title><style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui,Segoe UI,sans-serif;background:#f3f6f9;color:#23354a}
header{padding:13px 18px;background:#1d3b52;color:white}h1{font-size:20px;margin:0 0 4px}
header p{margin:0;color:#d8e4ed}.layout{display:grid;grid-template-columns:330px minmax(0,1fr);height:calc(100vh - 78px)}
aside{background:white;padding:14px;overflow:auto;border-right:1px solid #d7e0e8}
main{min-width:0;position:relative}svg{display:block;width:100%;height:100%;touch-action:none;background:#ecf2f6;cursor:grab}
svg.drag{cursor:grabbing}.road{fill:none;stroke-linecap:round;stroke-linejoin:round;pointer-events:none;vector-effect:non-scaling-stroke}
.road.major{stroke:#d5a271;stroke-width:2.4}.road.local{stroke:#bac4ce;stroke-width:1.6}
.road.path{stroke:#95ab97;stroke-width:1;stroke-dasharray:3 3}
#boundary{fill:#f1f7f1;stroke:#507a60;stroke-width:2;vector-effect:non-scaling-stroke;pointer-events:none}
.building{fill:#b9cad5;stroke:#557081;stroke-width:.8;vector-effect:non-scaling-stroke;pointer-events:none}
.building.candidate{fill:#ffe7a2;stroke:#b27b19;stroke-width:2.5}
.marker{cursor:pointer}.marker circle{vector-effect:non-scaling-stroke}.marker.active circle{stroke:#131a27;stroke-width:4}
label{display:flex;align-items:center;gap:8px;margin:10px 0}.dot{width:12px;height:12px;border-radius:50%;display:inline-block}
select{width:100%;padding:8px;border:1px solid #bccbd8;border-radius:6px}
#detail{white-space:pre-wrap;background:#f0f5fa;padding:12px;border-radius:8px;line-height:1.6;overflow-wrap:anywhere}
button{padding:7px 11px;border:1px solid #aec1d0;background:white;border-radius:7px;cursor:pointer}
.tools{position:absolute;right:12px;top:12px;display:flex;gap:7px}
small,.note{color:#61748a}.note{line-height:1.5;font-size:12px}
@media(max-width:770px){.layout{grid-template-columns:1fr;grid-template-rows:290px 1fr;height:calc(100vh - 78px)}}
</style></head><body><header>
<h1>BEV/OSM – offene Gebäudezuordnungen · Gemeinde __MID__</h1>
<p>__TOTAL__ BEV-Gebäudepunkte zur Prüfung · __NEAR__ nahe · __UNMATCHED__ ohne Treffer · __AMBIG__ Rand/Mehrfach</p>
</header><div class="layout"><aside>
<strong>Prüfstatus filtern</strong>
<label><input type="checkbox" class="filter" value="near_review" checked>
<span class="dot" style="background:#e7a12e"></span>Nahe Gebäudepunkte (__NEAR__)</label>
<label><input type="checkbox" class="filter" value="unmatched" checked>
<span class="dot" style="background:#d64e50"></span>Ohne Treffer (__UNMATCHED__)</label>
<label><input type="checkbox" class="filter" value="multiple_or_boundary" checked>
<span class="dot" style="background:#9352bd"></span>Rand/Mehrfach (__AMBIG__)</label>
<hr><strong>Kartenebenen</strong>
<label><input type="checkbox" id="show-roads" checked> OSM-Straßen/Wege (__ROADS_COUNT__)</label>
<label><input type="checkbox" id="show-buildings" checked> OSM-Gebäude (__BUILDINGS_COUNT__)</label>
<hr><label for="case">BEV-Prüfpunkt auswählen</label>
<select id="case"><option value="">— Prüfpunkt wählen —</option>__OPTIONS__</select>
<p><button id="next" type="button">Nächster sichtbarer Prüffall</button></p>
<strong>Details</strong><div id="detail" aria-live="polite">Prüfpunkt anklicken oder auswählen.</div>
<p class="note">Punktkoordinaten: BEV Gebäudereferenz (nicht Zugangs-/Adresskoordinate). Gelbe Grundrisse sind geometrische Kandidaten. Nahfälle werden nicht automatisch zugeordnet. Karte lokal, ohne Kacheldienst. Keine OIB-GK- oder Löschwasserbewertung.</p>
</aside><main>
<svg id="map" xmlns="http://www.w3.org/2000/svg" viewBox="__VIEWBOX__" aria-label="Interaktive offline BEV OSM Prüfkarte">
<path id="boundary" d="__BOUNDARY__" fill-rule="evenodd"/>
<g id="roads">__ROADS__</g><g id="buildings">__BUILDINGS__</g>
<g id="markers">__MARKERS__</g></svg>
<div class="tools"><button id="plus">+</button><button id="minus">−</button><button id="reset">Gesamtansicht</button></div>
</main></div><script>
(()=>{
const map=document.getElementById('map');
const markerEls=[...document.querySelectorAll('.marker')];
const buildings=[...document.querySelectorAll('.building')];
const select=document.getElementById('case'), detail=document.getElementById('detail');
const data=markerEls.map(m=>JSON.parse(m.dataset.info));
const bounds=map.viewBox.baseVal; const origin=[bounds.x,bounds.y,bounds.width,bounds.height];
let active=null, drag=null;
function markerSize(){
 const pixels=map.getBoundingClientRect().width;
 if(!pixels)return;
 const radius=6*map.viewBox.baseVal.width/pixels;
 markerEls.forEach(m=>m.querySelector('circle').setAttribute('r',radius));
}
function view(x,y,w,h){
 const v=map.viewBox.baseVal;v.x=x;v.y=y;v.width=w;v.height=h;markerSize();
}
function zoom(mult){
 const v=map.viewBox.baseVal,cx=v.x+v.width/2,cy=v.y+v.height/2;
 const w=Math.max(40,Math.min(origin[2]*12,v.width*mult)),h=w*origin[3]/origin[2];
 view(cx-w/2,cy-h/2,w,h);
}
function filter(){
 const enabled=new Set([...document.querySelectorAll('.filter:checked')].map(e=>e.value));
 markerEls.forEach((m,i)=>m.style.display=enabled.has(data[i].status)?'':'none');
 document.getElementById('roads').style.display=document.getElementById('show-roads').checked?'':'none';
 document.getElementById('buildings').style.display=document.getElementById('show-buildings').checked?'':'none';
}
function choose(index){
 if(!Number.isInteger(index)||index<0||index>=markerEls.length)return;
 if(active!==null)markerEls[active].classList.remove('active');
 active=index;const m=markerEls[index],d=data[index];
 m.classList.add('active');m.style.display='';
 select.value=String(index);
 const c=m.querySelector('circle'),x=Number(c.getAttribute('cx')),y=Number(c.getAttribute('cy'));
 const w=300,h=w*origin[3]/origin[2];view(x-w/2,y-h/2,w,h);
 buildings.forEach(b=>b.classList.remove('candidate'));
 const wanted=new Set((d.candidates||'').split('|').map(t=>t.trim()).filter(Boolean));
 buildings.forEach(b=>{if(wanted.has(b.dataset.id))b.classList.add('candidate')});
 detail.textContent='BEV-Subcode: '+d.subcode+'\nAdresscode: '+d.address_id+
  '\nAmtliche Adresse: '+[d.street||d.area,d.number].filter(Boolean).join(' ')+
  '\nBEV-Gebäudenummer: '+(d.building_number||'—')+
  '\nBEV-Bezeichnung: '+(d.building_identifier||'—')+
  '\nPrüfstatus: '+d.status+
  '\nOSM-Kandidaten: '+(d.candidates||'keine')+
  '\nAbstand zum nächsten OSM-Kandidaten: '+(d.distance||'nicht innerhalb des Prüfradius')+' m';
}
markerEls.forEach((m,i)=>m.addEventListener('click',()=>choose(i)));
select.addEventListener('change',()=>{if(select.value!=='')choose(Number(select.value))});
document.querySelectorAll('.filter').forEach(x=>x.addEventListener('change',filter));
document.getElementById('show-roads').addEventListener('change',filter);
document.getElementById('show-buildings').addEventListener('change',filter);
document.getElementById('next').onclick=()=>{
 const visible=markerEls.map((m,i)=>m.style.display==='none'?-1:i).filter(i=>i>=0);
 if(!visible.length)return;
 const position=visible.indexOf(active);
 choose(visible[(position+1)%visible.length]);
};
document.getElementById('plus').onclick=()=>zoom(.7);
document.getElementById('minus').onclick=()=>zoom(1.4);
document.getElementById('reset').onclick=()=>view(...origin);
map.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?.8:1.25)},{passive:false});
map.addEventListener('pointerdown',e=>{
 if(e.target.closest('.marker'))return;
 const v=map.viewBox.baseVal;
 drag={px:e.clientX,py:e.clientY,x:v.x,y:v.y,w:v.width,h:v.height};
 map.setPointerCapture(e.pointerId);map.classList.add('drag');
});
map.addEventListener('pointermove',e=>{
 if(!drag)return;
 const r=map.getBoundingClientRect();
 view(drag.x-(e.clientX-drag.px)*drag.w/r.width,
      drag.y-(e.clientY-drag.py)*drag.h/r.height,drag.w,drag.h);
});
map.addEventListener('pointerup',()=>{drag=null;map.classList.remove('drag')});
map.addEventListener('pointercancel',()=>{drag=null;map.classList.remove('drag')});
window.addEventListener('resize',markerSize);filter();markerSize();
})();
</script></body></html>'''
    replacements={
        "__MID__":escape(mid),"__TOTAL__":str(len(points)),
        "__NEAR__":str(actual["near_review"]),
        "__UNMATCHED__":str(actual["unmatched"]),
        "__AMBIG__":str(actual["multiple_or_boundary"]),
        "__ROADS_COUNT__":str(len(road_shapes)),
        "__BUILDINGS_COUNT__":str(len(shapes)),
        "__OPTIONS__":"".join(options),
        "__VIEWBOX__":" ".join(f"{n:.2f}" for n in view),
        "__BOUNDARY__":escape(polygon_path(border),quote=True),
        "__ROADS__":"\n".join(road_shapes),
        "__BUILDINGS__":"\n".join(shapes),
        "__MARKERS__":"\n".join(markers),
    }
    for needle,replacement in replacements.items():
        html=html.replace(needle,replacement)
    out=report/"bev_osm_pruefkarte.html"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(html,encoding="utf-8")
    print(f"[OK] BEV-Pruefpunkte: {len(points)} | {dict(actual)}")
    print(f"[INFO] OSM-Gebaeude: {len(shapes)}, Strassen/Wege: {len(road_shapes)}")
    print(f"[OK] {out}")
    print("[HINWEIS] Karte bleibt lokal. Keine automatischen Korrekturen.")
    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__=="__main__":
    main()
