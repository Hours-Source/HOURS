# Implementation Guide

**Audience**: analysts and researchers at institutions or foundations who have
real economy data and want to model their own civilization using the HOURS framework.
This is not a developer guide — see `extending.md` for that.

**Goal**: given your data, you should be able to run one function and get
outputs that mean something about your jurisdiction.

```python
from hours_eoh.core.simulation import make_economy_state
from hours_eoh.scenarios.collective import collective_snapshot

state = make_economy_state(population=..., capital_stock_teh=..., trust_balance=...)
report = collective_snapshot(state, parcels=your_parcel_inventory)
```

`collective_snapshot()` runs the EOH→TEH pipeline, the Ground Use Fee and the
fiscal snapshot on **one stated frame**, passing the three values between them
that otherwise have to be hand-carried. Run `eoh scenario run collective` to see
it on the shipped urban archetype.

**Use it in preference to calling the three by hand.** The sections below
document the pieces, because you will want to understand them and because
`collective_snapshot` is a thin assembly over exactly those calls — but running
them yourself means keeping eleven parameters in agreement across three
functions, and that is where the frame comes apart. It came apart in this
guide's own worked example, by a factor of 92.8.

---

## 1. What inputs the model needs

The EOH → TEH pipeline takes seven physical-state fields. Here is what each
represents and where to find it in real-world data:

| Field | Type | Units | Real-world data source |
|---|---|---|---|
| `population` | float | persons | Census — total resident population |
| `capital_stock_teh` | float | TEH (≈ labor-hours of value) | National accounts: gross fixed capital stock, converted at your TEH/dollar exchange rate |
| `capital_age_ratio` | float | [0, 1] | National accounts: average age of fixed assets / average design life (or use 0.5 as default if unavailable) |
| `ecosystem_health` | float | [0, 1] | Ecosystem Services Index (ESI), Biodiversity Intactness Index (BII), or local ecological monitoring; 0.7 = moderate degradation, 0.9 = near-pristine. **Since Phases 4e/4f this no longer moves the ecological DOMAIN** — see the note below. It still drives the Ground Use Fee, which is where the recurring cost now sits. |
| `monitoring_capability` | float | [0, 1] | Fraction of deferred ecological EOH your monitoring systems can detect; proxy with your ecological data coverage fraction |
| `age_distribution` | dict | fractions summing to 1.0 | Census age pyramid, grouped into the buckets in `AGE_GROUP_RANGES`; see `AGE_GROUP_FRACTIONS` |
| `knowledge_base_size` | float | relative (1.0 = ε=0 reference) | Harder to measure; use national R&D stock relative to a subsistence baseline, or leave at canonical default |
| `ecological_area_hectares` | float | hectares | **The land your collective is responsible for stewarding.** Your own cadastre, or the GUF parcel inventory (`land/collective.py`) if you have run a GUF assessment — it already carries area per parcel. Omit it and the model derives the area from your population at `LAND_HECTARES_PER_CAPITA` (a planetary average, and the wrong number for any actual collective). Pass `ecological_hectares_per_capita=` instead if you know your ratio but not your absolute area. |

> **The ecological domain is stocks-only, and is zero unless you supply one.**
> Phases 4e and 4f (adopted 2026-08-28/29) moved BOTH recurring ecological terms
> — the standing obligation of land at reference condition, and the response to
> its being degraded — to the Ground Use Fee, where they scale with land held
> rather than with the ledger. What remains in the domain is three STOCKS:
> `deferred_ecological`, `thermal_obligation` and `restoration_obligation`. None
> ships with a default, so **`eoh_to_teh_pipeline()` reports `ecological = 0.0`
> until you supply one**, and `fiscal_snapshot()` allocates nothing to it.
>
> **This does not mean the obligation is absent, and it must not be read that
> way.** `fiscal_snapshot()["ecological"]["relocated_to_guf"]` reports what the
> pre-partition policy would have charged, so you can see the size of what
> moved. To recover the pre-partition behaviour — which is what every figure
> published before 2026-08-28 was computed at — pass
> `ecological_standing_response="domain"` and `ecological_health_response="domain"`.
>
> **Where the obligation goes, and how to close the loop.** Pass your parcel
> inventory through `land/collective.compute_collective_guf()` and hand the
> result to `fiscal_snapshot(guf_revenue=...)`:
>
> ```python
> from hours_eoh.land.collective import compute_collective_guf
>
> guf = compute_collective_guf(your_parcels, epsilon)["guf_net_inflow"]
> snap = fiscal_snapshot(..., guf_revenue=guf)
>
> snap["guf"]["coverage"]   # fee ÷ the obligation relocated out of the domain
> snap["trust"]["guf_over_levy"]   # has the fee overtaken the labour levy?
> ```
>
> GUF arrives as its **own** Trust revenue line, never folded into the levy —
> the two behave oppositely across the arc, since the levy contracts with labour
> income while the fee scales with land held. It is circulatory: it redistributes
> TEH, it does not mint any.
>
> **`snap["guf"]["covered"] == True` is necessary, not sufficient.** The
> obligation it checks against is only the *ecological* requirement that left the
> domain; the fee also carries the **servicing** cost of the built environment,
> which the snapshot has no inventory for. On the shipped urban archetype the
> coverage figure is ~1e6, which says almost nothing — the denominator is tiny.
> Set the same revenue against the servicing census and it reads ~21× **over**,
> matching the 18.1× urban overshoot `scenarios/servicing_census` measured
> independently. Run `eoh scenario run servicing_census` for the comparison that
> actually constrains the fee's magnitude.

**State your frame.** Population, land area and capital stock are one frame and
must travel together: they are all extensive, so pairing one jurisdiction's
population with another's land silently rescales the ecological domain.
`CAPITAL_STOCK_DEFAULT` and `TRUST_BASE_TEH` say "at the 1M reference
population" in their own tag blocks and are per-frame quantities — running the
US population against the unscaled default models 335M people holding the
capital of 1M. `scenarios/frame.py` declares named frames and
`eoh scenario run frame` shows what an undeclared pairing costs.

**Converting capital stock to TEH**: if you have capital stock in dollars, divide by
your jurisdiction's mean labor-hour cost (the TEH/dollar exchange rate you decide).
The model is denominated in TEH, not dollars; the exchange rate is an input, not
something the model determines.

---

## 2. Which parameters to calibrate vs. keep at defaults

Every constant in `data.py` carries an inline provenance tag saying what kind of
claim its value makes. That tag, not intuition, tells you what to do with it.
Run `eoh provenance check` for the current counts, or read
`hours_eoh/reference/data/constant_provenance.csv` for all 288 with their
evidence. Both are generated from `data.py`, so neither can drift from it.

| Tag | What it means | What you should do |
|---|---|---|
| `physics` | Structural — a constant of nature | Keep. There are exactly **two**: `A_EARTH_M2`, `SIGMA_SB` |
| `measured` / `derived` | Sourced, or computed from sourced inputs | Keep unless you have better local data; check the source suits your jurisdiction |
| `convention` | A declared reference frame, not a claim | Keep. Changing it changes what the numbers *mean* |
| `normative` | A **decision**. No dataset settles it | **Decide it yourself.** This is a charter question, not a calibration |
| `bounded` | Picked inside a measured band | Re-pick inside the band if you have local evidence. Read `errs:` — it says which way the pick is wrong and whether that direction is safe |
| `placeholder` | Nothing constrains it | Replace where you can. Read `resolves_by:` for what would settle it |
| `instance` | **Yours to supply** — describes your jurisdiction | Supply it. The shipped number is a reference default, not evidence |

> **The single most important correction to make if you have read an older
> version of this guide.** It sorted constants into two bins, physics versus
> calibration, and listed
> `PERSONAL_EOH_BASE`, `ECOLOGICAL_THRESHOLD`, `M_BAND_LOW`/`M_BAND_HIGH`,
> `DEP_RATE` and `DIV_RATE` as physics to be left alone. **None of them is
> physics.** Two are constitutional commitments (`M_BAND_*`, `DIV_RATE`), two are
> desk estimates picked inside a band (`PERSONAL_EOH_BASE`, `DEP_RATE`), and one
> is an unconstrained placeholder (`ECOLOGICAL_THRESHOLD`). "Physics" was being
> used to mean "we are confident", which is precisely the wrong thing to tell an
> analyst deciding what not to touch.

### Start here: the constants that are yours, not ours

These carry the `instance` tag. Nothing about your jurisdiction can be measured
by this framework, so the shipped values are placeholders for *your* data — and
every canonical result in this repo was produced at them.

- **`TRUST_BASE_TEH = 35000000000.0`** — the most-consumed constant in the repo
  (77 call sites). Sized *backwards*: chosen so the dividend covers the
  obligations it must fund. Supply your Trust's real balance. Every fiscal
  function takes `trust_balance` as an argument, so you need not edit the
  constant — pass your own.
- **`CAPITAL_STOCK_DEFAULT = 2000000000.0`** — your gross fixed capital stock in
  TEH. Note it is 2,000 TEH/capita, which describes a *mid-arc* collective; at
  low ε you would be asserting capital the arc says is not there.
- **`CONTESTABILITY_G_PRIV = 0.03`** — your real capital return net of
  depreciation. Piketty's r gives 4–5%, above this default.
- **`GUF_LVI_W_*`** — land-value sub-index weights. Land value is local by
  construction; these come from a hedonic regression on *your* parcel data.
- **`AGE_GROUP_FRACTIONS`** — your census age pyramid, grouped to
  `AGE_GROUP_RANGES`. The shipped 7/16/60/17 is an OECD-shaped split that fits
  the US around 2020; by 2025 the US itself had moved to 6.5/14.5/60.0/18.9.
  `reference/care_demand.population_shares()` groups any band structure against
  the shipped census extract.

### Then: what to decide rather than measure

The `normative` constants are commitments your charter makes. No amount of data
retires them, and treating them as calibration knobs is a category error:

- `M_BAND_LOW = 1.8` / `M_BAND_HIGH = 2.1` — the constitutional multiplier band
- `DIV_RATE = 0.4` — the share of depreciation paid out as dividend
- `SUFF_LEVY_RATE = 0.0125` — a redistributive commitment. Worth knowing:
  `min_levy_for_solvency()` returns **zero at every ε** on the canonical
  configuration, because the dividend alone runs a surplus. This rate is not
  sized for solvency and never was; the Trust dividend funds the guarantee.

### Then: the placeholders worth your attention

Ranked by how much of the model they move, not by how wrong they are:

- **`AGE_WEIGHT_INFANT` / `AGE_WEIGHT_CHILD`** — `bounded`, and the band is
  ONE-SIDED. Measured at ≥ 2.55 and ≥ 1.35 against shipped 3.0 and 1.5, but
  ATUS surveys nobody under 15, so the self-maintenance term is missing and
  those floors can only rise. Leave them unless you have a time-use survey that
  covers children. They err HIGH, which is the safe direction: too low
  understates what a dependent needs and the deficit is paid in unserved care.
  (`AGE_WEIGHT_ELDERLY` is `measured` — 1.48, from ATUS + Census — and
  `AGE_WEIGHT_WORKING_AGE` is the numeraire, 1.0 by definition.)
- **`ECOLOGICAL_BASE_RATE = 500000.0`** — replace with your stewardship-hours
  census, but read §6 first: this constant is entangled with an open structural
  defect, and changing it alone will not fix what it looks like it should.
- **`CAPITAL_MACHINE_PROFILES`** — the tiers behind `civilization_epsilon()`
  (Step 3). Calibrated to bracket the mid-arc ε they are meant to produce.

**Rule of thumb**: ask *what would change this number?* If the answer is a
dataset, it is `measured`/`bounded`/`placeholder` and you calibrate it. If the
answer is "your jurisdiction", it is `instance` and you supply it. If the answer
is "a vote", it is `normative` and you decide it.

---

## 3. Calibration walkthrough — step by step

### Step 1: Establish a baseline

Start with `canonical_physical_state(0.40)` — the ideal mid-arc reference for
a civilization at 40% automation. Compare it to your actual data:

```python
from hours_eoh.core.trajectory import canonical_physical_state
canonical = canonical_physical_state(0.40)
# {'capital_stock_teh': 2_400_000_000, 'capital_age_ratio': 0.38,
#  'ecosystem_health': 0.82, 'monitoring_capability': 0.70, ...}

# Your actual data:
your_state = {
    "capital_stock_teh": your_capital_stock_in_teh,
    "capital_age_ratio": 0.45,             # from national accounts
    "ecosystem_health":  0.68,             # from ESI/BII index
    "monitoring_capability": 0.55,         # from ecological data coverage
    "knowledge_base_size": 3.2,            # relative to subsistence baseline
    "knowledge_complexity_per_unit": 1.8,  # estimated
    "age_distribution": {"infant": 0.06, "child": 0.18, "working_age": 0.62, "elderly": 0.14},
}
```

The divergence from canonical is the point — it tells you how your trajectory
differs from the ideal arc.

### Step 2: Run total_eoh() with your state

```python
from hours_eoh.core.eoh_generation import total_eoh

eoh = total_eoh(
    population=your_population,
    age_distribution=your_state["age_distribution"],
    capital_stock=your_state["capital_stock_teh"],
    capital_age_ratio=your_state["capital_age_ratio"],
    ecosystem_health=your_state["ecosystem_health"],
    monitoring_capability=your_state["monitoring_capability"],
    knowledge_complexity_per_unit=your_state["knowledge_complexity_per_unit"],
)
# eoh["total"] = your jurisdiction's total entropy obligation (h/yr)
# eoh["personal"] = biological burden (≈ 1,000 × population × 1.475)
# eoh["infrastructure"] = capital stock maintenance burden
```

Check plausibility: personal EOH should be roughly `PERSONAL_EOH_BASE × population
× 1.475`, where 1.475 is the age-weighted mean at default demographics. If it's
wildly off, check that your `age_distribution` fractions sum to 1.0 and match the
`AGE_GROUP_RANGES` keys.

**Which standard are you asking for?** `PERSONAL_EOH_BASE` is the operating value
between two others: `PERSONAL_EOH_SURVIVAL` (600, what it takes not to die) and
`PERSONAL_EOH_SUFFICIENCY` (1500, what it takes to live well), both referenced to
autarky. Pass `personal_standard=` to `total_eoh()` **or to
`eoh_to_teh_pipeline()`** to choose — both accept it as of 2026-08-17; before
that it reached only `total_eoh`, so this guide's two instructions could not
both be followed. **It is the largest single lever in the model: survival →
sufficiency moves total EOH 2.09×**, more than any domain base. This matters more
than it looks: a feasibility test run at the sufficiency standard and reported as
a survival result is the specific error this repo made and corrected — subsistence
*can* survive, it just cannot reach sufficiency without automation.

### Step 3: Choose your ε

ε is the fraction of EOH fulfilled by machines. At present (2024), most developed
economies are at ε ≈ 0.15–0.35: automation handles transport, manufacturing, and
basic computation, but not care, ecological stewardship, or knowledge maintenance.

You can estimate ε from your capital stock using `civilization_epsilon()`:

```python
from hours_eoh.core.civilization import civilization_epsilon
from hours_eoh.data import CAPITAL_MACHINE_PROFILES

eps_estimate = civilization_epsilon(
    capital_tiers={
        "power_grid": "standard",
        "water_treatment": "standard",
        "transportation": "advanced",
        "manufacturing": "advanced",
        "computing_ai": "basic",
    },
    population=your_population,
)
# eps_estimate["epsilon"] → estimated current ε
```

Or simply pick ε as a scenario parameter and run multiple values to bracket
uncertainty.

### Step 4: Run the full pipeline

```python
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

result = eoh_to_teh_pipeline(
    epsilon=eps_estimate,
    population=your_population,
    capital_stock=your_state["capital_stock_teh"],
    capital_age_ratio=your_state["capital_age_ratio"],
    ecosystem_health=your_state["ecosystem_health"],
    monitoring_capability=your_state["monitoring_capability"],
    knowledge_complexity_per_unit=your_state["knowledge_complexity_per_unit"],
)
# result["teh_created"]    → TEH entering circulation this period
# result["human_eoh"]      → labor demand on human workers (h/yr)
# result["registered_eoh"] → officially recognized labor (h/yr)
```

### Step 5: Run fiscal_snapshot()

```python
from hours_eoh.core.fiscal import fiscal_snapshot

snap = fiscal_snapshot(
    trust_balance=your_trust_balance,   # collective Trust fund balance in TEH
    labor_income=result["teh_created"], # TEH from pipeline
    capital_stock_teh=your_state["capital_stock_teh"],
    capital_age_ratio=your_state["capital_age_ratio"],
    population=your_population,
    epsilon=eps_estimate,
    ecosystem_health=your_state["ecosystem_health"],
    # STATE THE SAME FRAME YOU GAVE THE PIPELINE. Omit it and the area resolves
    # from your population at LAND_HECTARES_PER_CAPITA — a planetary average.
    ecological_area_hectares=your_state["ecological_area_hectares"],
)

print("Solvent:", snap["solvent"])
print("Trust end-of-period:", snap["trust"]["trust_end"])
print("Guarantee cost:", snap["guarantee"]["total_cost_teh"])
```

> **Pass the frame to both calls, or to neither.** `fiscal_snapshot()` sizes the
> ecological obligation independently of the pipeline, so if you give the
> pipeline your real land area and leave it off here, the two halves of your run
> describe two different jurisdictions. Before 2026-08-20 this function ignored
> the question entirely and always used the whole-contiguous-US anchor; the
> example in §4 below disagreed with its own pipeline call by **92.8×** while
> reporting `solvent: True`. It now resolves from your population exactly as
> `total_eoh()` does, so the default is at least a frame somebody chose — but a
> planetary average is still the wrong number for any actual collective.
>
> If you already have the pipeline's answer, pass it straight through with
> `eco_eoh_override=result["eoh_by_domain"]["ecological"]` and the two cannot
> diverge at all.

### Step 6: Sensitivity sweeps

Use `p.temporary()` to explore parameter sensitivity without polluting history:

```python
from hours_eoh.params import EohParams

p = EohParams()
# Sweep ecosystem_health from 0.5 to 0.9
for health in [0.50, 0.60, 0.70, 0.80, 0.90]:
    with p.temporary(ecosystem_health=health):
        result = eoh_to_teh_pipeline(eps_estimate, population=your_population,
                                     ecosystem_health=health)
        print(f"health={health}: EOH_eco={result['eoh_by_domain']['ecological']:.0f}")
```

Or use the CLI: `eoh sensitivity --param ecosystem_health --range 0.5:0.9:5`.

---

## 4. Running a scenario against local data — complete example

```python
"""
Minimal complete example: run eoh_to_teh_pipeline and fiscal_snapshot
with real inputs and interpret the outputs.
"""

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.research.recalibration import exit_financing

# --- Your data ---
population         = 5_000_000     # 5M people
land_hectares      = 12_000_000    # the land you steward — YOUR cadastre
capital_stock_teh  = 8_000_000_000 # 8B TEH (≈ 1,600 TEH/person)
capital_age_ratio  = 0.42
ecosystem_health   = 0.65          # moderately degraded
monitoring_cap     = 0.60
epsilon            = 0.28          # current automation level
trust_balance      = 150_000_000_000  # 30,000 TEH/person

# population, land and capital are ONE FRAME and must travel together.

age_dist = {
    "infant":      0.065,
    "child":       0.180,
    "working_age": 0.630,
    "elderly":     0.125,
}

# --- Run the pipeline ---
pipe = eoh_to_teh_pipeline(
    epsilon=epsilon,
    population=population,
    capital_stock=capital_stock_teh,
    capital_age_ratio=capital_age_ratio,
    ecosystem_health=ecosystem_health,
    monitoring_capability=monitoring_cap,
    age_distribution=age_dist,
    ecological_area_hectares=land_hectares,
)

# --- Run fiscal snapshot ---
# The ecological obligation is passed straight through from the pipeline, so the
# two calls cannot describe different jurisdictions. Equivalent here:
#   ecological_area_hectares=land_hectares
snap = fiscal_snapshot(
    trust_balance=trust_balance,
    labor_income=pipe["teh_created"],
    capital_stock_teh=capital_stock_teh,
    capital_age_ratio=capital_age_ratio,
    population=population,
    epsilon=epsilon,
    ecosystem_health=ecosystem_health,
    eco_eoh_override=pipe["eoh_by_domain"]["ecological"],
)

# --- Run contestability check (the ADOPTED §8.9 test) ---
exit_fin = exit_financing(epsilon, population=population)

# --- Interpret ---
print(f"Total EOH demand:  {pipe['total_eoh']/1e9:.2f}B h/yr")
print(f"Human EOH burden:  {pipe['human_eoh']/1e9:.2f}B h/yr  (= total × (1−ε))")
print(f"TEH created:       {pipe['teh_created']/1e9:.2f}B TEH/yr")
print(f"Fiscal solvent:    {snap['solvent']}")
print(f"Trust end:         {snap['trust']['trust_end']/1e9:.1f}B TEH")
print(f"Exit financeable:  {exit_fin['exit_financeable']}  "
      f"via {exit_fin['channel']}  (t_exit {exit_fin['t_labor_years']:.2f} yr)")
```

> **Do not use `contestability_margin()` (the bare χ = P/K_entry) for a reported
> result.** §8.9 superseded it with the three-channel time-to-finance-exit test
> above, and the difference is not academic: the repo's own recorded finding that
> "the corridor is CLOSED at defaults" was produced by the retired invariant, and
> the adopted test reopens it. The bare form is kept, callable, so the
> disagreement can be reproduced on demand — not because it is still the test.

---

## 5. Interpreting outputs

**`fiscal_snapshot()["solvent"] = False`**
The Trust cannot fund its obligations (stewardship + guarantee + ecological) from
dividend + levy. Action: increase `TRUST_BASE_TEH` (build reserves), raise
`SUFF_LEVY_RATE`, or reduce `DEP_RATE` / `DIV_RATE`. Run `eoh sensitivity` to
find the minimum trust balance for solvency at your ε.

**`trust["trust_stable"] = False`** (even when solvent)
Trust is eroding — expenditures exceed inflows. Long-run: Trust will deplete.
Action: raise levy or build reserves now while the economy is labor-intensive.

**`exit_financing()["exit_financeable"] = False`**
No channel finances a member out within one vesting period, so exit from the
collective is notional rather than substantive. Check `channel` to see which arm
was closest: `labor` carries the low arc, `underwritten` the mid-arc trough, and
`self` (dividend savings) the high end. Action: structural commonization — raise
the charter formation share φ, or seed the commons for entry underwriting. Levy
adjustments alone do not fix it; that is the §8.3 adversarial finding.

**`contestability_margin()["passes"] = False` (bare χ < 1)** — *superseded.*
Kept as a documented negative result. It reads RED across the whole arc at
current defaults because the sufficiency floor fell with the `PERSONAL_EOH_BASE`
reprice, and for a tenure-0 member that floor *is* the entire portable endowment.
Treat it as an advisory, not a verdict.

**`condition_ii["status"] = "FAIL"`** (multiplier band breach)
The mean multiplier has drifted outside [1.8, 2.1]. Run `eoh dashboard` to see
direction. If above band: assessors are systematically over-scoring; trigger
adversarial review. If below band: skill investment is insufficient.

---

## 6. Known limitations

What the model **cannot** tell you:

- **Domain balance — read this before you trust any ε**: personal EOH is
  **99.3% of total EOH at ε=0, falling to 62.5% at ε=0.89**, while ecological EOH
  books at **0.56–0.69 h/person·yr — 0.0% of the total at every ε**. Since
  ε = machine EOH / total EOH, your ε is overwhelmingly a personal-domain number,
  and your ecological and thermal obligations will round to nothing in its
  denominator. Run `eoh arc --domain-shares` to see it. **The ecological half of
  this is now closed (Phase 4f, adopted 2026-08-28), and not by a measurement.**
  `ECOLOGICAL_BASE_RATE` produces a *recurring* obligation, and the adopted
  partition assigns everything recurring to the Ground Use Fee — where it scales
  with land held rather than with the ledger. `ecological_standing_response`
  defaults to `"guf"`, so the ecological domain now carries stocks only and is
  exactly zero for land at reference condition. **Do not replace this anchor with
  your own measured stewardship cost**: that cost is GUF's, and charging it here
  as well would bill the same hours twice. What remains open is the KNOWLEDGE
  base and `CDR_LABOR_HOURS_PER_TONNE`; nothing in current data settles those.

- **Individual tenure-vesting**: the contestability model uses population-average
  portable endowment P. A late entrant to the collective has less vested capital
  than a founding member. Federation-wide tenure is tracked in
  `research/membership.py`, but per-capita figures elsewhere remain averages.

- **Between-collective exchange rates**: the shipped single-ledger model is the
  N=1 limit. `research/coasean.py` implements the N-collective federation with
  pairwise exchange rates, trust dynamics and settlement rules (§§6–7), anchored
  by a regression test reproducing single-ledger results exactly at N=1. It is
  research-tier: the API is not stable.

- **Desire economy**: the model covers entropy obligations (biological, physical,
  ecological, knowledge). It does not model the desire economy — discretionary
  consumption choices above the sufficiency floor. The `basket_price()` function
  captures the floor basket; above-floor pricing is left to collective discovery.

- **Calibration confidence — the honest headline**: of 288 constants, **72
  (25.0%) are grounded**, 18 are bounded picks, **114 (39.6%) are placeholders
  with no measurement behind them at all**, 67 are normative decisions, 12 are
  yours to supply, and 5 are retired. Measurement debt is **45.8%**, and the
  actionable part is the placeholders. The framework shows the direction and
  qualitative shape of the arc, not point forecasts — use it for structural
  analysis, not projection. Run `eoh provenance check` for the live figures;
  do not quote these from memory.

- **Four constants are calibrated to a target and say so**: `GUF_USE_*` (scaled
  so aggregate GUF matches levy revenue at mid-arc), `DEFAULT_SEGMENTS` (means
  set so the weighted mean hits 2.10, the band top — and it is the live default
  in `core/multipliers.py`, so any call omitting `segments` inherits it),
  `TRUST_BASE_TEH` (sized to cover the obligations it funds), and
  `CAPITAL_MACHINE_PROFILES` (tiers set to bracket the ε they are meant to
  produce). A result that depends on one of these is not independent evidence
  for it.

- **Objectivity vs. transparency**: the price computed by the model is the
  *floor price* — the minimum guaranteed by the TEH ledger. Actual market prices
  discovered above this floor are not modeled. See `hours-reconciliation.md §3`
  for the price-as-floor reframing.
