"""
The ten ratios, split the way the partition split the domain — REPORTING ONLY.

SPDX-License-Identifier: AGPL-3.0-or-later

THE PROBLEM. `GUF_USE_*` gives ten per-SLU coefficients indexed by USE CATEGORY.
They are `placeholder`, and the ×100 factor above them was reverse-engineered so
aggregate GUF matched levy revenue at mid-arc. Three things were known and none
of them settled the ratios:

  * the servicing census settles the LEVEL (~35× over in aggregate) and says so;
  * only **41.9%** of measured servicing hours scale with AREA — 44.5% follow
    parcel count and 13.6% throughput — while the fee is area-only, so
    `subdivision_invariance` returns the same fee to the float after splitting
    every parcel in two;
  * the two measured orderings available (the stewardship census's 27×
    disturbance gradient, and ρ) both measure DISTURBANCE, whereas U was defined
    as SERVICING. Adopting either would repeat the `SKILL_WORKING_LIFE_YEARS`
    wrong-instrument error.

WHAT CHANGED, AND WHY THE THIRD OBJECTION NO LONGER BINDS. Phases 4d/4e/4f moved
the recurring ECOLOGICAL obligation to GUF. U therefore no longer carries
servicing alone — it carries a disturbance component too, and for THAT component
a disturbance-measured ordering is the right instrument rather than the wrong
one. The objection was correct when written and the partition retired it.

THE MOVE IS THE ONE THAT WORKED ON THE DOMAIN: decompose first, then assign.
Phase 4e split `rate/health` into `standing + degradation_response` — an exact
identity that moved no number — and only then asked which side each belonged to.
This does the same to U:

    U(c)  =  U_servicing(c)  +  U_stewardship(c)  +  U_policy(c)

  U_servicing    what the BUILT ENVIRONMENT demands. Measured by
                 `scenarios/servicing_census`, and it has THREE scaling bases,
                 only one of which the fee can currently express.
  U_stewardship  what the LAND demands given its disturbance. ρ
                 (`GUF_SERVICE_RETENTION_BY_USE`) measures it and — crucially —
                 is already indexed BY USE CATEGORY, the same index as the fee
                 table, not by land class. That is the bridge the land-class
                 censuses could not provide.
  U_policy       the residual: luxury, land-banking and institutional
                 judgements. `normative`, and declared as such rather than
                 hiding inside a number that looks measured.

THE RESIDUAL IS THE FINDING, NOT AN ERROR TERM. Ranking the ten categories by
disturbance (1−ρ) and by fee gives a Spearman correlation of **0.891** — most of
U is disturbance — with four categories off by two ranks, and those four are
legible: `residential_secondary` and `agricultural_fallow` are charged ABOVE
their disturbance (a luxury and a land-banking judgement), `institutional` and
`industrial_light` BELOW it (social relief). U conflates a measured physical
ordering with unmeasured policy, and naming the second is what lets the first be
measured.

REPORTING ONLY. No coefficient moves; `TestUSplitChangesNothing` fails the
moment that stops being true. What this reports is what a split WOULD imply, so
the charter decision can be taken against numbers rather than against intuition.

WHAT IT STILL CANNOT SETTLE, stated so the module is not read as more than it
is: the per-parcel term needs a national PARCEL COUNT, which this package does
not ship (`PARCEL_COUNT_RESOLVES_BY` names assessor parcel rolls, and explicitly
NOT a housing-unit count — a multi-unit building is one parcel and many units).
Until that lands, `U_servicing` is measurable only in its area component, which
is 41.9% of it.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.data import (
    GUF_SERVICE_RETENTION_BY_USE,
    GUF_USE_AGRICULTURAL_ACTIVE,
    GUF_USE_AGRICULTURAL_FALLOW,
    GUF_USE_COMMERCIAL_OFFICE,
    GUF_USE_COMMERCIAL_RETAIL,
    GUF_USE_CONSERVATION_CREDIT,
    GUF_USE_INDUSTRIAL_HEAVY,
    GUF_USE_INDUSTRIAL_LIGHT,
    GUF_USE_INSTITUTIONAL,
    GUF_USE_RESIDENTIAL_PRIMARY,
    GUF_USE_RESIDENTIAL_SECONDARY,
)
from hours_eoh.reference.servicing import workers_by_scaling_basis

__all__ = [
    "SHIPPED_U",
    "disturbance_by_use",
    "rank_disagreement",
    "scaling_basis_gap",
    "split_report",
]

#: The shipped coefficients, bound rather than restated. A second copy of a
#: value whose source is elsewhere is the pattern this repo has found five
#: times; binding means this module cannot drift from `data.py`.
SHIPPED_U: dict[str, float] = {
    "residential_primary":   GUF_USE_RESIDENTIAL_PRIMARY,
    "residential_secondary": GUF_USE_RESIDENTIAL_SECONDARY,
    "agricultural_active":   GUF_USE_AGRICULTURAL_ACTIVE,
    "agricultural_fallow":   GUF_USE_AGRICULTURAL_FALLOW,
    "commercial_retail":     GUF_USE_COMMERCIAL_RETAIL,
    "commercial_office":     GUF_USE_COMMERCIAL_OFFICE,
    "industrial_light":      GUF_USE_INDUSTRIAL_LIGHT,
    "industrial_heavy":      GUF_USE_INDUSTRIAL_HEAVY,
    "institutional":         GUF_USE_INSTITUTIONAL,
    "conservation":          GUF_USE_CONSERVATION_CREDIT,
}


def disturbance_by_use() -> dict[str, float]:
    """
    Disturbance per use category, as 1 − ρ.

    Governing equation:

        disturbance(c) = 1 − ρ(c)          [dimensionless, 0 = pristine]

    ρ is the fraction of natural service a developed parcel still delivers
    (`GUF_SERVICE_RETENTION_BY_USE`, NLSA Eq. 14). Its `resolves_by` names NLCD
    Percent Developed Imperviousness — measured, gridded, and already aligned to
    land class.

    THE PROPERTY THAT MATTERS HERE IS THE INDEX, NOT THE VALUES. Both censuses
    aggregate over LAND CLASSES and the fee table is indexed by USE CATEGORY,
    which is why neither could settle the ratios. ρ is indexed by use category,
    so it can be compared to U row for row.

    units: dimensionless. Worked example: `industrial_heavy` ρ=0.02 → 0.98;
    `conservation` ρ=0.95 → 0.05.
    """
    return {c: 1.0 - r for c, r in GUF_SERVICE_RETENTION_BY_USE.items()}


def rank_disagreement() -> dict[str, Any]:
    """
    Where the fee ordering and the disturbance ordering disagree, and by how much.

    Governing statistic — Spearman's rank correlation over the ten categories:

        ρ_s = 1 − 6·Σd² / (n(n²−1))          n = 10

    Returns the coefficient plus a per-category rank gap. A category whose fee
    rank is BELOW its disturbance rank is charged more than disturbance alone
    would warrant; above, less.

    THE DISAGREEMENTS ARE THE POINT. ρ_s ≈ 0.89 says most of U is disturbance.
    The four categories off by two ranks are where a policy judgement has been
    layered on top, and they are legible as such — which is what makes the
    residual `normative` rather than noise.
    """
    dist = disturbance_by_use()
    fee = {c: v for c, v in SHIPPED_U.items() if c in dist}
    d_rank = {c: i for i, c in enumerate(sorted(fee, key=lambda k: -dist[k]))}
    f_rank = {c: i for i, c in enumerate(sorted(fee, key=lambda k: -fee[k]))}

    rows: list[dict[str, Any]] = []
    for c in sorted(fee, key=lambda k: -abs(f_rank[k] - d_rank[k])):
        gap = f_rank[c] - d_rank[c]
        rows.append({
            "use_category":     c,
            "disturbance":      dist[c],
            "shipped_u":        fee[c],
            "disturbance_rank": d_rank[c],
            "fee_rank":         f_rank[c],
            "rank_gap":         gap,
            # A negative gap means the fee ranks HIGHER (a lower index) than
            # disturbance — charged above what disturbance alone warrants.
            "reading": ("charged ABOVE its disturbance" if gap < 0
                        else "charged BELOW its disturbance" if gap > 0
                        else "agrees"),
        })
    n = len(rows)
    ssd = sum(int(r["rank_gap"]) ** 2 for r in rows)
    spearman = 1.0 - 6.0 * ssd / (n * (n * n - 1))
    return {
        "n": n,
        "spearman": spearman,
        "rows": rows,
        "disagreements": [r for r in rows if abs(int(r["rank_gap"])) >= 2],
    }


def scaling_basis_gap() -> dict[str, Any]:
    """
    How much of the measured servicing cost the fee's single basis can express.

    `A(p)` is in Standard Land Units — an AREA unit — so `base_fee` is
    proportional to ground area and to nothing else. Re-cutting the servicing
    census by what each occupation's cost actually follows gives three bases,
    and the fee can express one.

    THE FALSIFICATION IS ALREADY RUN ELSEWHERE: `guf_magnitude.subdivision_
    invariance` splits every parcel in two and gets the same fee back to the
    float, at every ε. Parcel count does not enter the fee at all.

    units: fractions of measured servicing workers.
    """
    w = workers_by_scaling_basis()
    shares = w["shares"]
    expressible = shares["area"]
    return {
        "shares":            shares,
        "expressible_now":   expressible,
        "inexpressible":     1.0 - expressible,
        "total_workers":     w["total_workers"],
        "verdict": (
            f"the fee has ONE scaling basis and the measured cost has three: "
            f"area {shares['area']:.1%}, parcel {shares['parcel']:.1%}, "
            f"throughput {shares['throughput']:.1%}. A per-SLU coefficient can "
            f"express {expressible:.1%} of it, so no value of GUF_USE_SCALE_FACTOR "
            f"— and no re-cut of the ten ratios — closes the remaining "
            f"{1 - expressible:.1%}. That needs a per-parcel TERM, which the fee "
            f"does not have: subdivision_invariance returns the same fee after "
            f"splitting every parcel in two."
        ),
    }


def split_report() -> dict[str, Any]:
    """
    The proposed decomposition, with what is measured and what is not.

    REPORTING ONLY — no coefficient moves. This states what a split would imply
    so the charter decision is taken against numbers.
    """
    ranks = rank_disagreement()
    basis = scaling_basis_gap()
    return {
        "scenario": "use_split",
        "shipped_u": dict(SHIPPED_U),
        "disturbance": disturbance_by_use(),
        "ranks": ranks,
        "basis": basis,
        "terms": {
            "U_servicing": (
                "what the BUILT ENVIRONMENT demands. Measured by "
                "scenarios/servicing_census at 45.92 h/ha·yr over 37.1 Mha. "
                f"Only {basis['expressible_now']:.1%} of it scales with area, so "
                "the fee needs a per-parcel term it does not have."
            ),
            "U_stewardship": (
                "what the LAND demands given its disturbance. ρ measures it and "
                "is indexed BY USE CATEGORY — the same index as the fee table — "
                "which is the bridge the land-class censuses could not provide. "
                "After Phases 4d/4e/4f, U carries the relocated recurring "
                "ecological obligation, so a disturbance instrument is the RIGHT "
                "one for this component rather than the wrong one."
            ),
            "U_policy": (
                "the residual, and it is a finding rather than an error term: "
                f"Spearman {ranks['spearman']:.3f} between the fee and "
                "disturbance orderings, with "
                f"{len(ranks['disagreements'])} categories off by two ranks — "
                "luxury and land-banking charged above, institutional relief "
                "below. NORMATIVE, and declared as such rather than hiding "
                "inside a number that looks measured."
            ),
        },
        "verdict": (
            f"U conflates a MEASURED physical ordering with UNMEASURED policy. "
            f"Spearman {ranks['spearman']:.3f} says most of it is disturbance, and "
            f"ρ is indexed the same way the fee table is — so the wrong-instrument "
            f"objection that blocked this dissolves by SPLITTING the term rather "
            f"than by finding new data, which is the move that worked on the "
            f"ecological domain. What a split does NOT close is the scaling basis: "
            f"{basis['inexpressible']:.1%} of the measured servicing cost follows "
            f"parcel count and throughput, and the fee has no term for either. "
            f"REPORTING ONLY — nothing here moves a coefficient."
        ),
    }
