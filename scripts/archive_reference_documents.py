#!/usr/bin/env python3
"""Quellenarchiv: OIB-PDFs einmalig beziehen, lokale Fachtexte aufnehmen und SHA256 pruefen.

Keine Weitergabe/Repo-Uploads. Oeffentliche direkte OIB-PDFs nur mit --download.
TRVB/VB-01/RIS nur autorisiert manuell lokal ablegen.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "reference_documents.json"
DEST = ROOT / "reports" / "references"
MAX_BYTES = 30 * 1024 * 1024


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_file(path):
    if path.stat().st_size > MAX_BYTES or path.stat().st_size < 100:
        raise ValueError(f"Nicht plausible PDF-Groesse: {path}")
    with path.open("rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError(f"Kein PDF: {path}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--download", action="store_true", help="Fehlende freigegebene OIB-PDFs herunterladen")
    p.add_argument("--status", action="store_true", help="Nur lokales Archiv pruefen (Standard)")
    p.add_argument("--import-file", type=Path, help="Berechtigt vorhandene PDF-Datei lokal ins Archiv kopieren")
    p.add_argument("--id", help="Quellen-ID zu --import-file")
    p.add_argument("--as-of", help="Rechtsstand/Pruefstichtag der importierten PDF im ISO-Format YYYY-MM-DD")
    args = p.parse_args()
    if args.download and args.import_file:
        p.error("--download und --import-file nicht kombinieren")
    if args.import_file and not args.id:
        p.error("--import-file braucht --id")
    if args.as_of and not args.import_file:
        p.error("--as-of nur zusammen mit --import-file")
    if args.as_of:
        try:
            date.fromisoformat(args.as_of)
        except ValueError:
            p.error("--as-of muss ein gueltiges Datum YYYY-MM-DD sein")
    catalog = json.loads(CONFIG.read_text(encoding="utf-8"))
    entries = catalog["documents"]
    known = {e["id"]:e for e in entries}
    DEST.mkdir(parents=True, exist_ok=True)
    state_file = DEST / "archive_manifest.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"schema_version":1,"documents":{}}
    modified = False
    imported_as_of = {}
    failures = []
    download_sources = {}

    if args.import_file:
        if args.id not in known:
            p.error(f"Unbekannte Quelle: {args.id}")
        target = DEST / known[args.id]["filename"]
        if target.exists():
            p.error(f"Datei existiert bereits; kein Ueberschreiben: {target}")
        src = args.import_file.resolve(strict=True)
        checked_file(src)
        temporary = target.with_suffix(".part")
        if temporary.exists():
            p.error(f"Part-Datei vorhanden: {temporary}")
        try:
            shutil.copyfile(src,temporary)
            checked_file(temporary)
            os.replace(temporary,target)
        finally:
            temporary.unlink(missing_ok=True)
        if known[args.id]["id"] in ("k_btv_2024", "k_gfpo_2000") and not args.as_of:
            p.error("Fuer RIS-Exporte ist --as-of YYYY-MM-DD zwingend erforderlich")
        imported_as_of[args.id] = args.as_of
        print(f"[IMPORT] {args.id} -> {target}")
        modified = True

    for entry in entries:
        key = entry["id"]
        file = DEST / entry["filename"]
        if args.download and entry["acquisition"] == "auto_pdf" and not file.exists():
            temporary = file.with_suffix(".part")
            if temporary.exists():
                raise RuntimeError(f"Unvollstaendige Datei vorhanden: {temporary}")
            candidates = entry.get("download_urls") or [entry["download_url"]]
            downloaded = False
            for url in candidates:
                if not url.startswith("https://"):
                    raise ValueError("Download nur HTTPS")
                print(f"[GET] {key}: {url}", flush=True)
                try:
                    req = Request(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; Loeschwasserversorgung-OfflineArchiv/1.1)",
                        "Accept": "application/pdf,*/*;q=0.5",
                    })
                    total = 0
                    with urlopen(req, timeout=50) as resp, temporary.open("wb") as dest:
                        final_url = resp.geturl()
                        if not final_url.startswith("https://"):
                            raise ValueError("Nicht-HTTPS-Redirect")
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > MAX_BYTES:
                                raise ValueError(f"PDF-Groessenlimit 30 MiB: {key}")
                            dest.write(chunk)
                    checked_file(temporary)
                    os.replace(temporary, file)
                    download_sources[key] = final_url
                    downloaded = True
                    modified = True
                    print(f"[OK] Quelle erreicht: {key}", flush=True)
                    break
                except (OSError, ValueError) as ex:
                    print(f"[WARN] {key}: {type(ex).__name__}: {ex}", flush=True)
                finally:
                    temporary.unlink(missing_ok=True)
            if not downloaded:
                failures.append(key)
                print(f"[FEHLER] {key}: Keine der {len(candidates)} PDF-Quellen lieferte ein gueltiges Dokument.", flush=True)
        if file.is_file():
            checked_file(file)
            digest = sha(file)
            previous = state["documents"].get(key,{})
            if previous.get("sha256") and previous["sha256"] != digest:
                raise RuntimeError(f"PDF weicht von archivierter SHA256 ab: {file}. "
                                   "Versionierung/Pruefung statt stiller Ersetzung!")
            state["documents"][key] = {
                "filename":entry["filename"],"sha256":digest,
                "size_bytes":file.stat().st_size,
                "catalog_edition":entry["edition"],
                "archived_utc":previous.get("archived_utc") or datetime.now(timezone.utc).isoformat(),
                "acquisition":entry["acquisition"],
                "downloaded_from":download_sources.get(key) or previous.get("downloaded_from"),
                "legal_as_of":imported_as_of.get(key) or previous.get("legal_as_of"),
            }
            print(f"[OK]   {key}: {file.name} ({file.stat().st_size//1024} KiB, sha256 {digest[:12]}...)")
            if not previous:
                modified = True
        else:
            print(f"[OFFEN] {key}: {entry['acquisition']} | {entry['online_url']}")
    if modified:
        temporary = state_file.with_suffix(".part")
        temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(temporary,state_file)
        print(f"[OK] Archivmanifest: {state_file}")
    if failures:
        print(f"[WARN] Nicht archiviert: {', '.join(failures)}. Bereits erfolgreiche Dateien bleiben erhalten.", flush=True)
    print("[HINWEIS] Quellenarchiv ausschliesslich lokal; Rechte und geltende Fassung selbst pruefen.")


if __name__ == "__main__":
    main()
