"""
GUF's magnitude — the derived revenue target, and the tariff the cost implies.

REPORTING ONLY. No constant moves here. `GUF_USE_SCALE_FACTOR` stays at 100.0
and the ten `GUF_USE_*` coefficients are untouched; `TestMagnitudeChangesNothing`
fails the moment that stops being true.

WHY THERE IS ANYTHING LEFT TO DO AFTER PHASE 2
----------------------------------------------
Phase 2 (`scenarios/servicing_census.py`) measured the quantity `GUF_USE_*`'s own
`resolves_by` names and found the ×100 fit overshooting ~35× in aggregate. It
left two things, and this module is both of them.

OPTION 1 — THE TARGET WAS INCOMPLETE ON THE PARTITION'S OWN TERMS.
Phase 2 compared the fee against SERVICING alone. But the Phase 4 partition,
signed off 2026-08-17, says GUF carries *the recurring flow* and the ecological
domain carries the stock — and the recurring flow has two measured halves, not
one:

    target(class) = servicing(class) + stewardship(class)

Servicing is what the BUILT ENVIRONMENT on the land demands (roads, utilities,
inspection, title). Stewardship is what the LAND demands to hold its condition.
The two censuses are disjoint by construction and a test already enforces it, so
they add rather than overlap. Adding the second half is what makes the target
match the definition the partition adopted.

OPTION 2 — THE FEE HAS ONE SCALING BASIS AND THE COST HAS THREE.
`base_fee` is A(p)·L(p)·U(p,ε)·D(p)·Z(p), and A is in Standard Land Units, which
are an AREA unit. So the fee is strictly proportional to ground area and to
nothing else. Re-cut by what each servicing occupation's cost actually follows
(`reference/servicing.SCALING_BASIS`), only 41.9% of the measured hours scale
with area; 44.5% scale with the count of separately-held parcels and 13.6% with
throughput. A fee with one basis cannot track a cost with three, at any
multiplier. `two_part_rates()` gives the form that can.

WHAT THIS CORRECTS IN THE RECORD
--------------------------------
Phase 2's stated mechanism for the urban/rural spread — "the fee is per-SLU, so
packing a hectare with more parcels multiplies the charge while the roads, pipes
and inspections serving that hectare do not" — IS FALSE, and
`subdivision_invariance()` demonstrates it rather than asserting it: splitting
every parcel in a collective in two leaves the fee per hectare EXACTLY
unchanged, because each half carries half the SLU. Parcel count does not enter
the fee at all. That is not a small correction, because it relocates the defect:
the urban 18× is driven by the L·U·D product — the location-value index and the
ten ratios — which is precisely the part Phase 2 correctly said its aggregate
census could not settle. And it sharpens Option 2 from "rescale the density
term" to "the fee has no per-parcel term to rescale".

WHAT THIS DOES NOT SETTLE
-------------------------
The ten ratios, still. Both censuses are aggregates over land classes, not over
use categories, and no occupational data is coded by the land use it serves.
Option 1 settles the LEVEL for the classes both censuses reach, and Option 2
settles the FORM. Neither settles the shape of the table.

The per-parcel rate, for want of one number. The parcel-scaling hours are
measured (404,600 workers); converting them to a rate needs a national parcel
count, which this repo does not carry. It is EXCLUDED, not costed at zero, and
names the field that would close it.

Layer: scenarios/ — imports core/, land/ and reference/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.data import SLU_HECTARES
from hours_eoh.land.collective import (
    compute_collective_guf,
    make_rural_collective,
    make_urban_collective,
)
from hours_eoh.land.guf import (
    FEE_BASES,
    PSI_POLICIES,
    TERM_BASIS,
    USE_CATEGORIES,
    epsilon_scaling,
    labor_content_scaling,
    psi_application,
)
from hours_eoh.reference import servicing
from hours_eoh.scenarios.food_conservation import hours_per_worker_year
from hours_eoh.scenarios.land_stewardship import ADOPTED_SCOPE, stewardship_intensities
from hours_eoh.scenarios.servicing_census import census

#: The instrument that would turn measured parcel-scaling HOURS into a
#: per-parcel RATE. Names the FIELD and not merely a source — the rule three
#: findings in this repo have now shared.
PARCEL_COUNT_RESOLVES_BY: str = (
    "A national count of separately-assessed land parcels. FIELD: the record "
    "count of the county assessor parcel rolls, aggregated nationally and "
    "restricted to the land classes SERVICED_LAND_CLASSES admits. Not a housing-"
    "unit count — a multi-unit building is one parcel and many units, and the "
    "occupations that scale per parcel (title search, building inspection, "
    "refuse round) follow the parcel, not the unit."
)


# ===========================================================================
# Option 1 — the derived revenue target
# ===========================================================================

def recurring_target_by_class(
    servicing_scope: str = "core",
    stewardship_scope: str = ADOPTED_SCOPE,
) -> list[dict]:
    """
    The recurring flow GUF must fund, per US land-use class.

    Governing sum, per ERS Major Land Uses class c:

        target(c) = servicing(c) + stewardship(c)      [h/ha·yr]

    where `servicing(c)` is the census rate for the scope's serviced classes and
    `None` for a class that receives none, and `stewardship(c)` is the per-class
    intensity from the stewardship census, `None` where unpriced.

    units: labour-hours per hectare per year.

    ε-behaviour: NONE, deliberately. Both inputs are censuses — snapshots of a
    present-day economy — so the target carries no automation scaling. The fee it
    is compared against carries one automation response under the default policy
    (α(ε) inside U) and carried two before Ψ was retired. The like-for-like
    comparison is at ONE ε either way, and `target_vs_realised` states which.

    EXCLUDED IS NOT ZERO. A class missing either half is marked incomplete and
    its known half is reported as a LOWER bound on the target, never as the
    target. Seven of the nine classes are incomplete on the stewardship side
    alone.

    Worked example (Land in urban areas, core/declared): servicing 45.92 +
    stewardship 4.35 = 50.27 h/ha·yr, complete on both halves.

    Raises:
        ValueError: if either scope is not one its census recognises.
    """
    serviced = servicing.SERVICED_LAND_CLASSES
    if servicing_scope not in serviced:
        raise ValueError(
            f"servicing_scope must be one of {sorted(serviced)}, got {servicing_scope!r}"
        )

    servicing_rate = census(servicing_scope)["hours_per_hectare_year"]
    serviced_classes = set(serviced[servicing_scope])

    rows: list[dict] = []
    for r in stewardship_intensities(stewardship_scope):
        name = str(r["land_use"])
        sv = servicing_rate if name in serviced_classes else None
        st = r["hours_per_hectare_year"]
        known = [x for x in (sv, st) if x is not None]
        rows.append({
            "land_use":            name,
            "area_hectares":       r["area_hectares"],
            "servicing_h_per_ha":  sv,
            "stewardship_h_per_ha": st,
            "target_h_per_ha":     sum(known) if known else None,
            "complete":            sv is not None and st is not None,
            "missing": [
                half for half, val in (("servicing", sv), ("stewardship", st))
                if val is None
            ],
            "stewardship_reason":  r["reason"],
        })
    return rows


def target_vs_realised(
    epsilon: float = 0.40,
    stewardship_scope: str = ADOPTED_SCOPE,
) -> dict:
    """
    What the shipped fee charges per hectare, against the recurring flow the two
    censuses measure for the same land.

        realised(archetype) = compute_collective_guf(...) / Σ hectares
        target              = servicing + stewardship, over the land class the
                              archetype occupies

    units: labour-hours per hectare per year, and a dimensionless ratio.

    The URBAN row is like-for-like: urban parcels against `urban_upper` (every
    core servicing worker charged to urban land alone) plus urban stewardship.
    That scope errs AGAINST the finding — the true urban servicing rate is lower,
    which makes the overshoot larger, not smaller.

    The RURAL row is NOT, and says so rather than producing a number. The rural
    archetype is 70% agricultural by parcel, and cropland and pasture are in no
    serviced land class and are unpriced by the stewardship census — BOTH halves
    of the target are missing. Phase 2 compared rural against the `core` average,
    which is taken over urban land and rural highway corridor; that 1.12× is
    reproduced here as `phase_2_comparison` and flagged, not repeated as a
    finding.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    by_class = {
        r["land_use"]: r
        for r in recurring_target_by_class("core", stewardship_scope)
    }
    urban = by_class["Land in urban areas"]
    urban_servicing = census("urban_upper")["hours_per_hectare_year"]
    urban_stewardship = urban["stewardship_h_per_ha"]
    urban_target = urban_servicing + (urban_stewardship or 0.0)

    rows: list[dict] = []
    for name, factory, count in (
        ("urban", make_urban_collective, 10_000),
        ("rural", make_rural_collective, 1_000),
    ):
        parcels = factory(count)
        hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
        realised = compute_collective_guf(parcels, epsilon)["guf_gross_revenue"] / hectares
        if name == "urban":
            rows.append({
                "archetype":         name,
                "hectares":          hectares,
                "realised_h_per_ha": realised,
                "target_h_per_ha":   urban_target,
                "servicing_h_per_ha": urban_servicing,
                "stewardship_h_per_ha": urban_stewardship,
                "ratio":             realised / urban_target,
                "like_for_like":     True,
                "note": (
                    "urban parcels against urban land, both halves measured. The "
                    "stewardship half adds "
                    f"{(urban_stewardship or 0.0) / urban_target:.1%} of the target "
                    "and is the correction Option 1 exists to make."
                ),
            })
        else:
            rows.append({
                "archetype":         name,
                "hectares":          hectares,
                "realised_h_per_ha": realised,
                "target_h_per_ha":   None,
                "servicing_h_per_ha": None,
                "stewardship_h_per_ha": None,
                "ratio":             None,
                "like_for_like":     False,
                "phase_2_comparison": realised / census("core")["hours_per_hectare_year"],
                "note": (
                    "NO TARGET. The rural archetype is 70% agricultural by parcel; "
                    "cropland and pasture receive no measured servicing (they are in "
                    "no serviced land class) and are unpriced by the stewardship "
                    "census. Both halves are missing, so the 1.12× Phase 2 reported "
                    "was the fee against an average over urban land and rural highway "
                    "corridor — a different land class. Reported as "
                    "`phase_2_comparison`, not as a ratio."
                ),
            })

    urban_row = rows[0]
    return {
        "epsilon":     epsilon,
        "stewardship_scope": stewardship_scope,
        "rows":        rows,
        "urban_ratio": urban_row["ratio"],
        "verdict": (
            f"At ε={epsilon:g} the urban archetype realises "
            f"{urban_row['realised_h_per_ha']:,.1f} h/ha·yr against a recurring "
            f"target of {urban_target:,.2f} — servicing {urban_servicing:,.2f} plus "
            f"stewardship {(urban_stewardship or 0.0):,.2f} — a factor of "
            f"{urban_row['ratio']:,.1f}×. Adding the stewardship half moves Phase 2's "
            f"18.1× to {urban_row['ratio']:,.1f}×: the direction of the finding is "
            f"unchanged and the target is now the one the Phase 4 partition actually "
            f"defines. The rural comparison is withdrawn — see its note."
        ),
    }


def amenity_sensitivity(epsilon: float = 0.40) -> dict:
    """
    The urban comparison across all three stewardship scopes.

    The amenity weight is worth 41× in the stewardship census, so a comparison
    that leans on it has to show its corners. Here it is worth about 2.5×:
    urban stewardship is 0 (ecosystem), 4.35 (declared) or 92.93 h/ha·yr
    (with_amenity), against a servicing rate of 63.66 that does not move.

    units: dimensionless ratio.

    THE SIGN IS ROBUST AND THE MAGNITUDE IS NOT. The fee over-collects at every
    corner, so no scope choice reverses the finding; but quoting one figure
    without the band would overstate how well determined it is. Same posture as
    the stewardship census's own two surviving corners.
    """
    from hours_eoh.scenarios.land_stewardship import SCOPES

    urban_servicing = census("urban_upper")["hours_per_hectare_year"]
    parcels = make_urban_collective(10_000)
    hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
    realised = compute_collective_guf(parcels, epsilon)["guf_gross_revenue"] / hectares

    rows = []
    for scope in SCOPES:
        st = next(
            r["hours_per_hectare_year"]
            for r in stewardship_intensities(scope)
            if r["land_use"] == "Land in urban areas"
        )
        target = urban_servicing + (st or 0.0)
        rows.append({
            "stewardship_scope":    scope,
            "stewardship_h_per_ha": st,
            "target_h_per_ha":      target,
            "ratio":                realised / target,
        })

    ratios = [r["ratio"] for r in rows]
    return {
        "epsilon":            epsilon,
        "realised_h_per_ha":  realised,
        "servicing_h_per_ha": urban_servicing,
        "rows":               rows,
        "ratio_span":         (min(ratios), max(ratios)),
        "spread_factor":      max(ratios) / min(ratios),
        "sign_robust":        all(r > 1.0 for r in ratios),
        "verdict": (
            f"The fee over-collects at every scope corner — ratios "
            f"{min(ratios):,.1f}×–{max(ratios):,.1f}×, a spread of "
            f"{max(ratios) / min(ratios):.2f}×. The amenity weight sets the "
            f"magnitude here, not the sign, which is the same reading the "
            f"stewardship census reached about its own anchor crossing."
        ),
    }


def conservation_credit_check(
    epsilon: float = 0.40,
    stewardship_scope: str = ADOPTED_SCOPE,
) -> dict:
    """
    What conservation-classed land pays, against what the partition says it owes.

    `GUF_USE_CONSERVATION_CREDIT` is the only negative use coefficient, so a
    conservation parcel's base fee is a credit. Under the Phase 4 partition the
    same land owes a positive recurring stewardship flow, and the stewardship
    census measures it: forest-use land 0.182 h/ha·yr, federal parks and
    wildlife 0.161.

    Governing comparison, per hectare of conservation-classed land:

        notional = Ψ(ε) · base_fee / hectares          [< 0, the credit]
        realised = Ψ(ε) · max(guf_floor, ·) / hectares [= 0, the credit clipped]
        owed     = stewardship(class)                  [> 0]

    units: labour-hours per hectare per year.

    THE FLOOR IS THE FINDING. `ground_use_fee` clamps at `guf_floor`, default
    0.0, so the credit NEVER PAYS OUT — it can only take a fee to zero.
    Conservation land therefore pays exactly nothing while owing a measured
    positive flow, and the coefficient's notional value (−90 h/ha·yr on the rural
    archetype's conservation parcels, ~500× the flow) is realised nowhere. Both
    numbers are reported because both are wrong in different directions and only
    one of them is visible in any output the framework currently produces.

    THIS IS NOT AUTOMATICALLY A DEFECT. A credit can be the instrument by which a
    collective PAYS a steward for the flow — that is `soil_health_credit` and
    §7.2's Trust disbursement, and is coherent. What the check establishes is
    that the two are not reconciled anywhere: the credit is a fixed coefficient
    in the fee table, the owed flow is a measured intensity per land class, and
    nothing sets one against the other. Reported so the reconciliation is a
    decision rather than an oversight.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    rows = [
        r for r in recurring_target_by_class("core", stewardship_scope)
        if r["stewardship_h_per_ha"] is not None
        and r["land_use"] not in ("Land in urban areas",)
    ]

    # The archetype's own conservation parcels, so no location value is invented.
    parcels = [
        p for p in make_rural_collective(1_000)
        if p["use_category"] == "conservation"
    ]
    hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
    result = compute_collective_guf(parcels, epsilon)
    realised = result["guf_gross_revenue"] / hectares
    notional = result["psi"] * sum(
        row["base_fee"] for row in result["guf_by_parcel"]
    ) / hectares

    owed_lo = min(r["stewardship_h_per_ha"] for r in rows)
    owed_hi = max(r["stewardship_h_per_ha"] for r in rows)
    owing = "; ".join(
        "{} {:.3f}".format(r["land_use"], r["stewardship_h_per_ha"]) for r in rows
    )
    return {
        "epsilon":                  epsilon,
        "conservation_coefficient": USE_CATEGORIES["conservation"],
        "is_credit":                USE_CATEGORIES["conservation"] < 0.0,
        "notional_h_per_ha":        notional,
        "realised_h_per_ha":        realised,
        "credit_is_clipped":        realised > notional,
        "owed_h_per_ha_range":      (owed_lo, owed_hi),
        "classes_owing_stewardship": [
            {
                "land_use":     r["land_use"],
                "area_hectares": r["area_hectares"],
                "owed_h_per_ha": r["stewardship_h_per_ha"],
            }
            for r in rows
        ],
        "verdict": (
            f"The only negative coefficient in the fee table sits on the land "
            f"classes the stewardship census measures a POSITIVE recurring flow "
            f"on ({owing} h/ha·yr). Its notional value is "
            f"{notional:,.1f} h/ha·yr, but the fee floor clips it: conservation "
            f"land realises {realised:,.1f} h/ha·yr, so the credit never pays out "
            f"and the owed flow is never collected. A credit may well be how a "
            f"collective pays that flow — but the coefficient is not derived from "
            f"it, nothing in the code connects the two, and as shipped neither "
            f"side of the exchange happens. Reconciling them is a charter decision."
        ),
    }


# ===========================================================================
# Option 2 — the two-part tariff
# ===========================================================================

def scaling_basis_shares(scope: str = "core") -> dict:
    """
    The measured servicing hours re-cut by what their cost SCALES WITH.

    Governing sum, per basis b:

        hours(b)  = workers(b) · hours_per_worker_year
        share(b)  = hours(b) / Σ_b hours(b)

    units: labour-hours per year, and dimensionless shares.

    Worked example (core scope): area 381,200 workers → 714.5M h/yr (41.9%);
    parcel 404,600 → 758.4M h/yr (44.5%); throughput 123,800 → 232.1M h/yr
    (13.6%). Totals reconcile with `servicing_census.census` by construction —
    it is the same worker set, cut a second way.

    The parcel share is reported as a RANGE: throughput is per-occupant and is
    only proxied by parcel count, so [parcel, parcel + throughput] brackets it
    rather than picking a corner.
    """
    cut = servicing.workers_by_scaling_basis(scope)
    h_worker = hours_per_worker_year()
    hours = {b: w * h_worker for b, w in cut["by_basis"].items()}
    total = sum(hours.values())
    shares = cut["shares"]
    return {
        "scope":            scope,
        "workers_by_basis": cut["by_basis"],
        "hours_by_basis":   hours,
        "total_hours":      total,
        "shares":           shares,
        "area_share":       shares["area"],
        "parcel_share_range": (
            shares["parcel"], shares["parcel"] + shares["throughput"]
        ),
        "missing_basis":    cut["missing_basis"],
        "verdict": (
            f"scope={scope}: {shares['area']:.1%} of servicing hours scale with "
            f"AREA, {shares['parcel']:.1%} with PARCEL COUNT and "
            f"{shares['throughput']:.1%} with THROUGHPUT. The Ground Use Fee "
            f"scales with area and nothing else, so it tracks at most "
            f"{shares['area']:.1%} of the cost's structure at any multiplier."
        ),
    }


def two_part_rates(scope: str = "core") -> dict:
    """
    The tariff the measured cost implies: a per-hectare rate plus a per-parcel
    rate, in place of one per-SLU rate.

    Governing equations:

        fee(p) = u_area · hectares(p)  +  u_parcel                [h/yr]
        u_area   = hours(area) / serviced_hectares                [h/ha·yr]
        u_parcel = hours(parcel) / parcel_count                   [h/parcel·yr]

    units: labour-hours per hectare per year, and per parcel per year.

    `u_area` is MEASURED and needs nothing further: 19.24 h/ha·yr under the core
    scope, and it does not depend on the parcel count. Expressed in the fee's own
    units that is 0.1924 TEH/SLU·yr, i.e. a scale factor of ×1.18 on the NLSA
    template's abstract values — where Phase 2's aggregate implied ×2.82. The
    difference is exactly the parcel- and throughput-scaling hours, which Phase 2
    divided by area along with everything else because the fee gave them nowhere
    else to go. So the level question does not close at one number either: ×2.82
    is the right answer to "what per-SLU rate recovers the whole cost" and ×1.18
    is the right answer to "what per-SLU rate recovers the part that is actually
    area-driven", and they differ by the 58.1% of the cost the current form
    cannot address.

    `u_parcel` is EXCLUDED, not zero. The hours are measured; the divisor is not
    in this repo. `PARCEL_COUNT_RESOLVES_BY` names the field.

    THE FORM IS THE FINDING, not the level. A per-parcel term makes the fee
    depend on subdivision, which it currently does not at all
    (`subdivision_invariance`). That is a substantive change — it prices
    fragmentation — and it is a charter decision, not a recalibration.
    """
    basis = scaling_basis_shares(scope)
    hectares = servicing.serviced_hectares(scope)
    u_area = basis["hours_by_basis"]["area"] / hectares
    template_mean = (
        sum(v for v in USE_CATEGORIES.values() if v > 0.0)
        / sum(1 for v in USE_CATEGORIES.values() if v > 0.0)
    ) / _shipped_scale_factor()

    return {
        "scope":               scope,
        "serviced_hectares":   hectares,
        "u_area_h_per_ha_yr":  u_area,
        "u_area_teh_per_slu_yr": u_area * SLU_HECTARES,
        "implied_scale_factor_area_only": (u_area * SLU_HECTARES) / template_mean,
        "u_parcel_h_per_parcel_yr": None,
        "u_parcel_hours_total":     basis["hours_by_basis"]["parcel"],
        "u_parcel_excluded_reason": (
            "measured in hours, unmeasured as a rate — no national parcel count "
            "is carried in this repo. EXCLUDED rather than costed at zero, which "
            "would assert that title search, building inspection and refuse "
            "collection are free."
        ),
        "u_parcel_resolves_by":     PARCEL_COUNT_RESOLVES_BY,
        "throughput_hours_total":   basis["hours_by_basis"]["throughput"],
        "throughput_note": (
            "Per-occupant, and the fee has no per-occupant term either. Ω(p) is "
            "an occupancy FRACTION of a parcel, not a headcount, so it cannot "
            "carry this share."
        ),
        "verdict": (
            f"scope={scope}: the area-scaling half of the cost is fully measured "
            f"at {u_area:,.2f} h/ha·yr = {u_area * SLU_HECTARES:.4f} TEH/SLU·yr, "
            f"which is ×{(u_area * SLU_HECTARES) / template_mean:.2f} on the "
            f"template values against the shipped ×{_shipped_scale_factor():g}. "
            f"The parcel-scaling half is "
            f"{basis['hours_by_basis']['parcel'] / 1e6:,.0f}M h/yr and has no rate "
            f"because it has no divisor here. A single per-SLU coefficient cannot "
            f"carry both."
        ),
    }


def subdivision_invariance(epsilon: float = 0.40) -> dict:
    """
    The demonstration that the Ground Use Fee does not depend on parcel count.

    Splits every parcel of the urban archetype in two, halving each one's
    `area_slu` so the collective holds the SAME LAND in twice as many holdings,
    and recomputes. The fee per hectare is unchanged to floating-point equality,
    because A(p) is in Standard Land Units and SLUs are an area unit.

    units: labour-hours per hectare per year; `ratio` is dimensionless and is 1.0.

    WHY IT IS HERE. `servicing_census.realized_vs_measured` records the urban
    overshoot's mechanism as "the fee is per-SLU, so packing a hectare with more
    parcels multiplies the charge". That is false, and the consequence is not
    cosmetic: it means the urban 18× is driven by the L·U·D product — the
    location-value index and the ten ratios — and not by density. Run rather than
    argued, on the established precedent that a claim about the model's behaviour
    should be a test.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    parcels = make_urban_collective(10_000)
    hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
    before = compute_collective_guf(parcels, epsilon)["guf_gross_revenue"] / hectares

    split: list[dict] = []
    for p in parcels:
        for half in (0, 1):
            q = dict(p)
            q["area_slu"] = float(p["area_slu"]) / 2.0
            q["parcel_id"] = f"{p['parcel_id']}_{half}"
            split.append(q)
    hectares_after = sum(p["area_slu"] for p in split) * SLU_HECTARES
    after = compute_collective_guf(split, epsilon)["guf_gross_revenue"] / hectares_after

    return {
        "epsilon":            epsilon,
        "parcels_before":     len(parcels),
        "parcels_after":      len(split),
        "hectares":           hectares,
        "h_per_ha_before":    before,
        "h_per_ha_after":     after,
        "ratio":              after / before,
        "invariant":          after == before,
        "verdict": (
            f"Doubling the parcel count on the same {hectares:,.1f} ha leaves the "
            f"fee at {after:,.2f} h/ha·yr, exactly as before. Parcel count does "
            f"not enter the fee. The mechanism recorded for the urban overshoot "
            f"in Phase 2 is therefore wrong, and the driver is the L·U·D product "
            f"— the ratios, which that census could not settle."
        ),
    }


# ===========================================================================
# The term-basis audit, and Ψ's double application
# ===========================================================================

def basis_table() -> dict:
    """
    Every term of the master equation, with the basis it rests on and its sign
    against the inverted-Goldilocks spec.

    This is the diagnostic step: `land/guf.TERM_BASIS` is the declaration, and
    this reads it back grouped, so a term whose basis conflicts with the fee's
    stated definition is visible without reading nine docstrings.

    units: none — a classification.

    THE AUDIT'S OWN FINDING. Scoring the terms is what showed that I is
    `cost_stock` rather than `benefit`: writing down "what quantity is this"
    forced the reading of `cost_teh/(design_life × beneficiary_count)` as an
    annuity. `benefit` is consequently NOT in `FEE_BASES` — a vocabulary entry
    nothing uses is a permission nobody reviews, and this one was refuted rather
    than merely unused.
    """
    by_basis: dict[str, list[str]] = {}
    by_direction: dict[str, list[str]] = {}
    for term, entry in TERM_BASIS.items():
        by_basis.setdefault(entry["basis"], []).append(term)
        by_direction.setdefault(entry["spec_direction"], []).append(term)

    carries_epsilon = [
        t for t, e in TERM_BASIS.items() if e["epsilon_response"] != "none"
    ]
    return {
        "terms":            dict(TERM_BASIS),
        "by_basis":         by_basis,
        "by_spec_direction": by_direction,
        "bases_in_use":     sorted(by_basis),
        "bases_unused":     [b for b in FEE_BASES if b not in by_basis],
        "carries_own_epsilon_response": carries_epsilon,
        "verdict": (
            f"{len(TERM_BASIS)} terms on {len(by_basis)} distinct bases. "
            f"Aligned with the spec: {', '.join(sorted(by_direction.get('aligned', [])))}. "
            f"Inverted: {', '.join(sorted(by_direction.get('inverted', [])))}. "
            f"{len(carries_epsilon)} terms carry their own automation response "
            f"({', '.join(sorted(carries_epsilon))}), which is the double "
            f"application psi_double_application() measures."
        ),
    }


def psi_double_application(epsilon: float = 0.99) -> dict:
    """
    The two independent automation adjustments applied to the same quantity.

    Governing comparison:

        alpha(ε) = labor_content_scaling(ε)   — inside U, per NLSA Eq. 19–20
        psi(ε)   = epsilon_scaling(ε)         — multiplying the whole bracket
        combined = alpha · psi                — what the flow leg actually gets

    units: dimensionless, all three normalised to 1.0 at ε=0.40.

    THE CASE FOR RETIRING THE BELL CURVE, in two numbers.

    HIGH END — DUPLICATION. Ψ's docstring justifies its ε→0.99 collapse as
    "labor costs collapse and the fee contracts to a stewardship-only floor".
    α's docstring justifies itself as "the declining human labor content of
    land-use administration and compliance as automation rises". These are the
    same claim. At ε=0.99 α = 0.1051 and Ψ = 0.0349, so the flow leg is
    discounted to 0.0037 of its ε=0.40 reference — 271×, for one mechanism
    counted twice.

    LOW END — CATEGORY ERROR. Ψ's ε=0 floor is justified as "institutional
    capacity is minimal". That is a claim about whether a fee can be COLLECTED,
    not about what a holding COSTS. And it points the opposite way from α, which
    correctly RISES at subsistence (1.4695) because unautomated administration
    takes more human hours. The product silently nets a cost against a
    collection capability.

    Neither end is a cost statement that survives, which is what makes the bell
    shape an artifact of far-end assumptions rather than a derived curve.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    arc = (0.0, 0.20, 0.40, 0.60, 0.80, 0.99)
    rows = [
        {
            "epsilon":  e,
            "alpha":    labor_content_scaling(e),
            "psi":      epsilon_scaling(e),
            "combined": labor_content_scaling(e) * epsilon_scaling(e),
        }
        for e in arc
    ]
    a = labor_content_scaling(epsilon)
    p = epsilon_scaling(epsilon)
    a0 = labor_content_scaling(0.0)
    p0 = epsilon_scaling(0.0)
    return {
        "epsilon":            epsilon,
        "alpha":              a,
        "psi":                p,
        "combined":           a * p,
        "arc":                rows,
        "opposite_signs_at_zero": (a0 > 1.0) and (p0 < 1.0),
        "alpha_at_zero":      a0,
        "psi_at_zero":        p0,
        "verdict": (
            f"At ε={epsilon:g} the flow leg carries α={a:.4f} and Ψ={p:.4f}, "
            f"combining to {a * p:.4f} of the ε=0.40 reference — a factor of "
            f"{1.0 / (a * p):,.0f} from two multipliers whose docstrings give the "
            f"same reason. At ε=0 they point OPPOSITE ways (α={a0:.4f} rising, "
            f"Ψ={p0:.4f} collapsing), because Ψ's low end is a claim about "
            f"institutional capacity rather than about cost."
        ),
    }


def psi_policy_comparison(stewardship_scope: str = ADOPTED_SCOPE) -> dict:
    """
    The urban archetype's realised fee under each Ψ policy, across the arc,
    against the derived recurring target.

    units: labour-hours per hectare per year, and a dimensionless ratio.

    Reports; changes nothing. `retired` is the shipped default since
    2026-08-20; `bell` reproduces every pre-flip figure exactly.

    NOTE `flow_only` CURRENTLY EQUALS `bell` ON EVERY SHIPPED PATH, and that is
    a finding rather than a defect in the switch: it differs only where E or I
    is non-zero, and no shipped scenario supplies `ecosystem_services` or
    `infrastructure_assets`. The stock leg is inert, so the fix to the stock
    double-count has nothing to act on yet. It will matter exactly when the
    asset inventory lands.
    """
    urban_target = (
        census("urban_upper")["hours_per_hectare_year"]
        + (next(
            r["hours_per_hectare_year"]
            for r in stewardship_intensities(stewardship_scope)
            if r["land_use"] == "Land in urban areas"
        ) or 0.0)
    )
    parcels = make_urban_collective(10_000)
    hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
    arc = (0.0, 0.20, 0.40, 0.60, 0.80, 0.99)

    rows = []
    realised_by_policy: dict[str, dict[float, float]] = {}
    for policy in PSI_POLICIES:
        realised = {
            e: compute_collective_guf(parcels, e, psi_policy=policy)["guf_gross_revenue"]
            / hectares
            for e in arc
        }
        realised_by_policy[policy] = realised
        rows.append({
            "psi_policy":      policy,
            "realised_h_per_ha": realised,
            "ratio_to_target": {e: v / urban_target for e, v in realised.items()},
            "monotone_falling": all(
                realised[arc[i]] >= realised[arc[i + 1]] for i in range(len(arc) - 1)
            ),
        })

    bell = realised_by_policy["bell"]
    retired = realised_by_policy["retired"]
    return {
        "target_h_per_ha":  urban_target,
        "arc":              arc,
        "rows":             rows,
        "realised_by_policy": realised_by_policy,
        "flow_only_equals_bell": realised_by_policy["flow_only"] == bell,
        "verdict": (
            f"Under `bell` the urban fee runs "
            f"{bell[0.0]:,.0f} → {bell[0.40]:,.0f} → {bell[0.99]:,.0f} h/ha·yr: "
            f"a bell. Under `retired` it runs "
            f"{retired[0.0]:,.0f} → {retired[0.40]:,.0f} → {retired[0.99]:,.0f} — monotone "
            f"falling, which is α(ε) alone and is the shape a labour-content "
            f"claim actually implies. `flow_only` equals `bell` today because "
            f"the stock and damage legs are both zero on every shipped path."
        ),
    }


# ===========================================================================
# Report
# ===========================================================================

def magnitude_report(
    epsilon: float = 0.40,
    servicing_scope: str = "core",
    stewardship_scope: str = ADOPTED_SCOPE,
) -> dict:
    """
    Both options in one run: the derived target, the tariff the cost implies, and
    what neither settles.

    Reports; changes nothing. No constant moves on this.
    """
    return {
        "epsilon":              epsilon,
        "servicing_scope":      servicing_scope,
        "stewardship_scope":    stewardship_scope,
        "by_class":             recurring_target_by_class(servicing_scope, stewardship_scope),
        "target_vs_realised":   target_vs_realised(epsilon, stewardship_scope),
        "amenity_sensitivity":  amenity_sensitivity(epsilon),
        "conservation_credit":  conservation_credit_check(epsilon, stewardship_scope),
        "scaling_basis":        scaling_basis_shares(servicing_scope),
        "two_part_rates":       two_part_rates(servicing_scope),
        "subdivision":          subdivision_invariance(epsilon),
        "term_basis":           basis_table(),
        "psi_double":           psi_double_application(),
        "psi_policies":         psi_policy_comparison(stewardship_scope),
        "what_this_does_not_settle": (
            "The ten RATIOS. Both censuses are aggregates over LAND CLASSES; the "
            "fee table is indexed by USE CATEGORY, and no occupational data is "
            "coded by the land use it serves. Option 1 settles the level for the "
            "classes both censuses reach and Option 2 settles the form; the shape "
            "of the table is untouched by either, and the subdivision result "
            "makes the ratios MORE load-bearing, not less, because they turn out "
            "to be what drives the urban overshoot."
        ),
    }


def _shipped_scale_factor() -> float:
    """The shipped ×100, read from `data.py` rather than restated."""
    from hours_eoh.data import GUF_USE_SCALE_FACTOR

    return GUF_USE_SCALE_FACTOR
