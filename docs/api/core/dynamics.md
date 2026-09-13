# EOH Dynamics

**Module:** `hours_eoh/core/eoh_dynamics.py`

Time-evolution of EOH obligations: compounding from deferred maintenance, regenerative labor offsets, investment ranking, and paydown schedules.

---

## Deferred Maintenance

### `deferred_eoh(accumulated_eoh, fulfilled_eoh)` → `float`

The maintenance deficit: accumulated EOH obligation minus what was fulfilled.

### `eoh_compounding(deferred, asset_type, time_deferred, …)` → `float`

Models non-linear compounding of deferred EOH. A neglected roof does not need five years of routine maintenance — it needs replacement. Behavior is discontinuous, not smooth like monetary interest.

!!! important "Not interest"
    EOH compounding is physics, not a social convention. It generates obligation without creating TEH. No party benefits from the compounding; all parties pay through degraded systems.

### `compounding_profile(asset_type, deferred, …)` → `list[dict]`

Projects deferred EOH accumulation over a period.

### `deferred_eoh_paydown(regenerative_result, current_deferred)` → `dict`

Retires accumulated deferred EOH through regenerative labour, from a `regenerative_offset()` result.

### `update_deferred_from_fulfillment(current_deferred, fulfilled_eoh)` → `dict`

Updates the deferred balance after a fulfillment event.

---

## Regenerative Labor

### `regenerative_offset(labor_type, regenerative_hours, epsilon)` → `dict`

Quantifies the future EOH reduction from regenerative labor (soil enrichment, preventive maintenance) versus maintenance labor (current EOH fulfillment).

### `regenerative_vs_maintenance_comparison(labor_hours, regen_type, current_eoh_demand, epsilon)` → `dict`

Compares outcomes of allocating labor to regenerative vs. maintenance work over a planning horizon.

### `eoh_reduction_ratio(production_cost_eoh, annual_maintenance_eoh, annual_eoh_eliminated, design_life, …)` → `dict`

Ratio of EOH eliminated to EOH generated (maintenance burden) for a proposed investment. Values > 1.0 indicate a net EOH reduction — the case for building. Research-only: not wired into the dashboard or simulation.

### `regenerative_investment_required(eoh_reduction_target, labor_type, epsilon, …)` → `dict`

Annual labour hours needed to achieve a target future EOH reduction rate through regenerative labour.

---

## Investment Ranking

These three are research-only tools — not wired into the dashboard or simulation.

### `rank_investment_candidates(candidates, epsilon)` → `list[dict]`

Ranks infrastructure investment candidates by their EOH reduction ratio. Highest-leverage investments first.

```python
from hours_eoh.core.eoh_dynamics import rank_investment_candidates

candidates = [
    {"name": "water treatment", "production_cost_eoh": 50_000,
     "annual_maintenance_eoh": 1_000, "annual_eoh_eliminated": 8_000, "design_life": 40},
    {"name": "road resurfacing", "production_cost_eoh": 10_000,
     "annual_maintenance_eoh": 400, "annual_eoh_eliminated": 500, "design_life": 10},
]
ranked = rank_investment_candidates(candidates, epsilon=0.40)
print([c["name"] for c in ranked])   # highest net EOH reduction first
```

### `optimal_investment(available_labor_eoh, candidates, epsilon)` → `dict`

Allocates a labour budget (`available_labor_eoh`, h/yr) across candidates to maximise EOH reduction.

### `maintenance_strategy_compare(asset_type, annual_eoh, teh_value, …)` → `dict`

Compares the total human-labour EOH cost of three strategies over a horizon — continuous maintenance, deferral to write-down, and replacement at write-down — and names the cheapest.
