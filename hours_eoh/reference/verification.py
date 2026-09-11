"""
The verification-cost census — what running an obligation register costs in labour.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. The anchor's comparative claim is that a registered-obligation
floor is more inspectable than geology, decree, protocol or credit. Two rivals
answer that by naming a cost this framework carries and they do not: gold's
advantage is "no registration apparatus, no assessors, no verification cost",
and a fixed-supply protocol needs no measurement of the world at all.

That cost is not merely unpriced in the prose. **It is absent from the model.**
No verification term exists in any of the four EOH domains; `core/registration`
returns shares admitted and never what admitting them costs; and the DELIVERY
account is `infrastructure + knowledge_apparatus`, neither of which is the
register. Meanwhile `core/multipliers.assess_tier` REQUIRES the apparatus —
three independent assessors, sortition, inter-rater reliability, a re-review
clock — and books zero EOH for all of it.

So the obligation is understated in the direction that flatters the framework,
on the one axis where its strongest rivals beat it. This module measures the
nearest thing that exists.

STRUCTURE, following `reference/servicing.py`'s discipline exactly:
  MEASURED   employment by occupation — BLS Employment Projections, via the
             `ep_employment_k` field of reference/data/multiplier_registry_v5.csv.
             Loaded through `servicing.load_registry_employment` rather than
             re-read here, so the two censuses cannot drift apart.
  ASSUMED    WHICH OCCUPATIONS VERIFY OBLIGATION. The one judgement, isolated in
             `VERIFICATION_ATTRIBUTIONS`, with every exclusion named and reasoned
             in `EXCLUDED_OCCUPATIONS` rather than filtered by a rule.
  ASSUMED    WHAT THE COST SCALES WITH. A second, separate judgement in
             `SCALING_BASIS`, never merged with the first — see below, because
             it is the design decision of the whole piece.

NO WEIGHTS AND NO FITTED PARAMETERS. `core` is the definitional set and is a
LOWER bound; `broad` adds every occupation arguably doing this work at its full
measured headcount and is an UPPER bound. Neither is a point estimate and there
is no coefficient anywhere to tune, which is deliberate: a weight chosen to land
the answer somewhere is the failure this repo names as calibrating to the target
you then check against.

THE ROLE-MIX TRAP, inherited from the parks finding and sharper here. A keyword
search for "inspector" returns `519061 Inspectors, Testers, Sorters, Samplers
and Weighers` (598.1k), which is manufacturing quality control and has nothing to
do with verifying an obligation. It is EXCLUDED BY NAME. `132011 Accountants and
Auditors` (1,652.6k) is the same hazard at ten times the scale: the SOC code
fuses preparing accounts with auditing them, and only the second is verification.

WHAT THIS CANNOT SETTLE, stated so nobody quotes it as more than it is: the US
has no HOURS register, so this measures TODAY'S apparatus as a proxy for one that
does not exist. That proxy errs in BOTH directions at once and the two are never
netted — see `direction_of_error()`.

REPORTING ONLY. Nothing here changes a shipped number, and nothing imports it.
The hours conversion and the account presentation are deliberately NOT here:
`reference/` returns workers, the scenario layer multiplies by
`hours_per_worker_year()`, exactly as `servicing.py` and `servicing_census.py`
divide the same work.

Layer: reference/ — pure data, imports nothing from the package outside
`reference/`.
"""

from __future__ import annotations

from typing import Mapping

from hours_eoh.reference.servicing import (
    SERVICING_ATTRIBUTIONS,
    load_registry_employment,
)

__all__ = [
    "VERIFICATION_ATTRIBUTIONS",
    "BROAD_SCOPE_ADDITIONS",
    "EXCLUDED_OCCUPATIONS",
    "SCALING_BASIS",
    "DISJOINT_FROM_SERVICING",
    "verification_workers",
    "direction_of_error",
    "what_this_cannot_settle",
]


#: Occupations whose work IS the determination of whether a claimed obligation
#: exists and whether it was met. Each names the register function it answers to.
#:
#: The test of membership is definitional, not statistical, and it mirrors the
#: one `servicing.py` uses: **would this occupation exist if nothing had to be
#: determined before it counted?** A compliance officer would not. A bookkeeper
#: would.
VERIFICATION_ATTRIBUTIONS: tuple[dict, ...] = (
    {
        "occ6": "131041", "function": "admission",
        "title": "Compliance Officers",
        "basis": (
            "Determines whether an activity conforms to a rule before it is "
            "recognised. That IS the registration decision — the boundary "
            "between obligation and mere activity."
        ),
    },
    {
        "occ6": "434061", "function": "admission",
        "title": "Eligibility Interviewers, Government Programs",
        "basis": (
            "Determines whether a claimant qualifies for a recognised "
            "entitlement. The closest existing analogue to admitting a personal "
            "obligation to a collective ledger, and the personal domain is the "
            "bulk of what a HOURS register would have to admit."
        ),
    },
    {
        "occ6": "131031", "function": "fulfilment_check",
        "title": "Claims Adjusters, Examiners, and Investigators",
        "basis": (
            "Determines whether a claimed event occurred and what discharging it "
            "costs. Verification of performance against a claim, which is the "
            "chain's middle link."
        ),
    },
    {
        "occ6": "132061", "function": "fulfilment_check",
        "title": "Financial Examiners",
        "basis": (
            "Verifies that reported accounts correspond to what actually "
            "happened. The audit function proper, as an occupation rather than "
            "as a fraction of one."
        ),
    },
    {
        "occ6": "132081", "function": "fulfilment_check",
        "title": "Tax Examiners and Collectors, and Revenue Agents",
        "basis": (
            "Verifies a self-reported quantity against an external standard. "
            "The self-reporting structure is the one a register inherits."
        ),
    },
    {
        "occ6": "231021", "function": "appeal",
        "title": "Administrative Law Judges, Adjudicators, and Hearing Officers",
        "basis": (
            "Appeal against refusal. A register with no appeal is a court with "
            "no defence, and a refused registration is a denial of income — so "
            "this is part of the apparatus, not an optional extra on it."
        ),
    },
    {
        "occ6": "152041", "function": "measurement",
        "title": "Statisticians",
        "basis": (
            "The measurement apparatus the register consumes. Obligation is "
            "derived from physical state, and somebody has to produce the state."
        ),
    },
    {
        "occ6": "193022", "function": "measurement",
        "title": "Survey Researchers",
        "basis": (
            "Same function, on the instrument this framework repeatedly finds it "
            "needs — a time-use survey is how three of its open constants would "
            "be settled."
        ),
    },
)


#: `broad` adds these at their FULL measured headcount. Each is arguably doing
#: this work and arguably not; including a fraction would require a weight
#: nothing measures, so the scope takes all of it and is read as an UPPER bound.
BROAD_SCOPE_ADDITIONS: tuple[dict, ...] = (
    {
        "occ6": "132011", "function": "fulfilment_check",
        "title": "Accountants and Auditors",
        "basis": (
            "The SOC code FUSES preparing accounts with auditing them, and only "
            "the second is verification. At 1,652.6k it dominates any total it "
            "enters, so it decides the answer by itself — which is exactly why "
            "it is quarantined in the upper bound instead of weighted into the "
            "middle."
        ),
    },
    {
        "occ6": "452011", "function": "fulfilment_check",
        "title": "Agricultural Inspectors",
        "basis": (
            "Verifies a physical condition against a standard, which is the "
            "shape of an ecological fulfilment check. Held out of `core` because "
            "the standard is a safety code rather than a registered obligation."
        ),
    },
    {
        "occ6": "536051", "function": "fulfilment_check",
        "title": "Transportation Inspectors",
        "basis": "Same reading, on infrastructure rather than on land.",
    },
    {
        "occ6": "332021", "function": "fulfilment_check",
        "title": "Fire Inspectors and Investigators",
        "basis": "Same reading, and the investigation half is closer than the inspection half.",
    },
)


#: Excluded BY NAME with the reason, never by a filter. Two of these are the
#: disjointness constraint against `servicing.py` and are not judgement calls at
#: all — counting them here would bill the same hours twice.
EXCLUDED_OCCUPATIONS: tuple[dict, ...] = (
    {
        "occ6": "519061", "title": "Inspectors, Testers, Sorters, Samplers, and Weighers",
        "reason": (
            "Manufacturing quality control. 598.1k of it, and a keyword search "
            "for 'inspector' returns it first — the same trap `servicing.py` "
            "names. It verifies PRODUCT against specification, not obligation "
            "against a register."
        ),
    },
    {
        "occ6": "474011", "title": "Construction and Building Inspectors",
        "reason": (
            "ALREADY COUNTED by `servicing.SERVICING_ATTRIBUTIONS` under "
            "`inspection`. Disjointness, not judgement: servicing charges the "
            "holder for it through GUF."
        ),
    },
    {
        "occ6": "232093", "title": "Title Examiners, Abstractors, and Searchers",
        "reason": (
            "ALREADY COUNTED by `servicing.SERVICING_ATTRIBUTIONS` under "
            "`dispute_resolution`. Same disjointness."
        ),
    },
    {
        "occ6": "439041", "title": "Insurance Claims and Policy Processing Clerks",
        "reason": (
            "Processes a determination somebody else made. The adjuster decides; "
            "this occupation records the decision. Including both would count "
            "one determination twice."
        ),
    },
    {
        "occ6": "434111", "title": "Interviewers, Except Eligibility and Loan",
        "reason": (
            "Market and survey interviewing with no entitlement decision "
            "attached. The eligibility half is admitted; this is the remainder "
            "and the SOC title says so."
        ),
    },
    {
        "occ6": "172111", "title": "Health and Safety Engineers",
        "reason": (
            "Designs the standard rather than checking compliance with it. "
            "Engineering, and it would be apparatus knowledge if anything."
        ),
    },
    {
        "occ6": "131032", "title": "Insurance Appraisers, Auto Damage",
        "reason": (
            "Values a loss in currency. A census route needs no valuation, and "
            "admitting a valuation occupation into the cost of a census would "
            "contradict the argument the census is there to support."
        ),
    },
)


#: THE DESIGN DECISION OF THE WHOLE PIECE, and a SEPARATE judgement from which
#: occupations qualify — the `servicing.SCALING_BASIS` discipline.
#:
#: Servicing scales with area, parcel count or throughput. Verification scales
#: with NONE of those. It follows the register's throughput: the count of
#: admission decisions plus the re-reviews the sunset clock forces.
#:
#: That matters twice. It is what makes this term disjoint from everything
#: area-scaled, which is most of what the framework already costs. And it sets
#: the ε-behaviour: the registered share of human EOH rises along the arc, so
#: more obligation is admitted, more fulfilment must be checked, and the cost
#: rises with the thing it serves. Whether it rises FASTER than the obligation
#: is the falsifiable question, and it is the scenario layer's to answer.
SCALING_BASIS: dict[str, str] = {
    "admission": (
        "registration decisions per period — the count of obligations admitted, "
        "not the hours they represent. A large obligation and a small one each "
        "cost one decision."
    ),
    "fulfilment_check": (
        "registered obligations per period, times the re-review frequency the "
        "sunset clock sets. This is the term that scales with the LEDGER rather "
        "than with the economy."
    ),
    "appeal": (
        "refusals and contested admissions per period — a fraction of admission "
        "volume, and the fraction is a governance parameter nobody has set."
    ),
    "measurement": (
        "physical state variables carried, times their measurement frequency. "
        "The only one that does NOT scale with the register's throughput, "
        "because the world must be measured whether or not anyone registers it."
    ),
}


#: Stated once, the way `servicing.DISJOINT_FROM_STEWARDSHIP` states its own.
DISJOINT_FROM_SERVICING: str = (
    "Servicing asks what the BUILT ENVIRONMENT costs to keep habitable — roads "
    "resurfaced, water delivered, buildings inspected, boundaries adjudicated — "
    "and is charged to the land holder through GUF. Verification asks what the "
    "REGISTER costs to run: deciding what counts, checking that it was done, and "
    "hearing the appeal. The two overlap on exactly two occupations, `474011` "
    "and `232093`, and both are excluded here by `occ6` with the reason, so the "
    "sets are disjoint by construction rather than by inspection. "
    "`test_verification_census` proves the intersection is empty."
)


def verification_workers(
    scope: str = "core",
    employment: Mapping[str, float] | None = None,
) -> dict:
    """
    Workers running the verification apparatus, by register function.

    Governing sum:

        core  : Σ over VERIFICATION_ATTRIBUTIONS of employment[occ]
        broad : core + Σ over BROAD_SCOPE_ADDITIONS of employment[occ]

    units: workers (headcount, not thousands).

    `core` is a LOWER bound and `broad` an UPPER bound; there is no weighted
    middle, because weighting `132011 Accountants and Auditors` would put a
    number nothing measures in front of the answer it decides.

    Returns the per-function breakdown, the total, and any attributed occupation
    the registry does not carry — reported, never silently dropped.

    Raises:
        ValueError: on an unknown scope, rather than silently returning `core`.
    """
    if scope not in ("core", "broad"):
        raise ValueError(f"scope must be 'core' or 'broad', got {scope!r}")

    emp = load_registry_employment() if employment is None else dict(employment)

    attributions = list(VERIFICATION_ATTRIBUTIONS)
    if scope == "broad":
        attributions += list(BROAD_SCOPE_ADDITIONS)

    by_function: dict[str, float] = {}
    missing: list[str] = []
    for att in attributions:
        occ = att["occ6"]
        if occ not in emp:
            missing.append(occ)
            continue
        by_function[att["function"]] = (
            by_function.get(att["function"], 0.0) + emp[occ] * 1_000.0
        )

    return {
        "scope":                 scope,
        "by_function":           by_function,
        "total_workers":         sum(by_function.values()),
        "occupations_counted":   len(attributions) - len(missing),
        "missing_from_registry": missing,
    }


def direction_of_error() -> dict:
    """
    Which way this census is wrong, stated in BOTH directions and never netted.

    The US has no HOURS register, so `verification_workers` measures today's
    compliance and audit apparatus as a proxy for one that does not exist. That
    proxy errs high and low simultaneously and which dominates is unknown. A
    single "best estimate" here would be a fitted answer wearing a measurement's
    tag, so this returns the two readings and no reconciliation.

    units: none — this returns the argument, not a number.
    """
    return {
        "over": (
            "Much of the US audit and compliance workforce verifies MONEY in an "
            "adversarial tax and legal environment. A register that verifies "
            "physical fulfilment against a stated obligation does not need most "
            "of that, and `131032` was excluded on precisely this ground."
        ),
        "under": (
            "A HOURS register admits personal EOH, which is the overwhelming "
            "majority of the obligation at low automation and still the largest "
            "domain at high automation — and almost none of it passes through "
            "any recorded channel today. NO existing apparatus has ever verified "
            "anything like that volume. And the shortfall is not that those "
            "occupations do not exist YET: verifying personal fulfilment means "
            "the person who did the care records that it happened, which is "
            "REGISTRANT-side labour and is nobody's occupation in any economy. "
            "An occupational census cannot reach it at any breadth — see "
            "`scope` and `what_this_cannot_settle`."
        ),
        "scope": (
            "BOTH scopes here are APPARATUS-side — people whose job is to "
            "verify. Neither reaches the party being verified. `core` and "
            "`broad` bound the apparatus, not the cost."
        ),
        "netted": None,
        "why_not_netted": (
            "The two are not opposite ends of one interval — they are errors in "
            "different quantities, one about the CONTENT of verification and one "
            "about its SCOPE. Combining them would invent a distribution nothing "
            "here measures."
        ),
    }


def what_this_cannot_settle() -> tuple[str, ...]:
    """
    The checker states its own gaps. An undocumented gap makes a measurement
    read as stronger than it is, which is the failure mode this repo names first.
    """
    return (
        "What a HOURS register would cost. This is the nearest existing "
        "apparatus, not the thing itself, and `direction_of_error()` says which "
        "ways that is wrong.",
        "Whether the cost is acceptable. `delivery_crossover`'s note is the "
        "precedent: exceeding the obligation is not by itself a failure "
        "condition, because it depends on how much the apparatus abates.",
        "The re-review frequency and the appeal rate, both of which "
        "`SCALING_BASIS` needs and neither of which any governance model here "
        "sets. Until they are set, the fulfilment-check and appeal terms scale "
        "with a parameter nobody has chosen.",
        "The audit fraction of `132011 Accountants and Auditors`. The gap "
        "between `core` and `broad` is mostly this one code, so the bound is "
        "wide for a single measurable reason rather than for a diffuse one.",
        "THE REGISTRANT SIDE — the largest gap, and it is STRUCTURAL rather "
        "than a shortfall of this census. Both scopes here are "
        "APPARATUS-side: they measure the people whose JOB is to verify. The "
        "hour a person spends recording that the care happened is not anyone's "
        "occupation, appears in no occupational classification, and no "
        "occupational census of any breadth can reach it. It scales with the "
        "volume of obligation rather than the size of any institution, which "
        "is the opposite basis from `SCALING_BASIS`. The one well-measured "
        "analogue — US federal tax compliance — runs an order of magnitude "
        "above the administering agency's own budget, so the direction is "
        "against the framework and the magnitude is unbounded here. The "
        "instrument is the Standard Cost Model (tariff x time x population x "
        "frequency), which measures the burden on the regulated party and is "
        "the complement of the Wallis & North occupational census this module "
        "runs, not a variant of it. Nothing here bounds it.",
    )


def _servicing_occupations() -> frozenset[str]:
    """The occ6 set `servicing.py` already counts. Used by the disjointness test."""
    return frozenset(str(a["occ6"]) for a in SERVICING_ATTRIBUTIONS)
