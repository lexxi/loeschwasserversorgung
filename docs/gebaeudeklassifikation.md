# Vorläufige Gebäudeklassifikation

**Status:** Technische Vor-Klassifikation anhand der OSM-Gebäudetags; **kein Nachweis der tatsächlichen Gebäudenutzung und kein Löschwasserbedarf**.

Skript: `scripts/classify_buildings.py`. Regeln: `config/building_classification.json`.

## Klassen

- `residential_candidate`: OSM-`building`-Tag ist explizit als Wohngebäudetyp konfiguriert (z. B. `house`, `detached`, `residential`, `apartments`).
- `non_residential_tag`: OSM-`building`-Tag weist auf einen Nicht-Wohngebäudetyp hin (z. B. `garage`, `retail`, `ossuary`). Das bedeutet nicht, dass dort kein objektspezifischer Löschwasserbedarf besteht.
- `use_unknown`: OSM-`building=yes`, `farm`, `hut`, `cabin` und alle nicht explizit zugeordneten Werte. Diese Objekte werden **nicht verworfen**.

Hausnummer, `amenity`, `tourism` und `shop` werden als zusätzliche Merkmale ausgewiesen, **ändern die Klasse aber nicht automatisch**. Die Klassifikation kann nach fachlicher Prüfung erweitert werden; dafür müssen die Regeln und Änderungen versioniert werden.

## Ausführung

```powershell
python scripts\classify_buildings.py
```

Voraussetzung: erfolgreiches `scripts/join_buildings_zoning.py`.

## Ausgabe

- `data/processed/current/building_classification/buildings_classified.geojson`
- `data/processed/current/building_classification/summary.json`

Der Datensatz enthält die bereits ermittelten Widmungszuordnungen und zusätzliche Felder für die Gebäudeklasse. Die Zahl der Gebäude darf sich durch diese Stufe nicht verändern.

## Methodische Grenzen

OSM kann unvollständige oder falsche Tags enthalten; ein Gebäude mit Hausnummer ist nicht automatisch ein Wohngebäude. Die räumliche Lage in `Bauland – Dorfgebiet` begründet ebenfalls keine Wohnnutzung. Für Siedlungsanalysen muss explizit angegeben werden, welche Klassen einbezogen werden. Alle Berechnungen zur Löschwasserversorgung bleiben davon getrennt.

## Abgrenzung zur baurechtlichen Gebäudeklasse und nächste Arbeitspakete

Diese OSM-Nutzungshinweise (`residential_candidate`, `non_residential_tag`, `use_unknown`) sind **keine** baurechtlichen Gebäudeklassen GK1–GK5 und lösen keine automatische Löschwasserbedarfszuordnung aus. Die **Regeldefinition** nach OIB/Kärntner Bautechnikrecht und TRVB ist ein eigenes Arbeitspaket; die **nachweisbare tatsächliche GK-Zuordnung jedes einzelnen Gebäudes** ein zweites. Auch die höchste planungsrechtlich zulässige GK für den Grundschutz ist separat von der tatsächlichen GK zu erfassen. Alle Gebäude bleiben enthalten, selbst wenn ihre GK unbekannt ist.

Siehe [Gebäudeklassen und Löschwasserbedarf](gebaeudeklassen-und-loeschwasserbedarf.md) mit Primärquellen, Vorgehensweise und Datenlücken.
