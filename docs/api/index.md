# Module Map

The `hours_eoh` package is organized into layers with strict import rules.

![EOH → TEH Pipeline](../images/eoh_teh_pipeline.svg)

---

## Layer Architecture

The map below names each layer and the modules a reader is most likely to need.
**It is not exhaustive** — `scenarios/` and `research/` grow with every
measurement — so browse the package, or run `eoh scenario list` for every
registered scenario.

```
hours_eoh/
  data.py              All named constants — single source of truth, every one provenance-tagged
  params.py            EohParams — mutable parameter container used by the CLI

  core/                Measurement-driven mechanics — stable API
    trajectory.py          Canonical arc + ε derivation
    eoh_generation.py      Four EOH domain functions + total_eoh()
    registration.py        Sigmoid admission curves per domain
    eoh_fulfillment.py     EOH → TEH pipeline
    multipliers.py         Condition II: multiplier band and tier logic
    fiscal.py              Levies, allocation, guarantee, trust
    prices.py              Floor price dynamics tied to human labor content
    capital.py             Asset and human capital lifecycle
    eoh_dynamics.py        Time-evolution: compounding, regenerative labor
    population.py          Population structure, age distribution
    workforce.py           Workforce lifecycle, competency reserve
    conditions.py          Structural conditions I–IV enforcement
    dashboard.py           Condition monitors + health indicators
    civilization.py        Endogenous ε from capital stock
    simulation.py          Period simulation engine
    autarky.py             The autarky reference: does the apparatus pay for itself?

  land/                Ground Use Fee + stewardship lease mechanics
    guf.py                 The fee, its terms, and the §9 write-down
    collective.py          Collective land inventory: compute_collective_guf(), archetypes
    calibration.py         Rate and weight calibration

  reference/           Measured reference data — pure data, imports nothing from the package
    (time use, parcels, occupations, the capital inventory, the personal basket, …)

  scenarios/           Applied research: stress tests, measurements, reporting
    collective.py          collective_snapshot() — ONE collective end to end; the institutional entry point
    sweep.py, shocks.py, maintenance.py, recovery.py, sensitivity.py, long_run.py,
    indust_overshoot.py, guf_stress.py       — the stress-test families
    obligation_accounts.py, feasibility.py, personal_floor.py, labour_epsilon.py,
    capital_retrodiction.py, verification_cost.py, register_capture.py, frame.py, …
                           — measurement and REPORTING ONLY modules

  research/            Experimental — NOT stable API
    contestability.py, recalibration.py, formation.py, membership.py, coasean.py,
    corridor.py, exchange.py, anchor_determinacy.py, thermal*.py, desire.py, …
```

## Import Rules

| Layer | May import from | Never imports from |
|---|---|---|
| `core/` | `data.py`, `params.py`, other `core/` | `land/`, `scenarios/`, `research/`, `utils/` |
| `land/` | `core/` | `scenarios/`, `research/`, `utils/` |
| `reference/` | nothing in the package | — (any layer may import it) |
| `scenarios/` | `core/`, `land/` | `research/`, `utils/` |
| `research/` | `core/` | `scenarios/`, `land/`, `utils/` |
| `utils/` | All layers freely | Never imported by any layer |

---

## Quick Navigation

| What you want | Where to look |
|---|---|
| Run one collective on your own data | [Implementation Guide](../guides/implementation_guide.md) |
| Constants and calibration values | [Parameters & Constants](params.md) |
| What every constant rests on | [Parameter Provenance](../parameter_provenance.md) |
| EOH generation from physical state | [EOH Generation](core/eoh_generation.md) |
| EOH → TEH pipeline | [EOH Fulfillment & Registration](core/eoh_fulfillment.md) |
| Price and basket functions | [Price Dynamics](core/prices.md) |
| Levies, Trust, Guarantee | [Fiscal Mechanics](core/fiscal.md) |
| Capital write-down, birth/death | [Capital & Population](core/capital.md) |
| Structural conditions I–IV | [Conditions & Dashboard](core/conditions.md) |
| Ground Use Fee (single parcel) | [Land — GUF Module](land.md) |
| Collective land inventory & calibration | [Land — GUF Module](land.md#collective-land-inventory) |
| Scenario runners | [Scenarios](scenarios.md) |
| Simulation engine | [Simulation Engine](core/simulation.md) |
