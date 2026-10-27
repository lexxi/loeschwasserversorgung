# Rechtsgrundlagen und fachliche Regelwerke

**Bearbeitungsstatus: Recherche und fachliche Prüfung offen.**

Eine gesetzliche Verpflichtung zur Löschwasserversorgung ist **nicht** gleichbedeutend mit einem pauschalen Durchflusswert für jedes Gebäude. Gesetz, allfällige Verordnungen/Bescheide, technische Regeln und Annahmen der Software sind getrennt zu behandeln.

## Kärnten

- **Kärntner Gefahrenpolizei- und Feuerpolizeiordnung 2000 (K-GFPO)**, insbesondere § 31 (Löschwasser): aktuelle Fassung und Anwendbarkeit im [RIS](https://www.ris.bka.gv.at/) prüfen.
- Bei der Auswertung zusätzlich einschlägige Bestimmungen der Bau- und Raumordnung sowie ortsbezogene rechtswirksame Festlegungen prüfen.

## Österreichische technische Regelwerke

- **ÖBFV-Richtlinie VB-01/23 – Die Löschwasserversorgung** (Ausgabe 2023): Anwendungsbereich, Bemessung, Entnahmestellen und Nachweise anhand des Originaldokuments prüfen.
- **TRVB 137/21 F – Löschwasserbedarf** (Ausgabe 2021): Anforderungen zu Grund- und Objektschutz anhand des Originaldokuments prüfen.

Technische Richtlinien sind nicht allein aufgrund ihrer Existenz automatisch allgemein verbindliches Gesetz. Eine rechtliche Verbindlichkeit im konkreten Fall muss festgestellt werden.

## Vorläufige Festlegungen im Projekt

- Bisherige Clusterparameter (100 m, 10 Punkte, 60 m Puffer, 5 Gebäude/ha) sind **Analyseparameter**, keine Rechtsnorm.
- `800_lpm` wird bis zur fachlichen Herleitung **nicht** als verbindlicher Löschwasserbedarf ausgewiesen.
- Tatsächliche Leistungsfähigkeit der Wasserversorgung kann nicht aus OSM-Gebäudedaten abgeleitet werden.
- Für jeden normativen Schwellenwert später dokumentieren: Quelle, Ausgabe/Fassung, Abschnitt/Tabelle, Geltungsbereich, Berechnungsannahme, Prüfstatus.

## Offene Punkte

1. Aktuellen konsolidierten Rechtsstand im RIS überprüfen, einschließlich einschlägiger Verweisnormen.
2. Originaltexte von VB-01/23 und TRVB 137/21 F beschaffen und die Anwendbarkeit bestätigen.
3. Zuständige fachliche Stelle für Interpretation und Freigabe der Bemessungsmethodik einbeziehen.
4. Rechtsstand und Prüfdatum versioniert dokumentieren.

## Gebäudeklassen / Löschwasserbedarf: verifizierte Referenzquellen (27.10.2026)

- [Kärntner Bautechnikverordnung 2024 (RIS)](https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=LrK&Gesetzesnummer=20000961): § 1 verweist unter anderem auf **OIB-Richtlinie 2** und die **OIB-Begriffsbestimmungen**, jeweils Mai 2023. Landesrechtliche Abweichungen und Übergangsfragen gesondert prüfen.
- [OIB-Begriffsbestimmungen, Mai 2023 (Original-PDF)](https://www.oib.or.at/sites/default/files/oib-rl_begriffsbestimmungen_ausgabe_mai_2023.pdf): GK1–GK5 und deren Definitionsmerkmale.
- [OIB-Richtlinie 2, Mai 2023 (Original-PDF)](https://www.oib.or.at/sites/default/files/oib-rl_2_ausgabe_mai_2023.pdf) und [Erläuterungen (Original-PDF)](https://www.oib.or.at/sites/default/files/erlaeuterungen_oib-rl_2_ausgabe_mai_2023.pdf): Brandschutz, Sonderregeln und grafische Einteilungshilfen.
- [TRVB 137 F/21 (ÖBFV)](https://www.bundesfeuerwehrverband.at/produkt/trvb-137-21-f-loeschwasserbedarf/) und [veröffentlichter Originaltext (PDF)](https://www.noe122.at/vorbeugender-brandschutz/gr%C3%BCner-ordner/4-12-trvb-137-f-21.pdf): Grundschutz Abschnitt 4, besondere Nutzungen Abschnitt 5, Objektschutz Abschnitt 6. Insbesondere ist im **Grundschutz** nach Abschnitt 4.1 die **höchste zulässige GK/Bebauungsart** maßgeblich; tatsächliche Bauwerks-GK und Planungszulässigkeit daher **nicht verwechseln**. Die TRVB spricht bei Grundschutz von Entfernungen entlang der verkehrstechnisch erschlossenen Grundstücksgrenze, nicht von unserer ODB-Luftlinie zur Gebäudegrundfläche.
- [ÖBFV VB-01/23 (offizielle Verlagsseite)](https://www.bundesfeuerwehrverband.at/produkt/vb-01-23-rl-die-loeschwasserversorgung/): Ausgabe 15.10.2023; Anforderungen an Versorgung und Entnahmestellen, vollständige Prüfung noch offen.

Die zugehörigen Arbeitspakete **Regeldefinition** und **Zuordnung aller konkreten Gebäude** sind in [Gebäudeklassen und Löschwasserbedarf](gebaeudeklassen-und-loeschwasserbedarf.md) dokumentiert. Die TRVB ist ein technisches Regelwerk; ob und wie sie in einem konkreten Fall maßgeblich ist, ist fachlich/rechtlich zu klären. Die Originalquellen bleiben im öffentlichen Repository ausschließlich verlinkt. Für die **lokale Offline-Verwendung** gibt es nun den Quellenkatalog `config/reference_documents.json` und das lokale PDF-Archiv `reports/references/` (siehe `docs/skriptuebersicht.md`). Berechtigt bezogene Originale werden dort mit SHA-256-Prüfsummen archiviert und nicht nach GitHub hochgeladen.
