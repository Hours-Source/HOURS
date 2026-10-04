"""
census — the repo's counted figures from ONE source, and the prose that quotes them.

The provenance count, the verdict-ladder tiers, the unbound shadow constants and
the confidence debt were each pinned as literals in several places — a test
assert, a claims predicate, CLAUDE.md, record/provenance.md — so adding one
constant meant ~6 hand edits in 4 files (the provenance count alone moved in
31 of 271 commits). Option B (author, 2026-10-03):

  * `live()` computes every figure from the repo's own functions;
  * `tests/census_snapshot.json` holds the figures last ACKNOWLEDGED;
  * the prose figures sit between `<!-- census:NAME -->` markers and are
    REGENERATED, never hand-edited;
  * `eoh provenance census --write` refreshes the snapshot and every block —
    running it is the acknowledgement, and the commit message carries the why.

The gate (`tests/test_provenance.py::TestTheCensusHasOneSource`) fails while the
live figures differ from the snapshot or a block differs from its rendering, so
nothing drifts silently. What it does NOT do: move the two RATCHET bounds
(`BASELINE_WITHOUT` in tests/test_confidence.py, the shadow bound in
tests/test_provenance.py). A ratchet that a regenerate command could raise is
not a ratchet; those stay deliberate edits.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "tests" / "census_snapshot.json"

#: Where each generated block lives. A block is `<!-- census:NAME -->…<!-- /census:NAME -->`.
DOCS = (REPO / "CLAUDE.md", REPO / "record" / "provenance.md")


def live() -> dict[str, Any]:
    """Every counted figure, from the functions that define it."""
    from utils import provenance as pv
    from utils.verdict_ladder import tier_census
    scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
    tagged, total = pv.coverage(scan)
    soft = [r for r in scan.records if r.tag in pv.SOFT_TAGS]
    tiers = tier_census()
    tags: dict[str, int] = {}
    for r in scan.records:
        tags[r.tag] = tags.get(r.tag, 0) + 1
    return {
        "tags": dict(sorted(tags.items())),
        "provenance_tagged": tagged,
        "provenance_total": total,
        "tiers": {k: int(v) for k, v in sorted(tiers["counts"].items())},
        "tier_total": int(tiers["total"]),
        "shadow_unbound": len([s for s in pv.shadow_constants() if not s.bound]),
        "confidence_without": len([r for r in soft if not getattr(r, "confidence", None)]),
        "confidence_soft": len(soft),
    }


def snapshot() -> dict[str, Any]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def render(name: str, s: dict[str, Any]) -> str:
    """The text a block holds, from a census `s`."""
    if name == "state":
        return (f"Provenance **{s['provenance_tagged']}/{s['provenance_total']}**, "
                f"shadow ratchet **{s['shadow_unbound']}**, confidence ratchet "
                f"**{s['confidence_without']}** of {s['confidence_soft']}")
    if name == "shadow":
        return str(s["shadow_unbound"])
    if name == "confidence":
        return f"**{s['confidence_without']} of {s['confidence_soft']}**"
    if name == "tags":
        n = sum(s["tags"].values())
        return ", ".join(f"{tag} {c} ({c / n:.1%})" for tag, c in
                         sorted(s["tags"].items(), key=lambda kv: (-kv[1], kv[0])))
    if name == "provenance":
        return (f"**{s['provenance_total']} constants in `data.py`, all tagged** — "
                f"`provenance {s['provenance_tagged']}/{s['provenance_total']}`")
    raise KeyError(f"no census block {name!r}")


_BLOCK = re.compile(r"<!-- census:(\w+) -->(.*?)<!-- /census:\1 -->", re.S)


def blocks(text: str) -> list[tuple[str, str]]:
    """(name, current content) for every census block in `text`."""
    return [(m.group(1), m.group(2)) for m in _BLOCK.finditer(text)]


def stale(s: dict[str, Any] | None = None) -> list[str]:
    """What disagrees: the live figures against the snapshot, and every block
    against its rendering from the snapshot. Empty means acknowledged."""
    s = snapshot() if s is None else s
    out = [f"{k}: live {v!r} ≠ acknowledged {s.get(k)!r}"
           for k, v in live().items() if s.get(k) != v]
    for doc in DOCS:
        for name, body in blocks(doc.read_text(encoding="utf-8")):
            if body != render(name, s):
                out.append(f"{doc.relative_to(REPO)} census:{name}: {body!r} ≠ {render(name, s)!r}")
    return out


def write() -> dict[str, Any]:
    """Acknowledge the live census: write the snapshot and regenerate every block."""
    s = live()
    SNAPSHOT.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        doc.write_text(_BLOCK.sub(
            lambda m: f"<!-- census:{m.group(1)} -->{render(m.group(1), s)}<!-- /census:{m.group(1)} -->",
            text), encoding="utf-8")
    return s
