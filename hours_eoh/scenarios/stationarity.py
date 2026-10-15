"""
Stationarity under the wage doctrine — can a collective STAND STILL at this ε,
in labour hours AND in TEH?

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. Composes the pipeline, the guarantee, the land fee and the
labour supply; adds no mechanism and moves no shipped number.

THE DOCTRINE (author decision, 2026-09-15): MINTED TEH IS THE WAGE
------------------------------------------------------------------
Registered human labour is paid when it mints. Everything below follows from
that and is computed here rather than asserted:

  * The Trust owes NONE of the registered stewardship, care or ecological
    labour — the mint already paid it. It owes only what does not mint: the
    sufficiency guarantee.
  * Core agrees since the same day: `trust_management` charges the Trust the
    guarantee alone and returns stewardship, ecological and care as
    `paid_by_mint`. This report states the same quantity under the same key.
  * The levy and the Ground Use Fee are TRANSFERS into the Trust.
  * The inheritance is a CHARTER INPUT, default 0.0. It exists only when a
    collective converts from a previous system; one starting from subsistence
    has none.
  * Unspent dividend stays in the Trust. A Trust is stationary when what flows
    in covers what it owes; drawing principal is not standing still.

THE TWO SIDES FAIL AT OPPOSITE ENDS, AND THAT IS WHY BOTH ARE REPORTED
---------------------------------------------------------------------
LABOUR: can the human hours the obligation needs be worked? Binds at the BOTTOM
of the arc, where people carry nearly all of it. TEH: can the Trust's inflows
pay the guarantee? Binds where the mint and the land fee are small against the
guarantee. Which side fails says what kind of shortfall it is: a labour
shortfall is physical (the obligation goes unmet — shorter lives, less care);
a TEH shortfall is fiscal (the Trust draws down).

THE LABOUR SIDE READS THE PIPELINE'S SPLIT
-----------------------------------------
Human hours come off `eoh_to_teh_pipeline`, the same split D3 and the guarantee
use. `arc_stability` read a uniform `1 − ε` until 2026-09-15 and now uses the
same adopted split; its verdict is carried alongside and the two are tested to
agree, so a future divergence is visible rather than silent.

STATED LIMITS
-------------
  * ONE BASE FOR BOTH SIDES, DEFAULT THE SHIPPED 1,000 h. The guarantee sizes
    on `PERSONAL_EOH_BASE` (author decision 2026-09-15: keep it), and so does
    this report unless `standard` (600 h survival, 1,500 h sufficiency) or
    `personal_base` is given. The sufficiency STANDARD stays 1,500 h; it and
    the guarantee's base are two quantities by decision. `guarantee_base` is
    reported so the choice is visible.
  * THE LAND FEE'S FRAME IS DECLARED. A parcel SAMPLE prices the fee; the
    collective's parcel COUNT scales it, defaulting to population × the measured
    national PRIVATE parcels per person (government parcels excluded,
    2026-10-15). The shipped archetypes are synthetic, and
    `record/guf.md` records the fee's level as structurally mis-set.
  * `v1` IS THE DEFAULT DESIGN HERE (author, 2026-09-16: "assume we adopt V1"),
    and this module is REPORTING ONLY — `core.fiscal.sufficiency_guarantee`
    still computes the shipped design, so adopting V1 in the fisc is a separate
    decision. `v2` remains proposed. Pass `guarantee="shipped"` for the
    pre-adoption reading.
  * The arc path in `drawdown` is a SCENARIO CHOICE. How fast ε advances is
    unknown; nothing here assumes a speed unless the caller supplies one.

WHAT THIS DOES NOT DO. It takes no charter decision: it does not choose a
guarantee design, a need fraction, a land-fee cap or an inheritance. It reports
where standing still is possible under each, and how long a Trust lasts where
it is not.

Layer: scenarios/ — imports core/, land/, reference/ and scenarios/; imported by
none of them.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline, human_eoh_per_domain
from hours_eoh.core.eoh_generation import personal_base_for, resolve_capital_stock
from hours_eoh.core.fiscal import (
    aggregate_care_stipend_from_demographics,
    assessed_levy_rate,
    stewardship_allocation,
    sufficiency_guarantee,
    trust_management,
)
from hours_eoh.data import (
    CAPITAL_AGE_RATIO_DEFAULT,
    EPSILON_ARC_MAX,
    REFERENCE_FRAME_POPULATION,
    ARC_REPORTING_POINTS,
    MEASURED_CAPACITY_H_YR,
    M_FLOOR,
    PERSONAL_EOH_BASE,
    SUFF_LEVY_RATE,
    SUFF_NEED_FRACTION,
)
from hours_eoh.land.collective import (
    PER_PARCEL_BASIS, default_parcel_count, make_urban_collective, per_parcel_guf,
    sample_scaled_guf)
from hours_eoh.scenarios.arc_stability import STANDARDS, band_from_flags, stability_at
from hours_eoh.scenarios.feasibility import (
    capacity_weighted_adult_share,
    labor_supply_per_capita,
)

__all__ = [
    "GUARANTEE_DESIGNS",
    "GUF_CAP_RULES",
    "d3_consumption",
    "stationarity_at",
    "stationarity_arc",
    "stationary_bands",
    "drawdown",
    "reserve_plan",
    "stationarity_report",
    "registered_work_access",
    "registered_work_arc",
]

#: `shipped` is the adopted default. `v1` (need fraction among the on-ledger
#: share) and `v2` (every on-ledger person) are PROPOSED, 2026-09-15.
GUARANTEE_DESIGNS: tuple[str, ...] = ("shipped", "v1", "v2")

#: A cap may be a plain share of the mint (a float), or `payable`: landholders
#: can pay at most what they hold after the levy and D3 consumption.
GUF_CAP_RULES: tuple[str, ...] = ("payable",)

def d3_consumption(
    personal_gross: float,
    personal_registration_share: float,
    personal_human: float,
) -> float:
    """
    D3 terminal consumption, in TEH: on-ledger personal EOH × its human-carried
    share × `M_FLOOR`.

    The same formula `core.simulation.simulate_period` applies under `use_d3`.
    Written here from its three inputs rather than by running a period, and
    BOUND TO THE SIMULATION BY TEST (`test_stationarity.py`), because the two
    must stay one quantity.

    units: TEH per year. ε-behaviour: through its inputs only.
    """
    if personal_gross <= 0.0:
        return 0.0
    human_share = personal_human / personal_gross
    return personal_gross * personal_registration_share * human_share * M_FLOOR


def _guarantee_owed(
    design: str,
    population: float,
    epsilon: float,
    need_fraction: float | None,
    personal_eoh_base: float,
    age_fractions: dict[str, float] | None = None,
) -> tuple[float, dict]:
    """The guarantee owed under a design — DELEGATED to core since 2026-09-16.

    This module used to carry its own copy of the V1 and V2 formulas while core
    computed only the shipped aggregation. Once `sufficiency_guarantee` gained a
    `design` parameter the copy became a second account of one quantity, and it
    immediately behaved like one: with the local branch still in place,
    `design="shipped"` called core WITHOUT `design=`, so it received core's new
    V1 default and "shipped" silently stopped meaning shipped.

    The delegation changes no number. This module passed the PIPELINE's realized
    personal registration share while core uses
    `registration.personal_eoh_registration_share(ε)`; they were measured equal
    to 1e-12 at ε ∈ {0, 0.20, 0.40, 0.70, 0.90, 0.99}, which is why the
    parameter could be dropped rather than threaded through.

    `None` resolves to SUFF_NEED_FRACTION — the V1 need fraction the levy was
    sized against. It used to resolve to the guarantee's own `floor_fraction`
    (0.15 at ε=0 decaying to 0.1005), roughly three times the adopted value, so
    the module's default ran V1 at a need fraction nobody had chosen.
    """
    need = SUFF_NEED_FRACTION if need_fraction is None else need_fraction
    g = sufficiency_guarantee(
        population, epsilon,
        personal_eoh_base=personal_eoh_base,
        design=design,
        need_fraction=need,
        age_fractions=age_fractions,
    )
    return g["total_cost_teh"], g


def stationarity_at(
    epsilon: float = 0.40,
    *,
    population: float = REFERENCE_FRAME_POPULATION,
    standard: str | None = None,
    personal_base: float | None = None,
    capital_stock_teh: float | None = None,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    guarantee: str = "v1",
    need_fraction: float | None = None,
    levy_rate: float = SUFF_LEVY_RATE,
    guf_parcels: list[dict] | None = None,
    guf_parcel_count: float | None = None,
    guf_cap: float | str | None = "payable",
    trust_start: float = 0.0,
    capital_age_ratio: float | None = None,
    adult_share: float | None = None,
    age_fractions: dict[str, float] | None = None,
) -> dict:
    """
    Both sides at one ε. Can the collective stand still here?

    Governing tests, per year:

        LABOUR   supply_per_capita          >= human_hours_per_capita
                 (survival_met: supply      >= human personal hours)
        TEH      levy + GUF                 >= guarantee owed

    with `human_hours` the pipeline's human EOH under its own split, `levy` =
    `levy_rate × mint`, and GUF = a parcel sample's revenue per parcel ×
    `guf_parcel_count`, capped by default at what the mint leaves to pay it.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Frame population.
        standard: `survival` or `sufficiency` — sets the personal base for both
            sides. None (the default) uses the shipped `PERSONAL_EOH_BASE`,
            1,000 h (author decision 2026-09-15), which is neither standard,
            so the `arc_stability_*` fields are None unless one is named.
        personal_base: Overrides the standard's base for both sides, h/yr per
            working-age-equivalent, so a base between or beyond the two named
            standards can be tested. `arc_stability` only knows the named
            standards, so when this differs from the standard's base the
            `arc_stability_*` comparison fields are None rather than computed
            at a different base.
        capital_stock_teh: Actual capital stock; resolved along the arc when None.
        adult_capacity_h_yr: Hours an adult can supply in a year.
        guarantee: One of `GUARANTEE_DESIGNS`.
        need_fraction: For `v1`, the share of on-ledger people receiving the
            guarantee. None uses `SUFF_NEED_FRACTION` (0.05), the adopted value
            the levy was sized against. Raising it moves the Trust's whole
            liability — at 10% the required levy roughly doubles.
        levy_rate: Levy as a share of the mint.
        guf_parcels: A parcel SAMPLE that prices the fee. None → no land fee,
            and `guf` is 0.0 — unless `guf_parcel_count` is given, when the
            fee is its measured per-parcel half (`per_parcel_guf`, 2026-10-15)
            with the area part NOT SUPPLIED. An empty list is no fee either way.
        guf_parcel_count: Parcels the collective holds. None → population × the
            measured national PRIVATE parcels per person (`default_parcel_count`).
        guf_cap: `payable` (default since 2026-10-15, author: "you can't pay
            what isn't minted") collects at most the mint less the levy and D3;
            a float caps at that share of the mint; None collects the whole
            assessed fee. The rest is `teh["guf_unpaid"]`, reported and never
            counted as inflow. An UPPER bound on collection: only private
            holders pay, and the ceiling is the whole collective's.
        trust_start: The inheritance, TEH. Default 0.0 — a collective starting
            from subsistence has none.
        capital_age_ratio: The stock's age over its service life — it sets the
            infrastructure upkeep, so the human hours and the mint. None reads
            `CAPITAL_AGE_RATIO_DEFAULT`, and the result says so.
        adult_share: Share of the population able to supply labour. None
            derives it from `age_fractions` when those are given, else from
            the shipped age weights, and the result says which.
        age_fractions: The population's age mix, `{group: fraction}`. Reaches
            the pipeline (personal obligation, so the hours and the mint), the
            guarantee's per-recipient obligation, the compass and — unless
            `adult_share` is given — the supply. None → the shipped mix.

    Returns:
        dict with `labour`, `teh`, `stationary` (both sides) and the inputs.

    Raises:
        ValueError: on an ε, standard, design, cap rule or share out of range.
    """
    if not 0.0 <= epsilon <= EPSILON_ARC_MAX:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if standard is not None and standard not in STANDARDS:
        raise ValueError(f"standard must be one of {STANDARDS} or None, got {standard!r}")
    if guarantee not in GUARANTEE_DESIGNS:
        raise ValueError(f"guarantee must be one of {GUARANTEE_DESIGNS}, got {guarantee!r}")
    if isinstance(guf_cap, str) and guf_cap not in GUF_CAP_RULES:
        raise ValueError(f"guf_cap rule must be one of {GUF_CAP_RULES}, got {guf_cap!r}")
    if isinstance(guf_cap, float) and not 0.0 <= guf_cap:
        raise ValueError(f"guf_cap share must be >= 0, got {guf_cap}")
    if need_fraction is not None and not 0.0 <= need_fraction <= 1.0:
        raise ValueError(f"need_fraction must be in [0, 1], got {need_fraction}")
    if personal_base is not None and personal_base <= 0.0:
        raise ValueError(f"personal_base must be > 0, got {personal_base}")

    standard_base = personal_base_for(standard) if standard is not None else PERSONAL_EOH_BASE
    base = standard_base if personal_base is None else personal_base
    at_standard = standard is not None and base == standard_base
    capital = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    age = CAPITAL_AGE_RATIO_DEFAULT if capital_age_ratio is None else capital_age_ratio
    # One population on both sides (2026-10-14): see arc_stability.stability_at.
    share_from_ages = adult_share is None and age_fractions is not None
    if share_from_ages:
        adult_share = capacity_weighted_adult_share(age_fractions)
    p = eoh_to_teh_pipeline(
        epsilon=epsilon, population=population, capital_stock=capital,
        capital_age_ratio=age, age_distribution=age_fractions,
        **({"personal_standard": standard} if at_standard
           else {"personal_base": base}),
    )
    by_domain = p["eoh_by_domain"]
    human = human_eoh_per_domain(by_domain, epsilon)
    r_personal = p["registration_by_domain"]["personal"]

    # ---- LABOUR -----------------------------------------------------------
    supply = labor_supply_per_capita(adult_capacity_h_yr=adult_capacity_h_yr,
                                     adult_share=adult_share)
    human_hours = p["human_eoh"] / population
    human_personal = human["personal"] / population
    compass = stability_at(
        epsilon, capital_stock_teh=capital, population=population,
        adult_capacity_h_yr=adult_capacity_h_yr, standard=standard,
        capital_age_ratio=age, adult_share=adult_share, age_fractions=age_fractions,
    ) if at_standard and standard is not None else None
    labour = {
        "supply_per_capita":         supply,
        "human_hours_per_capita":    human_hours,
        "human_personal_per_capita": human_personal,
        "survival_met":              supply >= human_personal,
        "stationary":                supply >= human_hours,
        "shortfall_per_capita":      max(0.0, human_hours - supply),
        "shortfall_share":           max(0.0, human_hours - supply) / human_hours if human_hours > 0.0 else 0.0,
        # `arc_stability`'s reading of the same point, carried so the two can be
        # compared rather than one silently replacing the other. None at a base
        # `arc_stability` cannot evaluate.
        "arc_stability_stationary":  compass["stationary"] if compass else None,
        "arc_stability_human_per_capita": (
            compass["obligation_per_capita"] + compass["delivery_per_capita"]
            if compass else None),
        "delivery_pays":             compass["delivery_pays"] if compass else None,
        # The compass's own supply, so the two readings are seen to stand on
        # the same capacity (2026-10-07: they did not, on the frame's adult share).
        "arc_stability_supply_per_capita": compass["supply_per_capita"] if compass else None,
    }

    # ---- TEH --------------------------------------------------------------
    mint = float(p["teh_created"])
    levy = levy_rate * mint
    consumption = d3_consumption(by_domain["personal"], r_personal, human["personal"])

    guf_uncapped = 0.0
    guf_basis = "none"
    if guf_parcels:
        count = (default_parcel_count(population)
                 if guf_parcel_count is None else guf_parcel_count)
        guf_uncapped = sample_scaled_guf(guf_parcels, epsilon, count)
        guf_basis = "sample mean × parcel count"
    elif guf_parcels is None and guf_parcel_count is not None:
        # A COUNT AND NO SAMPLE: the fee's measured half (2026-10-15, author).
        guf_uncapped = per_parcel_guf(epsilon, guf_parcel_count)
        guf_basis = PER_PARCEL_BASIS
    payable = max(0.0, mint - levy - consumption)
    if guf_cap is None:
        guf = guf_uncapped
    elif guf_cap == "payable":
        guf = min(guf_uncapped, payable)
    else:
        guf = min(guf_uncapped, float(guf_cap) * mint)

    owed, g = _guarantee_owed(guarantee, population, epsilon, need_fraction, base,
                              age_fractions)
    inflow = levy + guf
    deficit = max(0.0, owed - inflow)

    # `capital_age_ratio` is INERT in this call: with `infra_eoh_override`
    # supplied the allocation never recomputes infrastructure EOH. The age
    # reaches the result through the pipeline above, which set that EOH.
    stew = stewardship_allocation(
        capital_stock_teh=capital, capital_age_ratio=age, epsilon=epsilon,
        available_teh=float("inf"),
        infra_eoh_override=by_domain["infrastructure"],
    )["teh_required"]
    care = aggregate_care_stipend_from_demographics(population, epsilon,
                                                    age_fractions=age_fractions)

    teh = {
        "mint":                 mint,
        "levy":                 levy,
        "guf_uncapped":         guf_uncapped,
        "guf":                  guf,
        "guf_unpaid":           guf_uncapped - guf,
        "guf_basis":            guf_basis,
        "guf_share_of_mint":    guf_uncapped / mint if mint > 0.0 else 0.0,
        "guf_payable_ceiling":  payable,
        "d3_consumption":       consumption,
        "guarantee_design":     guarantee,
        "guarantee_base":       base,
        "guarantee_owed":       owed,
        "guarantee_recipients": owed / g["total_per_person"] if g["total_per_person"] > 0.0 else 0.0,
        "inflow":               inflow,
        "stationary":           inflow >= owed,
        "shortfall":            deficit,
        "shortfall_share":      deficit / owed if owed > 0.0 else 0.0,
        "trust_start":          trust_start,
        "years_covered":        (trust_start / deficit) if deficit > 0.0 else None,
        # Stewardship and care requirement: paid at the mint, owed by no one
        # else. `fiscal_snapshot` reports the same quantity under this key.
        "paid_by_mint":         stew + care,
    }

    return {
        "epsilon":     epsilon,
        "standard":    standard,
        "personal_base": base,
        "labour":      labour,
        "teh":         teh,
        "stationary":  labour["stationary"] and teh["stationary"],
        "capital_stock_teh":    capital,
        "capital_supplied":     capital_stock_teh is not None,
        "capital_source": (
            "passed in by the caller" if capital_stock_teh is not None
            else "NOT SUPPLIED — the canonical arc's stock at this ε and population"
        ),
        "capital_age_ratio":    age,
        "capital_age_supplied": capital_age_ratio is not None,
        "capital_age_source": (
            "passed in by the caller" if capital_age_ratio is not None
            else "NOT SUPPLIED — CAPITAL_AGE_RATIO_DEFAULT"
        ),
        "adult_share_source": ("derived from the supplied age mix" if share_from_ages
                               else "passed in by the caller" if adult_share is not None
                               else "NOT SUPPLIED — the shipped age weights"),
        "age_fractions_source": ("passed in by the caller" if age_fractions is not None
                                 else "NOT SUPPLIED — the shipped AGE_GROUPS mix"),
        "doctrine":    "minted TEH is the wage (author decision, 2026-09-15)",
    }


def stationarity_arc(
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **kw: Any,
) -> list[dict]:
    """Both sides at each reporting point. units: as `stationarity_at`."""
    return [stationarity_at(e, **kw) for e in points]


def stationary_bands(step: float = 0.01, **kw: Any) -> dict:
    """
    The ε range where each side stands still, and where both do.

    `step` is a scan resolution, not a domain quantity — the same convention as
    `arc_stability.stationary_band(tol=)`. Bands are threshold crossings, so
    their edges are reported to this resolution and no finer.

    Scans a grid at `step` and reuses `arc_stability.band_from_flags`, so a band
    that fails in its middle is reported as non-contiguous rather than spanned.
    Band edges are accurate to `step`.

    units: dimensionless ε.
    """
    n = max(2, int(round(EPSILON_ARC_MAX / step)))
    # Clamped: `i * 0.99 / n` lands on 0.9900000000000001 at the last point,
    # which the range check correctly refuses.
    rows = [stationarity_at(min(EPSILON_ARC_MAX, i * EPSILON_ARC_MAX / n), **kw) for i in range(n + 1)]
    return {
        "labour": band_from_flags([(r["epsilon"], r["labour"]["stationary"]) for r in rows]),
        "teh":    band_from_flags([(r["epsilon"], r["teh"]["stationary"]) for r in rows]),
        "both":   band_from_flags([(r["epsilon"], r["stationary"]) for r in rows]),
        # WHAT THE FEE ADDS, read off the same rows (2026-10-15): the levy does
        # not depend on the fee, so without one the inflow is the levy alone.
        # The verdict used to state that the fee carried the LOW end; on both
        # the reference and the US frame it carries the top.
        "teh_without_fee": band_from_flags(
            [(r["epsilon"], r["teh"]["levy"] >= r["teh"]["guarantee_owed"]) for r in rows]),
        "levy_to_cover": _levy_to_cover(rows, kw.get("guf_cap", "payable")),
        "step":   step,
    }


def _levy_to_cover(rows: list[dict], guf_cap: float | str | None) -> dict:
    """
    The smallest flat levy that holds the TEH side still at every scanned ε —
    what closes a gap at the top, REPORTED and never applied (the shipped rate
    is a decision, `SUFF_LEVY_RATE`).

    Per point it is `assessed_levy_rate` against the fee the cap would let in.
    Under `payable` the inflow is min(levy + fee, mint − D3), so no levy covers
    a point where mint − D3 < owed, and the result says `feasible: False`
    rather than return a rate that does not close it. An extremum on the
    band's grid, to its step.
    """
    rate, at, feasible = 0.0, None, True
    for r in rows:
        t = r["teh"]
        fee = (min(t["guf_uncapped"], guf_cap * t["mint"])
               if isinstance(guf_cap, float) else t["guf_uncapped"])
        if guf_cap == "payable" and t["mint"] - t["d3_consumption"] < t["guarantee_owed"]:
            feasible = False
        need = assessed_levy_rate(t["guarantee_owed"], t["mint"],
                                  guf_revenue=fee)["pay_as_you_go_rate"]
        if at is None or need > rate:
            rate, at = need, r["epsilon"]
    return {"rate": rate, "binding_epsilon": at, "feasible": feasible}


def drawdown(
    years: int,
    epsilon_start: float = 0.0,
    epsilon_end: float = EPSILON_ARC_MAX,
    **kw: Any,
) -> dict:
    """
    A Trust carried along an arc: T' = T + levy + GUF − guarantee each year.
    GUF is `stationarity_at`'s, collected (the payable cap), on the same
    parcels `stationarity_report` defaults to.

    THE PATH IS A SCENARIO CHOICE. ε moves linearly from `epsilon_start` to
    `epsilon_end` over `years`; how fast a real economy advances is unknown, so
    `years` has no default. Setting `epsilon_start == epsilon_end` holds the
    economy at one point, which is the stand-still question over time.

    Points are evaluated on a 0.01 grid and cached, so a long arc does not
    re-price the land fee every year.

    Returns:
        dict with `fails_in_year` (None if it holds), `fails_at_epsilon`,
        `trust_min`, `trust_min_epsilon`, `trust_end`, and
        `labour_short_epsilons` — the ε on the path where the labour side fails.
    """
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")
    # THE STANDARD METHOD (2026-10-15, author): the land fee as
    # `stationarity_report` prices it — the urban sample unless the caller
    # names its own parcels (an empty list for no land, or `guf_parcels=None`
    # with a count for the per-parcel half). Until today a drawdown carried NO
    # fee, so its Trust ran on the levy alone while stationarity's ran on both.
    if "guf_parcels" not in kw:
        kw = {**kw, "guf_parcels": make_urban_collective()}
    trust = float(kw.get("trust_start", 0.0))
    cache: dict[float, dict] = {}
    fail_year: int | None = None
    fail_eps: float | None = None
    t_min, e_min = trust, epsilon_start
    labour_short: list[float] = []
    for y in range(years + 1):
        e = epsilon_start + (epsilon_end - epsilon_start) * y / years
        key = round(e, 2)
        if key not in cache:
            cache[key] = stationarity_at(key, **kw)
        row = cache[key]
        # BOUND to core's rule rather than restating it (2026-09-15, when
        # `trust_management` adopted the same arithmetic): balance − owed +
        # inflows. dep_rate and div_rate no longer enter the balance, so the
        # two cannot drift apart at any rate.
        trust = trust_management(
            trust, row["teh"]["levy"], 0.0, row["teh"]["guarantee_owed"],
            guf_revenue=row["teh"]["guf"],
        )["trust_end"]
        if trust < t_min:
            t_min, e_min = trust, e
        if trust < 0.0 and fail_year is None:
            fail_year, fail_eps = y, e
        if not row["labour"]["stationary"] and key not in labour_short:
            labour_short.append(key)
    return {
        "years":                 years,
        "epsilon_start":         epsilon_start,
        "epsilon_end":           epsilon_end,
        "fails_in_year":         fail_year,
        "fails_at_epsilon":      fail_eps,
        "trust_min":             t_min,
        "trust_min_epsilon":     e_min,
        "trust_end":             trust,
        "labour_short_epsilons": labour_short,
    }


def reserve_plan(
    epsilon: float = 0.40,
    *,
    years_of_guarantee: float,
    insure_at_epsilon: float = EPSILON_ARC_MAX,
    build_years: float = 25.0,
    **kw: Any,
) -> dict:
    """
    What a reserve of N years of guarantee costs, and whether the shipped levy
    would ever build one. REPORTING ONLY.

    THE RULE (author, 2026-09-16): hold the Trust's slack as a DECLARED reserve
    with a ceiling — "N years of the guarantee, held against an arc that may
    not advance" — rather than as the residue of a levy sized to the far end of
    the arc. The levy itself is then assessed on the realized obligation
    (`fiscal.assessed_levy_rate`), and the reserve is a second, named line.

    N IS REQUIRED AND HAS NO DEFAULT. A shipped reserve level is a rationing
    rule about how much the present owes the future, the same reason
    `scenarios/frailty` ships no care default.

    PEG N TO THE ε YOU ARE INSURING AGAINST, NOT TO TODAY. The guarantee at
    ε=0.99 is ~35× the guarantee at subsistence, so "ten years of cover" sized
    at the bottom buys almost nothing at the top. `insure_at_epsilon` is that
    choice, declared.

    THE FINDING THIS FUNCTION EXISTS TO SHOW: read as a reserve rule, the
    shipped flat rate banks 17.8 years of guarantee per year at ε=0 and NONE at
    ε=0.99 — it fills instantly where a reserve is least needed and cannot fill
    at all where it is, because at the corner the rate IS the requirement.

    Args:
        epsilon: Where the collective is now — the reserve is paid from here.
        years_of_guarantee: N. Required; must be > 0.
        insure_at_epsilon: The ε whose guarantee N is counted in.
        build_years: Over how many years the reserve is built.
        **kw: Forwarded to `stationarity_at` (population, guarantee design,
            need_fraction, guf_parcels, levy_rate, …).

    Returns:
        dict with `target_teh`, `increment_rate` (share of the mint),
        `increment_per_capita`, `shipped_surplus`, `years_to_fill_at_shipped_rate`
        (None when the shipped rate never fills it), `fills_at_shipped_rate`,
        the `assessed` rate including the increment, and a verdict.

    Raises:
        ValueError: on a non-positive N or build horizon, or an ε out of range.
    """
    if years_of_guarantee <= 0.0:
        raise ValueError(f"years_of_guarantee must be > 0, got {years_of_guarantee}")
    if build_years <= 0.0:
        raise ValueError(f"build_years must be > 0, got {build_years}")
    if not 0.0 <= insure_at_epsilon <= EPSILON_ARC_MAX:
        raise ValueError(
            f"insure_at_epsilon must be in [0.0, 0.99], got {insure_at_epsilon}")

    population = float(kw.get("population", REFERENCE_FRAME_POPULATION))
    here = stationarity_at(epsilon, **kw)["teh"]
    insured = stationarity_at(insure_at_epsilon, **kw)["teh"]

    target = years_of_guarantee * insured["guarantee_owed"]
    increment = target / (build_years * here["mint"]) if here["mint"] > 0.0 else float("inf")
    # The shipped levy's surplus over what is owed here — what a flat rate
    # banks per year, which is the quantity the reserve rule replaces.
    surplus = here["levy"] + here["guf"] - here["guarantee_owed"]
    fills = surplus > 0.0
    assessed = assessed_levy_rate(
        here["guarantee_owed"], here["mint"],
        guf_revenue=here["guf"], reserve_increment=increment,
    )
    return {
        "epsilon":                       epsilon,
        "years_of_guarantee":            years_of_guarantee,
        "insure_at_epsilon":             insure_at_epsilon,
        "build_years":                   build_years,
        "guarantee_here":                here["guarantee_owed"],
        "guarantee_insured":             insured["guarantee_owed"],
        "target_teh":                    target,
        "mint":                          here["mint"],
        "increment_rate":                increment,
        "increment_per_capita":          increment * here["mint"] / population,
        "shipped_surplus":               surplus,
        "shipped_surplus_in_years_here": surplus / here["guarantee_owed"] if here["guarantee_owed"] > 0.0 else None,
        "years_to_fill_at_shipped_rate": (target / surplus) if fills else None,
        "fills_at_shipped_rate":         fills,
        "assessed":                      assessed,
        "reporting_only":                True,
        "verdict": (
            f"{years_of_guarantee:g} years of the ε={insure_at_epsilon:.2f} guarantee "
            f"is {target:,.0f} TEH. Built over {build_years:g} years from ε={epsilon:.2f}, "
            f"that is {increment * 100:.3f}% of the mint "
            f"({increment * here['mint'] / population:,.3f} TEH per person per year) "
            f"on top of a pay-as-you-go rate of "
            f"{assessed['pay_as_you_go_rate'] * 100:.3f}%. "
            + (f"The shipped flat levy banks it in "
               f"{target / surplus:,.1f} years."
               if fills else
               "The shipped flat levy NEVER fills it here — at this ε the rate "
               "is the requirement and there is no surplus.")
        ),
    }


def stationarity_report(epsilon: float = 0.40, **kw: Any) -> dict:
    """The report. CLI: `eoh scenario run stationarity`.

    THE FEE IS PART OF THE CONFIGURATION, AND UNTIL 2026-09-16 THIS REPORT RAN
    WITHOUT ONE. `stationarity_at` takes a parcel SAMPLE and prices the land fee
    from it; given none, `guf` is 0.0 and the TEH side has only the levy. The CLI
    passed no parcels, so the published verdict read "TEH stands still nowhere"
    at every ε — true for a collective that holds no land, and presented as the
    framework's answer. With the urban sample the record names as the adopted
    basis, the TEH side stands still on [0.00, 0.99] at the shipped 1,000 h base.

    So the report now supplies that inventory when the caller names none, and
    RETURNS the configuration it ran under. A caller passing `guf_parcels`
    explicitly — including an empty list, for the no-land case — is honoured.
    """
    if "guf_parcels" not in kw:
        kw = {**kw, "guf_parcels": make_urban_collective()}
    here = stationarity_at(epsilon, **kw)
    bands = stationary_bands(**kw)
    arc = stationarity_arc(**kw)

    def _band(b: dict) -> str:
        if not b["any_stationary"]:
            return "nowhere"
        s = f"[{b['lower']:.2f}, {b['upper']:.2f}]"
        return s if b["contiguous"] else s + " (NOT contiguous)"

    # What the ADOPTED rule would charge here (author, 2026-09-16): the levy
    # assessed on the realized obligation. Reported alongside the shipped flat
    # rate rather than replacing it as this report's default — the TEH side
    # exists to test whether inflows cover the guarantee, and assessing the
    # levy FROM the guarantee would make that verdict true by construction.
    assessed = assessed_levy_rate(
        here["teh"]["guarantee_owed"], here["teh"]["mint"],
        guf_revenue=here["teh"]["guf"],
    )
    # The rates APPLIED, not the shipped ones: a caller's levy_rate= or
    # need_fraction= was run and the verdict printed SUFF_* beside it.
    levy_rate = kw.get("levy_rate", SUFF_LEVY_RATE)
    need = kw.get("need_fraction")
    need = SUFF_NEED_FRACTION if need is None else need
    fee_priced = here["teh"]["guf"] > 0.0
    cover = bands["levy_to_cover"]
    whole_arc = bands["teh"]["lower"] == 0.0 and bands["teh"]["upper"] == EPSILON_ARC_MAX \
        and bands["teh"]["contiguous"]
    return {
        "epsilon":  epsilon,
        "here":     here,
        "arc":      arc,
        "bands":    bands,
        "assessed_levy": assessed,
        "verdict": (
            f"At ε={epsilon:.2f}, base={here['personal_base']:,.0f} h, guarantee="
            f"{here['teh']['guarantee_design']!r}: labour "
            f"{'stands still' if here['labour']['stationary'] else 'is SHORT'}, "
            f"TEH {'stands still' if here['teh']['stationary'] else 'is SHORT'}. "
            f"Labour stands still on {_band(bands['labour'])}, TEH on "
            f"{_band(bands['teh'])}, both on {_band(bands['both'])} "
            f"(to ±{bands['step']}). Under the doctrine that minted TEH is the "
            "wage, the Trust owes only the guarantee. Configuration: "
            f"guarantee={here['teh']['guarantee_design']!r} at "
            f"need={need:g}, levy={levy_rate:.3%}, land fee "
            f"{('priced as ' + here['teh']['guf_basis']) if fee_priced else 'ABSENT'}"
            + (f"; without the fee TEH stands still on {_band(bands['teh_without_fee'])}."
               if fee_priced else ".")
            + (" No flat levy holds TEH on the whole arc: somewhere the mint less D3 "
               "is below the guarantee." if not cover["feasible"] else
               f" The smallest flat levy that holds TEH on the whole arc is "
               f"{cover['rate']:.4%} (binding at ε {cover['binding_epsilon']:.2f})"
               + ("." if whole_arc else
                  f" — that closes the gap; {levy_rate:.3%} is applied."))
            + ("" if here["capital_supplied"] else
               " Capital was NOT supplied: every point reads the canonical arc's "
               "stock at its own ε, not an economy's.")
            + ("" if here["capital_age_supplied"] else
               " Capital age was NOT supplied: upkeep reads "
               "CAPITAL_AGE_RATIO_DEFAULT.")
            + ("" if "NOT SUPPLIED" not in here["adult_share_source"] else
               " Adult share was NOT supplied: supply reads the shipped age weights.")
        ),
        # WHAT WAS RUN, returned rather than left to be inferred. A band is only
        # meaningful against its configuration, and the fee's presence changes
        # the TEH side from "nowhere" to the whole arc.
        "configuration": {
            "guarantee_design": here["teh"]["guarantee_design"],
            "need_fraction":    need,
            "levy_rate":        levy_rate,
            "land_fee_priced":  fee_priced,
            "land_fee_basis":   here["teh"]["guf_basis"],
            "personal_base":    here["personal_base"],
        },
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# Access to registered work, beside the personal EOH it serves (2026-09-30)
# ---------------------------------------------------------------------------
#
# Author, 2026-09-30: the minimum market wage is a CHARTER choice, and the model
# proceeds with NONE. The register holds the 1:1 base on the mint. The register
# is mostly personal EOH, which reduces what members need; with higher
# automation they may need less TEH. The question to WATCH is whether someone
# can walk away to registered work instead, and whether that registered work
# covers its members.


def registered_work_access(
    epsilon: float,
    population: float = REFERENCE_FRAME_POPULATION,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    adult_share: float | None = None,
    **pipeline_kwargs: Any,
) -> dict:
    """
    Can a member walk away to registered work, and does it cover the members?

    Three blocks, per capita unless named per adult, all from ONE pipeline call:

    PERSONAL EOH SERVED — the obligation the register mostly consists of, split
    by who serves it:
        machine            served by capital; costs no TEH at the floor
        human_registered   on the ledger; paid by the mint, and what members
                           spend TEH on (D3 prices each hour at M_FLOOR)
        human_off_ledger   self-provision; paid in members' own time, not TEH

    ACCESS — the walk-away question:
        registered_hours_per_adult     registered work available per
                                       labour-supplying adult, if spread evenly
        reach                          registered hours over total labour supply
                                       — equally, the fraction of an adult's
                                       working year the register could fill
                                       (the two are one ratio by algebra, so
                                       only one is reported)
        time_left_per_adult            capacity minus the adult's share of
                                       off-ledger self-provision: the time free
                                       to take registered work at all
        walkaway_fits_time             registered hours per adult ≤ time left.
                                       This reduces to human hours per adult ≤
                                       capacity — the labour side of
                                       `stationarity_at` in walk-away form. It
                                       does not fire on the shipped arc; it
                                       fires when capacity is short.

    COVERAGE — does registered work cover its members:
        teh_need_per_capita            D3: registered human personal hours ×
                                       M_FLOOR — the TEH members need
        mint_per_capita                what registered work pays
        cover                          mint / need
        cover_structural_minimum       mean multiplier / M_FLOOR

    COVER CANNOT FALL BELOW m / M_FLOOR, BY CONSTRUCTION — and that is the 1:1
    base, not a finding. Every registered personal hour is both a need of
    M_FLOOR and a mint of m; non-personal registered work only adds mint. So
    "does registered work cover its members" is answered YES structurally, IN
    AGGREGATE. What is NOT structural, and what this reports so it can be
    watched: ACCESS. The figures are averages over an even spread of the
    register; the model has no variable for who the register admits
    (record/theory.md#capture-aggregate-bounded), so an average that covers
    says nothing about a member the register does not reach.

    ε-behaviour: need is near zero at subsistence (the register admits little),
    rises with registration, and turns down at the top of the arc as machines
    take personal EOH — the "less TEH with more automation" the author
    expected, which holds only past the turn. Read the turn off
    `registered_work_arc`, not off this docstring.
    """
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

    p = eoh_to_teh_pipeline(epsilon, population=population, **pipeline_kwargs)
    personal = float(p["eoh_by_domain"]["personal"])
    human_personal = float(human_eoh_per_domain(p["eoh_by_domain"], epsilon)["personal"])
    reg_personal = float(p["registered_eoh_by_domain"]["personal"])
    need = d3_consumption(personal, float(p["registration_by_domain"]["personal"]), human_personal)
    mint = float(p["teh_created"])
    m = float(p["mean_multiplier"])

    # One population on both sides (2026-10-14): an age mix given to the
    # pipeline sets the adult share too, unless one is given.
    share = (capacity_weighted_adult_share(pipeline_kwargs.get("age_distribution"))
             if adult_share is None else adult_share)
    adults = population * share
    reg_per_adult = float(p["registered_eoh"]) / adults
    off_ledger = max(0.0, human_personal - reg_personal)
    time_left = max(0.0, adult_capacity_h_yr - off_ledger / adults)
    supply = labor_supply_per_capita(adult_capacity_h_yr=adult_capacity_h_yr,
                                     adult_share=share)

    return {
        "epsilon": epsilon,
        "personal_served": {
            "gross": personal / population,
            "machine": (personal - human_personal) / population,
            "human_registered": reg_personal / population,
            "human_off_ledger": off_ledger / population,
        },
        "access": {
            "registered_hours_per_capita": float(p["registered_eoh"]) / population,
            "registered_hours_per_adult": reg_per_adult,
            "reach": (float(p["registered_eoh"]) / population) / supply,
            "time_left_per_adult": time_left,
            "walkaway_fits_time": reg_per_adult <= time_left,
        },
        "coverage": {
            "teh_need_per_capita": need / population,
            "mint_per_capita": mint / population,
            "cover": (mint / need) if need > 0.0 else None,
            "cover_structural_minimum": m / M_FLOOR,
        },
        "min_market_wage": None,
        "min_market_wage_basis": "charter choice; the model proceeds with none (author, 2026-09-30)",
        "averages_only": (
            "every figure assumes the register is spread evenly; who it admits "
            "is not represented"
        ),
        "reporting_only": True,
    }


def registered_work_arc(
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **kw: Any,
) -> dict:
    """
    `registered_work_access` along the arc, plus where TEH need per member
    turns down — the point past which more automation means less TEH needed.
    The turn is searched on a fine grid, not read off the reporting points
    (mode 3).
    """
    rows = [registered_work_access(e, **kw) for e in points]
    grid = [ARC_REPORTING_POINTS[-1] * i / 100 for i in range(101)]
    need = [registered_work_access(e, **kw)["coverage"]["teh_need_per_capita"] for e in grid]
    peak = grid[need.index(max(need))]
    return {
        "rows": rows,
        "need_peaks_at_epsilon": peak,
        "need_at_peak": max(need),
        "need_at_top": need[-1],
        "reporting_only": True,
    }
