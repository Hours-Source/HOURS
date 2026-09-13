"""
Every figure the anchor comparison page rests on, emitted from the functions.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. The anchor comparison page (`docs/theory/anchor_comparison.md`)
states results computed elsewhere. Restating a derived figure in prose is failure
mode 13 — the drift this repo has caught more often than any other — and on this
page it was not hypothetical: the verification-cost figures were written on
2026-09-08 and were wrong by 2026-09-10, twice over.

**SO THE PAGE NOW QUOTES SHAPES, AND THIS MODULE HOLDS THE NUMBERS.** Where a
figure is calibration, the page describes its shape and names the function; this
emitter is where the current value lives, keyed, with the sentence it supports.
Where a figure is STRUCTURAL — a designed zero, an exact unit elasticity, a
verdict string, the set of anchors holding all three properties — the page may
state it, and `tests/test_anchor_page_figures.py` reads the published page and
checks the statement against this dict.

History: until 2026-09-12 the page lived in gitignored `notes/` and could not be
gated at all. It moved to `docs/` on publication, which is what made the page
checks possible.

  - `python3 utils/anchor_page_figures.py` prints the current values;
  - `--markdown` emits them as a table beside the sentence each supports.

**REPORTING ONLY.** Nothing here changes a shipped number; it re-presents what
the scenario and research layers already compute. Every entry names the call, so
a reader can run it rather than trust this file.

Layer: utils/ — imports freely, imported by nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hours_eoh.core.eoh_fulfillment import (
    eoh_to_teh_pipeline,
    observable_epsilon_ceiling,
)
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.research.anchor_determinacy import (
    determinacy_table,
    hours_shock_response,
    registration_leverage,
)
from hours_eoh.scenarios.labour_epsilon import instrument_comparison
from hours_eoh.scenarios.obligation_accounts import obligation_accounts
from hours_eoh.scenarios.verification_cost import (
    PEAK_SEARCH_POINTS,
    cadence_feasibility,
    corridor_is_usable,
    verification_arc,
    verification_crossover,
    verification_hours_us,
)
from utils import provenance as pv

__all__ = ["FIGURES", "figures", "as_markdown"]


def _verification_peak(scope: str) -> float:
    rows = verification_arc(scope=scope, basis="per_registered",
                            points=PEAK_SEARCH_POINTS)
    return max(r["verification_over_obligation"] for r in rows)


def _debt_share() -> float:
    d = pv.debt_summary(pv.load())
    return (d.bounded + d.placeholder) / d.total


#: figure key -> (how to compute it, what the page says it is).
#: The second element is the SENTENCE the number supports, not a restatement of
#: the number — mode 13 says the drift is in the prose, so the prose is what has
#: to travel beside the call.
FIGURES: dict[str, tuple[Callable[[], Any], str]] = {
    # Gold · Obligation precedes issuance · Where the work points · What would change our mind — the verification apparatus
    "verification_peak_core": (
        lambda: _verification_peak("core"),
        "the apparatus peaks at a low single-digit percentage of the obligation, narrow scope",
    ),
    "verification_peak_broad": (
        lambda: _verification_peak("broad"),
        "the apparatus peaks at a low single-digit percentage of the obligation, broad scope",
    ),
    "verification_peak_epsilon": (
        lambda: verification_crossover(basis="per_registered")["peak_epsilon"],
        "the epsilon the apparatus ratio peaks at — NOT a reporting point",
    ),
    "verification_crossover_core": (
        lambda: verification_crossover(scope="core",
                                       basis="per_registered")["crossover_epsilon"],
        "no crossover on the arc at apparatus scope (None is the claim)",
    ),
    "verification_crossover_broad": (
        lambda: verification_crossover(scope="broad",
                                       basis="per_registered")["crossover_epsilon"],
        "no crossover on the arc at apparatus scope (None is the claim)",
    ),
    "census_workers_core": (
        lambda: verification_hours_us("core")["workers"],
        "measured headcount, narrow scope",
    ),
    "census_workers_broad": (
        lambda: verification_hours_us("broad")["workers"],
        "measured headcount, broad scope",
    ),
    # Where the work points · What would change our mind — the registrant side, priced by the declared cadence
    "corridor_verdict_shipped_default": (
        lambda: corridor_is_usable()["verdict"],
        "on the shipped episodic cadence the corridor is closed and usable",
    ),
    "corridor_verdict_continuous": (
        lambda: corridor_is_usable(cadence="continuous")["verdict"],
        "a continuous register leaves the corridor with open edges",
    ),
    "verification_headroom_share_at_subsistence": (
        lambda: cadence_feasibility()["headroom_share_of_obligation"],
        "the labour headroom for verification at subsistence, as a share of the obligation",
    ),
    "episodic_regimes_that_fit": (
        lambda: cadence_feasibility()["regimes_that_fit"],
        "every episodic regime fits inside that headroom",
    ),
    "continuous_human_affordable_from_epsilon": (
        lambda: cadence_feasibility(cadence="continuous")
        ["affordable_from_epsilon"]["continuous_human"],
        "human-performed continuous recording becomes affordable only from mid-arc",
    ),
    # How they compare — the shock table
    "shock_labour_minting": (
        lambda: hours_shock_response()["shocks"]["labour_halves"]["minting_change"],
        "labour halves: the base responds to labour alone",
    ),
    "shock_capital_obligation": (
        lambda: hours_shock_response()["shocks"]["capital_halves"]["obligation_change"],
        "capital halves: the obligation moves by a few percent",
    ),
    "shock_capital_minting": (
        lambda: hours_shock_response()["shocks"]["capital_halves"]["minting_change"],
        "capital halves: minting unmoved — the gap the supply claim concedes",
    ),
    "shock_ecosystem_minting": (
        lambda: hours_shock_response()["shocks"]["ecosystem_halves"]["minting_change"],
        "ecosystem halves: blind by charter, and the page keeps it visible",
    ),
    # Obligation precedes issuance · Where the work points — registration
    "registration_share": (
        lambda: registration_leverage(0.40)["baseline_share"],
        "the registered share at the reference epsilon — most human EOH mints nothing",
    ),
    "registration_elasticity": (
        lambda: registration_leverage(0.40)["elasticity"],
        "registration is unit elastic on the money supply",
    ),
    # Supply is endogenous to the population — the second instrument
    "instrument_verdict": (
        lambda: instrument_comparison()["verdict"],
        "the labour and capital routes to epsilon are adjacent, not overlapping",
    ),
    # ε is the share of obligation still dependent on human agency — the ceiling
    "observable_epsilon_at_top_capability": (
        lambda: eoh_to_teh_pipeline(0.99)["epsilon_observable"],
        "at capability 0.99 the observable machine share stays well short of 1",
    ),
    "human_fraction_at_top_capability": (
        lambda: eoh_to_teh_pipeline(0.99)["human_fraction"],
        "and the human share is many times the 1% the parameter implies",
    ),
    "ceiling_on_subsistence_mix": (
        lambda: observable_epsilon_ceiling(total_eoh(epsilon=0.0)),
        "the ceiling on the epsilon=0 obligation mix — the lower, flattering one",
    ),
    "ceiling_on_top_mix": (
        lambda: observable_epsilon_ceiling(total_eoh(epsilon=0.99)),
        "the ceiling on the epsilon=0.99 mix — higher, so a smaller human residual",
    ),
    # How strongly HOURS claims it — the accounts
    "delivery_ratio_at_zero": (
        lambda: (obligation_accounts(0.0)["delivery"]
                 / obligation_accounts(0.0)["obligation"]),
        "delivery as a share of the obligation at subsistence",
    ),
    "delivery_ratio_at_reference": (
        lambda: (obligation_accounts(0.40)["delivery"]
                 / obligation_accounts(0.40)["obligation"]),
        "delivery as a share of the obligation at the reference",
    ),
    "delivery_ratio_at_top": (
        lambda: (obligation_accounts(0.99)["delivery"]
                 / obligation_accounts(0.99)["obligation"]),
        "delivery as a share of the obligation at post-scarcity",
    ),
    # Where the work points · How strongly HOURS claims it — the constants
    "constants_total": (
        lambda: pv.debt_summary(pv.load()).total,
        "every constant is tagged and published with its basis",
    ),
    "measurement_debt_share": (
        _debt_share,
        "roughly two constants in five are placeholder or bounded",
    ),
    # Mutual credit · How they compare — the not-unique result
    "anchors_classified": (
        lambda: len(determinacy_table()),
        "anchors classified from their own definitions",
    ),
    "anchors_holding_all_three": (
        # DIRECT INDEXING, NOT `.get()`, AND THIS COST SOMETHING ALREADY.
        # The first version of this entry asked for `registers_obligation`;
        # the field is called `registered`. `.get()` returned None for every
        # row, the filter emptied, and the emitter cheerfully reported that NO
        # anchor holds all three properties — inverting the page's central
        # result, silently, in the module written to stop exactly that. A
        # missing key must raise.
        lambda: sorted(
            row["anchor"] for row in determinacy_table()
            if row["determinate"] and row["responsive"] and row["registered"]
        ),
        "the anchors holding all three properties — HOURS is not alone",
    ),
}


def figures() -> dict[str, Any]:
    """Every page figure, computed now. units: as each entry's own quantity."""
    return {key: fn() for key, (fn, _) in FIGURES.items()}


def as_markdown() -> str:
    """
    The figure table, with the sentence beside each value.

    A reader of the page sees prose; a reviser of the page should see this.
    """
    live = figures()
    width = max(len(k) for k in FIGURES)
    lines = [
        "<!-- generated by utils/anchor_page_figures.py — do not hand-edit -->",
        "",
        f"| {'figure':<{width}} | value | what the page says it is |",
        f"|{'-' * (width + 2)}|---|---|",
    ]
    for key, (_, meaning) in FIGURES.items():
        value = live[key]
        if isinstance(value, float):
            shown = f"{value:.6g}"
        elif isinstance(value, list):
            shown = ", ".join(str(v) for v in value)
        else:
            shown = str(value)
        lines.append(f"| `{key:<{width}}` | {shown} | {meaning} |")
    return "\n".join(lines)


def main() -> int:
    if "--markdown" in sys.argv:
        print(as_markdown())
        return 0

    live = figures()
    width = max(len(k) for k in FIGURES)
    for key, value in live.items():
        if isinstance(value, float):
            shown = f"{value:.6g}"
            if 0.0 < abs(value) < 10.0:
                shown += f"   ({value:.4%})"
        else:
            shown = str(value)
        print(f"{key:<{width}}  {shown}")
    print(
        f"\n{len(live)} figures. The page quotes shapes; these are the values "
        "behind them."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
