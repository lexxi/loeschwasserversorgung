#!/usr/bin/env python3
"""Liest autorisiert exportierte ODB-Wasserentnahmestellen aus lokalem GeoJSON.

Keine API-Anmeldung oder Netzwerkanfrage. Originalexport und Ergebnis bleiben
lokal und werden nicht nach GitHub hochgeladen.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, shape

CATEGORIES = {
    "Bach mit Stau": 1729,
    "Löschwasserteich": 1730,
    "Saugstelle": 3953,
    "Überflurhydrant": 1728,
    "Unterflurhydrant": 1727,
}
STATUS_LABELS = {"1": "verwendbar", "2": "eingeschränkt verwendbar", "3": "nicht verwendbar"}
FIELDS = ("odb_id", "name", "type", "status_raw", "status_label", "latitude", "longitude")
ROOT = Path(__file__).resolve().parent.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def load_geojson(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Kein gültiger GeoJSON-FeatureCollection-Export")
    if not isinstance(data.get("features"), list):
        raise ValueError("GeoJSON enthält keine Feature-Liste")
    # ODB bezeichnet möglicherweise unvollständige Kartenauszüge als sliceddata.
    sliced = data.get("sliceddata")
    if str(sliced).strip().lower() not in ("0", "false", "none", ""):
        raise ValueError(f"ODB-Export möglicherweise abgeschnitten: sliceddata={sliced!r}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemeinde", required=True, help="Kärntner GKZ, z. B. 20619")
    parser.add_argument("--input", type=Path, required=True,
                        help="Lokal gespeicherter GeoJSON-Export der ODB-Kategorie 1724")
    args = parser.parse_args()
    mid = args.gemeinde
    if not (len(mid) == 5 and mid.isdigit() and mid.startswith("2")):
        parser.error("--gemeinde muss eine fünfstellige Kärntner GKZ sein")
    if not args.input.is_file():
        parser.error(f"Export fehlt: {args.input}")
    base = ROOT / "data" / "processed" / mid
    boundary_path = base / "boundary.geojson"
    manifest_path = base / "import_manifest.json"
    if not boundary_path.is_file() or not manifest_path.is_file():
        parser.error(f"Gemeindegrenze/Manifest fehlen unter {base}")
    import_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(import_manifest.get("municipality_id")) != mid:
        parser.error("Gemeinde-ID im amtlichen Manifest stimmt nicht überein")

    boundary = gpd.read_file(boundary_path)
    if boundary.crs is None or boundary.empty:
        raise ValueError("Gemeindegrenze ohne CRS oder leer")
    boundary_wgs = boundary.to_crs(4326).geometry.union_all()
    data = load_geojson(args.input)
    features = data["features"]

    rows = []
    output_features = []
    rejected = Counter()
    types_all = Counter()
    statuses_all = Counter()
    seen_ids = set()
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            rejected["malformed_properties"] += 1
            continue
        properties = feature["properties"]
        category = str(properties.get("Type") or "").strip()
        status_value = properties.get("Status")
        status = "" if status_value is None else str(status_value)
        types_all[category or "(leer)"] += 1
        statuses_all[status or "(leer)"] += 1
        odb_id = properties.get("Id")
        if odb_id is None or str(odb_id).strip() == "":
            rejected["missing_id"] += 1
            continue
        odb_id = str(odb_id).strip()
        if odb_id in seen_ids:
            raise ValueError(f"Doppelte ODB-ID im Export: {odb_id}")
        seen_ids.add(odb_id)
        try:
            geom = shape(feature.get("geometry"))
        except (TypeError, ValueError, AttributeError):
            rejected["invalid_geometry"] += 1
            continue
        if not isinstance(geom, Point) or geom.is_empty or not geom.is_valid:
            rejected["non_point_geometry"] += 1
            continue
        if not (-180 <= geom.x <= 180 and -90 <= geom.y <= 90):
            rejected["invalid_coordinates"] += 1
            continue
        # GeoJSON-Koordinaten sind WGS84 (Längengrad, Breitengrad).
        if not boundary_wgs.covers(geom):
            rejected["outside_municipality"] += 1
            continue
        if category not in CATEGORIES:
            rejected["unknown_category"] += 1
            continue
        row = {"odb_id": odb_id, "name": str(properties.get("Name") or "").strip(),
               "type": category, "status_raw": status,
               "status_label": STATUS_LABELS.get(status, "nicht bestätigt"),
               "latitude": round(geom.y, 7), "longitude": round(geom.x, 7)}
        rows.append(row)
        output_features.append({"type": "Feature", "geometry": feature["geometry"],
                                "properties": row.copy()})

    rows.sort(key=lambda x: x["odb_id"])
    output_features.sort(key=lambda x: x["properties"]["odb_id"])
    out = base / "odb_water_sources"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "odb_water_sources.csv"
    geojson_path = out / "odb_water_sources.geojson"
    manifest_out = out / "odb_water_sources_manifest.json"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    geojson_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": output_features},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "municipality_id": mid,
        "source": "Kärntner Objektdatenbank; lokal gespeicherter, berechtigt bezogener GeoJSON-Export",
        "source_category": 1724,
        "source_file": str(args.input),
        "source_sha256": sha256(args.input),
        "boundary_sha256": sha256(boundary_path),
        "sliceddata": data.get("sliceddata"),
        "total_export_features": len(features),
        "total_by_type": dict(sorted(types_all.items())),
        "total_by_status_raw": dict(sorted(statuses_all.items())),
        "count": len(rows),
        "count_by_type": dict(sorted(Counter(row["type"] for row in rows).items())),
        "count_by_status_raw": dict(sorted(Counter(row["status_raw"] for row in rows).items())),
        "known_status_labels": STATUS_LABELS,
        "rejected": dict(sorted(rejected.items())),
        "csv_sha256": sha256(csv_path),
        "geojson_sha256": sha256(geojson_path),
        "limitations": [
            "Status 1 = verwendbar, Status 2 = eingeschränkt verwendbar, Status 3 = nicht verwendbar (gemäß Rückmeldung aus der ODB). Die Statusangabe ersetzt keine Vor-Ort-Prüfung.",
            "GeoJSON-Kartenauszug ist kein Nachweis der gesamten Gemeindeabdeckung.",
            "Verwendet nur ODB-Id, Name, Type, Status und Point-Koordinaten; lokale Daten nicht veröffentlichen.",
            "Standort, Einsatzbereitschaft und Löschwasserleistung sind nicht verifiziert.",
            "Keine OSM-Datensatz-Zusammenführung oder Dublettenbeurteilung.",
        ],
    }
    manifest_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Export: {len(features)} Features; sliceddata={data.get('sliceddata')!r}")
    print(f"[OK] Innerhalb GKZ {mid}: {len(rows)} Objekte")
    print("Kategorien:", json.dumps(result["count_by_type"], ensure_ascii=False))
    print("Status (Rohcodes):", json.dumps(result["count_by_status_raw"], ensure_ascii=False))
    print("Ausgeschieden:", json.dumps(result["rejected"], ensure_ascii=False))
    print(f"[OK] {csv_path}")
    print(f"[OK] {geojson_path}")
    print(f"[OK] {manifest_out}")


if __name__ == "__main__":
    main()
