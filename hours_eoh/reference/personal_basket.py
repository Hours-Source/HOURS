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

HEALTH AND CARE ARE ONE OBLIGATION SPLIT BY DELIVERY PATH, not two unrelated
needs. Care is the part that human attention discharges directly; health is the
part of the same family that requires apparatus to discharge at all. They appear
as separate lines at the granularity the delivery question demands — care in the
survival core, health above a step-in threshold — and not because the underlying
need divides. A future basket that costs them should expect their quantities to
be related, and their delivery productivities not to be.

WHY CARE IS IN THE BASKET (author decision, 2026-08-09)
--------------------------------------------------------
The basket does not track what things cost. It states EOH DEMAND; the framework
then measures how much of that demand can be met. On that reading care is not a
service the obligation might or might not extend to — it is a requirement of
human survival, and therefore a first-class term.

It is also the term the ledger rests on. TEH is denominated in human labour
hours, so the continuation of humans is the precondition for the accounting
system existing at all: a basket that omits care is measuring the obligations of
a population it has quietly assumed will keep appearing. Care is what makes that
assumption true, and it is the largest single term in the desk estimate (62.1%).

SCOPE, stated because it is a real limit and not a caveat: this basket is
human-specific. A framework serving other agents would carry different
components and different quantities, and nothing here generalises to them. What
generalises is the structure — demand stated physically, delivery costed
separately, unreachable kept distinct from zero.

Care is therefore declared with a quantity and NO delivery productivity, exactly
like the other uncosted components. Naming it does not price it.

CLIMATE — WHERE LATITUDE ENTERS
--------------------------------
Climate mostly changes what delivery COSTS, not what is OWED, and the basket's
quantity / hours_per_unit split already separates the two. `CLIMATE_CONDITIONING`
records which kind each component is.

The consequence for the one number this module actually has: **331 h/person·yr
is a rainfed tropical smallholder figure**, measured in seven Sub-Saharan
countries with no irrigation and no frost-limited season. Applied to a boreal
collective it is not conservative, it is out of scope — growing-season length
alone changes the calculation, before storage and preservation labour is counted.
The two-route convergence (331 vs 306, 7.6% apart) is evidence about the kcal
chain and NOT about climate generality: both routes come from the same seven
countries, so the climate uncertainty sits outside that spread, unquantified.

The direction of the transfer bias is deliberately not asserted
(`NUTRITION_TRANSFER_BIAS_SIGN = None`): shorter seasons and winter storage push
hours per kcal up, deeper temperate soils and lower pest pressure push them down,
and nothing here adjudicates.

Two components are exceptions worth knowing. **Thermal** is the one place climate
is the QUANTITY rather than the cost — degree-days are the requirement — which is
why the personal obligation cannot be a global scalar once that term is costed.
**Care** is climate-invariant in both quantity and delivery: a dependent needs the
same attention at any latitude. That is the same structural fact Block II records
as care's low abatability, reached from a different direction.

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

#: Care demand: one person-year of a human being alive and in relationship, per
#: person per year. The quantity is 1.0 by construction — everyone alive needs
#: caring for, for exactly as long as they are alive — which puts the whole
#: unknown into the delivery term where it belongs and can be measured.
CARE_PERSON_YEARS: float = 1.0

# ---------------------------------------------------------------------------
# Delivery productivity — measured where it has been measured
# ---------------------------------------------------------------------------

#: The seven LSMS-ISA countries behind every nutrition figure in this module.
#: ALL Sub-Saharan; none temperate, none boreal, none irrigated (the unassisted
#: stratum excludes irrigation by construction, so this is RAINFED cultivation).
LSMS_COUNTRIES: tuple[str, ...] = (
    "Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda",
)

#: The agro-ecology the measured delivery productivity belongs to. Stated as a
#: constant rather than a docstring aside because it BOUNDS the number's scope:
#: `NUTRITION_HOURS_PER_KCAL` is not a global constant, it is the delivery
#: productivity of rainfed smallholder cultivation in these zones.
LSMS_AGRO_ECOLOGY: str = (
    "rainfed tropical and sub-tropical Sub-Saharan Africa — Sahelian (Mali, "
    "Niger), tropical highland (Ethiopia, Uganda) and tropical savanna "
    "(Malawi, Nigeria, Tanzania); single or bimodal rainfed growing seasons, "
    "no irrigation, no frost-limited season"
)

#: LSMS-ISA unassisted stratum, median-of-ratios across 7 countries.
#: kcal produced per labour-DAY. MEASURED — in the agro-ecology above.
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
#:
#: WHAT THE CONVERGENCE DOES NOT SHOW. Both routes are computed from the SAME
#: seven countries, so their agreement is evidence about the kcal chain and says
#: nothing whatever about whether 331 h transfers to another agro-ecology. The
#: climate uncertainty is NOT inside the 7.6% spread; it is unquantified and
#: sits outside it.
NUTRITION_CROSSCHECK_HOURS_PER_YEAR: float = 306.0

#: The automation level below which the health basket has no delivery path.
#:
#: WHY ε AND NOT CAPITAL (author decision, 2026-08-09). The obvious alternative
#: is to key the step-in on capital per capita, the way `abatement_fraction`
#: does, which would keep every capital-driven mechanism on one variable. It was
#: considered and rejected on the substance: the binding condition for a
#: population to run a health system is not that the capital exists, it is that
#: there is enough LABOUR SLACK to staff it — and that is what ε measures. A
#: collective holding the machines with no spare hours does not deliver
#: healthcare. Capital is necessary and not sufficient; ε is the closer proxy for
#: the sufficient condition.
#:
#: The cost of that choice is stated rather than hidden: this is an ε argument
#: inside a `core/` generation function, where the repo's convention is that
#: generation takes physical state and ε belongs to fulfilment. The convention is
#: right about EOH generation in general and wrong here, because whether an
#: obligation is DELIVERABLE is a fulfilment question that has to be answered
#: before the obligation can be costed at all.
#:
#: CHOSEN, and deliberately conservative — the claim it encodes is only that SOME
#: automation is required, which the handoff establishes; the exact threshold is
#: not established by anything. resolves_by: the labour-slack reading makes this
#: measurable — the ε at which health-sector staffing becomes supportable given
#: the population's total labour supply, rather than a capital inventory.
#:
#: Nothing in the shipped floor depends on its value, because health is unmeasured
#: at every ε; it exists so the step-in mechanism is exercised and visible rather
#: than latent. It becomes load-bearing the moment health is costed.
HEALTH_MIN_EPSILON: float = 0.10

# ---------------------------------------------------------------------------
# The baskets
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Component shares — ONE decomposition, mirrored
#
# Shares weight `coverage`, so that the honesty metric is not a bare component
# count. They are the desk estimate's own four terms, so that this module and
# `data.PERSONAL_EOH_COMPONENTS` (which sets a_max) measure against the SAME
# denominator. Before care was added they did not, and `coverage` was flattered
# by the absence of the largest term.
#
# `reference/` may not import the package, so the four numerators are restated
# here and held to the originals by
# tests/test_personal_floor.py::test_shares_mirror_the_data_decomposition.
# ---------------------------------------------------------------------------

#: The desk estimate's four terms, h/person·yr. MIRROR of the shares in
#: `data.PERSONAL_EOH_COMPONENTS` — change one and the test fails.
DESK_ESTIMATE_HOURS: dict[str, float] = {
    "nutrition": 208.0,
    "shelter": 156.0,
    "health": 208.0,
    "care": 936.0,
}
_DESK_TOTAL: float = sum(DESK_ESTIMATE_HOURS.values())   # 1508


def _share(term: str, split: int = 1) -> float:
    """The desk-estimate share of one term, divided evenly over `split` lines."""
    return DESK_ESTIMATE_HOURS[term] / _DESK_TOTAL / split


#: Survival core — the components with an ε = 0 delivery path in principle.
#: The desk estimate's `shelter` term covers the whole serviced-dwelling bundle
#: (its own pointer is the JMP water-and-sanitation studies), so it is split
#: evenly across the four lines below that make that bundle explicit. The even
#: split is CHOSEN; the term total is not.
SURVIVAL_CORE: list[dict] = [
    {
        "component": "nutrition_production",
        "quantity_per_person_year": DIET_KCAL_PER_YEAR,
        "unit": "kcal",
        "hours_per_unit": NUTRITION_HOURS_PER_KCAL,
        "share": _share("nutrition", 2),
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
        "share": _share("nutrition", 2),
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
        "share": _share("shelter", 4),
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
        "share": _share("shelter", 4),
    },
    {
        "component": "thermal",
        "quantity_per_person_year": THERMAL_DEGREE_DAYS_PER_YEAR,
        "unit": "degree_days",
        "hours_per_unit": None,
        "share": _share("shelter", 4),
        # LATITUDE-DEPENDENT. Costing this makes the floor climate-indexed, which
        # is correct and means PERSONAL_EOH_BASE cannot remain a global scalar.
    },
    {
        "component": "sanitation",
        "quantity_per_person_year": SANITATION_SERVICE_YEARS,
        "unit": "service_years",
        "hours_per_unit": None,
        "share": _share("shelter", 4),
    },
    {
        "component": "care",
        "quantity_per_person_year": CARE_PERSON_YEARS,
        "unit": "person_years",
        "hours_per_unit": None,
        "share": _share("care"),
        # THE LARGEST TERM, 62.1% of the desk estimate, and the one the ledger
        # rests on: TEH is denominated in human labour hours, so human
        # continuation is the precondition for the accounting system existing.
        #
        # It has an ε=0 delivery path — humans have always cared for each other
        # unassisted — so it belongs in the survival core, not among the step-in
        # entitlements. What it does NOT have is a costed one.
        #
        # resolves_by: cross-cultural time allocation at a stated dependency
        # structure. Note the shape of the answer: care hours per person-year are
        # AGE-STRUCTURE-DEPENDENT, so any figure is only meaningful against a
        # stated age distribution — the same way the thermal term is only
        # meaningful against stated degree-days. ATUS 03+04 gives 158.9
        # h/person·yr for the US, but that is an OBSERVED figure at high capital
        # and primary-activity-only (supervising a child while cooking books as
        # cooking), so it is both contaminated and a lower bound. It is not
        # eligible for this slot; see the module docstring.
        #
        # Block II predicts this is the term infrastructure cannot remove
        # (abatability 0.25, the Baumol case), which is why the residual at full
        # abatement is 84.4% care.
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
        "share": _share("health"),
    },
]

#: The whole basket. Note that `coverage` over this list is dominated by what is
#: unmeasured — which is the honest reading of the parameter's current state.
FULL_BASKET: list[dict] = SURVIVAL_CORE + ENTITLEMENT_AUGMENTATION

# ---------------------------------------------------------------------------
# Climate conditioning — where latitude enters, per component
# ---------------------------------------------------------------------------

#: How climate bears on each component. Four kinds, and the distinction is the
#: point: climate mostly changes what delivery COSTS, not what is OWED.
#:
#:   quantity_is_climate  the requirement IS a climate variable
#:   delivery             the quantity is climate-invariant; the hours to
#:                        deliver it are not
#:   quantity_weak        the quantity moves with climate, but second-order
#:   none                 neither the quantity nor its delivery depends on it
CLIMATE_CONDITIONING: dict[str, str] = {
    "nutrition_production": "delivery",
    "nutrition_processing": "delivery",
    "water": "delivery",
    "shelter": "delivery",
    "thermal": "quantity_is_climate",
    "sanitation": "delivery",
    "care": "none",
    "health": "delivery",
}

#: Per-component detail, for the caveat that has to travel with any figure.
CLIMATE_NOTES: dict[str, str] = {
    "nutrition_production": (
        f"THE ONLY PRICED COMPONENT, AND IT IS CLIMATE-SPECIFIC. Measured in "
        f"{LSMS_AGRO_ECOLOGY}. Growing-season length, harvests per year, "
        f"frost-free days, crop mix and the storage/preservation labour needed "
        f"to bridge a non-growing season all differ outside those zones. The "
        f"figure does not transfer without restratification by agro-ecological "
        f"zone."
    ),
    "nutrition_processing": (
        "Fuel gathering and cooking scale with fuel availability and with how "
        "much of the diet must be stored and preserved rather than eaten fresh "
        "— both climate-driven."
    ),
    "water": (
        "Hauling distance and seasonal availability are climate-driven; the "
        "litres owed are only weakly so (heat raises requirement modestly)."
    ),
    "shelter": (
        "Materials, insulation and the maintenance interval against weathering "
        "differ by climate; the m² owed do not."
    ),
    "thermal": (
        "THE ONE COMPONENT WHERE CLIMATE IS THE QUANTITY. Degree-days ARE the "
        "requirement, so this term is latitude-indexed by construction and "
        "cannot be a global scalar. The shipped 2,500 is a stated temperate "
        "baseline, never costed."
    ),
    "sanitation": (
        "Ground conditions, freeze depth and water availability change what "
        "safe disposal costs; the service-year owed is invariant."
    ),
    "care": (
        "CLIMATE-INVARIANT IN BOTH QUANTITY AND DELIVERY. A dependent needs "
        "the same human attention at any latitude, and attention has no "
        "climate-dependent delivery cost. Care is the largest component and "
        "the only one for which this is true — which is the same structural "
        "fact Block II records as its low abatability (the Baumol case), "
        "arriving from a different direction."
    ),
    "health": (
        "Disease burden is strongly climate-linked (vector range, seasonality), "
        "so the intervention schedule and its delivery cost both shift; the "
        "step-in threshold does not."
    ),
}

#: The direction of the transfer bias is NOT determined by this data, and is
#: deliberately not asserted — the repo's standing posture where a sign is
#: undetermined. Two mechanisms run opposite: toward higher latitude a shorter
#: single season and the storage labour to bridge winter push hours per kcal UP,
#: while deeper temperate soils and lower pest and disease pressure push them
#: DOWN. Nothing in the LSMS stratum adjudicates between them.
#: resolves_by: restratification by agro-ecological zone, or a comparable
#: time-allocation measurement in a temperate or boreal subsistence setting
#: (the handoff's ethnographic time-allocation budgets).
NUTRITION_TRANSFER_BIAS_SIGN: None = None
