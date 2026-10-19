# Einzelgebäude: Widmungsschnitte ohne QGIS veranschaulichen

Für Rückfragen zu Gebäuden an Widmungsgrenzen erzeugt `scripts/show_building_zoning.py` eine **einzelne, vollständig offline nutzbare HTML-Seite**. Das Skript liest ausschließlich die bereits vorhandenen lokalen GeoJSON-Dateien der Gemeinde, fragt keine Web-Kartendienste ab und veröffentlicht nichts.

## Interaktiv ein auffälliges Gebäude auswählen

Im Projektverzeichnis:

```powershell
git pull --ff-only origin main
python scripts\show_building_zoning.py --gemeinde 20619 --open
```

Das Terminal zeigt bis zu 25 Gebäude mit mindestens zwei positiven Flächenschnitten, sortiert nach Nähe der größten Überdeckung zu 50 %. **Zahl aus der Liste eingeben**, oder eine vollständige OSM-ID eingeben. Nach der Auswahl wird die Datei automatisch unter `reports/20619/haus_<osm-id>.html` gespeichert und mit `--open` im Standardbrowser geöffnet.

Beispiel für ein bereits bekanntes Malta-Gebäude mit zwei Widmungen:

```powershell
python scripts\show_building_zoning.py --gemeinde 20619 --osm-id way/371120663 --open
```

Beispiel für Gmünd in Kärnten (20608):

```powershell
python scripts\show_building_zoning.py --gemeinde 20608 --osm-id relation/5148314 --open
```

Weitere Optionen: `--limit 50` zeigt mehr Auswahlbeispiele; `--out C:\Temp\beispiel.html` legt einen bestimmten Speicherort fest.

## Darstellung

- **Schwarze Kontur:** OSM-Gebäudeumriss.
- **Helle farbige Flächen:** die amtlichen Widmungspolygone, die dieses Gebäude mit positiver Fläche schneiden, auf einen kleinen Kartenausschnitt begrenzt.
- **Kräftig gefärbte Bereiche innerhalb der Gebäudegrundfläche:** konkrete Überschneidung der jeweiligen Widmung mit dem Gebäude.
- **Tabelle:** Kategorie, Widmungsbezeichnung, OBJECTID, Schnittfläche in m² und prozentualer Anteil am vollständigen Gebäudeumriss.
- **Schwarzer Punkt:** geometrischer Schwerpunkt des Gebäudes als Orientierung; dieser ist **nicht** der im Join verwendete Repräsentativpunkt.

Auch Gebäude mit drei oder mehr Schnitten lassen sich darstellen. Bei überlagerten Widmungspolygonen kann die Summe der Flächenanteile 100 % überschreiten. Lücken können eine geringere Gesamtsumme ergeben.

Diese Grafik **erklärt geometrische Schnitte**, legt aber keine rechtlich maßgebliche Widmung fest. Sie nutzt keine Orthofotos und zeigt keine Hausnummern. Die erzeugten HTML-Dateien befinden sich im per `.gitignore` ausgeschlossenen `reports/`-Verzeichnis und werden nicht automatisch veröffentlicht.

## Voraussetzungen

Zuerst `scripts/run_municipality.py` für die Gemeinde ausführen, sodass `data/processed/<gemeinde>/osm/buildings.geojson` und `data/processed/<gemeinde>/zoning.geojson` vorhanden sind. Benötigt werden die bestehenden Projekt-Abhängigkeiten, insbesondere GeoPandas und Shapely; kein QGIS und kein zusätzlicher Plotter.
