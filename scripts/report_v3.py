#!/usr/bin/env python3
"""Add auditable V3 sections and local QGIS review files to the municipality report."""
from __future__ import annotations

import json
from pathlib import Path
import geopandas as gpd
import pandas as pd


def _table(headers, rows):
    def cell(x):
        return str(x).replace("|", "\\|").replace("\n", " ")
    return ("| " + " | ".join(headers) + " |\n"
            + "| " + " | ".join("---" for _ in headers) + " |\n"
            + "".join("| " + " | ".join(cell(v) for v in row) + " |\n" for row in rows))


def _num(value, places=2):
    return f"{value:,.{places}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _find(base, recorded, fallbacks):
    options = ([Path(recorded)] if recorded else []) + [base / p for p in fallbacks]
    return next((p for p in options if p.is_file()), None)


def extend_report(base: Path, out: Path, manifest: dict, report: dict, markdown: str):
    """Returns updated report and markdown; writes review exports only into out."""
    warnings = report["warnings"]
    section = ["## 6. Qualitätsprüfung und QGIS-Stichprobe", ""]

    # Area topology: use union of ALL zoning footprints and subtract from municipality boundary.
    bpath = _find(base, manifest.get("outputs", {}).get("boundary", {}).get("file"),
                  ["boundary.geojson", "malta_boundary_2026.geojson"])
    zpath = _find(base, manifest.get("outputs", {}).get("zoning", {}).get("file"),
                  ["zoning.geojson", "malta_zoning.geojson"])
    area = None
    if bpath and zpath:
        b = gpd.read_file(bpath).to_crs(31287)
        z = gpd.read_file(zpath).to_crs(31287)
        if b.empty or z.empty or b.crs is None or z.crs is None:
            raise ValueError("Geometrie der Gemeinde oder Widmung fehlt.")
        municipality = b.geometry.union_all()
        zone_union = z.geometry.union_all()
        covered = municipality.intersection(zone_union)
        uncovered = municipality.difference(zone_union)
        raw_sum = float(z.geometry.area.sum())
        total_union = float(zone_union.area)
        inside_union = float(covered.area)
        area = {
            "municipality_ha": round(float(municipality.area) / 1e4, 4),
            "zoning_union_within_municipality_ha": round(inside_union / 1e4, 4),
            "uncovered_within_municipality_ha": round(float(uncovered.area) / 1e4, 4),
            "uncovered_pct": round(100 * uncovered.area / municipality.area, 5) if municipality.area else None,
            "raw_polygon_sum_ha": round(raw_sum / 1e4, 4),
            "union_all_polygons_ha": round(total_union / 1e4, 4),
            "duplicate_coverage_ha": round((raw_sum - total_union) / 1e4, 4),
            "outside_municipality_ha": round(float(zone_union.difference(municipality).area) / 1e4, 4),
        }
        section += [
            "### Topologische Flächenbilanz",
            "",
            _table(["Kennzahl", "Ergebnis"], [
                ("Gemeindefläche", _num(area["municipality_ha"], 4) + " ha"),
                ("Von mindestens einer Widmung überdeckte Gemeindefläche", _num(area["zoning_union_within_municipality_ha"], 4) + " ha"),
                ("Nicht von Widmungspolygonen überdeckte Gemeindefläche", _num(area["uncovered_within_municipality_ha"], 4) + " ha"),
                ("Nicht abgedeckter Anteil", _num(area["uncovered_pct"], 5) + " %" if area["uncovered_pct"] is not None else "n/a"),
                ("Summierte Einzelpolygonflächen", _num(area["raw_polygon_sum_ha"], 4) + " ha"),
                ("Einmalige Fläche aller Widmungspolygone (Union)", _num(area["union_all_polygons_ha"], 4) + " ha"),
                ("Mehrfach gezählte Fläche (Summe minus Union)", _num(area["duplicate_coverage_ha"], 4) + " ha"),
                ("Widmungsunion außerhalb Gemeinde", _num(area["outside_municipality_ha"], 4) + " ha"),
            ]),
            "**Interpretation:** „Mehrfach gezählte Fläche“ ist die Summe der Polygonflächen minus ihrer geometrischen Vereinigung. Sie misst Mehrfachabdeckung mit Multiplizität und ist nicht die Anzahl fehlerhafter Polygone. Nicht abgedeckte Fläche ist ebenfalls kein automatischer Datenfehler. Alle Werte beziehen sich auf den aktuellen Geometrieimport.",
            "",
        ]
    else:
        warnings.append("V3-Flächenbilanz: Gemeindegrenze oder Widmungsdatei nicht gefunden.")
        section += ["_Topologische Flächenbilanz mangels Geodatei nicht verfügbar._", ""]
    report["geometry"]["topology_audit"] = area

    # Review sample derived deterministically from overlap percentages, no house numbers.
    overlap_path = base / "building_zoning" / "zoning_footprint_overlaps.csv"
    classified_path = base / "building_classification" / "buildings_classified.geojson"
    selected = None
    if overlap_path.is_file() and classified_path.is_file():
        overlaps = pd.read_csv(overlap_path, sep=";", encoding="utf-8-sig", dtype={"osm_id": str})
        needed = {"osm_id", "overlap_pct", "KATEGORIE", "WIDMUNG"}
        if not needed.issubset(overlaps):
            raise ValueError(f"V3-Flächendatei ohne Felder {sorted(needed - set(overlaps))}.")
        overlaps["overlap_pct"] = pd.to_numeric(overlaps["overlap_pct"], errors="raise")
        grouped = overlaps.groupby("osm_id")
        counts = grouped.size()
        dominant = grouped["overlap_pct"].max()
        review_ids = sorted(
            [oid for oid in dominant.index if counts[oid] >= 2 and 50 <= dominant[oid] < 60],
            key=lambda oid: (dominant[oid], oid),
        )
        buildings = gpd.read_file(classified_path)
        if "osm_id" not in buildings or buildings["osm_id"].duplicated().any():
            raise ValueError("V3: nicht eindeutige osm_id in klassifizierten Gebäuden.")
        selected = buildings.loc[buildings["osm_id"].isin(review_ids)].copy()
        if len(selected) != len(review_ids):
            raise ValueError("V3: nicht alle starken Grenzfälle im Gebäudedatensatz vorhanden.")
        by_id = buildings.set_index("osm_id")
        rows = []
        for oid in review_ids:
            entries = overlaps.loc[overlaps["osm_id"].eq(oid)].sort_values("overlap_pct", ascending=False)
            vals = entries["overlap_pct"].tolist()
            categories = " / ".join(sorted(set(entries["KATEGORIE"].dropna().astype(str))))
            rows.append({
                "osm_id": oid,
                "dominant_pct": round(vals[0], 4),
                "second_pct": round(vals[1], 4),
                "intersections": len(vals),
                "categories": categories,
                "building_use_class": str(by_id.loc[oid, "building_use_class"]),
                "zoning_status": str(by_id.loc[oid, "zoning_status"]),
            })
        review_frame = pd.DataFrame(rows, columns=[
            "osm_id", "dominant_pct", "second_pct", "intersections",
            "categories", "building_use_class", "zoning_status"
        ])
        review_frame.to_csv(out / "grenzfaelle_50_60.csv", sep=";", encoding="utf-8-sig", index=False)
        # Export only audited properties plus geometry, not address/name metadata.
        if not selected.empty:
            selected = selected[["osm_id", "geometry"]].merge(review_frame, on="osm_id", validate="one_to_one")
            selected.to_crs(4326).to_file(out / "grenzfaelle_50_60.geojson", driver="GeoJSON", index=False)
        else:
            (out / "grenzfaelle_50_60.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": []}) + "\n", encoding="utf-8"
            )
        section += [
            "### Gebäude mit 50–unter 60 % größter Überdeckung",
            "",
            f"**{len(rows)} Gebäude** für vorrangige kartografische Prüfung.",
            "Lokale Exporte: `grenzfaelle_50_60.csv` und `grenzfaelle_50_60.geojson` (QGIS).",
            "Die Ausgaben enthalten OSM-IDs und Prüfwerte, aber **keine Hausnummern**.",
            "",
            _table(["OSM-ID", "Größte Fläche", "Zweitgrößte Fläche", "Schnitte", "Kategorien"],
                   [(r["osm_id"], _num(r["dominant_pct"], 2)+" %",
                     _num(r["second_pct"], 2)+" %", r["intersections"], r["categories"])
                    for r in rows]),
            "**Prüfreihenfolge:** Kartenlage, Kataster/Orthofoto und Widmungsgrenzen vergleichen; anschließend Ursache dokumentieren. Keine automatische Festlegung einer maßgeblichen Widmung.",
            "",
        ]
        report["boundary_review_sample"] = {
            "rule": "2+ positive intersections; 50 <= highest overlap percent < 60; sorted by highest percent and OSM-ID",
            "count": len(rows), "file_csv": "grenzfaelle_50_60.csv",
            "file_geojson": "grenzfaelle_50_60.geojson",
        }

        # Aggregate unknown use with housenumber, without exposing addresses.
        if "has_housenumber" in buildings:
            has_number = buildings["has_housenumber"].astype(str).str.lower().isin(["true", "1"])
        elif "addr:housenumber" in buildings:
            has_number = buildings["addr:housenumber"].notna() & buildings["addr:housenumber"].astype(str).str.strip().ne("")
        else:
            has_number = None
        if has_number is not None:
            unknown = buildings.loc[
                buildings["building_use_class"].eq("use_unknown") & has_number
            ].copy()
            if int(len(unknown)) != report["buildings"]["unknown_with_housenumber"]:
                raise ValueError("V3: Hausnummer-Unbekanntzahl stimmt nicht mit V2 überein.")
            group_columns = ["zone_kategorie", "zone_widmung", "building"]
            for col in group_columns:
                if col not in unknown:
                    unknown[col] = "(ohne Angabe)"
            unknown.loc[unknown["zoning_status"].ne("unique"), ["zone_kategorie", "zone_widmung"]] = "(Prüffall)"
            agg = (unknown.groupby(group_columns, dropna=False).size()
                   .reset_index(name="buildings").sort_values(
                       ["buildings", "zone_kategorie", "zone_widmung"],
                       ascending=[False, True, True]))
            agg.to_csv(out / "unbekannte_nutzung_mit_hausnummer_aggregation.csv",
                       sep=";", encoding="utf-8-sig", index=False)
            section += [
                "### Hausnummer vorhanden, OSM-Nutzung ungeklärt",
                "",
                f"**{len(unknown)} Gebäude** mit Hausnummer und unklarem OSM-`building`-Tag.",
                "Die folgende Tabelle zeigt die **aggregierten** Fälle nach Widmung und OSM-Gebäudetag. Es werden keine Hausnummern ausgegeben.",
                "",
                _table(["Kategorie", "Widmung", "building-Tag", "Gebäude"],
                       [(r["zone_kategorie"], r["zone_widmung"], r["building"], int(r["buildings"]))
                        for _, r in agg.iterrows()]),
                "Lokaler Export: `unbekannte_nutzung_mit_hausnummer_aggregation.csv`.",
                "Eine Hausnummer ist ein Hinweis auf Adressierung, **kein Nachweis einer Wohnnutzung**.",
                "",
            ]
            report["buildings"]["unknown_with_housenumber_by_zoning"] = [
                {"kategorie": str(r["zone_kategorie"]), "widmung": str(r["zone_widmung"]),
                 "building_tag": str(r["building"]), "count": int(r["buildings"])}
                for _, r in agg.iterrows()
            ]
        else:
            warnings.append("V3: keine Hausnummern-Indikatorspalte im klassifizierten Gebäudeexport.")
    else:
        warnings.append("V3-Grenzfälle: Flächenschnitte oder klassifizierte Gebäude fehlen.")
        section += ["_Grenzfall-Stichprobe mangels Eingabedateien nicht verfügbar._", ""]

    return report, markdown.rstrip() + "\n\n" + "\n".join(section) + "\n"
