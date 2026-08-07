"""
Structural constants for the HOURS EOH framework.

These are the default calibration targets and fixed parameters used
across the codebase. All domain-specific constants live here.

Mission Statement references throughout — see inline comments.
"""

# ---------------------------------------------------------------------------
# Age groups: personal EOH weights
# Mission Statement: §"Humans as capital stock" — newborns and elderly
# generate more personal EOH than working-age adults.
#
# Tags (2026-08-05 four-tag migration): eoh_weight is CHOSEN — the DIRECTION
# (infants and elderly draw more caregiver labour) is structural, the 3.0/2.5
# magnitudes are asserted. fraction is CHOSEN (an OECD-shaped default).
# Epistemic pointers: ATUS "caring for and helping household children/adults"
# hours per care-recipient by age, plus NHATS/HRS for assistance to older adults;
# national census / UN WPP for the fractions.
# ---------------------------------------------------------------------------
AGE_GROUPS: dict[str, dict] = {
    "infant":      {"range": (0, 5),    "fraction": 0.07, "eoh_weight": 3.0},
    "child":       {"range": (6, 17),   "fraction": 0.16, "eoh_weight": 1.5},
    "working_age": {"range": (18, 64),  "fraction": 0.60, "eoh_weight": 1.0},
    "elderly":     {"range": (65, 100), "fraction": 0.17, "eoh_weight": 2.5},
}

# ---------------------------------------------------------------------------
# Capital asset types: maintenance profiles for EOH compounding (Phase 2)
# Mission Statement: §"EOH and compounding" — "stone bridge: slow; software:
# fast; ecosystem: slow then spike"
# ---------------------------------------------------------------------------
ASSET_TYPES: dict[str, dict] = {
    # compound_exp: post-threshold power-law escalation exponent.
    # Higher → more severe collapse once threshold age is breached.
    # stone_bridge 1.5: slow structural creep; software 3.0: rapid cascade failure;
    # ecosystem 2.0: slow then hard spike; power_grid 2.2: cascade risk at threshold.
    "stone_bridge":  {"maint_rate": 0.005, "threshold_age": 80,  "compound_exp": 1.5},
    "software":      {"maint_rate": 0.25,  "threshold_age": 5,   "compound_exp": 3.0},
    "ecosystem":     {"maint_rate": 0.010, "threshold_age": 200, "compound_exp": 2.0},
    "building":      {"maint_rate": 0.020, "threshold_age": 50,  "compound_exp": 1.8},
    "power_grid":    {"maint_rate": 0.040, "threshold_age": 30,  "compound_exp": 2.2},
    "generic_infra": {"maint_rate": 0.025, "threshold_age": 40,  "compound_exp": 1.9},
}

# ---------------------------------------------------------------------------
# Capital machine profiles: EOH elimination capacity by capital type.
# Used by civilization.py to derive machine_eoh_fulfilled from physical
# capital stock, enabling endogenous ε computation.
#
# eoh_elimination_rate: system EOH (infra/ecological/knowledge) eliminated
#   per TEH of capital per year, at condition=1.0.
# personal_fulfillment_rate: personal EOH fulfilled per TEH per year, at
#   condition=1.0. The biological demand still exists; capital handles it.
# design_life: expected useful life in years (for age → condition derivation).
# tiers: shorthand specs per named tier.
#   teh_per_capita: TEH value per person (scaled by population at call time).
#   default_age: assumed age in years when tier is used without explicit age.
#   default_condition: assumed condition ∈ [0,1] when tier is used without explicit condition.
#
# Calibration rationale:
#   A civilization with all types at "standard" tier totals ~2000 TEH/person
#   (matching CAPITAL_STOCK_DEFAULT / 1M population) and produces machine_eoh
#   that implies ε ≈ 0.18. Advancing to "advanced" tiers across all types
#   implies ε ≈ 0.48. These bracket the mid-automation arc (ε=0.20–0.50)
#   for well-invested civilizations. ε > 0.50 requires explicit over-investment
#   or knowledge-intensive computing_ai / industrial_automation buildout.
#
# Mission Statement: §"ε is a physical observable" — this table is the
# machine-capacity sub-model that makes ε emergent from physical state.
# ---------------------------------------------------------------------------
CAPITAL_MACHINE_PROFILES: dict[str, dict] = {
    # --- Energy and utilities ---
    "power_grid": {
        # Eliminates infrastructure EOH; fulfills personal heating/cooling/cooking EOH.
        "eoh_elimination_rate":    0.04,
        "personal_fulfillment_rate": 0.15,
        "design_life": 40,
        "tiers": {
            "minimal":  {"teh_per_capita":   80, "default_age": 35, "default_condition": 0.58},
            "basic":    {"teh_per_capita":  160, "default_age": 25, "default_condition": 0.72},
            "standard": {"teh_per_capita":  380, "default_age": 15, "default_condition": 0.82},
            "advanced": {"teh_per_capita":  950, "default_age":  8, "default_condition": 0.92},
        },
    },
    "water_treatment": {
        # Eliminates ecological EOH; directly fulfills sanitation/drinking personal EOH.
        "eoh_elimination_rate":    0.02,
        "personal_fulfillment_rate": 0.18,
        "design_life": 50,
        "tiers": {
            "minimal":  {"teh_per_capita":   40, "default_age": 40, "default_condition": 0.60},
            "basic":    {"teh_per_capita":   80, "default_age": 25, "default_condition": 0.73},
            "standard": {"teh_per_capita":  180, "default_age": 20, "default_condition": 0.83},
            "advanced": {"teh_per_capita":  450, "default_age": 10, "default_condition": 0.93},
        },
    },
    # --- Healthcare ---
    "medical_systems": {
        # Dominant personal fulfillment: hospitals, diagnostics, automated care.
        # Knowledge EOH elimination: clinical informatics, decision support.
        "eoh_elimination_rate":    0.01,
        "personal_fulfillment_rate": 0.22,
        "design_life": 20,
        "tiers": {
            "minimal":  {"teh_per_capita":   60, "default_age": 18, "default_condition": 0.65},
            "basic":    {"teh_per_capita":  120, "default_age": 12, "default_condition": 0.76},
            "standard": {"teh_per_capita":  280, "default_age":  8, "default_condition": 0.85},
            "advanced": {"teh_per_capita":  700, "default_age":  4, "default_condition": 0.95},
        },
    },
    # --- Food and ecology ---
    "agricultural_automation": {
        # Eliminates significant ecological EOH (farming = primary ecosystem stewardship).
        # Fulfills personal EOH via food security.
        "eoh_elimination_rate":    0.08,
        "personal_fulfillment_rate": 0.18,
        "design_life": 15,
        "tiers": {
            "minimal":  {"teh_per_capita":   20, "default_age": 12, "default_condition": 0.62},
            "basic":    {"teh_per_capita":   45, "default_age":  8, "default_condition": 0.74},
            "standard": {"teh_per_capita":   90, "default_age":  5, "default_condition": 0.84},
            "advanced": {"teh_per_capita":  225, "default_age":  2, "default_condition": 0.95},
        },
    },
    "environmental_monitoring": {
        # Does not fulfill EOH directly — increases monitoring_capability, making
        # deferred ecological obligations visible. eoh_elimination_rate reflects
        # the ecological labor displaced by automated sensing/reporting.
        "eoh_elimination_rate":    0.06,
        "personal_fulfillment_rate": 0.00,
        "design_life": 12,
        "tiers": {
            "minimal":  {"teh_per_capita":    4, "default_age": 10, "default_condition": 0.62},
            "basic":    {"teh_per_capita":    8, "default_age":  7, "default_condition": 0.76},
            "standard": {"teh_per_capita":   18, "default_age":  4, "default_condition": 0.87},
            "advanced": {"teh_per_capita":   45, "default_age":  2, "default_condition": 0.95},
        },
    },
    # --- Industrial and logistics ---
    "industrial_automation": {
        # Primary system EOH eliminator: manufacturing, construction, maintenance bots.
        # Small personal fulfillment (goods production indirectly covers needs).
        "eoh_elimination_rate":    0.14,
        "personal_fulfillment_rate": 0.02,
        "design_life": 20,
        "tiers": {
            "minimal":  {"teh_per_capita":   40, "default_age": 18, "default_condition": 0.62},
            "basic":    {"teh_per_capita":   80, "default_age": 12, "default_condition": 0.74},
            "standard": {"teh_per_capita":  180, "default_age":  8, "default_condition": 0.84},
            "advanced": {"teh_per_capita":  450, "default_age":  4, "default_condition": 0.94},
        },
    },
    "transportation": {
        # Eliminates logistics/infrastructure EOH; moderate personal fulfillment
        # (mobility reduces effective personal care distances/costs).
        "eoh_elimination_rate":    0.05,
        "personal_fulfillment_rate": 0.06,
        "design_life": 30,
        "tiers": {
            "minimal":  {"teh_per_capita":   40, "default_age": 25, "default_condition": 0.63},
            "basic":    {"teh_per_capita":   80, "default_age": 18, "default_condition": 0.74},
            "standard": {"teh_per_capita":  180, "default_age": 12, "default_condition": 0.83},
            "advanced": {"teh_per_capita":  450, "default_age":  6, "default_condition": 0.93},
        },
    },
    # --- Knowledge and computing ---
    "computing_ai": {
        # Highest knowledge EOH eliminator: automates administrative, analytical,
        # and decision-support labor. Short design life due to rapid obsolescence.
        "eoh_elimination_rate":    0.22,
        "personal_fulfillment_rate": 0.01,
        "design_life": 6,
        "tiers": {
            "minimal":  {"teh_per_capita":   20, "default_age": 5, "default_condition": 0.60},
            "basic":    {"teh_per_capita":   45, "default_age": 3, "default_condition": 0.76},
            "standard": {"teh_per_capita":  100, "default_age": 2, "default_condition": 0.88},
            "advanced": {"teh_per_capita":  250, "default_age": 1, "default_condition": 0.96},
        },
    },
    "software": {
        # Knowledge EOH elimination via automation of workflows, logistics, governance.
        # Very short design life: software decays quickly without maintenance.
        "eoh_elimination_rate":    0.18,
        "personal_fulfillment_rate": 0.01,
        "design_life": 8,
        "tiers": {
            "minimal":  {"teh_per_capita":   10, "default_age": 6, "default_condition": 0.62},
            "basic":    {"teh_per_capita":   25, "default_age": 4, "default_condition": 0.74},
            "standard": {"teh_per_capita":   60, "default_age": 2, "default_condition": 0.86},
            "advanced": {"teh_per_capita":  150, "default_age": 1, "default_condition": 0.95},
        },
    },
    # --- Built environment ---
    "building": {
        # Long-lived shelter capital. Moderate personal fulfillment (housing).
        # Minimal EOH elimination — buildings don't automate entropy resistance.
        "eoh_elimination_rate":    0.01,
        "personal_fulfillment_rate": 0.08,
        "design_life": 60,
        "tiers": {
            "minimal":  {"teh_per_capita":   80, "default_age": 50, "default_condition": 0.68},
            "basic":    {"teh_per_capita":  160, "default_age": 30, "default_condition": 0.77},
            "standard": {"teh_per_capita":  380, "default_age": 20, "default_condition": 0.84},
            "advanced": {"teh_per_capita":  950, "default_age": 10, "default_condition": 0.93},
        },
    },
    "generic_infra": {
        # Catch-all for unspecified infrastructure (roads, bridges, ports, etc.).
        # Low EOH elimination and personal fulfillment — rough connectivity only.
        "eoh_elimination_rate":    0.02,
        "personal_fulfillment_rate": 0.02,
        "design_life": 40,
        "tiers": {
            "minimal":  {"teh_per_capita":   12, "default_age": 35, "default_condition": 0.63},
            "basic":    {"teh_per_capita":   30, "default_age": 25, "default_condition": 0.74},
            "standard": {"teh_per_capita":   54, "default_age": 15, "default_condition": 0.83},
            "advanced": {"teh_per_capita":  135, "default_age":  8, "default_condition": 0.93},
        },
    },
}

# ---------------------------------------------------------------------------
# Capital condition derivation constants (used in civilization.py)
# Linear decay: condition = 1.0 - COND_DECAY_SLOPE × (age/design_life),
# floored at COND_DECAY_FLOOR so end-of-life assets remain operational
# (full write-down is a separate explicit event via execute_writedown).
# ---------------------------------------------------------------------------
COND_DECAY_SLOPE: float = 0.70   # fractional condition lost over full design life
COND_DECAY_FLOOR: float = 0.30   # minimum condition for an asset still in service

# Environmental monitoring saturation constant: at this many TEH per capita
# of environmental_monitoring capital, monitoring_capability reaches 1.0.
# Below this, capability scales linearly above CANONICAL_MONITORING_CAPABILITY_BASE.
ENV_MONITORING_SATURATION_TEH_PER_CAPITA: float = 500.0

# ---------------------------------------------------------------------------
# Essential domains for Condition IV (Distributed Competency)
# Mission Statement: §"Condition IV" — agriculture, construction, energy,
# water, healthcare, manufacturing, and logistics.
# ---------------------------------------------------------------------------
ESSENTIAL_DOMAINS: list[str] = [
    "agriculture", "construction", "energy", "water",
    "healthcare", "manufacturing", "logistics",
]
COMPETENCY_THRESHOLD: float = 0.155  # 15.5% of workforce, per Mission Statement

# Minimum annual labor obligation supporting Condition IV
H_MIN: int = 260  # hours/year
H_MIN_ALLOCATION: dict[str, float] = {
    "competency_rotation": 0.40,  # 40% → essential domain practice
    "stewardship_service": 0.30,  # 30% → stewardship labor
    "regular_employment":  0.30,  # 30% → normal work
}

# ---------------------------------------------------------------------------
# Multiplier band (Condition II)
# Mission Statement: §"Condition II — Multiplier Band"
# ---------------------------------------------------------------------------
M_BAND_LOW: float = 1.8
M_BAND_HIGH: float = 2.1
M_BAND_TARGET: float = 2.1
M_MAX: float = 6.0

# Multiplier — additive formula absolute scale
# When all four alpha coefficients are at their equal share, each equals
# ALPHA_SCALE / 4 = 1.25, so m(c) = 1 + Σ αᵢ·fᵢ reaches M_MAX at all-ones.
ALPHA_SCALE: float = M_MAX - 1.0          # = 5.0; Σαᵢ = ALPHA_SCALE at full range

# Impact sub-question weights for compute_impact_score(); must sum to 1.0.
ALPHA_IMPACT_EOH_REDUCTION_WEIGHT:   float = 0.40  # fraction of domain EOH eliminated per hour
ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT: float = 0.35  # breadth of domain EOH this role covers
ALPHA_IMPACT_RESILIENCE_WEIGHT:      float = 0.25  # emergency reserve capacity

# ---------------------------------------------------------------------------
# Multiplier — measured-data geometric map (frozen reference mult-5.1.0)
#
# The FLOOR-semantics map adopted from the O*NET/BLS v5.1 measurement pass
# (reference epoch 2026-07-29). This SUPERSEDES the additive
# m = 1 + Σαᵢ·fᵢ form for the reference multiplier: author-signed-off
# 2026-07-30 (see notes/hours-reconciliation.md §3, handoffs/multipliers-v5
# KNOWN_ISSUES §3 — the additive floor term mechanically crushed the ladder).
# The additive tier_multiplier()/epoch_alpha_weights() are retained, deprecated,
# for backward compatibility.
#
#     m(composite) = M_FLOOR · M_GEOMETRIC_R ** z
#     z = clip((composite − Z_LO) / (Z_HI − Z_LO), 0, 1)
#     composite = Σ w_i · f_i    over measured factors f_i ∈ [0, 1]
#
# R, the z-range and the factor weights are FROZEN at the reference epoch; they
# are DERIVED-THEN-FROZEN, not tunable (re-derivation restores the circularity
# the freeze exists to break). Mirror of reference/data/multiplier_reference_bounds.json.
# ---------------------------------------------------------------------------
M_FLOOR:          float = 1.0    # constitutional floor multiplier (measured min)
M_GEOMETRIC_R:    float = 3.2    # DERIVED-THEN-FROZEN spread ratio (solved at reference epoch)
M_COMPOSITE_Z_LO: float = 0.15307309621788462  # frozen composite lower bound
M_COMPOSITE_Z_HI: float = 0.7401986094479613   # frozen composite upper bound

# Frozen factor weights (training, demand, scarcity, impact) — CHOSEN, uncalibrated.
# Epistemic pointer: no measurement behind the split; sweep ±0.10 each (see
# scenarios/multiplier_sensitivity.py). Sum to 1.0.
M_FACTOR_WEIGHTS: tuple[float, float, float, float] = (0.30, 0.25, 0.20, 0.25)

# Frozen impact sub-domain weights (dependency, substitutability, harm, temporal)
# — CHOSEN. Used to reconstruct f_impact from the measured i_* sub-components.
# Sum to 1.0. Impact composite is affine outer-normalized against these bounds.
M_IMPACT_SUBDOMAIN_WEIGHTS: tuple[float, float, float, float] = (0.30, 0.25, 0.25, 0.20)
M_IMPACT_COMPOSITE_LO: float = 0.3317494225632136  # frozen impact-composite lower bound
M_IMPACT_COMPOSITE_HI: float = 0.7519582943881703  # frozen impact-composite upper bound

# Epoch-adaptive factor weights across the automation arc — CHOSEN (illustrative
# anchors, piecewise-linear interpolated). Each anchor is (training, demand,
# scarcity, impact), summing to 1.0. Epistemic pointer: the ε-dependence of the
# weighting is a governance judgement, not a measurement; the ε=0.40 anchor
# equals the frozen M_FACTOR_WEIGHTS by construction. At ε→1 impact dominates
# (copy/merge limit: only impact survives — see handoffs KNOWN_ISSUES §5).
M_EPOCH_WEIGHT_ANCHORS: dict[float, tuple[float, float, float, float]] = {
    0.00: (0.35, 0.30, 0.20, 0.15),
    0.40: (0.30, 0.25, 0.20, 0.25),
    0.90: (0.20, 0.20, 0.20, 0.40),
    0.99: (0.15, 0.15, 0.15, 0.55),
}

# Governance assessment thresholds
GOVERNANCE_MIN_ASSESSORS:       int   = 3     # fewer than this triggers a WARN
GOVERNANCE_IRR_WARN_THRESHOLD:  float = 0.70  # inter-rater reliability below → WARN
GOVERNANCE_IRR_CRIT_THRESHOLD:  float = 0.50  # inter-rater reliability below → CRIT

# ---------------------------------------------------------------------------
# Multiplier governance: scarcity dampening (B3)
# Mission Statement: §"Scarcity — the three-year rolling average prevents
# oscillation; supply-response discount prevents over-rewarding roles where
# raising the multiplier will itself resolve the scarcity."
# ---------------------------------------------------------------------------
SCARCITY_ROLLING_WINDOW: int = 3        # periods in rolling average
SCARCITY_SUPPLY_LAG_YEARS: int = 3      # years for supply to respond to raised multiplier
SCARCITY_SEVERE_THRESHOLD: float = 0.80 # above this, flag as SEVERE_SCARCITY

# ---------------------------------------------------------------------------
# Multiplier governance: anti-gaming safeguards (B5)
# Mission Statement: §"Anti-gaming safeguards" — empirical training validation,
# artificial scarcity detection, sunset reassessment enforcement.
# ---------------------------------------------------------------------------
TRAINING_VALIDATION_TOLERANCE: float = 1.5        # mandated/median ratio ceiling
ARTIFICIAL_SCARCITY_PASS_RATE_FLOOR: float = 0.30 # below this always flagged
ARTIFICIAL_SCARCITY_QUALITY_THRESHOLD: float = 0.20 # min quality differential to justify low pass rate
TIER_ASSESSMENT_INTERVAL_YEARS: int = 5           # years before tier must be reassessed

# Default workforce tier segments: (name, fraction, mean_multiplier)
# Calibrated so weighted mean = 2.10 at ε=0.
# 0.20×1.20 + 0.50×1.87 + 0.25×2.80 + 0.05×4.50 = 2.100
DEFAULT_SEGMENTS: list[dict] = [
    {"name": "base",     "fraction": 0.20, "mean_mu": 1.20},
    {"name": "standard", "fraction": 0.50, "mean_mu": 1.87},
    {"name": "advanced", "fraction": 0.25, "mean_mu": 2.80},
    {"name": "elite",    "fraction": 0.05, "mean_mu": 4.50},
]

# ---------------------------------------------------------------------------
# Care registration sigmoid defaults
# Mission Statement: §"slow onset, rapid mid-range acceleration, and full
# registration reached before ε reaches 1.0"
# ---------------------------------------------------------------------------
CARE_SIGMOID_DEFAULTS: dict[str, float] = {
    "start_share":  0.05,   # minimal at ε=0 (formal education, public health only)
    "inflection":   0.45,   # rapid rise around ε=0.45
    "rate":         8.0,    # sigmoid steepness
    "saturation":   0.95,   # asymptote; never reaches 1.0
}

# ---------------------------------------------------------------------------
# EOH base rates (per-capita or per-unit at reference conditions)
#
# DOMAIN BALANCE (measured 2026-08-05, docs/parameter_provenance.md §"Domain
# balance"): at defaults the personal domain is 91–97% of total_eoh() at EVERY
# ε; ecological is 0.71 h/person·yr and knowledge 0.01–0.97. ε = machine/total is
# therefore ~95% a personal-domain number, and PERSONAL_EOH_BASE is the single
# most leveraged constant in the model. Retagged CHOSEN in the same pass — it is
# an arithmetic sum of four desk estimates (208 + 156 + 208 + 936), not a
# structural claim about entropy. Epistemic pointer: BLS American Time Use
# Survey, which measures all four components directly and is not yet used
# anywhere in this repo.
#
# ---------------------------------------------------------------------------
# THE STANDARDS SPLIT (Block I, 2026-08-06). One constant was doing three jobs.
#
# Two ORTHOGONAL axes were conflated in a single `PERSONAL_EOH_BASE`:
#
#                        autarky delivery      collective delivery
#   survival standard          S_a                    S_c
#   sufficiency standard       F_a                    F_c
#
# STANDARD is what is owed (staying alive vs living decently). DELIVERY is what
# it costs to discharge it (alone vs through a collective's apparatus). They are
# independent, and abatement — infrastructure REDUCING the obligation, not merely
# serving it — is the map from the left column to the right.
#
# Both standards below are AUTARKY-REFERENCED (X_a): what the obligation costs a
# person handling their own, with no collective apparatus. That is the reference
# the overbuild test compares against, and it is why F_a is allowed to exceed the
# labour supply — the gap between what sufficiency costs alone and what a
# population can supply alone is precisely why collectives form.
#
# S_a IS HARD-BOUNDED, F_a IS NOT. A survival standard exceeding labour supply
# means extinction, so S_a ≤ (L − R)/w = 627 per-equivalent against this file's
# own H_REF × workforce_fraction. 600 sits just inside it and is set
# INDEPENDENTLY rather than pinned to the bound, so scenarios/feasibility.py can
# still CHECK it — a constant that cannot fail its own test says nothing.
#
# This split corrects a category error: the earlier finding that "ε = 0 is not a
# feasible state" applied a SURVIVAL feasibility test to a SUFFICIENCY number. At
# S_a = 600, ε_suff = 0 — subsistence survives with no automation, as it did. The
# true statement is that subsistence can survive but cannot reach SUFFICIENCY
# without automation.
# ---------------------------------------------------------------------------
PERSONAL_EOH_SURVIVAL: float    = 600.0   # S_a — autarky-referenced survival standard.
                                          # CHOSEN. Bounded above by (L−R)/w = 627; checked,
                                          # not pinned. resolves_by: minimum-subsistence
                                          # time-allocation studies (the components that
                                          # kill you if unmet: food, water, shelter, warmth).
PERSONAL_EOH_SUFFICIENCY: float = 1500.0  # F_a — autarky-referenced sufficiency standard.
                                          # CHOSEN. The original desk estimate, re-read
                                          # correctly: it was never a survival figure.
                                          # Cross-checks: the identity route gives
                                          # F_c(modern) = 390–926, implying 38–74% abatement,
                                          # and "all needs met" needs 30% at ε=0.99 — mid-band.
                                          # resolves_by: cross-cultural time allocation at a
                                          # stated adequacy standard, + the identity route.

# ---------------------------------------------------------------------------
# PERSONAL_EOH_BASE — the ABATEMENT-COLLAPSED operating value.
#
# Until abatement a(K) exists (Block II), one number has to stand in for
# F_a × (1 − a(K)) at an unstated point on the arc. 1000 is that placeholder, and
# it is coherent as one: 1000 ≈ 1500 × (1 − 1/3), and a ≈ 33% sits mid-range
# between the 10% that "all needs met" requires at ε = 0.40 and the 38–74% the
# identity route implies at modern capital.
#
# Repriced 1500 → 1000 on 2026-08-06 (author decision) to the high end of the
# then-available evidence, on the asymmetric-loss argument: setting it too low
# hides a real shortfall (model reports feasible, capital under-built, deficit
# paid in unserved obligation), too high only over-builds capital.
#
# Block I deliberately does NOT move this to 1500. The standards above are
# declared and usable, but the generation default is unchanged, because it is
# abatement — not the standards split — that determines the operating value. When
# Block II lands, this constant is replaced by F_a × (1 − a(K)) and retired.
#
# STILL CHOSEN. resolves_by: the capital-inventory + time-use identity, NOT
# time-use data alone — see the circularity section in
# docs/parameter_provenance.md.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ABATEMENT (Block II, 2026-08-06) — infrastructure REDUCES the obligation,
# it does not only serve it.
#
# The model previously had SUBSTITUTION only: personal EOH is flat across the
# whole arc (1475 → 1480) and ε merely splits who serves it. That is physically
# wrong. PERSONAL_EOH_BASE's own components are infrastructure-dependent — a
# serviced dwelling needs less upkeep than a mud hut, a tap replaces water
# hauling, and sanitation cuts the disease burden that drives care hours.
#
#     B(K) = F_a × (1 − a(K))        a(K) = a_max · K / (K + K_half)
#
# a(0) = 0 and a(∞) = a_max. a_max is NOT a free parameter — it is derived from
# the per-component abatability ceilings below, weighted by the component shares,
# which are themselves the original desk estimate's own four terms
# (208 / 156 / 208 / 936 over 1508).
#
# THE STRUCTURAL PREDICTION, encoded here and TESTED rather than assumed:
# abatability and sufficiency are ANTI-CORRELATED. What infrastructure can remove
# is the survival-shaped work — hauling water, gathering fuel, preparing food.
# What it cannot remove is CARE: a child needs human attention, which is the
# Baumol case. So the residual personal obligation as ε → 1 should be almost
# entirely care, and a_max is bounded well below 1 by care's 62% share.
# ---------------------------------------------------------------------------
PERSONAL_EOH_COMPONENTS: dict[str, dict] = {
    # share:       fraction of the personal obligation (from the desk estimate)
    # abatability: the ceiling — the most of this component infrastructure can
    #              ever remove. CHOSEN, each with an epistemic pointer.
    "nutrition": {"share": 208.0 / 1508.0, "abatability": 0.85},
    #   resolves_by: food-system time-use across development levels (subsistence
    #   cultivation + processing vs a distribution network). Highly abatable.
    "shelter":   {"share": 156.0 / 1508.0, "abatability": 0.90},
    #   resolves_by: WHO/UNICEF JMP water-and-sanitation access studies, which
    #   measure hauling-time reduction directly. The most abatable component.
    "health":    {"share": 208.0 / 1508.0, "abatability": 0.60},
    #   resolves_by: GBD disease burden attributable to WASH, converted to care
    #   hours avoided. Partly abatable — prevention scales, treatment less so.
    "care":      {"share": 936.0 / 1508.0, "abatability": 0.25},
    #   resolves_by: childcare/eldercare time-use across development levels.
    #   LEAST abatable and the largest share — this is what bounds a_max.
}

ABATEMENT_HALF_CAPITAL_TEH: float = 1000.0
#   K_half — capital per capita at which HALF of the abatable obligation is
#   abated. CHOSEN, and the least-grounded constant in this block: it sets the
#   PACE of abatement along the arc, not its ceiling. resolves_by: the identity
#   route run at two or more capital levels — B(K) measured at matched
#   (inventory, time-use) pairs pins both a_max and K_half at once. Report the
#   sensitivity with any abatement figure until it does.

PERSONAL_EOH_BASE: float   = 1000.0     # hours/year per working-age-equivalent. CHOSEN — resolves_by: capital-inventory + time-use identity
INFRA_MAINT_RATE: float    = 0.025      # fraction of capital stock = EOH/year. CHOSEN — a point inside the OECD 2–4% band
INFRA_AGE_FACTOR_MAX: float = 2.0      # multiplier at end of design life. physics (convexity) / CHOSEN (the 2.0)

# ---------------------------------------------------------------------------
# Infrastructure — task-normative statutory floor (B+D design, currency-free)
#
# The floor stream of infrastructure_eoh_breakdown(): labour-hours per asset per
# year from a physical condition census, with NO money→hours conversion in the
# path. This is the measured, auditable half; discretionary maintenance ambition
# above it is a policy choice and enters the fulfilment/fiscal layer, never the
# floor. Motivated by handoffs/Infrastructure: the monetized capital_stock_teh
# path is convention-dominated 10× while every physical knob reads ×1.000 — the
# floor is ~5.9× better determined and its residual is timesheet-measurable.
#
# hours/unit/year = (12 / inspection_interval_months) × crew_hours_per_visit,
# which is what these defaults encode at the NBIS routine interval.
# Tag: CHOSEN (task-normative). Epistemic pointer: state DOT maintenance-activity
# manuals / inspection timesheets give the real per-condition crew-hours.
# ---------------------------------------------------------------------------
INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT: float = 24.0  # 23 CFR 650 routine default
INFRA_TREATMENT_HOURS_GOOD: float = 8.0    # hours/unit/year, good condition
INFRA_TREATMENT_HOURS_FAIR: float = 20.0   # hours/unit/year, fair condition
INFRA_TREATMENT_HOURS_POOR: float = 48.0   # hours/unit/year, poor condition

# SCALE WARNING (2026-08-05): ECOLOGICAL_BASE_RATE is documented as a RELATIVE
# anchor ("does not represent an absolute ecosystem-specific count") but is summed
# with absolute counts in total_eoh() and then divided into ε. At defaults it
# contributes 0.03% of total EOH, and KNOWLEDGE_EOH_BASE 0.005%. Consequence: the
# thermal obligation lands at ~1.8 h/person·yr and the ecological domain cannot
# move ε. Do not quote either domain's SHARE of total EOH until both are on an
# absolute footing. Epistemic pointers: a stewardship-hours census (agency FTEs
# per hectare / GUF parcel inventory × measured crew-hours); occupational
# training-and-CPD hours from the O*NET/BLS spine already ingested.
ECOLOGICAL_BASE_RATE: float = 500_000.0 # hours/year at pristine ecosystem health. CHOSEN — relative anchor, needs absolute footing
ECOLOGICAL_THRESHOLD: float = 0.40     # below this → nonlinear spike. physics (regime shift) / CHOSEN (0.40 on this index)
KNOWLEDGE_EOH_BASE: float  = 100_000.0  # baseline knowledge EOH at ε=0. CHOSEN — resolves_by: occupational CPD hours
KNOWLEDGE_EPS_EXPONENT: float = 2.0    # how steeply knowledge EOH grows with ε. physics (superlinear) / CHOSEN (exponent)

# ---------------------------------------------------------------------------
# Reference hours
# ---------------------------------------------------------------------------
H_REF: int = 2000  # reference work-year hours per worker

# ---------------------------------------------------------------------------
# TEH destruction defaults and ε-scaling slopes
# All anonymous ε-scaling factors that appear in eoh_fulfillment.py and
# simulation.py are named here so they can be swept and audited.
# ---------------------------------------------------------------------------
CAPITAL_FAILURE_RATE:               float = 0.005  # fraction of capital failing beyond repair/year
CAPITAL_WRITEDOWN_MONITORING_SLOPE: float = 0.30   # max failure-rate reduction at ε=1 from better monitoring
LABOR_INCOME_MIN_TEH:              float = 100_000_000.0  # hard floor on period labor income (100M TEH)
WORKFORCE_FRACTION_MIN:            float = 0.05           # minimum workforce fraction retained at any automation level

# ---------------------------------------------------------------------------
# D4 — CPI transaction-level destruction (Option 2)
# TEH destroyed when capital infrastructure delivers personal-EOH services at
# their embedded labor price. Fires proportionally to capital_personal_eoh_fulfilled.
# ---------------------------------------------------------------------------
# (no additional constants needed — uses BASKET_EOH_CONTENT and basket_price())

# ---------------------------------------------------------------------------
# D5 — Estate dissolution on death (Option 1)
# On death, accumulated savings above the personal reserve split into:
# inherited (circulatory), levied to Trust (circulatory), and written down.
# ---------------------------------------------------------------------------
ANNUAL_DEATH_RATE:              float = 0.010  # fraction of population dying per year
ESTATE_INHERITANCE_FRACTION:    float = 0.35   # fraction of excess above reserve passed to heirs
ESTATE_LEVY_FRACTION:           float = 0.15   # fraction of excess levied to Trust (circulatory)
ESTATE_PERSONAL_RESERVE_YEARS:  float = 10.0   # years of basket costs preserved unconditionally

# ---------------------------------------------------------------------------
# D6 — Accumulation ceiling capital commitment (Option 3, disabled by default)
# Excess TEH above the ceiling is committed to capital formation rather than
# sitting in perpetual savings. Moves TEH from circulation to capital_embodied.
# ---------------------------------------------------------------------------
ACCUMULATION_CEILING_MULTIPLIER: float = 3.5       # × base lifetime earnings
BASE_LIFETIME_EARNINGS_TEH:      float = 87_360.0  # 2080 TEH/yr × 42-yr career at 1× multiplier

# ---------------------------------------------------------------------------
# Fiscal architecture defaults (single source of truth)
# Used in: params.py, fiscal.py, dashboard.py, stress.py, prices.py
# ---------------------------------------------------------------------------
SUFF_LEVY_RATE:               float = 0.0125            # sufficiency levy rate on labor income
SUFF_GUARANTEE_EPS_DECAY:     float = 0.50              # rate at which guarantee floor_fraction shrinks with ε
TRUST_BASE_TEH:               float = 35_000_000_000.0  # Trust fund balance at ε=0 (TEH); sized for EOH-reimbursement guarantee
DEP_RATE:                     float = 0.045             # annual trust depreciation rate
DIV_RATE:                     float = 0.40              # fraction of depreciation paid as dividend
MEANINGFUL_ACTIVITY_TEH_BASE: float = 120.0            # discretionary spending bonus at ε=0 (TEH/yr)
MEANINGFUL_ACTIVITY_TEH_SCALE: float = 1.5              # quadratic ε-growth factor; bonus = base×(1+scale×ε²)
CAPITAL_STOCK_DEFAULT:        float = 2_000_000_000.0   # default capital stock for scenario functions
BASKET_EOH_CONTENT:           float = PERSONAL_EOH_BASE  # personal EOH hours satisfied per sufficiency basket — DEFINED as = PERSONAL_EOH_BASE
                                                         # (was a literal 1500.0 duplicating it; bound to the constant 2026-08-06 so the
                                                         # two cannot drift apart under repricing — one basket covers one person-year)

# ---------------------------------------------------------------------------
# Human capital biological constants (population.py + capital.py)
# ---------------------------------------------------------------------------
ELDERLY_EOH_EPSILON_FACTOR:   float = 0.05  # elderly EOH rises this fraction per ε unit
INFANT_EOH_EPSILON_FACTOR:    float = 0.10  # infant personal EOH declines this fraction per ε unit
HUMAN_CAPITAL_NATURAL_DECAY:  float = 0.005 # annual condition decay rate, non-elderly
HUMAN_CAPITAL_ELDERLY_DECAY:  float = 0.015 # annual condition decay rate, elderly
MATURATION_AUTO_LEVERAGE:     float = 0.30  # automation amplifies education returns: leverage = 1 + factor×ε

# ---------------------------------------------------------------------------
# Canonical trajectory constants
# These define the "ideal arc" — the expected physical state of a civilization
# at each ε value if it invests optimally. Previously hidden inside
# eoh_generation.py as anonymous private constants; now named and exported so
# trajectory.py can build canonical_physical_state() from a single source of
# truth and EOH generation functions remain pure-physics.
#
# Mission Statement: §"Principle 9 — Every mechanism must express the arc,
# not just a point on it." Diverse trajectories diverge from these values;
# this baseline ensures every function is validated across the full arc.
# ---------------------------------------------------------------------------
CANONICAL_CAPITAL_GROWTH_SLOPE:       float = 2.0   # capital 3× from ε=0 to ε=1: stock = baseline × (1 + slope×ε)
CANONICAL_MONITORING_CAPABILITY_BASE: float = 0.50  # fraction of deferred ecological EOH visible at ε=0
CANONICAL_MONITORING_CAPABILITY_SLOPE: float = 0.50 # additional visibility per ε unit (full at ε=1)
CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE: float = 9.0   # knowledge base ≈ 10× by ε=1: kbs = 1 + slope×ε
CANONICAL_KNOWLEDGE_COMPLEXITY_EXP:   float = 2.0   # per-unit complexity: factor = 1 + (ε^exp) × slope
CANONICAL_CAPITAL_AGE_DRIFT:          float = 0.20  # age_ratio increases across arc: 0.30 at ε=0 → 0.50 at ε=1
CANONICAL_ECOSYSTEM_HEALTH_BASE:      float = 0.90  # ecosystem health at ε=0 on ideal trajectory
CANONICAL_ECOSYSTEM_HEALTH_DRIFT:     float = -0.20 # drift by ε=1 (net of development pressure vs. stewardship)

# ---------------------------------------------------------------------------
# Ground Use Fee (GUF) — land/guf.py constants
# Template: NLSA Technical Manual TM-0042, Seventh Edition
# Mission Statement: §"Land is held by the collective … stewardship leases …
# the fee reflects real costs rather than speculative value."
# ---------------------------------------------------------------------------

# Epsilon scaling function Ψ(ε) — global arc multiplier (NLSA Eq. 18)
# Bell-shaped: near-floor at ε=0 and ε=0.99, peak near ε=0.40.
GUF_PSI_A:     float = 0.8   # rise speed from ε=0 (lower a = faster rise)
GUF_PSI_B:     float = 1.2   # fall speed toward ε=1 (higher b = faster fall)
GUF_PSI_FLOOR: float = 0.02  # irreducible floor; fee never reaches absolute zero
GUF_PSI_NORM:  float = 4.0   # normalizing constant; peak ≈ 1.0 when a+b≈2.0

# Labor-content scaling α(ε) — normalized so α(0.40) = 1.0 (NLSA Eq. 19-20)
GUF_ALPHA_ZETA:  float = 0.8   # rate of labor-content decline with automation
GUF_ALPHA_FLOOR: float = 0.05  # irreducible human-judgment fraction at ε→1

# Location Value Index default sub-index weights (NLSA Eq. 3); must sum to 1.0
GUF_LVI_W_CENTRALITY:      float = 0.35
GUF_LVI_W_TRANSIT:         float = 0.30
GUF_LVI_W_SERVICES:        float = 0.20
GUF_LVI_W_NATURAL_AMENITY: float = 0.15

# Use category reference rates at ε=0.40 (TEH/SLU/year) — midpoints of NLSA Eq. 9 ranges
# Calibrated so aggregate GUF across a 1M-population land inventory (~400k residential
# + 20k commercial parcels) is co-equal with levy revenue at mid-arc (ε≈0.40).
# At ×100 vs. the original abstract unit values: residential GUF ≈ 9.3M TEH/yr,
# commercial GUF ≈ 4.1M TEH/yr, total ≈ 13.4M TEH/yr vs. levy ≈ 6.2M TEH/yr (≈2.2×).
GUF_USE_RESIDENTIAL_PRIMARY:    float =  10.0
GUF_USE_RESIDENTIAL_SECONDARY:  float =  21.5
GUF_USE_AGRICULTURAL_ACTIVE:    float =   2.0
GUF_USE_AGRICULTURAL_FALLOW:    float =   5.0
GUF_USE_COMMERCIAL_RETAIL:      float =  30.0
GUF_USE_COMMERCIAL_OFFICE:      float =  22.5
GUF_USE_INDUSTRIAL_LIGHT:       float =  17.0
GUF_USE_INDUSTRIAL_HEAVY:       float =  37.5
GUF_USE_INSTITUTIONAL:          float =   1.0
GUF_USE_CONSERVATION_CREDIT:    float =  -6.0  # negative: credit reduces base fee

# Demand Pressure Modifier parameters (NLSA Eq. 11-13)
GUF_DEMAND_ETA_RESIDENTIAL: float = 0.15   # sensitivity for residential land
GUF_DEMAND_ETA_COMMERCIAL:  float = 0.25   # sensitivity for commercial land
GUF_DEMAND_D_MAX:           float = 1.80   # constitutional ceiling on D(p)

# Zone adjustment factor permitted range (NLSA §2.4.1)
GUF_ZONE_MIN: float = 0.80
GUF_ZONE_MAX: float = 1.25

# Ecosystem service replacement cost (κ) reference values at ε=0.40 (NLSA Eq. 14-15)
# These are κ_s(ε=0.40); the full ε-arc is derived in ecosystem_service_kappa().
GUF_ECO_KAPPA_WATER_FILTRATION:  float = 1.650   # TEH/ML/yr
GUF_ECO_KAPPA_FLOOD_ATTENUATION: float = 0.006   # TEH/m³/yr
GUF_ECO_KAPPA_CARBON:            float = 2.750   # TEH/tonne-CO₂eq/yr
GUF_ECO_KAPPA_AIR_QUALITY:       float = 5.500   # TEH/tonne-particulate/yr
GUF_ECO_KAPPA_POLLINATION:       float = 1.000   # TEH/ha-equiv/yr
GUF_ECO_KAPPA_BIODIVERSITY:      float = 0.350   # TEH/HQU/yr
GUF_ECO_KAPPA_THERMAL:           float = 0.030   # TEH/cooling-degree-day/yr

# Ecosystem service automation sensitivity β_s — exponent in κ(ε) decay (NLSA Eq. 15)
GUF_ECO_BETA_WATER_FILTRATION:  float = 0.8
GUF_ECO_BETA_FLOOD_ATTENUATION: float = 0.7
GUF_ECO_BETA_CARBON:            float = 0.9
GUF_ECO_BETA_AIR_QUALITY:       float = 1.0
GUF_ECO_BETA_POLLINATION:       float = 0.6
GUF_ECO_BETA_BIODIVERSITY:      float = 0.7
GUF_ECO_BETA_THERMAL:           float = 0.8

# Irreducible human-judgment floor for ecosystem κ — fraction of reference value
# At post-scarcity, some ecological judgment remains irreducibly human.
GUF_ECO_KAPPA_FLOOR_FRACTION: float = 0.10

# Infrastructure proximity distance-decay rates μ_k (km⁻¹) (NLSA Eq. 16)
GUF_INFRA_MU_TRANSIT:      float = 0.5
GUF_INFRA_MU_UTILITIES:    float = 0.2
GUF_INFRA_MU_PUBLIC_SPACE: float = 0.8

# Cross-collective infrastructure ownership factor (NLSA Eq. 25b)
GUF_CHI_EXTERNAL: float = 0.30

# Review cycle rate cap — max GUF increase per 5-year cycle (NLSA Eq. 21)
GUF_REVIEW_CYCLE_CAP: float = 0.10

# Income-linked subsidy thresholds for primary residential parcels (NLSA Eq. 24)
GUF_SUBSIDY_LOWER_THRESHOLD: float = 0.40  # below 40% of median → maximum subsidy
GUF_SUBSIDY_FLOOR_RATE:      float = 0.25  # subsidized leaseholders pay 25% of GUF
GUF_AFFORDABILITY_THRESHOLD: float = 0.25  # GUF ≤ 25% of income = accessible primary housing

# Agricultural soil-health credit rate (NLSA Eq. 26); symbol c_soil in equations
GUF_SOIL_CREDIT_RATE: float = 0.05  # TEH/SLU per unit improvement in Soil Health Index

# Ecological write-down parameters (NLSA §9)
GUF_WRITEDOWN_AMORTIZATION_YEARS: float = 50.0  # Y_r: replacement infra design life (Eq. 28)
GUF_EOH_ACCUMULATION_THRESHOLD:   float = 0.30  # 30% unfulfilled ecological EOH triggers warning (§9.8)

# ---------------------------------------------------------------------------
# Dashboard health indicator thresholds
# Dashboard.py owns the logic; data.py is the single numeric source.
# Stress tests also reference COMPOUNDING_CRIT.
# ---------------------------------------------------------------------------
DEFERRED_RATIO_WARN:       float = 0.10   # YELLOW: 10% deferred
DEFERRED_RATIO_CRIT:       float = 0.25   # RED: 25% deferred
REGISTRATION_WARN:         float = 0.35   # YELLOW below 35%
REGISTRATION_CRIT:         float = 0.20   # RED below 20%
COMPOUNDING_WARN:          float = 0.20   # YELLOW: compounding adds >20% of original
COMPOUNDING_CRIT:          float = 0.50   # RED: compounding adds >50% (spiral risk)
PP_INDEX_WARN:             float = 1.05                            # YELLOW threshold at ε=0.40 reference
PP_INDEX_WARN_SLOPE:       float = (PP_INDEX_WARN - 1.0) / 0.40  # per-ε slope: threshold = 1 + slope×ε
LEVY_SUFFICIENCY_WARN:     float = 0.02   # YELLOW if levy covers < 2% of guarantee
CARE_ADMISSION_GREEN_FRAC: float = 0.20   # care share ≥ 20% of saturation → GREEN
CARE_ADMISSION_YELLOW_FRAC: float = 0.10  # care share ≥ 10% of saturation → YELLOW

# ---------------------------------------------------------------------------
# Contestability invariant (reconciliation §8)
# Functional forms proposed, not calibrated from data — see research/contestability.py.
# ---------------------------------------------------------------------------
CONTESTABILITY_K0_TEH: float = 1_800.0          # founding cost of a viable alternative collective at ε=0 (TEH/person)
CONTESTABILITY_K_SLOPE: float = 1.6             # how fast K_entry scales per unit ε
CONTESTABILITY_K_FLOOR_FRACTION: float = 0.10   # minimum K_entry as fraction of K0 (replicable regime floor)
CONTESTABILITY_CHI_WARN: float = 1.20           # χ below → YELLOW
CONTESTABILITY_CHI_CRIT: float = 1.00           # χ below → RED (invariant breached)
CONTESTABILITY_PHI_FLOOR: float = 0.10          # minimum commonized fraction at ε=0
CONTESTABILITY_PHI_EXPONENT: float = 1.5        # power for φ(ε) = floor + (1−floor) × ε^n
CONTESTABILITY_G_PRIV: float = 0.03             # assumed private capital growth rate per unit ε
CONTESTABILITY_CAPITAL_YIELD_RATE: float = 0.10 # automated-capital annual yield rate assumption
CONTESTABILITY_VESTING_YEARS: float = 5.0       # years of FEDERATION tenure for the Trust dividend to fully
                                                # vest (linear vesting; calibration knob — matches the 5-year
                                                # tier-reassessment cadence, TIER_ASSESSMENT_INTERVAL_YEARS).
                                                # Tenure is federation-wide (recon. §8.7b): moving between
                                                # collectives never resets the clock or forfeits vested balance.

# ---------------------------------------------------------------------------
# Coasean collective federation (reconciliation §§6–7; research/coasean.py)
# Proposed functional forms — not calibrated from data. Treat as working
# hypotheses pending institutional study.
# ---------------------------------------------------------------------------
COASEAN_N_MAX: int = 20            # collective count at ε=0 (maximally fragmented)
COASEAN_BOUNDARY_EXPONENT: float = 1.0   # exponent in N(ε) = max(1, round(N_max×(1−ε)^exp))
COASEAN_RESERVE_FRACTION: float = 0.10  # fraction of TEH created held in inter-collective reserve
COASEAN_IMBALANCE_CEILING: float = 0.50  # bilateral net-flow ceiling as fraction of the deficit
                                         # collective's reserve; beyond it settlement is required
                                         # (paper's bilateral-imbalance-ceiling sketch, recon. §9-item-4)
COASEAN_DEPRECIATION_SLOPE: float = 0.20 # exchange-rate depreciation per unit of unsettled imbalance
                                         # beyond the ceiling (relative to reserve) — over-issuance
                                         # exports depreciation honestly (recon. §7 transition regime)

# ---------------------------------------------------------------------------
# Federation commons tier (reconciliation §8.7 a/c; research/coasean.py Phase 4)
# Calibration knobs with cooperative-law precedent, not physics.
# ---------------------------------------------------------------------------
COASEAN_COMMONS_TITHE: float = 0.03      # fraction of each collective's common-fund levy revenue passed
                                         # up to the federation commons. Precedent: Italian Law 59/1992
                                         # requires co-ops to contribute 3% of surplus to mutual funds.
COASEAN_INDIVISIBLE_RESERVE_FRACTION: float = 0.30
                                         # unallocated (indivisible) share of a collective's trust —
                                         # credited to no individual capital account; escheats to the
                                         # federation commons on merger/split/dissolution (recon. §8.7c).
                                         # Precedent: Italian co-op law's statutory ~30% indivisible
                                         # reserve. The allocated remainder follows members' accounts.

# ---------------------------------------------------------------------------
# Federation contestability closure (proposed §8.8; research/contestability.py
# entry_underwriting + commons dividend). Calibration knobs, not physics —
# both are uncalibrated research placeholders and say so.
# ---------------------------------------------------------------------------
CONTESTABILITY_MIN_VIABLE_POPULATION: float = 5_000.0
                                         # smallest population that can staff a viable alternative
                                         # collective: run the four-domain EOH pipeline (care,
                                         # production, stewardship, knowledge) with a full age
                                         # distribution and a governance quorum. UNCALIBRATED research
                                         # placeholder — deliberately far below the Coasean-efficient
                                         # size at any ε: a viable alternative need only clear minimum
                                         # scale, accepting a coordination-cost disadvantage; requiring
                                         # Coasean-optimal scale would make the entry threat vacuous at
                                         # high ε (the "alternative" would be the whole economy).
CONTESTABILITY_UNDERWRITE_FRACTION: float = 0.50
                                         # maximum share of the federation commons deployable per
                                         # period as entry underwriting (capitalizing new collectives'
                                         # trusts). The remainder is reserved as the sufficiency-floor
                                         # backstop (recon. §8.7a) — underwriting must never empty the
                                         # fund that backs the floor. Underwritten capital moves
                                         # commons → new collective trust: it stays commonized and
                                         # indivisible (§8.7c), never becoming a personal claim.

# ---------------------------------------------------------------------------
# Recalibration prototype (proposed §8.9; research/recalibration.py).
# Mutually-consistent K(ε)/T(ε) accounting: the commons OWNS share φ(ε) of a
# capital stock that grows with machine output, so τ = φ ≤ 1 by construction
# and dτ/dε ≥ 0 (Piketty inversion) is structural, not levy-contingent.
# Adopted-in-principle by the author 2026-07-26; calibration knobs flagged.
# ---------------------------------------------------------------------------
RECAL_CAPITAL_OUTPUT_RATIO: float = 4.0  # ν: capital stock required per unit of annual machine output
                                         # (K_machine = ν·Y_machine). Precedent: Piketty's β (national
                                         # capital / national income) ≈ 4–6 across observed economies;
                                         # low end chosen as the adversarially-cheap-capital posture
                                         # (smaller K → smaller commons → weaker underwriting arm).
RECAL_EPSILON_RATE_PER_YEAR: float = 0.02
                                         # arc speed dε/dt: a ~50-year subsistence→post-scarcity
                                         # transition. UNCALIBRATED placeholder — converts per-ε
                                         # capital-acquisition needs into per-year flows; faster arcs
                                         # tighten acquisition feasibility linearly.
RECAL_FOUNDING_LABOR_HOURS: float = 1_000.0
                                         # hours/yr a floor-backed founder can devote to building an
                                         # alternative collective (≈ 2/3 of PERSONAL_EOH_BASE, leaving
                                         # the rest for personal EOH). The sufficiency floor is what
                                         # makes this labor available — the floor IS the entry finance
                                         # of the low-ε arc. UNCALIBRATED placeholder.
RECAL_EXIT_HORIZON_YEARS: float = 5.0    # exit must be self-financeable within one vesting period
                                         # (= CONTESTABILITY_VESTING_YEARS): a member who joins can
                                         # accumulate the means to leave by the time they fully vest.
                                         # This is the RC4 fix — a stock target (K_entry) against a
                                         # flow (savable income) yields a TIME, not a ratio; the old
                                         # χ = P/K_entry demanded the stock be covered by ONE year of
                                         # flow, which made the invariant nearly unclosable (§8.8 RC4).
RECAL_ACCOUNT_CREDIT_SHARE: float = 0.50 # share of the annual per-capita dividend credited to the
                                         # member's individual capital account (a stock, per §8.7b)
                                         # rather than paid as cash. Zero-interest per Condition III:
                                         # the account is a sum of credits, never compounded.
                                         # Precedent: Mondragon internal capital accounts, which
                                         # retain a share of each year's surplus to member accounts.

# ---------------------------------------------------------------------------
# §8.9b charter-formation doctrine (research/recalibration.py phi_policy).
# The commons' share attaches to NEW capital at commissioning (charter
# condition; resource-license/Georgist model) — never by forced sale of
# existing holdings. Escalation converts private capital generationally,
# extending the existing D5 estate treatment to capital.
# ---------------------------------------------------------------------------
RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE: float = 0.15
                                         # share of a decedent's private CAPITAL escheating to the
                                         # commons (= ESTATE_LEVY_FRACTION: capital estates treated
                                         # exactly like TEH estates — the D5 doctrine extended, not
                                         # a new rule). Applies in the dilution/escalated policies.
RECAL_ESCALATION_ESTATE_SHARE: float = 1.0
                                         # capital-estate escheat share while a charter escalation is
                                         # active: full generational conversion (no living holder is
                                         # ever divested; conversion happens at mortality speed).
RECAL_ESCALATION_CAPACITY_FLOOR: float = 10.0
                                         # entry-underwriting capacity below which the charter
                                         # escalates (with the adversarial regime observed): the
                                         # commons must always be able to finance ~an order of
                                         # magnitude more foundings than one. Calibration knob,
                                         # UNCALIBRATED placeholder.

# ---------------------------------------------------------------------------
# §8.9c formation feedback (research/formation.py). Models who actually
# builds K(ε) under the charter share — the investment-disincentive loop the
# static §8.9b model flagged as open. Proposed forms, flagged.
# ---------------------------------------------------------------------------
FORMATION_DEPRECIATION_RATE: float = 0.05
                                         # aggregate annual depreciation of machine capital.
                                         # Derived from CAPITAL_MACHINE_PROFILES design lives
                                         # (≈ 20 yr → δ ≈ 1/20); the aggregate counterpart of the
                                         # per-asset lifecycle in core/capital.py. Gross return on
                                         # capital = 1/ν − δ = 0.25 − 0.05 = 0.20 at defaults.
FORMATION_HURDLE_RATE_MIN: float = 0.02
                                         # net private return below which NO private capital
                                         # formation occurs. Low BECAUSE of Condition III: idle TEH
                                         # earns zero interest and leaks via the accumulation
                                         # ceiling (D6) and estate dissolution (D5), so the
                                         # opportunity cost of investing is uniquely small —
                                         # ≈ risk compensation only. UNCALIBRATED placeholder.
FORMATION_FULL_SUPPLY_RATE: float = 0.10
                                         # net private return at (or above) which private investors
                                         # supply ALL needed formation. Linear supply between the
                                         # two rates (heterogeneous hurdle rates). Implies the
                                         # incentive-compatible charter share
                                         # s* = 1 − 0.10/0.20 = 0.50. UNCALIBRATED placeholder.

# ---------------------------------------------------------------------------
# Membership-terms audit thresholds (reconciliation §8.7e, §9-item-7;
# research/membership.py). Terms are contract space; these bound it — the
# code audits agreements against the contestability invariant, it does not
# legislate them.
# ---------------------------------------------------------------------------
MEMBERSHIP_VESTING_WARN_YEARS: float = 10.0     # vesting beyond 2× CONTESTABILITY_VESTING_YEARS → WARN
                                                # (dividend held hostage for a decade thins exit)
MEMBERSHIP_EXIT_NOTICE_WARN_YEARS: float = 1.0  # exit notice beyond one year → WARN (exit friction)
MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS: float = 3.0  # beyond three years → CRIT (exit is nominal, not substantive)
MEMBERSHIP_MIN_HOURS_WARN_FRACTION: float = 0.50  # min-hours obligation > 0.50 × PERSONAL_EOH_BASE → WARN
MEMBERSHIP_MIN_HOURS_CRIT_FRACTION: float = 1.00  # ≥ full personal EOH load → CRIT (membership is compulsion
                                                  # by definition — obligation equals the whole entropy load)
MEMBERSHIP_DIVIDEND_POLICY_WARN: float = 0.25   # distributing < 25% of the pro-rata dividend → WARN
                                                # (retention rebuilds the honeypot inside the collective)

# ---------------------------------------------------------------------------
# Thermal Sink EOH — planetary radiative capacity (research/thermal.py, P0)
#
# The uncounted vector: all degraded energy must exit through thermal emission
# to space, and that capacity is fixed and non-restorable by labor. See
# handoffs/Thermal_Sink_EOH_Implementation_Handoff_1_0.md. P0 / finding F2 is the
# provable ceiling bound (E29): the highest automation ε the thermal budget
# permits, computable from constants + existing inventory with NO new measurement.
#
# Two tiers of provenance, kept explicit:
#   - the budget chain (A_EARTH, σ_SB, seconds/year) is physics/measured;
#   - the assessed climate inputs (λ, F_GHG, ΔT_lo) and the thermodynamic floors
#     ι_floor are CHOSEN placeholders — the gating uncertainty. A floor-based
#     bound can only OVERSTATE ε_max (real ι ≥ ι_floor), so a floor bound < 1 is
#     conclusive (F2); a floor bound ≥ 1 is inconclusive and needs the measured
#     ι ladder (handoff §13.1 path C/B), not a constant change here.
# ---------------------------------------------------------------------------
A_EARTH_M2: float = 5.101e14        # Earth surface area, m² (physics)
SIGMA_SB: float = 5.670374419e-8    # Stefan–Boltzmann constant, W·m⁻²·K⁻⁴ (physics)
SECONDS_PER_YEAR: float = 3.155760e7  # Δt_s for one year (physics)

# Assessed climate inputs — CHOSEN placeholders (Guardrail I: measured, published
# with uncertainty, never negotiated). Values are for scaffolding only.
THERMAL_LAMBDA_FEEDBACK: float = 1.2   # W·m⁻²·K⁻¹ EQUILIBRIUM climate feedback parameter;
                                       # Planck-only ≈ 3.2. Value unchanged, but its POSITION is
                                       # now derived rather than assumed (2026-08-05,
                                       # research/thermal_lambda.py + reference/data/
                                       # climate_feedback.json): it sits below the AR6-implied
                                       # 1.310 (ECS 3.0 K) and the historical energy-budget
                                       # estimate 1.492 derived from the shipped IGCC series.
                                       # Both directions matter — a LOWER λ means a SMALLER
                                       # budget and a LARGER obligation, so 1.2 is the
                                       # conservative side and was not flattering the result.
                                       # FRAME DISCIPLINE: this is the EQUILIBRIUM λ and pairs
                                       # only with the equilibrium budget λ·ΔT−F. The historical
                                       # 1.492 pairs with a transient reading the framework
                                       # rejects; mixing them inflates the allowance ~6×, and
                                       # thermal_lambda.budget_forcing_headroom refuses it.
                                       # SENSITIVITY IS FIRST-CLASS: across AR6's likely ECS
                                       # range the budget runs from ZERO (ECS 5 K) to ~11× the
                                       # shipped case. Never publish a ψ*-derived figure without
                                       # λ and that band.
                                       # BEST GUESS, and it stays one (checked 2026-08-05):
                                       # λ_equilibrium CANNOT be assessed from the shipped data.
                                       # Two independent estimators of the HISTORICAL feedback
                                       # agree — 1.492 (ratio) and 1.693 ± 0.472 (regression,
                                       # 53 yr) — but converting historical to equilibrium needs
                                       # the pattern effect, which requires pattern-forced model
                                       # experiments or paleoclimate constraints. Neither is
                                       # derivable from ERF, EEI and GMST.
                                       # resolves_by: an assessed ECS with uncertainty — an
                                       # EXTERNAL input, not a rearrangement of what we hold.
THERMAL_F_GHG: float = 3.0             # W·m⁻² anthropogenic well-mixed GHG forcing (order of AR6).
                                       # Epistemic pointer: greenhouse forcing assessment.
THERMAL_F_ALB: float = 0.0             # W·m⁻² net anthropogenic albedo forcing; 0 default.
THERMAL_DT_LO: float = 2.0             # K assessed habitability threshold. **CHOSEN — the single
                                       # most leveraged input in the whole thermal layer.** It sets
                                       # the overage, the drawdown job and the obligation, and it is
                                       # the framework's own judgment rather than a measurement.
                                       # 2.0 K is adopted because it keeps results stable and lands
                                       # inside the indeterminate band, NOT because it is assessed;
                                       # it may well be judged too HIGH later, and every downward
                                       # revision enlarges the obligation (1.5 K is ~1.5× the job).
                                       # Assess in land extremes and convert by ÷THERMAL_TXX_PER_GMST
                                       # per C6. Epistemic pointer: a habitability assessment naming
                                       # the variable that actually binds, not a GMST round number.
THERMAL_COMMONS_RESERVE: float = 0.20  # r — fraction of budget held in reserve; ratcheted down only.
THERMAL_ANTHROPOGENIC_DISSIPATION_W: float = 2.0e13  # present Φ_other reference, W (~0.04 W·m⁻²).
                                                     # Epistemic pointer: energy-balance inventory.

# Thermodynamic floors ι_floor,d (J per EOH fulfilled) — CHOSEN placeholders.
# The per-domain minimum joules to fulfill one EOH by machine (E27). Ordering
# reflects the handoff: personal/infrastructure carry real caloric/enthalpy
# floors; knowledge's Landauer floor is astronomically lower (F6). ONE EOH is one
# hour of entropy-obligation-equivalent; the J/EOH mapping is the open quantity.
# Epistemic pointer: Landauer (knowledge), Carnot/enthalpy minima (infrastructure),
# caloric + heat-rejection COP (personal) — handoff §7.3 iota_floor().
THERMAL_IOTA_FLOOR_PERSONAL: float = 3.6e5        # J/EOH ≈ 100 W over one hour (metabolic-order floor)
THERMAL_IOTA_FLOOR_INFRASTRUCTURE: float = 3.6e5  # J/EOH — enthalpy/Carnot minimum, placeholder = personal order
THERMAL_IOTA_FLOOR_ECOLOGICAL: float = 3.6e4      # J/EOH — stewardship, order below personal, placeholder
THERMAL_IOTA_FLOOR_KNOWLEDGE: float = 1.0e-6      # J/EOH — Landauer-order; astronomically low (F6)

# ---------------------------------------------------------------------------
# Thermal Sink — Path C measured inputs (research/thermal_path_c.py)
#
# The measured top-down thermal residual (Eq. C1). Where P0 used thermodynamic
# floors, Path C uses published energy statistics + measured forcing, and the
# operative formula ε_max = ε_current · allocated_budget / Φ_auto needs NO EOH
# register (ι and EOH_total cancel). Measured energy mix, κ table, national
# records and their provenance tiers live in the shipped dataset
# reference/data/thermal_path_c.json — not here (that is data, with provenance).
# These are the structural constants the measured module needs beyond the P0 set.
# ---------------------------------------------------------------------------
A_LAND_CLAIMED_M2: float = 1.35e14     # land area ex-Antarctica, m² (geographic; the
                                       # denominator for land-allocated ψ*). Physics/geographic.
# Forcing — correction C5 (handoff 2.0 §2, applied 2026-08-03). The prior values
# were AR6 2019-baseline Tier C; these are measured IGCC 2025a, verified this
# session against the shipped synthesis timeseries (`total`/`anthro`/`wmghg`
# columns, time = 2025). Tier A. The recalled 2.72 was right for the wrong year.
#
# C4 governs WHICH column: the BUDGET uses `total`, not `anthro` — natural forcing
# consumes the habitability allowance regardless of cause. `anthro` is carried
# separately because the decarbonization GAIN (F3) is a different question: only
# the anthropogenic part is removable by labor. See research/thermal.py F3.
THERMAL_F_NET_ERF: float = 3.366       # W·m⁻² TOTAL ERF, IGCC 2025a p50, time=2025. Tier A.
THERMAL_F_NET_ERF_P05: float = 2.602   # W·m⁻² total ERF p05 — the determinacy band's lower edge.
THERMAL_F_NET_ERF_P95: float = 4.102   # W·m⁻² total ERF p95 — the determinacy band's upper edge.
THERMAL_F_ANTHRO_ERF: float = 3.104    # W·m⁻² anthropogenic ERF alone (incl. aerosol cooling) —
                                       # the REMOVABLE forcing, hence the honest F3 basis. Tier A.
THERMAL_F_WMGHG_ERF: float = 3.585     # W·m⁻² well-mixed GHG ERF alone (the forward-looking basis as
                                       # aerosol cooling declines). IGCC 2025a `wmghg`. Tier A.
# Drawdown chain (research/thermal_drawdown.py) — converting a forcing reduction
# into the labor that would deliver it. Each step is separately tiered so the
# gate's sensitivity lands on named quantities rather than one lumped constant.
CO2_FORCING_COEFFICIENT: float = 5.645  # W·m⁻² per ln(C/C₀). Tier A — DERIVED this
                                       # session by OLS of the IGCC 2025a CO₂ ERF series on
                                       # ln(concentration) over 350–426 ppm (n=38), the range a
                                       # drawdown actually traverses. Self-validating: the fitted
                                       # intercept implies C₀ = 279.8 ppm against the accepted
                                       # pre-industrial 278. Myhre's classic 5.35 runs 5.2% low here.
CO2_CONCENTRATION_PPM: float = 425.65  # ppm, IGCC 2025a annual mean at 2025. Tier A.
CO2_PPM_TO_GT: float = 7.82            # GtCO₂ per ppm. Tier B — atmospheric mass 5.148e18 kg
                                       # × 1e-6 × (44.01/28.96 molar ratio). Derivable, not fitted.
CDR_GROSS_REMOVAL_FACTOR: float = 1.8  # Removing CO₂ from the air lets ocean/land sinks OUTGAS
                                       # back, so the gross tonnage exceeds the concentration
                                       # drop. Tier D placeholder. resolves_by: ESM CDR
                                       # reversibility experiments (Zickfeld et al.). Omitting it
                                       # would understate the obligation ~2× and bias the
                                       # solvency gate toward passing — exactly the wrong error.
CDR_ENERGY_GJ_PER_TONNE: float = 4.0   # GJ per tonne CO₂ removed. Tier C — DAC-order, recalled
                                       # range 2–6. resolves_by: published plant LCA.
THERMAL_PROGRAMME_YEARS: float = 40.0  # Years over which the drawdown obligation is discharged.
                                       # **CHOSEN.** 40 yr keeps the programme inside a single
                                       # lifetime of responsibility: the generation that incurred
                                       # the debt discharges it, rather than booking the benefit and
                                       # willing the work to people who did not choose it. The
                                       # obligation scales as 1/horizon, so this is a real lever —
                                       # 30 yr is 1.33× the annual load, 100 yr is 0.4×. Epistemic
                                       # pointer: this is an ETHICAL choice about who bears the
                                       # work, not a technical one, and it should be argued as such.
CDR_ALLOCATION_BASIS: str = "responsibility"  # How the global job is split across collectives.
                                       # **CHOSEN, and a governance decision, not physics.**
                                       # "responsibility" (cumulative emissions) over "population"
                                       # because a collective cannot burden others with the
                                       # consequences of choices it made. See allocation_share().
CDR_RESPONSIBILITY_BASIS: str = "incl_luc"  # Which cumulative-CO₂ measure weights
                                       # responsibility: "incl_luc" (fossil + cement +
                                       # land-use change — the whole atmospheric burden the
                                       # drawdown must remove, and the basis matching the
                                       # forcing coefficient, which was fitted to a
                                       # concentration record that already reflects land use)
                                       # or "fossil" (lower uncertainty, but leaves ~33% of
                                       # the burden unallocated). **CHOSEN, and a live equity
                                       # question**: including land use moves substantial
                                       # burden onto collectives that were often converting
                                       # land under external demand, and the framework cannot
                                       # yet trade-adjust — OWID consumption-based emissions
                                       # begin only in 1990, far too short for a cumulative
                                       # measure. Sign-off item.
ETA_BASIS: str = "clear_sky"           # Which radiative-efficiency field weights a
                                       # collective's land allocation: "clear_sky" (default)
                                       # or "all_sky". **CHOSEN 2026-08-05.** All-sky η
                                       # credits a collective for being cloudy — cloud cover
                                       # is not a policy lever, is partly endogenous to
                                       # warming, and is the noisiest part of the field, so an
                                       # all-sky rule rewards weather. Clear-sky measures the
                                       # structural radiative transparency of the column,
                                       # which is what "this land's share of the sink" should
                                       # mean. The choice is not cosmetic: the two differ by
                                       # up to 0.27 in η (RMS 0.051, p95 0.085), so all-sky is
                                       # reported alongside as the physical reality check and
                                       # the per-collective gap must stay visible.
ETA_LAND_MASK_THRESHOLD: float = 0.50  # lsm ≥ this counts as land (§5 decision 1: territorial
                                       # sea excluded). Measured; ERA5 lsm is a fraction.
CDR_UNATTRIBUTED_POLICY: str = "pro_rata"  # What happens to emissions belonging to no
                                       # territory — international shipping and aviation,
                                       # 46 GtCO₂ / 2.49% of the cumulative fossil total.
                                       # "pro_rata" (default): redistribute across
                                       # collectives in proportion to their existing shares,
                                       # so shares sum to 1 and no part of the obligation is
                                       # left without a bearer. We all inherited the world as
                                       # it is. "unallocated": leave the gap open, which
                                       # means the commons silently absorbs it.
                                       # resolves_by: consumption-based allocation, once
                                       # trade data supports it — OWID's begins in 1990, and
                                       # 1990-forward is where the framework will start when
                                       # it does. CHOSEN.
CDR_LABOR_HOURS_PER_TONNE: float = 0.6 # Labor-hours per tonne removed. Tier D — a ~1 Mt/yr plant
                                       # at ~300 staff × 2000 h. resolves_by: operator staffing
                                       # disclosures. Together with the line above this DERIVES
                                       # ι_drawdown = (GJ/t)/(h/t) ≈ 6.7e9 J/EOH, so the framework's
                                       # ι is a function of two plant observables rather than a
                                       # third free placeholder. ~4 orders above the infrastructure
                                       # ι floor, as expected: drawdown is energy-intensive and
                                       # labor-thin.
THERMAL_F_NATURAL_ERF: float = 0.262   # W·m⁻² solar + volcanic ERF at 2025, IGCC 2025a `natural`.
                                       # Tier A. Consumes budget (C4) but is NOT removable by labor —
                                       # so it is the floor on achievable forcing, and the wedge
                                       # between the budget basis and the F3 gain basis (§10.1).
THERMAL_GMST_OBSERVED: float = 1.23    # K observed GMST anomaly, 2015–2024 mean (IGCC 2025a). Tier A.
                                       # Paired with the committed F/λ to expose the pipeline: the
                                       # warming already bought and not yet delivered (§10.3).
THERMAL_TXX_PER_GMST: float = 1.48     # dTXx/dGMST — land extreme amplification (C6). Measured this
                                       # session: OLS on the ERA5/Berkeley/HadEX3 mean TXx series vs
                                       # GMST, 1950–2025, n=76, slope 1.483. Per-dataset spread
                                       # 1.33–1.57 is the honest uncertainty. Tier A; Guardrail I
                                       # quantity — refresh annually.
THERMAL_U_FLOOR: float = 0.50          # utilization boundary for Standing-exposure regime. CHOSEN;
                                       # resolves_by: observed variance in Φ and ψ*, not a chosen value.
THERMAL_EPS_CURRENT: float = 0.40      # framework current-equilibrium ε for Eq. C1. CHOSEN (= arc midpoint).

# ---------------------------------------------------------------------------
# Capital thermal profiles — the §12.2 dual-output overlay (research/thermal_capital.py)
#
# The thermal handoff §12.2 makes infrastructure/capital DUAL-OUTPUT: the same
# capital inventory that eliminates EOH (CAPITAL_MACHINE_PROFILES) also dissipates
# heat. These are the two new physical fields per capital type — net operational
# power draw and embodied energy per unit capacity — that turn a capital stock
# into a thermal load Φ_auto. (The third §12.2 field, reliable service life, is
# already `design_life` in CAPITAL_MACHINE_PROFILES; the fourth, physical grid
# mix, is a COLLECTIVE property — κ applies to the grid serving the capital,
# §8.1 — so it is a derivation input, not a per-type field.)
#
# Kept as a SEPARATE parallel dict, not merged into CAPITAL_MACHINE_PROFILES:
# these are CHOSEN placeholders (research-tier, sign-off-gated ε-vector context),
# and separating them keeps the established EOH capital model visibly distinct
# from the experimental thermal overlay.
#
#   power_intensity_w_per_teh:  operational net power draw, W per TEH of capital.
#   embodied_energy_j_per_teh:  embodied (manufacturing) energy, J per TEH; the
#                               derivation amortizes it over design_life.
#
# Epistemic pointers (all CHOSEN — the calibration debts): power intensity ←
# measured energy-use intensity by capital class (IEA end-use / sectoral energy
# balances); embodied energy ← LCA inventories (ecoinvent, EPDs). Relative
# ordering is defensible (compute/industry heavy; software/monitoring light); the
# absolute scale is anchored only to order-of-consistency with Path C's measured
# ~2200 W·person⁻¹ net-additive dissipation, NOT fitted.
# ---------------------------------------------------------------------------
CAPITAL_THERMAL_PROFILES: dict[str, dict] = {
    "power_grid":               {"power_intensity_w_per_teh": 2.0, "embodied_energy_j_per_teh": 8.0e7},
    "water_treatment":          {"power_intensity_w_per_teh": 0.8, "embodied_energy_j_per_teh": 5.0e7},
    "medical_systems":          {"power_intensity_w_per_teh": 1.5, "embodied_energy_j_per_teh": 6.0e7},
    "agricultural_automation":  {"power_intensity_w_per_teh": 1.2, "embodied_energy_j_per_teh": 4.0e7},
    "environmental_monitoring": {"power_intensity_w_per_teh": 0.3, "embodied_energy_j_per_teh": 3.0e7},
    "industrial_automation":    {"power_intensity_w_per_teh": 4.0, "embodied_energy_j_per_teh": 1.0e8},
    "transportation":           {"power_intensity_w_per_teh": 3.0, "embodied_energy_j_per_teh": 9.0e7},
    "computing_ai":             {"power_intensity_w_per_teh": 8.0, "embodied_energy_j_per_teh": 1.2e8},
    "software":                 {"power_intensity_w_per_teh": 0.5, "embodied_energy_j_per_teh": 2.0e7},
    "building":                 {"power_intensity_w_per_teh": 0.6, "embodied_energy_j_per_teh": 1.5e8},
    "generic_infra":            {"power_intensity_w_per_teh": 1.0, "embodied_energy_j_per_teh": 8.0e7},
}

# Net thermal addition coefficient κ̄ of the grid serving the capital (§8.1). Default
# = world fossil+nuclear share (Path C, 2025). A fully flux-redirecting grid → 0.
THERMAL_GRID_KAPPA_DEFAULT: float = 0.93  # CHOSEN/measured; resolves_by: physical grid mix, not procurement.
