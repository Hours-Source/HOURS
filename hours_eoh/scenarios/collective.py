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

Every one is a place the frame can come apart. It has come apart six times, most
recently at **92.8× inside the guide's own worked example** — the pipeline
resolving the ecological area from population while the fiscal layer took the
whole contiguous US. This function makes that arithmetic unavailable to get
wrong: state the frame once, and the three calls cannot disagree.

WHY IT LIVES IN `scenarios/` AND NOT IN `core/`. `core/fiscal` needs a ground-use
fee it is owed, and `land/` imports `core/`, so core cannot ask for it. The
inversion is not worth having: moving GUF into core would assert that land
tenure is physics, and `land/` is a separate layer precisely because it is not.
`scenarios/` may import `core/` AND `land/`, so the assembly belongs here — one
layer up, owning both sides. That is the layer rule working as designed rather
than being worked around.

WHY IT DOES NOT USE `research/exchange.CollectiveFrame`. `research/` is not
importable by `scenarios/` (it is experimental and explicitly not depended on).
Rather than duplicate that dataclass, this takes the state container `core/`
already has — `core.simulation.make_economy_state()` — which carries population,
capital, trust balance, ecosystem health and ε, and which `fiscal_snapshot`
learned to read on 2026-08-29. The only thing a state does not carry is LAND,
because the ecological domain was keyed to area later than the state was
written; land is therefore the one extra argument.

THE PRECEDENT THIS FOLLOWS, and the reason it is a single owned entry rather
than another scenario: `scenarios/guf_stress.guf_fiscal_integration` was already
doing this assembly, and had drifted — folding the fee into the levy so it was
invisible in the very block meant to show it, and carrying its own copy of the
fee/levy ratio. An assembly point nobody owns drifts from the primitives it
assembles. This one is pinned against those primitives directly.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.data import SLU_HECTARES
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.land.collective import compute_collective_guf

__all__ = ["land_hectares_of", "collective_snapshot"]


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
    **fiscal_kwargs: Any,
) -> dict:
    """
    Run one collective end to end with the frame stated once.

    Governing chain — all three steps in `core/` and `land/`, none of it
    re-implemented here:

        pipeline = eoh_to_teh_pipeline(state, land)         → teh_created
        guf      = compute_collective_guf(parcels, ε)       → fee revenue
        fiscal   = fiscal_snapshot(state, land, guf)        → levies, Trust

    THE THREE HAND-PASSED VALUES ARE PASSED HERE, BY VALUE, so no caller can
    forget one:

      * `labor_income` is the pipeline's `teh_created` — what registered human
        labour actually earned this period, not an assumed income.
      * `eco_eoh_override` is the pipeline's ecological obligation, so the
        fiscal layer sizes its allocation against the SAME number the pipeline
        computed rather than resolving the frame a second time. This is the
        92.8× defect made structurally impossible.
      * `guf_revenue` is the fee the parcel inventory actually raises, so the
        obligation the Phase 4 partition moved to GUF arrives where it was sent.

    THE LAND FRAME COMES FROM THE PARCELS WHEN THEY ARE GIVEN. One inventory
    both pays the fee and sizes the ecological obligation, so the two cannot
    describe different jurisdictions. Supplying `land_hectares` alongside
    `parcels` is REFUSED rather than silently resolved — the same discipline
    `total_eoh` applies to base-vs-area and `fiscal_snapshot` to state-vs-loose:
    an area the caller believes is in force and is not is the
    silently-ignored-parameter failure this repo keeps finding.

    ε-behaviour
    -----------
    ε is read from the state, so it is the same value in all three calls. At
    ε=0 registration is minimal and `teh_created` is small; at ε=0.99 human
    labour approaches zero while GUF revenue does not — which is the
    substitution the partition is about, and `trust["guf_over_levy"]` reports it.

    Args:
        state: An economy state — `core.simulation.make_economy_state()` or any
            mapping carrying `population`, `epsilon`, `capital_stock_teh`,
            `capital_age_ratio`, `trust_balance`, `ecosystem_health`. Must also
            carry `labor_income_teh`, which this function overwrites with the
            pipeline's own figure (see above).
        land_hectares: Stewarded area. Omit when `parcels` is given.
        parcels: GUF parcel inventory. When given, it supplies BOTH the fee and
            the land area. Omit for a collective with no assessed land — GUF
            revenue is then 0.0 and the snapshot says so.
        psi_policy: Forwarded to `compute_collective_guf`. Default `"retired"`
            matches the shipped default (Ψ ≡ 1, the 2026-08-20 sign-off).
        **fiscal_kwargs: Forwarded to `fiscal_snapshot` — policy only (levy
            rates, dividend split). Frame quantities are refused.

    Returns:
        dict with `pipeline`, `fiscal`, `guf`, `frame` and `verdict`.

    Raises:
        ValueError: If both `land_hectares` and `parcels` are given, if neither
            is, or if `fiscal_kwargs` restates a frame quantity.
    """
    # Written as one branch chain rather than two guards so the type narrows:
    # after this, `hectares` is a float and the caller supplied exactly one of
    # the pair. Two answers to one question is how a frame comes apart, and a
    # missing answer is a collective with no frame at all.
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
    else:
        raise ValueError(
            "supply land_hectares or parcels: the ecological obligation is "
            "keyed to AREA, and a collective that states no land has no frame. "
            "See scenarios/frame.py for what an undeclared pairing costs."
        )

    owned = {"population", "capital_stock_teh", "capital_age_ratio", "epsilon",
             "ecosystem_health", "trust_balance", "labor_income",
             "ecological_area_hectares", "eco_eoh_override", "guf_revenue",
             "state"}
    clash = owned & set(fiscal_kwargs)
    if clash:
        raise ValueError(
            f"these are the frame's to state, not the caller's: {sorted(clash)}. "
            "Build a different state instead of overriding one."
        )

    # Exactly one of the pair was supplied — written so the type narrows past
    # it rather than asserting what the guards above already established.
    epsilon = float(state["epsilon"])

    pipeline = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=float(state["population"]),
        capital_stock=float(state["capital_stock_teh"]),
        capital_age_ratio=float(state["capital_age_ratio"]),
        ecosystem_health=float(state["ecosystem_health"]),
        ecological_area_hectares=hectares,
    )

    guf_revenue = 0.0
    if parcels is not None:
        guf_revenue = float(
            compute_collective_guf(parcels, epsilon, psi_policy=psi_policy)
            ["guf_net_inflow"]
        )

    # The state the fiscal layer sees: the caller's, with labour income replaced
    # by what the pipeline says was actually earned. Copied rather than mutated —
    # a function that edits its caller's state is a function whose result depends
    # on how many times it was called.
    fiscal_state = dict(state)
    fiscal_state["labor_income_teh"] = float(pipeline["teh_created"])

    fiscal = fiscal_snapshot(
        state=fiscal_state,
        ecological_area_hectares=hectares,
        eco_eoh_override=pipeline["eoh_by_domain"]["ecological"],
        guf_revenue=guf_revenue,
        **fiscal_kwargs,
    )

    return {
        "scenario": "collective_snapshot",
        "frame": {
            "population":     float(state["population"]),
            "land_hectares":  hectares,
            "capital_stock_teh": float(state["capital_stock_teh"]),
            "hectares_per_capita": hectares / max(float(state["population"]), 1.0),
            "epsilon":        epsilon,
            "parcel_count":   0 if parcels is None else len(parcels),
        },
        "pipeline": pipeline,
        "fiscal":   fiscal,
        "guf":      fiscal["guf"],
        "verdict": (
            f"one frame: {float(state['population']):,.0f} people on "
            f"{hectares:,.1f} ha at ε={epsilon:.2f}. The pipeline's ecological "
            f"obligation is passed to the fiscal layer by value, so the two "
            f"cannot resolve the frame differently — the failure that read "
            f"92.8× in the implementation guide's own example. "
            + (
                f"GUF raises {guf_revenue:,.0f} TEH/yr against a relocated "
                f"obligation of {fiscal['guf']['obligation']:,.2f}; read "
                f"`guf.coverage` with its own caveat, and "
                f"`fiscal['trust']['guf_over_levy']` "
                f"({fiscal['trust']['guf_over_levy']:.4f}) for whether the fee "
                f"has overtaken the contracting labour levy."
                if parcels is not None else
                "No parcel inventory supplied, so GUF revenue is 0.0 — the "
                "recurring obligation the partition moved to the fee is "
                "reported by `fiscal['ecological']['relocated_to_guf']` and "
                "funded by nothing. That is a frame with no assessed land, not "
                "a collective that owes nothing."
            )
        ),
    }
