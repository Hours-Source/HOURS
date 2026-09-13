"""
THE REGISTER'S FAILURE MODEL, AND THE CHECK THAT WOULD SEE IT — reporting only.

`research/anchor_determinacy.registration_leverage()` establishes the exposure:
registration is unit elastic on the money supply and is the SOLE lever. This
module answers the question that leaves open — *which registration decision,
moving which share, benefiting whom* — because until that is stated the six
candidate governance forms cannot be compared, only listed.

WHY A FAILURE MODEL BEFORE A MECHANISM
---------------------------------------
The framework's stated criticism of fiat is that issuance rests on discretion the
holder cannot see. The property that answers the hole-digger objection — that
only registered obligation mints — is the SAME property that concentrates that
risk in whoever maintains the register. That is not an incidental weakness; it is
the anchor's own argument turned around, and the anchor page carries it as a
live falsifier under "What would change our mind".

WHAT THIS MODULE DOES NOT DO, and the boundary is the point
------------------------------------------------------------
It does not choose a governance form. `notes/governance/the-check-not-the-constitution.md`
argues that choosing one is not the framework's job: a governance form is
`normative` in the provenance scheme's sense — it names a decider, and no dataset
retires it. What the framework can ship is the DECLARATION requirement and the
CHECK, which work whatever form a collective runs.

It also does not model an institution. There is no actor here, no incentive and
no defection: a simulation of capture would be a simulation of assumptions about
capture. What is computed is the mechanical consequence of a registration
decision on issuance, which is a property of this model and not a claim about
anyone's behaviour.

THE DETECTION PRINCIPLE
-----------------------
Capture has a signature that ordinary growth does not: **the registered share
moves while the physical obligation does not.** Registration RELOCATES obligation
across the ledger boundary and never creates it — `tests/test_registration_containment.py`
enforces that — so a rise in registered EOH unaccompanied by a rise in
`total_eoh` is issuance without a physical event behind it. That is what a
monitor can see, and it is why the monitor watches the SHARE rather than the
mint: the mint moving is not evidence of anything, since it moves whenever the
obligation does.

WHAT THE MONITOR IS NOT ALLOWED TO DO
--------------------------------------
- **It carries no shipped threshold.** `drift_monitor` requires one. A threshold
  calibrated to the shipped configuration is `LEVY_SUFFICIENCY_WARN` again — a
  warning that cannot fire — and it is failure mode 9 applied to the framework's
  own worst exposure. The threshold is the collective's declaration.
- **It reports drift; it does not adjudicate.** Naming a drift is a measurement.
  Calling it capture is a judgement with a defendant, and this module has no
  standing to make it.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

#: `registration_by_domain` and `registered_eoh_by_domain` carry an aggregate
#: `non_personal` key ALONGSIDE the domains it aggregates. Summing the dict
#: naively double-counts and the total silently stops matching `teh_created` —
#: caught the first time this module tried it. The real domains are these.
MINT_DOMAINS: tuple[str, ...] = ("personal", "infrastructure", "ecological", "knowledge")


def mint_decomposition(epsilon: float = 0.40, **kwargs: Any) -> dict[str, Any]:
    """
    Where the minted TEH comes from, by domain.

    `teh_created = mean_multiplier · Σ_domain (human_eoh_d · registration_share_d)`,
    so each domain's contribution is its registered EOH times the multiplier. The
    identity is asserted rather than assumed: `reconciles` compares the
    reconstruction against the pipeline's own `teh_created`.

    Returns per domain: the registration share, the registered EOH, the implied
    human EOH behind it, that domain's share OF THE MINT, and its HEADROOM —
    `1 − share`, the fraction of that domain's human obligation a register could
    still admit without any physical change.

    Headroom is the quantity the failure model turns on. A domain that is already
    fully registered cannot be captured further; one at a low share with a large
    human obligation is where issuance can be moved most.
    """
    p = eoh_to_teh_pipeline(epsilon=epsilon, **kwargs)
    shares = p["registration_by_domain"]
    registered = p["registered_eoh_by_domain"]
    m = float(p["mean_multiplier"])

    total_registered = sum(float(registered[d]) for d in MINT_DOMAINS)
    rows: dict[str, dict[str, float]] = {}
    for d in MINT_DOMAINS:
        s = float(shares[d])
        reg = float(registered[d])
        rows[d] = {
            "registration_share": s,
            "registered_eoh": reg,
            "human_eoh": (reg / s) if s > 0.0 else 0.0,
            "share_of_mint": (reg / total_registered) if total_registered > 0.0 else 0.0,
            "headroom": 1.0 - s,
            # exact, because the mint is linear in each share
            "d_mint_per_unit_share": m * ((reg / s) if s > 0.0 else 0.0),
        }

    reconstructed = total_registered * m
    return {
        "epsilon": epsilon,
        "by_domain": rows,
        "mean_multiplier": m,
        "teh_created": float(p["teh_created"]),
        "total_eoh": float(p["total_eoh"]),
        "reconstructed_mint": reconstructed,
        "reconciles": abs(reconstructed - float(p["teh_created"])) < 1.0,
        "reporting_only": True,
    }


def capture_channels(epsilon: float = 0.40, **kwargs: Any) -> dict[str, Any]:
    """
    The registration decisions ranked by how far each can move issuance.

    Ranked on `d_mint_per_unit_share × headroom` — the mint a decision could add
    if that domain were admitted in full. A domain with a steep sensitivity but
    no headroom is not a channel; one with headroom and no obligation behind it
    is not either. The product is what names the channel that matters.

    The ranking is a property of the SHIPPED configuration and moves with ε: the
    obligation mix changes across the arc, so which decision is most consequential
    changes with it. Callers should not quote a single ranking as the framework's.
    """
    d = mint_decomposition(epsilon, **kwargs)
    ranked = sorted(
        (
            {
                "domain": name,
                "registration_share": r["registration_share"],
                "headroom": r["headroom"],
                "share_of_mint": r["share_of_mint"],
                "d_mint_per_unit_share": r["d_mint_per_unit_share"],
                "mint_if_fully_admitted": r["d_mint_per_unit_share"] * r["headroom"],
            }
            for name, r in d["by_domain"].items()
        ),
        key=lambda x: x["mint_if_fully_admitted"],
        reverse=True,
    )
    live = [c for c in ranked if c["mint_if_fully_admitted"] > 0.0]
    return {
        "epsilon": epsilon,
        "channels": ranked,
        "widest": live[0]["domain"] if live else None,
        "teh_created": d["teh_created"],
        "note": (
            "ranked by mint reachable without any physical change. A domain with "
            "no human obligation behind it is not a channel however low its share"
        ),
        "reporting_only": True,
    }


def capture_scenario(
    domain: str,
    share_delta: float,
    epsilon: float = 0.40,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    One registration decision, priced: admit `share_delta` more of `domain`.

    Reports the mint change AND the obligation change, because the pair is the
    whole point. `total_eoh` is computed from physical state and takes no
    registration argument at all — `tests/test_registration_containment.py`
    asserts the signature stays that way — so the obligation CANNOT move in
    response to a registration decision.

    That is what makes the signature diagnostic rather than suggestive: any mint
    change here arrives with `obligation_change == 0.0` by construction, and a
    real economy in which issuance rose because more obligation existed would
    show both moving together.

    Args:
        domain: one of MINT_DOMAINS.
        share_delta: change in that domain's registration share. Positive admits
            more; negative is the refusal direction, which has a victim rather
            than a beneficiary and is modelled the same way.
    """
    if domain not in MINT_DOMAINS:
        raise ValueError(f"domain must be one of {MINT_DOMAINS}, got {domain!r}")

    before = mint_decomposition(epsilon, **kwargs)
    row = before["by_domain"][domain]
    new_share = row["registration_share"] + share_delta
    if not 0.0 <= new_share <= 1.0:
        raise ValueError(
            f"{domain} share would become {new_share:.4f}; a registration share "
            "outside [0, 1] is not a decision anyone can take"
        )

    delta_mint = row["d_mint_per_unit_share"] * share_delta
    after_mint = before["teh_created"] + delta_mint
    return {
        "domain": domain,
        "epsilon": epsilon,
        "share_before": row["registration_share"],
        "share_after": new_share,
        "mint_before": before["teh_created"],
        "mint_after": after_mint,
        "mint_change": (after_mint / before["teh_created"] - 1.0)
        if before["teh_created"] > 0.0
        else 0.0,
        "obligation_before": before["total_eoh"],
        "obligation_after": before["total_eoh"],
        "obligation_change": 0.0,
        "beneficiary": (
            f"whoever performs the {domain} labour newly admitted, and whoever "
            "holds TEH at the moment of issuance"
        ),
        "signature": (
            "registered share moved, physical obligation did not — issuance "
            "without a physical event behind it"
        ),
        "reporting_only": True,
    }


def drift_monitor(
    baseline_share: float,
    observed_share: float,
    threshold: float,
    obligation_change: float = 0.0,
) -> dict[str, Any]:
    """
    THE CHECK. Has the registered share moved further than the collective
    declared it would tolerate, without the obligation moving to justify it?

    `threshold` is REQUIRED and has no default anywhere in this module. It is the
    collective's declaration, not the framework's recommendation — the same
    treatment `currency_per_teh` receives, and for the same reason: a shipped
    value would bury the judgement the framework most needs visible, and a
    threshold calibrated to the shipped configuration is a warning that cannot
    fire.

    Args:
        baseline_share: the registered share the collective declared it was at.
        observed_share: the registered share now.
        threshold: absolute drift the collective declared it would tolerate.
            Must be positive — a threshold of 0 makes every rounding a breach.
        obligation_change: fractional change in `total_eoh` over the same period.
            Supply it. A share that moved because the obligation moved is not the
            same event as one that moved on its own, and the monitor cannot tell
            them apart without this.

    Returns `breached` (did the drift exceed the threshold) and `unexplained`
    (did it do so while the obligation held still). **Only the second is the
    capture signature**, and the monitor reports both rather than collapsing them,
    because a collective that automates fast will breach the first legitimately.
    """
    if threshold <= 0.0:
        raise ValueError(
            f"threshold must be positive, got {threshold}. A zero threshold makes "
            "every rounding a breach and is not a declaration"
        )
    for name, v in (("baseline_share", baseline_share), ("observed_share", observed_share)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {v}")

    drift = observed_share - baseline_share
    breached = abs(drift) > threshold
    unexplained = breached and abs(obligation_change) < abs(drift) / max(baseline_share, 1e-9)
    return {
        "baseline_share": baseline_share,
        "observed_share": observed_share,
        "drift": drift,
        "threshold": threshold,
        "breached": breached,
        "obligation_change": obligation_change,
        "unexplained": unexplained,
        "verdict": (
            "drift within the declared threshold" if not breached
            else "drift exceeds the declared threshold, and the obligation did "
                 "not move with it" if unexplained
            else "drift exceeds the declared threshold, but the obligation moved too"
        ),
        "this_is_not_an_accusation": (
            "a drift is a measurement. Whether it is capture is a judgement about "
            "people, which this function has no standing to make"
        ),
        "reporting_only": True,
    }


def capture_report(epsilon: float = 0.40, **kwargs: Any) -> dict[str, Any]:
    """The failure model as one call, for the governance handoff."""
    ch = capture_channels(epsilon, **kwargs)
    widest = ch["widest"]
    return {
        "epsilon": epsilon,
        "channels": ch["channels"],
        "widest_channel": widest,
        "worked_example": capture_scenario(widest, 0.01, epsilon, **kwargs) if widest else None,
        "what_the_monitor_needs": [
            "a declared baseline share",
            "a declared drift threshold — the framework ships neither",
            "the obligation change over the same period, or the monitor cannot "
            "distinguish capture from an economy that automated",
        ],
        "what_this_does_not_establish": [
            "that capture has occurred anywhere. No actor, incentive or defection "
            "is modelled here.",
            "that any governance form bounds capture. A monitor makes drift "
            "visible; §7's falsifier asks for it to be BOUNDED, which is a "
            "different and unanswered question.",
        ],
        "reporting_only": True,
    }
