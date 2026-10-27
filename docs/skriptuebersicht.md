# Skriptübersicht und Datenfluss

**Stand: 27.10.2026** · Gemeinde-Beispiel: Malta (`20619`).

Dieses Verzeichnis erklärt für **jedes Python-Skript** in [`scripts/`](../scripts/) seine Aufgabe, den Bedarf im Projekt, wesentliche Eingaben und den Speicherort der Ausgaben. Es trennt aktuelle Auswertungen von historischen Hilfswerkzeugen. `<GKZ>` steht für die fünfstellige Gemeindekennzahl. Programme mit `--out`/`--output` können alternative Zielpfade nutzen.

## Verzeichnisse und Datenschutz

| Verzeichnis | Verwendung | Veröffentlichung |
| --- | --- | --- |
| `data/raw/` | Originaldaten: Geofabrik-PBF, ODB-Export, BEV-ALS-Raster, amtliche Quellen | Lokal halten |
| `data/processed/<GKZ>/` | Transformierte Geodaten, Gemeindegrenze, Widmung, OSM-Gebäude/-Straßen, ODB-Punkte | Lokal halten |
| `data/processed/current/` | Frühere Malta-spezifische GIS-Auswertung und Zwischenstände | Lokal halten |
| `reports/<GKZ>/` | CSV/JSON-Ergebnisse, Offline-HTML-Karten, Qualitätsberichte | Lokal halten |
| `config/` | Öffentliche Klassifikationsregeln und GK-Regelwerksentwürfe | Im Repository |
| `docs/` | Bedienung und Methodik | Im Repository |

**Wichtig:** Die Wasserquellen des **aktuellen** Untersuchungswegs stammen **ausschließlich aus der lokal autorisiert exportierten Kärntner Objektdatenbank (ODB)**. Die historischen OSM-Wasserquellenskripte bleiben für Rückverfolgbarkeit bestehen, werden aber **nicht** in aktuelle Abstandsanalysen, Gebäude-Karten oder Versorgungsberichte eingebunden. Nur die OSM-**Gebäude** und OSM-**Straßen/Wege** werden dafür verwendet. Die private ODB-Datei und sämtliche daraus erzeugte Karten dürfen nicht unbesehen veröffentlicht werden.

## A. Grunddaten importieren – aktuelle Pipeline

| Skript | Was und warum? | Wesentliche Eingaben | Erzeugte Daten |
| --- | --- | --- | --- |
| [`import_geodata.py`](../scripts/import_geodata.py) | Importiert amtliche Gemeindegrenze und Kärntner Flächenwidmung. Räumlicher Bezugsrahmen für alle Zuordnungen. | Amtliche Statistik-Austria-/KAGIS-Dateien, ggf. `--download`, `--zoning-gpkg` | `data/processed/<GKZ>/boundary.geojson`, `zoning.geojson`, `bauland.geojson`, `import_manifest.json` |
| [`import_osm_buildings_pbf.py`](../scripts/import_osm_buildings_pbf.py) | Liest Gebäudegrundrisse und GK-relevante **OSM-Indizien** offline aus dem österreichischen PBF. Umgeht Overpass-Ausfälle. | `data/raw/austria-latest.osm.pbf`, `boundary.geojson`, amtliches Manifest | `data/processed/<GKZ>/osm/buildings.geojson`, `osm_manifest.json` |
| [`import_osm_roads_pbf.py`](../scripts/import_osm_roads_pbf.py) | Importiert OSM-Straßen und -Wege als **Orientierungshintergrund**, noch kein Routing oder Schlauchweg. | Geofabrik-PBF und Gemeindegrenze | `data/processed/<GKZ>/osm/roads.geojson`, `roads_manifest.json` |
| [`import_odb_water_sources.py`](../scripts/import_odb_water_sources.py) | Bereitet den **lokalen autorisierten ODB-Export** auf und berücksichtigt Quellentyp und Status. Einzige Wasserquellenbasis der aktiven Analyse. | Privater Export, z. B. `data/raw/odb_wasserentnahmestellen.geojson`, Gemeindegrenze | `data/processed/<GKZ>/odb_water_sources/odb_water_sources.geojson`, `odb_water_sources.csv`, `odb_water_sources_manifest.json` |
| [`import_osm.py`](../scripts/import_osm.py) | Alternativer/älterer OSM-Gebäudeimport aus lokaler GeoJSON oder OSMnx/Overpass. Enthält außerdem von den PBF-Importern genutzte Hilfsfunktionen/Feldliste. | `--input` oder `--download`, Gemeindegrenze | Im gemeindebezogenen Modus `data/processed/<GKZ>/osm/buildings.geojson`, `osm_manifest.json`; älterer Modus unter `data/processed/current/osm/` |

## B. ODB-Bestandsaufnahme, Gebäudeabstände und Offline-Karten – aktuell

| Skript | Was und warum? | Eingaben | Erzeugte Daten |
| --- | --- | --- | --- |
| [`analyze_odb_water_sources.py`](../scripts/analyze_odb_water_sources.py) | Rein beschreibende Bestandsanalyse: Anzahl, Typen, Status und räumliche Kennzahlen der ODB-Punkte. | Importiertes ODB-GeoJSON | `reports/<GKZ>/odb_bestandsanalyse.csv`, `odb_bestandsanalyse.json` |
| [`show_odb_water_sources.py`](../scripts/show_odb_water_sources.py) | Zeigt ODB-Quellen und Gemeindegrenze als lokale interaktive Karte ohne Internet-Kartenkacheln. | ODB-GeoJSON, Gemeindegrenze | `reports/<GKZ>/odb_wasserentnahmestellen.html` |
| [`analyze_buildings_odb_distance.py`](../scripts/analyze_buildings_odb_distance.py) | Berechnet für jedes OSM-Gebäude die kürzeste **Luftlinie von der Gebäudegrundfläche** zur nächsten ODB-Quelle mit Status 1; eingeschränkt verwendbare Quellen separat. Keine hydraulische Prüfung. | OSM-Gebäude, ODB-GeoJSON, Gemeindegrenze | `reports/<GKZ>/gebaeude_odb_abstaende.csv` und `gebaeude_odb_abstaende.json` |
| [`show_buildings_odb_distance.py`](../scripts/show_buildings_odb_distance.py) | Interaktive Karte mit Abstandsklassen, ODB-Punkten, optionalen OSM-Straßen und anklickbarer Verbindung Gebäude–Quelle. | Gebäude, ODB, Grenze, Gebäudeabstands-CSV, optional `roads.geojson` | `reports/<GKZ>/gebaeude_odb_abstandskarte.html` |

**Interpretation:** Alle bisherigen Abstände sind geometrische Luftlinien; Straßenfarben, Abstandsklassen und Punkte belegen weder eine geeignete Schlauchführung noch die tatsächliche Entnahmeleistung.

## C. GK-Regelwerk und Gebäudeeigenschaften – aktueller Entwicklungszweig

| Skript | Was und warum? | Eingaben | Erzeugte Daten |
| --- | --- | --- | --- |
| [`validate_firewater_rulebook.py`](../scripts/validate_firewater_rulebook.py) | Kontrolliert **formal** den versionierten GK-/TRVB-Regelwerksentwurf: Definitionseinträge, Teilraten, Quellen, Volumenrechnung und Sperren für ungeprüfte automatische Einstufungen. | `config/firewater_rulebook.json` | Konsolenausgabe, **keine Ausgabedatei**, keine fachliche Freigabe |
| [`inventory_gk_building_attributes.py`](../scripts/inventory_gk_building_attributes.py) | Inventarisiert bei **allen** Gebäuden vorhandene OSM-Nutzungs-, Höhen- und Geschossindizien sowie fehlende **verifizierte** GK-Merkmale. Vergibt keine GK. | `data/processed/<GKZ>/osm/buildings.geojson` | `reports/<GKZ>/gk_inventory/gebaeude_gk_merkmale.csv`, `summary.json` |
| [`download_bev_als.py`](../scripts/download_bev_als.py) | Wählt BEV-ALS-Kacheln reproduzierbar anhand der Gebäude-/Gemeindegeometrie aus; erstellt Plan oder lädt auf ausdrückliches `--download` komplette DSM/DTM-Kacheln. **Sehr große Dateien, nicht Standard für den Pilotversuch.** | Gebäude bzw. Grenze; fixer BEV-Stichtag | Optional `data/raw/bev/<Stichtag>/DSM/` und `DTM/` mit Original-TIFFs sowie `bev_als_<GKZ>_<source>_lock.json` (URL, SHA-256) |
| [`download_bev_als_subset.py`](../scripts/download_bev_als_subset.py) | **Bevorzugter Pilot:** Liest kleine, gleich ausgerichtete Ausschnitte aus den BEV-COG-Rastern über HTTPS-Teilabrufe. Vermeidet komplette 50-km-Kacheln. | Gebäude-Geometrie; Stichtag; optional Gebäude-ID, Radius; GDAL/rasterio mit HTTP-Range-Unterstützung | `data/raw/bev/<Stichtag>/subsets/<GKZ>/dom_malta.tif`, `dgm_malta.tif`, `subset_manifest.json` |
| [`analyze_buildings_als_height.py`](../scripts/analyze_buildings_als_height.py) | Verknüpft OSM-Grundrisse mit einem passenden DOM-/DGM-Rasterpaar; berechnet Median, P90, Maximum und Qualitätsflags der **geschätzten Objekthöhe**, nicht Fluchtniveau oder GK. | `buildings.geojson`, passend ausgerichtete lokale DOM-/DGM-GeoTIFFs, identische Höhenreferenz und Datenstand | `reports/<GKZ>/gk_inventory/gebaeude_als_hoehen.csv`, `als_hoehen_summary.json` |

Für den nächsten Test **nicht** `download_bev_als.py --download` ausführen. Der Vollkachel-Download für Malta ist bereits an der 8-GiB-Sicherheitsgrenze gescheitert. Die kleinen Ausschnitte sind der praktikable Versuch.

```powershell
git pull --ff-only origin main
python scripts\download_bev_als_subset.py --gemeinde 20619 --stichtag 20250915
```

Das Skript sucht zunächst automatisch ein zentral gelegenes Gebäude und fordert einen 2 × 2 km großen DSM-/DTM-Ausschnitt an. HTTP-Range- und GDAL-Unterstützung müssen im lokalen Versuch bestätigt werden. Es wird **kein** gesamter Gemeinde-Datensatz heruntergeladen. Erst anschließend die beiden erhaltenen GeoTIFFs mit `analyze_buildings_als_height.py` verarbeiten.

## D. Flächenwidmung, Berichte und Qualitätsprüfung – ältere/ergänzende Strecke

| Skript | Was und warum? | Eingaben | Erzeugte Daten |
| --- | --- | --- | --- |
| [`join_buildings_zoning.py`](../scripts/join_buildings_zoning.py) | Schichtet Gebäude und Widmung räumlich übereinander; identifiziert mehrdeutige Überdeckungen ohne erfundene Widmungspriorität. | Gebäude- und Widmungs-GeoJSON | `data/processed/current/building_zoning/buildings_with_zoning.geojson`, `zoning_candidates.csv`, `zoning_footprint_overlaps.csv`, `zoning_review.csv`, `summary.json` (oder `--out`) |
| [`classify_buildings.py`](../scripts/classify_buildings.py) | Ordnet OSM-Tags konservativ in Nutzungsindikatoren (`residential_candidate`, `non_residential_tag`, `use_unknown`) ein. **Keine GK1–GK5.** | Gebäudewidmungs-Geodaten, `config/building_classification.json` | `data/processed/current/building_classification/buildings_classified.geojson`, `summary.json` (oder `--out`) |
| [`generate_municipality_report.py`](../scripts/generate_municipality_report.py) | Erstellt den deskriptiven Gemeindebericht aus **bereits vorhandenen** Widmungs-/Gebäude-/Klassifikationsergebnissen. Kein Download und keine Löschwasserversorgungsprüfung. | Import-Manifest, OSM-/Zoning-Ergebnisse, ggf. Klassifikation | `reports/<GKZ>/gemeindebericht.md`, `gemeindebericht.json`; zusätzliche Review-Dateien nach Datenstand |
| [`report_v3.py`](../scripts/report_v3.py) | Hilfsmodul für Erweiterungen des Gemeindeberichts (Flächenbilanz, Grenzfälle, GIS-Prüfdaten). **Nicht direkt aufzurufen.** | Vom Report-Generator aufbereitete Daten | Zusätzliche Berichtsteile/Prüfexports über den aufrufenden Report-Generator |
| [`building_context.py`](../scripts/building_context.py) | Hilfsmodul für lokale Lagekarte/Ausschnitt eines Gebäudes; wird von Kartenskripten verwendet. **Nicht direkt aufzurufen.** | Gemeindegrenze, Gebäudegeometrie | HTML-/SVG-Fragmente über aufrufendes Skript, keine eigenständige Standarddatei |
| [`municipality_text.py`](../scripts/municipality_text.py) | Korrigiert nur erkennbare fehlerhafte UTF-8-Darstellungen in Ortsnamen für Berichte. **Nicht direkt aufzurufen.** | Zeichenketten aus anderen Modulen | Rückgabewert an aufrufendes Skript, keine Datei |
| [`show_building_zoning.py`](../scripts/show_building_zoning.py) | Öffnet einzelne Gebäude und ihre Widmungs-Schnittflächen zur manuellen Prüfung im Browser. | Gebäude, Widmung, OSM-ID | `reports/<GKZ>/haus_<osm-id>.html` oder `--out` |
| [`list_building_overlaps.py`](../scripts/list_building_overlaps.py) | Erstellt Übersicht über Gebäude mit mehreren positiven Widmungsüberschneidungen und anklickbaren Einzelansichten. | Verfügbare Gebäude-/Widmungsanalysen | Lokales `reports/<GKZ>/`-Verzeichnis mit `ueberlappungen.csv`, `index.html` und Einzel-HTML-Dateien |
| [`compare_osm.py`](../scripts/compare_osm.py) | Vergleicht zwei historische OSM-Gebäudestände über stabile OSM-IDs; erkennt Hinzugekommene, Entfernte und Veränderte. | `previous`, `current` | Standard `data/processed/osm_comparison/`: `added_buildings.csv`, `removed_buildings.csv`, `changed_buildings.csv`, `added_buildings.geojson`, `summary.json` |
| [`compare_zoning.py`](../scripts/compare_zoning.py) | Vergleicht zwei Widmungsstände und identifiziert geänderte Flächen; kein rechtsverbindlicher Widmungsnachweis. | `previous`, `current` | Standard `data/processed/zoning_comparison/`: `matched_changes.csv`, `unmatched_current.csv/.geojson`, `unmatched_previous.csv`, `previous_zoning_overlaps.csv`, `summary.json` |
| [`check_project.py`](../scripts/check_project.py) | Lesender Check für Python-Umgebung, Git und lokale Gemeindedateien. Zur Fehlersuche vor Import/Analyse. | Optional GKZ, `--json` | Konsolenausgabe; bei `--json` strukturierte Ausgabe, keine Datenänderung |
| [`run_municipality.py`](../scripts/run_municipality.py) | Orchestriert die **ältere** Gemeinde-Pipeline für amtliche Geodaten, OSM, Widmung und Bericht. **Keine vollständige ODB-/GK-/ALS-Automation.** | Importquellen, GKZ, mehrere Optionen | Ruft weitere Skripte auf; Ausgaben unter `data/processed/<GKZ>/` und ggf. `reports/<GKZ>/` |

## E. Historische/ausgeschlossene OSM-Wasserquellen-Werkzeuge

Diese Programme sind für die **aktuelle ODB-basierte Löschwasserversorgungsanalyse deaktiviert**. Ihre Ergebnisse sind kein Bestandteil der aktiven Gebäudekarte oder des GK-/ALS-Workflows.

| Skript | Historischer Zweck | Eingaben | Früherer/lokaler Speicherort |
| --- | --- | --- | --- |
| [`import_water_sources.py`](../scripts/import_water_sources.py) | Importiert OSM-`emergency=*`-Wasserobjekte zu rein deskriptiven Vergleichen. **Nicht aktive Wasserquelle.** | OSM-PBF, Overpass oder lokaler Export | `data/processed/<GKZ>/water_sources/water_sources.geojson`, `water_sources.csv`, `water_sources_manifest.json` |
| [`compare_water_sources.py`](../scripts/compare_water_sources.py) | Vergleicht räumliche Nähe historischer OSM-Wasserobjekte zu ODB-Punkten. **Keine Identitäts- oder Versorgungsbestätigung.** | Historisches OSM-Wasser-GeoJSON und privates ODB-GeoJSON | Lokale Vergleichsausgabe: `osm_odb_nearest.csv`, `comparison_summary.json` im Analyseordner |
| [`plot_osm_water_sources.py`](../scripts/plot_osm_water_sources.py) | Erstellt ausschließlich eine ältere PNG-Karte mit OSM-Wasserobjekten. **Nicht aktuelle Karte.** | Lokale historische OSM-Wasserquellen und Gemeindegrenze | Lokaler PNG-Report unter `reports/<GKZ>/` oder `--output` |

## Empfohlene Reihenfolge für Malta

```text
Amtliche GIS-Daten ── import_geodata.py
                    ├── import_osm_buildings_pbf.py ── Gebäude
                    ├── import_osm_roads_pbf.py ────── Straßenhintergrund
                    └── import_odb_water_sources.py ─ ODB-Quellen (privat)
                                  │
                 analyze_buildings_odb_distance.py
                                  │
                 show_buildings_odb_distance.py
                                  │
      Separater AP2-Zweig: inventory_gk_building_attributes.py
                                  │
            download_bev_als_subset.py (Pilot)
                                  │
            analyze_buildings_als_height.py
                                  │
    Später: belegte GK-Zuordnung und Grund-/Objektschutz-Prüfung
```

Die `validate_firewater_rulebook.py`-Prüfung läuft unabhängig davon auf dem Versionsstand `config/firewater_rulebook.json`. Das aktuelle Regelwerk ist noch ein **fachlich freizugebender Entwurf**, keine automatische GK-Zuordnung oder rechtliche Bedarfsfeststellung.

## Weitere Dokumentation

- [Gebäudeklassen und Löschwasserbedarf](gebaeudeklassen-und-loeschwasserbedarf.md)
- [ODB-Wasserentnahmestellen](odb-wasserentnahmestellen.md)
- [Gemeindebericht](gemeindebericht.md)
- [Rechtsgrundlagen](rechtsgrundlagen.md)
