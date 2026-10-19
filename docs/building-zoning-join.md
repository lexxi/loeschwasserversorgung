# Gebäudebestand und Flächenwidmung verknüpfen

Skript: `scripts/join_buildings_zoning.py`. Es erzeugt **genau ein Ergebnisobjekt je OSM-Gebäude**.

## Aufruf (PowerShell)

```powershell
python scripts\join_buildings_zoning.py
```

Verwendete Standarddateien:
- `data/processed/current/osm/buildings_malta.geojson`
- `data/processed/current/malta_zoning.geojson`

## Ergebnisse

Verzeichnis `data/processed/current/building_zoning/`:
- `buildings_with_zoning.geojson` – Gebäude mit zugeordneten Widmungsattributen, Status und Trefferzahl.
- `zoning_candidates.csv` – alle Punkt-in-Polygon-Treffer, auch bei Mehrfachüberdeckung.
- `zoning_footprint_overlaps.csv` – echte Gebäude-/Widmungsschnittflächen in m² und Prozent der Gebäudegrundfläche; `point_match` zeigt, ob der Referenzpunkt ebenfalls innerhalb dieser Fläche liegt.
- `zoning_review.csv` – Gebäude ohne eindeutige Zuordnung.
- `summary.json` – Zählungen und Methodik.

Statuswerte:
- `unique`: Genau ein Treffer, dessen Widmung übernommen wird.
- `multiple_review`: Mehrere Treffer, **keine** automatisch ausgewählte Widmung.
- `overlap_review`: Kein Punkt-Treffer, aber positive Überdeckung zwischen Gebäudegrundfläche und Widmung. Keine automatische Widmungszuweisung.
- `unassigned`: Weder Punkt-Treffer noch positive Flächenüberdeckung.

Die primäre räumliche Zuordnung nutzt je Gebäudepolygon einen `representative_point()` und prüft `within`. Zusätzlich werden für **alle** Gebäude die tatsächlichen Schnittflächen mit Widmungspolygonen berechnet. Die Spalte `zoning_boundary_review` markiert weitere potenzielle Grenz-/Mehrfachfälle. Ein einzelner Punkt kann nicht beweisen, dass die gesamte Gebäudegrundfläche innerhalb derselben Widmungszone liegt. Die derzeitigen KAGIS-Daten können überlappende Widmungen enthalten; rechtliche Wirksamkeit bzw. Priorität ist nicht durch dieses Skript geklärt.

## Stand

Auf einem historischen Referenzbestand mit 1.678 Gebäuden und 537 **vorher reparierten** Widmungsflächen funktionierte die Zuordnung und erzeugte 1.678 eindeutige Gebäudeobjekte. **Die aktuelle Kombination mit 1.686 Gebäuden und 540 Widmungen ist noch lokal zu testen.** Keine Löschwasserbedarfsberechnung.

## Bekannter Grenzfall

OSM-Gebäude `way/405910040` (`building=residential`) hatte im Punkt-in-Polygon-Verfahren keinen Treffer, obwohl sich sein Polygon mit `OBJECTID 5227706` (Bauland – Dorfgebiet) überschneidet. Die neue Methode soll es deshalb als `overlap_review` ausweisen und die überdeckte Fläche berechnen. **Die genaue Überdeckungsquote ist noch nicht ermittelt**, sie darf nicht angenommen werden.

## Noch zu prüfen

- Erste Ausführung mit 1.686 aktuellen Gebäuden und 540 Widmungsflächen.
- Ob teilweise überlagerte Gebäude auch bei eindeutiger Punktzuordnung zusätzlich fachlich zu prüfen sind.
- Widmungsvorrang und Rechtswirksamkeit nur nach belegten Regeln bestimmen; keine willkürlichen Prozentgrenzen für automatische Zuweisung.
