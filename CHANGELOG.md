# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

**Provenance coverage closed and gated (2026-08-09)**
- `utils/provenance.py` + `utils/provenance_cmd.py` — inline provenance tag blocks in
  `data.py` are parsed from source, checked against the tag scheme, and rendered as the
  shipped audit CSV and the generated tables in `docs/parameter_provenance.md`.
  CLI: `eoh provenance check | csv | table | doc`.
- `hours_eoh/reference/data/constant_provenance.csv` — **generated**, one row per
  `data.py` constant (value, units, tag, tier, form, block, `resolves_by`, note), so a
  public audit needs no Python. Packaged via the existing `hours_eoh.reference` data glob.
- All **228** `data.py` constants now carry an inline tag block, up from an effective 3.
  101 constants (44%) previously appeared nowhere in the provenance doc, 51 of them the
  entire GUF block. Nine doc tables were still on the retired binary
  `Kind = Physics | Calibration`.
- `tests/test_provenance.py` — 46 tests. Parser behaviour is pinned against synthetic
  source; the **coverage gate** runs against the real `data.py` with **no allowlist**,
  and fails on an untagged constant, a stale or unmatched tag block, a tag outside the
  closed vocabulary, a `CHOSEN` constant with no epistemic pointer, missing units, a
  misapplied tier, a stale audit CSV, stale generated doc tables, or a block with no doc
  home. Each was verified to bite by breaking it and reverting.
- `tier` (A–D) formalised as a **sub-qualifier** of `measured`/`CHOSEN` rather than a
  rival scheme, matching what the thermal layer already wrote. `convention` promoted to a
  declared sub-label. The ad-hoc `Physics-adjacent` tag is retired.

### Changed

**Provenance doc: tables generated, prose hand-written**
- Every constant table in `docs/parameter_provenance.md` now sits inside a
  `<!-- provenance:table -->` region rendered from `data.py`. The prose around them — where
  the epistemic argument lives — is untouched and stays hand-written. New sections for
  Ground Use Fee, dashboard thresholds, capital lifecycle, TEH destruction, human capital
  and multiplier governance, none of which had one.
- **No calibration constant changed.** Verified constant-by-constant against the previous
  commit: 228 compared, 0 value differences.
- Tag distribution over all 228: `CHOSEN` 190 (83.3%), `measured` 13, `derived` 9,
  `convention` 8, `derived-then-FROZEN` 6, **`physics` 2**. Applying the scheme's own
  demanding definition of *physics* honestly leaves `A_EARTH_M2` and `SIGMA_SB`.

### Fixed

**Four documentation drifts, found by the migration**
- `KNOWLEDGE_EOH_BASE` — doc said 490,107,421; the shipped value has been
  381,962,855.27 since the ε_ref fixed-point re-anchor.
- `CARE_SIGMOID_DEFAULTS` — doc said start_share 0.30 / inflection 0.55 against the
  shipped 0.05 / 0.45; it had never matched the code.
- Membership min-hours thresholds printed as 750 / 1500 h/yr and per-capita personal EOH
  as 2,213 — both are *products* of `PERSONAL_EOH_BASE` and went stale at the
  1,500 → 1,000 reprice. Now 500 / 1,000 and 1,475. A curated test pins these derived
  products, because no value-equality check can see a number restated in a sentence.
- `RECAL_FOUNDING_LABOR_HOURS` is documented as "≈ 2/3 of `PERSONAL_EOH_BASE`" but the
  reprice made it 100% of it. Recorded on the constant; the value is unchanged pending a
  decision.

### Findings (reported, not resolved)
- **NLSA cites this framework's own document.** All 51 GUF constants attribute to "NLSA
  Technical Manual TM-0042", whose own header reads *"Based on NLSA from HOURSFramework"*.
  Equation numbers now appear only under `form:`, never `resolves_by:` — they establish an
  asserted form, not external evidence for a value.
- **`GUF_ECO_KAPPA_CARBON` (2.750 TEH/tCO₂e) and `CDR_LABOR_HOURS_PER_TONNE` (0.6 h/t)
  are the same quantity from two layers — a 4.6× disagreement.** Also `DEP_RATE` 0.045 vs
  `FORMATION_DEPRECIATION_RATE` 0.05, and `CONTESTABILITY_CAPITAL_YIELD_RATE` 0.10 vs the
  0.20 derivable from `RECAL_CAPITAL_OUTPUT_RATIO` and `FORMATION_DEPRECIATION_RATE`.
- **Four constants are calibrated to a target and now say so:** `GUF_USE_*`,
  `DEFAULT_SEGMENTS`, `TRUST_BASE_TEH`, `CAPITAL_MACHINE_PROFILES` — the
  `_ECOLOGICAL_SPIKE_INTENSITY` pattern the 2026-08-05 pass named but did not sweep for.
- **`LEVY_SUFFICIENCY_WARN` cannot fire on the shipped configuration**: it warns below 2%
  guarantee coverage, and `SUFF_LEVY_RATE` delivers ≈2% at canonical defaults.
- **`_ECOLOGICAL_SPIKE_INTENSITY` lives in `core/eoh_generation.py`, not `data.py`**, so
  the gate cannot see a constant the retag log covers — a standing violation of the
  no-anonymous-constants invariant.
- Residual the gate does **not** close: free prose can still go stale. The curated
  derived-product test covers where the reprice drift actually hid; a narrative paragraph
  that goes stale in a way no field captures remains a human problem, and saying so is
  better than implying the test closes it.

**Federation contestability closure (reconciliation §8.7 — research tier)**
- `research/coasean.py` Phase 4 — two-tier Trust: `merge_collectives()` and
  `split_collective()` boundary events with indivisible-reserve escheat (§8.7c) and
  TEH-conservation postconditions (§8.7d); `simulate_federation(commons=True)` tracks a
  federation commons funded by a levy tithe (`COASEAN_COMMONS_TITHE`, Italian Law 59/1992
  precedent) plus consolidation escheats, and records per-collective χ each period
  (`chi_min`, `chi_marginal_min`, `chi_worst_collective`, `chi_status_worst`,
  `commons_balance`, `commons_floor_coverage`). τ counts both tiers. Defaults are
  byte-identical to Phase 3.
- `research/contestability.py` — `portable_endowment_federated()` (two-tier P: the floor
  is federation-guaranteed and never vests; the dividend claim is per-collective),
  `exit_value()` (the floor crosses collective boundaries at par; only the capital
  account converts at the exchange rate), `contestability_margin_federated()`.
  Tenure is federation-wide (§8.7b): moving collectives never resets vesting.
- `research/membership.py` — `MembershipTerms` + `contestability_audit()`: the §8.7e
  math/contract line. Admission cost adds to K_entry; exit notice, minimum hours,
  vesting length, and dividend retention are audited against `MEMBERSHIP_*` thresholds.
- CLI: `eoh coasean simulate` gains `--dynamics --g-priv --levy-rate --commons
  --commons-tithe --regime`; new `eoh contestability audit` subcommand.
- Honest adversarial findings at defaults (reported, not tuned): commons floor coverage
  is tiny at a 3% tithe, and consolidation escheat migrates trust from collective
  dividends to the commons across the arc, so the worst marginal χ worsens toward ε→1.

**Contestability closure mechanisms (proposed §8.8 — research tier, pending author
sign-off; see `notes/contestability-closure-proposal.md`)**
- Answers the Phase 4 adversarial findings. Root-cause diagnosis: (1) the commons was
  dividend-inert, so §8.7c escheat drained tenure-vested dividends into a fund paying
  no one; (2) the marginal (tenure-0) member holds no capital claim, so no levy
  schedule can close χ_marginal; (3) the static levy base ε·K·yield understates
  machine output ~12× at high ε (an ε=0-era capital calibration held fixed);
  (4) χ compares an annual endowment flow to a one-time founding stock.
- M1 — universal commons dividend: `portable_endowment_federated(...,
  commons_balance)` pays the commons yield per capita UNVESTED (Alaska Permanent
  Fund precedent); escheat becomes a stabilizer — consolidation moves capital from
  tenure-gated collective dividends into the universal tier.
- M2 — entry underwriting: `entry_underwriting()` + `commons_seed_required()`;
  the commons capitalizes new collectives' trusts (stays commonized, §8.7c).
  Combined invariant: `exit_financeable ⇔ χ_marginal ≥ 1 OR entry_capacity ≥ 1`.
  With a seed of ~1.8e7 TEH (~0.05% of the Trust base) the combined invariant holds
  at EVERY period of the canonical adversarial arc (asserted in tests) — while
  χ_marginal alone stays honestly CRIT at high ε (commons-financed, not
  self-financed exit).
- M3 — physically-consistent levy base: `machine_output_teh(ε) = ε·total_eoh(ε)`;
  `levy_schedule_for_chi(levy_base="machine_output")`. Growth steps of the schedule
  remain infeasible — M3 removes the calibration artifact, it does not manufacture
  feasibility.
- `simulate_federation(commons_dividend=True, commons_start=...)` wires M1+M2 into
  the federation arc (`commons_dividend_paid`, `entry_capacity`, `exit_financeable`);
  `contestability_audit(commons_dividend=, underwriting_policy=)` audits terms
  against the combined invariant (CRIT → WARN waiver is opt-in; §8.7e defaults
  unchanged). New constants `CONTESTABILITY_MIN_VIABLE_POPULATION` (uncalibrated
  placeholder, documented as such) and `CONTESTABILITY_UNDERWRITE_FRACTION`.
- CLI: `coasean simulate --commons-dividend --commons-start`; `contestability levy
  --levy-base`; `contestability audit --commons-dividend --underwriting-policy`.
- All defaults preserve §8.7 behavior float-exact; 38 new tests (1595 total).

**Recalibration prototype (proposed §8.9 — research tier; adopted-in-principle by the
author 2026-07-26, formal reconciliation-doc edit pending)**
- `research/recalibration.py` — resolves the three §8.8 "honest remainders" at their
  causes. RC4 fix: the flow/stock χ is replaced by time-to-finance-exit
  (`exit_financing()`, invariant `t_exit ≤ RECAL_EXIT_HORIZON_YEARS` = one vesting
  period) and a genuine accumulating §8.7b capital account (`capital_account_stock()`,
  Mondragon internal-account precedent, zero-interest per Condition III). Open item 3
  fix: `capital_stock_epsilon()` grows the stock with machine output
  (K(ε) = K₀ + ν·Y(ε), ν = Piketty's β ≈ 4) and the commons OWNS share φ(ε) of it
  (Meade social-dividend model), so τ = φ ≤ 1 by construction and dτ/dε ≥ 0
  (Piketty inversion) is structural, not levy-contingent. The dividend is the commons'
  capital income net of share acquisition (`commons_income_statement()`) — 0 at ε=0,
  ≈1,873 TEH/person·yr at ε=0.99: funded by measured machine output, not a promise.
- Self-financing dropped as the test (author decision): exit finance has three
  physical channels — own labor at low ε (the floor feeds the founders while they
  build), commons underwriting through the mid-arc trough (Caja Laboral / Marcora
  precedent), dividend savings at high ε. `recalibrated_arc()` shows the combined
  invariant holding at EVERY arc point in the adversarial regime, with the channel
  arcing labor → underwritten → self (asserted in tests).
- Honest findings at defaults (reported, not tuned): share acquisition out of commons
  income is infeasible for ε ≲ 0.15 (the initial endowment φ₀·K₀ and human-era
  fiscal levies must carry the early arc); endogenous private-capital growth turns
  negative past ε ≈ 0.5 — the §8.2 commonization made visible instead of assumed
  away as a fixed g_priv.
- `trust_required_for_chi()` and `levy_schedule_for_chi()` marked SUPERSEDED
  (retained unchanged as documented negative results: the trust-growth path cannot
  close bare χ — which is why underwriting exists).
- New constants (all provenance-documented, placeholders flagged):
  `RECAL_CAPITAL_OUTPUT_RATIO`, `RECAL_EPSILON_RATE_PER_YEAR`,
  `RECAL_FOUNDING_LABOR_HOURS`, `RECAL_EXIT_HORIZON_YEARS`,
  `RECAL_ACCOUNT_CREDIT_SHARE`.
- CLI: `eoh contestability recal` — the §8.9 arc table. 62 new tests (1657 total).

**§8.9b — charter-formation doctrine (research tier; doctrine bundle agreed with the
author 2026-07-26)**
- `phi_policy` on the recalibration module: `"dilution"` (new default doctrine),
  `"target"` (§8.9a purchase model, kept as the regression anchor), `"escalated"`.
- Charter formation (A3): the commons' share attaches to NEW capital at
  commissioning as a federation charter condition (resource-license / Georgist
  model) — `formation_share_required()` gives the per-ε charter share s(ε)
  (≈ 0.17 early, crossing 1 at ε ≈ 0.48). Nothing is purchased, so the §8.9a
  early-arc funding gap disappears and the dividend is the full φ·Y (self-financed
  exit from ε ≈ 0.30 vs 0.59 under §8.9a). `formation_levy_rate()` quantifies the
  compensated bridge (≈ 1% of labor-era output, sunsetting by ε ≈ 0.2).
- Dilution ratchet (B2): private capital is NEVER sold down — it follows a
  running-max ratchet (rises while s ≤ 1, then flat). Honest cost, reported not
  tuned: φ caps at ≈ 0.66–0.68 by ε = 0.99 (target 0.99); the exit invariant
  still holds at every arc point with D ≈ 1,600 TEH/person·yr.
- Escalation clause (B3): `escalation_trigger()` — adversarial regime observed AND
  (entry capacity < `RECAL_ESCALATION_CAPACITY_FLOOR` or invariant failing) →
  the charter takes all new formation (s = 1) and capital-estate escheat rises to
  `RECAL_ESCALATION_ESTATE_SHARE`. The trigger LATCHES in the arc; at canonical
  defaults it NEVER fires (asserted in tests; forced firing tested at a 40×
  founding cohort, lifting φ to ≈ 0.86 at ε = 0.99).
- Generational conversion (B4): `estate_conversion_flow()` — capital estates
  escheat at `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE` (0.15 = `ESTATE_LEVY_FRACTION`:
  the D5 doctrine extended to capital, not a new rule). Honest finding: mortality
  speed is slow (half-life ≈ 69 yr even at full escheat) — φ → target is
  asymptotic over generations; §8.2's "φ must be ABLE to → 1" survives as an
  asymptotic capability, and the exit invariant never depends on it.
- `recalibrated_arc()` path-integrates the capital split (TEH-conservation
  asserted); rows gain phi_target, cap_binding, s_required, escalation_active,
  private_capital_delta_per_year (the absolute-flow reporting fix — a rate on a
  vanishing base was theatrical). Open item, flagged: the charter share is an
  implicit tax on private capital formation; the investment-disincentive feedback
  on K(ε) is not simulated.
- CLI: `contestability recal --phi-policy --estate-escheat --min-viable-population`;
  s_req/ΔKpriv columns, cap-binding and escalation markers. 79 new tests (1736
  total).

**§8.9c — formation feedback (research tier): who actually builds K(ε)**
- `research/formation.py` closes the investment-disincentive circularity §8.9b
  flagged open. Formation is FINANCED or it does not happen: private supply
  f(s) falls linearly as the charter share cuts the net return
  r_priv = (1−s)(1/ν−δ); the commons co-funds from net income per a priority
  policy; ε is DERIVED from the capital actually formed (aggregate inversion of
  the module's own physics; typed-capital integration via core/civilization.py
  is the follow-up).
- Two corrections found in planning, now in the accounting: (1) the §8.9b
  funding hole — in the cap region s = 1 attracts zero private funding, so the
  commons pays for ALL formation there; (2) replacement — the commons must
  replace its own worn stock (δ·T_K ≈ a 20–24% dividend haircut);
  `commons_income_statement(net_of_replacement=True)` reports it (default False
  preserves published §8.9b gross figures).
- Null anchor (charter share pinned 0): reproduces the canonical ~50-yr arc
  pace exactly — the baseline every feedback effect is measured against.
- VERDICTS (honest, asserted in tests): share-first priority holds the canonical
  pace with ZERO delay — the feedback costs the arc nothing in time, but the
  dividend pays for it (D ≈ 113 vs static 302 at ε ≈ 0.4; self-financing onset
  moves from ε ≈ 0.30 to ε ≈ 0.86, underwriting carries the transition).
  Dividend-first never stalls but CRAWLS: ε ≈ 0.60 after 120 years, never
  completing. The exit invariant holds at every simulated year under BOTH
  priorities and even in the fiat counterfactual — capacity does not depend on
  the dividend.
- THE CONDITION III FINDING: zero interest is the doctrine's structural ally.
  The incentive-compatible charter share is s* = 1 − r_full/r_gross = 0.50 at
  zero-interest returns vs ≈ 0.10 at fiat-like returns; in the fiat
  counterfactual the commons must drive the dividend to literally ZERO mid-arc
  to hold pace, where the zero-interest world never does. The framework's
  pieces reinforce each other, quantified.
- New constants (provenance-documented, flagged): `FORMATION_DEPRECIATION_RATE`
  (from CAPITAL_MACHINE_PROFILES design lives), `FORMATION_HURDLE_RATE_MIN`,
  `FORMATION_FULL_SUPPLY_RATE`. CLI: `contestability formation --priority
  --hurdle --full-supply --escalation --charter-share`. 39 new tests (1775
  total).

**Collective land-inventory system (`hours_eoh/land/`)**
- `collective.py` — Standard parcel schema and batch GUF calculator for a collective land
  inventory. `compute_collective_guf(parcels, epsilon, median_income)` loops all parcels through
  `ground_use_fee()`, applies soil-health credits, review-cycle caps, and income-linked subsidies
  per parcel, then aggregates via `guf_trust_inflow()`. Schema maps directly to geo-data pipeline
  column names for zero-friction integration with GeoJSON/CSV sources.
- `collective.make_urban_collective(parcel_count)` — Synthetic dense-urban archetype (75 %
  residential_primary · 15 % commercial_retail · 5 % commercial_office · 5 % institutional).
- `collective.make_rural_collective(parcel_count)` — Synthetic rural archetype (50 %
  agricultural_active · 20 % agricultural_fallow · 20 % residential_primary · 10 %
  conservation).
- `calibration.py` — Rate and weight calibration tools.
  - `guf_rate_calibration(inventory, target_guf_levy_ratio, population, epsilon)` — Closed-form
    linear solve to find the use-coefficient multiplier `k` such that aggregate GUF ≈
    `target × levy_revenue`. Binary-verifies with a sample run; reports `converged` flag.
  - `guf_lvi_weight_sensitivity(inventory, epsilon, weight_variants)` — Sweeps Location Value
    Index weight configurations to quantify how sensitive aggregate GUF is to sub-index weighting
    choices (centrality vs. transit vs. services vs. natural amenity). Ships five canonical
    variants; callers may supply their own.
- `land/__init__.py` re-exports all four new public functions.

**Multi-period automation→levy→GUF stress scenario**
- `scenarios/guf_stress.automation_levy_guf_stress(parcel_inventory, epsilon_start,
  epsilon_end, n_periods, ...)` — Period-by-period fiscal stress loop: as ε rises, levy revenue
  (derived from the EOH pipeline) falls, GUF tracks the Ψ(ε) bell curve, and the sufficiency
  guarantee cost evolves. Reports `levy_peak_period`, `guf_peak_period`, `crossover_period`
  (first period where GUF exceeds levy), `first_insolvency`, `compensation_adequacy`, and
  outcome `ADEQUATE / PARTIAL / CRISIS`.

**Multi-period simulation scenarios (`hours_eoh/scenarios/`)**
- `long_run.py` — `canonical_arc_trajectory`, `trust_depletion_stress`,
  `automation_transition_trajectory`: three functions that call `run_simulation()` and return
  multi-period trajectories with inflection-point detection and stressor profiles.
- `indust_overshoot.py` — `indust_overshoot_baseline`, `indust_recovery_trajectory`:
  models the industrial-overshoot archetype (high capital age, degraded ecosystem, large
  deferred-ecological backlog) and recovery pathways.
- `shocks.py` additions — `labor_income_shock` (income-fraction shock with solvency delta) and
  `compound_shock` (combines ecological, demographic, and automation shocks; combined outcome
  is always ≥ worst individual outcome).

**Simulation engine extensions (`hours_eoh/core/simulation.py`)**
- `simulate_period(..., workforce_epsilon_decay: bool = False)` — Optional parameter; when
  `True`, `workforce_fraction` shrinks proportionally with rising ε. Default `False` preserves
  backward compatibility.
- `simulate_period(..., guf_net_inflow: float | None = None)` — Optional GUF land-fee revenue
  injected into the Trust each period.
- `run_simulation()` and the `eoh simulate` CLI forward both new parameters.

**GUF calibration fix**
- `GUF_USE_*` constants in `data.py` multiplied by 100 (e.g. `residential_primary` 0.10 →
  10.0 TEH/SLU/yr, `commercial_retail` 0.30 → 30.0). At ε = 0.40 with a 1 M-population
  territory (~420 k parcels), aggregate GUF is now co-equal with levy revenue — the design
  target in the mission statement.
- `guf_fiscal_integration()` labor-income proxy replaced: was `trust_balance × 0.5`
  (35× inflated); now uses `eoh_to_teh_pipeline(epsilon, population)["teh_created"]`.

**CLI (`utils/`)**
- `guf inventory calculate --parcels FILE [--epsilon ε] [--median-income TEH]` — Batch GUF
  from a JSON parcel file; prints aggregate summary table or JSON.
- `guf inventory sweep --parcels FILE [--epsilon-start ε] [--epsilon-end ε] [--steps N]` —
  Sweeps aggregate GUF across the ε arc.
- `guf inventory stress --parcels FILE [--epsilon-start ε] [--epsilon-end ε] [--periods N]` —
  Multi-period automation→GUF stress with per-period trajectory table.
- `scenario` command: 10 new scenarios wired — `canonical-arc`, `trust-depletion`,
  `automation-transition`, `indust-baseline`, `indust-recovery`, `labor-shock`,
  `compound-shock`, `guf-integration`, `guf-writedown`, `guf-sweep`.
- `simulate` command: `--workforce-decay` and `--guf-inflow TEH` flags.

**Documentation and diagrams**
- MkDocs GitHub Pages site deployed at `https://hours-source.github.io/HOURS/`.
- Five GUF Mermaid diagrams: calculation flow, LVI component weights, Ψ(ε) epsilon arc,
  Trust fund flow, and ecological write-down pathways. Rendered SVGs in `docs/images/`.

### Fixed
- **eco-collapse-1 (closed)** — Ecological collapse is now handled via the GUF layer
  (`land/guf.py` §9) rather than direct TEH destruction. Two pathways: restoration
  (V_s baselines reset to recovery target, revenue maintained) and abandonment
  (rebuilding surcharge R_b amortised over 50 years). Preventive monitoring via
  `eoh_accumulation_warning()` (§9.8). `research/writedown.py` re-exports with rationale.
- `guf_net_inflow` guard in `simulate_period()` corrected from `> 0.0` to `is not None`
  so negative inflows (subsidy-heavy periods) are no longer silently dropped.
- `WORKFORCE_FRACTION_MIN` named constant added to `data.py`; replaces anonymous `0.05`
  literal in simulation.

### Changed
- Test count: 1040 → 1169 (129 new tests across `tests/land/`, `tests/scenarios/`).

---

## [0.1.0] — 2026-05-06

Initial public release of the HOURS EOH framework.

### Added

**Core package (`hours_eoh/core/`)**
- `trajectory.py` — Canonical arc, ε derivation, `canonical_physical_state()`, `compute_epsilon()`
- `eoh_generation.py` — Four EOH domain functions: `personal_eoh`, `infrastructure_eoh`, `ecological_eoh`, `knowledge_eoh`, `total_eoh`
- `registration.py` — Per-domain sigmoid admission curves; `personal_eoh_registration_share` (near-zero at ε=0), `total_registration_share` (labor composite)
- `eoh_fulfillment.py` — EOH → TEH pipeline: `human_eoh_share`, `human_eoh_per_domain`, `registered_eoh`, `eoh_to_teh_pipeline`
- `multipliers.py` — Condition II multiplier band and tier logic
- `fiscal.py` — Fiscal architecture: levies, stewardship and ecological allocations (co-equal), sufficiency guarantee, trust management, care stipend
- `prices.py` — Price dynamics tied to human labor content: `basket_price`, `purchasing_power`, `floor_purchasing_power`
- `capital.py` — Asset and human capital lifecycle: `make_asset`, `birth_event`, `maturation_update`, `death_event`, `writedown_trigger`, `execute_writedown`
- `eoh_dynamics.py` — Time-evolution: `eoh_compounding`, `asset_condition_trajectory`, `regenerative_offset`, `eoh_reduction_ratio`
- `population.py` — Population structure, age distribution, demographic events (`aging`)
- `workforce.py` — Workforce lifecycle, domain headcount, competency reserve, `apply_death_redistribution`
- `conditions.py` — Structural Conditions I–IV enforcement: `balance_check`, `condition_iii_balance_growth_check`
- `dashboard.py` — Condition monitors and EOH/fiscal health indicators
- `civilization.py` — Endogenous ε from capital stock: `civilization_epsilon`, `CAPITAL_MACHINE_PROFILES`
- `simulation.py` — Period simulation engine: `make_economy_state`, `simulate_period`

**Land module (`hours_eoh/land/`)**
- `guf.py` — Ground Use Fee framework (NLSA TM-0042, 7th Ed.): 14 functions from `epsilon_scaling` through `guf_trust_inflow`

**Scenarios (`hours_eoh/scenarios/`)**
- `sweep.py` — `epsilon_sweep`: arc coherence check with fiscal solvency at every ε
- `shocks.py` — `automation_failure_shock`, `demographic_shock`, `ecological_eoh_spike`
- `maintenance.py` — `deferred_maintenance_crisis`, `care_registration_delay`
- `recovery.py` — `maintenance_recovery_schedule`, `minimum_fulfillment_for_recovery`
- `sensitivity.py` — `fiscal_parameter_sweep`, `eoh_arc_sensitivity`, `epsilon_delta_sensitivity`

**Research (`hours_eoh/research/`)**
- `investment.py` — `rank_investment_candidates`, `optimal_investment`, `eoh_reduction_ratio` (re-exported from core)
- `writedown.py` — Placeholder: ecological write-down for collapse scenarios (eco-collapse-1, future work)

**Test suite**
- 1040 tests across 20 test files covering the full arc from ε = 0 to ε = 0.99
- Phase tests (1–14) cover the complete development arc
- Module tests cover trajectory, civilization ε, GUF, and all scenario modules

### Design invariants established
- ε is a derived observable, not a policy lever or generation-function input
- EOH generation takes physical state; EOH fulfillment takes ε
- `data.py` is the single source of truth for all named constants
- Per-domain registration split: personal uses demand sigmoid; non-personal use labor composite
- Ecological and stewardship allocations are co-equal (neither is residual)
- Zero interest (Condition III): balances grow only through labor
- All functions verified at ε = 0 (subsistence) and ε = 0.99 (effective post-scarcity)

### Known gaps
- **eco-collapse-1** — Ecological write-down for collapse scenarios not yet implemented (placeholder in `research/writedown.py`)

[0.1.0]: https://github.com/Hours-Source/HOURS/releases/tag/v0.1.0
