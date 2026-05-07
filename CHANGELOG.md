# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

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
