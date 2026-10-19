# Erste Bestandsaufnahme: OSM-Löschwasserquellen

Das Skript `scripts/import_water_sources.py` erweitert **nicht** die Gebäude-/Widmungspipeline, sondern arbeitet auf deren bereits importierter amtlicher Gemeindegrenze. Es erstellt eine erste Liste der **explizit für Feuerwehrwasser gekennzeichneten** OSM-Objekte.

## Ausführung (PowerShell)

```powershell
cd C:\pyprojects\loeschwasserversorgung
git pull --ff-only origin main
python scripts\import_water_sources.py --gemeinde 20619 --download
```

Anschließend, falls gewünscht:

```powershell
python scripts\import_water_sources.py --gemeinde 20608 --download
```

Ein neues Laden der amtlichen GIS-Daten oder erneuter Gebäudedownload ist dafür **nicht** erforderlich.

Bei überlastetem Overpass: Die Downloadfunktion versucht HTTP 429/502/503/504 bis zu zweimal erneut (15 s / 30 s). Optional: `--overpass-retries 0` oder `--overpass-url https://.../api`.

Zur reproduzierbaren Verarbeitung vorhandener Quellen: `--input C:\Pfad\osm_export.geojson` statt `--download`. Der GeoJSON-Export benötigt OSM-`emergency`-Tags und OSM-Element-IDs.

## Übernommene OSM-Kategorien

| OSM-Tag | Inventarkategorie | Fachliche Bedeutung |
| --- | --- | --- |
| `emergency=fire_hydrant` | Hydrant | OSM-erfasster Hydrant |
| `emergency=suction_point` | Saugstelle | OSM-erfasster Entnahmepunkt |
| `emergency=water_tank` | Löschwasserbehälter | OSM-erfasster Tank/Behälter |
| `emergency=fire_water_pond` | Löschwasserteich | OSM-erfasste Feuerwehrwasserfläche |

Quellen: [OSM fire_hydrant](https://wiki.openstreetmap.org/wiki/Tag:emergency%3Dfire_hydrant), [suction_point](https://wiki.openstreetmap.org/wiki/Tag:emergency%3Dsuction_point), [water_tank](https://wiki.openstreetmap.org/wiki/Tag:emergency%3Dwater_tank), [fire_water_pond](https://wiki.openstreetmap.org/wiki/Tag:emergency%3Dfire_water_pond).

Normale Bäche, Seen, Brunnen oder Teiche **ohne explizite Feuerwehr-Kennzeichnung** bleiben in dieser ersten Stufe ausgeschlossen. Nicht als Quellen erfassen: Feuerwehr-Einspeisungen (`emergency=fire_service_inlet`), die Wasser **entgegennehmen**, statt es abzugeben.

## Erzeugte lokale Dateien

Unter `data/processed/<GKZ>/water_sources/`:

- `water_sources.csv`: Excel-freundlicher Semikolon-Export mit UTF-8 BOM.
- `water_sources.geojson`: Punktgeometrien in WGS84; bei flächenhaften Quellen ist der Punkt nur ein **geometrischer Repräsentativpunkt**, nicht die Lage einer tatsächlichen Entnahmestelle.
- `water_sources_manifest.json`: Zeitpunkt, Quellenhinweis (OSM/ODbL), Gemeindekennzahl, Gemeindegrenze-Hash, Filter, Datensatzanzahl und Prüfeinschränkungen.

Die erfassten Eigenschaften enthalten u. a. OSM-ID, OSM-Typ, Koordinaten, `fire_hydrant:type`, `fire_hydrant:diameter`, `fire_hydrant:pressure`, `water_source`, `water_tank:volume`, `capacity`, `access` und `survey:date`, **sofern** in OSM vorhanden. Alle Werte bleiben Rohangaben und werden weder in l/min umgerechnet noch als bestätigt dargestellt.

Die Verarbeitung filtert nach Gemeindefläche, erwartet eindeutige OSM-IDs und hält die Dateiausgaben im durch `.gitignore` ausgeschlossenen lokalen Datenordner. Keine unkontrollierte Veröffentlichung von Versorgungsdaten.

## Nächster fachlicher Schritt

Erst die Inventarliste anhand belastbarer kommunaler/Feuerwehrquellen auf Vollständigkeit, Typ, Standort, Zugänglichkeit, Hydrantennetz, Druck/Entnahmeleistung, Behältervolumen und zeitliche Verfügbarkeit prüfen. OSM-Verfügbarkeit ist **kein** Löschwasser-Nachweis. Gebäudeabstände oder ein Versorgungskreis wären ohne Leitungs-/Straßen- und Kapazitätsdaten ebenfalls **kein** Nachweis ausreichender Versorgung.
