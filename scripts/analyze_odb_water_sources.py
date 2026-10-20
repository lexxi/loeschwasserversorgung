#!/usr/bin/env python3
"""ODB-Wasserentnahmestellen: lokale, rein deskriptive Bestandsanalyse.

Keine OSM-Daten, keine Abdeckungs-/Eignungsbehauptung und keine externen APIs.
Entfernungen sind Luftlinie im metrischen CRS EPSG:31287.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median

from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent
STATUS_LABELS = {"1": "verwendbar", "2": "eingeschränkt verwendbar", "3": "nicht verwendbar"}
OUTPUT_COLUMNS = (
    "odb_id", "name", "type", "status_raw", "status_label",
    "nearest_other_id", "nearest_other_distance_m",
    "nearest_usable_id", "nearest_usable_distance_m",
    "other_within_100m", "other_within_250m", "other_within_500m",
)


def load_sources(path):
    if not path.is_file():
        raise FileNotFoundError(f"ODB-Import fehlt: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError("ODB-GeoJSON hat kein gültiges FeatureCollection-Format")
    transform = Transformer.from_crs("EPSG:4326", "EPSG:31287", always_xy=True)
    sources = []
    ids = set()
    for i, feature in enumerate(data["features"], 1):
        props = feature.get("properties")
        if not isinstance(props, dict):
            raise ValueError(f"Feature {i}: properties fehlen")
        key = str(props.get("odb_id") or "").strip()
        if not key or key in ids:
            raise ValueError(f"Feature {i}: ID fehlt oder ist doppelt: {key!r}")
        ids.add(key)
        geom = shape(feature.get("geometry"))
        if not isinstance(geom, Point) or geom.is_empty:
            raise ValueError(f"Feature {i}: keine gültige Punktgeometrie")
        x, y = transform.transform(geom.x, geom.y)
        if not all(map(lambda value: abs(value) < 1e8, (x, y))):
            raise ValueError(f"Feature {i}: unplausible Koordinaten")
        status = str(props.get("status_raw") or "").strip()
        sources.append({
            "odb_id": key,
            "name": str(props.get("name") or ""),
            "type": str(props.get("type") or ""),
            "status_raw": status,
            "status_label": STATUS_LABELS.get(status, "unbekannt"),
            "point": Point(x, y),
        })
    return sources


def nearest(source, others):
    if not others:
        return None, None
    winner = min(others, key=lambda item: (source["point"].distance(item["point"]), item["odb_id"]))
    return winner["odb_id"], source["point"].distance(winner["point"])


def stats(values):
    if not values:
        return {"min_m": None, "median_m": None, "max_m": None}
    return {"min_m": round(min(values), 1), "median_m": round(median(values), 1),
            "max_m": round(max(values), 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="GKZ, z.B. 20619")
    args = parser.parse_args()
    mid = args.gemeinde
    if len(mid) != 5 or not mid.isdigit() or not mid.startswith("2"):
        parser.error("Ungültige Kärntner Gemeinde-GKZ")
    path = ROOT / "data" / "processed" / mid / "odb_water_sources" / "odb_water_sources.geojson"
    sources = load_sources(path)
    sources.sort(key=lambda item: item["odb_id"])

    output_rows, nearest_distances = [], []
    for source in sources:
        others = [item for item in sources if item["odb_id"] != source["odb_id"]]
        usable = [item for item in others if item["status_raw"] == "1"]
        closest_id, distance = nearest(source, others)
        usable_id, usable_distance = nearest(source, usable)
        if distance is not None:
            nearest_distances.append(distance)
        row = {key: source[key] for key in ("odb_id", "name", "type", "status_raw", "status_label")}
        row.update({
            "nearest_other_id": closest_id or "",
            "nearest_other_distance_m": round(distance, 1) if distance is not None else "",
            "nearest_usable_id": usable_id or "",
            "nearest_usable_distance_m": round(usable_distance, 1) if usable_distance is not None else "",
        })
        for radius in (100, 250, 500):
            row[f"other_within_{radius}m"] = sum(
                1 for item in others if source["point"].distance(item["point"]) <= radius
            )
        output_rows.append(row)

    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "source": "Lokaler Import der Kärntner Objektdatenbank, Kategorie 1724",
        "count": len(sources),
        "by_type": dict(sorted(Counter(s["type"] for s in sources).items())),
        "by_status": dict(sorted(Counter(s["status_label"] for s in sources).items())),
        "nearest_other_source_distance": stats(nearest_distances),
        "sources_with_another_within_100m": sum(r["other_within_100m"] > 0 for r in output_rows),
        "sources_with_another_within_250m": sum(r["other_within_250m"] > 0 for r in output_rows),
        "sources_with_another_within_500m": sum(r["other_within_500m"] > 0 for r in output_rows),
        "limitations": [
            "Entfernungen sind geradlinige Punktabstände, keine Schlauchstrecken oder Fahrwege.",
            "Abstände zwischen Quellen belegen weder Versorgungslücken noch Abdeckung.",
            "Der Status 1 (verwendbar) enthält keinen Nachweis von Durchfluss, Druck oder Kapazität.",
            "Status 2 und 3 werden nicht als voll verwendbare Quellen eingestuft.",
            "Objektdatenbank-Bestand kann auf Zugriffsfreigaben beschränkt sein.",
            "Alle vier archivierten OSM-Wasserquellen bleiben unberücksichtigt.",
        ],
    }
    folder = ROOT / "reports" / mid
    folder.mkdir(parents=True, exist_ok=True)
    csv_path = folder / "odb_bestandsanalyse.csv"
    json_path = folder / "odb_bestandsanalyse.json"
    md_path = folder / "odb_bestandsanalyse.md"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=OUTPUT_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(output_rows)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = result["nearest_other_source_distance"]
    md = [
        f"# ODB-Wasserentnahmestellen – Bestandsanalyse Gemeinde {mid}",
        "",
        f"Erfasste ODB-Objekte: **{len(sources)}**. Keine OSM-Wasserquellen enthalten.",
        "",
        "## Kategorien",
        *[f"- {typ}: {count}" for typ, count in result["by_type"].items()],
        "",
        "## Verwendbarkeitsstatus (laut ODB)",
        *[f"- {label}: {count}" for label, count in result["by_status"].items()],
        "",
        "## Räumliche Verteilung (Luftlinie)",
        f"- Nächster anderer ODB-Punkt, minimal: {d['min_m']} m",
        f"- Nächster anderer ODB-Punkt, Median: {d['median_m']} m",
        f"- Nächster anderer ODB-Punkt, maximal: {d['max_m']} m",
        f"- Quellen mit mindestens einer weiteren ODB-Quelle in 100 m Entfernung: {result['sources_with_another_within_100m']}",
        f"- Quellen mit mindestens einer weiteren ODB-Quelle in 250 m Entfernung: {result['sources_with_another_within_250m']}",
        f"- Quellen mit mindestens einer weiteren ODB-Quelle in 500 m Entfernung: {result['sources_with_another_within_500m']}",
        "",
        "## Einschränkungen",
        *[f"- {limitation}" for limitation in result["limitations"]],
        "",
        "Die Schwellen 100/250/500 m sind reine Beschreibungsintervalle, keine normativen Versorgungsradien.",
        "",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Gemeinde {mid}: {len(sources)} ODB-Wasserentnahmestellen")
    print("Kategorien:", json.dumps(result["by_type"], ensure_ascii=False))
    print("Status:", json.dumps(result["by_status"], ensure_ascii=False))
    print("Abstand zum nächsten ODB-Punkt (m):", json.dumps(d, ensure_ascii=False))
    for radius in (100, 250, 500):
        print(f"Quellen mit Nachbar <= {radius} m: {result[f'sources_with_another_within_{radius}m']}")
    for out in (md_path, csv_path, json_path):
        print(f"[OK] {out}")


if __name__ == "__main__":
    main()
