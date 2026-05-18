# Simulation Engine

**Module:** `hours_eoh/core/simulation.py`

Period-by-period simulation of the EOH/TEH economy. Tracks the full physical state across multiple periods, applying all core mechanics.

---

## `make_economy_state(epsilon, p)` → `dict`

Creates an initial economy state for simulation. Initializes all state variables from canonical physical state at ε.

```python
from hours_eoh.core.simulation import make_economy_state

state = make_economy_state(epsilon=0.30, p=p)
```

---

## `simulate_period(state, epsilon, p)` → `dict`

Advances the economy by one period at a given ε. Applies:

1. EOH generation from current physical state
2. EOH fulfillment pipeline (machine/human split, registration, TEH creation)
3. Fiscal mechanics (levy collection, Trust allocations, sufficiency guarantee)
4. TEH destruction mechanisms (D1–D6)
5. Capital aging and potential write-down trigger
6. Population aging

Returns the updated state plus a period summary dict.

```python
from hours_eoh.core.simulation import simulate_period

period_result = simulate_period(state, epsilon=0.30, p=p)
next_state = period_result["next_state"]
```

---

## `run_simulation(initial_epsilon, epsilon_delta, periods, p)` → `list[dict]`

Runs a multi-period simulation with ε growing by `epsilon_delta` each period.

```python
from hours_eoh.core.simulation import run_simulation

results = run_simulation(initial_epsilon=0.30, epsilon_delta=0.02, periods=20, p=p)
for period in results:
    print(f"Period {period['period']}: ε={period['epsilon']:.2f}  TEH={period['teh_created']:.0f}")
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
