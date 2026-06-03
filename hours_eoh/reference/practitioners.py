"""
Reference practitioner/demand histories for scarcity_score().

Each entry is a list of (practitioner_count, demand_eoh) tuples, most-recent
last, spanning 5 periods. demand_eoh is expressed in practitioner-equivalents:
the number of full-time practitioners needed to meet collective EOH demand for
this occupation. Sized for a 1M-population reference economy (workforce ≈ 600K).

Six shapes are provided to cover the key test and illustration cases:

  community_care_worker   Stable moderate scarcity (~0.33)
  ecological_steward      Rising scarcity (0.40 → 0.72) — trending worse
  civil_engineer          Recovering scarcity (0.65 → 0.28) — supply response visible
  neurosurgeon            Severe stable scarcity (> 0.80)
  general_educator        Oversupply — practitioners exceed demand → scarcity = 0
  restoration_ecologist   Full arc: rises then recovers over 5 periods

Layer rule: no imports from hours_eoh core, land, or scenarios.
"""

# ---------------------------------------------------------------------------
# Practitioner histories
# (practitioner_count, demand_eoh) — most-recent last, 5 periods each
# ---------------------------------------------------------------------------

PRACTITIONER_HISTORIES: dict[str, list[tuple[float, float]]] = {

    # --- Care domain ---

    # Community care worker: moderate stable scarcity.
    # ~8 000 practitioners against ~12 000 needed. Supply is growing slowly
    # but demand tracks an aging cohort — net scarcity is stable around 0.33.
    "community_care_worker": [
        (7_600, 11_400),   # period -4: scarcity ≈ 0.33
        (7_700, 11_550),   # period -3: scarcity ≈ 0.33
        (7_850, 11_750),   # period -2: scarcity ≈ 0.33
        (8_000, 12_000),   # period -1: scarcity ≈ 0.33
        (8_100, 12_150),   # current:  scarcity ≈ 0.33
    ],

    # Neurosurgeon: severe stable scarcity.
    # Training pipeline (10–14 years) cannot respond quickly. ~80 surgeons for
    # a collective with demand equivalent to ~520 full-time surgeons.
    "neurosurgeon": [
        (76, 500),   # period -4: scarcity ≈ 0.85
        (77, 510),   # period -3: scarcity ≈ 0.85
        (78, 510),   # period -2: scarcity ≈ 0.85
        (79, 515),   # period -1: scarcity ≈ 0.85
        (80, 520),   # current:  scarcity ≈ 0.85
    ],

    # --- Ecological domain ---

    # Ecological steward: rising scarcity.
    # Accelerating ecological EOH demand (degraded land, habitat loss) while
    # the training pipeline is slow. Rolling window captures the worsening trend.
    "ecological_steward": [
        (480, 800),    # period -4: scarcity ≈ 0.40
        (450, 850),    # period -3: scarcity ≈ 0.47
        (420, 900),    # period -2: scarcity ≈ 0.53
        (380, 980),    # period -1: scarcity ≈ 0.61
        (340, 1_200),  # current:  scarcity ≈ 0.72
    ],

    # Restoration ecologist: rise then recovery.
    # An ecological writedown event in period -3 spiked demand; a training
    # surge and collective land program is refilling supply by the current period.
    "restoration_ecologist": [
        (220, 800),    # period -4: scarcity ≈ 0.73 (pre-crisis baseline)
        (200, 1_100),  # period -3: scarcity ≈ 0.82 (crisis spike)
        (250, 1_050),  # period -2: scarcity ≈ 0.76 (demand stabilising)
        (380, 980),    # period -1: scarcity ≈ 0.61 (new cohort graduating)
        (520, 900),    # current:  scarcity ≈ 0.42 (supply response visible)
    ],

    # --- Infrastructure domain ---

    # Civil engineer: recovering scarcity with supply-response elasticity.
    # A multiplier increase 6 years ago attracted trainees; they are now
    # qualified. Demonstrates the supply-response discount in scarcity_score().
    "civil_engineer": [
        (1_750, 5_000),  # period -4: scarcity ≈ 0.65
        (1_850, 5_000),  # period -3: scarcity ≈ 0.63
        (2_050, 5_000),  # period -2: scarcity ≈ 0.59
        (2_400, 5_000),  # period -1: scarcity ≈ 0.52
        (3_600, 5_000),  # current:  scarcity ≈ 0.28
    ],

    # --- Knowledge domain ---

    # General educator: oversupply — practitioners exceed demand.
    # Automation has absorbed much routine education delivery; human educator
    # demand has contracted. Practitioner count exceeds demand → scarcity = 0.
    "general_educator": [
        (5_200, 5_800),  # period -4: scarcity ≈ 0.10
        (5_500, 5_600),  # period -3: scarcity ≈ 0.02
        (5_900, 5_500),  # period -2: scarcity = 0 (supply meets demand)
        (6_200, 5_300),  # period -1: scarcity = 0 (oversupply begins)
        (6_400, 5_100),  # current:  scarcity = 0 (clear oversupply)
    ],
}

# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------

SEVERE_SCARCITY_EXAMPLE: list[tuple[float, float]] = PRACTITIONER_HISTORIES["neurosurgeon"]
RECOVERING_EXAMPLE:      list[tuple[float, float]] = PRACTITIONER_HISTORIES["civil_engineer"]
STABLE_EXAMPLE:          list[tuple[float, float]] = PRACTITIONER_HISTORIES["community_care_worker"]
