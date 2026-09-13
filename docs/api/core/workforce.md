# Workforce & ε Derivation

**Modules:** `hours_eoh/core/workforce.py`, `hours_eoh/core/civilization.py`

These modules model the human workforce capacity and — via `civilization.py` — the derivation of endogenous ε from actual capital stock.

---

## Workforce (workforce.py)

### `competency_reserve(certified_by_domain, workforce_size, …)` → `dict`

Computes the competency reserve fraction — the share of the workforce with current certified competency in essential infrastructure domains (Condition IV).

```python
from hours_eoh.core.workforce import competency_reserve

reserve = competency_reserve(
    certified_by_domain={"agriculture": 150, "construction": 200, "healthcare": 180},
    workforce_size=5000,
)
# Returns a per-domain breakdown: certified and required counts, the reserve
# fraction, whether each domain meets the threshold, and the gap.
print(reserve["per_domain"]["agriculture"]["meets_threshold"])
```

**Condition IV threshold:** ~15.5% of the workforce across essential domains. See [Structural Conditions](../../theory/structural_conditions.md#condition-iv-distributed-competency-strongly-recommended).

### `competency_check(reserve, …)` → `dict`

Evaluates whether the competency reserve satisfies Condition IV.

### `minimum_hours_allocation(epsilon, …)` → `dict`

Minimum annual labor obligation (h_min) broken down by purpose: competency rotation, stewardship service, regular employment.

### `automation_failure_scenario(epsilon, critical_eoh, reserve_capacity_eoh, h_min_labor_eoh, …)` → `dict`

Sudden loss of automation: the `critical_eoh` machines were carrying must be met by the competency reserve's capacity plus emergency mobilisation at h_min. Reports the coverage ratio and a severity band (covered / MODERATE / SEVERE / CRITICAL).

### `apply_death_redistribution(death_result, current_eoh_burden)` → `dict`

Redistributes EOH obligations from a deceased worker to remaining workers or automation.

### `competency_to_knowledge_eoh_delta(reserve_result, knowledge_eoh_base, …)` → `dict`

Change in knowledge EOH from a shift in competency reserve levels — captures the knowledge atrophy risk of reduced competency.

---

## Civilization ε Derivation (civilization.py)

### `machine_eoh_from_capital(capital_desc, population)` → `dict`

Computes machine EOH capacity from the capital profile — what the capital stock can actually fulfill.

```python
from hours_eoh.core.civilization import machine_eoh_from_capital

# keys are CAPITAL_MACHINE_PROFILES types; values a tier name or a spec dict
machine_eoh = machine_eoh_from_capital(
    {"power_grid": "standard", "computing_ai": "basic"},
    population=1_000_000,
)
print(machine_eoh["machine_eoh_total"])
```

### `civilization_epsilon(civ)` → `dict`

Derives endogenous ε from a complete civilization state dict (capital stock, ecosystem, population).

```python
from hours_eoh.core.civilization import civilization_epsilon

result = civilization_epsilon({
    "population": 1_000_000,
    "capital": {"power_grid": "standard", "water_treatment": "standard",
                "computing_ai": "basic"},
})
# Returns: {"epsilon", "physical_state", "eoh_gross", "machine_eoh", "pipeline", ...}
print(result["epsilon"])
```

This is the path to endogenous ε — rather than setting ε exogenously, derive it from the capital stock's actual machine capacity. Currently ε is often set exogenously for simplicity; the architecture supports full endogenous derivation via this module.

`CAPITAL_MACHINE_PROFILES` in `civilization.py` defines reference machine profiles by capital type.
