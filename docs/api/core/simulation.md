# Simulation Engine

**Module:** `hours_eoh/core/simulation.py`

Period-by-period simulation of the EOH/TEH economy. Tracks the full physical state across multiple periods, applying all core mechanics.

---

## `make_economy_state(epsilon, …)` → `dict`

Creates an initial economy state for simulation: every quantity that persists between periods. Fields left unsupplied take the function's defaults — the capital stock, knowledge complexity and monitoring capability from the canonical arc at ε, the rest from fixed defaults. Per-period inputs such as levy rates are passed to `simulate_period()` rather than stored in the state.

```python
from hours_eoh.core.simulation import make_economy_state

state = make_economy_state(epsilon=0.30)
```

---

## `simulate_period(state, epsilon_delta, …)` → `tuple[dict, dict]`

Advances the economy by one period from the ε carried in `state`. Per-period
inputs (growth and degradation rates, levy rates, `epsilon_delta`) are keyword
arguments, not state. Applies, in causal order:

1. Population grows or shrinks by the growth rate
2. Capital ages, and grows through investment
3. Ecosystem degrades or restores, and deferred ecological EOH accumulates
4. The EOH → TEH pipeline (machine/human split, registration, TEH creation)
5. Fiscal mechanics (levies, stewardship, the sufficiency guarantee, the Trust balance)
6. TEH destruction (see the table below)
7. State update: ε advances and cumulative TEH is carried forward

The period does not mutate `state`; it returns a fresh one.

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

Each destruction mechanism is switched by a keyword argument of `simulate_period()`:

| Period event | D# | How the period applies it | Default |
|---|---|---|---|
| Capital write-down | D1 | A failure rate on the capital stock, reduced as monitoring improves — an aggregate proxy, not `execute_writedown()` per asset | always on |
| Income-driven consumption | D2 | A consumption rate on period income (net wages plus the Trust dividend), falling as purchasing power rises | on, unless `use_d3=True` |
| Biology-anchored consumption | D3 | On-ledger personal EOH converted to baskets at the basket price | `use_d3=False` |
| Capital-delivered services | D4 | `cpi_goods_destruction()` | `use_cpi_destruction=True` |
| Death events | D5 | `estate_dissolution()`; the estate levy returns to the Trust | `use_estate_dissolution=True` |
| Accumulation ceiling | D6 | `accumulation_ceiling_commitment()` — commits the excess to capital formation rather than destroying it | `use_accumulation_ceiling=False` |

Levy collection and Trust spending are circulatory (TEH redirected, not destroyed).
