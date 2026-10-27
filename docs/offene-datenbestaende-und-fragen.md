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
