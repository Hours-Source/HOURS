# EOH Generation

**Module:** `hours_eoh/core/eoh_generation.py`

Measurement-driven — these functions take the actual physical state of the civilization and return entropy obligations, derived from physical inputs via calibrated constants. ε is not a primary input here; these functions measure what entropy demands, not who fulfills it.

---

## Four Domain Functions

### `personal_eoh(population, age_distribution, …)` → `float`

Entropy obligation from human bodies — biological needs across the population.

**Inputs:** population, age distribution, and the personal standard (`survival`, the operating base, or `sufficiency`)

**Arc:** At ε = 0 this domain consumes nearly all labor. The physical obligation never disappears — only who (or what) fulfills it changes.

---

### `infrastructure_eoh(capital_age_ratio, …)` → `float`

Entropy obligation from built systems — maintenance burden of the capital stock.

**Inputs:** capital stock in TEH — the stock you hold now, used exactly as supplied — and capital age ratio (older stock generates more EOH)

**Arc:** Grows as the capital stock expands. Drives increasing stewardship obligation at high ε.

---

### `ecological_eoh(ecosystem_health, monitoring_capability, …)` → `float`

Entropy obligation from natural systems — what ecosystem degradation demands.

**Inputs:** ecosystem health index, monitoring capability, the stewarded area, and the ecological STOCKS — deferred ecological EOH, the thermal obligation and the restoration obligation

**Arc:** Independent of automation level. **Since the Phase 4e/4f partition the domain carries stocks only**: the recurring cost of land at reference condition, and its response to degradation, belong to the Ground Use Fee, where they scale with land held. With no stock supplied the domain is zero — which is an assignment, not an absence.

---

### `knowledge_eoh(knowledge_base_size, …)` → `float`

Entropy obligation from information systems — skill atrophy, institutional memory, standard drift.

**Arc:** Grows monotonically with ε, from almost nothing at subsistence to roughly a third of the obligation at ε = 0.99. It does not become dominant: personal EOH remains the largest domain across the whole arc (`eoh arc --domain-shares`).

---

## `total_eoh(…)` → `dict[str, float]`

Aggregate entropy obligation across all four domains.

```python
from hours_eoh.core.eoh_generation import total_eoh

# Canonical arc at ε = 0.40 (the physical state is filled from the reference arc)
eoh = total_eoh(epsilon=0.40)

# Or real physical state, which is the point of the generation layer
eoh = total_eoh(population=5_000_000, capital_stock=8.0e9, capital_age_ratio=0.45,
                ecosystem_health=0.68, monitoring_capability=0.55)
# Returns: {personal, infrastructure, ecological, knowledge, total, ...}
print(eoh["total"])
```

---

## Supporting Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `ecological_eoh_breakdown(ecosystem_health, …)` | `dict` | The terms that sum to `ecological_eoh()` — baseline, spike, visible deferred and thermal |
| `domain_labor_requirements(eoh_by_domain, epsilon, …)` | `dict` | Headcount needed per domain: the human-labor share divided by annual hours per worker |
| `eoh_to_essential_domains(eoh_by_domain, …)` | `dict` | The four EOH domains distributed across the seven essential workforce domains, for Condition IV |
| `epsilon_delta_sensitivity(base_epsilon, delta_epsilon, …)` | `dict` | Sensitivity of EOH totals to Δε at a given point |

---

!!! important "Design invariant"
    EOH generation functions must not use ε to proxy physical assumptions. If ε is accepted as an optional backward-compat parameter, it must call `canonical_physical_state(epsilon)` to derive physical state — it must never use ε directly inside EOH calculation logic. See [Extending the Library](../../guides/extending.md#eoh-generation-functions).
