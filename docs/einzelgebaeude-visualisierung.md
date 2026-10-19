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


## Gesamtliste aller Gebäude mit mehreren Widmungsschnitten

Die interaktive Einzelobjekt-Auswahl zeigt nur eine kleine Stichprobe. Für **alle** Gebäude mit mindestens zwei positiven Widmungs-Flächenschnitten gibt es zusätzlich den lokalen HTML-/CSV-Katalog:

```powershell
git pull --ff-only origin main
python scripts\list_building_overlaps.py --gemeinde 20619 --open
python scripts\list_building_overlaps.py --gemeinde 20608 --open
```

Der HTML-Katalog unter `reports/<gemeinde>/ueberlappungen/index.html` enthält eine **durchsuchbare Tabelle** mit OSM-ID, Gebäudetyp, Gebäudegrundfläche, Anzahl der Widmungspolygone, größtem und zweitgrößtem Schnittanteil, Kategorie und OBJECTIDs. **Jede OSM-ID ist anklickbar** und öffnet eine automatisch erzeugte, vollständige Gebäudeansicht. Daneben wird `ueberlappungen.csv` (UTF-8 mit BOM, Semikolon) für Excel und eigene Auswertungen abgelegt.

Die Detailansicht ergänzt nun:

- **OSM-Gebäudeattribute** (soweit vorhanden): `building`, `building:use`, `building:levels`, `amenity`, `tourism`, `shop`, `landuse`, OSM-ID, Grundfläche, Geometrietyp.
- **Amtliche Attribute jedes geschnittenen Polygons**, soweit in KAGIS vorhanden: OBJECTID, KATEGORIE, WIDMUNG, BEZEICHNUNG, KURZBEZEICHNUNG, CODE, WIDCODE, GEMNR, gesamte Polygonfläche, Gebäudeschnittfläche und Schnittanteil.

**Datenschutz und Einschränkung:** Hausnummern, Straßennamen und OSM-Name werden **bewusst nicht** in den automatisch generierten HTML-/CSV-Dateien ausgegeben. Die Dateien befinden sich lokal im ignorierten `reports/`-Ordner; sie werden nicht auf GitHub hochgeladen. Anteil und Gebäudetyp sind geometrische/OSM-basierte Angaben, keine rechtswirksame Zuordnung oder amtliche Nutzungsklassifikation. Die Liste enthält jeden Mehrfachschnitt, also ausdrücklich auch 99/1-%-Fälle; keine automatische Bewertung als Fehler.

## Voraussetzungen

Zuerst `scripts/run_municipality.py` für die Gemeinde ausführen, sodass `data/processed/<gemeinde>/osm/buildings.geojson` und `data/processed/<gemeinde>/zoning.geojson` vorhanden sind. Benötigt werden die bestehenden Projekt-Abhängigkeiten, insbesondere GeoPandas und Shapely; kein QGIS und kein zusätzlicher Plotter.

## Wiederholte KAGIS-OBJECTIDs

Im Malta-Datensatz wurde festgestellt, dass die KAGIS-`OBJECTID 5227477` **44 separaten Polygon-Datensätzen** zugeordnet ist. Deren Flächen summieren sich auf ungefähr **255,5812 km²**. Die Detailseite hatte bei einem konkreten Datensatz **252,8020 km²** ausgegeben: das ist die Fläche **dieser einen Polygongeometrie**, nicht die Summe aller Datensätze mit derselben OBJECTID.

Deshalb zeigt die Detailansicht zusätzlich den **0-basierten GeoJSON-Datensatzindex** und bei mehrfachen OBJECTIDs die Anzahl der Vorkommen. Der Index ist nur innerhalb **des jeweiligen importierten GeoJSON-Datenstandes** stabil; nach einem erneuten Import kann er sich ändern. Zur Reproduzierbarkeit gehören somit Datensatzstand/Quelldatei, Datensatzindex und OBJECTID zusammen. Gleiche OBJECTIDs dürfen nicht als Beleg dafür gelten, dass geometrisch nur ein einziges Polygon existiert.
