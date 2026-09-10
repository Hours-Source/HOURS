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

Reference: the personal-obligation handoff §0.1, §0.3, §1.1,
§1.2, §2.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Physical quantities — the basket, stated in units that cannot drift
# ---------------------------------------------------------------------------

#: WHAT KIND OF UNKNOWN EACH COMPONENT IS (2026-09-09).
#:
#: The floor's remaining work is not one job repeated seven times. Each component
#: is blocked on a different KIND of thing, and the kinds want different
#: instruments — so this table exists to stop "five components are unmeasured"
#: being read as one homogeneous backlog.
#:
#: Three axes, each a closed vocabulary and each bound to the data by
#: `tests/test_personal_floor.py` so the classification cannot drift from the
#: basket it describes:
#:
#:   quantity  — is WHAT IS OWED the same everywhere?
#:               "universal" a biological or chosen standard that does not vary
#:                           by place; "instance" a property of the location.
#:   delivery  — is WHAT IT COSTS to deliver the same everywhere?
#:               "instance" varies by climate, technology or distance;
#:               "invariant" does not; "none" has no unassisted path at all.
#:   status    — "measured"      costed, transferable
#:               "one_frame"     costed in ONE setting, transfer unasserted
#:               "bound"         costed as a declared BOUND on the quantity
#:                               rather than as the quantity, with the direction
#:                               stated. Distinct from `one_frame`: that one is
#:                               the right quantity in the wrong place, this one
#:                               is the wrong quantity everywhere — and reading
#:                               it as the value is the specific error the
#:                               status exists to prevent.
#:               "open"          not costed; an instrument exists
#:               "undefined"     not costed and NOT costable at this ε
#:
#: THE TWO STRUCTURAL FACTS THIS TABLE MAKES VISIBLE, both of which are
#: consequences rather than opinions:
#:
#: 1. TWO COMPONENTS CARRY A PLACE PROPERTY ON THE QUANTITY SIDE, and together
#:    they set the grain at which a floor can be stated at all. Shelter carries
#:    degree-days; water carries distance-to-source (2026-09-09, author
#:    decision). Degree-days makes the floor CLIMATE-indexed. Distance makes it
#:    SITE-indexed, which is a strictly finer grain: two collectives in one
#:    climate, one beside a spring and one 3 km from it, share a climate and do
#:    NOT share a floor. **So `PERSONAL_EOH_BASE` cannot be made correct by
#:    declaring a climate zone — the finest honest index is a site, and the arc
#:    from "one global scalar" to "one number per site" is the whole distance
#:    this parameter has to travel.**
#: 2. HEALTH'S GAP IS NOT A MEASUREMENT GAP. Q/P(0) is undefined, not large: no
#:    quantity of unassisted labour delivers a caesarean. More data does not
#:    close it and it must never be filled with a plausible number.
#:
#: `care` is the one component invariant on BOTH axes — a dependent needs the
#: same attention at any latitude — which is the same structural fact Block II
#: reaches from abatability. It is also the largest desk term (62.1%).
COMPONENT_STATUS: dict[str, dict[str, str]] = {
    "nutrition_production": {
        "quantity": "universal",
        "delivery": "instance",
        "status": "one_frame",
        "blocked_on": "transfer out of rainfed tropical smallholder agro-ecology; "
                      "NUTRITION_TRANSFER_BIAS_SIGN is deliberately None",
    },
    "nutrition_processing": {
        "quantity": "universal",
        "delivery": "instance",
        "status": "bound",
        "blocked_on": "MTUS code 19 for ZA2000 and ZA2010 — the only two of 46 "
                      "samples missing it, and the only two in the base's declared "
                      "SSA frame. Absent, not zero, so the priced figure bounds "
                      "from below; South Africa is also not ε≈0, which pushes the "
                      "same way. An SSA survey reporting both codes closes it",
    },
    "water": {
        "quantity": "instance",
        "delivery": "instance",
        "status": "open",
        "blocked_on": "A FORM QUESTION FIRST, THEN AN ACQUISITION — and the form "
                      "question is why DHS would not have settled it. Four "
                      "independent variables sit inside one hours_per_unit: "
                      "(1) DISTANCE to the source; (2) CARRY per trip, which is "
                      "container volume and therefore capital, not a human "
                      "constant; (3) MOVED-vs-USED — one person carries and a "
                      "household consumes, so collection time is per COLLECTOR "
                      "while the quantity is per PERSON, and the conversion needs "
                      "household size, a demographic instance; (4) CARRIED-vs-"
                      "USED-IN-PLACE — washing at the source costs transport "
                      "nothing while drinking and cooking water must come back, "
                      "so the litres NEEDING carriage are a site- and "
                      "practice-dependent fraction of litres used. The basket\'s "
                      "quantity x hours_per_unit form cannot carry four; this is "
                      "thermal\'s problem, not nutrition\'s, and thermal was "
                      "merged into shelter rather than costed",
    },
    "shelter": {
        "quantity": "instance",
        "delivery": "instance",
        "status": "open",
        "blocked_on": "A CROSS-DOMAIN BOUNDARY, before the data question. MTUS "
                      "(20,21,22) validates against ATUS at 0.9757 and is ready "
                      "— but a DWELLING IS IN THE CAPITAL STOCK: "
                      "`capital_inventory` carries $34.4T of private residential "
                      "structures on the `building` profile, so `infrastructure_eoh` "
                      "already charges maintenance on it. Household upkeep and "
                      "capital maintenance are the same physical work counted in "
                      "two domains, and nothing separates self-performed from "
                      "collectively-delivered. Draw the boundary BY CONSTRUCTION "
                      "the way `verification.py` excludes 474011 and 232093 "
                      "because servicing already counts them. Then degree-days "
                      "makes the floor climate-indexed",
    },
    "sanitation": {
        "quantity": "universal",
        "delivery": "instance",
        "status": "open",
        "blocked_on": "no named instrument yet — the weakest resolves_by of the seven",
    },
    "care": {
        "quantity": "universal",
        "delivery": "invariant",
        "status": "bound",
        "blocked_on": "a code set that CLEARS THE 5% BAR. This one runs 0.827 of "
                      "ATUS care and data.py's COMPONENT_CODES_MTUS excludes it "
                      "for that reason; it is priced past that determination "
                      "deliberately, as a bound. Errs LOW three ways — 0.827 of "
                      "ATUS care, ATUS care narrower than the model's, and "
                      "delivered rather than owed",
    },
    "health": {
        "quantity": "universal",
        "delivery": "none",
        "status": "undefined",
        "blocked_on": "nothing measurable. Below min_epsilon the obligation is owed "
                      "and undeliverable; the floor says so rather than costing it",
    },
}

#: The closed vocabularies, exported so the test does not restate them.
COMPONENT_STATUS_VOCAB: dict[str, frozenset[str]] = {
    "quantity": frozenset({"universal", "instance"}),
    "delivery": frozenset({"instance", "invariant", "none"}),
    "status":   frozenset({"measured", "one_frame", "bound", "open", "undefined"}),
}

#: MOVED TO `data.py` 2026-08-16 — the basket QUANTITIES are chosen standards,
#: not measured data, so they belong with the framework's other parameters and
#: under the shadow-constant gate. `BASKET_DIET_KCAL_PER_DAY`,
#: `BASKET_WATER_LITRES_PER_DAY`, `BASKET_THERMAL_DEGREE_DAYS_PER_YEAR` and
#: `BASKET_HEALTH_MIN_EPSILON` are now supplied by the caller. What stays here
#: is what this layer is for: the MEASURED delivery productivities.
DIET_DAYS_PER_YEAR: float = 365.25

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

#: PROCESSING, from MTUS codes (18,19) — food and drink PREPARATION, validated
#: against ATUS 0202 at a mean ratio of 1.0147 over 21 overlapping years
#: (`automation_floors.validate_code_mapping`). Disjoint from the LSMS figure
#: above by construction: LSMS measures the harvest, this measures the meal.
#:
#: THE TWO SSA SAMPLES ONLY, because the base declares an SSA rainfed tropical
#: frame and the 46-sample median (240.4 h/person·yr) is a different frame. The
#: frame rule is `data.PERSONAL_EOH_BASE_CLIMATE_FRAME`, declared 2026-09-04 and
#: not chosen after seeing these numbers.
#:
#: **A LOWER BOUND, TWICE OVER.** (1) ZA2000 and ZA2010 are the ONLY two of 46
#: samples carrying code 18 without code 19 — absent, not zero. Where both are
#: present code 19 runs 12.3%–53.4% of the pair (median 21.8%), so grossing
#: would give 506–517 h/person·yr; that is an imputation and is NOT adopted.
#: (2) South Africa is not ε≈0, so even the SSA end understates the unassisted
#: requirement. Both push the same way.
#:
#: Direction is measured, not assumed: processing FALLS with capital — US2004–08
#: lowest at 31–32 min/day against ZA/BG/FR1966 at 65–78, pre-1980 mean 59.4
#: against post-2000 40.8. `delivery: instance` behaving as the classification
#: says it should, and the opposite of care.
MTUS_PROCESSING_SAMPLES: tuple[str, ...] = ("ZA2000", "ZA2010")
PROCESSING_HOURS_PER_PERSON_YEAR: float = 400.2

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
def survival_core(
    diet_kcal_per_day: float,
    water_litres_per_day: float,
    thermal_degree_days_per_year: float,
    shelter_m2_per_person: float,
    water_distance_m: float,
    care_hours_per_person_year: float,
) -> list[dict]:
    """
    The components with an ε = 0 delivery path in principle.

    QUANTITIES ARE SUPPLIED, NOT STORED. They are chosen standards — a dietary
    reference intake, a WHO service level, a temperate degree-day baseline — and
    chosen standards belong in `data.py` with the framework's other parameters,
    not in the layer reserved for measured data. What this module keeps is the
    measured half: `NUTRITION_HOURS_PER_KCAL` and the stratum it came from.

    units: quantities per person per year, in each component's own unit.

    Args:
        water_distance_m: `data.BASKET_WATER_DISTANCE_M` — the SITE property on
            water's quantity side, carried and never costed. See the water row.
        diet_kcal_per_day: `data.BASKET_DIET_KCAL_PER_DAY`.
        water_litres_per_day: `data.BASKET_WATER_LITRES_PER_DAY`.
        thermal_degree_days_per_year: `data.BASKET_THERMAL_DEGREE_DAYS_PER_YEAR`.
        shelter_m2_per_person: `data.BASKET_SHELTER_M2_PER_PERSON`.

    Raises:
        ValueError: on a non-positive quantity — a basket line with no
            requirement is not a zero requirement, it is a mistake.
    """
    for name, q in (
        ("diet_kcal_per_day", diet_kcal_per_day),
        ("water_litres_per_day", water_litres_per_day),
        ("thermal_degree_days_per_year", thermal_degree_days_per_year),
        ("shelter_m2_per_person", shelter_m2_per_person),
        # a zero-distance source is a tap, which is a DIFFERENT delivery regime
        # rather than a free one — the hauling productivity does not describe it.
        ("water_distance_m", water_distance_m),
        ("care_hours_per_person_year", care_hours_per_person_year),
    ):
        if q <= 0.0:
            raise ValueError(f"{name} must be positive, got {q}")

    diet_kcal_per_year = diet_kcal_per_day * DIET_DAYS_PER_YEAR
    water_litres_per_year = water_litres_per_day * DIET_DAYS_PER_YEAR

    return [
    {
        "component": "nutrition_production",
        "quantity_per_person_year": diet_kcal_per_year,
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
        "quantity_per_person_year": diet_kcal_per_year,
        "unit": "kcal",
        # PRICED 2026-09-10 from MTUS (18,19), SSA samples only — see
        # PROCESSING_HOURS_PER_PERSON_YEAR for the frame rule and the two
        # reasons it bounds from below.
        #
        # THE MEASUREMENT IS PER PERSON-YEAR AND THE COMPONENT'S UNIT IS KCAL,
        # so the conversion is written HERE rather than baked into the constant.
        # Dividing by this basket's own kcal keeps the measured number in the
        # units it was measured in, and makes the assumption visible instead of
        # hiding it inside a constant: expressing processing per kcal ASSERTS
        # that preparation labour scales with calories, which MTUS does not test.
        # The assumption is more defensible at the low-capital end that supplies
        # this figure — threshing, milling and pounding do scale with grain —
        # than at the high-capital end, where a larger meal is not a longer one.
        "hours_per_unit": PROCESSING_HOURS_PER_PERSON_YEAR / diet_kcal_per_year,
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
        "quantity_per_person_year": water_litres_per_year,
        "unit": "litres",
        "hours_per_unit": None,
        "share": _share("shelter", 3),
        "distance_to_source_m": water_distance_m,
        # DISTANCE CARRIED HERE 2026-09-09, on the shelter/thermal template and
        # for the same reason. The physical form is
        #     litres x distance x hours per (litre.metre)   at a stated carry
        # so distance is an INTENSITY on the quantity, not part of the delivery
        # productivity. It is NOT multiplied into the floor — `hours_per_unit`
        # is still None — exactly as `degree_days_per_year` is carried and not
        # costed on the shelter row.
        #
        # WHY IT CANNOT LIVE INSIDE `hours_per_unit`. A single hours-per-litre
        # figure has a distance distribution AND a carry distribution folded
        # invisibly into it. Those are independent and each spans an order of
        # magnitude — 10 m against 1 km, four units carried against ten — so the
        # average describes no actual collective. Splitting distance out is what
        # leaves a remainder that transfers at all: hours per litre.metre at a
        # stated carry is bounded by human porterage, which is a fact about
        # bodies rather than about places.
        #
        # "at a stated carry" does the work "at a stated envelope" does for
        # thermal, and it is age-structured — who fetches the water. That is the
        # same dependency `care` carries and for the same reason.
        #
        # AND DISTANCE IS ITSELF A FUNCTION OF CAPITAL: siting a well closer is
        # the abatement channel, the way insulation trades against heating on the
        # shelter row. Two additive line items can only take one point from each
        # curve, so a costed water term has to name which siting it assumes.
        #
        # resolves_by: DHS water-collection time (~90 countries, has trips/day
        # and container volume) in preference to the LSMS WASH modules, which
        # lack both in many waves. The LSMS merge harness is built and dry-run
        # clean; the fallback imputes litres from household size against the WHO
        # threshold, which imports an assumption into a term meant to be
        # assumption-free.
    },
    {
        "component": "shelter",
        "quantity_per_person_year": shelter_m2_per_person,
        "unit": "m2",
        "hours_per_unit": None,
        "share": _share("shelter", 3),
        "degree_days_per_year": thermal_degree_days_per_year,
        # THERMAL MERGED IN HERE 2026-09-04, and for three reasons.
        #
        # (1) DEGREE-DAYS IS NOT A PER-PERSON QUANTITY. It is a property of a
        # place: a village of 100 and a city of a million in one climate both
        # face 2,500. The basket's form is Σ quantity_per_person_year ×
        # hours_per_unit, and exactly one row violated it — which is what
        # CLIMATE_CONDITIONING already recorded by marking thermal
        # `quantity_is_climate` while every other component is `delivery`.
        #
        # (2) THERMAL HAS NO QUANTITY OF ITS OWN; IT BORROWS SHELTER'S. The
        # physical form is m² × degree-days × hours per (m²·degree-day) at a
        # stated envelope, so degree-days is an INTENSITY on shelter's quantity.
        # It is carried here as `degree_days_per_year` for exactly that use and
        # is NOT multiplied into the floor — `hours_per_unit` is still None.
        #
        # (3) THEY ARE SUBSTITUTES AND THE BASKET SUMS. Insulation is shelter
        # capital, heating is thermal flow; a better envelope RAISES shelter
        # hours and LOWERS thermal hours. The true cost is the minimum over that
        # trade-off, and two additive line items can only add one point from
        # each curve — wrong wherever the envelope is not already optimal.
        #
        # The consequence the thermal row used to state still holds and is now
        # stated once instead of twice: costing this makes the floor
        # climate-indexed, so PERSONAL_EOH_BASE must declare which climate it
        # is for. That is a `person` item, not a defect of this row.
    },
    {
        "component": "sanitation",
        "quantity_per_person_year": SANITATION_SERVICE_YEARS,
        "unit": "service_years",
        "hours_per_unit": None,
        "share": _share("shelter", 3),
    },
    {
        "component": "care",
        "quantity_per_person_year": CARE_PERSON_YEARS,
        "unit": "person_years",
        "hours_per_unit": care_hours_per_person_year,
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

def entitlement_augmentation(health_min_epsilon: float) -> list[dict]:
    """
    Owed, with no unassisted delivery path — a step-in term above `min_epsilon`.

    `health_min_epsilon` is a CLASSIFICATION GATE rather than a quantity: below
    it the component is owed and undeliverable, so the floor reports it as
    `below_min_epsilon` rather than `unmeasured`. Either way it is EXCLUDED, not
    costed at zero.

    Args:
        health_min_epsilon: `data.BASKET_HEALTH_MIN_EPSILON`, ∈ [0, 1].

    Raises:
        ValueError: if the gate is outside [0, 1].
    """
    if not 0.0 <= health_min_epsilon <= 1.0:
        raise ValueError(
            f"health_min_epsilon must be in [0, 1], got {health_min_epsilon}"
        )
    return [
    {
        "component": "health",
        "quantity_per_person_year": HEALTH_SCHEDULES_PER_YEAR,
        "unit": "schedules",
        "hours_per_unit": None,
        "min_epsilon": health_min_epsilon,
        "share": _share("health"),
    },
]

def full_basket(
    diet_kcal_per_day: float,
    water_litres_per_day: float,
    thermal_degree_days_per_year: float,
    shelter_m2_per_person: float,
    health_min_epsilon: float,
    water_distance_m: float,
    care_hours_per_person_year: float,
) -> list[dict]:
    """
    The whole basket, survival core plus entitlement augmentation.

    `coverage` over this list is dominated by what is unmeasured — one priced
    component of seven, 6.9% — which is the honest reading of the parameter's
    current state and not a defect of the list.

    Every quantity is supplied by the caller from `data.py`; see `survival_core`
    for why. `scenarios.personal_floor` is the caller in this repo.
    """
    return survival_core(
        diet_kcal_per_day,
        water_litres_per_day,
        thermal_degree_days_per_year,
        shelter_m2_per_person,
        water_distance_m,
        care_hours_per_person_year,
    ) + entitlement_augmentation(health_min_epsilon)

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
