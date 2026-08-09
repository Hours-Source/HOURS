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
# provenance-block: EOH generation — personal domain
# tag: CHOSEN | units: relative eoh_weight (working_age = 1.0) and population fractions
# form: the DIRECTION is structural — infants and elderly draw more caregiver
#   labour than working-age adults. The 3.0 / 1.5 / 1.0 / 2.5 magnitudes and
#   the 7/16/60/17 split are not.
# note: the age-weighted mean w = Σ(fraction × weight) = 1.475 is the bridge
#   from per-working-age-EQUIVALENT to per-capita, and forgetting it is the
#   age-weight trap scenarios/feasibility.py exists to catch.
# resolves_by: ATUS "caring for and helping household children/adults" hours
#   per care-recipient by recipient age, plus NHATS/HRS for hours of
#   assistance to older adults with functional limitation; national census or
#   UN WPP for the fractions. ATUS is now partly ingested
#   (reference/atus_time_use.py) but has not been cut by care-recipient age,
#   which is the cut this constant needs.
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
# provenance-block: Capital and asset lifecycle
# tag: CHOSEN | units: maint_rate fraction of capital/yr; threshold_age years; compound_exp dimensionless
# form: physics — post-threshold maintenance escalates as a power law rather
#   than linearly, and the ORDERING across asset classes (software fastest to
#   fail, stone slowest) is a defensible engineering claim. The exponents are
#   not.
# resolves_by: measured maintenance and failure curves by asset class. The
#   infrastructure floor shows the route — a physical condition census in
#   crew-hours rather than money (INFRA_TREATMENT_HOURS_*). Design lives here
#   are order-of-magnitude right; nothing measures the compounding exponents.
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
# tag: CHOSEN | units: EOH eliminated per TEH of capital per year; TEH per capita; years; condition ∈ [0,1]
# note: CALIBRATED TO A TARGET, on its own admission — the tiers were set so
#   that "standard" across all types totals ~2000 TEH/person (matching
#   CAPITAL_STOCK_DEFAULT) and implies ε ≈ 0.18, with "advanced" implying ε ≈
#   0.48, so the table brackets the mid-arc by construction. That makes ε
#   emergent from a capital stock whose profile was chosen to produce the ε
#   expected of it. The circularity is documented, not resolved.
# resolves_by: measured EOH-elimination rates per capital class — the
#   labour-hours a unit of each capital type actually displaces per year. This
#   is the same instrument the food conservation test used at one stage
#   (scenarios/food_conservation.py found a 62× collapse in production
#   labour), so the method is proven and the coverage is what is missing. Note
#   research/thermal_capital.py already treats the same inventory as
#   dual-output; a measured pass should settle both fields at once.
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
# tag: CHOSEN | units: fraction of condition (slope over full design life; floor level) | family: COND_DECAY_*
# form: linear decay to a floor. Physics in one respect — an end-of-life asset
#   is degraded but still operational, so the floor must be above zero (full
#   write-down is a separate explicit event via execute_writedown). The
#   linearity is a simplification; real condition curves are convex.
# resolves_by: measured condition ratings against age by asset class. Bridge
#   inventories publish exactly this (the NBIS condition data behind
#   INFRA_TREATMENT_HOURS_* is the same source), so this is reconcilable
#   against data the repo already reaches for elsewhere.
COND_DECAY_SLOPE: float = 0.70   # fractional condition lost over full design life
COND_DECAY_FLOOR: float = 0.30   # minimum condition for an asset still in service

# Environmental monitoring saturation constant: at this many TEH per capita
# of environmental_monitoring capital, monitoring_capability reaches 1.0.
# Below this, capability scales linearly above CANONICAL_MONITORING_CAPABILITY_BASE.
# tag: CHOSEN | units: TEH per capita of environmental-monitoring capital
# resolves_by: an observed relationship between monitoring investment and
#   detected fraction of ecological deferral. This constant governs how much
#   deferred ecological EOH is VISIBLE, so it sets what the ledger can see
#   rather than what is there — the honest pointer is a detection-rate study,
#   and until then monitoring capability is an assumption about the
#   framework's own eyesight.
ENV_MONITORING_SATURATION_TEH_PER_CAPITA: float = 500.0

# ---------------------------------------------------------------------------
# Essential domains for Condition IV (Distributed Competency)
# Mission Statement: §"Condition IV" — agriculture, construction, energy,
# water, healthcare, manufacturing, and logistics.
# ---------------------------------------------------------------------------
# provenance-block: Labor and Condition IV
# tag: CHOSEN | units: list of domain names
# form: physics-adjacent — a civilization does have a set of functions whose
#   failure is not survivable, so the CATEGORY is structural. Which seven, and
#   the fact that there are seven, is not.
# resolves_by: a criticality analysis for the jurisdiction being modelled —
#   national critical-infrastructure sector designations are the nearest
#   external analogue, and they do not agree with each other on the list
#   either.
ESSENTIAL_DOMAINS: list[str] = [
    "agriculture", "construction", "energy", "water",
    "healthcare", "manufacturing", "logistics",
]
# tag: CHOSEN | units: fraction of workforce certified per essential domain
# resolves_by: an observed relationship between practitioner density and
#   recovery time from a domain outage. The Mission Statement asserts 15.5%;
#   the three significant figures imply a precision nothing supplies, which is
#   itself the tell. Workforce composition series plus outage post-mortems
#   would settle it.
COMPETENCY_THRESHOLD: float = 0.155  # 15.5% of workforce, per Mission Statement

# Minimum annual labor obligation supporting Condition IV
# tag: CHOSEN | units: hours per year
# form: 5 h/wk × 52 wk. Below some floor a practitioner stops maintaining
#   competency, which is structural; the level is the choice.
# resolves_by: measured skill-retention against practice hours by domain — the
#   currency-of-practice literature in aviation and surgery measures exactly
#   this and reports domain-specific thresholds, which is the point: one
#   economy-wide 260 cannot be right for both a surgeon and a farmhand.
H_MIN: int = 260  # hours/year
# tag: CHOSEN | units: fractions of H_MIN, summing to 1.0
# resolves_by: a charter decision on how the minimum obligation is
#   apportioned. The three-way split is a policy design; nothing measures it.
H_MIN_ALLOCATION: dict[str, float] = {
    "competency_rotation": 0.40,  # 40% → essential domain practice
    "stewardship_service": 0.30,  # 30% → stewardship labor
    "regular_employment":  0.30,  # 30% → normal work
}

# ---------------------------------------------------------------------------
# Multiplier band (Condition II)
# Mission Statement: §"Condition II — Multiplier Band"
#
# RETAGGED 2026-08-09. These carried `Physics` in docs/parameter_provenance.md,
# justified there by statements like "below 1.8 the differential between labor
# tiers is too small to reflect real skill differentials". That is an argument
# about fairness and legitimacy, not about how entropy works — it is a
# CONSTITUTIONAL commitment, which is the strongest possible reason to hold it and
# no reason at all to call it physics. Under this scheme's own definition (physics
# "needs a theoretical justification, not a knob") they are CHOSEN, and their
# epistemic pointer is a charter decision.
#
# The band is also the load-bearing surface of the skill-differential wound in
# notes/historical-autopsy.md, so mislabelling it as physics hid the one number
# most in need of argument.
# ---------------------------------------------------------------------------
# provenance-block: Multipliers — constitutional band (Condition II)
# tag: CHOSEN | units: dimensionless multiplier | family: M_BAND_*
# form: physics-adjacent in one respect only — a band must EXIST for Condition
#   II to be checkable. Where its edges sit is not implied by that.
# resolves_by: a charter decision on the tolerable spread of labour valuation.
#   The measured route now exists and disagrees usefully: the O*NET/BLS
#   reference multiplier (mult-5.1.0) produces a population-weighted mean from
#   measured factors, and handoffs/multipliers-v5/FALSIFIABILITY.md records
#   that the band PASS is a construction artifact of the normalization (±2.8×
#   across normalizations) with no empirical content. So the band cannot be
#   validated against the measurement — it can only be chosen and then
#   honoured.
M_BAND_LOW: float = 1.8
M_BAND_HIGH: float = 2.1
M_BAND_TARGET: float = 2.1
# tag: CHOSEN | units: dimensionless multiplier
# form: physics — a hard cap must exist, or TEH accumulation is unbounded in
#   the tier dimension. Its LEVEL is the choice.
# resolves_by: a charter decision on maximum permitted labour-valuation
#   inequality. 6.0 is a 6:1 ratio against the floor; that is the substantive
#   commitment and it should be argued as a distributional limit, not derived.
M_MAX: float = 6.0

# Multiplier — additive formula absolute scale
# When all four alpha coefficients are at their equal share, each equals
# ALPHA_SCALE / 4 = 1.25, so m(c) = 1 + Σ αᵢ·fᵢ reaches M_MAX at all-ones.
# tag: derived | units: dimensionless (sum of the four alpha coefficients)
# form: Σαᵢ = M_MAX − 1, so that perfect scores on all four factors land
#   exactly on the cap. Genuinely computed from M_MAX rather than pinned — it
#   moves when the cap moves.
# resolves_by: n/a — it inherits M_MAX's standing, which is CHOSEN. Nothing
#   additional is owed here beyond settling the cap.
ALPHA_SCALE: float = M_MAX - 1.0          # = 5.0; Σαᵢ = ALPHA_SCALE at full range

# Impact sub-question weights for compute_impact_score(); must sum to 1.0.
# tag: CHOSEN | units: fraction | family: ALPHA_IMPACT_*
# form: derived only in that the three weights are constrained to sum to 1.0.
# resolves_by: nothing measures the relative importance of EOH reduction,
#   domain breadth and reserve capacity against each other — it is a judgement
#   about what the collective values in a role. Sweep it:
#   scenarios/multiplier_sensitivity.py already provides the harness, and the
#   shipped sweep is ±0.10 per weight.
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
# provenance-block: Multipliers — measured geometric map (mult-5.1.0)
# tag: CHOSEN | units: dimensionless multiplier
# form: the constitutional floor of the geometric map — one hour of the least
#   demanding registered labour mints exactly one TEH.
# resolves_by: a charter decision on the floor. It is arguably the framework's
#   cleanest normative commitment (an hour is an hour at the floor) and needs
#   no measurement — but it is a commitment, not a measured minimum.
M_FLOOR:          float = 1.0    # constitutional floor multiplier (measured min)
# tag: derived-then-FROZEN | units: dimensionless ratio
# form: solved once at the reference epoch from {M_FLOOR, the band, the
#   measured composite distribution} so that the mapped mean lands in the
#   band.
# resolves_by: an O*NET/BLS vintage refresh re-solves it mechanically. It is
#   NOT a knob — re-deriving it per vintage restores the circularity the
#   freeze exists to break. Note the consequence recorded in
#   handoffs/multipliers-v5/ FALSIFIABILITY.md: because R is solved to make
#   the band pass, the band pass carries no empirical content. The rank
#   ordering and pairwise ratios do.
M_GEOMETRIC_R:    float = 3.2    # DERIVED-THEN-FROZEN spread ratio (solved at reference epoch)
# tag: derived-then-FROZEN | units: composite score, dimensionless | family: M_COMPOSITE_Z_*
# form: the observed composite range at the reference epoch, used to normalize
#   z = clip((composite − Z_LO)/(Z_HI − Z_LO), 0, 1).
# resolves_by: an O*NET/BLS vintage refresh. Frozen for the same reason as R.
M_COMPOSITE_Z_LO: float = 0.15307309621788462  # frozen composite lower bound
M_COMPOSITE_Z_HI: float = 0.7401986094479613   # frozen composite upper bound

# Frozen factor weights (training, demand, scarcity, impact) — CHOSEN, uncalibrated.
# Epistemic pointer: no measurement behind the split; sweep ±0.10 each (see
# scenarios/multiplier_sensitivity.py). Sum to 1.0.
# tag: CHOSEN | units: fraction
# resolves_by: no measurement stands behind the split between the four
#   assessment factors — it is what the collective decides a labour-hour's
#   value turns on. Sweep ±0.10 each; scenarios/multiplier_sensitivity.py runs
#   it and reports that rank ordering survives while absolute levels do not.
M_FACTOR_WEIGHTS: tuple[float, float, float, float] = (0.30, 0.25, 0.20, 0.25)

# Frozen impact sub-domain weights (dependency, substitutability, harm, temporal)
# — CHOSEN. Used to reconstruct f_impact from the measured i_* sub-components.
# Sum to 1.0. Impact composite is affine outer-normalized against these bounds.
# tag: CHOSEN | units: fraction
# resolves_by: as for M_FACTOR_WEIGHTS — a governance judgement, swept not
#   fitted.
M_IMPACT_SUBDOMAIN_WEIGHTS: tuple[float, float, float, float] = (0.30, 0.25, 0.25, 0.20)
# tag: derived-then-FROZEN | units: impact composite score, dimensionless | family: M_IMPACT_COMPOSITE_*
# form: the observed impact-composite range at the reference epoch; the impact
#   composite is affine outer-normalized against these bounds.
# resolves_by: an O*NET/BLS vintage refresh.
M_IMPACT_COMPOSITE_LO: float = 0.3317494225632136  # frozen impact-composite lower bound
M_IMPACT_COMPOSITE_HI: float = 0.7519582943881703  # frozen impact-composite upper bound

# Epoch-adaptive factor weights across the automation arc — CHOSEN (illustrative
# anchors, piecewise-linear interpolated). Each anchor is (training, demand,
# scarcity, impact), summing to 1.0. Epistemic pointer: the ε-dependence of the
# weighting is a governance judgement, not a measurement; the ε=0.40 anchor
# equals the frozen M_FACTOR_WEIGHTS by construction. At ε→1 impact dominates
# (copy/merge limit: only impact survives — see handoffs KNOWN_ISSUES §5).
# tag: CHOSEN | units: fraction, per ε anchor
# resolves_by: the ε-dependence of the weighting is a governance judgement,
#   not a measurement. The DIRECTION is argued (training matters less as
#   skills stop being scarce; impact matters more as fewer hours carry more
#   consequence); the four anchor vectors are illustrative.
M_EPOCH_WEIGHT_ANCHORS: dict[float, tuple[float, float, float, float]] = {
    0.00: (0.35, 0.30, 0.20, 0.15),
    0.40: (0.30, 0.25, 0.20, 0.25),
    0.90: (0.20, 0.20, 0.20, 0.40),
    0.99: (0.15, 0.15, 0.15, 0.55),
}

# Governance assessment thresholds
# provenance-block: Multiplier governance and anti-gaming safeguards
# tag: CHOSEN | units: count of assessors
# resolves_by: a charter decision on panel size. Three is the smallest panel
#   that can break a tie, which is an argument rather than a measurement;
#   sortition literature on minimum panel size for stable outcomes would
#   strengthen it.
GOVERNANCE_MIN_ASSESSORS:       int   = 3     # fewer than this triggers a WARN
# tag: CHOSEN | units: inter-rater reliability coefficient | family: GOVERNANCE_IRR_*
# form: the WARN/CRIT pair on assessment agreement.
# resolves_by: convention exists and is close at hand — these sit near the
#   established Krippendorff/Cohen κ reading (≥0.80 good, 0.67–0.80 tentative,
#   below that unreliable). Adopting a cited standard would move both to
#   `convention`; as written they are the framework's own rounder numbers.
GOVERNANCE_IRR_WARN_THRESHOLD:  float = 0.70  # inter-rater reliability below → WARN
GOVERNANCE_IRR_CRIT_THRESHOLD:  float = 0.50  # inter-rater reliability below → CRIT

# ---------------------------------------------------------------------------
# Multiplier governance: scarcity dampening (B3)
# Mission Statement: §"Scarcity — the three-year rolling average prevents
# oscillation; supply-response discount prevents over-rewarding roles where
# raising the multiplier will itself resolve the scarcity."
# ---------------------------------------------------------------------------
# tag: CHOSEN | units: periods
# form: physics-adjacent — SOME smoothing is structurally required, because
#   scarcity is endogenous to the multiplier that responds to it and an
#   unsmoothed feedback oscillates. The window LENGTH is the choice.
# resolves_by: the observed autocorrelation of occupational vacancy series.
#   BLS JOLTS measures exactly this and is not yet ingested; three periods is
#   the framework's assertion about how long the oscillation is.
SCARCITY_ROLLING_WINDOW: int = 3        # periods in rolling average
# tag: CHOSEN | units: years
# resolves_by: measured time from a wage/valuation signal to a completed
#   training pipeline, by occupation. Programme lengths are published (O*NET
#   job-zone training times are already shipped in reference/data/), so this
#   is one of the more readily settled constants in the block — and three
#   years is implausibly uniform across occupations that range from weeks to a
#   decade.
SCARCITY_SUPPLY_LAG_YEARS: int = 3      # years for supply to respond to raised multiplier
# tag: CHOSEN | units: normalized scarcity score ∈ [0,1]
# resolves_by: a charter decision on when scarcity becomes an emergency worth
#   naming. It gates a label, not an allocation.
SCARCITY_SEVERE_THRESHOLD: float = 0.80 # above this, flag as SEVERE_SCARCITY

# ---------------------------------------------------------------------------
# Multiplier governance: anti-gaming safeguards (B5)
# Mission Statement: §"Anti-gaming safeguards" — empirical training validation,
# artificial scarcity detection, sunset reassessment enforcement.
# ---------------------------------------------------------------------------
# tag: CHOSEN | units: ratio of mandated to median observed training duration
# form: the anti-gaming test — a credential mandating far more training than
#   practitioners actually needed is rent extraction wearing a training claim.
# resolves_by: the distribution of mandated-vs-actual training ratios across
#   licensed occupations. O*NET training data plus licensure requirements
#   would give the empirical spread, and the tolerance should sit at its upper
#   tail rather than at a round 1.5.
TRAINING_VALIDATION_TOLERANCE: float = 1.5        # mandated/median ratio ceiling
# tag: CHOSEN | units: fraction | family: ARTIFICIAL_SCARCITY_*
# form: the pass-rate floor and the quality differential that can excuse
#   falling below it — a gate is artificial unless the failures are really
#   unqualified.
# resolves_by: observed licensure pass rates paired with a measured competency
#   differential between passers and failers. Board pass rates are published;
#   the competency half is the missing instrument, and without it the excuse
#   cannot be tested — only asserted.
ARTIFICIAL_SCARCITY_PASS_RATE_FLOOR: float = 0.30 # below this always flagged
ARTIFICIAL_SCARCITY_QUALITY_THRESHOLD: float = 0.20 # min quality differential to justify low pass rate
# tag: CHOSEN | units: years
# form: the sunset clock — a tier assessment that never expires becomes a
#   property right, which is the failure mode notes/historical-autopsy.md
#   names.
# resolves_by: a charter decision on revalidation cadence, with abundant
#   precedent in professional recertification cycles (commonly 2–10 years).
#   Several other constants are pinned to it (CONTESTABILITY_VESTING_YEARS),
#   so moving it moves them.
TIER_ASSESSMENT_INTERVAL_YEARS: int = 5           # years before tier must be reassessed

# Default workforce tier segments: (name, fraction, mean_multiplier)
# Calibrated so weighted mean = 2.10 at ε=0.
# 0.20×1.20 + 0.50×1.87 + 0.25×2.80 + 0.05×4.50 = 2.100
# tag: CHOSEN | units: fractions of workforce and dimensionless multipliers
# note: CALIBRATED TO A TARGET — the segment means were set so the weighted
#   mean lands on 2.10, the top of the constitutional band, at ε=0. Same class
#   as the GUF_USE_* rates: a value reverse-engineered from a desired outcome.
# resolves_by: SUPERSEDED IN PRACTICE. reference/workforce.py ships measured
#   workforce composition snapshots and scenarios/measured.py builds segments
#   from the O*NET/BLS registry (751 occupations, 94.2% of US employment).
#   This default survives as a self-contained fixture for tests and examples;
#   prefer the measured path for any reported result.
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
# provenance-block: Registration sigmoids
# tag: CHOSEN | units: start_share/saturation fractions; inflection in ε; rate dimensionless
# form: physics-adjacent in shape only — admission to a collective ledger
#   plausibly follows slow onset, mid-range acceleration and saturation below
#   1.0 (some care stays informal at any automation level). Every one of the
#   four numbers is asserted.
# note: docs/parameter_provenance.md's Registration table still lists
#   start_share 0.30 and inflection 0.55 against the 0.05 and 0.45 shipped
#   here — caught by this migration, corrected in the generated table.
# resolves_by: the measured formal/informal split of care labour against an
#   automation index — the share of care hours that pass through a paid or
#   recorded channel. ATUS separates household care from paid care and is now
#   partly ingested (reference/atus_time_use.py), so the start_share is the
#   most nearly reachable of the four; the inflection needs a cross-country
#   panel.
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
# provenance-block: EOH generation — personal domain
# tag: CHOSEN | units: hours/year per working-age-equivalent
# form: S_a — the autarky-referenced SURVIVAL standard. Hard-bounded above by
#   (L−R)/w = 627: a survival standard exceeding labour supply is extinction.
#   Set independently and CHECKED rather than pinned to the bound, so
#   scenarios/feasibility.py can still fail it — a constant that cannot fail
#   its own test says nothing.
# resolves_by: minimum-subsistence time-allocation studies covering only the
#   components that kill you if unmet — food, water, shelter, warmth.
PERSONAL_EOH_SURVIVAL: float    = 600.0   # S_a — autarky-referenced survival standard.
                                          # CHOSEN. Bounded above by (L−R)/w = 627; checked,
                                          # not pinned. resolves_by: minimum-subsistence
                                          # time-allocation studies (the components that
                                          # kill you if unmet: food, water, shelter, warmth).
# tag: CHOSEN | units: hours/year per working-age-equivalent
# form: F_a — the autarky-referenced SUFFICIENCY standard. MAY exceed labour
#   supply, and that gap is precisely why collectives form.
# resolves_by: cross-cultural time allocation at a stated adequacy standard,
#   plus the capital-inventory + time-use identity route. Cross-checks already
#   in hand: the identity route gives F_c(modern) = 390–926, implying 38–74%
#   abatement, and "all needs met" requires ~30% at ε=0.99 — 1500 sits
#   mid-band against both.
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
# tag: CHOSEN | units: share = fraction of the personal obligation; abatability = fraction removable
# form: the shares are the original desk estimate's own four terms
#   (208/156/208/936 over 1508), so they are internally consistent with
#   PERSONAL_EOH_SUFFICIENCY rather than independent of it. The abatability
#   ceilings are the per-component most that infrastructure can ever remove,
#   and their ORDERING encodes the block's structural prediction: abatability
#   and sufficiency are ANTI-CORRELATED, because what infrastructure removes
#   is survival-shaped work and what it cannot remove is care (the Baumol
#   case). That prediction is TESTED in TestAntiCorrelationPrediction, not
#   asserted here — changing these weights falsifies it.
# resolves_by: per-component pointers are on each line below. a_max = Σ share
#   × abatability = 0.4483 is DERIVED from this table, so it is not a free
#   parameter; the table is where the judgement lives.
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

# tag: CHOSEN | units: TEH of capital per capita
# form: K_half in a(K) = a_max · K/(K + K_half). It sets the PACE of abatement
#   along the arc, not its ceiling.
# note: THE LEAST-GROUNDED CONSTANT IN BLOCK II, and the only new free
#   parameter the block introduced. Report the sensitivity alongside any
#   abatement figure until it is measured.
# resolves_by: the identity route run at two or more capital levels — B(K)
#   measured at matched (inventory, time-use) pairs pins a_max and K_half
#   together.
ABATEMENT_HALF_CAPITAL_TEH: float = 1000.0
#   K_half — capital per capita at which HALF of the abatable obligation is
#   abated. CHOSEN, and the least-grounded constant in this block: it sets the
#   PACE of abatement along the arc, not its ceiling. resolves_by: the identity
#   route run at two or more capital levels — B(K) measured at matched
#   (inventory, time-use) pairs pins both a_max and K_half at once. Report the
#   sensitivity with any abatement figure until it does.

# tag: CHOSEN | units: hours/year per working-age-equivalent
# form: the ABATEMENT-COLLAPSED operating value — one number standing in for
#   F_a × (1 − a(K)) at an unstated point on the arc. 1000 ≈ 1500 × (1 − 1/3),
#   and a ≈ 33% sits mid-range between the 10% "all needs met" requires at ε =
#   0.40 and the 38–74% the identity route implies at modern capital. Retired
#   when abatement becomes the default generation path.
# note: THE SINGLE MOST LEVERAGED CONSTANT IN THE MODEL. Personal EOH is
#   91–97% of total EOH at every ε, so this effectively sets the denominator
#   of ε. Repriced 1500 → 1000 on 2026-08-06 (author decision) to the HIGH end
#   of the evidence band, on an asymmetric-loss argument: too low hides a real
#   shortfall (model reports feasible, capital under-built, deficit paid in
#   unserved biological obligation), too high only over-builds capital. Erring
#   high is the mortality-minimising error. Per working-age-EQUIVALENT: × w =
#   1.475 gives the per-capita claim of 1,475 h/person·yr.
# resolves_by: the capital-inventory + time-use identity, NOT time-use data
#   alone — see the circularity section in docs/parameter_provenance.md.
#   Partial progress: core/eoh_generation.personal_statutory_floor() now
#   builds a currency-free floor from physical quantities, but only one of
#   seven basket components is priced (nutrition production, 330.9
#   h/person·yr), so coverage is 6.9% and the floor cannot yet falsify this
#   value.
PERSONAL_EOH_BASE: float   = 1000.0     # hours/year per working-age-equivalent. CHOSEN — resolves_by: capital-inventory + time-use identity
# provenance-block: EOH generation — infrastructure domain
# tag: CHOSEN | units: fraction of capital stock, as EOH-hours per year
# resolves_by: it cites a 2–4% band and picks a point inside it. The statutory
#   floor below is the better instrument and supersedes this in practice — a
#   physical condition census in crew-hours, with no money→hours step.
INFRA_MAINT_RATE: float    = 0.025      # fraction of capital stock = EOH/year. CHOSEN — a point inside the OECD 2–4% band
# tag: CHOSEN | units: dimensionless multiplier at end of design life
# form: physics — maintenance burden really is convex in age. The DOUBLING is
#   not.
# resolves_by: measured maintenance hours against age for a single asset
#   class, which the NBIS condition data behind INFRA_TREATMENT_HOURS_* could
#   supply.
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
# (Structured provenance blocks sit immediately above each constant below.)
# ---------------------------------------------------------------------------
# tag: convention | units: months between routine inspections
# form: the statutory routine inspection interval, adopted from 23 CFR 650 (US
#   National Bridge Inspection Standards). A stated regulatory basis rather
#   than a claim about the world, which is what `convention` marks.
# resolves_by: the governing standard for the jurisdiction being modelled —
#   the interval is whatever that jurisdiction's code says, and adopting a
#   different code changes it legitimately.
INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT: float = 24.0  # 23 CFR 650 routine default
# tag: CHOSEN | units: labour-hours per asset unit per year | family: INFRA_TREATMENT_HOURS_*
# form: task-normative — hours/unit/year = (12 / inspection_interval_months) ×
#   crew_hours_per_visit, currency-free by construction. This is the measured,
#   auditable half of infrastructure EOH; discretionary maintenance ambition
#   above it is a policy choice and enters the fiscal layer, never the floor.
# note: the reason this stream exists — the monetized capital_stock_teh path
#   is convention-dominated 10.26× while every physical knob on this path
#   reads ×1.000 (scenarios/infrastructure_floor.doctrine_floor_invariance).
#   The floor is ~5.9× better determined and its residual is
#   timesheet-measurable.
# resolves_by: state DOT maintenance-activity manuals and inspection
#   timesheets, which record the real per-condition crew-hours. This is the
#   nearest-to-closed CHOSEN debt in the file: the instrument exists, is
#   public, and the units match.
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
# provenance-block: EOH generation — ecological domain
# tag: CHOSEN | units: hours/year at pristine ecosystem health (relative anchor)
# note: THE DOMAIN-BALANCE DEFECT LIVES HERE. This is documented as a RELATIVE
#   anchor — "does not represent an absolute ecosystem-specific count" — but
#   it is SUMMED with absolute counts in total_eoh() and then divided into ε.
#   At defaults it contributes 0.03% of total EOH (0.71 h/person·yr against
#   personal's 2,213), so the ecological domain cannot move ε and the thermal
#   obligation books at ~1.8 h/person·yr. Do not quote this domain's SHARE of
#   total EOH until it is on an absolute footing. Either this is low by 2–3
#   orders, or CDR_LABOR_HOURS_PER_TONNE is, or both; nothing in current data
#   settles it.
# resolves_by: a stewardship-hours census on an absolute footing — agency FTEs
#   per hectare, or the GUF parcel inventory × measured crew-hours.
ECOLOGICAL_BASE_RATE: float = 500_000.0 # hours/year at pristine ecosystem health. CHOSEN — relative anchor, needs absolute footing
# tag: CHOSEN | units: ecosystem health index ∈ [0,1]
# form: physics — ecological regime shifts are established, so a threshold
#   below which burden escalates nonlinearly is structural. Where 0.40 falls
#   on THIS index is a mapping, not a measurement.
# resolves_by: an ecological time series relating a defined health index to
#   observed regime shift. GUF_EOH_ACCUMULATION_THRESHOLD makes the same class
#   of claim on the deferral rate rather than the state; both resolve from one
#   series.
ECOLOGICAL_THRESHOLD: float = 0.40     # below this → nonlinear spike. physics (regime shift) / CHOSEN (0.40 on this index)
# --- KNOWLEDGE_EOH_BASE — ADOPTED FROM MEASUREMENT (Block K-IV, 2026-08-08) ---
#
# Was 100_000.0, CHOSEN, with the epistemic pointer "occupational CPD hours".
# That pointer is now redeemed: the O*NET 30.3 / BLS spine already shipped in
# `reference/data/` carries the input, and `reference/onet_knowledge.py` recovers
# it by inverting the documented log-minmax normalization of `f_training`.
#
#   embodied training stock   11,001.3 h/worker      (751 occ, 157.79 M employment)
#   per head of population     5,501.0 h/person      (E/P = 0.500, registry route)
#   de-anchored to ε=0        ÷ kbs(0.40)·cpu(0.40) = 11.224
#   →  KNOWLEDGE_EOH_BASE      4.901074e8 h at KNOWLEDGE_REFERENCE_POPULATION
#
# Re-deriving per vintage would reintroduce the circularity the multiplier's
# frozen bounds exist to break. `tests/test_knowledge_base.py` asserts the frozen
# value still matches the live derivation, so a registry refresh fails loudly
# rather than drifting silently.
#
# THE ANCHORING ASSUMPTION IS THE UNCERTAINTY, NOT THE MEASUREMENT. The registry
# describes a modern, already-automated workforce, so the stock must be
# de-anchored at a reference automation level ε_ref. Across ε_ref ∈ [0.2, 0.6]
# the constant moves **7.13×**, against only 1.20× from the per-capita route.
#
# --- RE-ANCHORED TO THE FIXED POINT (Finding E, author-approved 2026-08-09) ---
#
# K-IV used ε_ref = 0.40 partly because the labour-residual route independently
# corroborated it at 0.391. That corroboration did not survive the adoption it
# justified: raising the knowledge base grew total EOH ~12% at mid-arc, and the
# residual solves `(1−ε)·total_eoh(ε) = observed` — so the denominator moved and
# the residual went to 0.470. **The shipped pair was not a fixed point of its own
# derivation.**
#
# The defect was the SHAPE of the derivation, not the value: a one-shot anchor
# cannot be self-consistent when the constant it sets sits inside the quantity
# that checks it. A third one-shot would have the same defect. So the anchor and
# the base are now solved TOGETHER —
# `scenarios/knowledge_base.epsilon_ref_fixed_point()` iterates
# base(ε_ref) → total_eoh → ε_residual → ε_ref to convergence:
#
#   ε* = 0.4522   (8 iterations, damped)
#   base = 3.81963e8   =  0.779 × the K-IV value
#
# WHAT THIS DOES NOT FIX, stated plainly: the fixed point is still anchored on
# 937.3 h/person·yr of US PAID labour (ATUS 2025, `scenarios/personal_floor`).
# It removes the self-inconsistency, not the US-specificity or the paid-labour
# convention. The convention is at least coherent with
# `personal_eoh_registration_share(0)` being near-zero — subsistence labour is
# off-ledger by design — and the full-labour reading has NO solution at all
# (supply exceeds the whole obligation; Finding B). That unresolved
# over-determination is the real limit on this anchor.
#
# resolves_by (to leave derived-then-FROZEN): an O*NET/BLS vintage refresh moves
# it mechanically; the ANCHOR now resolves by whatever settles Finding B — the
# capital-inventory route remains unusable (Finding A).
# provenance-block: EOH generation — knowledge domain
# tag: derived-then-FROZEN | units: embodied knowledge-hours (STOCK) at the ε=0 reference, at KNOWLEDGE_REFERENCE_POPULATION
# form: recovered from the O*NET 30.3 / BLS spine already shipped in
#   reference/data/ by inverting the documented log-minmax normalization of
#   f_training: 11,001.3 h/worker embodied training stock over 751 occupations
#   → 5,501.0 h/person at E/P = 0.500 → de-anchored to ε=0 by ÷
#   kbs(ε*)·cpu(ε*). Anchor and base are solved TOGETHER at the fixed point ε*
#   = 0.4522 (scenarios/knowledge_base.epsilon_ref_fixed_point, 8 damped
#   iterations), because a one-shot anchor cannot be self-consistent when the
#   constant it sets sits inside the quantity that checks it. Frozen at the
#   reference epoch so it stays comparable across data vintages.
# note: THE ANCHORING ASSUMPTION IS THE UNCERTAINTY, NOT THE MEASUREMENT.
#   Across ε_ref ∈ [0.2, 0.6] the constant moves 7.13×, against only 1.20×
#   from the per-capita route. What the fixed point does NOT fix: the anchor
#   is still 937.3 h/person·yr of US PAID labour, so it removes the
#   self-inconsistency, not the US-specificity or the paid-labour convention —
#   and the full-labour reading has no solution at all (supply exceeds the
#   whole obligation; Finding B). tests/test_knowledge_base.py asserts the
#   frozen value still matches the live derivation, so a registry refresh
#   fails loudly rather than drifting.
# resolves_by: an O*NET/BLS vintage refresh moves it mechanically; the ANCHOR
#   resolves by whatever settles Finding B. The capital-inventory route is
#   unusable (Finding A).
KNOWLEDGE_EOH_BASE: float  = 381_962_855.27  # embodied knowledge STOCK at the ε=0 reference. derived-then-FROZEN (O*NET 30.3/BLS, epoch 2026-07-29, ε_ref = 0.4522 fixed point)
# tag: CHOSEN | units: dimensionless exponent
# form: physics — knowledge EOH grows superlinearly with ε, because complexity
#   compounds. The exponent is asserted.
# resolves_by: measured knowledge-maintenance hours against an automation
#   index at three or more points, which is what distinguishes an exponent
#   from a slope.
KNOWLEDGE_EPS_EXPONENT: float = 2.0    # how steeply knowledge EOH grows with ε. physics (superlinear) / CHOSEN (exponent)

# --- Knowledge domain: stock/flow semantics and reference population (Block K-I) --
#
# UNITS CORRECTION (2026-08-08). KNOWLEDGE_EOH_BASE was documented as a FLOW
# ("baseline knowledge EOH at ε=0, hours/year") but knowledge_eoh() computes
#     base × kbs × cpu × skill_decay
# so at the ε=0 reference it returns base × 0.10 = 10,000, not 100,000. The
# constant was never the answer; it operates as a STOCK of embodied knowledge
# hours, with skill_decay_rate as the annual renewal fraction. The docstrings
# now say so. No value changed — this is a labelling correction, and it is the
# reason the O*NET route fits: that data supplies exactly a training STOCK and
# a renewal RATE. See notes/knowledge-eoh-closure.md.
#
# KNOWLEDGE_REFERENCE_POPULATION exists because knowledge EOH was
# population-INVARIANT: the same absolute number was returned at 1M and at 300M
# population, so the domain's share of total EOH fell as 1/population while
# every other domain scaled. The base is now explicitly "stock at the reference
# population" and knowledge_eoh() scales linearly off it. 1e6 is the repo-wide
# default population, so this reproduces prior output exactly at the default.
# tag: convention | units: persons
# form: a stated denominator, not a claim about the world — the population
#   KNOWLEDGE_EOH_BASE is quoted at. It exists because knowledge EOH was
#   population-INVARIANT: the same absolute number came back at 1M and at
#   300M, so the domain's share of total EOH fell as 1/population while every
#   other domain scaled. 1e6 is the repo-wide default population, so this
#   reproduces prior output exactly at the default.
# resolves_by: n/a — a convention is settled by declaring it, which this does.
KNOWLEDGE_REFERENCE_POPULATION: float = 1_000_000.0  # persons; the population KNOWLEDGE_EOH_BASE is quoted at

# The annual renewal fraction applied to the knowledge stock. Previously an
# anonymous literal (0.10) in three call sites and in params.py, violating the
# no-anonymous-constants invariant; naming it is a prerequisite for splitting it.
# CHOSEN, and it is CONFLATING TWO RATES that Block K-III separates:
#   transmission — stock ÷ working life ≈ 1/40, the cost of re-creating training
#                  as cohorts retire (knowledge dies with people)
#   CPD          — recurring hours a WORKING practitioner spends staying current
# At 0.10 the shipped value implies a 10-year half-life on ACQUISITION stock —
# a physician re-doing medical school every decade — which is why it cannot be
# either rate alone. resolves_by: transmission from cohort turnover (entry-to-
# retirement); CPD from Eurostat CVTS (paid training hours per employee), the
# only public series that measures the recurring term directly. O*NET cannot
# give CPD: it measures the stock to reach competency, not the flow to hold it.
# DEPRECATED as of Block K-IV (2026-08-08) — retained, not deleted, per the
# additive-not-destructive rule. Nothing defaults to it any more; the default
# renewal rate is SKILL_TRANSMISSION_RATE below. Kept because it is the value
# every pre-K-IV result in this repo was produced at, so reproducing an old
# figure means passing it explicitly rather than guessing what it was.
# It is NOT a renewal rate: see the credibility check under the split.
# tag: CHOSEN | units: fraction of the knowledge stock renewed per year
# form: DEPRECATED as of Block K-IV — retained, not deleted, per the
#   additive-not-destructive rule. Nothing defaults to it; the default renewal
#   rate is SKILL_TRANSMISSION_RATE. Kept because it is the value every
#   pre-K-IV result in this repo was produced at, so reproducing an old figure
#   means passing it explicitly rather than guessing what it was.
# note: IT WAS NEVER A RENEWAL RATE. At 0.10 against the measured 11,001
#   h/worker stock it implies 1,100 h/worker·yr — 55% of the H_REF work-year
#   spent forever re-acquiring knowledge already held. No time-use or training
#   series reports anything close. It was also CONFLATING two rates that Block
#   K-III separates: transmission (cohort turnover) and CPD (staying current
#   while working).
# resolves_by: superseded — see SKILL_TRANSMISSION_RATE and SKILL_CPD_RATE,
#   whose sum is 0.0277 against this 0.10. That gap is a finding, not an error
#   to reconcile away.
SKILL_DECAY_RATE: float = 0.10  # DEPRECATED placeholder (pre-K-IV default). CHOSEN — conflated; see skill_renewal_rate()

# --- Block K-III: the renewal rate, split ----------------------------------
#
# The two rates SKILL_DECAY_RATE was conflating, now set INDEPENDENTLY and
# checked rather than pinned to reproduce it. Their sum is 0.0277, against the
# shipped 0.10. That gap is a FINDING, not an error to reconcile away:
#
#   measured stock                       11,001 h/worker  (reference/onet_knowledge)
#   at d = 0.10   →  1,100 h/worker·yr  =  55.0% of the H_REF 2,000 h work-year
#   at d = 0.0277 →    305 h/worker·yr  =  15.2%
#
# A renewal rate of 0.10 asserts that every worker spends more than half of
# every working year, forever, re-acquiring knowledge they already have. No
# time-use or training series reports anything close. The shipped value was
# never a renewal rate; it was a placeholder that no measurement had reached.
#
# ADOPTED IN BLOCK K-IV (2026-08-08): the default renewal rate is now
# SKILL_TRANSMISSION_RATE, the LOWER of the two credible doctrines and the only
# one containing no CHOSEN component — transmission is derived from the working
# life, whereas CPD is a judgement call awaiting Eurostat CVTS.
#
# CPD IS EXCLUDED FROM THE DEFAULT, NOT DENIED. SKILL_CPD_RATE remains defined
# and `skill_renewal_rate()` still returns the sum; a caller who wants the fuller
# obligation passes it. The adopted default therefore UNDERSTATES the renewal
# obligation by ~10.8%, deliberately, so that no CHOSEN number rides in the
# shipped arc. This is the same posture the thermal layer takes when it withholds
# a budget whose sign is undetermined: prefer the defensible understatement to
# the unbacked completion.
# `core.eoh_generation.skill_renewal_rate()` reports both components and the gap.

# TRANSMISSION — the stock is re-created as cohorts retire. Knowledge dies with
# people; this is the entropy the domain measures, and the framing the author
# accepted 2026-08-08. DERIVED: 1 / working life, with the horizon below.
# The horizon is the only input, and it is weakly held: halving or doubling it
# moves transmission 2× against ε_ref's 7.13× lever on the base.
# tag: CHOSEN | units: years, entry to retirement
# note: the only input to transmission, and weakly held — but halving or
#   doubling it moves transmission 2×, against ε_ref's 7.13× lever on
#   KNOWLEDGE_EOH_BASE, so it is not where the uncertainty lives.
# resolves_by: BLS Employee Tenure, or cohort exit rates from the labour
#   force.
SKILL_WORKING_LIFE_YEARS: float = 40.0   # years entry→retirement. CHOSEN — resolves_by: BLS Employee Tenure / cohort exit rates
# tag: derived | units: fraction of the knowledge stock renewed per year
# form: 1 / SKILL_WORKING_LIFE_YEARS = 0.025. Transmission is the stock being
#   re-created as cohorts retire — knowledge dies with people, which is the
#   entropy this domain measures (framing accepted by the author 2026-08-08).
#   Adopted as the default renewal rate in Block K-IV because it is the LOWER
#   of the two credible doctrines and the only one containing no CHOSEN
#   component.
# resolves_by: n/a — it inherits SKILL_WORKING_LIFE_YEARS's standing.
SKILL_TRANSMISSION_RATE: float = 1.0 / SKILL_WORKING_LIFE_YEARS  # derived — 0.025

# CPD — recurring hours a WORKING practitioner spends staying current. This is
# the term O*NET structurally cannot supply: it measures the hours to REACH
# competency, never the hours to HOLD it. Set from the licensure/continuing-
# education scale (US state boards typically mandate 20–50 h per two-year
# cycle → 10–25 h/yr for licensed occupations, which are ~a quarter of
# employment; Eurostat CVTS reports ~25 h per participating employee·yr at
# ~40% participation). ~30 h/worker·yr economy-wide against an 11,001 h stock
# gives 0.0027. CHOSEN, and the least-grounded number in Block K-III.
# resolves_by: Eurostat CVTS (paid training hours per employee, all sectors) —
# the single public series that measures this term directly.
# tag: CHOSEN | units: fraction of stock renewed per year by continuing practice
# form: the recurring hours a WORKING practitioner spends staying current —
#   the term O*NET structurally cannot supply, because it measures the hours
#   to REACH competency, never the hours to HOLD it. ~30 h/worker·yr
#   economy-wide against an 11,001 h stock gives 0.0027, from the licensure
#   scale (US state boards mandate 20–50 h per two-year cycle for licensed
#   occupations, ~a quarter of employment) and Eurostat CVTS (~25 h per
#   participating employee·yr at ~40% participation).
# note: THE LEAST-GROUNDED NUMBER IN BLOCK K-III, and EXCLUDED FROM THE
#   DEFAULT — not denied. skill_renewal_rate() still returns the sum and a
#   caller who wants the fuller obligation passes it. The adopted default
#   therefore UNDERSTATES renewal by ~10.8%, deliberately, so no CHOSEN number
#   rides in the shipped arc — the same posture the thermal layer takes when
#   it withholds a budget whose sign is undetermined.
# resolves_by: Eurostat CVTS (paid training hours per employee, all sectors),
#   the single public series that measures this term directly.
SKILL_CPD_RATE: float = 0.0027  # fraction of stock renewed per year by continuing practice. CHOSEN

# ---------------------------------------------------------------------------
# Reference hours
# ---------------------------------------------------------------------------
# provenance-block: Reference and workforce
# tag: convention | units: hours/year per worker
# form: a stated normalizer — 50 weeks × 40 h. Used to convert workforce-hours
#   to TEH, not a claim about how long anyone works.
# resolves_by: n/a as a convention. If it were read as a measurement of actual
#   hours worked it would be wrong in most jurisdictions (OECD average annual
#   hours run ~1,400–2,200), which is precisely why it is tagged as the
#   denominator it is.
H_REF: int = 2000  # reference work-year hours per worker

# ---------------------------------------------------------------------------
# TEH destruction defaults and ε-scaling slopes
# All anonymous ε-scaling factors that appear in eoh_fulfillment.py and
# simulation.py are named here so they can be swept and audited.
# ---------------------------------------------------------------------------
# provenance-block: TEH destruction and ε-scaling
# tag: CHOSEN | units: fraction of capital stock per year
# form: catastrophic failure beyond recoverability, triggering D1 write-down.
# resolves_by: observed catastrophic-failure rates by asset class. Insurance
#   and asset-registry loss data measure this directly; ASSET_TYPES in this
#   file already carries per-class threshold ages, so a measured pass should
#   produce a per-class rate rather than one economy-wide 0.5%.
CAPITAL_FAILURE_RATE:               float = 0.005  # fraction of capital failing beyond repair/year
# tag: CHOSEN | units: fraction of the failure rate removable at ε=1
# form: better monitoring at high ε reduces catastrophic failure —
#   structurally right in direction (detected degradation is repairable
#   degradation), asserted in magnitude.
# resolves_by: measured failure-rate reduction attributable to condition
#   monitoring. Note this shares the framework's monitoring-eyesight
#   assumption with ENV_MONITORING_SATURATION_TEH_PER_CAPITA and neither is
#   measured.
CAPITAL_WRITEDOWN_MONITORING_SLOPE: float = 0.30   # max failure-rate reduction at ε=1 from better monitoring
# tag: CHOSEN | units: TEH per period (at the 1M reference population)
# form: a numerical guard, not an economic claim — it keeps period labour
#   income from reaching zero and producing division-by-zero at high ε, which
#   the ε-coherence rule requires every function to survive.
# resolves_by: n/a as a floor; it should ideally be derived from
#   WORKFORCE_FRACTION_MIN × H_REF × the mean multiplier rather than pinned,
#   which would make the guard consistent with the quantities it guards.
LABOR_INCOME_MIN_TEH:              float = 100_000_000.0  # hard floor on period labor income (100M TEH)
# tag: CHOSEN | units: fraction of population in the workforce
# form: the minimum workforce retained at any automation level. Structural in
#   direction — full automation still needs someone, which Condition IV
#   asserts as distributed competency — and asserted in level.
# resolves_by: the minimum staffing that holds ESSENTIAL_DOMAINS above
#   COMPETENCY_THRESHOLD; that makes it derivable from two other constants in
#   this file rather than independent, and it is currently set independently
#   of both.
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
# tag: CHOSEN | units: fraction of population per year
# form: crude death rate. EXOGENOUS — nothing in the model links mortality to
#   the deferred personal-EOH deficit that core/eoh_fulfillment.py now tracks,
#   so a severe unserved survival obligation and this rate are independent.
#   That is a known limit, stated because the deficit reports HOURS, not
#   outcomes.
# resolves_by: national vital statistics or UN WPP for the jurisdiction being
#   modelled. 1%/yr is a plausible developed-world crude rate and directly
#   measurable, making this one of the cheaper CHOSEN debts to close.
ANNUAL_DEATH_RATE:              float = 0.010  # fraction of population dying per year
# tag: CHOSEN | units: fraction of the excess above reserve | family: ESTATE_*
# form: the D5 split on death — inherited (circulatory), levied to Trust
#   (circulatory), and the remainder written down. Note the three shares are a
#   distributional design, and RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE deliberately
#   reuses the 0.15 levy fraction so capital estates get the same treatment as
#   TEH estates rather than a new rule.
# resolves_by: a charter decision on inheritance. There is no measurement of
#   what fraction of an estate SHOULD pass to heirs; comparative
#   inheritance-tax schedules give precedent for the range, not the value.
ESTATE_INHERITANCE_FRACTION:    float = 0.35   # fraction of excess above reserve passed to heirs
ESTATE_LEVY_FRACTION:           float = 0.15   # fraction of excess levied to Trust (circulatory)
# tag: CHOSEN | units: years of basket cost
# form: the unconditionally preserved personal reserve — the part of an estate
#   D5 never touches.
# resolves_by: a charter decision. It is a commitment about how much security
#   a person may hold beyond their own lifetime without it being reclaimed.
ESTATE_PERSONAL_RESERVE_YEARS:  float = 10.0   # years of basket costs preserved unconditionally

# ---------------------------------------------------------------------------
# D6 — Accumulation ceiling capital commitment (Option 3, disabled by default)
# Excess TEH above the ceiling is committed to capital formation rather than
# sitting in perpetual savings. Moves TEH from circulation to capital_embodied.
# ---------------------------------------------------------------------------
# tag: CHOSEN | units: multiple of base lifetime earnings
# form: the D6 accumulation ceiling above which excess TEH is committed to
#   capital formation rather than sitting in perpetual savings. Disabled by
#   default.
# resolves_by: a charter decision on the maximum permitted accumulation — the
#   framework's most direct statement about tolerable wealth concentration,
#   and it belongs in deliberation. Note it interacts with M_MAX: a 6×
#   multiplier cap and a 3.5× accumulation cap are two different answers to
#   the same question and have not been reconciled.
ACCUMULATION_CEILING_MULTIPLIER: float = 3.5       # × base lifetime earnings
# tag: derived | units: TEH over a career
# form: 2080 TEH/yr × 42-yr career at a 1× multiplier = 87,360. Note the 2080
#   differs from H_REF's 2000 (2080 = 40 h × 52 wk, with no leave), so the
#   repo carries two work-year conventions; this one is the FTE-hours
#   convention the multiplier registry also uses.
# resolves_by: n/a — arithmetic from a stated career length and work-year. The
#   career length (42 yr) is close to SKILL_WORKING_LIFE_YEARS (40) and should
#   probably be bound to it rather than restated.
BASE_LIFETIME_EARNINGS_TEH:      float = 87_360.0  # 2080 TEH/yr × 42-yr career at 1× multiplier

# ---------------------------------------------------------------------------
# Fiscal architecture defaults (single source of truth)
# Used in: params.py, fiscal.py, dashboard.py, stress.py, prices.py
# ---------------------------------------------------------------------------
# provenance-block: Fiscal architecture
# tag: CHOSEN | units: fraction of labor income
# resolves_by: min_levy_for_solvency() in core/fiscal.py already derives the
#   rate the guarantee requires at a given ε, so the honest route is to
#   REPLACE this default with that derivation rather than measure it. Recorded
#   finding: at canonical ε=0.40 this rate raises ≈6.2M TEH/yr against a 307M
#   TEH guarantee — it does not fund the guarantee and was never sized to; the
#   Trust dividend does.
SUFF_LEVY_RATE:               float = 0.0125            # sufficiency levy rate on labor income
# tag: CHOSEN | units: fraction, per ε unit
# resolves_by: nothing measures how fast a guarantee floor should shrink as
#   automation rises; it is a distributional commitment about who carries the
#   transition. Argue it, do not fit it.
SUFF_GUARANTEE_EPS_DECAY:     float = 0.50              # rate at which guarantee floor_fraction shrinks with ε
# tag: CHOSEN | units: TEH (at the 1M reference population)
# note: THE CRITICAL SOLVENCY KNOB, and it is sized backwards — chosen so the
#   annual dividend (Trust × DEP_RATE × DIV_RATE = 630M TEH) covers the
#   stewardship, ecological and guarantee obligations at mid-arc. Calibrated
#   to a target, like GUF_USE_* and DEFAULT_SEGMENTS.
# resolves_by: a real capital inventory in TEH for the jurisdiction being
#   modelled. research/epsilon_inverse.capital_for_epsilon() is the tool that
#   makes an inventory-first reading possible, and the constant should follow
#   the inventory rather than the obligation it is required to cover.
TRUST_BASE_TEH:               float = 35_000_000_000.0  # Trust fund balance at ε=0 (TEH); sized for EOH-reimbursement guarantee
# tag: CHOSEN | units: fraction of Trust per year
# form: physics — the capital the Trust represents really does deteriorate, so
#   a depreciation term must exist. The RATE is not structural.
# resolves_by: a weighted mean design life over the actual capital inventory.
#   FORMATION_DEPRECIATION_RATE (0.05) in this file derives exactly that from
#   CAPITAL_MACHINE_PROFILES design lives — so the repo holds two aggregate
#   depreciation rates, 0.045 and 0.05, on the same physical quantity. They
#   should be reconciled to one derivation.
DEP_RATE:                     float = 0.045             # annual trust depreciation rate
# tag: CHOSEN | units: fraction of annual depreciation
# form: the dividend/renewal split. That a split exists is structural — pay
#   out everything and the Trust erodes; retain everything and it never
#   circulates.
# resolves_by: a charter decision on the payout ratio. It is the framework's
#   central distributional lever and belongs in deliberation, not measurement.
DIV_RATE:                     float = 0.40              # fraction of depreciation paid as dividend
# tag: CHOSEN | units: TEH per recipient per year (at ε=0) | family: MEANINGFUL_ACTIVITY_TEH_*
# form: base × (1 + scale × ε²) — quadratic so non-participants gain real
#   purchasing power as the labour pool shrinks. Also serves as the
#   sufficiency basket cost at ε=0, so basket_price(0) = 120 TEH/yr.
# resolves_by: a charter decision on discretionary provision above biological
#   reimbursement — this is what a collective thinks a life beyond subsistence
#   costs, which is the same question PERSONAL_EOH_SUFFICIENCY asks in hours.
#   The two should be reconciled; at present they are set independently.
MEANINGFUL_ACTIVITY_TEH_BASE: float = 120.0            # discretionary spending bonus at ε=0 (TEH/yr)
MEANINGFUL_ACTIVITY_TEH_SCALE: float = 1.5              # quadratic ε-growth factor; bonus = base×(1+scale×ε²)
# tag: CHOSEN | units: TEH (at the 1M reference population)
# resolves_by: a capital inventory for the jurisdiction being modelled, via
#   research/epsilon_inverse.capital_for_epsilon(). Note this is 2,000
#   TEH/capita and Block III established that the ε=0 endpoint carries NO
#   apparatus, so this default describes a mid-arc collective, not a
#   subsistence one — callers supplying it at low ε are asserting capital the
#   arc says is not there.
CAPITAL_STOCK_DEFAULT:        float = 2_000_000_000.0   # default capital stock for scenario functions
# tag: derived | units: personal EOH hours per sufficiency basket
# form: DEFINED equal to PERSONAL_EOH_BASE — one basket covers one
#   person-year. Was a literal 1500.0 duplicating it; bound to the constant on
#   2026-08-06 so the two cannot drift apart under repricing.
# resolves_by: n/a — it inherits PERSONAL_EOH_BASE's standing by construction,
#   and the binding is the point: this is the repricing-hazard fix, not a free
#   value.
BASKET_EOH_CONTENT:           float = PERSONAL_EOH_BASE  # personal EOH hours satisfied per sufficiency basket — DEFINED as = PERSONAL_EOH_BASE
                                                         # (was a literal 1500.0 duplicating it; bound to the constant 2026-08-06 so the
                                                         # two cannot drift apart under repricing — one basket covers one person-year)

# ---------------------------------------------------------------------------
# Human capital biological constants (population.py + capital.py)
# ---------------------------------------------------------------------------
# provenance-block: Human capital and population
# tag: CHOSEN | units: fraction shift per ε unit
# form: automation improves medicine, so lives lengthen and the elderly
#   fraction grows. Direction is arguable; the magnitude is asserted, and it
#   is secondary to the dominant ε effect in the fulfillment split.
# resolves_by: a longitudinal life-expectancy series against a measured
#   automation index.
ELDERLY_EOH_EPSILON_FACTOR:   float = 0.05  # elderly EOH rises this fraction per ε unit
# tag: CHOSEN | units: fraction shift per ε unit
# form: infant personal EOH declines with automation — formula feeding,
#   monitoring and sanitation displace caregiver hours. This is the abatement
#   claim of Block II applied to one age group, and note it runs OPPOSITE to
#   care's low abatability; the two have not been reconciled.
# resolves_by: ATUS childcare hours per child against a capital index, which
#   is the same cut AGE_GROUPS needs.
INFANT_EOH_EPSILON_FACTOR:    float = 0.10  # infant personal EOH declines this fraction per ε unit
# tag: CHOSEN | units: fraction of condition per year | family: HUMAN_CAPITAL_*
# form: annual health-condition decay, higher for the elderly. Direction is
#   biological; the 3× ratio between them is asserted.
# resolves_by: measured functional-decline rates by age — NHATS/HRS carry
#   exactly this and are already named as the pointer for the AGE_GROUPS care
#   weights, so one dataset closes both.
HUMAN_CAPITAL_NATURAL_DECAY:  float = 0.005 # annual condition decay rate, non-elderly
HUMAN_CAPITAL_ELDERLY_DECAY:  float = 0.015 # annual condition decay rate, elderly
# tag: CHOSEN | units: dimensionless leverage coefficient per ε unit
# form: automation amplifies the return on education — leverage = 1 + factor ×
#   ε.
# resolves_by: measured returns to schooling against an automation index. The
#   direction is contested in the literature (automation may raise the return
#   to skill or hollow the middle), so the sign is not safe to assume either.
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
# provenance-block: Canonical trajectory
# tag: CHOSEN | units: mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | family: CANONICAL_*
# form: these define the IDEAL ARC, not a prediction. A real simulation
#   diverges from it, and divergence is the point of modelling —
#   canonical_physical_state(ε) exists for arc testing and cross-sectional
#   analysis, so these constants are a deliberately smooth reference rather
#   than a claim about any actual trajectory. That is why they are one family:
#   they share a single epistemic status.
# note: the capital path was corrected in Block III to 2.0B × (1 + slope) × ε
#   so that ε=0 carries NO apparatus — a collective with infrastructure and no
#   automation contradicts ε's own definition. Only the intercept moved; ε=1
#   is still 3× the base. DELIBERATE DIVERGENCE:
#   effective_capital_from_epsilon(base, ε) was NOT changed, because it scales
#   a caller-supplied ε=0 baseline and zeroing it would destroy the caller's
#   input.
# resolves_by: nothing, and by design — an ideal arc is a reference frame, not
#   a measurement. What CAN be measured is how far an actual trajectory sits
#   from it, which is what the scenario layer reports. Treat these as the
#   axis, not the data.
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
#   (notes/Ground_Use_Fee_Framework_Template.md)
# Mission Statement: §"Land is held by the collective … stewardship leases …
# the fee reflects real costs rather than speculative value."
#
# PROVENANCE WARNING, recorded during the four-tag migration (2026-08-09).
# "NLSA" is the National Land Stewardship Authority and its Technical Manual is a
# document of THIS framework — the template's own header says "Based on NLSA from
# HOURSFramework". It is written in the register of an external standard, and
# every constant in this block cites it by equation number.
#
# Those citations establish a functional FORM the framework asserts. They supply
# NO external evidence for a value. So an "NLSA Eq. N" reference appears below
# only under `form:`, never under `resolves_by:`, and every value constant in this
# block is CHOSEN. Citing one's own design document as a source is exactly the
# authority-borrowing the tag scheme exists to prevent, and the equation numbers
# read like external provenance to anyone who has not opened the template.
# ---------------------------------------------------------------------------

# Epsilon scaling function Ψ(ε) — global arc multiplier (NLSA Eq. 18)
# Bell-shaped: near-floor at ε=0 and ε=0.99, peak near ε=0.40.
# provenance-block: Ground Use Fee (land/guf.py)
# tag: CHOSEN | units: dimensionless | family: GUF_PSI_*
# form: NLSA Eq. 18 — the framework's own claim that land's labour-content
#   cost peaks mid-arc and is low at both extremes.
# resolves_by: a ground-fee-vs-automation panel across jurisdictions at
#   differing automation levels. Nothing in the repo constrains the rise and
#   fall speeds independently of one another, so sweep them jointly until it
#   does.
GUF_PSI_A:     float = 0.8   # rise speed from ε=0 (lower a = faster rise)
GUF_PSI_B:     float = 1.2   # fall speed toward ε=1 (higher b = faster fall)
# tag: CHOSEN | units: fraction of the reference fee
# resolves_by: the lowest ground-use fee observed in a highly-automated
#   jurisdiction that still levies one. The floor asserts the fee never
#   reaches zero, which is a policy commitment awaiting an observed analogue.
GUF_PSI_FLOOR: float = 0.02  # irreducible floor; fee never reaches absolute zero
# tag: CHOSEN | units: dimensionless
# form: derived — the normalization that puts Ψ's peak at ≈1.0 given a+b≈2.0.
#   It is PINNED here rather than computed, so it goes stale if either speed
#   moves.
# resolves_by: computing it from GUF_PSI_A/GUF_PSI_B instead of pinning it.
#   The debt here is in the wiring, not in the data — no measurement is owed.
GUF_PSI_NORM:  float = 4.0   # normalizing constant; peak ≈ 1.0 when a+b≈2.0

# Labor-content scaling α(ε) — normalized so α(0.40) = 1.0 (NLSA Eq. 19-20)
# tag: CHOSEN | units: dimensionless | family: GUF_ALPHA_*
# form: NLSA Eq. 19–20 — labour content declines with automation to an
#   irreducible human-judgment floor.
# resolves_by: measured labour-hours per parcel-administration task against an
#   automation index. The O*NET/BLS spine already shipped in reference/data/
#   covers the occupations but has never been cut to land administration.
GUF_ALPHA_ZETA:  float = 0.8   # rate of labor-content decline with automation
GUF_ALPHA_FLOOR: float = 0.05  # irreducible human-judgment fraction at ε→1

# Location Value Index default sub-index weights (NLSA Eq. 3); must sum to 1.0
# tag: CHOSEN | units: fraction | family: GUF_LVI_W_*
# form: NLSA Eq. 3 — the four weights are constrained to sum to 1.0. The split
#   between them is constrained by nothing.
# resolves_by: a hedonic regression of parcel transaction values on the four
#   sub-indices for the jurisdiction being modelled. These weights ARE that
#   regression's coefficients, so the pointer is a well-defined study rather
#   than an aspiration — this is the standard land-valuation method.
GUF_LVI_W_CENTRALITY:      float = 0.35
GUF_LVI_W_TRANSIT:         float = 0.30
GUF_LVI_W_SERVICES:        float = 0.20
GUF_LVI_W_NATURAL_AMENITY: float = 0.15

# Use category reference rates at ε=0.40 (TEH/SLU/year) — midpoints of NLSA Eq. 9 ranges
# Calibrated so aggregate GUF across a 1M-population land inventory (~400k residential
# + 20k commercial parcels) is co-equal with levy revenue at mid-arc (ε≈0.40).
# At ×100 vs. the original abstract unit values: residential GUF ≈ 9.3M TEH/yr,
# commercial GUF ≈ 4.1M TEH/yr, total ≈ 13.4M TEH/yr vs. levy ≈ 6.2M TEH/yr (≈2.2×).
# tag: CHOSEN | units: TEH per Standard Land Unit per year, at ε=0.40 | family: GUF_USE_*
# form: NLSA Eq. 9 — midpoints of the manual's per-category ranges.
# note: CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These
#   were scaled ×100 from the template's abstract unit values so that
#   aggregate GUF over a 1M-population inventory (~400k residential + 20k
#   commercial parcels) lands co-equal with levy revenue at mid-arc:
#   residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈
#   6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN
#   under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was
#   retagged for the same reason on 2026-08-05 — whatever the ratios between
#   categories rest on.
# resolves_by: a stewardship-cost census — collective labour-hours per year
#   actually attributable to servicing each use category (roads, utilities,
#   inspection, dispute resolution), divided by land area. That measures the
#   quantity the fee is DEFINED as, so it settles the levels and the ratios in
#   one instrument rather than calibrating one against the other.
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
# tag: CHOSEN | units: dimensionless elasticity | family: GUF_DEMAND_ETA_*
# form: NLSA Eq. 11–13 — fee sensitivity to occupancy pressure, by land class.
# resolves_by: measured fee-to-occupancy elasticity by land class — vacancy
#   and turnover response in a jurisdiction that has actually varied its
#   ground fees.
GUF_DEMAND_ETA_RESIDENTIAL: float = 0.15   # sensitivity for residential land
GUF_DEMAND_ETA_COMMERCIAL:  float = 0.25   # sensitivity for commercial land
# tag: CHOSEN | units: dimensionless multiplier
# form: NLSA Eq. 11–13 — a constitutional CEILING on D(p), not an estimate of
#   it.
# resolves_by: a charter decision, not a measurement. It bounds how far demand
#   pressure may lift a fee above its reference; 1.80 is the framework's own
#   judgement about tolerable variation and should be argued, not fitted.
GUF_DEMAND_D_MAX:           float = 1.80   # constitutional ceiling on D(p)

# Zone adjustment factor permitted range (NLSA §2.4.1)
# tag: CHOSEN | units: dimensionless multiplier | family: GUF_ZONE_M*
# form: NLSA §2.4.1 — the permitted band for a collective's local zone
#   adjustment: governance headroom, not an estimated quantity.
# resolves_by: a charter decision on how much local discretion the schedule
#   allows. No measurement settles a permitted range — the honest pointer is
#   the deliberation, and pretending otherwise would be the error.
GUF_ZONE_MIN: float = 0.80
GUF_ZONE_MAX: float = 1.25

# Ecosystem service replacement cost (κ) reference values at ε=0.40 (NLSA Eq. 14-15)
# These are κ_s(ε=0.40); the full ε-arc is derived in ecosystem_service_kappa().
# tag: CHOSEN | units: TEH per megalitre per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: crew-hours to operate treatment capacity delivering equivalent
#   filtration — a plant staffing schedule, not a valuation study.
GUF_ECO_KAPPA_WATER_FILTRATION:  float = 1.650   # TEH/ML/yr
# tag: CHOSEN | units: TEH per cubic metre of retention per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: crew-hours to build and maintain engineered retention of equal
#   volume, amortized over its design life.
GUF_ECO_KAPPA_FLOOD_ATTENUATION: float = 0.006   # TEH/m³/yr
# tag: CHOSEN | units: TEH per tonne CO₂-equivalent per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: CDR_LABOR_HOURS_PER_TONNE, already in this file at 0.6 h/t from
#   plant staffing disclosures. This constant is 2.750 — a 4.6× disagreement
#   between two labour-hours-per-tonne-CO₂ figures in the same repo, on the
#   same quantity. One of them is wrong and nothing currently reconciles them.
GUF_ECO_KAPPA_CARBON:            float = 2.750   # TEH/tonne-CO₂eq/yr
# tag: CHOSEN | units: TEH per tonne particulate per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: operating hours for filtration capacity of equal removal rate.
GUF_ECO_KAPPA_AIR_QUALITY:       float = 5.500   # TEH/tonne-particulate/yr
# tag: CHOSEN | units: TEH per hectare-equivalent per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: measured hand-pollination labour per hectare, which is the one
#   service in this table with a directly observed human-substitute cost
#   (Sichuan pear orchards, Maoxian).
GUF_ECO_KAPPA_POLLINATION:       float = 1.000   # TEH/ha-equiv/yr
# tag: CHOSEN | units: TEH per Habitat Quality Unit per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: nothing yet, and this is the weakest of the seven — a Habitat
#   Quality Unit is a framework construct, so the pointer has to define the
#   unit before it can price it. Managed-reserve staffing per unit area is the
#   nearest observable.
GUF_ECO_KAPPA_BIODIVERSITY:      float = 0.350   # TEH/HQU/yr
# tag: CHOSEN | units: TEH per cooling-degree-day per year, at ε=0.40
# form: NLSA Eq. 14–15.
# resolves_by: operating and maintenance hours for mechanical cooling
#   delivering the same degree-day offset. Note the thermal layer treats this
#   quantity as a physical budget rather than a service (research/thermal.py)
#   — the two readings have not been reconciled.
GUF_ECO_KAPPA_THERMAL:           float = 0.030   # TEH/cooling-degree-day/yr

# Ecosystem service automation sensitivity β_s — exponent in κ(ε) decay (NLSA Eq. 15)
# tag: CHOSEN | units: dimensionless exponent | family: GUF_ECO_BETA_*
# form: NLSA Eq. 15 — how fast each service's replacement cost falls with
#   automation. The ORDERING is an argument the framework makes (physical
#   treatment automates readily; pollination and biodiversity resist it, the
#   same Baumol logic that bounds care abatability in Block II); the
#   magnitudes are not constrained by anything.
# resolves_by: per-service labour intensity of the replacement task measured
#   at two or more automation levels. Until then the ordering is the claim and
#   the values are placeholders that happen to encode it.
GUF_ECO_BETA_WATER_FILTRATION:  float = 0.8
GUF_ECO_BETA_FLOOD_ATTENUATION: float = 0.7
GUF_ECO_BETA_CARBON:            float = 0.9
GUF_ECO_BETA_AIR_QUALITY:       float = 1.0
GUF_ECO_BETA_POLLINATION:       float = 0.6
GUF_ECO_BETA_BIODIVERSITY:      float = 0.7
GUF_ECO_BETA_THERMAL:           float = 0.8

# Irreducible human-judgment floor for ecosystem κ — fraction of reference value
# At post-scarcity, some ecological judgment remains irreducibly human.
# tag: CHOSEN | units: fraction of the reference κ
# resolves_by: the residual human oversight hours in the most automated
#   environmental-management operation observable. Same structural claim as
#   GUF_ALPHA_FLOOR and PERSONAL_EOH_COMPONENTS' care abatability ceiling —
#   that judgment does not automate to zero — reached here for a third time
#   and still without a measurement behind any of the three.
GUF_ECO_KAPPA_FLOOR_FRACTION: float = 0.10

# Infrastructure proximity distance-decay rates μ_k (km⁻¹) (NLSA Eq. 16)
# tag: CHOSEN | units: per kilometre | family: GUF_INFRA_MU_*
# form: NLSA Eq. 16 — exponential decay of infrastructure benefit with
#   distance.
# resolves_by: measured catchment gradients — transit ridership, utility
#   connection cost, and park usage against distance. All three are routinely
#   measured by transport and planning agencies; none has been ingested here.
GUF_INFRA_MU_TRANSIT:      float = 0.5
GUF_INFRA_MU_UTILITIES:    float = 0.2
GUF_INFRA_MU_PUBLIC_SPACE: float = 0.8

# Cross-collective infrastructure ownership factor (NLSA Eq. 25b)
# tag: CHOSEN | units: fraction of infrastructure burden attributed externally
# form: NLSA Eq. 25b.
# resolves_by: a federation cost-allocation study — the share of a parcel's
#   infrastructure benefit physically supplied by a neighbouring collective.
#   In the polycentric model (research/coasean.py) this is a settlement
#   question between collectives, so it resolves by agreement as much as by
#   measurement.
GUF_CHI_EXTERNAL: float = 0.30

# Review cycle rate cap — max GUF increase per 5-year cycle (NLSA Eq. 21)
# tag: CHOSEN | units: fraction increase per 5-year review cycle
# form: NLSA Eq. 21.
# resolves_by: a charter decision. A rate cap is a commitment about how fast a
#   leaseholder can be asked to absorb change, which is deliberation, not
#   measurement. Precedent exists in statutory rent-review caps.
GUF_REVIEW_CYCLE_CAP: float = 0.10

# Income-linked subsidy thresholds for primary residential parcels (NLSA Eq. 24)
# tag: CHOSEN | units: fraction | family: GUF_SUBSIDY_*
# form: NLSA Eq. 24 — a taper from a lower income threshold to a floor rate.
# resolves_by: a charter decision on the subsidy schedule. Distributional
#   thresholds are political commitments; the measurable input is the income
#   distribution they are applied to, not the thresholds themselves.
GUF_SUBSIDY_LOWER_THRESHOLD: float = 0.40  # below 40% of median → maximum subsidy
GUF_SUBSIDY_FLOOR_RATE:      float = 0.25  # subsidized leaseholders pay 25% of GUF
# tag: CHOSEN | units: fraction of income
# form: NLSA Eq. 24 — the accessibility test on a primary residence.
# resolves_by: a charter decision, with a strong external analogue: 25%
#   mirrors the housing-cost-burden convention in national housing statistics
#   (the US 30% burden threshold is the better-known variant). Adopting a
#   published threshold explicitly would move this to `convention`.
GUF_AFFORDABILITY_THRESHOLD: float = 0.25  # GUF ≤ 25% of income = accessible primary housing

# Agricultural soil-health credit rate (NLSA Eq. 26); symbol c_soil in equations
# tag: CHOSEN | units: TEH per Standard Land Unit per unit Soil Health Index gain
# form: NLSA Eq. 26.
# resolves_by: measured labour-hours of soil-building practice (cover
#   cropping, reduced tillage, amendment) per unit index gain — an agronomic
#   trial with a labour diary. Agricultural extension services run the trials;
#   the labour column is the part usually missing.
GUF_SOIL_CREDIT_RATE: float = 0.05  # TEH/SLU per unit improvement in Soil Health Index

# Ecological write-down parameters (NLSA §9)
# tag: CHOSEN | units: years
# form: NLSA Eq. 28 — Y_r, the design life over which replacement
#   infrastructure is amortized.
# resolves_by: engineering design lives for the specific replacement asset
#   class. ASSET_TYPES in this file already carries measured-order threshold
#   ages for comparable classes, so this one is reconcilable against a table
#   we ship.
GUF_WRITEDOWN_AMORTIZATION_YEARS: float = 50.0  # Y_r: replacement infra design life (Eq. 28)
# tag: CHOSEN | units: fraction of ecological EOH left unfulfilled
# form: NLSA §9.8 — the preventive monitoring trigger.
# resolves_by: an observed relationship between deferred stewardship and
#   ecosystem regime shift. ECOLOGICAL_THRESHOLD in this file makes the same
#   class of claim on the state variable rather than the deferral rate, and
#   neither is measured; both would resolve from the same ecological time
#   series.
GUF_EOH_ACCUMULATION_THRESHOLD:   float = 0.30  # 30% unfulfilled ecological EOH triggers warning (§9.8)

# ---------------------------------------------------------------------------
# Dashboard health indicator thresholds
# Dashboard.py owns the logic; data.py is the single numeric source.
# Stress tests also reference COMPOUNDING_CRIT.
#
# EVERY CONSTANT IN THIS BLOCK IS CHOSEN, and that is the honest reading rather
# than a gap. These set where an indicator turns YELLOW or RED — they govern when
# the framework raises its hand, not what is physically true. A threshold is a
# judgement about tolerable risk by construction, so "measure it" is the wrong
# demand; the right demand is that each be argued, and that the quantity it
# watches be measured. Where a threshold could be derived from a modelled quantity
# rather than picked, that is said on the line.
# ---------------------------------------------------------------------------
# provenance-block: Dashboard health thresholds
# tag: CHOSEN | units: fraction of EOH deferred | family: DEFERRED_RATIO_*
# resolves_by: an observed relationship between deferral and unrecoverable
#   degradation — the point past which deferred maintenance stops being
#   catch-up work and becomes replacement. scenarios/recovery.py models the
#   recovery side, so the crossover is derivable in-model rather than needing
#   new data.
DEFERRED_RATIO_WARN:       float = 0.10   # YELLOW: 10% deferred
DEFERRED_RATIO_CRIT:       float = 0.25   # RED: 25% deferred
# tag: CHOSEN | units: registration share (fraction of human EOH admitted to the ledger) | family: REGISTRATION_*
# resolves_by: a charter decision on the minimum ledger coverage that keeps
#   TEH circulating meaningfully. Note these are ε-INVARIANT while
#   total_registration_share(ε) is low by design at low ε, so at subsistence
#   the indicator reads RED for a state the framework considers correct.
REGISTRATION_WARN:         float = 0.35   # YELLOW below 35%
REGISTRATION_CRIT:         float = 0.20   # RED below 20%
# tag: CHOSEN | units: fraction of original EOH added by compounding | family: COMPOUNDING_*
# resolves_by: the compounding rate at which ASSET_TYPES' power-law escalation
#   outruns any feasible maintenance response — derivable from that table plus
#   a labour-supply constraint, so this is a wiring debt rather than a data
#   debt.
COMPOUNDING_WARN:          float = 0.20   # YELLOW: compounding adds >20% of original
COMPOUNDING_CRIT:          float = 0.50   # RED: compounding adds >50% (spiral risk)
# tag: CHOSEN | units: purchasing-power index (1.0 = parity)
# form: the threshold is ε-scaled, threshold = 1 + slope × ε, because
#   purchasing power is expected to RISE across the arc — so a flat 1.05 would
#   pass trivially at high ε.
# resolves_by: a charter decision on how much purchasing-power gain the arc is
#   expected to deliver before the absence of it counts as a warning.
PP_INDEX_WARN:             float = 1.05                            # YELLOW threshold at ε=0.40 reference
# tag: derived | units: purchasing-power index per ε unit
# form: (PP_INDEX_WARN − 1.0) / 0.40 — the slope through the ε=0.40 reference
#   point that makes the threshold 1.0 at ε=0.
# resolves_by: n/a — it inherits PP_INDEX_WARN's standing by construction.
PP_INDEX_WARN_SLOPE:       float = (PP_INDEX_WARN - 1.0) / 0.40  # per-ε slope: threshold = 1 + slope×ε
# tag: CHOSEN | units: fraction of the sufficiency guarantee covered by levy
# note: set at 2%, and the shipped SUFF_LEVY_RATE covers ≈2% of the guarantee
#   at canonical defaults — so this indicator is calibrated to sit just at the
#   value it watches. It will not warn about the configuration it was drawn
#   around.
# resolves_by: a charter decision on the minimum share of the guarantee that
#   current labour should fund, rather than the Trust dividend. That is a real
#   solvency question and deserves a threshold argued independently of the
#   default.
LEVY_SUFFICIENCY_WARN:     float = 0.02   # YELLOW if levy covers < 2% of guarantee
# tag: CHOSEN | units: fraction of care-registration saturation | family: CARE_ADMISSION_*
# resolves_by: a charter decision on how much care must be on the ledger
#   before admission counts as working. The quantity watched resolves with
#   CARE_SIGMOID_DEFAULTS; the thresholds are the framework's own bar.
CARE_ADMISSION_GREEN_FRAC: float = 0.20   # care share ≥ 20% of saturation → GREEN
CARE_ADMISSION_YELLOW_FRAC: float = 0.10  # care share ≥ 10% of saturation → YELLOW

# ---------------------------------------------------------------------------
# Contestability invariant (reconciliation §8)
# Functional forms proposed, not calibrated from data — see research/contestability.py.
# ---------------------------------------------------------------------------
# provenance-block: Contestability (reconciliation §8)
# tag: CHOSEN | units: TEH per person
# form: K_entry(0) — the founding cost of a viable alternative collective at
#   ε=0. Set at ≈1.2× the annual sufficiency guarantee per person.
# resolves_by: observed founding capitalization of real cooperatives and
#   intentional communities per member. Mondragon and the Italian co-op sector
#   (already cited in this file for COASEAN_COMMONS_TITHE and the indivisible
#   reserve) both publish enough to bound it, which makes this one of the more
#   closable debts here.
CONTESTABILITY_K0_TEH: float = 1_800.0          # founding cost of a viable alternative collective at ε=0 (TEH/person)
# tag: CHOSEN | units: fraction of K₀ per ε unit
# form: the ADVERSARIAL increasing-returns regime — K_entry rises with
#   automation because incumbents' capital advantage compounds. Chosen as the
#   default because it is the hostile case; the replicable regime is the
#   optimistic one.
# note: the regime is the honest uncertainty, not the slope (reconciliation
#   §8.5). Nothing in the data settles which regime a real automation arc
#   follows, and the two give opposite answers about whether exit stays
#   viable.
# resolves_by: measured entry costs in an industry across an automation
#   transition.
CONTESTABILITY_K_SLOPE: float = 1.6             # how fast K_entry scales per unit ε
# tag: CHOSEN | units: fraction of K₀
# form: in the replicable regime K_entry falls, but not to zero — there is
#   always some minimum founding cost. Structural in that respect, asserted in
#   level.
# resolves_by: the cheapest observed viable founding, which is the empirical
#   floor.
CONTESTABILITY_K_FLOOR_FRACTION: float = 0.10   # minimum K_entry as fraction of K0 (replicable regime floor)
# tag: CHOSEN | units: dimensionless χ ratio | family: CONTESTABILITY_CHI_*
# form: CRIT at 1.00 is definitional, not chosen — χ < 1 means the portable
#   endowment cannot cover entry, so exit is notional rather than substantive.
#   WARN at 1.20 is an early-warning margin and is chosen.
# resolves_by: n/a — SUPERSEDED. §8.9 replaced the ratio with a TIME (t_exit ≤
#   one vesting period), because a stock target against a flow yields a time,
#   not a ratio. core/dashboard.py now demotes χ to a YELLOW advisory when
#   exit_financeable is supplied.
CONTESTABILITY_CHI_WARN: float = 1.20           # χ below → YELLOW
CONTESTABILITY_CHI_CRIT: float = 1.00           # χ below → RED (invariant breached)
# tag: CHOSEN | units: fraction of automation value held in common
# form: φ(0) — even at subsistence some automation value is commonly held (the
#   Trust baseline).
# resolves_by: n/a in the adopted model — §8.9b makes φ(ε) emerge from the
#   charter formation share under a stated policy (dilution / target /
#   escalated) rather than from a floor plus a power law. Kept for the
#   superseded arm.
CONTESTABILITY_PHI_FLOOR: float = 0.10          # minimum commonized fraction at ε=0
# tag: CHOSEN | units: dimensionless power
# form: sub-linear growth of commonization early in the arc (ε^1.5 rather than
#   ε), asserting that political-economy constraints make rapid commonization
#   hard.
# resolves_by: n/a — superseded by the charter-formation model, as above.
CONTESTABILITY_PHI_EXPONENT: float = 1.5        # power for φ(ε) = floor + (1−floor) × ε^n
# tag: CHOSEN | units: fraction per year
# form: g_priv, the private capital growth rate. The Piketty-inversion
#   condition requires dτ/dε ≥ 0, i.e. the Trust must grow faster than private
#   capital.
# note: at canonical defaults the levy-alone path to that condition is
#   infeasible (levy_fraction ≫ 1) — the adversarial finding of reconciliation
#   §8.3, and §8.9 showed the failure was the miscalibrated cash-Trust frame
#   rather than the levy. §8.9c then found endogenous g_priv turns NEGATIVE
#   past ε≈0.5, so this fixed 3% is not the operative reading in the adopted
#   model.
# resolves_by: real capital returns net of depreciation for the jurisdiction
#   being modelled; Piketty's r series is the standard source and gives 4–5%
#   historically.
CONTESTABILITY_G_PRIV: float = 0.03             # assumed private capital growth rate per unit ε
# tag: CHOSEN | units: fraction per year
# form: the annual yield on automated capital, used to compute
#   automated_output_teh = ε × capital_stock × yield.
# resolves_by: 1/RECAL_CAPITAL_OUTPUT_RATIO − FORMATION_DEPRECIATION_RATE =
#   0.20 is the same quantity derived elsewhere in this file, against 0.10
#   here. A 2× disagreement between two capital-yield constants in one repo;
#   they should be reconciled to one derivation.
CONTESTABILITY_CAPITAL_YIELD_RATE: float = 0.10 # automated-capital annual yield rate assumption
# tag: CHOSEN | units: years of federation tenure
# form: linear vesting of the Trust dividend. Tenure is FEDERATION-wide
#   (reconciliation §8.7b): moving between collectives never resets the clock
#   or forfeits vested balance, and the sufficiency floor never vests at all —
#   it is membership-independent (§8.1). Matches
#   TIER_ASSESSMENT_INTERVAL_YEARS.
# resolves_by: a charter decision. Shorter vesting strengthens the marginal
#   member's exit directly, so this is the cheapest lever on contestability
#   the framework has — which is exactly why it belongs in deliberation and
#   not in a data pointer.
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
# provenance-block: Coasean federation (reconciliation §§6–7)
# tag: CHOSEN | units: number of collectives
# form: N(0) — the collective count at maximum fragmentation, consolidating
#   toward N=1 as ε→1 (the existing single-ledger model is that limit case).
# note: a working hypothesis from reconciliation §6, explicitly NOT derived
#   from institutional data. The real count depends on governance, geography
#   and transaction-cost structure, which is the Coasean question the block is
#   named for.
# resolves_by: an institutional study of collective scale against coordination
#   technology — the empirical form of Coase's boundary-of-the-firm question.
COASEAN_N_MAX: int = 20            # collective count at ε=0 (maximally fragmented)
# tag: CHOSEN | units: dimensionless exponent
# form: N(ε) = max(1, round(N_max × (1−ε)^exp)). Linear by default: the count
#   consolidates in proportion to automation. Higher values front-load
#   consolidation.
# resolves_by: as for COASEAN_N_MAX — the same study settles both, and neither
#   is independently identifiable without it.
COASEAN_BOUNDARY_EXPONENT: float = 1.0   # exponent in N(ε) = max(1, round(N_max×(1−ε)^exp))
# tag: CHOSEN | units: fraction of period TEH creation
# form: each collective's inter-collective reserve, consumed by
#   settlement_check() for imbalance settlement. Analogous to a central-bank
#   FX reserve ratio.
# resolves_by: observed reserve ratios in monetary unions and clearing
#   systems, which is a real and well-documented comparator.
COASEAN_RESERVE_FRACTION: float = 0.10  # fraction of TEH created held in inter-collective reserve
# tag: CHOSEN | units: fraction of the debtor collective's reserve
# form: the bilateral net-flow credit ceiling (the paper's
#   bilateral-imbalance-ceiling sketch, reconciliation §9-item-4). Within it
#   trade continues on credit; beyond it settlement from reserve is required.
# resolves_by: observed bilateral credit limits in real clearing unions — the
#   European Payments Union and regional ACUs set exactly this parameter, so
#   the precedent is concrete.
COASEAN_IMBALANCE_CEILING: float = 0.50  # bilateral net-flow ceiling as fraction of the deficit
                                         # collective's reserve; beyond it settlement is required
                                         # (paper's bilateral-imbalance-ceiling sketch, recon. §9-item-4)
# tag: CHOSEN | units: dimensionless slope
# form: factor = 1/(1 + slope × excess_ratio) — exchange-rate depreciation per
#   unit of unsettled imbalance beyond the ceiling. Makes over-issuance a
#   visible exchange rate movement, which is reconciliation §7's
#   transition-regime claim: inflation between collectives shows up as FX, not
#   as a broken price identity.
# resolves_by: a proposed functional form, not calibrated from anything.
#   Observed depreciation against payment-imbalance data would settle the
#   slope; the FORM is the substantive claim and it is the part worth arguing.
COASEAN_DEPRECIATION_SLOPE: float = 0.20 # exchange-rate depreciation per unit of unsettled imbalance
                                         # beyond the ceiling (relative to reserve) — over-issuance
                                         # exports depreciation honestly (recon. §7 transition regime)

# ---------------------------------------------------------------------------
# Federation commons tier (reconciliation §8.7 a/c; research/coasean.py Phase 4)
# Calibration knobs with cooperative-law precedent, not physics.
# ---------------------------------------------------------------------------
# tag: convention | units: fraction of each collective's common-fund levy revenue
# form: the tithe passed up to the federation commons (reconciliation §8.7a).
#   Adopted from Italian Law 59/1992, which requires cooperatives to
#   contribute 3% of annual surplus to the mutualistic funds — a real
#   statutory rate, and the only real-world calibration point for a
#   federation-level mutual levy. Tagged `convention` rather than CHOSEN
#   because it names a specific external instrument.
# note: honest adversarial finding, reported not tuned — at 3% the commons
#   floor coverage is tiny, so the federation commons cannot carry the
#   sufficiency floor at the precedent rate.
# resolves_by: n/a as a convention. Departing from 3% would make it CHOSEN and
#   require its own argument.
COASEAN_COMMONS_TITHE: float = 0.03      # fraction of each collective's common-fund levy revenue passed
                                         # up to the federation commons. Precedent: Italian Law 59/1992
                                         # requires co-ops to contribute 3% of surplus to mutual funds.
# tag: convention | units: fraction of a collective's trust
# form: the unallocated (indivisible) share, credited to no individual capital
#   account, escheating to the federation commons on merger/split/dissolution
#   (reconciliation §8.7c). Adopted from Italian co-op law's statutory ~30%
#   indivisible legal reserve. The allocated remainder follows members'
#   accounts.
# note: the model tracks no individual accounts, so a named fraction is the
#   minimal honest allocated/unallocated split — a tenure-derived fraction
#   would be false precision. Adversarial finding: consolidation escheat
#   drains per-collective dividends, so the worst marginal χ worsens toward
#   ε→1 even as total τ holds.
# resolves_by: n/a as a convention, per COASEAN_COMMONS_TITHE.
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
# tag: CHOSEN | units: persons
# form: the smallest population that can staff a viable alternative collective
#   — run the four-domain EOH pipeline with a full age distribution and a
#   governance quorum. Deliberately far below Coasean-efficient scale at any
#   ε: a viable alternative need only clear MINIMUM scale, accepting a
#   coordination-cost disadvantage. Requiring optimal scale would make the
#   entry threat vacuous at high ε, because the "alternative" would have to be
#   the whole economy.
# resolves_by: derive it from this repo's own machinery rather than measure it
#   — COMPETENCY_THRESHOLD × ESSENTIAL_DOMAINS with a full age distribution
#   gives a minimum headcount directly. UNCALIBRATED research placeholder
#   until that is wired.
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
# tag: CHOSEN | units: fraction of the federation commons per period
# form: the ceiling on entry underwriting (§8.8 M2). The remainder stays as
#   the sufficiency-floor backstop (§8.7a) — underwriting must never empty the
#   fund that backs the floor. Underwritten capital moves commons → new
#   collective trust, staying commonized and indivisible (§8.7c), never
#   becoming a personal claim.
# resolves_by: a charter decision on the split between underwriting and
#   backstop. It is a prudential limit, so it resolves by argument — but the
#   ARGUMENT can be made quantitative: the backstop needs to cover the floor
#   at the worst modelled drawdown, which is computable from the fiscal layer.
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
# provenance-block: Recalibration and charter formation (§8.9)
# tag: convention | units: years (capital stock per unit annual output)
# form: ν in K(ε) = K₀ + ν·Y(ε). Adopted from Piketty's β (national capital /
#   national income), observed at ≈4–6 across economies; the LOW end is taken
#   as the adversarially-cheap-capital posture, because a smaller commons
#   weakens the underwriting arm. Tagged `convention` because it names a
#   specific measured external series and then picks its conservative edge.
# note: this fixed §8.8 open item 3 at the root — the old frame held an
#   ε=0-era stock fixed while ε rose, giving τ = 17.5 for a quantity DEFINED
#   as a share ≤ 1.
# resolves_by: the capital/income ratio for the jurisdiction being modelled.
#   Moving to the middle of the observed range would strengthen the commons,
#   so the choice is deliberately unflattering to the framework's own result.
RECAL_CAPITAL_OUTPUT_RATIO: float = 4.0  # ν: capital stock required per unit of annual machine output
                                         # (K_machine = ν·Y_machine). Precedent: Piketty's β (national
                                         # capital / national income) ≈ 4–6 across observed economies;
                                         # low end chosen as the adversarially-cheap-capital posture
                                         # (smaller K → smaller commons → weaker underwriting arm).
# tag: CHOSEN | units: ε per year
# form: arc speed dε/dt — a ~50-year subsistence→post-scarcity transition.
#   Converts per-ε acquisition needs into per-year flows, and faster arcs
#   tighten acquisition feasibility LINEARLY, so this is a real lever on every
#   §8.9 result.
# resolves_by: UNCALIBRATED placeholder. It could be derived rather than
#   chosen: research/formation.py already produces a realized pace from
#   financed capacity (canonical ≈47 yr under the null anchor), so the
#   endogenous arc speed exists in the repo and this constant should follow
#   it.
RECAL_EPSILON_RATE_PER_YEAR: float = 0.02
                                         # arc speed dε/dt: a ~50-year subsistence→post-scarcity
                                         # transition. UNCALIBRATED placeholder — converts per-ε
                                         # capital-acquisition needs into per-year flows; faster arcs
                                         # tighten acquisition feasibility linearly.
# tag: CHOSEN | units: hours per year
# form: hours a floor-backed founder can devote to building an alternative
#   collective (≈2/3 of PERSONAL_EOH_BASE, leaving the rest for personal EOH).
#   The sufficiency floor is what frees this labour — the floor IS the entry
#   finance of the low-ε arc, which is the substantive claim.
# note: it is pinned to a fraction of PERSONAL_EOH_BASE without being bound to
#   it, so the 2026-08-06 reprice 1500 → 1000 left this at 1,000 — now the
#   WHOLE base rather than two-thirds of it. The stated rationale and the
#   value have drifted apart; caught by this migration.
# resolves_by: UNCALIBRATED placeholder. Time-use data on discretionary hours
#   available to subsistence-floor recipients would settle it.
RECAL_FOUNDING_LABOR_HOURS: float = 1_000.0
                                         # hours/yr a floor-backed founder can devote to building an
                                         # alternative collective (≈ 2/3 of PERSONAL_EOH_BASE, leaving
                                         # the rest for personal EOH). The sufficiency floor is what
                                         # makes this labor available — the floor IS the entry finance
                                         # of the low-ε arc. UNCALIBRATED placeholder.
# tag: CHOSEN | units: years
# form: exit must be financeable within one vesting period (=
#   CONTESTABILITY_VESTING_YEARS): a member who joins can accumulate the means
#   to leave by the time they fully vest. THIS IS THE RC4 FIX — a stock target
#   (K_entry) against a flow (savable income) yields a TIME, not a ratio, and
#   the retired χ = P/K_entry demanded the founding stock be covered by ONE
#   year of flow, which made the invariant nearly unclosable.
# resolves_by: a charter decision, bound to the vesting period rather than set
#   independently. The substantive commitment is "within one vesting period",
#   not the number 5 — so this resolves whenever CONTESTABILITY_VESTING_YEARS
#   does.
RECAL_EXIT_HORIZON_YEARS: float = 5.0    # exit must be self-financeable within one vesting period
                                         # (= CONTESTABILITY_VESTING_YEARS): a member who joins can
                                         # accumulate the means to leave by the time they fully vest.
                                         # This is the RC4 fix — a stock target (K_entry) against a
                                         # flow (savable income) yields a TIME, not a ratio; the old
                                         # χ = P/K_entry demanded the stock be covered by ONE year of
                                         # flow, which made the invariant nearly unclosable (§8.8 RC4).
# tag: convention | units: fraction of the annual per-capita dividend
# form: the share credited to the member's individual capital account (a
#   stock, per §8.7b) rather than paid as cash. Zero-interest per Condition
#   III: the account is a sum of credits, never compounded. Adopted from
#   Mondragon's internal capital accounts, which retain a share of each year's
#   surplus to member accounts.
# resolves_by: n/a as a convention — but the 0.50 is rounder than Mondragon's
#   actual practice, so the precedent supports the MECHANISM more strongly
#   than the level.
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
# tag: derived | units: fraction of a decedent's private capital estate
# form: set EQUAL to ESTATE_LEVY_FRACTION — capital estates are treated
#   exactly like TEH estates, so this is the existing D5 doctrine extended to
#   capital rather than a new rule. That is the whole point of the value, and
#   it should be bound to ESTATE_LEVY_FRACTION rather than restated as a
#   literal.
# resolves_by: n/a — it inherits ESTATE_LEVY_FRACTION's standing (a charter
#   decision).
RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE: float = 0.15
                                         # share of a decedent's private CAPITAL escheating to the
                                         # commons (= ESTATE_LEVY_FRACTION: capital estates treated
                                         # exactly like TEH estates — the D5 doctrine extended, not
                                         # a new rule). Applies in the dilution/escalated policies.
# tag: CHOSEN | units: fraction of a capital estate
# form: full generational conversion while a §8.9b charter escalation is
#   active (Piketty's inheritance-tax instrument). No living holder is ever
#   divested; conversion happens at mortality speed.
# note: even at 1.0 the private-capital half-life is ≈69 years at the 1%/yr
#   death rate, so φ → target is asymptotic over generations and the exit
#   invariant never depends on reaching it. At canonical defaults the
#   escalation NEVER fires.
# resolves_by: a charter decision — the maximum is definitionally 1.0, so the
#   only question is whether full conversion is the right escalation, not what
#   number it is.
RECAL_ESCALATION_ESTATE_SHARE: float = 1.0
                                         # capital-estate escheat share while a charter escalation is
                                         # active: full generational conversion (no living holder is
                                         # ever divested; conversion happens at mortality speed).
# tag: CHOSEN | units: number of foundings financeable per period
# form: the underwriting capacity below which the charter escalates (with the
#   adversarial regime observed) — the commons must always be able to finance
#   about an order of magnitude more foundings than one, because a commons
#   that can fund exactly one alternative is not a credible entry threat.
# note: UNCALIBRATED placeholder. At canonical defaults capacity stays
#   ≈145–280, so the trigger never fires and this constant has never been
#   exercised by a shipped run.
# resolves_by: a charter decision on the credible-threat margin.
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
# provenance-block: Formation feedback (§8.9c)
# tag: derived | units: fraction per year
# form: derived from CAPITAL_MACHINE_PROFILES design lives (≈20 yr → δ ≈ 1/20)
#   — the aggregate counterpart of the per-asset lifecycle in core/capital.py.
#   Gross return on capital = 1/ν − δ = 0.25 − 0.05 = 0.20 at defaults, and
#   the commons replacement cost δ·T_K is a ≈20–24% haircut on the gross
#   dividend.
# resolves_by: n/a — it inherits CAPITAL_MACHINE_PROFILES' standing, which is
#   CHOSEN. See DEP_RATE (0.045) for the same physical quantity derived a
#   second way; the two should be reconciled to one.
FORMATION_DEPRECIATION_RATE: float = 0.05
                                         # aggregate annual depreciation of machine capital.
                                         # Derived from CAPITAL_MACHINE_PROFILES design lives
                                         # (≈ 20 yr → δ ≈ 1/20); the aggregate counterpart of the
                                         # per-asset lifecycle in core/capital.py. Gross return on
                                         # capital = 1/ν − δ = 0.25 − 0.05 = 0.20 at defaults.
# tag: CHOSEN | units: net return per year | family: FORMATION_*
# form: the linear private-supply curve — no formation below the hurdle rate,
#   all needed formation supplied at or above the full-supply rate,
#   heterogeneous hurdle rates in between. Implies the incentive-compatible
#   charter share s* = 1 − 0.10/0.20 = 0.50.
# note: THE HURDLE IS LOW BECAUSE OF CONDITION III, and that is the finding,
#   not an assumption: idle TEH earns zero interest and leaks via the
#   accumulation ceiling (D6) and estate dissolution (D5), so the opportunity
#   cost of investing is uniquely small and only risk compensation remains. A
#   fiat-like 0.18 full-supply rate gives s* ≈ 0.10 — i.e. zero interest is
#   what makes the charter affordable, quantified. Raising the hurdle toward
#   fiat levels IS the Condition III counterfactual.
# resolves_by: UNCALIBRATED placeholders. No observed economy runs at zero
#   interest with an accumulation ceiling, so there is no series to read these
#   off — the counterfactual is the argument and the sensitivity is the honest
#   output.
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
# provenance-block: Membership-terms audit thresholds (§8.7e)
# tag: derived | units: years
# form: 2 × CONTESTABILITY_VESTING_YEARS — a dividend held hostage for twice
#   the vesting period thins the marginal member's exit without formally
#   breaching χ. Should be BOUND to that constant rather than restated as
#   10.0.
# resolves_by: n/a — inherits CONTESTABILITY_VESTING_YEARS' standing.
MEMBERSHIP_VESTING_WARN_YEARS: float = 10.0     # vesting beyond 2× CONTESTABILITY_VESTING_YEARS → WARN
                                                # (dividend held hostage for a decade thins exit)
# tag: CHOSEN | units: years of exit notice | family: MEMBERSHIP_EXIT_NOTICE_*
# form: WARN at one year (friction accumulating), CRIT at three. The CRIT is
#   close to definitional under reconciliation §8.1: exit deferred three years
#   is nominal, not substantive, so the term itself breaches the invariant
#   whatever χ reads.
# resolves_by: a charter decision, with real precedent — cooperative and
#   partnership withdrawal-notice periods are documented and would give an
#   observed distribution to place these against.
MEMBERSHIP_EXIT_NOTICE_WARN_YEARS: float = 1.0  # exit notice beyond one year → WARN (exit friction)
MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS: float = 3.0  # beyond three years → CRIT (exit is nominal, not substantive)
# tag: CHOSEN | units: fraction of PERSONAL_EOH_BASE | family: MEMBERSHIP_MIN_HOURS_*
# form: WARN above half the personal entropy load, CRIT at or above the whole
#   of it. The CRIT is definitional rather than chosen: an obligation equal to
#   a person's entire entropy load is compulsion, not a membership term
#   (§9-item-7).
# note: THESE ARE FRACTIONS, SO THEY MOVED WITH THE REPRICE. At
#   PERSONAL_EOH_BASE = 1000 they are 500 and 1,000 h/yr;
#   docs/parameter_provenance.md still printed the pre-reprice 750 and 1500.
#   Caught by this migration and corrected — and the reason the gate now
#   includes a curated test over prose-restated derived figures, which a
#   value-equality check cannot see.
# resolves_by: a charter decision on the maximum obligation membership may
#   impose.
MEMBERSHIP_MIN_HOURS_WARN_FRACTION: float = 0.50  # min-hours obligation > 0.50 × PERSONAL_EOH_BASE → WARN
MEMBERSHIP_MIN_HOURS_CRIT_FRACTION: float = 1.00  # ≥ full personal EOH load → CRIT (membership is compulsion
                                                  # by definition — obligation equals the whole entropy load)
# tag: CHOSEN | units: fraction of the pro-rata dividend
# form: distributing less than a quarter of the pro-rata dividend to accounts
#   → WARN, because retention rebuilds the undistributed-commons honeypot
#   INSIDE the collective that the indivisible-reserve escheat rule exists to
#   defuse.
# resolves_by: a charter decision on minimum distribution.
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
#
# TIER IS A SUB-QUALIFIER HERE, NOT A RIVAL SCHEME. This block already wrote
# "measured (Tier A)", and the four-tag pass formalises that reading: `tier` grades
# how good a source is, so it applies only to `measured` and `CHOSEN`. A `physics`
# constant has no source to grade — it is structural or it is wrong. No thermal
# finding is revisited by this pass; only the labels are made machine-readable.
# ---------------------------------------------------------------------------
# provenance-block: Thermal sink — budget chain (P0)
# tag: physics | units: m²
# form: Earth surface area. Definitional geometry.
A_EARTH_M2: float = 5.101e14        # Earth surface area, m² (physics)
# tag: physics | units: W·m⁻²·K⁻⁴
# form: the Stefan–Boltzmann constant. A physical constant of nature.
SIGMA_SB: float = 5.670374419e-8    # Stefan–Boltzmann constant, W·m⁻²·K⁻⁴ (physics)
# tag: convention | units: seconds
# form: Δt_s for a one-year period — 365.25 d, the Julian year. A stated
#   denominator; the choice between Julian, tropical and calendar years is a
#   convention and matters at the 4th significant figure.
SECONDS_PER_YEAR: float = 3.155760e7  # Δt_s for one year (physics)

# Assessed climate inputs — CHOSEN placeholders (Guardrail I: measured, published
# with uncertainty, never negotiated). Values are for scaffolding only.
# tag: CHOSEN | tier: C | units: W·m⁻²·K⁻¹
# form: the EQUILIBRIUM climate feedback parameter. FRAME DISCIPLINE: it pairs
#   only with the equilibrium budget λ·ΔT − F. The historical 1.492 pairs with
#   a transient reading the framework rejects; mixing them inflates the
#   allowance ~6×, and thermal_lambda.budget_forcing_headroom() refuses it.
# note: BEST GUESS, AND IT STAYS ONE (checked 2026-08-05): λ_equilibrium
#   CANNOT be assessed from the shipped data. Two independent estimators of
#   the HISTORICAL feedback agree — 1.492 (ratio) and 1.693 ± 0.472
#   (regression, 53 yr) — but converting historical to equilibrium needs the
#   pattern effect, which requires pattern-forced model experiments or
#   paleoclimate constraints. Neither is derivable from ERF, EEI and GMST. The
#   value is unchanged but its POSITION is now derived: it sits below the
#   AR6-implied 1.310 (ECS 3.0 K) and below the historical energy-budget
#   estimate, so 1.2 is the CONSERVATIVE side — a lower λ means a smaller
#   budget and a LARGER obligation, and it was not flattering the result.
#   SENSITIVITY IS FIRST-CLASS: across AR6's likely ECS range the budget runs
#   from ZERO (ECS 5 K) to ~11× the shipped case. Never publish a ψ*-derived
#   figure without λ and that band.
# resolves_by: an assessed ECS with uncertainty — an EXTERNAL input, not a
#   rearrangement of what we already hold.
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
# tag: CHOSEN | tier: C | units: W·m⁻²
# form: anthropogenic well-mixed GHG forcing, at the order of AR6. Lowering it
#   raises the budget, which is finding F3: decarbonization and automation
#   headroom trade against each other.
# note: SUPERSEDED IN PRACTICE by the Path C measured values
#   (THERMAL_F_WMGHG_ERF = 3.585, IGCC 2025a, Tier A). This P0 constant is
#   retained for the scaffolding bound.
# resolves_by: a published forcing assessment — already done, see the Path C
#   block.
THERMAL_F_GHG: float = 3.0             # W·m⁻² anthropogenic well-mixed GHG forcing (order of AR6).
                                       # Epistemic pointer: greenhouse forcing assessment.
# tag: CHOSEN | tier: D | units: W·m⁻²
# form: net anthropogenic albedo forcing. Defaults to ZERO, which is a
#   placeholder standing in for a quantity that is not zero — land-use albedo
#   change is a real forcing term (IGCC assesses it at roughly −0.2 W·m⁻²).
# note: the default understates the budget rather than overstating it, so it
#   errs toward a larger obligation, which is the framework's preferred
#   direction of error.
# resolves_by: the land-use albedo term from the same IGCC synthesis already
#   shipped in reference/data/ for the other forcing constants — reachable
#   from data in hand.
THERMAL_F_ALB: float = 0.0             # W·m⁻² net anthropogenic albedo forcing; 0 default.
# tag: CHOSEN | tier: D | units: K
# form: the assessed habitability threshold.
# note: THE SINGLE MOST LEVERAGED INPUT IN THE WHOLE THERMAL LAYER. It sets
#   the overage, the drawdown job and the obligation, and it is the
#   framework's own judgment rather than a measurement. 2.0 K is adopted
#   because it keeps results stable and lands inside the indeterminate band,
#   NOT because it is assessed. It may well be judged too HIGH later, and
#   every downward revision ENLARGES the obligation (1.5 K is ~1.5× the job).
#   Assess in land extremes and convert by ÷THERMAL_TXX_PER_GMST per C6.
# resolves_by: a habitability assessment naming the variable that actually
#   binds — not a GMST round number.
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
# tag: CHOSEN | units: fraction of the thermal budget
# form: r — the share held in reserve rather than allocated. RATCHETED DOWN
#   ONLY, which is the governance property that matters more than the level: a
#   reserve that can be raised again is not a commitment.
# resolves_by: a charter decision on precautionary margin. No measurement
#   settles how much of a planetary budget to leave unspent.
THERMAL_COMMONS_RESERVE: float = 0.20  # r — fraction of budget held in reserve; ratcheted down only.
# tag: measured | tier: C | units: W (global total)
# form: the present Φ_other reference — anthropogenic heat dissipation not
#   attributable to modelled automation capital, ~0.04 W·m⁻² when spread over
#   A_EARTH_M2.
# resolves_by: a global energy-balance inventory. The order is well
#   established from primary energy consumption; the split between Φ_other and
#   Φ_auto is the framework's own partition and is where the uncertainty sits.
THERMAL_ANTHROPOGENIC_DISSIPATION_W: float = 2.0e13  # present Φ_other reference, W (~0.04 W·m⁻²).
                                                     # Epistemic pointer: energy-balance inventory.

# Thermodynamic floors ι_floor,d (J per EOH fulfilled) — CHOSEN placeholders.
# The per-domain minimum joules to fulfill one EOH by machine (E27). Ordering
# reflects the handoff: personal/infrastructure carry real caloric/enthalpy
# floors; knowledge's Landauer floor is astronomically lower (F6). ONE EOH is one
# hour of entropy-obligation-equivalent; the J/EOH mapping is the open quantity.
# Epistemic pointer: Landauer (knowledge), Carnot/enthalpy minima (infrastructure),
# caloric + heat-rejection COP (personal) — handoff §7.3 iota_floor().
# tag: CHOSEN | tier: D | units: joules per EOH fulfilled | family: THERMAL_IOTA_FLOOR_*
# form: the per-domain thermodynamic MINIMUM joules to fulfill one EOH by
#   machine (E27). Ordering follows the handoff: personal and infrastructure
#   carry real caloric and enthalpy floors, while knowledge's Landauer floor
#   is astronomically lower (finding F6). One EOH is one hour of
#   entropy-obligation-equivalent, and the J/EOH mapping is the open quantity.
# note: THE GATING UNCERTAINTY OF THE P0 LAYER, and a floor-based bound can
#   only OVERSTATE ε_max (real ι ≥ ι_floor) — so a floor bound < 1 would be
#   CONCLUSIVE (F2), while a bound ≥ 1 is inconclusive and points to the
#   measured-ι ladder rather than to changing these numbers. At non-degenerate
#   constants the bound comes back ε_max ≫ 1 → INCONCLUSIVE, which is the
#   honest P0 result: the thermodynamic floor is too low to bind automation.
# resolves_by: measured ι via the handoff §13.1 ladder D→C→B. Path C
#   (research/thermal_path_c.py) already bypasses these entirely — ι and
#   EOH_total cancel in ε_max = ε_current · budget / Φ_auto — so the measured
#   route exists and these are retained for the provable bound, not for
#   reported results.
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
# provenance-block: Thermal sink — Path C measured inputs
# tag: measured | tier: B | units: m²
# form: land area ex-Antarctica — the denominator for land-allocated ψ*.
#   Geographic rather than a free parameter, but the EXCLUSION of Antarctica
#   is a framework decision about what land can bear an allocation, not a
#   measurement.
# resolves_by: a standard geographic dataset; the figure is not in dispute.
#   What is in dispute is the exclusion rule, which ETA_LAND_MASK_THRESHOLD
#   also touches.
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
# tag: measured | tier: A | units: W·m⁻²
# form: TOTAL effective radiative forcing, IGCC 2025a p50 at time = 2025 — the
#   BUDGET basis per C4, because natural forcing consumes the habitability
#   allowance regardless of cause. Verified 2026-08-03 against the shipped
#   synthesis timeseries (`total` column). Correction C5 replaced AR6
#   2019-baseline Tier C values; the recalled 2.72 was right for the wrong
#   year.
# resolves_by: an annual IGCC refresh. Guardrail I quantity — measured,
#   published with uncertainty, never negotiated.
THERMAL_F_NET_ERF: float = 3.366       # W·m⁻² TOTAL ERF, IGCC 2025a p50, time=2025. Tier A.
# tag: measured | tier: A | units: W·m⁻² | family: THERMAL_F_NET_ERF_P*
# form: the IGCC 2025a p05/p95 bounds on total ERF. This band is what makes
#   the determinacy map computable — the layer withholds a budget where its
#   sign is undetermined across the band rather than reporting the p50 alone.
# resolves_by: an annual IGCC refresh.
THERMAL_F_NET_ERF_P05: float = 2.602   # W·m⁻² total ERF p05 — the determinacy band's lower edge.
THERMAL_F_NET_ERF_P95: float = 4.102   # W·m⁻² total ERF p95 — the determinacy band's upper edge.
# tag: measured | tier: A | units: W·m⁻²
# form: anthropogenic ERF alone, including aerosol cooling — the REMOVABLE
#   forcing, hence the defensible F3 gain basis. Carried separately from the
#   budget basis because decarbonization gain and budget consumption are
#   different questions: only the anthropogenic part is removable by labour.
# resolves_by: an annual IGCC refresh.
THERMAL_F_ANTHRO_ERF: float = 3.104    # W·m⁻² anthropogenic ERF alone (incl. aerosol cooling) —
                                       # the REMOVABLE forcing, hence the honest F3 basis. Tier A.
# tag: measured | tier: A | units: W·m⁻²
# form: well-mixed GHG ERF alone (IGCC 2025a `wmghg`) — the forward-looking
#   basis as aerosol cooling declines.
# resolves_by: an annual IGCC refresh.
THERMAL_F_WMGHG_ERF: float = 3.585     # W·m⁻² well-mixed GHG ERF alone (the forward-looking basis as
                                       # aerosol cooling declines). IGCC 2025a `wmghg`. Tier A.
# Drawdown chain (research/thermal_drawdown.py) — converting a forcing reduction
# into the labor that would deliver it. Each step is separately tiered so the
# gate's sensitivity lands on named quantities rather than one lumped constant.
# provenance-block: Thermal sink — drawdown chain
# tag: measured | tier: A | units: W·m⁻² per ln(C/C₀)
# form: DERIVED by OLS of the IGCC 2025a CO₂ ERF series on ln(concentration)
#   over 350–426 ppm (n=38) — the range a drawdown actually traverses.
#   Self-validating: the fitted intercept implies C₀ = 279.8 ppm against the
#   accepted pre-industrial 278. Myhre's classic 5.35 runs 5.2% low over this
#   range.
# resolves_by: an IGCC vintage refresh re-fits it. Moved from recalled to
#   derived in the measurement spine pass.
CO2_FORCING_COEFFICIENT: float = 5.645  # W·m⁻² per ln(C/C₀). Tier A — DERIVED this
                                       # session by OLS of the IGCC 2025a CO₂ ERF series on
                                       # ln(concentration) over 350–426 ppm (n=38), the range a
                                       # drawdown actually traverses. Self-validating: the fitted
                                       # intercept implies C₀ = 279.8 ppm against the accepted
                                       # pre-industrial 278. Myhre's classic 5.35 runs 5.2% low here.
# tag: measured | tier: A | units: ppm
# form: IGCC 2025a annual mean at 2025.
# resolves_by: an annual refresh.
CO2_CONCENTRATION_PPM: float = 425.65  # ppm, IGCC 2025a annual mean at 2025. Tier A.
# tag: derived | units: GtCO₂ per ppm
# form: atmospheric mass 5.148e18 kg × 1e-6 × (44.01/28.96 molar ratio).
#   Derivable arithmetic from physical constants, not fitted to anything.
# resolves_by: n/a — it follows from atmospheric mass and molar masses.
CO2_PPM_TO_GT: float = 7.82            # GtCO₂ per ppm. Tier B — atmospheric mass 5.148e18 kg
                                       # × 1e-6 × (44.01/28.96 molar ratio). Derivable, not fitted.
# tag: CHOSEN | tier: D | units: dimensionless gross/net ratio
# form: removing CO₂ from the air lets ocean and land sinks OUTGAS back, so
#   the gross tonnage removed exceeds the concentration drop achieved.
# note: OMITTING IT WOULD UNDERSTATE THE OBLIGATION ~2× and bias the solvency
#   gate toward passing — exactly the wrong error, which is why a Tier D
#   placeholder is carried rather than the term dropped.
# resolves_by: ESM CDR reversibility experiments (Zickfeld et al.).
CDR_GROSS_REMOVAL_FACTOR: float = 1.8  # Removing CO₂ from the air lets ocean/land sinks OUTGAS
                                       # back, so the gross tonnage exceeds the concentration
                                       # drop. Tier D placeholder. resolves_by: ESM CDR
                                       # reversibility experiments (Zickfeld et al.). Omitting it
                                       # would understate the obligation ~2× and bias the
                                       # solvency gate toward passing — exactly the wrong error.
# tag: CHOSEN | tier: C | units: GJ per tonne CO₂ removed
# form: DAC-order energy intensity; recalled range 2–6.
# resolves_by: published plant LCA. Together with CDR_LABOR_HOURS_PER_TONNE
#   this DERIVES ι_drawdown = (GJ/t)/(h/t) ≈ 6.7e9 J/EOH, so the framework's
#   drawdown ι is a function of two plant observables rather than a third free
#   placeholder.
CDR_ENERGY_GJ_PER_TONNE: float = 4.0   # GJ per tonne CO₂ removed. Tier C — DAC-order, recalled
                                       # range 2–6. resolves_by: published plant LCA.
# tag: CHOSEN | units: years
# form: the horizon over which the drawdown obligation is discharged. 40 yr
#   keeps the programme inside a single lifetime of responsibility: the
#   generation that incurred the debt discharges it, rather than booking the
#   benefit and willing the work to people who did not choose it.
# note: A REAL LEVER — the obligation scales as 1/horizon, so 30 yr is 1.33×
#   the annual load and 100 yr is 0.4×.
# resolves_by: nothing measurable. This is an ETHICAL choice about who bears
#   the work, not a technical one, and it should be argued as such — which is
#   why the pointer says so rather than naming a study that would not settle
#   it.
THERMAL_PROGRAMME_YEARS: float = 40.0  # Years over which the drawdown obligation is discharged.
                                       # **CHOSEN.** 40 yr keeps the programme inside a single
                                       # lifetime of responsibility: the generation that incurred
                                       # the debt discharges it, rather than booking the benefit and
                                       # willing the work to people who did not choose it. The
                                       # obligation scales as 1/horizon, so this is a real lever —
                                       # 30 yr is 1.33× the annual load, 100 yr is 0.4×. Epistemic
                                       # pointer: this is an ETHICAL choice about who bears the
                                       # work, not a technical one, and it should be argued as such.
# provenance-block: Thermal sink — allocation doctrine
# tag: CHOSEN | units: policy switch — "responsibility"
# form: how the global drawdown job is split across collectives.
#   "responsibility" (cumulative emissions) is chosen over "population"
#   because a collective cannot burden others with the consequences of choices
#   it made. See allocation_share().
# resolves_by: nothing measurable — a governance decision, not physics. Both
#   options are implemented so the choice is visible and reversible rather
#   than baked in.
CDR_ALLOCATION_BASIS: str = "responsibility"  # How the global job is split across collectives.
                                       # **CHOSEN, and a governance decision, not physics.**
                                       # "responsibility" (cumulative emissions) over "population"
                                       # because a collective cannot burden others with the
                                       # consequences of choices it made. See allocation_share().
# tag: CHOSEN | units: policy switch — "incl_luc"
# form: which cumulative-CO₂ measure weights responsibility. "incl_luc"
#   (fossil + cement + land-use change) is the whole atmospheric burden the
#   drawdown must remove, and it matches the forcing coefficient, which was
#   fitted to a concentration record that already reflects land use. "fossil"
#   has lower uncertainty but leaves ~33% of the burden unallocated.
# note: A LIVE EQUITY QUESTION and a sign-off item. Including land use moves
#   substantial burden onto collectives that were often converting land under
#   external demand, and the framework cannot yet trade-adjust — OWID
#   consumption-based emissions begin only in 1990, far too short for a
#   cumulative measure.
# resolves_by: consumption-based allocation once trade data supports it.
#   Recorded for live implementations to settle, not resolved by the model.
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
# tag: CHOSEN | units: policy switch — "clear_sky"
# form: which radiative-efficiency field weights a collective's land
#   allocation. Clear-sky measures the STRUCTURAL radiative transparency of
#   the column, which is what "this land's share of the sink" should mean.
#   All-sky η credits a collective for being cloudy — cloud cover is not a
#   policy lever, is partly endogenous to warming, and is the noisiest part of
#   the field, so an all-sky rule rewards weather.
# note: NOT COSMETIC — the two differ by up to 0.27 in η (RMS 0.051, p95
#   0.085), so all-sky is reported alongside as the physical reality check and
#   the per-collective gap must stay visible.
# resolves_by: a governance decision on what the allocation is meant to track.
#   The FIELDS themselves are measured (ERA5, 258 collectives); the choice
#   between them is not.
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
# tag: CHOSEN | units: ERA5 land-sea-mask fraction ∈ [0,1]
# form: lsm ≥ this counts as land (§5 decision 1: territorial sea excluded).
#   The ERA5 mask is a fraction, so a threshold is required; 0.50 is the
#   natural midpoint but it IS a threshold on a continuous field, not a
#   measurement.
# resolves_by: a governance decision on whether partly-marine cells bear an
#   allocation. The underlying field is measured (ERA5); where the line falls
#   is not.
ETA_LAND_MASK_THRESHOLD: float = 0.50  # lsm ≥ this counts as land (§5 decision 1: territorial
                                       # sea excluded). Measured; ERA5 lsm is a fraction.
# tag: CHOSEN | units: policy switch — "pro_rata"
# form: what happens to emissions belonging to no territory — international
#   shipping and aviation, 46 GtCO₂ / 2.49% of the cumulative fossil total.
#   "pro_rata" redistributes across collectives in proportion to existing
#   shares, so shares sum to 1 and no part of the obligation is left without a
#   bearer: we all inherited the world as it is. "unallocated" leaves the gap
#   open, which means the commons silently absorbs it — and silence is the
#   objection.
# resolves_by: consumption-based allocation once trade data supports it.
#   OWID's begins in 1990, and 1990-forward is where the framework will start
#   when it does.
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
# provenance-block: Thermal sink — observed climate state
# tag: CHOSEN | tier: D | units: labour-hours per tonne CO₂ removed
# form: a ~1 Mt/yr plant at ~300 staff × 2000 h. Together with
#   CDR_ENERGY_GJ_PER_TONNE this DERIVES ι_drawdown ≈ 6.7e9 J/EOH — ~4 orders
#   above the infrastructure ι floor, as expected: drawdown is
#   energy-intensive and labour-thin.
# note: A CANDIDATE FOR THE DOMAIN-BALANCE DEFECT. Either ECOLOGICAL_BASE_RATE
#   is low by 2–3 orders or this is, or both; nothing in current data settles
#   it. And note GUF_ECO_KAPPA_CARBON = 2.750 TEH per tonne-CO₂eq is the SAME
#   quantity reached from the land layer — a 4.6× disagreement inside one
#   repo, unreconciled.
# resolves_by: operator staffing disclosures.
CDR_LABOR_HOURS_PER_TONNE: float = 0.6 # Labor-hours per tonne removed. Tier D — a ~1 Mt/yr plant
                                       # at ~300 staff × 2000 h. resolves_by: operator staffing
                                       # disclosures. Together with the line above this DERIVES
                                       # ι_drawdown = (GJ/t)/(h/t) ≈ 6.7e9 J/EOH, so the framework's
                                       # ι is a function of two plant observables rather than a
                                       # third free placeholder. ~4 orders above the infrastructure
                                       # ι floor, as expected: drawdown is energy-intensive and
                                       # labor-thin.
# tag: measured | tier: A | units: W·m⁻²
# form: solar + volcanic ERF at 2025 (IGCC 2025a `natural`). Consumes budget
#   per C4 but is NOT removable by labour, so it is the floor on achievable
#   forcing and the wedge between the budget basis and the F3 gain basis
#   (§10.1).
# resolves_by: an annual IGCC refresh.
THERMAL_F_NATURAL_ERF: float = 0.262   # W·m⁻² solar + volcanic ERF at 2025, IGCC 2025a `natural`.
                                       # Tier A. Consumes budget (C4) but is NOT removable by labor —
                                       # so it is the floor on achievable forcing, and the wedge
                                       # between the budget basis and the F3 gain basis (§10.1).
# tag: measured | tier: A | units: K (GMST anomaly)
# form: observed GMST anomaly, 2015–2024 mean (IGCC 2025a). Paired with the
#   committed F/λ to expose the pipeline — the warming already bought and not
#   yet delivered (§10.3).
# resolves_by: an annual refresh.
THERMAL_GMST_OBSERVED: float = 1.23    # K observed GMST anomaly, 2015–2024 mean (IGCC 2025a). Tier A.
                                       # Paired with the committed F/λ to expose the pipeline: the
                                       # warming already bought and not yet delivered (§10.3).
# tag: measured | tier: A | units: K per K (dTXx/dGMST)
# form: land extreme amplification (C6). OLS on the ERA5/Berkeley/HadEX3 mean
#   TXx series against GMST, 1950–2025, n = 76, slope 1.483. Per-dataset
#   spread 1.33–1.57 is the honest uncertainty.
# resolves_by: annual refresh. Guardrail I quantity.
THERMAL_TXX_PER_GMST: float = 1.48     # dTXx/dGMST — land extreme amplification (C6). Measured this
                                       # session: OLS on the ERA5/Berkeley/HadEX3 mean TXx series vs
                                       # GMST, 1950–2025, n=76, slope 1.483. Per-dataset spread
                                       # 1.33–1.57 is the honest uncertainty. Tier A; Guardrail I
                                       # quantity — refresh annually.
# tag: CHOSEN | units: utilization fraction
# form: the utilization boundary separating the Standing-exposure regime.
# resolves_by: observed variance in Φ and ψ* — a measured quantity, not a
#   chosen value, and it should stop being a constant once that variance is
#   characterized.
THERMAL_U_FLOOR: float = 0.50          # utilization boundary for Standing-exposure regime. CHOSEN;
                                       # resolves_by: observed variance in Φ and ψ*, not a chosen value.
# tag: CHOSEN | units: ε (dimensionless automation fraction)
# form: the framework's current-equilibrium ε for Eq. C1 — set to the arc
#   midpoint.
# note: SUPERSEDED WHERE AN INVENTORY EXISTS.
#   thermal_capital.epsilon_current_from_inventory() derives ε from the same
#   capital that produces Φ, via civilization_epsilon, and
#   capital_thermal_ceiling() now defaults to that. This constant survives for
#   global ε_max, where no measured world capital inventory in TEH exists —
#   and there global_ceiling() reports a band over ε_current ∈ [0.2, 0.6] so
#   the chosen value travels with its sensitivity.
# resolves_by: a measured world capital inventory in TEH.
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
# provenance-block: Capital thermal profiles (§12.2 dual-output)
# tag: CHOSEN | tier: D | units: power_intensity W per TEH; embodied_energy J per TEH
# form: the two new physical fields per capital type that turn a capital stock
#   into a thermal load Φ_auto. Kept as a SEPARATE parallel dict rather than
#   merged into CAPITAL_MACHINE_PROFILES, so the established EOH capital model
#   stays visibly distinct from the experimental thermal overlay.
# note: relative ORDERING is defensible (compute and industry heavy; software
#   and monitoring light); the absolute scale is anchored only to
#   order-of-consistency with Path C's measured ~2200 W·person⁻¹ net-additive
#   dissipation, NOT fitted.
# resolves_by: power intensity ← measured energy-use intensity by capital
#   class (IEA end-use / sectoral energy balances); embodied energy ← LCA
#   inventories (ecoinvent, EPDs). Both are Path-D placeholders awaiting
#   exactly those two sources.
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
# tag: measured | tier: C | units: dimensionless net-thermal-addition coefficient
# form: κ̄ of the grid serving the capital (§8.1). Default = world
#   fossil+nuclear share (Path C, 2025). A fully flux-redirecting grid → 0,
#   because renewable generation redirects an existing flux rather than adding
#   a new one.
# resolves_by: the PHYSICAL grid mix serving the capital, not procurement
#   contracts — a collective buying renewable certificates on a fossil grid
#   still dissipates fossil heat, and κ̄ measures the electrons, not the
#   paperwork.
THERMAL_GRID_KAPPA_DEFAULT: float = 0.93  # CHOSEN/measured; resolves_by: physical grid mix, not procurement.
