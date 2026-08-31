"""
The personal obligation's four components, measured against observed time use —
and why it is a BOUND rather than a closure.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. `PERSONAL_EOH_COMPONENTS` is untouched and
`TestComponentSharesChangeNothing` fails the moment that stops being true.

WHAT THIS IS FOR. Phase 2's headline — the human fraction at ε=0.99 is 10.2×
the uniform figure — is weighted by care's **62.1% share of the personal
obligation**, and that share is a `placeholder`: the desk estimate's own four
terms, 208/156/208/936 over 1508. So the pending Phase 2 sign-off rests on a
number nothing measures. This module asks what the one instrument the repo owns
says about it.

WHAT IT FINDS. At the shipped defaults (ATUS 2025, the latest comparable year)
and under the mapping declared below, care is **25.7%** of mapped personal time
— 0.41× the desk share — and shelter 35.6% against a desk 10.3%. At the observed
care share Phase 2's factor is **4.82×** rather than 10.22×. Every figure quoted
in this module is pinned live by `TestTheQuotedFiguresAreStillTrue`.

WHY THAT IS A BOUND AND NOT A REPLACEMENT — THREE REASONS, AND THE THIRD IS
DECISIVE:

  1. OBSERVED IS NOT OBLIGATION. `observed = obligation − deferred + extraction`
     is the identification problem `scenarios/personal_floor` states; one
     observable, three unknowns.
  2. ONE COUNTRY, ONE DEVELOPMENT LEVEL. The desk shares are the obligation at
     AUTARKY. ATUS measures a high-capital society.
  3. **CARE HAS BEEN MARKETISED, and it moves the result in exactly this
     direction.** Daycare and residential elder care shift care out of unpaid
     time use into paid employment, and ATUS codes 03/04 count unpaid care only.
     So observed unpaid care UNDERSTATES the care obligation in a rich country —
     which is precisely the finding. The confound cannot be separated with this
     data, so the observed share is a LOWER bound on care's true share and the
     4.82× is a LOWER bound on Phase 2's factor.

THE ABATABILITIES CANNOT BE REACHED AT ALL, and their own pointers say why:
every one names cross-development variation (WHO/UNICEF JMP, GBD, "across
development levels"). `ABATEMENT_HALF_CAPITAL_TEH` is worse — its `resolves_by`
wants two or more CAPITAL levels, and 22 years of US deepening is 22 points at
one saturated level.

ONE ACQUISITION CLOSES ALL OF IT, and the repo has already named it three times
(`reference/atus_time_use`, `docs/theory/prior_art`, `AGE_WEIGHT_INFANT`): a
cross-country time-use panel spanning development levels — HETUS/MTUS. It would
settle the component shares, the abatabilities, K_half, the extraction wedge and
the infant age-weight band together.

Layer: scenarios/ — imports core/, data and reference/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.data import CARE_AUTOMATION_FLOOR, PERSONAL_EOH_COMPONENTS
from hours_eoh.reference import atus_time_use as atus

__all__ = [
    "COMPONENT_CODES",
    "EXCLUDED_CODES",
    "observed_shares",
    "share_comparison",
    "abatability_direction",
    "phase_2_sensitivity",
    "shares_report",
]

#: THE ASSUMED MAPPING — one declared judgement, isolated so it can be argued
#: with, on the `STEWARDSHIP_ATTRIBUTIONS` and `SCALING_BASIS` precedent. ATUS
#: tier-2 activity codes onto the four components of the personal obligation.
#:
#: Nothing in ATUS is coded by "obligation component"; this is an attribution and
#: not a measurement. The measured inputs are the hours.
#:
#: `0399` and `0499` are ATUS residual "other" categories and are absent from
#: some survey years entirely (17/22 and 18/22) because nobody reported the
#: activity. They are kept — a category with zero reported time is zero, not
#: missing — and the accessor returns 0.0 for a code the year does not carry.
COMPONENT_CODES: dict[str, tuple[str, ...]] = {
    # Caring for and helping household (03*) and non-household (04*) members.
    "care": ("0301", "0302", "0303", "0304", "0305", "0399",
             "0401", "0402", "0403", "0404", "0405", "0499"),
    # Food and drink preparation, presentation and clean-up.
    "nutrition": ("0202",),
    # Interior/exterior upkeep of the dwelling and its equipment.
    "shelter": ("0201", "0203", "0204", "0207", "0208"),
    # Health-directed time: children's health, and medical/care services.
    "health": ("0303", "0804"),
}

#: EXCLUDED, NOT ASSIGNED — the discipline `personal_statutory_floor`
#: established. Each is real time that plausibly serves the obligation and
#: cannot be attributed to ONE component without inventing a split.
EXCLUDED_CODES: dict[str, str] = {
    "0205": "lawn, garden and houseplants — amenity, shelter upkeep, or food production",
    "0206": "animals and pets — not a component of the human obligation as defined",
    "0209": "household management — overhead across all four, no basis to split it",
    "0701": "consumer purchases — groceries sit inside a total dominated by other retail",
    "0805": "personal care services — self-maintenance rather than an obligation component",
}

#: `0303` (children's health) is DELIBERATELY in both `care` and `health`. It is
#: care delivered FOR a health purpose and either attribution is defensible, so
#: the overlap is declared rather than resolved by fiat. It is ~2 h/person·yr
#: against a mapped total near 745, so no reported figure turns on it — and
#: `share_comparison` reports the overlap so a reader can see it is small.
_OVERLAPPING = ("0303",)


def observed_shares(year: int | None = None) -> dict:
    """
    Observed component shares of mapped personal time use, from ATUS.

    Governing sums, per component c:

        hours(c)  = Σ_{code ∈ COMPONENT_CODES[c]} hours_per_person_15plus(code)
        share(c)  = hours(c) / Σ_c hours(c)

    units: labour-hours per person aged 15+ per year, and dimensionless shares.

    ε-behaviour: NONE. This is a census of a present-day economy and carries no
    automation scaling; the ε-dependence lives in `phase_2_sensitivity`, which
    applies the shares to the automation floor.

    Worked example (2025, the shipped default): care 191.5, nutrition 259.8,
    shelter 265.2, health 28.7, mapped total 745.2 h/person15+·yr — care 25.7%.

    Args:
        year: ATUS survey year. Defaults to the latest comparable year.
    """
    y = atus.latest_year() if year is None else year
    hours = {
        c: atus.hours_per_person_15plus(y, codes)
        for c, codes in COMPONENT_CODES.items()
    }
    total = sum(hours.values())
    excluded = sum(
        atus.hours_per_person_15plus(y, (code,)) for code in EXCLUDED_CODES
    )
    return {
        "year":            y,
        "hours":           hours,
        "shares":          {c: h / total for c, h in hours.items()},
        "mapped_total":    total,
        "excluded_hours":  excluded,
        "excluded_share_of_all": excluded / (total + excluded),
        "overlap_hours": sum(
            atus.hours_per_person_15plus(y, (code,)) for code in _OVERLAPPING
        ),
    }


def share_comparison(year: int | None = None) -> dict:
    """
    Observed shares against the desk estimate, component by component.

    units: dimensionless shares and their ratio.

    THE RATIO IS THE FINDING and the level is not: at the 2025 default care
    reads 0.41× the desk share and shelter 3.44×, and both are far outside
    anything a mapping choice explains. The direction is what the marketisation
    confound also predicts, so the disagreement is real and its SIZE is not
    settled.
    """
    obs = observed_shares(year)
    rows = []
    for c, desk_spec in PERSONAL_EOH_COMPONENTS.items():
        desk = float(desk_spec["share"])
        seen = obs["shares"][c]
        rows.append({
            "component":  c,
            "observed":   seen,
            "desk":       desk,
            "ratio":      seen / desk,
            "abatability": float(desk_spec["abatability"]),
        })
    return {
        "year":  obs["year"],
        "rows":  rows,
        "mapped_total": obs["mapped_total"],
        "excluded_hours": obs["excluded_hours"],
        "overlap_hours": obs["overlap_hours"],
        "care_observed": obs["shares"]["care"],
        "care_desk":     float(PERSONAL_EOH_COMPONENTS["care"]["share"]),
        "is_a_bound":    True,
        "bound_reason": (
            "observed is not obligation; one country at one development level; "
            "and care has been MARKETISED out of unpaid time use, which moves "
            "the result in exactly this direction. The observed care share is "
            "therefore a LOWER bound on care's true share."
        ),
    }


def _spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation. n is 4 here, so this is a direction, not a p-value."""
    n = len(xs)
    rx = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: xs[i]))}
    ry = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: ys[i]))}
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def abatability_direction(
    start: int = 2003,
    end: int | None = None,
) -> dict:
    """
    Does `abatability` predict how each component moved over 22 years of capital
    deepening? Measured, not argued.

    Governing comparisons:

        change(c) = hours(c, end) / hours(c, start) − 1
        ρ_change  = Spearman(abatability, change)          a(K) predicts ρ < 0
        ρ_share   = Spearman(abatability, observed share)  Block II predicts ρ < 0

    units: dimensionless.

    WHAT IT FINDS (2003 → 2025, the shipped defaults). ρ_change is **+0.400**
    where a(K) predicts negative: nutrition — abatability 0.85, the second most
    abatable — ROSE **+33.7%**, while care, the LEAST abatable, fell **−20.7%**,
    the largest fall of the four. Block II's anti-correlation prediction is
    **−1.000** in the desk table (by construction — the table was built that way)
    and reads **+0.800** against observed shares.

    THIS DOES NOT REFUTE a(K), AND THE MODULE WILL NOT SAY THAT IT DOES. The
    mapped TOTAL moved −2.9% over the period, which is consistent with a(K)
    being SATURATED in a rich economy — where the predicted change is small
    anyway. What is not explained by saturation is the composition, and the
    marketisation confound reaches that directly. It is reported as an anomaly
    with a named alternative explanation, which is the honest state.
    """
    e = atus.latest_year() if end is None else end
    # Parallel typed lists alongside the report rows: the rows dict is
    # heterogeneous, so reading floats back out of it loses the type.
    names: list[str] = []
    ab: list[float] = []
    change: list[float] = []
    rows: list[dict] = []
    t0 = t1 = 0.0
    for c, codes in COMPONENT_CODES.items():
        h0 = atus.hours_per_person_15plus(start, codes)
        h1 = atus.hours_per_person_15plus(e, codes)
        a = float(PERSONAL_EOH_COMPONENTS[c]["abatability"])
        names.append(c)
        ab.append(a)
        change.append(h1 / h0 - 1.0)
        t0 += h0
        t1 += h1
        rows.append({
            "component":   c,
            "abatability": a,
            "hours_start": h0,
            "hours_end":   h1,
            "change":      h1 / h0 - 1.0,
        })
    obs = observed_shares(e)["shares"]
    return {
        "start": start, "end": e, "rows": rows,
        "mapped_total_start": t0,
        "mapped_total_end":   t1,
        "mapped_total_change": t1 / t0 - 1.0,
        "spearman_abatability_vs_change": _spearman(ab, change),
        "spearman_abatability_vs_desk_share": _spearman(
            ab, [float(PERSONAL_EOH_COMPONENTS[n]["share"]) for n in names]
        ),
        "spearman_abatability_vs_observed_share": _spearman(
            ab, [float(obs[n]) for n in names]
        ),
        "refutes_abatement": False,
        "note": (
            "The mapped total moved only -2.9%, which is consistent with a(K) "
            "being SATURATED in a rich economy. The composition is not explained "
            "by saturation, and care marketisation reaches it directly. Reported "
            "as an anomaly with a named alternative, not as a refutation."
        ),
    }


def phase_2_sensitivity(epsilon: float = 0.99, year: int | None = None) -> dict:
    """
    What the care share is worth to Phase 2's headline.

    Governing comparison, at automation level ε:

        f(share) = share·[c + (1 − c)(1 − ε)] + (1 − share)·(1 − ε)
        factor   = f(share) / (1 − ε)

    where c is `CARE_AUTOMATION_FLOOR`.

    units: dimensionless.

    Worked example (ε=0.99, 2025 default): at the desk share 62.1% the factor is
    10.22×; at the observed 25.7% it is 4.82×. **The finding survives the swap — it is
    order-of-magnitude-class either way — and its LEVEL does not.** Both are
    lower bounds, because the observed care share is itself one.

    Raises:
        ValueError: if epsilon is outside [0.0, 1.0].
    """
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError(f"epsilon must be in [0.0, 1.0], got {epsilon}")

    uniform = 1.0 - epsilon
    c = CARE_AUTOMATION_FLOOR

    def factor(share: float) -> float:
        f = share * (c + (1.0 - c) * uniform) + (1.0 - share) * uniform
        return f / uniform if uniform else float("inf")

    desk = float(PERSONAL_EOH_COMPONENTS["care"]["share"])
    seen = observed_shares(year)["shares"]["care"]
    return {
        "epsilon":            epsilon,
        "care_share_desk":     desk,
        "care_share_observed": seen,
        "factor_at_desk":      factor(desk),
        "factor_at_observed":  factor(seen),
        "survives_the_swap":   factor(seen) > 4.0,
        "note": (
            "Both are LOWER bounds: the observed care share is itself a lower "
            "bound, because marketised care leaves unpaid time use. The "
            "order-of-magnitude finding survives the swap; the level does not."
        ),
    }


def shares_report(year: int | None = None) -> dict:
    """The report. CLI: `eoh scenario run component_shares`."""
    cmp_ = share_comparison(year)
    direction = abatability_direction()
    sens = phase_2_sensitivity(0.99, year)
    return {
        "comparison":  cmp_,
        "direction":   direction,
        "sensitivity": sens,
        "mapping": {
            "components": COMPONENT_CODES,
            "excluded":   EXCLUDED_CODES,
            "overlap":    _OVERLAPPING,
        },
        "verdict": (
            f"ATUS {cmp_['year']} puts care at {cmp_['care_observed']:.1%} of "
            f"mapped personal time against a desk share of "
            f"{cmp_['care_desk']:.1%} — {cmp_['care_observed'] / cmp_['care_desk']:.2f}×. "
            f"Phase 2's factor at ε=0.99 moves "
            f"{sens['factor_at_desk']:.2f}× → {sens['factor_at_observed']:.2f}×, so the "
            f"order-of-magnitude finding survives and its level does not. This "
            f"is a BOUND, not a closure: observed is not obligation, it is one "
            f"country at one development level, and marketised care leaves "
            f"unpaid time use in exactly this direction. A cross-country "
            f"time-use panel (HETUS/MTUS) would settle the shares, the "
            f"abatabilities, K_half, the extraction wedge and the infant "
            f"age-weight band together."
        ),
        "reporting_only": True,
    }
