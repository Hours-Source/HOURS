# Parameter Provenance

Every parameter used by the EOH → TEH model, with its default value, units,
and derivation rationale.

> **Allocation doctrine (decided 2026-08-05).** The framework is built to work
> going forward, not to be a complete record of the past. An exhaustive backward
> accounting is impossible and self-defeating: records are biased toward whoever
> kept documentation, so the more history an allocation demands, the more it
> privileges the well-documented. A line has to be drawn or there is no end to how
> far back one goes. **Looking back sets a starting point, not a verdict** — pick
> a defensible line, allocate what is known, and move forward, because that begins
> solving and preventing, which a perfect ledger of blame never does.
>
> Two consequences, both implemented: emissions belonging to no territory
> (international shipping and aviation, 46 GtCO₂) are **redistributed pro-rata**
> rather than left unowned — we all inherited the world as it is — superseded by
> consumption-based allocation once trade data supports it, which for OWID means
> 1990 forward. And land converted inside a collective counts as **that
> collective's**, whatever demand motivated it. Both are real arguments; they are
> recorded for live implementations to settle, not resolved by the model.

## The tag scheme

The goal is that **every constant carries a provenance tag, and the CHOSEN set
shrinks over time as measured data replaces guesses**. Four tags:

- **physics** — a structural claim about how entropy works. Changing it changes
  the model's claim about the world; needs a theoretical justification, not a knob.
- **measured** — read from an external empirical source (e.g. O*NET, BLS). The
  strongest tag: it can be wrong, and a data refresh would show it.
- **derived** — computed from measured inputs by a stated formula (normalizations,
  composites). Inherits its authority from the measurements beneath it.
- **CHOSEN** — a value set by judgement, not yet backed by measurement. **Every
  CHOSEN constant carries an *epistemic pointer* — the specific evidence or
  measurement that would move it off CHOSEN.** These are the calibration targets
  and the honest debts of the model.

A fifth working label, **derived-then-FROZEN**, marks a derived value pinned at a
reference epoch so it stays comparable across data vintages (re-deriving it per
vintage would reintroduce circularity).

> **Migration note (updated 2026-08-05).** The EOH-domain tables have now been
> migrated off the older binary **Kind = Physics | Calibration**. The migration
> was not cosmetic: several constants carrying the `Physics` tag turned out to be
> desk estimates, and under this scheme's own definition — *physics* is "a
> structural claim about how entropy works… needs a theoretical justification,
> not a knob" — they are `CHOSEN`. Where a functional FORM is structural but its
> constant is not, the table says so explicitly (`physics` form / `CHOSEN`
> value) rather than letting the stronger tag cover both.
>
> The retags are listed in [Retag log](#retag-log-2026-08-05) below. The
> machine-readable source of truth for the multiplier constants is
> [`hours_eoh/reference/data/multiplier_provenance_v5.csv`](../hours_eoh/reference/data/multiplier_provenance_v5.csv)
> (column `resolves_by` = the epistemic pointer).

Source: `hours_eoh/data.py` and `hours_eoh/params.py`; measured multiplier data
in `hours_eoh/reference/data/` (O*NET 30.3 / BLS, frozen epoch 2026-07-29).

---

## EOH Generation — Personal Domain

> **This is the highest-leverage block in the model.** Personal EOH is 87–96% of
> total EOH at every point on the arc (see [Domain balance](#domain-balance--the-denominator-problem)),
> so `PERSONAL_EOH_BASE` effectively sets the denominator of ε. It carried the
> `Physics` tag while being a four-line desk estimate.
>
> **Repriced 1,500 → 1,000 on 2026-08-06** (author decision) to the high end of
> the evidence band, on the asymmetric-loss argument below. Still `CHOSEN`.

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `PERSONAL_EOH_BASE` | **1,000** (was 1,500) | h/yr·person (working-age-equivalent) | **CHOSEN** | **BLS American Time Use Survey (ATUS)**, annual averages by activity code — household activities (food prep & cleanup, interior/exterior maintenance, laundry), caring for & helping household members, and health self-care. ATUS reports hours/day per capita by activity and demographic, which converts directly to this constant's units. *No ATUS data is currently used anywhere in the repo.* |
| `AGE_GROUPS` (eoh_weight) | infant=3.0, child=1.5, working_age=1.0, elderly=2.5 | relative to working-age=1.0 | **CHOSEN** | ATUS "caring for and helping household children / adults" hours per care-recipient by recipient age, plus NHATS/HRS for hours of assistance to older adults with functional limitation. The *direction* (infants and elderly draw more caregiver labor) is structural; the 3.0 / 2.5 magnitudes are not. |
| `AGE_GROUPS` (fraction) | infant=7%, child=16%, working_age=60%, elderly=17% | fraction of population | **CHOSEN** | National census / UN WPP age distribution for the jurisdiction being modelled. Approximate OECD default. Age-weighted mean = Σ(fraction×weight) = 1.475 → mean personal EOH = 1,500 × 1.475 = 2,213 h/yr·person. |
| `ELDERLY_EOH_EPSILON_FACTOR` | 0.05 | fraction shift per ε unit | **CHOSEN** | Longitudinal life-expectancy series against a measured automation index. Rationale: automation improves medicine → longer lives → larger elderly fraction. Modest; secondary to the dominant ε effect in the fulfillment split. |

**Derivation of the shipped 1,500** (retained so the retag is auditable): food
preparation and nutrition ~4 h/wk = 208 h/yr; shelter maintenance and sanitation
~3 h/wk = 156 h/yr; basic healthcare and hygiene ~4 h/wk = 208 h/yr; social
reproduction and care ~18 h/wk = 936 h/yr; total ≈ 1,508 → rounded to 1,500.
Every one of those four is an estimate, and the largest (care, 62% of the total)
is the least constrained. ATUS measures all four directly.

### Block III — the ε=0 endpoint, two floors, and the accounting basis

*Added 2026-08-06.*

#### Subsistence has no apparatus

`canonical_physical_state` asserted **2,000 TEH/capita of built capital at ε = 0**
— a collective with an apparatus and no automation to justify it. That
contradicted ε's own definition (zero machine capital ⇒ ε = 0, which
`civilization_epsilon` already honoured) and made the autarky comparison report
the arc as overbuilt at the origin for a reason that was an artifact of one line.

The path is now `2.0B × (1 + slope) × ε`. **Only the intercept moved:** capital at
ε = 1 is still 3× the base, and at ε = 0.99 reads 5,940 TEH/capita against the
previous 5,960. That is why this cost 4 tests rather than the suite.

**A deliberate divergence to know about.** `effective_capital_from_epsilon` was
*not* changed, and the two now differ:

| | question it answers | at ε = 0 |
|---|---|---|
| `canonical_physical_state(ε)` | the ARC's capital *at* ε | **0** |
| `effective_capital_from_epsilon(base, ε)` | scale a **caller-supplied** ε=0 baseline | `base` |

The caller of the second is asserting that stock exists; zeroing it would destroy
their input rather than model anything. Same reasoning applies to
`total_eoh(epsilon=…)`, whose legacy path also treats `capital_stock` as a
supplied baseline — so `total_eoh(epsilon=0)` still shows infrastructure while the
CLI `arc`, which uses the canonical state, now shows 0.0. Pinned in
`test_trajectory.py` so the divergence stays deliberate rather than looking like
drift.

#### Two lower bounds, not one

A collective can be infeasible for two independent reasons, so the band's floor
is now the **max** over every supplied floor:

| floor | meaning of a breach |
|---|---|
| `survival` | the population cannot meet its obligation at all |
| `overbuild` | the apparatus costs members more hours than autarky — they should disperse, **not because they would die but because the collective is not worth being in** |

`corridor()` accepts either a bare float (backward compatible) or a list of
`Floor`, and names the binding one. `overbuild_floor()` is non-binding whenever
the obligation test already passes. Visible in `corridor band`, which grew a
Floors table and a `--capital-stock` argument.

#### The accounting basis

`total_eoh(..., basis="gross"|"final")`:

    total_base     = personal + ecological + civilisational knowledge
    total_overhead = infrastructure + apparatus knowledge
    gross          = base + overhead        (default, unchanged)
    final          = base

Infrastructure and apparatus knowledge are **intermediate** — the cost of the
service apparatus, not obligations a civilisation owes. Counting them in the
total is the same error as adding intermediate consumption to GDP. Both totals
are always reported, whichever basis is selected.

The conservation result, which is what motivated the whole line of work:

| | ε = 0 | ε = 0.99 | drift |
|---|---|---|---|
| gross | 1,550.7 | 1,705.3 | **+10.0%** |
| final | 1,475.7 | 1,480.9 | **+0.35%** |

The final basis is near-constant — population × per-person obligation — with the
residual drift coming from the elderly-fraction shift and the growing
civilisational corpus, not from the apparatus.

*One bug worth recording:* an early version put the basis label (a `str`) into a
`dict[str, float]`. mypy caught the type violation and four tests caught the
consequence — `isfinite` checks downstream broke on it.

---

### Abatement — infrastructure reduces the obligation, not only who serves it

*Added 2026-08-06 (Block II). `PERSONAL_EOH_COMPONENTS`, `ABATEMENT_HALF_CAPITAL_TEH`,
`core.eoh_generation.abatement_fraction()`, `core/autarky.py`.*

Before this the model had **substitution only**: personal EOH was flat across the
entire arc (1,475 → 1,480) and ε merely split who served it. That is physically
wrong — a serviced dwelling needs less upkeep than a mud hut, a tap replaces
hauling, and sanitation cuts the disease burden driving care hours.

    B(K) = F_a × (1 − a(K))        a(K) = a_max · K / (K + K_half)

**`a_max` is DERIVED, not chosen** — it falls out of the component weights, which
are the original desk estimate's own four terms:

| component | share | abatability | `resolves_by` |
|---|---|---|---|
| nutrition | 208/1508 | 0.85 | Food-system time-use across development levels |
| shelter | 156/1508 | 0.90 | **WHO/UNICEF JMP** water-and-sanitation access — measures hauling-time reduction directly |
| health | 208/1508 | 0.60 | GBD disease burden attributable to WASH → care hours avoided |
| care | 936/1508 | **0.25** | Childcare/eldercare time-use across development levels |

`a_max = Σ share·abatability = **0.4483**`.

Only one genuinely new free constant: **`ABATEMENT_HALF_CAPITAL_TEH` = 1,000**
TEH/capita, the *pace* of abatement, not its ceiling. It is the least-grounded
value in the block. `resolves_by`: the identity route run at two or more capital
levels — matched (inventory, time-use) pairs pin `a_max` and `K_half` together.
Report the sensitivity with any abatement figure until it does.

#### The anti-correlation prediction — tested, not assumed

Abatability and sufficiency run **opposite**: infrastructure removes the
survival-shaped work (hauling, gathering, preparing) and cannot remove care,
because a child needs human attention — the Baumol case. The residual at full
abatement is therefore **84.4% care**, which falls out of the weights rather than
being asserted. Pinned in `tests/test_autarky.py::TestAntiCorrelationPrediction`
so that changing the weights falsifies the prediction rather than silently
absorbing it.

#### Aggregate overbuild is now representable

Pre-Block-II, machine capacity and maintenance were **both linear** in K with a
fixed 4.08:1 ratio, so capital always paid and there was no interior optimum —
overbuild could only appear through the capital *mix* (`generic_infra` at 0.97).
Abatement **saturates** while overhead does not, so:

| K/capita | a(K) | B(K) | overhead | total | net vs autarky | verdict |
|---|---|---|---|---|---|---|
| 0 | 0.000 | 2,213 | 0 | 2,213 | 0 | **neutral** |
| 1,000 | 0.224 | 1,717 | 38 | 1,755 | +458 | pays |
| 4,145 | 0.361 | 1,414 | 155 | 1,570 | **+644 (optimum)** | pays |
| 25,448 | 0.431 | — | — | — | **0** | neutral |
| >25,448 | → 0.448 | — | grows linearly | — | negative | **overbuilt** |

There is an optimum apparatus size (~4,145 TEH/capita) and a size beyond which
more apparatus is pure overhead (~6.1× the optimum). The boundary at K=0 is
**neutral** — equivalent to autarky, not worse; strict inequality matters there.

#### Two tests, because they answer different questions

    obligation test   B(K) + I(K)  <  B₀        "all needs met effectively"
    labour test       (1−ε)·total  <  B₀        "worth being in"

A collective can pass the labour test and fail the obligation test — worth being
in, but only because automation is masking an apparatus that does not carry its
own weight. Both are reported for exactly that case. `break_even_epsilon()` is
the labour test's crossing and is a genuine **corridor lower bound**: below it a
collective should dissolve rather than operate.

*Implementation note worth keeping:* the crossing derives against **B₀**, not
B(K). Abatement makes those diverge, and deriving against B(K) reports a
break-even that is too high. A test caught it.

#### Temporary overbuild, made decidable

`payback()` integrates over an asset's design life instead of judging a single
period, so "overbuilt now, worth it over the life" is a claim that can be
checked. Both sides are in TEH-hours — the capital stock is denominated in
verified labour-hours — so `payback_years` reads as "years of saved labour to
repay the labour embodied in the apparatus". An apparatus that never pays back is
overbuilt in the sense that matters, whatever a single period says.

Run it: `python3 utils/eoh_cli.py scenario run overbuild`, or see the autarky
block on `dashboard`.

---

### The standards split — one constant was doing three jobs

*Added 2026-08-06 (Block I). `PERSONAL_EOH_SURVIVAL`, `PERSONAL_EOH_SUFFICIENCY`,
`core.eoh_generation.personal_base_for()`.*

Two **orthogonal** axes were conflated in a single `PERSONAL_EOH_BASE`:

|  | autarky delivery | collective delivery |
|---|---|---|
| **survival standard** | S_a | S_c |
| **sufficiency standard** | F_a | F_c |

STANDARD is what is owed; DELIVERY is what discharging it costs. **Abatement** —
infrastructure *reducing* the obligation rather than merely serving it — is the
map from the left column to the right, and it does not exist yet (Block II).

| Constant | Value | Meaning | Bound |
|---|---|---|---|
| `PERSONAL_EOH_SURVIVAL` | 600 | S_a — what must be met or people die | **Hard: ≤ (L−R)/w = 627.** A survival standard above labour supply is extinction. Set independently and *checked*, not pinned — a constant that cannot fail its own test says nothing. |
| `PERSONAL_EOH_SUFFICIENCY` | 1,500 | F_a — what a decent life costs alone | **None.** May exceed supply; that gap is why collectives form. |
| `PERSONAL_EOH_BASE` | 1,000 | the abatement-collapsed operating value, F_a × (1−a(K)) at an unstated point | Retired when Block II lands. 1,000 ≈ 1,500 × (1 − ⅓), and a ≈ 33% is mid-range between the 10% "all needs met" needs at ε=0.40 and the 38–74% the identity route implies at modern capital. |

**Block I moved no numbers.** The generation default is unchanged; the standards
are declared and selectable via `personal_standard=`. Defaulting to F_a would
assert *zero* abatement — exactly the simplification Block II exists to remove.

#### The category error this corrects

The earlier finding that "ε = 0 is not a feasible state" applied a **survival**
feasibility test to a **sufficiency** number:

| inventory standard | ε_suff |
|---|---|
| survival (600) | **0.00** — subsistence survives with no automation |
| operating (1,000) | 0.31 |
| sufficiency (1,500) | 0.53 |

All three are meaningful; only the first is a survival floor. The correct
statement is **subsistence can survive but cannot reach sufficiency without
automation** — which is what the historical record shows. `research/corridor.py`
gained `survival_inventory()` so the floor is computed at the right standard, and
`corridor band --standard` exposes all three.

#### Consumer audit — which standard each caller should use

| Consumer | Should use | Status |
|---|---|---|
| `corridor.survival_floor_epsilon` | **survival** | Fixed — `survival_inventory()`, CLI default |
| fiscal guarantee, `BASKET_EOH_CONTENT` | sufficiency | Uses `PERSONAL_EOH_BASE`; correct once it means F_a×(1−a) |
| `contestability` P (the exit-funding floor) | sufficiency | Same — the floor that funds exit is a sufficiency guarantee |
| `membership` min-hours thresholds | sufficiency | Same |
| `population`, `capital` per-capita loads | operating | Correct as-is |
| `total_eoh` generation default | operating | Correct as-is |

The three sufficiency consumers are *currently* reading the collapsed value,
which is right in magnitude but wrong in provenance — they will be re-pointed at
`F_a × (1−a(K))` when abatement lands rather than at the placeholder.

#### The knowledge split — no new constant

`knowledge_eoh_breakdown()` separates the domain into **civilisational** (the
corpus a civilisation renews whatever its capital) and **apparatus** (the cost of
knowing how to run the machines). The split derives from the existing functional
form and its existing rationale — `complexity_per_unit` is already documented as
automation-driven — giving `apparatus_fraction = 1 − 1/cpu`, which runs 0% at
ε=0 to 89.8% at ε=0.99. The apparatus component belongs in the collective's
*overhead* for the overbuild test; the civilisational component is a standing
obligation. **Scale caveat:** knowledge EOH is ~0.005% of total, so this split is
structurally right and numerically inconsequential until the domain bases are
commensurable.

---

### The feasibility ceiling — `PERSONAL_EOH_BASE` is over-determined

*Added 2026-08-06. `hours_eoh/scenarios/feasibility.py`; run it with
`python3 utils/eoh_cli.py scenario run feasibility`.*

An EOH demand is a claim about hours that must be worked, and at ε = 0 no machine
carries any of them. That gives a hard ceiling computable from constants the repo
already ships:

    supply  L = c · a                    c = adult capacity h/yr, a = adult share
    demand  D(ε) = (1 − ε)·[w·B + R]     w = 1.475, B = PERSONAL_EOH_BASE
    feasible ⇔ D ≤ L   ⇒   B ≤ (L/(1−ε) − R) / w

**The constant is not 1,500 per capita.** It is 1,500 per working-age-*equivalent*,
and the age weighting w = Σ(fraction × eoh_weight) = 1.475 makes the per-capita
claim **2,213 h/person·yr**. Because the extra weight on infants (3.0×) and
elderly (2.5×) is *caregiver* labour, all 2,213 hours must still be supplied by
adults — the weighting raises demand without raising supply. Any feasibility test
run against the 1,500 figure understates the gap by 1.475×.

**Self-consistency arm — no external data required.** Using only `H_REF` = 2,000
and `workforce_fraction` = 0.5 (the same 1e9-for-1M figure the corridor tests
pass as `available_labor_eoh`):

| | |
|---|---|
| supply | 1,000 h/person·yr |
| demand at ε = 0 | 2,288 h/person·yr |
| **ratio** | **2.29×** |
| implied ceiling on `PERSONAL_EOH_BASE` | 627 h/yr |
| overshoot | 2.39× |
| supply-side alternative | 4,576 h/yr per adult = 12.5 h/day, every day |

**Subsistence sweep.** Adult shares 0.55–0.60, adult capacities 1,200–2,600 h/yr
(the top of that band exceeds the modern 2,080-hour full-time reference, so the
result does not rest on a stingy labour budget): the ratio runs **1.47–3.47×**
and the implied ceiling **396–1,006 h/yr**. **No case in the sweep is feasible.**

**What this does and does not show.** It does not falsify 1,500 in isolation —
feasibility is a joint property. The finding is that the *pair*

> `PERSONAL_EOH_BASE` = 1,500  and  `H_REF` × `workforce_fraction` = 1,000

cannot both hold. Closing the gap on the supply side needs adults working
~10.5–12.5 h/day with no rest days, which no observed subsistence population
sustains, so the resolution has to come mostly from the demand side. On the
per-capita basis the compatible range is ≈ 1,000–1,300 h/person·yr, i.e.
`PERSONAL_EOH_BASE` ≈ **680–1,000** rather than 1,500.

**Consequence: ε = 0 is not a feasible state of this model.** The framework
documents ε = 0 as "subsistence"; its own arithmetic says subsistence requires
ε ≈ 0.58. `research/corridor.survival_floor_epsilon` has been reporting this all
along as ε_suff ≈ 0.53 (scoped to the personal domain alone) — the number was
visible, but it was read as a corridor bound rather than as a verdict on the
constant that produces it. Note also that the crossover is *later* than the naive
`1 − L/D(0)` = 0.563, because automation is capital and capital generates
infrastructure EOH: automation relieves demand and creates it at the same time.

Not fixed here. Changing `PERSONAL_EOH_BASE` moves ~95% of the ε denominator and
every downstream result with it; that is a calibration decision for the author.

### The circularity trap, and the route around it

*Added 2026-08-06 after the question was raised directly. This supersedes the
earlier note above that named ATUS as the resolving measurement — **ATUS alone
cannot resolve `PERSONAL_EOH_BASE`, and using it that way is the trap.***

**What is clean: the ε = 0 endpoint.** ε = machine_EOH / total_EOH, and at zero
machine capital the numerator is zero, so ε = 0 *whatever B is*. Verified: the
endpoint is B-free and an anchor society fixes it without circularity.

**What is not clean: the interior.** B is the scale factor of the entire ε axis.
At one fixed capital inventory (all-standard tier):

| B | total EOH h/p·yr | ε at that same capital |
|---|---|---|
| 500 | 813 | 0.327 |
| 900 | 1,403 | 0.189 |
| 1,500 | 2,288 | 0.116 |
| 2,500 | 3,763 | 0.071 |

A 5× change in B moves ε by 4.6× at unchanged physical capital. Every ε-indexed
result in the repo inherits that.

**The trap, precisely.** If B is calibrated from *observed hours worked*, then
demand is set equal to supply by construction — the demand/supply ratio is
1.000 identically, `feasibility_check` has no content, and ε_personal is forced
to 0. Observed hours are *fulfilled* EOH; B is *total* EOH. In a capital-rich
society ATUS measures the human residual (1 − ε)·D, not D — so an ATUS-derived B
would define ε ≡ 0 for the society you measured it in.

**The route around it — the accounting identity.**

    D = M + H          total obligation = machine-served + human-served
    D = w·B + R        the model's own decomposition
    ⇒ B = (M + H − R) / w     and    ε = M / (M + H)  as a BY-PRODUCT

This is non-circular because **M is B-free**: it comes from a capital inventory
scored against `CAPITAL_MACHINE_PROFILES` elimination rates, a different
instrument entirely. Two measurements, one unknown. Implemented as
`identify_base()`.

| capital tier | M h/p·yr | B @2.5 h/day | @2.8 | @3.2 |
|---|---|---|---|---|
| basic | 103 | 390 | 434 | 494 |
| standard | 266 | 500 | 544 | 604 |
| advanced | 741 | 822 | 867 | 926 |

**B = 390–926 — inside the feasibility band 396–1,006, from a completely
independent route.** Two methods that share no assumption converge on ≈400–1,000
and both exclude 1,500.

**The one residual assumption, and it inverts the intuition.** `D = M + H`
assumes every hour of obligation is served. If some is unserved, true
D = M + H + deficit, so the identity returns a **lower bound**. Therefore:

- the ε ≈ 0 anchor **fixes the endpoint** cleanly but is the **worst** place to
  measure B — its deficit is largest and least observable, paid in infant
  mortality rather than recorded in a diary;
- a **capital-rich society is the best place to measure B**, because its deficit
  is smallest. The opposite of calibrating a subsistence constant on subsistence
  data.

**What defending B = 1,500 requires you to assert.** Not an arithmetic error — a
deficit. At standard-tier capital, D = M + H + deficit gives **62% of the
personal obligation permanently unserved** (41% at advanced tier). That is a
substantive and possibly partly-true empirical claim about unmet care, deferred
health and social reproduction. It should be *stated and defended*, not carried
silently inside a constant. `feasibility_check` now returns `deficit_share` so
this third resolution is priced alongside the other two.

### The interior from the productivity route — and the test the framework lacks

Yes, the interior is buildable: ε(K) = M(K) / (w·B + R(K)) with B fixed by the
identity. And it is **overidentified**, which is the valuable part — fixing B
turns the human-hours residual into a *falsifiable prediction* at every capital
stock (`implied_human_hours()`):

    H(K) = w·B + R − M(K)

| B | basic | standard | advanced |
|---|---|---|---|
| 600 | 3.9 h/adult·day | 3.2 | 1.0 |
| 900 | 5.9 | 5.2 | 3.0 |
| **1,500** | **10.0** | **9.2** | **7.1** |

Cross-cultural time-allocation data measures exactly this. **B = 1,500 predicts
7.1 h/adult·day of entropy-resistance labour in an advanced-capital society**;
no time-use survey reports a figure near it. B ≈ 600–900 predicts days that are
in range. This is the first genuinely refutable claim the personal domain has
had — the multiplier's rank ordering is falsifiable, and until now nothing in
EOH generation was.

**A second use, sharper.** `core.eoh_fulfillment.human_eoh_per_domain` applies
(1 − ε) *uniformly across all four domains*. Run the identity per domain and any
disagreement in implied ε **falsifies that uniformity** — which is precisely the
ε-as-a-vector question (§12.1), so far argued on theory grounds and sign-off
gated. This converts it into a measurement.

### What repricing actually looks like

Lowering B raises ε everywhere at unchanged physical capital, because it shrinks
the denominator:

| B | total h/p·yr | ε at std capital | ×ε vs 1,500 | personal share | ε_feas | K needed for a target ε |
|---|---|---|---|---|---|---|
| 1,500 | 2,288 | 0.116 | 1.00 | 96.7% | 0.580 | 1.00× |
| 1,200 | 1,846 | 0.144 | 1.24 | 95.9% | 0.480 | 0.81× |
| 900 | 1,403 | 0.189 | 1.63 | 94.6% | 0.311 | 0.61× |
| 700 | 1,108 | 0.240 | 2.06 | 93.2% | 0.112 | 0.48× |
| 600 | 961 | 0.277 | 2.38 | 92.1% | 0.000 | 0.42× |

Consequences, in order of how much work they imply:

1. **Every ε-calibrated constant changes meaning, not just value.** The
   registration sigmoid inflections, `epoch_alpha_weights(ε)`,
   `canonical_physical_state(ε)`, the `CANONICAL_*` trajectory,
   `THERMAL_EPS_CURRENT`, the contestability channel crossovers
   (labour→underwritten→self), `formation` s\*(ε), and every corridor bound were
   all positioned against the old axis. A collective previously described as
   "ε = 0.12" becomes "ε = 0.28" without a single machine being installed.
2. **The feasibility defect resolves** at B ≲ 600 (ε_feas → 0), and ε = 0 becomes
   a state the model can actually represent.
3. **Domain balance does NOT resolve.** Personal share only falls 96.7% → 92.1%.
   These are two separate defects and fixing one leaves the other.
4. **Two mechanical hazards for whoever does it.** `params.py` exposes
   `personal_eoh_base`, but `p.temporary(personal_eoh_base=…)` **does not reach
   `total_eoh()`** — the function binds `PERSONAL_EOH_BASE` as an argument
   default at import, so a sweep silently changes nothing. And
   `core/population.py:462` uses the module constant directly rather than the
   parameter. Repricing means editing `data.py`, or first routing both paths
   through the parameter. The single most leveraged constant in the model is not
   actually sweepable today.

---

## EOH Generation — Infrastructure Domain

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `INFRA_MAINT_RATE` | 0.025 | fraction of capital stock / year | **CHOSEN** | OECD public-capital maintenance series gives the 2–4% band; 2.5% is a point picked inside it, so the band is evidence and the point is not. Note this constant sits on the *monetized* path that `scenarios/infrastructure_floor.py` shows is doctrine-dominated (10.26× spread); the statutory floor below exists to route around it. |
| `INFRA_AGE_FACTOR_MAX` | 2.0 | dimensionless multiplier | `physics` (convexity) / **CHOSEN** (magnitude) | That maintenance burden rises convexly toward end of design life is structural. That it exactly doubles is not — a condition-vs-crew-hours regression over NBI condition ratings joined to DOT maintenance timesheets would measure it. |
| `CAPITAL_STOCK_DEFAULT` | 2,000,000,000 | TEH (1 TEH = 1 verified labor-hour) | **CHOSEN** | National-accounts capital stock for the jurisdiction, converted at a stated money→hours convention (and see the determinacy warning above about that conversion). Default = 2,000 TEH/person for 1M people at ε=0; produces infrastructure EOH ≈ 75M h/yr at mid-life, ≈ 3% of total EOH. |

### Task-normative statutory floor (B+D design — currency-free)

The floor stream of `infrastructure_eoh_breakdown()`. These reprice the physical
condition census into hours **without** a money→hours conversion — the auditable
half. Motivated by `handoffs/Infrastructure`: the monetized `capital_stock_teh`
path moves 10× with the accounting doctrine and ×1.000 with every physical knob;
the floor moves only with the physical census (`scenarios/infrastructure_floor.py`
proves floor_spread = 1.000). 4-tag scheme with epistemic pointers:

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT` | 24.0 | months | measured | 23 CFR 650 routine inspection interval (regulation). |
| `INFRA_TREATMENT_HOURS_GOOD` | 8.0 | h/unit·yr | CHOSEN | State DOT maintenance-activity manuals / inspection timesheets give real per-condition crew-hours. |
| `INFRA_TREATMENT_HOURS_FAIR` | 20.0 | h/unit·yr | CHOSEN | (as above) — the fair-condition crew-hour rate is timesheet-measurable. |
| `INFRA_TREATMENT_HOURS_POOR` | 48.0 | h/unit·yr | CHOSEN | (as above) — poor-condition rate; the residual 1.69× determinacy gap is this tiering, and it is measurable, not conventional. |

---

## EOH Generation — Ecological Domain

> **Scale warning.** `ECOLOGICAL_BASE_RATE` is documented as a *relative* anchor
> ("does not represent an absolute ecosystem-specific count") but is summed with
> absolute counts in `total_eoh()` and then divided into ε. At defaults it
> contributes 0.71 h/person·yr against personal's 2,213 — 0.03% of total EOH. See
> [Domain balance](#domain-balance--the-denominator-problem). Until it is put on
> an absolute footing, no result that depends on the ecological domain's *share*
> of total EOH should be quoted.

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `ECOLOGICAL_BASE_RATE` | 500,000 | h/yr (at health=1.0) | **CHOSEN** | A stewardship-hours census: land-management agency staffing (e.g. national park/forest service FTEs per hectare), conservation-district labour returns, or the GUF layer's own parcel inventory converted at measured crew-hours. Needed on an ABSOLUTE footing, not as a relative anchor — that is the defect, not the value. |
| `ECOLOGICAL_THRESHOLD` | 0.40 | fraction (dimensionless) | `physics` (regime shift exists) / **CHOSEN** (0.40) | That ecosystems exhibit nonlinear regime shifts is established (Scheffer et al. 2009). That the shift sits at 0.40 of *this* health index is a framework mapping; an ecosystem-specific tipping-point assessment resolves it. |
| `_ECOLOGICAL_SPIKE_INTENSITY` | 5.0 | dimensionless spike multiplier | **CHOSEN** | Reverse-engineered from a target ("calibrated to produce an EOH doubling within ≈10% below threshold"), which makes it a knob by construction. Post-collapse restoration labour records would measure the true post-threshold slope. |

---

## EOH Generation — Knowledge Domain

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `KNOWLEDGE_EOH_BASE` | **490,107,421** (was 100,000) | hours — an embodied **STOCK** at `KNOWLEDGE_REFERENCE_POPULATION` | **derived-then-FROZEN** | **Closed 2026-08-08 (Block K-IV).** The pointer above named O\*NET/BLS training hours, and the registry already carried them: `f_training` is tagged "log-minmax of measured hours", so `hours = exp(lo + f·(hi−lo))` inverts it exactly. Employment-weighted mean **11,001 h/worker** over 751 occupations / 157.79 M employment → 5,501 h/person at E/P = 0.500 → ÷ kbs(0.40)·cpu(0.40) = 11.224. Frozen at O\*NET 30.3 / BLS epoch 2026-07-29, ε_ref = 0.40. `tests/test_knowledge_base.py` asserts the frozen value still matches the live derivation. **Residual uncertainty is the ANCHOR, not the measurement**: 7.13× across ε_ref ∈ [0.2, 0.6] vs 1.20× from the per-capita route. Sweep with `arc --knowledge-epsilon-ref`. |
| `KNOWLEDGE_REFERENCE_POPULATION` | 1,000,000 | persons | `convention` | The population `KNOWLEDGE_EOH_BASE` is quoted at. Exists because knowledge EOH was population-INVARIANT before Block K-I — the same absolute figure at 1M and 300M, so the domain's share fell as 1/population while every other domain scaled. A stated denominator, not a claim about the world. |
| `SKILL_TRANSMISSION_RATE` | 0.025 | 1/yr | `derived` | 1 / `SKILL_WORKING_LIFE_YEARS`. The stock is re-created as cohorts retire — knowledge dies with people, which is the entropy this domain measures (framing accepted by the author 2026-08-08). **The adopted default renewal rate.** |
| `SKILL_WORKING_LIFE_YEARS` | 40 | years | **CHOSEN** | BLS Employee Tenure / cohort exit rates. Weakly held but low-leverage: halving or doubling it moves transmission 2× against ε_ref's 7.13× lever. |
| `SKILL_CPD_RATE` | 0.0027 | 1/yr | **CHOSEN** | **Eurostat CVTS** (paid training hours per employee, all sectors) — the only public series that measures the recurring term directly. O\*NET structurally cannot: it measures the hours to REACH competency, never the hours to HOLD it. ~30 h/worker·yr against the 11,001 h stock. **Excluded from the shipped default** (see below), so no CHOSEN number rides in the adopted arc. |
| `KNOWLEDGE_EPS_EXPONENT` | 2.0 | dimensionless power | `physics` (superlinear form) / **CHOSEN** (exponent = 2) | That knowledge-maintenance complexity grows superlinearly in automation is the structural claim. The exponent's *value* is asserted; a complexity metric tracked against a measured automation index over time would fit it. |
| `skill_decay_rate` (param) | **0.025** (was 0.10) | fraction of the knowledge stock / year | `derived` (bound to `SKILL_TRANSMISSION_RATE`) | **Split and repriced 2026-08-08 (Blocks K-III/K-IV).** `SKILL_DECAY_RATE` = 0.10 was conflating two orthogonal rates: transmission (cohort turnover, derivable) and CPD (staying current, not in O\*NET). Set independently, they sum to **0.0277 against the shipped 0.10** — and against the measured 11,001 h/worker stock, 0.10 implies **1,100 h/worker·yr = 55% of the `H_REF` 2,000 h work-year, every year, forever**. No time-use or training series supports it; the shipped value was never a renewal rate. The author's decision (2026-08-08) was to adopt **the lower rate**: transmission alone, the only doctrine containing no CHOSEN component. This deliberately **understates** the renewal obligation by ~10.8% rather than let a judgement call ride in the shipped arc. |
| `SKILL_DECAY_RATE` | 0.10 | 1/yr | **DEPRECATED** (was CHOSEN) | Retained, not deleted — every pre-K-IV figure in this repo was produced at it, so reproducing one means passing it explicitly. Nothing defaults to it. |

---

## Domain balance — the denominator problem

*Added 2026-08-05. Updated 2026-08-08 after Block K-IV, and 2026-08-09 after the
Finding-E re-anchor. This is a property of the calibration set, not of any one
constant, and it conditions how every measured result in this repo should be
read.*

> **PARTLY CLOSED (Block K-IV, 2026-08-08; re-anchored 2026-08-09).** Putting
> `KNOWLEDGE_EOH_BASE` on its measured O\*NET/BLS footing cut the personal share
> from a flat 87–96% across the whole arc to 94.3% → 51.1%, and knowledge became
> the largest non-personal domain at the top. Re-anchoring the base to the ε_ref
> FIXED POINT (Finding E — the K-IV anchor was not a fixed point of its own
> derivation) took 0.779× off the base and gave back ~5 points at the top of the
> arc: the share now runs **99.3% → 56.2%**. The table below is the current
> picture; the pre-adoption figures are kept in the second table for comparison.
>
> **What is still open.** `ECOLOGICAL_BASE_RATE` was untouched and the
> ecological domain is still ~0.04% of total EOH at 0.71 h/person·yr — the
> "relative anchor summed with absolute counts" defect is unresolved. And
> personal still dominates the LOW arc (94% at ε=0), where there is no
> apparatus for knowledge to attach to, so `PERSONAL_EOH_BASE` and ATUS still
> own the denominator there. **Two of the three original consequences stand**:
> ε remains a personal-domain number at low ε, and the thermal obligation is
> still ~0.1% of the ledger.
>
> Reproduce with `python3 utils/eoh_cli.py arc --domain-shares`.

### Current (post-K-IV, re-anchored to the ε_ref fixed point)

Canonical-arc figures, `arc --domain-shares`:

| Domain | ε = 0 | ε = 0.40 | ε = 0.99 |
|---|---|---|---|
| personal | 99.3% | 88.6% | 56.2% |
| infrastructure | 0.0% | 5.0% | 8.5% |
| knowledge | 0.6% | **6.4%** | **35.3%** |
| ecological | <0.1% | <0.1% | <0.1% |

*The ε = 0 column reads 99.3% personal / 0.0% infrastructure because Block III
set the canonical capital path to zero at the origin — subsistence has no
apparatus, by ε's own definition. The legacy `total_eoh(epsilon=0)` path scales a
caller-supplied baseline instead and still shows infrastructure there; both are
intended and pinned in `test_trajectory.py`.*

*A CLI bug was fixed alongside: `arc` passed the corpus size `kbs` into the
base-RATE slot (`knowledge_base=`) while the actual kbs argument
(`knowledge_complexity=`) stayed at its 1.0 default, so the arc's knowledge
column had been under-reported by a factor of `KNOWLEDGE_EOH_BASE` for the whole
life of the command and never responded to the constant at all.*

### Pre-K-IV (retained for comparison)

ε is defined as machine-fulfilled EOH over total EOH. Running `total_eoh()` at
defaults for a population of 1M:

| Domain | ε = 0 | ε = 0.40 | ε = 0.99 | per person·yr (ε=0.40) |
|---|---|---|---|---|
| personal | 1,475,000,000 | 1,478,200,000 | 1,480,100,000 | 1,478 |
| infrastructure | 75,000,000 | 135,000,000 | 223,500,000 | 135 |
| ecological | 714,286 | 714,286 | 714,286 | **0.71** |
| knowledge | 10,000 | 112,240 | 973,251 | **0.11** |
| **personal share** | **95.1%** | **91.6%** | **86.8%** | |

*(At `PERSONAL_EOH_BASE` = 1,500 the personal share ran 96.7% → 90.8%. The
2026-08-06 reprice to 1,000 moved it to 95.1% → 86.8% — it did **not** fix the
imbalance, which is a separate defect from the feasibility one.)*

Three consequences, stated plainly:

1. **ε is ~90% a personal-domain number.** Whatever else is measured, the
   denominator is `PERSONAL_EOH_BASE` almost exclusively. This is why that
   constant's tag matters more than any other in this document.
2. **The measurement spine landed on the small domains.** The multiplier, the
   infrastructure statutory floor and the thermal layer are the most defensible
   work in the repo, and they act on domains totalling 3–9% of the denominator.
   That does not make them wrong; it means they cannot move ε much, and claims
   about ε should not be attributed to them.
3. **It hollows out the thermal obligation.** `research/thermal_solvency.solvency_at_epsilon(0.40)`
   books a thermal flow of 1.79M h/yr — **1.8 h/person·yr**, taking loaded
   ecological EOH to 2.5 against personal's 1,478. The planetary radiative
   obligation enters the ledger at roughly one part in a thousand of what the
   model already says people owe to entropy, and the accompanying "the fiscal
   system carries it with a 38× margin" verdict passes because the obligation is
   negligible, not because the fisc is strong.

Both candidate explanations are unresolved and both are `CHOSEN` inputs: either
the ecological/knowledge bases are low by two to three orders of magnitude, or
the thermal→EOH conversion is (`CDR_LABOR_HOURS_PER_TONNE` = 0.6, Tier D), or
both. Nothing in the current data settles it.

Reproduce with `python3 utils/eoh_cli.py arc --domain-shares`, or:

```python
from hours_eoh.core.eoh_generation import total_eoh
d = total_eoh(epsilon=0.40)
print({k: v / d["total"] for k, v in d.items() if k != "total"})
```

Regression-pinned in `tests/test_eoh_generation.py::test_domain_balance_*`.

---

## Retag log (2026-08-05)

Constants whose tag changed during the four-tag migration, with the reason. No
*values* changed — this is an evidence-labelling pass only, and every retag is
reversible by argument.

| Parameter | Was | Now | Why |
|---|---|---|---|
| `PERSONAL_EOH_BASE` | Physics | CHOSEN | Arithmetic sum of four desk estimates; no entropy-structural derivation. Directly measurable (ATUS). |
| `AGE_GROUPS` (eoh_weight) | Physics | CHOSEN | Direction is structural, magnitudes are asserted. |
| `AGE_GROUPS` (fraction) | Calibration | CHOSEN | Straight relabel under the new scheme. |
| `ELDERLY_EOH_EPSILON_FACTOR` | Calibration | CHOSEN | Straight relabel. |
| `INFRA_MAINT_RATE` | Physics | CHOSEN | Cites a 2–4% band and picks a point inside it. |
| `INFRA_AGE_FACTOR_MAX` | Physics | physics (form) / CHOSEN (2.0) | Convexity structural; the doubling is not. |
| `CAPITAL_STOCK_DEFAULT` | Calibration | CHOSEN | Straight relabel. |
| `ECOLOGICAL_BASE_RATE` | Calibration | CHOSEN | Relabel, plus the absolute-vs-relative scale warning above. |
| `ECOLOGICAL_THRESHOLD` | Physics | physics (form) / CHOSEN (0.40) | Regime shifts are established; this index's threshold is a mapping. |
| `_ECOLOGICAL_SPIKE_INTENSITY` | Physics | CHOSEN | Reverse-engineered from a target outcome. |
| `KNOWLEDGE_EOH_BASE` | Calibration | CHOSEN | Straight relabel. |
| `KNOWLEDGE_EPS_EXPONENT` | Physics | physics (form) / CHOSEN (2.0) | Superlinearity structural; the exponent is asserted. |
| `skill_decay_rate` | Calibration | CHOSEN | Straight relabel. |

Net effect on the CHOSEN count for the EOH-generation block: 13 constants now
carry an epistemic pointer where 6 previously claimed structural status. Four of
the thirteen resolve against one public dataset (ATUS) that the repo does not
yet use.

---

## Multipliers (Condition II)

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `M_BAND_LOW` | 1.8 | dimensionless multiplier | Physics | Lower bound of constitutional multiplier band. Below 1.8, the differential between labor tiers is too small to reflect real skill differentials. |
| `M_BAND_HIGH` | 2.1 | dimensionless multiplier | Physics | Upper bound and target mean. An economy-wide mean multiplier of 2.1 means the average worker creates 2.1 TEH per EOH registered — the "standard" skill premium consistent with the four-factor formula at calibrated alpha weights. Mission Statement §"Condition II." |
| `M_MAX` | 6.0 | dimensionless multiplier | Physics | Hard constitutional cap: no individual tier may exceed 6.0. Prevents extreme inequality in TEH accumulation; limits the additive formula output 1 + Σαᵢ·fᵢ ≤ M_MAX. |
| `ALPHA_SCALE` | 5.0 | dimensionless (sum of absolute alpha coefficients) | Physics | Σαᵢ = 5.0 is calibrated so that perfect scores on all four factors (T=D=S=I=1.0) yield m = 1 + 5.0 = 6.0 = M_MAX. Default equal distribution: each αᵢ = 1.25 at ε=0. |

---

## Registration Sigmas

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `CARE_SIGMOID_DEFAULTS` (start_share) | 0.30 | fraction | Calibration | At ε=0, 30% of care labor is on the collective ledger (subsistence: informal care dominates). |
| `CARE_SIGMOID_DEFAULTS` (saturation) | 0.95 | fraction | Physics | Maximum registration share: 95% of care labor can be collectively recognized even at ε=0.99. 5% remains informal. |
| `CARE_SIGMOID_DEFAULTS` (inflection) | 0.55 | ε value | Calibration | Care labor registration inflects at ε=0.55: early automation captures production first; care registration ramps up as middle-automation tools emerge. |
| Labor weights (care/production/stewardship) | 0.30 / 0.45 / 0.25 | fraction summing to 1.0 | Calibration | Non-personal domain registration share is a weighted composite of care, production, and stewardship registration rates. Default weights reflect a service-economy labor mix. |

---

## Fiscal Parameters

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `SUFF_LEVY_RATE` | 0.0125 | fraction of labor income | Calibration | 1.25% sufficiency levy on all TEH earnings. At ε=0.40 canonical: levy_inflow ≈ 6.2M TEH/yr on 494M TEH labor income. Does NOT cover the sufficiency guarantee alone (307M TEH) — the Trust dividend fills the gap. Calibrated to be non-burdensome while building Trust reserves. |
| `TRUST_BASE_TEH` | 35,000,000,000 | TEH | Calibration | Default Trust balance for 1M population = 35,000 TEH/person. Sized so that the annual dividend (Trust × dep_rate × div_rate = 35B × 4.5% × 40% = 630M TEH) covers stewardship + ecological + guarantee obligations at mid-arc. This is the critical calibration knob for fiscal solvency. |
| `DEP_RATE` | 0.045 | fraction of Trust / year | Physics | Trust capital depreciates at 4.5%/year: the same physical capital it represents deteriorates. Combined with div_rate to split depreciation into dividend (circulated) vs. renewal (retained). |
| `DIV_RATE` | 0.40 | fraction of annual depreciation | Physics | 40% of annual Trust depreciation is paid out as dividend (circulated to holders); 60% is retained for Trust renewal. Interaction: annual_dividend = Trust × dep_rate × div_rate; annual_renewal = Trust × dep_rate × (1 − div_rate). Together: Trust erodes unless levy_inflow replaces the net. |
| `MEANINGFUL_ACTIVITY_TEH_BASE` | 120.0 | TEH/yr per recipient (at ε=0) | Calibration | Discretionary spending bonus in the sufficiency guarantee at ε=0. Provides non-participant purchasing power beyond biological EOH reimbursement. Also used as the sufficiency basket cost at ε=0 (basket_price(0) = 120 TEH/yr). |
| `MEANINGFUL_ACTIVITY_TEH_SCALE` | 1.5 | dimensionless quadratic coefficient | Calibration | meaningful_activity bonus = base × (1 + 1.5 × ε²). Quadratic growth ensures non-participants gain real purchasing power as the labor pool shrinks at high ε. At ε=0.70: bonus = 120 × (1 + 1.5 × 0.49) = 208 TEH/yr. |

---

## Labor Parameters (Condition IV)

| Parameter | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `H_REF` | 2,000 | h/yr | Calibration | Reference full-time work-year (50 weeks × 40 h). Used to normalize workforce-hours to TEH. |
| `H_MIN` | 260 | h/yr | Physics | Minimum annual labor obligation (Condition IV): 5 h/wk × 52 wk. Below this, a worker is not maintaining competency in their domain — knowledge EOH is unmet. |
| `COMPETENCY_THRESHOLD` | 0.155 | fraction | Physics | Minimum certified-worker fraction per essential domain. Below this, the domain is at competency risk: knowledge EOH demand amplifies and emergency registration protocols may activate. |
| `CAPITAL_FAILURE_RATE` | 0.005 | fraction of capital / year | Calibration | Fraction of capital stock that fails catastrophically each year (beyond recoverability), triggering TEH destruction (D1). Default 0.5%/yr with better monitoring at high ε slightly reducing failure rates. |

---

## Canonical Trajectory Constants (data.py `CANONICAL_*` prefix)

These define the ideal-arc reference. A real simulation diverges from this arc;
canonical_physical_state(ε) is for testing and cross-sectional analysis only.

| Constant | Value | Governs |
|---|---|---|
| `CANONICAL_CAPITAL_GROWTH_SLOPE` | 2.0 | capital_stock = 2B × (1 + 2ε) — automation requires capital investment |
| `CANONICAL_CAPITAL_AGE_DRIFT` | 0.20 | capital_age_ratio = 0.30 + 0.20ε — older assets on average as stock grows |
| `CANONICAL_ECOSYSTEM_HEALTH_BASE` | 0.90 | ecosystem_health = max(0.01, 0.90 − 0.20ε) — slight degradation under productivity pressure |
| `CANONICAL_ECOSYSTEM_HEALTH_DRIFT` | −0.20 | (see above) |
| `CANONICAL_MONITORING_CAPABILITY_BASE` | 0.50 | monitoring_capability = 0.50 + 0.50ε — improving sensing technology |
| `CANONICAL_MONITORING_CAPABILITY_SLOPE` | 0.50 | (see above) |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE` | 9.0 | knowledge_base_size = 1 + 9ε; complexity_per_unit = 1 + ε² × 9 |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_EXP` | 2.0 | (quadratic complexity growth — see knowledge_base_size formula above) |

---

## Contestability Parameters (Workstream B — `research/contestability.py`)

Added to support the contestability instrumentation (originally the bare
invariant χ(ε) = P(ε)/K_entry(ε) ≥ 1, since superseded by the §8.9
time-to-finance/two-arm form — see the Recalibration and §8.9c sections
below; the χ machinery remains as documented negative results).
See `hours-reconciliation.md §8` and `notes/workstream b.md` for derivation.

| Constant | Default | Units | Kind | Source / Derivation |
|---|---|---|---|---|
| `CONTESTABILITY_K0_TEH` | 1,800 | TEH/person | Calibration | Entry cost of founding a viable alternative collective at ε=0. Calibrated to ≈ 1.2× the annual sufficiency guarantee per person — the minimum capitalization for a collective to function. |
| `CONTESTABILITY_K_SLOPE` | 1.6 | fraction per ε unit (increasing_returns regime) | Calibration | In the adversarial increasing_returns regime, K_entry = K₀ × (1 + 1.6ε). At ε=0.99: K_entry = 1,800 × 2.584 = 4,651 TEH/person. Calibrated so that K_entry grows at roughly the rate automated capital appreciates. |
| `CONTESTABILITY_K_FLOOR_FRACTION` | 0.10 | fraction of K₀ | Physics | In the replicable regime, K_entry cannot fall below 10% of K₀ (180 TEH/person): there is always some minimum founding cost. |
| `CONTESTABILITY_CHI_CRIT` | 1.00 | dimensionless | Physics | χ < 1 means exit is notional, not substantive — the contestability invariant is breached. |
| `CONTESTABILITY_CHI_WARN` | 1.20 | dimensionless | Calibration | Early-warning threshold: χ < 1.20 triggers a yellow flag in the dashboard (χ eroding toward breach). |
| `CONTESTABILITY_PHI_FLOOR` | 0.10 | fraction | Physics | Minimum commonized fraction at ε=0: even at subsistence, 10% of automation value is held in common (Trust baseline). φ(ε) = 0.10 + 0.90 × ε^1.5 → φ(0.99) ≈ 0.996. |
| `CONTESTABILITY_PHI_EXPONENT` | 1.5 | dimensionless power | Calibration | Sub-linear growth of commonization in early arc (ε^1.5 rather than ε) ensures a gentle ramp — political economy constraints make rapid commonization difficult. |
| `CONTESTABILITY_G_PRIV` | 0.03 | fraction / year | Calibration | Private capital growth rate (g_priv): 3%/yr real. The Piketty-inversion condition requires dτ/dε ≥ 0, i.e., Trust must grow faster than private capital. At canonical defaults, the levy-alone path is infeasible (levy_fraction >> 1) — the adversarial finding (reconciliation §8.3). |
| `CONTESTABILITY_CAPITAL_YIELD_RATE` | 0.10 | fraction / year | Calibration | Automated capital yield rate: 10%/yr. Used to compute automated_output_teh = ε × capital_stock × yield for the Piketty-inversion levy calculation. |
| `CONTESTABILITY_VESTING_YEARS` | 5.0 | years | Calibration | Years of **federation** tenure for the Trust dividend to fully vest (linear vesting), used by `portable_endowment_individual()` and `portable_endowment_federated()`. Tenure is federation-wide (reconciliation §8.7b): moving between collectives never resets the clock or forfeits vested balance. Matches the 5-year tier-reassessment cadence (`TIER_ASSESSMENT_INTERVAL_YEARS`). The sufficiency floor never vests — it is membership-independent (reconciliation §8.1). A pure calibration knob: shorter vesting strengthens the marginal member's χ. |

## Coasean Federation Parameters (Workstream D / Phase 3 — `research/coasean.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `COASEAN_N_MAX` | 20 | collectives | Calibration | Collective count at ε=0 (maximally fragmented). A working hypothesis from reconciliation §6, not derived from institutional data — the real count depends on governance, geography, and transaction-cost structure. Calibration knob, not physics. |
| `COASEAN_BOUNDARY_EXPONENT` | 1.0 | dimensionless | Calibration | Exponent in N(ε) = max(1, round(N_max × (1−ε)^exp)). Linear default: collective count consolidates in proportion to automation. Higher values front-load consolidation. |
| `COASEAN_RESERVE_FRACTION` | 0.10 | fraction of TEH created | Calibration | Share of each collective's period TEH creation held as inter-collective reserve, consumed by `settlement_check()` for imbalance settlement. Analogous to a central-bank FX reserve ratio. |
| `COASEAN_IMBALANCE_CEILING` | 0.50 | fraction of debtor reserve | Calibration | Bilateral net-flow credit ceiling (paper's bilateral-imbalance-ceiling sketch, reconciliation §9-item-4). Within it, trade continues on credit; beyond it, settlement from reserve is required. |
| `COASEAN_DEPRECIATION_SLOPE` | 0.20 | dimensionless | Calibration | Exchange-rate depreciation per unit of unsettled imbalance beyond the ceiling: factor = 1/(1 + slope × excess_ratio). Makes over-issuance a visible exchange-rate movement (reconciliation §7 transition regime). Proposed functional form, not calibrated from data. |
| `COASEAN_COMMONS_TITHE` | 0.03 | fraction of levy revenue | Calibration | Fraction of each collective's common-fund levy revenue passed up to the federation commons (reconciliation §8.7a). Precedent: Italian Law 59/1992 requires cooperatives to contribute 3% of annual surplus to the mutualistic funds — the only real-world calibration point for a federation-level mutual levy. |
| `COASEAN_INDIVISIBLE_RESERVE_FRACTION` | 0.30 | fraction of collective trust | Calibration | Unallocated (indivisible) share of a collective's trust — credited to no individual capital account; escheats to the federation commons on merger/split/dissolution (reconciliation §8.7c). Precedent: Italian co-op law's statutory ~30% indivisible legal reserve. The model tracks no individual accounts, so a named constant is the minimal honest allocated/unallocated split — a tenure-derived fraction would be false precision. |
| `CONTESTABILITY_MIN_VIABLE_POPULATION` | 5,000 | persons | Calibration | Smallest population able to staff a viable alternative collective: the four-domain EOH pipeline with a full age distribution and a governance quorum (proposed §8.8 M2). UNCALIBRATED research placeholder, deliberately far below Coasean-efficient scale — a viable alternative need only clear minimum scale; requiring optimal scale would make the entry threat vacuous at high ε. |
| `CONTESTABILITY_UNDERWRITE_FRACTION` | 0.50 | fraction of commons | Calibration | Maximum share of the federation commons deployable per period as entry underwriting (proposed §8.8 M2); the remainder stays as the sufficiency-floor backstop (§8.7a). Underwritten capital moves commons → new collective trust, staying commonized and indivisible (§8.7c). |

## Recalibration Prototype (proposed §8.9 — `research/recalibration.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `RECAL_CAPITAL_OUTPUT_RATIO` | 4.0 | years (K per unit annual output) | Calibration | ν in K(ε) = K₀ + ν·Y(ε): capital stock required per unit of annual machine output. Precedent: Piketty's β (national capital / national income) ≈ 4–6 across observed economies; the low end is the adversarially-cheap-capital posture (a smaller commons weakens the underwriting arm). Fixes §8.8 open item 3 at the root — the old frame held an ε=0-era stock fixed while ε rose, giving τ = 17.5 for a quantity defined as a share ≤ 1. |
| `RECAL_EPSILON_RATE_PER_YEAR` | 0.02 | ε per year | Calibration | Arc speed dε/dt — a ~50-year subsistence→post-scarcity transition. UNCALIBRATED placeholder; converts per-ε acquisition needs into per-year flows, and faster arcs tighten acquisition feasibility linearly. |
| `RECAL_FOUNDING_LABOR_HOURS` | 1,000 | hours/year | Calibration | Hours per year a floor-backed founder can devote to building an alternative collective (≈ 2/3 of `PERSONAL_EOH_BASE`). The sufficiency floor is what frees this labor — the floor is the entry finance of the low-ε arc. UNCALIBRATED placeholder. |
| `RECAL_EXIT_HORIZON_YEARS` | 5.0 | years | Calibration | Self-financing horizon: exit must be financeable within one vesting period (= `CONTESTABILITY_VESTING_YEARS`). This is the RC4 fix — a stock target against a flow yields a TIME; the retired χ = P/K_entry demanded the founding stock be covered by one year of income. |
| `RECAL_ACCOUNT_CREDIT_SHARE` | 0.50 | fraction of dividend | Calibration | Share of the annual per-capita dividend credited to the member's individual capital account (§8.7b) rather than paid as cash. Zero-interest per Condition III: the account is a sum of credits, never compounded. Precedent: Mondragon internal capital accounts. |
| `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE` | 0.15 | fraction of capital estate | Calibration | Share of a decedent's private capital escheating to the commons (§8.9b, B4). Set equal to `ESTATE_LEVY_FRACTION`: capital estates treated exactly like TEH estates — the existing D5 doctrine extended to capital, not a new rule. No living holder is ever divested; conversion happens at mortality speed. |
| `RECAL_ESCALATION_ESTATE_SHARE` | 1.0 | fraction of capital estate | Calibration | Capital-estate escheat share while a §8.9b charter escalation is active: full generational conversion (Piketty's inheritance-tax instrument). Even at 1.0 the private-capital half-life is ≈ 69 years at the 1%/yr death rate — φ → target is asymptotic over generations; the exit invariant never depends on reaching it. |
| `RECAL_ESCALATION_CAPACITY_FLOOR` | 10.0 | foundings financeable | Calibration | Entry-underwriting capacity below which the charter escalates (with the adversarial regime observed): the commons must always be able to finance an order of magnitude more foundings than one. UNCALIBRATED placeholder; at canonical defaults capacity stays ≈ 145–280 and the trigger never fires. |
| `FORMATION_DEPRECIATION_RATE` | 0.05 | per year | Calibration | Aggregate annual depreciation of machine capital (§8.9c) — the aggregate counterpart of the per-asset lifecycle in `core/capital.py`, derived from `CAPITAL_MACHINE_PROFILES` design lives (≈ 20 yr → δ ≈ 1/20). Sets the gross return on capital 1/ν − δ = 0.20 and the commons replacement cost δ·T_K (a ≈ 20–24% haircut on the gross dividend). |
| `FORMATION_HURDLE_RATE_MIN` | 0.02 | net return per year | Calibration | Net private return below which no private capital formation occurs (§8.9c). Low BECAUSE of Condition III: idle TEH earns zero interest and leaks via the accumulation ceiling (D6) and estate dissolution (D5), so only risk compensation remains. UNCALIBRATED placeholder; raising it toward fiat-like levels is the Condition III counterfactual. |
| `FORMATION_FULL_SUPPLY_RATE` | 0.10 | net return per year | Calibration | Net private return at which formation demand is fully supplied (linear supply between the two rates — heterogeneous hurdle rates). Implies the incentive-compatible charter share s* = 1 − 0.10/0.20 = 0.50; a fiat-like 0.18 gives s* ≈ 0.10. UNCALIBRATED placeholder. |

## Membership-Terms Audit Thresholds (reconciliation §8.7e — `research/membership.py`)

| Parameter | Value | Units | Type | Source / Derivation |
|-----------|-------|-------|------|---------------------|
| `MEMBERSHIP_VESTING_WARN_YEARS` | 10.0 | years | Calibration | Vesting beyond 2× `CONTESTABILITY_VESTING_YEARS` → WARN: a dividend held hostage for a decade thins the marginal member's exit without formally breaching χ. |
| `MEMBERSHIP_EXIT_NOTICE_WARN_YEARS` | 1.0 | years | Calibration | Exit notice beyond one year → WARN (exit friction accumulating). |
| `MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS` | 3.0 | years | Calibration | Notice beyond three years → CRIT: exit deferred that long is nominal, not substantive (reconciliation §8.1) — the term itself breaches the invariant regardless of χ arithmetic. |
| `MEMBERSHIP_MIN_HOURS_WARN_FRACTION` | 0.50 | fraction of `PERSONAL_EOH_BASE` | Calibration | Minimum-hours obligation above half the personal entropy load (750 h/yr) → WARN (§9-item-7: membership rules must not be drawn so tight they destroy χ). |
| `MEMBERSHIP_MIN_HOURS_CRIT_FRACTION` | 1.00 | fraction of `PERSONAL_EOH_BASE` | Physics-adjacent | Obligation at or above the full personal EOH load (1500 h/yr) → CRIT: an obligation equal to the whole entropy load is compulsion by definition, not a membership term. |
| `MEMBERSHIP_DIVIDEND_POLICY_WARN` | 0.25 | fraction of pro-rata dividend | Calibration | Distributing less than 25% of the pro-rata dividend to accounts → WARN: retention rebuilds the honeypot (undistributed commons) inside the collective that the indivisible-reserve escheat rule exists to defuse. |

---

## Reference Multiplier (measured — O*NET 30.3 / BLS, mult-5.1.0)

The multiplier prices **one hour of labour** and sets the **floor at which TEH is
minted** — not realized earnings (a discovered market premium sits on top;
reconciliation §3). All four assessment factors are **measured** from public
survey data; the map that turns them into a multiplier is **derived-then-frozen**.

**Read `handoffs/multipliers-v5/FALSIFIABILITY.md` before citing any number.**
The rank ordering and pairwise ratios are measurements (falsifiable against
source data); the absolute range, global spread ratio and band pass are
construction artifacts of the normalization choice (±2.8× swing across
normalizations) with no empirical content. `scenarios/multiplier_sensitivity.py`
quantifies both — run `eoh multiplier sensitivity`.

### Measured factors and the geometric map

| Parameter | Default | Kind | Source / Derivation |
|---|---|---|---|
| `f_training`, `f_demand`, `f_scarcity`, `f_impact` | per-occupation, ∈[0,1] | measured / derived | O*NET 30.3 education+training (T), abilities/skills/work-context burden (D), BLS EP openings+growth (S), O*NET+BLS impact sub-components (I). 751 occupations, 94.2% of US employment. Loaded via `hours_eoh.reference.onet_multipliers`. |
| `M_FLOOR` | 1.0 | CHOSEN (constitutional) | Constitutional floor multiplier. Resolves only by a charter decision on the floor. |
| `M_GEOMETRIC_R` | 3.2 | derived-then-FROZEN | Spread ratio, solved once from {floor, band, measured composite} at the reference epoch. Not a knob — re-derivation per vintage restores the circularity the freeze breaks. |
| `M_COMPOSITE_Z_LO`, `M_COMPOSITE_Z_HI` | 0.153, 0.740 | derived-then-FROZEN | Frozen composite normalization range for `z = clip((c−z_lo)/(z_hi−z_lo),0,1)`. |
| `M_IMPACT_COMPOSITE_LO/HI` | 0.332, 0.752 | derived-then-FROZEN | Frozen affine outer-normalization bounds for the impact composite (makes stated sub-domain weights operative; rank-preserving). |

The map: `composite = Σ wᵢ·fᵢ`; `m = M_FLOOR · M_GEOMETRIC_R ** z`. It has **no
free parameters** — floor constitutional, R and z-range derived-then-frozen,
curvature deleted (`core/multipliers.py:reference_multiplier`).

### CHOSEN constants — each with its epistemic pointer

Every remaining CHOSEN carries the evidence that would resolve it. Full list with
sweep ranges in the CSV; the load-bearing ones:

| Parameter | Default | Epistemic pointer (`resolves_by`) |
|---|---|---|
| `M_FACTOR_WEIGHTS` | (0.30, 0.25, 0.20, 0.25) | External anchor (an occupation-pair ratio asserted on other grounds) or a stated distributional target the measured data could fail. Sensitivity harness bounds the exposure: rank ordering robust (Spearman ≳0.97 under ±0.10), band is convention. |
| `M_EPOCH_WEIGHT_ANCHORS` | 4 ε-anchor vectors | Governance judgement on which leverage matters as ε rises; the ε→1 impact-only limit is theory (copy/merge degeneracy, `KNOWN_ISSUES §5`), not measurement. |
| `M_IMPACT_SUBDOMAIN_WEIGHTS` | (0.30, 0.25, 0.25, 0.20) | An outcome study linking dependency/substitutability/harm/temporal to measured entropy-reduction would calibrate the split. |
| `scarcity_leg_weights` | O 0.667 / G 0.333 | Add the vacancy leg V (JOLTS by SOC, economy-wide) and fit O/G/V from realized time-to-fill. |
| `substitution_tier_weights` | 1.0 / 0.6 / 0.3 | Observed cross-occupation transition rates (BLS mobility / longitudinal survey). |
| `temporal_activity_lists` | 5 persisting / 3 transient | An output-half-life measure (how long the work's product persists) would replace hand-picked activity lists. |
| `epsilon` | 0.40 | Measure ε = machine_EOH / total_EOH from capital stock (`civilization.py`) — then ε is *observed*, not chosen. |
| `band` scope | [1.8, 2.1] | Resolve whether it binds the minted floor or realized compensation; the band is near-non-discriminating (a convention). A distributional target the data could actually fail would replace it. |

### Not yet available (tag: planned)

`vacancy_leg_V` (JOLTS by SOC), `abandonment_rate` (longitudinal exit-without-
onward-destination — an audit trigger, not a multiplier input), `time_to_harm_speed`
(no dataset exists), `ai_exposure_machine_leg` (per-occupation Iceberg Index).
These are the model's honest data debts.

---

## Thermal Sink EOH — planetary radiative budget (research/thermal.py, P0)

The uncounted vector: degraded energy exits only by radiation to space, and that
capacity is fixed and non-restorable by labour
(`handoffs/Thermal_Sink_EOH_Implementation_Handoff_1_0.md`). P0 computes the
provable automation-ceiling bound (E29 / finding F2) — advisory-only, generates
no obligation. Two provenance tiers, kept explicit:

| Parameter | Default | Units | Kind | `resolves_by` (epistemic pointer) |
|---|---|---|---|---|
| `A_EARTH_M2` | 5.101e14 | m² | physics | Earth surface area. |
| `SIGMA_SB` | 5.6704e-8 | W·m⁻²·K⁻⁴ | physics | Stefan–Boltzmann constant. |
| `SECONDS_PER_YEAR` | 3.1558e7 | s | physics | Δt_s for a one-year period. |
| `THERMAL_LAMBDA_FEEDBACK` | 1.2 | W·m⁻²·K⁻¹ | CHOSEN | Climate assessment (IPCC-class); Planck-only ≈ 3.2. Corridor **sign** is highly sensitive to this — §10.2 robustness. |
| `THERMAL_F_GHG` | 3.0 | W·m⁻² | CHOSEN | Anthropogenic GHG forcing assessment (AR6 order). Lowering it raises the budget (F3: decarbonization ↔ automation headroom). |
| `THERMAL_DT_LO` | 2.0 | K | CHOSEN | Habitability-threshold assessment (low end). §8 requires a range spanning ≥2×; the sign sensitivity across it is the P0 finding, not this point value. |
| `THERMAL_COMMONS_RESERVE` | 0.20 | fraction | CHOSEN | Governance; ratcheted down only. |
| `THERMAL_ANTHROPOGENIC_DISSIPATION_W` | 2.0e13 | W | measured | Present Φ_other reference (~0.04 W·m⁻²); energy-balance inventory. |
| `THERMAL_IOTA_FLOOR_*` (4 domains) | 3.6e5 / 3.6e5 / 3.6e4 / 1e-6 | J/EOH | CHOSEN | Thermodynamic floors ι_floor,d: Landauer (knowledge), Carnot/enthalpy (infrastructure), caloric+COP (personal). The gating uncertainty — the J/EOH mapping is unmeasured; measured ι via handoff §13.1 ladder D→C→B retires these. |

**Honest P0 result.** At non-degenerate constants the floor-based bound comes back
ε_max ≫ 1 → **INCONCLUSIVE**: the thermodynamic floor is too low to bind
automation. A floor bound can only overstate ε_max, so a bound < 1 would be
conclusive (F2) — but it does not bind, which correctly points to the measured-ι
ladder (path C) as the binding question, not a constant change. The only
"binding" corner is UNBUDGETED (ψ*=0), driven by GHG forcing exhausting the
allowance — an F3 statement about decarbonization, not automation intensity.

### Path C — measured top-down thermal residual (research/thermal_path_c.py)

The measurement that resolves the P0 "INCONCLUSIVE" bound into a concrete answer,
via the operative formula ε_max = ε_current · allocated_budget / Φ_auto (ι and
EOH_total cancel — no EOH register needed). Measured energy mix, κ table, forcing
and national records ship in [`reference/data/thermal_path_c.json`](../hours_eoh/reference/data/thermal_path_c.json)
with per-input provenance tiers (A retrieved / B constant / C training-data-unverified
/ D framework placeholder) — **the weakest data drives the strongest finding, so
read the tiers before citing.** Structural constants added to `data.py`:

| Parameter | Default | Units | Kind | `resolves_by` |
|---|---|---|---|---|
| `A_LAND_CLAIMED_M2` | 1.35e14 | m² | physics | land ex-Antarctica; the ψ* denominator. |
| `THERMAL_F_NET_ERF` | 3.366 | W·m⁻² | measured (Tier A) | IGCC 2025a total ERF at 2025 — the **budget** basis per C4 (natural forcing consumes habitability regardless of cause). Verified 2026-08-03. |
| `THERMAL_F_NET_ERF_P05` / `_P95` | 2.602 / 4.102 | W·m⁻² | measured (Tier A) | IGCC 2025a p05/p95. The band is what makes the determinacy map computable. |
| `THERMAL_F_ANTHRO_ERF` | 3.104 | W·m⁻² | measured (Tier A) | IGCC 2025a anthropogenic ERF — the **removable** forcing, hence the defensible F3 gain basis (sign-off item). |
| `THERMAL_F_WMGHG_ERF` | 3.585 | W·m⁻² | measured (Tier A) | IGCC 2025a well-mixed GHG ERF (forward-looking basis as aerosol cooling declines). |
| `THERMAL_DT_LO` | 2.0 | K | **CHOSEN** | The single most leveraged input in the thermal layer — it sets the overage, the drawdown job and the obligation. Adopted because it keeps results stable and sits inside the indeterminate band, **not** because it is assessed; may well be judged too high later, and every downward revision *enlarges* the obligation (1.5 K ≈ 1.5× the job). Assess in land extremes, convert by ÷1.48 (C6). |
| `THERMAL_PROGRAMME_YEARS` | 40 | years | **CHOSEN** | Horizon over which the drawdown obligation is discharged. 40 yr keeps it inside a single lifetime of responsibility: the generation that incurred the debt does the work rather than willing it forward. Obligation scales as 1/horizon (30 yr = 1.33× the annual load). An **ethical** choice, not a technical one. |
| `CDR_ALLOCATION_BASIS` | `"responsibility"` | — | **CHOSEN** | How the global job splits across collectives. Responsibility (cumulative emissions) over population, because a collective cannot burden others with the consequences of its own choices. Resolved 2026-08-05 against [`reference/data/cumulative_emissions.json`](../hours_eoh/reference/data/cumulative_emissions.json) (OWID / Global Carbon Budget, **1750–2024**, 215 collectives). Falls back to population **and declares the fallback** for an unknown collective. Effect: the US owes 4.8× its headcount share, Bangladesh 0.06× — ~80× per-person spread. |
| `CDR_UNATTRIBUTED_POLICY` | `"pro_rata"` | — | **CHOSEN** | What happens to the 46 GtCO₂ (2.49%) of shipping and aviation belonging to no territory. Pro-rata redistribution normalises shares to sum to 1, so no part of the obligation lacks a bearer. `"unallocated"` returns raw shares and lets the commons absorb the gap. resolves_by: consumption-based allocation, 1990 forward. |
| `CDR_RESPONSIBILITY_BASIS` | `"incl_luc"` | — | **CHOSEN — decided** | Which cumulative measure weights responsibility. `incl_luc` (fossil + cement + land-use change) matches the physical target — the drawdown removes the whole atmospheric burden, and the forcing coefficient was fitted to a concentration record that already reflects land use. `fossil` has lower uncertainty but leaves ~33% unallocated. Decided 2026-08-05: land converted inside a collective is that collective's, whatever demand motivated it. It roughly quintuples Brazil's share and cuts the UK's by a third — a real argument, recorded for live implementations rather than resolved by the model. |
| `CDR_ENERGY_GJ_PER_TONNE` | 4.0 | GJ/tCO₂ | measured (Tier C) | DAC-order, recalled range 2–6. **Does not affect the EOH obligation at all** — the energy term cancels out of it (EOH = gross tonnes × labour-hours/tonne); it drives only the programme's own dissipation. |
| `CDR_LABOR_HOURS_PER_TONNE` | 0.6 | h/tCO₂ | **CHOSEN (Tier D)** | The one number the obligation actually rests on. ~1 Mt/yr plant at ~300 staff × 2000 h. Together with the line above it *derives* ι_drawdown ≈ 6.7e9 J/EOH. resolves_by: operator staffing disclosures. Gate margin: the Trust gives way at 22.9 h/t, 38× this value. |
| `CDR_GROSS_REMOVAL_FACTOR` | 1.8 | — | **CHOSEN (Tier D)** | Sink reversal: removing CO₂ lets ocean/land outgas back, so tonnage processed exceeds the concentration drop. Omitting it understates the obligation ~2× and biases the solvency gate toward passing. resolves_by: ESM CDR reversibility experiments. |
| `CO2_FORCING_COEFFICIENT` | 5.645 | W·m⁻² per ln(C/C₀) | measured (Tier A) | **Derived** by OLS on the IGCC 2025a CO₂ ERF series over 350–426 ppm (n=38) — the range a drawdown traverses. Self-validating: fitted intercept implies C₀ = 279.8 ppm vs accepted 278. Myhre's 5.35 runs 5.2% low here. |
| `CO2_CONCENTRATION_PPM` | 425.65 | ppm | measured (Tier A) | IGCC 2025a annual mean, 2025. |
| `CO2_PPM_TO_GT` | 7.82 | GtCO₂/ppm | physics | Atmospheric mass 5.148e18 kg × 1e-6 × molar ratio 44.01/28.96. Derivable, not fitted. |
| `THERMAL_F_NATURAL_ERF` | 0.262 | W·m⁻² | measured (Tier A) | IGCC 2025a solar + volcanic at 2025. Consumes budget per C4 but is **not removable by labor**, so it is the floor on achievable forcing and the wedge between the budget basis and the F3 gain basis. |
| `THERMAL_GMST_OBSERVED` | 1.23 | K | measured (Tier A) | IGCC 2025a GMST anomaly, 2015–2024 mean. Paired with the committed F/λ to expose the pipeline — the warming already bought and not yet delivered. |
| `THERMAL_TXX_PER_GMST` | 1.48 | K·K⁻¹ | measured (Tier A) | C6 land-extreme amplification; OLS of the ERA5/Berkeley/HadEX3 mean TXx series on GMST, 1950–2025, n=76. Per-dataset spread 1.33–1.57. Guardrail I — refresh annually. |
| `THERMAL_LAMBDA_FEEDBACK` | 1.2 | W·m⁻²·K⁻¹ | **derived-position (Tier C value)** | The **equilibrium** feedback. Value unchanged, but its position is now derived rather than assumed ([`research/thermal_lambda.py`](../hours_eoh/research/thermal_lambda.py), [`reference/data/climate_feedback.json`](../hours_eoh/reference/data/climate_feedback.json)): it sits **below** the AR6-implied 1.310 (ECS 3.0 K) and below the historical energy-budget estimate **1.492** derived from the shipped IGCC series — so 1.2 is the **conservative** side (lower λ → smaller budget → larger obligation) and was not flattering the framework. **Frame discipline:** pairs only with the equilibrium budget λ·ΔT−F; the historical 1.492 pairs with a transient reading the framework rejects, and `budget_forcing_headroom` **refuses** the mix (it inflates the allowance ~6×). **Sensitivity is first-class:** across AR6's likely ECS range the budget runs from **ZERO** (ECS 5 K) to ~11× the shipped case. resolves_by: an assessed equilibrium feedback with uncertainty, not a point value. |
| λ_historical (derived) | 1.492 | W·m⁻²·K⁻¹ | measured (**Tier A**) | `(F − N)/ΔT` from IGCC 2025a total ERF, Earth energy imbalance and GMST. Four windows 1995–2024 agree within 5% (1.466–1.537), so it is a property of the data not the window. Band 0.52–2.44, dominated by **aerosol** forcing uncertainty. Pattern effect vs AR6-implied equilibrium: **+0.182**, the expected sign and scale — an independent check the derivation behaves. **Not for the budget.** |
| `THERMAL_U_FLOOR` | 0.50 | — | CHOSEN | derive from observed variance in Φ and ψ*, not chosen. |
| `THERMAL_EPS_CURRENT` | 0.40 | — | CHOSEN | framework current-equilibrium ε (arc midpoint). **ε_max is directly proportional to this**, which sits badly with the invariant that ε is an observable, not an input — report the measured ratio `B/Φ_auto` instead, and derive ε from `core/civilization.py`. |

**P0 reorder (F3-first).** Per the Path C run, the P0 headline is now F3
(`research/thermal.py:decarbonization_headroom`, computable from constants), and
the thermodynamic-floor ceiling bound (E29/F1/F2) is demoted to CONDITIONAL —
non-binding at current dissipation.

**Findings (reproduced exactly).** F1: the global thermal ceiling does NOT bind at
current dissipation (ε_max = 2.6–19×) — conditional, binds at ~10–50× present Φ.
F3 (load-bearing, now the P0 headline): decarbonization is worth ~1000–1100 TW ≈ 60× current dissipation —
carbon has consumed the budget. F11 (strongest measured, now a corridor bound):
dense collectives are in Contact NOW (Singapore U≈22, S. Korea 1.4, Netherlands 1.0)
while the World aggregate sits at U≈0.05 — so the thermal corridor bound is a
**collective-level** instrument (`measured_thermal_ceiling`), global is uninformative.
ΔT_lo (Tier D) dominates all of it; Path C is 5–10× uncertainty — regime SIGN only,
**not** obligation (that needs Path B).

### Asset census — one survey, two floors (B1/B2)

The condition census consumed by `infrastructure_statutory_floor` carries four
**optional** thermal keys alongside the two required ones. The hours side ignores
them; `research/thermal_capital.infrastructure_thermal_floor` reads them and
returns the dissipation floor in watts from the same survey.

| Key | Required | Kind | Notes |
|---|---|---|---|
| `count` | yes | measured | physical asset count in the condition class |
| `hours_per_unit_year` | yes | task-normative | interval × crew-hours; no currency enters |
| `type` | no | measured | `CAPITAL_THERMAL_PROFILES` key |
| `teh_per_unit` | no | measured | bridges census **counts** to per-TEH intensities |
| `condition` | no | measured | ∈ [0, 1]; missing reads as 1.0 — conservative (max draw) |
| `design_life_years` | no | measured | missing falls back to the type's profile life |

A bucket without usable thermal keys contributes zero **and is reported** in
`unpriced_buckets`, with `coverage` giving the share of counted assets actually
priced — a thermal floor at 40% coverage is a different claim from one at 100%.

The good/fair/poor condition defaults in `census_from_condition_counts`
(0.85 / 0.60 / 0.35) are **CHOSEN**, mapping NBI-style classes onto the [0, 1]
scale the capital profiles use. A real census carries per-asset condition and
should pass it rather than accept these.

Specifying the thermal keys at survey time costs nothing; retrofitting means
re-surveying. That is the whole argument for fixing this schema before the
census is collected rather than after.

### Capital thermal profiles — §12.2 dual-output (research/thermal_capital.py)

The §12.2 adaptation: the same capital inventory that eliminates EOH
(`CAPITAL_MACHINE_PROFILES`) also dissipates heat. `CAPITAL_THERMAL_PROFILES`
(parallel dict, all 11 capital types) carries the two new physical fields;
`design_life` (already in the EOH profiles) is the third §12.2 field, and grid κ
is a collective input (§8.1), not per-type.

| Parameter | Default | Units | Kind | `resolves_by` |
|---|---|---|---|---|
| `power_intensity_w_per_teh` (per type) | 0.3–8.0 | W/TEH | CHOSEN | measured energy-use intensity by capital class (IEA end-use / sectoral balances). |
| `embodied_energy_j_per_teh` (per type) | 2e7–1.5e8 | J/TEH | CHOSEN | LCA inventories (ecoinvent / EPDs); amortized over `design_life`. |
| `THERMAL_GRID_KAPPA_DEFAULT` | 0.93 | — | CHOSEN/measured | physical grid mix serving the capital (§8.1), not procurement; default = world fossil+nuclear share. |

`machine_dissipation_from_capital` derives Φ_auto = Σ (teh·condition·power_intensity
+ teh·embodied/(design_life·Δt_s))·κ̄ — the thermal twin of
`machine_eoh_from_capital`, reusing its resolved stock (DRY). **Honest status:** the
intensities are CHOSEN placeholders — relative ordering defensible (compute/industry
heavy), absolute scale anchored only to order-of-consistency with Path C's measured
~2200 W·person⁻¹ (a well-invested standard-tier collective reads ~3200 W·person⁻¹,
within ~1.5×; NOT fitted). Path-B-shaped structure on Path-D magnitudes: the
deliverable is the closed loop (one inventory → {ε, Φ, U, thermal ceiling}), not the
numbers. Advisory only.
