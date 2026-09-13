# Capital & Population

**Modules:** `hours_eoh/core/capital.py`, `hours_eoh/core/population.py`

These two modules model humans as capital stock. Capital is both physical (infrastructure, machines) and human (people). Both decay, both can be written down, and both generate EOH.

---

## Asset Lifecycle (capital.py)

### `make_asset(asset_id, asset_type, teh_value, annual_eoh, design_life, …)` → `Asset`

Construct a well-formed asset record — embedded TEH value, annual EOH, design life, age and condition. The same record type carries human capital (`is_human_capital=True`).

### `asset_condition(initial_condition, maintenance_history, …)` → `float`

Current condition (0.0 = irrecoverable, 1.0 = like-new) replayed from a maintenance history of `{"eoh_demanded", "eoh_fulfilled"}` periods: under-maintenance lowers it, a small natural decay applies every period, and surplus maintenance restores a little.

### `writedown_trigger(condition, …)` → `bool`

Returns `True` when condition has fallen below the recoverability threshold (default 0.2) and the asset should be written down.

### `execute_writedown(asset, …)` → `dict`

Executes a capital write-down (D1 destruction) and returns the ledger updates to apply.

!!! note "D1 is not interest"
    Capital write-down destroys TEH that was embodied in the asset. This is not interest — it measures a real physical loss. The obligation to rebuild or abandon remains; the TEH representing the now-failed capital is removed from circulation.

---

## Human Capital Lifecycle

### `birth_event(population, eoh_ledger_total, …)` → `dict`

Registers a new member: maximum personal EOH, zero entropy-reduction capacity. Apply the result with `apply_birth_eoh()`.

### `death_event(asset, workforce_size, …)` → `dict`

A human capital write-down — delegates to `execute_writedown()`. Apply the redistribution with `workforce.apply_death_redistribution()`. Estate TEH is a separate, aggregate mechanism: `estate_dissolution()` below.

### `maturation_update(asset, years_elapsed, …)` → `dict`

Updates a human capital asset's entropy-reduction capacity as it matures, with optional education and training EOH invested along the way.

### `estate_dissolution(teh_in_circulation, population, epsilon, …)` → `dict`

D5 TEH destruction — clears accumulated balance above the estate transfer cap at death.

---

## Aggregate Functions

| Function | Description |
|----------|-------------|
| `aggregate_personal_eoh_fulfilled(assets, population)` | Total personal EOH covered across a population |
| `aggregate_eoh_eliminated(assets)` | Total EOH reduction from infrastructure assets |
| `apply_birth_eoh(birth_result, current_total_personal_eoh)` | Apply birth EOH demand to population state |

---

## Population Structure (population.py)

### `aging(asset, …)` → `dict`

Advances one human capital asset's age by `years_elapsed` and updates its personal EOH and capacity accordingly. For a whole population, use `cohort_aging_trajectory()`.

### `population_eoh_curve(age_distribution, …)` → `list[dict]`

Personal EOH demand by age group — the shape of human capital depreciation.

### `population_lifecycle_snapshot(age_distribution, epsilon, …)` → `dict`

Comprehensive snapshot: EOH by age group, care obligations, working-age capacity.

### `cohort_aging_trajectory(initial_distribution, …)` → `dict`

Simulates year-by-year cohort flow — births, ageing between groups, elderly deaths — and tracks how the age distribution and its EOH demand shift.

### `age_group_for_age(age)` → `str`

Maps an age in years to its `AGE_GROUPS` key (`infant`, `child`, `working_age`, `elderly`).
