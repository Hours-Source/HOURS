"""
Phase 4c — who owes the reset cost on land no collective holds.

**Author decision (2026-08-17): unowned land is FEDERATION.** A reset cost with
no holder does not go uncollected; it falls to the federation commons.

THE RULE, and why it is one line rather than a special case
-----------------------------------------------------------
GUF is the fee for EXCLUSIVE USE. The whole partition rests on that: holding
land to the exclusion of others is what creates the obligation to hold it in
condition. So the question "who pays when nobody holds it exclusively?" answers
itself once the federation is admitted as a holder:

    Land held by no member collective is held by the FEDERATION,
    and its reset cost is a federation commons obligation.

**Federal land is not an exception to this — it is the central case.** A
national park is not unowned; the federation is its holder, and it owes exactly
what any other holder owes on land of that condition. What is genuinely
residual is much smaller than "all public land": it is land under no tenure at
all.

WHAT THIS IS NOT
----------------
It is not a new funding mechanism. `research/coasean.simulate_federation`
already carries a federation commons, funded by a levy tithe and consolidation
escheats (reconciliation §8.7). This is a DRAW against it, and the wiring is an
allocation rule, not new mechanics.

THE OPEN QUANTITY, stated rather than filled
--------------------------------------------
Which US land sits under no exclusive holding. `reference/land_stewardship`'s
ERS Major Land Uses gives area by USE class and carries no TENURE split, so the
allocation below is driven by a caller-supplied tenure fraction per class. The
obvious unknown is "Miscellaneous other land" (90.6 Mha) — the residual class in
a use-based survey is exactly where a tenure question hides.

resolves_by: BLM Public Land Statistics reports federal surface acreage by
agency and state, and state trust-land inventories cover the rest. FIELD:
surface acres under Federal/State/private tenure by class. That is a tenure
survey rather than a use survey, which is the instrument this needs.

Layer: scenarios/ — imports core/ and reference/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.reference.land_stewardship import land_hectares_by_class

#: Tenure classes an obligation can be assigned to. `federation` is the residual
#: and it is NEVER "uncollected" — that is the decision this module implements.
TENURE_CLASSES: tuple[str, ...] = ("member_collective", "federation")


def allocate_by_tenure(
    obligation_hours: float,
    federation_fraction: float,
) -> dict:
    """
    Split a land obligation between member collectives and the federation.

    Governing equation:

        federation_share = obligation × federation_fraction
        member_share     = obligation × (1 − federation_fraction)

    units: labour-hours per year, in whatever period the obligation was stated.

    The identity `member + federation == obligation` is the whole content: no
    part of a land obligation is unassigned, which is what "unowned land is
    federation" means operationally. Asserted in the tests, not assumed.

    Args:
        obligation_hours:    The reset obligation to allocate (h/yr).
        federation_fraction: Share of the underlying land under no member
                             collective's exclusive holding, ∈ [0, 1].
    """
    if obligation_hours < 0.0:
        raise ValueError(f"obligation_hours must be >= 0, got {obligation_hours}")
    if not 0.0 <= federation_fraction <= 1.0:
        raise ValueError(
            f"federation_fraction must be in [0, 1], got {federation_fraction}"
        )
    federation = obligation_hours * federation_fraction
    return {
        "obligation_hours":    obligation_hours,
        "federation_fraction": federation_fraction,
        "federation_hours":    federation,
        "member_hours":        obligation_hours - federation,
        "uncollected_hours":   0.0,
    }


def tenure_allocation(
    intensity_h_per_ha_year: float,
    tenure_fractions: dict[str, float],
) -> dict:
    """
    Allocate a per-hectare obligation across the ERS land classes by tenure.

    Governing equation, per class c:

        obligation_c = area_c × intensity
        federation_c = obligation_c × tenure_fractions[c]

    units: labour-hours per year.

    `tenure_fractions` is the CALLER'S — the share of each ERS class under no
    member collective. Any class omitted is treated as wholly member-held
    (fraction 0.0) and is REPORTED as omitted, because silently defaulting a
    tenure share to zero would understate the federation's obligation without
    saying so.

    Args:
        intensity_h_per_ha_year: The reset intensity to apply (h/ha·yr).
        tenure_fractions:        {ERS land-use class: federation fraction}.
    """
    if intensity_h_per_ha_year < 0.0:
        raise ValueError(
            f"intensity must be >= 0, got {intensity_h_per_ha_year}"
        )
    land_use = land_hectares_by_class()
    unknown = sorted(set(tenure_fractions) - set(land_use))
    if unknown:
        raise KeyError(
            f"unknown land classes {unknown}; ERS classes are {sorted(land_use)}"
        )

    rows = []
    fed_total = 0.0
    mem_total = 0.0
    # No aggregate row to skip: `land_hectares_by_class` returns only the nine
    # classes that partition total land. The `if name == "Total land": continue`
    # this loop carried until 2026-08-17 was a workaround for a duplicate
    # loader, and removing the duplicate removed the workaround.
    for name, hectares in land_use.items():
        frac = tenure_fractions.get(name, 0.0)
        obligation = hectares * intensity_h_per_ha_year
        split = allocate_by_tenure(obligation, frac)
        rows.append({
            "land_use":            name,
            "hectares":            hectares,
            "federation_fraction": frac,
            "declared":            name in tenure_fractions,
            "obligation_hours":    obligation,
            "federation_hours":    split["federation_hours"],
            "member_hours":        split["member_hours"],
        })
        fed_total += split["federation_hours"]
        mem_total += split["member_hours"]

    omitted = [r["land_use"] for r in rows if not r["declared"]]
    total = fed_total + mem_total
    return {
        "intensity_h_per_ha_year": intensity_h_per_ha_year,
        "by_class":                rows,
        "federation_hours":        fed_total,
        "member_hours":            mem_total,
        "total_hours":             total,
        "federation_share":        fed_total / total if total > 0.0 else 0.0,
        "classes_without_declared_tenure": omitted,
        "uncollected_hours":       0.0,
        "note": (
            f"{len(omitted)} of {len(rows)} ERS classes carry no declared tenure "
            f"fraction and were treated as wholly member-held. That is the "
            f"conservative direction for the FEDERATION's balance and the "
            f"unsafe one for provisioning it, so the list is returned rather "
            f"than folded away. ERS is a USE survey and carries no tenure split; "
            f"see this module's resolves_by for the instrument that does."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 4e — the health response, relocated and picked up
# ---------------------------------------------------------------------------

def health_response_relocation(
    ecosystem_health: float,
    epsilon: float = 0.40,
    **eco_kwargs: float,
) -> dict:
    """
    What relocating the health response moves, and where it lands.

    Governing identity (asserted, not assumed):

        domain_total("domain")  ==  domain_total("guf")  +  relocated

    so nothing is created or destroyed by the relocation — the obligation is
    the same and only its ADDRESS changes.

    THE 4e ARGUMENT. `ecological_eoh` reads `rate / ecosystem_health`, so
    falling health raises the STANDING obligation. Under the 2026-08-17
    partition that is the wrong side: degraded condition is disturbance,
    disturbance is a reset cost, and reset costs are attributable to whoever
    holds the land. The relocation books the health-driven part as GUF's.

    What survives in the domain is `standing` — what land in reference
    condition asks whatever anyone does to it — plus the two stocks. At
    health = 1.0 the relocated amount is EXACTLY ZERO, which is the partition's
    own claim arriving as algebra rather than assertion.

    Returns the split plus `relocated_share`, the fraction of the domain that
    moves. That share rises with degradation, which is the property to check:
    if it did not, the health response would not be a disturbance measure.
    """
    from hours_eoh.core.eoh_generation import ecological_eoh_breakdown

    kept = ecological_eoh_breakdown(
        ecosystem_health, epsilon, health_response="guf", **eco_kwargs
    )
    whole = ecological_eoh_breakdown(
        ecosystem_health, epsilon, health_response="domain", **eco_kwargs
    )
    relocated = kept["relocatable_to_guf"]
    return {
        "ecosystem_health":     ecosystem_health,
        "epsilon":              epsilon,
        "domain_total_before":  whole["total"],
        "domain_total_after":   kept["total"],
        "relocated_to_guf":     relocated,
        "relocated_share":      relocated / whole["total"] if whole["total"] > 0 else 0.0,
        "standing":             kept["standing"],
        "degradation_response": kept["degradation_response"],
        "spike":                kept["spike"],
        "conserved":            abs(
            kept["total"] + relocated - whole["total"]
        ) < 1e-9 * max(1.0, whole["total"]),
    }
