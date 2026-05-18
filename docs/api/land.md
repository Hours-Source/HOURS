# Land — GUF Module

**Module:** `hours_eoh/land/guf.py`

14 functions implementing the Ground Use Fee framework (NLSA TM-0042). All functions follow the layer rules: `land/` imports from `core/` but is never imported by `core/`.

For the full mathematical specification, see [Ground Use Fee Framework](../theory/guf_framework.md).

---

## Core GUF Components

### `epsilon_scaling(epsilon)` → `float`

The Ψ(ε) bell-shaped function: `4 × ε^0.8 × (1−ε)^1.2 + 0.02`

Peaks near ε = 0.40 (Ψ ≈ 1.06), floors at 0.02 at both extremes. Shape parameters `a=0.8`, `b=1.2`, `floor=0.02` are named constants in `data.py`.

### `labor_content_scaling(epsilon)` → `float`

The α(ε) function: `(1−ε)^0.8 + 0.05`, normalized so α(0.40) = 1.0. Scales Use Category Coefficients for the declining labor content of land-use activities.

### `location_value_index(centrality, transit, services, natural_amenity, weights)` → `float`

L(p) — weighted composite of four sub-indices (Eq. 3).

### `use_category_coefficient(use_category, epsilon)` → `float`

U(p,ε) — reference rate for the use category scaled by α(ε) (Eq. 9).

### `demand_pressure_modifier(demand_supply_ratio, eta)` → `float`

D(p) — logarithmic demand modifier, capped at 1.8 (Eq. 11).

### `ecosystem_service_kappa(kappa_ref, beta, epsilon)` → `float`

κ_s(ε) — labor-time replacement cost per unit of ecosystem service at ε (Eq. 15). Cost contracts with automation — the same ecosystem service costs less to engineer as ε rises.

### `ecosystem_displacement_surcharge(services, epsilon)` → `dict`

E(p,ε) — annualized labor-time cost of natural services displaced by development (Eq. 14).

### `infrastructure_proximity_premium(assets, parcel_location)` → `dict`

I(p,ε) — annualized share of collectively funded infrastructure cost attributed to the parcel (Eq. 16).

---

## Full GUF Calculation

### `base_fee(area_slu, location_value, use_category, epsilon, ...)` → `dict`

Base fee component: `A(p) × L(p) × U(p,ε) × D(p) × Z(p)`.

### `ground_use_fee(area_slu, location_value, use_category, epsilon, ...)` → `dict`

Master equation (Eq. 1): `GUF(p) = Ψ(ε) × [base + E + I] × Ω`, applying the GUF floor.

```python
from hours_eoh.land.guf import ground_use_fee

result = ground_use_fee(
    area_slu=3.5,
    location_value=0.629,
    use_category="residential_primary",
    epsilon=0.40,
)
print(result["guf_formula"], result["floor_applied"])
```

---

## Rate Constraints

### `review_cycle_cap(guf_formula, guf_previous, phi)` → `float`

Rate-change cap (Eq. 22): `min(guf_formula, guf_previous × (1 + φ))`. Default φ = 0.10.

### `income_linked_subsidy(guf_applied, income_teh, median_income_teh)` → `float`

Income adjustment factor σ (Eq. 23–24): leaseholders below 40% of median pay 25% of GUF.

### `soil_health_credit(area_slu, delta_shi, c_soil)` → `float`

Soil Health Index credit for agricultural parcels (Eq. 26): `−c_soil × A(p) × ΔSHI`.

### `guf_trust_inflow(guf_revenues, subsidies_absorbed)` → `dict`

Net Trust revenue from GUF flows after subsidy absorption.

---

## Ecological Write-Down (NLSA §9)

### `rebuilding_surcharge(services_lost, epsilon, amortization_years)` → `dict`

R_b(p,ε) — annualized replacement cost of lost ecosystem services (Eq. 28):
`R_b = Σ_s [V_s_lost × κ_s(ε)] / Y_r`

```python
from hours_eoh.land.guf import rebuilding_surcharge

result = rebuilding_surcharge(
    services_lost=[{"label": "biodiversity", "volume_lost": 5.0, "kappa_ref": 0.35, "beta": 0.7}],
    epsilon=0.40,
    amortization_years=50,
)
```

### `ground_use_fee_writedown(area_slu, ..., services_reset, services_lost, ...)` → `dict`

Modified GUF during a write-down event (Eq. 29):
`GUF_wd = Ψ × [base + E_reset + I + R_b] × Ω`

- `services_reset=None, services_lost=None` → restoration pathway (E uses recovery target baseline)
- `services_lost=[...]` → abandonment pathway (R_b surcharge added)

```python
from hours_eoh.land.guf import ground_use_fee_writedown

result = ground_use_fee_writedown(
    area_slu=3.5,
    epsilon=0.40,
    services_reset=[{"label": "water", "volume": 0.4, "kappa_ref": 1.65, "beta": 0.8, "retained": 0.3}],
    services_lost=None,  # restoration pathway
)
```

### `eoh_accumulation_warning(unfulfilled_eoh, total_eoh, threshold)` → `dict`

Preventive signal (§9.8): `ratio = unfulfilled / total`. Warning triggers when `ratio > threshold` (default 0.30).

```python
from hours_eoh.land.guf import eoh_accumulation_warning

result = eoh_accumulation_warning(unfulfilled_eoh=450_000, total_eoh=1_200_000)
# Returns: {ratio, threshold, warning, accelerated_rho_review, ecology_fund_priority}
```
