"""
What KIND of thing a(K) claims, per component — and how much of it is removal.

`abatement_fraction` reduces the personal obligation by a(K), and
`eoh_fulfillment` defines the field it is built from precisely: *"abatability is
the most infrastructure can REMOVE — a(K), ε-free by construction. This is who
does what REMAINS. They compose."* So the two fields are distinct and there is
no double-count with ε. What was never checked is whether the shipped
abatabilities MEASURE removal, and only removal justifies reducing the
obligation. Anything else shrinks the ledger for work still being done, which is
what the non-personal-only elimination invariant was written to prevent.

THREE KINDS, NOT TWO, and the third is the one that was missing from the
question as first posed:

  RELOCATION   the obligation moves domain. A pipe means nobody hauls, and the
               pipe must be maintained: personal EOH falls, infrastructure EOH
               rises, TOTAL is unchanged. No deflation. The entropy still has to
               be resisted; a different domain resists it.
  SUBSTITUTION a machine resists the same entropy. Total unchanged, human share
               falls. This is ε's channel, and counting it here would shrink an
               obligation that is still owed and still being met.
  REMOVAL      the entropy is not generated. Sanitation means the illness does
               not happen, so the care hours are never owed. Total EOH falls,
               and this is the ONLY kind that justifies a(K).

WHY THIS IS A JUDGEMENT AND SAYS SO. Nothing measures which kind a component's
abatability belongs to; the classification below is read off what the capital
physically does, stated per component so it can be argued with. It is therefore
reported as a BAND — the removal-justified a_max under the most and least
generous readings — and never as a point. A point here would be a fitted
constant wearing a measurement's clothes, which is the failure this module
exists to flag in someone else's constant.

A CROSS-COMPONENT EFFECT THE ADDITIVE BASKET CANNOT EXPRESS. Sanitation's
removal does not land on sanitation — it lands on health and care, whose hours
are never owed. The basket sums independent line items, so a component that
reduces ANOTHER component's quantity has nowhere to put it. Same shape as the
shelter/thermal substitution the 2026-09-04 merge fixed, and not fixed here.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.data import PERSONAL_EOH_COMPONENTS

#: What the capital physically does, per component. A JUDGEMENT, not a
#: measurement — each entry states the reading so it can be disputed.
ABATEMENT_KIND: dict[str, dict] = {
    "shelter": {
        "kinds": ("substitution", "removal"),
        "removal_is_certain": False,
        "why": (
            "Construction machinery is substitution — the building still gets "
            "built. Durability is removal: a dwelling that lasts a century "
            "instead of two decades genuinely owes fewer rebuild-hours per "
            "year. Both are present and nothing separates them."
        ),
    },
    "nutrition": {
        "kinds": ("substitution", "relocation"),
        "removal_is_certain": False,
        "why": (
            "A tractor does not reduce the entropy of growing food, it resists "
            "it with machine effort; a mill does not un-mill the grain. Piped "
            "water and grid power RELOCATE the obligation to infrastructure, "
            "which must then be maintained. Neither removes the requirement: "
            "the person still needs the kilocalories."
        ),
    },
    "health": {
        "kinds": ("removal", "substitution"),
        "removal_is_certain": True,
        "why": (
            "The one unambiguous case. Sanitation and immunisation mean the "
            "illness does not occur, so the hours are never owed by anyone — "
            "no machine resists that entropy, it is not generated. Diagnostic "
            "and surgical capital is substitution and sits alongside it."
        ),
    },
    "care": {
        "kinds": ("substitution",),
        "removal_is_certain": False,
        "why": (
            "A dependant needs the same attention; capital can supply it "
            "instead of a person, which is substitution. The only route to "
            "genuine removal is fewer dependent years — morbidity compression "
            "— and that is HEALTH's channel reaching care, not care's own. "
            "The additive basket cannot carry it."
        ),
    },
}


class RemovalBound(TypedDict):
    shipped_a_max: float
    removal_lower: float
    removal_upper: float
    shipped_over_lower: float
    certain_components: tuple[str, ...]
    verdict: str


def removal_bound() -> RemovalBound:
    """
    The band of a_max that REMOVAL supports, against the shipped a_max.

    upper — every abatability is removal. This is the shipped assumption, and
            stating it as an upper bound is the finding: a(K) currently takes
            the most generous reading available.
    lower — only components whose removal is unambiguous count.

    units: dimensionless, share of the personal obligation. ε-behaviour: none;
    abatability is ε-free by construction and so is this.
    """
    upper = sum(c["share"] * c["abatability"] for c in PERSONAL_EOH_COMPONENTS.values())
    certain = tuple(
        n for n, k in ABATEMENT_KIND.items() if k["removal_is_certain"]
    )
    lower = sum(
        PERSONAL_EOH_COMPONENTS[n]["share"] * PERSONAL_EOH_COMPONENTS[n]["abatability"]
        for n in certain
    )
    ratio = upper / lower if lower else float("inf")
    return {
        "shipped_a_max": upper,
        "removal_lower": lower,
        "removal_upper": upper,
        "shipped_over_lower": ratio,
        "certain_components": certain,
        "verdict": (
            f"a_max ships at {upper:.4f}, which assumes EVERY abatability is "
            f"removal. Only {', '.join(certain)} is unambiguously removal, "
            f"giving {lower:.4f} — the shipped value is {ratio:.1f}x the "
            "reading that is certain. Adopting abatement as the default "
            "generation path therefore reduces the obligation by up to "
            f"{ratio:.1f}x more than removal justifies, and the excess is work "
            "still being done — by machines under substitution, by another "
            "domain under relocation. That is the deflationary loop the "
            "non-personal-only elimination invariant was written to prevent, "
            "and it is not hypothetical at this spread."
        ),
    }


class RemovalConsequence(TypedDict):
    capital_per_capita: float
    a_max_shipped: float
    a_max_removal_only: float
    base_shipped: float
    base_removal_only: float
    per_capita_shipped: float
    per_capita_removal_only: float
    supply_per_capita: float
    covered_shipped: bool
    covered_removal_only: bool
    verdict: str


def removal_consequence(capital_per_capita_teh: float | None = None) -> RemovalConsequence:
    """
    What the two readings do to the abated base — the question that decides
    whether the deflation concern is real.

    THE RESULT, and it is why this module exists: the abatement path is
    FEASIBLE under the shipped a_max and INFEASIBLE under the removal-only
    one. So adopting abatement as the default generation path does not merely
    lower a number — it lowers it past the point where the labour supply can
    cover the obligation, and it gets there by counting substitution and
    relocation as removal.

    units: hours/year per working-age-equivalent, and per capita after w.
    ε-behaviour: none — a(K) is ε-free and so is this.
    """
    from hours_eoh.core.eoh_generation import abatement_fraction
    from hours_eoh.data import (
        CAPITAL_STOCK_DEFAULT, PERSONAL_EOH_SUFFICIENCY, REFERENCE_FRAME_POPULATION,
    )
    from hours_eoh.scenarios.feasibility import age_weight_mean, labor_supply_per_capita

    K = (CAPITAL_STOCK_DEFAULT / REFERENCE_FRAME_POPULATION
         if capital_per_capita_teh is None else capital_per_capita_teh)
    bound = removal_bound()
    w = age_weight_mean()
    supply = labor_supply_per_capita()

    def base(a_max: float) -> float:
        return PERSONAL_EOH_SUFFICIENCY * (1.0 - abatement_fraction(K, a_max=a_max))

    b_ship = base(bound["removal_upper"])
    b_rem = base(bound["removal_lower"])
    pc_ship, pc_rem = b_ship * w, b_rem * w
    return {
        "capital_per_capita": K,
        "a_max_shipped": bound["removal_upper"],
        "a_max_removal_only": bound["removal_lower"],
        "base_shipped": b_ship,
        "base_removal_only": b_rem,
        "per_capita_shipped": pc_ship,
        "per_capita_removal_only": pc_rem,
        "supply_per_capita": supply,
        "covered_shipped": pc_ship <= supply,
        "covered_removal_only": pc_rem <= supply,
        "verdict": (
            f"At K={K:,.0f} TEH/capita the abated base is {b_ship:,.0f} under the "
            f"shipped a_max and {b_rem:,.0f} under removal only — "
            f"{pc_ship:,.0f} against {pc_rem:,.0f} h/person·yr once age-weighted, "
            f"against a labour supply of {supply:,.0f}. The shipped reading "
            f"CLEARS; the removal-only reading DOES NOT. So the abatement path's "
            "feasibility rests on counting substitution and relocation as "
            "removal, and the over-determination does not disappear under "
            "abatement — it reappears the moment a(K) is held to its own "
            "definition."
        ),
    }
