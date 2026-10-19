# Gemeindeunabhängige Analysepipeline

**Status: erste Implementierung, Regressionstest ausständig.** Ziel ist, dieselben Auswertungen für jede Gemeinde in **Kärnten** anhand ihrer fünfstelligen Gemeindenummer durchzuführen. Die Flächenwidmung stammt weiterhin ausschließlich aus dem Kärntner Datenangebot; eine österreichweite Auswertung ist noch nicht implementiert.

## Ein Aufruf pro Gemeinde

Vorhandene Rohdateien (`data/raw/gemeinden_2026.zip`, `data/raw/flawi_ktn_gpkg.zip`) verwenden und OSM aktuell beziehen:

```powershell
python scripts\run_municipality.py --gemeinde 20619 --osm-download --repair-invalid
```

Alternativ landesweites, bereits entpacktes GeoPackage verwenden:

```powershell
python scripts\run_municipality.py --gemeinde 20619 --zoning-gpkg data\raw\flawi_ktn_gpkg.gpkg --osm-download --repair-invalid
```

**Reproduzierbarer Malta-Test ohne neuen OSM-Download** (vorhandene, früher erzeugte Datei, kein Überschreiben der bisherigen `data/processed/current`):

```powershell
python scripts\run_municipality.py --gemeinde 20619 --zoning-gpkg data\raw\flawi_ktn_gpkg.gpkg --osm-input data\processed\current\osm\buildings_malta.geojson --repair-invalid
```

Voraussetzung: die jeweils angegebenen ZIP-/GPKG-/GeoJSON-Dateien existieren lokal. Die ZIP-Dateien können alternativ mit `--download-geodata` beim Lauf neu bezogen werden. Achtung: Ein erneuter Download kann einen **anderen Datenstand** ergeben und erschwert den 1:1-Regressionstest.

## Getrennte Ablage

```text
data/processed/
  current/                  # Bisherige Malta-Ergebnisse, unverändert
  20619/
    import_manifest.json
    boundary.geojson
    zoning.geojson
    bauland.geojson
    osm/
      buildings.geojson
      osm_manifest.json
    building_zoning/
    building_classification/
reports/
  20619/
    gemeindebericht.md
    gemeindebericht.json
    grenzfaelle_50_60.csv
    grenzfaelle_50_60.geojson
```

Die Pipeline ruft nacheinander `import_geodata.py`, `import_osm.py`, `join_buildings_zoning.py`, `classify_buildings.py` und `generate_municipality_report.py` auf. Der Bericht liest die Gemeinde-ID aus dem amtlichen Importmanifest.

## Regressionstest

Bei gleichem KAGIS- und OSM-Datenstand sollten für Malta folgende Vergleichswerte reproduziert werden:

- 540 Widmungspolygone, davon 224 Bauland.
- 1.686 Gebäude.
- 432 Gebäude mit mehreren positiven Widmungs-Flächenschnitten.
- 202 Wohngebäude-Kandidaten, 122 andere Gebäudetypen, 1.362 ungeklärte Nutzung.
- 22 starke Grenzfälle bei 50–unter 60 % größter Überdeckung.

Abweichungen können auch von neu heruntergeladenen Daten stammen. Bei Fehlermeldungen den ersten fehlerhaften Analyseschritt prüfen, keine stillschweigende Korrektur von Geometrien vornehmen.

## Grenzen

- Die Analyse basiert auf OSM-Gebäudeumrissen und Kärntner Flächenwidmungen. Weder Wohnnutzung noch Löschwasserbedarf werden amtlich festgestellt.
- Referenzpunkt-Zuordnung und positive Gebäudeflächenüberschneidung sind getrennte Prüfgrößen.
- Historische Vergleichsdaten fehlen bei neu hinzugenommenen Gemeinden möglicherweise.
- Vor einer Veröffentlichung gelten die Hinweise zu Datenqualität, Datenlizenzen und Wasserinfrastruktur.
- **Geplante Repository-Umbenennung:** Nach erfolgreichem Test mehrerer Gemeinden soll `loeschwasserversorgung_9854_malta` in einen gemeindeunabhängigen Namen wie `loeschwasserversorgung` umbenannt werden. Derzeit **kein Rename**, bestehende lokale Klone und Git-Remotes bleiben gültig.

## Regressionstest: Ergebnis 19.10.2026

**Status: Erfolgreich für den Vergleich Malta (20619) bei identischem KAGIS-Datenstand.** Nutzerseitig unter Windows/PowerShell überprüft.

| Prüfgröße | Bisherige feste Malta-Pipeline | Neue Pipeline mit `--gemeinde 20619` |
| --- | ---: | ---: |
| SHA-256 des KAGIS-GeoPackage | identisch | identisch |
| Widmungspolygone | 540 | 540 |
| OSM-Gebäude | 1.686 | 1.686 |
| Gebäude mit mehreren Widmungs-Flächenschnitten (`boundary_review`) | 432 | 432 |
| Eindeutige Repräsentativpunkt-Zuordnungen (`unique`) | 1.685 | 1.685 |

Die übrigen Gebäudeklassifikationen waren schon beim ersten Probelauf gleich: 202 Wohngebäude-Kandidaten, 122 Nicht-Wohngebäude-Tags, 1.362 ungeklärte Nutzungen.

**Wichtige Erkenntnis zur Reproduzierbarkeit:** Der erste neue Lauf enthielt nur 537 Widmungspolygone und 429 Grenzfälle, weil mit `--zoning-gpkg data/raw/flawi_ktn_gpkg.gpkg` ein älterer GeoPackage-Datenstand verwendet wurde. Die Quelle hatte einen anderen SHA-256-Hash als der bisherige Download. Der zweite Lauf nutzte das ursprüngliche heruntergeladene KAGIS-ZIP ohne `--zoning-gpkg` und reproduzierte die Werte vollständig. **Nicht** als Hinweis auf kurzfristige Änderungen der zentralen KAGIS-Datenbank interpretieren.

Dieser Regressionstest deckt die oben aufgeführten Kennzahlen ab, **nicht** automatisch Bytegleichheit aller Geometrien oder sämtliche Funktionen des Gemeindeberichts. Als nächster Test folgt eine zweite Kärntner Gemeinde und die Prüfung der neuen Gemeinde-spezifischen Ausgabeordner.
