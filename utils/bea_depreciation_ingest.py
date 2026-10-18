"""BEA Fixed Assets → the shipped depreciation extract: what the US stock LOSES each
year against what it holds, 1925–2024, by the inventory's scopes.

    python3 utils/bea_depreciation_ingest.py [--raw rawdata/bea/fixed_assets] [--out hours_eoh/reference/data]

Output (committed):
    bea_depreciation_1925_2024.csv   year, then net stock and depreciation for each line
                                     below, BILLIONS of current dollars (BEA publishes
                                     millions; billions match `capital_inventory.BEA_UNITS`)

It reads the full-history workbooks BEA publishes (`Section1all_xls.xlsx`,
`Section7all_xls.xlsx`): current-cost NET STOCK at yearend (Tables 1.1, 7.1) and
current-cost DEPRECIATION over the year (Tables 1.3, 7.3).

WHY THIS EXISTS. `DEP_RATE` (0.045) and `FORMATION_DEPRECIATION_RATE` (0.05) hold one
physical quantity twice. The profiles' design lives gave 0.0428, 0.0286 or 0.0602,
depending on how one averages the lives
(`record/provenance.md#depreciation-derivation-does-not-reproduce`). BEA does not
average lives: it depreciates each asset type at its own measured rate and SUMS the
dollars. So depreciation over stock is the stock-weighted mean of the asset-level rates:
the aggregation the dispute could not choose, MEASURED, not chosen.

THE LINES, chosen to match `reference/capital_inventory.SCOPES`:
    private_nonres   Table 1.1/1.3 line 4 — private nonresidential ("productive")
    private_res      line 8 — private residential (what "residential" adds)
    government       Table 7.1/7.3 line 1 — all government fixed assets
    defense          Table 7.1/7.3 line 22 — federal national defense; the inventory's
                     government scope is NONDEFENCE, so the reader subtracts it, not this
                     script
    fixed            Table 1.1/1.3 line 2 — every fixed asset, defence included

The ingest checks each line's LABEL against the workbook, so a BEA renumbering fails the
ingest instead of shipping the wrong line.

It reads the workbooks with the standard library (zipfile + XML), with no Excel
dependency.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import zipfile
from xml.etree import ElementTree as ET

OUT_NAME = "bea_depreciation_1925_2024.csv"

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

#: (column prefix, workbook, stock sheet, depreciation sheet, line, label it must carry)
LINES: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("private_nonres", "Section1all_xls.xlsx", "FAAt101-A", "FAAt103-A", "4", "Nonresidential"),
    ("private_res",    "Section1all_xls.xlsx", "FAAt101-A", "FAAt103-A", "8", "Residential"),
    ("government",     "Section7all_xls.xlsx", "FAAt701-A", "FAAt703-A", "1", "Government fixed assets"),
    ("defense",        "Section7all_xls.xlsx", "FAAt701-A", "FAAt703-A", "22", "National defense"),
    ("fixed",          "Section1all_xls.xlsx", "FAAt101-A", "FAAt103-A", "2", "Fixed assets"),
)

#: The titles the two kinds of sheet must carry.
STOCK_TITLE = "Current-Cost Net Stock"
DEPRECIATION_TITLE = "Current-Cost Depreciation"


def read_sheet(path: pathlib.Path, name: str) -> list[dict[str, str | None]]:
    """One worksheet as a list of {column letter: cell text} rows."""
    z = zipfile.ZipFile(path)
    strings = [
        "".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS)
    ]
    targets = {r.get("Id"): r.get("Target")
               for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheets = ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", _NS)
    target = next((targets[s.get(_REL)] for s in sheets if s.get("name") == name), None)
    if target is None:
        raise KeyError(f"{path.name} has no sheet {name!r}")
    member = target.lstrip("/")
    member = member if member.startswith("xl/") else "xl/" + member
    rows: list[dict[str, str | None]] = []
    for r in ET.fromstring(z.read(member)).iter(f"{{{_NS['m']}}}row"):
        out: dict[str, str | None] = {}
        for c in r.findall("m:c", _NS):
            m = re.match(r"[A-Z]+", c.get("r", ""))
            if m is None:
                continue
            v = c.find("m:v", _NS)
            if v is None:
                t = c.find(".//m:t", _NS)
                out[m.group()] = t.text if t is not None else None
            else:
                out[m.group()] = strings[int(v.text or 0)] if c.get("t") == "s" else v.text
        rows.append(out)
    return rows


def _series(rows: list[dict[str, str | None]], line: str, label: str,
            title: str) -> dict[int, float]:
    if title not in (rows[0].get("A") or ""):
        raise ValueError(f"expected a {title!r} table, got {rows[0].get('A')!r}")
    header = next(r for r in rows if r.get("A") == "Line")
    years = {col: int(v) for col, v in header.items() if v and v.isdigit() and len(v) == 4}
    row = next((r for r in rows if r.get("A") == line), None)
    found = re.sub(r"\\\d+\\", "", (row or {}).get("B") or "").strip()
    if found != label:
        raise ValueError(f"line {line} reads {found!r}, expected {label!r} — BEA renumbered?")
    assert row is not None
    return {y: float(row[col]) for col, y in years.items() if row.get(col) not in (None, "", "...")}


def ingest(raw: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    columns: dict[str, dict[int, float]] = {}
    for prefix, book, stock_sheet, dep_sheet, line, label in LINES:
        path = raw / book
        columns[f"{prefix}_stock"] = _series(read_sheet(path, stock_sheet), line, label, STOCK_TITLE)
        columns[f"{prefix}_depreciation"] = _series(
            read_sheet(path, dep_sheet), line, label, DEPRECIATION_TITLE)
    years = sorted(set.intersection(*(set(s) for s in columns.values())))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / OUT_NAME
    with out.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", *columns])
        for y in years:
            writer.writerow([y, *(f"{columns[c][y] / 1000.0:.3f}" for c in columns)])
    print(f"{out}: {len(years)} years ({years[0]}–{years[-1]}), {len(columns)} columns")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default=pathlib.Path("rawdata/bea/fixed_assets"), type=pathlib.Path)
    parser.add_argument("--out", default=pathlib.Path("hours_eoh/reference/data"), type=pathlib.Path)
    args = parser.parse_args(argv)
    ingest(args.raw, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
