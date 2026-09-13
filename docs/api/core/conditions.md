# Conditions & Dashboard

**Modules:** `hours_eoh/core/conditions.py`, `hours_eoh/core/dashboard.py`

These modules form the structural integrity layer. `conditions.py` enforces the four Structural Conditions; `dashboard.py` provides health indicators and the system-level integrity check.

---

## Structural Conditions (conditions.py)

### `condition_i_check(teh_created, teh_destroyed, teh_observed, …)` → `dict`

Verifies the Ledger Identity: `teh_supply = teh_created − teh_destroyed`. Returns pass/fail with the computed gap.

### `condition_ii_check(mean_multiplier, …)` → `dict`

Verifies the Multiplier Band: population-weighted mean is within `[band_min, band_max]` and targeting the ideal.

### `balance_check(balance_start, earnings, expenditures, balance_end, …)` → `dict`

Verifies Condition III compliance for a single balance — that it grew only through income, not passive accumulation.

### `condition_iii_balance_growth_check(prev_balance, new_balance, labor_income, expenditure, …)` → `dict`

Verifies the Zero Interest condition over a history of balances and incomes.

### `condition_iv_check(workforce, competent_workers, …)` → `dict`

Verifies Distributed Competency: the workforce reserve fraction meets the threshold and essential domains are covered.

```python
from hours_eoh.core.conditions import condition_iv_check

result = condition_iv_check(
    workforce=600_000,
    competent_workers=96_000,
    domain_coverage={"agriculture": 0.03, "healthcare": 0.04},
)
print(result["passes"], result["reserve_fraction"], result["status"])
```

### `dashboard_snapshot(teh_created, teh_destroyed, teh_observed, mean_multiplier, balance_start, earnings, expenditures, balance_end, workforce, competent_workers, epsilon, …)` → `dict`

Single-call all-conditions check at ε.

### `domain_eoh_coverage(reserve_result, domain_eoh_demands, …)` → `dict`

Per-domain EOH coverage ratios — what fraction of each domain's EOH is being fulfilled.

---

## Dashboard (dashboard.py)

### `eoh_health_indicators(total_eoh, fulfilled_eoh, epsilon, …)` → `dict`

EOH-side health metrics: deferred ratio, domain balance, compounding risk.

### `fiscal_health_check(trust_balance, labor_income, capital_stock_teh, capital_age_ratio, population, floor_teh, epsilon, …)` → `dict`

Fiscal health metrics: Trust solvency, sufficiency guarantee coverage, levy-to-guarantee ratio.

### `system_dashboard(epsilon, teh_created, teh_destroyed, teh_observed, balance_start, earnings, expenditures, balance_end, certified_by_domain, workforce_size, total_eoh, fulfilled_eoh, trust_balance, labor_income, capital_stock_teh, capital_age_ratio, population, floor_teh, …)` → `dict`

Comprehensive system health snapshot. All four Structural Conditions, EOH health, fiscal health, pricing arc validity.

`system_dashboard()` takes the period's accounts as keyword arguments — TEH
created, destroyed and observed, the Trust's opening and closing balance, the
certified workforce by domain, total and fulfilled EOH — because a structural
check is only as good as the ledger figures it is given. The quickest way to see
it assembled is the CLI:

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```

**Read the CLI's assembly as a demonstration, not a measurement.** Several of the
accounts it passes are stand-ins built inside `utils/dashboard_cmd.py` rather
than tracked quantities. For a real collective, pass your own ledger figures.

!!! important "The dashboard is the constitution's test bench"
    Green means every check it runs passes on the accounts it was given — not that the system works. A yellow or red reading is reported, never tuned away. See [Design Principle 8](../../theory/design_principles.md#8-the-code-is-the-constitutions-test-bench).

---

The dashboard CLI mirrors this:

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```
