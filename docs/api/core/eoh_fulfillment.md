# EOH Fulfillment & Registration

**Modules:** `hours_eoh/core/eoh_fulfillment.py`, `hours_eoh/core/registration.py`

These two modules form the fulfillment pipeline: registration curves gate which EOH enters the collective ledger; the fulfillment functions turn registered EOH into TEH. Both are genuinely ε-driven.

---

## Registration (registration.py)

Registration curves are sigmoid functions of ε. Each domain uses a distinct curve.

### `personal_eoh_registration_share(epsilon, …)` → `float`

Share of personal EOH admitted to the collective ledger. Near-zero at ε = 0 (off-ledger subsistence), rising through the mid-automation range to most — not all — of personal EOH at ε = 0.99. It is a *demand* boundary (what the collective is formally accountable for), not a labor registration share.

!!! warning "Distinct mechanism from other domains"
    Personal EOH uses its own sigmoid — do not conflate with `total_registration_share()`. The two represent distinct mechanisms.

### `total_registration_share(epsilon, …)` → `float`

The weighted composite of care, production and stewardship registration, each weighted by its share of human EOH fulfillment at ε. The pipeline applies it to the non-personal domains.

### Domain-specific registration

```python
from hours_eoh.core.registration import (
    care_registration_share,
    production_registration_share,
    stewardship_registration_share,
    knowledge_eoh_registration_share,
    labor_category_weights,
    validate_registration_trajectory,
)
```

Each follows its own sigmoid with different inflection points. Care registration accelerates in the mid-ε range.

`validate_registration_trajectory(epsilon_sequence)` — verifies all registration curves are monotonically non-decreasing and well-behaved at the arc extremes.

---

## Fulfillment Pipeline (eoh_fulfillment.py)

### `human_eoh_share(total_eoh, epsilon)` → `float`

The uniform split factor `1 − ε`. **This is not the human share of the obligation** under the default per-component automation response: personal EOH has its own automation floors, so the human share is higher. Read `human_fraction` from `human_eoh_per_domain()` or the pipeline for that.

### `human_eoh_per_domain(total_eoh_dict, epsilon, …)` → `dict`

Applies the human/machine split to each domain's EOH.

### `registered_eoh(human_eoh, registration_share)` → `float`

EOH admitted to the collective ledger: `human_eoh × registration_share`.

### `teh_created(registered_eoh_hours, mean_multiplier)` → `float`

TEH entering circulation: `registered_eoh × mean_multiplier`.

### `teh_supply(teh_created_total, teh_destroyed_total)` → `float`

Net TEH for an economy that began with no endowment: cumulative creation minus cumulative destruction — Condition I's operational definition. It currently has no caller, and a test fails if it gains one.

### `capital_writedown(capital_stock_teh, …)` → `float`

D1 destruction: TEH removed when capital degrades beyond maintainability.

### `eoh_to_teh_pipeline(epsilon, …)` → `dict`

Full pipeline in one call — physical state (canonical where not supplied) → EOH → machine/human split → registration → TEH. With `available_labor_eoh` supplied, the mint is capped at the labour actually available and the shortfall is booked as deferral. Solvency is the fiscal layer's question, not this function's — see `fiscal_snapshot()` or `scenarios.collective.collective_snapshot()`.

```python
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

result = eoh_to_teh_pipeline(0.40)
# Returns, among others: teh_created, total_eoh, eoh_by_domain, human_eoh,
# registered_eoh, registration_share, human_fraction, epsilon_observable,
# labor_constrained, deferred_total. Supply available_labor_eoh= to mint from
# what was SERVED rather than what was demanded.
print(result["teh_created"], result["labor_constrained"])
```

---

## TEH Destruction Mechanisms

| D# | Name | Location |
|----|------|----------|
| D1 | Capital write-down | `capital.py` → `execute_writedown()` |
| D2 | Income-driven consumption | `simulation.py` → `simulate_period()` (the default) |
| D3 | Biology-anchored consumption | `simulation.py` → `simulate_period(use_d3=True)` |
| D4 | CPI delivery | `prices.py` → `cpi_goods_destruction()` |
| D5 | Estate dissolution | `capital.py` → `estate_dissolution()` |
| D6 | Accumulation ceiling | `fiscal.py` → `accumulation_ceiling_commitment()` |

Levies and Trust spending are *circulatory* — TEH moves, not destroyed.
