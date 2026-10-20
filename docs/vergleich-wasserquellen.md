# Abgleich OSM ↔ Objektdatenbank: Löschwasserquellen

> **Projektentscheidung (20.10.2026):** Die vier für Malta (GKZ 20619) importierten OSM-Hydranten bleiben ausschließlich als lokaler historischer Vergleichsbestand erhalten. Sie werden **nicht mehr dargestellt, nicht mit ODB vereinigt und nicht in die weitere Löschwasserversorgungsanalyse oder Berechnungen einbezogen**. Der ODB-Bestand ist die maßgebliche Arbeitsdatenquelle. Die nachfolgend beschriebenen OSM-Vergleichswerkzeuge dienen nur der Nachvollziehbarkeit früherer Untersuchungen und sind nicht Bestandteil der aktiven Analysepipeline.

Der Abgleich ist **lokal**, read-only gegenüber den beiden Originalimporten und verwendet weder Web-API noch API-Schlüssel.

## Voraussetzungen

Vorhandene lokale Importergebnisse für die GKZ, z. B.:

- `data/processed/20619/water_sources/water_sources.geojson` (OSM)
- `data/processed/20619/odb_water_sources/odb_water_sources.geojson` (ODB)

Aufruf:

```powershell
git pull --ff-only origin main
python scripts\compare_water_sources.py --gemeinde 20619
```

Ergebnis unter `data/processed/20619/water_sources_comparison/`:

- `osm_odb_nearest.csv`: für **jeden OSM-Eintrag** nächster beliebiger ODB-Punkt, dessen Kategorie und Status sowie nächster ODB-Punkt mit kompatibler Objektklasse (falls vorhanden)
- `comparison_summary.json`: aggregierte Zählwerte und Einschränkungen

Die Entfernungen werden über `EPSG:31287` in Metern berechnet. Die Ausgabe gruppiert Entfernungen in 0–10m, 10–30m, 30–100m und über 100m. Das sind **Prüfintervalle, keine festen fachlichen Dublettengrenzen**.

**Typverknüpfung:** OSM-Hydrant ↔ ODB-Überflur-/Unterflurhydrant; Saugstelle ↔ Saugstelle; Löschwasserteich ↔ Löschwasserteich. OSM-Löschwasserbehälter hat keine direkte Entsprechung in den fünf derzeit bekannten ODB-Kategorien. Bach mit Stau ↔ Saugstelle wird **nicht** automatisch gleichgesetzt, sondern als fachlich zu prüfen markiert.

**Einschränkungen:**

- Die OSM-Importdaten können repräsentative Punkte für Wege/Flächen enthalten. Diese sind keine exakten Saugstellen-Positionen.
- Ein naher Punkt kann eine weitere eigenständige Einrichtung sein; abweichende Standorte können dennoch dieselbe Einrichtung bezeichnen.
- Der Vergleich ist je OSM-Eintrag unabhängig; dass derselbe ODB-Eintrag mehrfach als nächster Nachbar erscheint, ist möglich.
- Die CSV enthält örtliche Objektkennungen; ausschließlich lokal speichern, nicht in öffentliche Repositories laden.
- Erst nach fachlicher Sichtung manuell entscheiden: Duplikat, wahrscheinlich eigenständig oder offen.
