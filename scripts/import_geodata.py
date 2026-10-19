#!/usr/bin/env python3
"""Import amtliche Gemeindegrenze und Kärntner Flächenwidmung für eine Gemeinde.

Beispiel:
    python scripts/import_geodata.py --download
    python scripts/import_geodata.py --download --zoning-gpkg data/raw/flawi_ktn_gpkg.gpkg --repair-invalid

Keine Löschwasserbedarfsberechnung. Rechtswirksamkeit von Widmungen separat prüfen.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import ssl
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
import zipfile

import geopandas as gpd
import truststore

GEMEINDE_ID = "20619"
GEMEINDE_NAME = "Malta"
TARGET_EPSG = 31287
SOURCES = {
    "boundary": "https://www.statistik.gv.at/gs-open/GEODATA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=GEODATA:STATISTIK_AUSTRIA_GEM_20260101&outputFormat=SHAPE-ZIP&format_options=CHARSET:UTF-8",
    "zoning": "https://gis.ktn.gv.at/OGD/Geographie_Planung/flawi_ktn_gpkg.zip",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(Request(url, headers={"User-Agent": "Löschwasserversorgung-geodata-import/0.2"}), timeout=180, context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as response, tmp.open("wb") as out:
            while block := response.read(1024 * 1024):
                out.write(block)
        if not zipfile.is_zipfile(tmp):
            raise ValueError(f"Download ist kein gültiges ZIP: {url}")
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)


def unpack_archive(path: Path, directory: Path, extension: str) -> Path:
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Ungültiges ZIP: {path}")
    with zipfile.ZipFile(path) as archive:
        entries = [f for f in archive.infolist() if not f.is_dir()]
        # ZIP-Slip und externe Pfade verhindern
        for entry in entries:
            parts = Path(entry.filename.replace("\\", "/")).parts
            if entry.filename.startswith("/") or ".." in parts:
                raise ValueError(f"Unsicherer ZIP-Pfad: {entry.filename}")
        matches = [f for f in entries if f.filename.lower().endswith(extension)]
        if len(matches) != 1:
            raise ValueError(f"Erwarte genau eine {extension}-Datei in {path}, gefunden: {[f.filename for f in matches]}")
        archive.extractall(directory)
    return directory / matches[0].filename


def valid_crs(frame: gpd.GeoDataFrame, name: str) -> gpd.GeoDataFrame:
    if frame.crs is None:
        raise ValueError(f"{name}: kein CRS ausgewiesen. CRS wird nicht geraten.")
    if frame.empty or frame.geometry.isna().all():
        raise ValueError(f"{name}: keine Geometrien vorhanden")
    return frame


def select_municipality(frame: gpd.GeoDataFrame, municipality_id: str) -> tuple[gpd.GeoDataFrame, str]:
    """Gemeinde anhand amtlicher ID eindeutig auswählen.

    Statistik Austria WFS (2026): g_id / g_name.
    Ältere Exporte können ID / NAME verwenden.
    """
    columns = {c.casefold(): c for c in frame.columns}
    id_column = next((columns[key] for key in ("g_id", "id") if key in columns), None)
    name_column = next((columns[key] for key in ("g_name", "name") if key in columns), None)
    if id_column is None or name_column is None:
        raise ValueError(
            f"Gemeindedaten ohne erwartete ID-/Namensspalten: {list(frame.columns)}"
        )
    ids = frame[id_column].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    names = frame[name_column].astype(str).str.strip()
    selection = frame.loc[ids.eq(municipality_id)].copy()
    if len(selection) != 1:
        raise ValueError(
            f"Erwarte genau eine Gemeinde ({municipality_id}), "
            f"gefunden: {len(selection)}"
        )
    if selection.geometry.is_empty.any() or (~selection.geometry.is_valid).any():
        raise ValueError("Gemeindegrenze hat ungültige oder leere Geometrie")
    return selection.to_crs(epsg=TARGET_EPSG), str(names.loc[selection.index[0]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gemeinde", type=str, default=None, help="5-stellige Kärntner Gemeindenummer, z. B. 20619")
    parser.add_argument("--download", action="store_true", help="ZIP-Dateien aus amtlichen Quellen herunterladen")
    parser.add_argument("--boundary-zip", type=Path, default=Path("data/raw/gemeinden_2026.zip"))
    parser.add_argument("--zoning-zip", type=Path, default=Path("data/raw/flawi_ktn_gpkg.zip"))
    parser.add_argument("--zoning-layer", default="WIDG", help="Flächenwidmungs-Layer, Standard: WIDG")
    parser.add_argument("--zoning-gpkg", type=Path, help="Bereits vorhandene landesweite .gpkg-Datei statt ZIP verwenden")
    parser.add_argument("--repair-invalid", action="store_true", help="Ungültige Widmungspolygone explizit mit make_valid reparieren; Anzahl protokollieren")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    municipality_id = args.gemeinde if args.gemeinde is not None else GEMEINDE_ID
    if not (len(municipality_id) == 5 and municipality_id.isdigit() and municipality_id.startswith("2")):
        parser.error("--gemeinde muss eine 5-stellige Kärntner Gemeindenummer sein")
    generic_mode = args.gemeinde is not None
    if args.output_dir is None:
        args.output_dir = Path("data/processed") / municipality_id if generic_mode else Path("data/processed")

    inputs = [("boundary", args.boundary_zip)]
    if args.zoning_gpkg is None:
        inputs.append(("zoning", args.zoning_zip))
    for key, path in inputs:
        if args.download:
            print(f"[INFO] Download {key}: {SOURCES[key]}", flush=True)
            download(SOURCES[key], path)
        if not path.is_file():
            parser.error(f"Datei fehlt: {path}. Bitte --download verwenden oder lokales ZIP angeben.")

    with tempfile.TemporaryDirectory(prefix="municipality_gis_") as temporary:
        tmp = Path(temporary)
        shp = unpack_archive(args.boundary_zip, tmp / "municipalities", ".shp")
        gpkg = args.zoning_gpkg if args.zoning_gpkg is not None else unpack_archive(args.zoning_zip, tmp / "zoning", ".gpkg")
        if not gpkg.is_file():
            parser.error(f"Landesweites GeoPackage fehlt: {gpkg}")

        boundary, municipality_name = select_municipality(valid_crs(gpd.read_file(shp), "Gemeinden"), municipality_id)
        layers = gpd.list_layers(gpkg)["name"].tolist()
        if args.zoning_layer:
            if args.zoning_layer not in layers:
                raise ValueError(f"Layer nicht gefunden: {args.zoning_layer}. Vorhanden: {layers}")
            layer = args.zoning_layer
        elif len(layers) == 1:
            layer = layers[0]
        else:
            raise ValueError(f"Mehrere GeoPackage-Layer: {layers}. Bitte --zoning-layer wählen.")
        # Kärntner Widmungsdaten enthalten GEMNR: vor der Geometrieoperation filtern.
        zoning_all = valid_crs(gpd.read_file(gpkg, layer=layer), "Flächenwidmung")
        if "GEMNR" not in zoning_all.columns:
            raise ValueError(f"Flächenwidmung ohne GEMNR: {list(zoning_all.columns)}")
        gemnr = zoning_all["GEMNR"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        zoning = zoning_all.loc[gemnr.eq(municipality_id)].copy()
        if zoning.empty:
            raise ValueError(f"Keine Widmungen für GEMNR {municipality_id} im Layer {layer}.")
        if not zoning.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
            raise ValueError("Gemeinde-Flächenwidmung enthält Nicht-Polygon-Geometrien")
        invalid_mask = ~zoning.geometry.is_valid
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            if not args.repair_invalid:
                ids = zoning.loc[invalid_mask, "OBJECTID"].tolist() if "OBJECTID" in zoning.columns else zoning.index.tolist()
                raise ValueError(
                    f"{invalid_count} ungültige Widmungsgeometrien (OBJECTID/Index: {ids[:20]}). "
                    "Mit --repair-invalid ausdrücklich reparieren und Ergebnis kontrollieren."
                )
            from shapely import make_valid
            zoning.loc[invalid_mask, "geometry"] = zoning.loc[invalid_mask].geometry.map(make_valid)
            if not zoning.geometry.is_valid.all() or not zoning.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
                raise ValueError("Reparatur erzeugte keine durchgehend gültigen Polygone")
        zoning = zoning.to_crs(epsg=TARGET_EPSG)

        area = boundary.geometry.iloc[0]
        zoning = zoning.loc[zoning.intersects(area)].copy()
        if zoning.empty:
            raise ValueError("Keine Flächenwidmungsobjekte schneiden das Gemeindegebiet.")
        zoning["geometry"] = zoning.geometry.intersection(area)
        zoning = zoning.loc[~zoning.geometry.is_empty].copy()
        if zoning.empty:
            raise ValueError("Keine Flächen nach Verschneidung übrig.")
        zoning = gpd.GeoDataFrame(zoning, geometry="geometry", crs=f"EPSG:{TARGET_EPSG}")
        if "KATEGORIE" not in zoning.columns:
            raise ValueError("Spalte KATEGORIE fehlt; Bauland kann nicht bestimmt werden.")
        bauland = zoning.loc[zoning["KATEGORIE"].astype(str).str.strip().str.casefold().eq("bauland")].copy()

        args.output_dir.mkdir(parents=True, exist_ok=True)
        if generic_mode:
            bfile = args.output_dir / "boundary.geojson"
            zfile = args.output_dir / "zoning.geojson"
            afile = args.output_dir / "bauland.geojson"
        else:
            bfile = args.output_dir / "malta_boundary_2026.geojson"
            zfile = args.output_dir / "malta_zoning.geojson"
            afile = args.output_dir / "malta_bauland.geojson"
        boundary.to_file(bfile, driver="GeoJSON")
        zoning.to_file(zfile, driver="GeoJSON")
        bauland.to_file(afile, driver="GeoJSON")
        manifest = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "municipality_id": municipality_id,
            "municipality_name": municipality_name,
            "target_epsg": TARGET_EPSG,
            "municipality_geometry_date": "2026-01-01",
            "zoning_legal_validity_verified": False,
            "sources": {
                key: {"url": SOURCES[key], "local_path": str(path), "sha256": sha256(path)}
                for key, path in ([("boundary", args.boundary_zip)] + ([("zoning", args.zoning_zip)] if args.zoning_gpkg is None else []))
            },
            "zoning_layer": layer,
            "zoning_source_file": str(gpkg),
            "zoning_source_sha256": sha256(gpkg),
            "zoning_invalid_geometry_count_before_repair": invalid_count,
            "zoning_invalid_geometry_repaired": bool(invalid_count and args.repair_invalid),
            "zoning_source_crs": str(valid_crs(gpd.read_file(gpkg, layer=layer), "Flächenwidmung").crs),
            "outputs": {
                "boundary": {"file": str(bfile), "features": len(boundary)},
                "zoning": {"file": str(zfile), "features": len(zoning)},
                "bauland": {"file": str(afile), "features": len(bauland)},
            },
        }
        (args.output_dir / "import_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(manifest["outputs"], indent=2, ensure_ascii=False))
        print("[HINWEIS] Flächenwidmung ist nicht auf rechtliche Aktualität geprüft.")


if __name__ == "__main__":
    main()
