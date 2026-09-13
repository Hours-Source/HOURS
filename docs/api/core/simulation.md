# Simulation Engine

**Module:** `hours_eoh/core/simulation.py`

Period-by-period simulation of the EOH/TEH economy. Tracks the full physical state across multiple periods, applying all core mechanics.

---

## `make_economy_state(epsilon, …)` → `dict`

Creates an initial economy state for simulation. Initializes all state variables from canonical physical state at ε.

```python
from hours_eoh.core.simulation import make_economy_state

state = make_economy_state(epsilon=0.30)
```

---

## `simulate_period(state, epsilon_delta, …)` → `tuple[dict, dict]`

Advances the economy by one period from the ε carried in `state`. Per-period
inputs (growth and degradation rates, levy rates, `epsilon_delta`) are keyword
arguments, not state. Applies:

1. EOH generation from current physical state
2. EOH fulfillment pipeline (machine/human split, registration, TEH creation)
3. Fiscal mechanics (levy collection, Trust allocations, sufficiency guarantee)
4. TEH destruction mechanisms (D1–D6)
5. Capital aging and potential write-down trigger
6. Population aging

Returns `(next_state, period_result)`.

```python
from hours_eoh.core.simulation import simulate_period

next_state, period_result = simulate_period(state)
print(next_state["period"], period_result["teh_created"])
```

---

## `run_simulation(initial_state, n_periods, …)` → `dict`

Runs `simulate_period` repeatedly from an initial state; any per-period keyword
(such as `epsilon_delta`) is forwarded to every period. Returns `states`,
`period_results`, `final_state`, `summary`, `solvent_all` and `first_insolvency`.

```python
from hours_eoh.core.simulation import run_simulation

results = run_simulation(make_economy_state(epsilon=0.30), n_periods=20,
                         epsilon_delta=0.02)
print(results["solvent_all"], results["first_insolvency"])
for row in results["period_results"]:
    print(f"ε={row['epsilon']:.2f}  TEH={row['teh_created']:.3e}")
```

The CLI wrapper:

```bash
python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02
```

---

## TEH Lifecycle in the Simulation

The simulation engine explicitly models all six destruction mechanisms:

| Period event | D# | Function |
|---|---|---|
| Capital write-down | D1 | `execute_writedown()` when `writedown_trigger()` fires |
| Income-driven consumption | D2 | Applied to all income above floor |
| Biology-anchored consumption | D3 | Applied to biological consumption events |
| CPI basket delivery | D4 | `cpi_goods_destruction()` |
| Death events | D5 | `estate_dissolution()` |
| Accumulation ceiling | D6 | `accumulation_ceiling_commitment()` |

Levy collection and Trust spending are circulatory (TEH redirected, not destroyed).
