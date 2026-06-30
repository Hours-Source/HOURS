# Implementation Guide

**Audience**: analysts and researchers at institutions or foundations who have
real economy data and want to model their own civilization using the HOURS framework.
This is not a developer guide — see `extending.md` for that.

**Goal**: given your data, you should be able to run `eoh_to_teh_pipeline()` and
`fiscal_snapshot()` and get outputs that mean something about your jurisdiction.

---

## 1. What inputs the model needs

The EOH → TEH pipeline takes seven physical-state fields. Here is what each
represents and where to find it in real-world data:

| Field | Type | Units | Real-world data source |
|---|---|---|---|
| `population` | float | persons | Census — total resident population |
| `capital_stock_teh` | float | TEH (≈ labor-hours of value) | National accounts: gross fixed capital stock, converted at your TEH/dollar exchange rate |
| `capital_age_ratio` | float | [0, 1] | National accounts: average age of fixed assets / average design life (or use 0.5 as default if unavailable) |
| `ecosystem_health` | float | [0, 1] | Ecosystem Services Index (ESI), Biodiversity Intactness Index (BII), or local ecological monitoring; 0.7 = moderate degradation, 0.9 = near-pristine |
| `monitoring_capability` | float | [0, 1] | Fraction of deferred ecological EOH your monitoring systems can detect; proxy with your ecological data coverage fraction |
| `age_distribution` | dict | fractions summing to 1.0 | Census age pyramid, grouped into infant/child/working_age/elderly buckets matching `AGE_GROUPS` |
| `knowledge_base_size` | float | relative (1.0 = ε=0 reference) | Harder to measure; use national R&D stock relative to a subsistence baseline, or leave at canonical default |

**Converting capital stock to TEH**: if you have capital stock in dollars, divide by
your jurisdiction's mean labor-hour cost (the TEH/dollar exchange rate you decide).
The model is denominated in TEH, not dollars; the exchange rate is an input, not
something the model determines.

---

## 2. Which parameters to calibrate vs. keep at defaults

**The physics/calibration split** (see full table in `docs/parameter_provenance.md`):

**Keep at defaults (physics parameters)**:
- `PERSONAL_EOH_BASE = 1500` — the biological entropy burden per person is a physical claim
- `ECOLOGICAL_THRESHOLD = 0.40` — the tipping-point threshold for ecosystem collapse
- `M_BAND_LOW / M_BAND_HIGH = 1.8 / 2.1` — constitutional multiplier band
- `DEP_RATE = 0.045`, `DIV_RATE = 0.40` — Trust capital dynamics

**Change these to fit your data (calibration parameters)**:
- `ECOLOGICAL_BASE_RATE = 500,000` → replace with your measured ecosystem stewardship cost
- `TRUST_BASE_TEH = 35B` → scale to your population (default is per 1M people)
- `SUFF_LEVY_RATE = 0.0125` → calibrate to fiscal solvency requirements
- `AGE_GROUPS` fractions → replace with your census age pyramid
- `skill_decay_rate = 0.10` → replace with measured sector-specific skill obsolescence

**Rule of thumb**: if changing the parameter changes what the model *claims* about
physics (entropy, biology, tipping points), it's physics. If it changes the
calibration to your jurisdiction, it's a calibration knob.

---

## 3. Calibration walkthrough — step by step

### Step 1: Establish a baseline

Start with `canonical_physical_state(0.40)` — the ideal mid-arc reference for
a civilization at 40% automation. Compare it to your actual data:

```python
from hours_eoh.core.trajectory import canonical_physical_state
canonical = canonical_physical_state(0.40)
# {'capital_stock_teh': 3_600_000_000, 'ecosystem_health': 0.82, ...}

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
# eoh["personal"] = biological burden (should be ~1,500 × population × 1.475)
# eoh["infrastructure"] = capital stock maintenance burden
```

Check plausibility: personal EOH should be roughly `1,500 × population × 1.475`
(age-weighted mean = 1.475 at default demographics). If it's wildly off, check
that your `age_distribution` fractions sum to 1.0 and match the `AGE_GROUPS` keys.

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
)

print("Solvent:", snap["solvent"])
print("Trust end-of-period:", snap["trust"]["trust_end"])
print("Guarantee cost:", snap["guarantee"]["total_cost_teh"])
```

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
from hours_eoh.research.contestability import contestability_margin

# --- Your data ---
population         = 5_000_000     # 5M people
capital_stock_teh  = 8_000_000_000 # 8B TEH (≈ 1,600 TEH/person)
capital_age_ratio  = 0.42
ecosystem_health   = 0.65          # moderately degraded
monitoring_cap     = 0.60
epsilon            = 0.28          # current automation level
trust_balance      = 150_000_000_000  # 30,000 TEH/person

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
)

# --- Run fiscal snapshot ---
snap = fiscal_snapshot(
    trust_balance=trust_balance,
    labor_income=pipe["teh_created"],
    capital_stock_teh=capital_stock_teh,
    capital_age_ratio=capital_age_ratio,
    population=population,
    epsilon=epsilon,
    ecosystem_health=ecosystem_health,
)

# --- Run contestability check ---
chi = contestability_margin(epsilon, population, trust_balance)

# --- Interpret ---
print(f"Total EOH demand:  {pipe['total_eoh']/1e9:.2f}B h/yr")
print(f"Human EOH burden:  {pipe['human_eoh']/1e9:.2f}B h/yr  (= total × (1−ε))")
print(f"TEH created:       {pipe['teh_created']/1e9:.2f}B TEH/yr")
print(f"Fiscal solvent:    {snap['solvent']}")
print(f"Trust end:         {snap['trust']['trust_end']/1e9:.1f}B TEH")
print(f"Contestability χ:  {chi['chi']:.3f}  ({'OK' if chi['passes'] else 'BREACH'})")
```

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

**`contestability_margin()["passes"] = False` (χ < 1)**
The portable endowment P is less than the cost of founding a competing collective.
Exit from the collective is notional, not substantive. Action: grow Trust
(increasing P) or reduce barriers to collective formation (lowering K_entry).
This is the adversarial finding under increasing_returns — it requires structural
commonization, not just levy adjustments.

**`condition_ii["status"] = "FAIL"`** (multiplier band breach)
The mean multiplier has drifted outside [1.8, 2.1]. Run `eoh dashboard` to see
direction. If above band: assessors are systematically over-scoring; trigger
adversarial review. If below band: skill investment is insufficient.

---

## 6. Known limitations

What the model **cannot** tell you:

- **Individual tenure-vesting**: the contestability model uses population-average
  portable endowment P. A late entrant to the collective has less vested capital
  than a founding member. The model does not yet track individual tenure — all
  per-capita figures are averages. This is documented in
  `research/contestability.py` as an open gap.

- **Between-collective exchange rates**: the current implementation is a single
  collective (the N=1 limit). Multi-collective dynamics, inter-collective FX
  rates, and relative inflation between collectives are modeled in
  `research/contestability.py` only as scalar χ — the Polycentric/Coasean
  scaffolding (Workstream D) is still in-progress.

- **Desire economy**: the model covers entropy obligations (biological, physical,
  ecological, knowledge). It does not model the desire economy — discretionary
  consumption choices above the sufficiency floor. The `basket_price()` function
  captures the floor basket; above-floor pricing is left to collective discovery.

- **Calibration confidence**: most parameters are calibrated to reasonable
  structural priors, not fitted to historical data. The framework shows the
  direction and qualitative shape of the arc, not point forecasts. Use it for
  structural analysis, not projection.

- **Objectivity vs. transparency**: the price computed by the model is the
  *floor price* — the minimum guaranteed by the TEH ledger. Actual market prices
  discovered above this floor are not modeled. See `hours-reconciliation.md §3`
  for the price-as-floor reframing.
