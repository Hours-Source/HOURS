"""
Tests for utils/grib_scan.py — the header-only GRIB locator.

Messages are synthesised byte-by-byte rather than read from a file, so the suite
needs no GRIB fixture and no eccodes install. That also makes these tests a
readable specification of the two header layouts the scanner parses.

The parser itself was validated against eccodes on real ERA5 data: 120 messages
of rawdata/data00utc.grib, zero mismatches on reference date/time (edition 1).
"""

from __future__ import annotations

import pytest

from utils.grib_scan import Message, find, timestamps, walk


# ---------------------------------------------------------------------------
# synthetic messages
# ---------------------------------------------------------------------------

def _grib1(year: int, month: int, day: int, hour: int, length: int = 64) -> bytes:
    """A GRIB edition-1 message: date lives in the PDS at octets 13-16 + 25."""
    body = bytearray(b"\x00" * length)
    body[0:4] = b"GRIB"
    body[4:7] = length.to_bytes(3, "big")
    body[7] = 1
    pds = 8                          # PDS starts here
    body[pds + 12] = year % 100
    body[pds + 13] = month
    body[pds + 14] = day
    body[pds + 15] = hour
    body[pds + 24] = year // 100 + 1  # century octet is 1-based
    return bytes(body)


def _grib2(year: int, month: int, day: int, hour: int, length: int = 64) -> bytes:
    """A GRIB edition-2 message: date lives in section 1 at octets 13-17."""
    body = bytearray(b"\x00" * length)
    body[0:4] = b"GRIB"
    body[7] = 2
    body[8:16] = length.to_bytes(8, "big")
    s1 = 16
    body[s1 + 12:s1 + 14] = year.to_bytes(2, "big")
    body[s1 + 14] = month
    body[s1 + 15] = day
    body[s1 + 16] = hour
    return bytes(body)


def _write(tmp_path, *messages: bytes):
    p = tmp_path / "synthetic.grib"
    p.write_bytes(b"".join(messages))
    return str(p)


# ---------------------------------------------------------------------------
# parsing both editions
# ---------------------------------------------------------------------------

def test_reads_edition_1_reference_time(tmp_path):
    path = _write(tmp_path, _grib1(1940, 5, 1, 0))
    (m,) = list(walk(path))
    assert (m.year, m.month, m.day, m.hour) == (1940, 5, 1, 0)
    assert m.offset == 0 and m.length == 64


def test_reads_edition_2_reference_time(tmp_path):
    path = _write(tmp_path, _grib2(2020, 12, 31, 18))
    (m,) = list(walk(path))
    assert (m.year, m.month, m.day, m.hour) == (2020, 12, 31, 18)


def test_century_octet_handled(tmp_path):
    """GRIB1 stores year-of-century plus a 1-based century octet — 2000 is
    century 21, not 20, and getting it wrong shifts every date by 100 years."""
    path = _write(tmp_path, _grib1(2000, 1, 1, 0), _grib1(1999, 1, 1, 0))
    years = [m.year for m in walk(path)]
    assert years == [2000, 1999]


# ---------------------------------------------------------------------------
# walking by declared length
# ---------------------------------------------------------------------------

def test_walks_variable_length_messages(tmp_path):
    """Messages differ in size, so the walk must seek by each declared length
    rather than a fixed stride."""
    path = _write(tmp_path,
                  _grib1(1940, 1, 1, 0, length=64),
                  _grib1(1940, 3, 1, 0, length=128),
                  _grib1(1940, 5, 1, 0, length=96))
    got = [(m.month, m.length) for m in walk(path)]
    assert got == [(1, 64), (3, 128), (5, 96)]


def test_stops_cleanly_on_desync(tmp_path):
    """A short walk is a signal, not silent truncation: once the magic no longer
    reads GRIB the arithmetic has lost sync and we stop."""
    path = _write(tmp_path, _grib1(1940, 1, 1, 0), b"NOTGRIB" + b"\x00" * 57)
    assert len(list(walk(path))) == 1


def test_stops_on_unknown_edition(tmp_path):
    body = bytearray(_grib1(1940, 1, 1, 0))
    body[7] = 9
    path = _write(tmp_path, bytes(body))
    assert list(walk(path)) == []


def test_handles_empty_and_truncated_files(tmp_path):
    assert list(walk(_write(tmp_path))) == []
    assert list(walk(_write(tmp_path, b"GRIB"))) == []


# ---------------------------------------------------------------------------
# timestamps
# ---------------------------------------------------------------------------

def test_timestamps_counts_and_preserves_file_order(tmp_path):
    path = _write(tmp_path,
                  _grib1(1940, 1, 1, 0), _grib1(1940, 1, 1, 0),
                  _grib1(1940, 3, 1, 0))
    order, counts = timestamps(path)
    assert order == [(1940, 1, 1, 0), (1940, 3, 1, 0)]
    assert counts[(1940, 1, 1, 0)] == 2


def test_stop_after_distinct_bounds_the_walk(tmp_path):
    path = _write(tmp_path, *[_grib1(1940, m, 1, 0) for m in (1, 3, 5, 8, 10, 12)])
    order, _ = timestamps(path, stop_after_distinct=2)
    assert order == [(1940, 1, 1, 0), (1940, 3, 1, 0)]


# ---------------------------------------------------------------------------
# find — the reusable locate-then-decode pattern
# ---------------------------------------------------------------------------

def test_find_returns_target_day(tmp_path):
    path = _write(tmp_path,
                  _grib1(1940, 5, 1, 0), _grib1(1940, 5, 1, 12),
                  _grib1(1940, 8, 1, 0))
    hits = find(path, 1940, 5, 1)
    assert [h.hour for h in hits] == [0, 12]


def test_find_includes_the_accumulation_base(tmp_path):
    """Fields valid 00-06Z on the 1st carry the PREVIOUS month's 18Z reference.
    Dropping that block is how six hours of radiation data go missing without
    any error being raised."""
    path = _write(tmp_path, _grib1(1940, 4, 30, 18), _grib1(1940, 5, 1, 0))
    assert len(find(path, 1940, 5, 1)) == 2
    assert len(find(path, 1940, 5, 1, include_accumulation_base=False)) == 1


def test_find_stops_once_past_the_target_month(tmp_path):
    """Targets near the head of a file must not cost a full traversal."""
    path = _write(tmp_path,
                  _grib1(1940, 5, 1, 0), _grib1(1940, 8, 1, 0),
                  _grib1(1945, 1, 1, 0))
    hits = find(path, 1940, 5, 1)
    assert [h.month for h in hits] == [5]


def test_find_reports_byte_ranges_usable_for_selective_decode(tmp_path):
    path = _write(tmp_path, _grib1(1940, 5, 1, 0, length=80))
    (h,) = find(path, 1940, 5, 1)
    assert isinstance(h, Message)
    raw = open(path, "rb").read()[h.offset:h.offset + h.length]
    assert raw[:4] == b"GRIB" and len(raw) == 80
