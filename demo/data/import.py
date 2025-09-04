#!/usr/bin/env python3
import argparse, csv, gzip, os, re, sqlite3, sys
from typing import List, Optional

def open_text(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")

def sanitize(name: str) -> str:
    s = name.strip()
    if s.startswith("#"):
        s = s[1:]
    s = s.strip()
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    if re.match(r"^\d", s):
        s = "_" + s
    return s or "col"

def detect_header_and_data_start(lines: List[str]) -> (List[str], int):
    header_idx = None
    header_cols = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("# STN"):
            # Gebruik de hele regel na '#'
            raw = line.lstrip()[1:].strip()
            header_cols = [c.strip() for c in raw.split(",") if c.strip()]
            header_idx = i
            break
    if header_idx is None or not header_cols:
        raise RuntimeError("Kon de headerregel niet vinden (verwacht iets als: '# STN,YYYYMMDD,...').")
    return header_cols, header_idx + 1

def parse_value(cell: str, nullify_neg9999: bool) -> Optional[int]:
    cell = cell.strip()
    if cell == "":
        return None
    try:
        val = int(cell)
        if nullify_neg9999 and val == -9999:
            return None
        return val
    except ValueError:
        # Laat evt. strings (zoals datum yyyymmdd) intact als TEXT
        return cell

def main():
    ap = argparse.ArgumentParser(description="Import KNMI etmgeg_*.txt naar SQLite.")
    ap.add_argument("input_txt", help="Pad naar KNMI TXT (evt. .gz).")
    ap.add_argument("-o", "--output-db", default="knmi_etmgeg.sqlite", help="Uitvoer .sqlite bestand.")
    ap.add_argument("-t", "--table", default="etmgeg", help="Tabelnaam.")
    ap.add_argument("--drop-table", action="store_true", help="Bestaande tabel droppen als die bestaat.")
    ap.add_argument("--nullify-neg9999", action="store_true", help="Zet -9999 om naar NULL.")
    ap.add_argument("--no-index", action="store_true", help="Sla indexen aanmaken over.")
    ap.add_argument("--batch", type=int, default=5000, help="Batchgrootte voor inserts.")
    args = ap.parse_args()

    # Lees alle regels (we moeten eerst de header vinden)
    with open_text(args.input_txt) as f:
        lines = f.readlines()

    header_cols, data_start = detect_header_and_data_start(lines)
    columns = [sanitize(c) for c in header_cols]

    # Bepaal simpele types: STN → INTEGER, YYYYMMDD → TEXT, rest → INTEGER (KNMI daily is meestal int in tienden)
    col_defs = []
    for c in columns:
        if c.upper() == "STN":
            col_defs.append(f'"{c}" INTEGER')
        elif c.upper() == "YYYYMMDD":
            col_defs.append(f'"{c}" TEXT')
        else:
            col_defs.append(f'"{c}" INTEGER')

    # Maak/prepareer DB
    if not os.path.exists(args.output_db):
        open(args.output_db, "wb").close()
    con = sqlite3.connect(args.output_db)
    cur = con.cursor()

    if args.drop_table:
        cur.execute(f'DROP TABLE IF EXISTS "{args.table}";')

    cur.execute(f'CREATE TABLE IF NOT EXISTS "{args.table}" ({", ".join(col_defs)});')
    con.commit()

    # Insert data
    placeholders = ",".join(["?"] * len(columns))
    batch = []
    total = 0

    for line in lines[data_start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        row = next(csv.reader([line], delimiter=","))
        # trim/pad naar kolomlengte
        row = [x.strip() for x in row]
        if len(row) < len(columns):
            row += [""] * (len(columns) - len(row))
        elif len(row) > len(columns):
            row = row[:len(columns)]

        parsed = [parse_value(cell, args.nullify_neg9999) for cell in row]
        batch.append(parsed)
        if len(batch) >= args.batch:
            cur.executemany(f'INSERT INTO "{args.table}" VALUES ({placeholders});', batch)
            con.commit()
            total += len(batch)
            batch.clear()
            print(f"Ingevoegd: {total} rijen...", flush=True)

    if batch:
        cur.executemany(f'INSERT INTO "{args.table}" VALUES ({placeholders});', batch)
        con.commit()
        total += len(batch)
        batch.clear()

    print(f"Klaar. Totaal ingevoegd: {total} rijen in tabel {args.table}.")

    # Indexen
    if not args.no_index:
        try:
            # Index op STN en datum (indien aanwezig)
            if "STN" in columns:
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{args.table}_stn ON "{args.table}" (STN);')
            if "YYYYMMDD" in columns:
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{args.table}_date ON "{args.table}" (YYYYMMDD);')
            con.commit()
            print("Indexen aangemaakt.")
        except Exception as e:
            print(f"Kon indexen niet aanmaken: {e}", file=sys.stderr)

    con.close()
    print(f"SQLite DB: {args.output_db}")

if __name__ == "__main__":
    main()
