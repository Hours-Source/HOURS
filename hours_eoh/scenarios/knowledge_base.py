"""
KNOWLEDGE_EOH_BASE from the measured O*NET/BLS training stock — Block K-II.

REPORTING ONLY. Nothing here changes a default, and `KNOWLEDGE_EOH_BASE` is
untouched. This module produces the number and its band so the adoption decision
(Block K-IV) can be made against evidence rather than against a docstring.

What this bridges
-----------------
`reference/onet_knowledge.py` recovers a measured training STOCK (hours embodied
in the workforce). `core/eoh_generation.knowledge_eoh` consumes a stock and a
renewal rate — the same shape, which is the whole reason this closure is possible
(see the stock/flow correction in Block K-I). This module is the seam:

    measured stock  ──►  annual flow  ──►  back-derived base_rate  ──►  arc

THE ANCHORING PROBLEM, AND WHY THIS EMITS A BAND
-------------------------------------------------
The registry describes a MODERN, already-automated workforce. Treating its stock
as the ε=0 baseline would repeat the Block I category error — applying a number
defined at one point on the arc as though it were defined at another. So the
constant must be back-derived at a stated reference automation level::

    base_rate = flow_measured(ε_ref) / [ kbs(ε_ref) · cpu(ε_ref) · d ]

and the result falls steeply in ε_ref: across ε_ref ∈ [0.2, 0.6] the answer moves
**7.13×**, against a 1.20× spread from the per-capita conversion. **The epoch
anchoring is the uncertainty, not the measurement.** That asymmetry is the single
most important output of this module, which is why `knowledge_base_band()` exists
and why K-IV ships a band rather than a point. Precedent:
`research/thermal_path_c.global_ceiling()` returns `epsilon_max_band` for exactly
this reason.

BASE_RATE IS THE EMBODIED STOCK, AND THE DERIVATION IS DECAY-FREE (K-III fix)
------------------------------------------------------------------------------
K-I established that `base_rate` is a STOCK. K-II's first derivation quietly
contradicted that: it built the measured flow at the transmission rate (1/40)
and divided by `SKILL_DECAY_RATE` (0.10), returning a base **4× smaller** than
the stock it was documented as. Corrected here — the derivation now runs

    base_rate = S_per_capita · P_ref / [ kbs(ε_ref) · cpu(ε_ref) ]

with no renewal rate in it at all. `base_rate` is the embodied training stock
at the ε=0 reference, full stop, and `knowledge_eoh` applies whatever renewal
rate the caller believes in.

CONSEQUENCE, AND IT IS THE POINT OF BLOCK K-III: the arc level is now directly
proportional to the renewal rate `d`, so the arc is sensitive to the CPD term —
the one term O*NET cannot supply. The split does not make the uncertainty go
away; it RELOCATES it from an unexamined 0.10 into a named component with an
epistemic pointer (Eurostat CVTS). `renewal_doctrine_comparison()` reports the
arc under each doctrine so the sensitivity is visible rather than buried.

Three routes to ε_ref (the knowledge-base closure note §4):
  1. capital inventory  → ε ≈ 0.78–1.00, SATURATED and unusable; see Finding A
  2. labour residual    → ε = 0.391, corroborates the standing 0.40, no new data
  3. the chosen 0.40
Routes 2 and 3 agree; route 1 disagrees violently and that disagreement is a
finding about the capital profiles, not about knowledge.

The kbs·cpu·d response is never reimplemented here — it is obtained by calling
`knowledge_eoh` itself at unit base, so this module cannot drift from the
function it is calibrating.

Reference: the knowledge-base closure note; Block K-II.
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import (
    knowledge_eoh, skill_renewal_rate, total_eoh,
)
from hours_eoh.data import (
    AGE_GROUPS,
    H_REF,
    KNOWLEDGE_EOH_BASE,
    KNOWLEDGE_REFERENCE_POPULATION,
    SKILL_DECAY_RATE,
    SKILL_TRANSMISSION_RATE,
    SKILL_WORKING_LIFE_YEARS,
    US_REFERENCE_POPULATION,
)
from hours_eoh.reference.onet_knowledge import workforce_training_stock

# ---------------------------------------------------------------------------
# Inputs the registry cannot supply, each with its provenance stated
# ---------------------------------------------------------------------------

# Fraction of US employment the 751-occupation registry covers. Stated in the
# multiplier handoff and this repo's own module docstring; NOT a field in any
# shipped data file, so it is carried here as a documented input rather than
# asserted inside `reference/`. CHOSEN (recorded upstream) —
# resolves_by: BLS OEWS total employment for the same reference epoch.
REGISTRY_EMPLOYMENT_COVERAGE: float = 0.942

# Population the registry's employment is drawn against. BOUND to data.py
# rather than restated: this value also lived in reference/land_stewardship.py
# under a second name, and one value under two names in two files outside the
# gate is the shadow-constant pattern. The alias is kept so every existing
# caller and import is unaffected.
REFERENCE_POPULATION_US: float = US_REFERENCE_POPULATION

# Years of working life over which the embodied training stock must be
# re-created as cohorts turn over. This is the TRANSMISSION rate of Block K-III;
# it is NOT the shipped SKILL_DECAY_RATE, which additionally carries an
# unseparated CPD term.
#
# BOUND TO data.SKILL_WORKING_LIFE_YEARS 2026-08-16. It was a duplicate literal
# 40.0 carrying its own copy of the same WRONG pointer (BLS Employee Tenure
# measures job tenure, not working life), and it lived HERE rather than in
# data.py — so the provenance gate, which scans data.py only, could not see it.
# When the working life was measured at 37.5 the two diverged silently and
# broke a structural identity: `test_reproduces_the_measured_flow_at_the_anchor`
# computes the flow at THIS horizon and the base at the data.py rate, and the
# two came apart by exactly 40/37.5 = 1.0667. The identity test caught it,
# which is the argument for identity tests over pinned levels — a pin would
# have been updated and the divergence preserved underneath it.
#
# Fourth instance of the pattern (`= 1500.0` in the EOH generators,
# `skill_decay_rate = 0.10` in the pipeline, `_ECOLOGICAL_SPIKE_INTENSITY` in
# core/): a domain constant restated as a literal away from its source. The
# alias is kept so callers and the `working_life_years=` parameter still work.
TRANSMISSION_WORKING_LIFE_YEARS: float = SKILL_WORKING_LIFE_YEARS

# The two documented employment-to-population routes (§1 of the closure note).
# Their 1.20× spread is the measurement uncertainty; compare ε_ref's 8.5×.
_EP_REGISTRY = "registry"   # registry employment ÷ coverage ÷ reference population
_EP_REPO = "repo"           # the repo's own working-age fraction, at full employment

KEY_EPSILONS: tuple[float, ...] = (0.0, 0.40, 0.99)
DEFAULT_EPSILON_REF_BAND: tuple[float, ...] = (0.20, 0.40, 0.60)


def employment_to_population(route: str = _EP_REGISTRY) -> float:
    """
    Employment-to-population ratio, by one of the two documented routes.

    units: dimensionless, employed persons per head of population.
    ε-behavior: none — an observed ratio at the frozen epoch.

    Args:
        route: "registry" — the registry's own employment grossed up by
                   `REGISTRY_EMPLOYMENT_COVERAGE` and divided by
                   `REFERENCE_POPULATION_US`. Self-consistent: the same source
                   supplies numerator and the coverage correction. Gives 0.500.
               "repo" — the repo's `AGE_GROUPS` working-age fraction, which
                   assumes every working-age person is employed and therefore
                   runs HIGH. Gives 0.600.

    Returns:
        The ratio. The two differ by 1.20×; that is the honest spread.

    Raises:
        ValueError: on an unknown route.
    """
    if route == _EP_REGISTRY:
        stock = workforce_training_stock()
        total_employment = (
            stock["covered_employment"] / REGISTRY_EMPLOYMENT_COVERAGE
        )
        return total_employment / REFERENCE_POPULATION_US
    if route == _EP_REPO:
        return float(AGE_GROUPS["working_age"]["fraction"])
    raise ValueError(
        f"route must be {_EP_REGISTRY!r} or {_EP_REPO!r}, got {route!r}"
    )


def measured_knowledge_flow_per_capita(
    route: str = _EP_REGISTRY,
    working_life_years: float = TRANSMISSION_WORKING_LIFE_YEARS,
) -> dict:
    """
    The measured annual knowledge obligation per head, under the TRANSMISSION
    framing (author-accepted 2026-08-08).

        flow = mean_training_hours_per_worker · (E/P) / working_life

    Read it as: the workforce embodies a training stock; every year, 1/working_life
    of it walks out the door with a retiring cohort and must be re-created in
    someone else. Knowledge dies with people — that is the entropy, and it is what
    makes this domain an obligation rather than an analogy.

    units: hours per person per year.
    ε-behavior: none directly — but see `knowledge_base_from_registry`, which is
    where the ε_ref anchoring enters and where the real uncertainty lives.

    Args:
        route: employment-to-population route; see `employment_to_population`.
        working_life_years: transmission horizon (> 0).

    Returns:
        dict with "flow_per_capita_h_yr", "mean_hours_per_worker",
        "employment_to_population", "transmission_rate", "route".

    Raises:
        ValueError: if working_life_years is not positive.

    Worked example (registry route, 40-year life): 11,001 h/worker × 0.500 / 40
    = 137.5 h/person·yr. The repo route gives 165.0 — a 1.20× spread.
    """
    if working_life_years <= 0.0:
        raise ValueError(
            f"working_life_years must be positive, got {working_life_years}"
        )
    stock = workforce_training_stock()
    ep = employment_to_population(route)
    rate = 1.0 / working_life_years
    return {
        "flow_per_capita_h_yr":     stock["mean_hours_per_worker"] * ep * rate,
        "mean_hours_per_worker":    stock["mean_hours_per_worker"],
        "employment_to_population": ep,
        "transmission_rate":        rate,
        "route":                    route,
    }


def _unit_response(epsilon: float, decay: float) -> float:
    """
    kbs(ε) · cpu(ε) · decay, obtained from `knowledge_eoh` at unit base so this
    module can never drift from the function it calibrates.
    """
    return knowledge_eoh(
        1.0, decay, epsilon=epsilon, base_rate=1.0,
        population=KNOWLEDGE_REFERENCE_POPULATION,
    )


def _complexity_response(epsilon: float) -> float:
    """kbs(ε) · cpu(ε) alone — the decay-free part, for the stock derivation."""
    return _unit_response(epsilon, 1.0)


def embodied_stock_per_capita(route: str = _EP_REGISTRY) -> float:
    """
    Training hours embodied per head of population at the frozen epoch.

        S_per_capita = mean_hours_per_worker · (E/P)

    This is the quantity `KNOWLEDGE_EOH_BASE` denominates, before any renewal
    rate is applied and before the ε_ref anchoring is removed. It is what the
    O*NET spine actually measures.

    units: hours per person (a STOCK, not per year).
    ε-behavior: none — an observed workforce at one epoch.

    Worked example (registry route): 11,001.3 × 0.500 = 5,500.7 h/person.
    """
    return workforce_training_stock()["mean_hours_per_worker"] * \
        employment_to_population(route)


def knowledge_base_from_registry(
    epsilon_ref: float,
    route: str = _EP_REGISTRY,
    working_life_years: float = TRANSMISSION_WORKING_LIFE_YEARS,
    # ADOPTED DEFAULT (2026-08-16). This was SKILL_DECAY_RATE — the rate this
    # module's own doctrine table reports as "not credible against the measured
    # stock". base_rate is decay-free, so the default never touched the derived
    # constant; it set the REPORTED ARC LEVEL, which is the figure a reader
    # takes away. The last parameter default on the refuted rate.
    decay: float = SKILL_TRANSMISSION_RATE,
) -> dict:
    """
    Back-derive `KNOWLEDGE_EOH_BASE` from the measured stock at a stated ε_ref.

        base_rate = flow_measured · P_ref / [ kbs(ε_ref) · cpu(ε_ref) · d ]

    NOT ADOPTED. This reports what the constant would be; nothing is changed.

    units: base_rate in hours (a STOCK at `KNOWLEDGE_REFERENCE_POPULATION`).
    ε-behavior: defined for ε_ref ∈ [0, 0.99]. The result FALLS steeply as ε_ref
    rises — at higher assumed automation the same measured flow is explained by a
    smaller underlying corpus, because kbs and cpu have already multiplied it up.

    Args:
        epsilon_ref: The automation level the measured workforce is taken to sit
            at. THE DOMINANT UNCERTAINTY — 8.5× across [0.2, 0.6].
        route: employment-to-population route.
        working_life_years: transmission horizon.
        decay: renewal rate used consistently on both sides of the derivation, so
            it CANCELS in the arc. Changing it rescales `base_rate` and leaves
            `stock_flow_product` and `knowledge_h_per_capita` untouched — see the
            module docstring.

    Returns:
        dict with "base_rate", "stock_flow_product" (the decay-invariant one),
        "base_rate_ratio_to_shipped", "epsilon_ref", "flow_per_capita_h_yr",
        "knowledge_h_per_capita" (at KEY_EPSILONS), and the inputs echoed for
        auditability.

    Raises:
        ValueError: if epsilon_ref is outside [0, 0.99] or the unit response is
            non-positive.

    Worked example (ε_ref = 0.40, registry route, 40 yr, d = 0.10): flow 137.5
    h/person·yr → base_rate 1.225e8, 1,225× the shipped 1.0e5, putting knowledge
    at 12.3 / 137.5 / 1,192 h/person·yr across ε ∈ {0, 0.40, 0.99}. At d = 1/40
    the same inputs give base_rate 4.901e8 and the SAME three arc figures.
    """
    if not 0.0 <= epsilon_ref <= 0.99:
        raise ValueError(
            f"epsilon_ref must be in [0, 0.99], got {epsilon_ref}"
        )
    flow = measured_knowledge_flow_per_capita(route, working_life_years)
    # DECAY-FREE (K-III): base_rate is the embodied stock at the ε=0 reference.
    # No renewal rate enters — the caller's `decay` sets the arc LEVEL below,
    # which is exactly the sensitivity Block K-III exists to expose.
    response = _complexity_response(epsilon_ref)
    if response <= 0.0:
        raise ValueError(
            f"non-positive knowledge response at epsilon_ref={epsilon_ref}"
        )
    per_capita = flow["flow_per_capita_h_yr"]
    base_rate = (
        embodied_stock_per_capita(route) * KNOWLEDGE_REFERENCE_POPULATION
        / response
    )
    return {
        "epsilon_ref":                epsilon_ref,
        "base_rate":                  base_rate,
        # The stock the base denominates, before ε_ref de-anchoring — the
        # measured quantity, carried so the derivation stays auditable.
        "embodied_stock_per_capita":  embodied_stock_per_capita(route),
        "stock_flow_product":         base_rate * decay,
        "base_rate_ratio_to_shipped": base_rate / KNOWLEDGE_EOH_BASE,
        "flow_per_capita_h_yr":       per_capita,
        "mean_hours_per_worker":      flow["mean_hours_per_worker"],
        "employment_to_population":   flow["employment_to_population"],
        "transmission_rate":          flow["transmission_rate"],
        "route":                      route,
        "decay":                      decay,
        "knowledge_h_per_capita": {
            eps: base_rate * _unit_response(eps, decay)
                 / KNOWLEDGE_REFERENCE_POPULATION
            for eps in KEY_EPSILONS
        },
    }


def knowledge_base_band(
    epsilon_refs: tuple[float, ...] = DEFAULT_EPSILON_REF_BAND,
    routes: tuple[str, ...] = (_EP_REGISTRY, _EP_REPO),
    working_life_years: float = TRANSMISSION_WORKING_LIFE_YEARS,
) -> dict:
    """
    The band over ε_ref and per-capita route — the honest shipped form.

    THE HEADLINE FINDING lives in the two spread numbers this returns:
    `epsilon_ref_spread` ≈ 7.13 against `route_spread` ≈ 1.20. The measurement is
    well determined; the epoch it is anchored to is not. Any single-value quote
    of `KNOWLEDGE_EOH_BASE` from this route is quoting the anchoring assumption,
    not the data. Both spreads are decay-invariant.

    units: base_rate in hours; spreads dimensionless.
    ε-behavior: covers ε_ref ∈ [0.2, 0.6] by default — the same band
    `thermal_path_c.global_ceiling()` uses for ε_current, and for the same reason.

    Args:
        epsilon_refs: reference automation levels to span.
        routes: per-capita conversion routes to span.
        working_life_years: transmission horizon.

    Returns:
        dict with "rows" (one per ε_ref × route), "base_rate_low"/"_high",
        "epsilon_ref_spread", "route_spread", "shipped_base_rate", and
        "dominant_uncertainty" — a plain-language verdict naming which lever wins.

    Raises:
        ValueError: if epsilon_refs or routes is empty.
    """
    if not epsilon_refs:
        raise ValueError("epsilon_refs must not be empty")
    if not routes:
        raise ValueError("routes must not be empty")

    rows = [
        knowledge_base_from_registry(eps, route, working_life_years)
        for eps in epsilon_refs
        for route in routes
    ]
    bases = [r["base_rate"] for r in rows]

    def _spread(values: list[float]) -> float:
        lo, hi = min(values), max(values)
        return hi / lo if lo > 0.0 else float("inf")

    # ε_ref lever measured at a fixed route; route lever at a fixed ε_ref.
    ref_route = routes[0]
    eps_spread = _spread([
        r["base_rate"] for r in rows if r["route"] == ref_route
    ])
    mid_eps = epsilon_refs[len(epsilon_refs) // 2]
    route_spread = _spread([
        r["base_rate"] for r in rows if r["epsilon_ref"] == mid_eps
    ])
    return {
        "rows":                rows,
        "base_rate_low":       min(bases),
        "base_rate_high":      max(bases),
        "epsilon_ref_spread":  eps_spread,
        "route_spread":        route_spread,
        "shipped_base_rate":   KNOWLEDGE_EOH_BASE,
        "dominant_uncertainty": (
            "epsilon_ref" if eps_spread > route_spread else "per_capita_route"
        ),
        "note": (
            f"epsilon_ref moves the answer {eps_spread:.1f}x against the "
            f"per-capita route's {route_spread:.2f}x — the anchoring assumption "
            f"dominates the measurement. Ship the band, not a point."
        ),
    }


def renewal_doctrine_comparison(
    epsilon_ref: float = 0.40,
    route: str = _EP_REGISTRY,
) -> dict:
    """
    The arc under each renewal doctrine — Block K-III's headline output.

    With `base_rate` now decay-free (it is the embodied stock), the arc level is
    directly proportional to the renewal rate. So the question "what is d?" is no
    longer buried in a placeholder; it moves the answer linearly, and this
    function shows by how much.

    Three doctrines:
        "shipped"       d = SKILL_DECAY_RATE (0.10) — the unexamined placeholder
        "split"         d = transmission + CPD (0.0277) — Block K-III
        "transmission"  d = transmission alone (0.025) — the measurable floor

    THE CREDIBILITY TEST, and it is the reason the split was worth doing: each
    doctrine implies a number of hours per worker per year spent renewing
    knowledge, and that number is checkable against a work-year. The shipped
    0.10 implies **52.9% of the H_REF 2,080 h work-year, every year, forever**.
    The split implies 15.2%. Nothing in any time-use or training series supports
    the former. This is reported, not silently corrected — `SKILL_DECAY_RATE` is
    still the default everywhere.

    units: hours/person·yr, hours/worker·yr, and dimensionless shares.
    ε-behavior: evaluated across KEY_EPSILONS; full arc safe.

    Args:
        epsilon_ref: anchoring level for the (decay-free) base derivation.
        route: per-capita conversion route.

    Returns:
        dict with "doctrines" (per doctrine: rate, arc figures, h/worker·yr,
        work-year share, credible flag), "base_rate", "embodied_stock_per_capita",
        and "verdict".

    Worked example (ε_ref = 0.40, registry): base_rate 4.901e8 — the embodied
    stock, 4× the pre-K-III figure. Knowledge at ε=0.40 reads 550.1 h/person·yr
    under the shipped rate, 152.4 under the split, 137.5 under transmission
    alone — the last reproducing K-II's arc exactly, which is the continuity
    check that the decay-free fix did not move the measurement.
    """
    derived = knowledge_base_from_registry(epsilon_ref, route)
    base_rate = derived["base_rate"]
    stock_per_worker = workforce_training_stock()["mean_hours_per_worker"]
    split = skill_renewal_rate()

    doctrines = {}
    for name, rate in (
        ("shipped",      SKILL_DECAY_RATE),
        ("split",        split["total"]),
        ("transmission", split["transmission"]),
    ):
        per_worker = stock_per_worker * rate
        work_year_share = per_worker / H_REF
        doctrines[name] = {
            "renewal_rate":            rate,
            "hours_per_worker_year":   per_worker,
            "work_year_share":         work_year_share,
            # A worker cannot spend most of every year re-learning their job.
            # The threshold is deliberately generous: anything above a quarter
            # of a work-year is flagged, not just the absurd cases.
            "credible":                work_year_share <= 0.25,
            "knowledge_h_per_capita": {
                eps: base_rate * _unit_response(eps, rate)
                     / KNOWLEDGE_REFERENCE_POPULATION
                for eps in KEY_EPSILONS
            },
        }

    shipped_share = doctrines["shipped"]["work_year_share"]
    split_share = doctrines["split"]["work_year_share"]
    return {
        "epsilon_ref":               epsilon_ref,
        "route":                     route,
        "base_rate":                 base_rate,
        "embodied_stock_per_capita": derived["embodied_stock_per_capita"],
        "stock_per_worker":          stock_per_worker,
        "doctrines":                 doctrines,
        "shipped_over_split":        SKILL_DECAY_RATE / split["total"],
        "verdict": (
            f"shipped d={SKILL_DECAY_RATE} implies {shipped_share:.1%} of a "
            f"work-year per worker per year; the split implies "
            f"{split_share:.1%}. The shipped rate is "
            f"{SKILL_DECAY_RATE / split['total']:.1f}x the components and is "
            f"not credible against the measured stock."
        ),
    }


def domain_share_projection(
    epsilon_ref: float = 0.40,
    route: str = _EP_REGISTRY,
    epsilons: tuple[float, ...] = KEY_EPSILONS,
    population: float = KNOWLEDGE_REFERENCE_POPULATION,
    decay: float | None = None,
) -> dict:
    """
    What adopting this base WOULD do to domain balance — the K-IV decision input.

    NOT ADOPTED, and deliberately reported as a projection: it substitutes the
    derived knowledge figure into the shipped `total_eoh` breakdown and recomputes
    shares, leaving every other domain exactly as calibrated.

    This is the payoff test. `knowledge_eoh`'s own reference text says human labor
    at ε→1 is "almost entirely care, judgment, and knowledge maintenance"; at
    shipped calibration the domain is 0.005% of total EOH. The projection shows
    whether the derived base delivers the behaviour the model already asserts.

    units: hours/year and dimensionless shares.
    ε-behavior: evaluated at each ε in `epsilons`, full arc safe.

    Args:
        epsilon_ref: anchoring level for the back-derivation.
        route: per-capita conversion route.
        epsilons: arc points to report.
        population: population to evaluate the breakdown at.

    Returns:
        dict with "rows" (per ε: shipped vs projected knowledge, h/person·yr, and
        projected domain shares) and "personal_share_range"/"knowledge_share_range".

    Worked example (ε_ref = 0.40, registry route): personal falls 94.4% → 84.4%
    → 51.1% across the arc while knowledge rises 0.8% → 7.9% → 41.2%. This does
    NOT fix domain balance on its own — personal still runs 51–94%.
    """
    # DOCTRINE CHOICE, stated: the projection pairs the measured base with the
    # EVIDENCE-BASED renewal rate (Block K-III's split), not the shipped
    # placeholder. Adopting a measured stock while keeping a rate that implies
    # 55% of a work-year would be incoherent — the two are one decision.
    if decay is None:
        decay = skill_renewal_rate()["total"]
    derived = knowledge_base_from_registry(epsilon_ref, route)
    base_rate = derived["base_rate"]

    rows = []
    for eps in epsilons:
        shipped = total_eoh(epsilon=eps, population=population)
        k_new = base_rate * _unit_response(eps, decay) \
            * (population / KNOWLEDGE_REFERENCE_POPULATION)
        others = shipped["personal"] + shipped["infrastructure"] + shipped["ecological"]
        projected_total = others + k_new
        rows.append({
            "epsilon":              eps,
            "knowledge_shipped":    shipped["knowledge"],
            "knowledge_projected":  k_new,
            "knowledge_h_per_capita": k_new / population,
            "personal_share":       shipped["personal"] / projected_total,
            "infrastructure_share": shipped["infrastructure"] / projected_total,
            "ecological_share":     shipped["ecological"] / projected_total,
            "knowledge_share":      k_new / projected_total,
            "knowledge_share_shipped": shipped["knowledge"] / shipped["total"],
        })
    return {
        "epsilon_ref":  epsilon_ref,
        "route":        route,
        "base_rate":    base_rate,
        "decay":        decay,
        "rows":         rows,
        "personal_share_range": (
            min(r["personal_share"] for r in rows),
            max(r["personal_share"] for r in rows),
        ),
        "knowledge_share_range": (
            min(r["knowledge_share"] for r in rows),
            max(r["knowledge_share"] for r in rows),
        ),
        "note": (
            "Projection only — KNOWLEDGE_EOH_BASE is unchanged. Personal EOH "
            "still dominates; this closes one of the two small domains, not the "
            "domain-balance defect."
        ),
    }


# ---------------------------------------------------------------------------
# The ε_ref fixed point (Finding E, approved 2026-08-09)
#
# K-IV derived KNOWLEDGE_EOH_BASE at ε_ref = 0.40 on the strength of the
# labour-residual route corroborating that anchor — and then the adoption grew
# total EOH by ~12% at mid-arc, which moves the residual. The corroboration was
# consumed by the adoption it justified.
#
# The defect is not the value, it is the SHAPE of the derivation: a one-shot
# anchor cannot be self-consistent when the thing it anchors is in the
# denominator of the thing that checks it. A third one-shot would have the same
# defect. So solve the loop instead.
# ---------------------------------------------------------------------------

def labour_residual_epsilon(
    observed_hours_per_capita: float,
    knowledge_base: float,
    population: float = KNOWLEDGE_REFERENCE_POPULATION,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> float | None:
    """
    The ε at which the model's own unmet obligation equals the labour supplied.

    Governing equation:

        (1 − ε) · total_eoh(ε, pop) / pop  =  observed_hours_per_capita

    units: dimensionless ε.

    ε-behavior: `(1 − ε) · total_eoh(ε)` is decreasing in ε over [0, 0.99], so
    the root is unique where it exists. Returns **None** — not a clamped 0 —
    when the supplied labour exceeds the entire obligation at ε = 0, because
    "no ε explains this" is a finding and zero is a different claim.

    Worked example: 937.3 h/person·yr of paid US labour against the shipped
    calibration → ε ≈ 0.470. The same solver on 1,701.1 (paid + unpaid) returns
    None: supply exceeds the whole obligation by 14% (Finding B).

    Raises:
        ValueError: if observed_hours_per_capita is negative.
    """
    if observed_hours_per_capita < 0.0:
        raise ValueError(
            f"observed hours must be non-negative, got {observed_hours_per_capita}"
        )

    def unmet(epsilon: float) -> float:
        # PER-DOMAIN since the Phase 2 adoption (2026-09-01). This used a flat
        # (1 - epsilon) on the total, which is the superseded `uniform` policy —
        # and leaving it would have solved the fixed point against a labour
        # requirement the model no longer makes, silently. The personal domain
        # carries its own human fraction; the other three keep (1 - epsilon).
        from hours_eoh.core.eoh_fulfillment import human_eoh_per_domain
        domains = _domain_eoh(epsilon, knowledge_base, population)
        return human_eoh_per_domain(domains, epsilon)["total"] / population

    if unmet(0.0) < observed_hours_per_capita:
        return None
    lo, hi = 0.0, 0.99
    if unmet(hi) > observed_hours_per_capita:
        return hi
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if unmet(mid) > observed_hours_per_capita:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def _total_eoh_per_capita(
    epsilon: float,
    knowledge_base: float,
    population: float,
) -> float:
    """Gross total EOH per capita on the canonical arc at a stated knowledge base."""
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.core.trajectory import canonical_physical_state

    state = canonical_physical_state(epsilon)
    return total_eoh(
        population=population,
        capital_stock=state["capital_stock_teh"],
        capital_age_ratio=state["capital_age_ratio"],
        ecosystem_health=state["ecosystem_health"],
        monitoring_capability=state["monitoring_capability"],
        age_distribution=state["age_distribution"],
        knowledge_complexity=state["knowledge_base_size"],
        knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        knowledge_base=knowledge_base,
        skill_decay_rate=SKILL_TRANSMISSION_RATE,
    )["total"] / population


def _domain_eoh(epsilon: float, knowledge_base: float, population: float) -> dict:
    """Per-domain gross EOH on the canonical arc at a stated knowledge base."""
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.core.trajectory import canonical_physical_state

    state = canonical_physical_state(epsilon)
    return total_eoh(
        population=population,
        capital_stock=state["capital_stock_teh"],
        capital_age_ratio=state["capital_age_ratio"],
        ecosystem_health=state["ecosystem_health"],
        monitoring_capability=state["monitoring_capability"],
        age_distribution=state["age_distribution"],
        knowledge_complexity=state["knowledge_base_size"],
        knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        knowledge_base=knowledge_base,
        skill_decay_rate=SKILL_TRANSMISSION_RATE,
    )


def epsilon_ref_fixed_point(
    observed_hours_per_capita: float,
    route: str = _EP_REGISTRY,
    epsilon_start: float = 0.40,
    tol: float = 1e-4,
    max_iter: int = 50,
) -> dict:
    """
    Solve the anchor and the base together, instead of anchoring then checking.

    The loop that K-IV left open:

        base(ε_ref)  ──►  total_eoh  ──►  ε_residual(observed)  ──►  ε_ref …

    Iterated to a fixed point ε* where the anchor the base is derived AT equals
    the anchor the labour residual IMPLIES given that base. Damped fixed-point
    iteration; the map is a contraction over the arc's interior because the base
    falls in ε_ref while the residual rises in the base.

    units: ε dimensionless; base_rate in hours at KNOWLEDGE_REFERENCE_POPULATION.

    ε-behavior: converges from any start in (0, 0.99). Reports `converged` and
    the iteration count rather than silently returning the last iterate.

    Args:
        observed_hours_per_capita: measured human labour per capita per year.
            THE CONVENTION MATTERS — see `scenarios/personal_floor` — and the
            paid-labour reading is the one self-consistent with
            `personal_eoh_registration_share(0)` being near-zero.
        route: per-capita conversion route for the measured stock.
        epsilon_start: initial anchor. The fixed point does not depend on it;
            the field is kept so the path can be inspected.

    Returns:
        dict with `epsilon_fixed_point`, `base_rate`, `shipped_base_rate`,
        `epsilon_shipped_anchor`, `ratio_to_shipped`, `converged`, `iterations`,
        `path`, and a `note`.

    Worked example: at 937.3 h/person·yr (US paid labour, 2025) the loop settles
    away from the shipped 0.40 anchor — the distance IS Finding E, and the base
    that comes with it is what a self-consistent derivation gives.
    """
    epsilon = float(epsilon_start)
    path: list[dict] = []
    converged = False
    base = float(KNOWLEDGE_EOH_BASE)
    for i in range(max_iter):
        base = knowledge_base_from_registry(
            epsilon, route=route, decay=SKILL_TRANSMISSION_RATE
        )["base_rate"]
        implied = labour_residual_epsilon(observed_hours_per_capita, base)
        path.append({
            "iteration": i,
            "epsilon_ref": epsilon,
            "base_rate": base,
            "epsilon_implied": implied,
        })
        if implied is None:
            return {
                "epsilon_fixed_point": None,
                "base_rate": None,
                "shipped_base_rate": KNOWLEDGE_EOH_BASE,
                "ratio_to_shipped": None,
                "is_shipped_anchor": False,
                "converged": False,
                "iterations": i + 1,
                "path": path,
                "note": (
                    "no fixed point: the supplied labour exceeds the entire "
                    "obligation at ε=0, so no anchor explains it. That is "
                    "Finding B, not a solver failure — the over-determination "
                    "has to be resolved before this loop means anything."
                ),
            }
        if abs(implied - epsilon) < tol:
            converged = True
            epsilon = implied
            break
        # Damped: the two directions overshoot each other otherwise.
        epsilon = 0.5 * (epsilon + implied)

    base = knowledge_base_from_registry(
        epsilon, route=route, decay=SKILL_TRANSMISSION_RATE
    )["base_rate"]
    base = knowledge_base_from_registry(
        epsilon, route=route, decay=SKILL_TRANSMISSION_RATE
    )["base_rate"]
    ratio = base / KNOWLEDGE_EOH_BASE
    # The shipped constant WAS re-anchored to this fixed point on 2026-08-09, so
    # at the default inputs `is_shipped_anchor` is True. It stops being true if
    # the registry vintage moves, if the observed-hours input changes, or if
    # anything upstream shifts total EOH — which is exactly the drift K-IV's
    # one-shot anchor could not detect, and the reason this reports rather than
    # asserts.
    is_shipped = abs(ratio - 1.0) < 1e-6
    return {
        "epsilon_fixed_point": epsilon,
        "base_rate": base,
        "shipped_base_rate": KNOWLEDGE_EOH_BASE,
        "ratio_to_shipped": ratio,
        "is_shipped_anchor": is_shipped,
        "converged": converged,
        "iterations": len(path),
        "path": path,
        "note": (
            f"anchor and base solved together: ε* = {epsilon:.4f}, base "
            f"{base:.4e}. " + (
                "The shipped constant IS this fixed point — the derivation is "
                "self-consistent at these inputs."
                if is_shipped else
                f"The shipped constant is {KNOWLEDGE_EOH_BASE:.4e} "
                f"({ratio:.3f}x off): it is NOT a fixed point of its own "
                f"derivation, which is the Finding-E defect recurring."
            )
        ),
    }
