#!/usr/bin/env python3
"""Build the self-contained multiplier registry explorer page.

The page lets a reader find an occupation and see every step from the measured
O*NET/BLS inputs to its reference multiplier, compare two occupations, and move
the CHOSEN factor weights. It runs entirely in the browser: data, constants and
math are embedded in one HTML file.

Where each thing comes from — nothing here is a copy:
    rows, provenance, bounds   hours_eoh/reference/data/ (registry, provenance, bounds)
    slider range               the default `delta` of scenarios.multiplier_sensitivity.sweep_factor_weights
    weights, map constants     hours_eoh.data (M_FACTOR_WEIGHTS, M_IMPACT_SUBDOMAIN_WEIGHTS,
                               M_COMPOSITE_Z_*, M_IMPACT_COMPOSITE_*, M_FLOOR, M_GEOMETRIC_R,
                               M_BAND_*, M_MAX, MEAN_MULTIPLIER_REFERENCE)

The build REFUSES to write a page when:
    - the bounds file and data.py disagree on any constant the page uses;
    - the repo's own functions (impact_composite_from_subdomains,
      composite_from_factors, reference_multiplier) do not reproduce the registry;
    - the page names a provenance key the provenance CSV does not carry, or the
      CSV carries a tag the page has no class for.

What it CANNOT check (stated, per the checker-gaps rule): the page's JavaScript
math. That is a second implementation; `tests/test_explorer_build.py` runs it
under node against the repo's functions, and each occupation card shows a
✓/✗ against the registry in the browser.

Usage:
    python3 utils/explorers/multiplier/build.py [--out FILE]

Normally run by hooks/docs_explorers.py during `mkdocs build`.
"""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hours_eoh import data as D  # noqa: E402
from hours_eoh.core.multipliers import (  # noqa: E402
    composite_from_factors,
    epoch_factor_weights,
    impact_composite_from_subdomains,
    reference_multiplier,
)
from hours_eoh.scenarios.multiplier_sensitivity import sweep_factor_weights  # noqa: E402

DATA_DIR = REPO_ROOT / "hours_eoh" / "reference" / "data"
REGISTRY = DATA_DIR / "multiplier_registry_v5.csv"
PROVENANCE = DATA_DIR / "multiplier_provenance_v5.csv"
BOUNDS = DATA_DIR / "multiplier_reference_bounds.json"
TEMPLATE = Path(__file__).resolve().parent / "template.html"

PLACEHOLDER = "/*DATA*/"

# The page's tag classes, keyed by the provenance CSV's closed tag vocabulary.
# An unmapped tag fails the build rather than rendering a plausible default.
TAG_CLASSES: dict[str, str] = {
    "measured": "measured",
    "derived": "derived",
    "physics": "derived",
    "CHOSEN": "chosen",
    "planned": "planned",
    "derived_then_FROZEN": "frozen",
    "n/a": "na",
}

FACTOR_NAMES = ("training", "demand", "scarcity", "impact")
IMPACT_NAMES = ("dependency", "substitutability", "harm", "temporal")

NUMERIC = {
    "ep_employment_k", "oews_median_wage", "f_training", "f_demand", "f_scarcity",
    "i_dependency", "i_substitutability", "i_harm", "i_temporal", "f_impact",
    "composite", "reference_multiplier",
}
COLUMNS = ["occ6", "title", "ep_employment_k", "oews_median_wage",
           "f_training", "f_demand", "f_scarcity", "f_impact",
           "i_dependency", "i_substitutability", "i_harm", "i_temporal",
           "composite", "reference_multiplier"]

# Agreement with the registry. The registry stores reference_multiplier to 3 dp,
# so the multiplier is compared after rounding; composite and f_impact are
# stored at full precision.
TOL_STORED = 1e-9
TOL_ROUNDED = 5e-4


class BuildError(Exception):
    """The page would not reproduce the repo; nothing is written."""


def _num(v: str) -> float | None:
    if v is None or v.strip() == "":
        return None
    x = float(v)
    return None if math.isnan(x) else x


def constants() -> dict[str, Any]:
    """Every constant the page uses, read from data.py — the source of truth."""
    return {
        "factor_weights": dict(zip(FACTOR_NAMES, D.M_FACTOR_WEIGHTS)),
        "impact_weights": dict(zip(IMPACT_NAMES, D.M_IMPACT_SUBDOMAIN_WEIGHTS)),
        "z_range": [D.M_COMPOSITE_Z_LO, D.M_COMPOSITE_Z_HI],
        "impact_bounds": [D.M_IMPACT_COMPOSITE_LO, D.M_IMPACT_COMPOSITE_HI],
        "floor": D.M_FLOOR,
        "R": D.M_GEOMETRIC_R,
        "band": [D.M_BAND_LOW, D.M_BAND_HIGH],
        "cap": D.M_MAX,
        "mean_reference": D.MEAN_MULTIPLIER_REFERENCE,
        # The weight sliders span published ± this, the harness's own sweep range.
        "weight_span": inspect.signature(sweep_factor_weights).parameters["delta"].default,
    }


def check_bounds_agree(C: dict[str, Any], bounds: dict[str, Any]) -> None:
    """data.py is a declared mirror of the bounds file; the page must not ship if
    the two sources disagree, whichever one moved."""
    pairs = [
        ("factor_weights", [C["factor_weights"][k] for k in FACTOR_NAMES],
         [bounds["factor_weights"][k] for k in FACTOR_NAMES]),
        ("composite_z_range", C["z_range"], bounds["composite_z_range"]),
        ("impact_composite bounds", C["impact_bounds"], bounds["bounds"]["impact_composite"]),
        ("floor", [C["floor"]], [bounds["floor"]]),
        ("R", [C["R"]], [bounds["R"]]),
        ("band", C["band"], bounds["band"]),
        ("cap", [C["cap"]], [bounds["cap"]]),
    ]
    for name, ours, theirs in pairs:
        if len(ours) != len(theirs) or any(abs(a - b) > TOL_STORED for a, b in zip(ours, theirs)):
            raise BuildError(f"data.py and multiplier_reference_bounds.json disagree on {name}: "
                             f"{ours} vs {theirs}")
    # The page says the published weights are the ε = 0.40 weights.
    at_ref = epoch_factor_weights(0.40)
    if any(abs(a - b) > TOL_STORED for a, b in zip(at_ref, D.M_FACTOR_WEIGHTS)):
        raise BuildError(f"epoch_factor_weights(0.40) = {at_ref} is not M_FACTOR_WEIGHTS; "
                         "the page's 'set for ε = 0.40' sentence would be false")


def check_registry(reg: list[dict[str, str]], methodology: str) -> None:
    """Recompute every row with the repo's functions — not a re-implementation."""
    versions = {r["methodology_version"] for r in reg}
    if versions != {methodology}:
        raise BuildError(f"methodology mismatch: registry {versions} vs bounds {methodology}")
    worst = 0.0
    for r in reg:
        fi = impact_composite_from_subdomains(
            float(r["i_dependency"]), float(r["i_substitutability"]),
            float(r["i_harm"]), float(r["i_temporal"]))
        comp = composite_from_factors(
            float(r["f_training"]), float(r["f_demand"]), float(r["f_scarcity"]), fi)
        m = reference_multiplier(comp)
        worst = max(worst,
                    abs(fi - float(r["f_impact"])),
                    abs(comp - float(r["composite"])))
        if abs(round(m, 3) - float(r["reference_multiplier"])) > TOL_ROUNDED:
            raise BuildError(f"{r['occ6']} {r['title']}: reference_multiplier() gives {m:.6f}, "
                             f"registry has {r['reference_multiplier']}")
    if worst > TOL_STORED:
        raise BuildError(f"repo functions do not reproduce the registry: max deviation {worst:g}")


def template_prov_keys(html: str) -> set[str]:
    """Every provenance key the template names, in any of its four spellings."""
    keys: set[str] = set()
    keys.update(re.findall(r'data-prov="([A-Za-z0-9_]+)"', html))
    keys.update(re.findall(r'tag\("([A-Za-z0-9_]+)"', html))
    keys.update(re.findall(r'prov:"([A-Za-z0-9_]+)"', html))
    keys.update(re.findall(r'provValue\("([A-Za-z0-9_]+)"', html))
    return keys


def check_provenance(prov: list[dict[str, str]], html: str) -> None:
    known = {p["constant_or_input"] for p in prov}
    missing = sorted(template_prov_keys(html) - known)
    if missing:
        raise BuildError(f"page names provenance keys absent from {PROVENANCE.name}: {missing}")
    unmapped = sorted({p["tag"] for p in prov} - set(TAG_CLASSES))
    if unmapped:
        raise BuildError(f"provenance tags with no page class: {unmapped}; add them to TAG_CLASSES")


def load_payload() -> dict[str, Any]:
    with REGISTRY.open(newline="", encoding="utf-8") as f:
        reg = list(csv.DictReader(f))
    with PROVENANCE.open(newline="", encoding="utf-8") as f:
        prov = list(csv.DictReader(f))
    bounds = json.loads(BOUNDS.read_text(encoding="utf-8"))

    C = constants()
    check_bounds_agree(C, bounds)
    check_registry(reg, bounds["methodology"])

    rows: list[list[Any]] = []
    for r in reg:
        row: list[Any] = []
        for c in COLUMNS:
            if c == "occ6":
                row.append(int(r[c]))
            elif c in NUMERIC:
                row.append(_num(r[c]))
            else:
                row.append(r[c])
        rows.append(row)
    meta = {k: bounds[k] for k in ("methodology", "reference_epoch", "sources")}
    return {"columns": COLUMNS, "rows": rows, "provenance": prov,
            "constants": C, "meta": meta, "tag_classes": TAG_CLASSES}


def build_html(template: Path = TEMPLATE) -> str:
    """Return the finished page, or raise BuildError."""
    html = template.read_text(encoding="utf-8")
    if html.count(PLACEHOLDER) != 1:
        raise BuildError(f"template must contain {PLACEHOLDER} exactly once")
    payload = load_payload()
    check_provenance(payload["provenance"], html)
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return html.replace(PLACEHOLDER, blob)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="multiplier_explorer.html", type=Path)
    a = ap.parse_args()
    try:
        html = build_html()
    except BuildError as e:
        raise SystemExit(f"multiplier explorer not built: {e}")
    a.out.write_text(html, encoding="utf-8")
    print(f"Wrote {a.out} ({a.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
