# Offene Datenbestände, Fachfragen und nächste Schritte

**Stand:** 27.10.2026 · **Pilotgemeinde:** Malta, Kärnten (GKZ 20619) · **Zweck:** Arbeitsregister für die GIS-Bestandsaufnahme und spätere fachliche Bewertung der Löschwasserversorgung.

> **Kein Löschwassernachweis:** Dieses Dokument unterscheidet verfügbar, unvollständig, ungeprüft und noch nicht beschafft. Die bloße Existenz eines Datensatzes begründet weder seine rechtliche Verbindlichkeit noch eine fachliche Freigabe der Schlussfolgerungen. Lokal vorhandene sensible Daten bleiben außerhalb des öffentlichen Repositories.

## Prioritäten und Bearbeitungsstand

- **P0:** Voraussetzung für den nächsten belastbaren Analyseschritt.
- **P1:** Wichtig für die korrekte Interpretation und Fachbewertung.
- **P2:** Ausbau, Datenqualität oder Reproduzierbarkeit.
- Status: **vorhanden**, **teilweise**, **offen**, **prüfen**. Status bezieht sich ausdrücklich auf den aktuellen Projektworkflow und nicht auf die generelle Verfügbarkeit bei Behörden.

| ID | Prio | Datenbestand / Thema | Aktueller Stand | Quelle / Ansprechstelle | Fragen, die wir beantworten müssen | Nächster Schritt |
| --- | --- | --- | --- | --- | --- | --- |
| **D01** | **P0** | **Amtliche Hausnummern/Adressregister** | **Offen**: 758 Hausnummern als frühere Bestandskennzahl; keine belegte aktuelle lokale Eingabedatei im Projektworkflow | **BEV Adressregister** (Stichtagsdaten/INSPIRE GPKG), ggf. Gemeinde Malta | Gibt es aktuelle Ausgabe **01.10.2026** als GPKG/CSV? Wie heißen GKZ, Straße, Hausnummer, Adresscode, Gebäudesubcode und Koordinatenfelder? Lizenz und Exportumfang? | BEV-Paket einmalig laden, Inhalt/Layer inspizieren, auf GKZ 20619 filtern und Quelldatum/Prüfsumme registrieren |
| **D02** | **P0** | **Adresspunkt ↔ Gebäude** | **Teilweise**: vorläufiges räumliches Skript `join_buildings_addresses.py`, noch ohne Testdatensatz | BEV-Schnittstellenbeschreibung/relationales Modell, Gemeinde Malta | Ist Geometrie **Adress-/Zugangskoordinate** oder **Gebäudekoordinate**? Existiert eine offizielle Relation Adresscode + Gebäudesubcode? Wie wird ein Gebäude mit mehreren Adressen behandelt? | Erst das **amtliche Datenmodell** prüfen; Schlüssel-Join bevorzugen, geometrischen Match nur als Plausibilisierung; vorhandenen Point-in-Polygon-Prototyp **nicht als endgültige amtliche Verknüpfung werten** |
| **D03** | **P0** | **Genehmigte / geplante Bauvorhaben und tatsächliche Gebäudeklassen** | **Offen** | Gemeinde/Bauakt, berechtigte GWR-Zugänge | Gibt es verwertbare GK, Fluchtniveau, Geschosszahlen, Gesamt-BGF und Nutzungseinheiten? Welche Daten dürfen projektbezogen verarbeitet werden? | Benötigte Attribute und Freigabeberechtigung bei zuständiger Stelle abklären; GK bleibt bis dahin unbekannt |
| **D04** | **P1** | **Planungsrechtlich höchste zulässige GK / Bebauungsart** | **Teilweise**: Flächenwidmungen lokal vorhanden; verbindliche Bebauungspläne, Höhen-/Geschossregeln noch nicht systematisch erhoben | Gemeinde Malta, KAGIS, Rechtsquellen | Welche Bebauungspläne gelten je Grundstück, welcher Stichtag? Sind maximale Gebäudehöhe, Geschosszahl, Nutzung und BGF ableitbar? | Rechtswirksame Planstände und Geometrie-/Grundstücksbezug erheben; **zulässige GK von tatsächlicher GK trennen** |
| **D05** | **P1** | **ODB-Wasserentnahmestellen – Status und technische Leistung** | **Teilweise**: lokal autorisierter ODB-Export und 41 Quellen, Status/Typ; keine bestätigte vollständige Leistungsbewertung | Kärntner Objektdatenbank, zuständige Feuerwehr/Gemeinde/Wasserversorger | Welche Quelle liefert gesichert l/min bei welcher Druckbedingung, wie lange, aus welchem Volumen? Datum letzter Prüfungen? Ist Entnahmestelle ganzjährig zugänglich? | Quellen-ID, Leistung, Druck, Vorrat, Messung, Gültigkeit und Verantwortliche abfragen; keine Leistungswerte erraten |
| **D06** | **P1** | **Straßen, Zufahrten, Weg-/Schlauchstrecken** | **Teilweise**: OSM-Straßen als Offline-Kartenhintergrund, Abstände bisher **Luftlinien** | OSM, amtliche GIP/KAGIS, örtliche Feuerwehr | Welche Wege sind befahrbar, für Einsatzfahrzeuge ausreichend, öffentlich zugänglich und ganzjährig nutzbar? Wo liegt der zulässige Entfernungsbezug der TRVB (Grundstücksgrenze/Zugang)? | Netzkonnektivität und Erreichbarkeit gesondert prüfen; keinesfalls Straßenlinien als bereits validiertes Routing interpretieren |
| **D07** | **P1** | **BEV ALS DOM/DGM – Gebäudehöhen** | **Teilweise**: 1.634/1.686 geschätzt, 52 zu wenig Pixel; 55 Medianwerte unter 1 m, 14 mit großer Höhenspreizung | BEV ALS-COGs 20250915, OSM-Grundrisse | Sind Datumsstand, vertikaler Höhenbezug, Rasterabdeckung und Dach-/Vegetationseinflüsse plausibel? Wie prüfen wir kleine Gebäude? | Prüfkarte und Ausreißerlisten abarbeiten; Objekthöhe **nicht** mit OIB-Fluchtniveau gleichsetzen |
| **D08** | **P1** | **Gebäudegrundrisse und Gebäudeidentitäten** | **Teilweise**: 1.686 OSM-Gebäude, OSM-ID als technische Verknüpfung | OSM-PBF, Kataster/Gemeinde als Kontrollquelle | Welche Gebäude sind Nebengebäude, Gebäudeteile, Abbruch-/Neubaufälle? Wie stabil sind OSM-IDs zwischen Snapshots? | Quelldatum/Hash erhalten, Differenzanalysen, spätere Referenz auf amtliche IDs getrennt behandeln |
| **D09** | **P1** | **OIB, TRVB, ÖBFV, Kärntner Recht** | **Teilweise**: OIB-Archivierung implementiert, übrige lokale PDFs/RIS-Stände teils offen; Regelwerk `draft_review_required` | BEV/OIB, ÖBFV, RIS, zuständige Fachstelle | Welche Ausgabe ist anzuwenden? Übergangsrecht? Rechte für lokale Archivkopie? Welche TRVB-Bedingungen gelten bei Bestand/Neubau? | PDFs mit SHA-256, Rechtsstand und Bezugsnachweis vollständig archivieren; Fachprüfung dokumentieren |
| **D10** | **P1** | **Wasserbedarf – Grundschutz/Objektschutz** | **Offen**: strukturierter Entwurf, keine automatisch freigegebene Anwendung | TRVB 137 F/21, VB-01/23, Feuerwehr/Gemeinde | Höchste zulässige GK statt tatsächlicher GK? Sondernutzungen, Teilraten 125/250/500 m, Dauer, Gleichzeitigkeit, Bestandsschutz? | Vollständige Regeln und Prüfbeispiele mit fachlicher Stelle validieren; `auto_assignment_enabled=false` belassen |
| **D11** | **P2** | **Widmungsgeometrie/Überlagerungen** | **Teilweise**: aktuelle Zuordnung mit bekannten Grenz- und Überlappungsprüffällen | KAGIS, Gemeinde Malta | Welche Grenzfälle sind Topologie-/Rundungseffekte? Welche Widmung ist rechtswirksam? | Quellstand und Fälle dokumentieren, keine willkürliche Zuordnung |
| **D12** | **P2** | **Offline-Reproduzierbarkeit** | **Teilweise**: GitHub-Skripte, Offline-HTML, BEV-Cache und Quellenmanifest | Repo, alle Datengeber | Welche Dateien und Versionen müssen für identische Auswertung aufbewahrt werden? Lizenzen/Weitergabe? | Gemeindeweites Datenstandsmanifest mit URL, Abrufdatum, Lizenz, CRS, SHA-256, Importskript-Version und Reportversion |
| **D13** | **P2** | **Gebäudebezogene Einwohner-/Einheiten-/Nutzungsdaten** | **Offen**: OSM-Nutzungsindikatoren reichen nicht für gesicherte GK | Statistik Austria/GWR, Gemeinde, ggf. autorisierte Fachstellen | Welche aggregierten bzw. objektspezifischen Daten dürfen verwendet werden? Sind Sondernutzungen verlässlich dokumentiert? | Berechtigung und Datenminimierung vor jeder personenbezogenen/gebäudescharfen Verarbeitung klären |

## Bezugswege für D01/D02: österreichische Adressen

1. **Primärquelle BEV:** [Österreichisches Adressregister](https://www.bev.gv.at/Services/Produkte/Adressregister/Oesterreichisches-Adressregister.html); [unentgeltliche Stichtagsdaten](https://www.bev.gv.at/Services/Downloads/Produktbezogene-Downloads/Unentgeltliche-Produkte/Adressregister.html). Der BEV-Datensatz ist amtlich und wird von den Gemeinden geführt. Die **relationalen Stichtagsdaten** sind laut BEV unter CC BY 4.0 zugänglich. **Eine ältere Zahl von 758 Hausnummern ist nicht als aktuelle BEV-Zählung zu behandeln.**
2. **Georeferenzierter Export:** [Adressregister INSPIRE, Stichtag 01.04.2026](https://data.europa.eu/data/datasets/2b6d519c-6e87-4912-a5ca-32b6421145bb?locale=de) – CSV/GPKG, EPSG:3035. Daneben sind **relationale Stichtagsdaten zum 01.10.2026** im Datenkatalog beschrieben; Format, Datei und Datenmodell vor Verwendung prüfen.
3. **Fachliche Besonderheit:** **Adresskoordinate/Zugangskoordinate** kann nahe der Grundstücksgrenze und **außerhalb** des zugehörigen Gebäudegrundrisses liegen. **Gebäudekoordinate** kann in der Gebäudemitte liegen. Das BEV verwendet Adresscode und Gebäudesubcode für Beziehungen. Daher ist **Point-in-Polygon allein keine vollständige amtliche Zuordnungsregel**.
4. **Abgleich bei Bedarf:** Die **Gemeinde Malta** ist für Adressvergabe/-führung die fachlich wichtigste Klärungsstelle. GWR-Strukturmerkmale haben eigene Zugriffsregeln und sind **nicht** mit dem frei zugänglichen Adressregister gleichzusetzen.

### Konkrete Fragen für Anfrage an BEV / Gemeinde

- Welcher **Datenstand** ist der neueste verfügbare für GKZ **20619** (gewünscht: 01.10.2026 oder neuer)?
- Können wir **Adressebene und Gebäudeebene samt Schlüsselbeziehung** (Adresscode und Gebäudesubcode) bekommen? Wie heißen die Felder im Produkt?
- Welche Koordinate liefert das gewählte Paket genau: **Adress-/Zugangskoordinate oder Gebäudekoordinate**? In welchem CRS, mit welcher Genauigkeit und welchen NULL-Werten?
- Wie werden **mehrere Gebäude pro Adresse**, **mehrere Adressen pro Gebäude**, Nebengebäude und Sonderadressen abgebildet?
- Bestehen **Lizenz-/Weitergabebeschränkungen**, obwohl die lokale Auswertung erlaubt ist? Welche Attribution ist gefordert?
- Sind für die geplante Löschwasserdokumentation weitere **nichtöffentliche Gebäudemerkmale** zulässig? Ansprechstelle/Berechtigung?

## Unmittelbarer, vorsichtiger Arbeitsablauf

1. BEV-Datenpaket und Schnittstellenbeschreibung beschaffen; Rohdatei unter `data/raw/bev/addresses/` ablegen (nicht ins Repo committen).
2. Dateiformat, Layer, Spalten, Geometrie und CRS untersuchen; **noch keine räumliche Zuordnung**.
3. Relationale amtliche Schlüssel testen. Erst **danach** `scripts/join_buildings_addresses.py` um die offizielle Schlüsselbeziehung erweitern oder räumliche Geometrieprüfung nutzen.
4. Datenqualität ausweisen: Adressen insgesamt, Gebäudeobjekte, Null-Geokoordinaten, Mehrfachrelationen, geometrische Ausreißer und ungeklärte Fälle.
5. In `reports/<GKZ>/addresses/` und der lokalen Gebäudehöhenkarte sichtbar machen; offen/mehrdeutig getrennt lassen.
6. Erst nach fachlicher Klärung konkrete GK- oder Versorgungsschlüsse ziehen.

**Pflege:** Bei jedem neuen Datenbestand Status und Datum in dieser Datei aktualisieren. Gelöste Themen bleiben zur Nachvollziehbarkeit mit Ergebnis und Quellbeleg bestehen.

## Paketprüfung (BEV 01.10.2026) – implementiert 27.10.2026

Für den aktuellen BEV-INSPIRE-Stichtag existiert ein [Metadateneintrag 01.10.2026](https://data.europa.eu/data/datasets/bed08735-6342-49a2-8eae-6247363187c3?locale=de). Die Dateiadressen müssen über dessen Distribution/BEV-Katalog abgerufen werden; solange ein stabiler Direktdownload nicht geprüft wurde, wird **keine URL im Programm geraten**.

Der erste Offline-Prüfschritt ist [`scripts/inspect_bev_address_package.py`](../scripts/inspect_bev_address_package.py). Er kann nach einmaligem manuellem Download die Inhalte von ZIP-Dateien auflisten, in GPKGs Layer und Felder auslesen oder CSV-/GeoJSON-Metadaten anzeigen. Es gibt **keinen Netzaufruf, keinen Import und keine Zuordnung**.

```powershell
git pull --ff-only origin main
python scripts\inspect_bev_address_package.py --input "C:\Pfad\BEV-Adressdaten.zip" --gemeinde 20619
```

Für ein entpacktes GeoPackage entsprechend `--input "C:\Pfad\datei.gpkg"`. Erst nach tatsächlicher Schema-Prüfung werden GKZ-Filter, Schlüsselverknüpfungen und gegebenenfalls ein Gebäudegeometrie-Abgleich entwickelt. Originalpakete lokal unter `data/raw/bev/addresses/` sichern.

## BEV-INSPIRE-GPKG eingetroffen – Schema- und Datenstandsprüfung (27.10.2026)

**D01/D02: Datenpaket vorhanden; kommunale Filter- und Schlüsselprüfung noch offen.** Lokal bereitgestellt:

- `data/raw/bev/addresses/AT-INSPIRE_AD_Address_20261001.gpkg`
- Größe: **1.657.053.184 Bytes** (ca. 1,54 GiB)
- SHA-256: `34c21e933febacd4eed80b9a88d542212e419bf63c94f22455d79d6b62319382`
- Referenz-CRS der Geometrie-Layer: **EPSG:3035**.

Die Inspektion mit `scripts/inspect_bev_address_package.py` zeigt folgende tatsächlich vorhandene Layer:
`AD_AddressAreaName`, `AD_AddressGeometry`, `AD_AddressLocatorMatchingTable`, `AD_AreaName`, `AD_BuildingGeometry`, `AD_Municipality`, `AD_PostalDescriptor`, `AD_ThoroughfareName`.

**Für die kommunale Verknüpfung relevant:**

| BEV-Layer | Im geprüften Schema vorhandene Felder | Methodische Bedeutung |
| --- | --- | --- |
| `AD_AddressLocatorMatchingTable` | `localId_ADRCD`, `inspireId_GKZ`, `addressIdentifierGeneral`, `locatorLevelValue`, `inspireId_SKZ`, `inspireId_ZO`, `inspireId_PLZ` | Kandidat zur Gemeinde- und Schlüsselzuordnung; **konkrete Werte noch prüfen** |
| `AD_AddressGeometry` | `localId_ADRCD`, `EPSG`, `RW`, `HW`, `WKT_EPSG3035` | Adressebene; Semantik und Lage der Koordinaten prüfen |
| `AD_BuildingGeometry` | `localId_ADRCD`, `localId_ADRCD_SUBCD`, `buildingIdentifier`, `buildingNumber`, `geometrySpecification` | Gebäudeebene und Subcodes; Relation zum Gebäudegrundriss gesondert prüfen |
| `AD_Municipality` | `localId_GKZ`, `inspireId_GKZ`, `text` | Gemeinde-Referenz |
| `AD_ThoroughfareName`, `AD_AddressAreaName`, `AD_PostalDescriptor` | Namen und Postleitzahlen | Ergänzung der maschinenlesbaren Adressbeschreibung |

**Wichtig:** Aus der Existenz der Spalten lässt sich noch **nicht** ableiten, wie viele **eindeutige Adressen oder Gebäude** für Malta vorhanden sind. Die frühere Zahl 758 bleibt ein separater, bisher nicht gegengeprüfter Bestand.

Die nächste Stufe ist `scripts/probe_bev_address_municipality.py`. Sie untersucht die realen GKZ-Werte, passenden Adresscodes und optional die über `localId_ADRCD` verknüpften Gebäude-Datensätze direkt in der SQLite-/GeoPackage-Datenbank, **ohne 1,66 GB in GeoPandas einzulesen oder Ergebnisse zu ändern**:

```powershell
git pull --ff-only origin main
python scripts\probe_bev_address_municipality.py --gemeinde 20619
```

Die Ausgabe umfasst Beispielwerte von `inspireId_GKZ`, Kandidaten für GKZ 20619, Anzahl zugehöriger Matching-Zeilen und eindeutiger Adresscodes. Der anfängliche Filter nutzt bewusst nur eine **GKZ-Teilzeichenfolge** und muss anhand der tatsächlich gemeldeten Referenzwerte auf einen exakten Bezeichner präzisiert werden. Für einen gesonderten, potentiell teureren Schlüsselabgleich:

```powershell
python scripts\probe_bev_address_municipality.py --gemeinde 20619 --check-building-links
```

**Nächste offene Fragen:** Ist `inspireId_GKZ` für Malta eindeutig? Welcher Feldwert trägt die tatsächlich sichtbare Hausnummer? Gibt es pro `localId_ADRCD` mehrere Matching-Einträge und Gebäude-Subcodes? Welche Geometrie ist Zugang und welche Baukörper? Erst nach diesen Befunden wird ein lokaler Gemeindeexport mit vollständiger Adressbeschreibung und der Verbindung zu OSM-Grundrissen erstellt.

### Malta: erster BEV-Filter erfolgreich (27.10.2026)

Die lokale Probe ergab:

- `AD_Municipality.localId_GKZ = 20619`, Gemeindename `Malta`.
- Der tatsächliche INSPIRE-Gemeindeschlüssel lautet **`AT.BEV.AD.GKZ.20619`**.
- **824 Matching-Tabellenzeilen**, **824 unterschiedliche `localId_ADRCD`**, **0 NULL-Adresscodes** für den bisherigen GKZ-Teilzeichenfolgenfilter; da alle Beispieldatensätze exakt den bestätigten GKZ-Schlüssel tragen, wurde das Skript jetzt auf **exakten Gleichheitsfilter** umgestellt. Die Zahl muss beim erneuten Lauf bestätigt werden.
- `addressIdentifierGeneral` enthält erkennbare Hausnummernwerte (Beispiele `1`, `2`, `7a`, `7b`).
- `locatorLevelValue` in den Beispielen: `siteLevel`; das allein bestätigt **nicht**, dass die Geometrie innerhalb eines OSM-Gebäudepolygons liegt.

**Folgerung:** Die früher genannte Bestandskennzahl **758** ist nicht mit dem nun abgefragten BEV-Datenstand gleichzusetzen. Derzeit sind **824 verschiedene Adresscodes**, aber noch **nicht 824 Gebäude** oder zwingend **824 unterschiedliche postalische Hausnummern** nachgewiesen.

**Nächster Prüfbefehl:** `python scripts\probe_bev_address_municipality.py --gemeinde 20619 --check-building-links`. Er liefert zusätzlich vorhandene `AD_BuildingGeometry`-Zeilen, die Anzahl verknüpfter Adresscodes und Gebäudesubcodes sowie Beispielwerte. Keine automatische Verknüpfung mit OSM-Gebäuden vor Prüfung der Geometrien und Datenmodell-Semantik.

### BEV-Gebäudebeziehungen geprüft und Gemeindeexport vorbereitet (27.10.2026)

Die zweite Probe der **BEV INSPIRE Adressen, Datenstand 01.10.2026**, bestätigte für Malta (GKZ `20619`):

| Kennzahl | Ergebnis | Interpretation |
| --- | ---: | --- |
| Amtliche Matching-Zeilen | **824** | Exakt `AT.BEV.AD.GKZ.20619` |
| Unterschiedliche Adresscodes `localId_ADRCD` | **824** | Keine leeren oder doppelten Adresscodes in der Auswahl |
| BEV-`AD_BuildingGeometry`-Zeilen | **788** | Gebäude-**Referenzpunkte**, keine OSM-Gebäudepolygone |
| Mit BEV-Gebäudezeilen verknüpfte Adresscodes | **779** | 45 der 824 Adresscodes ohne zugehörige Gebäudezeile |
| Unterschiedliche Gebäude-Subcodes | **788** | `localId_ADRCD_SUBCD`, z. B. `6106447.001` |
| Zusätzliche Gebäudezeilen relativ zu 1 je Adresse | **9** | Verteilung auf tatsächlich mehrfach zugeordnete Adressen noch nicht ausgewiesen |

Die Beispieldaten enthalten u. a. `buildingIdentifier = Osnabrückerhütte`, `Kattowitzerhütte`, `Gmünder Hütte` und `buildingNumber` wie `0163792`. Die Spalte `addressIdentifierGeneral` trägt Werte wie `7a` und `7b`.

**Neue Verarbeitung:** [`scripts/export_bev_municipality_addresses.py`](../scripts/export_bev_municipality_addresses.py) extrahiert anhand des **exakten** Gemeindeschlüssels aus dem lokalen 1,66-GB-GPKG die zugehörigen Datensätze. Die Abfragen laufen über SQLite; der nationale Datenbestand wird nicht komplett in den Arbeitsspeicher geladen. Die GeoPackage-Punktgeometrien werden von **EPSG:3035 nach WGS84 (EPSG:4326)** umgerechnet und absichtlich **getrennt** exportiert:

- `data/processed/20619/bev_addresses/bev_adresspunkte.geojson`: BEV-Adressreferenzpunkte.
- `data/processed/20619/bev_addresses/bev_gebaeudepunkte.geojson`: BEV-Gebäudereferenzpunkte inklusive originaler BEV-Adresscodes und Gebäude-Subcodes.
- `data/processed/20619/bev_addresses/bev_adressen.csv`: alle 824 Adresscodes und textuelle Hausnummer, Orts-/Straßenreferenzen, Anzahl verknüpfter Gebäudereferenzen.
- `data/processed/20619/bev_addresses/bev_adressen_summary.json`: Quelle, SHA-256, Projektionsangaben, Geometriezahlen und Mehrfachrelationen.

```powershell
git pull --ff-only origin main
python scripts\export_bev_municipality_addresses.py --gemeinde 20619
```

**Bewusst noch nicht gemacht:** Ein BEV-Gebäudereferenzpunkt beweist ohne räumliche Prüfung **nicht**, welcher der **1.686 OSM-Gebäudegrundrisse** dazugehört. Der vorhandene Adresspunkt-PIP-Prototyp darf **nicht direkt** auf die BEV-Zugangs-/Adresspunkte als sichere Gebäudeidentifikation angewendet werden. Im nächsten Arbeitsschritt werden die amtlichen **Gebäudepunkte** räumlich mit OSM-Polygonen abgeglichen und eindeutige Treffer bzw. Grenz-/Abweichungsfälle ausgewiesen.

**Datenschutz und Reproduzierbarkeit:** Alle Ausgabedateien in `data/processed/` bleiben lokal und außerhalb von Git. Ausgangs-GPKG mit SHA-256 `34c21e933febacd4eed80b9a88d542212e419bf63c94f22455d79d6b62319382`.

### BEV-Gemeindeexport erfolgreich; geometrischer OSM-Abgleich implementiert (27.10.2026)

Der lokale Export von `AT-INSPIRE_AD_Address_20261001.gpkg` war erfolgreich. Die dabei erschienenen `DeprecationWarning`-Meldungen betrafen ausschließlich `shapely.ops.transform`; die vier Ergebnisse wurden vollständig erzeugt. Der Generator ist auf direkte Punktkoordinaten-Transformation via `pyproj.Transformer` und `shapely.geometry.Point` umgestellt.

**Bestätigte Exportkennzahlen für Malta:**

- **824** amtliche Adresscodes, **824** Adresspunktgeometrien, **0** Adressen ohne Adressgeometrie.
- **788** BEV-Gebäudepunkte mit **788** unterschiedlichen Gebäude-Subcodes.
- **779** Adresscodes mit mindestens einem BEV-Gebäudepunkt; **45** ohne Gebäudepunkt.
- **8** Adresscodes mit mehreren BEV-Gebäudepunkten (insgesamt **9** zusätzliche Punkte über eine 1:1-Relation hinaus).

**Nächster Schritt, AP3:** Das neue [`scripts/join_bev_building_points_osm.py`](../scripts/join_bev_building_points_osm.py) vergleicht genau die **788 BEV-Gebäudereferenzpunkte** mit den **1.686 OSM-Gebäudegrundrissen** in EPSG:31287. Die BEV-Adress-/Zugangspunkte werden **nicht** zur automatischen Gebäudeidentifikation verwendet.

| Status | Interpretation |
| --- | --- |
| `inside_unique` | BEV-Gebäudepunkt liegt **streng innerhalb genau eines** OSM-Polygons: geometrisch eindeutiger Zuordnungskandidat |
| `multiple_or_boundary` | Punkt liegt auf einer Grenze oder in mehreren OSM-Polygonen: Prüffall |
| `near_review` | Punkt liegt außerhalb, aber höchstens 15 m vom OSM-Grundriss entfernt: Prüffall, **keine automatische Zuordnung** |
| `unmatched` | Kein OSM-Gebäude innerhalb des Suchradius: offener Fall |

```powershell
git pull --ff-only origin main
python scripts\join_bev_building_points_osm.py --gemeinde 20619
python scripts\review_building_als_heights.py --gemeinde 20619 --open
```

Der Zuordner erzeugt `reports/20619/addresses/bev_gebaeudepunkte_osm_zuordnung.csv` (jede BEV-Subcode-Geometrie inklusive Kandidaten), `gebaeude_adressen.csv` (alle OSM-Gebäude mit BEV-Adressinformationen) und `bev_osm_zuordnung_summary.json` (Statuszahlen und Provenienz). **Achtung:** Bestehende Zuordnungsdateien werden zum Schutz vor versehentlicher Überschreibung nur mit dem expliziten Schalter `--overwrite` ersetzt.

Erst nachdem die lokale Ausgabe der Zuordnung vorliegt, können wir belastbar sagen, wie viele OSM-Gebäude einen geometrisch eindeutigen BEV-Gebäudepunkt enthalten. Eine solche Zuordnung ist **kein amtlich bestätigter OSM-Identitätsnachweis**; bei mehreren Adressen je Gebäude werden Adresscode und Gebäude-Subcode getrennt erhalten. Fehlende Adressen bedeuten nicht, dass ein Gebäude ungenutzt ist.

### AP3 – BEV-Gebäudepunkte erfolgreich mit OSM abgeglichen (27.10.2026)

**Lokal bestätigtes Ergebnis** mit `scripts/join_bev_building_points_osm.py --gemeinde 20619` und anschließend erfolgreichem `scripts/review_building_als_heights.py --gemeinde 20619 --open`:

| Metrik | Ergebnis | Bedeutung |
| --- | ---: | --- |
| BEV-Gebäudereferenzpunkte | **788** | Zu analysierende amtliche Gebäudepunkte |
| `inside_unique` | **747** | Punkt strikt innerhalb genau eines OSM-Gebäudepolygons, nur geometrisch zugeordnet |
| `near_review` | **29** | Punkt außerhalb eines Polygons, mindestens ein Kandidat innerhalb von 15 m |
| `unmatched` | **12** | Kein OSM-Polygon innerhalb des 15-m-Prüfradius |
| `multiple_or_boundary` | **0** | In dieser Auswertung keine Treffer an Polygonrändern/Überlappungen |
| OSM-Gebäude mit mindestens einem BEV-Innen-Treffer | **737** | **737 von 1.686** OSM-Gebäuden, keine gesicherte amtliche Gebäudeidentifikation |
| Unterschiedliche zugeordnete BEV-Adresscodes | **740** | Bezieht sich nur auf die geometrischen Innen-Treffer, **nicht** auf alle 824 BEV-Adressen |
| OSM-Gebäude ohne BEV-Innen-Treffer | **949** | Kein Adresstreffer ist **kein** Nutzungs- oder Wohnstatusnachweis |

**Rechenhinweis:** Die Anzahl BEV-Punkte ist nicht die Anzahl betroffener Gebäude: 747 Innen-Treffer verteilen sich auf 737 OSM-Gebäude. 740 verschiedene BEV-Adresscodes kommen in den Innen-Treffern vor. Diese Mengen beschreiben unterschiedliche Identitäten; die Differenzen dürfen nicht als Fehler oder bewiesene Mehrfachhausnummern interpretiert werden.

**Kartenintegration erfolgreich:** `reports/20619/gk_inventory/gebaeude_als_hoehenkarte.html` sowie `gebaeude_gk_merkmale_mit_als.csv` wurden neu erstellt; der Generator meldete die eingebundene `reports/20619/addresses/gebaeude_adressen.csv`. Die Kartendarstellung selbst ist damit noch nicht fachlich visuell geprüft.

**Priorisierte Prüfliste:**
1. **29 `near_review`:** Lageabweichung BEV-Gebäudepunkt ↔ OSM-Polygon, Gebäudegrundriss, Subcode und mögliche Nebengebäude kontrollieren; keine automatische Zuweisung.
2. **12 `unmatched`:** Fehlende/geänderte OSM-Grundrisse, Lage des BEV-Punktes und Sonderfälle (z. B. Almhütten) prüfen.
3. **949 OSM-Gebäude ohne Innen-Treffer:** Nach Nutzungsindikatoren, Gebäudegröße, Lage und OSM-Tags untersuchen; nicht automatisch als adresslos oder ungenutzt klassifizieren.
4. **Mehrfachzuordnungen:** Bei zehn zusätzlichen BEV-Punkt-zu-OSM-Gebäude-Treffern gegenüber der Zahl betroffener OSM-Gebäude und sieben Adresscode-Differenzeinheiten insbesondere Gebäudeteil-/Mehrfachadressen-Konstellationen untersuchen. Keine 1:1-Beziehung erzwingen.
5. **BEV ↔ OSM:** Ein eindeutiger Punkt-in-Polygon-Treffer ist ein plausibler geometrischer Kandidat, aber **keine** amtlich bestätigte Identitätsrelation.
6. **Darstellung:** In der Höhenkarte prüfen, ob amtliche Adresse, Anzahl und `address_status` korrekt sowie von OSM-Adressen unterscheidbar erscheinen.

**Verfügbare lokale Prüfdateien:**
- `reports/20619/addresses/bev_gebaeudepunkte_osm_zuordnung.csv`
- `reports/20619/addresses/gebaeude_adressen.csv`
- `reports/20619/addresses/bev_osm_zuordnung_summary.json`

Damit ist die **erste Geometriezuordnung umgesetzt**, die fachliche Verifizierung und Behandlung der Prüffälle bleiben ausdrücklich offen.

### Interaktive BEV/OSM-Prüfkarte (27.10.2026)

Neu: [`scripts/show_bev_osm_review_map.py`](../scripts/show_bev_osm_review_map.py) erstellt aus dem **bereits erfolgten** BEV-/OSM-Abgleich eine lokale HTML-Karte `reports/20619/addresses/bev_osm_pruefkarte.html`. Sie lädt nur lokale Projektdateien und verwendet **keine Internet-Kartenkacheln**. Die ursprüngliche OSM-/BEV-Zuordnung wird nicht verändert.

```powershell
git pull --ff-only origin main
python scripts\show_bev_osm_review_map.py --gemeinde 20619 --open
python scripts\generate_report_index.py --gemeinde 20619 --open
```

Für den vorliegenden Stand werden **41 offene BEV-Punktfälle** erwartet: **29 `near_review`**, **12 `unmatched`**, **0 `multiple_or_boundary`**. Die Karte prüft vor dem Rendern, ob die Statuszahlen aus CSV und JSON zusammenpassen und ob die 788 BEV-Gebäude-Subcodes im lokalen GeoJSON exakt zum Zuordnungsergebnis passen. Bei widersprüchlichen Daten bricht sie ab und fordert einen erneuten Abgleich.

**Bedienung:** Fälle mit Status-Checkboxen filtern, über die Subcode-Auswahlliste oder „Nächster sichtbarer Prüffall“ auf einen BEV-Gebäudepunkt zentrieren; OSM-Gebäude und Straßen einzeln ein-/ausblenden; zoomen und verschieben. Auf Basis der vorhandenen Kandidaten-IDs werden mögliche OSM-Polygone hervorgehoben. **Rote `unmatched`-Punkte haben im 15-m-Radius keinen OSM-Treffer; das ist keine Aussage, dass es dort kein reales Gebäude gibt.** Der standardmäßig 15 m große Prüfradius stammt aus der vorherigen Zuordnung und ist kein gesetzlicher Abstand.

**Weiteres Vorgehen:** Die 41 Fälle anhand von Punktlage, Gebäudepolygon, aktuellem OSM-Stand und ggf. zugelassenen amtlichen Luftbild-/Gebäudedaten prüfen. Erst danach eine **separate, nachvollziehbare Review-Entscheidungsliste** entwerfen (Bearbeiter, Datum, Nachweis, Korrekturtyp, optional OSM-ID). Keine manuelle Entscheidung in die Original-BEV-/OSM-Exporte schreiben. Die vollständige Offline-Karte inklusive BEV-Adress- und Gebäudedaten gehört **nicht in das öffentliche Repository**.

### AP3 – 2-m-Toleranz für BEV-Gebäudepunkte (27.10.2026)

Nach Sichtkontrolle eines BEV-Referenzpunktes direkt an der OSM-Gebäudekante wurde der geometrische Abgleich um **`boundary_tolerance`** erweitert. **2,0 m ist eine projektinterne Prüfschwelle, kein amtlicher/geodätischer Genauigkeitsnachweis und keine Rechtsnorm.**

- `inside_unique`: Punkt streng innerhalb genau eines OSM-Gebäudegrundrisses, unverändert.
- `boundary_tolerance`: Punkt außerhalb jedes OSM-Polygons, ein und nur ein Polygon in **höchstens 2,0 m Abstand**. Vorläufig geometrisch zugeordnet, aber **weiterhin fachlich zu prüfen**.
- `near_review`: Punkt außerhalb und mindestens ein Kandidat in 15 m, jedoch **keine eindeutige** Zuordnung innerhalb 2 m (einschließlich konkurrierender Gebäude im 2-m-Bereich).
- `unmatched`: kein Kandidat innerhalb 15 m.
- `multiple_or_boundary`: Punkt berührt Polygonrand oder mehrere Polygone; bleibt **ohne automatische Zuordnung**, auch wenn die metrische Distanz 0 ist.

**Neu:** Die Statuswerte werden im BEV-zu-OSM-CSV und Summary getrennt ausgewiesen. `gebaeude_adressen.csv` enthält `boundary_tolerance_count` und `match_method`, sodass die Höhenkarte eine tolerierte Zuordnung gegenüber dem strengen Innentreffer unterscheidbar kennzeichnet. In der BEV/OSM-Prüfkarte werden Toleranzpunkte **grün** angezeigt und bleiben über einen eigenen Filter anwählbar. Die Tabelle verändert weder BEV-Originaldaten noch OSM-Geometrien.

Da die alten lokalen CSV-/JSON-Ergebnisse geschützt sind, **muss** der Abgleich für den neuen Stand einmalig mit `--overwrite` ausgeführt werden:

```powershell
git pull --ff-only origin main
python scripts\join_bev_building_points_osm.py --gemeinde 20619 --boundary-tolerance-m 2 --overwrite
python scripts\show_bev_osm_review_map.py --gemeinde 20619 --open
python scripts\review_building_als_heights.py --gemeinde 20619 --open
```

Danach die **neuen**, lokal berechneten Fallzahlen ablesen und mit dem bisherigen Ausgangsstand **747 strikt innerhalb / 29 nahe / 12 ohne Treffer** vergleichen. Der neue `boundary_tolerance`-Bestand darf nicht vorausberechnet werden; die Anzahl steht erst nach erneutem lokalen Skriptlauf fest. Wenn die Prüfkarten in der Berichtszentrale erscheinen sollen: `python scripts\generate_report_index.py --gemeinde 20619 --open`.

**Noch offen:** Ein fachlicher Reviewstatus (bestätigt/abgelehnt/ungeklärt, Bearbeiter, Datum, Bild-/Quellenbeleg) sollte getrennt von dieser rein geometrischen Kategorie gespeichert werden.

### 2-m-Toleranz: lokal bestätigte Ergebnisse (27.10.2026)

Alle drei Verarbeitungsschritte wurden lokal erfolgreich ausgeführt: `join_bev_building_points_osm.py --boundary-tolerance-m 2 --overwrite`, `show_bev_osm_review_map.py --open` und `review_building_als_heights.py --open`.

| Status | Vorher (ohne Toleranz) | Jetzt (2 m) | Interpretation |
| --- | ---: | ---: | --- |
| `inside_unique` | 747 | **747** | Strenge Innentreffer, unverändert |
| `boundary_tolerance` | 0 | **16** | Vorläufige geometrische Zuordnung innerhalb 2 m mit genau einem Kandidaten |
| `near_review` | 29 | **13** | Weiterhin ungeklärte Nahfälle |
| `unmatched` | 12 | **12** | Kein OSM-Grundriss innerhalb 15 m |
| **Summe BEV-Gebäudepunkte** | **788** | **788** | Vollständige, disjunkte Zuordnung |

- **753 von 1.686 OSM-Gebäuden** besitzen nun mindestens einen zugeordneten BEV-Gebäudereferenzpunkt (einschließlich Toleranz); ohne Toleranz waren es **737**. **933 OSM-Gebäude** besitzen derzeit keinen solchen Punkt.
- **756 unterschiedliche BEV-Adresscodes** sind den geometrisch zugeordneten BEV-Punkten zugehörig (vorher 740).
- Die Prüflandkarte zeigt weiterhin **41 Fälle**: 16 separat grün dargestellte **Toleranzfälle** zur Validierung, 13 `near_review` und 12 `unmatched`. Damit **25 ungeklärte** Fälle ohne Zuordnung; **16 zusätzliche vorläufig zugeordnete** Fälle, die trotzdem fachlich geprüft werden sollten.
- Die Prüfkarte wurde mit **1.686 OSM-Gebäuden** und **1.383 OSM-Straßen-/Wegegeometrien** erfolgreich erstellt: `reports/20619/addresses/bev_osm_pruefkarte.html`.
- Die Gebäudehöhenkarte und CSV wurden erneut mit eingebundenen amtlichen Adressen erstellt: **1.686 Gebäude**, **1.634 ALS-Höhenschätzungen**; Qualitätsflags unverändert (55 sehr niedrige Schätzungen, 52 unzureichende Pixel, 14 große Dachhöhenspannen).

**Methodischer Vorbehalt:** Die neue Kennzahl **753** ist keine Zahl amtlich bestätigter BEV/OSM-Gebäudeidentitäten; die 16 Toleranzpunkte sind explizit nur Kandidaten unter unserer selbst gewählten 2-m-Heuristik. Für Analysen, die ausschließlich streng geprüfte Geometriezuordnungen verwenden sollen, ist weiterhin die Menge der **737 OSM-Gebäude mit `inside_unique`** maßgeblich. Die 45 amtlichen Adresscodes ohne BEV-Gebäudepunkt werden durch diese Berechnung nicht verändert.

**Nächste fachliche Arbeiten:** Die **13 Nahfälle** und **12 nicht zuordenbaren BEV-Punkte** untersuchen, anschließend die **16 grün markierten Toleranzfälle** plausibilisieren. Eine manuell freigegebene Zuordnung getrennt mit Quelle, Prüfer und Datum dokumentieren; weder OSM- noch BEV-Rohdaten überschreiben.

### Übergabe ungeklärter Geometriefälle an Gemeinde / Fachstelle (27.10.2026)

**Entscheidung:** Wir lösen unklare BEV/OSM-Geometrien nicht allein aufgrund von Karteneindruck oder eines Toleranzwertes auf. Fachliche Rückmeldung von Gemeinde, Datenführenden oder zuständiger Stelle ist vorzuziehen.

[`scripts/export_bev_osm_municipality_questions.py`](../scripts/export_bev_osm_municipality_questions.py) stellt aus dem existierenden lokalen Abgleich eine **CSV-Liste mit zunächst 25 offenen Fällen** bereit: **13 `near_review` und 12 `unmatched`**. Es enthält BEV-Gebäude-Subcode, Adresscode, Straße/Ortsteil/Hausnummer, BEV-Gebäudenummer und -bezeichnung, OSM-Kandidaten, Abstand und präzise Rückfrage sowie leere Spalten für Prüfer, Prüftag, Rückmeldung, Entscheidung und Nachweis.

```powershell
git pull --ff-only origin main
python scripts\export_bev_osm_municipality_questions.py --gemeinde 20619
python scripts\generate_report_index.py --gemeinde 20619 --open
```

Ergebnis: `reports/20619/addresses/gemeinde_rueckfragen_bev_osm.csv`, verlinkt in der Gemeindeübersicht. **Optional** können 16 `boundary_tolerance`-Fälle mit `--include-tolerance` ergänzt werden. Die Standardliste enthält diese bewusst **nicht**.

**Wichtig:** Die CSV ist ein Arbeitsentwurf zur fachlichen Abstimmung; keine Nachricht wird automatisch gesendet. Vor Weitergabe Inhalt, Herkunft und zulässigen Empfängerkreis prüfen. Um manuell eingetragene Antworten nicht zu verlieren, wird die CSV nicht ohne `--overwrite` erneut erzeugt. Bearbeitete Antworten vor einer Neu-Erzeugung separat sichern. Die ursprünglichen BEV-/OSM-Rohdaten bleiben unberührt.

### Erläuterungsseite / Glossar

Die zentrale Berichts-Navigation erzeugt nun **`reports/glossar.html`**, vollständig offline, und verlinkt sie sowohl in `reports/index.html` als auch in `reports/20619/index.html`. Enthalten sind u. a. BEV, OSM, ODB, ALS, DOM, DGM, GIS, EPSG, GPKG, GKZ, INSPIRE, GK, OIB, TRVB, ÖBFV, RIS sowie die geometrischen Statuscodes und die Differenz zwischen 2-m-/15-m-Heuristik und fachlicher Bestätigung.

**OEM und BSM:** Im derzeitigen Projekt nicht als eindeutige Fachkürzel dokumentiert, daher bewusst als klärungsbedürftig beschrieben; „OEM“ könnte „OSM“ gemeint haben, wird aber nicht stillschweigend umgedeutet.

### AP1 – Anforderungsmatrix als Arbeitsgrundlage (27.10.2026)

Die neue [Anforderungsmatrix GK/Löschwasser](anforderungsmatrix-gk-loeschwasser.md) verknüpft die Kärntner Bautechnikverordnung 2024, OIB 2023, K-GFPO §31 sowie die dokumentierten TRVB-/ÖBFV-Quellen mit tatsächlich vorhandenen Daten und fehlenden Nachweisen. Sie dient der Vorbereitung fachlicher Rückfragen und **verändert die Automatisierungssperre im Regelwerksentwurf nicht**. Als erste priorisierte offene Merkmale gelten Fluchtniveau, Geschosszahl, Brutto-Grundfläche, Nutzungseinheiten, nachgewiesene Entnahmeleistung und Erreichbarkeit.
