# EOH Dynamics

**Module:** `hours_eoh/core/eoh_dynamics.py`

Time-evolution of EOH obligations: compounding from deferred maintenance, regenerative labor offsets, investment ranking, and paydown schedules.

---

## Deferred Maintenance

### `deferred_eoh(accumulated_deferred, current_eoh, fulfillment_rate, p)` → `float`

Net change in deferred EOH over a period: `current_eoh × (1 − fulfillment_rate)` minus decay from previous deferrals.

### `eoh_compounding(deferred_eoh, compounding_rate, years, p)` → `float`

Models non-linear compounding of deferred EOH. A neglected roof does not need five years of routine maintenance — it needs replacement. Behavior is discontinuous, not smooth like monetary interest.

!!! important "Not interest"
    EOH compounding is physics, not a social convention. It generates obligation without creating TEH. No party benefits from the compounding; all parties pay through degraded systems.

### `compounding_profile(deferred_eoh, years, p)` → `list[dict]`

Projects deferred EOH accumulation over a period.

### `deferred_eoh_paydown(deferred_eoh, paydown_teh_per_year, epsilon, p)` → `list[dict]`

Models the paydown trajectory given a sustained fulfillment investment.

### `update_deferred_from_fulfillment(deferred, fulfilled, p)` → `float`

Updates the deferred balance after a fulfillment event.

---

## Regenerative Labor

### `regenerative_offset(labor_teh, service_type, epsilon, p)` → `dict`

Quantifies the future EOH reduction from regenerative labor (soil enrichment, preventive maintenance) versus maintenance labor (current EOH fulfillment).

### `regenerative_vs_maintenance_comparison(total_teh, split_fraction, epsilon, p)` → `dict`

Compares outcomes of allocating labor to regenerative vs. maintenance work over a planning horizon.

### `eoh_reduction_ratio(asset_teh_cost, asset_eoh_eliminated, design_life, p)` → `float`

Ratio of EOH eliminated to EOH generated (maintenance burden) for a proposed investment. Values > 1.0 indicate a net EOH reduction — the case for building.

### `regenerative_investment_required(target_eoh_reduction, years, epsilon, p)` → `float`

TEH investment required to achieve a target future EOH reduction through regenerative labor.

---

## Investment Ranking

### `rank_investment_candidates(candidates, epsilon, p)` → `list[dict]`

Ranks infrastructure investment candidates by their EOH reduction ratio. Highest-leverage investments first.

```python
from hours_eoh.core.eoh_dynamics import rank_investment_candidates

candidates = [
    {"label": "water treatment", "teh_cost": 50000, "eoh_eliminated": 80000, "design_life": 40},
    {"label": "road resurfacing", "teh_cost": 10000, "eoh_eliminated": 5000, "design_life": 10},
]
ranked = rank_investment_candidates(candidates, epsilon=0.40, p=p)
```

### `optimal_investment(budget_teh, candidates, epsilon, p)` → `dict`

Selects the optimal set of investments within a TEH budget to maximize EOH reduction.

### `maintenance_strategy_compare(asset, strategies, epsilon, p)` → `dict`

Compares maintenance strategies (preventive vs. reactive vs. deferred) over a planning horizon in TEH cost and EOH outcome.
