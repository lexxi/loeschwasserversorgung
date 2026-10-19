# Löschwasserversorgung – Analysewerkzeug (Referenzgemeinde Malta)

Analyseprojekt zur räumlichen Untersuchung der Siedlungsstruktur und zur **vorbereitenden** Bewertung der Löschwasserversorgung in Kärntner Gemeinden. Malta (20619) dient als bisherige Referenzgemeinde.

> **Status: Neuaufbau / fachliche Validierung ausständig.** Die vorhandenen Python-Prototypen und deren Grenzwerte sind noch nicht als gültige Löschwasserbedarfsberechnung freigegeben. Ergebnisse sind weder eine behördliche Feststellung noch ein Nachweis einer ausreichenden Löschwasserversorgung.

## Ziele

- Amtliche Gemeindegrenze, Flächenwidmung und rechtswirksame Bebauungspläne mit dokumentiertem Datenstand erfassen.
- OpenStreetMap-Gebäude nachvollziehbar klassifizieren und räumliche Siedlungsanalysen durchführen.
- Rechtliche Anforderungen, technische Richtwerte und algorithmische Heuristiken klar trennen.
- Erst nach fachlicher Validierung einen Löschwasserbedarf ableiten und später mit gesicherten Versorgungsdaten abgleichen.

## Bisheriger Prototyp (noch nicht veröffentlicht)

1. OSM-GeoJSON aus Overpass importieren und Wohngebäude-Kandidaten filtern.
2. Gebäudedichte in einem konfigurierbaren Radius ermitteln.
3. Gebäude mit DBSCAN clustern und Siedlungsflächen ableiten.

Die bisherige Kennzeichnung `800_lpm` basiert auf **nicht validierten Parametern** (Gebäudeanzahl/Dichte); sie darf nicht als normative Forderung interpretiert werden.

## Repository-Struktur

- `docs/rechtsgrundlagen.md`: Rechtsquellen, technische Regelwerke und offene Prüfaufgaben.
- `data/sources.json`: Datenquellenregister für die geplante Erhebung.
- `.gitignore`: Ausschluss lokaler Umgebungen und generierter GIS-Daten.
- `scripts/import_geodata.py`: Beschaffung und Zuschnitt amtlicher Geodaten.
- `docs/import.md`: Ausführungsanleitung.
- `scripts/import_osm.py`: OSM-Gebäudeimport aus lokalem Export oder via Overpass.
- `docs/osm-import.md`: Anleitung und Datenherkunft zum OSM-Import.
- `docs/datenqualitaet-methodik.md`: Messergebnisse, Unsicherheiten und Prüfplan zur geometrischen Widmungszuordnung.
- `scripts/classify_buildings.py` und `config/building_classification.json`: Konservative Klassifikation der OSM-Gebäudetags.
- `docs/gebaeudeklassifikation.md`: Regeln und Grenzen der Gebäudezuordnung.
- `scripts/run_municipality.py`: Gemeindebezogener Gesamtlauf von Geodatenimport bis Gemeindebericht.
- `docs/gemeinde-pipeline.md`: Anleitung für weitere Kärntner Gemeinden und Regressionstest.
- `scripts/generate_municipality_report.py`: Generiert einen Gemeindereport (Markdown und JSON) aus den vorhandenen Auswertungen.
- `docs/gemeindebericht.md`: Aufbau, Ausführung und Datenanforderungen des Gemeindeberichts.

Ein **erster, noch nicht vollständig getesteter GIS-Importer** ist unter `scripts/import_geodata.py` verfügbar; Anleitung unter [GIS-Import](docs/import.md). Die ursprünglichen Analyseprototypen, automatisierte Tests und eine fachlich validierte Löschwasserberechnung sind noch nicht veröffentlicht.

## Git und lokale Entwicklungsumgebung (Windows)

Standardverzeichnis für lokale Projekte: `C:\pyprojects`. Die folgenden Befehle sind für **CMD (Eingabeaufforderung)** ausgelegt. In PowerShell funktioniert die Git-Bedienung gleich, aber die Aktivierung der virtuellen Python-Umgebung unterscheidet sich.

### Git auf einem neuen Rechner installieren (einmalig)

```powershell
winget install --id Git.Git -e --source winget
```

**Danach das Terminal schließen und neu öffnen**, damit `git` im PATH verfügbar ist.

```bat
git --version
```

### Repository zum ersten Mal klonen

Nur verwenden, wenn das Projektverzeichnis **noch nicht existiert**:

```bat
mkdir C:\pyprojects
cd /d C:\pyprojects
git clone https://github.com/lexxi/loeschwasserversorgung_9854_malta.git
cd loeschwasserversorgung_9854_malta
git status
```

Falls `C:\pyprojects` bereits existiert, ist `mkdir` nicht erforderlich. Ein vorhandenes lokales Projektverzeichnis nicht durch erneutes Klonen überschreiben.

### Bestehendes Repository aktualisieren

```bat
cd /d C:\pyprojects\loeschwasserversorgung_9854_malta
git status
git pull --ff-only origin main
```

Bei lokalen Änderungen oder Konflikten nicht blind überschreiben: zuerst `git status` prüfen und Änderungen sichern.

### Änderungen prüfen und veröffentlichen

Nur beabsichtigte **Code- und Dokumentationsdateien** aufnehmen; keine ungeprüften GIS-Rohdaten, Ausgabedateien, Zugangsdaten oder die virtuelle Umgebung.

```bat
git status
git diff
git add README.md
git diff --cached
git commit -m "docs: update README"
git push origin main
```

`git add README.md` ist ein Beispiel. Für andere Änderungen gezielt die entsprechenden Dateipfade angeben. Nicht unkontrolliert `git add .` verwenden.

### Python-Umgebung (CMD)

```bat
cd /d C:\pyprojects\loeschwasserversorgung_9854_malta
py -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Unter **PowerShell** stattdessen die Umgebung mit `.\.venv\Scripts\Activate.ps1` aktivieren. Die Umgebung `.venv` bleibt lokal und gehört nicht ins Git-Repository.

## Daten und Veröffentlichung

OSM-Daten stehen unter der Open Database License (ODbL); amtliche GIS-Daten haben jeweils eigene Nutzungsbedingungen. **Vor einer Veröffentlichung von Eingangs- oder abgeleiteten Daten sind Quelle, Lizenz und Attribution zu prüfen.** Interne Wasserleitungs-, Hydranten- und Kapazitätsdaten gehören nicht ohne gesonderte Freigabe in ein öffentliches Repository.

## Rechtliche Hinweise

Siehe [Rechtsgrundlagen](docs/rechtsgrundlagen.md). Maßgeblich sind die jeweils geltenden Vorschriften und die fachliche Beurteilung durch die zuständigen Stellen.

## Lizenz

Noch festzulegen. Bis zur ausdrücklichen Lizenzvergabe sind die Repository-Inhalte nicht automatisch Open Source.
