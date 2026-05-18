# Workforce & ε Derivation

**Modules:** `hours_eoh/core/workforce.py`, `hours_eoh/core/civilization.py`

These modules model the human workforce capacity and — via `civilization.py` — the derivation of endogenous ε from actual capital stock.

---

## Workforce (workforce.py)

### `competency_reserve(domain_headcounts, total_workforce, p)` → `dict`

Computes the competency reserve fraction — the share of the workforce with current certified competency in essential infrastructure domains (Condition IV).

```python
from hours_eoh.core.workforce import competency_reserve

reserve = competency_reserve(
    domain_headcounts={"agriculture": 150, "construction": 200, "healthcare": 180, ...},
    total_workforce=5000,
    p=p
)
# Returns: {"reserve_fraction": 0.xx, "condition_iv_satisfied": bool, ...}
```

**Condition IV threshold:** ~15.5% of the workforce across essential domains. See [Structural Conditions](../../theory/structural_conditions.md#condition-iv-distributed-competency-strongly-recommended).

### `competency_check(reserve_fraction, p)` → `dict`

Evaluates whether the competency reserve satisfies Condition IV.

### `minimum_hours_allocation(epsilon, total_workforce, p)` → `dict`

Minimum annual labor obligation (h_min) broken down by purpose: competency rotation, stewardship service, regular employment.

### `automation_failure_scenario(epsilon, dropout_fraction, p)` → `dict`

Models the EOH obligation impact when automation handles `dropout_fraction` of EOH and suddenly fails.

### `apply_death_redistribution(deceased_worker, active_workforce, epsilon, p)` → `dict`

Redistributes EOH obligations from a deceased worker to remaining workers or automation.

### `competency_to_knowledge_eoh_delta(epsilon, competency_change, p)` → `float`

Change in knowledge EOH from a shift in competency reserve levels — captures the knowledge atrophy risk of reduced competency.

---

## Civilization ε Derivation (civilization.py)

### `machine_eoh_from_capital(capital_profile, epsilon_at_build, p)` → `float`

Computes machine EOH capacity from the capital profile — what the capital stock can actually fulfill.

```python
from hours_eoh.core.civilization import machine_eoh_from_capital

machine_eoh = machine_eoh_from_capital(
    capital_profile={"automation": 2e9, "infrastructure": 5e8, ...},
    epsilon_at_build=0.35,
    p=p
)
```

### `civilization_epsilon(civ)` → `dict`

Derives endogenous ε from a complete civilization state dict (capital stock, ecosystem, population).

```python
from hours_eoh.core.civilization import civilization_epsilon

result = civilization_epsilon(civ={"capital_stock": ..., "total_eoh": ..., "machine_eoh": ...})
# Returns: {"epsilon": 0.xx, "machine_eoh": ..., "total_eoh": ..., ...}
```

This is the path to endogenous ε — rather than setting ε exogenously, derive it from the capital stock's actual machine capacity. Currently ε is often set exogenously for simplicity; the architecture supports full endogenous derivation via this module.

`CAPITAL_MACHINE_PROFILES` in `civilization.py` defines reference machine profiles by capital type.
