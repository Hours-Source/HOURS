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
# ---------------------------------------------------------------------------
PERSONAL_EOH_BASE: float   = 1500.0     # hours/year per working-age-equivalent
INFRA_MAINT_RATE: float    = 0.025      # fraction of capital stock = EOH/year
INFRA_AGE_FACTOR_MAX: float = 2.0      # multiplier at end of design life
ECOLOGICAL_BASE_RATE: float = 500_000.0 # hours/year at pristine ecosystem health
ECOLOGICAL_THRESHOLD: float = 0.40     # below this → nonlinear spike
KNOWLEDGE_EOH_BASE: float  = 100_000.0  # baseline knowledge EOH at ε=0
KNOWLEDGE_EPS_EXPONENT: float = 2.0    # how steeply knowledge EOH grows with ε

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
BASKET_EOH_CONTENT:           float = 1500.0            # personal EOH hours satisfied per sufficiency basket (= PERSONAL_EOH_BASE)

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
GUF_USE_RESIDENTIAL_PRIMARY:    float =  0.100
GUF_USE_RESIDENTIAL_SECONDARY:  float =  0.215
GUF_USE_AGRICULTURAL_ACTIVE:    float =  0.020
GUF_USE_AGRICULTURAL_FALLOW:    float =  0.050
GUF_USE_COMMERCIAL_RETAIL:      float =  0.300
GUF_USE_COMMERCIAL_OFFICE:      float =  0.225
GUF_USE_INDUSTRIAL_LIGHT:       float =  0.170
GUF_USE_INDUSTRIAL_HEAVY:       float =  0.375
GUF_USE_INSTITUTIONAL:          float =  0.010
GUF_USE_CONSERVATION_CREDIT:    float = -0.060  # negative: credit reduces base fee

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
