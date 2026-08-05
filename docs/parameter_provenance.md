# Parameter Provenance

Every parameter used by the EOH → TEH model, with its default value, units,
and derivation rationale.

## The tag scheme

The goal is that **every constant carries a provenance tag, and the CHOSEN set
shrinks over time as measured data replaces guesses**. Four tags:

- **physics** — a structural claim about how entropy works. Changing it changes
  the model's claim about the world; needs a theoretical justification, not a knob.
- **measured** — read from an external empirical source (e.g. O*NET, BLS). The
  strongest tag: it can be wrong, and a data refresh would show it.
- **derived** — computed from measured inputs by a stated formula (normalizations,
  composites). Inherits its authority from the measurements beneath it.
- **CHOSEN** — a value set by judgement, not yet backed by measurement. **Every
  CHOSEN constant carries an *epistemic pointer* — the specific evidence or
  measurement that would move it off CHOSEN.** These are the calibration targets
  and the honest debts of the model.

A fifth working label, **derived-then-FROZEN**, marks a derived value pinned at a
reference epoch so it stays comparable across data vintages (re-deriving it per
vintage would reintroduce circularity).

> **Migration note.** The EOH-domain tables below predate this scheme and still
> use the older binary **Kind = Physics | Calibration** (Physics ≈ `physics`;
> Calibration ≈ `CHOSEN` awaiting local calibration). The **Multiplier** section
> is the first block fully migrated to the four-tag scheme with epistemic
> pointers. The machine-readable source of truth for the multiplier constants is
> [`hours_eoh/reference/data/multiplier_provenance_v5.csv`](../hours_eoh/reference/data/multiplier_provenance_v5.csv)
> (column `resolves_by` = the epistemic pointer).

Source: `hours_eoh/data.py` and `hours_eoh/params.py`; measured multiplier data
in `hours_eoh/reference/data/` (O*NET 30.3 / BLS, frozen epoch 2026-07-29).

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

### Task-normative statutory floor (B+D design — currency-free)

The floor stream of `infrastructure_eoh_breakdown()`. These reprice the physical
condition census into hours **without** a money→hours conversion — the auditable
half. Motivated by `handoffs/Infrastructure`: the monetized `capital_stock_teh`
path moves 10× with the accounting doctrine and ×1.000 with every physical knob;
the floor moves only with the physical census (`scenarios/infrastructure_floor.py`
proves floor_spread = 1.000). 4-tag scheme with epistemic pointers:

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT` | 24.0 | months | measured | 23 CFR 650 routine inspection interval (regulation). |
| `INFRA_TREATMENT_HOURS_GOOD` | 8.0 | h/unit·yr | CHOSEN | State DOT maintenance-activity manuals / inspection timesheets give real per-condition crew-hours. |
| `INFRA_TREATMENT_HOURS_FAIR` | 20.0 | h/unit·yr | CHOSEN | (as above) — the fair-condition crew-hour rate is timesheet-measurable. |
| `INFRA_TREATMENT_HOURS_POOR` | 48.0 | h/unit·yr | CHOSEN | (as above) — poor-condition rate; the residual 1.69× determinacy gap is this tiering, and it is measurable, not conventional. |

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

Added to support the contestability instrumentation (originally the bare
invariant χ(ε) = P(ε)/K_entry(ε) ≥ 1, since superseded by the §8.9
time-to-finance/two-arm form — see the Recalibration and §8.9c sections
below; the χ machinery remains as documented negative results).
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
| `CONTESTABILITY_VESTING_YEARS` | 5.0 | years | Calibration | Years of **federation** tenure for the Trust dividend to fully vest (linear vesting), used by `portable_endowment_individual()` and `portable_endowment_federated()`. Tenure is federation-wide (reconciliation §8.7b): moving between collectives never resets the clock or forfeits vested balance. Matches the 5-year tier-reassessment cadence (`TIER_ASSESSMENT_INTERVAL_YEARS`). The sufficiency floor never vests — it is membership-independent (reconciliation §8.1). A pure calibration knob: shorter vesting strengthens the marginal member's χ. |

## Coasean Federation Parameters (Workstream D / Phase 3 — `research/coasean.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `COASEAN_N_MAX` | 20 | collectives | Calibration | Collective count at ε=0 (maximally fragmented). A working hypothesis from reconciliation §6, not derived from institutional data — the real count depends on governance, geography, and transaction-cost structure. Calibration knob, not physics. |
| `COASEAN_BOUNDARY_EXPONENT` | 1.0 | dimensionless | Calibration | Exponent in N(ε) = max(1, round(N_max × (1−ε)^exp)). Linear default: collective count consolidates in proportion to automation. Higher values front-load consolidation. |
| `COASEAN_RESERVE_FRACTION` | 0.10 | fraction of TEH created | Calibration | Share of each collective's period TEH creation held as inter-collective reserve, consumed by `settlement_check()` for imbalance settlement. Analogous to a central-bank FX reserve ratio. |
| `COASEAN_IMBALANCE_CEILING` | 0.50 | fraction of debtor reserve | Calibration | Bilateral net-flow credit ceiling (paper's bilateral-imbalance-ceiling sketch, reconciliation §9-item-4). Within it, trade continues on credit; beyond it, settlement from reserve is required. |
| `COASEAN_DEPRECIATION_SLOPE` | 0.20 | dimensionless | Calibration | Exchange-rate depreciation per unit of unsettled imbalance beyond the ceiling: factor = 1/(1 + slope × excess_ratio). Makes over-issuance a visible exchange-rate movement (reconciliation §7 transition regime). Proposed functional form, not calibrated from data. |
| `COASEAN_COMMONS_TITHE` | 0.03 | fraction of levy revenue | Calibration | Fraction of each collective's common-fund levy revenue passed up to the federation commons (reconciliation §8.7a). Precedent: Italian Law 59/1992 requires cooperatives to contribute 3% of annual surplus to the mutualistic funds — the only real-world calibration point for a federation-level mutual levy. |
| `COASEAN_INDIVISIBLE_RESERVE_FRACTION` | 0.30 | fraction of collective trust | Calibration | Unallocated (indivisible) share of a collective's trust — credited to no individual capital account; escheats to the federation commons on merger/split/dissolution (reconciliation §8.7c). Precedent: Italian co-op law's statutory ~30% indivisible legal reserve. The model tracks no individual accounts, so a named constant is the minimal honest allocated/unallocated split — a tenure-derived fraction would be false precision. |
| `CONTESTABILITY_MIN_VIABLE_POPULATION` | 5,000 | persons | Calibration | Smallest population able to staff a viable alternative collective: the four-domain EOH pipeline with a full age distribution and a governance quorum (proposed §8.8 M2). UNCALIBRATED research placeholder, deliberately far below Coasean-efficient scale — a viable alternative need only clear minimum scale; requiring optimal scale would make the entry threat vacuous at high ε. |
| `CONTESTABILITY_UNDERWRITE_FRACTION` | 0.50 | fraction of commons | Calibration | Maximum share of the federation commons deployable per period as entry underwriting (proposed §8.8 M2); the remainder stays as the sufficiency-floor backstop (§8.7a). Underwritten capital moves commons → new collective trust, staying commonized and indivisible (§8.7c). |

## Recalibration Prototype (proposed §8.9 — `research/recalibration.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `RECAL_CAPITAL_OUTPUT_RATIO` | 4.0 | years (K per unit annual output) | Calibration | ν in K(ε) = K₀ + ν·Y(ε): capital stock required per unit of annual machine output. Precedent: Piketty's β (national capital / national income) ≈ 4–6 across observed economies; the low end is the adversarially-cheap-capital posture (a smaller commons weakens the underwriting arm). Fixes §8.8 open item 3 at the root — the old frame held an ε=0-era stock fixed while ε rose, giving τ = 17.5 for a quantity defined as a share ≤ 1. |
| `RECAL_EPSILON_RATE_PER_YEAR` | 0.02 | ε per year | Calibration | Arc speed dε/dt — a ~50-year subsistence→post-scarcity transition. UNCALIBRATED placeholder; converts per-ε acquisition needs into per-year flows, and faster arcs tighten acquisition feasibility linearly. |
| `RECAL_FOUNDING_LABOR_HOURS` | 1,000 | hours/year | Calibration | Hours per year a floor-backed founder can devote to building an alternative collective (≈ 2/3 of `PERSONAL_EOH_BASE`). The sufficiency floor is what frees this labor — the floor is the entry finance of the low-ε arc. UNCALIBRATED placeholder. |
| `RECAL_EXIT_HORIZON_YEARS` | 5.0 | years | Calibration | Self-financing horizon: exit must be financeable within one vesting period (= `CONTESTABILITY_VESTING_YEARS`). This is the RC4 fix — a stock target against a flow yields a TIME; the retired χ = P/K_entry demanded the founding stock be covered by one year of income. |
| `RECAL_ACCOUNT_CREDIT_SHARE` | 0.50 | fraction of dividend | Calibration | Share of the annual per-capita dividend credited to the member's individual capital account (§8.7b) rather than paid as cash. Zero-interest per Condition III: the account is a sum of credits, never compounded. Precedent: Mondragon internal capital accounts. |
| `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE` | 0.15 | fraction of capital estate | Calibration | Share of a decedent's private capital escheating to the commons (§8.9b, B4). Set equal to `ESTATE_LEVY_FRACTION`: capital estates treated exactly like TEH estates — the existing D5 doctrine extended to capital, not a new rule. No living holder is ever divested; conversion happens at mortality speed. |
| `RECAL_ESCALATION_ESTATE_SHARE` | 1.0 | fraction of capital estate | Calibration | Capital-estate escheat share while a §8.9b charter escalation is active: full generational conversion (Piketty's inheritance-tax instrument). Even at 1.0 the private-capital half-life is ≈ 69 years at the 1%/yr death rate — φ → target is asymptotic over generations; the exit invariant never depends on reaching it. |
| `RECAL_ESCALATION_CAPACITY_FLOOR` | 10.0 | foundings financeable | Calibration | Entry-underwriting capacity below which the charter escalates (with the adversarial regime observed): the commons must always be able to finance an order of magnitude more foundings than one. UNCALIBRATED placeholder; at canonical defaults capacity stays ≈ 145–280 and the trigger never fires. |
| `FORMATION_DEPRECIATION_RATE` | 0.05 | per year | Calibration | Aggregate annual depreciation of machine capital (§8.9c) — the aggregate counterpart of the per-asset lifecycle in `core/capital.py`, derived from `CAPITAL_MACHINE_PROFILES` design lives (≈ 20 yr → δ ≈ 1/20). Sets the gross return on capital 1/ν − δ = 0.20 and the commons replacement cost δ·T_K (a ≈ 20–24% haircut on the gross dividend). |
| `FORMATION_HURDLE_RATE_MIN` | 0.02 | net return per year | Calibration | Net private return below which no private capital formation occurs (§8.9c). Low BECAUSE of Condition III: idle TEH earns zero interest and leaks via the accumulation ceiling (D6) and estate dissolution (D5), so only risk compensation remains. UNCALIBRATED placeholder; raising it toward fiat-like levels is the Condition III counterfactual. |
| `FORMATION_FULL_SUPPLY_RATE` | 0.10 | net return per year | Calibration | Net private return at which formation demand is fully supplied (linear supply between the two rates — heterogeneous hurdle rates). Implies the incentive-compatible charter share s* = 1 − 0.10/0.20 = 0.50; a fiat-like 0.18 gives s* ≈ 0.10. UNCALIBRATED placeholder. |

## Membership-Terms Audit Thresholds (reconciliation §8.7e — `research/membership.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `MEMBERSHIP_VESTING_WARN_YEARS` | 10.0 | years | Calibration | Vesting beyond 2× `CONTESTABILITY_VESTING_YEARS` → WARN: a dividend held hostage for a decade thins the marginal member's exit without formally breaching χ. |
| `MEMBERSHIP_EXIT_NOTICE_WARN_YEARS` | 1.0 | years | Calibration | Exit notice beyond one year → WARN (exit friction accumulating). |
| `MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS` | 3.0 | years | Calibration | Notice beyond three years → CRIT: exit deferred that long is nominal, not substantive (reconciliation §8.1) — the term itself breaches the invariant regardless of χ arithmetic. |
| `MEMBERSHIP_MIN_HOURS_WARN_FRACTION` | 0.50 | fraction of `PERSONAL_EOH_BASE` | Calibration | Minimum-hours obligation above half the personal entropy load (750 h/yr) → WARN (§9-item-7: membership rules must not be drawn so tight they destroy χ). |
| `MEMBERSHIP_MIN_HOURS_CRIT_FRACTION` | 1.00 | fraction of `PERSONAL_EOH_BASE` | Physics-adjacent | Obligation at or above the full personal EOH load (1500 h/yr) → CRIT: an obligation equal to the whole entropy load is compulsion by definition, not a membership term. |
| `MEMBERSHIP_DIVIDEND_POLICY_WARN` | 0.25 | fraction of pro-rata dividend | Calibration | Distributing less than 25% of the pro-rata dividend to accounts → WARN: retention rebuilds the honeypot (undistributed commons) inside the collective that the indivisible-reserve escheat rule exists to defuse. |

---

## Reference Multiplier (measured — O*NET 30.3 / BLS, mult-5.1.0)

The multiplier prices **one hour of labour** and sets the **floor at which TEH is
minted** — not realized earnings (a discovered market premium sits on top;
reconciliation §3). All four assessment factors are **measured** from public
survey data; the map that turns them into a multiplier is **derived-then-frozen**.

**Read `handoffs/multipliers-v5/FALSIFIABILITY.md` before citing any number.**
The rank ordering and pairwise ratios are measurements (falsifiable against
source data); the absolute range, global spread ratio and band pass are
construction artifacts of the normalization choice (±2.8× swing across
normalizations) with no empirical content. `scenarios/multiplier_sensitivity.py`
quantifies both — run `eoh multiplier sensitivity`.

### Measured factors and the geometric map

| Parameter | Default | Kind | Source / Derivation |
|---|---|---|---|
| `f_training`, `f_demand`, `f_scarcity`, `f_impact` | per-occupation, ∈[0,1] | measured / derived | O*NET 30.3 education+training (T), abilities/skills/work-context burden (D), BLS EP openings+growth (S), O*NET+BLS impact sub-components (I). 751 occupations, 94.2% of US employment. Loaded via `hours_eoh.reference.onet_multipliers`. |
| `M_FLOOR` | 1.0 | CHOSEN (constitutional) | Constitutional floor multiplier. Resolves only by a charter decision on the floor. |
| `M_GEOMETRIC_R` | 3.2 | derived-then-FROZEN | Spread ratio, solved once from {floor, band, measured composite} at the reference epoch. Not a knob — re-derivation per vintage restores the circularity the freeze breaks. |
| `M_COMPOSITE_Z_LO`, `M_COMPOSITE_Z_HI` | 0.153, 0.740 | derived-then-FROZEN | Frozen composite normalization range for `z = clip((c−z_lo)/(z_hi−z_lo),0,1)`. |
| `M_IMPACT_COMPOSITE_LO/HI` | 0.332, 0.752 | derived-then-FROZEN | Frozen affine outer-normalization bounds for the impact composite (makes stated sub-domain weights operative; rank-preserving). |

The map: `composite = Σ wᵢ·fᵢ`; `m = M_FLOOR · M_GEOMETRIC_R ** z`. It has **no
free parameters** — floor constitutional, R and z-range derived-then-frozen,
curvature deleted (`core/multipliers.py:reference_multiplier`).

### CHOSEN constants — each with its epistemic pointer

Every remaining CHOSEN carries the evidence that would resolve it. Full list with
sweep ranges in the CSV; the load-bearing ones:

| Parameter | Default | Epistemic pointer (`resolves_by`) |
|---|---|---|
| `M_FACTOR_WEIGHTS` | (0.30, 0.25, 0.20, 0.25) | External anchor (an occupation-pair ratio asserted on other grounds) or a stated distributional target the measured data could fail. Sensitivity harness bounds the exposure: rank ordering robust (Spearman ≳0.97 under ±0.10), band is convention. |
| `M_EPOCH_WEIGHT_ANCHORS` | 4 ε-anchor vectors | Governance judgement on which leverage matters as ε rises; the ε→1 impact-only limit is theory (copy/merge degeneracy, `KNOWN_ISSUES §5`), not measurement. |
| `M_IMPACT_SUBDOMAIN_WEIGHTS` | (0.30, 0.25, 0.25, 0.20) | An outcome study linking dependency/substitutability/harm/temporal to measured entropy-reduction would calibrate the split. |
| `scarcity_leg_weights` | O 0.667 / G 0.333 | Add the vacancy leg V (JOLTS by SOC, economy-wide) and fit O/G/V from realized time-to-fill. |
| `substitution_tier_weights` | 1.0 / 0.6 / 0.3 | Observed cross-occupation transition rates (BLS mobility / longitudinal survey). |
| `temporal_activity_lists` | 5 persisting / 3 transient | An output-half-life measure (how long the work's product persists) would replace hand-picked activity lists. |
| `epsilon` | 0.40 | Measure ε = machine_EOH / total_EOH from capital stock (`civilization.py`) — then ε is *observed*, not chosen. |
| `band` scope | [1.8, 2.1] | Resolve whether it binds the minted floor or realized compensation; the band is near-non-discriminating (a convention). A distributional target the data could actually fail would replace it. |

### Not yet available (tag: planned)

`vacancy_leg_V` (JOLTS by SOC), `abandonment_rate` (longitudinal exit-without-
onward-destination — an audit trigger, not a multiplier input), `time_to_harm_speed`
(no dataset exists), `ai_exposure_machine_leg` (per-occupation Iceberg Index).
These are the model's honest data debts.
