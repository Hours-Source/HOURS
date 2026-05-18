# Canonical Trajectory

**Module:** `hours_eoh/core/trajectory.py`

Provides the canonical physical-state reference at each ε (the ideal arc for a civilization investing optimally), and ε derivation utilities.

---

## `canonical_physical_state(epsilon)` → `dict`

Returns the ideal-arc physical state at a given ε. Used as the reference baseline for arc testing.

```python
from hours_eoh.core.trajectory import canonical_physical_state

state = canonical_physical_state(0.40)
# Returns: {capital_stock_teh, capital_age_ratio, ecosystem_health,
#           monitoring_capability, age_distribution, knowledge_base_size,
#           knowledge_complexity_per_unit}
```

!!! note "Real simulations pass actual state"
    `canonical_physical_state(ε)` is the *ideal-arc reference* for a civilization that invests optimally. Real simulations track actual capital stock, ecosystem health, etc. Divergence from canonical is the point of modeling.

---

## `canonical_age_distribution(epsilon)` → `dict[str, float]`

Ideal-arc age distribution at ε.

---

## `compute_epsilon(machine_eoh, total_eoh_value)` → `float`

Derives ε from machine EOH and total EOH: `ε = machine_eoh / total_eoh`, clamped to `[0.0, 0.99]`.

```python
from hours_eoh.core.trajectory import compute_epsilon

epsilon = compute_epsilon(machine_eoh=1.5e9, total_eoh_value=2.5e9)  # → 0.60
```

Currently ε is often set exogenously. The architecture supports endogenous ε when machine capacity is modeled from capital stock — see `civilization.py` in [Workforce & ε Derivation](workforce.md).

---

## `effective_capital_from_epsilon(capital_stock_at_eps0, epsilon)` → `float`

Expected capital stock at ε given starting capital at ε=0.
