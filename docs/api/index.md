# Module Map

The `hours_eoh` package is organized into four layers with strict import rules.

![EOH → TEH Pipeline](../images/eoh_teh_pipeline.svg)

---

## Layer Architecture

```
hours_eoh/
  data.py              All named constants — single source of truth
  params.py            EohParams — mutable parameter container

  core/                Measurement-driven mechanics — stable API
    trajectory.py          Canonical arc + ε derivation
    eoh_generation.py      Four EOH domain functions + total_eoh()
    registration.py        Sigmoid admission curves per domain
    eoh_fulfillment.py     EOH → TEH pipeline
    multipliers.py         Condition II: multiplier band and tier logic
    fiscal.py              Levies, allocation, guarantee, trust
    prices.py              Price dynamics tied to human labor content
    capital.py             Asset and human capital lifecycle
    eoh_dynamics.py        Time-evolution: compounding, regenerative labor
    population.py          Population structure, age distribution
    workforce.py           Workforce lifecycle, competency reserve
    conditions.py          Structural conditions I–IV enforcement
    dashboard.py           Condition monitors + health indicators
    civilization.py        Endogenous ε from capital stock
    simulation.py          Period simulation engine

  land/                Ground Use Fee + stewardship lease mechanics
    guf.py                 GUF framework (NLSA TM-0042) — 14 functions
    collective.py          Collective land-inventory: compute_collective_guf(), make_urban_collective(),
                           make_rural_collective()
    calibration.py         Rate/weight calibration: guf_rate_calibration(), guf_lvi_weight_sensitivity()

  scenarios/           Applied research: stress tests and scenario runners
    sweep.py               epsilon_sweep — arc coherence check
    shocks.py              automation_failure_shock, demographic_shock, ecological_eoh_spike,
                           labor_income_shock, compound_shock
    maintenance.py         deferred_maintenance_crisis, care_registration_delay
    recovery.py            maintenance_recovery_schedule, minimum_fulfillment_for_recovery
    sensitivity.py         fiscal_parameter_sweep, eoh_arc_sensitivity
    long_run.py            canonical_arc_trajectory, trust_depletion_stress,
                           automation_transition_trajectory
    indust_overshoot.py    indust_overshoot_baseline, indust_recovery_trajectory
    guf_stress.py          guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep,
                           automation_levy_guf_stress

  research/            Experimental — NOT stable API
    investment.py          rank_investment_candidates, optimal_investment
    writedown.py           Redirect: eco-collapse resolved via land/guf.py §9
```

## Import Rules

| Layer | May import from | Never imports from |
|---|---|---|
| `core/` | `data.py`, `params.py`, other `core/` | `land/`, `scenarios/`, `research/`, `utils/` |
| `land/` | `core/` | `scenarios/`, `research/`, `utils/` |
| `scenarios/` | `core/`, `land/` | `research/`, `utils/` |
| `research/` | `core/` (re-exports only) | all others |
| `utils/` | All layers freely | Never imported by any layer |

---

## Quick Navigation

| What you want | Where to look |
|---|---|
| Constants and calibration values | [Parameters & Constants](params.md) |
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
