# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

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
