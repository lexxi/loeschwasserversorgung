#!/usr/bin/env python3
"""Erstellt eine lokale PNG-Uebersicht der OSM-Wasserquellen einer Gemeinde.

Verwendet ausschliesslich bereits importierte, lokale GeoJSON-Dateien.
Keine Web-Anfragen und keine Weitergabe von Standortdaten.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Fuenfstellige Gemeinde-GKZ")
    parser.add_argument("--output", type=Path, help="Optionaler PNG-Zielpfad")
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit():
        parser.error("--gemeinde erwartet eine fuenfstellige GKZ")

    boundary_path = ROOT / "data" / "processed" / mid / "boundary.geojson"
    osm_path = ROOT / "data" / "processed" / mid / "water_sources" / "water_sources.geojson"
    for path in (boundary_path, osm_path):
        if not path.is_file():
            parser.error(f"Datei fehlt: {path}")

    boundary = gpd.read_file(boundary_path).to_crs("EPSG:31287")
    osm = gpd.read_file(osm_path).to_crs("EPSG:31287")
    if boundary.empty:
        parser.error("Die Gemeindegrenze enthaelt keine Geometrie.")
    if osm.empty:
        parser.error("Keine OSM-Wasserquellen in dieser Gemeinde vorhanden.")
    if not osm.geometry.geom_type.eq("Point").all():
        parser.error("OSM-GeoJSON enthaelt nicht nur Punkte.")

    fig, ax = plt.subplots(figsize=(11, 9))
    boundary.plot(ax=ax, facecolor="#edf4eb", edgecolor="#34523b", linewidth=1)
    osm.plot(ax=ax, color="#c82b2b", markersize=65, zorder=3)

    for i, (_, row) in enumerate(osm.iterrows(), 1):
        ax.annotate(
            str(i), (row.geometry.x, row.geometry.y),
            xytext=(6, 5), textcoords="offset points", fontsize=10,
            fontweight="bold", color="#8a0909", zorder=4,
        )

    # Separate Legende verhindert sich ueberlappende OSM-IDs im Kartenbild.
    labels = []
    for i, (_, row) in enumerate(osm.iterrows(), 1):
        hydrant_type = row.get("fire_hydrant:type")
        if hydrant_type is None or str(hydrant_type).lower() in ("nan", "none", ""):
            hydrant_type = "nicht angegeben"
        labels.append(f"{i}: {row['osm_id']} ({hydrant_type})")

    fig.text(
        0.07, 0.035, "\n".join(labels),
        ha="left", va="bottom", fontsize=9, family="monospace",
    )
    ax.set_title(f"Gemeinde {mid} - OSM-Wasserquellen ({len(osm)})")
    ax.set_aspect("equal")
    ax.set_axis_off()

    output = args.output or ROOT / "reports" / mid / "osm_wasserquellen.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(bottom=min(0.1 + 0.035 * len(osm), 0.36))
    fig.savefig(output, dpi=180)
    plt.close(fig)
    print(f"[OK] {len(osm)} OSM-Wasserquellen: {output}")


if __name__ == "__main__":
    main()
