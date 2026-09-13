# HOURS

**HOURS** is a mathematical framework for a currency system — *Entropy Obligation Hours (EOH) → Time-Equivalent Hours (TEH)* — that remains internally coherent, auditable, and fiscally solvent across the full civilizational transition from subsistence to post-scarcity.

> "An economy is the organized effort of a civilization to resist entropy — in its people, in its infrastructure, in its ecosystems, and in its knowledge."

---

## Core Idea

A single parameter, **ε (epsilon)**, tracks where a civilization sits on the transition arc:

- **ε = 0 — Subsistence.** All entropy resistance is human labor. The collective ledger sees almost nothing. TEH barely circulates.
- **ε = 0.99 — Effective post-scarcity.** Nearly all entropy resistance is automated. Floor prices have collapsed. The human share of the obligation is small but not zero — care resists automation, so observable ε stays below 1. The ledger must remain solvent.

ε is not a policy lever. It is an *observed* state of the world — the measured degree to which physical entropy obligations are fulfilled by machines rather than human bodies.

**ε = 1 is aspirational — the target to reach, not the measure of success.** Success is a *stable, measurable corridor*: a band of ε over which every invariant holds (the sufficiency floor, contestability, solvency, and — once measured — the thermal ceiling), with positive width sustained over time. A collective stable at ε = 0.6 with a positive corridor and a met sufficiency floor is a success by this framework's standard, not a failed run at ε = 1. If a ceiling sits below full automation, that is a finding the framework is built to report, not a failure. See `hours_eoh/research/corridor.py`.

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

**EOH generation is measurement-driven.** Functions take the actual physical state of the civilization (capital stock, ecosystem health, population structure, knowledge base) and return the entropy obligations that state implies, derived from calibrated physical constants and auditable baselines.

**EOH fulfillment is where ε belongs.** The machine/human split, registration curves, and fiscal mechanisms are genuinely ε-driven.

## Installation

```bash
git clone https://github.com/Hours-Source/HOURS
cd HOURS
pip install -e ".[dev]"
```

Requires Python ≥ 3.10.

## Quick Start

```python
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

# The obligation on the canonical arc at ε = 0.40 — a reference frame, not a
# measurement of anywhere. Pass real physical state for a real collective.
eoh = total_eoh(epsilon=0.40)
print(f"Total EOH: {eoh['total']:.3e} h/yr")

# Full EOH → TEH pipeline at ε = 0.40
result = eoh_to_teh_pipeline(0.40)
print(f"TEH created: {result['teh_created']:.3e}")
# False: no labour supply was given, so this is minted from obligation DEMANDED.
print(f"Verified against labour: {result['labor_constrained']}")
```

Running the epsilon sweep to verify arc coherence:

```python
from hours_eoh.scenarios.sweep import epsilon_sweep

report = epsilon_sweep(n_points=11)
print(report["status"])
for row in report["sweep"]:
    print(f"ε={row['epsilon']:.2f}  EOH={row['total_eoh']:.3e}  solvent={row['fiscal_solvent']}")
```

For one collective end to end — pipeline, Ground Use Fee and fisc on a single
stated frame — use `scenarios.collective.collective_snapshot()`; the
[Implementation Guide](docs/guides/implementation_guide.md) walks through it.

## Research CLI

A command-line interface for exploring the system without writing Python. No install required — run directly from the repo root.

```bash
python3 utils/eoh_cli.py <command> [options]
```

`--no-color` is a global flag and goes *before* the command — `python3 utils/eoh_cli.py --no-color arc` — to strip ANSI output for piping or logging.

### Commands

| Command | What it does |
|---------|-------------|
| `arc` | Sweep ε from 0 to 0.99 — EOH by domain, registration share, TEH created, floor price, fiscal solvency |
| `arc --domain-shares` | The same sweep as SHARES of total EOH — the denominator check (personal is almost all of it at ε=0 and still the largest domain at ε=0.99) |
| `dashboard` | Color-coded system health snapshot: Conditions I–IV, EOH health, fiscal health, contestability |
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
| `multiplier` | Four-factor multiplier breakdown and arc sweep |
| `contestability` | Contestability arc table, stress sweep, audit, recalibration, formation (§8–§8.9c) |
| `coasean` | [EXPERIMENTAL] N-collective federation mechanics (§§6–7) |
| `thermal` | [EXPERIMENTAL] Planetary radiative capacity: overage, determinacy map, ceilings |
| `corridor band` | [EXPERIMENTAL] The stability corridor [ε_suff, ε_max] and which invariant binds it |
| `corridor axes` | [EXPERIMENTAL] Both contestability axes side by side — the adopted §8.9 test and the superseded bare-χ |
| `provenance check` | Coverage and the honest debt summary across every `data.py` constant |
| `provenance csv \| table \| doc` | Regenerate the machine-readable audit CSV and the generated doc tables |

Most commands support `--format table|csv|json`. CSV and JSON are useful for piping results into analysis tools.

### Examples

Sweep the arc:

```bash
python3 utils/eoh_cli.py --no-color arc --points 6
```

Each row reports the obligation by domain, the registered share, TEH created, the
`floor_price`, floor purchasing power and solvency. What to look for is the SHAPE, and it
is why no figures are pasted here — they move with every calibration decision:

- **Personal EOH dominates the whole arc**; infrastructure and knowledge grow with ε.
- **Infrastructure EOH is 0 at ε=0**, because subsistence carries no apparatus (Block III).
- **The ecological domain reads 0** unless you supply a stock — its recurring cost moved to
  the Ground Use Fee, where it scales with land held.
- **The registered share rises, the floor price falls, and floor purchasing power rises.**

The column is `floor_price`, not `price`: the computed figure is the price *below which the
collective guarantees work is always available and always paid*. Discovery happens above it.

System health snapshot with color-coded conditions:

```bash
python3 utils/eoh_cli.py --no-color dashboard --epsilon 0.40
```

It prints the four Structural Conditions, EOH and fiscal health, the adopted §8.9
contestability invariant beside the superseded χ stress reading, and the autarky comparison
(does the apparatus remove more personal obligation than it costs?).

**The reference configuration does not read all-green, and that is reported rather than
tuned away.** Two of these are known, documented defects rather than model failures:
`Personal registration` is RED because `REGISTRATION_WARN/_CRIT` are ε-invariant thresholds
applied to a share that is *low by design* at low ε; the superseded bare-χ lines are kept
visible as a stress reading after §8.9 retired that invariant for a flow/stock mismatch.
Both are described in `docs/parameter_provenance.md`.

Preview the downstream effect of a parameter change before persisting:

```bash
python3 utils/eoh_cli.py --no-color params set suff_levy_rate 0.03 --dry-run
```

The preview reports TEH created and the Trust surplus at ε = 0, 0.40 and 0.99. For the
levy rate, TEH created does not move at all — the levy is circulatory, it redistributes
TEH and mints none — while the surplus does.

Run a scenario and export to CSV for analysis:

```
$ python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

Run a 20-period simulation with ε growing at 0.02 per period:

```
$ python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02
```

### Available scenarios

**`scenario list` is the authoritative list** — generated from the registry, with each
scenario's own options, so it cannot fall behind. The families:

| Family | Representative scenarios |
|------|-------------|
| Arc coherence | `sweep` |
| Shocks | `automation_failure`, `demographic_shock`, `ecological_spike`, `labor_income_shock`, `compound_shock` |
| Maintenance & recovery | `maintenance_crisis`, `care_delay`, `recovery` |
| Long run | `canonical_arc`, `trust_stress`, `transition`, `indust_baseline`, `indust_recovery` |
| One collective, end to end | `collective` — the documented institutional entry point |
| Land / GUF | `guf_integration`, `guf_writedown`, `guf_sweep`, `guf_magnitude`, `servicing_census`, `land_tenure` |
| Measured spine | `measured_sim`, `multiplier_sensitivity`, `infra_floor`, `knowledge_base` |
| The personal obligation | `personal_floor`, `food_conservation`, `care_curve`, `component_shares` |
| Reading ε off a real economy | `labour_epsilon`, `frame` |
| Structural tests | `feasibility`, `overbuild`, `arc_stability`, `obligation_accounts`, `thermal_load` |
| The register itself | `verification_cost`, `verification_band`, `register_capture` |

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

  core/            Measurement-driven mechanics — stable API
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
# Full suite
python3 -m pytest tests/ -q

# Single test file
python3 -m pytest tests/test_conditions.py

# Single test
python3 -m pytest tests/test_conditions.py::TestDashboardSnapshot::test_green_at_all_key_epsilons

# Type checking
python3 -m mypy hours_eoh/
```

## Examples

Three standalone scripts demonstrate the core mechanics. Run from repo root with no extra dependencies:

```bash
python3 examples/arc_sweep.py            # EOH → TEH pipeline across 11 ε points
python3 examples/multiplier_breakdown.py # four-factor multiplier at {0, 0.40, 0.90, 0.99}
python3 examples/contestability_chart.py # χ(ε) under replicable vs adversarial regimes
```

`contestability_chart.py` plots the bare χ = P/K_entry axis, which §8.9 **superseded** as the
invariant; it is kept as a stress reading. The adopted three-channel test is
`contestability recal` / `research/recalibration.exit_financing()`.

Two further scripts rebuild the external climate inputs behind the thermal layer:
`examples/fetch_era5_2015_12utc.py` (fetches from the ERA5 archive over the network) and
`examples/eta_extract.py` (re-derives `reference/data/eta_land.json` from a local GRIB
archive in `rawdata/`). Neither is needed to run anything above — the reduced extracts ship
in `hours_eoh/reference/data/`.

## Documentation

Full documentation: **[wiki.hoursframework.org](https://wiki.hoursframework.org/)**
(`hours-source.github.io/HOURS` redirects here.)

- [Theory](https://wiki.hoursframework.org/theory/overview/) — Mathematical foundations, ε arc, structural conditions, design principles
- [Prior Art and Limitations](https://wiki.hoursframework.org/theory/prior_art/) — The labour-currency lineage (Owen, Ithaca, Wörgl, WIR, Technocracy), the seven recurring failure modes that killed it, and what this framework does differently on each with an honest verdict. Ends by separating **deliberate boundaries** (decisions no dataset retires) from **open fronts** (unexplored, each stated with the route that would settle it) — the same `normative` / `placeholder` discipline the provenance page applies to constants
- [Developer Reference](https://wiki.hoursframework.org/api/) — Complete API for all modules with worked examples
- [Parameter Provenance](https://wiki.hoursframework.org/parameter_provenance/) — Every `data.py` constant: default, units, provenance tag, and the evidence that would settle it. The vocabulary is closed and tested — seven tags (`physics`, `measured`, `derived`, `bounded`, `placeholder`, `normative`, `instance`) plus two sub-labels (`derived-then-FROZEN`, `convention`) — and it is designed so the page cannot flatter the model. `placeholder` means *nothing* stands behind the value and names what would settle it; `normative` constants state who decides and explicitly refuse to pretend data could; `instance` constants are ones *you* supply for your jurisdiction, so the shipped default is not evidence about yours; `bounded` values carry their measured band and which way they err. **Measurement debt is large — roughly two constants in five — and the page leads with the live figure rather than burying it.** Tables are generated from inline tags in `data.py` and gated by `tests/test_provenance.py` with no allowlist, so coverage cannot regress silently. Machine-readable: [`constant_provenance.csv`](hours_eoh/reference/data/constant_provenance.csv). Run `python3 utils/eoh_cli.py provenance check`.
- [Implementation Guide](https://wiki.hoursframework.org/guides/implementation_guide/) — How to plug your institution's real data into the model
- [Guides](https://wiki.hoursframework.org/guides/quickstart/) — Quick start, CLI reference, extending the library
- [Architecture Reference](CLAUDE.md) — Module layout, design invariants, layer rules (local)
- [Contributing](CONTRIBUTING.md) — Development guide and function requirements
- [Changelog](CHANGELOG.md) — Version history

## License

**GNU Affero General Public License v3.0** — see [LICENSE](LICENSE).

## Author

AWol — [hoursframework.org](https://hoursframework.org)
