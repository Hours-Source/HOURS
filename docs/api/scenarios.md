# Scenarios

**Package:** `hours_eoh/scenarios/`

Applied research tools that use `core/` physics and mechanics to test specific stress conditions. Scenario modules import from `core/` and `land/` but never the reverse.

For usage examples and how to write new scenarios, see [Running Scenarios](../guides/scenarios_howto.md).

---

## sweep.py — Arc Coherence

### `epsilon_sweep(p)` → `list[dict]`

Sweeps ε from 0 to 0.99 and verifies that every mechanism produces valid output at each point. Primary arc coherence check.

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

results = epsilon_sweep()
assert all(r["fiscally_solvent"] for r in results)
```

---

## shocks.py — Shock Events

### `automation_failure_shock(epsilon, dropout_fraction, p)` → `dict`

Sudden machine EOH dropout: automation that was handling `dropout_fraction` of EOH stops. Tests whether the competency reserve (Condition IV) can absorb the sudden labor demand.

### `demographic_shock(epsilon, aging_factor, p)` → `dict`

Shifts the population age distribution toward older ages by `aging_factor`. Tests fiscal solvency under increased care EOH and reduced working-age capacity.

### `ecological_eoh_spike(epsilon, spike_multiplier, p)` → `dict`

Sudden increase in ecological EOH (e.g., ecosystem threshold event). Tests Trust ecological allocation and the GUF's preventive mechanisms.

### `labor_income_shock(epsilon, income_fraction, trust_balance, population, ...)` → `dict`

Compresses labor income to `income_fraction × baseline`. Runs `fiscal_snapshot()` at both levels and returns `{baseline_income, shocked_income, trust_solvent_before, trust_solvent_after, surplus_deficit_delta, outcome}`. Outcome: `STABLE` / `DEGRADED` / `CRISIS`.

### `compound_shock(epsilon, ecology_collapse, demographic_shock_spec, automation_fraction_lost, ...)` → `dict`

Runs `ecological_eoh_spike`, `demographic_shock`, and `automation_failure_shock` independently, then aggregates combined EOH obligation. `combined_outcome` is always ≥ worst individual outcome in severity. Returns `{individual_outcomes, combined_eoh_delta, trust_absorbs_combined, combined_outcome}`.

---

## maintenance.py — Maintenance Crises

### `deferred_maintenance_crisis(epsilon, deferred_fraction, periods, p)` → `dict`

Models a crisis where `deferred_fraction` of infrastructure EOH is deferred per period for `periods` periods. Shows how compounding makes deferred maintenance increasingly expensive.

### `care_registration_delay(epsilon, delay_periods, p)` → `dict`

Lag in care EOH being admitted to the collective ledger. Models a policy failure where care labor is not registered promptly, creating under-investment in human capital.

---

## recovery.py — Recovery Planning

### `maintenance_recovery_schedule(deferred_eoh, epsilon, p)` → `list[dict]`

Period-by-period paydown schedule for an accumulated maintenance backlog.

### `minimum_fulfillment_for_recovery(deferred_eoh, epsilon, p)` → `float`

Minimum annual fulfillment rate required to prevent EOH from compounding faster than it is paid down.

---

## sensitivity.py — Parameter Sensitivity

### `fiscal_parameter_sweep(param, values, epsilon, p)` → `list[dict]`

Sweeps a fiscal parameter across values at a given ε. Useful for finding the solvency boundary of key parameters.

### `eoh_arc_sensitivity(p)` → `list[dict]`

Cross-sectional sensitivity metrics across the full ε arc — how each mechanism's output varies from expected canonical values.

### `epsilon_delta_sensitivity(epsilon, delta, p)` → `dict`

Sensitivity of all key outputs to a small change Δε around a given ε. Re-exported from `core/eoh_generation.py`.

---

## long_run.py — Multi-Period Trajectories

### `canonical_arc_trajectory(epsilon_start, epsilon_end, n_periods, population, trust_balance, ...)` → `dict`

Runs `run_simulation()` from `epsilon_start` to `epsilon_end` over `n_periods`. Returns the raw trajectory plus a compact `summary_table` and `inflection_points` (significant state transitions). Outcome: `STABLE` / `DEGRADED` / `CRISIS`.

```python
from hours_eoh.scenarios.long_run import canonical_arc_trajectory

result = canonical_arc_trajectory(epsilon_start=0.0, epsilon_end=0.99, n_periods=20)
print(result["outcome"], result["inflection_points"])
```

### `trust_depletion_stress(n_periods, population, trust_balance, stressor_profile, ...)` → `dict`

Multi-stressor run — applies compounding stressors each period and records when (if ever) the Trust first becomes insolvent. Returns `{first_insolvency_period, outcome, trajectory, summary_table}`. `stressor_profile` controls per-period compounding shock magnitudes.

### `automation_transition_trajectory(epsilon_start, epsilon_delta, n_periods, ...)` → `dict`

Fixed `epsilon_delta` step per period. Tracks purchasing power and fiscal convergence as the economy transitions. Detects convergence when the relative surplus change falls below 5%. Returns `{converged, convergence_period, outcome, trajectory}`.

---

## indust_overshoot.py — Industrial Overshoot Archetype

### `indust_overshoot_baseline(population, epsilon)` → `dict`

Single-period EOH/fiscal snapshot under industrial-overshoot physical state: 10× canonical capital stock, capital age ratio 0.75 (aging fleet), ecosystem health 0.38 (below spike threshold), 100 B-hour deferred ecological backlog. Compares against the canonical baseline at the same ε to quantify the overshoot burden.

```python
from hours_eoh.scenarios.indust_overshoot import indust_overshoot_baseline

result = indust_overshoot_baseline(population=65_000_000, epsilon=0.40)
print(result["overshoot_eoh_delta"], result["fiscally_solvent"])
```

### `indust_recovery_trajectory(epsilon_start, n_periods, restoration_rate, ...)` → `dict`

Multi-period run starting from industrial-overshoot state. Models whether ecosystem restoration at `restoration_rate` (fraction per period) can pull the economy out of the overshoot regime before Trust depletion. Returns `{escaped_overshoot, escape_period, outcome, trajectory}`.

---

## guf_stress.py — GUF Fiscal Stress Scenarios

### `guf_fiscal_integration(epsilon, parcel_configs, trust_balance, population, ...)` → `dict`

Compares Trust solvency with and without GUF revenue at a given ε. Runs `trust_management()` twice — levy-only vs. levy + GUF — and reports whether GUF closes a levy deficit. Returns `{levy_only_solvent, guf_integrated_solvent, guf_net_inflow, deficit_closed, guf_contribution_fraction}`.

### `guf_writedown_scenario(epsilon, services_reset, services_lost, ...)` → `dict`

Full ecological collapse event: triggers `eoh_accumulation_warning()`, then applies the write-down via `ground_use_fee_writedown()` in both restoration and abandonment pathways. Returns `{warning_triggered, restoration_result, abandonment_result, trust_impact}`.

### `guf_revenue_sweep(parcel_configs, epsilon_start, epsilon_end, steps, ...)` → `list[dict]`

Sweeps aggregate GUF across the ε arc and shows how GUF tracks the Ψ(ε) bell curve. Useful for identifying the GUF revenue peak relative to the levy revenue peak.

### `automation_levy_guf_stress(parcel_inventory, epsilon_start, epsilon_end, n_periods, population, trust_balance, ...)` → `dict`

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
