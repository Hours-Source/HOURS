# Price Dynamics

**Module:** `hours_eoh/core/prices.py`

These functions compute **floor prices**: the TEH price set by a good's human labor content. As automation rises, floor prices fall, so the floor's purchasing power rises — within the model this follows from its structure, not from policy. Prices above the floor are discovered by exchange and are not modelled here.

![Price Mechanism](../../images/price_mechanism.svg)

---

## `teh_price(human_labor_hours_at_eps0, epsilon, …)` → `float`

Floor price of a good in TEH: human labor content × mean multiplier, where human labor content = `(1 − ε) × base_hours`. A goods price floor keeps some irreducible human contribution, so the price never reaches zero. An optional `scarcity_factor` from `domain_scarcity_multiplier()` raises it when demand outruns capacity.

```python
from hours_eoh.core.prices import teh_price

price = teh_price(human_labor_hours_at_eps0=0.1, epsilon=0.40)
```

---

## `basket_price(epsilon, …)` → `float`

TEH cost of the sufficiency basket at ε. Goods (60% of basket) decline steeply with automation; services (40%) decline more slowly. Both fall, so the floor's purchasing power rises automatically.

![Basket Price Arc](../../images/basket_price_arc.svg)

---

## `purchasing_power(teh_amount, epsilon, …)` → `dict`

Real purchasing power of a given TEH income at ε — how many sufficiency baskets can be purchased.

---

## `floor_purchasing_power(floor_teh, epsilon, …)` → `dict`

Purchasing power of the sufficiency guarantee floor at ε. Rises monotonically with automation.

![Purchasing Power Arc](../../images/purchasing_power_arc.svg)

---

## `domain_scarcity_multiplier(eoh_demand, fulfillment_capacity, …)` → `float`

The only S/D-like mechanism in the framework. Activates only when EOH demand exceeds fulfillment capacity. Corrective, not foundational — resets once labor is redirected.

![Scarcity Signal](../../images/scarcity_signal.svg)

---

## Audit and Monotonicity

### `full_price_monotonicity_audit(…)` → `dict`

Verifies Principle 5 for every price component at once: `basket_price()` and `teh_price()` non-increasing in ε, floor purchasing power non-decreasing. Scarcity multipliers are demand-dependent and may legitimately break monotonicity, so they are not checked.

### `floor_monotonicity_guard(…)` → `dict`

Sweeps ε from 0 to 0.99 and flags any step at which floor purchasing power declines.

### `cpi_goods_destruction(capital_personal_eoh_fulfilled_total, epsilon, …)` → `dict`

D4 TEH destruction: when capital assets (water treatment, hospitals, energy grids) deliver personal-EOH services, those services are consumed at their embedded labor price and the TEH is destroyed at the point of delivery.

---

## Additional Functions

| Function | Description |
|----------|-------------|
| `teh_price_trajectory(human_labor_hours_at_eps0, …)` | Price across a range of ε values |
| `purchasing_power_sweep(teh_amount, …)` | Purchasing power across the arc |

---

## Design Invariant

Basket price must be non-increasing across the full ε arc, and floor purchasing power non-decreasing. The `full_price_monotonicity_audit()` and `floor_monotonicity_guard()` functions enforce this. Any mechanism that violates this invariant violates [Design Principle 5](../../theory/design_principles.md#5-the-floor-rises-with-automation-it-never-falls).
