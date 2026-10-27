# Skriptübersicht und Datenfluss

**Stand: 27.10.2026** · Gemeinde-Beispiel: Malta (`20619`).

Dieses Verzeichnis erklärt für **jedes Python-Skript** in [`scripts/`](../scripts/) seine Aufgabe, den Bedarf im Projekt, wesentliche Eingaben und den Speicherort der Ausgaben. Es trennt aktuelle Auswertungen von historischen Hilfswerkzeugen. `<GKZ>` steht für die fünfstellige Gemeindekennzahl. Programme mit `--out`/`--output` können alternative Zielpfade nutzen.

## Startseite / Navigation für alle Unterseiten

Der lokale Navigator [`scripts/generate_report_index.py`](../scripts/generate_report_index.py) erzeugt eine **zentrale `index.html`** und eine eigene Gemeindeseite. Er scannt ausschließlich die bereits vorhandenen Ausgabedateien in `reports/` und zeigt nur Links auf tatsächlich vorhandene Karten, Berichte und weitere HTML-Seiten. Er liest **keine** ODB-Originaldateien und führt keine Netzwerkanfragen aus.

```powershell
git pull --ff-only origin main
python scripts\generate_report_index.py --gemeinde 20619 --open
```

Anschließend sind folgende Dateien vorhanden:

- `reports/index.html` – Übersicht über alle lokal vorhandenen Gemeinden, für die bereits ein Index erstellt wurde.
- `reports/20619/index.html` – Navigation zu Malta-Karten und Berichten, inklusive `gk_inventory/gebaeude_als_hoehenkarte.html`, `gebaeude_odb_abstandskarte.html`, `odb_wasserentnahmestellen.html` sowie CSV-/JSON-Auswertungen, **soweit die jeweiligen Dateien existieren**.

Alternativ ohne `--gemeinde` sämtliche Gemeindeverzeichnisse unter `reports/` aktualisieren:

```powershell
python scripts\generate_report_index.py --open
```

**Wichtig:** Neue oder gelöschte Berichte erscheinen erst nach erneutem Generatorlauf. Der Generator erstellt nur Navigation, berechnet keine Analysen. Das `reports/`-Verzeichnis ist lokal und darf wegen der enthaltenen ODB-Daten **nicht als Ganzes öffentlich veröffentlicht werden**. HTML, CSS und Links funktionieren offline über `file://`.

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
| [`generate_report_index.py`](../scripts/generate_report_index.py) | Erzeugt eine zentrale lokale Startseite für vorhandene HTML-Karten, CSV-/JSON-Berichte und zusätzliche Unterseiten; überspringt fehlende Dateien. | `reports/<GKZ>/` mit bereits generierten Ergebnissen | `reports/index.html`, `reports/<GKZ>/index.html` |

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
| [`process_bev_als_municipality.py`](../scripts/process_bev_als_municipality.py) | **Gesamte Gemeinde:** gruppiert OSM-Gebäude in belegte 2-km-Zellen, lädt nur benötigte DSM-/DTM-Fenster, prüft/cachet sie mit SHA-256 und berechnet alle Höhenindikatoren in einer CSV. Unterstützt Planmodus, inkrementellen Download und gesonderte Analyse. | `buildings.geojson`, fixer BEV-Stichtag, online COG-Raster | `data/raw/bev/<Stichtag>/municipality_tiles/<GKZ>/<tile-id>/dom.tif`, `dgm.tif`, `manifest.json`; `reports/<GKZ>/gk_inventory/gebaeude_als_hoehen_gemeinde.csv`, `als_hoehen_gemeinde_summary.json` |
| [`review_building_als_heights.py`](../scripts/review_building_als_heights.py) | Führt den gemeindeweiten Höhenbericht per **OSM-ID** mit vorhandenen Gebäude-Tags zusammen. Ermittelt Höhe-Perzentile, heuristische Qualitätsflags und erstellt eine **offline bedienbare SVG-Karte** mit Filtern, Suche und Gebäudedetails. Keine GK- oder Löschwasserzuordnung. | `data/processed/<GKZ>/osm/buildings.geojson`, `reports/<GKZ>/gk_inventory/gebaeude_als_hoehen_gemeinde.csv` | `reports/<GKZ>/gk_inventory/gebaeude_gk_merkmale_mit_als.csv`, `als_hoehen_qualitaet.json`, `gebaeude_als_hoehenkarte.html` |
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

## Windows PowerShell: venv-Aktivierung durch Execution Policy blockiert

**Symptom:** Der Aufruf `\.\.venv\Scripts\Activate.ps1` scheitert mit **PSSecurityException / UnauthorizedAccess** und der Meldung, dass die Ausführung von Skripts deaktiviert ist.

**Ursache:** Die PowerShell-Ausführungsrichtlinie verhindert die Aktivierung per `Activate.ps1`. Die virtuelle Python-Umgebung ist dadurch nicht automatisch beschädigt.

### Empfehlung A: Python direkt aus der virtuellen Umgebung starten

Die Aktivierung ist nicht erforderlich. Der direkte Interpreter funktioniert auch bei gesperrter Skriptausführung:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_bev_als_subset.py --gemeinde 20619 --stichtag 20250915
```

Falls `.venv` noch fehlt, zuerst mit `py -m venv .venv` erstellen. Bei einem anderen venv-Namen den entsprechenden Python-Pfad verwenden.

### Alternative B: Nur für das aktuelle PowerShell-Fenster freigeben

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Die Prozesseinstellung verfällt beim Schließen des PowerShell-Fensters. Bei restriktiver Gruppenrichtlinie kann die Änderung unwirksam sein. Dann Methode A verwenden oder die IT-Administration kontaktieren.

Zum Nachsehen:

```powershell
Get-ExecutionPolicy -List
```

**Nicht erforderlich und nicht empfohlen:** Die Richtlinie nur wegen der Python-venv-Aktivierung dauerhaft für `LocalMachine` oder `CurrentUser` mit `Unrestricted` oder `Bypass` lockern. Keine Administratorrechte nötig.

Weitere Infos: [Microsoft: about_Execution_Policies](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_execution_policies).

## Fehlerbehebung: BEV-ALS „Ausschnitt nicht am Pixelgitter ausgerichtet“

**Beobachteter Fehler beim BEV-Pilot am 27.10.2026:**

```text
[INFO] DSM Ausschnitt per HTTPS-Range: https://data.bev.gv.at/download/ALS/DSM/20250915/ALS_DSM_CRS3035RES50000mN2650000E4550000.tif
ValueError: DSM: Ausschnitt nicht am Pixelgitter ausgerichtet
```

**Ursache:** Version 1 von `download_bev_als_subset.py` berechnete den Ausschnitt aus ganzzahligen EPSG:3035-Meterkoordinaten und nahm fälschlich an, diese seien automatisch **Pixelgrenzen im Original-GeoTIFF**. Das Raster besitzt aber einen eigenen GeoTIFF-Transformationsursprung. Das Programm konnte die BEV-Datei bereits öffnen; es stoppte bei seiner lokalen Rastergitterprüfung, **vor dem Schreiben des DSM-Ausschnitts**.

**Korrektur:** Seit Commit `a693ccd` wird der angefragte Ausschnitt nach außen an die **tatsächlichen Rasterpixel des DSM** angepasst. Das DTM muss dieselben Pixelgrenzen, den gleichen Rastertransform und dieselben Dimensionen besitzen. Falls nicht, stoppt das Skript **ohne stillschweigendes Resampling**, um verfälschte Höhenunterschiede zu vermeiden.

```powershell
git pull --ff-only origin main
python scripts\download_bev_als_subset.py --gemeinde 20619 --stichtag 20250915
```

**Falls ein früherer Lauf bereits eine lokale TIFF-Datei erzeugt hat:** Das Skript überschreibt sie bewusst nicht. Vor einem erneuten Versuch die vorhandene Datei/deren Herkunft prüfen; nur bekannte, unvollständige Pilotdateien gezielt entfernen. Bei erneutem Fehler die Ausgabe mit **Rasterursprung, Dimensionen und der konkreten DSM-/DTM-Fehlermeldung** dokumentieren. Ein korrektes DSM-/DTM-Gitter ist Voraussetzung für `analyze_buildings_als_height.py`.


## Gesamter BEV-Datenbestand für Malta – kleine, wiederverwendbare Teilfenster

Nach erfolgreichem 2 × 2 km-Pilot (**389 geschätzte Gebäudehöhen, 1.290 Gebäude außerhalb des Pilotausschnitts**) ergänzt `process_bev_als_municipality.py` die **gebäudeweise flächendeckende** Höhenanalyse. Dabei werden **nur Zellen mit OSM-Gebäuden** berücksichtigt; je Zelle wird die tatsächlich benötigte **Gebäudeumhüllende plus 5 m** aus dem jeweiligen BEV-COG gelesen. Das Skript lädt **keine 50-km-Originalkacheln**. Es benutzt für DOM und DGM dasselbe tatsächliche 1-m-Raster und führt die Qualitätskontrollen des Pilot-Analysers aus.

**Schritt 1: Downloadplan anzeigen, noch ohne Datenübertragung:**

```powershell
git pull --ff-only origin main
python scripts\process_bev_als_municipality.py --gemeinde 20619 --stichtag 20250915
```

**Schritt 2: Zunächst maximal drei Zellen herunterladen und prüfen:**

```powershell
python scripts\process_bev_als_municipality.py --gemeinde 20619 --stichtag 20250915 --download --max-tiles 3
```

**Schritt 3: Nach erfolgreichem Pilot alle übrigen benötigten Ausschnitte beziehen:**

```powershell
python scripts\process_bev_als_municipality.py --gemeinde 20619 --stichtag 20250915 --download
```

**Schritt 4: Über alle 1.686 Gebäude einen zusammengeführten Bericht erstellen:**

```powershell
python scripts\process_bev_als_municipality.py --gemeinde 20619 --stichtag 20250915 --analyze
```

Alternativ `--download --analyze` für Download und Gesamtauswertung in einem Aufruf. Die ursprünglichen Pilotraster bleiben unangetastet. Die Gemeindeergebnisse bekommen **eigene Dateinamen**, um `gebaeude_als_hoehen.csv` aus dem ersten Pilot nicht zu überschreiben.

**Wiederaufnahme:** Ein erfolgreich bezogener DSM-/DTM-Kachel-Ausschnitt liegt zusammen mit genauen Quell-URLs, Ausschnittskoordinaten, BEV-Stichtag und SHA-256-Werten im lokalen `manifest.json`. Bei erneuten Läufen wird dieser Cache verifiziert. Fehlende Dateien werden heruntergeladen, sofern kein widersprüchlicher/teilweise vorhandener Cache vorliegt. **Cache-Korruption, Rasterunterschiede und nicht vollständig erfasste Gebäude am 50-km-BEV-Kachelrand führen zu einer klaren Fehlermeldung bzw. eigenem Qualitätsstatus** statt zu stiller Nutzung. Kachel-/Gebäudegeometrien ändern sich möglicherweise durch einen neuen OSM-Import; der aktuelle Cache kann dann nur bei übereinstimmenden Ausschnittgrenzen genutzt werden.

**Noch offen:** Für Gebäude, die eine 50-km-BEV-Kachelgrenze überschreiten, wird zunächst `crosses_bev_tile` dokumentiert – diese benötigen einen späteren expliziten Mehrkachel-Abgleich. Wegen Bewuchs, Dachgeometrie, historischen Befliegungen und Rasterwerten bleibt auch `estimated` eine **nicht überprüfte Objekthöhe**. Kein automatischer Rückschluss auf Fluchtniveau, Geschosszahl oder GK.


## Gebäudehöhen gemeinsam prüfen: Bericht und Offline-Karte

Nach dem erfolgreichen gemeindeweiten BEV-ALS-Lauf mit **1.634 geschätzten Objekthöhen und 52 Fällen mit zu wenigen Pixeln**:

```powershell
git pull --ff-only origin main
python scripts\review_building_als_heights.py --gemeinde 20619 --open
```

Das Skript benötigt nur die bereits vorhandenen **lokalen** Gebäudegrundrisse und `gebaeude_als_hoehen_gemeinde.csv`; es führt **keinen Download** aus. Es vergleicht die OSM-IDs **streng eins zu eins** und stoppt, wenn Gebäude zwischenzeitlich importiert, gelöscht oder umnummeriert wurden. Dadurch werden keine Höhen einem falschen Gebäude zugeordnet.

Lokale Ergebnisse:
- `reports/20619/gk_inventory/gebaeude_gk_merkmale_mit_als.csv`: kombinierte OSM-Attribute, geometrische Grundfläche, BEV-Höhenindikatoren, Qualität, Prüfhinweise; `gk_actual=unknown`.
- `reports/20619/gk_inventory/als_hoehen_qualitaet.json`: Anzahl nach Status, Höhenverteilung (Median, P05 und P95) und Prüfflag-Häufigkeiten.
- `reports/20619/gk_inventory/gebaeude_als_hoehenkarte.html`: vollständig lokale SVG-Übersicht aller Gebäude, mit Farbklassen, Ein-/Ausblenden, OSM-ID-Suche, Zoom und anklickbaren Details.

Die Farbklassen **unter 3 / 3–6 / 6–9 / 9–12 / 12–18 / ab 18 m** sind frei gewählte **Visualisierungsintervalle und ausdrücklich keine OIB-GK-Grenzen**. Prüfhinweise sind ebenfalls **nur heuristisch**: geschätzter Median unter 1 m, ab 25 m, große Differenz von Maximum zu Median ab 10 m oder Rasterabdeckung unter 85 %. Gebäude mit `too_few_pixels` werden gesondert gekennzeichnet. Alle Statistiken zur Höhenverteilung berücksichtigen nur Datensätze mit `quality=estimated`. Dachaufbauten, Bäume, unterschiedliche ALS-Aufnahmedaten und kleine Gebäude können Abweichungen verursachen.

Die Karte benötigt **keine externe Karten-API** und enthält keine ODB-Wasserquellen. Trotzdem bleiben CSV, JSON und HTML unter dem lokal gehaltenen `reports/`-Ordner. **Objekthöhe ≠ OIB-Fluchtniveau; weder Geschosszahl noch GK oder Löschwasserbedarf werden daraus bestimmt.**

## Fehlerbehebung: Gebäudehöhenkarte zeigt keine Details; Gemeindegrenze und Wege fehlen

**Beobachtung vom 27.10.2026:** In `gebaeude_als_hoehenkarte.html` erschien der Hinweis „Gebäude auf der Karte anklicken“, aber beim Klicken keine Detailanzeige. Außerdem fehlten die aus der ODB-Karte bekannten Gemeindegrenze und OSM-Straßen/Wege.

**Ursache der Klickstörung:** Der erste Kartenstand leitete jeden `pointerdown`-Vorgang an die Verschiebefunktion weiter und nutzte `setPointerCapture()` auch über einem Gebäude. Dadurch konnte der nachfolgende Klick statt beim Gebäude bei der SVG-Karte landen.

**Korrektur:** Der Drag-Modus startet nur noch auf dem freien Kartenbereich. Gebäudepolygone erhalten wieder ihre eigenen Klickereignisse. Zudem werden die amtliche Gemeindegrenze aus `data/processed/<GKZ>/boundary.geojson` und optionale Straßen/Wege aus `data/processed/<GKZ>/osm/roads.geojson` als **getrennt ein-/ausblendbare SVG-Ebenen** eingebaut. Die Ebenen liegen hinter den Gebäuden und fangen keine Mausklicks ab. Die Straßen zeigen lediglich OSM-Verläufe, **keine berechnete Fahr-/Schlauchroute**.

Nach Update die **HTML-Datei neu erzeugen** und den Browser-Tab ggf. mit `Strg+F5` aktualisieren:

```powershell
git pull --ff-only origin main
python scripts\review_building_als_heights.py --gemeinde 20619 --open
```

Die Ausgabedatei bleibt `reports/20619/gk_inventory/gebaeude_als_hoehenkarte.html`. Der Befehl erstellt daneben die bereits bekannten CSV-/JSON-Dateien erneut; die BEV-Raster werden **nicht** noch einmal heruntergeladen. Wenn `roads.geojson` fehlt, zeigt die Karte 0 Straßen/Wege an, ohne die Gebäudekarte zu verhindern.

**Hausnummern in der ALS-Karte:** Die OSM-Attribute `addr:street`, `addr:housenumber` und `addr:city` werden im Gebäudeimport soweit vorhanden beibehalten. Seit Commit `c58797e` übernimmt auch `review_building_als_heights.py` diese Felder in `gebaeude_gk_merkmale_mit_als.csv` und zeigt Straße/Hausnummer/Ort in den Gebäudedetails. Fehlende OSM-Adressattribute bleiben leer; die separat importierten amtlichen Hausnummern werden dadurch **noch nicht** automatisch gebäudeweise verknüpft.
