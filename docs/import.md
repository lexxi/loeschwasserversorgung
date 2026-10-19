# Amtlicher GIS-Import

Der Import ist eine **Vorbereitung der geografischen Datengrundlage**, keine Löschwasserbedarfsermittlung.

## Umgebung

Python 3.11+ und GeoPandas/Fiona:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Import

```powershell
python scripts/import_geodata.py --download
```

Wenn `flawi_ktn_gpkg.gpkg` bereits lokal vorliegt, kopiere sie nach `data/raw/` und nutze sie **ohne erneuten Download**. Die Gemeindegrenze wird vom amtlichen WFS geladen:

```powershell
python scripts/import_geodata.py --download --zoning-gpkg data/raw/flawi_ktn_gpkg.gpkg --repair-invalid
```

`--repair-invalid` muss ausdrücklich gesetzt werden, wenn ungültige Widmungspolygone gefunden werden. Die Anzahl reparierter Polygone steht im Manifest. Die Reparatur ist anschließend in QGIS zu kontrollieren.

Alternativ die ZIP-Dateien selbst von den Quellen laden und dann:

```powershell
python scripts/import_geodata.py --boundary-zip data/raw/gemeinden_2026.zip --zoning-zip data/raw/flawi_ktn_gpkg.zip
```

Wenn das GeoPackage mehrere Ebenen enthält, nennt die Fehlermeldung die verfügbaren Layer; dann mit `--zoning-layer NAME` wiederholen.

### Ergebnis

- `data/processed/malta_boundary_2026.geojson`
- `data/processed/malta_zoning.geojson`
- `data/processed/malta_bauland.geojson`
- `data/processed/import_manifest.json` (Zeit, Quelle, SHA-256, Layer, Featureanzahl)

Die Gemeinde wird mit **ID 20619 und Name Malta** ausgewählt. Aus dem landesweiten Widmungs-Layer `WIDG` werden Datensätze mit `GEMNR=20619` extrahiert und zusätzlich mit der Gemeindegrenze verschnitten. Die Ausgangs-CRS werden geprüft; die GIS-Ausgabe erfolgt in EPSG:31287. Ungültige Geometrien führen zunächst zu einem Fehler statt zu unbemerkter Änderung.

**Wichtig:** Der landesweite Widmungsdatensatz ist kein alleiniger Beleg für Rechtswirksamkeit einzelner Gemeindeänderungen. Ohne Abgleich mit Kundmachungen dürfen die Flächen nur als GIS-Datenstand bezeichnet werden.

Quellen: [Statistik Austria](https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_GEM_1), [Land Kärnten](https://www.data.gv.at/katalog/dataset/cef1c710-3564-4c4a-adce-39896ba4bed8). Lizenzen jeweils CC BY 4.0, Attribution erforderlich.
