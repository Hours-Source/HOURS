# Implementation Guide

**Audience**: analysts and researchers at institutions or foundations who have
real economy data and want to model their own civilization using the HOURS framework.
This is not a developer guide — see `extending.md` for that.

**Goal**: given your data, you should be able to run one function and get
outputs that mean something about your jurisdiction.

```python
# template
from hours_eoh.core.simulation import make_economy_state
from hours_eoh.scenarios.collective import collective_snapshot

state = make_economy_state(population=..., capital_stock_teh=..., trust_balance=...)
report = collective_snapshot(
    state,
    parcels=your_parcel_inventory,          # or land_hectares=... if you have no inventory
    available_labor_eoh=your_labour_hours,  # omit it and you are measuring DEMAND
)
report["frame"]["labour_supplied"]          # True: the mint is what was served, not demanded
report["frame"]["labor_constrained"]        # True: your hours BOUND, and the shortfall is deferred
```

`collective_snapshot()` runs the EOH→TEH pipeline, the Ground Use Fee and the
fiscal snapshot on **one stated frame**, passing the three values between them
that otherwise have to be hand-carried. Run `eoh scenario run collective` to see
it on the shipped urban archetype.

**Pass `available_labor_eoh`.** Until 2026-09-12 this entry point could not
accept it, so every snapshot minted from obligation *demanded* while this guide
called the field its most consequential input. It is now forwarded to the
pipeline, the shortfall is reported as deferral, and the fiscal layer raises its
levies on what was served. The verdict string says which of the two you got.

**Use it in preference to calling the three by hand.** The sections below
document the pieces, because you will want to understand them and because
`collective_snapshot` is a thin assembly over exactly those calls — but running
them yourself means keeping eleven parameters in agreement across three
functions, and that is where the frame comes apart. It came apart in this
guide's own worked example, by nearly two orders of magnitude.

---

## 1. What inputs the model needs

The EOH → TEH pipeline takes eight physical-state fields. Here is what each
represents and where to find it in real-world data:

| Field | Type | Units | Real-world data source |
|---|---|---|---|
| `population` | float | persons | Census — total resident population |
| `capital_stock_teh` | float | TEH (≈ labor-hours of value) | National accounts: gross fixed capital stock, converted at your TEH/dollar exchange rate. **This is the stock you hold NOW, not an ε=0 baseline** — it is used exactly as supplied and is never rescaled by ε (author decision, 2026-09-09). Omit it and the model fills it from the canonical arc at your ε, which is a reference trajectory rather than your economy. Capital travels with `population` and `ecological_area_hectares` as ONE FRAME: the shipped default is stated at a 1M reference population, so moving the population without moving capital models your jurisdiction with someone else's apparatus. |
| `capital_age_ratio` | float | [0, 1] | National accounts: average age of fixed assets / average design life (or use 0.5 as default if unavailable) |
| `ecosystem_health` | float | [0, 1] | Ecosystem Services Index (ESI), Biodiversity Intactness Index (BII), or local ecological monitoring; 0.7 = moderate degradation, 0.9 = near-pristine. **Since Phases 4e/4f this no longer moves the ecological DOMAIN** — see the note below. It still drives the Ground Use Fee, which is where the recurring cost now sits. |
| `monitoring_capability` | float | [0, 1] | Fraction of deferred ecological EOH your monitoring systems can detect; proxy with your ecological data coverage fraction |
| `age_distribution` | dict | fractions summing to 1.0 | Census age pyramid, grouped into the buckets in `AGE_GROUP_RANGES`; see `AGE_GROUP_FRACTIONS` |
| `knowledge_base_size` | float | relative (1.0 = ε=0 reference) | Harder to measure; use national R&D stock relative to a subsistence baseline, or leave at canonical default |
| `ecological_area_hectares` | float | hectares | **The land your collective is responsible for stewarding.** Your own cadastre, or the GUF parcel inventory (`land/collective.py`) if you have run a GUF assessment — it already carries area per parcel. Omit it and the model derives the area from your population at `LAND_HECTARES_PER_CAPITA` (a planetary average, and the wrong number for any actual collective). Pass `ecological_hectares_per_capita=` instead if you know your ratio but not your absolute area. |
| `available_labor_eoh` | float | EOH-hours per year | **The labour your collective actually has.** `employment × annual hours per worker`, from your labour force survey; include unpaid household and care labour if your register admits it. **Do not use working-age population** — an hours-per-worker figure multiplied by the working-age band assumes full employment and overstates supply by the non-participation and unemployment rates together. Omit the field entirely and the pipeline assumes every hour of human-carried obligation gets worked; see the note below, which is the single most consequential default in this table. |

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
> coverage figure is enormous, which says almost nothing — the denominator is
> tiny. Set the same revenue against the servicing census and it reads an order
> of magnitude **over**, in line with the urban overshoot
> `scenarios/servicing_census` measures independently. Run
> `eoh scenario run servicing_census` for the comparison that actually
> constrains the fee's magnitude.

> **Supply `available_labor_eoh`, or you are measuring demand and calling it
> fulfilment.**
> The framework's claim is a chain — *physical obligation → verified fulfilment
> → monetary claim* — and the middle link is the one you have to supply. The
> register enforces that an obligation existed: nothing mints without one, and
> offering more hours than the obligation requires mints nothing further. What
> the pipeline cannot know on its own is whether the work was **done**.
>
> `available_labor_eoh` defaults to unsupplied. On that path the pipeline mints
> from the human obligation that is *demanded*, not the part actually *served*.
> At its sharpest: run the pipeline with `population=0` and it still mints,
> because infrastructure and knowledge obligations do not depend on anyone
> existing. Supply `available_labor_eoh=0.0` on the same call and it mints
> exactly nothing, booking the whole obligation as deferred.
>
> Both paths are legitimate — a demand figure is what you want when sizing an
> obligation — but they are different quantities and only one of them is
> fulfilment. Whether you passed the field tells you which produced your figure
> (`collective_snapshot()` reports it as `frame["labour_supplied"]`);
> `result["labor_constrained"]` says whether the hours you supplied BOUND — it is
> False both when they sufficed and when none were given. And `result["deferred_personal"]` / `result["deferred_total"]` report the
> shortfall rather than absorbing it. Two rationing doctrines are available:
> `survival_first` (the default — personal obligation is served first, so a
> non-zero `deferred_personal` is a severe reading) and `pro_rata`.

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
`hours_eoh/reference/data/constant_provenance.csv` for every constant with its
evidence. Both are generated from `data.py`, so neither can drift from it. This
guide deliberately quotes no counts: they move every time a constant lands.

| Tag | What it means | What you should do |
|---|---|---|
| `physics` | Structural — a constant of nature | Keep. There are only a handful, and the CSV names them |
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
every canonical result in this repo was produced at them. **Filter the
provenance CSV on `tag == instance` for the complete list**; the ones below are
grouped by what they describe, and the list grows as the framework learns to
ask rather than assume.

- **`TRUST_BASE_TEH`** — the most-consumed constant in the repo. Sized
  *backwards*: chosen so the dividend covers the obligations it must fund.
  Supply your Trust's real balance. Every fiscal function takes `trust_balance`
  as an argument, so you need not edit the constant — pass your own.
- **`CAPITAL_STOCK_DEFAULT`** — your gross fixed capital stock in TEH, and it is
  the stock you hold NOW: since 2026-09-09 a supplied stock is used exactly as
  given and is never rescaled by ε. The shipped value is stated **at the 1M
  reference population** and describes a *mid-arc* collective — so passing it
  unchanged at low ε asserts capital the arc says is not there, and passing it
  unchanged at a different population asserts someone else's apparatus. Leave
  the field unset and the model fills it from the canonical arc at your ε
  instead.
- **`LAND_HECTARES_PER_CAPITA`** — a planetary average, and the wrong number for
  any actual collective. Supply your land, as in §1.
- **`REGISTER_CADENCE`** — how often your register records fulfilment:
  `episodic` (the default, which errs toward the costlier reading on purpose) or
  `continuous`. It decides whether the register's own verification cost fits
  inside the labour your population can supply. Run
  `eoh scenario run verification_band --cadence continuous` to see where a
  continuous register stops being affordable.
- **`BASKET_WATER_*`** — the distance to water, the carry volume and the share
  carried by hand. A village and a city beside one spring walk the same
  distance, so no survey of one population transfers to another. Declare yours
  and `scenarios/personal_floor.water_feasibility()` reports whether it fits and
  the furthest distance that still does.
- **`PERSONAL_ABATABILITY_*`** and **`PERSONAL_EOH_BASE_CLIMATE_FRAME`** — how
  far automation can reach each personal component in your setting, and the
  climate your personal base is stated for.
- **`CONTESTABILITY_G_PRIV = 0.03`** — your real capital return net of
  depreciation. Piketty's r gives 4–5%, above this default.
- **`GUF_LVI_W_*`** — land-value sub-index weights. Land value is local by
  construction; these come from a hedonic regression on *your* parcel data.
- **`AGE_GROUP_FRACTIONS`** — your census age pyramid, grouped to
  `AGE_GROUP_RANGES`. The shipped split is OECD-shaped and fits the US of a few
  years ago; the US itself has aged since, which is the point — a pyramid is a
  date as well as a place.
  `reference/care_demand.population_shares()` groups any band structure against
  the shipped census extract.

### Then: what to decide rather than measure

The `normative` constants are commitments your charter makes. No amount of data
retires them, and treating them as calibration knobs is a category error:

- `M_BAND_LOW` / `M_BAND_HIGH` — the constitutional multiplier band
- `DIV_RATE` — the share of depreciation paid out as dividend
- `SUFF_LEVY_RATE` — a redistributive commitment. Worth knowing:
  `min_levy_for_solvency()` returns **zero at every ε** on the canonical
  configuration, because the dividend alone runs a surplus. This rate is not
  sized for solvency and never was; the Trust dividend funds the guarantee.

### Then: the placeholders worth your attention

Ranked by how much of the model they move, not by how wrong they are:

- **`AGE_WEIGHT_INFANT` / `AGE_WEIGHT_CHILD`** — `bounded`, and the band is
  ONE-SIDED. The measured values are floors below the shipped picks, because
  ATUS surveys nobody under 15, so the self-maintenance term is missing and
  those floors can only rise. Leave them unless you have a time-use survey that
  covers children. They err HIGH, which is the safe direction: too low
  understates what a dependent needs and the deficit is paid in unserved care.
  (`AGE_WEIGHT_ELDERLY` is `measured`, from ATUS + Census, and
  `AGE_WEIGHT_WORKING_AGE` is the numeraire, 1.0 by definition.)
- **`ECOLOGICAL_BASE_RATE`** — do NOT replace it with your stewardship-hours
  census; read §6 first. Since the Phase 4f partition the recurring ecological
  cost is the Ground Use Fee's, and charging it here as well would bill the same
  hours twice.
- **`CAPITAL_MACHINE_PROFILES`** — the tiers behind `civilization_epsilon()`
  (Step 3). Calibrated to bracket the mid-arc ε they are meant to produce.

**Rule of thumb**: ask *what would change this number?* If the answer is a
dataset, it is `measured`/`bounded`/`placeholder` and you calibrate it. If the
answer is "your jurisdiction", it is `instance` and you supply it. If the answer
is "a vote", it is `normative` and you decide it.

---

## 3. Calibration walkthrough — step by step

**Every block in this section runs as written, in order**, against the
illustrative inputs below — `tests/test_doc_examples.py` fails the build if one
stops. Replace the values with yours; the variable names are what the later
steps read.

```python
# Illustrative inputs for a 5M-person collective. REPLACE EVERY VALUE.
your_population           = 5_000_000
your_capital_stock_in_teh = 8_000_000_000   # national accounts ÷ your TEH/currency rate
your_trust_balance        = 150_000_000_000
your_labour_hours         = 5_000_000 * 0.63 * 0.70 * 2_080.0   # employed × hours/worker
```

### Step 1: Establish a baseline

Start with `canonical_physical_state(0.40)` — the ideal mid-arc reference for
a civilization at 40% automation. Compare it to your actual data:

```python
from hours_eoh.core.trajectory import canonical_physical_state
canonical = canonical_physical_state(0.40)
print(sorted(canonical))   # the fields a physical state carries — compare yours field by field

# Your actual data:
your_state = {
    "capital_stock_teh": your_capital_stock_in_teh,
    "capital_age_ratio": 0.45,             # from national accounts
    "ecosystem_health":  0.68,             # from ESI/BII index
    "monitoring_capability": 0.55,         # from ecological data coverage
    "knowledge_base_size": 3.2,            # relative to subsistence baseline
    "knowledge_complexity_per_unit": 1.8,  # estimated
    "age_distribution": {"infant": 0.06, "child": 0.18, "working_age": 0.62, "elderly": 0.14},
    "ecological_area_hectares": 12_000_000,  # YOUR cadastre
    "available_labor_eoh": your_labour_hours,
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
# eoh["personal"] = biological burden (≈ PERSONAL_EOH_BASE × population × w,
#                   where w is the age-weighted mean — see the check below)
# eoh["infrastructure"] = capital stock maintenance burden
```

Check plausibility: personal EOH should be roughly `PERSONAL_EOH_BASE × population
× w`, where `w` is the age-weighted mean at YOUR demographics. Get it from
`scenarios.feasibility.age_weight_mean()` rather than from a number written here
— that mean has moved twice as age weights were measured, and a copy of it
written here went stale for a month the first time. If your figure is wildly off, check
that your `age_distribution` fractions sum to 1.0 and match the
`AGE_GROUP_RANGES` keys.

**Which standard are you asking for?** `PERSONAL_EOH_BASE` is the operating value
between two others: `PERSONAL_EOH_SURVIVAL` (what it takes not to die) and
`PERSONAL_EOH_SUFFICIENCY` (what it takes to live well), both referenced to
autarky. Pass `personal_standard=` to `total_eoh()` **or to
`eoh_to_teh_pipeline()`** to choose — both accept it as of 2026-08-17; before
that it reached only `total_eoh`, so this guide's two instructions could not
both be followed. **It is the largest single lever in the model: survival →
sufficiency roughly doubles total EOH**, more than any domain base. This matters more
than it looks: a feasibility test run at the sufficiency standard and reported as
a survival result is the specific error this repo made and corrected — subsistence
*can* survive, it just cannot reach sufficiency without automation.

### Step 3: Choose your ε

ε is the fraction of EOH fulfilled by machines. **Do not pick it from a
sentence in a guide — read it off your economy, and expect a band rather than a
number.** The framework carries two instruments that share no data:

- **From capital** — `scenarios/capital_retrodiction.py` reads ε off a fixed-asset
  inventory. It rests on three declared judgements (valuation doctrine, the
  currency-to-hours rate, and what counts as capital), so it returns a GRID.
  `currency_per_teh` is required and has no default, because converting money to
  hours is itself a valuation.
- **From time use** — `scenarios/labour_epsilon.py` reads ε off time diaries,
  with no currency in the chain and one judgement instead of three. Run
  `eoh scenario run labour_epsilon`.

Run for the US, the two bands land close to each other without overlapping,
which is the honest word for what a second instrument can show. Both divide by
the same obligation, so they check the machine/human split, not the total.

For a quick structural estimate from a capital description, use
`civilization_epsilon()`:

```python
from hours_eoh.core.civilization import civilization_epsilon

estimate = civilization_epsilon({
    "population": your_population,
    # keys are CAPITAL_MACHINE_PROFILES types; values a tier name or a spec dict
    "capital": {
        "power_grid": "standard",
        "water_treatment": "standard",
        "transportation": "advanced",
        "industrial_automation": "advanced",
        "computing_ai": "basic",
    },
})
eps_estimate = estimate["epsilon"]
```

Or pick ε as a scenario parameter and run several values to bracket the
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
    # WITHOUT THIS the two lines below report demand, not fulfilment.
    available_labor_eoh=your_state["available_labor_eoh"],
)
# result["teh_created"]      → TEH entering circulation this period
# result["human_eoh"]        → labor carried by humans (h/yr)
# result["registered_eoh"]   → officially recognized labor (h/yr)
#
# result["labor_constrained"] → True means your hours BOUND; False means they
#                               sufficed — or that none were supplied
# result["deferred_total"]    → obligation nobody had the hours to meet
#
# NOTE once the constraint binds, result["human_eoh"] is what was SERVED, not
#      what was owed. The obligation is human_eoh + deferred_total. Reading
#      human_eoh alone under a binding constraint reports your labour supply
#      back to you.
#
# result["human_fraction"]      → share of obligation people carry. NOT 1 - ε:
#                                 since Phase 2 the personal domain has its own
#                                 automation floor. The old quantity is reported
#                                 as result["uniform_split_factor"].
# result["machine_capability"]  → the index you supplied (alias: "epsilon")
# result["epsilon_observable"]  → the machine share the split actually implies,
#                                 which is BELOW the index you gave it
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
> example in §4 below disagreed with its own pipeline call by **nearly two
> orders of magnitude** while
> reporting `solvent: True`. It now resolves from your population exactly as
> `total_eoh()` does, so the default is at least a frame somebody chose — but a
> planetary average is still the wrong number for any actual collective.
>
> If you already have the pipeline's answer, pass it straight through with
> `eco_eoh_override=result["eoh_by_domain"]["ecological"]` and the two cannot
> diverge at all.

### Step 6: Sensitivity sweeps

Physical inputs are keyword arguments, so a sweep is a loop over the call.
Sweep what bites: since the Phase 4f partition, ecosystem health moves the Ground
Use Fee rather than the ecological domain, so the informative sweep for an
institution is usually the labour supply:

```python
for share in [0.6, 0.8, 1.0, 1.2]:
    result = eoh_to_teh_pipeline(
        eps_estimate, population=your_population,
        capital_stock=your_state["capital_stock_teh"],
        ecological_area_hectares=your_state["ecological_area_hectares"],
        available_labor_eoh=share * your_state["available_labor_eoh"],
    )
    print(f"labour ×{share}: deferred={result['deferred_total']:.3e} h/yr  "
          f"TEH={result['teh_created']:.3e}")
```

For fiscal parameters use the CLI:
`eoh sensitivity fiscal --parameter dep_rate --values 0.03,0.045,0.06`.

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
epsilon            = 0.28          # machine CAPABILITY index (alias for
                                   # machine_capability=); the OBSERVED machine
                                   # share comes back below and is lower
# YOUR labour force survey. Derived from this example's own demography so the
# two cannot disagree, and note the EMPLOYMENT RATE: hours-per-worker applies to
# people who work, not to the working-age band.
#   from hours_eoh.data import H_REF          # 2,080 h/yr, the policy-free
#                                             # nominal (40 h x 52 wk)
employment_rate    = 0.70          # employed / working-age — YOUR labour survey
workers            = 5_000_000 * 0.630 * employment_rate     # 2,205,000
labour_hours       = workers * 2_080.0                       # H_REF
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
    available_labor_eoh=labour_hours,
)
# Check which path produced these figures before quoting any of them:
#   pipe["labor_constrained"] is True  -> your labour BOUND (False: it sufficed)
#   pipe["deferred_total"]             -> obligation your labour could not meet
#
# THIS EXAMPLE DOES NOT CLEAR, AND THAT IS THE POINT OF SHOWING IT.
# The obligation is pipe["human_eoh"] + pipe["deferred_total"] — read it from
# the call rather than from this comment. Against 2,205,000 workers it needs
# more hours each per year than ANY point in WORK_YEAR_REFERENCE_POINTS reaches,
# nominal included, so the shortfall stands at every work-year the framework
# carries and pipe["deferred_total"] is non-zero.
#
# Only the SHAPE is stated here, deliberately. An earlier version of this
# comment carried three derived figures and all three had gone stale — they
# still described a configuration two changes back. That drift is failure mode
# 13, and the remedy the repo already applies elsewhere is to print the number
# instead of restating it.
#
# That is expected rather than alarming. Hold this capital stock and demography
# fixed and the obligation is met from a capability somewhere near half; the
# example runs at 0.28. COMPUTE YOUR OWN clearing point rather than quoting one
# — it depends on your capital stock, your demography and your land, and the
# package default from `eoh scenario run feasibility` is a DIFFERENT
# configuration with a different answer.
#
# Do NOT raise the labour figure until the deferral disappears. The deferral is
# the finding, and suppressing it is exactly what this field exists to prevent.

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
print(f"Human EOH burden:  {pipe['human_eoh']/1e9:.2f}B h/yr  (= SERVED, not owed)")
# Under a binding labour constraint human_eoh reports what was SERVED, so
# reading it alone hands your own labour supply back to you. The obligation is
# the sum below, and the identity is what makes the deferral visible.
obligation = pipe["human_eoh"] + pipe["deferred_total"]
print(f"Human obligation:  {obligation/1e9:.3f}B h/yr  "
      f"({obligation/workers:,.0f} h per worker · yr against {workers:,.0f} workers)")
print(f"Deferred:          {pipe['deferred_total']/1e9:.3f}B h/yr  "
      f"(labour-constrained: {pipe['labor_constrained']})")
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
The Trust cannot fund the guarantee from dividend + levy + GUF. Stewardship,
ecological and care labour are paid at the mint and are not Trust expenditure. Action: increase `TRUST_BASE_TEH` (build reserves), raise
`SUFF_LEVY_RATE`, or reduce `DEP_RATE` / `DIV_RATE`. Run `eoh sensitivity` to
find the minimum trust balance for solvency at your ε.

**`trust["trust_stable"] = False`** (even when solvent)
Trust is eroding — the guarantee exceeds levy + GUF inflows, so the balance is
paying the difference out of principal. Long-run: the Trust depletes.
Action: raise levy or build reserves now while the economy is labor-intensive.

Since 2026-09-15 only what the Trust OWES leaves it (unspent dividend is
retained), so at the shipped defaults `trust_stable` is **True at every ε** and
the balance GROWS — levy inflow exceeds the guarantee across the arc. Eroding is
now the exception rather than the default; `trust["guarantee_unfunded"]` reports
what the balance and inflows together could not cover.

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
  **almost all of the obligation at subsistence and still the largest domain at
  the top of the arc**, while the ecological domain carries only stocks and is
  zero for land at reference condition. Since ε = machine EOH / total EOH, your ε
  is overwhelmingly a personal-domain number, and your ecological and thermal
  obligations will round to nothing in its denominator. Run
  `eoh arc --domain-shares` for the live shares. **The ecological half of
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

- **Calibration confidence — the honest headline**: well under a third of the
  constants are grounded, the largest single category is placeholders with no
  measurement behind them at all, and measurement debt runs at roughly two
  constants in five. The actionable part is the placeholders. **The strongest
  verdict any result here can carry is "possible"**: a verdict may not outrank
  the weakest input it rests on, and every headline function rests on at least
  one placeholder (`utils/verdict_ladder.py` computes this). The framework shows
  the direction and qualitative shape of the arc, not point forecasts — use it
  for structural analysis and feasibility checks, not projection. Run
  `eoh provenance check` for the live figures; do not quote them from memory.

- **Verification cost is reported beside the accounts, not inside them.** What
  running the register costs is measured for the apparatus and checked against
  the labour a population can supply (`eoh scenario run verification_band`), but
  it is not added to the obligation, because a registrant's documentation hour
  may already be inside it. Read the band before sizing a register, and declare
  `REGISTER_CADENCE`.

- **Distribution under a captured register is not modelled.** Capture cannot
  raise the total mint — registering cannot create obligation, and the mint
  cannot exceed what was served — but a captured register can admit one
  household's obligation and refuse another's, and every figure here is a
  per-capita aggregate with no variable for who was excluded. Your governance of
  the register is the only protection against that, and this model cannot check
  it for you.

- **Four constants are calibrated to a target and say so**: `GUF_USE_*` (scaled
  so aggregate GUF matches levy revenue at mid-arc), `DEFAULT_SEGMENTS` (means
  set so the weighted mean lands on a chosen point in the band — and it is the live default
  in `core/multipliers.py`, so any call omitting `segments` inherits it),
  `TRUST_BASE_TEH` (sized to cover the obligations it funds), and
  `CAPITAL_MACHINE_PROFILES` (tiers set to bracket the ε they are meant to
  produce). A result that depends on one of these is not independent evidence
  for it.

- **Objectivity vs. transparency**: the price computed by the model is the
  *floor price* — the minimum guaranteed by the TEH ledger. Actual market prices
  discovered above this floor are not modeled. See
  [Prior Art and Limitations](../theory/prior_art.md#what-this-framework-does-differently)
  for the price-as-floor reframing.
