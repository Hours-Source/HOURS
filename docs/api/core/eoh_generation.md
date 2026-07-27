# EOH Generation

**Module:** `hours_eoh/core/eoh_generation.py`

Measurement-driven — these functions take the actual physical state of the civilization and return entropy obligations, derived from physical inputs via calibrated constants. ε is not a primary input here; these functions measure what entropy demands, not who fulfills it.

---

## Four Domain Functions

### `personal_eoh(population, age_distribution, ..., p)` → `float`

Entropy obligation from human bodies — biological needs across the population.

**Inputs:** population, age distribution, `p: EohParams`

**Arc:** At ε = 0 this domain consumes nearly all labor. The physical obligation never disappears — only who (or what) fulfills it changes.

---

### `infrastructure_eoh(capital_stock_teh, capital_age_ratio, ..., p)` → `float`

Entropy obligation from built systems — maintenance burden of the capital stock.

**Inputs:** capital stock in TEH, capital age ratio (older stock generates more EOH), monitoring capability, `p`

**Arc:** Grows as the capital stock expands. Drives increasing stewardship obligation at high ε.

---

### `ecological_eoh(ecosystem_health, monitoring_capability, ..., p)` → `float`

Entropy obligation from natural systems — what ecosystem degradation demands.

**Inputs:** ecosystem health index, monitoring capability, `p`

**Arc:** Independent of automation level. Compounding consequences when neglected.

---

### `knowledge_eoh(knowledge_base_size, knowledge_complexity_per_unit, ..., p)` → `float`

Entropy obligation from information systems — skill atrophy, institutional memory, standard drift.

**Arc:** Grows monotonically with ε; becomes the dominant domain at high automation.

---

## `total_eoh(**physical_state, p)` → `dict`

Aggregate entropy obligation across all four domains.

```python
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.trajectory import canonical_physical_state

state = canonical_physical_state(0.40)
eoh = total_eoh(**state, p=p)
# Returns: {personal, infrastructure, ecological, knowledge, total}
```

---

## Supporting Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `ecological_eoh_breakdown(...)` | `dict` | Decompose ecological EOH by service category |
| `domain_labor_requirements(eoh_dict, epsilon, p)` | `dict` | Human labor requirements per domain |
| `eoh_to_essential_domains(total_eoh, epsilon, p)` | `dict` | EOH allocation for Condition IV competency modeling |
| `epsilon_delta_sensitivity(epsilon, delta, p)` | `dict` | Sensitivity of EOH totals to Δε at a given point |

---

!!! important "Design invariant"
    EOH generation functions must not use ε to proxy physical assumptions. If ε is accepted as an optional backward-compat parameter, it must call `canonical_physical_state(epsilon)` to derive physical state — it must never use ε directly inside EOH calculation logic. See [Extending the Library](../../guides/extending.md#eoh-generation-functions).
