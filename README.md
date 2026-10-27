# Löschwasserversorgung – Analysewerkzeug (Referenzgemeinde Malta)

Analyseprojekt zur räumlichen Untersuchung der Siedlungsstruktur und zur **vorbereitenden** Bewertung der Löschwasserversorgung in Kärntner Gemeinden. Malta (20619) dient als bisherige Referenzgemeinde.

> **Status: Neuaufbau / fachliche Validierung ausständig.** Die vorhandenen Python-Prototypen und deren Grenzwerte sind noch nicht als gültige Löschwasserbedarfsberechnung freigegeben. Ergebnisse sind weder eine behördliche Feststellung noch ein Nachweis einer ausreichenden Löschwasserversorgung.

## Ziele

- Amtliche Gemeindegrenze, Flächenwidmung und rechtswirksame Bebauungspläne mit dokumentiertem Datenstand erfassen.
- OpenStreetMap-Gebäude nachvollziehbar klassifizieren und räumliche Siedlungsanalysen durchführen.
- Rechtliche Anforderungen, technische Richtwerte und algorithmische Heuristiken klar trennen.
- Erst nach fachlicher Validierung einen Löschwasserbedarf ableiten und später mit gesicherten Versorgungsdaten abgleichen.

## Bisheriger Prototyp (noch nicht veröffentlicht)

1. OSM-GeoJSON aus Overpass importieren und Wohngebäude-Kandidaten filtern.
2. Gebäudedichte in einem konfigurierbaren Radius ermitteln.
3. Gebäude mit DBSCAN clustern und Siedlungsflächen ableiten.

Die bisherige Kennzeichnung `800_lpm` basiert auf **nicht validierten Parametern** (Gebäudeanzahl/Dichte); sie darf nicht als normative Forderung interpretiert werden.

## Repository-Struktur

- `docs/rechtsgrundlagen.md`: Rechtsquellen, technische Regelwerke und offene Prüfaufgaben.
- `data/sources.json`: Datenquellenregister für die geplante Erhebung.
- `.gitignore`: Ausschluss lokaler Umgebungen und generierter GIS-Daten.
- `scripts/import_geodata.py`: Beschaffung und Zuschnitt amtlicher Geodaten.
- `docs/import.md`: Ausführungsanleitung.
- `scripts/import_osm.py`: OSM-Gebäudeimport aus lokalem Export oder via Overpass.
- `scripts/import_water_sources.py` und `docs/loeschwasserquellen-osm.md`: Eigenständige erste OSM-Bestandsaufnahme von Hydranten, Saugstellen, Löschwasserbehältern und Löschwasserteichen; ohne Leistungs- oder Eignungsnachweis.
- `scripts/import_odb_water_sources.py` und `docs/odb-wasserentnahmestellen.md`: Separater lokaler Import von berechtigt exportierten Objektdatenbank-Wasserentnahmestellen (GeoJSON-Kategorie 1724).
- `docs/osm-import.md`: Anleitung und Datenherkunft zum OSM-Import.
- `docs/datenqualitaet-methodik.md`: Messergebnisse, Unsicherheiten und Prüfplan zur geometrischen Widmungszuordnung.
- `scripts/classify_buildings.py` und `config/building_classification.json`: Konservative Klassifikation der OSM-Gebäudetags.
- `docs/gebaeudeklassifikation.md`: Regeln und Grenzen der Gebäudezuordnung.
- `scripts/run_municipality.py`: Gemeindebezogener Gesamtlauf von Geodatenimport bis Gemeindebericht.
- `scripts/check_project.py` und `docs/projektcheck.md`: Lokaler Projektcheck (Python-Pakete, Git, Rohdaten, Gemeindeimporte und Löschwasserquellen) mit Handlungsempfehlungen.
- `docs/gemeinde-pipeline.md`: Anleitung für weitere Kärntner Gemeinden und Regressionstest.
- `scripts/show_building_zoning.py` und `docs/einzelgebaeude-visualisierung.md`: Einzelgebäude mit den tatsächlich geschnittenen Widmungspolygonen offline als HTML anzeigen (ohne QGIS).
- `scripts/list_building_overlaps.py`: Durchsuchbare HTML-/CSV-Gesamtliste aller Gebäude mit Mehrfachschnitt, inklusive anklickbarer grafischer Detailansichten.
- `scripts/generate_municipality_report.py`: Generiert einen Gemeindereport (Markdown und JSON) aus den vorhandenen Auswertungen.
- `docs/gemeindebericht.md`: Aufbau, Ausführung und Datenanforderungen des Gemeindeberichts.

Der Geodatenimport und die Gemeinde-Pipeline wurden für Malta (20619) regressionsgeprüft und für Gmünd in Kärnten (20608) erfolgreich ausgeführt; siehe [Gemeinde-Pipeline](docs/gemeinde-pipeline.md). Eine fachlich validierte Löschwasserbedarfsberechnung und umfassende automatisierte Tests stehen noch aus.

## Git und lokale Entwicklungsumgebung (Windows)

Standardverzeichnis für lokale Projekte: `C:\pyprojects`. Die folgenden Befehle sind für **CMD (Eingabeaufforderung)** ausgelegt. In PowerShell funktioniert die Git-Bedienung gleich, aber die Aktivierung der virtuellen Python-Umgebung unterscheidet sich.

### Git auf einem neuen Rechner installieren (einmalig)

```powershell
winget install --id Git.Git -e --source winget
```

**Danach das Terminal schließen und neu öffnen**, damit `git` im PATH verfügbar ist.

```bat
git --version
```

### Repository zum ersten Mal klonen

Nur verwenden, wenn das Projektverzeichnis **noch nicht existiert**:

```bat
mkdir C:\pyprojects
cd /d C:\pyprojects
git clone https://github.com/lexxi/loeschwasserversorgung.git
cd loeschwasserversorgung
git status
```

Falls `C:\pyprojects` bereits existiert, ist `mkdir` nicht erforderlich. Ein vorhandenes lokales Projektverzeichnis nicht durch erneutes Klonen überschreiben.

### Lokalen Projektstand prüfen (besonders beim Rechnerwechsel)

```powershell
python scripts\check_project.py
```

Das Skript benötigt keine zusätzlichen Python-Pakete, führt keine Downloads oder Änderungen durch und zeigt die fehlenden Bestandteile sowie nächste Befehle an. Weitere Optionen: [Projektcheck](docs/projektcheck.md).

### Bestehendes Repository aktualisieren

```bat
cd /d C:\pyprojects\loeschwasserversorgung
git status
git pull --ff-only origin main
```

Bei lokalen Änderungen oder Konflikten nicht blind überschreiben: zuerst `git status` prüfen und Änderungen sichern.

### Änderungen prüfen und veröffentlichen

Nur beabsichtigte **Code- und Dokumentationsdateien** aufnehmen; keine ungeprüften GIS-Rohdaten, Ausgabedateien, Zugangsdaten oder die virtuelle Umgebung.

```bat
git status
git diff
git add README.md
git diff --cached
git commit -m "docs: update README"
git push origin main
```

`git add README.md` ist ein Beispiel. Für andere Änderungen gezielt die entsprechenden Dateipfade angeben. Nicht unkontrolliert `git add .` verwenden.

### Python-Umgebung (CMD)

```bat
cd /d C:\pyprojects\loeschwasserversorgung
py -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Unter **PowerShell** stattdessen die Umgebung mit `.\.venv\Scripts\Activate.ps1` aktivieren. Die Umgebung `.venv` bleibt lokal und gehört nicht ins Git-Repository.

## Schnellstart: Gemeindedaten auf einem neuen Rechner

Nach dem Klonen und `python -m pip install -r requirements.txt` werden die amtlichen Rohdaten und die OSM-Gebäude **lokal** importiert. Sie sind aus Lizenz- und Datenschutzgründen nicht im Git-Repository enthalten. Die Befehle im Projektverzeichnis ausführen:

```powershell
cd C:\pyprojects\loeschwasserversorgung
# Erster Lauf: amtliche ZIP-Dateien laden sowie OSM-Gebäude von Malta (20619)
python scripts\run_municipality.py --gemeinde 20619 --download-geodata --osm-download --repair-invalid
# Zweiter Lauf: dieselben amtlichen ZIP-Dateien wiederverwenden; OSM für Gmünd (20608)
python scripts\run_municipality.py --gemeinde 20608 --osm-download --repair-invalid
```

Ausgaben: `data/processed/20619/`, `data/processed/20608/` und `reports/<gemeinde>/gemeindebericht.md`. Die Datenverzeichnisse bleiben lokal und werden von Git ignoriert. Bei späteren Läufen auf demselben Rechner entfällt `--download-geodata`, sofern die ZIP-Dateien bereits unter `data/raw/` liegen. **Achtung:** Ein neuer Download kann einen anderen Datenstand liefern. `--repair-invalid` repariert ungültige Widmungspolygone ausdrücklich und dokumentiert die Anzahl; keine rechtliche Prüfung.

Gesamtliste der Überschneidungen für eine Gemeinde im Browser öffnen:

```powershell
python scripts\list_building_overlaps.py --gemeinde 20619 --open
python scripts\list_building_overlaps.py --gemeinde 20608 --open
```

Einzelne Gebäude und ihre Widmungs-Flächenschnitte lassen sich anschließend **ohne QGIS** als Offline-HTML zeigen:

```powershell
python scripts\show_building_zoning.py --gemeinde 20619 --open
python scripts\show_building_zoning.py --gemeinde 20608 --open
```

Dabei wählt man eine Nummer aus den angezeigten Grenzfällen oder gibt eine vollständige OSM-ID an. Anleitung: [Einzelgebäude-Visualisierung](docs/einzelgebaeude-visualisierung.md). Die vollständige Importdokumentation steht unter [Gemeinde-Pipeline](docs/gemeinde-pipeline.md).

### HTTPS-Zertifikatsfehler beim Geodaten-Download (Windows)

Wenn Python beim Download von Statistik Austria mit `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` abbricht, kann eine Firmenproxy-/TLS-Inspection-Zertifikatskette beteiligt sein. Der Importer verwendet deshalb `truststore` zur **weiterhin aktiven** Zertifikatsprüfung anhand des nativen Windows-Zertifikatsspeichers. Auf einem neuen Rechner einmal ausführen:

```powershell
git pull --ff-only origin main
python -m pip install -r requirements.txt
```

Danach den Gemeindeimport wiederholen. Voraussetzung: Die zuständige Stammzertifizierungsstelle ist korrekt im Windows-Zertifikatsspeicher installiert. Falls der Fehler bestehen bleibt, die Zertifikatskette durch die IT prüfen lassen; **nicht** die TLS-Prüfung abschalten (`verify=False`, unverified SSL-Kontext).

### Overpass überlastet (HTTP 502/503/504)

Ein öffentlicher Overpass-Server kann bei voller Warteschlange zeitweise mit `502 Bad Gateway` abbrechen. Das ist **kein** Fehler der lokalen Gebäude-/GIS-Verarbeitung. Nach einem erfolgreichen amtlichen Import lässt sich die Pipeline direkt beim OSM-Download fortsetzen:

```powershell
git pull --ff-only origin main
python scripts\run_municipality.py --gemeinde 20619 --skip-geodata --osm-download
```

Bei HTTP 429/502/503/504 folgen standardmäßig höchstens **zwei zusätzliche Versuche** mit Wartezeit (15 und 30 Sekunden). Alternativ kann ein anderer vertrauenswürdiger Overpass-HTTPS-Endpunkt mit `--overpass-url https://.../api` gewählt werden; öffentlichen Diensten keine schnellen unbegrenzten Wiederholungen zumuten. `--overpass-retries 0` schaltet die zusätzlichen Versuche ab. Ein dauerhaft ausgelasteter Endpunkt kann weiterhin fehlschlagen. Bereits vorhandene OSM-Daten lassen sich stattdessen über `--osm-input <datei.geojson>` verwenden.

## Löschwasserquellen: erste OSM-Bestandsaufnahme

Für Malta (20619) nach dem bestehenden Gemeindeimport:

```powershell
python scripts\\import_water_sources.py --gemeinde 20619 --download
```

Optional für Gmünd (20608):

```powershell
python scripts\\import_water_sources.py --gemeinde 20608 --download
```

Die Ergebnisdateien `water_sources.csv`, `water_sources.geojson` und `water_sources_manifest.json` liegen unter `data/processed/<GKZ>/water_sources/`. Die Erfassung nutzt explizite OSM-Feuerwehrwasser-Tags; sie prüft **weder Wasserverfügbarkeit noch Entnahmeleistung**. Weitere Angaben, Grenzen und Prüfschritte: [OSM-Löschwasserquellen](docs/loeschwasserquellen-osm.md).

### Objektdatenbank: lokale Fachdaten (getrennt von OSM)

Den über den berechtigten Objektdatenbank-Zugang gespeicherten GeoJSON-Export der Kategorie 1724 lokal nach `data/raw/odb_wasserentnahmestellen.geojson` legen. Danach:

```powershell
python scripts\import_odb_water_sources.py --gemeinde 20619 --input data\raw\odb_wasserentnahmestellen.geojson
```

Der Import filtert auf die amtliche Gemeindegrenze, übernimmt ID, Kategorie, Statusrohcode und Koordinaten und speichert lokale Ergebnisse unter `data/processed/20619/odb_water_sources/`. Keine Anmeldung oder API-Key-Verwendung durch dieses Skript. Details: [ODB-Wasserentnahmestellen](docs/odb-wasserentnahmestellen.md).

## Daten und Veröffentlichung

Die Nutzungsbedingungen sind für die einzelnen Quellen verschieden: **Statistik Austria (Gemeindegrenzen 2026): CC BY 4.0; Land Kärnten/KAGIS (Flächenwidmung): CC BY 4.0; OpenStreetMap (Gebäude): ODbL 1.0.** Für die **Kärntner Objektdatenbank** ist keine öffentliche Weitergabelizenz nachgewiesen: Die Exportdaten und standortbezogenen Ergebnisse bleiben lokal, solange keine geeignete Freigabe vorliegt.

Alle Quellenangaben, Metadaten-Nachweise und Hinweise zur Veröffentlichung: **[Lizenzen und Datenquellen](docs/lizenzen-und-datenquellen.md)**. Eine Datenlizenz ist nicht gleichbedeutend mit der Lizenz unseres Quellcodes.

## Rechtliche Hinweise

Siehe [Rechtsgrundlagen](docs/rechtsgrundlagen.md). Maßgeblich sind die jeweils geltenden Vorschriften und die fachliche Beurteilung durch die zuständigen Stellen.

## Lizenz

Der eigene Quellcode und die selbst erstellte Projektdokumentation stehen unter der **[MIT License](LICENSE)** (Copyright © 2026 lexxi). Sie erlaubt Nutzung, Änderung und Weitergabe unter Beibehaltung des Lizenzhinweises. **Externe Geodaten und fremde Inhalte sind davon nicht umfasst**: Für Statistik Austria, KAGIS, OSM und die Kärntner Objektdatenbank gelten weiterhin die jeweiligen eigenen Nutzungsbedingungen. Siehe [Lizenz- und Quellenübersicht](docs/lizenzen-und-datenquellen.md).

## Datenfluss

![Datenfluss Löschwasserversorgung](docs/datenfluss_löschwasserversorgung_in_kärnten.png)

Die [illustrierte PNG-Übersicht](docs/datenfluss_löschwasserversorgung_in_kärnten.png) zeigt Datenquellen, Importskripte, Zwischenstände und Berichte ohne die archivierten OSM-Wasserquellen. Eine [zusätzliche bearbeitbare SVG-Version](docs/datenfluss-loeschwasserversorgung.svg) ist ebenfalls verfügbar.

## Gebäudeklassen und Löschwasseranforderungen

Die weitere Fachentwicklung ist in **zwei getrennte Arbeitspakete** gegliedert: **(1) Gebäudeklassen GK1–GK5 und Löschwasseranforderungen quellenbasiert definieren; (2) alle erfassten Gebäude anhand nachprüfbarer Daten zuordnen – mit ausdrücklicher Kennzeichnung unbekannter GK**. Tatsächliche Gebäude-GK und höchste planungsrechtlich zulässige GK werden für Objekt- bzw. Grundschutz separat behandelt. Die derzeitige OSM-Nutzungsklassifikation ist **keine** rechtlich gesicherte Gebäudeklasse. Details, technische Richtwerte, Rechtsgrundlagen und Links zu den Originaldokumenten: [Gebäudeklassen und Löschwasserbedarf](docs/gebaeudeklassen-und-loeschwasserbedarf.md).

**Technischer Stand AP 1 (v0.2.0):** [Versioniertes Regelwerk `config/firewater_rulebook.json`](config/firewater_rulebook.json) und [formaler Validator](scripts/validate_firewater_rulebook.py) sind vorhanden (`python scripts\validate_firewater_rulebook.py`). **Entwurf mit acht OIB-Varianten und sechs TRVB-Distanzstaffeln; keine automatische Gebäudeklassen- oder Bedarfszuordnung.**

## Skriptkatalog und Speicherorte

Für alle Python-Skripte sind **Zweck, benötigte Eingaben, erzeugte Dateien, Ablageorte und aktueller/historischer Status** in der [Skriptübersicht](docs/skriptuebersicht.md) dokumentiert. Für den BEV-ALS-Test bevorzugt [`download_bev_als_subset.py`](scripts/download_bev_als_subset.py) statt des vollständigen Kacheldownloads; die Originalkachel überschreitet das 8-GiB-Limit.

Für eine **gemeindeweite** BEV-ALS-Höheninventur ohne Vollkachel-Download: [`scripts/process_bev_als_municipality.py`](scripts/process_bev_als_municipality.py) (zuerst nur planen, danach `--download --max-tiles 3`, anschließend gesamte Auswahl und `--analyze`). Bedienung und Speicherorte: [Skriptübersicht](docs/skriptuebersicht.md).
