# CLAUDE.md

## Local working material

Design documents, data handoffs, raw datasets and diagram sources are **not in
the repo** — `notes/`, `handoffs/`, `rawdata/` and `diagrams/` are gitignored.
**`notes/README.md` indexes all of it**: what each design document settles and
whether it is signed off, which handoff feeds which committed extract, which
ingest script derives which dataset, the diagram render workflow, and the local
environment quirks. It also holds the original commission (Workstreams A–F, all
merged) and the agent corpus pointer.

Read it when a citation below points at `notes/…`, `handoffs/…`, `rawdata/…` or
`diagrams/…` and you cannot find the file, or before opening several notes to
work out which one is relevant. Nothing there governs the code; every adopted
decision is stated in **Current status** below and pinned by a test.

## Standing guardrails

Numbered 3 and 5 because the status log cites them by number ("§3 forbids
rewriting theory in docstrings", "per the §5 guardrail"). The rest of the
commission they came from is in `notes/README.md`.

### 3. Standing guardrails (apply to every workstream)

- **Honor the layer rules.** `core/` stays pure and imports nothing outside itself. Experimental work (contestability, multi-collective) goes in `research/` until it has a stable API and tests. `scenarios/` and `land/` may import `core/` but never the reverse.
- **ε-coherence is mandatory.** Every new function must return physically meaningful output across the full arc ε ∈ [0, 0.99], not just at the 0.40 reference. Add an arc test for each.
- **Keep the suite green and typed.** The whole existing suite must still pass; add tests for new code; `python3 -m mypy hours_eoh/` must stay clean.
- **Additive, not destructive.** Prefer new modules and new functions; deprecate rather than delete public API; don't break the CLI.
- **License.** Repo is AGPL-3.0; preserve headers and license obligations.
- **Author sign-off for theory changes.** Some items are substantive intellectual commitments, not refactors (the price-as-floor reframing, demoting system-wide inflation-impossibility to a floor/limit property, and any objectivity→transparency language change). Implement these behind clearly-labeled PRs/issues that link the reconciliation doc, for the author (AWol) to approve. Do not silently rewrite the theory in docstrings or docs.

### 5. What NOT to do

- Do not delete or rewrite the existing inflation-impossibility result; reframe it as floor-level/limit per reconciliation §7 and leave the original theorem documented as the ε→1 case (behind a sign-off PR).
- Do not move experimental code into `core/` until it has a stable API and full tests.
- Do not invent function signatures from a description; confirm the real ones in the code first.
- Do not change calibration constants to make a chart look better; if a result is ugly, report it.

## Commands

```bash
python3 -m pytest tests/ -q                          # full suite
python3 -m pytest tests/test_eoh_generation.py       # single file
python3 -m mypy hours_eoh/                           # type-check
python3 utils/eoh_cli.py <command>                   # research CLI (see README)
```

Diagram rendering (`mmdc`) is local tooling — see `notes/README.md`.

The package is importable directly from the repo root. `tests/conftest.py` adds the repo root to sys.path automatically for all tests.

---


## Architecture

### What this is

`hours_eoh` models an **Entropy Obligation Hours (EOH) → Time-Equivalent Hour (TEH)** currency system. Entropy generates demand for labor across four physical domains. EOH is the demand signal; TEH is the record of labor performed in response. The system must remain mathematically coherent and fiscally solvent across the full arc from ε=0 (subsistence) to ε=0.99 (post-scarcity).

ε (epsilon) is a **physical observable** — the fraction of EOH fulfilled by machines relative to total EOH demand. It is not a policy lever; it is a score the economy produces.

**Layer separation**: EOH generation is measurement-driven — functions take actual physical state (capital stock, ecosystem health, age distribution, knowledge base, monitoring capability) and return entropy obligations. ε does not appear here except as backward-compat shorthand. EOH fulfillment is where ε belongs — it drives the machine/human split, registration curves, and fiscal mechanisms. Real simulations track physical state directly; `canonical_physical_state(ε)` provides the ideal reference for arc testing.

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
    autarky.py         Autarky reference B₀, overbuild_check(), break_even_epsilon(), payback() (Block II)

  land/                Ground Use Fee + stewardship lease mechanics
    guf.py             GUF framework (NLSA) — the fee, Ψ policies, ecosystem-service term, §9 write-down
    collective.py      Collective land inventory: compute_collective_guf(), make_urban_collective(), make_rural_collective()
    calibration.py     Rate/weight calibration: guf_rate_calibration(), guf_lvi_weight_sensitivity()

  reference/           Calibrated example data — pure data, no domain imports
    practitioners.py   Practitioner/demand histories for scarcity_score() (6 occupations, 5 periods each)
    workforce.py       Workforce composition snapshots for population_weighted_mean_multiplier() (5 snapshots)
    atus_time_use.py   Measured US time use 2003–2025 (BLS ATUS); ingest via utils/atus_ingest.py
    mtus_time_use.py   Multinational time use — self-maintenance by age, 977,809 diaries; ingest via utils/mtus_ingest.py
    care_demand.py     ATUS care demand by age: care_by_age(), elderly_per_capita(), coverage()
    parcels.py         County parcel counts (160,573,137 parcels / 3,230 counties); ingest via utils/parcel_ingest.py
    onet_multipliers.py  The measured O*NET 30.3/BLS multiplier registry and its FROZEN bounds
    onet_knowledge.py  Knowledge/training axis inverted against the same frozen bounds
    personal_basket.py The personal obligation pinned to physical quantities; one component priced.
                       QUANTITIES live in data.py as BASKET_*; this holds the MEASURED delivery
                       productivities and takes the quantities as arguments
    restoration.py     WHAT RESETTING A HECTARE COSTS: restoration as ASAE field-operation
                       sequences; 3 classes EXCLUDED not zeroed, each naming its FIELD
    servicing.py       WHAT HOLDING LAND UNDER USE COSTS: BLS employment × ERS land use for roads,
                       utilities, inspection and title — disjoint from stewardship by construction
    land_stewardship.py US land use (ERS MLU 2022), federal land-agency workforce (OPM FedScope),
                       ASAE field capacity, the EQIP practice inventory — and what each cannot price

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
    measured.py        measured_segments, measured_mean_multiplier, run_measured_simulation (O*NET/BLS registry)
    multiplier_sensitivity.py  reconstruct, sweep_factor_weights, monte_carlo_factor_weights, sensitivity_report
    infrastructure_floor.py    census_from_condition_counts, doctrine_floor_invariance (B+D currency-free floor)
    thermal_load.py    thermal_load_arc, thermal_load_verdict — the planetary obligation carried in the ledger
    feasibility.py     labor_supply_per_capita, feasibility_check, over_determination_report, feasible_epsilon
    personal_floor.py  obligation_floor, identity_report, floor_vs_constants — normative floor vs measured hours
    food_conservation.py conservation_test, uncounted_headroom — did automation eliminate food labour, or relocate it?
    land_tenure.py     allocate_by_tenure, tenure_allocation — UNOWNED LAND IS FEDERATION;
                       nothing uncollected, undeclared tenure REPORTED not folded away
    restoration_cost.py restoration_band, legacy_stock, implied_kappa, pristine_gap_obligation — the derived reset cost,
                       and the 12–69× biological-vs-engineered κ ratio; REPORTING ONLY
    guf_magnitude.py   recurring_target_by_class, target_vs_realised, scaling_basis_shares,
                       two_part_rates, subdivision_invariance, conservation_credit_check —
                       GUF's magnitude: the DERIVED target (servicing + stewardship) and the
                       two-part tariff; REPORTING ONLY, and the fee is area-only while the
                       cost has THREE scaling bases
    servicing_census.py census, shipped_vs_measured, realized_vs_measured — the SERVICING census
                       against the GUF_USE_* ×100 fit; REPORTING ONLY
    frame.py           frame_for, at_frame, frame_check, frame_report — the population/land/CAPITAL
                       pairing; REPORTING ONLY, and the 464x the undeclared default flatters eco share
    ecological_floor.py  domain_balance_report — the ecological anchor INVERTED: what intensity a given share demands
    land_stewardship.py  census_report, agency_report, field_capacity_report, frame_report, scope_comparison
                       — the anchor's resolves_by RUN: the forward question, US, 38.1% covered
    obligation_accounts.py  The three accounts — OBLIGATION / DELIVERY / STOCK — and anchor_sensitivity();
                       REPORTING ONLY; the partition closes to float equality against total_eoh()
    arc_stability.py   Can the system STAND STILL here: obligation met, delivery pays, stock stationary
    component_shares.py  The desk component shares measured against observed ATUS time use; a BOUND, REPORTING ONLY
    use_split.py       U = servicing + stewardship + policy — the ten GUF ratios decomposed; REPORTING ONLY
    knowledge_base.py  epsilon_ref_fixed_point() — anchor and base solved TOGETHER, and credible_shipped
    care_curve.py      implied_weights() — measured obligation by age vs the shipped AGE_GROUPS weights; REPORTING ONLY

  research/            Experimental — NOT stable API, not imported by core or scenarios
    investment.py      rank_investment_candidates, optimal_investment
    writedown.py       Redirect: eco-collapse-1 resolved via land/guf.py §9 functions
    contestability.py  P, k_entry, chi, phi, tau — §8; bare-χ SUPERSEDED by §8.9
    recalibration.py   exit_financing (the ADOPTED invariant), phi_actual, capital_account_stock
    formation.py       formation_feedback_simulation — the K(ε) circularity closed
    membership.py      MembershipTerms, contestability_audit
    coasean.py         N-collective federation (§§6–7)
    corridor.py        survival_floor_epsilon, contestability_ceiling, thermal_ceiling, corridor
    epsilon_inverse.py capital_for_epsilon — sweep the economy, not the score
    exchange.py        Exchange accounting: CollectiveFrame, double-entry Ledger, parity_rate, the named FX seam
    anchor_determinacy.py  Eight anchors CLASSIFIED from their own definitions — no rival is modelled; REPORTING ONLY
    thermal*.py        thermal, thermal_path_c, thermal_lambda, thermal_overage, thermal_drawdown,
                       thermal_solvency, thermal_capital — the planetary radiative layer
    desire.py          Discovery-above-the-floor stub (sign-off-gated)

utils/                 Presentation layer — CLI and research helpers (see README)
  provenance.py        data.py tag-block scanner + audit-CSV / doc-table generators
  provenance_cmd.py    `eoh provenance check | csv | table | doc`
```

**Layer rules:**
- `core/` imports only from `data.py`, `params.py`, and other `core/` modules
- `land/` imports from `core/` only
- `scenarios/` imports from `core/` and `land/` — never the reverse
- `reference/` imports nothing from the package — pure data; any layer may import from it
- `research/` re-exports from `core/`; callers are in experimental territory
- `utils/` imports freely from all layers; never imported by any of them
- New scenario code goes in `scenarios/` (the former `core/stress.py` was removed; do not recreate it)

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

**Use Mermaid for all diagrams.** Source `.mmd` files stay local (`diagrams/`,
gitignored) and are **never committed**; rendered SVGs go in `docs/images/`
(committed) and are referenced in markdown as `![Label](images/name.svg)` — that
is what GitHub and the docs see.

- **Flowcharts** (`flowchart TD/LR/TB`) — pipelines, relationships, layered structures
- **XY charts** (`xychart-beta`) — numeric arcs (price vs. ε, purchasing power vs. ε)

15 diagrams exist — EOH→TEH pipeline, four domains, pricing arcs, demand
layers, scarcity signal, TEH lifecycle, automation arc, purchasing power, and
the five GUF diagrams. They are referenced from `docs/theory/diagrams.md` and
from the theory and API pages that use them.

The `mmdc` render commands, the WSL puppeteer config and the system deps are
local tooling: see `notes/README.md`.

---

## Recurring failure modes

**Read this before building a gate, writing a test for a normalising function,
acting on a `resolves_by`, or changing a constant.** These are not model bugs —
every one of them made the framework look *better verified than it was*, which is
the most expensive class of error here, because the whole positioning is
show-your-work rather than physical truth. A check that cannot fail is worse than
no check, since it gets quoted as evidence.

They live here, and not in `record/`, because they do not belong to a subject
area — the instance counts below span every area in the repo. `gated by:` names
the test that now catches the pattern; a mode with no gate is caught only by
someone remembering it, which is what this section is for.

1. **THE UNPINNED QUANTITY** *(corpus F-004)* — "no tests failed" usually means "nothing tested
   it". Four load-bearing numbers changed with a green suite: `GUF_PSI_NORM`
   (fee curve −5.7% across the arc, 0 failures), `RECAL_FOUNDING_LABOR_HOURS`
   (labour arm 1.5× longer, 0), `DEFAULT_SEGMENTS` (Condition II mean −4.93%, 0),
   `mean_multiplier = 2.10` in eleven core functions (**the rate all TEH is
   minted at**, −4.9%, 1). *The tell:* tests pin derived results and orderings;
   nobody pins the input. *Do:* measure blast radius **before** changing a
   constant; if it is zero, add the pin in the same change and say so.
   `gated by:` nothing directly — `test_tolerances.py` covers only the inverse.

2. **THE ASSERTION ENFORCED BY THE IMPLEMENTATION** *(corpus F-006)* — normalisers (`/ total`),
   clamps (`max(FLOOR, x)`) and residuals (`1 − a − b − c`) manufacture their own
   invariant. All three tests of `epoch_alpha_weights` passed with the eight α
   constants set to absurd values. `floor_spread == 1.000` cannot fail — the
   doctrine parameter never reaches the floor. *Do:* test the SHAPE the docstring
   claims — monotonicity, where a peak sits, which term dominates at each end —
   then break a constant and watch it fail.

3. **MEASURED WHERE THE DEFECT IS INVISIBLE** *(corpus F-007, F-028)* — the ε=0.40 trap. A β mismatch
   cancelled exactly at 0.40 because κ = κ_ref there by construction, and every
   existing test ran at 0.40. `teh_per_capita` could drop `/ population` entirely
   and 57 tests passed, because every collective compared had the same
   population. *Do:* for any ratio or difference, include a case where the two
   sides DIFFER in the quantity being divided out; evaluate at 0, 0.40, 0.90,
   0.99, never at 0.40 alone.

4. **THE COPY OF A VALUE WHOSE SOURCE IS ELSEWHERE** *(corpus F-036)* — six instances and
   counting: `= 1500.0` in five generators surviving the `PERSONAL_EOH_BASE`
   reprice; `skill_decay_rate = 0.10` running the pipeline 4× the direct path;
   `TRANSMISSION_WORKING_LIFE_YEARS`; `mean_multiplier`; the US population under
   two names; `ASSET_TYPES["generic_infra"]["maint_rate"]` duplicating
   `INFRA_MAINT_RATE` 1,087 lines away. *The tell:* a bare literal that equals a
   named constant AND shares its name — value-equality alone returns 214
   candidates and is unusable. *Do:* bind by expression where the layers allow,
   by test where they do not. But binding ASSERTS the two are one quantity — if
   that is a theory claim, report it instead.

5. **THE STRANDED PARAMETER** *(corpus F-037, F-026)* — reaches `total_eoh` and stops at
   `eoh_to_teh_pipeline`, which is the path the implementation guide tells
   institutions to run. Four instances: `personal_standard` (worth 2.09× on total
   EOH), `ecological_health_response`, `knowledge_base_size`,
   `restoration_obligation`. *Do:* a new parameter is not wired until it is
   reachable from the documented entry point and a test moves an output through
   it. `gated by:` `tests/test_parameter_wiring.py`

6. **THE FRAME SEAM** *(corpus F-002, F-005, F-030)* — a quantity that must travel with the population/land
   frame and does not. Seven instances, including `CAPITAL_STOCK_DEFAULT` and
   `TRUST_BASE_TEH`, both declared "at the 1M reference population" and consumed
   by callers that moved the population without moving them. *The tell:* grep the
   `units:` field for a stated frame, not the name. *Do:* state the frame; a
   frame-invariant share is the check that it is stated.
   `gated by:` `tests/test_ecological_scale_resolution.py` (ecological chain only)

7. **THE STATUS NOTE OUTLIVING ITS DECISION** *(corpus F-009)* — nine instances. `land_stewardship`
   printed a retracted reading for eleven days; five retracted claims were still
   shipping in docstrings and runtime verdicts at the Phase 4f adoption. *Do:*
   compute ratios live rather than restating them in prose; when a decision
   lands, grep for the claim it replaces. `gated by:` `tests/test_claims_register.py`
   — **which checks that an open item is DECLARED, never that it is still OPEN.**
   That gap let a `STILL OPEN` line sit stale for a day while the file asserted
   the adoption two entries up.

8. **THE WRONG INSTRUMENT — a `resolves_by` is a LEAD, not a finding.** *(corpus F-001, F-017, F-029)*
   `SKILL_WORKING_LIFE_YEARS` pointed at BLS Employee Tenure: median years with
   the *current employer* (3.9) against working life (37.5) — wrong by 2.6× and
   wrong in mechanism. Reading pointers in full dissolved about half the
   placeholder-audit shortlist. The same rule applies **inside** the repo: the
   `function` label ("roads", "utilities") gave a 77.5/22.5 split, each
   occupation's own `basis` field gave 41.9/44.5/13.6 — **the label names the
   department, the field names the quantity.** *Do:* open the source and check it
   measures the quantity before binding anything to it.

9. **CALIBRATED TO THE TARGET IT IS CHECKED AGAINST** *(corpus F-018, F-032)* — `DEFAULT_SEGMENTS`' means
   were set so the weighted mean landed exactly on the band ceiling, making
   `in_band: True` unfalsifiable. Same class: `GUF_USE_*`, `TRUST_BASE_TEH`,
   `CAPITAL_MACHINE_PROFILES`, `ECOLOGICAL_SPIKE_INTENSITY`. *Do:* ask **both**
   questions of every threshold — can it fire, and can it NOT fire?
   `LEVY_SUFFICIENCY_WARN` cannot fire on the shipped configuration;
   `settlement_report`'s breach was unconditionally true before a single trade.

10. **THE REPORTED VALUE THAT ISN'T THE APPLIED VALUE** *(corpus F-008)* — latent until a default
    moves. `ground_use_fee` returned `psi = Ψ(ε)` while applying something else,
    and `guf_rate_calibration` multiplied by the reported value to solve for a
    coefficient the fee never uses. `human_fraction` meant the split factor and
    said it meant the human share — 5.8× understated at the documented entry
    point. *Do:* when a computation gains a mode parameter, audit every value it
    REPORTS against every value it USES; ship the raw form under a different key.

11. **THE DOUBLE APPLICATION** *(corpus F-024)* — two terms, one mechanism, composed. `U`'s
    `labor_content_scaling` and `Ψ` both encoded "labour costs collapse";
    combined, the flow leg was discounted 273× for one mechanism. **Neither
    function is wrong alone and both docstrings are honest** — the defect exists
    only in the composition, so no test of either can see it. *Do:* record per
    term whether it carries its own response to the shared driver, then ask
    whether another term already implements your stated rationale.

12. **THE GATE THAT DOESN'T BITE — verify by breaking it, always.** *(corpus F-015, F-016, F-012, F-033)* The
    reporting-position check passed a deliberate breakage: "lands under a literal
    key" accepts any dict value. Worse, **a mutation that does not execute is a
    false pass** — an edit inside `if epsilon is not None` while the test called
    with `epsilon=None` reported the test as weak when it was fine. *Do:* assert
    the mutation is present in the LOADED source before believing the result, and
    run with `PYTHONDONTWRITEBYTECODE=1` — `cp`-restoring a module does not
    reliably invalidate `__pycache__`, and "passes alone, fails in suite" is a
    bytecode question before a logic one. `git status` cannot verify restoration
    of an untracked file.

13. **VERIFYING THE NEIGHBOURHOOD IS NOT VERIFYING THE CLAIM.** *(corpus F-027)* Four times in one
    session the numbers were checked and the sentence about them was not: a false
    crossover, a "clears with 6% to spare" that held only under an unstated
    full-employment assumption, a figure half-sourced from a gitignored artifact,
    and a causal explanation asserted beside figures that *were* checked, which
    made it read as though it had been. *Do:* for every "because X", evaluate X
    and check its DIRECTION. And do not restate a derived figure in prose — that
    drift has been caught nine times; return it from the function instead.

**A checker must state its own gaps** (corpus F-013). An undocumented gap makes
the checker read as stronger than it is, which is mode 1 one level up. Static and
runtime checks are complementary, never redundant: static is TOTAL but SHALLOW
(all code, position only); runtime is DEEP but NARROW (exact flow through loops
and calls, only the paths a caller drives).

**The `corpus F-0NN` markers above are not citations for their own sake.** This
section and the agent corpus at `~/.claude/corpus/` are the same knowledge at two
altitudes: here is the tell, loaded every session; there is the full finding with
its `instance:`, its `cost:`, and above all its `detect:` — the probe to run,
written so someone who has never seen this model can run it. **Reach for the
corpus when you need to CHECK for a mode, not to recognise one.** Validate with
`python3 ~/.claude/corpus/check.py`.

Modes 4 and 5 had no finding when this mapping was made and now do (F-036,
F-037) — written because the mapping made contact with the gap, not backfilled.
Modes 1–3 and 6–13 each name findings that already existed. The corpus also
holds 20 findings with no mode here, most of them `kind: method`, which is a
different thing from a failure mode; that is correct scoping, not a gap.

---

## Current status

### Where the record lives

`CLAUDE.md` is loaded in full every session; **`record/` is not** — it is opened
on demand, the way `notes/README.md` indexes the local design material. Filed by
subject area, not by date, because almost nothing here is consulted
chronologically.

**Read `record/<area>.md` before working in that area.** Its history is where the
retracted claims, the near-misses and the rejected instruments live.

| Area | File | Migrated |
|---|---|---|
| Ecological domain, Phases 3–4f, area/frame keying, restoration, domain balance | `record/ecological.md` | **yes** |
| Ground Use Fee — Ψ, term basis, the ten ratios, parcels, servicing | `record/guf.md` | **yes** |
| Personal domain — basket, floors, Blocks I–III/P-I, ATUS/MTUS, capacity | `record/personal.md` | **yes** |
| Provenance — tags, gate, shadow constants, confidence, re-anchors | `record/provenance.md` | **yes** |
| Verification — the gates, suite audits, mutation, pin coverage | `record/verification.md` | **yes** |
| Fulfilment — automation response, capability vs observable ε, mint, accounts | `record/fulfilment.md` | **yes** |
| Contestability and the Coasean layer — §§8.7–8.9c | `record/contestability.md` | **yes** |
| Thermal — P0, Path C, λ, drawdown, solvency | `record/thermal.md` | **yes** |
| Theory awaiting the author — value anchor, anchor comparison, discovery layer | `record/theory.md` | **yes** |

**All nine areas are migrated.** `record/README.md` is the index, states the
conventions, and says how to add a tenth. A new finding goes into its area file's
history with an anchor — not into this section, which holds state and open items
only.

**The recurring failure modes stay HERE, not in `record/`** — see the section
above. They do not belong to an area: the frame seam was found in six different
subsystems, the stranded parameter in four, a status note outliving its decision
in nine places. Filing a lesson under the area where it was last found means the
session most likely to repeat it is exactly the one that does not load it.

**`tests/test_claims_register.py` reads `CLAUDE.md` PLUS every `record/*.md`.** A
claim does not stop being checked because it moved. `tests/test_record_index.py`
requires every `record/` file to be linked from `record/README.md`.

### The state

**3,977 tests passing (1 skipped), mypy clean on 90 source files** (verified
2026-09-04). Provenance **300/300**, shadow ratchet **33**, confidence ratchet
**126** of 138, wiring ratchet **12**. Workstreams A–F merged to main, including
the contestability closure and Coasean Phase 3.

**The status log was split by subject area on 2026-09-03/04** (`b2892ac`) — this
file went 304,528 → ~40,000 chars against a 150,000 limit, and its history is
now `record/`, indexed below. Two gates live outside the repo because what they
check does: `python3 ~/.claude/corpus/check.py` (the portable agent corpus, and
that every `F-0NN` cited above resolves) and
`python3 ~/.claude/corpus/check_memory.py` (session-memory pointers, commit
shas, and that nothing is filed in two stores). Neither can run in CI. See
[`record/verification.md#the-record-split`](record/verification.md#the-record-split).

Per-area state — the adopted defaults, what is true now, and which lines are
gated — is at the top of each `record/<area>.md`. It is not repeated here,
because two accounts of one quantity is the shape that let `psi` diverge from
`psi_applied`.

### Open across the repo

An index, not the items themselves. Each links to where it is declared with what
would settle it. **An item that is open, unlisted and quietly false is the state
this whole structure forbids.**

**Needs the author, not a gate** — [`record/theory.md § Open`](record/theory.md#open)
- `notes/value-anchor.md` §2 is not signed off for publication, including the
  corrected CENSUS-vs-VALUATION framing.
- The discovery layer above the floor is a 120-line stub; every purchasing-power
  claim is scoped to the floor.
- Registration capture is measured and unmodelled — the contestability arc
  addresses EXIT, this is VOICE.
- **~~The base is blind to ecosystem condition~~ — SETTLED 2026-09-02** (author
  decision, charter). Kept visible: the 0.0% is real and a reader will find it.
  See [`record/ecological.md`](record/ecological.md#live-state).

**The standing measurement debt**
- **126 of 138** placeholder/bounded constants carry no confidence figure;
  ratcheted, may not rise. **Leverage runs OPPOSITE to confidence** and that
  ordering is pinned. → [`record/provenance.md § Open`](record/provenance.md#open)
- **Two of four** personal automation floors are measured — care and nutrition.
  Shelter and health carry none, which is an ADMISSION and not a zero, so the
  observable-ε ceiling errs HIGH. → [`record/personal.md § Open`](record/personal.md#open)
- The three-curves-one-shape lead: three constants make the same claim with
  exponents spread 2.9× and floors 4×. **One measurement may settle four.**
  → [`record/provenance.md § Open`](record/provenance.md#open)
- The ten `GUF_USE_*` ratios. → [`record/guf.md § Open`](record/guf.md#open)
- `P_service` needs an external service-point count. → [`record/guf.md § Open`](record/guf.md#open)

**Held deliberately — do not build without a reason to**
- Anchor comparison Phases 1–3; Phase 0 may be sufficient, and building further
  is the surface growth the review's §15 warns about.
  → [`record/theory.md § Open`](record/theory.md#open)
- `teh_supply` is pinned, not decided — a test fails if it acquires a caller,
  which is the safe holding state.
  → [`record/verification.md § Live state`](record/verification.md#live-state)
- The compensating-mechanism audit and dynamic stability / oscillation are both
  unbuilt; nothing tests for limit cycles.
  → [`record/verification.md § Open`](record/verification.md#open)

### Method — the finding this repo keeps re-learning

**Verifying the neighbourhood is not verifying the claim.** Four separate times
in one session the numbers were checked and the sentence about them was not: a
false crossover claim in a guide, a "clears with 6% to spare" that held only
under an unstated full-employment assumption, a figure half-sourced from a
gitignored artifact, and a causal explanation asserted beside figures that *were*
checked — which made it read as though it had been too.

For every "because X", evaluate X and check its DIRECTION. This is mode 13 in
the section above, and it is recorded as F-027 in the agent corpus at
**`~/.claude/corpus/`** — 32 findings, 4 roles, portable and outside every repo,
citing this one through `anchor:` + `repo: HOURS`. Validate with
`python3 ~/.claude/corpus/check.py`. (`notes/agents/` is now a signpost only.)

## Test file index

**89 test files. The name rule covers 64 of them:** `tests/test_<module>.py`
covers `hours_eoh/**/<module>.py`, and `tests/scenarios/`, `tests/land/` mirror
the package. Those are deliberately not listed — the mapping *is* the filename,
and a list of function names restated here is a list that goes stale. (The
previous version of this table listed 50 of 88 files and read as complete.)

The 25 files the rule does not cover are all listed below, plus two that do
follow it (`test_corridor.py`, `test_personal_floor.py`) because they carry a
superseded form and a cross-layer floor respectively. Most are **gates**: they check a
property of the repo rather than a module's behaviour, which is exactly what a
name-derived index cannot express — and they are the safeguard surface, so they
are the ones worth knowing by name.

### Gates — they check the repo, not a module

| File | What it enforces |
|------|------------------|
| `test_claims_register.py` | **This file.** Every LIVE claim in CLAUDE.md the code can answer, checked against the code; a claim whose anchor text is edited fails loudly. Plus the open-item discipline: an item is struck through (closed) or declared with what would settle it. |
| `test_provenance.py` | `utils/provenance.py` + every `data.py` constant carries a tag block; closed vocabulary; `CHOSEN` has an epistemic pointer; units present; the CSV and the generated doc tables are current. No allowlist. |
| `test_confidence.py` | The confidence ratchet — the count of placeholder/bounded constants *without* a confidence figure may not rise. |
| `test_dataset_governance.py` | A dataset's stated method against the constants it governs, sha256-fingerprinted so a regenerated file breaks the build until the constants are re-checked. |
| `test_parameter_wiring.py` | A parameter that is accepted, changes nothing at any configuration tried, and that no test passes by name. |
| `test_ecological_scale_resolution.py` | Every caller entering the ecological scale chain with a population in scope states its frame. |
| `test_one_mint_path.py` | Exactly one mint call site across `core/`, `land/` and `scenarios/` — by AST, not grep. |
| `test_cli_dispatch.py` | Every registered scenario actually runs; walks the registry rather than a hand-kept list. |
| `test_reference_data.py` | `reference/` layer isolation — no domain imports; globs the directory from disk so it cannot fall behind. |
| `test_tolerances.py` | Insensitivity, not pinning: a numerics-only tolerance must **not** move a reported result. If it does, it is an undeclared parameter. |
| `test_stock_is_bounded.py` | `supply = endowment + Σcreated − Σdestroyed`, exactly, against three independent accounts; and Condition III as behaviour (the Trust draws down, it does not yield). |
| `test_doctrine_invariance.py` | The census route ignores valuation fields and is aggregation-invariant; the valuation route transmits the doctrine undamped. |

### Cross-cutting, or named differently from the module

| File | Covers |
|------|--------|
| `test_automation_response.py` | Phase 2 per-component automation — the care contradiction's fix |
| `test_capability_vs_observable.py` | The machine-capability index vs the observed machine share |
| `test_civilization_epsilon.py` | `core/civilization.py` — endogenous ε from capital state |
| `test_coasean_phase2.py`, `test_coasean_phase3.py`, `test_coasean_phase4.py` | `research/coasean.py`, phases 2–4 |
| `test_eta_land.py` | The shipped η table and its loader (`reference/data/eta_land.json`) |
| `test_grib_scan.py` | `utils/grib_scan.py` — the header-only GRIB locator |
| `test_land_guf.py` | `land/guf.py` — all functions across the arc, boundary verification, worked example |
| `test_maintain_vs_replace.py` | B3 — maintain vs replace with the embodied-energy pulse (`research/thermal_capital.py`) |
| `test_parcel_extract.py` | `reference/parcels.py` — the county parcel extract |
| `test_reference_multiplier.py` | `core/multipliers.py` geometric composite + `reference/onet_multipliers.py`, `scenarios/measured.py` |
| `test_work_year.py` | The work-year reference — `H_REF`, policy-free, with the band reported |
| `test_corridor.py` | `research/corridor.py` — including `contestability_ceiling_bare_chi`, kept as the superseded form |
| `test_personal_floor.py` | The currency-free personal floor across `core/`, `reference/` and `scenarios/` |
