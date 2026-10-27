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
