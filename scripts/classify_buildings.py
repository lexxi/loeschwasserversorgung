#!/usr/bin/env python3
"""Conservative, auditable OSM building classification (not firewater demand)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


def normalized_tag(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip().casefold()


def load_rules(path):
    rules = json.loads(path.read_text(encoding="utf-8"))
    residential = {str(s).strip().casefold() for s in rules["explicit_residential"]}
    non_residential = {str(s).strip().casefold() for s in rules["explicit_non_residential"]}
    if not residential or not non_residential or residential & non_residential:
        raise ValueError("Klassifikationslisten sind leer oder widersprechen sich.")
    return residential, non_residential


def classify(frame, residential, non_residential):
    if "osm_id" not in frame or "building" not in frame:
        raise ValueError("Erforderliche Spalten osm_id und building fehlen.")
    if frame["osm_id"].isna().any() or frame["osm_id"].duplicated().any():
        raise ValueError("Fehlende oder doppelte OSM-IDs.")
    result = frame.copy()
    tags = result["building"].map(normalized_tag)
    if tags.eq("").any():
        raise ValueError("Gebaeude ohne building-Tag gefunden.")
    def identify(tag):
        if tag in residential:
            return "residential_candidate"
        if tag in non_residential:
            return "non_residential_tag"
        return "use_unknown"
    result["building_use_class"] = tags.map(identify)
    result["building_class_source"] = "osm_building_tag"
    result["building_class_rule"] = tags
    # Contextual indicators are informational only; they never override the building tag.
    for column, suffix in [
        ("addr:housenumber", "has_housenumber"),
        ("amenity", "has_amenity_tag"),
        ("tourism", "has_tourism_tag"),
        ("shop", "has_shop_tag"),
    ]:
        result[suffix] = result[column].map(normalized_tag).ne("") if column in result else False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(
        "data/processed/current/building_zoning/buildings_with_zoning.geojson"))
    parser.add_argument("--config", type=Path, default=Path(
        "config/building_classification.json"))
    parser.add_argument("--out", type=Path, default=Path(
        "data/processed/current/building_classification"))
    args = parser.parse_args()
    source = gpd.read_file(args.input)
    if source.empty or source.crs is None:
        raise ValueError("Gebaeude-Datei leer oder ohne CRS.")
    if source.geometry.isna().any() or source.geometry.is_empty.any():
        raise ValueError("Unvollstaendige Geometrien.")
    residential, non_residential = load_rules(args.config)
    result = classify(source, residential, non_residential)
    if len(source) != len(result):
        raise AssertionError("Anzahl der Gebaeude hat sich geaendert.")
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / "buildings_classified.geojson"
    result.to_crs(4326).to_file(output, driver="GeoJSON", index=False)
    counts = result["building_use_class"].value_counts()
    unknown_tags = result.loc[
        result["building_use_class"].eq("use_unknown"), "building"
    ].map(normalized_tag).value_counts()
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "config": str(args.config),
        "output": str(output),
        "total_buildings": int(len(result)),
        "residential_candidate": int(counts.get("residential_candidate", 0)),
        "non_residential_tag": int(counts.get("non_residential_tag", 0)),
        "use_unknown": int(counts.get("use_unknown", 0)),
        "unknown_building_tags": {str(k): int(v) for k, v in unknown_tags.items()},
        "note": "Classification reflects OSM building tags only. Unknown remains unknown; housenumbers do not establish residential use. No firewater requirement inferred."
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
