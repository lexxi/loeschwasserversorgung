# Gemeindebericht (automatisch)

Der Report-Generator `scripts/generate_municipality_report.py` fasst **bereits berechnete** Ergebnisse einer Gemeinde zusammen. Er lädt keine neuen Daten herunter und führt keine Löschwasserbedarfsberechnung durch.

## Malta: vorhandenen Datenstand auswerten

Voraussetzung: `import_geodata.py`, `import_osm.py`, `join_buildings_zoning.py` und `classify_buildings.py` wurden erfolgreich ausgeführt.

```powershell
python scripts\generate_municipality_report.py
```

Ausgabe:

```text
reports/
  20619/
    gemeindebericht.md
    gemeindebericht.json
```

In VS Code oder GitHub kann `gemeindebericht.md` als lesbarer Bericht angezeigt werden. Die JSON-Datei enthält dieselben Kernkennzahlen zur weiteren maschinellen Verwendung. Generierte Berichte bleiben zunächst lokal (vor Veröffentlichung Quellen und Datenlizenzen prüfen).

## Andere Gemeinde

Der Generator liest **Gemeindenummer und Gemeindename aus dem amtlichen `import_manifest.json`** und baut unter `--out-root` automatisch ein Unterverzeichnis mit der Gemeindenummer:

```powershell
python scripts\generate_municipality_report.py --base "data\processed\20619"
```

**Wichtig:** Dieser Aufruf funktioniert nur, wenn im angegebenen Verzeichnis bereits ein vollständiger, konsistenter Analysedatenbestand mit der vom Importer erwarteten Ordnerstruktur existiert. Die automatisierte Erstellung des gesamten Datenbestands für beliebige Gemeinden ist noch nicht implementiert; die aktuellen Import-Skripte sind teilweise auf Malta zugeschnitten.

## Inhalte

- Gemeinde-ID und Name, Zeitstempel der Verarbeitung, Datenquellen und amtlicher Gebietsstand.
- Gesamtanzahl Widmungspolygone, Gruppierung nach `KATEGORIE`.
- Gebäudeanzahl und OSM-Gebäudetags.
- Punktzuordnung zur Widmung, offene Grenzfälle und Statusübersicht.
- Anzahl der von einem Gebäude geschnittenen Widmungspolygone.
- Maximaler und zweitgrößter Gebäude-Flächenanteil in Widmungen sowie Summenprüfung.
- Gebäudeklassifikation mit Anteilen und Anzahl ungeklärter Tags.
- Methodische Einschränkungen und fehlende Teilquellen.

## Schutz vor irreführenden Aussagen

- Widersprechen sich Gebäude- oder Widmungszahlen zwischen Dateien, bricht das Skript mit einer Fehlermeldung ab.
- Die amtliche Gemeindekennzahl muss mit der des OSM-Imports übereinstimmen.
- Die Überschneidungswerte stammen aus `zoning_footprint_overlaps.csv`, nicht aus manuell eingetragenen Malta-Zahlen.
- Bei fehlender Geodatei oder Flächenschnittdatei wird im Bericht eine Warnung ausgewiesen; es werden keine Werte erfunden.
- `99–100 % größte Überdeckung` bedeutet: **Ein einzelnes Gebäude** liegt nahezu vollständig in **einer** Widmungsfläche, schneidet aber weitere Flächen. Das ist kein Bauland- oder Löschwassernachweis.
- Die Berichtszahlen sind ein Iststand und ersetzen keinen Vergleich mit früheren Datenständen. Historische Vergleiche können in einer späteren Ausbaustufe eingebaut werden.

## Eingaben

```text
data/processed/current/
  import_manifest.json
  malta_zoning.geojson
  osm/osm_manifest.json
  building_zoning/summary.json
  building_zoning/zoning_footprint_overlaps.csv
  building_classification/summary.json
```

Die Dateinamen der Rohimporte sind derzeit teilweise Malta-spezifisch. Der Report selbst ermittelt den Gemeindenamen anhand der Metadaten und legt keine feste Gemeinde-ID zugrunde.

Die Dokumentation der Datenqualität ist unter `docs/datenqualitaet-methodik.md` zu finden.

## Version 2: zusätzliche Auswertungen

Die zweite Version erweitert den bestehenden Gemeindebericht, ohne die Import- oder Join-Ergebnisse zu verändern:

- **Gemeindefläche und Widmungsflächen in Hektar** (EPSG:31287, geometrische Vereinigung pro Kategorie); zusätzliche prozentuelle Anteile an der Gemeindefläche. Verschiedene Kategorien können sich überlagern, daher dürfen die Anteile nicht ungeprüft zu 100 % addiert werden.
- **Gebäude nach Widmung und OSM-Nutzungsklasse**, ausschließlich bei eindeutiger Repräsentativpunktzuordnung. Die übrigen Gebäude erscheinen als Prüffälle, nicht unter einer erfundenen Widmung.
- **Unbekannte Gebäudenutzung trotz Hausnummer**, ohne die Hausnummer selbst im Bericht zu veröffentlichen.
- **Detailverteilung für Gebäude mit 50–90 % größter Widmungsüberdeckung**: 50–60, 60–70, 70–80 und 80–90 %, ergänzt um die Kombination der geschnittenen Widmungskategorien. Kein Vorrang wird automatisch abgeleitet.

Die Kennzahlen werden unmittelbar aus den erzeugten GeoJSON- und CSV-Dateien berechnet. Bei fehlenden Eingaben werden Warnungen ausgegeben; widersprüchliche Gesamtzahlen führen weiterhin zum Abbruch.

**Hinweis:** Die Flächenauswertung ist eine geometrische Bestandsaufnahme. KAGIS-Datenstand und Rechtswirksamkeit, Gebäude-Nutzung und etwaiger Löschwasserbedarf sind gesondert zu verifizieren.

## Version 3: Datenqualität und gezielte Prüflisten

Der bisherige Befehl bleibt unverändert:

```powershell
git pull --ff-only origin main
python scripts\generate_municipality_report.py
```

Zusätzlich erstellt das Skript unter `reports/<Gemeindenummer>/`:

- `grenzfaelle_50_60.csv`: Reproduzierbare Prüfung aller Gebäude mit mindestens zwei positiven Widmungs-Flächenschnitten und **50 bis unter 60 % größter Überdeckung**, aufsteigend nach Dominanzanteil und dann OSM-ID sortiert.
- `grenzfaelle_50_60.geojson`: Dieselben Gebäude als QGIS-Layer (EPSG:4326) mit **OSM-ID und Prüfkennzahlen, ohne Hausnummern**.
- `unbekannte_nutzung_mit_hausnummer_aggregation.csv`: Aggregierte Anzahl von Gebäuden mit Hausnummer, aber unklarem OSM-`building`-Tag nach Widmung, Kategorie und Gebäudetag; **keine einzelnen Hausnummern**.

Der Markdown- und JSON-Bericht enthalten zusätzlich:

1. **Topologische Flächenbilanz**: Gemeindefläche, Union aller Widmungspolygone innerhalb der Gemeinde, nicht abgedeckte Gemeindefläche und mögliche außerhalb liegende Geometrie.
2. **Flächenmehrfachabdeckung**: Summe der Einzelpolygonflächen minus Fläche ihrer Union. Diese Differenz zählt mehrfach überdeckte Flächen entsprechend ihrer Multiplikität; sie ist keine automatische Fehlerfeststellung.
3. **Grenzfall-Prüftabelle** mit den tatsächlichen OSM-IDs, größten und zweitgrößten Flächenanteilen, Anzahl von Flächenschnitten und betroffenen Kategorien.
4. **Aggregierte Nutzungslücken** für Gebäude mit Hausnummer und unbekannter Gebäudenutzung.

Alle Flächenoperationen erfolgen in **EPSG:31287**. Die Grenzfall-Grenzen sind bewusst reine **Prüfkriterien**, keine rechtlichen Zuordnungsregeln.

Die V3-Ausgaben werden nur erzeugt, wenn die jeweils benötigten Daten vorhanden sind; fehlende Eingaben werden als Warnung dokumentiert. Für einen erneuten Vergleich stets den zuvor verwendeten Datenstand beibehalten.

**Datenschutz und Veröffentlichung:** Die erzeugten Berichte und GeoJSON-Exports werden weiterhin durch `.gitignore` unter `reports/` vom öffentlichen Repository ausgeschlossen. Vor einer Veröffentlichung sind Quelllizenzen und mögliche Schutzinteressen zu prüfen.
