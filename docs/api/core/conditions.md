# Conditions & Dashboard

**Modules:** `hours_eoh/core/conditions.py`, `hours_eoh/core/dashboard.py`

These modules form the structural integrity layer. `conditions.py` enforces the four Structural Conditions; `dashboard.py` provides health indicators and the system-level integrity check.

---

## Structural Conditions (conditions.py)

### `condition_i_check(teh_created, teh_destroyed, teh_observed, …)` → `dict`

Verifies the Ledger Identity: TEH in circulation equals cumulative creation minus cumulative destruction. A gap means TEH was created outside the fulfillment pipeline or destroyed by a mechanism other than terminal consumption or capital write-down.

### `condition_ii_check(mean_multiplier, …)` → `dict`

Verifies the Multiplier Band: the population-weighted mean is within `[band_low, band_high]`. Delegates to `multipliers.multiplier_band_check()`.

### `balance_check(balance_start, earnings, expenditures, balance_end, …)` → `dict`

Verifies Condition III for one balance: `B(t+Δt) = B(t) + E − X`, with no third term.

### `condition_iii_balance_growth_check(prev_balance, new_balance, labor_income, expenditure, …)` → `dict`

The same zero-interest invariant for a single period, stated as a balance delta: the only valid source of growth is labor income minus expenditure.

### `condition_iv_check(workforce, competent_workers, …)` → `dict`

Verifies Distributed Competency: the share of the workforce with certified competency across essential domains meets the recommended threshold (15.5%).

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

### `condition_iv_coverage(reserve_result, pipeline, demand="registered", …)` → `dict`

Whether the people certified in each essential domain can carry its work — Condition IV in hours. Capacity is `certified × hours_per_certified_worker` (default `MEASURED_CAPACITY_H_YR`, the measured adult capacity), independent of ε. Demand is read off an `eoh_to_teh_pipeline` result — `"registered"` hours by default (the register is what the collective carries), or `"human"` — and mapped onto the seven essential domains by `eoh_generation.eoh_to_essential_domains`. A domain is covered or it is not; no threshold is chosen. Returns `per_domain`, `domains_short`, `all_covered`, `status`.

`demand="personal"` reads only the registered PERSONAL hours — the survival tier: Condition IV is first about whether the agents' own needs have competent hands, and the rest can be rebuilt as the arc climbs (author, 2026-10-01). Hours no essential domain is certified for are reported as `unattributed_eoh`, never counted short. The bridge's personal column is derived from the obligation's components; the other three columns are the original judgement. At the Condition IV minimum healthcare is short over a band of the upper arc in both registered readings, because care — most of the personal obligation — has no essential domain of its own and is set against healthcare.

### `domain_eoh_coverage(reserve_result, domain_eoh_demands, …)` → `dict` — deprecated

Kept with unchanged output so earlier figures reproduce; warns. It sized a certified worker as `H_MIN × mean_multiplier × (1 − ε)` — hours times the TEH multiplier, shrinking as machines take share — and so reported Condition IV failing at every ε, worse with automation. Use `condition_iv_coverage`.

---

## Dashboard (dashboard.py)

### `eoh_health_indicators(total_eoh, fulfilled_eoh, epsilon, …)` → `dict`

EOH-side health: the deferred-maintenance ratio, the compounding rate of the deferred backlog, registration coverage, and the personal registration share.

### `fiscal_health_check(trust_balance, labor_income, capital_stock_teh, capital_age_ratio, population, floor_teh, epsilon, …)` → `dict`

Fiscal health: Trust solvency (can it fund the guarantee — stewardship and ecological labour are paid at the mint, not by the Trust, and are reported rather than owed), the floor purchasing-power index, and levy sufficiency — whether inflows cover the guarantee or the Trust is drawing down principal to pay it.

### `system_dashboard(epsilon, teh_created, teh_destroyed, teh_observed, balance_start, earnings, expenditures, balance_end, certified_by_domain, workforce_size, total_eoh, fulfilled_eoh, trust_balance, labor_income, capital_stock_teh, capital_age_ratio, population, floor_teh, …)` → `dict`

Comprehensive system health snapshot: all four Structural Conditions, EOH health and fiscal health in one report. The overall status is the worst of the individual statuses.

`system_dashboard()` takes the period's accounts as keyword arguments — TEH
created, destroyed and observed, the Trust's opening and closing balance, the
certified workforce by domain, total and fulfilled EOH — because a structural
check is only as good as the ledger figures it is given. The quickest way to see
it assembled is the CLI:

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```

**Read the CLI's assembly as a demonstration on the reference frame, not a
measurement of a collective.** Its EOH accounts come from the pipeline, and its
ledger and Trust accounts from one simulated period on the same frame. One input
is declared rather than tracked — the certified share of the workforce, which
nothing in the package measures (`--certified-fraction`) — and the command prints
it as declared. For a real collective, pass your own ledger figures.

**Condition IV is read twice.** `condition_iv` is the certified *fraction* per
domain against the threshold. `condition_iv_hours` asks whether those people can
carry the *hours* (`condition_iv_coverage`), in two tiers: a shortfall against
the agents' own registered needs (`personal`) is RED and fails the condition; a
shortfall only against everything the collective registers (`registered`) is
YELLOW. A reserve can pass the fraction and fail the hours: at the CLI's
declared 0.18 it does over a band of the upper arc, in care. Pass `pipeline=`
(an `eoh_to_teh_pipeline` result) to read both at your own state; without it the
dashboard computes one from the fiscal arguments.

!!! important "The dashboard is the constitution's test bench"
    Green means every check it runs passes on the accounts it was given — not that the system works. A yellow or red reading is reported, never tuned away. See [Design Principle 8](../../theory/design_principles.md#8-the-code-is-the-constitutions-test-bench).
