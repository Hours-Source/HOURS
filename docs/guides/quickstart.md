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
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

# The obligation on the canonical arc at ε = 0.40
eoh = total_eoh(epsilon=0.40)
print(f"Total EOH: {eoh['total']:.3e} h/yr")

# Full EOH → TEH pipeline at ε = 0.40
result = eoh_to_teh_pipeline(0.40)
print(f"TEH created: {result['teh_created']:.3e}")
print(f"Verified against labour: {result['labor_constrained']}")
```

Passing `epsilon` alone fills the physical state from `canonical_physical_state(ε)`,
the ideal-arc reference. It is a frame, not a measurement of anywhere: real
simulations pass actual tracked state, and a real collective should also pass
`available_labor_eoh` — without it the pipeline mints from the obligation
*demanded*, not the part actually served.

---

## Arc Coherence Check

Verify the system behaves correctly across the full ε arc:

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

report = epsilon_sweep(n_points=11)
print(report["status"])
for row in report["sweep"]:
    print(f"ε={row['epsilon']:.2f}  EOH={row['total_eoh']:.3e}  solvent={row['fiscal_solvent']}")
```

Every mechanism must produce meaningful output at all four arc waypoints:

| ε | Description | Expected behavior |
|---|---|---|
| 0.00 | Subsistence | Near-zero TEH, minimal registration |
| 0.40 | Calibration reference | The reference point, not a design target |
| 0.90 | High automation | Floor prices falling, care registration high |
| 0.99 | Effective post-scarcity | Floor purchasing power still rising |

---

## One Collective, End to End

```python
from hours_eoh.core.simulation import make_economy_state
from hours_eoh.scenarios.collective import collective_snapshot

state = make_economy_state(population=30_000, epsilon=0.40,
                           capital_stock_teh=6.0e7, trust_balance=1.05e9)
report = collective_snapshot(state, land_hectares=300.0,
                             available_labor_eoh=2.0e7)
print(report["verdict"])
```

The pipeline, the Ground Use Fee and the fiscal snapshot run on one stated
frame. See the [Implementation Guide](implementation_guide.md) for what each
input means and where to find it.

---

## Structural Conditions Check

```bash
python3 utils/eoh_cli.py dashboard --epsilon 0.40
```

Conditions I–IV should read OK. The overall status at the reference is YELLOW,
not green, and the dashboard names why — see [Structural
Conditions](../theory/structural_conditions.md).

---

## CLI Quick Start

The research CLI lets you explore the system without writing Python:

```bash
python3 utils/eoh_cli.py arc --points 10
```

Each row reports the obligation by domain, the registered share, TEH created,
the floor price, floor purchasing power and solvency. Personal EOH dominates the
whole arc; the floor price falls and floor purchasing power rises as ε grows.

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
python3 -m pytest tests/ -q          # full suite
python3 -m mypy hours_eoh/           # type check
```
