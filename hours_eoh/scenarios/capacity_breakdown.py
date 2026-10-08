"""
WHERE THE WORK GOES — the obligation broken down as a share of the hours people
can supply, at the survival and the sufficiency standard side by side.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. Nothing imports this; it reads the same accounts the compass
(`arc_stability.stability_at`) reads and splits them by component.

HOURS OF WORK, NOT CASH. Every figure here is TIME — hours of labour, paid or
unpaid, done by a household or bought — as a share of the labour CAPACITY of
the frame (adult capacity × the share of people able to supply it). It is not
a share of income and cannot be read as one: there is no price layer above the
floor in this repo (`research/desire.py` is a stub), so no currency enters.
A household budget divides cash by paid income; this divides hours of work by
hours available. The two answer different questions, and the second exists
whether or not anything is bought.

Each row is the HUMAN share of an obligation at the frame's ε — the machine
share is already removed — on the same split the pipeline uses:

    personal component c   share_c · personal · [ f_c + (1 − f_c)·(1 − ε) ]
    knowledge (civil.)     (1 − ε) · knowledge_civilisational
    infrastructure upkeep  (1 − ε) · infrastructure
    knowledge apparatus    (1 − ε) · knowledge_apparatus

divided by `labor_supply_per_capita`. The personal rows sum to
`personal_human_fraction(ε) · personal`, and the whole to the compass's
obligation + delivery; both identities are tested. The ecological STOCK is the
third account and is not counted, as in the compass — it is returned.

THE PERSONAL SPLIT IS NOT MEASURED, so it is reported two ways. `desk` is the
shipped `PERSONAL_EOH_COMPONENTS` (a placeholder: care 936/1508);
`observed` is ATUS time use (`component_shares.observed_shares`), which that
module documents as a BOUND, not a replacement — observed unpaid care
understates the care obligation in a rich country. The two disagree by ~2.4× on
care, and that disagreement is the error bar on the personal rows. The
collective rows and the total barely move between them.

THE STANDARD IS THE ONLY "SHOULD" HERE. Survival (600 h) and sufficiency
(1,500 h) are the autarky-referenced standards in `data.py`, the latter
`bounded` and erring HIGH; neither is a measured national standard.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.eoh_fulfillment import personal_human_fraction
from hours_eoh.core.eoh_generation import resolve_capital_stock
from hours_eoh.data import (
    CAPITAL_AGE_RATIO_DEFAULT,
    EPSILON_ARC_MAX,
    MEASURED_CAPACITY_H_YR,
    PERSONAL_AUTOMATION_FLOORS,
    PERSONAL_EOH_COMPONENTS,
    REFERENCE_FRAME_POPULATION,
    WEEKS_PER_YEAR,
)
from hours_eoh.scenarios.arc_stability import STANDARDS
from hours_eoh.scenarios.component_shares import observed_shares
from hours_eoh.scenarios.feasibility import labor_supply_per_capita
from hours_eoh.scenarios.obligation_accounts import obligation_accounts

__all__ = ["SHARE_SOURCES", "COLLECTIVE_ROWS", "breakdown_at", "capacity_report"]

#: Where the personal component shares come from — see the module docstring.
SHARE_SOURCES: tuple[str, ...] = ("desk", "observed")

#: The rows that are not personal, with the account each belongs to.
COLLECTIVE_ROWS: dict[str, str] = {
    "knowledge (civilisational)": "obligation",
    "infrastructure upkeep":      "delivery",
    "knowledge apparatus":        "delivery",
}


def _personal_shares(source: str) -> dict[str, float]:
    if source == "desk":
        return {c: float(s["share"]) for c, s in PERSONAL_EOH_COMPONENTS.items()}
    if source == "observed":
        return dict(observed_shares()["shares"])
    raise ValueError(f"shares must be one of {SHARE_SOURCES}, got {source!r}")


def breakdown_at(
    epsilon: float = 0.40,
    *,
    standard: str = "sufficiency",
    shares: str = "desk",
    population: float = REFERENCE_FRAME_POPULATION,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float | None = None,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    adult_share: float | None = None,
) -> dict:
    """
    The human hours of each obligation, as a share of labour capacity, at one ε
    and one standard.

    units: hours per person per year; shares dimensionless; `hours_per_adult_week`
    is the share times one adult's weekly capacity (`adult_capacity_h_yr /
    WEEKS_PER_YEAR`) — hours of work, never currency.

    ε-behaviour: every row's human share falls with ε; the personal rows with a
    floor (care, nutrition) fall slowest, so their share of the total RISES
    along the arc. Infrastructure upkeep follows the stock, which is the
    caller's (or the canonical arc's at ε when not supplied — and the result
    says which).

    Args:
        epsilon: Automation level [0.0, 0.99].
        standard: One of `arc_stability.STANDARDS`.
        shares: One of `SHARE_SOURCES` — the personal split.
        population: Frame population.
        capital_stock_teh: TOTAL stock; None resolves the canonical arc's.
        capital_age_ratio: Stock age over service life; None reads
            `CAPITAL_AGE_RATIO_DEFAULT`.
        adult_capacity_h_yr: Hours one adult can supply in a year.
        adult_share: Share of people able to supply it; None derives it from
            the shipped age weights (`labor_supply_per_capita`'s default).

    Raises:
        ValueError: on an ε, standard or share source out of range.
    """
    if not 0.0 <= epsilon <= EPSILON_ARC_MAX:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if standard not in STANDARDS:
        raise ValueError(f"standard must be one of {STANDARDS}, got {standard!r}")
    split = _personal_shares(shares)

    capital = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    age = CAPITAL_AGE_RATIO_DEFAULT if capital_age_ratio is None else capital_age_ratio
    acct = obligation_accounts(
        epsilon, population=population, personal_standard=standard,
        capital_stock=capital, capital_age_ratio=age,
    )
    supply = labor_supply_per_capita(adult_capacity_h_yr=adult_capacity_h_yr,
                                     adult_share=adult_share)
    week = adult_capacity_h_yr / WEEKS_PER_YEAR

    human = 1.0 - epsilon
    personal = acct["obligation_components"]["personal"] / population
    hours: dict[str, float] = {}
    for c in PERSONAL_EOH_COMPONENTS:
        f = PERSONAL_AUTOMATION_FLOORS.get(c, 0.0)
        hours[c] = split[c] * personal * (f + (1.0 - f) * human)
    hours["knowledge (civilisational)"] = (
        human * acct["obligation_components"]["knowledge_civilisational"] / population)
    hours["infrastructure upkeep"] = (
        human * acct["delivery_components"]["infrastructure"] / population)
    hours["knowledge apparatus"] = (
        human * acct["delivery_components"]["knowledge_apparatus"] / population)

    rows = [{
        "component": k,
        "account": COLLECTIVE_ROWS.get(k, "personal"),
        "hours_per_capita_yr": h,
        "share_of_capacity": h / supply,
        "hours_per_adult_week": h / supply * week,
    } for k, h in hours.items()]
    total = sum(hours.values())
    return {
        "epsilon": epsilon,
        "standard": standard,
        "shares": shares,
        "rows": rows,
        "total_hours_per_capita_yr": total,
        "total_share_of_capacity": total / supply,
        "total_hours_per_adult_week": total / supply * week,
        "within_capacity": total <= supply,
        "capacity_per_capita_yr": supply,
        "capacity_per_adult_week": week,
        "personal_human_fraction": personal_human_fraction(epsilon),
        "stock_not_counted_per_capita": acct["stock"] / population,
        "capital_stock_teh": capital,
        "capital_source": ("passed in by the caller" if capital_stock_teh is not None
                           else "NOT SUPPLIED — the canonical arc's stock at this ε and population"),
        "capital_age_ratio": age,
        "capital_age_source": ("passed in by the caller" if capital_age_ratio is not None
                               else "NOT SUPPLIED — CAPITAL_AGE_RATIO_DEFAULT"),
        "adult_share_source": ("passed in by the caller" if adult_share is not None
                               else "NOT SUPPLIED — the shipped age weights"),
        "units": "hours of work (paid or unpaid) as a share of labour capacity — no currency",
    }


def capacity_report(epsilon: float = 0.40, **kw: Any) -> dict:
    """
    Survival against sufficiency, under both personal splits. CLI:
    `eoh scenario run capacity_breakdown`.

    units: as `breakdown_at`. `added_by_sufficiency` is the sufficiency row
    minus the survival row — the work the higher standard adds — on the desk
    split; the collective rows add nothing, because the standard sets only the
    personal obligation.
    """
    runs = {(std, src): breakdown_at(epsilon, standard=std, shares=src, **kw)
            for std in STANDARDS for src in SHARE_SOURCES}
    surv, suff = runs[("survival", "desk")], runs[("sufficiency", "desk")]
    added = {a["component"]: b["hours_per_adult_week"] - a["hours_per_adult_week"]
             for a, b in zip(surv["rows"], suff["rows"])}

    def _within(r: dict) -> str:
        return "within" if r["within_capacity"] else "BEYOND"

    obs = runs[("sufficiency", "observed")]
    return {
        "epsilon": epsilon,
        "runs": runs,
        "added_by_sufficiency": added,
        "survival_within_capacity": surv["within_capacity"],
        "sufficiency_within_capacity": suff["within_capacity"],
        "verdict": (
            f"At ε={epsilon:.3f}, as hours of work against a capacity of "
            f"{suff['capacity_per_adult_week']:.1f} h per adult-week: survival takes "
            f"{surv['total_share_of_capacity']:.1%} ({_within(surv)} capacity), "
            f"sufficiency {suff['total_share_of_capacity']:.1%} ({_within(suff)}; "
            f"{obs['total_share_of_capacity']:.1%} on the ATUS split). Time only — "
            "no currency enters; the personal split is unmeasured, so read the "
            "desk and ATUS columns as its bracket."
        ),
        "reporting_only": True,
    }
