#!/usr/bin/env python3
"""BEV-Adressregisterpaket lokal inspizieren, ohne Zuordnung oder Datenmutation.

Akzeptiert ZIP, GeoPackage (GPKG), GeoJSON oder einen entpackten Ordner.
Die Ausgabe ist eine Metadaten-Inventur; sensible Originaldaten bleiben lokal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MAX_NAMES = 80


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def scan_csv(path):
    for enc in ("utf-8-sig","utf-16","cp1252"):
        try:
            with path.open("r",encoding=enc,newline="") as f:
                sample=f.read(32768)
                if not sample.strip():
                    return {"type":"CSV","empty":True}
                dialect=csv.Sniffer().sniff(sample,delimiters=";,\t|")
                f.seek(0)
                reader=csv.reader(f,dialect)
                header=next(reader,[])
                return {"type":"CSV","encoding":enc,"delimiter":dialect.delimiter,
                        "fields":header[:MAX_NAMES],"sample_columns":len(header)}
        except (UnicodeError,csv.Error):
            continue
    return {"type":"CSV","warning":"encoding_or_delimiter_unresolved"}


def scan_gpkg(path):
    con=sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro",uri=True)
    try:
        layers=con.execute("SELECT table_name,data_type,identifier,srs_id "
                           "FROM gpkg_contents ORDER BY table_name").fetchall()
        results=[]
        for name,typ,identifier,srs in layers:
            safe='"'+name.replace('"','""')+'"'
            columns=[r[1] for r in con.execute(f"PRAGMA table_info({safe})")]
            results.append({"layer":name,"data_type":typ,"identifier":identifier,
                            "srs_id":srs,"fields":columns[:MAX_NAMES]})
        return {"type":"GPKG","layers":results}
    finally:
        con.close()


def list_zip(path):
    with zipfile.ZipFile(path) as z:
        entries=[]
        for x in z.infolist():
            if x.is_dir():
                continue
            if x.filename.startswith("/") or ".." in Path(x.filename.replace("\\","/")).parts:
                raise ValueError("Unsicherer ZIP-Eintrag: "+x.filename)
            entries.append({"name":x.filename,"uncompressed_bytes":x.file_size,
                            "compressed_bytes":x.compress_size})
        return {"type":"ZIP","entries":entries[:150],
                "total_entries":len(entries),"truncated":len(entries)>150}


def inspect(path):
    if path.is_dir():
        files=sorted(p for p in path.rglob("*") if p.is_file())
        result={"type":"DIRECTORY","files":len(files),
                "items":[{"name":str(x.relative_to(path)),"bytes":x.stat().st_size}
                         for x in files[:100]]}
        return result
    extension=path.suffix.lower()
    if extension==".zip":
        return list_zip(path)
    if extension==".gpkg":
        return scan_gpkg(path)
    if extension in (".csv",".txt"):
        return scan_csv(path)
    if extension in (".geojson",".json"):
        with path.open(encoding="utf-8-sig") as f:
            data=json.load(f)
        if data.get("type")=="FeatureCollection":
            first=data.get("features",[])[:1]
            return {"type":"GeoJSON","features":len(data.get("features",[])),
                    "first_geometry":first[0].get("geometry",{}).get("type") if first else None,
                    "fields":list((first[0].get("properties") or {}).keys()) if first else []}
    raise ValueError(f"Unbekannter Dateityp: {path.suffix}. ZIP/GPKG/CSV/GeoJSON erwartet.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True,help="BEV ZIP/GPKG/CSV/GeoJSON oder entpackter Ordner")
    parser.add_argument("--gemeinde",default="20619",help="Dokumentations-Kennung; kein Geo-Filter")
    parser.add_argument("--out",type=Path,help="Optionaler lokaler JSON-Bericht")
    args=parser.parse_args()
    path=args.input.resolve()
    if not path.exists():
        parser.error(f"Datei/Ordner fehlt: {path}")
    print(f"[INFO] BEV-Paket: {path}",flush=True)
    result={"municipality_context":args.gemeinde,"source_path":str(path),
            "bytes":path.stat().st_size if path.is_file() else None,
            "sha256":digest(path) if path.is_file() else None,
            "inspection":inspect(path),
            "note":"Nur Paketinspektion. Kein Gebaeude-Join, keine Adress-Zuordnung."
           }
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(f"[OK] {args.out}")


if __name__=="__main__":
    main()
