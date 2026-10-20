# Lizenzen, Datenherkunft und Quellenangaben

Stand der Prüfung: 20. Oktober 2026.

**Wichtig:** Die Lizenz einer Datenquelle ist **nicht** die Softwarelizenz für die Python-Skripte. Das Projekt enthält Code zur lokalen Verarbeitung externer Daten; die Nutzungsrechte der Daten verbleiben beim jeweiligen Rechteinhaber.

## 1. Software-Quellcode dieses Repositories

Im Repository wurde bislang **keine `LICENSE`-Datei hinterlegt**, und es wurde noch keine eigene Open-Source-Lizenz durch den Rechteinhaber ausgewählt. Deshalb ist die Nutzung über die gesetzlichen Schranken und explizite Rechte hinaus nicht allgemein freigegeben.

Die Wahl einer Softwarelizenz (z. B. MIT, Apache-2.0 oder GPL-3.0) muss der Repository-Inhaber selbst treffen. Diese Wahl gilt nur für eigene, lizenzierbare Projektbestandteile und ändert **nicht** die Nutzungsrechte an importierten OSM-, OGD- oder ODB-Daten.

## 2. Geodatenquellen

| Quelle | Verwendete Daten | Lizenz / Nutzungsstand | Offizieller Nachweis |
| --- | --- | --- | --- |
| **Statistik Austria** | Gemeindegrenzen, Stand 01.01.2026 | **CC BY 4.0 International**; Quellen-/Lizenzangabe und Hinweis auf Bearbeitung | [Metadaten: Gliederung Österreichs in Gemeinden](https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_GEM_1) |
| **Land Kärnten / KAGIS** | Flächenwidmung (WIDG), daraus abgeleitetes Bauland | **CC BY 4.0** gemäß OGD-Katalogeintrag; genaue Download-Distribution und Stand im Importmanifest festhalten | [Flächenwidmung Kärnten, data.gv.at](https://www.data.gv.at/katalog/dataset/cef1c710-3564-4c4a-adce-39896ba4bed8) |
| **OpenStreetMap-Mitwirkende** | Gebäudegrundflächen aus OSM bzw. Geofabrik Austria PBF | **Open Database License (ODbL) 1.0**; Attribution und bei öffentlicher Weitergabe ggf. weitere ODbL-Pflichten | [OSM Copyright](https://www.openstreetmap.org/copyright), [OSMF Attribution](https://osmfoundation.org/wiki/Attribution_Guidelines), [ODbL](https://opendatacommons.org/licenses/odbl/1.0/) |
| **Kärntner Objektdatenbank** | Wasserentnahmestellen, GeoJSON-Kategorie 1724 | **Keine öffentliche Datenlizenz oder Export-Weitergabeberechtigung nachgewiesen.** Nur im Rahmen des berechtigten Zugangs lokal nutzen; Rechte für Weitergabe/Veröffentlichung beim Betreiber klären | [Objektdatenbank Kärnten](https://kaernten.objektdatenbank.at/) |

### Empfohlene Quellenangaben bei einer ausdrücklich freigegebenen Veröffentlichung

**Für Karten mit OSM-Gebäudegrundflächen:**

> Gebäudegrundflächen: © OpenStreetMap-Mitwirkende, Daten unter ODbL 1.0 (https://www.openstreetmap.org/copyright). Aus OSM/Geofabrik-Daten lokal gefiltert und räumlich ausgewertet.

Die OSM-Quellenangabe gehört bei öffentlich genutzten Karten in eine gut sichtbare Stelle **an der Karte**, nicht nur in eine separate README. Bei veröffentlichten OSM-Datenbanken und Derived Databases können zusätzliche Bereitstellungspflichten gelten; vor einer externen Veröffentlichung solcher Ergebnisse sind die ODbL-Bestimmungen gesondert zu prüfen.

**Für die amtliche Gemeindegrenze:**

> Quelle: Statistik Austria, Gliederung Österreichs in Gemeinden (Gebietsstand 01.01.2026), CC BY 4.0. Für die Gemeinde lokal gefiltert und kartografisch aufbereitet.

**Für Flächenwidmung/Bauland:**

> Quelle: Land Kärnten / KAGIS, Flächenwidmung Kärnten, CC BY 4.0. Gemeindegefiltert, geometrisch zugeschnitten; Bauland lokal aus dem Datensatz abgeleitet.

Die Datenstands- und Abrufangaben sollen dabei aus dem jeweiligen lokalen `import_manifest.json` ergänzt werden. Die Nutzung des OGD-Datensatzes sagt nicht aus, dass lokale Änderungen die geltende Flächenwidmung rechtsverbindlich wiedergeben.

**Für die Kärntner Objektdatenbank:**

> Datenquelle: Kärntner Objektdatenbank, lokal für die berechtigte Projektbearbeitung verwendet. Keine öffentliche Nachnutzungslizenz bestätigt.

Diese letzte Formulierung ist ein **interner Herkunftsvermerk**, **keine** Erlaubnis, Standorte, Titel, Kennungen, Einsatzdaten, Quellen-GeoJSON oder daraus generierte Karten an Dritte zu verteilen.

## 3. Welche Inhalte dürfen ins öffentliche GitHub?

- **Ja, soweit selbst erstellt:** generische Skripte, Beispielkonfigurationen ohne Geheimnisse, Methodenbeschreibungen, abstrakte Datenflussdiagramme und Dokumentation.
- **Nicht ohne Prüfung und gegebenenfalls Freigabe:** Rohdaten/Exports (`data/raw/`), verarbeitete Geodaten (`data/processed/`), standortbezogene Reports/Karten (`reports/`), ODB-Objektbezeichnungen, interne Quelleninformationen, Zugangsdaten.
- **OSM-Daten:** Offen lizenziert, aber nicht lizenzfrei; Lizenz- und Attributionspflichten beachten. Datenlizenzen nicht durch eine vermeintlich einheitliche Repository-Lizenz überschreiben.

Die vier historischen OSM-Wasserquellen aus Malta werden ausschließlich lokal archiviert und sind **kein aktiver Eingang** der Wasserquellenanalyse. OSM-Gebäudegeometrien bleiben eine separate Eingangsquelle.

## 4. Noch offen vor einer externen Veröffentlichung

1. **Softwarelizenz wählen:** Der Projektinhaber legt fest, unter welcher Lizenz sein Code veröffentlicht werden soll.
2. **ODB-Datenfreigabe schriftlich klären:** Dürfen Exportdaten, Karten, Objektkoordinaten oder nur aggregierte Auswertungen weitergegeben werden, und an wen? Ein vorhandener API-Key ist keine öffentliche Publikationserlaubnis.
3. **OSM-Attribution in jeder öffentlichen Karte/Publikation prüfen** sowie gegebenenfalls Zugangs-/Weitergabepflichten für zugrunde liegende ODbL-Daten erfüllen.
4. **Amtliche Datenstände und Änderungen dokumentieren:** Manifestdaten beibehalten; bei veröffentlichten KAGIS-/Statistik-Austria-Karten CC-BY-Hinweise sichtbar platzieren.
5. **Berichte vor Weitergabe prüfen:** Auch kombinierte Analysen können Standorte oder vertrauliche Fachdaten erschließen lassen.

Das Dokument ist eine technische Lizenz-Checkliste, keine rechtsverbindliche Rechtsberatung.
