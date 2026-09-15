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
    national parcels per person. The shipped archetypes are synthetic, and
    `record/guf.md` records the fee's level as structurally mis-set.
  * `v1` AND `v2` ARE PROPOSED, NOT ADOPTED. `shipped` is the default design.
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
    stewardship_allocation,
    sufficiency_guarantee,
)
from hours_eoh.data import (
    ARC_REPORTING_POINTS,
    MEASURED_CAPACITY_H_YR,
    M_FLOOR,
    PERSONAL_EOH_BASE,
    SUFF_LEVY_RATE,
    US_REFERENCE_POPULATION,
)
from hours_eoh.land.collective import compute_collective_guf
from hours_eoh.reference.parcels import national_parcel_count
from hours_eoh.scenarios.arc_stability import STANDARDS, band_from_flags, stability_at
from hours_eoh.scenarios.feasibility import labor_supply_per_capita

__all__ = [
    "GUARANTEE_DESIGNS",
    "GUF_CAP_RULES",
    "d3_consumption",
    "stationarity_at",
    "stationarity_arc",
    "stationary_bands",
    "drawdown",
    "stationarity_report",
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
    personal_registration_share: float,
    need_fraction: float | None,
    personal_eoh_base: float,
) -> tuple[float, dict]:
    g = sufficiency_guarantee(population, epsilon, personal_eoh_base=personal_eoh_base)
    need = g["floor_fraction"] if need_fraction is None else need_fraction
    if design == "shipped":
        return g["total_cost_teh"], g
    if design == "v1":
        return population * personal_registration_share * need * g["total_per_person"], g
    return population * personal_registration_share * g["total_per_person"], g


def stationarity_at(
    epsilon: float = 0.40,
    *,
    population: float = 1.0e6,
    standard: str | None = None,
    personal_base: float | None = None,
    capital_stock_teh: float | None = None,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    guarantee: str = "shipped",
    need_fraction: float | None = None,
    levy_rate: float = SUFF_LEVY_RATE,
    guf_parcels: list[dict] | None = None,
    guf_parcel_count: float | None = None,
    guf_cap: float | str | None = None,
    trust_start: float = 0.0,
) -> dict:
    """
    Both sides at one ε. Can the collective stand still here?

    Governing tests, per year:

        LABOUR   supply_per_capita          >= human_hours_per_capita
                 (survival_met: supply      >= human personal hours)
        TEH      levy + GUF                 >= guarantee owed

    with `human_hours` the pipeline's human EOH under its own split, `levy` =
    `levy_rate × mint`, and GUF = a parcel sample's revenue per parcel ×
    `guf_parcel_count`, optionally capped.

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
            guarantee. None uses the shipped decaying fraction.
        levy_rate: Levy as a share of the mint.
        guf_parcels: A parcel SAMPLE that prices the fee. None → no land fee,
            and `guf` is 0.0.
        guf_parcel_count: Parcels the collective holds. None → population × the
            measured national parcels per person.
        guf_cap: None (uncapped), a float share of the mint, or `payable`.
        trust_start: The inheritance, TEH. Default 0.0 — a collective starting
            from subsistence has none.

    Returns:
        dict with `labour`, `teh`, `stationary` (both sides) and the inputs.

    Raises:
        ValueError: on an ε, standard, design, cap rule or share out of range.
    """
    if not 0.0 <= epsilon <= 0.99:
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
    capital = resolve_capital_stock(capital_stock_teh, epsilon)
    p = eoh_to_teh_pipeline(
        epsilon=epsilon, population=population, capital_stock=capital,
        **({"personal_standard": standard} if at_standard
           else {"personal_base": base}),
    )
    by_domain = p["eoh_by_domain"]
    human = human_eoh_per_domain(by_domain, epsilon)
    r_personal = p["registration_by_domain"]["personal"]

    # ---- LABOUR -----------------------------------------------------------
    supply = labor_supply_per_capita(adult_capacity_h_yr=adult_capacity_h_yr)
    human_hours = p["human_eoh"] / population
    human_personal = human["personal"] / population
    compass = stability_at(
        epsilon, capital_stock_teh=capital, population=population,
        adult_capacity_h_yr=adult_capacity_h_yr, standard=standard,
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
    }

    # ---- TEH --------------------------------------------------------------
    mint = float(p["teh_created"])
    levy = levy_rate * mint
    consumption = d3_consumption(by_domain["personal"], r_personal, human["personal"])

    guf_uncapped = 0.0
    if guf_parcels:
        count = (population * national_parcel_count() / US_REFERENCE_POPULATION
                 if guf_parcel_count is None else guf_parcel_count)
        sample = compute_collective_guf(guf_parcels, epsilon)
        guf_uncapped = sample["guf_net_inflow"] / len(guf_parcels) * count
    payable = max(0.0, mint - levy - consumption)
    if guf_cap is None:
        guf = guf_uncapped
    elif guf_cap == "payable":
        guf = min(guf_uncapped, payable)
    else:
        guf = min(guf_uncapped, float(guf_cap) * mint)

    owed, g = _guarantee_owed(guarantee, population, epsilon, r_personal,
                              need_fraction, base)
    inflow = levy + guf
    deficit = max(0.0, owed - inflow)

    # `capital_age_ratio` is INERT here: with `infra_eoh_override` supplied the
    # allocation never recomputes infrastructure EOH, so the age ratio does not
    # reach the result. Passed by keyword at the pipeline's own default so it
    # reads as that, not as a domain figure.
    stew = stewardship_allocation(
        capital_stock_teh=capital, capital_age_ratio=0.5, epsilon=epsilon,
        available_teh=float("inf"),
        infra_eoh_override=by_domain["infrastructure"],
    )["teh_required"]
    care = aggregate_care_stipend_from_demographics(population, epsilon)

    teh = {
        "mint":                 mint,
        "levy":                 levy,
        "guf_uncapped":         guf_uncapped,
        "guf":                  guf,
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
    n = max(2, int(round(0.99 / step)))
    # Clamped: `i * 0.99 / n` lands on 0.9900000000000001 at the last point,
    # which the range check correctly refuses.
    rows = [stationarity_at(min(0.99, i * 0.99 / n), **kw) for i in range(n + 1)]
    return {
        "labour": band_from_flags([(r["epsilon"], r["labour"]["stationary"]) for r in rows]),
        "teh":    band_from_flags([(r["epsilon"], r["teh"]["stationary"]) for r in rows]),
        "both":   band_from_flags([(r["epsilon"], r["stationary"]) for r in rows]),
        "step":   step,
    }


def drawdown(
    years: int,
    epsilon_start: float = 0.0,
    epsilon_end: float = 0.99,
    **kw: Any,
) -> dict:
    """
    A Trust carried along an arc: T' = T + levy + GUF − guarantee each year.

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
        trust = trust + row["teh"]["inflow"] - row["teh"]["guarantee_owed"]
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


def stationarity_report(epsilon: float = 0.40, **kw: Any) -> dict:
    """The report. CLI: `eoh scenario run stationarity`."""
    here = stationarity_at(epsilon, **kw)
    bands = stationary_bands(**kw)
    arc = stationarity_arc(**kw)

    def _band(b: dict) -> str:
        if not b["any_stationary"]:
            return "nowhere"
        s = f"[{b['lower']:.2f}, {b['upper']:.2f}]"
        return s if b["contiguous"] else s + " (NOT contiguous)"

    return {
        "epsilon":  epsilon,
        "here":     here,
        "arc":      arc,
        "bands":    bands,
        "verdict": (
            f"At ε={epsilon:.2f}, base={here['personal_base']:,.0f} h, guarantee="
            f"{here['teh']['guarantee_design']!r}: labour "
            f"{'stands still' if here['labour']['stationary'] else 'is SHORT'}, "
            f"TEH {'stands still' if here['teh']['stationary'] else 'is SHORT'}. "
            f"Labour stands still on {_band(bands['labour'])}, TEH on "
            f"{_band(bands['teh'])}, both on {_band(bands['both'])} "
            f"(to ±{bands['step']}). Under the doctrine that minted TEH is the "
            "wage, the Trust owes only the guarantee."
        ),
        "reporting_only": True,
    }
