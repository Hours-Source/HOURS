# Running Scenarios

## What Scenarios Are

Scenarios are applied research tools in `hours_eoh/scenarios/`. They use `core/` physics and mechanics to test specific stress conditions, shocks, and parameter trajectories. They model system behavior under realistic conditions rather than verifying individual function outputs.

Scenarios import from `core/` and `land/` but never the reverse. Many are **REPORTING ONLY**: they measure something and say what it means, and nothing else in the package reads their output.

---

## Running via CLI

```bash
python3 utils/eoh_cli.py scenario list
python3 utils/eoh_cli.py scenario run NAME [--format table|csv|json]
```

`scenario list` is the authoritative list, with each scenario's own options.

Export to CSV for analysis:

```bash
python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

---

## Python API

Every example below runs as written, and `tests/test_doc_examples.py` fails the
build if one stops. The printed keys are the ones each function returns; read the
function's docstring for the rest.

### epsilon_sweep — Arc coherence check

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

report = epsilon_sweep(n_points=11)
print(report["status"], report["discontinuities"])
for row in report["sweep"]:
    print(f"ε={row['epsilon']:.2f}  solvent={row['fiscal_solvent']}")
```

Use after any significant change to `core/`.

### Shock scenarios

```python
from hours_eoh.scenarios.shocks import (
    automation_failure_shock,
    demographic_shock,
    ecological_eoh_spike,
)

# Automation that was carrying EOH stops: can the competency reserve absorb it?
result = automation_failure_shock(epsilon=0.60)
print(result["outcome"], result["coverage_ratio"])

# shock_type is "growth", "decline" or "aging"; magnitude is a fraction
result = demographic_shock(epsilon=0.40, shock_type="aging", magnitude=0.20)
print(result["outcome"])

# An ecosystem crossing its threshold
result = ecological_eoh_spike(epsilon=0.50, ecosystem_health_before=0.70,
                              ecosystem_health_after=0.30)
print(result["threshold_crossed"], result["outcome"])
```

### Maintenance scenarios

```python
from hours_eoh.scenarios.maintenance import (
    deferred_maintenance_crisis,
    care_registration_delay,
)

# Meeting 80% of an annual obligation for ten years — when does it compound into crisis?
result = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=1e6,
                                     fulfillment_fraction=0.80, years=10)
print(result["outcome"], result["crisis_year"])

# Care registration lagging the arc by 0.10 in ε
result = care_registration_delay(epsilon=0.40, delay_epsilon=0.10)
print(result["outcome"], result["lag_fraction"])
```

### Recovery scenarios

```python
from hours_eoh.scenarios.recovery import (
    maintenance_recovery_schedule,
    minimum_fulfillment_for_recovery,
)

schedule = maintenance_recovery_schedule(epsilon=0.40, current_deferred=5e6, annual_eoh=1e6)
print(schedule["recoverable"], schedule["recovery_year"])

minimum = minimum_fulfillment_for_recovery(epsilon=0.40, current_deferred=5e6, annual_eoh=1e6)
print(minimum["min_fulfillment"])
```

### Sensitivity sweeps

```python
from hours_eoh.scenarios.sensitivity import (
    fiscal_parameter_sweep,
    eoh_arc_sensitivity,
    epsilon_delta_sensitivity,
)

sweep = fiscal_parameter_sweep(parameter="dep_rate", values=[0.03, 0.045, 0.06], epsilon=0.40)
print(sweep["solvent_range"])

rows = eoh_arc_sensitivity()
point = epsilon_delta_sensitivity(base_epsilon=0.40, delta_epsilon=0.05)
print(len(rows), sorted(point["metrics"]))
```

### Income and compound shocks

```python
from hours_eoh.scenarios.shocks import labor_income_shock, compound_shock

# Compress labor income to 60% of baseline
result = labor_income_shock(epsilon=0.40, income_fraction=0.60)
print(result["outcome"])  # STABLE / DEGRADED / CRISIS

# Ecological collapse, an ageing shock and lost automation, together
result = compound_shock(
    epsilon=0.40,
    ecology_collapse=True,
    ecosystem_health_after=0.30,
    demographic_shock_spec={"shock_type": "aging", "magnitude": 0.20},
    automation_fraction_lost=0.20,
)
print(result["combined_outcome"], result["trust_absorbs_combined"])
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
print(result["solvent_all"], result["first_insolvency"], result["inflection_points"])

# Multi-stressor trust depletion run
result = trust_depletion_stress(n_periods=30)
print(result["outcome"], result["first_insolvency"])

# Fixed-step automation transition
result = automation_transition_trajectory(epsilon_start=0.20, epsilon_delta=0.03)
print(result["convergence_period"])
```

### Industrial overshoot archetype

```python
from hours_eoh.scenarios.indust_overshoot import (
    indust_overshoot_baseline,
    indust_recovery_trajectory,
)

# Single-period overshoot snapshot vs. the canonical arc at the same ε
result = indust_overshoot_baseline(population=65_000_000, epsilon=0.40)
print(result["outcome"], result["eoh_vs_canonical_ratio"])

# Can ecological restoration pull the economy out of the overshoot regime?
result = indust_recovery_trajectory(epsilon=0.40, n_periods=20, ecological_restoration_rate=0.05)
print(result["ecosystem_recovered"], result["years_to_ecosystem_recovery"])
```

### GUF fiscal stress scenarios

```python
from hours_eoh.scenarios.guf_stress import (
    guf_fiscal_integration,
    guf_revenue_sweep,
    automation_levy_guf_stress,
)
from hours_eoh.land.collective import make_urban_collective

# Does GUF revenue keep the Trust solvent where the levy alone would not?
result = guf_fiscal_integration(epsilon=0.60)
print(result["trust_solvent_levy_only"], result["trust_solvent_with_guf"],
      result["guf_revenue_fraction_of_levy"])

# The fee across the ε arc
for row in guf_revenue_sweep():
    print(f"ε={row['epsilon']:.2f}  applied={row['guf_applied']:.2f}")

# Multi-period automation → levy → GUF stress
result = automation_levy_guf_stress(
    parcel_inventory=make_urban_collective(1_000),
    epsilon_start=0.20,
    epsilon_end=0.80,
    n_periods=20,
)
print(result["outcome"])           # ADEQUATE / PARTIAL / CRISIS
print(result["crossover_period"])  # first period GUF > levy, or None
```

---

## Writing a New Scenario

1. Create the file in `hours_eoh/scenarios/`.
2. Import from `core/` and `land/` as needed — never from `research/` or `utils/`.
3. Take every input as an explicit keyword argument with a named `data.py` default, and forward it to the calls it governs. A parameter a scenario accepts and does not forward is the stranded-parameter failure `tests/test_parameter_wiring.py` exists to catch:

    ```python
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

    def my_scenario(epsilon: float, available_labor_eoh: float | None = None) -> dict:
        result = eoh_to_teh_pipeline(epsilon, available_labor_eoh=available_labor_eoh)
        return {"scenario": "my_scenario", "teh_created": result["teh_created"],
                "labor_constrained": result["labor_constrained"]}
    ```

4. Write tests in `tests/scenarios/test_my_scenario.py`. Test at ε = 0, 0.40, 0.90, 0.99, and break a constant to confirm each test can fail.
5. Register it in `utils/scenario_cmd.py` so `scenario list` shows it; `tests/test_cli_dispatch.py` runs every registered scenario.

---

## Interpreting Results

Check every scenario result against:

- **Its verdict and outcome** — most scenarios return an `outcome` or `verdict` and a `recommendation`. Read the verdict's own caveats; they are there because a bare figure was misread before.
- **Structural conditions** — do Conditions I–IV remain satisfied?
- **Arc coherence** — does the scenario resolve gracefully as ε approaches 0.99?
- **Which quantity was minted** — a pipeline result with `labor_constrained: False` is minted from obligation demanded, not work served.

Spot-check with the dashboard after running with modified params:

```bash
python3 utils/eoh_cli.py params set capital_stock_teh 2000000000
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```
