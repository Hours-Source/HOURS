"""
The food conservation test — did automation ELIMINATE food labour, or relocate it?

The handoff calls this "the single highest-value test now available", and it is
the sharpest test the framework has of its own central claim. Automation is
supposed to reduce entropy obligations, not merely move who discharges them. Food
is where that can be checked, because both ends of the ε arc are measured on
comparable units: LSMS-ISA gives unassisted smallholder cultivation at ε ≈ 0.05,
ATUS plus the O*NET/BLS registry give the US at ε ≈ 0.9.

THE TRAP, AND WHY A SINGLE TOTAL IS THE WRONG INSTRUMENT
---------------------------------------------------------
In the US, personal EOH did not disappear — most of it moved onto the registered
ledger. A US household spends well under an hour a day preparing food because
farming, milling, transport and most processing happen inside paid employment.
Reading ATUS household time alone as "US food EOH" would understate it enormously
and manufacture a spuriously steep P(ε). So the registered term must be added:

    H_food_total(ε) = unpaid household food time + food-system employment ÷ population

The first version of this test compared that total against the LSMS figure and
called the result ambiguous. **That was the wrong comparison**, because the LSMS
number covers PRODUCTION ONLY and the US total covers production, processing and
service. Compared stage by stage the answer is not ambiguous at all, and it is
not the same answer at every stage — which is the actual finding.

WHAT IS COUNTED, AND WHAT IS NOT
---------------------------------
The paid term is a strict LOWER BOUND, and knowing that is what makes the result
usable. Counted: agriculture (SOC 45 less forestry and logging), food processing
(SOC 51-3), food preparation and serving (SOC 35). Not counted, for want of
industry-level data this repo does not carry: food wholesale and retail, food
transport, food manufacturing outside 51-3, packaging, and the agricultural input
industries. **And OEWS excludes the self-employed**, so proprietor farmers are
missing entirely — against ~919k counted wage-and-salary agricultural workers that
is a large omission pointing one way.

Every uncounted term RAISES the US number. `uncounted_headroom()` converts that
from a caveat into a quantity.

THE CONFOUND THAT REMAINS
--------------------------
The baskets are not held fixed. The US food basket carries variety, year-round
availability, food safety regulation and out-of-home service that the LSMS basket
does not. Equal hours therefore do not mean equal output, and this test cannot
settle whether the extra hours buy extra sufficiency or are the extraction term
by another name. Handoff open decision #1 governs; nothing here resolves it.

The LSMS side is also climate-specific — rainfed tropical smallholder cultivation,
seven Sub-Saharan countries. See `reference/personal_basket.LSMS_AGRO_ECOLOGY`.

Layer: scenarios/ imports reference/ only — pure, no I/O beyond shipped extracts.

ε-coherence: this is a two-point comparison between measured epochs, not a
function of ε. It is deliberately NOT dressed as an arc: there is no measurement
between ε ≈ 0.05 and ε ≈ 0.9, and interpolating would invent one.

Reference: handoffs/personal_eoh/HANDOFF_personal_eoh_base.md §2, §3.3, §3.5;
notes/personal-eoh-floor.md Finding D.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.data import BASKET_DIET_KCAL_PER_DAY
from hours_eoh.reference import atus_time_use
from hours_eoh.reference.onet_multipliers import load_registry
from hours_eoh.reference.personal_basket import (
    DIET_DAYS_PER_YEAR,
    NUTRITION_CROSSCHECK_HOURS_PER_YEAR,
    NUTRITION_HOURS_PER_KCAL,
)
from hours_eoh.scenarios.knowledge_base import (
    REGISTRY_EMPLOYMENT_COVERAGE,
    REFERENCE_POPULATION_US,
)

#: Unassisted crop-PRODUCTION labour, h/person·yr, at ε ≈ 0.05.
#:
#: DERIVED, NOT RESTATED (2026-08-28). This was the bare literal `320.0` — a
#: THIRD number for a quantity `reference/personal_basket` already measures. Its
#: own docstring cited both routes ("331 kcal-chain, 306 observed-labour") and
#: then stated a value that is neither, and is not their midpoint (318.46)
#: either. It is now the kcal chain itself:
#:
#:     diet_kcal/day × days/yr × hours/kcal
#:
#: so it cannot drift from the basket that supplies the same figure to the
#: personal floor. It moves 320.0 → 330.9233 (+3.3%).
#:
#: THE MOVE COST NOTHING AND THAT IS THE FINDING: a 3.3% change to the constant
#: anchoring this module's entire conservation result failed ZERO tests. The
#: production-collapse ratio is now pinned, and pinned across the whole measured
#: band rather than at one route — see TestTheProductionCollapseIsRobust.
#:
#: PRODUCTION ONLY — it excludes processing, and every known bias in it runs
#: upward. The 7.6% spread between the two routes is NOT a climate error bar:
#: both are computed from the same seven countries.
LSMS_CROP_PRODUCTION_HOURS: float = (
    BASKET_DIET_KCAL_PER_DAY * DIET_DAYS_PER_YEAR * NUTRITION_HOURS_PER_KCAL
)

#: The measured band for the quantity above: the observed-labour cross-check at
#: one end, the kcal chain at the other. Carried so a result can be reported
#: across the band instead of resting on whichever route was picked.
LSMS_CROP_PRODUCTION_BAND: tuple[float, float] = (
    NUTRITION_CROSSCHECK_HOURS_PER_YEAR,
    LSMS_CROP_PRODUCTION_HOURS,
)

#: LSMS processing labour: threshing, milling, fuel gathering, water for cooking,
#: cooking. NOT MEASURED — the binding unknown, and the entire difference between
#: the handoff's 700 and 1,400 h/person·yr recommendation for the survival core.
#: In hand-powered systems it plausibly EXCEEDS production labour. None, not 0.0:
#: an unmeasured term is not a zero term.
LSMS_PROCESSING_HOURS: float | None = None

#: SOC major-group prefixes by food-system stage. Agriculture deliberately
#: excludes 45-4 (forest, conservation, logging) — forestry is not food.
SOC_AGRICULTURE: tuple[str, ...] = ("451", "452", "453")
SOC_FOOD_PROCESSING: tuple[str, ...] = ("513",)
SOC_FOOD_SERVICE: tuple[str, ...] = ("35",)

#: Food-system employment this repo cannot count, each with the direction it
#: would move the US total. All of them raise it.
UNCOUNTED_SECTORS: dict[str, str] = {
    "self_employed_farmers": (
        "OEWS covers wage-and-salary employment only. Proprietor farmers are "
        "absent entirely, against ~919k counted agricultural workers — the "
        "single largest omission, and it is in the stage where the US number is "
        "smallest."
    ),
    "food_wholesale_retail": (
        "Grocery employment sits in SOC 41 (sales) and 43 (office/admin), which "
        "cannot be split by industry from an occupation registry."
    ),
    "food_transport": "SOC 53, not separable by commodity.",
    "food_manufacturing_outside_513": (
        "Packaging, machine operation and maintenance in food plants sit in "
        "51-9 and 49, not separable by industry."
    ),
    "agricultural_inputs": "Fertiliser, machinery, seed — upstream of SOC 45.",
}


class Stage(TypedDict):
    stage: str
    lsms_hours: float | None
    us_paid_hours: float
    us_unpaid_hours: float
    us_total_hours: float
    ratio_us_to_lsms: float | None


class ConservationReport(TypedDict):
    year: int
    hours_per_worker_year: float
    stages: list[Stage]
    lsms_total_measured: float
    us_total: float
    us_total_is_lower_bound: bool
    production_ratio: float
    verdict: str
    caveat: str


def hours_per_worker_year(year: int | None = None) -> float:
    """
    Average paid hours per worker per year — DERIVED, not chosen.

    Governing equation:

        h_worker = (paid hours per person 15+ × population_15_plus)
                   / total employment

    where the numerator is the 15+ paid-hours AGGREGATE and total employment is
    the registry's covered employment grossed up by
    `REGISTRY_EMPLOYMENT_COVERAGE`. Both sides are measured, so no annual-hours
    convention is imported.

    units: hours per worker per year.

    Worked example: 2025 — 2,258.4 h/person15+·yr × 278.0M ÷ 334.9M workers…
    resolving to **1,874.4284 h/worker·yr**. A chosen 1,800 would have been
    defensible and is not needed.

    IT NO LONGER TAKES A POPULATION, AND THAT IS A FIX (2026-08-31). It used to
    accept `total_population`, convert the 15+ hours DOWN to a per-capita figure
    with it, and then multiply the same population back in — a round trip that
    cancelled exactly. The answer was 1,874.4284 at every population, so a caller
    reframing to another country got the same number while believing they had
    reframed it: the frame-seam shape this repo has found seven times. Found by
    `tests/test_parameter_wiring`; the value is unchanged, because a cancelling
    parameter cannot have been affecting it.

    THE FRAME IS NOW WHERE IT BELONGS. This ratio is population-free by
    construction — hours per worker does not depend on how many non-workers
    there are. Callers that need a PER-CAPITA figure still divide by their own
    `total_population`, which is live and stays.

    Raises:
        ValueError: if the registry reports non-positive employment.
        KeyError: if `year` is not an ATUS survey year.
    """
    y = atus_time_use.latest_year() if year is None else year
    paid_15plus_total = (
        atus_time_use.hours_per_person_15plus(y, ("05",))
        * atus_time_use.population_15_plus(y)
    )
    covered = sum(row["employment_k"] for row in load_registry()) * 1_000.0
    total_employment = covered / REGISTRY_EMPLOYMENT_COVERAGE
    if total_employment <= 0.0:
        raise ValueError("registry reports non-positive employment")
    return paid_15plus_total / total_employment


def food_system_employment() -> dict[str, float]:
    """
    Counted food-system employment by stage, in workers.

    units: workers (the registry stores thousands; this returns headcount).

    Worked example: agriculture 919.5k, processing 869.9k, service 14,173.8k —
    and the ordering is itself the finding: the US employs fifteen times as many
    people serving food as growing it.
    """
    rows = load_registry()

    def total(prefixes: tuple[str, ...]) -> float:
        return sum(
            row["employment_k"] * 1_000.0
            for row in rows
            if any(row["occ6"].startswith(p) for p in prefixes)
        )

    return {
        "production": total(SOC_AGRICULTURE),
        "processing": total(SOC_FOOD_PROCESSING),
        "service": total(SOC_FOOD_SERVICE),
    }


def unpaid_food_hours(
    year: int | None = None,
    total_population: float = REFERENCE_POPULATION_US,
) -> dict[str, float]:
    """
    Measured US unpaid food labour per capita, by stage.

    ATUS 0202 (food and drink preparation, presentation, cleanup) is the
    processing analogue; 0701 (grocery shopping) is provisioning — the US
    analogue of gathering. Nothing maps to production: US households do not grow
    food in measurable quantity, which is itself the result.

    units: hours per capita (ALL ages) per year.

    Worked example: 2025 → processing 215.6, provisioning 90.4, production 0.0.
    """
    year = atus_time_use.latest_year() if year is None else year
    return {
        "production": 0.0,
        "processing": atus_time_use.hours_per_capita(year, ("0202",), total_population),
        "service": atus_time_use.hours_per_capita(year, ("0701",), total_population),
    }


def conservation_test(
    year: int | None = None,
    total_population: float = REFERENCE_POPULATION_US,
) -> ConservationReport:
    """
    THE TEST, stage by stage — the handoff's §3.3, done at the granularity the
    data supports.

    Governing equation, per stage:

        US_total = paid_employment × hours_per_worker / population  +  unpaid_ATUS

    compared against the LSMS ε ≈ 0.05 figure for the same stage.

    units: hours per capita per year throughout.

    ε-behavior: none by construction — two measured epochs, no interpolation.

    Worked example (2025): production collapses 320 → 5.1 h/person·yr, a 62×
    reduction that is robust to every uncounted term. Processing and service do
    not collapse: they run 220.5 and 166.6 h/person·yr against an LSMS
    processing term nobody has measured. The totals end up comparable, and the
    single-total reading of that ("ambiguous") hides a stage-level answer that
    is not ambiguous at all.
    """
    year = atus_time_use.latest_year() if year is None else year
    per_worker = hours_per_worker_year(year)
    employment = food_system_employment()
    unpaid = unpaid_food_hours(year, total_population)
    lsms = {
        "production": LSMS_CROP_PRODUCTION_HOURS,
        "processing": LSMS_PROCESSING_HOURS,
        "service": 0.0,
    }

    stages: list[Stage] = []
    for name in ("production", "processing", "service"):
        paid = employment[name] * per_worker / total_population
        total = paid + unpaid[name]
        reference = lsms[name]
        stages.append(Stage(
            stage=name,
            lsms_hours=reference,
            us_paid_hours=paid,
            us_unpaid_hours=unpaid[name],
            us_total_hours=total,
            ratio_us_to_lsms=(total / reference if reference else None),
        ))

    us_total = sum(s["us_total_hours"] for s in stages)
    production = next(s for s in stages if s["stage"] == "production")
    production_ratio = production["us_total_hours"] / LSMS_CROP_PRODUCTION_HOURS

    return ConservationReport(
        year=year,
        hours_per_worker_year=per_worker,
        stages=stages,
        lsms_total_measured=LSMS_CROP_PRODUCTION_HOURS,
        us_total=us_total,
        us_total_is_lower_bound=True,
        production_ratio=production_ratio,
        verdict=(
            f"PRODUCTION labour collapsed {1.0 / production_ratio:.0f}x "
            f"({LSMS_CROP_PRODUCTION_HOURS:.0f} → "
            f"{production['us_total_hours']:.1f} h/person·yr) and the direction "
            f"is robust — every uncounted term raises the US side and it is "
            f"still two orders below. PREPARATION did not: it runs "
            f"{stages[1]['us_total_hours']:.0f} h/person·yr against an LSMS "
            f"processing term nobody has measured. The framework's claim holds "
            f"where automation had something physical to automate and is "
            f"unsupported where the work is preparation and service — which is "
            f"the same split the 2003–2025 ATUS series shows independently "
            f"(food prep +34%, grocery −26%)."
        ),
        caveat=(
            "US total is a LOWER BOUND (uncounted sectors, self-employed farmers "
            "excluded from OEWS); the LSMS total is ALSO a lower bound (no "
            "processing term). The baskets are not held fixed, so equal hours do "
            "not mean equal output — that confound is why the TOTALS cannot "
            "settle the question and the STAGES can."
        ),
    )


def uncounted_headroom(
    employment_share: float = 0.01,
    year: int | None = None,
    total_population: float = REFERENCE_POPULATION_US,
) -> dict:
    """
    What each uncounted slice of employment would add to the US total.

    Turns "we are missing sectors" from a caveat into a quantity: how many
    h/person·yr does one percent of total employment carry? Anyone who thinks a
    missing sector matters can price their own estimate of it.

    units: hours per capita per year, per unit of employment share.

    Worked example: 1% of US employment ≈ 1.675M workers ≈ 9.4 h/person·yr — so
    the entire uncounted food-system tail would have to exceed ~34% of national
    employment to close the production gap, which it plainly does not.
    """
    if not 0.0 <= employment_share <= 1.0:
        raise ValueError(f"employment_share must be in [0, 1], got {employment_share}")
    per_worker = hours_per_worker_year(year)
    covered = sum(row["employment_k"] for row in load_registry()) * 1_000.0
    total_employment = covered / REGISTRY_EMPLOYMENT_COVERAGE
    per_point = employment_share * total_employment * per_worker / total_population
    return {
        "employment_share": employment_share,
        "workers": employment_share * total_employment,
        "hours_per_capita": per_point,
        "uncounted_sectors": UNCOUNTED_SECTORS,
        "note": (
            f"{employment_share:.1%} of employment carries "
            f"{per_point:.1f} h/person·yr. Compare against the production gap of "
            f"{LSMS_CROP_PRODUCTION_HOURS:.0f} h/person·yr: the uncounted tail "
            f"cannot close it."
        ),
    }


def unpaid_food_series() -> dict:
    """
    The 2003–2025 unpaid side, which is the half of this test that moves.

    THE PAID TERM CANNOT MOVE HERE. The registry is a single frozen epoch (BLS EP
    2024–2034), so a time series of the full test is not available and is not
    faked: only the ATUS side is a series, and it is returned as one.

    units: hours **per person aged 15+** per year — the ATUS native unit, NOT per
    capita. This is deliberate and it is a trap worth naming. Converting a
    historical series to per capita needs a matching total-population series, and
    this repo carries only `REFERENCE_POPULATION_US`, a single recent figure.
    Holding that fixed across the window silently divides by a constant while the
    15+ population grows 225.3M → 278.0M, which alone manufactures a spurious
    +23% and turned a measured −26% into −8%. Everything else in this module is
    per capita because it is evaluated at ONE year, where the bridge is valid.

    ε-behavior: none — calendar time, not the arc.

    Worked example: preparation rises 194.3 → 259.8 h/person15+·yr while
    provisioning falls 146.4 → 108.9. Automation reached the shopping trip and
    not the meal.
    """
    prep = atus_time_use.series(("0202",))
    shop = atus_time_use.series(("0701",))
    rows = [
        {
            "year": year,
            "preparation": prep[year],
            "provisioning": shop[year],
            "total": prep[year] + shop[year],
        }
        for year in sorted(prep)
    ]
    first, last = rows[0], rows[-1]
    return {
        "rows": rows,
        "preparation_change": last["preparation"] / first["preparation"] - 1.0,
        "provisioning_change": last["provisioning"] / first["provisioning"] - 1.0,
        "paid_term_is_epoch_frozen": True,
        "note": (
            f"preparation {last['preparation'] / first['preparation'] - 1.0:+.1%}, "
            f"provisioning {last['provisioning'] / first['provisioning'] - 1.0:+.1%} "
            f"over {first['year']}–{last['year']}, per person 15+. The paid term "
            f"is frozen at one registry epoch, so this is the unpaid half only."
        ),
    }
