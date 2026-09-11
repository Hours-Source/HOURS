"""
Every figure the anchor comparison page quotes, emitted from the functions.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. `notes/anchor_comparison_draft.md` hand-copies every number it
states from a function that computes it. That is failure mode 13 — the drift this
repo has caught more often than any other — and on this page it is not
hypothetical: the verification-cost figures were published on 2026-09-08 and were
wrong by 2026-09-10, twice over. An earlier header guessed the page would go
stale "within weeks"; the measured interval is two days.

**THE PAGE CANNOT BE GATED WHERE IT LIVES.** `tests/test_claims_register.py`
checks CLAUDE.md and `record/*.md` because those are in the repo. `notes/` is
gitignored, so no test in `tests/` can read the draft. That is the real shape of
the blocker: the page has no regeneration path AND no gate, and it cannot have a
gate until it lands in `docs/`.

So this module is the half that can exist now. It emits the figures as a keyed
dict with the call that produced each one, so:

  - the draft can be checked against it by hand today (`--check` diffs a pasted
    figure block against the live values);
  - `--markdown` emits the block to paste, so a revision is a regeneration
    rather than a transcription;
  - when the page moves to `docs/theory/anchor_comparison.md`, a claims-register
    entry reads THIS dict rather than re-deriving the numbers, and the gate
    becomes a three-line addition instead of a project.

**REPORTING ONLY.** Nothing here changes a shipped number; it re-presents what
the scenario and research layers already compute. Every entry names the call, so
a reader can run it rather than trust this file — which is the same discipline
the page itself is trying to keep.

Layer: utils/ — imports freely, imported by nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hours_eoh.research.anchor_determinacy import (
    determinacy_table,
    hours_shock_response,
    registration_leverage,
)
from hours_eoh.scenarios.obligation_accounts import obligation_accounts
from hours_eoh.scenarios.verification_cost import (
    PEAK_SEARCH_POINTS,
    registrant_scope_sensitivity,
    verification_arc,
    verification_crossover,
    verification_hours_us,
)

__all__ = ["FIGURES", "figures", "as_markdown"]


def _verification_peak(scope: str) -> float:
    rows = verification_arc(scope=scope, basis="per_registered",
                            points=PEAK_SEARCH_POINTS)
    return max(r["verification_over_obligation"] for r in rows)


def _scope_sensitivity(scope: str, key: str) -> Any:
    # 40x is the ONE multiple that compares in matching units (registrant
    # workers against apparatus workers). It is a transferred judgement from a
    # single adversarial, money-denominated case with a 7.7x error bar of its
    # own, and `registrant_scope_sensitivity` refuses to default it. Passing it
    # HERE, at the presentation layer, is the right place for a judgement the
    # page is making out loud.
    return registrant_scope_sensitivity(40.0, scope=scope)[key]


#: figure key -> (how to compute it, what the page says it is).
#: The second element is the SENTENCE the number appears in, not a restatement
#: of the number — mode 13 says the drift is in the prose, so the prose is what
#: has to travel beside the call.
FIGURES: dict[str, tuple[Callable[[], Any], str]] = {
    # §3.1 / §5.2 / §6 / §7 — verification cost
    "verification_peak_core": (
        lambda: _verification_peak("core"),
        "the apparatus peaks at this share of the obligation, narrow scope",
    ),
    "verification_peak_broad": (
        lambda: _verification_peak("broad"),
        "the apparatus peaks at this share of the obligation, broad scope",
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
    # The conditional — apparatus PLUS a transferred registrant multiple
    "scope_sensitivity_core_peak": (
        lambda: _scope_sensitivity("core", "combined_peak"),
        "narrow scope at the 40x registrant multiple — does NOT cross",
    ),
    "scope_sensitivity_broad_peak": (
        lambda: _scope_sensitivity("broad", "combined_peak"),
        "broad scope at the 40x registrant multiple — DOES cross",
    ),
    "scope_sensitivity_broad_crossover": (
        lambda: _scope_sensitivity("broad", "crossover_epsilon"),
        "the epsilon at which the broad-scope conditional crosses",
    ),
    "scope_sensitivity_core_crosses": (
        lambda: _scope_sensitivity("core", "crosses"),
        "narrow scope does not cross even at 40x — both verdicts are live",
    ),
    # §4 — the shock table
    "shock_labour_minting": (
        lambda: hours_shock_response()["shocks"]["labour_halves"]["minting_change"],
        "labour halves: the base responds to labour alone",
    ),
    "shock_capital_obligation": (
        lambda: hours_shock_response()["shocks"]["capital_halves"]["obligation_change"],
        "capital halves: the obligation moves and the mint does not",
    ),
    "shock_capital_minting": (
        lambda: hours_shock_response()["shocks"]["capital_halves"]["minting_change"],
        "capital halves: minting unmoved — the gap section 5.2 concedes",
    ),
    "shock_ecosystem_minting": (
        lambda: hours_shock_response()["shocks"]["ecosystem_halves"]["minting_change"],
        "ecosystem halves: blind by charter, and the page keeps it visible",
    ),
    # §6 — registration capture
    "registration_share": (
        lambda: registration_leverage(0.40)["baseline_share"],
        "the registered share at the reference epsilon",
    ),
    "registration_elasticity": (
        lambda: registration_leverage(0.40)["elasticity"],
        "registration is unit elastic on the money supply",
    ),
    # §4 / §5 — the accounts
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
    # §3.7 / §4 — the not-unique result
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
    The figure block to paste into the page, with the sentence beside each value.

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
        f"\n{len(live)} figures. This is what the page must say. "
        "Paste with --markdown; do not retype."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
