# OSM-Gebäudeimport für Malta

Das Skript `scripts/import_osm.py` verarbeitet vorhandene OpenStreetMap-GeoJSON-Daten oder lädt den aktuellen Gebäudebestand über **OSMnx/Overpass**. Grundlage ist die zuvor importierte amtliche Gemeindegrenze (Gebietsstand 01.01.2026).

## Vorbereitung

```powershell
cd C:\pyprojects\loeschwasserversorgung_9854_malta
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## A: Vorhandenen Export als Referenz prüfen

Wenn `export.geojson` vorliegt, etwa lokal im Projektordner:

```powershell
python scripts\import_osm.py --input export.geojson --out data\processed\baseline\osm
```

Das Skript übernimmt kein unbekanntes Erstellungsdatum als aktuelles Download-Datum. Der lokale Export dient als **historischer Vergleich**.

## B: Aktuelle OSM-Gebäude herunterladen

```powershell
python scripts\import_osm.py --download --out data\processed\current\osm
```

Die Standard-Gemeindegrenze ist `data/processed/current/malta_boundary_2026.geojson`. Ein abweichender Pfad ist über `--boundary` möglich.

**Hinweis:** Overpass ist ein öffentlicher, limitierter Dienst. Eine große Gemeinde kann lange Abfragen, Rate-Limits oder Timeouts verursachen. Der Live-Download muss noch auf Windows getestet werden. Ein erfolgreicher Download ist kein Beleg für vollständige OSM-Gebäudedaten.

## Ausgaben

- `buildings_malta.geojson`: OSM-Gebäude-Polygone mit ausgewählten Tags und stabiler OSM-Element-ID
- `osm_manifest.json`: Abfrageart, Datum, Datenquelle, SHA-256 und Statistiken

Die Gebäude werden nach Überschneidung mit der Gemeindegrenze ausgewählt; **die Gebäudegeometrie wird dabei nicht abgeschnitten**, damit der Gebäudefußabdruck erhalten bleibt. Die Auswahl an der Grenze ist dadurch bewusst inklusiv.

## Weitere Schritte (noch nicht implementiert)

1. Historischen OSM-Export und Live-Download per OSM-ID vergleichen.
2. Gebäude mit Flächenwidmung verknüpfen, mehrfache Zuordnungen und Überlappungen ausdrücklich ausweisen.
3. Wohngebäude-Klassifikation mit nachvollziehbaren Regeln verbessern.
4. Erst danach Clusterbildung und fachliche Löschwasserbedarfsprüfung.

Die Daten sind unter der Open Database License (ODbL) von OpenStreetMap-Mitwirkenden verfügbar; Lizenz und Attribution bei Veröffentlichungen beachten.
