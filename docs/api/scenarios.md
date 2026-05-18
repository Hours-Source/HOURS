# Scenarios

**Package:** `hours_eoh/scenarios/`

Applied research tools that use `core/` physics and mechanics to test specific stress conditions. All scenario modules import from `core/` but never the reverse.

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
