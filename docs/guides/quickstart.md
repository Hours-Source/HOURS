# Quick Start

## Installation

```bash
git clone https://github.com/Hours-Source/HOURS
cd HOURS
pip install -e ".[dev]"
```

Requires Python ≥ 3.10.

---

## First Code: the EOH → TEH Pipeline

```python
from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.params import EohParams

p = EohParams()

# Physical state on the canonical arc at ε = 0.40 (current equilibrium reference)
state = canonical_physical_state(0.40)

# Aggregate entropy obligation from physics
eoh = total_eoh(**state, p=p)
print(f"Total EOH: {eoh:.3e}")

# Full EOH → TEH pipeline at ε = 0.40
result = eoh_to_teh_pipeline(0.40, p=p)
print(f"TEH created: {result['teh_created']:.1f}")
print(f"Fiscally solvent: {result['fiscally_solvent']}")
```

`canonical_physical_state(ε)` gives the ideal-arc reference physical state at a given ε. Real simulations pass actual tracked state.

---

## Arc Coherence Check

Verify the system behaves correctly across the full ε arc:

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

results = epsilon_sweep()
for row in results:
    print(f"ε={row['epsilon']:.2f}  TEH={row['teh_created']:.0f}  solvent={row['fiscally_solvent']}")
```

Every mechanism must produce meaningful output at all four arc waypoints:

| ε | Description | Expected behavior |
|---|---|---|
| 0.00 | Subsistence | Near-zero TEH, minimal registration |
| 0.40 | Current equilibrium | Calibration reference point |
| 0.90 | Near-post-scarcity | Prices falling, care registration high |
| 0.99 | Effective post-scarcity | Near-zero prices, floor still rising |

---

## Structural Conditions Check

```python
from hours_eoh.core.dashboard import system_dashboard

snapshot = system_dashboard(epsilon=0.40)
for key, val in snapshot.items():
    print(f"{key}: {val}")
```

All four Structural Conditions should be green. See [Structural Conditions](../theory/structural_conditions.md).

---

## CLI Quick Start

The research CLI lets you explore the system without writing Python:

```bash
python3 utils/eoh_cli.py arc --points 10
```

Output:

```
ε      personal  infra     eco       knowledge  total_eoh  reg%   teh_created  price    floor_pp  solvent
-----  --------  --------  --------  ---------  ---------  -----  -----------  -------  --------  -------
0.000  2.212B    65.000M   555.556K  0.100      2.278B     15.1%  70.210M      120.000  1.000     Y
0.110  2.213B    77.620M   566.434K  0.152      2.291B     27.7%  133.783M     113.773  1.068     Y
...
0.990  2.220B    223.202M  712.251K  9.733      2.444B     94.2%  44.987M      21.546   5.570     Y
```

System dashboard:

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```

```
System Dashboard — ε = 0.400  [GREEN]

Structural Conditions
  I   — Ledger Identity:         OK
  II  — Multiplier Band:         OK
  III — Zero Interest:           OK
  IV  — Distributed Competency:  OK
```

For the full CLI reference see [CLI Reference](cli.md).

---

## Ground Use Fee

```bash
python3 utils/eoh_cli.py guf calculate --epsilon 0.40 --area-slu 3.5 \
    --use-category residential_primary --location-value 0.629
```

See [CLI Reference — GUF commands](cli.md#guf-land-use-fee-commands) and [GUF Framework](../theory/guf_framework.md).

---

## Running Tests

```bash
python3 -m pytest tests/ -q          # full suite (1169 tests)
python3 -m mypy hours_eoh/           # type check
```
