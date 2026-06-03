# CLAUDE.md

## Commands

```bash
python3 -m pytest tests/ -q                          # full suite
python3 -m pytest tests/test_eoh_generation.py       # single file
python3 -m mypy hours_eoh/                           # type-check
python3 utils/eoh_cli.py <command>                   # research CLI (see README)
mmdc -i diagrams/<name>.mmd -o docs/images/<name>.svg -p ~/.config/mermaid/puppeteer.json   # render one
for f in diagrams/*.mmd; do mmdc -i "$f" -o "docs/images/$(basename $f .mmd).svg" -p ~/.config/mermaid/puppeteer.json --quiet; done  # render all
```

The package is importable directly from the repo root. `tests/conftest.py` adds the repo root to sys.path automatically for all tests.

---

## Architecture

### What this is

`hours_eoh` models an **Entropy Obligation Hours (EOH) → Time-Equivalent Hour (TEH)** currency system. Entropy generates demand for labor across four physical domains. EOH is the demand signal; TEH is the record of labor performed in response. The system must remain mathematically coherent and fiscally solvent across the full arc from ε=0 (subsistence) to ε=0.99 (post-scarcity).

ε (epsilon) is a **physical observable** — the fraction of EOH fulfilled by machines relative to total EOH demand. It is not a policy lever; it is a score the economy produces.

**Layer separation**: EOH generation is pure physics — functions take actual physical state (capital stock, ecosystem health, age distribution, knowledge base, monitoring capability) and return entropy obligations. ε does not appear here except as backward-compat shorthand. EOH fulfillment is where ε belongs — it drives the machine/human split, registration curves, and fiscal mechanisms. Real simulations track physical state directly; `canonical_physical_state(ε)` provides the ideal reference for arc testing.

### Module layout

```
hours_eoh/
  data.py              Structural constants — single source of truth, all named
  params.py            EohParams — mutable parameter container with change tracking

  core/                Pure physics + mechanics — stable, no applied scenarios
    trajectory.py      Canonical arc + ε derivation
    eoh_generation.py  Four EOH domain functions + total_eoh()
    registration.py    Sigmoid admission curves per domain
    eoh_fulfillment.py EOH → TEH pipeline
    multipliers.py     Condition II: multiplier band and tier logic
    fiscal.py          Levies, allocation, guarantee, trust
    prices.py          Price dynamics tied to human labor content
    capital.py         Asset and human capital lifecycle
    eoh_dynamics.py    Time-evolution: compounding, regenerative labor, investment
    population.py      Population structure, age distribution, demographic events
    workforce.py       Workforce lifecycle, domain headcount, competency reserve
    conditions.py      Structural conditions I–IV enforcement
    dashboard.py       Condition monitors + EOH/fiscal health indicators
    civilization.py    Endogenous ε from capital stock
    simulation.py      Period simulation engine

  land/                Ground Use Fee + stewardship lease mechanics
    guf.py             GUF framework (NLSA) — 14 functions
    collective.py      Collective land inventory: compute_collective_guf(), make_urban_collective(), make_rural_collective()
    calibration.py     Rate/weight calibration: guf_rate_calibration(), guf_lvi_weight_sensitivity()

  reference/           Calibrated example data — pure data, no domain imports
    practitioners.py   Practitioner/demand histories for scarcity_score() (6 occupations, 5 periods each)
    workforce.py       Workforce composition snapshots for population_weighted_mean_multiplier() (5 snapshots)

  scenarios/           Applied research: stress tests and scenario runners
    sweep.py           epsilon_sweep — arc coherence check with fiscal solvency
    shocks.py          automation_failure_shock, demographic_shock, ecological_eoh_spike, labor_income_shock, compound_shock
    maintenance.py     deferred_maintenance_crisis, care_registration_delay
    recovery.py        maintenance_recovery_schedule, minimum_fulfillment_for_recovery
    sensitivity.py     fiscal_parameter_sweep, eoh_arc_sensitivity, epsilon_delta_sensitivity
    long_run.py        canonical_arc_trajectory, trust_depletion_stress, automation_transition_trajectory
    indust_overshoot.py indust_overshoot_baseline, indust_recovery_trajectory
    guf_stress.py      guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep, automation_levy_guf_stress
    multiplier.py      m_below_band_drift, m_above_band_drift, m_band_sweep

  research/            Experimental — NOT stable API, not imported by core or scenarios
    investment.py      rank_investment_candidates, optimal_investment
    writedown.py       Redirect: eco-collapse-1 resolved via land/guf.py §9 functions

utils/                 Presentation layer — CLI and research helpers (see README)
```

**Layer rules:**
- `core/` imports only from `data.py`, `params.py`, and other `core/` modules
- `land/` imports from `core/` only
- `scenarios/` imports from `core/` and `land/` — never the reverse
- `reference/` imports nothing from the package — pure data; any layer may import from it
- `research/` re-exports from `core/`; callers are in experimental territory
- `utils/` imports freely from all layers; never imported by any of them
- New scenario code goes in `scenarios/` — do not add to `core/stress.py`

### The EOH → TEH pipeline

Physical state (tracked by simulation, or derived via `canonical_physical_state(ε)` for arc testing):
`capital_stock_teh`, `capital_age_ratio`, `ecosystem_health`, `monitoring_capability`, `age_distribution`, `knowledge_base_size`, `knowledge_complexity_per_unit`

1. `total_eoh(physical_state)` — entropy obligation from physics; ε is optional backward compat only
2. `human_eoh_per_domain(eoh_dict, ε)` — ε drives the machine/human split
3. Per-domain registration: personal uses `personal_eoh_registration_share(ε)` (demand sigmoid); other domains use `total_registration_share(ε)` (labor composite)
4. `registered_eoh(human_eoh, registration_share)` — EOH admitted to the collective ledger
5. `teh_created = registered_eoh × mean_multiplier` — TEH enters circulation
6. `compute_epsilon(machine_eoh, total_eoh)` → derived ε. Currently ε is set exogenously; the architecture supports endogenous ε when machine capacity is modeled from capital stock.

### Key design invariants

**ε range `[0.0, 0.99]`**: ε=0 is subsistence — personal EOH mostly off-ledger, TEH barely circulates. ε=0.99 is effective post-scarcity — prices collapsed, human labor near-zero. All functions must produce meaningful output across the full range.

**Physical state drives EOH generation; ε drives fulfillment**: Generation functions (`personal_eoh`, `infrastructure_eoh`, `ecological_eoh`, `knowledge_eoh`, `total_eoh`) take physical state. They do not use ε to proxy unspecified physical assumptions — that encodes hidden state and prevents modeling divergent trajectories (e.g., fast automation with low capital investment).

**Canonical trajectory vs. actual state**: `canonical_physical_state(ε)` is the ideal-arc reference. Real simulations pass actual tracked state. Divergence from canonical is the point of modeling.

**Physical grounding**: EOH measures entropy, not wages or preferences. Every EOH function must have a physical basis. No sigmoid parameter is arbitrary — each has a calibration rationale in the mission statement.

**No anonymous constants**: every numeric literal in domain logic must be a named constant in `data.py`. Canonical trajectory constants are prefixed `CANONICAL_`.

**Per-domain registration split**: personal EOH uses `personal_eoh_registration_share(ε)` (near-zero at ε=0 — off-ledger subsistence); non-personal domains use `total_registration_share(ε)`. These are different mechanisms; do not conflate them.

**Ecological co-equal with stewardship**: `ecological_allocation()` and `stewardship_allocation()` are co-equal Trust obligations. Neither is residual.

**Zero interest (Condition III)**: balances grow only through labor income minus expenditure. EOH compounding is physics (entropy), not interest — it does not create TEH.

**TEH destruction**: D2 (income-driven consumption), D3 (biology-anchored consumption), D4 (CPI delivery), D5 (estate dissolution), D6 (accumulation ceiling) destroy TEH. D1 (capital write-down) destroys capital-embodied TEH. Levies and spending are circulatory.

**EohParams**: use `p.set(key, value, reason=...)` for calibration-path changes. Use `p.temporary(**overrides)` for sweep code — restores state on exit, no history entries.

### Adding new functions

- **EOH generation**: accept physical state parameters as primary inputs; retain `epsilon: float | None = None` for backward compat (use `canonical_physical_state(ε)` to fill unspecified state when provided)
- **Fulfillment, registration, fiscal, price**: accept ε directly — these mechanisms are genuinely ε-driven
- **All functions**:
  - Produce physically meaningful output at ε=0, 0.40, 0.90, 0.99
  - Degrade gracefully as ε → 1.0 — no discontinuities, no division-by-zero
  - Do not depend on human labor volume being large
  - Use named constants from `data.py` — no anonymous numeric literals
  - Include a comment referencing the relevant mission statement section
  - Have tests at the four key ε values and monotonicity where expected
  - Be in `dashboard.py` or carry an explicit comment explaining why it is research-only
- **Placement**: applied scenarios → `scenarios/`; experimental functions → `research/`; neither is imported by `core/`

---

## Visuals and Diagrams

**Use Mermaid for all diagrams.** Source `.mmd` files stay local (`diagrams/`, gitignored). Rendered SVGs go in `docs/images/` (committed) and are referenced in markdown as `![Label](images/name.svg)`. The CLI tool `mmdc` (v11, installed globally via npm) does the rendering.

- **Flowcharts** (`flowchart TD/LR/TB`) — pipelines, relationships, layered structures
- **XY charts** (`xychart-beta`) — numeric arcs (price vs. ε, purchasing power vs. ε)
- **Source files** live in `diagrams/` (gitignored) as `.mmd` files — never committed
- **Rendered SVGs** live in `docs/images/` (committed) — what GitHub and the docs see
- Re-render a diagram: `mmdc -i diagrams/<name>.mmd -o docs/images/<name>.svg -p ~/.config/mermaid/puppeteer.json`
- Re-render all: `for f in diagrams/*.mmd; do mmdc -i "$f" -o "docs/images/$(basename $f .mmd).svg" -p ~/.config/mermaid/puppeteer.json --quiet; done`

Puppeteer config for WSL (no-sandbox): `~/.config/mermaid/puppeteer.json`

**System deps** (Ubuntu 24.04, required for mmdc): `libnss3 libnspr4 libasound2t64`

Existing diagrams: `diagrams/*.mmd` → `docs/images/*.svg`, referenced in `docs/eoh_visuals.md`.
10 diagrams: EOH→TEH pipeline, four domains, pricing arc, demand layers, scarcity signal,
TEH lifecycle, automation arc.

---

## Current status

**1283 tests passing** (2026-06-03). Phase 2 complete. No open gaps.

**eco-collapse-1 closed** (2026-05-18): ecological collapse is handled via the GUF layer (`land/guf.py` §9), not TEH destruction. Two pathways: restoration (V_s baselines reset to recovery target, revenue maintained) and abandonment (rebuilding surcharge R_b(p,ε) added, Eq. 28–29). Preventive monitoring via `eoh_accumulation_warning()` (§9.8). `research/writedown.py` re-exports these functions with rationale.

---

## Test file index

| File | Source module | What it covers |
|------|--------------|----------------|
| `test_eoh_generation.py` | `core/eoh_generation.py` | personal_eoh, infrastructure_eoh, ecological_eoh, knowledge_eoh, total_eoh, domain_labor_requirements, epsilon_delta_sensitivity, eoh_to_essential_domains |
| `test_eoh_fulfillment.py` | `core/eoh_fulfillment.py` | human_eoh_share, registered_eoh, teh_created, teh_supply, capital_writedown, human_eoh_per_domain, eoh_to_teh_pipeline |
| `test_eoh_dynamics.py` | `core/eoh_dynamics.py` | eoh_compounding, regenerative_offset, eoh_reduction_ratio, rank_investment_candidates, optimal_investment, maintenance_strategy_compare, deferred_eoh_paydown, regenerative_investment_required |
| `test_registration.py` | `core/registration.py` | care/production/stewardship/personal/knowledge registration shares, total_registration_share, validate_registration_trajectory |
| `test_multipliers.py` | `core/multipliers.py` | population_weighted_mean_multiplier, multiplier_band_check, tier_multiplier, epoch_alpha_weights, scarcity_score, validate_training_duration, detect_artificial_scarcity, tier_expiry_check, reclassification_impact |
| `test_conditions.py` | `core/conditions.py` | condition_i_check, condition_ii_check, balance_check, condition_iii_balance_growth_check, condition_iv_check, dashboard_snapshot, domain_eoh_coverage |
| `test_dashboard.py` | `core/dashboard.py` | eoh_health_indicators, fiscal_health_check, system_dashboard |
| `test_fiscal.py` | `core/fiscal.py` | levy_collection, stewardship_allocation, ecological_allocation, sufficiency_guarantee, trust_management, fiscal_snapshot, care_stipend, min_levy_for_solvency, accumulation_ceiling_commitment |
| `test_prices.py` | `core/prices.py` | teh_price, basket_price, purchasing_power, floor_purchasing_power, domain_scarcity_multiplier, full_price_monotonicity_audit, cpi_goods_destruction |
| `test_capital.py` | `core/capital.py` | make_asset, asset_condition, writedown_trigger, execute_writedown, birth_event, death_event, maturation_update, estate_dissolution, aggregate_personal_eoh_fulfilled |
| `test_population.py` | `core/population.py` | age_group_for_age, aging, population_eoh_curve, population_lifecycle_snapshot, cohort_aging_trajectory |
| `test_workforce.py` | `core/workforce.py` | competency_reserve, competency_check, minimum_hours_allocation, automation_failure_scenario, apply_death_redistribution, competency_to_knowledge_eoh_delta |
| `test_simulation.py` | `core/simulation.py` | make_economy_state, simulate_period, run_simulation; TEH lifecycle D1–D6 |
| `test_trajectory.py` | `core/trajectory.py` | canonical_age_distribution, canonical_physical_state, compute_epsilon, effective_capital_from_epsilon |
| `test_civilization_epsilon.py` | `core/civilization.py` | civilization_epsilon, machine_eoh_from_capital, CAPITAL_MACHINE_PROFILES |
| `test_params.py` | `params.py` | EohParams defaults, temporary() context manager, params-driven pipeline |
| `test_land_guf.py` | `land/guf.py` | GUF framework: all 14 functions, boundary verification, worked example, min_income_for_access |
| `land/test_collective.py` | `land/collective.py` | compute_collective_guf, parcel schema validation, archetype factories, subsidy/cap logic |
| `land/test_calibration.py` | `land/calibration.py` | guf_rate_calibration convergence and direction, guf_lvi_weight_sensitivity variants |
| `scenarios/test_sweep.py` | `scenarios/sweep.py` | epsilon_sweep |
| `scenarios/test_shocks.py` | `scenarios/shocks.py` | automation_failure_shock, demographic_shock, ecological_eoh_spike, labor_income_shock, compound_shock |
| `scenarios/test_maintenance.py` | `scenarios/maintenance.py` | deferred_maintenance_crisis, care_registration_delay |
| `scenarios/test_recovery.py` | `scenarios/recovery.py` | maintenance_recovery_schedule, minimum_fulfillment_for_recovery |
| `scenarios/test_sensitivity.py` | `scenarios/sensitivity.py` | fiscal_parameter_sweep, eoh_arc_sensitivity, epsilon_delta_sensitivity re-export |
| `scenarios/test_long_run.py` | `scenarios/long_run.py` | canonical_arc_trajectory, trust_depletion_stress, automation_transition_trajectory |
| `scenarios/test_indust_overshoot.py` | `scenarios/indust_overshoot.py` | indust_overshoot_baseline, indust_recovery_trajectory |
| `scenarios/test_guf_stress.py` | `scenarios/guf_stress.py` | guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep, automation_levy_guf_stress |
| `scenarios/test_multiplier.py` | `scenarios/multiplier.py`, `core/simulation.py` | m_below_band_drift, m_above_band_drift, m_band_sweep, mean_multiplier_schedule in run_simulation |
| `test_reference_data.py` | `reference/practitioners.py`, `reference/workforce.py` | practitioner history well-formedness, scarcity_score compat, workforce snapshot compat, layer isolation |
