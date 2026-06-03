"""
Reference workforce composition snapshots for population_weighted_mean_multiplier().

Each snapshot is a list of segment dicts compatible with
population_weighted_mean_multiplier() — keys "name", "fraction", "mean_mu".
Fractions sum to 1.0 (verified at module load).

Five snapshots cover the key multiplier band positions:

  reference     M ≈ 1.98  FI-0023 national baseline at ε ≈ 0.40
  below_band    M ≈ 1.65  Automation eliminated base-tier jobs; M collapsed
  above_band    M ≈ 2.35  Credential inflation: Skilled → Advanced reclassification drift
  high_epsilon  M ≈ 2.20  High-ε composition: base tier nearly automated away
  low_epsilon   M ≈ 1.85  Low-ε composition: large base workforce, few specialists

Layer rule: no imports from hours_eoh core, land, or scenarios.
"""

WORKFORCE_SNAPSHOTS: dict[str, list[dict]] = {

    # Reference economy — FI-0023 national baseline at ε ≈ 0.40.
    # M = 0.22×1.20 + 0.52×1.85 + 0.21×2.70 + 0.05×4.00 ≈ 1.993
    "reference": [
        {"name": "base",     "fraction": 0.22, "mean_mu": 1.20},
        {"name": "standard", "fraction": 0.52, "mean_mu": 1.85},
        {"name": "advanced", "fraction": 0.21, "mean_mu": 2.70},
        {"name": "elite",    "fraction": 0.05, "mean_mu": 4.00},
    ],

    # Below-band — automation displaced base-tier workers faster than mid-tier
    # roles absorbed them. Remaining workforce is concentrated in low-skill
    # service roles and an unchanged specialist tier.
    # M = 0.40×1.10 + 0.40×1.70 + 0.15×2.50 + 0.05×3.00 ≈ 1.645
    "below_band": [
        {"name": "base",     "fraction": 0.40, "mean_mu": 1.10},
        {"name": "standard", "fraction": 0.40, "mean_mu": 1.70},
        {"name": "advanced", "fraction": 0.15, "mean_mu": 2.50},
        {"name": "elite",    "fraction": 0.05, "mean_mu": 3.00},
    ],

    # Above-band — credential inflation: governance cycle allowed systematic
    # reclassification of Skilled roles into Advanced without corresponding
    # competency evidence. Anti-gaming safeguards should flag this.
    # M = 0.15×1.10 + 0.45×1.90 + 0.30×3.00 + 0.10×4.30 ≈ 2.350
    "above_band": [
        {"name": "base",     "fraction": 0.15, "mean_mu": 1.10},
        {"name": "standard", "fraction": 0.45, "mean_mu": 1.90},
        {"name": "advanced", "fraction": 0.30, "mean_mu": 3.00},
        {"name": "elite",    "fraction": 0.10, "mean_mu": 4.30},
    ],

    # High-epsilon — automation has absorbed most base-tier production work.
    # Remaining human workforce is concentrated in care, stewardship, and
    # complex knowledge roles. Base tier near-zero.
    # M = 0.10×1.10 + 0.55×1.85 + 0.28×2.90 + 0.07×4.00 ≈ 2.220
    "high_epsilon": [
        {"name": "base",     "fraction": 0.10, "mean_mu": 1.10},
        {"name": "standard", "fraction": 0.55, "mean_mu": 1.85},
        {"name": "advanced", "fraction": 0.28, "mean_mu": 2.90},
        {"name": "elite",    "fraction": 0.07, "mean_mu": 4.00},
    ],

    # Low-epsilon — early-arc economy with large base labor force and few
    # specialists. Human capital investment is just beginning.
    # M = 0.30×1.15 + 0.48×1.80 + 0.18×2.60 + 0.04×4.50 ≈ 1.857
    "low_epsilon": [
        {"name": "base",     "fraction": 0.30, "mean_mu": 1.15},
        {"name": "standard", "fraction": 0.48, "mean_mu": 1.80},
        {"name": "advanced", "fraction": 0.18, "mean_mu": 2.60},
        {"name": "elite",    "fraction": 0.04, "mean_mu": 4.50},
    ],
}

# Verify all snapshots at module load — fractions must sum to 1.0.
for _name, _segs in WORKFORCE_SNAPSHOTS.items():
    _total = sum(s["fraction"] for s in _segs)
    assert abs(_total - 1.0) < 1e-6, (
        f"WORKFORCE_SNAPSHOTS['{_name}'] fractions sum to {_total:.6f}, expected 1.0"
    )
del _name, _segs, _total
