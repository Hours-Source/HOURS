"""
National parcel census → the shipped county extract.

SPDX-License-Identifier: AGPL-3.0-or-later

Run this ONCE when the raw parcel file changes; the repo ships only the small
derived CSV it writes. The raw file is ~68 GB and lives in `rawdata/parcels/`,
which is gitignored — exactly as the 2.9 GB ATUS microdata lives in
`rawdata/atus/` while the repo ships `atus_annual_0325.csv`.

    python3 utils/parcel_ingest.py [--raw rawdata/parcels/...] [--out hours_eoh/reference/data]

Output (committed):
    parcel_county_counts.csv   statefp, countyfp, parcels, area_m2, area_parcels,
                               government_parcels, ownertype_known

WHY THIS EXTRACT AND NOT A RICHER ONE
--------------------------------------
The fee has ONE scaling basis and the measured servicing cost has three —
area 41.9%, parcel 44.5%, throughput 13.6% (`scenarios/use_split`). The 44.5%
that follows PARCEL COUNT is inexpressible in a per-SLU fee, and
`guf_magnitude.subdivision_invariance` proves it: splitting every parcel in two
returns the same fee to the float. Closing that needs a per-parcel TERM, and a
term needs a denominator.

**This extract is that denominator and nothing else.** It carries no use-category
mapping, because `usedesc` is 41.2% filled and is free text from 3,230
independent county systems (`RESIDENTIAL`, `Residential`, `SFR`, `Single Family
Detached`, `residential,residential`, `0131`). Normalising that onto ten fee
categories is a project with a real judgement in it, and bundling a judgement
into a count would make the count unciteable. It is deliberately left out.

AREA IS SHIPPED AND MUST NOT BE READ AS LAND AREA
--------------------------------------------------
`area_m2` is the sum of parcel FOOTPRINT areas. It is **not** the land area of
the county, and validating it against published state land areas shows why:

    FL  18.2 Mha summed vs 13.9 actual   1.31x
    TX  78.2            vs 67.7          1.16x
    IL  16.0            vs 14.4          1.11x
    CA  42.5            vs 40.3          1.05x
    AK  11.4            vs 147.8         0.08x
    UT   9.3            vs 21.3          0.43x

Six of twelve checked states EXCEED their own land area, and the pattern is
legible: developed states over-count because parcel footprints overlap, while
federal-land-heavy states under-count because that land is thinly parcelised.

THE OBVIOUS EXPLANATION IS NOT THE RIGHT ONE. `stackid` marks stacked parcels —
condominium units sharing a footprint — and on Florida, the worst offender, it
is populated on **0.2% of rows** (19,102 of 7.86M, largest stack 189 parcels).
That is nowhere near a 31% over-count, so deduplicating by `stackid` would not
fix it and the residual cause is unidentified. Easements, air and mineral
rights, and untagged condominium splits are all candidates and none is checked.

So the column is shipped because it is real data — these are the geometries the
census carries — and it is documented as unsafe to sum for land area, with
`tests/test_parcel_extract.py` pinning the over-count so the limitation cannot
be quietly forgotten. **The deliverable of this extract is the parcel COUNT**,
which is unaffected: geography is 100% populated and the total matches the
file's own row count exactly.

`calcarea` NOT `taxacres`
--------------------------
`taxacres` is assessor-reported and contaminated. Its median (0.6 acres) is
plausible and its tail is not: p95 = 10,489 acres, p99 = 37,183, with a sentinel
cap near 99,998. Summed it gives 157,478 Mha against 915 Mha of US land — **172×
over**. A field whose median is right and whose tail is garbage survives a spot
check and fails an aggregate, which is why this script sums the other one.

`calcarea` is geometry-derived and is in SQUARE METRES — established, not
assumed: the median ratio `calcarea/taxacres` over 717,431 rows where both are
sane is **4,046.6 against 4,046.86 m²/acre**, matching to four significant
figures and ruling out square feet.

WHAT THE COUNTS DO AND DO NOT INCLUDE
--------------------------------------
`parcels` counts every row for the county — the parcel roll as it stands.
`area_parcels` counts only those with a positive `calcarea`, and `area_m2` sums
those. A caller computing mean parcel size must divide by `area_parcels`, not by
`parcels`. In this vintage the distinction is nearly immaterial — **99.9% of
parcels carry geometry** — but both columns are shipped rather than a single
averaged one, because a vintage with poorer geometry coverage would make the
difference matter and an averaged column would hide it.

`government_parcels` counts `ownertype == 'GOVERNMENT'`, and `ownertype_known`
counts rows where the field is populated at all (81.5% nationally). The pair is
shipped rather than a bare fraction for the same reason: an unpopulated owner
type is not a private owner, and a fraction over the wrong denominator is how
the coverage-inflation trap works in `scenarios/land_stewardship`.

NO NATIONAL TOTAL IS WRITTEN. Callers sum the rows. A shipped total is a second
copy of a value whose source is elsewhere, and this repo has found that pattern
five times.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

#: Columns read from the raw file. Deliberately minimal: every extra column is
#: another pass over 160M rows, and every extra field is another judgement the
#: extract would be smuggling.
COLUMNS = ["statefp", "countyfp", "calcarea", "ownertype"]

DEFAULT_RAW = "rawdata/parcels/NATIONWIDE_SAMPLE_Q3_R2.parquet"
DEFAULT_OUT = "hours_eoh/reference/data"
OUT_NAME = "parcel_county_counts.csv"

#: `calcarea` is geometry-derived and mostly clean, but a parcel larger than
#: this is almost certainly a geometry artefact rather than a land holding.
#: 1e10 m² = 1,000,000 ha = 10,000 km², larger than the largest US county
#: outside Alaska. Rows above it are counted in `parcels` — they exist — but
#: excluded from `area_m2` and `area_parcels`, which is the
#: EXCLUDED-NOT-ZEROED discipline the ecological floor established: a value
#: that cannot be trusted is left out and said to be left out, never silently
#: costed at zero or silently included.
AREA_CEILING_M2 = 1.0e10


def ingest(raw: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    """One streaming pass over the parcel census; writes the county extract."""
    try:
        import pyarrow.parquet as pq
    except ImportError:  # pragma: no cover - environment-dependent
        sys.exit(
            "pyarrow is required to read the parquet census and is not "
            "installed. This script is run rarely and by hand; install it in a "
            "virtualenv rather than the system Python, which is PEP-668 "
            "managed. The repo itself never imports pyarrow — it ships the CSV."
        )

    pf = pq.ParquetFile(str(raw), memory_map=True)
    counts: dict[tuple[str, str], list[float]] = {}
    dropped_area = 0

    for batch in pf.iter_batches(batch_size=1_000_000, columns=COLUMNS):
        st = batch.column(0).to_pylist()
        ct = batch.column(1).to_pylist()
        ar = batch.column(2).to_pylist()
        ow = batch.column(3).to_pylist()
        for s, c, a, o in zip(st, ct, ar, ow):
            key = (s or "", c or "")
            row = counts.get(key)
            if row is None:
                row = counts[key] = [0.0, 0.0, 0.0, 0.0, 0.0]
            row[0] += 1                                    # parcels
            if a is not None and a > 0.0:
                if a <= AREA_CEILING_M2:
                    row[1] += a                            # area_m2
                    row[2] += 1                            # area_parcels
                else:
                    dropped_area += 1
            if o:
                row[4] += 1                                # ownertype_known
                if o == "GOVERNMENT":
                    row[3] += 1                            # government_parcels

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / OUT_NAME
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["statefp", "countyfp", "parcels", "area_m2", "area_parcels",
                    "government_parcels", "ownertype_known"])
        for (s, c), r in sorted(counts.items()):
            w.writerow([s, c, int(r[0]), f"{r[1]:.1f}", int(r[2]),
                        int(r[3]), int(r[4])])

    total = sum(r[0] for r in counts.values())
    print(f"{out}: {len(counts):,} counties, {int(total):,} parcels")
    print(f"  area rows dropped above the {AREA_CEILING_M2:.0e} m² ceiling: "
          f"{dropped_area:,}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default=DEFAULT_RAW, type=pathlib.Path)
    ap.add_argument("--out", default=DEFAULT_OUT, type=pathlib.Path)
    a = ap.parse_args(argv)
    if not a.raw.exists():
        sys.exit(f"raw parcel file not found: {a.raw} (it is gitignored by design)")
    ingest(a.raw, a.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
