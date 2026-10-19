#!/usr/bin/env python3
"""Generate a reproducible municipality report from existing GIS analysis outputs.

No downloads, no reclassification and no firewater demand calculation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from municipality_text import readable_name


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Pflichtdatei fehlt: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def percent(part, total) -> str:
    return (f"{100 * part / total:.2f}".replace(".", ",") + " %") if total else "n/a"


def md_table(headers, rows):
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")
    return ("| " + " | ".join(headers) + " |\n"
            + "| " + " | ".join("---" for _ in headers) + " |\n"
            + "".join("| " + " | ".join(cell(v) for v in row) + " |\n" for row in rows))


def resolve_source(base: Path, name: str, relative: str, warnings: list):
    path = base / relative
    if not path.is_file():
        warnings.append(f"{name}: {path} fehlt; Teilbericht nicht verfügbar.")
        return None
    return path


def compute(base: Path) -> tuple[dict, str]:
    manifest = read_json(base / "import_manifest.json")
    osm = read_json(base / "osm" / "osm_manifest.json")
    joined = read_json(base / "building_zoning" / "summary.json")
    classification = read_json(base / "building_classification" / "summary.json")
    municipality_id = str(manifest.get("municipality_id", "")).strip()
    municipality_name = readable_name(str(manifest.get("municipality_name", "")).strip())
    if not municipality_id or not municipality_name:
        raise ValueError("Gemeinde-ID oder -Name fehlt im Import-Manifest.")
    if str(osm.get("municipality_id", "")).strip() != municipality_id:
        raise ValueError("Gemeinde-ID von amtlichem Import und OSM-Import stimmt nicht ueberein.")

    warnings = []
    recorded = manifest.get("outputs", {}).get("zoning", {}).get("file")
    candidates = [Path(recorded)] if recorded else []
    candidates += [base / "zoning.geojson", base / "malta_zoning.geojson"]
    zoning_path = next((p for p in candidates if p.is_file()), None)
    if zoning_path is None:
        warnings.append("Widmungsgeometrie fehlt; Flaechenstatistik nicht verfuegbar.")
    boundary_recorded = manifest.get("outputs", {}).get("boundary", {}).get("file")
    boundary_candidates = ([Path(boundary_recorded)] if boundary_recorded else [])
    boundary_candidates += [base / "boundary.geojson", base / "malta_boundary_2026.geojson"]
    boundary_path = next((p for p in boundary_candidates if p.is_file()), None)
    if boundary_path is None:
        warnings.append("Gemeindegrenze fehlt; Gemeinde- und Flaechenanteile nicht verfuegbar.")

    categories = {}
    zoning_count = None
    category_areas = {}
    municipality_area_ha = None
    if boundary_path is not None:
        boundary = gpd.read_file(boundary_path)
        if boundary.empty or boundary.crs is None:
            raise ValueError("Gemeindegrenze leer oder ohne CRS.")
        municipality_area_ha = round(float(boundary.to_crs(31287).geometry.union_all().area) / 10000, 4)
    if zoning_path is not None:
        zone_frame = gpd.read_file(zoning_path)
        if "KATEGORIE" not in zone_frame:
            warnings.append("Widmungsdatei enthaelt kein Feld KATEGORIE.")
        else:
            categories = {str(k): int(v) for k, v in zone_frame["KATEGORIE"].fillna("(ohne Angabe)").value_counts().items()}
        zoning_count = len(zone_frame)
        if not zone_frame.empty and zone_frame.crs is not None and "KATEGORIE" in zone_frame:
            metric = zone_frame.to_crs(31287)
            for category, subset in metric.groupby(metric["KATEGORIE"].fillna("(ohne Angabe)")):
                # union rather than arithmetic polygon sum within each category
                area = float(subset.geometry.union_all().area) / 10000
                category_areas[str(category)] = {
                    "area_ha_union": round(area, 4),
                    "share_of_municipality_pct": (
                        round(100 * area / municipality_area_ha, 4)
                        if municipality_area_ha else None
                    ),
                }

    buildings = int(joined["buildings_output"])
    if buildings != int(classification["total_buildings"]):
        raise ValueError("Gebaeudezahl in Join und Klassifikation widerspricht sich.")
    if buildings != int(osm.get("statistics", {}).get("buildings_selected", osm.get("statistics", {}).get("malta_buildings", buildings))):
        raise ValueError("Gebaeudezahl in OSM-Manifest und Join widerspricht sich.")
    join_keys = ["unique", "multiple_review", "overlap_review", "unassigned"]
    if sum(int(joined.get(key, 0)) for key in join_keys) != buildings:
        raise ValueError("Join-Statussummen stimmen nicht mit der Gebaeudezahl ueberein.")
    class_keys = ["residential_candidate", "non_residential_tag", "use_unknown"]
    if sum(int(classification.get(key, 0)) for key in class_keys) != buildings:
        raise ValueError("Klassifikationssummen stimmen nicht mit der Gebaeudezahl ueberein.")

    overlap_file = resolve_source(base, "Flaechenschnitte", "building_zoning/zoning_footprint_overlaps.csv", warnings)
    overlap_info = None
    if overlap_file is not None:
        frame = pd.read_csv(overlap_file, sep=";", encoding="utf-8-sig", dtype={"osm_id": str})
        needed = {"osm_id", "overlap_pct", "zone_idx"}
        if not needed.issubset(frame):
            raise ValueError(f"Flaechenschnitt-CSV ohne Spalten: {sorted(needed - set(frame))}")
        if frame[["osm_id", "overlap_pct"]].isna().any().any():
            raise ValueError("Fehlende Schnittflaechenwerte.")
        frame["overlap_pct"] = pd.to_numeric(frame["overlap_pct"], errors="raise")
        counts = frame.groupby("osm_id").size()
        if len(counts) != buildings:
            raise ValueError("Anzahl der Gebaeude in den Flaechenschnitten weicht ab.")
        multi_ids = counts[counts >= 2].index
        multi = frame.loc[frame["osm_id"].isin(multi_ids)].copy()
        values = multi.groupby("osm_id")["overlap_pct"].apply(lambda x: sorted(x, reverse=True))
        dominant = [v[0] for v in values]
        second = [v[1] for v in values]
        total = multi.groupby("osm_id")["overlap_pct"].sum()
        overlap_info = {
            "positive_intersection_pairs": int(len(frame)),
            "intersection_count_distribution": {str(int(k)): int(v) for k, v in sorted(counts.value_counts().items())},
            "multiple_buildings": int(len(multi_ids)),
            "dominant_99_to_100": sum(99 <= x <= 100.0001 for x in dominant),
            "dominant_90_to_under_99": sum(90 <= x < 99 for x in dominant),
            "dominant_50_to_under_90": sum(50 <= x < 90 for x in dominant),
            "dominant_other": sum(not (50 <= x <= 100.0001) for x in dominant),
            "second_ge_10": sum(x >= 10 for x in second),
            "second_ge_50": sum(x >= 50 for x in second),
            "total_gt_101": int((total > 101).sum()),
            "max_total_pct": round(float(total.max()), 4) if len(total) else 0.0,
        }
        overlap_info["dominant_50_to_under_90_details"] = {
            "50_to_under_60": sum(50 <= x < 60 for x in dominant),
            "60_to_under_70": sum(60 <= x < 70 for x in dominant),
            "70_to_under_80": sum(70 <= x < 80 for x in dominant),
            "80_to_under_90": sum(80 <= x < 90 for x in dominant),
        }
        overlap_info["second_share_30_to_under_50"] = sum(30 <= x < 50 for x in second)
        # Pair categories without implying a preferred designation.
        subset = multi.loc[multi["osm_id"].isin([
            osm_id for osm_id, vals in values.items() if 50 <= vals[0] < 90
        ])].copy()
        if "KATEGORIE" in subset and "WIDMUNG" in subset:
            def pair_label(series):
                names = sorted({str(x) for x in series.dropna()})
                return " + ".join(names) if names else "(ohne Kategorie)"
            pairs = subset.groupby("osm_id")["KATEGORIE"].apply(pair_label).value_counts()
            overlap_info["dominant_50_to_under_90_category_combinations"] = {
                str(k): int(v) for k, v in pairs.items()
            }
        if overlap_info["multiple_buildings"] != int(joined.get("boundary_review", -1)):
            warnings.append("Zahl der Mehrfachschnitte und boundary_review ist nicht identisch; Definitionen vergleichen.")

    # Version 2: build a status-aware zone x building-use table.
    cross_tab = []
    unknown_with_housenumber = None
    classified_path = base / "building_classification" / "buildings_classified.geojson"
    if classified_path.is_file():
        classified_frame = gpd.read_file(classified_path)
        needed = {"osm_id", "building_use_class", "zoning_status", "zone_kategorie", "zone_widmung"}
        if not needed.issubset(classified_frame.columns):
            warnings.append("Klassifizierte Gebaeude haben nicht alle erforderlichen Join-Spalten.")
        elif len(classified_frame) != buildings or classified_frame["osm_id"].duplicated().any():
            raise ValueError("Klassifizierte GeoJSON-Gebaeude stimmen nicht mit dem Gesamtbestand ueberein.")
        else:
            unknown = classified_frame["building_use_class"].eq("use_unknown")
            if "has_housenumber" in classified_frame:
                housenumbers = classified_frame["has_housenumber"].astype(str).str.lower().isin(["true", "1"])
            elif "addr:housenumber" in classified_frame:
                housenumbers = classified_frame["addr:housenumber"].notna() & classified_frame["addr:housenumber"].astype(str).str.strip().ne("")
            else:
                housenumbers = None
            if housenumbers is not None:
                unknown_with_housenumber = int((unknown & housenumbers).sum())
            else:
                warnings.append("Hausnummernmerkmal in klassifizierten Gebaeuden fehlt.")
            work = classified_frame[["building_use_class", "zoning_status", "zone_kategorie", "zone_widmung"]].copy()
            assigned = work["zoning_status"].eq("unique")
            work.loc[~assigned, "zone_kategorie"] = "(nicht eindeutig zugeordnet)"
            work.loc[~assigned, "zone_widmung"] = "(Prueffall)"
            work["zone_kategorie"] = work["zone_kategorie"].fillna("(ohne Kategorie)")
            work["zone_widmung"] = work["zone_widmung"].fillna("(ohne Widmung)")
            grouped = work.groupby(["zone_kategorie", "zone_widmung", "building_use_class"]).size()
            wide = grouped.unstack(fill_value=0)
            for (category, designation), row in wide.iterrows():
                cross_tab.append({
                    "kategorie": str(category), "widmung": str(designation),
                    "total": int(row.sum()),
                    **{key: int(row.get(key, 0)) for key in class_keys},
                })
            if sum(item["total"] for item in cross_tab) != buildings:
                raise ValueError("Gebaeude-Widmungs-Kreuztabelle unvollstaendig.")
    else:
        warnings.append("Klassifizierte Gebaeude-GeoJSON fehlt; Kreuztabelle nicht verfuegbar.")

    imported_zoning_count = manifest.get("outputs", {}).get("zoning", {}).get("features")
    if zoning_count is not None and imported_zoning_count is not None and int(imported_zoning_count) != zoning_count:
        raise ValueError("Widmungsanzahl stimmt nicht mit dem Import-Manifest ueberein.")
    if imported_zoning_count is not None and int(imported_zoning_count) != int(joined["zoning_input"]):
        raise ValueError("Widmungsanzahl in Manifest und Join stimmt nicht ueberein.")

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {
        "generated_utc": generated_at,
        "municipality": {"id": municipality_id, "name": municipality_name},
        "input_snapshots_utc": {
            "official": manifest.get("generated_utc"),
            "osm": osm.get("generated_utc"),
            "join": joined.get("generated_utc"),
            "classification": classification.get("generated_utc"),
        },
        "sources": {
            "municipality_geometry_date": manifest.get("municipality_geometry_date"),
            "official": manifest.get("sources", {}),
            "osm": {"source": osm.get("source"), "mode": osm.get("source_mode"),
                    "snapshot": osm.get("source_snapshot_date")},
        },
        "geometry": {
            "municipality_area_ha": municipality_area_ha,
            "zoning_category_areas": category_areas,
            "zoning_polygons": int(joined["zoning_input"]),
            "zoning_categories": categories,
            "invalid_zoning_before_repair": manifest.get("zoning_invalid_geometry_count_before_repair"),
            "invalid_zoning_repaired": manifest.get("zoning_invalid_geometry_repaired"),
            "zoning_legal_validity_verified": manifest.get("zoning_legal_validity_verified"),
        },
        "buildings": {
            "total": buildings,
            "with_housenumber": osm.get("statistics", {}).get("buildings_with_housenumber"),
            "osm_tag_counts": osm.get("statistics", {}).get("building_tag_counts", {}),
            "join": {key: int(joined.get(key, 0)) for key in join_keys},
            "boundary_review": int(joined.get("boundary_review", 0)),
            "classification": {key: int(classification.get(key, 0)) for key in class_keys},
            "unknown_building_tags": classification.get("unknown_building_tags", {}),
            "unknown_with_housenumber": unknown_with_housenumber,
            "zone_use_cross_tab": cross_tab,
        },
        "footprint_overlaps": overlap_info,
        "warnings": warnings,
        "limitations": [
            "OSM-Gebäudetags sind keine amtliche Nutzungsfeststellung.",
            "Ein positiver Flächenschnitt ist kein Nachweis der vollständigen Widmungszugehörigkeit.",
            "Die Rechtswirksamkeit der Widmungen ist nicht automatisch verifiziert.",
            "Wasserentnahmestellen, Hydranten, Netzkapazitäten und Löschwasserbedarf sind nicht untersucht.",
            "Bericht beschreibt einen Datenstand; historische Vergleiche nur mit gesonderten Vergleichsdaten.",
        ],
    }
    lines = [
        f"# Gemeindebericht – {municipality_name} ({municipality_id})",
        "",
        f"**Generiert (UTC):** {generated_at}",
        "",
        "> Automatisch erzeugter technischer Bestandsbericht; **keine** behördlich geprüfte Widmung, kein Löschwasserbedarfs- oder Versorgungsnachweis.",
        "",
        "## 1. Datenstand und Herkunft",
        "",
        md_table(["Quelle / Verarbeitung", "Zeitstempel (UTC)"], [
            ("Amtliche Geodaten importiert", manifest.get("generated_utc", "unbekannt")),
            ("OSM-Gebäude importiert", osm.get("generated_utc", "unbekannt")),
            ("Widmungszuordnung", joined.get("generated_utc", "unbekannt")),
            ("Gebäudeklassifikation", classification.get("generated_utc", "unbekannt")),
        ]),
        f"- Gemeindegrenze: Gebietsstand {manifest.get('municipality_geometry_date', 'unbekannt')}.",
        f"- OSM: {osm.get('source', 'unbekannt')} (Importmodus: {osm.get('source_mode', 'unbekannt')}).",
        f"- Amtlicher GIS-Quell-Layer: {manifest.get('zoning_layer', 'unbekannt')}; CRS der räumlichen Analyse: EPSG:{manifest.get('target_epsg', 'unbekannt')}.",
        f"- Vor Import erkannte ungültige Widmungspolygone: {manifest.get('zoning_invalid_geometry_count_before_repair', 'unbekannt')}; Reparatur: {manifest.get('zoning_invalid_geometry_repaired', 'unbekannt')}.",
        "",
        "## 2. Gemeinde, Widmung und Gebäudebestand",
        "",
        md_table(["Kennzahl", "Wert"], [
            ("Widmungspolygone", fmt(joined["zoning_input"])),
            ("OSM-Gebäude (Polygonobjekte)", fmt(buildings)),
            ("Gebäude mit OSM-Hausnummer", fmt(osm.get("statistics", {}).get("buildings_with_housenumber", 0))),
        ]),
        "### Widmungskategorien (Polygonanzahl, keine Flächenanteile)",
        "",
        md_table(["Kategorie", "Polygone"], [(k, fmt(v)) for k, v in sorted(categories.items())]) if categories else "_Keine Kategorien aus Geodatei verfügbar._",
        "",
        "### Flächenstatistik der Widmungskategorien",
        "",
        (f"**Gemeindefläche:** {municipality_area_ha:,.2f} ha".replace(",", "X").replace(".", ",").replace("X", ".")
         if municipality_area_ha is not None else "_Gemeindefläche nicht verfügbar._"),
        "",
        (md_table(["Kategorie", "Union-Fläche (ha)", "Anteil an Gemeinde"],
                  [(k, str(v["area_ha_union"]).replace(".", ","),
                    (str(v["share_of_municipality_pct"]).replace(".", ",") + " %" if v["share_of_municipality_pct"] is not None else "n/a"))
                   for k, v in sorted(category_areas.items())])
         if category_areas else "_Keine Flächenstatistik verfügbar._"),
        "**Methodik:** Flächen werden je Kategorie geometrisch vereinigt, damit Überlagerungen innerhalb einer Kategorie nicht mehrfach zählen. Kategorien können sich gegenseitig überlagern; ihre Prozentanteile dürfen nicht ungeprüft summiert werden.",
        "",
        "### OSM-Gebäudetags",
        "",
        md_table(["building-Tag", "Gebäude"], [(k, fmt(v)) for k, v in sorted(report["buildings"]["osm_tag_counts"].items(), key=lambda x: (-x[1], x[0]))]),
        "",
        "## 3. Räumliche Widmungszuordnung",
        "",
        md_table(["Ergebnis", "Gebäude"], [
            ("Eindeutiger Repräsentativpunkt-Treffer", fmt(joined.get("unique", 0))),
            ("Mehrere Punkt-Treffer: Prüfung", fmt(joined.get("multiple_review", 0))),
            ("Nur Flächenschnitt: Prüfung", fmt(joined.get("overlap_review", 0))),
            ("Keine Zuordnung", fmt(joined.get("unassigned", 0))),
            ("Weitere mögliche Grenzfälle (boundary_review)", fmt(joined.get("boundary_review", 0))),
        ]),
        "**Hinweis:** Die letzte Zeile ist eine zusätzliche Prüfmarkierung und wird nicht zu den vier Statuswerten addiert.",
        "",
    ]
    if overlap_info is not None:
        lines += [
            "### Überdeckungen der Gebäudegrundflächen",
            "",
            md_table(["Anzahl geschnittener Widmungspolygone", "Gebäude"],
                     [(k, fmt(v)) for k, v in overlap_info["intersection_count_distribution"].items()]),
            md_table(["Prüfkennzahl (nur Gebäude mit mindestens zwei Schnitten)", "Gebäude / Wert"], [
                ("Mehrfachschnitte", fmt(overlap_info["multiple_buildings"])),
                ("Größte Überdeckung 99–100 %", fmt(overlap_info["dominant_99_to_100"])),
                ("Größte Überdeckung 90–unter 99 %", fmt(overlap_info["dominant_90_to_under_99"])),
                ("Größte Überdeckung 50–unter 90 %", fmt(overlap_info["dominant_50_to_under_90"])),
                ("Zweitgrößte Überdeckung mindestens 10 %", fmt(overlap_info["second_ge_10"])),
                ("Zweitgrößte Überdeckung mindestens 50 %", fmt(overlap_info["second_ge_50"])),
                ("Summierte Überdeckung über 101 %", fmt(overlap_info["total_gt_101"])),
                ("Maximale summierte Überdeckung", str(overlap_info["max_total_pct"]).replace(".", ",") + " %"),
            ]),
            "### Vertiefung der 50–90-%-Grenzfälle",
            "",
            md_table(["Größte Überdeckung", "Gebäude"], [
                ("50–unter 60 %", overlap_info["dominant_50_to_under_90_details"]["50_to_under_60"]),
                ("60–unter 70 %", overlap_info["dominant_50_to_under_90_details"]["60_to_under_70"]),
                ("70–unter 80 %", overlap_info["dominant_50_to_under_90_details"]["70_to_under_80"]),
                ("80–unter 90 %", overlap_info["dominant_50_to_under_90_details"]["80_to_under_90"]),
            ]),
            f"Zweitgrößte Überdeckung zwischen 30 und unter 50 %: **{fmt(overlap_info['second_share_30_to_under_50'])} Gebäude** (unter allen {fmt(overlap_info['multiple_buildings'])} Mehrfachfällen).",
            "",
            (md_table(["Kombination geschnittener Kategorien", "Gebäude"],
                      [(k, fmt(v)) for k, v in sorted(
                          overlap_info.get("dominant_50_to_under_90_category_combinations", {}).items(),
                          key=lambda x: (-x[1], x[0]))])
             if overlap_info.get("dominant_50_to_under_90_category_combinations") else "_Keine Kategorienkombinationen verfügbar._"),
            "Auch hier werden keine automatischen Vorrangregeln zwischen Widmungen festgelegt.",
            "",
            "Beispiel: 99 % in Widmung A und 1 % in Widmung B ergeben **ein Gebäude mit zwei Schnitten** und **99 % größter Überdeckung**. Die dominante Widmung muss nicht Bauland sein.",
            "Kleine Schnittflächen sind nicht automatisch Datenfehler. Einzelfälle erfordern ggf. Kataster-/Orthofoto-Prüfung.",
            "",
        ]
    lines += [
        "## 4. Vorläufige Gebäudeklassifikation",
        "",
        md_table(["OSM-Klasse", "Anzahl", "Anteil"], [
            (key, fmt(classification.get(key, 0)), percent(int(classification.get(key, 0)), buildings))
            for key in class_keys
        ]),
        "**Ungeklärte OSM-building-Tags:**",
        "",
        md_table(["Tag", "Gebäude"], [(k, fmt(v)) for k, v in sorted(
            classification.get("unknown_building_tags", {}).items(), key=lambda x: (-x[1], x[0]))]),
        (f"**Ungeklärte Nutzung trotz Hausnummer:** {fmt(unknown_with_housenumber)} Gebäude."
         if unknown_with_housenumber is not None else "**Ungeklärte Nutzung trotz Hausnummer:** nicht ermittelbar."),
        "",
        "### Gebäude nach Widmung und Nutzungsklasse",
        "",
        (md_table(["Kategorie", "Widmung", "Gesamt", "Wohnen (Kandidat)", "Nichtwohnen (OSM)", "Unbekannt"],
                  [(r["kategorie"], r["widmung"], fmt(r["total"]),
                    fmt(r["residential_candidate"]), fmt(r["non_residential_tag"]), fmt(r["use_unknown"]))
                   for r in sorted(cross_tab, key=lambda x: (-x["total"], x["kategorie"], x["widmung"]))])
         if cross_tab else "_Keine Gebäudekreuztabelle verfügbar._"),
        "Die Kreuztabelle verwendet die eindeutige Repräsentativpunkt-Zuordnung; offene Fälle werden als Prüffälle ausgewiesen. Grenzüberdeckungen bleiben unabhängig davon im Prüfstatus. Eine Widmung beweist keine Gebäudenutzung.",
        "",
        "Hausnummer oder Baulandlage beweisen keine Wohnnutzung. Auch Nicht-Wohngebäude können einen relevanten Löschwasserbedarf haben.",
        "",
        "## 5. Fachliche Grenzen und offene Arbeiten",
        "",
        *[f"- {item}" for item in report["limitations"]],
        *[f"- **Unvollständige Quelle:** {item}" for item in warnings],
        "",
        "Die Klassifikations- und GIS-Regeln werden in `docs/datenqualitaet-methodik.md` sowie `docs/gebaeudeklassifikation.md` erläutert.",
        "Die Auswertung ist ein reproduzierbarer **Iststandsbericht**, keine Auswertung von Änderungen gegenüber älteren Gemeindedaten.",
        "",
    ]
    return report, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("data/processed/current"),
                        help="Gemeindeverzeichnis mit import_manifest.json sowie osm/, building_zoning/, building_classification/")
    parser.add_argument("--out-root", type=Path, default=Path("reports"),
                        help="Zielbasis; pro Gemeindekennzahl wird ein eigenes Unterverzeichnis angelegt")
    args = parser.parse_args()
    report, markdown = compute(args.base)
    municipality = report["municipality"]["id"]
    if not municipality.isdigit() or len(municipality) != 5:
        raise ValueError(f"Ungueltige Gemeindenummer: {municipality!r}")
    output = args.out_root / municipality
    output.mkdir(parents=True, exist_ok=True)
    from report_v3 import extend_report
    manifest = read_json(args.base / "import_manifest.json")
    report, markdown = extend_report(args.base, output, manifest, report, markdown)
    (output / "gemeindebericht.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "gemeindebericht.md").write_text(markdown, encoding="utf-8")
    print(f"[OK] {output / 'gemeindebericht.md'}")
    print(f"[OK] {output / 'gemeindebericht.json'}")
    print(f"[INFO] Gemeinde: {report['municipality']['name']} ({municipality})")
    print(f"[INFO] Gebaeude: {report['buildings']['total']}; Widmungen: {report['geometry']['zoning_polygons']}")
    for warning in report["warnings"]:
        print(f"[WARN] {warning}")


if __name__ == "__main__":
    main()
