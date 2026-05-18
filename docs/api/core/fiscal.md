# Fiscal Mechanics

**Module:** `hours_eoh/core/fiscal.py`

Levies, allocations, sufficiency guarantee, trust management, and the care stipend. All fiscal flows are circulatory — they redirect TEH but do not create or destroy it (except D2, D3, D6 destruction mechanisms).

---

## Levy Collection

### `levy_collection(teh_income, epsilon, p)` → `dict`

Collects levies from all registered labor income. Returns gross levy, net-of-threshold income, and levy breakdown.

---

## Trust Allocations

The Trust has three co-equal obligations. Neither is residual — both `ecological_allocation` and `stewardship_allocation` are primary claims on Trust revenue.

### `stewardship_allocation(capital_stock_teh, epsilon, p)` → `dict`

TEH directed toward fulfilling infrastructure entropy obligations from the capital stock. Grows with the capital stock, making it the dominant revenue-independent fiscal flow at high ε.

### `ecological_allocation(ecosystem_health, epsilon, p)` → `dict`

TEH directed toward ecological EOH fulfillment and natural system stewardship.

### `sufficiency_guarantee(epsilon, p)` → `dict`

The floor — minimum TEH guaranteed to every collective member. Real purchasing power rises automatically with automation (same nominal TEH, lower basket prices). See [Design Principle 5](../../theory/design_principles.md#5-the-floor-rises-with-automation-it-never-falls).

---

## Trust Management

### `trust_management(revenues, obligations, balance, p)` → `dict`

Full Trust solvency calculation — revenues in, obligations out, surplus/deficit.

### `fiscal_snapshot(epsilon, p)` → `dict`

Comprehensive fiscal state at ε — all revenue streams, all allocations, solvency status.

```python
from hours_eoh.core.fiscal import fiscal_snapshot

snap = fiscal_snapshot(0.40, p=p)
print(snap["fiscally_solvent"], snap["trust_surplus"])
```

### `trust_solvency_trajectory(epsilon_range, p)` → `list[dict]`

Trust solvency across a range of ε values.

### `min_levy_for_solvency(epsilon, p)` → `float`

Minimum levy rate that keeps the Trust solvent at ε.

---

## Care Stipend

### `care_stipend(caregiver_age, dependent_ages, epsilon, p)` → `dict`

TEH disbursed to recognized care providers. Follows a diminishing-returns structure (fewer TEH per additional dependent). Backed by verified personal EOH of the dependents.

### `aggregate_care_stipend_from_demographics(age_distribution, epsilon, p)` → `dict`

Total care stipend obligation from population demographics.

---

## Additional Functions

| Function | Description |
|----------|-------------|
| `steward_eoh_obligation(parcel_data, epsilon, p)` | EOH obligation for a land steward |
| `collective_land_registration(parcels, epsilon, p)` | Aggregate GUF flow into Trust from all parcels |
| `stewardship_dividend_needed(capital_stock, epsilon, p)` | Trust draw needed to fund stewardship labor |
| `accumulation_ceiling_commitment(balance, epsilon, p)` | D6 TEH removed when balance exceeds ceiling |
| `care_stipend(...)` | Care compensation for registered dependents |

---

## Key Design Invariant

The fiscal system must remain solvent at ε = 0 (near-zero creation and destruction) and at ε = 0.99 (near-zero creation and destruction from price collapse). Revenue streams that depend on production output are supplementary. The Stewardship Allocation — which scales with the capital stock — is the foundational revenue source that persists even at full automation.
