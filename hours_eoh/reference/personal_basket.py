"""
The personal-obligation basket, pinned to physical quantities.

`PERSONAL_EOH_BASE` is unfalsifiable until the basket is stated in physical
units. If the basket floats, any observed hours figure can be absorbed by
redefining what the hours were buying — which is how a desk estimate survives
contact with data indefinitely. This module states the quantities, and states
the delivery productivity for the ONE component anybody has measured.

Read with `core.eoh_generation.personal_statutory_floor`, which sums
quantity × hours_per_unit and returns the rest as unreachable-with-reason.

WHAT IS MEASURED, AND WHAT IS DECLARED
---------------------------------------
Exactly one component is costed: crop production, from LSMS-ISA harmonised v2.0,
seven countries, unassisted stratum (no improved seed, no inorganic fertiliser,
no irrigation, no tractor). Two routes that share only the raw labour variable
land within 6% of each other — 331 h/person·yr bottom-up from kcal per labour-day,
306 h/person·yr from observed labour scaled by crop self-sufficiency.

Every other component carries `hours_per_unit=None`. That is not an oversight and
must not be filled with a plausible-looking number: an invented productivity
would enter the floor with the same standing as the measured one and there would
be no way to tell them apart afterwards. The floor they produce is a strict LOWER
BOUND on the personal obligation, and `coverage` reports how partial it is.

THE BINDING GAP is food processing — threshing, winnowing, pounding, milling,
drying, storage, fuel collection, water for cooking, and cooking itself. LSMS
measures the harvest and not the meal. In hand-powered systems processing
plausibly exceeds production labour, which is the entire difference between the
handoff's 700 and 1,400 h/person·yr recommendation for the survival core. It is
declared here as its own component so the floor cannot be mistaken for a
complete food cost.

THE SURVIVAL CORE / ENTITLEMENT SPLIT
--------------------------------------
Health is not a scaled-down version of the other components — it has no ε = 0
delivery path at all. No quantity of unassisted human labour delivers a
caesarean or an antibiotic, so Q_health / P_health(0) is undefined, not large.
It therefore carries `min_epsilon`: below that automation level the obligation is
owed and undeliverable, and the floor says so rather than costing it.

This is a DIFFERENT mechanism from the registration boundary. Registration
governs what the collective ledger recognises; this governs what the basket
physically contains.

Layer rule: `reference/` imports nothing from the package — these are data, and
any layer may read them.

Reference: handoffs/personal_eoh/HANDOFF_personal_eoh_base.md §0.1, §0.3, §1.1,
§1.2, §2.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Physical quantities — the basket, stated in units that cannot drift
# ---------------------------------------------------------------------------

#: Dietary energy target, kcal/person/day. The handoff's stated food target.
#: CHOSEN — a standard adult reference intake, not a derived optimum.
DIET_KCAL_PER_DAY: float = 2100.0
DIET_DAYS_PER_YEAR: float = 365.25
DIET_KCAL_PER_YEAR: float = DIET_KCAL_PER_DAY * DIET_DAYS_PER_YEAR   # 767,025

#: WHO basic-access water, litres/person/day → litres/person/year.
#: Quantity is well-established; the labour to deliver it is not measured here.
WATER_LITRES_PER_DAY: float = 50.0
WATER_LITRES_PER_YEAR: float = WATER_LITRES_PER_DAY * DIET_DAYS_PER_YEAR

#: Adequate dwelling floor area, m² per person (UN-Habitat adequacy framing).
SHELTER_M2_PER_PERSON: float = 12.0

#: Conditioned-space heating/cooling load, degree-days per year. LATITUDE-
#: DEPENDENT by construction — this is a stated baseline, not a global constant,
#: and it is the reason PERSONAL_EOH_BASE cannot be a single global scalar.
#: 2,500 is a temperate-baseline placeholder carried only so the component
#: appears in the basket with its unit; it is never costed here.
THERMAL_DEGREE_DAYS_PER_YEAR: float = 2500.0

#: Sanitation service-years per person: one person, one year of safe disposal.
SANITATION_SERVICE_YEARS: float = 1.0

#: A defined schedule of health interventions per person-year. Held as 1.0
#: "schedule" because the schedule's contents are an open decision — writing a
#: number here before the schedule exists would be exactly the floating basket
#: this module was written to prevent.
HEALTH_SCHEDULES_PER_YEAR: float = 1.0

# ---------------------------------------------------------------------------
# Delivery productivity — measured where it has been measured
# ---------------------------------------------------------------------------

#: LSMS-ISA unassisted stratum, median-of-ratios across 7 countries.
#: kcal produced per labour-DAY. MEASURED.
LSMS_KCAL_PER_LABOUR_DAY: float = 13907.0

#: Hours per labour-day. CALIBRATED, not assumed: plot-level `total_labor_days`
#: cross-referenced against the individual file's 7-day `farm_hrs` recall over a
#: 20-week season gives country medians of 2.7–6.9 h, median ≈ 6.
LSMS_HOURS_PER_LABOUR_DAY: float = 6.0

#: kcal per labour-HOUR, and its inverse — the only measured delivery
#: productivity in this basket.
LSMS_KCAL_PER_LABOUR_HOUR: float = LSMS_KCAL_PER_LABOUR_DAY / LSMS_HOURS_PER_LABOUR_DAY
NUTRITION_HOURS_PER_KCAL: float = 1.0 / LSMS_KCAL_PER_LABOUR_HOUR

#: The independent cross-check, carried so the convergence is auditable rather
#: than asserted: observed family crop labour of 167 h/household-member/yr at a
#: median crop self-sufficiency of 0.55 scales to ~306 h/person/yr, against the
#: 331 the kcal route gives. Two routes, one shared variable, 6% apart.
NUTRITION_CROSSCHECK_HOURS_PER_YEAR: float = 306.0

#: The automation level below which the health basket has no delivery path.
#: CHOSEN, and deliberately conservative — the claim it encodes is only that
#: SOME automation is required, which the handoff establishes; the exact
#: threshold is not established by anything. resolves_by: service-specific
#: delivery-path analysis (what capital a given intervention actually requires).
#: Nothing in the shipped floor depends on its value, because health is
#: unmeasured at every ε; it exists so the step-in mechanism is exercised and
#: visible rather than latent.
HEALTH_MIN_EPSILON: float = 0.10

# ---------------------------------------------------------------------------
# The baskets
# ---------------------------------------------------------------------------

#: Survival core — the components with an ε = 0 delivery path in principle.
#:
#: SHARES ARE CHOSEN, and they are NOT the `PERSONAL_EOH_COMPONENTS` weights.
#: They exist only to weight `coverage`, so that the honesty metric is not a bare
#: component count. Two things follow and both matter:
#:
#:   1. `data.PERSONAL_EOH_COMPONENTS` decomposes the same obligation differently
#:      — nutrition 0.138 / shelter 0.103 / health 0.138 / **care 0.621** — so
#:      `coverage` here and `a_max` there are measured against DIFFERENT
#:      denominators. Do not read one as calibrating the other.
#:   2. **There is no care line in this basket at all**, and care is the largest
#:      term in that decomposition and the whole Block II anti-correlation
#:      finding. Care resists a physical-quantity statement in a way food and
#:      water do not — "how many hours of attention does a child need" is not a
#:      kcal figure — which is why it is absent rather than declared. Until it is
#:      resolved, `coverage` is optimistic: it reports how much of THIS basket is
#:      priced, not how much of the obligation.
#:
#: Reconciling the two decompositions is an open item (notes/personal-eoh-floor.md §4).
SURVIVAL_CORE: list[dict] = [
    {
        "component": "nutrition_production",
        "quantity_per_person_year": DIET_KCAL_PER_YEAR,
        "unit": "kcal",
        "hours_per_unit": NUTRITION_HOURS_PER_KCAL,
        "share": 0.30,
        # MEASURED — LSMS-ISA, 7 countries, unassisted stratum. Every known bias
        # in the estimate runs upward (livestock labour unmeasured, draft animals
        # not in the assist flags, processing excluded), so 331 is a floor on a
        # floor. Nigeria recall inflation is the one downward correction and it
        # moves robust estimators by 4–5%.
    },
    {
        "component": "nutrition_processing",
        "quantity_per_person_year": DIET_KCAL_PER_YEAR,
        "unit": "kcal",
        "hours_per_unit": None,
        "share": 0.30,
        # THE BINDING UNKNOWN. Threshing, milling, fuel, water for cooking,
        # cooking. Plausibly exceeds production labour in hand-powered systems.
        # resolves_by: ATUS 0202 gives the high-ε end (259.8 h/person15+·yr in
        # 2025) but the US does most processing inside the registered ledger, so
        # the ε≈0 end needs ethnographic time-allocation budgets or a time-use
        # survey in a low-capital setting.
    },
    {
        "component": "water",
        "quantity_per_person_year": WATER_LITRES_PER_YEAR,
        "unit": "litres",
        "hours_per_unit": None,
        "share": 0.10,
        # resolves_by: DHS water-collection time (~90 countries, has trips/day
        # and container volume) in preference to the LSMS WASH modules, which
        # lack both in many waves. The LSMS merge harness is built and dry-run
        # clean; the fallback imputes litres from household size against the WHO
        # threshold, which imports an assumption into a term meant to be
        # assumption-free.
    },
    {
        "component": "shelter",
        "quantity_per_person_year": SHELTER_M2_PER_PERSON,
        "unit": "m2",
        "hours_per_unit": None,
        "share": 0.10,
    },
    {
        "component": "thermal",
        "quantity_per_person_year": THERMAL_DEGREE_DAYS_PER_YEAR,
        "unit": "degree_days",
        "hours_per_unit": None,
        "share": 0.10,
        # LATITUDE-DEPENDENT. Costing this makes the floor climate-indexed, which
        # is correct and means PERSONAL_EOH_BASE cannot remain a global scalar.
    },
    {
        "component": "sanitation",
        "quantity_per_person_year": SANITATION_SERVICE_YEARS,
        "unit": "service_years",
        "hours_per_unit": None,
        "share": 0.10,
    },
]

#: Entitlement augmentation — owed, with no unassisted delivery path. Enters as
#: a step-in term above `min_epsilon`, not as a constant scaled down by ε.
ENTITLEMENT_AUGMENTATION: list[dict] = [
    {
        "component": "health",
        "quantity_per_person_year": HEALTH_SCHEDULES_PER_YEAR,
        "unit": "schedules",
        "hours_per_unit": None,
        "min_epsilon": HEALTH_MIN_EPSILON,
        "share": 0.0,
        # share 0.0: health is deliberately outside the survival-core coverage
        # denominator. Mixing a step-in entitlement into the survival core's
        # coverage would make the core look less complete than it is for a
        # reason that has nothing to do with the core.
    },
]

#: The whole basket. Note that `coverage` over this list is dominated by what is
#: unmeasured — which is the honest reading of the parameter's current state.
FULL_BASKET: list[dict] = SURVIVAL_CORE + ENTITLEMENT_AUGMENTATION
