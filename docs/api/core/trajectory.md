# Canonical Trajectory

**Module:** `hours_eoh/core/trajectory.py`

Provides the canonical physical-state reference at each ε — a reference frame for arc testing, not a measurement of any real economy — and ε derivation utilities.

---

## `canonical_physical_state(epsilon)` → `dict`

Returns the physical state on the reference trajectory at a given ε. Used to test functions at specific ε without a full simulation, and as the baseline a simulated trajectory's divergence is measured against.

```python
from hours_eoh.core.trajectory import canonical_physical_state

state = canonical_physical_state(0.40)
# Returns: {capital_stock_teh, capital_age_ratio, ecosystem_health,
#           monitoring_capability, age_distribution, knowledge_base_size,
#           knowledge_complexity_per_unit}
```

!!! note "Real simulations pass actual state"
    `canonical_physical_state(ε)` is the *reference arc*. Real simulations track actual capital stock, ecosystem health, etc. Divergence from canonical is the point of modeling.

---

## `canonical_age_distribution(epsilon)` → `dict[str, float]`

Age distribution on the canonical arc. **Independent of ε**: the former drift from children toward elders as ε rises is retired, and `epsilon` is kept only so existing callers do not break.

---

## `compute_epsilon(machine_eoh_fulfilled, total_eoh_collective_potential)` → `float`

Derives ε from machine EOH and total EOH: `ε = machine_eoh / total_eoh`, clamped to `[0.0, 0.99]`.

```python
from hours_eoh.core.trajectory import compute_epsilon

epsilon = compute_epsilon(machine_eoh_fulfilled=1.5e9,
                          total_eoh_collective_potential=2.5e9)  # → 0.60
```

Currently ε is often set exogenously. The architecture supports endogenous ε when machine capacity is modeled from capital stock — see `civilization.py` in [Workforce & ε Derivation](workforce.md).

---

## `effective_capital_from_epsilon(capital_stock_at_eps0, epsilon)` → `float`

Canonical capital stock at ε from an ε=0 baseline. Not equivalent to `canonical_physical_state(ε)["capital_stock_teh"]` — the two answer different questions; the function's docstring gives the distinction.
