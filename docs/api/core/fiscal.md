# Fiscal Mechanics

**Module:** `hours_eoh/core/fiscal.py`

Levies, allocations, sufficiency guarantee, trust management, and the care stipend. All fiscal flows are circulatory — they redirect TEH but do not create or destroy it (except D2, D3, D6 destruction mechanisms).

---

## Levy Collection

### `levy_collection(labor_income, levy_rates)` → `dict`

Collects levies from labour income, each rate a fraction of gross. Circulatory: `worker_net + total_levied == labor_income`. Returns the total rate, total levied, worker net and the per-levy breakdown.

---

## Trust Allocations

Ecological and stewardship requirements are co-equal — neither is residual. Since 2026-09-15 (minted TEH is the wage) both are paid at the mint, not by the Trust; the Trust owes only the guarantee.

### `stewardship_allocation(capital_stock_teh, capital_age_ratio, epsilon, available_teh, …)` → `dict`

The TEH the infrastructure obligation of the capital stock calls for. It grows with the capital stock; since 2026-09-15 it is paid at the mint (as registered stewardship labour), so `trust_management` reports it as `paid_by_mint` and it is not a Trust expenditure.

### `ecological_allocation(ecosystem_health, epsilon, available_teh, …)` → `dict`

TEH directed toward ecological EOH fulfillment and natural system stewardship.

### `effective_personal_eoh(epsilon, personal_eoh_base, automation_response)` → `float`

Personal obligation hours per person that still need human labour at ε: the age-weighted obligation × its human-carried share. The obligation itself does not fall with automation; this does. Labour embodied in machine-delivered goods mints in infrastructure and is not in this share.

### `sufficiency_guarantee(population, epsilon, …)` → `dict`

The floor — minimum TEH guaranteed to every collective member. The EOH reimbursement pays `effective_personal_eoh(ε)` at `M_FLOOR`, 1 TEH per human obligation hour, so it buys the same human-carried obligation at every ε; any rise in purchasing power comes from the meaningful-activity term. `capital_personal_eoh_fulfilled_per_person` is deprecated and not applied. See [Design Principle 5](../../theory/design_principles.md#5-the-floor-rises-with-automation-it-never-falls).

---

## Trust Management

### `trust_management(trust_balance, levy_revenue, stewardship_cost, guarantee_cost, …)` → `dict`

Full Trust solvency calculation — revenues in, the guarantee out, surplus/deficit. `stewardship_cost` is returned as `paid_by_mint` and is not expenditure. Balance: `trust_end = start − guarantee + levy + GUF`; only what the Trust owes leaves it, and unspent dividend is retained (2026-09-15), so `ann_depreciation`, `dividend` and `renewal` are reporting only. What the balance and this period's inflows could not cover is `guarantee_unfunded`.

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
| `stewardship_dividend_needed(stewardship_teh_required, dep_rate, trust_balance)` | **Deprecated 2026-09-30.** Minimum `div_rate` for the Trust dividend to cover stewardship — a question the wage doctrine retired, since the Trust no longer pays stewardship |
| `accumulation_ceiling_commitment(teh_in_circulation, population, …)` | D6 — TEH above the accumulation ceiling, routed into capital formation |

---

## Key Design Invariant

The fiscal system must remain solvent across the whole arc, including both ends: at ε = 0, where almost none of the obligation is registered and creation is at its lowest, and at ε = 0.99, where human labour is a small share of the obligation and creation has fallen back from its late-arc peak while staying far above its ε = 0 level.

Under the wage doctrine (2026-09-15) the Trust owes one thing, the sufficiency guarantee. Registered labour — stewardship, ecological and care work included — is paid when it mints, not by the Trust. What flows in is the levy (a share of the mint) and the Ground Use Fee; what a collective brought with it is its opening balance. Solvency is therefore `levy + GUF` against the guarantee, with the balance as the buffer.

Where that holds is computed, not asserted. `scenarios.stationarity.stationary_bands()` reports the range of ε over which a collective founded with **no** prior work stands still in TEH; it covers nearly the whole arc and stops short of the top, where the mint falls and the guarantee does not. With the default prior work the balance carries that last stretch. Call the function for the edge rather than quoting it — it moves with the levy rate and the guarantee design.
