# Running Scenarios

## What Scenarios Are

Scenarios are applied research tools in `hours_eoh/scenarios/`. They use `core/` physics and mechanics to test specific stress conditions, shocks, and parameter trajectories. They model system behavior under realistic conditions rather than verifying individual function outputs.

Scenarios import from `core/` and `land/` but never the reverse.

---

## Running via CLI

```bash
python3 utils/eoh_cli.py scenario list
python3 utils/eoh_cli.py scenario run NAME [--format table|csv|json]
```

Export to CSV for analysis:

```bash
python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

---

## Python API

### epsilon_sweep — Arc coherence check

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

results = epsilon_sweep()
for row in results:
    print(f"ε={row['epsilon']:.2f}  solvent={row['fiscally_solvent']}")
```

Use after any significant change to `core/` parameters.

### Shock scenarios

```python
from hours_eoh.scenarios.shocks import (
    automation_failure_shock,
    demographic_shock,
    ecological_eoh_spike,
)

result = automation_failure_shock(epsilon=0.60, dropout_fraction=0.30)
result = demographic_shock(epsilon=0.40, aging_factor=1.2)
result = ecological_eoh_spike(epsilon=0.50, spike_multiplier=3.0)
```

### Maintenance scenarios

```python
from hours_eoh.scenarios.maintenance import (
    deferred_maintenance_crisis,
    care_registration_delay,
)

result = deferred_maintenance_crisis(epsilon=0.40, deferred_fraction=0.20, periods=5)
result = care_registration_delay(epsilon=0.40, delay_periods=3)
```

### Recovery scenarios

```python
from hours_eoh.scenarios.recovery import (
    maintenance_recovery_schedule,
    minimum_fulfillment_for_recovery,
)

schedule = maintenance_recovery_schedule(deferred_eoh=5e8, epsilon=0.40)
min_rate = minimum_fulfillment_for_recovery(deferred_eoh=5e8, epsilon=0.40)
```

### Sensitivity sweeps

```python
from hours_eoh.scenarios.sensitivity import (
    fiscal_parameter_sweep,
    eoh_arc_sensitivity,
    epsilon_delta_sensitivity,
)

results = fiscal_parameter_sweep(param="suff_levy_rate", values=[0.01, 0.02, 0.03], epsilon=0.40)
results = eoh_arc_sensitivity()
results = epsilon_delta_sensitivity(epsilon=0.40, delta=0.05)
```

### Income and compound shocks

```python
from hours_eoh.scenarios.shocks import labor_income_shock, compound_shock

# Compress labor income to 60% of baseline
result = labor_income_shock(epsilon=0.40, income_fraction=0.60)
print(result["outcome"])  # STABLE / DEGRADED / CRISIS

# Combined ecological + demographic + automation shock
result = compound_shock(
    epsilon=0.40,
    ecology_collapse={"spike_multiplier": 2.5},
    demographic_shock_spec={"aging_factor": 1.3},
    automation_fraction_lost=0.20,
)
print(result["combined_outcome"])
```

### Multi-period long-run trajectories

```python
from hours_eoh.scenarios.long_run import (
    canonical_arc_trajectory,
    trust_depletion_stress,
    automation_transition_trajectory,
)

# Full arc 0 → 0.99 over 20 periods
result = canonical_arc_trajectory(n_periods=20)
print(result["outcome"], result["inflection_points"])

# Multi-stressor trust depletion run
result = trust_depletion_stress(n_periods=30)
print(result["first_insolvency_period"])

# Fixed-step automation transition
result = automation_transition_trajectory(epsilon_start=0.20, epsilon_delta=0.03)
print(result["converged"], result["convergence_period"])
```

### Industrial overshoot archetype

```python
from hours_eoh.scenarios.indust_overshoot import (
    indust_overshoot_baseline,
    indust_recovery_trajectory,
)

# Single-period overshoot snapshot vs. canonical
result = indust_overshoot_baseline(population=65_000_000, epsilon=0.40)
print(result["overshoot_eoh_delta"])

# Recovery trajectory — can restoration escape the overshoot regime?
result = indust_recovery_trajectory(epsilon_start=0.40, n_periods=20, restoration_rate=0.05)
print(result["escaped_overshoot"], result["escape_period"])
```

### GUF fiscal stress scenarios

```python
from hours_eoh.scenarios.guf_stress import (
    guf_fiscal_integration,
    guf_writedown_scenario,
    guf_revenue_sweep,
    automation_levy_guf_stress,
)
from hours_eoh.land.collective import make_urban_collective

# Does GUF revenue close a levy deficit at ε=0.60?
result = guf_fiscal_integration(epsilon=0.60)
print(result["deficit_closed"], result["guf_contribution_fraction"])

# GUF across the ε arc (tracks the Ψ bell curve)
trajectory = guf_revenue_sweep(parcel_configs=None)

# Multi-period automation→levy→GUF stress
result = automation_levy_guf_stress(
    parcel_inventory=make_urban_collective(1_000),
    epsilon_start=0.20,
    epsilon_end=0.80,
    n_periods=20,
)
print(result["outcome"])           # ADEQUATE / PARTIAL / CRISIS
print(result["crossover_period"])  # first period GUF > levy
```

---

## Writing a New Scenario

1. Create the file in `hours_eoh/scenarios/`.
2. Import from `core/` and `land/` as needed — never from `research/` or `utils/`.
3. Use `EohParams.temporary(**overrides)` for sweep code:

    ```python
    from hours_eoh.params import EohParams
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

    def my_scenario(epsilon: float, modified_rate: float) -> dict:
        p = EohParams()
        with p.temporary(levy_rate=modified_rate):
            result = eoh_to_teh_pipeline(epsilon, p=p)
        return result
    ```

    `temporary()` restores state on exit and adds no history entries — always prefer it over `p.set()` in sweep code.

4. Write tests in `tests/scenarios/test_my_scenario.py`. Test at ε = 0, 0.40, 0.90, 0.99.

---

## Interpreting Results

Check every scenario result against:

- **Fiscal solvency** (`fiscally_solvent: True/False`) — does the Trust remain solvent under stress?
- **Structural conditions** — do Conditions I–IV remain satisfied?
- **Arc coherence** — does the scenario resolve gracefully as ε approaches 0.99?

Spot-check with the dashboard after running with modified params:

```bash
python3 utils/eoh_cli.py params set capital_stock_teh 2000000000
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```
