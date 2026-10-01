"""
scenarios/essential_bridge — WHO CAN CARRY THE PERSONAL OBLIGATION, derived.

The bridge from the four EOH domains to the essential workforce domains
(`core/eoh_generation._EOH_TO_ESSENTIAL_WEIGHTS`) is what Condition IV in hours
(`conditions.condition_iv_coverage`) sets certified capacity against. Its
personal column — healthcare 0.80, logistics 0.20 — was written before the
personal obligation was decomposed, and never used the decomposition. This
module derives that column from what the repo now measures, so the verdict
rests on a computation rather than a pick (author, 2026-10-01: "fix the domain
mapping, as that seems to be an oversight on work that was done to update the
framework").

    GOVERNING RELATION

        w(d, personal) = Σ_c  share_c × split_c(d)

    over the four components of `PERSONAL_EOH_COMPONENTS` (shares sum to 1),
    each split onto essential domains by its own measured composition:

    health    → healthcare                                     (the component IS it)
    care      → care              its own essential domain since 2026-10-01
                                  (author). Until then the seven domains had no
                                  care domain and care was set against
                                  healthcare.
    nutrition → agriculture : manufacturing, by the floor's own terms —
                unassisted PRODUCTION (LSMS, `food_conservation`) against
                unassisted PROCESSING (the anchor `NUTRITION_AUTOMATION_FLOOR`
                adopts, `automation_floors.anchored_processing_estimate`).
                FOOD SERVICE IS NOT IN THE OBLIGATION (author, 2026-09-03): it
                has no upper bound, so it is discovery above the floor and has
                no essential domain to carry it.
    shelter   → construction : energy : UNATTRIBUTED, by the measured shelter
                destinations (`component_shares.shelter_decomposition`):
                structure → construction, thermal → energy, upkeep (cleaning,
                laundry) → no certified domain. WATER IS NOT SEPARABLE in the
                measured frame — piped water hides hauling inside upkeep — and
                no measurement prices it at low capital; it is HELD rather than
                weighted (author: no new placeholders), and stays in the
                unattributed share where the frame put it.

    The UNATTRIBUTED share is the part of the obligation no essential domain is
    certified for. It is reported, not forced onto a domain — the old column
    summed to 1 over the seven by construction, which manufactured the claim
    that every hour had a certified home (failure mode 2).

REPORTING / DERIVATION ONLY. `core/` cannot import this layer, so the column is
frozen in `data.ESSENTIAL_BRIDGE_PERSONAL` (tag `derived`) and
`tests/scenarios/test_essential_bridge.py` recomputes it from these functions.
"""

from __future__ import annotations

from hours_eoh.data import ESSENTIAL_DOMAINS, PERSONAL_EOH_COMPONENTS

#: The column's keys: the essential domains and the share no domain carries.
UNATTRIBUTED: str = "unattributed"


def personal_column() -> dict:
    """
    Derive the personal column of the essential-domain bridge.

    Returns:
        {"column": {essential_domain | "unattributed": share}, summing to 1,
         "inputs": the measured quantities each split was read from,
         "declared": the judgements the column still rests on}.

    units: dimensionless shares of the personal obligation.
    ε-behaviour: none — a composition of the obligation, not of its automation.
    """
    from hours_eoh.scenarios.food_conservation import conservation_test
    from hours_eoh.scenarios.automation_floors import anchored_processing_estimate
    from hours_eoh.scenarios.component_shares import shelter_decomposition

    share = {c: float(v["share"]) for c, v in PERSONAL_EOH_COMPONENTS.items()}

    stages = {s["stage"]: s for s in conservation_test()["stages"]}
    lsms = stages["production"]["lsms_hours"]
    if lsms is None or lsms <= 0.0:
        raise ValueError("no measured unassisted production benchmark")
    production = float(lsms)
    anchored = anchored_processing_estimate()
    processing = float(anchored["anchors"][anchored["tightest_anchor"]]["processing_h_yr"])

    shelter = shelter_decomposition()["by_destination"]
    structure, thermal, upkeep = (float(shelter[k]) for k in ("structure", "thermal", "upkeep"))
    in_shelter = structure + thermal + upkeep          # `not_shelter` is not shelter

    col = {d: 0.0 for d in ESSENTIAL_DOMAINS}
    col[UNATTRIBUTED] = 0.0
    col["healthcare"] += share["health"]
    col["care"] += share["care"]
    col["agriculture"] += share["nutrition"] * production / (production + processing)
    col["manufacturing"] += share["nutrition"] * processing / (production + processing)
    col["construction"] += share["shelter"] * structure / in_shelter
    col["energy"] += share["shelter"] * thermal / in_shelter
    col[UNATTRIBUTED] += share["shelter"] * upkeep / in_shelter

    return {
        "column": col,
        "inputs": {
            "component_shares":           share,
            "unassisted_production_h_yr": production,
            "unassisted_processing_h_yr": processing,
            "processing_anchor":          anchored["tightest_anchor"],
            "shelter_destinations_h_yr":  {"structure": structure, "thermal": thermal,
                                           "upkeep": upkeep},
        },
        "declared": (
            "food service is excluded from the obligation (author, 2026-09-03)",
            "water is not separable in the measured shelter frame; held, not weighted",
            "shelter destinations are ATUS, a high-capital frame",
            "component shares are the desk estimate (PERSONAL_EOH_COMPONENTS, confidence 25)",
        ),
    }
