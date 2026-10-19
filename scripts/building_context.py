"""Offline-Lagekarten und WGS84-Standortlink für die Einzelgebäudeansicht.

Nur bereits importierte Gemeindegrenzen und Gebäude; kein Kachel-/Straßendownload.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box
from shapely.ops import transform

EPSG = 31287


def load_context(base: Path, buildings: gpd.GeoDataFrame):
    path = base / "boundary.geojson"
    if not path.is_file():
        raise FileNotFoundError(f"Gemeindegrenze fehlt: {path}")
    boundary = gpd.read_file(path)
    if boundary.empty or boundary.crs is None:
        raise ValueError("Gemeindegrenze leer oder ohne CRS")
    return boundary.to_crs(epsg=EPSG).geometry.union_all(), buildings.sindex


def _paths(shape, xform):
    if shape.is_empty:
        return ""
    if shape.geom_type == "Polygon":
        pieces = [shape]
    elif shape.geom_type == "MultiPolygon":
        pieces = shape.geoms
    elif shape.geom_type == "GeometryCollection":
        return " ".join(_paths(p, xform) for p in shape.geoms)
    else:
        return ""
    results = []
    for polygon in pieces:
        for ring in (polygon.exterior, *polygon.interiors):
            results.append("M " + " L ".join(f"{a:.2f},{b:.2f}" for a, b in
                        (xform(x, y) for x, y in ring.coords)) + " Z")
    return " ".join(results)


def _project(bounds, width=560, height=400, margin=18):
    x0, y0, x1, y1 = bounds
    dx = max(x1 - x0, 1)
    dy = max(y1 - y0, 1)
    factor = min((width - 2 * margin) / dx, (height - 2 * margin) / dy)
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2
    return lambda x, y: (width / 2 + (x - center_x) * factor,
                          height / 2 - (y - center_y) * factor), factor


def _svg(contents, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 400" '
            f'role="img" aria-label="{escape(title, quote=True)}">'
            '<rect width="560" height="400" fill="#f1f5f8"/>'
            + "".join(contents) + '</svg>')


def render_context(footprint, boundary, buildings, spatial_index):
    center = footprint.representative_point()
    # Einfache Ortsübersicht: vollständige Gemeindekontur im Maßstab der Gemeinde.
    projector, _ = _project(boundary.bounds)
    marker_x, marker_y = projector(center.x, center.y)
    overview = _svg([
        f'<path d="{_paths(boundary, projector)}" fill="#d6e5d6" stroke="#54735b" '
        'stroke-width="1.5" fill-rule="evenodd"/>',
        f'<circle cx="{marker_x:.2f}" cy="{marker_y:.2f}" r="7" fill="#da3636" '
        'stroke="#fff" stroke-width="2.5"/>',
        '<text x="12" y="22" fill="#334155" font-size="14">N ↑</text>',
    ], "Gemeindegrenze mit rotem Gebäudestandort")

    # Lokale, metrische 250-m-Ansicht (500 m Bildbreite); kein OSM-Basemap.
    radius = 250.0
    bounds = (center.x - radius, center.y - radius,
              center.x + radius, center.y + radius)
    window = box(*bounds)
    projector, pixels_per_meter = _project(bounds)
    shapes = []
    for idx in spatial_index.query(window, predicate="intersects"):
        geom = buildings.geometry.iloc[int(idx)]
        if geom.equals(footprint):
            continue
        clipped = geom.intersection(window)
        path = _paths(clipped, projector)
        if path:
            shapes.append(f'<path d="{path}" fill="#c1cad4" stroke="#64748b" '
                          'stroke-width="0.9" fill-rule="evenodd"/>')
    shapes.append(f'<path d="{_paths(footprint, projector)}" fill="#df4444" '
                  'stroke="#8e1717" stroke-width="2.5" fill-rule="evenodd"/>')
    marker_x, marker_y = projector(center.x, center.y)
    shapes.append(f'<circle cx="{marker_x:.2f}" cy="{marker_y:.2f}" r="3.5" fill="#111827"/>')
    bar_width = 100 * pixels_per_meter
    shapes.append(f'<path d="M 18,365 h {bar_width:.2f}" stroke="#263443" stroke-width="4"/>')
    shapes.append(f'<text x="18" y="355" fill="#263443" font-size="13">100 m</text>')
    shapes.append('<text x="12" y="22" fill="#334155" font-size="14">N ↑</text>')
    local = _svg(shapes, "Umgebung 250 Meter um das Gebäude mit Nachbargebäuden")

    location = gpd.GeoSeries([center], crs=f"EPSG:{EPSG}").to_crs(epsg=4326).iloc[0]
    lat, lon = location.y, location.x
    osm_url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=18/{lat:.6f}/{lon:.6f}"
    location_html = (
        f'<p class="note">Standort (WGS84, Repräsentativpunkt): '
        f'<strong>{lat:.6f}, {lon:.6f}</strong> · '
        f'<a href="{escape(osm_url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        'In OpenStreetMap öffnen ↗</a></p>'
    )
    cards = (
        '<div class="location-grid">'
        '<section class="panel"><h2>Lage in der Gemeinde</h2>' + overview + '</section>'
        '<section class="panel"><h2>Gebäudeumgebung (±250 m)</h2>' + local + '</section>'
        '</div>' + location_html
        + '<p class="note">Rot: ausgewähltes Gebäude; Grau: weitere importierte OSM-Gebäude. '
        'Keine Straßen, Hausnummern oder Kartografie-Hintergrunddaten. '
        'Die beiden Grafiken funktionieren offline; nur der OSM-Link benötigt Internet.</p>'
    )
    return cards
