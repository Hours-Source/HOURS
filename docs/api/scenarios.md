# Scenarios

**Package:** `hours_eoh/scenarios/`

Applied research tools that use `core/` physics and mechanics to test specific stress conditions. Scenario modules import from `core/` and `land/` but never the reverse.

For usage examples and how to write new scenarios, see [Running Scenarios](../guides/scenarios_howto.md).

---

## sweep.py — Arc Coherence

### `epsilon_sweep(…)` → `dict`

Sweeps ε from 0 to 0.99 and verifies that every mechanism produces valid output at each point. Primary arc coherence check.

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

report = epsilon_sweep()
assert report["all_finite"] and not report["discontinuities"]
print(report["status"], all(row["fiscal_solvent"] for row in report["sweep"]))
```

---

## shocks.py — Shock Events

Every shock is a change to ONE state — machine capability, population and age mix, ecosystem health and the restoration a collapse leaves — read through the shared pipeline before and after, capped at the labour supply the population can give (`feasibility.labor_supply_per_capita`, moving with the age mix). Added human demand is taken up within that supply; the rest is **deferred**, survival-first, so `deferred_personal_eoh > 0` means the survival floor itself is unmet. **Nothing is charged to the Trust**: a balance cannot supply an hour of labour, and work that is done registers and mints. The Trust's real obligation, the guarantee, is read from `fiscal_snapshot()` at the after-state with the register held at the pre-shock ε (`registration_epsilon`). The outcome is the worse of the labour reading (STABLE: all taken up; DEGRADED: some deferred; CRISIS: personal deferred) and the Trust's position.

### `automation_failure_shock(epsilon, …)` → `dict`

Machines lose `fraction_lost` (default 1) of their capability; the OBSERVED machine load lost (`machine_eoh_lost`) falls to people. Reports `taken_up_eoh`, `deferred_eoh`, `deferred_personal_eoh`, the mint and floor price before and after, the Trust surplus, and `failure_boundary`. **Competency (Condition IV) is tested** in every shock: the work taken up is set against the people certified for it, per essential domain (`conditions.condition_iv_coverage`, certification at the Condition IV minimum of the state's own working-age headcount); in two tiers: a shortfall the shock CREATES in registered personal demand — the agents' own needs without competent hands — is CRISIS; one elsewhere is DEGRADED; one already present is reported, not blamed on it (`competency_short_before` / `_created`, `competency_personal_short_created`, `competency_unattributed_eoh`). `workforce_size`, `mean_entropy_reduction_capacity` and `reserve_fraction` are deprecated and ignored.

### `demographic_shock(epsilon, shock_type, magnitude, …)` → `dict`

`"growth"` / `"decline"` (population × (1 ± `magnitude`)) or `"aging"` (a share `magnitude` of the WHOLE population moves from working age to elderly; refused beyond the working-age share). Labour supply follows the new age mix, so aging lowers supply as it raises demand. Reports supply, obligation and guarantee before and after, and the cascade. Labour income is the mint unless `labor_income_base` is supplied (the legacy proxy).

### `ecological_eoh_spike(epsilon, ecosystem_health_before, ecosystem_health_after, …)` → `dict`

A collapse leaves a **restoration stock**: the health lost over the frame's land (`population × LAND_HECTARES_PER_CAPITA`), priced by `restoration_cost.pristine_gap_obligation` and amortised over `restoration_years`, entering the pipeline as `restoration_obligation`. Both band corners are reported (`restoration_eoh_low` / `_high`; `restoration_corner` sets which is cascaded). The land holder's added GUF flow is reported in hours (`guf_flow_added_eoh`) and not cascaded. `threshold_crossed` is reported and no longer sets the outcome alone. Not modelled: biological recovery time. `base_rate` is deprecated.

### `labor_income_shock(epsilon, income_fraction, trust_balance, population, …)` → `dict`

Compresses labor income to `income_fraction × baseline`, where the baseline is the period's mint, unfloored (`income_fraction=0` is a true collapse). Runs `fiscal_snapshot()` at both levels and returns `{baseline_income, shocked_income, trust_solvent_before, trust_solvent_after, surplus_deficit_delta, outcome}`. Outcome: `STABLE` / `DEGRADED` / `CRISIS`.

### `compound_shock(epsilon, ecology_collapse, demographic_shock_spec, automation_fraction_lost, …)` → `dict`

Applies every enabled change to ONE state and reads one cascade — the shocks share one labour pool. Each component is also run alone (`individual_outcomes`); `combined_outcome` is never better than the worst of them. Returns `{individual_outcomes, combined_eoh_delta (added human demand, h/yr), combined_deferred_eoh, combined_deferred_personal_eoh, automation_deferred_eoh, trust_absorbs_combined, combined_outcome}`.

---

## maintenance.py — Maintenance Crises

### `deferred_maintenance_crisis(epsilon, annual_eoh, fulfillment_fraction, years, …)` → `dict`

Models a crisis where `deferred_fraction` of infrastructure EOH is deferred per period for `periods` periods. Shows how compounding makes deferred maintenance increasingly expensive.

### `care_registration_delay(epsilon, …)` → `dict`

Lag in care EOH being admitted to the collective ledger. Models a policy failure where care labor is not registered promptly, creating under-investment in human capital.

---

## recovery.py — Recovery Planning

### `maintenance_recovery_schedule(epsilon, current_deferred, annual_eoh, …)` → `dict`

Period-by-period paydown schedule for an accumulated maintenance backlog.

### `minimum_fulfillment_for_recovery(epsilon, current_deferred, annual_eoh, …)` → `dict`

Minimum annual fulfillment rate required to prevent EOH from compounding faster than it is paid down.

---

## sensitivity.py — Parameter Sensitivity

### `fiscal_parameter_sweep(parameter, values, epsilon, …)` → `dict`

Sweeps a fiscal parameter across values at a given ε. Useful for finding the solvency boundary of key parameters.

### `eoh_arc_sensitivity(…)` → `list[dict]`

Cross-sectional sensitivity metrics across the full ε arc — how each mechanism's output varies from expected canonical values.

### `epsilon_delta_sensitivity(base_epsilon, delta_epsilon, …)` → `dict`

Sensitivity of all key outputs to a small change Δε around a given ε. Re-exported from `core/eoh_generation.py`.

---

## long_run.py — Multi-Period Trajectories

### `canonical_arc_trajectory(epsilon_start, epsilon_end, n_periods, …)` → `dict`

Runs `run_simulation()` from `epsilon_start` to `epsilon_end` over `n_periods`. Returns the raw trajectory plus a compact `summary_table` and `inflection_points` (significant state transitions). Outcome: `STABLE` / `DEGRADED` / `CRISIS`.

```python
from hours_eoh.scenarios.long_run import canonical_arc_trajectory

result = canonical_arc_trajectory(epsilon_start=0.0, epsilon_end=0.99, n_periods=20)
print(result["solvent_all"], result["first_insolvency"], result["inflection_points"])
```

### `trust_depletion_stress(n_periods, stressor_profile, population, …)` → `dict`

Multi-stressor run — applies compounding stressors each period and records when (if ever) the Trust first becomes insolvent. Returns `{first_insolvency_period, outcome, trajectory, summary_table}`. `stressor_profile` controls per-period compounding shock magnitudes.

### `automation_transition_trajectory(epsilon_start, epsilon_delta, n_periods, …)` → `dict`

Fixed `epsilon_delta` step per period. Tracks purchasing power and fiscal convergence as the economy transitions. Detects convergence when the relative surplus change falls below 5%. Returns `{converged, convergence_period, outcome, trajectory}`.

---

## indust_overshoot.py — Industrial Overshoot Archetype

### `indust_overshoot_baseline(population, epsilon)` → `dict`

Single-period EOH/fiscal snapshot under industrial-overshoot physical state: 10× canonical capital stock, capital age ratio 0.75 (aging fleet), ecosystem health 0.38 (below spike threshold), 100 B-hour deferred ecological backlog. Compares against the canonical baseline at the same ε to quantify the overshoot burden.

```python
from hours_eoh.scenarios.indust_overshoot import indust_overshoot_baseline

result = indust_overshoot_baseline(population=65_000_000, epsilon=0.40)
print(result["outcome"], result["eoh_vs_canonical_ratio"])
```

### `indust_recovery_trajectory(n_periods, …)` → `dict`

Multi-period run starting from industrial-overshoot state. Models whether ecosystem restoration at `restoration_rate` (fraction per period) can pull the economy out of the overshoot regime before Trust depletion. Returns `{escaped_overshoot, escape_period, outcome, trajectory}`.

---

## guf_stress.py — GUF Fiscal Stress Scenarios

### `guf_fiscal_integration(epsilon, parcel_configs, trust_balance, population, …)` → `dict`

Compares Trust solvency with and without GUF revenue at a given ε. Runs `trust_management()` twice — levy-only vs. levy + GUF — and reports whether GUF closes a levy deficit. Returns `{levy_only_solvent, guf_integrated_solvent, guf_net_inflow, deficit_closed, guf_contribution_fraction}`.

### `guf_writedown_scenario(epsilon, …)` → `dict`

Full ecological collapse event: triggers `eoh_accumulation_warning()`, then applies the write-down via `ground_use_fee_writedown()` in both restoration and abandonment pathways. Returns `{warning_triggered, restoration_result, abandonment_result, trust_impact}`.

### `guf_revenue_sweep(…)` → `list[dict[str, Any]]`

Sweeps aggregate GUF across the ε arc and shows how GUF tracks the Ψ(ε) bell curve. Useful for identifying the GUF revenue peak relative to the levy revenue peak.

### `automation_levy_guf_stress(parcel_inventory, epsilon_start, epsilon_end, …)` → `dict`

Multi-period automation→levy→GUF stress loop: as ε rises, levy revenue falls; GUF tracks the Ψ(ε) bell curve; the sufficiency guarantee cost evolves. Carries the Trust balance forward each period.

```python
from hours_eoh.scenarios.guf_stress import automation_levy_guf_stress
from hours_eoh.land.collective import make_urban_collective

result = automation_levy_guf_stress(
    parcel_inventory=make_urban_collective(1_000),
    epsilon_start=0.20,
    epsilon_end=0.80,
    n_periods=20,
)
print(result["outcome"])               # ADEQUATE / PARTIAL / CRISIS
print(result["crossover_period"])      # first period GUF > levy (or None)
print(result["first_insolvency"])      # first insolvent period (or None)
print(result["compensation_adequacy"]) # mean GUF / levy shortfall
```

Returns `{scenario, trajectory, parcel_count, epsilon_range, levy_peak_period, guf_peak_period, crossover_period, first_insolvency, compensation_adequacy, outcome, recommendation}`.
