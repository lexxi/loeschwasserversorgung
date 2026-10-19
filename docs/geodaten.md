# Geodaten – Beschaffung und Prüfstatus

Stand der Quellenrecherche: **19.10.2026**. Hier sind bislang **Quellen geprüft**, noch keine neuen Geodatensätze heruntergeladen oder geometrisch validiert.

## Gemeindegrenze Malta

- Anbieter: Statistik Austria
- Datensatz: Gemeinden 2026, Gebietsstand 01.01.2026
- Metadaten: https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_GEM_1
- Download: https://www.statistik.gv.at/gs-open/GEODATA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=GEODATA:STATISTIK_AUSTRIA_GEM_20260101&outputFormat=SHAPE-ZIP&format_options=CHARSET:UTF-8
- Bezugssystem: EPSG:31287; Lizenz: CC BY 4.0
- Geplant: Gemeindepolygon per amtlichem Gemeindeschlüssel und Name auswählen, Topologie und Grenzen prüfen.

## Flächenwidmung

- Anbieter: Land Kärnten/KAGIS
- Katalog: https://www.data.gv.at/katalog/dataset/cef1c710-3564-4c4a-adce-39896ba4bed8
- GeoPackage-ZIP: https://gis.ktn.gv.at/OGD/Geographie_Planung/flawi_ktn_gpkg.zip
- Bezugssystem: EPSG:31258; Lizenz: CC BY 4.0
- Katalog zuletzt aktualisiert: 20.06.2026
- **Warnung:** Katalogdatum ist kein Nachweis des Rechtsstands für Malta. Insbesondere sind Widmungsänderungen und ihre rechtswirksamen Kundmachungen abzugleichen.
- Geplant: Schema/Layers prüfen, Malta mit amtlicher Gemeindegrenze clippen, nach EPSG:31287 transformieren und Widmungsschlüssel dokumentieren.

## Bebauungspläne

- Gemeindeseite: https://malta.gv.at/verwaltung
- Textlicher Bebauungsplan / Erläuterungen: https://malta.gv.at/fileadmin/malta/05-Verwaltung/Textlicher_Bebauungsplan.pdf
- Änderung aus 2016: https://malta.gv.at/fileadmin/malta/05-Verwaltung/Bebauungsplan_AEnderung.pdf
- Verordnungen und Änderungen zusätzlich im RIS Gemeinderecht recherchieren.
- Allgemeiner textlicher Bebauungsplan und Teilbebauungspläne sind getrennt zu erfassen. Die Rechtswirksamkeit der aktuell gültigen Fassung ist **noch nicht abschließend bestätigt**.

## Raumordnungsänderungen, die geprüft werden müssen

- RIS: https://ris.bka.gv.at/Dokumente/Gemeinderecht/GEMRE_KA_20619_031_3_2025_VO/GEMRE_KA_20619_031_3_2025_VO.html – Änderung beschlossen 18.12.2025, genehmigt 26.02.2026.
- RIS: https://ris.bka.gv.at/Dokumente/Gemeinderecht/GEMRE_KA_20619_031_3_2026_1/GEMRE_KA_20619_031_3_2026_1.html – Entwurf mit Auflage 17.09.–22.10.2026. **Nicht als geltende Widmung behandeln**, solange entsprechende Rechtswirksamkeit nicht nachgewiesen ist.

## Import-/Validierungsregeln

1. Für jeden Download: Original-URL, Abrufdatum, Lizenz, SHA-256 und ggf. Gebietsstand aufzeichnen.
2. Ursprungs-CRS nicht erraten; erst danach in das Analyse-CRS EPSG:31287 transformieren.
3. Flächen auf gültige Geometrien, Mehrfachflächen, Grenzüberstände und leere Ergebnisse prüfen.
4. Amtliche Widmung nicht mit tatsächlicher Gebäudenutzung gleichsetzen.
5. Eingangsdaten und generierte GIS-Dateien bleiben zunächst außerhalb des öffentlichen Repositorys.
6. Ein späterer automatisierter Import muss Reproduzierbarkeit und Quellenattribution sicherstellen.


## Validierter Änderungsvergleich: Malta 2026 (Recherche vom 19.10.2026)

Der lokal durchgeführte Vergleich des bisherigen GeoPackage-Bestands mit dem neu geladenen KAGIS-Datensatz lieferte:

- Alt: 537 Widmungsobjekte / 221 Baulandobjekte.
- Neu: 540 Widmungsobjekte / 224 Baulandobjekte.
- 537 räumlich zugeordnete Altobjekte ohne Änderung der verglichenen Fachattribute bzw. Geometrien innerhalb der eingestellten Toleranzen.
- Drei zusätzliche Polygonobjekte (nicht zwingend drei unabhängige Widmungsverfahren):
  - OBJECTID 5227970, Bauland – Dorfgebiet: 299,61 m².
  - OBJECTID 5227971, Bauland – Dorfgebiet: 454,80 m².
  - OBJECTID 5227971, Bauland – Dorfgebiet: 83,60 m².
- Zusammen 838,01 m². Alle drei liegen räumlich innerhalb des alten Grünlandpolygons OBJECTID 5126985 („Für die Land- und Forstwirtschaft bestimmte Fläche, Ödland“).

**Amtliche Zuordnung (sehr hohe Plausibilität, QGIS-Lagevergleich noch offen):**

Verordnung des Gemeinderats vom 18.12.2025, Zahl 031/3/2025/VO, genehmigt vom Land Kärnten am 26.02.2026, Zahl 07-RO-71-6460/2026-5:

- Änderung **19/2024**: Grundstück .9 (109 m²) und Teilfläche 480 (191 m²), KG Malta 73008: insgesamt **300 m²**, Grünland → Bauland Dorfgebiet.
- Änderung **20/2024**: Grundstück .8/3 (33 m²), Teilfläche 474/2 (465 m²), Teilfläche 478/2 (41 m²), KG Malta 73008: insgesamt **539 m²**, Grünland → Bauland Dorfgebiet.
- 300 m² ↔ GIS 299,61 m²; 539 m² ↔ GIS 454,80 + 83,60 = 538,40 m². Summe amtlich 839 m² gegenüber GIS 838,01 m² (Differenz 0,99 m²).

Quellen:
- [RIS: Verordnung 031/3/2025/VO](https://ris.bka.gv.at/Dokumente/Gemeinderecht/GEMRE_KA_20619_031_3_2025_VO/GEMRE_KA_20619_031_3_2025_VO.html).
- [Gemeinde Malta: Lagepläne Änderungen 19/2024 und 20/2024 (PDF)](https://malta.gv.at/fileadmin/malta/user_upload/Kundmachung_Umwimdung_19_2024-20_2024_mit_Lageplaenen.pdf).

**Offene Prüfpunkte:** exakter geometrischer Abgleich der drei neuen GIS-Polygone mit den planlichen Anlagen; Kundmachungsdatum des Inkrafttretens; Interpretation der weiterhin überlagernden alten Grünlandgeometrie. Eine simple Flächensumme der GIS-Polygone ist nicht mit einer flächenbereinigten Widmungsbilanz gleichzusetzen.

Der Änderungsentwurf **02/2026** (Schutzstreifen als Immissionsschutz, Auflage 17.09.–22.10.2026) betrifft ein anderes Verfahren und ist nicht mit den oben genannten drei neuen Dorfgebietsobjekten zu verwechseln.
