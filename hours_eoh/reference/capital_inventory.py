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
  MEASURED   line by line in `AGE_ROWS` (2026-10-04), with BEA's own SERVICE
             LIVES beside the ages — what the stock's age ratio is read from.
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
    "AGE_ROWS",
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
    {"line": "Electrical equipment, n.e.c.", "usd_b": 55.2, "profile": "generic_infra",
     "scope": "productive",
     "basis": "Miscellaneous electrical equipment; no named obligation, so the same "
              "catch-all. ADDED 2026-10-04: it had been in no line and in no "
              "exclusion — dropped without a name."},
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
    {"line": "Government buildings", "usd_b": 6488.5, "profile": "building",
     "scope": "government",
     "basis": "Office, educational, public safety, commercial, recreation. CORRECTED "
              "2026-10-04 from 6,967.5, which also held government health care "
              "(479.1) — counted again as its own line."},
    {"line": "Conservation and development", "usd_b": 613.5, "profile": "environmental_monitoring",
     "scope": "government", "basis": "The only stewardship-coded line in the inventory."},
    {"line": "Government other structures", "usd_b": 100.7, "profile": "generic_infra",
     "scope": "government",
     "basis": "Residual after water and sewer are broken out. CORRECTED 2026-10-04 "
              "from 209.4 ('… and industrial'): BEA's government industrial "
              "structures (108.7) are all national defence (Table 7.1 lines 5 = "
              "33), which `EXCLUDED_LINES` already drops."},
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
    {"line": "Government residential", "usd_b": 434.1, "profile": "building",
     "scope": "residential",
     "basis": "Same reading as private housing, publicly held; kept separate so the "
              "tenure split stays visible. State and local only — CORRECTED "
              "2026-10-04 from 599.4, which held federal DEFENCE housing (165.3) "
              "that the National defense exclusion also drops."},
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
    {"line": "Entertainment, literary, and artistic originals", "usd_b": 712.2,
     "reason": "Films, television, books and music: an asset in the accounts, but "
               "no machine that does obligation work. NAMED 2026-10-04 — it had "
               "been dropped with no line and no exclusion."},
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


#: THE STOCK'S AGE AGAINST ITS LIFE, LINE BY LINE (2026-10-04). Each `PROFILE_MAP`
#: line rebuilt from BEA's finest published rows, so the age ratio needs no
#: profile judgement — `CAPITAL_MACHINE_PROFILES`' design lives are placeholders
#: and the profile map assigns a line by the OBLIGATION it serves, which says
#: nothing about how long it lasts (communication structures under `computing_ai`
#: would read 3.9 lives old against its 6 years).
#:   usd_b, age          MEASURED — current-cost net stock (Tables 2.1 / 7.1, $B,
#:                       yearend 2024) and current-cost average age (2.9 / 7.7, yr)
#:   usd_b_hist, age_hist  MEASURED — historical cost (2.3 / 2.10); private only,
#:                       BEA publishes no historical-cost government tables
#:   life                BEA's service life, (low, high) years, from "BEA Rates of
#:                       Depreciation, Service Lives, Declining-Balance Rates, and
#:                       Hulten-Wykoff Categories" (apps.bea.gov/national/pdf/
#:                       BEA_depreciation_rates.pdf, FETCHED 2026-10-04 — not a
#:                       handoff). A span where BEA varies the life by industry or
#:                       the line holds sub-types; None where BEA publishes a
#:                       depreciation rate and NO life (R&D, computers, autos) or
#:                       no age, each saying why. Excluded by name, never zeroed.
#:   life_basis          WHICH methodology row the life was read from — the ONE
#:                       judgement here, made per row and stated
#: Every line's rows sum to its `PROFILE_MAP` figure — rebuilding them found
#: four errors in the inventory, corrected 2026-10-04 and marked on their lines.
#: BEA's service life is the mean of a retirement distribution, so a row can
#: sit past it.
AGE_ROWS: tuple[dict, ...] = (
    # ---- Electrical transmission equipment
    {"line": "Electrical transmission equipment", "bea": "2.1/2.9 line 17", "type": "Electrical transmission, distribution, and industrial apparatus",
     "usd_b": 851.912, "age": 12.2, "usd_b_hist": 661.187, "age_hist": 9.8,
     "life": (33, 33), "life_basis": "Electrical transmission, distribution, and industrial apparatus"},
    # ---- Medical equipment and instruments
    {"line": "Medical equipment and instruments", "bea": "2.1/2.9 line 7", "type": "Medical equipment and instruments",
     "usd_b": 657.85, "age": 4.9, "usd_b_hist": 617.72, "age_hist": 4.9,
     "life": (9, 12), "life_basis": "Medical instruments 12; electromedical equipment 9"},
    # ---- Nonmedical instruments
    {"line": "Nonmedical instruments", "bea": "2.1/2.9 line 8", "type": "Nonmedical instruments",
     "usd_b": 285.224, "age": 6.2, "usd_b_hist": 243.368, "age_hist": 5.7,
     "life": (12, 12), "life_basis": "Nonmedical instruments"},
    # ---- Industrial equipment less transmission
    {"line": "Industrial equipment less transmission", "bea": "2.1/2.9 line 12", "type": "Fabricated metal products",
     "usd_b": 248.94, "age": 9.4, "usd_b_hist": 187.068, "age_hist": 7.6,
     "life": (18, 18), "life_basis": "Other fabricated metal products"},
    {"line": "Industrial equipment less transmission", "bea": "2.1/2.9 line 13", "type": "Engines and turbines",
     "usd_b": 156.288, "age": 13.7, "usd_b_hist": 123.49, "age_hist": 10.9,
     "life": (8, 32), "life_basis": "Steam engines and turbines 32; internal combustion engines 8"},
    {"line": "Industrial equipment less transmission", "bea": "2.1/2.9 line 14", "type": "Metalworking machinery",
     "usd_b": 345.636, "age": 9.0, "usd_b_hist": 291.7, "age_hist": 7.8,
     "life": (12, 27), "life_basis": "Metalworking machinery, by industry"},
    {"line": "Industrial equipment less transmission", "bea": "2.1/2.9 line 15", "type": "Special industry machinery, n.e.c.",
     "usd_b": 434.247, "age": 8.7, "usd_b_hist": 377.479, "age_hist": 7.5,
     "life": (12, 27), "life_basis": "Special industry machinery, nec, by industry"},
    {"line": "Industrial equipment less transmission", "bea": "2.1/2.9 line 16", "type": "General industrial, including materials handling, equipment",
     "usd_b": 1002.066, "age": 8.0, "usd_b_hist": 817.615, "age_hist": 6.7,
     "life": (12, 27), "life_basis": "General industrial incl. materials handling, by industry"},
    # ---- Construction/mining/service machinery
    {"line": "Construction/mining/service machinery", "bea": "2.1/2.9 line 29", "type": "Construction machinery",
     "usd_b": 321.407, "age": 5.6, "usd_b_hist": 274.792, "age_hist": 4.9,
     "life": (8, 10), "life_basis": "Construction tractors 8; construction machinery 10"},
    {"line": "Construction/mining/service machinery", "bea": "2.1/2.9 line 30", "type": "Mining and oilfield machinery",
     "usd_b": 190.491, "age": 5.6, "usd_b_hist": 162.968, "age_hist": 5.1,
     "life": (11, 11), "life_basis": "Mining and oil field machinery"},
    {"line": "Construction/mining/service machinery", "bea": "2.1/2.9 line 31", "type": "Service industry machinery",
     "usd_b": 258.437, "age": 5.9, "usd_b_hist": 206.633, "age_hist": 5.1,
     "life": (10, 11), "life_basis": "Service industry machinery, by industry"},
    # ---- Agricultural machinery
    {"line": "Agricultural machinery", "bea": "2.1/2.9 line 28", "type": "Agricultural machinery",
     "usd_b": 304.2, "age": 6.5, "usd_b_hist": 253.907, "age_hist": 5.6,
     "life": (9, 14), "life_basis": "Farm tractors 9; agricultural machinery except tractors 14"},
    # ---- Transportation equipment
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 20", "type": "Light trucks (including utility vehicles)",
     "usd_b": 629.714, "age": 1.6, "usd_b_hist": 573.282, "age_hist": 1.4,
     "life": (17, 17), "life_basis": "Light trucks (1992 and later)"},
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 21", "type": "Other trucks, buses, and truck trailers",
     "usd_b": 305.499, "age": 4.5, "usd_b_hist": 290.671, "age_hist": 4.0,
     "life": (9, 14), "life_basis": "Other trucks, buses and trailers, by industry"},
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 22", "type": "Autos",
     "usd_b": 118.172, "age": 7.0, "usd_b_hist": 114.33, "age_hist": 6.2,
     "life": None, "life_basis": "Autos: BEA derives depreciation from used-auto prices with no service life"},
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 23", "type": "Aircraft",
     "usd_b": 560.404, "age": 10.7, "usd_b_hist": 415.373, "age_hist": 8.3,
     "life": (15, 25), "life_basis": "Aircraft (1960 and later), by industry"},
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 24", "type": "Ships and boats",
     "usd_b": 115.628, "age": 14.9, "usd_b_hist": 85.353, "age_hist": 10.9,
     "life": (27, 27), "life_basis": "Ships and boats"},
    {"line": "Transportation equipment", "bea": "2.1/2.9 line 25", "type": "Railroad equipment",
     "usd_b": 190.045, "age": 14.0, "usd_b_hist": 157.81, "age_hist": 10.3,
     "life": (28, 28), "life_basis": "Railroad equipment"},
    # ---- Computers and peripheral equipment
    {"line": "Computers and peripheral equipment", "bea": "2.1/2.9 line 5", "type": "Computers and peripheral equipment",
     "usd_b": 378.344, "age": 2.0, "usd_b_hist": 373.732, "age_hist": 2.0,
     "life": None, "life_basis": "Computers: empirical used-price profiles, no service life"},
    # ---- Communication equipment
    {"line": "Communication equipment", "bea": "2.1/2.9 line 6", "type": "Communication equipment",
     "usd_b": 843.656, "age": 4.9, "usd_b_hist": 1045.509, "age_hist": 7.0,
     "life": (11, 15), "life_basis": "Communications equipment, by industry"},
    # ---- Furniture, photocopy, office, other equipment
    {"line": "Furniture, photocopy, office, other equipment", "bea": "2.1/2.9 line 27", "type": "Furniture and fixtures",
     "usd_b": 438.049, "age": 7.7, "usd_b_hist": 359.889, "age_hist": 6.6,
     "life": (12, 14), "life_basis": "Household furniture 12; other furniture 14"},
    {"line": "Furniture, photocopy, office, other equipment", "bea": "2.1/2.9 line 9", "type": "Photocopy and related equipment",
     "usd_b": 43.0, "age": 4.6, "usd_b_hist": 42.867, "age_hist": 4.7,
     "life": (9, 9), "life_basis": "Photocopy and related equipment"},
    {"line": "Furniture, photocopy, office, other equipment", "bea": "2.1/2.9 line 10", "type": "Office and accounting equipment",
     "usd_b": 14.071, "age": 2.8, "usd_b_hist": 13.193, "age_hist": 2.7,
     "life": (7, 7), "life_basis": "Office and accounting equipment (1978 and later)"},
    {"line": "Furniture, photocopy, office, other equipment", "bea": "2.1/2.9 line 33", "type": "Other nonresidential equipment",
     "usd_b": 533.36, "age": 5.9, "usd_b_hist": 458.885, "age_hist": 5.3,
     "life": (11, 11), "life_basis": "Other nonresidential equipment"},
    # ---- Electrical equipment, n.e.c.
    {"line": "Electrical equipment, n.e.c.", "bea": "2.1/2.9 line 32", "type": "Electrical equipment, n.e.c.",
     "usd_b": 55.246, "age": 4.4, "usd_b_hist": 48.859, "age_hist": 4.0,
     "life": (9, 9), "life_basis": "Miscellaneous electrical equipment"},
    # ---- Power structures
    {"line": "Power structures", "bea": "2.1/2.9 line 51", "type": "Electric",
     "usd_b": 2085.599, "age": 21.8, "usd_b_hist": 1324.319, "age_hist": 11.8,
     "life": (45, 45), "life_basis": "Electric light and power (1946 and later)"},
    {"line": "Power structures", "bea": "2.1/2.9 line 52", "type": "Other power",
     "usd_b": 866.058, "age": 28.1, "usd_b_hist": 404.583, "age_hist": 13.5,
     "life": (30, 40), "life_basis": "Gas and petroleum pipelines 40; wind and solar 30"},
    # ---- Communication structures
    {"line": "Communication structures", "bea": "2.1/2.9 line 53", "type": "Communication",
     "usd_b": 951.184, "age": 23.2, "usd_b_hist": 509.309, "age_hist": 16.0,
     "life": (40, 40), "life_basis": "Communication"},
    # ---- Health care structures
    {"line": "Health care structures", "bea": "2.1/2.9 line 41", "type": "Hospitals",
     "usd_b": 1085.613, "age": 23.9, "usd_b_hist": 558.321, "age_hist": 15.7,
     "life": (48, 48), "life_basis": "Hospitals"},
    {"line": "Health care structures", "bea": "2.1/2.9 line 42", "type": "Special care",
     "usd_b": 236.9, "age": 25.8, "usd_b_hist": 114.241, "age_hist": 17.0,
     "life": (48, 48), "life_basis": "Special care"},
    {"line": "Health care structures", "bea": "2.1/2.9 line 43", "type": "Medical buildings",
     "usd_b": 416.575, "age": 18.7, "usd_b_hist": 251.47, "age_hist": 11.7,
     "life": (36, 36), "life_basis": "Medical buildings"},
    # ---- Manufacturing structures
    {"line": "Manufacturing structures", "bea": "2.1/2.9 line 48", "type": "Manufacturing",
     "usd_b": 2904.602, "age": 21.3, "usd_b_hist": 1540.667, "age_hist": 11.0,
     "life": (31, 31), "life_basis": "Manufacturing"},
    # ---- Farm structures
    {"line": "Farm structures", "bea": "2.1/2.9 line 65", "type": "Farm",
     "usd_b": 545.861, "age": 37.2, "usd_b_hist": 198.773, "age_hist": 16.9,
     "life": (38, 38), "life_basis": "Farm"},
    # ---- Transportation structures
    {"line": "Transportation structures", "bea": "2.1/2.9 line 63", "type": "Air",
     "usd_b": 96.746, "age": 19.3, "usd_b_hist": 54.524, "age_hist": 10.6,
     "life": (38, 38), "life_basis": "Air transportation"},
    {"line": "Transportation structures", "bea": "2.1/2.9 line 64", "type": "Land",
     "usd_b": 561.443, "age": 50.1, "usd_b_hist": 231.435, "age_hist": 16.1,
     "life": (38, 54), "life_basis": "Other land transportation and railroad track 38; other railroad structures 54"},
    # ---- Commercial and other structures
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 38", "type": "Office",
     "usd_b": 3278.523, "age": 24.0, "usd_b_hist": 1447.001, "age_hist": 14.2,
     "life": (36, 36), "life_basis": "Office buildings"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 44", "type": "Multimerchandise shopping",
     "usd_b": 1083.229, "age": 26.6, "usd_b_hist": 435.194, "age_hist": 17.2,
     "life": (34, 34), "life_basis": "Multimerchandise shopping"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 45", "type": "Food and beverage establishments",
     "usd_b": 532.67, "age": 27.6, "usd_b_hist": 211.507, "age_hist": 16.7,
     "life": (34, 34), "life_basis": "Food and beverage establishments"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 46", "type": "Warehouses",
     "usd_b": 1078.431, "age": 18.4, "usd_b_hist": 596.92, "age_hist": 9.9,
     "life": (40, 40), "life_basis": "Commercial warehouses"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 47", "type": "Other commercial",
     "usd_b": 849.487, "age": 25.6, "usd_b_hist": 346.443, "age_hist": 16.3,
     "life": (16, 34), "life_basis": "Other commercial buildings 34; mobile offices 16"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 58", "type": "Religious",
     "usd_b": 459.681, "age": 36.9, "usd_b_hist": 152.376, "age_hist": 21.8,
     "life": (48, 48), "life_basis": "Religious buildings"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 59", "type": "Educational and vocational",
     "usd_b": 889.391, "age": 24.2, "usd_b_hist": 412.908, "age_hist": 14.0,
     "life": (48, 48), "life_basis": "Educational buildings"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 60", "type": "Lodging",
     "usd_b": 1001.765, "age": 20.1, "usd_b_hist": 529.736, "age_hist": 13.2,
     "life": (32, 32), "life_basis": "Lodging"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 61", "type": "Amusement and recreation",
     "usd_b": 607.825, "age": 23.5, "usd_b_hist": 301.074, "age_hist": 13.7,
     "life": (30, 30), "life_basis": "Amusement and recreational buildings"},
    {"line": "Commercial and other structures", "bea": "2.1/2.9 line 66", "type": "Other",
     "usd_b": 243.264, "age": 33.4, "usd_b_hist": 88.479, "age_hist": 21.3,
     "life": (38, 40), "life_basis": "Water supply, sewage, highway and conservation 40; public safety 38"},
    # ---- Mining exploration structures
    {"line": "Mining exploration structures", "bea": "2.1/2.9 line 55", "type": "Petroleum and natural gas",
     "usd_b": 1203.724, "age": 13.4, "usd_b_hist": 1005.622, "age_hist": 9.2,
     "life": (12, 12), "life_basis": "Petroleum and natural gas (1973 and later)"},
    {"line": "Mining exploration structures", "bea": "2.1/2.9 line 56", "type": "Mining",
     "usd_b": 215.667, "age": 13.7, "usd_b_hist": 134.523, "age_hist": 9.4,
     "life": (20, 20), "life_basis": "Mining exploration, other"},
    # ---- Software
    {"line": "Software", "bea": "2.1/2.9 line 79", "type": "Prepackaged",
     "usd_b": 419.579, "age": 1.2, "usd_b_hist": 408.839, "age_hist": 1.2,
     "life": (3, 3), "life_basis": "Prepackaged software"},
    {"line": "Software", "bea": "2.1/2.9 line 80", "type": "Custom",
     "usd_b": 582.678, "age": 2.1, "usd_b_hist": 586.759, "age_hist": 2.2,
     "life": (5, 5), "life_basis": "Custom software"},
    {"line": "Software", "bea": "2.1/2.9 line 81", "type": "Own account",
     "usd_b": 217.301, "age": 2.1, "usd_b_hist": 219.024, "age_hist": 2.2,
     "life": (5, 5), "life_basis": "Own-account software"},
    # ---- Semiconductor and electronics R&D
    {"line": "Semiconductor and electronics R&D", "bea": "2.1/2.9 line 87", "type": "Semiconductor and other electronic component manufacturing",
     "usd_b": 183.611, "age": 3.1, "usd_b_hist": 170.154, "age_hist": 2.9,
     "life": None, "life_basis": "R&D: BEA estimates a depreciation rate directly, no service life"},
    {"line": "Semiconductor and electronics R&D", "bea": "2.1/2.9 line 88", "type": "Other computer and electronic product manufacturing",
     "usd_b": 147.065, "age": 2.7, "usd_b_hist": 137.309, "age_hist": 2.6,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    # ---- Pharmaceutical and medicine R&D
    {"line": "Pharmaceutical and medicine R&D", "bea": "2.1/2.9 line 85", "type": "Pharmaceutical and medicine manufacturing",
     "usd_b": 1000.907, "age": 6.2, "usd_b_hist": 867.539, "age_hist": 5.5,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    # ---- Other research and development
    {"line": "Other research and development", "bea": "2.1/2.9 line 86", "type": "Chemical manufacturing, excluding pharmaceutical and medicine",
     "usd_b": 73.154, "age": 6.0, "usd_b_hist": 63.607, "age_hist": 5.3,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Other research and development", "bea": "2.1/2.9 line 89", "type": "Motor vehicles, bodies and trailers, and parts manufacturing",
     "usd_b": 93.689, "age": 2.5, "usd_b_hist": 87.954, "age_hist": 2.4,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Other research and development", "bea": "2.1/2.9 line 90", "type": "Aerospace products and parts manufacturing",
     "usd_b": 68.992, "age": 3.8, "usd_b_hist": 62.872, "age_hist": 3.4,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Other research and development", "bea": "2.1/2.9 line 91", "type": "Other manufacturing",
     "usd_b": 420.967, "age": 5.0, "usd_b_hist": 373.82, "age_hist": 4.5,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Other research and development", "bea": "2.1/2.9 line 92", "type": "Nonmanufacturing",
     "usd_b": 1303.829, "age": 3.6, "usd_b_hist": 1195.218, "age_hist": 3.3,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Other research and development", "bea": "2.1/2.9 line 95", "type": "Nonprofit institutions serving households (NPISHs)",
     "usd_b": 199.824, "age": 4.6, "usd_b_hist": 181.26, "age_hist": 4.2,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    # ---- Private residential structures and equipment
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 70", "type": "1 to 4 unit",
     "usd_b": 21879.036, "age": 36.9, "usd_b_hist": 8265.726, "age_hist": 18.3,
     "life": (80, 80), "life_basis": "1-to-4-unit structures, new"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 71", "type": "5-or more-unit",
     "usd_b": 3412.636, "age": 33.7, "usd_b_hist": 1401.998, "age_hist": 15.0,
     "life": (65, 65), "life_basis": "5-or-more-unit structures, new"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 72", "type": "Manufactured homes",
     "usd_b": 388.373, "age": 26.8, "usd_b_hist": 192.371, "age_hist": 15.6,
     "life": (20, 20), "life_basis": "Manufactured homes"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 73", "type": "Brokers' commissions and other ownership transfer costs",
     "usd_b": 169.446, "age": None, "usd_b_hist": 690.061, "age_hist": None,
     "life": None, "life_basis": "Ownership transfer costs: BEA publishes no average age (the stock can be negative)"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 74", "type": "Improvements",
     "usd_b": 8280.338, "age": 19.2, "usd_b_hist": 4638.463, "age_hist": 11.9,
     "life": (20, 40), "life_basis": "Additions and alterations 32-40; major replacements 20-25"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 75", "type": "Other residential",
     "usd_b": 146.81, "age": 26.8, "usd_b_hist": 67.585, "age_hist": 12.6,
     "life": (40, 40), "life_basis": "Other residential structures"},
    {"line": "Private residential structures and equipment", "bea": "2.1/2.9 line 34", "type": "Residential equipment",
     "usd_b": 99.942, "age": 4.6, "usd_b_hist": 105.435, "age_hist": 4.7,
     "life": (11, 11), "life_basis": "Residential equipment"},
    # ---- Sewer systems
    {"line": "Sewer systems", "bea": "7.1/7.7 line 68", "type": "Sewer systems",
     "usd_b": 1234.526, "age": 30.2,
     "life": (60, 60), "life_basis": "Government nonbuildings: sewer systems"},
    # ---- Water systems
    {"line": "Water systems", "bea": "7.1/7.7 line 69", "type": "Water systems",
     "usd_b": 923.826, "age": 28.8,
     "life": (60, 60), "life_basis": "Government nonbuildings: water systems"},
    # ---- Highways and streets
    {"line": "Highways and streets", "bea": "7.1/7.7 line 14", "type": "Highways and streets",
     "usd_b": 5020.642, "age": 29.0,
     "life": (45, 45), "life_basis": "Highways and streets (shortened from 60 in 1999)"},
    # ---- Government transportation structures
    {"line": "Government transportation structures", "bea": "7.1/7.7 line 12", "type": "Transportation",
     "usd_b": 1256.385, "age": 21.3,
     "life": (50, 60), "life_basis": "Government buildings, other 50; nonbuildings, other 60"},
    # ---- Government power structures
    {"line": "Government power structures", "bea": "7.1/7.7 line 13", "type": "Power",
     "usd_b": 573.654, "age": 28.9,
     "life": (45, 60), "life_basis": "Private electric light and power 45; government nonbuildings, other 60"},
    # ---- Government health care structures
    {"line": "Government health care structures", "bea": "7.1/7.7 line 8", "type": "Health care",
     "usd_b": 479.088, "age": 29.6,
     "life": (50, 50), "life_basis": "Government buildings: hospital"},
    # ---- Government buildings
    {"line": "Government buildings", "bea": "7.1/7.7 line 6", "type": "Office",
     "usd_b": 1471.606, "age": 24.2,
     "life": (50, 50), "life_basis": "Government buildings, other"},
    {"line": "Government buildings", "bea": "7.1/7.7 line 7", "type": "Commercial",
     "usd_b": 90.887, "age": 38.9,
     "life": (50, 50), "life_basis": "Government buildings, other"},
    {"line": "Government buildings", "bea": "7.1/7.7 line 9", "type": "Educational",
     "usd_b": 4080.436, "age": 25.5,
     "life": (50, 50), "life_basis": "Government buildings: educational"},
    {"line": "Government buildings", "bea": "7.1/7.7 line 10", "type": "Public safety",
     "usd_b": 408.037, "age": 28.2,
     "life": (50, 50), "life_basis": "Government buildings, other"},
    {"line": "Government buildings", "bea": "7.1/7.7 line 11", "type": "Amusement and recreation",
     "usd_b": 437.535, "age": 25.2,
     "life": (50, 50), "life_basis": "Government buildings, other"},
    # ---- Conservation and development
    {"line": "Conservation and development", "bea": "7.1/7.7 line 16", "type": "Conservation and development",
     "usd_b": 613.499, "age": 37.5,
     "life": (60, 60), "life_basis": "Government nonbuildings: conservation and development"},
    # ---- Government other structures and industrial
    {"line": "Government other structures", "bea": "7.1/7.7 line 51", "type": "Other structures",
     "usd_b": 55.366, "age": 24.7,
     "life": (50, 60), "life_basis": "Government buildings, other 50; nonbuildings, other 60"},
    {"line": "Government other structures", "bea": "7.1/7.7 line 71", "type": "Other structures",
     "usd_b": 45.335, "age": 30.0,
     "life": (50, 60), "life_basis": "Government buildings, other 50; nonbuildings, other 60"},
    # ---- Government software
    {"line": "Government software", "bea": "7.1/7.7 line 53", "type": "Software",
     "usd_b": 100.164, "age": 1.9,
     "life": (3, 5), "life_basis": "Government software: prepackaged 3; custom and own-account 5"},
    {"line": "Government software", "bea": "7.1/7.7 line 73", "type": "Software",
     "usd_b": 68.894, "age": 1.7,
     "life": (3, 5), "life_basis": "Government software: prepackaged 3; custom and own-account 5"},
    # ---- Government research and development
    {"line": "Government research and development", "bea": "7.1/7.7 line 54", "type": "Research and development",
     "usd_b": 982.277, "age": 8.3,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    {"line": "Government research and development", "bea": "7.1/7.7 line 74", "type": "Research and development",
     "usd_b": 149.334, "age": 4.9,
     "life": None, "life_basis": "R&D: depreciation rate only"},
    # ---- Government equipment, all types
    {"line": "Government equipment, all types", "bea": "7.1/7.7 line 39", "type": "Equipment",
     "usd_b": 191.441, "age": 7.4,
     "life": None, "life_basis": "No by-type breakdown outside defence (see UNALLOCATED); lives span 5-33"},
    {"line": "Government equipment, all types", "bea": "7.1/7.7 line 56", "type": "Equipment",
     "usd_b": 323.951, "age": 8.3,
     "life": None, "life_basis": "No by-type breakdown outside defence (see UNALLOCATED); lives span 5-33"},
    # ---- Government residential
    {"line": "Government residential", "bea": "7.1/7.7 line 58", "type": "Residential",
     "usd_b": 434.054, "age": 31.7,
     "life": (65, 80), "life_basis": "Residential capital: 5-or-more-unit 65; 1-to-4-unit 80 (state and local; federal housing is defence, excluded)"},
)



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
