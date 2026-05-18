# Capital & Population

**Modules:** `hours_eoh/core/capital.py`, `hours_eoh/core/population.py`

These two modules model humans as capital stock. Capital is both physical (infrastructure, machines) and human (people). Both decay, both can be written down, and both generate EOH.

---

## Asset Lifecycle (capital.py)

### `make_asset(capital_teh, design_life, epsilon_at_build, ...)` → `Asset`

Create an asset record with embedded TEH cost, design life, and condition state.

### `asset_condition(asset, current_age)` → `float`

Current physical condition of an asset (0.0 = failed, 1.0 = new). Condition declines non-linearly — slower early, accelerating near end of design life.

### `writedown_trigger(asset, threshold, p)` → `bool`

Returns `True` when an asset has degraded below the maintainability threshold and should be written down.

### `execute_writedown(asset, p)` → `dict`

Executes a capital write-down (D1 destruction). Returns the TEH destroyed and the new EOH obligation.

!!! note "D1 is not interest"
    Capital write-down destroys TEH that was embodied in the asset. This is not interest — it measures a real physical loss. The obligation to rebuild or abandon remains; the TEH representing the now-failed capital is removed from circulation.

---

## Human Capital Lifecycle

### `birth_event(age_distribution, p)` → `dict`

Models a birth event — increases personal EOH demand, starts the care registration clock.

### `death_event(worker, eoh_redistributed, p)` → `dict`

D5 estate dissolution — clears personal EOH, distributes estate TEH, redistributes EOH obligations to remaining workers or automation.

### `maturation_update(person, years_elapsed, p)` → `dict`

Advances a person's age/capacity state. Tracks the progressive shift from high-EOH-low-output (child) to low-EOH-high-output (working age) to high-EOH-low-output (elder).

### `estate_dissolution(balance, epsilon, p)` → `float`

D5 TEH destruction — clears accumulated balance above the estate transfer cap at death.

---

## Aggregate Functions

| Function | Description |
|----------|-------------|
| `aggregate_personal_eoh_fulfilled(assets, epsilon, p)` | Total personal EOH covered across a population |
| `aggregate_eoh_eliminated(assets, epsilon, p)` | Total EOH reduction from infrastructure assets |
| `apply_birth_eoh(population, births, p)` | Apply birth EOH demand to population state |

---

## Population Structure (population.py)

### `aging(age_distribution, years, p)` → `dict`

Advances the population's age distribution by `years`. Adjusts EOH demand and entropy-reduction capacity.

### `population_eoh_curve(age_distribution, p)` → `dict`

Personal EOH demand by age group — the shape of human capital depreciation.

### `population_lifecycle_snapshot(age_distribution, epsilon, p)` → `dict`

Comprehensive snapshot: EOH by age group, care obligations, working-age capacity.

### `cohort_aging_trajectory(cohort_age, years, p)` → `list[dict]`

Track a single cohort's EOH profile as it ages.

### `age_group_for_age(age)` → `str`

Maps an age (in years) to an age group label (`child`, `young_adult`, `working_age`, `elder`).
