# Price Dynamics

**Module:** `hours_eoh/core/prices.py`

TEH prices are tied to human labor content. As automation rises, prices fall. The floor's purchasing power rises automatically — not by policy, but by mathematical consequence.

![Price Mechanism](../../images/price_mechanism.svg)

---

## `teh_price(base_labor_hours, epsilon, p)` → `float`

Price of a good or service in TEH. Human labor content = `(1 − ε) × base_hours`. A floor prevents prices reaching absolute zero.

```python
from hours_eoh.core.prices import teh_price

price = teh_price(base_labor_hours=0.1, epsilon=0.40, p=p)
```

---

## `basket_price(epsilon, p)` → `float`

TEH cost of the sufficiency basket at ε. Goods (60% of basket) decline steeply with automation; services (40%) decline more slowly. Both fall, so the floor's purchasing power rises automatically.

![Basket Price Arc](../../images/basket_price_arc.svg)

---

## `purchasing_power(teh_income, epsilon, p)` → `float`

Real purchasing power of a given TEH income at ε — how many sufficiency baskets can be purchased.

---

## `floor_purchasing_power(epsilon, p)` → `float`

Purchasing power of the sufficiency guarantee floor at ε. Rises monotonically with automation.

![Purchasing Power Arc](../../images/purchasing_power_arc.svg)

---

## `domain_scarcity_multiplier(eoh_fulfilled, eoh_total, p)` → `float`

The only S/D-like mechanism in the framework. Activates only when EOH demand exceeds fulfillment capacity. Corrective, not foundational — resets once labor is redirected.

![Scarcity Signal](../../images/scarcity_signal.svg)

---

## Audit and Monotonicity

### `full_price_monotonicity_audit(p)` → `dict`

Verifies that basket price decreases and purchasing power increases monotonically across the full ε arc. Used in tests and dashboard checks.

### `floor_monotonicity_guard(previous_floor, current_floor, p)` → `bool`

Guards against any mechanism that would allow the real floor to decline.

### `cpi_goods_destruction(basket_delivery_teh, epsilon, p)` → `float`

D4 TEH destruction from sufficiency basket delivery. TEH is destroyed when goods are consumed at the floor price.

---

## Additional Functions

| Function | Description |
|----------|-------------|
| `teh_price_trajectory(base_hours, epsilon_range, p)` | Price across a range of ε values |
| `purchasing_power_sweep(epsilon_range, p)` | Purchasing power across the arc |

---

## Design Invariant

Basket price must be strictly decreasing across the full ε arc. Floor purchasing power must be strictly non-decreasing. The `full_price_monotonicity_audit()` and `floor_monotonicity_guard()` functions enforce this. Any mechanism that violates this invariant violates [Design Principle 5](../../theory/design_principles.md#5-the-floor-rises-with-automation-it-never-falls).
