# Kärntner Objektdatenbank: Wasserentnahmestellen (lokaler GeoJSON-Import)

Die Objektdatenbank `kaernten.objektdatenbank.at` verwaltet Objekte, die anschließend in der Feuerwehr-Einsatzanwendung angezeigt werden können. Die beiden Anwendungen haben unterschiedliche Schnittstellen. Für unseren Import verwenden wir zunächst **nur einen lokal und berechtigt gespeicherten GeoJSON-Export** aus der Objektdatenbank; es wird kein API-Key benötigt oder übertragen.

## Herkunft und Kategorien

Die in der Anwendung sichtbare Hauptkategorie **1724 – Wasserentnahmestellen** hat folgende Unterkategorien:

| Kategorie | ODB-Kategorie-ID |
| --- | ---: |
| Bach mit Stau | 1729 |
| Löschwasserteich | 1730 |
| Saugstelle | 3953 |
| Überflurhydrant | 1728 |
| Unterflurhydrant | 1727 |

Der erste manuell geprüfte Export enthielt **41 Objekte**, davon 32 Überflurhydranten, 3 Unterflurhydranten, 3 Bach mit Stau, 2 Saugstellen und 1 Löschwasserteich. `sliceddata=0`. Statuscodes: 40 × `1`, 1 × `2`. **Status 1 bedeutet „verwendbar“, Status 2 „eingeschränkt verwendbar“, Status 3 „nicht verwendbar“** (laut Rückmeldung aus der Objektdatenbank). 41 ist die Anzahl der exportierten Features, nicht bereits die GIS-geprüfte Anzahl innerhalb der amtlichen Gemeindegrenze.

## Export und Import

Im **angemeldeten Browser**, soweit der Benutzer dazu berechtigt ist, kann die Kategorieansicht GeoJSON über `/backend/export/geojson/kategorie/1724` laden. Ob dieser Webendpunkt für direkte API-Key-Authentifizierung vorgesehen ist, ist noch **nicht** geklärt. Keine Session-Cookies oder API-Schlüssel in Projektcode, Chats oder Git speichern.

Den GeoJSON-Export lokal z. B. unter `data/raw/odb_wasserentnahmestellen.geojson` ablegen. Danach:

```powershell
git pull --ff-only origin main
python scripts\import_odb_water_sources.py --gemeinde 20619 --input data\raw\odb_wasserentnahmestellen.geojson
python scripts\check_project.py --gemeinde 20619
```

Das Skript erwartet vorhandene amtliche `data/processed/20619/boundary.geojson` und `import_manifest.json`, nutzt die Gemeindegrenze als räumlichen Filter und schreibt unter `data/processed/20619/odb_water_sources/`:

- `odb_water_sources.csv` (Semikolon, UTF-8 mit BOM),
- `odb_water_sources.geojson` (nur Objekt-ID, Kategorie, Statusrohcode, Statuslabel, lokalen Objekttitel (Name) und Punktkoordinaten),
- `odb_water_sources_manifest.json` (Quell-Hash, Filterergebnisse, Gesamtzahlen/Status/Kategorien und Einschränkungen).

Zur Datensparsamkeit werden `Text`, `Links`, `Image`, `Editurl` **nicht** in die Ergebnisdateien übernommen. Das Feld `Name` wird für die lokale Titelanzeige und Suche übernommen; Ergebnisse dürfen nicht öffentlich hochgeladen werden. Der Originalexport bleibt im lokalen, von Git ignorierten `data/raw/`-Ordner. Nur exakte ODB-Ids im autorisierten Datenbestand werden übernommen, nicht veröffentlicht.

### Wichtige Abgrenzungen

- Der GeoJSON-Export kann nur die für den angemeldeten Nutzer sichtbaren Objekte umfassen.
- `sliceddata=0` ist ein Hinweis gegen die Kürzung der Kartenausgabe; kein Beweis vollständiger Daten.
- Es werden nur **Point-Geometrien** und die bekannten fünf Wasserentnahmestellen-Kategorien importiert. Objekte außerhalb der amtlichen Gemeindegrenze werden lediglich gezählt und nicht ausgegeben.
- ODB und OSM werden **nicht** blind zusammengeführt: identische Einrichtungen könnten in beiden Beständen stehen.
- Status 1 ist als „verwendbar“, Status 2 als „eingeschränkt verwendbar“ und Status 3 als „nicht verwendbar“ bekannt. Die Rohcodes bleiben unverändert gespeichert. Die tatsächliche Verfügbarkeit, Wassermenge, Druck, technische Eignung und Vollständigkeit bleiben bis zur fachlichen Verifizierung offen.
- Die Nutzung/Freigabe der Daten sowie eine eventuelle API-Anbindung müssen mit der zuständigen Stelle geklärt werden. API-Key-Zugriff ist nicht aus dem Browser-GeoJSON-Endpunkt abzuleiten.

## Offline-Karte (ODB-only)

Nach dem lokalen ODB-Import:

```powershell
git pull --ff-only origin main
python scripts\show_odb_water_sources.py --gemeinde 20619
ii reports\20619\odb_wasserentnahmestellen.html
```

Die eigenständige HTML-Datei arbeitet **ohne Webkarten, externe Bibliotheken oder Internetverbindung**. Sie zeigt die amtliche Gemeindegrenze sowie ausschließlich die importierten ODB-Punkte. Verfügbar sind Filter nach den fünf Typen, drei Statuscodes, eine Suche nach ODB-ID oder Objekttitel, Zoom und Verschieben sowie Titelanzeige beim Darüberfahren oder Klick.

**Ausgeschlossen:** sämtliche vier archivierten OSM-Hydranten aus Malta. Sie werden weder eingelesen noch auf der Karte dargestellt. Die Karte stellt nur Quellstandorte dar, keine geprüfte hydraulische oder normative Versorgung.

Nach einer Aktualisierung des Skripts muss der ODB-Importer erneut laufen, damit die Titel (`Name`) aus dem lokalen Originalexport in die Ergebnisdatei übernommen werden.
