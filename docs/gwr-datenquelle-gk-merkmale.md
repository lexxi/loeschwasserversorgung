# GWR/AGWR als Datenquelle für GK-Eingangsmerkmale

**Stand:** 27.10.2026 · **Pilotgemeinde:** Malta, GKZ 20619 · **Status:** Quellenrecherche / Klärung einer rechtmäßigen Datenbereitstellung, kein Datenabruf.

## Kernergebnis

Das **Gebäude- und Wohnungsregister (GWR)** von Statistik Austria wird über **Adress-GWR-Online (AGWR II)** von Gemeinden bzw. zuständigen Verwaltungsbehörden mitgeführt. Es enthält gebäudebezogene Strukturmerkmale. Das ist ein viel konkreterer Ansatz für die GK1–GK5-Vorbereitung als die Annahme, die Gemeinde müsse bereits eine Liste fertiger OIB-Gebäudeklassen besitzen.

**Wichtig:** Das GWR verwendet ebenfalls Begriffe wie „Gebäudekategorie“ und „Gebäudeeigenschaft“. Diese sind **nicht automatisch** identisch mit OIB-GK1–GK5. Auch das GWR-Feld „Gebäudehöhe“ ist **nicht** das OIB-Fluchtniveau; die Anzahl oberirdischer Geschosse und Flächenwerte sind vor einer fachlichen Übernahme auf Definitionskompatibilität und Aktualität zu prüfen.

## Belegter Merkmalsbestand

| Merkmal / Fachfrage | Registerhinweis | Bedeutung für unsere GIS-Auswertung |
| --- | --- | --- |
| Oberirdische Geschosse | GWR-Merkmalskatalog: `ANZGESCHO` | Für GK wichtige Eingangsinformation, dennoch Definition/Bestandsstand prüfen |
| Geschossbezogene Brutto-Grundfläche | AGWR-Bedienungsanleitung und GWR-Merkmalskatalog | Potenziell Grundlage für Gesamt-BGF; keine Gleichsetzung mit OSM-Grundriss |
| Geschosshöhen / Gebäudehöhe | GWR-Gesetz Anlage 1 Abschnitt D, GWR-Merkmalskatalog | Plausibilitätsprüfung zu ALS; **kein** automatisches Fluchtniveau |
| Nutzungseinheiten, Nutzungsart, Nettogrundflächen | GWR-Gesetz Anlage 1 Abschnitte E und G | Ansatz für Wohn- und Betriebseinheiten; notwendige Details je OIB-Variante prüfen |
| Gebäudeidentifikatoren/Adresse | AGWR/BEV Adresscode, Objektnummer, Gebäudeadresse | Möglicher Schlüssel-/Adressabgleich; amtlicher GWR-Schlüssel ist nicht automatisch eine OSM-ID |
| Gebäudestatus | AGWR-Verwaltungsbericht | Aktive, ehemalige und nie existierende Gebäude trennen |

**Fachlicher Vorbehalt:** Die rechtlich möglichen Registerfelder beweisen noch nicht, dass sie für *jedes* Bestandsgebäude befüllt, vollständig oder auf dem aktuellen Stand sind.

## Konkreter Weg über die Gemeinde

Statistik Austria dokumentiert in der Anleitung **„Adress-GWR-Online – Verwaltungsberichte und Statistiken“ (August 2026)** den **„Verwaltungsbericht Gebäude“**:

- Die Verwaltungsberichte sind **Einzeldatenlisten**, im Unterschied zu aggregierten Statistiken.
- Der Gebäudeverwaltungsbericht enthält die gemeldeten Bestandsgebäude einschließlich früherer Status (z. B. Abbruch); **ein Gebäude kann in mehreren Zeilen vorkommen, je eine Zeile pro Geschoss**. Bei unzugeordneten Flächen können zusätzliche Zeilen vorkommen.
- Ein **XLS-Bericht** wird in der Dokumentation beispielhaft gezeigt. Das genaue Exportformat und die erlaubten Spalten im konkreten Gemeindezugang müssen vorab erfragt werden.
- Verwaltungsberichte sind gemäß Anleitung **30 Tage** über AGWR II abrufbar, danach werden sie im System automatisch gelöscht. Das beschreibt die Systembereitstellung, **nicht** eine Berechtigung zu beliebiger dauerhafter Speicherung oder Weitergabe.

**Priorisierte Anfrage an Malta:**

1. Kann die zuständige Stelle im AGWR II für GKZ **20619** den **Verwaltungsbericht Gebäude** hinsichtlich **verfügbarer Spalten, Befüllungsgrad und rechtlicher Nutzungsmöglichkeiten** prüfen?
2. Sind `ANZGESCHO`, geschossbezogene BGF, Geschosshöhen, Gebäudehöhe, Gebäudestatus und Gebäudekennung / Adresscode für den Bestand ausreichend vorhanden? Unbekannte Werte bitte als solche kennzeichnen.
3. Sind Nutzungseinheiten und deren Nutzungen/Flächen im Rahmen eines separaten, datensparsamen Berichts verfügbar?
4. Dürfte die Gemeinde einen **zweckgebundenen und datensparsamen, um persönliche Angaben reduzierten Auszug** für die interne/fachlich abgestimmte Löschwasser-Bestandsaufnahme bereitstellen? Welche rechtliche Grundlage und Bedingungen wären hierfür erforderlich? Ohne Freigabe kein Datenaustausch.
5. Ist eine **aggregierte Vollständigkeitsstatistik** ohne gebäudescharfe Daten als erster Schritt einfacher und zulässig?
6. Wer könnte zusätzlich fehlendes **OIB-Fluchtniveau**, tatsächliche Bauart, Feuerwehrzugänglichkeit und Sondernutzungen fachlich prüfen? Diese Angaben sind durch GWR nicht durchgehend belegt.

## Weitere öffentliche Datenquellen

- **BEV Adressregister:** Für offizielle Adress- und Gebäudekoordinaten sowie Gebäude-/Adressschlüssel geeignet, aber **kein Ersatz für Gebäudestrukturdaten des GWR**.
- **Statistik Austria offene Gemeindeaggregate zu Gebäuden/Wohnungen:** Nützlich für **Plausibilitätskontrollen und Bestandsabgleich**, aber nicht zur GK-Zuordnung einzelner OSM-Polygone.
- **KAGIS / Kärntner Flächenwidmung:** Rechts-/Planungskontext; aus Flächenwidmung allein werden weder tatsächlich errichtete Geschosse noch OIB-GK bestimmt.
- **BEV ALS:** Gut für die objekträumliche Höhenschätzung und Qualitätskontrollen; kein Fluchtniveau.

Ein öffentlich zugänglicher, amtlicher, gebäudescharfer Datensatz mit den vollständigen für eine OIB-GK-Bewertung erforderlichen Kärntner Merkmalen wurde in dieser Recherche **nicht verifiziert**.

## Quellen (öffentlich; aufgerufen 27.10.2026)

- [Statistik Austria: Zugang und Zugriffsberechtigungen AGWR](https://www.statistik.at/datenbanken/adress-gebaeude-und-wohnungsregister/adress-gebaeude-und-wohnungsregister/adress-gwr-online-agwr/zugang-und-technische-informationen)
- [Statistik Austria: AGWR Dokumentation / Handbücher](https://www.statistik.at/datenbanken/adress-gebaeude-und-wohnungsregister/adress-gebaeude-und-wohnungsregister/adress-gwr-online-agwr/dokumentation)
- [Statistik Austria: AGWR Verwaltungsberichte und Statistiken, August 2026](https://www.statistik.at/fileadmin/pages/489/AGWR_Online_VerwaltungsberichteStatistiken_2026_08.pdf), insbesondere S. 4 und 8
- [Statistik Austria: AGWR Merkmalskatalog, Mai 2025](https://www.statistik.at/fileadmin/pages/489/AGWR_Merkmalskatalog2025_09.pdf), insbesondere Abschnitt 3.1
- [GWR-Gesetz, konsolidiert: Anlage 1 / Gebäudemerkmale](https://ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=20003223)
- [Statistik Austria: GWR-Bestandsdaten / Gemeindeaggregate](https://www.statistik.at/datenbanken/adress-gebaeude-und-wohnungsregister/adress-gebaeude-und-wohnungsregister/daten-des-gebaeude-und-wohnungsregisters/bestandsdaten)
- [BEV: Adressregister](https://www.bev.gv.at/Themen/Adressregister.html)

## Projektintegration (erst nach berechtigtem Datenerhalt)

1. Privaten GWR-Auszug nur **lokal** unter `data/raw/` ablegen, keinesfalls auf GitHub hochladen.
2. Vor einer Importfunktion zuerst Spalten/Kodierungen/Schlüssel, Exportdatum, Schutzbedarf und Zuordnung zum BEV-Datenmodell prüfen.
3. Eine Rohdateneinheit kann **mehrere Zeilen pro Gebäude** umfassen; nicht naiv als ein Gebäude pro Excel-Zeile behandeln.
4. Merkmale nur mit Herkunft, Datenstand, Plausibilitätsstatus und fehlenden Werten übernehmen.
5. OSM↔BEV↔GWR-Zuordnung nachvollziehbar kennzeichnen. Die 16 Toleranzfälle und 25 offenen Geometrieprüffälle bleiben unbestätigt.
6. `config/firewater_rulebook.json`: `auto_assignment_enabled=false` bleibt unverändert bis zur vollständigen fachlichen Prüfung.
