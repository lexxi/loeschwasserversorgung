# AP1 – Anforderungsmatrix Gebäudeklassen und Löschwasser

**Arbeitsstand:** 27.10.2026 · **Pilot:** Malta (GKZ 20619) · **Status:** `draft_review_required`

> **Kein automatischer Rechts- oder Versorgungsnachweis.** Die Matrix verbindet Rechts-/Fachquellen mit den tatsächlich vorhandenen GIS-Attributen. Sie ist eine Prüf- und Beschaffungsmatrix, **kein** freigegebener Regelalgorithmus. Maßgeblich sind zum konkreten Vorhaben die anwendbaren Fassungen, landesrechtlichen Übergangsregeln und die fachliche Bewertung.

## 1. Verifizierte Quellen und Geltungsfragen

| Quelle | Bezugsstelle / Fassung | Für uns relevant | Prüfstatus |
| --- | --- | --- | --- |
| Kärntner Bautechnikverordnung 2024 (K-BTV) | [RIS Gesamtausgabe](https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=LrK&Gesetzesnummer=20000961), § 1; RIS-Abfrage am 27.10.2026 | § 1 benennt u. a. **OIB-Richtlinie 2, Brandschutz, Ausgabe Mai 2023** als technischen Regelwerksbezug | Verweis im RIS überprüft; Anwendbarkeit je Bauakt, Abweichung und Übergangsrecht offen |
| OIB-Begriffsbestimmungen | [Original Mai 2023](https://www.oib.or.at/sites/default/files/oib-rl_begriffsbestimmungen_ausgabe_mai_2023.pdf), S. 6 | GK1–GK5, Fluchtniveau, oberirdische Geschosse, Brutto-Grundfläche, Nutzungseinheiten, Zugänglichkeit | Definitionsstruktur vorhanden; **kein** an realen Objekten geprüfter GK-Klassifikator |
| OIB-Richtlinie 2 – Brandschutz | [Mai 2023](https://www.oib.or.at/sites/default/files/oib-rl_2_ausgabe_mai_2023.pdf) | Brandschutzanforderungen, Anwendungs- und Sonderfälle | Primärquelle referenziert; objektspezifische Anwendbarkeit nicht geprüft |
| Kärntner Gefahrenpolizei- und Feuerpolizeiordnung (K-GFPO) | [RIS § 31 / konsolidiert](https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=LrK&Gesetzesnummer=20000024) | Gemeindliche Sorge für jederzeit vorhandenes Löschwasser in bebauten Gebieten sowie unbehinderte Erreichbarkeit und Benützbarkeit von Wasserentnahmestellen | Gesetzestext überprüft; konkrete erforderliche Menge wird dadurch **nicht** pauschal festgelegt |
| TRVB 137 F/21 – Löschwasserbedarf | [ÖBFV Produkt-/Bezugsseite](https://www.bundesfeuerwehrverband.at/produkt/trvb-137-21-f-loeschwasserbedarf/) · 01.09.2021 | Referenz für Grundschutz-Tabelle und gesonderten Objektschutz | Im vorhandenen `config/firewater_rulebook.json` tabellarisch **als Entwurf** modelliert; vollständige Fachfreigabe offen |
| ÖBFV VB-01/23 – Die Löschwasserversorgung | [ÖBFV Produkt-/Bezugsseite](https://www.bundesfeuerwehrverband.at/produkt/vb-01-23-rl-die-loeschwasserversorgung/) · 15.10.2023 | Technische Fachgrundlage für Löschwasserversorgung | Im Quellenkatalog gelistet; nicht automatisch anwendbar, zugriffsberechtigte Originalfassung fachlich prüfen |

Die Originalverweise und ggf. zulässige Offline-Kopien sind in `config/reference_documents.json` inventarisiert. Das vorhandene `config/firewater_rulebook.json` ist **Version 0.2.0**, hat `auto_assignment_enabled=false` und bleibt unverändert.

## 2. Anforderungsmatrix – Gebäudeklassen

**Legende:** `vorhanden` = lokaler Projektwert; `Indiz` = nur heuristisch; `offen` = nicht belastbar nachgewiesen. Die OIB-Definitionen können mehrere Merkmale **gleichzeitig** erfordern. Aus dem Fehlen eines Merkmals darf keine GK gefolgert werden.

| ID | Erforderliches Merkmal / Unterscheidung | Maßgebliche Quelle | Derzeitiger Datenbestand | Eignung für GK | Fehlender Nachweis / Beschaffungsfrage |
| --- | --- | --- | --- | --- | --- |
| GK-01 | Fluchtniveau in Metern, **nicht Dach-/Gesamthöhe** | OIB-Begriffsbestimmungen Mai 2023 | BEV-ALS-Dachhöhen geschätzt: 1.634 von 1.686 OSM-Gebäuden | **Nicht ausreichend** | Tatsächliches Fluchtniveau aus Plänen / Bauakt / Bestandsaufnahme |
| GK-02 | Zahl der **oberirdischen Geschosse** | OIB-Begriffsbestimmungen | OSM-`building:levels` teils vorhanden | Indiz, nicht amtlich bestätigt | Bauakt, verifizierte Geschossanzahl und Definition oberirdisch |
| GK-03 | Gesamte Brutto-Grundfläche der **oberirdischen Geschosse** | OIB-Begriffsbestimmungen (u. a. GK1/2) | OSM-Grundrissfläche je Gebäude | **Nicht ausreichend**; Grundriss ≠ Summe BGF | Geschossflächen, Baupläne, Abgrenzung Gebäudeeinheiten |
| GK-04 | Nutzfläche **je Wohnung / Betriebseinheit** (z. B. GK4-a) | OIB-Begriffsbestimmungen | Keine belastbaren Wohnungs-/Betriebseinheitenflächen | offen | Baubeschreibung / Geschosspläne / zulässige Registerdaten |
| GK-05 | Anzahl und Art von Wohnungen / Betriebseinheiten | OIB-Begriffsbestimmungen | OSM-`building:flats`, `building:units` nur gelegentliche Indizien | offen | Bestätigte Nutzungseinheiten |
| GK-06 | Freistehend, Reihenhaus, baulicher Zusammenhang | OIB-Begriffsbestimmungen | OSM-Gebäudepolygone und Tags | Indiz | Baulicher Bestand, Grundstücks-/Gebäudeabgrenzung |
| GK-07 | Zugänglichkeit an mindestens drei Seiten (GK1 / GK2-c) | OIB-Begriffsbestimmungen | OSM-Straßen als Kartenhintergrund | **Nicht ausreichend** | Eigener Grund, Verkehrsflächen, reale Zugangsmöglichkeiten |
| GK-08 | Ausschließliche Wohnnutzung vs. andere Nutzung | OIB-Begriffsbestimmungen und OIB RL 2 | OSM-`building`, `building:use`, `amenity`, `tourism` | Indiz | Gemeinde, Bauakt, bestätigte Nutzung und Sondernutzungen |
| GK-09 | GK1, GK2-a/b/c, GK3, GK4-a/b, GK5 als vollständige **Kombinationsprüfung** | OIB-Begriffsbestimmungen | `config/firewater_rulebook.json` enthält Varianten als Modell | **Nicht ausführungsreif** | Alle vorstehenden Merkmale und Norm-/Ausnahmenprüfung |
| GK-10 | Tatsächliche GK gegenüber **höchster planungsrechtlich zulässiger GK** | OIB, K-BTV, geltende Bebauungspläne | KAGIS-Widmung und Gebäudeinventar | Beide **unbekannt** | Rechtswirksame Bebauungspläne, Bestandsakten, Stichtag |
| GK-11 | Objekte oberhalb der GK5-Definitionsgrenze und Sonderbauten | OIB-Begriffsbestimmungen / RL 2 | BEV-ALS-Höhenschätzung | Nur Auffälligkeit | Fluchtniveau, Spezialregelungen, sachverständige Prüfung |

**Wichtige Schwellen aus OIB-Begriffsbestimmungen Mai 2023 (nur Orientierung, keine fertige Entscheidungstabelle):** GK1–GK3 enthalten Voraussetzungen im Bereich höchstens 3 oberirdische Geschosse / höchstens 7 m Fluchtniveau, GK4 höchstens 4 oberirdische Geschosse / höchstens 11 m Fluchtniveau mit weiteren Einheitendetails, GK5 höchstens 22 m Fluchtniveau bei Ausschluss der niedrigeren Klassen. **Die weiteren Flächen-, Nutzungs-, Anordnungs- und Zugänglichkeitsbedingungen sind unverzichtbar.** Der Wert 22 m ist kein allgemeiner Dachhöhengrenzwert.

## 3. Anforderungsmatrix – Löschwasser und räumliche Zuordnung

| ID | Fachfrage / Parameter | Referenz / fachlicher Stand | Bereits vorhandene Daten | Belastbar bewertbar? | Fehlende Angaben / nächste Stelle |
| --- | --- | --- | --- | --- | --- |
| LW-01 | Zuständigkeit: Löschwasser in bebauten Gebieten und Zugang | K-GFPO § 31 | Gemeindegrenze und 41 lokal erfasste ODB-Wasserentnahmestellen | **Nur Inventur** | Gemeinde / Feuerwehr: Erfüllung, Erreichbarkeit und regelmäßige Kontrolle |
| LW-02 | Grundschutzbedarf nach zutreffender Gebäudeklasse und Nutzung | TRVB 137 F/21, vorhandenes Regelwerk **Entwurf** | `water_demand_levels` im JSON, OSM-/Widmungsindizien | **Nein** | Bestätigte GK oder Planungsfall, Nutzung, anwendbare Regelversion, Fachfreigabe |
| LW-03 | Sondernutzung / Objektschutz | TRVB 137 F/21, gesonderte Abschnitte | Nur vereinzelt OSM-Nutzungs-Tags | **Nein** | Brandlast, Nutzung, Objektgröße, Schutzkonzept, sachkundige Stelle |
| LW-04 | Wasserentnahmestellen: Typ, Zahl, Standort, Status | Autorisierter ODB-Export | **41** lokale Punkte, Status und Typ | **Bestandsbeschreibung ja** | Datenstand, tatsächliche Einsatzfähigkeit und fachliche Plausibilisierung |
| LW-05 | Verfügbare Durchflussmenge / Druck / Dauer / Vorrat | TRVB / VB-01/23 und technische Bemessung | In unserem Bestand nicht als vollständig verifiziert nachgewiesen | **Nein** | Feuerwehr / Wasserversorger / Betreiber: Messprotokolle, l/min, Druck, Dauer, Entnahmeregeln |
| LW-06 | Entfernung Gebäude–Quelle | Projekt-GIS und ggf. abweichender TRVB-Bezugsweg | Luftlinie vom OSM-Gebäudegrundriss zur ODB-Quelle | **Nur Luftlinie** | Belastbarer Bezugsort, Straßen-/Schlauchweg, Zugänglichkeit und Führung |
| LW-07 | Teilraten bei mehreren Entfernungsklassen | TRVB-Grundschutztabelle, JSON-Entwurf | Tabellenzeilen/125-m-, 250-m- und 500-m-Scheiben als Entwurf vorhanden | **Nein** | Fachprüfung der Entfernungsdefinition, tatsächliche Netzerreichbarkeit und Leistungsaddition |
| LW-08 | Ganzjährige Erreichbarkeit und Nutzbarkeit | K-GFPO § 31 Abs. 2 | OSM-Straßengeometrie, ODB-Status | **Nein** | Verkehrsrecht, Schneeräumung, Zufahrtsbreite, Winter-/Sperrzustand, örtliche Begehung |
| LW-09 | Vorhandene vs. geplante Bebauung | Rechtskräftige Flächenwidmung/Bebauungsplan, Bauakte | KAGIS-Widmung, OSM-Bestand | **Getrennt auswertbar, nicht rechtlich klassifiziert** | Baubewilligungen und geltende Planungsregeln |
| LW-10 | Offene BEV/OSM-Geometrien | BEV INSPIRE Adressen + OSM | 747 Innenpunkte, 16 Toleranzkandidaten, 13 Nahfälle, 12 ohne Treffer | **Geometrischer Prüfstatus** | CSV mit 25 Fällen zur Gemeinde; keine automatische Korrektur |
| LW-11 | Aussagekraft / Freigabe des Gemeindeberichts | GIS-Bestandsaufnahme, K-GFPO §31, TRVB/VB als Referenzen | Karten, Quelleninventur, ALS und Qualitätskennzahlen | **Bestandsbericht ja**, Versorgungsnachweis nein | Gegenzeichnung / fachliche Prüfung / Grenzen und Datenstand dokumentieren |

## 4. Reihenfolge der fachlichen Bearbeitung

1. **Rechts- und Quellenstand sichern:** RIS-Stand am Auswertungstag; OIB 2023 und die berechtigt vorhandenen Fassungen von TRVB 137 F/21 und VB-01/23 archivieren, Prüfsummen protokollieren.
2. **GK-Eingangsmerkmale klären:** für jeden Gebäudeklassenparameter bezeichnen, wer ihn verbindlich bereitstellen kann (Gemeinde/Bauakt/zulässige Registerdaten) und was bewusst unbekannt bleibt.
3. **Keine automatische Zuordnung:** `auto_assignment_enabled=false` beibehalten. OSM-Gebäudetyp, Widmung oder ALS-Höhe niemals als genügenden GK-Nachweis ausgeben.
4. **Löschwasserdatenqualität:** je ODB-Quelle Verfügbarkeit, Durchfluss, Druck, Dauer, Vorrat und Zugänglichkeit abfragen; nicht aus Koordinaten oder Status allein schließen.
5. **Validierung:** geprüfte Beispielgebäude und explizite Fachfreigabe, bevor aus der Regelwerkstruktur operative Kennzahlen oder Gebäudeklassenzuordnungen berechnet werden.

## 5. Konkrete Fragen an Gemeinde und Feuerwehr

- Welche **Gebäudeklasse** und welches **Fluchtniveau** sind bei Bestandsgebäuden aus Bauakten belastbar erhältlich?
- Wo liegen **rechtswirksame Bebauungspläne**, und welches Höchstmaß ist für Planungsfälle festgelegt?
- Wer kann die **25 BEV-/OSM-Prüffälle** plausibilisieren, ohne sie aus Karteneindruck willkürlich zu korrigieren?
- Gibt es zu den **41 ODB-Entnahmestellen** aktuelle Durchfluss-/Druck- und Erreichbarkeitsprotokolle?
- Nach welchem dokumentierten Fachregelwerk, Geltungsstand und konkreten **Bezugsweg** beurteilt die zuständige Stelle die benötigten Mengen?

## 6. Datenhaltung und Schutz

Die Anforderungsmatrix enthält nur öffentliche Methodik. Keine gemeindescharfen privaten Adresslisten oder ODB-Koordinaten in GitHub committen. Personen-/bauaktbezogene Angaben nur mit Berechtigung und Datenminimierung lokal verarbeiten.

**Verwandt:** [Quellenkatalog](../config/reference_documents.json) · [Regelwerksentwurf](../config/firewater_rulebook.json) · [offene Datenbestände](offene-datenbestaende-und-fragen.md) · [Skriptübersicht](skriptuebersicht.md)

## 7. Geplante Anfrage an Gemeinde Malta: tatsächliche und zulässige Gebäudeklassen

**Status: Anfrageentwurf; noch nicht versandt.** Ziel ist zunächst die Klärung von **Verfügbarkeit, Datenformat, Rechtsstand, Berechtigung und Ansprechpartner**, nicht die ungeprüfte Übermittlung sämtlicher personenbezogener Bauaktinformationen.

**Fragen:**

1. Liegen für bestehende Gebäude dokumentierte **tatsächliche Gebäudeklassen GK1–GK5** vor? Falls ja: für welche Objekte/Datenstände und mit welcher fachlichen bzw. rechtlichen Zuordnung?
2. Sind die Angaben **strukturiert** verfügbar (z. B. Tabelle mit Objektkennung/Adresse, GK, Stand und Quelle) oder nur in einzelnen Bauakten?
3. Sind bei älteren Gebäuden statt einer GK lediglich andere Daten vorhanden, insbesondere **Fluchtniveau, oberirdische Geschosse, Brutto-Grundfläche, Nutzung, Zahl der Nutzungseinheiten und Gebäudeart**?
4. Bestehen auf Grundstücks-/Planungsebene Informationen zur **höchsten zulässigen Bebauung** und dazu ein digital zugänglicher rechtswirksamer Bebauungsplan? Diese ist getrennt von der tatsächlichen GK zu führen.
5. Welche **Nutzungs- und Weitergaberechte** gelten für eine ausschließlich interne bzw. fachlich abgestimmte gemeindeweite GIS-Bestandsaufnahme? Wäre ein minimierter Datenauszug ohne Namen/Eigentümer möglich?
6. Wer ist die **zuständige Ansprechstelle** für eine fachliche Validierung und für Fragen zu historischen Bauakten?

**Mögliche Anlieferung, sofern ausdrücklich freigegeben:** Objektkennung, normalisierte Adresse, tatsächliche GK oder „nicht dokumentiert“, Datenstand, Quelltyp/Bauaktbezug, verifizierte GK-Merkmale und getrennt davon höchstzulässige planungsrechtliche Werte. Keine Eigentümerdaten anfordern. Aktuelle OSM-/BEV-Zuordnungen sind kein Nachweis amtlicher Gebäudeidentität.

Die Anfrage kann gemeinsam mit der separaten **Liste der 25 offenen BEV-/OSM-Geometriefälle** an die Gemeinde gerichtet werden; Rückmeldungen bleiben zwei getrennte Datenstränge. Bis zu einer fachlich verifizierten Antwort bleibt die GK-Einstufung im Projekt **unbekannt** (`auto_assignment_enabled=false`).
