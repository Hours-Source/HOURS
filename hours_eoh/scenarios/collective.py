"""
The single assembly point: one collective, one frame, one reconciled snapshot.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. `docs/guides/implementation_guide.md` tells an institution to
run `eoh_to_teh_pipeline()` and `fiscal_snapshot()`, and — since GUF revenue was
wired into the fisc — `compute_collective_guf()` as well. Running those three by
hand means keeping **eleven shared parameters in agreement** across the calls
(`population`, `ecosystem_health`, `ecological_area_hectares`, `epsilon`,
`mean_multiplier`, `capital_age_ratio`, …) and hand-passing **three values**
between them:

    labor_income      <- pipeline["teh_created"]
    eco_eoh_override  <- pipeline["eoh_by_domain"]["ecological"]
    guf_revenue       <- compute_collective_guf(parcels)["guf_net_inflow"]

Every one is a place the frame can come apart. When this was written it had come apart
six times, most recently at **92.8× inside the guide's own worked example** — the
pipeline resolving the ecological area from population while the fiscal layer took the
whole contiguous US. This function makes that arithmetic unavailable to get wrong: state
the frame once, and the three calls cannot disagree.

WHY IT LIVES IN `scenarios/` AND NOT IN `core/`. `core/fiscal` needs the ground-use fee
that collectives owe it, and `land/` imports `core/`, so core cannot ask for it. The
inversion is not worth having. Moving GUF into core would assert that land tenure is
physics, and `land/` is a separate layer precisely because it is not. `scenarios/` may
import `core/` AND `land/`, so the assembly belongs here — one layer up, owning both
sides. That is the layer rule working as designed, not a workaround.

WHY IT DOES NOT USE `research/exchange.CollectiveFrame`. `research/` is not
importable by `scenarios/` (it is experimental and explicitly not depended on).
Rather than duplicate that dataclass, this takes the state container `core/`
already has — `core.simulation.make_economy_state()` — which carries population,
capital, trust balance, ecosystem health and ε, and which `fiscal_snapshot`
learned to read on 2026-08-29. The only thing a state does not carry is LAND,
because the ecological domain was keyed to area later than the state was
written; land is therefore an extra argument — and so, since 2026-10-14, is
the age mix (`age_fractions`) — which a state may also carry since the same
day, in which case it need not be repeated.

THE PRECEDENT THIS FOLLOWS, and the reason it is a single owned entry rather than
another scenario: `scenarios/guf_stress.guf_fiscal_integration` was already doing this
assembly, and had drifted — folding the fee into the levy so it was invisible in the
very block meant to show it, and carrying its own copy of the fee/levy ratio. An
assembly point nobody owns drifts from the primitives it assembles. Tests pin this one
against those primitives directly.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.data import SLU_HECTARES
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import PIPELINE_SHARED_PARAMS, fiscal_snapshot
from hours_eoh.land.collective import (
    PER_PARCEL_BASIS, compute_collective_guf, default_parcel_count, per_parcel_guf,
    sample_scaled_guf)
from hours_eoh.scenarios.stationarity import GUF_CAP_RULES, d3_consumption

__all__ = ["land_hectares_of", "collective_snapshot", "SHARED_WITH_PIPELINE",
           "STATE_FIELDS_TO_PIPELINE"]

#: THE QUANTITIES BOTH HALVES TAKE BY KEYWORD, fiscal name → pipeline name
#: (2026-10-14). A `fiscal_kwargs` entry naming one of these is passed to the
#: pipeline too, so the two halves cannot run on different values of it. Until
#: this table existed the guard below refused frame quantities BY NAME and
#: forwarded everything else to the fiscal layer only: an institution passing
#: its own age mix got fiscal expenditure on that mix and personal EOH on the
#: shipped one. DERIVED from `core.fiscal.PIPELINE_SHARED_PARAMS` (the one
#: table both assembly points read), less the four this function takes another
#: way — the age mix as its own argument, the other three from the state.
#: `tests/scenarios/test_collective.py::TestBothHalvesSeeOneValue` derives the
#: shared set from the two signatures and requires every member to be here or
#: refused — its own gap: a rename it is not told about is invisible.
_TAKEN_OTHERWISE = frozenset({"age_fractions", "registration_epsilon",
                              "deferred_ecological", "capital_eoh_eliminated"})
SHARED_WITH_PIPELINE: dict[str, str] = {
    f: p for f, p in PIPELINE_SHARED_PARAMS.items() if f not in _TAKEN_OTHERWISE}

#: THE STATE'S FIELDS THE PIPELINE TAKES, state key → pipeline name — the ones
#: `simulate_period` passes. The last three were dropped here until 2026-10-14
#: while `fiscal_snapshot(state=…)` read the same state: a state carrying a
#: register at ε 0.70 moved fiscal expenditure 3.96× and the mint not at all.
STATE_FIELDS_TO_PIPELINE: dict[str, str] = {
    "deferred_ecological":   "deferred_ecological",
    "knowledge_complexity":  "knowledge_complexity",
    "monitoring_capability": "monitoring_capability",
    "registration_epsilon":  "registration_epsilon",
    "capital_eoh_eliminated": "capital_eoh_eliminated",
    "capital_personal_eoh_fulfilled": "capital_personal_eoh_fulfilled",
}


def land_hectares_of(parcels: list[dict]) -> float:
    """
    Hectares under a parcel inventory.

    Governing equation:

        hectares = Σ area_slu(p) × SLU_HECTARES        [1 SLU = 100 m²]

    Units: hectares. The conversion is `data.SLU_HECTARES`, not a literal —
    "1 SLU = 100 m²" lived in three docstrings and no value until 2026-08-28,
    which is the prose-only-constant pattern this repo has now found four times.

    Worked example: the shipped urban archetype is 30,250 SLU → 302.5 ha.
    """
    return sum(float(p.get("area_slu", 0.0)) for p in parcels) * SLU_HECTARES


def collective_snapshot(
    state: dict,
    *,
    land_hectares: float | None = None,
    parcels: list[dict] | None = None,
    psi_policy: str = "retired",
    available_labor_eoh: float | None = None,
    rationing: str = "survival_first",
    age_fractions: dict[str, float] | None = None,
    guf_sample: list[dict] | None = None,
    guf_parcel_count: float | None = None,
    guf_cap: float | str | None = "payable",
    **fiscal_kwargs: Any,
) -> dict:
    """
    Run one collective end to end with the frame stated once.

    Governing chain — all three steps in `core/` and `land/`, none of it
    re-implemented here:

        pipeline = eoh_to_teh_pipeline(state, land)         → teh_created
        guf      = compute_collective_guf(parcels, ε)       → fee revenue
        fiscal   = fiscal_snapshot(state, land, guf)        → levies, Trust

    THIS FUNCTION PASSES THE THREE HAND-PASSED VALUES, BY VALUE, so no caller can forget
    one:

      * `labor_income` is the pipeline's `teh_created` — what registered human
        labour actually earned this period, not an assumed income.
      * `eco_eoh_override` is the pipeline's ecological obligation. So the fiscal layer
      sizes its allocation against the SAME number the pipeline computed, and does not
      resolve the frame a second time. This is the
        92.8× defect made structurally impossible.
      * `guf_revenue` is the fee the parcel inventory actually raises, so the obligation
      the Phase 4 partition moved to GUF arrives where the partition sent it.

    THE LAND FRAME COMES FROM THE PARCELS WHEN THE CALLER GIVES THEM. One inventory both
    pays the fee and sizes the ecological obligation, so the two cannot describe
    different jurisdictions. Supplying `land_hectares` alongside `parcels` is REFUSED
    rather than silently resolved — the same discipline `total_eoh` applies to
    base-vs-area and `fiscal_snapshot` to state-vs-loose: an area the caller believes is
    in force and is not is the silently-ignored-parameter failure this repo keeps
    finding.

    ε-behaviour ----------- The function reads ε from the state, so all three calls see
    the same value. At ε=0 registration is minimal and `teh_created` is small; at ε=0.99
    human labour approaches zero while GUF revenue does not — which is the substitution
    the partition is about, and `trust["guf_over_levy"]` reports it.

    Args:
        state: An economy state — `core.simulation.make_economy_state()` or any
            mapping carrying `population`, `epsilon`, `capital_stock_teh`,
            `capital_age_ratio`, `trust_balance`, `ecosystem_health`. Must also
            carry `labor_income_teh`, which this function overwrites with the
            pipeline's own figure (see above).
        land_hectares: Stewarded area. Omit it when you give `parcels`.
        parcels: GUF parcel inventory. When given, it supplies BOTH the fee and
            the land area. Omit for a collective with no assessed land — GUF
            revenue is then 0.0 and the snapshot says so.
        psi_policy: Forwarded to `compute_collective_guf`. Default `"retired"`
            matches the shipped default (Ψ ≡ 1, the 2026-08-20 sign-off).
        available_labor_eoh: The labour this collective actually has, EOH-hours
            per year (employment × hours per worker, from a labour force
            survey). **Supply it, or the snapshot measures DEMAND and calls it
            fulfilment**: omitted, the pipeline assumes every hour of
            human-carried obligation is worked and mints on that assumption.
            Supplied, the mint tracks what was SERVED and the shortfall is
            booked as deferral — and `labor_income` in the fiscal layer is the
            constrained figure, so the Trust is not funded by work nobody did.
            A per-period input rather than a state field, as
            `make_economy_state` documents for per-period inputs.
        rationing: Forwarded to the pipeline — which obligation a labour
            shortfall defers first. `"survival_first"` (default) or
            `"pro_rata"`. Inert unless the caller supplies `available_labor_eoh`.
        age_fractions: The population's age mix, `{group: fraction}` over
            `AGE_GROUPS`. Reaches BOTH halves — the pipeline's personal
            obligation (`age_distribution`) and the fiscal layer's guarantee.
            A state built with `make_economy_state(age_fractions=…)` carries it and need
            not repeat it; the function refuses a DIFFERENT value beside it.
            Omitted from both, both halves read the shipped mix.
        guf_sample: A parcel SAMPLE that prices the fee when the frame has no
            parcel inventory, only a count (2026-10-14, author: the entry
            point follows stationarity). The fee is the sample's mean times
            `guf_parcel_count` (`land.collective.sample_scaled_guf`); the LAND
            still comes from `land_hectares`, never from the sample. Refused
            beside `parcels`, which already carry both.
        guf_parcel_count: The parcels that scale the sample's mean. None →
            `land.collective.default_parcel_count(population)`, stationarity's
            default. WITHOUT a sample (2026-10-15, author) it prices the fee's
            measured per-parcel half, `per_parcel_guf` — the area part NOT
            SUPPLIED, so the fee is a lower bound. Refused beside `parcels`.
        guf_cap: How much of the ASSESSED fee the Trust COLLECTS (2026-10-15, author:
            "you can't pay what isn't minted"). `"payable"` (default) collects
            at most the mint less the levy and D3 consumption —
            `scenarios.stationarity`'s rule, so both read one ceiling; a float
            caps at that share of the mint; None collects the whole assessed
            fee, the pre-2026-10-15 arithmetic. The report gives the rest as
            `land_fee["unpaid"]` and never books it: a fee no one can pay is a shortfall
            on the land a collective claims, not Trust revenue.
            The ceiling is an UPPER bound on collection — it is the whole
            collective's disposable mint, and only private holders pay.
        **fiscal_kwargs: Forwarded to `fiscal_snapshot` — policy only (levy
            rates, dividend split). The function refuses frame and state quantities, and
            forwards a quantity the pipeline also takes (`SHARED_WITH_PIPELINE`) to
            BOTH, never to one.

    Returns:
        dict with `pipeline`, `fiscal`, `guf`, `land_fee` (assessed /
        collected / unpaid), `frame` and `verdict`. `guf["revenue"]` and the
        Trust's `guf_inflow` are the COLLECTED fee.

    Raises:
        ValueError: If both `land_hectares` and `parcels` are given, if neither
            is (and the state carries no land), if the state carries a land
            the call contradicts, if `fiscal_kwargs` restates a frame or state
            quantity, or if
            the state carries a deferred infrastructure backlog (compounding is
            a period dynamic — run `simulate_period`).
    """
    # Written as one branch chain rather than two guards so the type narrows:
    # after this, `hectares` is a float and the caller supplied exactly one of
    # the pair. Two answers to one question is how a frame comes apart, and a
    # missing answer is a collective with no frame at all.
    if guf_sample is not None and parcels is not None:
        raise ValueError("pass parcels OR guf_sample, not both: an inventory "
                         "already prices its own fee")
    if guf_parcel_count is not None and parcels is not None:
        raise ValueError("pass parcels OR guf_parcel_count, not both: an inventory "
                         "already counts its own parcels")
    if isinstance(guf_cap, str) and guf_cap not in GUF_CAP_RULES:
        raise ValueError(f"guf_cap rule must be one of {GUF_CAP_RULES}, got {guf_cap!r}")
    if isinstance(guf_cap, float) and not 0.0 <= guf_cap:
        raise ValueError(f"guf_cap share must be >= 0, got {guf_cap}")
    if parcels is not None:
        if land_hectares is not None:
            raise ValueError(
                "pass land_hectares OR parcels, not both: parcels already carry "
                "the area, and two answers to one question is how a frame comes "
                "apart. Use land_hectares only when there is no inventory."
            )
        hectares = land_hectares_of(parcels)
    elif land_hectares is not None:
        hectares = float(land_hectares)
    elif state.get("land_hectares") is not None:
        hectares = float(state["land_hectares"])
    else:
        raise ValueError(
            "supply land_hectares or parcels: the ecological obligation is "
            "keyed to AREA, and a collective that states no land has no frame. "
            "See scenarios/frame.py for what an undeclared pairing costs."
        )
    # A STATE MAY CARRY THE LAND (2026-10-14, `make_economy_state`'s
    # `land_hectares`): a third answer to the one question, refused unless equal.
    state_land = state.get("land_hectares")
    if state_land is not None and float(state_land) != hectares:
        raise ValueError(
            f"the state carries {float(state_land):,.1f} ha and the call states "
            f"{hectares:,.1f} ha: land is one quantity. Build a state with the "
            "collective's land, or leave the state's land unset")

    # The frame's quantities, then the state's (the fiscal layer would refuse
    # these only when the state carries the key; refused here whatever it
    # carries, so the message names the entry point), then the age mix (an
    # argument of its own) and the land per head (the land is stated).
    owned = {"population", "capital_stock_teh", "capital_age_ratio", "epsilon",
             "ecosystem_health", "trust_balance", "labor_income",
             "ecological_area_hectares", "eco_eoh_override", "guf_revenue",
             "state", "deferred_ecological", "capital_eoh_eliminated",
             "registration_epsilon",
             "age_fractions", "ecological_hectares_per_capita"}
    clash = owned & set(fiscal_kwargs)
    if clash:
        raise ValueError(
            f"these are the frame's to state, not the caller's: {sorted(clash)}. "
            "Build a different state instead of overriding one."
        )
    # A deferred infrastructure backlog compounds PER PERIOD (`simulate_period`
    # turns it into `infrastructure_compounding_eoh` from its age); a snapshot
    # has no period to compound over, and reading it as zero would be the
    # stranded field this function exists to forbid.
    if float(state.get("deferred_infrastructure_eoh") or 0.0) > 0.0:
        raise ValueError(
            "the state carries a deferred infrastructure backlog, which "
            "compounds per period; a snapshot cannot apply it. Run "
            "core.simulation.simulate_period, or state the backlog at zero."
        )

    # A STATE MAY CARRY THE AGE MIX (2026-10-14, `make_economy_state`'s
    # `age_fractions`). Two answers to one question are refused unless equal.
    state_ages = state.get("age_fractions")
    if state_ages is not None:
        if age_fractions is not None and dict(age_fractions) != dict(state_ages):
            raise ValueError("the state carries an age mix and a different one was "
                             "passed as age_fractions; build a different state")
        age_fractions = state_ages

    # Exactly one of the pair was supplied — written so the type narrows past
    # it rather than asserting what the guards above already established.
    epsilon = float(state["epsilon"])

    # THE STATE'S OWN PHYSICAL FIELDS REACH THE PIPELINE, as they do in
    # `simulate_period`. Until 2026-09-12 this call dropped `deferred_ecological`,
    # `knowledge_complexity` and `monitoring_capability`, so one state gave one
    # answer through the period engine and another through this entry point —
    # the stranded parameter, at the entry point the implementation guide names.
    # On a state built at defaults the blast radius is zero at every arc point
    # (all three resolve canonically from ε); it is a state carrying real values
    # that was being silently read as canonical. `.get` because any mapping
    # carrying the required keys is accepted.
    # And until 2026-10-14 it dropped three more that `simulate_period` passes
    # — `STATE_FIELDS_TO_PIPELINE` names all six.
    optional_physical = {
        to: state[k] for k, to in STATE_FIELDS_TO_PIPELINE.items()
        if state.get(k) is not None
    }
    shared = {to: fiscal_kwargs[k] for k, to in SHARED_WITH_PIPELINE.items()
              if k in fiscal_kwargs}
    pipeline = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=float(state["population"]),
        capital_stock=float(state["capital_stock_teh"]),
        capital_age_ratio=float(state["capital_age_ratio"]),
        ecosystem_health=float(state["ecosystem_health"]),
        ecological_area_hectares=hectares,
        available_labor_eoh=available_labor_eoh,
        rationing=rationing,
        age_distribution=age_fractions,
        **optional_physical,
        **shared,
    )
    # Two facts, not one: whether a supply was given, and whether it BOUND. The
    # pipeline's flag is the second — it is False both when no supply was given
    # and when an ample one was, and reading it as the first tells an institution
    # with enough labour that it measured demand.
    labour_supplied = available_labor_eoh is not None
    labour_constrained = bool(pipeline["labor_constrained"])

    guf_revenue = 0.0
    guf_count: float | None = None
    if parcels is not None:
        guf_revenue = float(
            compute_collective_guf(parcels, epsilon, psi_policy=psi_policy)
            ["guf_net_inflow"]
        )
    elif guf_sample is not None:
        guf_count = (default_parcel_count(float(state["population"]))
                     if guf_parcel_count is None else float(guf_parcel_count))
        guf_revenue = sample_scaled_guf(guf_sample, epsilon, guf_count, psi_policy=psi_policy)
    elif guf_parcel_count is not None:
        # A COUNT AND NO SAMPLE: the fee's measured half (2026-10-15, author:
        # "ship the per-parcel half first"); the area part is NOT SUPPLIED.
        guf_count = float(guf_parcel_count)
        guf_revenue = per_parcel_guf(epsilon, guf_count)

    # The state the fiscal layer sees: the caller's, with labour income replaced
    # by what the pipeline says was actually earned. Copied rather than mutated —
    # a function that edits its caller's state is a function whose result depends
    # on how many times it was called.
    fiscal_state = dict(state)
    fiscal_state["labor_income_teh"] = float(pipeline["teh_created"])

    def _fisc(guf: float) -> dict:
        return fiscal_snapshot(
            state=fiscal_state,
            ecological_area_hectares=hectares,
            eco_eoh_override=pipeline["eoh_by_domain"]["ecological"],
            guf_revenue=guf,
            age_fractions=age_fractions,
            **fiscal_kwargs,
        )

    # THE FEE ASSESSED IS NOT THE FEE COLLECTED (2026-10-15, author: "you
    # can't pay what isn't minted"). Holders pay from what they were paid, so
    # collection is bounded by the mint less the levy and D3 consumption —
    # stationarity's `payable` rule, on the fisc's OWN levy (the applied
    # value, not a second rate). The levy does not read the fee, so the first
    # call's levy is the second's; when the ceiling does not bind the first
    # call is the answer and the figures are those of the uncapped fee.
    mint = float(pipeline["teh_created"])
    fiscal = _fisc(guf_revenue)
    levy = float(fiscal["trust"]["levy_inflow"])
    d3 = d3_consumption(pipeline["eoh_by_domain"]["personal"],
                        pipeline["registration_by_domain"]["personal"],
                        pipeline["human_eoh_by_domain"]["personal"])
    payable = max(0.0, mint - levy - d3)
    if guf_cap is None:
        collected = guf_revenue
    elif guf_cap == "payable":
        collected = min(guf_revenue, payable)
    else:
        collected = min(guf_revenue, float(guf_cap) * mint)
    if collected < guf_revenue:
        fiscal = _fisc(collected)
    unpaid = guf_revenue - collected
    land_fee = {
        "assessed":        guf_revenue,
        "collected":       collected,
        "unpaid":          unpaid,
        "payable_ceiling": payable,
        "cap":             guf_cap,
        "ceiling_is_an_upper_bound": True,
    }

    return {
        "scenario": "collective_snapshot",
        "frame": {
            "population":     float(state["population"]),
            "land_hectares":  hectares,
            "capital_stock_teh": float(state["capital_stock_teh"]),
            "hectares_per_capita": hectares / max(float(state["population"]), 1.0),
            "epsilon":        epsilon,
            # The parcels the fee was assessed on: the inventory's, or the
            # count a sample was scaled to; 0 when no fee was assessed.
            "parcel_count":   (len(parcels) if parcels is not None
                               else guf_count if guf_count is not None else 0),
            "guf_basis":      ("parcel inventory" if parcels is not None
                               else "sample mean × parcel count" if guf_sample is not None
                               else PER_PARCEL_BASIS if guf_count is not None
                               else "none"),
            # Which quantity `pipeline["teh_created"]` is. `labour_supplied`
            # False: minted from obligation DEMANDED. True: checked against
            # the hours given, and `labor_constrained` says whether they BOUND.
            "labour_supplied":   labour_supplied,
            "labor_constrained": labour_constrained,
        },
        "pipeline": pipeline,
        "fiscal":   fiscal,
        "guf":      fiscal["guf"],
        "land_fee": land_fee,
        "verdict": (
            f"one frame: {float(state['population']):,.0f} people on "
            f"{hectares:,.1f} ha at ε={epsilon:.2f}. The pipeline's ecological "
            f"obligation is passed to the fiscal layer by value, so the two "
            f"cannot resolve the frame differently — the failure that read "
            f"92.8× in the implementation guide's own example. "
            + (
                f"Labour was SUPPLIED and BOUND, so the mint is what was served; "
                f"{float(pipeline['deferred_total']):,.0f} h/yr of obligation "
                f"had no hours to meet it and is booked as deferral. "
                if labour_constrained else
                "Labour was SUPPLIED and sufficed: every human-carried hour "
                "had hours to meet it, so the mint is what was served and "
                "nothing is deferred. "
                if labour_supplied else
                "No labour supply was given, so the mint assumes every "
                "human-carried hour was worked — this is DEMAND, not "
                "fulfilment. Pass `available_labor_eoh` to verify it. "
            )
            + (
                f"GUF is assessed at {guf_revenue:,.0f} TEH/yr against a relocated "
                f"obligation of {fiscal['guf']['obligation']:,.2f}; read "
                f"`guf.coverage` with its own caveat, and "
                f"`fiscal['trust']['guf_over_levy']` "
                f"({fiscal['trust']['guf_over_levy']:.4f}) for whether the fee "
                f"has overtaken the contracting labour levy."
                if parcels is not None else
                f"GUF is assessed at {guf_revenue:,.0f} TEH/yr, priced as a parcel "
                f"sample's mean fee over {guf_count:,.0f} parcels — stationarity's "
                f"convention, which ASSUMES every parcel pays the sample's mean "
                f"(`fiscal['trust']['guf_over_levy']` "
                f"{fiscal['trust']['guf_over_levy']:.4f}). "
                if guf_sample is not None else
                f"GUF is assessed at {guf_revenue:,.0f} TEH/yr over {guf_count:,.0f} "
                f"parcels — the per-parcel half only. The AREA part is NOT "
                f"SUPPLIED: it needs a class→use mapping and a location value, "
                f"so this is a LOWER bound on the fee. "
                if guf_count is not None else
                "No parcel inventory supplied, so GUF revenue is 0.0 — the "
                "recurring obligation the partition moved to the fee is "
                "reported by `fiscal['ecological']['relocated_to_guf']` and "
                "funded by nothing. That is a frame with no assessed land, not "
                "a collective that owes nothing."
            )
            + (
                f" Of the {guf_revenue:,.0f} TEH/yr assessed, "
                f"{unpaid:,.0f} goes UNPAID: it exceeds what the "
                f"mint leaves holders ({payable:,.0f} TEH/yr after levy and D3), "
                f"so it is a reported shortfall on the land claimed, not revenue."
                if unpaid > 0.0 else ""
            )
        ),
    }
