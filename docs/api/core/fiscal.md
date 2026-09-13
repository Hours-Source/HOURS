# Fiscal Mechanics

**Module:** `hours_eoh/core/fiscal.py`

Levies, allocations, sufficiency guarantee, trust management, and the care stipend. All fiscal flows are circulatory — they redirect TEH but do not create or destroy it (except D2, D3, D6 destruction mechanisms).

---

## Levy Collection

### `levy_collection(labor_income, levy_rates)` → `dict`

Collects levies from labour income, each rate a fraction of gross. Circulatory: `worker_net + total_levied == labor_income`. Returns the total rate, total levied, worker net and the per-levy breakdown.

---

## Trust Allocations

The Trust has three co-equal obligations. Neither is residual — both `ecological_allocation` and `stewardship_allocation` are primary claims on Trust revenue.

### `stewardship_allocation(capital_stock_teh, capital_age_ratio, epsilon, available_teh, …)` → `dict`

TEH directed toward fulfilling infrastructure entropy obligations from the capital stock. Grows with the capital stock, making it the dominant revenue-independent fiscal flow at high ε.

### `ecological_allocation(ecosystem_health, epsilon, available_teh, …)` → `dict`

TEH directed toward ecological EOH fulfillment and natural system stewardship.

### `sufficiency_guarantee(population, epsilon, …)` → `dict`

The floor — minimum TEH guaranteed to every collective member. Real purchasing power rises automatically with automation (same nominal TEH, lower basket prices). See [Design Principle 5](../../theory/design_principles.md#5-the-floor-rises-with-automation-it-never-falls).

---

## Trust Management

### `trust_management(trust_balance, levy_revenue, stewardship_cost, guarantee_cost, …)` → `dict`

Full Trust solvency calculation — revenues in, obligations out, surplus/deficit.

### `fiscal_snapshot(epsilon, …)` → `dict`

Comprehensive fiscal state at ε — all revenue streams, all allocations, solvency status.

```python
from hours_eoh.core.fiscal import fiscal_snapshot

from hours_eoh.core.simulation import make_economy_state

snap = fiscal_snapshot(state=make_economy_state(epsilon=0.40))
print(snap["solvent"], snap["trust"]["surplus_deficit"])
```

### `trust_solvency_trajectory(initial_trust_balance, …)` → `dict`

Simulates the Trust balance across `n_periods` at one ε and assesses long-run solvency.

### `min_levy_for_solvency(trust_balance, epsilon, …)` → `dict`

Minimum levy revenue that keeps the Trust solvent and stable at ε.

---

## Care Stipend

### `care_stipend(dependents, epsilon, …)` → `dict`

TEH disbursed to recognized care providers. Follows a diminishing-returns structure (fewer TEH per additional dependent). Backed by verified personal EOH of the dependents.

### `aggregate_care_stipend_from_demographics(population, epsilon, …)` → `float`

Total care stipend obligation from population demographics.

---

## Additional Functions

| Function | Description |
|----------|-------------|
| `steward_eoh_obligation(structure_value_teh, land_area_units, epsilon, …)` | Private EOH a land steward bears for the structures they use |
| `collective_land_registration(epsilon, …)` | Fraction of housing/land EOH registered to the collective ledger |
| `stewardship_dividend_needed(stewardship_teh_required, dep_rate, trust_balance)` | Minimum `div_rate` for the Trust dividend to cover stewardship cost |
| `accumulation_ceiling_commitment(teh_in_circulation, population, …)` | D6 — TEH above the accumulation ceiling, routed into capital formation |

---

## Key Design Invariant

The fiscal system must remain solvent across the whole arc, including both ends: at ε = 0, where almost none of the obligation is registered and creation is at its lowest, and at ε = 0.99, where human labor is a small share of the obligation and creation has fallen back from its late-arc peak while staying far above its ε = 0 level. Revenue streams that depend on production output are supplementary. The Stewardship Allocation — which scales with the capital stock — is the foundational revenue source that persists even at full automation.
