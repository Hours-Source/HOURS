# Conditions & Dashboard

**Modules:** `hours_eoh/core/conditions.py`, `hours_eoh/core/dashboard.py`

These modules form the structural integrity layer. `conditions.py` enforces the four Structural Conditions; `dashboard.py` provides health indicators and the system-level integrity check.

---

## Structural Conditions (conditions.py)

### `condition_i_check(teh_supply, teh_created_cumulative, teh_destroyed_cumulative, p)` → `dict`

Verifies the Ledger Identity: `teh_supply = teh_created − teh_destroyed`. Returns pass/fail with the computed gap.

### `condition_ii_check(mean_multiplier, p)` → `dict`

Verifies the Multiplier Band: population-weighted mean is within `[band_min, band_max]` and targeting the ideal.

### `balance_check(balance, income, p)` → `dict`

Verifies Condition III compliance for a single balance — that it grew only through income, not passive accumulation.

### `condition_iii_balance_growth_check(balance_history, income_history, p)` → `dict`

Verifies the Zero Interest condition over a history of balances and incomes.

### `condition_iv_check(competency_reserve_fraction, domain_allocations, p)` → `dict`

Verifies Distributed Competency: the workforce reserve fraction meets the threshold and essential domains are covered.

```python
from hours_eoh.core.conditions import condition_iv_check

result = condition_iv_check(
    competency_reserve_fraction=0.16,
    domain_allocations={"agriculture": 0.03, "healthcare": 0.04, ...},
    p=p
)
```

### `dashboard_snapshot(epsilon, p)` → `dict`

Single-call all-conditions check at ε.

### `domain_eoh_coverage(eoh_dict, fulfillment_dict, p)` → `dict`

Per-domain EOH coverage ratios — what fraction of each domain's EOH is being fulfilled.

---

## Dashboard (dashboard.py)

### `eoh_health_indicators(epsilon, p)` → `dict`

EOH-side health metrics: deferred ratio, domain balance, compounding risk.

### `fiscal_health_check(epsilon, p)` → `dict`

Fiscal health metrics: Trust solvency, sufficiency guarantee coverage, levy-to-guarantee ratio.

### `system_dashboard(epsilon, p)` → `dict`

Comprehensive system health snapshot. All four Structural Conditions, EOH health, fiscal health, pricing arc validity.

```python
from hours_eoh.core.dashboard import system_dashboard

snapshot = system_dashboard(epsilon=0.40, p=p)
# Returns: {
#   "condition_i": {"passed": True, ...},
#   "condition_ii": {"passed": True, "mean_multiplier": 2.05, ...},
#   "condition_iii": {"passed": True, ...},
#   "condition_iv": {"passed": True, "reserve_fraction": 0.16, ...},
#   "eoh_health": {...},
#   "fiscal_health": {...},
#   "overall": "GREEN"
# }
```

!!! important "The dashboard is the constitution's test bench"
    If the dashboard shows green, the system works. If it shows red, the papers have a problem, not the code. See [Design Principle 8](../../theory/design_principles.md#8-the-code-is-the-constitutions-test-bench).

---

The dashboard CLI mirrors this:

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```
