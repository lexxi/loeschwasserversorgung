# Projektcheck auf jedem Rechner

Mit `scripts/check_project.py` lässt sich vor dem Weiterarbeiten prüfen, welche lokalen Voraussetzungen und Datenstände für die Löschwasserversorgungsanalyse vorhanden sind.

**Keine Zusatzpakete erforderlich.** Das Skript liest lediglich Dateien, JSON-Manifeste und lokale Git-Informationen aus. Es verbindet sich **nicht** mit dem Internet und verändert **keine** Dateien.

## Start (PowerShell)

```powershell
cd C:\pyprojects\loeschwasserversorgung
python scripts\check_project.py
```

Standardmäßig werden **Malta (20619)** und **Gmünd in Kärnten (20608)** geprüft. Für nur eine Gemeinde:

```powershell
python scripts\check_project.py --gemeinde 20619
```

Für mehrere beliebige Kärntner Gemeinden:

```powershell
python scripts\check_project.py --gemeinde 20619 --gemeinde 20608
```

Für die Auswertung durch andere Programme:

```powershell
python scripts\check_project.py --json
```

## Was geprüft wird

- Tatsächlich laufende Python-Version und Pfad zum Interpreter.
- Installierte Module `geopandas`, `osmnx`, `truststore` und optional `osmium`; **nur Vorhandensein**, keine Kompatibilitäts- oder Funktionstests.
- Git-Branch, Commit, ungesicherte Änderungen und Vergleich mit **bereits lokal gespeichertem** `origin/main`. Dieser Wert kann veraltet sein! `git fetch origin` ist nötig, wenn du den aktuellen Remote-Stand sicher wissen willst.
- Vorhandensein der Rohdaten: Statistik-Austria-Gemeinde-ZIP, KAGIS-Flächenwidmungs-ZIP, österreichische OSM-PBF.
- Pro Gemeinde: amtliche Grenz-/Widmungs-Geodaten, Manifest und Gemeinde-ID, OSM-Gebäude/Manifest, Gebäudeschnitt-Analyse, Klassifikation, Gemeindebericht, HTML-Überlappungsliste sowie Löschwasserquellen-/Manifest.
- Zum Schluss Vorschläge für **konkrete nächste Befehle**, abhängig von der lokalen Datenlage.

**Wichtig:** `[OK]` heißt nur, dass die erwarteten Dateien oder Pakete vorhanden sind und ein geprüftes Manifest lesbar und der richtigen Gemeinde zugeordnet ist. Der Check beweist **nicht**, dass die GeoJSONs gültige Geometrien enthalten, die Daten aktuell oder vollständig sind oder Löschwasserleistung und -eignung nachgewiesen wurden.

## Typischer Arbeitsplatzwechsel

```powershell
git status
git pull --ff-only origin main
python scripts\check_project.py
```

Wenn `python` bereits am Paketimport scheitert, ist meist `python -m pip install -r requirements.txt` nötig; für den OSM-PBF-Import zusätzlich `python -m pip install osmium`. Die vorgeschlagenen Aktionen werden nicht automatisch gestartet. Auf dem zweiten Rechner generierte `data/processed/`-Dateien werden **nicht über Git synchronisiert**, weil sie mit Absicht ignoriert werden.
