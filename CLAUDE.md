# CLAUDE.md

## Current Task

0. One-line mission

Take the HOURS model from "high-level functions that run simulations" to "in-depth, documented, reproducible mechanics that a researcher or a foundation can read, trust, and instantiate" — and fold in the reconciliation decisions made in the attached design documents, starting with a full multiplier and a contestability layer.

1. Files to attach to this session

Design documents produced in the prior session all found in notes/ :


hours-reconciliation.md — the controlling spec. Its §§6–9 define the price-as-floor reframing, the polycentric/Coasean architecture, the contestability invariant and its math, and the prioritized open-work list. Treat this as the source of truth for what to build.
coasean-collectives.md — the conceptual basis for the multi-collective workstream (D).
historical-autopsy.md — the failure-mode taxonomy and the revised scorecard. Use it as an acceptance checklist: each change should move a named failure mode, not just add code.
HOURS_-_Time_Currency_Framework_For_Automation.docx — the working paper. Source of the full multiplier assessment function, the Comprehensive Price Identity, the fiscal mechanisms, and the module list. When the README and the paper disagree on detail, surface it rather than guessing.


Repo files to read first, before writing anything (in this order):


CLAUDE.md — architecture reference, module layout, design invariants, layer rules. Authoritative for repo conventions.
CONTRIBUTING.md — function requirements (note the ε-coherence rule).
README.md — package structure, CLI, structural conditions.
docs/ — especially theory/overview and design principles.
hours_eoh/params.py and hours_eoh/data.py — the parameter container and constants.
hours_eoh/core/ — especially eoh_fulfillment.py (the EOH→TEH pipeline and where the multiplier is applied), fiscal.py (levies, guarantee, Trust), registration.py, eoh_generation.py, trajectory.py, simulation.py.
utils/eoh_cli.py — the research CLI (commands: arc, dashboard, params, scenario, simulate, sensitivity, guf).
tests/ — the 2,608-test suite; learn its patterns before adding to it.


First action: read the above, then produce a short written map of (a) where each paper "module" currently lives in code, and (b) which modules are only high-level stubs. That gap map drives everything else.

2. Context — what was decided in the design session

The reconciliation resolved a tension between two "engines" in the framework: objectivity (measured prices, inflation impossible by definition) vs transparency + discovery (a measured floor, market discovery above it, polycentric collectives). The decision was to make transparency-plus-discovery load-bearing and demote measured-pricing to a floor. Three consequences drive this codebase work:


The computed price is the floor price, not the price. Discovery happens above it and between collectives.
The system is a federation of Coasean collectives; the number of collectives is emergent from the automation level ε, not fixed. The current single-ledger model is the ε→1 limit case.
The invariant held constant across the whole ε arc is contestability — substantive right of exit — guaranteed by a portable, commonly-held, ε-growing capital dividend. Its math is in hours-reconciliation.md §8 and is summarized in Workstream B below.


3. Standing guardrails (apply to every workstream)


Honor the layer rules. core/ stays pure and imports nothing outside itself. Experimental work (contestability, multi-collective) goes in research/ until it has a stable API and tests. scenarios/ and land/ may import core/ but never the reverse.
ε-coherence is mandatory. Every new function must return physically meaningful output across the full arc ε ∈ [0, 0.99], not just at the 0.40 reference. Add an arc test for each.
Keep the suite green and typed. All 2,608 existing tests must still pass; add tests for new code; python3 -m mypy hours_eoh/ must stay clean.
Additive, not destructive. Prefer new modules and new functions; deprecate rather than delete public API; don't break the CLI.
License. Repo is AGPL-3.0; preserve headers and license obligations.
Author sign-off for theory changes. Some items below are substantive intellectual commitments, not refactors (the price-as-floor reframing, demoting system-wide inflation-impossibility to a floor/limit property, and any objectivity→transparency language change). Implement these behind clearly-labeled PRs/issues that link the reconciliation doc, for the author (AWol) to approve. Do not silently rewrite the theory in docstrings or docs.


4. Workstreams

A. The multiplier — full breakdown (highest-priority deepening)

Why: the README models Condition II as a "Multiplier Band" check; the paper specifies a full assessment function. This is the single biggest "high-level stub → in-depth mechanic" gap, and it is the skill-differential wound from the autopsy.
Build: a dedicated module (suggest hours_eoh/core/multiplier.py, or extend wherever the multiplier is currently applied — confirm first) implementing the paper's assessment function in full:


m(c) = 1 + α₁·T(c) + α₂·D(c) + α₃·S(c) + α₄·I(c) over the four factors (training/skill-acquisition cost, demand, scarcity, impact), with epoch-adaptive weights αᵢ(ε).
Enforce the constitutional band (mean ≈ the paper's [1.8, 2.1], hard cap ≈ 6.0) as a checked invariant, not a hard-coded constant.
Implement the paper's scarcity-feedback handling (scarcity is endogenous → use the lagged/decayed measure the paper specifies) and the decomposed "impact" sub-questions.
Encode the governance safeguards as parameters/hooks: sortition-based assessor selection, adversarial-review flag, inter-rater-reliability inputs, and a sunset/revalidation clock. These can be data structures and validators now; they document the mechanism even before they're fully simulated.
Reframe per §3 above: the multiplier sets the floor wage rate, not the universal price. Document this; it eases the measurement burden (the multiplier need only be fair-enough at the floor).
Acceptance: multiplier reproducible and band-compliant across the arc; a CLI/notebook breakdown that shows the four-factor contributions at chosen ε; tests at ε ∈ {0, 0.4, 0.99}; docstring states the governing equation.


B. Contestability instrumentation (legitimacy-critical, new)

Why: hours-reconciliation.md §8 makes contestability the invariant the whole arc must preserve. Nothing in the repo measures it yet.
Build: hours_eoh/research/contestability.py implementing:


P(epsilon) — portable per-capita endowment (Sufficiency floor + vested per-capita share of the commonly-held Trust). Hook into fiscal.py's Trust/guarantee.
k_entry(epsilon, regime) — sunk cost of founding a viable alternative collective, with a regime switch: increasing_returns (K_entry rises with ε) vs replicable (K_entry falls). Default to the adversarial increasing_returns case.
chi(epsilon, regime) = P / k_entry — the contestability margin; invariant requires χ ≥ 1 across the arc.
phi(epsilon) — commonized fraction of automation value; in the adversarial regime it must be able to → 1 as ε → 1.
tau(epsilon) = T/K (Trust share of total automated capital) and a check that dτ/dε ≥ 0 ⇔ g_Trust ≥ g_priv — the Piketty-inverted condition. Derive the common-fund levy schedule that satisfies it and expose it as a function of ε.
Wire in: add a CLI command contestability (arc table of ε, P, k_entry, χ, φ, τ, pass/fail) and a line in dashboard that goes RED when χ < 1. Add a scenario contestability_stress (increasing-returns regime, rising K_entry) to the scenario list.
Acceptance: a reproducible χ(ε) chart across the arc under both regimes; a derived levy schedule that holds χ ≥ 1 in the adversarial regime; tests; honest docstring noting the regime uncertainty (reconciliation §8.5).


C. Price-as-floor refactor (theory-flagged — open PR for sign-off)

Why: reconciliation §3 demotes the Comprehensive Price Identity to the floor price.
Build: locate the price computation feeding the CLI arc "price" column (likely eoh_fulfillment.py/fiscal.py). Expose it explicitly as floor_price(...) and add a market_premium hook (default 0.0) so discovered premiums can layer above the floor without changing the floor's guarantee. Update docstrings to say "floor price, not the price."
Acceptance: behavior unchanged at default (premium 0); the seam is now explicit and documented; PR links reconciliation §3 and §9-item-3 and asks the author to confirm the reframing before merge.

D. Polycentric / Coasean scaffolding (research-tier, larger)

Why: reconciliation §§6–7 and coasean-collectives.md. The current single ledger is the mono limit; the general case is N collectives trading at floating rates.
Build (in research/): a Collective wrapper around the existing single-ledger pipeline; an N-collective simulation with pairwise exchange rates and reserve holdings; and the three-regime inflation metric (within-collective floor-impossibility at all ε; inter-collective relative inflation as FX in transition; system-wide impossibility as the ε→1 limit) from reconciliation §7. Let the Coasean boundary (collective size) be an emergent function of ε rather than a fixed input.
Acceptance: an N-collective scenario that reproduces, at N=1, the existing single-ledger results exactly (a regression anchor); an inter-collective inflation series that behaves per §7; clearly marked experimental status.

E. Research & foundation accessibility (the through-line goal)

Why: the explicit aim — make the modules legible and instantiable, not just runnable.
Build:


In-depth docstrings: every core/ function gains the governing equation, units, ε-behavior, and a worked numeric example. This is the "full-blown workings" the high-level stubs lack.
Parameter provenance table: for every EohParams value, document source/derivation and whether it is physics (structural) or a calibration knob. Put it in docs/ and link from the README.
Reproducible figure/notebook scripts (suggest examples/ or docs/notebooks/): the arc sweep, the multiplier four-factor breakdown (A), and the χ(ε) contestability chart (B), each runnable end-to-end from repo root.
Foundation Implementation Guide (docs/): how an institution maps its real data (capital stock, ecosystem health, population structure, knowledge base) onto the EOH inputs; which parameters to calibrate; how to run a scenario against local data; what outputs mean. Written for an analyst, not a core dev.
Acceptance: a newcomer can go from clone → understand one core mechanism in depth → run a figure → see how to plug in their own numbers, using only docs/ and examples/.


F. Objectivity → transparency language pass (theory-flagged — open PR for sign-off)

Why: reconciliation §9-item-9. Replace physical-truth claims ("the currency tells the truth," "better physics") with show-your-work / floor framing in README and docs/.
Do not apply unilaterally. Open a single PR proposing the wording changes with the reconciliation rationale, for author approval. Low effort, high return, but it is a positioning decision.

5. What NOT to do


Do not delete or rewrite the existing inflation-impossibility result; reframe it as floor-level/limit per §7 and leave the original theorem documented as the ε→1 case (behind a sign-off PR).
Do not move experimental code into core/ until it has a stable API and full tests.
Do not invent function signatures from this prompt; confirm the real ones in the code first (this prompt is written from the README, not the module internals).
Do not change calibration constants to make a chart look better; if a result is ugly, report it.


6. Definition of done (per PR)

New/changed code has: governing-equation docstrings, arc tests at ε ∈ {0, 0.4, 0.99}, green full suite, clean mypy, a CLI or notebook entry point where user-facing, and — for theory-flagged items (C, D's reframing, F) — a PR description linking the relevant reconciliation section and explicitly requesting author sign-off.

7. Suggested sequencing


Gap map (§1 first action) — where each paper module lives, which are stubs.
A. Multiplier — biggest deepening win, self-contained.
B. Contestability — legitimacy-critical; depends on fiscal.py Trust hooks.
E. Accessibility — run alongside A and B so each new mechanic ships with its docstring, provenance entry, and figure.
C. Price-as-floor — small, but theory-flagged; open the sign-off PR early so it can be discussed in parallel.
D. Polycentric scaffolding — largest; research-tier; anchor it with the N=1 regression test.
F. Language pass — last, as a single reviewable PR.


8. The test that this prompt succeeded

A researcher who has never seen HOURS can open the repo, read one core mechanism (say the multiplier) and understand its full workings from the docstring alone, run the χ(ε) contestability chart to see whether exit stays viable across the arc, and find a guide telling them how to plug their own institution's data in — and every claim the code makes about itself is a show-your-work claim the ledger can back, not a physics-truth claim it cannot.



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

  land/                Ground Use Fee + stewardship lease mechanics
    guf.py             GUF framework (NLSA) — 14 functions
    collective.py      Collective land inventory: compute_collective_guf(), make_urban_collective(), make_rural_collective()
    calibration.py     Rate/weight calibration: guf_rate_calibration(), guf_lvi_weight_sensitivity()

  reference/           Calibrated example data — pure data, no domain imports
    practitioners.py   Practitioner/demand histories for scarcity_score() (6 occupations, 5 periods each)
    workforce.py       Workforce composition snapshots for population_weighted_mean_multiplier() (5 snapshots)
    atus_time_use.py   Measured US time use 2003–2025 (BLS ATUS); ingest via utils/atus_ingest.py
    personal_basket.py The personal obligation pinned to physical quantities; one component priced

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

**2650 tests passing, mypy clean on 71 source files** (verified 2026-08-16). Workstreams A–F merged to main, including the contestability closure (derived levy schedule, marginal χ, dashboard wiring) and Coasean Phase 3 (trust dynamics, settlement rules, desire stub).

**THE CHAIN AUDIT AND THE THREE CLOSURES** (2026-08-16, `notes/placeholder-inversion-audit.md`). Traced the constant dependency graph and closed the three items the ranked-placeholder table called "not really fieldwork". **Live placeholders 92 → 89, debt 45.8% → 44.5%.**
- **THE EDGE CLASS IS THE FINDING.** Treating every constant named in another's tag prose as a dependency gives 9 constants resting on a placeholder; splitting by WHICH FIELD named the parent gives 4, and only **2 where `data.py` actually computes the value**. A `form:` edge is a live dependency; a `resolves_by:` or `note:` edge is a lead or a comparison — the same lesson as the Tier-A/B withdrawals, now mechanised. **No constant is defined in terms of itself, directly or through a chain**; all five apparent cycles are prose cross-references.
- **`SKILL_WORKING_LIFE_YEARS` MEASURED: 40 → 37.5** (Eurostat `lfsi_dwl_a`, EU 2025, Tier B). **ITS `resolves_by` NAMED THE WRONG INSTRUMENT** — BLS Employee Tenure is median years with the CURRENT EMPLOYER (3.9 yr); binding to it would have set renewal to 0.256, **2.6× the very rate Block K-III refuted**, and wrong in mechanism: changing employer does not destroy what you know. The correct pointer was the constant's own second clause (cohort exit from the labour force), which is exactly Eurostat's construction. No current US equivalent exists (BLS ceased worklife tables; last is Smith 1986 on 1979–80 behaviour), so the jurisdiction mismatch is unavoidable and IS the Tier B reservation. Errs toward understatement of a US working life ⇒ overstatement of renewal ⇒ the conservative side.
- **Consequences:** `KNOWLEDGE_EOH_BASE` re-anchored a THIRD time, 533,620,818.74 → **522,918,893.27** (ε\* 0.3828 → **0.38689**). A 6.7% rise in the renewal rate moved the base only −2.0% — **the fixed point absorbs most of it, so the coupling is real and damped**, which a one-shot anchor could not have shown. 19 tests updated with mechanism recorded. **`SKILL_TRANSMISSION_RATE` is now the file's first and only `band_from:` claim**, verified transitively.
- **A FOURTH SHADOW CONSTANT: `TRANSMISSION_WORKING_LIFE_YEARS = 40.0` in `scenarios/knowledge_base.py`** — a duplicate carrying its own copy of the same wrong pointer, living OUTSIDE `data.py` and therefore invisible to the gate. It broke a structural identity by exactly 40/37.5 when the source moved. **The identity test caught it; a pinned level would have been updated and the divergence preserved underneath.** Now bound. (`= 1500.0`, the pipeline's `skill_decay_rate = 0.10`, and `_ECOLOGICAL_SPIKE_INTENSITY` are the other three.)
- **`SKILL_DECAY_RATE` RETIRED, and the 2026-08-15 reading of the block was wrong twice** — `scenarios/knowledge_base.py` reads it too, and exiling a live credibility finding to `research/` to lower a counter is the wrong trade. The real defect was one more parameter default (`knowledge_base_from_registry(decay=…)` set the REPORTED arc under the refuted doctrine). New **`baseline_in:`** field: a retired constant may be READ as a refuted baseline, but **never be a parameter default** — checked by `ast` in `parameter_default_consumers()`, not regex, because that is the condition the exemption cannot waive. `scenario run knowledge_base` still prints `credible_shipped: False`.
- **`DEFAULT_SEGMENTS` RETIRED; `core/` now defaults to the measured registry** (`registry_segments()`, O\*NET 30.3/BLS). **The Condition II mean moved 2.100 → 1.9964 (−4.93%) and NOT ONE TEST FAILED** — the quantity the multiplier block exists to govern was pinned nowhere. Third instance of this pattern (`GUF_PSI_NORM`, `RECAL_FOUNDING_LABOR_HOURS`). The synthetic set sat exactly ON the 2.10 band ceiling because it was built to, so `in_band: True` was **unfalsifiable**; the measured mean lands inside on its own evidence. `TestMeasuredWorkforceIsTheDefault` is now the pin. **`core/` imports `reference/` for the first time** — permitted, acyclic, and it supersedes a `scenarios/measured.py` paragraph asserting the opposite as deliberate design.
- **OPEN, now the highest-value provenance item: derive `form:` edges from the expressions.** `band_from:` is opt-in, which is the wrong shape for a circularity check — every failure found here was one nobody thought to declare. The right-hand side of each `data.py` assignment is already an exact, un-stale-able dependency statement readable with `ast`; both live cases fall straight out. `band_from` then narrows to bound-by-TEST cases only. Should also **scan beyond `data.py`**: "236/236 tagged" means 236 constants *in `data.py`*, and shadow constants elsewhere are invisible to every count the repo publishes.
**THE BASELINE EXEMPTION IS NOW CHECKED, NOT DECLARED** (2026-08-16, `eoh provenance baseline`). `baseline_in:` originally verified only "no parameter defaults", which named the most common failure precisely but left the POSITIVE claim untested — a retired constant could sit mid-expression feeding a live return. Now **three conditions**: every operative reader named; never a parameter default anywhere (AST, unwaivable); and **every read in a reporting position under a DECLARED label** (`baseline_labels:`) — shape is a dict value under a literal key, an f-string, or a label-carrying tuple, with arithmetic transparent and function calls refused as an unfollowable handoff.
- **THE SECOND HALF EXISTS BECAUSE THE FIRST FAILED ITS OWN BITE TEST.** Shape alone accepts ANY dict value, and nearly every function here returns a dict — a retired constant multiplied into a live figure under the key `"total"` passed cleanly. Requiring the label to be DECLARED makes adding one a visible act in a diff rather than an emergent property of Python syntax. A declared label nothing uses is also refused: a permission nobody exercises is a permission nobody reviews.
- **WHY NOT JUST EXILE TO `research/`** (the rejected path): it would not even have achieved the retirement (`scenarios/knowledge_base.py` reads it too), it would have missed the `decay=` parameter default entirely, and it makes the gate satisfiable by RELOCATION — measuring where code lives rather than what governs output. It also costs falsifiability, which is the point: `credible_shipped: False` and `in_band: True` are only meaningful because the refuted value survives beside its replacement.
- **A FOURTH CONDITION CLOSES THE STATIC GAP: a RUNTIME FLOW TRACE** (`trace_baseline_flow`). The labelled tuple proves attribution AT THE READ, not containment downstream — a loop target bound from `("shipped", OLD)` carried the value into a live figure undetected, demonstrated by a deliberate escape before the fix. Closing it statically needs intra-procedural taint plus a model of the comparison-table idiom and would STILL leave calls opaque, which is where the arithmetic happens (`_unit_response(eps, rate)`). So the flow is RUN: a `Refuted` float subclass (arithmetic propagates, bools/strings deliberately do not) is patched into every `baseline_in:` module, each reader callable without arguments is driven, and the returned structure is walked for survivors outside the declared labels. **static = TOTAL but SHALLOW (all code, position only); runtime = DEEP but NARROW (exact flow through loops AND calls, only paths a caller drives).** Neither subsumes the other. Wired into both `eoh provenance check` and `test_no_retired_constant_leaks_into_a_live_figure`; verified by re-running the escape, which both now refuse.
- **THREE STATED LIMITS**: readers needing arguments are REPORTED as skipped, never silently passed (`exercised` is asserted alongside `leaks`, so "clean" cannot mean "ran nothing"); bools/strings carry no taint by design (`credible_shipped: False` is a verdict ABOUT the value); and the traced module must BE the scanned file, since a dotted name resolves against whatever package is loaded.
- **Key-path labelling**: a read reports under ALL enclosing dict keys, so `{"shipped": {"renewal_rate": OLD}}` needs only one declared — stopping at the innermost would push the vocabulary toward field names that say nothing about being superseded.

**SHADOW CONSTANTS — THE COVERAGE FIGURE HAS THE WRONG DENOMINATOR** (2026-08-16, `eoh provenance shadow`). "237/237 tagged (100.0%)" means 237 constants **in `data.py`**. Two classes live outside it, carry no tag or `resolves_by`, appear in no debt figure, and are read by the same domain logic. **True coverage is 237/313 = 75.7%.**
- **Class A — 76 named constants in the wrong file.** `core/registration.py` alone holds **20** (every sigmoid base/growth/rate/inflection, for all five domains) against CLAUDE.md's own claim that *"no sigmoid parameter is arbitrary — each has a calibration rationale"*; `core/multipliers.py` holds **8** (the `epoch_alpha_weights` α-coefficients, Workstream A's own assessment function); then population 6, fiscal 5, prices 5, eoh_dynamics 5, capital 4.
- **Class B — de-facto constants with no name at all**: a literal repeated as the same parameter across independent functions is a constant BY BEHAVIOUR and a literal BY DECLARATION. `epsilon=0.4` (46 sites/17 files), `population=1e6` (30/14), `ecosystem_health=0.7` (12/10), `capital_age_ratio=0.3` (10/5). **Repetition is the filter that makes this usable** — value-equality against `data.py` returns 230 candidates and almost all are coincidence (`tol=1e-6` is not `THERMAL_IOTA_FLOOR_KNOWLEDGE`).
- **FOUND IMMEDIATELY: `mean_multiplier = 2.10` in ELEVEN core functions** — the pipeline, `teh_created`, three fiscal, both price functions, the simulation engine, `condition_ii`. **That is `M_BAND_TARGET`, a `normative` charter decision, standing in as the measured rate at which all TEH is minted** — Condition II verifying a measured economy against a target it was seeded with. **The sequence is not flattering: these AGREED with `population_weighted_mean_multiplier()` until retiring `DEFAULT_SEGMENTS` created the divergence.** Fixed by moving the other path, not reverting: new **`MEAN_MULTIPLIER_REFERENCE` = 1.9964197854540455**, `measured` Tier B, bound by TEST to `registry_segments()` (data.py sits below reference/), all eleven defaults repointed. **Blast radius: ONE assertion in the whole suite** (thermal_solvency breaking intensity 44.7 → 48.2). A −4.9% change to the rate the entire currency is created at moved one number — the fourth instance after `GUF_PSI_NORM`, `RECAL_FOUNDING_LABOR_HOURS` and `DEFAULT_SEGMENTS`.
- **A RATCHET, NOT A GATE** (`test_shadow_constant_count_does_not_grow`). 76 pre-existing means an unconditional gate fails the build on honest states — the `band_from:` precedent. The count may not RISE; lowering it is a migration, not a rename, because each constant moved must then say what would settle it.
- **DOMAIN BALANCE TABLE INVERTED:** knowledge is now the LARGEST domain at ε=0.99 (**47.1%** vs personal 45.2%), crossing over on this change. Stated in `docs/parameter_provenance.md` as **not robust** — two points apart, separated by a 6.7% correction, on an anchor that has moved four times. Do not build an argument on which side leads.

**PLACEHOLDER AUDIT — 9 CONSTANTS SETTLEABLE WITH NO NEW DATA** (2026-08-15, `notes/placeholder-inversion-audit.md`). Audited all 97 placeholders for **anchored inversions**: cases where the model's own structure constrains a value from OTHER constants. The scheme names three results but only ever named two operations — measure it, decide it — while the repo's two best-grounded constants (`PERSONAL_EOH_BASE`, `AGE_WEIGHT_INFANT`) got their bands from a third: derive a constraint from structure. **THE ANTI-CIRCULARITY RULE: an inversion counts only if every input is measured/derived/convention/normative/instance — never placeholder**, or you launder a guess into a band. Tier A (4, anchored, actionable now), Tier B (5, redundant — retire as independent unknowns; 2 of them chain into a CIRCULAR dependency on `COMPETENCY_THRESHOLD` and must NOT be upgraded), Tier C (~8–10, data already ingested), Tier D (~60+, genuinely needs fieldwork). 97 → 88 possible, debt 47.0% → ≈43%.
- **TWO LIVE ERRORS FOUND.** `CONTESTABILITY_CAPITAL_YIELD_RATE` is **2.0× out** (identity `1/RECAL_CAPITAL_OUTPUT_RATIO − FORMATION_DEPRECIATION_RATE` = 0.20 vs shipped 0.10). `SKILL_DECAY_RATE` is **3.6× out** (`SKILL_TRANSMISSION_RATE + SKILL_CPD_RATE` = 0.0277 vs 0.10) — **and the repo already knew**: `scenario run knowledge_base` prints `credible_shipped: False` and has been ignored. Same failure mode as the domain-share table — the model said something true and the constant did not move.
- **BLAST RADIUS, MEASURED.** `CONTESTABILITY_CAPITAL_YIELD_RATE` 0.10 → 0.20: **zero behavioural change** (2,630 pass, 2 fail, both the provenance regeneration gate). Two of its three consumers (`min_levy_for_pi`, `levy_schedule_for_chi`) are SUPERSEDED by §8.9; the third is research-tier and untested. It is 2× wrong and its wrongness never mattered.
- **ACTED ON 2026-08-15.** `CONTESTABILITY_CAPITAL_YIELD_RATE` 0.10 -> **0.20**, retagged `derived`, bound by TEST not expression (inputs are defined below it; the `GUF_ECO_KAPPA_CARBON` precedent). The pipeline literal is bound (sign-off). **TWO OF THE FOUR TIER-A CANDIDATES DID NOT SURVIVE CONTACT**, and both failures are informative: `SKILL_DECAY_RATE` cannot be tagged `retired` because the gate scopes to core/land/scenarios and `knowledge_eoh_renewal_split()` still reads it there (the gate is right — a retired constant core/ reads is a second parameter running in parallel); and `ECOLOGICAL_BASE_RATE`'s thermal anchor **fails the anti-circularity rule transitively** — the drawdown chain applies `CDR_GROSS_REMOVAL_FACTOR`, a placeholder. **THE RULE MUST BE TRANSITIVE**: `derived` inherits authority from beneath, so a one-level check passes things that bottom out on a placeholder. Both surviving cases have that shape. Net movement after Tier B: **97 -> 94, debt 47.0% -> 45.8%**.
- **A THIRD ERROR: `GUF_PSI_NORM` was pinned at 4.0 while its own form claimed to normalize Ψ's peak to 1.0 — the actual peak was 1.061.** Derived from a, b and the floor it is 3.765274, and the GUF fee curve falls a near-uniform **-5.7%** across the productive arc. **NO TEST MOVED** — the peak of the fee curve was entirely unpinned; `TestPsiNormalization` is now that pin, and `epsilon_scaling`'s docstring ("Ψ(0.40) ≈ 1.04") was stale. `LABOR_INCOME_MIN_TEH` retagged `placeholder` -> `convention`, no value change: it carried `resolves_by: n/a`, a contradiction, since placeholder REQUIRES naming what would settle it while its own form says it makes "no economic claim". A division-by-zero guard is a stated frame, not debt.
- **TIER B WAS 2 OF 5, AND THE AUDIT MISCLASSIFIED TWO OF ITS OWN CANDIDATES.** `GUF_EOH_ACCUMULATION_THRESHOLD` is a DEFERRAL FRACTION against `ECOLOGICAL_THRESHOLD`'s HEALTH INDEX — sharing a future source is not being the same quantity. `GUF_WRITEDOWN_AMORTIZATION_YEARS` is "reconcilable against" `ASSET_TYPES`, a comparison not an identity. `WORKFORCE_FRACTION_MIN` stays placeholder: circular, and `COMPETENCY_THRESHOLD × len(ESSENTIAL_DOMAINS)` = 1.085, which is not a workforce fraction at all.
- **THE PATTERN ACROSS BOTH TIERS: reading the pointer in full, and tracing the chain, dissolves about half the candidates. A `resolves_by` that names another constant is a LEAD, not a finding.**
- **`band_from:` shipped** — an opt-in claim that a derivation is anchored, gated TRANSITIVELY (`utils/provenance.unanchored_ancestors`, 6 tests). A one-level check passes both real cases. No constant claims one yet, which is the honest position rather than an omission: a constant genuinely derived from a placeholder states it in `form:` and omits the field, as `FORMATION_DEPRECIATION_RATE` does.
- **THE REAL DEFECT IS A HARD-CODED COPY, NOT THE CONSTANT.** `core/eoh_generation.knowledge_eoh` already migrated to `SKILL_TRANSMISSION_RATE` (0.025), but **`core/eoh_fulfillment.eoh_to_teh_pipeline` carries `skill_decay_rate: float = 0.10` as a bare literal** and passes it into `total_eoh`, overriding that default — the `= 1500.0` repricing hazard again. Two paths compute knowledge EOH **4× apart** (ε=0.99: 1.298e9 direct vs 5.193e9 pipeline). **The `arc` table is therefore internally inconsistent**: `knowledge`/`total_eoh` columns come from the direct path, `teh_created` from the pipeline. Binding the literal moves pipeline total **2.38×** and teh_created **2.16×** at ε=0.99 — a suite-wide calibration change, **SIGN-OFF REQUIRED**, not a docs fix.

**WORKSTREAMS C AND F SIGNED OFF AND PUBLISHED** (2026-08-15, author decision). The theory-flagged positions are no longer pending: **price-as-floor**, **system-wide inflation-impossibility demoted** to a within-collective floor property with an ε→1 asymptote, and the **objectivity → transparency** language pass are adopted *on the grounds that they are the more defensible case* — a weaker true claim beats a stronger false one. The original theorem is documented as the limit case, not deleted, per the §5 guardrail. Published in `docs/theory/prior_art.md`, which carries the sign-off note. **The guardrail at §3 of this file still governs everything else** — §8.8's website-language gate is a separate item and is NOT lifted by this.

**PROVENANCE COVERAGE CLOSED AND GATED** (2026-08-09, `2a7b29e`, 46 tests). The four-tag migration is finished and machine-checked: **all 228 `data.py` constants carry an inline tag block**, up from an effective 3. Before this, 101 (44%) appeared nowhere in `docs/parameter_provenance.md` — 51 of them the entire GUF block — and nine doc tables were still on the retired binary `Kind = Physics | Calibration`.
- **Tags live inline in `data.py`, immediately above each value.** Proximity is what stops regression: you cannot add a constant without touching the lines the tag lives on. Format is `# tag: X | units: Y [| tier: A | family: GLOB]` plus `form:`/`note:`/`resolves_by:` continuation lines; `# provenance-block: <name>` sections the file. `family:` covers a run of siblings so the diff stays proportionate (170 blocks, 31 globs, 228 constants).
- **Doc tables are GENERATED, prose is hand-written.** 28 `<!-- provenance:table "..." -->` regions in `docs/parameter_provenance.md` render from `data.py`; the prose around them is untouched. `hours_eoh/reference/data/constant_provenance.csv` is generated for public audit (value, units, tag, tier, form, block, resolves_by, note) — **never hand-edit either**. Regenerate: `eoh provenance doc --write` and `eoh provenance csv --write`.
- **The gate has NO allowlist** (`tests/test_provenance.py`). All 228 were tagged first so it is unconditional from day one. Fails on: untagged constant, stale/unmatched tag block, tag outside the closed vocabulary, `CHOSEN` without an epistemic pointer, missing units, misapplied tier, stale CSV, stale doc tables, block with no doc home. Each verified to bite by breaking it and reverting.
- **`tier` (A–D) is a sub-qualifier of `measured`/`CHOSEN`, not a rival scheme** — a `physics` claim has no source to grade. `convention` is a declared sub-label. The ad-hoc `Physics-adjacent` tag is retired.
- **NO calibration constant changed** — verified constant-by-constant against the prior commit: 228 compared, 0 differences. `TestPIChangesNothing`-style discipline.
- **SIX TAGS, not four — `CHOSEN` was split (author decision 2026-08-09).** One tag was covering three epistemic states: it made the set read as 83% guesswork while HIDING the real debts, and it filed charter decisions under "awaiting measurement" — a category error. Now: **`bounded`** (14; picked inside a MEASURED band — `band:` and `errs:` are REQUIRED and gated, so bounded is not a free upgrade over placeholder; `errs` opens with HIGH/LOW/NEITHER/**WITHHELD**), **`placeholder`** (106; nothing constrains it — THE actionable debt), **`normative`** (60; a decision — requires `decided_by:`, may carry `precedent:`, and is **FORBIDDEN a `resolves_by:`**, which is the point). The eight `CANONICAL_*` became `convention` (an ideal-arc reference FRAME). `tier` applies only where there is a source to grade: `measured`/`bounded`/`placeholder`.
- **THE HONEST HEADLINE — quote this, not "83% CHOSEN":** grounded 49 (21.4%), bounded 14 (6.1%), **placeholder 106 (46.3%)**, normative 60 (26.2%). **Debt = 52.4%, and the actionable figure is the 46.3% placeholders.** The 60 normative constants are NOT debt; they need argument, not data. `eoh provenance check` prints this via `debt_summary()`.
- **Only 2 of 229 constants are `physics`** (`A_EARTH_M2`, `SIGMA_SB`). `M_BAND_*`/`M_MAX`/`DEP_RATE`/`DIV_RATE`/`H_MIN`/`COMPETENCY_THRESHOLD` all claimed Physics while being constitutional commitments or desk estimates. **The pattern: "Physics" was being used to mean "we are confident", not "this is structural".**
- **Of the 14 bounded picks, 7 err LOW — and for `DEP_RATE`, `THERMAL_F_GHG` and `GOVERNANCE_IRR_*` low is the UNSAFE direction** (flatters solvency, overstates the thermal allowance, sets the assessment gate below the conventional κ bar). `SCARCITY_SUPPLY_LAG_YEARS` is WITHHELD: a single economy-wide lag cannot err in one direction when the true quantity is per-occupation across weeks-to-a-decade.

**FINDINGS FROM THE PROVENANCE PASS — each belongs to another part of the model:**
- **NLSA cites this framework's own document.** All 51 GUF constants attribute to "NLSA Technical Manual TM-0042, Seventh Edition", whose own header reads *"Based on NLSA from HOURSFramework"*. It is written in the register of an external standard. Equation numbers now appear only under `form:`, never `resolves_by:` — they establish an asserted FORM, not external evidence for a value.
- **`GUF_ECO_KAPPA_CARBON` (2.750 TEH/tonne-CO₂eq) and `CDR_LABOR_HOURS_PER_TONNE` (0.6 h/tonne) are the same physical quantity reached from two layers — a 4.6× disagreement, unreconciled.** Two more duplications: `DEP_RATE` 0.045 vs `FORMATION_DEPRECIATION_RATE` 0.05 (aggregate capital depreciation, the second derived from `CAPITAL_MACHINE_PROFILES`); `CONTESTABILITY_CAPITAL_YIELD_RATE` 0.10 vs the 0.20 implied by `1/RECAL_CAPITAL_OUTPUT_RATIO − FORMATION_DEPRECIATION_RATE`.
- **Four constants are calibrated to a target and now say so:** `GUF_USE_*` (scaled ×100 so aggregate GUF matches levy revenue at mid-arc), `DEFAULT_SEGMENTS` (means set so the weighted mean hits 2.10, the band top), `TRUST_BASE_TEH` (sized so the dividend covers the obligations it must fund), `CAPITAL_MACHINE_PROFILES` (tiers set to bracket the mid-arc ε they are meant to produce — ε emergent from a profile chosen to produce the expected ε). Same pattern as `_ECOLOGICAL_SPIKE_INTENSITY`, which the 2026-08-05 pass named but did not sweep for.
- **`LEVY_SUFFICIENCY_WARN` cannot fire on the shipped configuration** — it warns below 2% guarantee coverage and `SUFF_LEVY_RATE` delivers ≈2% at canonical defaults. `REGISTRATION_WARN/_CRIT` are ε-invariant while registration is low *by design* at low ε, so subsistence reads RED for a state the framework considers correct.
- **Four doc drifts fixed:** `KNOWLEDGE_EOH_BASE` 490,107,421 → 381,962,855.27 (stale since the ε_ref re-anchor); `CARE_SIGMOID_DEFAULTS` doc 0.30/0.55 vs code 0.05/0.45 (never matched); membership min-hours 750/1500 → **500/1,000** and per-capita personal EOH 2,213 → **1,475** (both *products* of `PERSONAL_EOH_BASE`, stale since the reprice).

**TWO CONSTANTS REVALUED** (2026-08-09, author decisions, `23cba0b`):
- **`RECAL_FOUNDING_LABOR_HOURS` 1,000 → 666.67, bound to `PERSONAL_EOH_BASE`** via new `RECAL_FOUNDING_FRACTION` = 2/3. The reprice had silently turned "two-thirds of the base" into the WHOLE base — a founder devoting every hour of their personal obligation to founding with nothing to live on. **Blast radius: the labour arm lengthens exactly 1.5×** (t_labor 1.80 → 2.70 yr at ε=0; worst 1.90 → 2.85 across the arc), the three-channel exit invariant holds at EVERY arc point, channel order unchanged, worst case still clears the 5-yr horizon with ~43% headroom. **No existing test moved, and that was the real defect** — nothing exercised the labour arm's TIMING, only `t_exit ≤ horizon`, which both 1.80 and 2.70 clear. `TestFoundingLabourArm` now anchors the mechanism.
- **`GUF_ECO_KAPPA_CARBON` 2.750 → 0.6**, adopting `CDR_LABOR_HOURS_PER_TONNE` as the better-sourced figure for the same quantity (operator staffing, n=1, vs an NLSA-template midpoint). Bound by **test** not expression — CDR is defined far below in data.py, so a reference would be forward; `TestCarbonKappaReconciliation` fails whichever side moves alone. **Left OPEN and pinned:** whether `CDR_GROSS_REMOVAL_FACTOR` (1.8, sink reversal) belongs in this path — it applies when drawing concentration DOWN, while replacing a displaced sink offsets a FLOW. Applying it would give 1.08. **Zero blast radius, for a reason worth knowing: the GUF κ constants are named defaults NOTHING consumes** — scenarios and the CLI build service dicts with literals (1.65, 0.35), the same anonymous-literal hazard as the `= 1500.0` defaults.
- **`_ECOLOGICAL_SPIKE_INTENSITY` lives in `core/eoh_generation.py:47`, not `data.py`** — so the gate cannot see a constant the retag log covers. Moving it into `data.py` brings it under the gate.
- **Residual the gate does NOT close:** free prose can still go stale. A curated test pins the derived products the doc restates in sentences — which is exactly where the reprice drift hid — but a narrative paragraph that goes stale in a way no field captures remains a human problem, and the doc says so rather than implying otherwise.
- **Constants that restate a literal instead of binding to their source, and should be bound:** `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE` (= `ESTATE_LEVY_FRACTION`), `MEMBERSHIP_VESTING_WARN_YEARS` (= 2 × `CONTESTABILITY_VESTING_YEARS`), `RECAL_EXIT_HORIZON_YEARS` (= `CONTESTABILITY_VESTING_YEARS`), `BASE_LIFETIME_EARNINGS_TEH` (career length 42 vs `SKILL_WORKING_LIFE_YEARS` 40, and a 2,080 h work-year against `H_REF` 2,000 — the repo carries two work-year conventions).

**Measurement spine merged** (`f2a242e`, 2026-08-05, 12 commits): measured inputs replacing chosen constants across the multiplier (O\*NET 30.3/BLS, 751 occupations, 94.2% of employment), infrastructure (currency-free statutory floor from a physical condition census, doctrine-invariant at spread 1.000 vs the monetized path's 10.26×), and thermal (P0 bound, Path C, corridor, capital dual-output, C5 forcing correction, overage/debt reframing, drawdown chain + solvency gate, responsibility allocation over the full 1750–2024 record, η from ERA5 for 258 collectives, derived λ, ε inversion via `capital_for_epsilon`, maintain-vs-replace). Two constants moved from recalled to derived (CO₂ forcing coefficient, λ_historical). What the branch DECLINED to claim is recorded with equal weight: λ_equilibrium is not assessable from this data; marginal-capacity η was built three ways and none is usable; carrying λ honestly widens the indeterminate band 2× and the layer now withholds the budget where the sign is undetermined.

**Audit closures** (2026-08-05, branch `fix/audit-close-now`): six gaps found by auditing the framework against its own claims, all closed with no new data.
- **Corridor contestability axis migrated.** `research/corridor.py` was still taking its ceiling from the bare χ = P/K_entry that §8.9 superseded, so the recorded "corridor CLOSED at defaults" finding was produced by a retired invariant. `contestability_ceiling()` now runs the adopted three-channel `exit_financing()` test; the old form survives as `contestability_ceiling_bare_chi()` and `contestability_axes()` reports the disagreement. At defaults the corridor is **OPEN** (nothing binds); under `--bare-chi` it still closes at ε_suff 0.517 vs ceiling 0.290, reproducing the earlier result on demand. `core/dashboard.py` gained `exit_financeable`, which governs the contestability flag when supplied and demotes χ to a YELLOW advisory (χ alone keeps pre-§8.9 behavior).
- **Thermal ε_current derived where an inventory exists.** `thermal_capital.epsilon_current_from_inventory()` + `capital_thermal_ceiling(epsilon_current=None)` default to deriving ε from the same capital that produces Φ, via `civilization_epsilon`. Global ε_max keeps a chosen ε_current — no measured world capital inventory in TEH exists — but `global_ceiling()` now returns `epsilon_max_band`/`binds_within_band` over ε_current ∈ [0.2, 0.6], so the chosen constant travels with its sensitivity. H = B/Φ_auto stays the headline.
- **Provenance four-tag migration finished** for the EOH-generation block, with a retag log. 13 constants now carry epistemic pointers where 6 previously claimed structural status.
- **Domain balance documented** (see below) with regression tests and `arc --domain-shares`.
- **Thermal obligation made reachable**: `scenarios/thermal_load.py` + `scenario run thermal_load`, `--thermal-obligation` on `arc` and `dashboard`.
- **Orphans registered**: `measured_sim`, `multiplier_sensitivity`, `infra_floor`, `thermal_load` in `scenario list`; new `corridor` CLI (`band`, `axes`).

**PERSONAL_EOH_BASE REPRICED 1,500 → 1,000** (2026-08-06, author decision; `scenarios/feasibility.py`, `scenario run feasibility`). The 1,500 was a desk estimate. Two independent routes bounded it far lower: the **supply ceiling** B ≤ (L−R)/w = 627 against the repo's own labour supply (396–1,006 across subsistence parameters), and the **accounting identity** B = (M+H−R)/w = 390–926, where M comes from a capital inventory and is B-FREE — a different instrument, so the routes share no assumption and still converge. 1,000 is the HIGH end, chosen on an asymmetric loss function: setting B too low hides a real shortfall (model reports feasible, capital under-built, deficit paid in unserved biological obligation); too high only over-builds capital. **Erring high is the mortality-minimising error.** NOTE the constant is per working-age-EQUIVALENT — the AGE_GROUPS weighting w = 1.475 makes the per-capita claim 1,475 h/person·yr, and since infant/elderly weight is CAREGIVER labour, adults supply all of it.

**What the reprice did NOT fix, and what it moved:**
- **Still over-determined at ε=0**: demand 1,551 vs supply 1,000 → ratio 1.55 (was 2.29). ε = 0 remains infeasible as a fully-served state (crossover ε ≈ 0.38, was 0.58) — now the CORRECT behaviour, reported through `deferred_personal` rather than surfacing as an unexplained defect. Only one subsistence-sweep case clears, at ratio 0.99, at a capacity above the modern full-time reference.
- **Domain balance NOT fixed**: personal share 96.7–90.8% → 95.1–86.8%. Separate defect.
- **The floor that funds exit fell with it.** The sufficiency floor ∝ PERSONAL_EOH_BASE, and for a tenure-0 member it IS their whole portable endowment — so bare χ_marginal now breaches across the WHOLE arc (0.886 at ε=0) and unseeded federation period-zero is uncovered by both arms. The ADOPTED §8.9 invariant still holds at every ε. Pinned in `TestRepriceBaseline`.
- **Self-financing channel never opens** under `formation_feedback_simulation` (was ε≈0.86): contestability is commons-financed for the entire transition. Do NOT quote 0.30 or 0.86.
- Dividend at ε=0.99: 1,873 → 1,287 (target) / 1,092 (dilution). Formation levy sunset 0.20 → 0.25. `exit_financing` self channel from ε≈0.50 (was 0.30). Null-anchor arc runs 46 yr not 47 — ε = capacity/total_EOH and the denominator shrank, so the same capacity scores higher.
- **Repricing hazard FIXED**: `total_eoh`, `personal_eoh`, `ecological_eoh*`, `knowledge` and `capital.py` hard-coded their bases as literal defaults (`= 1500.0`), so the constant did not propagate. All now bind the `data.py` constants; `BASKET_EOH_CONTENT` is bound to `PERSONAL_EOH_BASE` rather than duplicating it.

**BLOCK I — THE STANDARDS SPLIT** (2026-08-06, 2230 tests). One constant was doing three jobs. Two ORTHOGONAL axes were conflated in `PERSONAL_EOH_BASE`: **standard** (survival vs sufficiency) and **delivery** (autarky vs collective). Abatement is the map between columns and arrives in Block II. New: `PERSONAL_EOH_SURVIVAL` = 600 (S_a, autarky-referenced, HARD-bounded by ≤ (L−R)/w = 627 — a survival standard above labour supply is extinction; set independently and *checked*, not pinned), `PERSONAL_EOH_SUFFICIENCY` = 1500 (F_a, autarky-referenced, MAY exceed supply — that gap is why collectives form). `PERSONAL_EOH_BASE` = 1000 stays as the abatement-collapsed operating value (≈ 1500 × (1−⅓), mid-range against the 38–74% the identity route implies) and is retired when Block II lands. `personal_base_for()`, `personal_eoh(standard=)`, `total_eoh(personal_standard=)`. **Block I moved NO numbers** — defaulting to F_a would assert zero abatement, the very simplification Block II removes.

**CATEGORY ERROR CORRECTED**: the earlier "ε = 0 is not a feasible state" finding applied a SURVIVAL feasibility test to a SUFFICIENCY number. ε_suff by inventory standard: survival **0.00** / operating 0.31 / sufficiency 0.53. The correct statement is **subsistence can survive but cannot reach sufficiency without automation** — what the historical record shows. `research/corridor.survival_inventory()` computes the floor at the right standard; `corridor band --standard` exposes all three. The feasibility ceiling of 627 was never a bound on the personal obligation in general — it bounds the SURVIVAL standard only.

**KNOWLEDGE SPLIT, no new constant**: `knowledge_eoh_breakdown()` → civilisational (the corpus renewed whatever the capital) vs apparatus (the cost of knowing how to run the machines). Derives from the existing form — `complexity_per_unit` is already documented as automation-driven — giving `apparatus_fraction = 1 − 1/cpu`, 0% at ε=0 → 89.8% at ε=0.99. Apparatus belongs in collective OVERHEAD for the overbuild test; civilisational is a standing obligation. Scale caveat: knowledge is ~0.005% of total, so structurally right and numerically inconsequential until domain balance is fixed.

**BLOCK II — ABATEMENT + THE AUTARKY INSTRUMENT** (2026-08-06, 2271 tests). The physics the model was missing. Before it, personal EOH was FLAT across the whole arc (1,475→1,480): infrastructure changed only WHO served the obligation, never how much was owed. Physically wrong — a tap replaces hauling, sanitation cuts the disease burden that drives care hours.
- **`B(K) = F_a × (1 − a(K))`, `a(K) = a_max·K/(K + K_half)`.** `core/eoh_generation.abatement_fraction()`, `abated_personal_base()`, `max_abatement()`. a(0)=0 (autarky by definition), saturating at a_max. **ε-FREE by construction** — abatement is capital-driven so it COMPOSES with ε instead of double-counting: ε says who serves what remains, a(K) says how much remains.
- **`a_max` = 0.4483 is DERIVED, not chosen** — Σ share·abatability over `PERSONAL_EOH_COMPONENTS`, whose shares are the original desk estimate's own four terms (208/156/208/936 ÷ 1508). Only ONE new free constant: `ABATEMENT_HALF_CAPITAL_TEH` = 1000, the PACE not the ceiling, and the least-grounded value in the block. resolves_by: the identity route at two+ capital levels pins a_max and K_half together.
- **ANTI-CORRELATION PREDICTION CONFIRMED STRUCTURALLY**: residual at full abatement is **84.4% care**. Abatability and sufficiency run opposite — infrastructure removes survival-shaped work, cannot remove care (Baumol). TESTED in `TestAntiCorrelationPrediction`, not asserted in a docstring, so changing the weights falsifies it.
- **AGGREGATE OVERBUILD IS NOW REPRESENTABLE — new capability.** Pre-Block-II M and R were both linear in K at a fixed 4.08:1, so capital ALWAYS paid and no optimum existed (overbuild only via the mix — `generic_infra` 0.97). Abatement saturates while overhead grows linearly ⇒ **optimum at ~4,145 TEH/capita (net +644 h/person·yr), overbuilt beyond ~25,448 (6.1× the optimum)**.
- **`core/autarky.py`**: `autarky_reference()` (B₀ = personal at the autarky standard + ecological, NO apparatus terms), `overbuild_check()` with pays/**neutral**/overbuilt (K=0 is EQUIVALENT to autarky, not worse — strict inequality at the origin), `break_even_epsilon()`, `payback()`.
- **TWO TESTS, different questions**: obligation `B(K)+I(K) < B₀` ("all needs met effectively", the goal) and labour `(1−ε)·total < B₀` ("worth being in"). A collective can pass the labour test and FAIL the obligation test — worth being in only because automation masks an apparatus that doesn't carry its weight. Both reported.
- **BUG CAUGHT BY A TEST**: `break_even_epsilon` must derive against **B₀**, not B(K). Abatement makes them diverge; deriving against B(K) reported a break-even that was too high.
- **`payback()`** integrates over `design_life` — "overbuilt now, worth it over the life" is now decidable rather than an excuse. Both sides in TEH-hours, so payback_years = years of saved labour to repay the labour embodied in the apparatus.
- CLI: `scenario run overbuild` (incl. a K-sweep so the interior optimum is visible), autarky block on `dashboard`.

**BLOCK III — ε=0 ENDPOINT, TWO FLOORS, ACCOUNTING BASIS** (2026-08-06, 2292 tests).
- **Subsistence has no apparatus.** `canonical_physical_state` asserted 2,000 TEH/capita at ε=0 — a collective with infrastructure and no automation to justify it, contradicting ε's own definition. Path is now `2.0B × (1+slope) × ε`: **only the intercept moved**, ε=1 is still 3× base and ε=0.99 reads 5,940 vs the previous 5,960. Cost 4 tests, as measured.
- **DELIBERATE DIVERGENCE**: `effective_capital_from_epsilon` was NOT changed. `canonical_physical_state(ε)` = the arc's capital AT ε (0 at origin); `effective_capital_from_epsilon(base, ε)` scales a CALLER-SUPPLIED ε=0 baseline — zeroing it would destroy the caller's input. Same for `total_eoh(epsilon=)`'s legacy path, so `total_eoh(epsilon=0)` still shows infrastructure while CLI `arc` (canonical state) now shows 0.0. Pinned in test_trajectory.py.
- **TWO LOWER BOUNDS**: `corridor()` now takes a float (backward compat) OR a list of `Floor` and binds on the MAX. `survival` = cannot meet the obligation; `overbuild` = the apparatus costs more hours than autarky, so members should disperse **not because they would die but because the collective is not worth being in**. `overbuild_floor()`, `survival_floor()`, `binding_floor` in the report, Floors table + `--capital-stock` in `corridor band`.
- **ACCOUNTING BASIS**: `total_eoh(basis="gross"|"final")`. base = personal + ecological + civilisational knowledge; overhead = infrastructure + apparatus knowledge; gross = base + overhead (default, unchanged). Both always reported. **CONSERVATION RESULT: final basis drifts +0.35% across the arc (1,475.7 → 1,480.9) against gross's +10.0%** — population × per-person obligation, with the residual from the elderly-fraction shift and the civilisational corpus, not the apparatus.
- Bug worth remembering: putting the basis label (a `str`) into a `dict[str, float]` broke `isfinite` checks in 4 downstream tests. mypy caught the type violation.

**OPEN after Blocks I–III**: type-specific abatement (which capital abates which component — abatement is currently driven by TOTAL capital per capita); adopting abatement as the DEFAULT generation path, which retires the `PERSONAL_EOH_BASE` collapsed placeholder and will move numbers suite-wide like the reprice did; calibrating `ABATEMENT_HALF_CAPITAL_TEH` (the identity route at 2+ capital levels pins it and a_max together). The 0<ε<0.05 overbuild window on the labour test is now moot at the origin but the early arc should be re-checked against the new capital path.

**DEFERRED PERSONAL EOH NOW TRACKED** (2026-08-06): `core/eoh_fulfillment.labor_constrained_fulfillment()` + `eoh_to_teh_pipeline(available_labor_eoh=..., rationing=...)`. Ecological EOH has carried a `deferred` term from the start; personal EOH — the survival floor — carried none, so the pipeline reported a DEMAND figure as fulfillment. Now: `deferred_personal`, `deferred_total`, `labor_constrained`, `fulfillment_coverage`, and registration operating on SERVED rather than demanded EOH (labor that does not exist cannot mint TEH). Default `None` → every existing caller unchanged. Two rationing doctrines: `survival_first` (default; personal served first — a population short of labour feeds itself before maintaining bridges, so a non-zero personal deficit is a SEVERE reading) and `pro_rata`. At B=1,000 and L=1e9 the constraint binds to ε≈0.3: deferred_personal 475M h/yr at ε=0, 181M at ε=0.20, zero by ε=0.40. **Reports HOURS, not outcomes** — mortality is exogenous (`ANNUAL_DEATH_RATE`) and nothing links the deficit to it.

**BLOCK P-I — THE NORMATIVE PERSONAL FLOOR** (2026-08-08 → care added 2026-08-09, 2424 tests, mypy clean on 67 files; `notes/personal-eoh-floor.md`). Author decision: **normative floor for the obligation, frontier panel for the wedge, extraction as the reporting structure** — floor first, extraction NAMED but UNQUANTIFIED, frontier panel if/when HETUS/MTUS arrive. **REPORTING ONLY**; `TestPIChangesNothing` fails the moment that stops being true.
- **The identification problem.** `observed = obligation − deferred + extraction` — one observable, three unknowns, which is why the handoff's "observed hours are a LOWER bound" (deferred) and the extraction hypothesis's "UPPER bound" are both right and neither is usable alone. A floor from physical quantities at a stated delivery productivity is `obligation` by construction: nothing in it derives from what anyone was observed to do or paid. Same move as the infrastructure floor (doctrine spread 10.26× monetized → 1.000× physical).
- **`core.eoh_generation.personal_statutory_floor()`** — `floor = Σ quantity × hours_per_unit`, currency-free, twin of `infrastructure_statutory_floor`. **UNREACHABLE IS NOT ZERO**: a component with no delivery path is EXCLUDED, not costed at zero, and carries its reason — `unmeasured` (nobody costed it) vs `below_min_epsilon` (no path exists at this ε). The second implements the handoff's finding that **health has no ε=0 delivery path** — `Q/P(0)` is undefined, not large — so `PERSONAL_EOH_BASE` cannot be one ε-invariant constant scaled by automation. Below-threshold beats unmeasured; tested.
- **`reference/personal_basket.py`** — basket in physical units. **One component of seven is priced**: nutrition production, 767,025 kcal/yr ÷ 2,317.8 kcal per labour-hour (LSMS-ISA, 7 countries, unassisted stratum) = **330.9 h/person·yr**, with an independent cross-check 7.6% away. Everything else declares `hours_per_unit=None`. `test_only_nutrition_production_is_priced` guards the discipline: an invented productivity would enter with the same standing as the measured one and afterwards nothing could tell them apart.
- **CARE ADDED, and the two decompositions reconciled** (2026-08-09, author decision). The basket states EOH DEMAND, not cost — the framework then measures how much of that demand can be met — so care is a first-class term: a requirement of human survival, and TEH is denominated in human labour hours, so human continuation is the precondition for the ledger existing at all. It has an ε=0 delivery path (humans have always cared for each other unassisted) so it sits in the survival core, not among the step-in entitlements. Scope limit stated in the module: the basket is HUMAN-SPECIFIC; other agents would carry different components and only the structure generalises. **Coverage fell 0.30 → 0.069** — the old figure was flattered by the absence of the largest term (care is 62.1%). Shares are now the desk estimate's own four terms mirrored from `data.PERSONAL_EOH_COMPONENTS` (the layer rule forbids importing it) and held there by `test_shares_mirror_the_data_decomposition`, so `coverage` and `a_max` finally share a denominator. **The floor itself did not move** — care is unpriced, so it is excluded rather than costed at zero, which is the module's central behaviour demonstrated on its largest term.
- **`reference/atus_time_use.py` + `utils/atus_ingest.py`** — ATUS 2003–2025 (258,954 respondents) → two shipped extracts; raw 2.9 GB stays gitignored. **2020 needs `TU20FWGT`** (`TUFNWGTP` is zero for it) and is excluded by default with `comparable=False` — partial collection, ~May–Dec.
- **THE CURRENT READING**: observed 763.8 (US 2025 unpaid household+care) − floor_priced 330.9 at **coverage 0.069** = residual 432.9. `identity_report()` returns `deferred=None`, `extraction=None`, `identified=False`. **The extraction wedge is NOT identified at current basket coverage** — the residual's largest term is the repo's own incompleteness, and a number for extraction today would be a fitted residual. Raising coverage is the prerequisite; the frontier panel is the only route that identifies it without a residual.
- Floor vs constants (per capita after w=1.475): 37.4% of survival, 22.4% of operating, 15.0% of sufficiency. **Falsifies nothing yet** — the only ordering compatible with 6.9% coverage.
- **CLIMATE PROVENANCE CLOSED** (2026-08-09). The one priced number was itself climate-specific and did not say so: 331 h/person·yr is **rainfed** smallholder cultivation in seven Sub-Saharan countries, no irrigation, no frost-limited season. `LSMS_COUNTRIES`, `LSMS_AGRO_ECOLOGY`, `CLIMATE_CONDITIONING`/`CLIMATE_NOTES`, and `climate_conditioning()` state it; the CLI prints it beside the figure so the caveat cannot be separated from the number. Three findings: **the two-route convergence is NOT evidence of climate generality** (331 vs 306 is 7.6% apart but both routes use the same seven countries — the climate uncertainty sits outside that spread, unquantified); **the transfer-bias sign is WITHHELD, not unknown** (shorter seasons push hours/kcal up, deeper temperate soils push them down; the stratum adjudicates neither — same posture as the thermal layer on an undetermined budget sign); **thermal is the one component where climate is the QUANTITY** and **care is the one climate does not touch at all**, which is Block II's low care abatability reached from another direction. Climate INDEXING itself is deferred to production per author decision — climate changes what delivery costs, not what is owed.
- CLI: `scenario run personal_floor [--epsilon --convention --atus-year]`.

**FINDINGS FROM THE ATUS INGEST — belong to other parts of the model** (detail in `notes/personal-eoh-floor.md` §3):
- **C — personal-domain labour ROSE over 22 years of capital deepening.** Food prep 194.3 → 259.8 h/person15+·yr (**+34%**, trend predates COVID); grocery shopping 146.4 → 108.9 (**−26%**) — provisioning automated, preparation did not. **The atomisation explanation is dead**: shift-share on `TRNUMHOU` gives household-size composition **−1.3%**, within-cell behaviour **+105%**; every cell rose. Bears directly on Block II — `a(K)` rises in capital, the measured series went the other way. If a(K) cannot fit it, that is reported, not retuned. Ageing and restaurant-substitution controls still owed.
- **D — the conservation test: elimination at one stage, relocation at another. BUILT (`scenarios/food_conservation.py`, `scenario run food_conservation`).** The single-total reading (392 vs 320, "ambiguous") was the WRONG comparison — LSMS covers PRODUCTION ONLY, the US total covers three stages. Stage by stage: **production 320 → 5.1 h/person·yr, a 62× collapse robust to every uncounted term**; **processing 220.5 (and 215.6 of it UNPAID — households, not the ledger)** against an LSMS processing term nobody has measured; service 169.6 against ~0. **The claim holds where automation had something physical to automate and is unsupported where the work is preparation and service** — the same split the ATUS series shows independently (prep +33.7%, provisioning −25.6%). `hours_per_worker_year()` is DERIVED (1,874 h/worker·yr from ATUS × population ÷ registry employment), not a chosen 1,800; agriculture excludes SOC 45-4 (forestry is not food); `uncounted_headroom()` prices the missing sectors — 1% of employment is 9.4 h/person·yr, so closing the production gap needs ~34% of US employment uncounted. Both sides remain lower bounds and **the baskets are not held fixed**, so the TOTALS still cannot settle it — which is why the module reports stages.
- **B (knowledge-eoh-closure §6) — now measured and worse.** Supply **1,701.1 h/person·yr** vs gross obligation **1,487.8 at ε=0**; no ε solves the residual. Units trap: 1,701 is NOT comparable to the handoff's 700–1,400 survival core — the comparable figure is unpaid 763.8, at the BOTTOM of that band.
- **E — the ε_ref anchor was not a fixed point. CLOSED 2026-08-09 (author-approved).** `KNOWLEDGE_EOH_BASE` was derived at ε_ref=0.40 on a labour-residual corroboration that K-IV's own +12% mid-arc growth then consumed, moving the residual to 0.470. The defect was the SHAPE of the derivation — a one-shot anchor cannot be self-consistent when the constant it sets sits inside the quantity that checks it — so `scenarios/knowledge_base.epsilon_ref_fixed_point()` now solves anchor and base TOGETHER (damped iteration, 8 steps): **ε\* = 0.4522, base 3.81963e8 = 0.779× the K-IV value.** `labour_residual_epsilon()` returns **None**, not a clamped 0, when supply exceeds the whole obligation — Finding B is a finding, not a solver failure. `is_shipped_anchor` flags when the shipped constant stops being the fixed point, which is the self-check K-IV lacked. **What it does NOT fix:** the anchor is still US paid labour (937.3 h/person·yr) — it removes the self-inconsistency, not the US-specificity or the paid-labour convention, and the full-labour reading still has no solution at all. 14 tests moved, each updated with its mechanism recorded: personal share 94.3%→51.1% becomes **99.3%→56.2%** on the canonical arc; knowledge share at ε=0.99 0.412→0.353; final-basis drift +7.7%→+6.1% (the re-anchor shrinks it proportionally without touching its cause); registration composite 0.234→0.253; dilution-vs-purchase dividend ratio 1.089→1.050 (**the sign, which is the claim, is unchanged**); feasibility crossover 0.441→0.425. CLI: `scenario run knowledge_base [--observed-hours]`.
- **A (capital-profile scale) — DEFERRED by author decision.**

**DOMAIN BALANCE — the first open defect** (found 2026-08-05, not fixed): personal EOH is **91–97% of total EOH at every ε**; ecological is 0.71 h/person·yr and knowledge 0.01–0.97, against personal's 2,213. So ε = machine/total is ~95% a personal-domain number, and the entire measurement spine acts on domains totalling 3–9% of the denominator. Root cause is declared but not resolved: `ECOLOGICAL_BASE_RATE` is documented as a RELATIVE anchor and is summed with absolute counts. Consequence: the thermal obligation books at 1.8 h/person·yr, and `thermal_solvency`'s "38× margin" verdict passes because the obligation is negligible, not because the fisc is strong. `scenarios/thermal_load.py` reports both readings side by side and adds a second finding pointing the other way — levy coverage of the loaded ecological requirement is **0.17× at ε=0 and 0.66× at ε=0.20**, crossing 1 between 0.20 and 0.40: negligible in the ledger and still unaffordable at low automation. Either the ecological/knowledge bases are low by 2–3 orders, or `CDR_LABOR_HOURS_PER_TONNE` (0.6, Tier D) is, or both. Nothing in current data settles it. **Highest-value unclaimed measurement: BLS ATUS**, which resolves `PERSONAL_EOH_BASE` and the age weights directly and appears nowhere in the repo.

**Federation contestability closure implemented** (reconciliation §8.7 addendum, decided and built 2026-07-10): two-tier Trust — `simulate_federation(commons=True)` tracks a federation commons (levy tithe + consolidation escheats) and per-collective per-period χ; `merge_collectives()`/`split_collective()` boundary events with indivisible-reserve escheat and TEH-conservation postconditions; `portable_endowment_federated()`, `exit_value()`, `contestability_margin_federated()` in `research/contestability.py` (tenure is federation-wide); `research/membership.py` `MembershipTerms` + `contestability_audit()` (the §8.7e math/contract line); CLI `coasean simulate --dynamics --commons ...` and `contestability audit`. Honest adversarial findings at defaults (reported, not tuned): commons floor coverage is tiny at a 3% tithe; consolidation escheat drains per-collective dividends so the worst marginal χ worsens toward ε→1 while total τ holds.

**§8.8 closure mechanisms built, pending author sign-off** (2026-07-17, 1595 tests): the Phase 4 findings answered research-tier behind default-off flags — M1 universal unvested commons dividend (`portable_endowment_federated(..., commons_balance)`, Alaska PF precedent; escheat becomes a stabilizer), M2 entry underwriting (`entry_underwriting()`, `commons_seed_required()`; combined invariant `exit_financeable ⇔ χ_marginal ≥ 1 OR entry_capacity ≥ 1`; holds at every period of the canonical adversarial arc with a seed of ~0.05% of the Trust base), M3 physically-consistent levy base (`machine_output_teh(ε)=ε·total_eoh`; the static base understates ~12× at high ε). `simulate_federation(commons_dividend=True)`, audit flags `commons_dividend`/`underwriting_policy`. Proposal + sign-off items in `notes/contestability-closure-proposal.md` — **gates the website language rewrite** (do not publish "χ ≥ 1 across the arc" unqualified). Honest remainders: χ_marginal alone stays CRIT at high ε (commons-financed, not self-financed exit); levy growth steps stay infeasible even under M3; piketty_ok still fails at the canonical run's 20% levy.

**§8.9 recalibration prototype built** (2026-07-26, 1657 tests; adopted-in-principle by the author, formal doc edit pending): `research/recalibration.py` resolves the §8.8 honest remainders at root. RC4 fixed — time-to-finance-exit (`exit_financing()`, t_exit ≤ one vesting period) + accumulating §8.7b capital account (`capital_account_stock()`, Mondragon, zero-interest) replace the flow/stock χ; `trust_required_for_chi()`/`levy_schedule_for_chi()` marked SUPERSEDED (kept as documented negative results). Open-item-3 fixed — K(ε)=K₀+ν·Y(ε) (ν=Piketty β≈4) with the commons OWNING share φ(ε) (Meade social dividend): τ=φ≤1 and dτ/dε≥0 structural; piketty_ok's failure was the miscalibrated cash-Trust frame. Self-financing dropped as the test (author decision): three channels — labor (low ε, the floor feeds founders), commons underwriting (mid-arc trough ε≈0.2–0.55), dividend savings (high ε, D≈1,873 TEH/p·yr at 0.99 from measured machine output). `recalibrated_arc()`: financeable at every point, channel arcs labor→underwritten→self. New honest findings: acquisition infeasible from commons income for ε≲0.15 (initial endowment φ₀·K₀ carries it); endogenous g_priv turns negative past ε≈0.5 (the §8.2 commonization made visible). CLI `contestability recal`; §8.9 addendum in `notes/contestability-closure-proposal.md` with updated comms wording.

**§8.9b charter-formation doctrine built** (2026-07-26, 1736 tests; doctrine bundle agreed with the author): `phi_policy` on `research/recalibration.py` — `"dilution"` (default doctrine: the commons' share attaches to NEW capital at commissioning, resource-license/Georgist model; `formation_share_required()` s(ε) ≈ 0.17 early, crossing 1 at ε≈0.48; private capital follows a no-sale ratchet), `"target"` (§8.9a purchase model, regression anchor), `"escalated"` (charter escalation: adversarial regime observed + capacity < `RECAL_ESCALATION_CAPACITY_FLOOR` → s=1 and capital-estate escheat → `RECAL_ESCALATION_ESTATE_SHARE`; latches; NEVER fires at canonical defaults). Generational conversion via `estate_conversion_flow()` (0.15 = `ESTATE_LEVY_FRACTION`, D5 extended to capital). `formation_levy_rate()`: the compensated bridge ≈ 1% of labor output, sunset by ε≈0.2. Honest findings: **φ under dilution caps BELOW the target and "φ→1" survives only asymptotically** (half-life ≈69 yr even at full escheat). **THE DOCTRINE TRADE-OFF REVERSED AND NOTHING CAUGHT IT (found 2026-08-15).** §8.9b recorded the cost of no-forced-sales as a dividend "≈13% below the purchase model" with a crossover at ε≈0.45. At current constants the crossover is at **ε≈0.05** and dilution pays MORE across essentially the whole arc: **D(0.99) 2,155 vs target's 1,906 — ≈13% ABOVE**, same magnitude, inverted sign. Mechanism unchanged and it was always in the note: target BUYS its share so acquisition consumes commons income before distribution (income 2.758e9 − 8.517e8 reinvestment), while dilution's share attaches to new capital at commissioning for free (2.155e9, nothing withheld). Target ends with the larger base (φ 0.987 vs 0.771) and the smaller payout. **"The price of never forcing a sale" is no longer paid in dividend — only in the capped φ.** Why it went unnoticed: the tests pinned the *φ* ordering, which never moved, and nothing pinned the *dividend* ordering, which is what the doctrine argument turns on. Now pinned by `TestPhiActual::test_dilution_pays_MORE_than_target_despite_the_smaller_share` (asserts the SIGN; levels are calibration and will move again). Re-run `recalibrated_arc(phi_policy=...)` before citing any level. Trough narrows to ε≈0.05–0.27, self-financing from ε≈0.30; invariant holds at every arc point under all three policies; investment-disincentive feedback on K(ε) not simulated (flagged). §8.9b addendum + comms wording in the proposal note.

**§8.9c formation feedback built** (2026-07-26, 1775 tests): `research/formation.py` closes the K(ε) circularity — formation is financed or doesn't happen (linear private supply between `FORMATION_HURDLE_RATE_MIN`/`FORMATION_FULL_SUPPLY_RATE`; s* = 1−r_full/r_gross = 0.50), commons co-funds from NET income (replacement correction: δ·T_K ≈ 20–24% dividend haircut, `commons_income_statement(net_of_replacement=True)`), ε derived from realized capacity. Null anchor (s≡0) reproduces canonical 47-yr pace. Verdicts (asserted): share-first holds canonical pace with ZERO delay but dividend pays (D≈113 vs static 302 at ε≈0.4; self-financing onset ε≈0.86 not 0.30 — do NOT quote the §8.9b onset); dividend-first crawls (ε≈0.60 at 120 yr, never completes); exit invariant holds every simulated year under both priorities and the fiat counterfactual (capacity doesn't depend on the dividend). CONDITION III FINDING: s* = 0.50 zero-interest vs ≈0.10 fiat-like; fiat world must drive the dividend to zero mid-arc to hold pace — zero interest is what makes the charter affordable, quantified. §8.9b funding hole (s=1 attracts no private funding → commons pays all cap-region formation) closed and visible. CLI `contestability formation`. §8.9c addendum + amended comms wording in proposal note. Open: typed-capital integration (civilization.py), supply-curve calibration, intermediate priority policies.

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
| `scenarios/test_feasibility.py` | `scenarios/feasibility.py` | feasibility ceiling, age-weight trap, over-determination verdict, subsistence sweep, ε crossover |
| `scenarios/test_thermal_load.py` | `scenarios/thermal_load.py` | thermal_load_arc, thermal_load_verdict — obligation reachability, negligible-in-ledger flag, low-ε coverage gap |
| `test_reference_data.py` | `reference/practitioners.py`, `reference/workforce.py` | practitioner history well-formedness, scarcity_score compat, workforce snapshot compat, layer isolation |
| `test_corridor.py` | `research/corridor.py` | survival_floor_epsilon, contestability_ceiling (adopted §8.9), contestability_ceiling_bare_chi (superseded), contestability_axes, thermal_ceiling, corridor, corridor_stability |
| `test_contestability.py`, `test_recalibration.py`, `test_formation.py`, `test_membership.py` | `research/contestability.py`, `recalibration.py`, `formation.py`, `membership.py` | §8 → §8.9c: χ and its retirement, exit_financing, φ policies, formation feedback, membership terms |
| `test_thermal*.py` (7 files) | `research/thermal*.py` | P0 bound, Path C + η, λ determinacy map, overage/debt, drawdown chain, solvency gate, capital dual-output + derived ε_current |
| `test_epsilon_inverse.py` | `research/epsilon_inverse.py` | capital_for_epsilon round-trip, monotonicity, mix_spread |
| `test_infrastructure_floor.py` | `scenarios/infrastructure_floor.py` | statutory floor, doctrine invariance (floor_spread = 1.000) |
| `test_reference_multiplier.py` | `reference/onet_multipliers.py`, `scenarios/measured.py`, `multiplier_sensitivity.py` | measured registry load, repricing to ε, rank/pairwise robustness, Monte Carlo |
| `scenarios/test_food_conservation.py` | `scenarios/food_conservation.py` | stage decomposition, derived hours-per-worker, uncounted-sector headroom, per-person-15+ series trap |
| `test_personal_floor.py` | `core/eoh_generation.personal_statutory_floor`, `reference/atus_time_use.py`, `reference/personal_basket.py`, `scenarios/personal_floor.py` | currency-free floor, unreachable-vs-zero + step-in entitlements, ATUS extract (day closes to 1440, 2020 flagged), identity report leaves extraction unattributed |
| `test_provenance.py` | `utils/provenance.py`, `hours_eoh/data.py` (all constants), `docs/parameter_provenance.md`, `reference/data/constant_provenance.csv` | tag-block parser (family globs, orphans, continuations, closed vocabulary) against synthetic source; **the coverage gate** against the real `data.py` with no allowlist — every constant tagged, every CHOSEN has a pointer, every constant has units, CSV and generated doc tables current, no block without a doc home; curated derived-prose figures |
