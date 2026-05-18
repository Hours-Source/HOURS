# EOH Fulfillment & Registration

**Modules:** `hours_eoh/core/eoh_fulfillment.py`, `hours_eoh/core/registration.py`

These two modules form the fulfillment pipeline: registration curves gate which EOH enters the collective ledger; the fulfillment functions turn registered EOH into TEH. Both are genuinely ε-driven.

---

## Registration (registration.py)

Registration curves are sigmoid functions of ε. Each domain uses a distinct curve.

### `personal_eoh_registration_share(epsilon, p)` → `float`

Share of personal EOH admitted to the collective ledger. Near-zero at ε = 0 (off-ledger subsistence), rising through the mid-automation range, approaching 1.0 before ε = 1.

!!! warning "Distinct mechanism from other domains"
    Personal EOH uses its own sigmoid — do not conflate with `total_registration_share()`. The two represent distinct mechanisms.

### `total_registration_share(epsilon, p)` → `float`

Labor composite registration share for non-personal domains (infrastructure, ecological, knowledge, care, production, stewardship).

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

`validate_registration_trajectory(p)` — verifies all registration curves are monotonically non-decreasing and well-behaved at the arc extremes.

---

## Fulfillment Pipeline (eoh_fulfillment.py)

### `human_eoh_share(epsilon)` → `float`

Share of total EOH fulfilled by human labor: `1 − ε`.

### `human_eoh_per_domain(eoh_dict, epsilon)` → `dict`

Applies the human/machine split to each domain's EOH.

### `registered_eoh(human_eoh, registration_share)` → `float`

EOH admitted to the collective ledger: `human_eoh × registration_share`.

### `teh_created(registered_eoh_value, mean_multiplier)` → `float`

TEH entering circulation: `registered_eoh × mean_multiplier`.

### `teh_supply(epsilon, p)` → `float`

Total TEH in the system at ε.

### `capital_writedown(capital_teh, writedown_fraction)` → `float`

D1 destruction: TEH removed when capital degrades beyond maintainability.

### `eoh_to_teh_pipeline(epsilon, p)` → `dict`

Full pipeline in one call — canonical physical state → EOH → registration → TEH → fiscal solvency check.

```python
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

result = eoh_to_teh_pipeline(0.40, p=p)
# Returns: teh_created, registration_share, fiscally_solvent, component breakdown
```

---

## TEH Destruction Mechanisms

| D# | Name | Location |
|----|------|----------|
| D1 | Capital write-down | `capital.py` → `execute_writedown()` |
| D2 | Income-driven consumption | `fiscal.py` |
| D3 | Biology-anchored consumption | `fiscal.py` |
| D4 | CPI delivery | `prices.py` → `cpi_goods_destruction()` |
| D5 | Estate dissolution | `capital.py` → `estate_dissolution()` |
| D6 | Accumulation ceiling | `fiscal.py` → `accumulation_ceiling_commitment()` |

Levies and Trust spending are *circulatory* — TEH moves, not destroyed.
