#!/usr/bin/env python3
"""
grib_scan — locate content in very large GRIB files without decoding them.

Every GRIB message declares its own byte length in section 0, so a file can be
traversed header-to-header with seeks, reading ~37 bytes per message and never
touching a payload. On the ERA5 archives in `rawdata/` (~200 GB each) this walks
a file in seconds where `pygrib.open()` followed by iteration times out: pygrib
reads each message to build its index, which is the wrong tool when the question
is merely "which timestamps are in here, and where?".

Two uses:

    timestamps(path)          which reference stamps a file contains
    find(path, y, m, d)       byte ranges for one day, to decode selectively

The second is the reusable pattern: walk cheaply to get offsets, then hand only
those byte ranges to eccodes. That turned a 200 GB scan into a ~7 GB read when
extracting three variables for one date.

── TWO TRAPS, both found the hard way on ERA5 ──────────────────────────────────

1. THIS REPORTS REFERENCE TIME, NOT VALIDITY TIME. Section 1 carries the
   reference (forecast base) time; the validity time is reference + step, and
   step lives in section 4, which this deliberately does not read. For
   INSTANTANEOUS fields step = 0 and the two coincide. For ACCUMULATED and
   mean-rate fields they do not:

       data12utc.grib reports stamps at "06Z" — those are `tp`, `bld`, `cdir`
       and friends with step 6, ACTUALLY VALID AT 12Z.

   Consequences in both directions: a file can appear to hold hours it does not
   sample, and fields valid 00–06Z on the 1st of a month sit under the PREVIOUS
   month's 18Z reference, so a naive month filter silently drops them. If you
   need validity, decode with eccodes and read `validityDate`/`validityTime`.

2. ONE shortName CAN COVER TWO GRIDS. ERA5 files carry both the 0.25° reanalysis
   (Ni = 1440) and the 0.5° ensemble (Ni = 720), the latter at 3-hourly steps.
   Keying extracted fields by hour alone lets the ensemble silently overwrite the
   reanalysis at hours 0/3/6/9/12/15/18/21. Filter on `Ni == 1440` — this scanner
   cannot see Ni, so the filter belongs in whatever decodes the offsets.

Validated against eccodes: 120 messages of `data00utc.grib`, zero mismatches on
reference date/time (GRIB edition 1). See tests/test_grib_scan.py.

Layer: utils/ — a data-handling helper. Imports nothing from hours_eoh; requires
no third-party package (stdlib only), so it runs wherever Python does.

Usage:
    python3 utils/grib_scan.py FILE [--stamps N]
    python3 utils/grib_scan.py FILE --find 1940-05-01
"""

from __future__ import annotations

import argparse
import collections
from typing import Iterator, NamedTuple

_HEADER = 16          # section 0 is 16 bytes in edition 2, 8 in edition 1
_ED1_EXTRA = 20       # enough of the PDS to reach the century octet
_ED2_EXTRA = 21       # enough of section 1 to reach the hour octet


class Message(NamedTuple):
    offset: int       # byte offset of the "GRIB" magic
    length: int       # total message length in bytes
    year: int
    month: int
    day: int
    hour: int         # REFERENCE hour — see trap 1


def walk(path: str) -> Iterator[Message]:
    """
    Yield one Message per GRIB record, reading only headers.

    Stops cleanly at EOF or at the first record whose magic is not "GRIB" — the
    latter means the length arithmetic lost sync, so a short walk is a signal,
    not a silent truncation. Handles editions 1 and 2.
    """
    with open(path, "rb") as fh:
        while True:
            offset = fh.tell()
            head = fh.read(_HEADER)
            if len(head) < _HEADER or head[:4] != b"GRIB":
                return
            edition = head[7]
            if edition == 1:
                length = int.from_bytes(head[4:7], "big")
                pds = head[8:_HEADER] + fh.read(_ED1_EXTRA)
                century = pds[24] if len(pds) > 24 else 20
                year = (century - 1) * 100 + pds[12]
                month, day, hour = pds[13], pds[14], pds[15]
            elif edition == 2:
                length = int.from_bytes(head[8:_HEADER], "big")
                sec1 = fh.read(_ED2_EXTRA)
                year = int.from_bytes(sec1[12:14], "big")
                month, day, hour = sec1[14], sec1[15], sec1[16]
            else:
                return
            yield Message(offset, length, year, month, day, hour)
            fh.seek(offset + length)


def timestamps(path: str, stop_after_distinct: int | None = None) -> tuple[list, dict]:
    """
    Distinct reference stamps in file order, with a message count for each.

    `stop_after_distinct` bounds the walk — enough to read a sampling pattern off
    the head of a file without traversing all of it.

    Returns (ordered stamps, {stamp: count}) where a stamp is
    (year, month, day, hour).
    """
    counts: collections.Counter = collections.Counter()
    order: list = []
    for m in walk(path):
        key = (m.year, m.month, m.day, m.hour)
        if key not in counts:
            order.append(key)
        counts[key] += 1
        if stop_after_distinct and len(order) >= stop_after_distinct:
            break
    return order, dict(counts)


def find(path: str, year: int, month: int, day: int,
         include_accumulation_base: bool = True) -> list[Message]:
    """
    Byte ranges for one day, ready to hand to eccodes.

    With `include_accumulation_base` (the default) this also returns the previous
    day's 18Z block, because accumulated fields valid 00–06Z on the target day
    carry that as their reference time (trap 1). Omitting it is how a month
    filter loses six hours of radiation data without erroring.

    The walk stops once the file passes the target month, so targets near the
    start of a file cost a fraction of a full traversal.
    """
    hits: list[Message] = []
    for m in walk(path):
        on_day = (m.year, m.month, m.day) == (year, month, day)
        next_day = (m.year, m.month, m.day) == (year, month, day + 1)
        prev_day = include_accumulation_base and (
            (m.year, m.month) == (year, month) and m.day == day - 1
            or (m.month == month - 1 and m.year == year and m.day >= 28)
        )
        if on_day or next_day or prev_day:
            hits.append(m)
        if (m.year, m.month) > (year, month):
            break
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="grib_scan", description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="GRIB file")
    ap.add_argument("--stamps", type=int, default=12, metavar="N",
                    help="stop after N distinct reference stamps (default: 12)")
    ap.add_argument("--find", metavar="YYYY-MM-DD",
                    help="report byte ranges for one day instead of stamps")
    args = ap.parse_args()

    if args.find:
        y, m, d = (int(x) for x in args.find.split("-"))
        hits = find(args.path, y, m, d)
        total = sum(h.length for h in hits)
        print(f"{args.path}: {len(hits)} messages for {args.find} "
              f"(+ accumulation base) = {total / 1e9:.2f} GB to decode")
        if hits:
            print(f"  first offset {hits[0].offset}, last {hits[-1].offset}")
        print("  NOTE: reference times — decode for validityDate/validityTime,")
        print("        and filter Ni to exclude the 0.5 deg ensemble.")
        return

    order, counts = timestamps(args.path, stop_after_distinct=args.stamps)
    walked = sum(counts.values())
    print(f"{args.path}: {walked} messages walked, {len(order)} distinct reference stamps")
    for k in order:
        print(f"   {k[0]:04d}-{k[1]:02d}-{k[2]:02d} {k[3]:02d}Z   ({counts[k]} msgs)")
    print("  NOTE: REFERENCE times, not validity — accumulated fields are stamped")
    print("        at their forecast base (see module docstring, trap 1).")


if __name__ == "__main__":
    main()
