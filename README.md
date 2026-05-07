# HOURS

**HOURS** is a mathematical framework for a currency system — *Entropy Obligation Hours (EOH) → Time-Equivalent Hours (TEH)* — that remains coherent, physically grounded, and fiscally solvent across the full civilizational transition from subsistence to post-scarcity.

> "An economy is the organized effort of a civilization to resist entropy — in its people, in its infrastructure, in its ecosystems, and in its knowledge."

---

## Core Idea

A single parameter, **ε (epsilon)**, tracks where a civilization sits on the transition arc:

- **ε = 0 — Subsistence.** All entropy resistance is human labor. The collective ledger sees almost nothing. TEH barely circulates.
- **ε = 0.99 — Effective post-scarcity.** All entropy resistance is automated. Prices have collapsed. Human labor is near-zero. The ledger must remain solvent.

ε is not a policy lever. It is an *observed* state of the world — the measured degree to which physical entropy obligations are fulfilled by machines rather than human bodies.

Every function in this codebase must produce physically meaningful output across the full arc from ε = 0 to ε = 0.99. A mechanism that only works at the current calibration midpoint (ε = 0.40) is incomplete.

## Four Entropy Domains

| Domain | What It Covers |
|--------|---------------|
| **Personal EOH** | Biological needs: food, shelter, healthcare, sanitation |
| **Infrastructure EOH** | Buildings, roads, power grids, water systems, communications |
| **Ecological EOH** | Soil fertility, water cycles, pollination, fisheries, climate |
| **Knowledge EOH** | Skills, institutional memory, standards, software, training |

## The EOH → TEH Pipeline

```
Physical state → total_eoh()          # entropy obligation from physics
             → human_eoh_per_domain() # ε drives the machine/human split
             → registration boundary  # EOH admitted to the collective ledger
             → × worker multiplier    # TEH enters circulation
```

**EOH generation is pure physics.** Functions take the actual physical state of the civilization (capital stock, ecosystem health, population structure, knowledge base) and return the entropy obligations that state implies.

**EOH fulfillment is where ε belongs.** The machine/human split, registration curves, and fiscal mechanisms are genuinely ε-driven.

## Installation

```bash
pip install hours-eoh
```

From source:

```bash
git clone https://github.com/Hours-Source/HOURS
cd HOURS
pip install -e ".[dev]"
```

Requires Python ≥ 3.10.

## Quick Start

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

# Full EOH → TEH pipeline at ε = 0.40
result = eoh_to_teh_pipeline(0.40, p=p)
print(f"TEH created: {result['teh_created']:.1f}")
```

Running the epsilon sweep to verify arc coherence:

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

results = epsilon_sweep()
for row in results:
    print(f"ε={row['epsilon']:.2f}  TEH={row['teh_created']:.0f}  solvent={row['fiscally_solvent']}")
```

## Research CLI

A command-line interface for exploring the system without writing Python. No install required — run directly from the repo root.

```bash
python3 utils/eoh_cli.py <command> [options]
```

Add `--no-color` to any command to strip ANSI output for piping or logging.

### Commands

| Command | What it does |
|---------|-------------|
| `arc` | Sweep ε from 0 to 0.99 — EOH by domain, registration share, TEH created, basket price, fiscal solvency |
| `dashboard` | Color-coded system health snapshot: Conditions I–IV, EOH health, fiscal health |
| `params show` | Print all EohParams values; overridden keys are marked |
| `params set KEY VALUE` | Persist a parameter change with downstream impact preview at ε = 0 / 0.40 / 0.99 |
| `params set KEY VALUE --dry-run` | Preview the delta without persisting |
| `params diff` | Show all active overrides relative to defaults |
| `params reset` | Clear all persisted overrides |
| `scenario list` | List available scenarios |
| `scenario run NAME` | Run a named scenario and print results |
| `simulate` | Multi-period simulation; period-by-period state table |
| `sensitivity fiscal` | Sweep a fiscal parameter across values at a given ε |
| `sensitivity arc` | Cross-sectional Δ-metrics across the full ε arc |
| `sensitivity delta` | ε-delta sensitivity at a single point |
| `guf calculate` | Compute Ground Use Fee for a parcel |
| `guf trust` | Compute GUF trust inflow from a list of revenues |

Most commands support `--format table|csv|json`. CSV and JSON are useful for piping results into analysis tools.

### Examples

Sweep the arc at 10 points:

```
$ python3 utils/eoh_cli.py arc --points 10

ε      personal  infra     eco       knowledge  total_eoh  reg%   teh_created  price    floor_pp  solvent
-----  --------  --------  --------  ---------  ---------  -----  -----------  -------  --------  -------
0.000  2.212B    65.000M   555.556K  0.100      2.278B     15.1%  70.210M      120.000  1.000     Y
0.110  2.213B    77.620M   566.434K  0.152      2.291B     27.7%  133.783M     113.773  1.068     Y
...
0.990  2.220B    223.202M  712.251K  9.733      2.444B     94.2%  44.987M      21.546   5.570     Y
```

System health snapshot with color-coded conditions:

```
$ python3 utils/eoh_cli.py dashboard --epsilon 0.40

System Dashboard — ε = 0.400  [GREEN]

Structural Conditions
  I   — Ledger Identity:         OK
  II  — Multiplier Band:         OK
  III — Zero Interest:           OK
  IV  — Distributed Competency:  OK

EOH Health
  Deferred ratio:        GREEN  0.000
  Registration coverage: GREEN  0.592

Fiscal Health
  Trust solvency:        GREEN  158.207M
  PP index:              GREEN  1.390
  Levy/guarantee ratio:  GREEN  0.020
```

Preview the downstream effect of a parameter change before persisting:

```
$ python3 utils/eoh_cli.py params set suff_levy_rate 0.03 --dry-run

[DRY RUN] params set suff_levy_rate
  suff_levy_rate: 0.0125  →  0.03

  Downstream impact (TEH created / solvency):
       ε    before teh     after teh             Δ  solvent
    0.00       70.210M       70.210M           +0  Y
    0.40      494.120M      494.120M           +0  Y
    0.99       44.987M       44.987M           +0  Y
```

Run a scenario and export to CSV for analysis:

```
$ python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

Run a 20-period simulation with ε growing at 0.02 per period:

```
$ python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02
```

### Available scenarios

| Name | Description |
|------|-------------|
| `sweep` | Arc coherence check from ε = 0 to ε = 0.99 |
| `automation_failure` | Sudden machine EOH dropout — tests reserve coverage |
| `demographic_shock` | Population age-structure shift |
| `ecological_spike` | Ecosystem EOH surge |
| `maintenance_crisis` | Compounding deferred infrastructure backlog |
| `care_delay` | Lag in care EOH admission to the collective ledger |
| `recovery` | Maintenance backlog paydown arc |

### Parameter persistence

`params set` changes are written to `utils/_params_state.json` and applied to every subsequent CLI command. This lets you establish a modified baseline — e.g., a different levy rate or capital stock — and explore all commands from that position without re-specifying values each time.

```bash
python3 utils/eoh_cli.py params set capital_stock_teh 4000000000 --reason "high-capital scenario"
python3 utils/eoh_cli.py arc --points 20        # uses the modified capital stock
python3 utils/eoh_cli.py dashboard --epsilon 0.60
python3 utils/eoh_cli.py params reset            # back to defaults
```

## Package Structure

```
hours_eoh/
  data.py          Structural constants (single source of truth)
  params.py        EohParams — mutable parameter container

  core/            Pure physics + mechanics — stable API
    trajectory.py      Canonical arc and ε derivation
    eoh_generation.py  Four EOH domain functions + total_eoh()
    registration.py    Sigmoid admission curves
    eoh_fulfillment.py EOH → TEH pipeline
    fiscal.py          Levies, allocation, guarantee, trust
    simulation.py      Period simulation engine
    ...

  land/            Ground Use Fee + stewardship lease mechanics
  scenarios/       Stress tests and scenario runners (applied research)
  research/        Experimental — not stable API
```

**Layer rules:** `core/` is imported by everything but imports nothing outside itself. `scenarios/` and `land/` import from `core/` but are never imported by it. `research/` is experimental territory.

## Structural Conditions

| Condition | Description |
|-----------|-------------|
| **I — Ledger Identity** | Every TEH in circulation has a verified labor record |
| **II — Multiplier Band** | Skill-tier multipliers grounded in entropy-reduction leverage |
| **III — Zero Interest** | Balances grow only through labor, never passively |
| **IV — Distributed Competency** *(recommended)* | Minimum human workforce in essential infrastructure domains |

## Running Tests

```bash
# Full suite (974 tests)
python3 -m pytest tests/ -q

# Single test file
python3 -m pytest tests/test_eoh_phase5.py

# Single test
python3 -m pytest tests/test_eoh_phase5.py::TestConditionDashboard::test_green_at_midpoint

# Type checking
python3 -m mypy hours_eoh/
```

## Documentation

- [Mission Statement](docs/mission_statement.md) — Theoretical foundation and design principles
- [Architecture Reference](CLAUDE.md) — Module layout, design invariants, layer rules
- [Contributing](CONTRIBUTING.md) — Development guide and function requirements
- [Changelog](CHANGELOG.md) — Version history

## License

See [LICENSE](LICENSE).

## Author

AWol — [hoursframework.org](https://hoursframework.org)
