"""
The US capital inventory, mapped onto the machine profiles — BEA Fixed Assets.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. `research/thermal_capital.epsilon_current_from_inventory()` can
derive ε from a capital inventory, and the only inventory ever run through it was
an estimate: `K = CFC/δ` on a BEA FLOW table, giving $64–107T and
**ε = 0.777–1.000, saturated**. That is not a credible reading of an economy
where 158M people work, and `record/thermal.md` concluded from it that the
profile scale is "miscalibrated by ~3×".

**THE STOCK TABLES SAY THE ESTIMATE WAS FINE AND THE CONCLUSION WAS WRONG.**
BEA Table 1.1 puts 2024 fixed assets at $91.5T, inside the estimated range. What
the detailed tables add is not a better input but a DECOMPOSITION, and it finds
the 3× in three places, none of them the profiles:

    doctrine     1.79x   current-cost vs historical-cost, ONE unchanging stock
    convention   1.45x   wages/compensation x 2,080/derived hours (USD per TEH)
    scope        ~2.5x   productive capital vs every fixed asset there is

Any two of those compound past 3×. All three are judgements nobody had declared.

**AND THE DOCTRINE FIGURE IS THE FRAMEWORK'S OWN THESIS, MEASURED ON ITSELF.**
The value-anchor argument is that a census needs no convention while a valuation
transmits doctrine undamped. BEA publishes two valuations of the identical
physical inventory — current-cost and historical-cost — and they differ by
**1.79×** in aggregate and by 1.09× to 2.12× by asset class. Meanwhile the
model's own side is a census: `CAPITAL_MACHINE_PROFILES` counts machines by tier
at stated TEH/capita. So a retrodiction compares a census against a valuation,
and the spread it produces is exactly what the framework predicts a valuation
route does. That is evidence FOR §2, not a defect in this module.

STRUCTURE, following `reference/servicing.py` and `reference/verification.py`:
  MEASURED   net stock by asset type — BEA Fixed Assets Tables 1.1, 2.1 and 7.1,
             2024 current-cost, yearend, $B. Both doctrines at class level.
  MEASURED   average age at yearend — Tables 2.9 and 7.7. This REPLACES the
             `age: 10.0` placeholder every previous run of this comparison used.
  ASSUMED    WHICH BEA LINE SERVES WHICH PROFILE. The one judgement, isolated in
             `PROFILE_MAP`, every line carrying the basis it was assigned on.
  ASSUMED    WHAT COUNTS AS CAPITAL AT ALL. A SECOND judgement, never merged with
             the first, isolated in `SCOPES` and worth ~2.5× on its own.

NO CURRENCY CONVERSION HAPPENS HERE, and that is deliberate — see
`scenarios/capital_retrodiction`. A currency-per-TEH rate is specific to a
currency, a year, a wage series and an hours convention; it is an INTAKE field
with no default, the way `deferred_ecological` is. Shipping one would bury the
valuation doctrine this module exists to expose.

Layer: reference/ — pure data, imports nothing from the package.
"""

from __future__ import annotations

from typing import Mapping

__all__ = [
    "BEA_YEAR", "BEA_UNITS", "BEA_POPULATION",
    "PROFILE_MAP", "EXCLUDED_LINES", "SCOPES",
    "DOCTRINE_RATIOS", "MEASURED_AGES", "UNALLOCATED", "UNALLOCATED_USD_B",
    "capital_by_profile", "scope_total", "what_this_cannot_settle",
]

#: BEA Fixed Assets, yearend 2024, current-cost net stock.
BEA_YEAR: int = 2024
BEA_UNITS: str = "billions of current US dollars, yearend net stock"
#: The population the inventory is counted over. Extensive figures mean nothing
#: away from it — the frame seam this repo has found in seven subsystems.
BEA_POPULATION: float = 335_000_000.0


#: BEA line → machine profile, with the basis for each assignment.
#:
#: The membership test mirrors `servicing.py`'s: **would this asset exist if the
#: obligation it serves did not?** A sewer main would not. An office tower is
#: `building`, not `generic_infra`, because shelter is a personal component.
#:
#: `scope` says which of `SCOPES` first admits the line.
PROFILE_MAP: tuple[dict, ...] = (
    # ---- private nonresidential: equipment -------------------------------
    {"line": "Electrical transmission equipment", "usd_b": 851.9, "profile": "power_grid",
     "scope": "productive", "basis": "Transmission and distribution plant is the grid."},
    {"line": "Medical equipment and instruments", "usd_b": 657.9, "profile": "medical_systems",
     "scope": "productive", "basis": "Named for the obligation it serves."},
    {"line": "Nonmedical instruments", "usd_b": 285.2, "profile": "environmental_monitoring",
     "scope": "productive", "basis": "Measurement instruments; the closest profile to sensing."},
    {"line": "Industrial equipment less transmission", "usd_b": 2187.2, "profile": "industrial_automation",
     "scope": "productive", "basis": "Engines, metalworking, machinery — production plant."},
    {"line": "Construction/mining/service machinery", "usd_b": 770.3, "profile": "industrial_automation",
     "scope": "productive", "basis": "Mobile production plant; the same function off-site."},
    {"line": "Agricultural machinery", "usd_b": 304.2, "profile": "agricultural_automation",
     "scope": "productive", "basis": "Named for the obligation it serves."},
    {"line": "Transportation equipment", "usd_b": 1919.5, "profile": "transportation",
     "scope": "productive", "basis": "Trucks, autos, aircraft, ships, rail."},
    {"line": "Computers and peripheral equipment", "usd_b": 378.3, "profile": "computing_ai",
     "scope": "productive", "basis": "Named for the obligation it serves."},
    {"line": "Communication equipment", "usd_b": 843.7, "profile": "computing_ai",
     "scope": "productive", "basis": "Networks carry computation; no separate profile exists."},
    {"line": "Furniture, photocopy, office, other equipment", "usd_b": 1028.5, "profile": "generic_infra",
     "scope": "productive", "basis": "Fulfils no named obligation; the catch-all is honest here."},
    # ---- private nonresidential: structures -------------------------------
    {"line": "Power structures", "usd_b": 2951.7, "profile": "power_grid",
     "scope": "productive", "basis": "Generation and distribution plant."},
    {"line": "Communication structures", "usd_b": 951.2, "profile": "computing_ai",
     "scope": "productive", "basis": "Towers and exchanges; same function as the equipment in them."},
    {"line": "Health care structures", "usd_b": 1739.1, "profile": "medical_systems",
     "scope": "productive", "basis": "Hospitals and medical buildings serve the health component."},
    {"line": "Manufacturing structures", "usd_b": 2904.6, "profile": "industrial_automation",
     "scope": "productive", "basis": "The plant the industrial equipment sits in."},
    {"line": "Farm structures", "usd_b": 545.9, "profile": "agricultural_automation",
     "scope": "productive", "basis": "Serves the nutrition component."},
    {"line": "Transportation structures", "usd_b": 658.2, "profile": "transportation",
     "scope": "productive", "basis": "Air and land terminals — the fixed plant transport equipment runs between."},
    {"line": "Commercial and other structures", "usd_b": 10024.3, "profile": "building",
     "scope": "productive", "basis": "Offices, retail, warehouses, education, lodging — occupied space."},
    {"line": "Mining exploration structures", "usd_b": 1419.4, "profile": "generic_infra",
     "scope": "productive", "basis": "Extraction; serves no named component directly."},
    # ---- private nonresidential: IPP --------------------------------------
    {"line": "Software", "usd_b": 1219.6, "profile": "software",
     "scope": "productive", "basis": "Named for the obligation it serves."},
    {"line": "Semiconductor and electronics R&D", "usd_b": 330.7, "profile": "computing_ai",
     "scope": "productive", "basis": "R&D embodied in the computing stock."},
    {"line": "Pharmaceutical and medicine R&D", "usd_b": 1000.9, "profile": "medical_systems",
     "scope": "productive", "basis": "R&D embodied in the medical stock."},
    {"line": "Other research and development", "usd_b": 2160.4, "profile": "generic_infra",
     "scope": "productive", "basis": "Unattributable across components."},
    # ---- government nondefence: structures --------------------------------
    {"line": "Sewer systems", "usd_b": 1234.5, "profile": "water_treatment",
     "scope": "government", "basis": "The ONLY water/sanitation line in the inventory."},
    {"line": "Water systems", "usd_b": 923.8, "profile": "water_treatment",
     "scope": "government", "basis": "Same. Both are state-and-local; there is no federal line."},
    {"line": "Highways and streets", "usd_b": 5020.6, "profile": "transportation",
     "scope": "government", "basis": "The largest single government asset class."},
    {"line": "Government transportation structures", "usd_b": 1256.4, "profile": "transportation",
     "scope": "government", "basis": "Public transit systems and terminals; the same function as the private line, publicly held."},
    {"line": "Government power structures", "usd_b": 573.6, "profile": "power_grid",
     "scope": "government", "basis": "Municipal and federal generation."},
    {"line": "Government health care structures", "usd_b": 479.1, "profile": "medical_systems",
     "scope": "government", "basis": "Public hospitals and clinics; serves the health component exactly as the private line does."},
    {"line": "Government buildings", "usd_b": 6967.5, "profile": "building",
     "scope": "government", "basis": "Office, educational, public safety, commercial, recreation."},
    {"line": "Conservation and development", "usd_b": 613.5, "profile": "environmental_monitoring",
     "scope": "government", "basis": "The only stewardship-coded line in the inventory."},
    {"line": "Government other structures and industrial", "usd_b": 209.4, "profile": "generic_infra",
     "scope": "government", "basis": "Residual after water and sewer are broken out."},
    # ---- government nondefence: IPP and equipment -------------------------
    {"line": "Government software", "usd_b": 169.1, "profile": "software",
     "scope": "government", "basis": "Named for the obligation it serves."},
    {"line": "Government research and development", "usd_b": 1131.6, "profile": "generic_infra",
     "scope": "government", "basis": "Unattributable across components."},
    {"line": "Government equipment, all types", "usd_b": 515.4, "profile": "computing_ai",
     "scope": "government",
     "basis": "NO BY-TYPE BREAKDOWN IS PUBLISHED outside defence — Tables 7.1 and "
              "7.5 both carry it as one line. Assigned to the largest plausible "
              "profile; `UNALLOCATED` records that this is a placement, not a "
              "measurement, and the sensitivity is bounded rather than assumed."},
    # ---- residential -------------------------------------------------------
    {"line": "Private residential structures and equipment", "usd_b": 34376.6, "profile": "building",
     "scope": "residential",
     "basis": "Housing discharges part of the shelter obligation — `building` "
              "carries personal_fulfillment_rate 0.08 — but whether a dwelling "
              "is MACHINE capital that displaces human agency is the judgement "
              "this scope exists to isolate."},
    {"line": "Government residential", "usd_b": 599.4, "profile": "building",
     "scope": "residential", "basis": "Same reading as private housing, publicly held; kept separate so the tenure split stays visible."},
)


#: Excluded BY NAME with the reason. Never a filter.
EXCLUDED_LINES: tuple[dict, ...] = (
    {"line": "National defense", "usd_b": 2330.2,
     "reason": "Military equipment and facilities discharge NO obligation in any "
               "of the four EOH domains. Including them would credit machines "
               "with fulfilling a civilizational requirement the framework does "
               "not recognise as one. This is a judgement, and it is worth 4.3% "
               "of the government scope."},
    {"line": "Consumer durable goods", "usd_b": 8111.2,
     "reason": "Not fixed assets in the BEA sense and not a collective inventory "
               "— counted in Table 1.1's headline and excluded here. A washing "
               "machine plainly abates household labour, so this is the most "
               "arguable exclusion in the module and is named rather than "
               "quietly dropped."},
)


#: WHAT COUNTS AS CAPITAL — the second judgement, worth ~2.5x on its own and
#: kept strictly separate from which profile a line serves.
SCOPES: dict[str, dict] = {
    "productive": {
        "includes": ("productive",),
        "reading": "Private nonresidential equipment, structures and IPP only. "
                   "The narrowest defensible reading: capital that produces.",
    },
    "government": {
        "includes": ("productive", "government"),
        "reading": "Adds government nondefence. Roads, water, sewer, schools and "
                   "public hospitals plainly discharge obligations, and "
                   "`water_treatment` has NO private counterpart at all — a "
                   "productive-only run silently zeroes a shipped profile.",
    },
    "residential": {
        "includes": ("productive", "government", "residential"),
        "reading": "Adds housing. The widest reading, and the one nearest to what "
                   "the original saturated retrodiction ran.",
    },
}


#: THE DOCTRINE MEASUREMENT. BEA publishes two valuations of ONE unchanging
#: physical inventory; these are their ratios, 2024. This is the number §2's
#: census-versus-valuation argument predicts and had never measured.
DOCTRINE_RATIOS: dict[str, float] = {
    "private_fixed_assets": 70276.5 / 39372.0,
    "equipment":            9381.8 / 8300.0,
    "structures":           55470.9 / 26110.0,
    "intellectual_property": 5423.8 / 4960.0,
}

#: Average age at yearend, years — Tables 2.9 (private) and 7.7 (government).
#: MEASURED, and it replaces the `age: 10.0` placeholder every earlier run used.
MEASURED_AGES: dict[str, float] = {
    "private_all":        24.1,
    "private_equipment":   7.1,
    "private_structures": 28.6,
    "private_ipp":         4.2,
    "government_all":     25.7,
    "government_equipment": 8.7,
    "government_structures": 28.8,
    "government_ipp":      6.5,
}

#: The one line placed rather than measured, with what it is worth.
UNALLOCATED_USD_B: float = 515.4
UNALLOCATED: dict[str, object] = {
    "line": "Government equipment, all types",
    "usd_b": UNALLOCATED_USD_B,
    "share_of_government_scope": 0.0096,
    "epsilon_spread_across_every_profile": 0.009,
    "why_it_does_not_need_closing": (
        "Reassigning the whole $515.4B to any single profile moves derived ε by "
        "at most 0.009 — two orders of magnitude below the doctrine spread "
        "(1.79x) and the conversion spread (1.45x). The gap is BOUNDED, and "
        "bounding it is the result; acquiring the breakdown would not change a "
        "conclusion."
    ),
    "what_would_close_it": (
        "A FUNCTION-coded source rather than an asset-type one — Census of "
        "Governments capital outlay by function (education, highways, sewerage) "
        "— because the profiles are functional categories and the field that "
        "names the function measures the quantity, while the asset type names "
        "the department. BEA Fixed Assets does not publish it: Tables 7.1 and "
        "7.5 both carry government equipment as a single line outside defence."
    ),
}


def capital_by_profile(
    scope: str = "government",
    doctrine: str = "current_cost",
) -> dict[str, float]:
    """
    Capital by machine profile, in billions of the inventory's own currency.

    units: $B (BEA current-dollar net stock). NOT TEH — no conversion happens in
    this layer, because the rate is an intake field with no default.

    Args:
        scope: one of `SCOPES`.
        doctrine: "current_cost" as published, or "historical_cost", which
            applies the MEASURED class ratios in `DOCTRINE_RATIOS`. The second is
            a real published valuation of the same physical stock, not a
            sensitivity band.

    Raises:
        ValueError: on an unknown scope or doctrine.
    """
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {sorted(SCOPES)}, got {scope!r}")
    if doctrine not in ("current_cost", "historical_cost"):
        raise ValueError(
            f"doctrine must be 'current_cost' or 'historical_cost', got {doctrine!r}"
        )

    admitted = SCOPES[scope]["includes"]
    out: dict[str, float] = {}
    for row in PROFILE_MAP:
        if row["scope"] not in admitted:
            continue
        usd = float(row["usd_b"])
        if doctrine == "historical_cost":
            usd /= DOCTRINE_RATIOS["private_fixed_assets"]
        out[row["profile"]] = out.get(row["profile"], 0.0) + usd
    return out


def scope_total(scope: str = "government", doctrine: str = "current_cost") -> float:
    """Total admitted capital in $B. units: billions of current US dollars."""
    return sum(capital_by_profile(scope, doctrine).values())


def what_this_cannot_settle() -> tuple[str, ...]:
    """The checker states its own gaps, or it reads as stronger than it is."""
    return (
        "Which scope is right. Whether a dwelling or a road is MACHINE capital "
        "that displaces human agency is a theory question, not a data one, and "
        "it is worth ~2.5x on the answer.",
        "Which valuation doctrine is right. BEA publishes two and they differ by "
        "1.79x on one unchanging stock. The framework's own position is that a "
        "census needs no such choice — which is why this module reports the "
        "spread rather than picking a side.",
        "The currency-per-TEH rate, which is not here at all. It is specific to "
        "a currency, a year, a wage series and an hours convention, and it "
        "belongs to the institution supplying it.",
        "Whether the machine profiles' tier scale is right. This module gives "
        "the inventory that would test it and does not itself test it — a "
        "comparison whose two sides are a census and a valuation cannot settle "
        "a calibration question on its own.",
        str(UNALLOCATED["why_it_does_not_need_closing"]),
    )
