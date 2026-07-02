# Parameter Provenance

Every parameter used by the EOH → TEH model, with its default value, units,
and derivation rationale. The **Kind** column distinguishes:

- **Physics** — changing this changes the model's physical claim about the world.
  These reflect choices about how entropy works; changing them requires a theoretical
  justification, not just calibration.
- **Calibration** — a knob researchers turn to fit their local economy. Change
  these to match your data; the structural behavior of the model is preserved.

Source: `hours_eoh/data.py` and `hours_eoh/params.py`.

---

## EOH Generation — Personal Domain

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `PERSONAL_EOH_BASE` | 1,500 | h/yr·person (working-age-equivalent) | Physics | Sum of estimated annual entropy-resistance labor for four necessities: food preparation and nutrition (~4 h/wk = 208 h/yr), shelter maintenance and sanitation (~3 h/wk = 156 h/yr), basic healthcare and hygiene (~4 h/wk = 208 h/yr), social reproduction and care (~18 h/wk = 936 h/yr). Total ≈ 1,508 h/yr → rounded to 1,500. Applies to working-age adults (eoh_weight=1.0); infants and elderly are weighted higher. |
| `AGE_GROUPS` (eoh_weight) | infant=3.0, child=1.5, working_age=1.0, elderly=2.5 | relative to working-age=1.0 | Physics | Infants require 3× the caregiver labor of working-age adults; elderly with age-related decline require 2.5×. These are structural multipliers on PERSONAL_EOH_BASE. |
| `AGE_GROUPS` (fraction) | infant=7%, child=16%, working_age=60%, elderly=17% | fraction of population | Calibration | Approximate OECD-country demographic default. Replace with measured census data for your jurisdiction. Age-weighted mean EOH = Σ(fraction×weight) = 1.475 → mean personal EOH = 1,500 × 1.475 = 2,213 h/yr·person. |
| `ELDERLY_EOH_EPSILON_FACTOR` | 0.05 | fraction shift per ε unit | Calibration | On the canonical arc, automation improves medicine → longer lives → slightly larger elderly fraction. A 5%/ε shift of the child→elderly fraction. Modest; secondary to the dominant ε effect in the fulfillment split. |

---

## EOH Generation — Infrastructure Domain

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `INFRA_MAINT_RATE` | 0.025 | fraction of capital stock / year | Physics | Standard infrastructure maintenance burden: ~2.5% of replacement value per year when assets are at mid-life (age_ratio=0.5, age_factor=1.5 → effective rate 3.75%). Consistent with OECD public capital maintenance norms (2–4% of stock). |
| `INFRA_AGE_FACTOR_MAX` | 2.0 | dimensionless multiplier | Physics | At age_ratio=1.0 (all assets at end of design life), maintenance burden doubles. Reflects convex aging: infrastructure requires disproportionately more labor as it approaches failure. |
| `CAPITAL_STOCK_DEFAULT` | 2,000,000,000 | TEH (1 TEH = 1 verified labor-hour) | Calibration | Default for a civilization of 1M people at ε=0: 2,000 TEH/person in capital stock. Produces infrastructure EOH ≈ 75M h/yr at mid-life (age_ratio=0.5), ≈ 8% of personal EOH. Replace with measured national-accounts capital stock for your jurisdiction. |

---

## EOH Generation — Ecological Domain

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `ECOLOGICAL_BASE_RATE` | 500,000 | h/yr (at health=1.0) | Calibration | Stewardship labor needed per year when ecosystem_health=1.0 (pristine). Anchors relative scaling; does not represent an absolute ecosystem-specific count. At default health=0.70 → baseline ≈ 714K h/yr. Replace with a measured stewardship-hours estimate for your ecosystem. |
| `ECOLOGICAL_THRESHOLD` | 0.40 | fraction (dimensionless) | Physics | Below this health level, EOH surges nonlinearly (fishery collapse, soil depletion, aquifer loss). The 0.40 threshold reflects empirical tipping-point observations in the ecology literature (Scheffer et al. 2009 on regime shifts). |
| `_ECOLOGICAL_SPIKE_INTENSITY` | 5.0 | dimensionless spike multiplier | Physics | At the threshold, EOH grows 5× faster than baseline via spike = base × 5 × ((threshold − health)/threshold)². Calibrated to produce an EOH doubling within ≈10% below threshold. |

---

## EOH Generation — Knowledge Domain

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `KNOWLEDGE_EOH_BASE` | 100,000 | h/yr (at knowledge_base_size=1.0, skill_decay=0.10, complexity=1.0) | Calibration | Knowledge maintenance EOH at ε=0 reference level. Scales proportionally with knowledge_base_size × complexity_per_unit × skill_decay_rate. At ε=0.40 canonical arc (kbs=4.6, complexity=2.44, decay=0.10): ≈ 112K h/yr. |
| `KNOWLEDGE_EPS_EXPONENT` | 2.0 | dimensionless power | Physics | complexity_per_unit grows as ε² × CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE. Quadratic growth reflects accelerating knowledge complexity as automation enables more complex systems — each increment of automation creates more complex knowledge infrastructure to maintain. |
| `skill_decay_rate` (param) | 0.10 | fraction of skills / year | Calibration | Default: 10% of the knowledge base requires renewal each year. Reflects half-life of technical skills ~7 years (0.10/yr ≈ ln(2)/7). Calibrate from measured skill obsolescence rates in your sector. |

---

## Multipliers (Condition II)

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `M_BAND_LOW` | 1.8 | dimensionless multiplier | Physics | Lower bound of constitutional multiplier band. Below 1.8, the differential between labor tiers is too small to reflect real skill differentials. |
| `M_BAND_HIGH` | 2.1 | dimensionless multiplier | Physics | Upper bound and target mean. An economy-wide mean multiplier of 2.1 means the average worker creates 2.1 TEH per EOH registered — the "standard" skill premium consistent with the four-factor formula at calibrated alpha weights. Mission Statement §"Condition II." |
| `M_MAX` | 6.0 | dimensionless multiplier | Physics | Hard constitutional cap: no individual tier may exceed 6.0. Prevents extreme inequality in TEH accumulation; limits the additive formula output 1 + Σαᵢ·fᵢ ≤ M_MAX. |
| `ALPHA_SCALE` | 5.0 | dimensionless (sum of absolute alpha coefficients) | Physics | Σαᵢ = 5.0 is calibrated so that perfect scores on all four factors (T=D=S=I=1.0) yield m = 1 + 5.0 = 6.0 = M_MAX. Default equal distribution: each αᵢ = 1.25 at ε=0. |

---

## Registration Sigmas

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `CARE_SIGMOID_DEFAULTS` (start_share) | 0.30 | fraction | Calibration | At ε=0, 30% of care labor is on the collective ledger (subsistence: informal care dominates). |
| `CARE_SIGMOID_DEFAULTS` (saturation) | 0.95 | fraction | Physics | Maximum registration share: 95% of care labor can be collectively recognized even at ε=0.99. 5% remains informal. |
| `CARE_SIGMOID_DEFAULTS` (inflection) | 0.55 | ε value | Calibration | Care labor registration inflects at ε=0.55: early automation captures production first; care registration ramps up as middle-automation tools emerge. |
| Labor weights (care/production/stewardship) | 0.30 / 0.45 / 0.25 | fraction summing to 1.0 | Calibration | Non-personal domain registration share is a weighted composite of care, production, and stewardship registration rates. Default weights reflect a service-economy labor mix. |

---

## Fiscal Parameters

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `SUFF_LEVY_RATE` | 0.0125 | fraction of labor income | Calibration | 1.25% sufficiency levy on all TEH earnings. At ε=0.40 canonical: levy_inflow ≈ 6.2M TEH/yr on 494M TEH labor income. Does NOT cover the sufficiency guarantee alone (307M TEH) — the Trust dividend fills the gap. Calibrated to be non-burdensome while building Trust reserves. |
| `TRUST_BASE_TEH` | 35,000,000,000 | TEH | Calibration | Default Trust balance for 1M population = 35,000 TEH/person. Sized so that the annual dividend (Trust × dep_rate × div_rate = 35B × 4.5% × 40% = 630M TEH) covers stewardship + ecological + guarantee obligations at mid-arc. This is the critical calibration knob for fiscal solvency. |
| `DEP_RATE` | 0.045 | fraction of Trust / year | Physics | Trust capital depreciates at 4.5%/year: the same physical capital it represents deteriorates. Combined with div_rate to split depreciation into dividend (circulated) vs. renewal (retained). |
| `DIV_RATE` | 0.40 | fraction of annual depreciation | Physics | 40% of annual Trust depreciation is paid out as dividend (circulated to holders); 60% is retained for Trust renewal. Interaction: annual_dividend = Trust × dep_rate × div_rate; annual_renewal = Trust × dep_rate × (1 − div_rate). Together: Trust erodes unless levy_inflow replaces the net. |
| `MEANINGFUL_ACTIVITY_TEH_BASE` | 120.0 | TEH/yr per recipient (at ε=0) | Calibration | Discretionary spending bonus in the sufficiency guarantee at ε=0. Provides non-participant purchasing power beyond biological EOH reimbursement. Also used as the sufficiency basket cost at ε=0 (basket_price(0) = 120 TEH/yr). |
| `MEANINGFUL_ACTIVITY_TEH_SCALE` | 1.5 | dimensionless quadratic coefficient | Calibration | meaningful_activity bonus = base × (1 + 1.5 × ε²). Quadratic growth ensures non-participants gain real purchasing power as the labor pool shrinks at high ε. At ε=0.70: bonus = 120 × (1 + 1.5 × 0.49) = 208 TEH/yr. |

---

## Labor Parameters (Condition IV)

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `H_REF` | 2,000 | h/yr | Calibration | Reference full-time work-year (50 weeks × 40 h). Used to normalize workforce-hours to TEH. |
| `H_MIN` | 260 | h/yr | Physics | Minimum annual labor obligation (Condition IV): 5 h/wk × 52 wk. Below this, a worker is not maintaining competency in their domain — knowledge EOH is unmet. |
| `COMPETENCY_THRESHOLD` | 0.155 | fraction | Physics | Minimum certified-worker fraction per essential domain. Below this, the domain is at competency risk: knowledge EOH demand amplifies and emergency registration protocols may activate. |
| `CAPITAL_FAILURE_RATE` | 0.005 | fraction of capital / year | Calibration | Fraction of capital stock that fails catastrophically each year (beyond recoverability), triggering TEH destruction (D1). Default 0.5%/yr with better monitoring at high ε slightly reducing failure rates. |

---

## Canonical Trajectory Constants (data.py `CANONICAL_*` prefix)

These define the ideal-arc reference. A real simulation diverges from this arc;
canonical_physical_state(ε) is for testing and cross-sectional analysis only.

| Constant | Value | Governs |
|---|---|---|
| `CANONICAL_CAPITAL_GROWTH_SLOPE` | 2.0 | capital_stock = 2B × (1 + 2ε) — automation requires capital investment |
| `CANONICAL_CAPITAL_AGE_DRIFT` | 0.20 | capital_age_ratio = 0.30 + 0.20ε — older assets on average as stock grows |
| `CANONICAL_ECOSYSTEM_HEALTH_BASE` | 0.90 | ecosystem_health = max(0.01, 0.90 − 0.20ε) — slight degradation under productivity pressure |
| `CANONICAL_ECOSYSTEM_HEALTH_DRIFT` | −0.20 | (see above) |
| `CANONICAL_MONITORING_CAPABILITY_BASE` | 0.50 | monitoring_capability = 0.50 + 0.50ε — improving sensing technology |
| `CANONICAL_MONITORING_CAPABILITY_SLOPE` | 0.50 | (see above) |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE` | 9.0 | knowledge_base_size = 1 + 9ε; complexity_per_unit = 1 + ε² × 9 |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_EXP` | 2.0 | (quadratic complexity growth — see knowledge_base_size formula above) |

---

## Contestability Parameters (Workstream B — `research/contestability.py`)

Added to support the contestability invariant χ(ε) = P(ε) / K_entry(ε) ≥ 1.
See `hours-reconciliation.md §8` and `notes/workstream b.md` for derivation.

| Constant | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `CONTESTABILITY_K0_TEH` | 1,800 | TEH/person | Calibration | Entry cost of founding a viable alternative collective at ε=0. Calibrated to ≈ 1.2× the annual sufficiency guarantee per person — the minimum capitalization for a collective to function. |
| `CONTESTABILITY_K_SLOPE` | 1.6 | fraction per ε unit (increasing_returns regime) | Calibration | In the adversarial increasing_returns regime, K_entry = K₀ × (1 + 1.6ε). At ε=0.99: K_entry = 1,800 × 2.584 = 4,651 TEH/person. Calibrated so that K_entry grows at roughly the rate automated capital appreciates. |
| `CONTESTABILITY_K_FLOOR_FRACTION` | 0.10 | fraction of K₀ | Physics | In the replicable regime, K_entry cannot fall below 10% of K₀ (180 TEH/person): there is always some minimum founding cost. |
| `CONTESTABILITY_CHI_CRIT` | 1.00 | dimensionless | Physics | χ < 1 means exit is notional, not substantive — the contestability invariant is breached. |
| `CONTESTABILITY_CHI_WARN` | 1.20 | dimensionless | Calibration | Early-warning threshold: χ < 1.20 triggers a yellow flag in the dashboard (χ eroding toward breach). |
| `CONTESTABILITY_PHI_FLOOR` | 0.10 | fraction | Physics | Minimum commonized fraction at ε=0: even at subsistence, 10% of automation value is held in common (Trust baseline). φ(ε) = 0.10 + 0.90 × ε^1.5 → φ(0.99) ≈ 0.996. |
| `CONTESTABILITY_PHI_EXPONENT` | 1.5 | dimensionless power | Calibration | Sub-linear growth of commonization in early arc (ε^1.5 rather than ε) ensures a gentle ramp — political economy constraints make rapid commonization difficult. |
| `CONTESTABILITY_G_PRIV` | 0.03 | fraction / year | Calibration | Private capital growth rate (g_priv): 3%/yr real. The Piketty-inversion condition requires dτ/dε ≥ 0, i.e., Trust must grow faster than private capital. At canonical defaults, the levy-alone path is infeasible (levy_fraction >> 1) — the adversarial finding (reconciliation §8.3). |
| `CONTESTABILITY_CAPITAL_YIELD_RATE` | 0.10 | fraction / year | Calibration | Automated capital yield rate: 10%/yr. Used to compute automated_output_teh = ε × capital_stock × yield for the Piketty-inversion levy calculation. |

## Coasean Federation Parameters (Workstream D / Phase 3 — `research/coasean.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `COASEAN_N_MAX` | 20 | collectives | Calibration | Collective count at ε=0 (maximally fragmented). A working hypothesis from reconciliation §6, not derived from institutional data — the real count depends on governance, geography, and transaction-cost structure. Calibration knob, not physics. |
| `COASEAN_BOUNDARY_EXPONENT` | 1.0 | dimensionless | Calibration | Exponent in N(ε) = max(1, round(N_max × (1−ε)^exp)). Linear default: collective count consolidates in proportion to automation. Higher values front-load consolidation. |
| `COASEAN_RESERVE_FRACTION` | 0.10 | fraction of TEH created | Calibration | Share of each collective's period TEH creation held as inter-collective reserve, consumed by `settlement_check()` for imbalance settlement. Analogous to a central-bank FX reserve ratio. |
| `COASEAN_IMBALANCE_CEILING` | 0.50 | fraction of debtor reserve | Calibration | Bilateral net-flow credit ceiling (paper's bilateral-imbalance-ceiling sketch, reconciliation §9-item-4). Within it, trade continues on credit; beyond it, settlement from reserve is required. |
| `COASEAN_DEPRECIATION_SLOPE` | 0.20 | dimensionless | Calibration | Exchange-rate depreciation per unit of unsettled imbalance beyond the ceiling: factor = 1/(1 + slope × excess_ratio). Makes over-issuance a visible exchange-rate movement (reconciliation §7 transition regime). Proposed functional form, not calibrated from data. |
