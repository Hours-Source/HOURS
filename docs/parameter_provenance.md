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

The goal is that **every constant carries a provenance tag, that the tag says what
KIND of thing the value is, and that the set awaiting measurement shrinks over
time**. Seven tags, plus two sub-labels — nine values in all, and the vocabulary
is closed and enforced (`utils/provenance.py: VALID_TAGS`). The seven tags:

- **physics** — a structural claim about how entropy works. Changing it changes the
  model's claim about the world; needs a theoretical justification, not a knob.
- **measured** — read from an external empirical source (e.g. O\*NET, BLS). The
  strongest tag: it can be wrong, and a data refresh would show it.
- **derived** — computed from measured inputs by a stated formula (normalizations,
  composites). Inherits its authority from the measurements beneath it.
- **bounded** — picked inside a **measured band**. The band is evidence; the point
  inside it is not. Must state its `band` and which way it `errs`.
- **placeholder** — no measurement stands behind it at all. Must name the evidence
  that would settle it. **This is the real debt.**
- **normative** — a decision, not measurable even in principle. Must state
  `decided_by`, may carry a `precedent` that informs without settling, and **may not
  claim a `resolves_by`**.
- **instance** — describes *the jurisdiction being modelled*, so the deploying
  institution supplies it and this framework never measures it. Must state
  `supplied_by` (what they measure, and the intake path here) **and** `default`
  (what the shipped number is), and **may not claim a `resolves_by`**.

And two **sub-labels**. These are not rival tags — they qualify how a value was
arrived at, and `provenance check` reports them in the same table, which is why
the count there reads nine rather than seven:

- **derived-then-FROZEN** — a `derived` value pinned at a reference epoch so it
  stays comparable across data vintages. It moves only when the epoch is
  deliberately re-cut, not when a source refreshes underneath it.
- **convention** — a stated denominator or reference frame, not a claim about the
  world. The eight `CANONICAL_*` constants carry it: the canonical arc is an
  ideal-arc *reference*, and calling it `measured` or `placeholder` would both be
  category errors.

### `band_from:` — claiming an anchored derivation, and the transitive gate

Three operations can settle a constant, not two: **measure it** (`measured`),
**decide it** (`normative`), or **derive a constraint from the model's own
structure plus other constants**. The scheme named the results of the third but
never the operation — even though the two best-grounded constants here got their
bands that way. `PERSONAL_EOH_BASE`'s band is `(L−R)/w` and `(M+H−R)/w`, neither
a direct measurement of B; `AGE_WEIGHT_INFANT`'s is a one-sided `≥ 2.55`.

**`band_from:` names the constants such a derivation rests on, and it is
gated.** No named ancestor may be a `placeholder` — **transitively**. A band
resting on an unmeasured input launders a guess into evidence.

**The one-level check is not enough, and that is not hypothetical.** `derived`
inherits its authority from what lies beneath it, so a `derived` input can bottom
out on a placeholder two or three steps down. Both anchored-inversion candidates
examined on 2026-08-15 had exactly that shape:

```
CONTESTABILITY_CAPITAL_YIELD_RATE
  ← FORMATION_DEPRECIATION_RATE   (derived)
    ← CAPITAL_MACHINE_PROFILES    (PLACEHOLDER)

ECOLOGICAL_BASE_RATE  ← the thermal drawdown chain
    ← CDR_GROSS_REMOVAL_FACTOR    (PLACEHOLDER)
```

A one-level check passes both. Hand-tracing caught them, and the gate is that
trace in code.

**`band_from:` is opt-in, and its absence is not a gap.** It means *"I claim this
derivation is anchored."* A constant genuinely derived from a placeholder should
say so in `form:`/`resolves_by:` and omit the field — which is what
`FORMATION_DEPRECIATION_RATE` already does (*"it inherits CAPITAL_MACHINE_PROFILES'
standing, which is CHOSEN"*). No constant in `data.py` currently claims an
anchored band, and that is the honest position rather than an omission.

> **Why `instance` was split out of `placeholder` (2026-08-09).** Same category
> error as `normative`, in a different direction. `TRUST_BASE_TEH` and
> `CAPITAL_STOCK_DEFAULT` are the two most-consumed constants in the repo — 77 and
> 65 call sites — and both were tagged `placeholder` with a `resolves_by` reading
> "a capital inventory **for the jurisdiction being modelled**". No dataset this
> framework could ever gather retires them, because they are not facts about the
> world; they are the inputs an institution brings. Filing them as unpaid
> measurement debt overstated the framework's ignorance *and* hid the intake path
> from the analyst whose job it is to supply them.
>
> **The risk of this tag is laundering**, and `default:` is the field that
> prevents it: an `instance` constant still ships with a number, every canonical
> result in this repo was produced at that number, and none of those results is
> evidence about anyone else's jurisdiction. `TRUST_BASE_TEH`'s `default:` says
> so in as many words — it was *sized backwards*, chosen so the dividend covers
> the obligations it must fund.

**`superseded_by` marks a constant retired**, naming the live replacement — either
another constant or a whole measured pathway (`DEFAULT_SEGMENTS` →
`hours_eoh.scenarios.measured`). A retired constant is kept rather than deleted,
per the additive-not-destructive rule: it is the value every earlier result was
produced at. It owes no `resolves_by`, `band` or `decided_by`, because those
obligations exist so a *live* value can be improved.

**Retirement is verified, not asserted.** `test_retired_constants_have_no_operative_consumers`
checks that nothing in `core/`, `land/` or `scenarios/` still reads it —
`research/` may keep a superseded arm, which is what that layer is for. The check
earned its place immediately: it falsified **two of the four** retirement claims
made when it was written. `DEFAULT_SEGMENTS` was still the live default in
`core/multipliers.py:82` and `core/dashboard.py:493`, and `SKILL_DECAY_RATE` was
still read by `core/eoh_generation.py`. Both went back into the debt count rather
than the check being loosened.

### `baseline_in:` / `baseline_labels:` — the refuted value, kept visible

The no-readers rule asks *"is it mentioned?"*, and that conflates two things:

```python
decay: float = SKILL_DECAY_RATE     # a second parameter, running in parallel
"shipped": SKILL_DECAY_RATE         # the refuted value, printed beside its
                                    # replacement so the gap stays visible
```

Only the first is what retirement exists to prevent. The second is a documented
negative result, and this framework depends on keeping several: `scenario run
knowledge_base` prints `credible_shipped: False` **because** the refuted 0.10 is
still there to compare against, and `in_band: True` became falsifiable only when
the synthetic `DEFAULT_SEGMENTS` survived alongside the measured registry. A rule
whose remedy is *move the code to `research/`* would strip that out — and would
make the gate satisfiable by relocation, which measures where code lives rather
than what governs output.

So the exemption is declared and then **checked, in three conditions**:

1. **`baseline_in:` names every operative reader.** An undeclared reader is how a
   value creeps back onto a computing path under cover of a claim made about
   other modules.
2. **It may never be a parameter default**, anywhere, verified by `ast` in
   `parameter_default_consumers()`. A default is exactly how a superseded value
   keeps governing output after everyone stops thinking about it — the
   `decay=SKILL_DECAY_RATE` and `skill_decay_rate=0.10` defects were both this.
   This condition cannot be waived.
3. **Every read must be in a reporting position, under a declared label.** Shape:
   a dict value under a literal key, an f-string, or a tuple carrying a label.
   Arithmetic on the way is fine — a ratio against the refuted value is still a
   comparison — but a function call is not, because that is a handoff the
   analysis cannot follow. Label: the literal must appear in `baseline_labels:`.

**Condition 3's second half exists because the first half failed its own bite
test.** Shape alone accepts *any* dict value, and nearly every function here
returns a dict — so a retired constant multiplied into a live figure under the
key `"total"` passed cleanly. Requiring the label to be declared makes adding one
a visible act in a diff rather than an emergent property of Python syntax. A
declared label nothing uses is also refused: a permission nobody exercises is a
permission nobody reviews.

A nested structure reports under **all** its enclosing keys, so
`{"shipped": {"renewal_rate": OLD}}` carries both and only one needs declaring.
Stopping at the innermost key would push the vocabulary toward field names like
`renewal_rate`, which say nothing about a value being superseded.

#### The fourth condition: a runtime flow trace

Conditions 1–3 are static, and static analysis has one gap here that is real
rather than theoretical. The labelled tuple proves attribution **at the read**,
not containment downstream: a loop target bound from `("shipped", OLD)` can
carry the value into a live figure, and did so undetected in a deliberate
escape written to test exactly that.

Closing it statically means intra-procedural taint plus a model of the
comparison-table idiom — and would *still* leave function calls opaque, which is
where the interesting arithmetic happens (`_unit_response(eps, rate)`). So the
flow is checked by running it instead. `trace_baseline_flow()` substitutes a
`Refuted` float — a subclass whose arithmetic propagates the marker — into every
module `baseline_in:` names, calls each reading function that can be driven
without arguments, and walks the returned structure for survivors. A survivor is
a leak unless some key on its path is a declared label.

The two halves divide cleanly, and neither subsumes the other:

| | coverage | depth |
|---|---|---|
| **static** (`baseline_reads`) | all code | position only |
| **runtime** (`trace_baseline_flow`) | only paths a caller drives | exact flow, through loops **and** calls |

Three deliberate limits, each stated because a checker whose gaps are
undocumented reads as stronger than it is:

- **Only reachable functions are exercised.** Readers needing arguments are
  *reported as skipped*, never silently passed — "the trace was clean" must not
  be able to mean "the trace ran nothing", so `exercised` is asserted alongside
  `leaks`.
- **Bools and strings do not carry taint.** A bool derived from the refuted
  value is a *verdict about it* — `credible_shipped: False` is the whole reason
  it is still here — and a string cannot corrupt a figure.
- **The traced module must be the scanned file.** A dotted name resolves against
  whatever package is already loaded, so a scan rooted elsewhere would otherwise
  patch the real module and report on code it never read.

Inspect all of it with `eoh provenance baseline [CONSTANT]`, which prints each
read's position, label and verdict, then the runtime trace beneath it.

## Checking the guides

`docs/parameter_provenance.md` is safe by construction — its tables are generated
from `data.py`. **`docs/guides/` is not.** It is hand-written prose, it is the
first thing an outside analyst reads, and nothing checked it until 2026-08-09,
when `docs/guides/implementation_guide.md` was found to be advertising
`PERSONAL_EOH_BASE = 1500` after the reprice to 1000, listing six constants as
"physics" to be left at their defaults when **none of them is physics**, pointing
institutions at a deprecated parameter, and calling `contestability_margin()` —
the bare χ that §8.9 superseded — in its worked example.

Four checks now run over every file in `docs/guides/`:

| Check | Catches |
|---|---|
| `test_guides_do_not_quote_stale_constant_values` | any `NAME = number` claim that contradicts `data.py` |
| `test_guides_do_not_use_the_retired_tag_vocabulary` | teaching the retired binary Physics/Calibration scheme |
| `test_guides_do_not_name_constants_that_no_longer_exist` | a backticked constant that is not in `data.py` |
| `test_there_are_guides_to_check` | the glob silently matching nothing |

**What this does not close.** The value check is value-equality, so it sees a
constant repriced while the sentence naming it stays put — the drift that
actually happened. It cannot see a *derived product* restated in prose (as
`docs/parameter_provenance.md` handles with a curated stale-figure test), nor a
narrative paragraph that goes stale in a way no field captures. That residual is
a human problem, and saying so is better than implying otherwise.

> **Why `CHOSEN` was split (author decision 2026-08-09).** One tag was covering
> three different epistemic states, and lumping them distorted the picture in both
> directions. It made the calibration set read as **83% guesswork** while *hiding*
> which constants are the actual debts — `INFRA_MAINT_RATE` sitting inside a
> measured OECD band was filed identically to `ABATEMENT_HALF_CAPITAL_TEH`, which
> nothing constrains at all.
>
> And it committed a category error: `M_MAX`, `DIV_RATE`, `ESTATE_INHERITANCE_FRACTION`
> and `THERMAL_PROGRAMME_YEARS` were all listed as "awaiting measurement". No dataset
> will ever settle what fraction of an estate should pass to heirs, or over how many
> years a generation should discharge a debt it incurred — `THERMAL_PROGRAMME_YEARS`
> says so in its own comment: *"this is an ETHICAL choice about who bears the work,
> not a technical one"*. Filing a commitment as an unpaid measurement both overstates
> the model's ignorance and lets the commitment escape the argument it actually owes.
> **`normative` is forbidden a `resolves_by` for exactly that reason: the forbidding
> is the point.**

**`band` and `errs` are required on `bounded`, and gated.** Without them, "bounded"
would be a free upgrade — a placeholder claiming to be better founded than it is. The
repo already leans on the direction of error for its most leveraged picks (*"erring
high is the mortality-minimising error"* for `PERSONAL_EOH_BASE`; *"1.2 is the
conservative side"* for `THERMAL_LAMBDA_FEEDBACK`) but those lived in prose where
nothing checked them. `errs` opens with **HIGH**, **LOW**, **NEITHER** or
**WITHHELD** — the last a real epistemic state here, not an escape hatch: the thermal
layer already refuses to publish a budget whose sign is undetermined. A `band` on any
other tag is an error, since a band means the value was picked inside measured bounds.

Two working sub-labels sit alongside the six:

- **derived-then-FROZEN** — a derived value pinned at a reference epoch so it stays
  comparable across data vintages (re-deriving it per vintage would reintroduce
  the circularity the freeze exists to break).
- **convention** — a stated denominator, an adopted external standard, or a declared
  reference frame; not a claim about the world. `H_REF` = 2,000 h/yr is the clearest
  case: read as a measurement of hours worked it would be wrong nearly everywhere,
  but it is not one. The `CANONICAL_*` arc constants are here too — an ideal-arc
  reference axis that real trajectories are measured *against*.

**`tier` (A–D) is a sub-qualifier, not a rival scheme.** The thermal layer already
wrote "measured (Tier A)"; the tag scheme now formalises that reading. Tier grades
*how good a source is*, so it applies only where there is a source to grade —
`measured`, `bounded` and `placeholder`. A `physics` claim has no source (it is
structural or it is wrong) and a `normative` decision has none either.

### Where the model stands

Run `python3 utils/eoh_cli.py provenance check` for the live figures. As of
2026-08-20, over all 265 constants:

| | count | share | what it means |
|---|---|---|---|
| grounded | 72 | 27.2% | structural, measured, derived, or a stated convention |
| bounded | 18 | 6.8% | picked inside a measured band — the band is the evidence |
| **placeholder** | **96** | **36.2%** | **no measurement behind it at all — the debt** |
| normative | 62 | 23.4% | a decision; no dataset retires it |
| instance | 12 | 4.5% | the deploying institution supplies it, not this framework |
| retired | 5 | 1.9% | superseded; governs no current output |

**Debt is 43.0%**, and the actionable figure is the 36.2% of constants that are
placeholders. That is the number to drive down. The 62 normative constants are not
debt; they are what the framework has decided, and they need argument rather than
data. The 7 `instance` constants are not debt either — but their shipped defaults
are not evidence, which is why they are reported on their own line rather than
folded into `grounded`.

**Where the reduction from 106 came from, and where it did not.** Ten constants
left the placeholder count on 2026-08-09 without a single new measurement: seven
were `instance` all along, two were genuinely retired, and `SUFF_LEVY_RATE` became
`normative` after its own stated derivation was run and returned **zero at every
ε** — the dividend alone runs a surplus, so no levy rate is required for solvency
and deriving it would set a different policy rather than a better calibration.
Three further constants were *examined and left as debt*, because the derivations
their pointers named do not work:

- `CONTESTABILITY_MIN_VIABLE_POPULATION` — `COMPETENCY_THRESHOLD × ESSENTIAL_DOMAINS`
  is 0.155 × 7 = **1.085**, a fraction greater than one, which yields no headcount.
- `RECAL_EPSILON_RATE_PER_YEAR` — the simulation that would derive it **consumes
  it** as an input, so the derivation is circular; the null anchor implies
  0.0254/yr against the shipped 0.02, a 27% disagreement that the circularity
  makes uninterpretable. It needs a fixed-point solve, as `epsilon_ref_fixed_point()`
  did for the ε_ref anchor.
- `SKILL_DECAY_RATE` and `DEFAULT_SEGMENTS` — claimed retired, falsified by the
  operative-consumer check (see above).

Of the 18 bounded picks, **9 err LOW, 4 HIGH, 4 NEITHER and 1 is WITHHELD**. The lean
toward LOW is worth noting rather than celebrating: for `DEP_RATE`, `THERMAL_F_GHG`
and the `GOVERNANCE_IRR_*` pair, erring low is the *unsafe* direction — it flatters
solvency, overstates the thermal allowance, and sets the assessment-quality gate below
the conventional bar. Each says so on its own line.

> **Migration note (completed 2026-08-09 — now machine-checked).** All **265**
> `data.py` constants carry an inline tag block, and `tests/test_provenance.py`
> fails if that stops being true. The migration off the older binary
> **Kind = Physics | Calibration** is finished: nine tables were still on it, and
> the whole 51-constant GUF block was undocumented.
>
> The migration was not cosmetic. Several constants carrying `Physics` turned out
> to be desk estimates or constitutional commitments. **Only 2 of 265 constants are
> `physics`** — applying this scheme's own demanding definition honestly leaves
> `A_EARTH_M2` and `SIGMA_SB` and nothing else. The 190 that became `CHOSEN` were
> then split into `bounded` / `placeholder` / `normative` (see above), because one
> tag covering three epistemic states was itself obscuring the picture. Where a functional FORM is
> structural but its constant is not, the `form:` field says so rather than letting
> the stronger tag cover both.
>
> **Tags live inline in `data.py`, immediately above each value** — proximity is
> what stops coverage regressing, since you cannot add a constant without touching
> the lines the tag lives on. Every table in this document below a
> `<!-- provenance:table -->` marker is **generated** from those blocks; the prose
> around them is hand-written and is where the argument lives. Regenerate with:
>
>     python3 utils/eoh_cli.py provenance doc --write
>     python3 utils/eoh_cli.py provenance csv --write
>
> Retags are in [Retag log](#retag-log-2026-08-05) and
> [Retag log (2026-08-09)](#retag-log-2026-08-09) below.

**Machine-readable sources of truth.** For a public audit that never opens Python:
[`constant_provenance.csv`](hours_eoh/reference/data/constant_provenance.csv) —
one row per `data.py` constant with value, units, tag, tier, form, block,
`resolves_by` and any note. For the measured multiplier registry:
[`multiplier_provenance_v5.csv`](hours_eoh/reference/data/multiplier_provenance_v5.csv).
Both are generated; neither is hand-edited.

Source: `hours_eoh/data.py` and `hours_eoh/params.py`; measured multiplier data
in `hours_eoh/reference/data/` (O*NET 30.3 / BLS, frozen epoch 2026-07-29).

**Scope of the coverage gate.** It covers module-level constants in `data.py`. Three
provenance surfaces sit outside it and are marked as such where they appear:
`EohParams` defaults (`params.py`), the per-occupation multiplier registry, and any
constant that never made it into `data.py` — of which
`_ECOLOGICAL_SPIKE_INTENSITY` in `core/eoh_generation.py:47` is the one known case,
a standing violation of the no-anonymous-constants invariant.

---

## EOH Generation — Personal Domain

> **This is the highest-leverage block in the model.** Personal EOH is 98.9% of
> total EOH at ε = 0, 84.8% at ε = 0.40 and 46.1% at ε = 0.99 (re-measured
> 2026-08-10; see [Domain balance](#domain-balance-the-denominator-problem)), so
> `PERSONAL_EOH_BASE` sets the denominator of ε outright across the low arc and
> still sets half of it at the top. It carried the `Physics` tag while being a
> four-line desk estimate.
>
> **Repriced 1,500 → 1,000 on 2026-08-06** (author decision) to the high end of
> the evidence band, on the asymmetric-loss argument below. Still `CHOSEN`.

<!-- provenance:table "EOH generation — personal domain" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `AGE_GROUP_RANGES` | <dict: 4 keys> | inclusive age bounds in years | convention<br>form: a partition of a continuum, chosen not found. The 2026-08-10 care measurement looked for natural breakpoints and there are none: care received per person declines SMOOTHLY through childhood (113.6 → 70.7 → 36.1 → 9.6 min/day over 0-4/5-9/10-14/15-19) with nothing happening at 5/6 or at 17/18. These bounds are administrative, and the model reads four steps off a smooth curve. | —<br>the bands are a REPORTING VIEW. Anything sensitive to where the cuts fall should integrate a demand curve over age instead — see reference/care_demand.py, which carries the curve these bands approximate. |
| `AGE_GROUP_FRACTIONS` | {'infant': 0.07, 'child': 0.16, 'working_age': 0.6, 'elderly': 0.17} | fraction of population | instance | **you supply** your census age pyramid, grouped to AGE_GROUP_RANGES. Intake path: reference/data/census_age_2020_2025.csv ships the US reading by single year of age, and reference/care_demand.population_shares() groups any band structure against it. Nothing about YOUR population is derivable from this framework.<br>**shipped default** an OECD-shaped split that happens to fit the US around 2020 (measured 6.98/15.24/60.91/16.87 that year). By 2025 the US had moved to 6.5/14.5/60.0/18.9 — the elderly band is already 2pp off and rising, so the shipped default is a snapshot, not a standard. Swapping the 2025 reading in moves w by only +0.8%, because the weights dominate. |
| `AGE_WEIGHT_WORKING_AGE` | 1.0 | relative personal EOH (dimensionless) | convention<br>form: the NUMERAIRE. Every other weight is expressed against a working-age adult, so this is 1.0 by definition and carries no evidential content — measuring it is not a coherent request. | — |
| `AGE_WEIGHT_INFANT` | 3.0 | relative personal EOH (dimensionless) | bounded (Tier B)<br>form: personal obligation generated per person of that age, relative to a working-age adult: (self-maintenance + care received) integrated over the band and divided by the numeraire band's total. | **band** ≥ 2.55, one-sided — and the openness is the whole point. Measured 2026-08-10 from ATUS 2021–25 pooled (scenario run care_curve), but ATUS surveys nobody under 15, so the self-maintenance term is missing for the ENTIRE infant band. The measurement is a FLOOR that can only rise, never a point estimate, and calling it a two-sided band would be a worse claim than leaving the constant a placeholder.<br>**errs** HIGH, and high is the safe direction, by the same asymmetric-loss argument that set PERSONAL_EOH_BASE. A weight set too low understates the obligation a dependent generates, and the deficit is paid in unserved care — the model reports feasible while a child goes unattended. Too high only over-provisions. The shipped 3.0 and 1.5 sit above their measured floors by 18% and 11%, which is the direction to be wrong in.<br>self-maintenance below age 15, which ATUS cannot observe because it does not survey children. A time-use survey covering children (some HETUS members do) would close the band from below and turn these into point estimates. |
| `AGE_WEIGHT_CHILD` | 1.5 | relative personal EOH (dimensionless) | bounded (Tier B)<br>form: as AGE_WEIGHT_INFANT — (self-maintenance + care received) over ages 6–17, relative to a working-age adult. | **band** ≥ 1.35, one-sided. Measured 2026-08-10 (ATUS 2021–25 pooled). The band is one-sided for the same reason as the infant weight, but LESS of this one is missing: ATUS observes ages 15–17, so the band's self-maintenance term is partly present (24.5 min/day measured across the band) rather than wholly absent.<br>**errs** HIGH, and high is the safe direction — a weight set too low understates the obligation a dependent generates and the deficit is paid in unserved care. The shipped 1.5 sits 11% above its measured floor.<br>self-maintenance for ages 6–14, which ATUS cannot observe. A time-use survey covering children would close the band from below. |
| `AGE_WEIGHT_ELDERLY` | 1.48 | relative personal EOH (dimensionless) | measured (Tier B)<br>form: as above — (self-maintenance + care received) over the 65+ band, relative to working age. The ONE band where both terms are measured: 207.1 min/day self-maintenance + 30.5 care = 237.5 against working age's 160.2, giving 1.4824, adopted at 1.48. | the INSTITUTIONAL population. ATUS covers households only, so the institutionalised elderly — who need the most care — are outside the frame entirely, and 1.48 is a lower bound for the elderly population as a whole. CMS Payroll-Based Journal reports nurse staffing hours per resident-day for every certified US nursing home and would close it. Recipient-side ACTIVITY monitoring would NOT: datasets of that class (TIHM was checked) record the monitored person's own movement and physiology rather than anyone's care hours, and are home-based cohorts, so they re-measure the population ATUS already covers.<br>measured 2026-08-10 from ATUS 2021–25 pooled with Census 2025 denominators (scenario run care_curve), replacing a shipped 2.5 that was asserted. Bound to the measurement by test rather than by expression — data.py sits below reference/ and cannot import it — so test_the_elderly_weight_was_adopted_from_this_measurement fails if either side moves alone. Tier B, not A: a large national survey, but with a named systematic exclusion, below. |
| `AGE_GROUPS` | <dict: 4 keys> | composite of AGE_GROUP_RANGES, AGE_GROUP_FRACTIONS and the AGE_WEIGHT_* constants | derived<br>form: assembled from the four constants above, which is the point — this dict was ONE constant carrying FOUR different epistemic states (a chosen partition, jurisdiction data, a numeraire, and two grades of measurement) under a single `placeholder` tag, so the tag necessarily read the weakest element and told a reader nothing about any of the others. | —<br>retained as the public shape because ~70 call sites read it, and the split is additive: the assembled value is byte-identical to what the hand-written dict held. New code should prefer the specific constant it actually needs — a caller wanting the population split should read AGE_GROUP_FRACTIONS and see the `instance` tag telling them to supply their own. |
| `PERSONAL_EOH_SURVIVAL` | 600.0 | hours/year per working-age-equivalent | bounded<br>form: S_a — the autarky-referenced SURVIVAL standard. Hard-bounded above by (L−R)/w = 627: a survival standard exceeding labour supply is extinction. Set independently and CHECKED rather than pinned to the bound, so scenarios/feasibility.py can still fail it — a constant that cannot fail its own test says nothing. | **band** hard upper bound (L−R)/w = 627 h/yr per working-age-equivalent, from this file's own H_REF × workforce fraction. 600 sits just inside it.<br>**errs** LOW. Set below the supply bound rather than at it, so it understates the survival obligation if anything, which keeps ε_suff optimistic. Deliberate: the bound is CHECKED by scenarios/feasibility.py rather than pinned, because a constant that cannot fail its own test says nothing.<br>minimum-subsistence time-allocation studies covering only the components that kill you if unmet — food, water, shelter, warmth. |
| `PERSONAL_EOH_SUFFICIENCY` | 1500.0 | hours/year per working-age-equivalent | bounded<br>form: F_a — the autarky-referenced SUFFICIENCY standard. MAY exceed labour supply, and that gap is precisely why collectives form. | **band** 390–926 h/yr from the capital-inventory + time-use identity at MODERN capital — which measures F_c, not F_a, the two reconciled by 38–74% abatement. Independently, 'all needs met' requires ~30% abatement at ε=0.99, putting F_a mid-band.<br>**errs** HIGH. It is the autarky-referenced standard, so it MAY exceed labour supply — that gap is why collectives form, not an error. Erring high overstates what a decent life costs alone, which overstates the case for collective delivery rather than understating a survival risk.<br>cross-cultural time allocation at a stated adequacy standard, plus the capital-inventory + time-use identity route. Cross-checks already in hand: the identity route gives F_c(modern) = 390–926, implying 38–74% abatement, and "all needs met" requires ~30% at ε=0.99 — 1500 sits mid-band against both. |
| `PERSONAL_EOH_COMPONENTS` | <dict: 4 keys> | share = fraction of the personal obligation; abatability = fraction removable | placeholder<br>form: the shares are the original desk estimate's own four terms (208/156/208/936 over 1508), so they are internally consistent with PERSONAL_EOH_SUFFICIENCY rather than independent of it. The abatability ceilings are the per-component most that infrastructure can ever remove, and their ORDERING encodes the block's structural prediction: abatability and sufficiency are ANTI-CORRELATED, because what infrastructure removes is survival-shaped work and what it cannot remove is care (the Baumol case). That prediction is TESTED in TestAntiCorrelationPrediction, not asserted here — changing these weights falsifies it. | per-component pointers are on each line below. a_max = Σ share × abatability = 0.4483 is DERIVED from this table, so it is not a free parameter; the table is where the judgement lives. |
| `ABATEMENT_HALF_CAPITAL_TEH` | 1000.0 | TEH of capital per capita | placeholder<br>form: K_half in a(K) = a_max · K/(K + K_half). It sets the PACE of abatement along the arc, not its ceiling. | the identity route run at two or more capital levels — B(K) measured at matched (inventory, time-use) pairs pins a_max and K_half together.<br>THE LEAST-GROUNDED CONSTANT IN BLOCK II, and the only new free parameter the block introduced. Report the sensitivity alongside any abatement figure until it is measured. |
| `PERSONAL_EOH_BASE` | 1000.0 | hours/year per working-age-equivalent | bounded<br>form: the ABATEMENT-COLLAPSED operating value — one number standing in for F_a × (1 − a(K)) at an unstated point on the arc. 1000 ≈ 1500 × (1 − 1/3), and a ≈ 33% sits mid-range between the 10% "all needs met" requires at ε = 0.40 and the 38–74% the identity route implies at modern capital. Retired when abatement becomes the default generation path. | **band** 390–1006 h/yr per working-age-equivalent, from two instruments sharing no assumption: the supply ceiling (L−R)/w = 396–1006 across subsistence parameters, and the accounting identity B = (M+H−R)/w = 390–926, whose M comes from a capital inventory and is B-FREE.<br>**errs** HIGH. Set at the TOP of the band on an asymmetric loss function: too low hides a real shortfall (the model reports feasible, capital is under-built, and the deficit is paid in unserved biological obligation), while too high only over-builds capital. Erring high is the mortality-minimising error.<br>the capital-inventory + time-use identity, NOT time-use data alone — see the circularity section in docs/parameter_provenance.md. Partial progress: core/eoh_generation.personal_statutory_floor() now builds a currency-free floor from physical quantities, but only one of seven basket components is priced (nutrition production, 330.9 h/person·yr), so coverage is 6.9% and the floor cannot yet falsify this value.<br>THE SINGLE MOST LEVERAGED CONSTANT IN THE MODEL. Personal EOH is 98.9% of total EOH at ε=0, 84.8% at ε=0.40 and 46.1% at ε=0.99 (re-measured 2026-08-10), so this effectively sets the denominator of ε across the low arc, and still sets half of it at the top. Repriced 1500 → 1000 on 2026-08-06 (author decision) to the HIGH end of the evidence band, on an asymmetric-loss argument: too low hides a real shortfall (model reports feasible, capital under-built, deficit paid in unserved biological obligation), too high only over-builds capital. Erring high is the mortality-minimising error. Per working-age-EQUIVALENT: × w = 1.3016 gives the per-capita claim of 1,301.6 h/person·yr. (w was 1.475 until the AGE_GROUPS elderly revalue of 2026-08-10. The band above was derived at the OLD w and has not been re-derived; a lower w raises the supply-ceiling arm B ≤ (L−R)/w, so the band is now conservative rather than wrong, and re-deriving it is owed.) |
| `BASKET_DIET_KCAL_PER_DAY` | 2100.0 | kilocalories per person per day | convention<br>form: a declared dietary energy reference, not a derived optimum. 2,100 kcal/day is the humanitarian planning standard (Sphere / WHO-FAO-UNU emergency reference), adopted here because the basket needs a stated figure and this one is the most widely used. | —<br>THE ONLY BASKET QUANTITY THAT CURRENTLY MOVES A NUMBER. Nutrition production is the one priced component of seven, so this scales the floor 1:1 — 1,800 kcal/day gives 283.6 h/person·yr, 2,500 gives 394.0, against the shipped 330.9. The other three quantities multiply into nothing today because their components carry `hours_per_unit=None`, and are excluded rather than costed at zero. |
| `BASKET_WATER_LITRES_PER_DAY` | 50.0 | litres per person per day | convention<br>form: the WHO "basic access" service level. A declared adequacy threshold — the quantity is well-established; the labour to deliver it is not measured anywhere in this repo. | —<br>DORMANT BUT ARMED. The water component carries `hours_per_unit=None`, so this multiplies into nothing today and becomes load-bearing the moment anyone prices water collection. Nothing would announce that transition, which is the reason it is tagged here rather than left in the basket module. |
| `BASKET_SHELTER_M2_PER_PERSON` | 12.0 | square metres of dwelling floor area per person | convention<br>form: the UN-Habitat adequacy framing for sufficient living space. A declared threshold, like the water service level above. | —<br>dormant like water and thermal — the shelter component carries `hours_per_unit=None`, so this multiplies into nothing today and is excluded rather than costed at zero. |
| `BASKET_THERMAL_DEGREE_DAYS_PER_YEAR` | 2500.0 | degree-days per person per year | placeholder (Tier D)<br>form: a temperate baseline, carried so the thermal component appears in the basket with its unit. It is never costed. | heating and cooling degree-days for the jurisdiction being modelled, against a stated indoor set-point. This is an instance quantity wearing a placeholder's clothes until the framework indexes by climate.<br>LATITUDE-DEPENDENT BY CONSTRUCTION, and that is the finding rather than a caveat: thermal is the one basket component where climate is the QUANTITY and not merely the delivery cost, so costing it makes the floor climate-indexed and PERSONAL_EOH_BASE cannot remain a single global scalar. |
| `BASKET_HEALTH_MIN_EPSILON` | 0.1 | automation level ε ∈ [0, 1] | normative<br>form: NOT a quantity like the three above — a CLASSIFICATION GATE. Below it, the health component is owed and undeliverable, so the floor reports it as `below_min_epsilon` rather than `unmeasured`, and excludes it either way. Unreachable is excluded, not zero: that is the personal floor's central behaviour and this constant is what exercises it. | **decided by** a charter judgement about where a delivery path begins to exist for interventions no quantity of unassisted human labour delivers — a caesarean, an antibiotic. No dataset returns this number, because the question is which interventions the collective commits to counting as owed.<br>precedent: the registration boundary is a different mechanism with the same shape — what the ledger recognises, versus what the basket physically contains.<br>_no measurement settles this_ |
<!-- /provenance:table -->

The age-weighted mean w = Σ(fraction × weight) = **1.3016** is the bridge from
per-working-age-*equivalent* to per capita, so `PERSONAL_EOH_BASE` = 1,000 is a
per-capita claim of **1,301.6 h/person·yr**. Forgetting that weight is the age-weight
trap `scenarios/feasibility.py` exists to catch.

w was **1.475** until 2026-08-10, when the `AGE_GROUPS` elderly weight was
revalued 2.5 → 1.48 on measurement (`scenario run care_curve`). Figures computed
at the old w are marked as such where they survive below; anything quoting 1.475
or 2,213 h/person·yr without that marking is stale.

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
| 0 | 0.000 | 1,953 | 0 | 1,953 | 0 | **neutral** |
| 250 | 0.090 | 1,778 | 9 | 1,787 | +166 | pays |
| 1,000 | 0.224 | 1,516 | 38 | 1,553 | +400 | pays |
| 4,145 | 0.361 | 1,248 | 155 | 1,403 | **+550 (optimum)** | pays |
| 20,000 | 0.427 | 1,120 | 750 | 1,870 | +84 | pays |
| 100,000 | 0.444 | 1,087 | 3,750 | 4,837 | −2,884 | **overbuilt** |

Regenerate with `eoh scenario run overbuild`. These moved with the 2026-08-10
elderly revalue — the autarky reference is `PERSONAL_EOH_SUFFICIENCY × w`, so a
lower w lowers the bar the apparatus has to clear, and the net gain at the
optimum fell from +644 to +550 h/person·yr. **The shape did not change**: there
is still an interior optimum near 4,145 TEH/capita and still a size past which
apparatus is pure overhead.

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
    demand  D(ε) = (1 − ε)·[w·B + R]     w = 1.3016 (was 1.475), B = PERSONAL_EOH_BASE
    feasible ⇔ D ≤ L   ⇒   B ≤ (L/(1−ε) − R) / w

> **Read this passage as of its date.** It is the finding that produced the
> 1,500 → 1,000 reprice, stated at the constants of the time: base 1,500 and
> w = 1.475. Both have since moved (the base on 2026-08-06, w on 2026-08-10),
> so the *numbers* below are historical. The *argument* is not, and it is why
> `scenarios/feasibility.py` exists.

**The constant is not 1,500 per capita.** It is 1,500 per working-age-*equivalent*,
and the age weighting w = Σ(fraction × eoh_weight) = 1.475 made the per-capita
claim **2,213 h/person·yr**. Because the extra weight on infants (3.0×) and
elderly (then 2.5×) is *caregiver* labour, all 2,213 hours still had to be supplied
by adults — the weighting raises demand without raising supply. Any feasibility test
run against the 1,500 figure understated the gap by 1.475×.

At today's constants the same identity gives 1,000 × 1.3016 = **1,301.6
h/person·yr**, and the lower w *loosens* the ceiling, since it appears in the
denominator of B ≤ (L−R)/w.

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

<!-- provenance:table "EOH generation — infrastructure domain" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `INFRA_MAINT_RATE` | 0.025 | fraction of capital stock, as EOH-hours per year | bounded | **band** 0.02–0.04 of capital stock per year (OECD public-capital maintenance series)<br>**errs** NEITHER. 0.025 sits in the lower half of the band. The larger problem is not the point but the PATH: this constant sits on the monetized route that scenarios/infrastructure_floor.py shows is doctrine-dominated 10.26×, so narrowing it inside the band buys very little.<br>it cites a 2–4% band and picks a point inside it. The statutory floor below is the better instrument and supersedes this in practice — a physical condition census in crew-hours, with no money→hours step. |
| `INFRA_AGE_FACTOR_MAX` | 2.0 | dimensionless multiplier at end of design life | placeholder<br>form: physics — maintenance burden really is convex in age. The DOUBLING is not. | measured maintenance hours against age for a single asset class, which the NBIS condition data behind INFRA_TREATMENT_HOURS_* could supply. |
| `INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT` | 24.0 | months between routine inspections | convention<br>form: the statutory routine inspection interval, adopted from 23 CFR 650 (US National Bridge Inspection Standards). A stated regulatory basis rather than a claim about the world, which is what `convention` marks. | the governing standard for the jurisdiction being modelled — the interval is whatever that jurisdiction's code says, and adopting a different code changes it legitimately. |
| `INFRA_TREATMENT_HOURS_GOOD` | 8.0 | labour-hours per asset unit per year | placeholder<br>form: task-normative — hours/unit/year = (12 / inspection_interval_months) × crew_hours_per_visit, currency-free by construction. This is the measured, auditable half of infrastructure EOH; discretionary maintenance ambition above it is a policy choice and enters the fiscal layer, never the floor. | state DOT maintenance-activity manuals and inspection timesheets, which record the real per-condition crew-hours. This is the nearest-to-closed CHOSEN debt in the file: the instrument exists, is public, and the units match.<br>the reason this stream exists — the monetized capital_stock_teh path is convention-dominated 10.26× while every physical knob on this path reads ×1.000 (scenarios/infrastructure_floor.doctrine_floor_invariance). The floor is ~5.9× better determined and its residual is timesheet-measurable. |
| `INFRA_TREATMENT_HOURS_FAIR` | 20.0 | labour-hours per asset unit per year | placeholder<br>form: task-normative — hours/unit/year = (12 / inspection_interval_months) × crew_hours_per_visit, currency-free by construction. This is the measured, auditable half of infrastructure EOH; discretionary maintenance ambition above it is a policy choice and enters the fiscal layer, never the floor. | state DOT maintenance-activity manuals and inspection timesheets, which record the real per-condition crew-hours. This is the nearest-to-closed CHOSEN debt in the file: the instrument exists, is public, and the units match.<br>the reason this stream exists — the monetized capital_stock_teh path is convention-dominated 10.26× while every physical knob on this path reads ×1.000 (scenarios/infrastructure_floor.doctrine_floor_invariance). The floor is ~5.9× better determined and its residual is timesheet-measurable. |
| `INFRA_TREATMENT_HOURS_POOR` | 48.0 | labour-hours per asset unit per year | placeholder<br>form: task-normative — hours/unit/year = (12 / inspection_interval_months) × crew_hours_per_visit, currency-free by construction. This is the measured, auditable half of infrastructure EOH; discretionary maintenance ambition above it is a policy choice and enters the fiscal layer, never the floor. | state DOT maintenance-activity manuals and inspection timesheets, which record the real per-condition crew-hours. This is the nearest-to-closed CHOSEN debt in the file: the instrument exists, is public, and the units match.<br>the reason this stream exists — the monetized capital_stock_teh path is convention-dominated 10.26× while every physical knob on this path reads ×1.000 (scenarios/infrastructure_floor.doctrine_floor_invariance). The floor is ~5.9× better determined and its residual is timesheet-measurable. |
<!-- /provenance:table -->

`INFRA_MAINT_RATE` sits on the *monetized* path that
`scenarios/infrastructure_floor.py` shows is doctrine-dominated (10.26× spread);
the statutory floor below exists to route around it. `CAPITAL_STOCK_DEFAULT` is
listed under [Fiscal architecture](#fiscal-parameters) — at 2,000 TEH/person it
produces infrastructure EOH ≈ 75M h/yr at mid-life, ≈ 3% of total EOH.

### Task-normative statutory floor (B+D design — currency-free)

The floor stream of `infrastructure_eoh_breakdown()`. These reprice the physical
condition census into hours **without** a money→hours conversion — the auditable
half. Motivated by `handoffs/Infrastructure`: the monetized `capital_stock_teh`
path moves 10× with the accounting doctrine and ×1.000 with every physical knob;
the floor moves only with the physical census (`scenarios/infrastructure_floor.py`
proves floor_spread = 1.000). 4-tag scheme with epistemic pointers:

The four floor constants appear in the generated table above. The residual 1.69×
determinacy gap is the good/fair/poor tiering, and it is measurable, not
conventional.

---

## EOH Generation — Ecological Domain

> **Scale warning.** `ECOLOGICAL_BASE_RATE` is documented as a *relative* anchor
> ("does not represent an absolute ecosystem-specific count") but is summed with
> absolute counts in `total_eoh()` and then divided into ε. At defaults it
> contributes 0.61 h/person·yr against personal's 1,301.6 — 0.04% of total EOH. See
> [Domain balance](#domain-balance-the-denominator-problem). Until it is put on
> an absolute footing, no result that depends on the ecological domain's *share*
> of total EOH should be quoted.

<!-- provenance:table "EOH generation — ecological domain" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `ECOLOGICAL_BASE_RATE` | 500000.0 | hours/year at pristine ecosystem health (relative anchor) | placeholder | a stewardship-hours census on an absolute footing — agency FTEs per hectare, or the GUF parcel inventory × measured crew-hours. The intake path now exists: core/eoh_generation.ecological_statutory_floor() takes the census in physical units and excludes unpriced parcels rather than costing them at zero, and scenarios/ecological_floor.floor_from_census() reports the ratio against this anchor, which is the falsification.<br>THE DOMAIN-BALANCE DEFECT LIVES HERE. This is documented as a RELATIVE anchor — "does not represent an absolute ecosystem-specific count" — but it is SUMMED with absolute counts in total_eoh() and then divided into ε. At defaults it contributes 0.04% of total EOH (0.61 h/person·yr against personal's 1,301.6), so the ecological domain cannot move ε and the thermal obligation books at ~1.8 h/person·yr. Do not quote this domain's SHARE of total EOH until it is on an absolute footing. THE GAP IS NOW MEASURED, not just asserted (2026-08-15, scenarios/ecological_floor.py). Inverting the question — what stewardship intensity would a given EOH share require? — the anchor implies 0.37 labour-hours per hectare per year across ALL land, every biome and condition class including cropland. Reaching a 5% share of total EOH needs 48.9 h/ha·yr, a factor of 132x; a 1% share needs 9.4, a factor of 25x. So "low by 2-3 orders" is not merely plausible, it is what the arithmetic requires. This still does NOT settle the level — no stewardship-hours census exists in this repo, and choosing a value to produce a target share would be the fitted-residual error the personal floor refuses. It states what a census would have to find. Run `eoh scenario run ecological_floor`. |
| `US_MAINLAND_HECTARES` | 765495267.0 | hectares | measured (Tier B)<br>form: USDA ERS Major Land Uses, "48 States" total land, 2022 vintage (released 2026-08-14): 1,891,580 thousand acres x 0.40468564224 ha/acre. | nothing — this is a published measurement. It moves only when ERS revises the series (5-year cycle).<br>THE REFERENCE FRAME FOR THE ECOLOGICAL DOMAIN. Stewardship demand is a property of AREA, so the domain needs an extensive quantity to be keyed to, and a test frame needs one that is measured rather than assumed. The contiguous 48 is chosen over the 915,052,512 ha US total because Alaska's 150 Mha is overwhelmingly unmanaged and would dilute every intensity by 16% for land no stewardship workforce reaches. Paired with US_POPULATION in reference/land_stewardship.py, it gives 2.285 ha/person against the shipped global LAND_HECTARES_PER_CAPITA of 1.65 — the US carries 38.5% MORE land per person than the planetary average, which is the direction that makes per-capita stewardship burden harder, not easier. |
| `ECOLOGICAL_INTENSITY_BASE` | 0.000653171902629 | labour-hours per hectare per year at pristine health | derived<br>form: ECOLOGICAL_BASE_RATE / US_MAINLAND_HECTARES. Bound by TEST rather than expression because ECOLOGICAL_BASE_RATE is defined above and the pairing is what must not drift; same treatment as GUF_ECO_KAPPA_CARBON. | scenarios/land_stewardship.census_report() — the measured stewardship-hours census. At the declared amenity weight it reads 0.585 h/ha/yr, ~900x this value, over 30% of censused area.<br>THIS IS THE DOMAIN-BALANCE DEFECT, QUANTIFIED. Before this constant existed, `ecological_eoh` took no area and no population — it returned base_rate/health and nothing scaled it, making ecological the ONLY domain with no extensive quantity behind it (personal scales with population, infrastructure with capital, knowledge with the corpus). Spread over the land it is nominally the obligation for, the shipped anchor is 6.5317e-4 h/ha/yr — **2.35 SECONDS per hectare per year**. Introducing it changes NO number: area x intensity reproduces ECOLOGICAL_BASE_RATE exactly at the reference frame, so this commit fixes the FORM and leaves the LEVEL for the census to move. Note this disagrees 464x with `scenarios/ecological_floor .implied_stewardship_intensity`, which reports 0.37 h/ha/yr — the SAME anchor over a different area (1e6 people x 1.65 ha). Both are correct and the disagreement IS the point: an anchor keyed to nothing implies whatever per-hectare figure the area you supply happens to produce. |
| `AMENITY_STEWARDSHIP_WEIGHT` | 0.0468 | dimensionless fraction of amenity labour | bounded (Tier C) | **band** every admissible weight puts the census above the anchor, so the choice of w sets the magnitude and not the sign.<br>**errs** LOW. The lower bound is adopted, so the ecological obligation is understated. That is the conservative direction for the open question — a floor that errs low cannot manufacture the "anchor is orders too low" finding it is being used to test — but it is the UNSAFE direction for provisioning, since under-booking stewardship under-provisions it. Flagged rather than split, because splitting would put a fitted number where a composition-derived one now sits.<br>a task decomposition within SOC 37-3011 — what fraction of groundskeeping hours go to woody vegetation versus turf. Municipal urban- forestry program staffing against total grounds-maintenance staffing is the nearest public instrument; i-Tree Eco's urban-forestry surveys are the other.<br>AUTHOR DECISION 2026-08-16 (the amenity-scope sign-off). Urban groundskeeping counts as ecological EOH to the extent it maintains a structure delivering one of the seven GUF services — canopy in, turf out. The two corners are 0.0 and 1.0 and differ 50x in the census, so a weight had to be named. Note the anchor is crossed at w* = 0.0228, BELOW this |
| `AGENCY_STEWARDSHIP_ROLE_MIX` | 0.2263 | dimensionless fraction of agency headcount | bounded (Tier B) | **band** [0.2263, 0.4073] — NPS + FWS combined, from record-level OPM Federal Workforce Data (employment 2025-09 v3, 27,104 staff, 337 occupational series). LOWER bound counts only unambiguous resource-management series (0401 general natural resources, 0404 biological science technician, 0454 rangeland, 0460/0462 forestry, 0470 soil science, 0482 fish biology, 0485 refuge management, 0486 wildlife biology, 1315 hydrology and neighbours). UPPER adds the two genuinely split series: 0456 wildland fire management (fuels treatment and prescribed burning against emergency response) and 0025 park ranger (resource protection against interpretation).<br>**errs** LOW. The lower bound is adopted, matching AMENITY_STEWARDSHIP_WEIGHT's treatment of the same shape of ambiguity, so agency stewardship is understated. 0025 alone is 3,991 NPS staff who do some of both.<br>a task decomposition inside series 0025 and 0456 — the share of park-ranger and wildland-fire hours spent on resource condition rather than visitors and response. NPS budget justifications report FTE by activity (Resource Stewardship vs Visitor Services vs Facility Operations) and are the direct instrument; they would replace this band with a measured split.<br>THE TWO AGENCIES DISAGREE BY 5.3x AND THAT IS THE INTERESTING PART. NPS reads 10.12% (its largest series are park ranger 20.7% and maintenance mechanic 13.9%); FWS reads 53.64% (its largest is general natural resources at 27.8%). NPS is a visitor-services organisation standing on land; FWS refuges are a land-management organisation. A single federal "agency stewardship" rate would have concealed that, which is why the census splits them and this constant is only the combined summary. IT ALSO OVERTURNED A DIRECTIONAL CLAIM. Before the role mix was measured, the RAW agency intensity (0.709 h/ha/yr combined, 1.090 for NPS) suggested agency land was worked ~6x harder than forest and would RAISE the census. Role-mix-corrected it is 0.16-0.29 h/ha/yr, comparable to forest's 0.182 and BELOW the declared census mean of 0.585 — so pricing it LOWERS the mean and raises coverage. The raw figure was wrong by the size of the role mix, which is exactly why the class was not priced on it. |
| `US_REFERENCE_POPULATION` | 335000000.0 | persons | placeholder (Tier C)<br>form: the population the frozen O*NET/BLS registry's employment is drawn against (reference epoch 2026-07-29 -> 2024 vintage weights), stated round. | Census Bureau national population estimate for the reference epoch. The shipped figure is round to three significant figures and the estimate is not, so this closes on contact with the source.<br>MIGRATED FROM TWO PLACES AT ONCE (2026-08-16). The same value lived as `REFERENCE_POPULATION_US` in scenarios/knowledge_base.py and as `US_POPULATION` in reference/land_stewardship.py — one value, two names, two files, neither under the gate. That is the fifth instance of the pattern behind GUF_PSI_NORM, RECAL_FOUNDING_LABOR_HOURS, DEFAULT_SEGMENTS and the mean-multiplier literal: a copy of a value whose source is elsewhere. Both names now bind here. Its epistemic status is UNCHANGED by the move — it was debt before and it is debt now, only visible. |
| `PRACTICE_EQUIPMENT_WIDTHS_FT` | <dict: 7 keys> | feet | instance | **you supply** the working width of the equipment YOUR collective actually operates. Field capacity is linear in width, so these values scale the reported stewardship hours one-for-one: halving a width doubles the hours.<br>**shipped default** mid-range North American row-crop equipment, so the shipped practice figures have a stated scale rather than none. NOT a measurement and not a published standard — the ASAE table supplies efficiency and speed because those are properties of the operation, and deliberately omits width because it is a machine-size CHOICE.<br>this is the input that makes hours-per-acre a DELIVERY PRODUCTIVITY rather than a physical constant, the same role the LSMS unassisted stratum plays in reference/personal_basket.py. It lived in reference/ until 2026-08-16, where the shadow-constant ratchet could not see it — utils.provenance.OPERATIVE_LAYERS omits that layer — which is why it moved rather than the layer boundary moving. |
| `LAND_HECTARES_PER_CAPITA` | 1.65 | hectares of land per person | instance | **you supply** the land area your collective is responsible for stewarding, divided by its population. Intake path: the GUF parcel inventory (land/collective.py) already carries area per parcel, so a collective that has run its GUF assessment has this figure without new survey work.<br>**shipped default** global land area excluding Antarctica (~1.34e10 ha) over a world population of ~8.1e9. A planetary average is the WRONG number for any actual collective — stewardship land per person varies by more than an order of magnitude between a city and a rangeland — and it is here only so scenarios/ecological_floor.py can state the inversion at a stated scale. |
| `WORLD_POPULATION` | 8100000000.0 | persons | measured (Tier A)<br>form: world population, UN World Population Prospects 2024 revision, mid-2025 estimate rounded to two significant figures at the scale it is used. | nothing — a published measurement. It moves when the UN revises (2-year cycle).<br>this number already governed a shipped constant while existing only as PROSE. LAND_HECTARES_PER_CAPITA = 1.65 is documented as "~1.34e10 ha over a world population of ~8.1e9", so the divisor was carried in a comment where nothing could read it, check it or age it. Naming it makes the global frame in JURISDICTION_FRAMES derivable instead of restated — the same move that bound US_POPULATION and REFERENCE_POPULATION_US to one source. |
| `REFERENCE_FRAME_POPULATION` | 1000000.0 | persons | convention<br>form: the population at which this package's extensive TEH constants are stated. CAPITAL_STOCK_DEFAULT and TRUST_BASE_TEH both say "TEH (at the 1M reference population)" in their own tag blocks; this names the population those sentences refer to. | —<br>A THIRD QUANTITY THAT MUST TRAVEL WITH THE FRAME, and the one that hides. Land and population are the visible pairing, but capital is stated per-frame too, so running the US population against an unscaled CAPITAL_STOCK_DEFAULT models 335M people holding the capital stock of 1M — 5.97 TEH/capita against 2,000. It was found by a frame-invariance test failing at 5.7% while the other two domains agreed exactly, not by reading the constant. What the frame holds fixed is capital INTENSITY, not the absolute stock. |
| `FRAME_CONSISTENCY_TOLERANCE` | 0.1 | fraction | normative<br>form: the band around a declared frame's hectares-per-capita within which a supplied (population, area) pairing is called consistent with it. | **decided by** a reporting threshold, chosen. No dataset settles what counts as "the same frame"; the same status as the dashboard health thresholds, and like them it governs a label rather than a quantity.<br>_no measurement settles this_<br>deliberately WIDE. The question it answers is "is this the same order of land per person", not "do these agree to the hectare" — the mismatch it exists to catch is 335x. A tight tolerance would reclassify ordinary collectives as inconsistent and make the check noise. |
| `JURISDICTION_FRAMES` | <dict: 3 keys> | dict of frame name -> {population: persons, land_hectares: ha} | convention<br>form: DECLARED PAIRINGS of a population with the land area it is responsible for. Every value is BOUND to the constant that already carries it — US_REFERENCE_POPULATION, US_MAINLAND_HECTARES, LAND_HECTARES_PER_CAPITA — rather than restated. A frame that restated 335,000,000 would be the sixth copy-of-a-value-whose-source-is-elsewhere, after GUF_PSI_NORM, RECAL_FOUNDING_LABOR_HOURS, DEFAULT_SEGMENTS, the mean_multiplier literal and US_POPULATION itself. | —<br>THE FRAME MISMATCH THIS EXISTS TO MAKE VISIBLE. ECOLOGICAL_BASE_RATE is the obligation for the WHOLE contiguous US (765,495,267 ha), while the shipped default population across the package is 1,000,000. Nothing connects them, so the ecological domain is divided by a millionth of the population that lives on the land it is keyed to, and the reported ecological SHARE is frame-dependent by a factor of 335: 0.0448% at the shipped pairing against 0.000146% at the honest US one. The shipped default is the FLATTERING reading. `reference_1m` is the consistent million-person frame — the US land-per-person ratio, not the whole US. REPORTING ONLY at introduction: no generation function consumes this and no shipped number moves. Making the default frame consistent is a calibration change and needs sign-off, because it moves the ecological anchor 335x. |
| `ECOLOGICAL_THRESHOLD` | 0.4 | ecosystem health index ∈ [0,1] | placeholder<br>form: physics — ecological regime shifts are established, so a threshold below which burden escalates nonlinearly is structural. Where 0.40 falls on THIS index is a mapping, not a measurement. | an ecological time series relating a defined health index to observed regime shift. GUF_EOH_ACCUMULATION_THRESHOLD makes the same class of claim on the deferral rate rather than the state; both resolve from one series. |
<!-- /provenance:table -->

That ecosystems exhibit nonlinear regime shifts is established (Scheffer et al.
2009); that the shift sits at 0.40 of *this* health index is a framework mapping.

**Not in `data.py`, so outside the coverage gate.** `_ECOLOGICAL_SPIKE_INTENSITY`
(5.0, dimensionless spike multiplier) lives in `hours_eoh/core/eoh_generation.py:47`,
not in `data.py` — a standing violation of the no-anonymous-constants invariant that
says every numeric literal in domain logic is a named constant in `data.py`. It is
`CHOSEN`: reverse-engineered from a target ("calibrated to produce an EOH doubling
within ≈10% below threshold"), which makes it a knob by construction. Post-collapse
restoration labour records would measure the true post-threshold slope. **Moving it
into `data.py` would bring it under the gate**; until then the retag log covers a
constant the generated tables cannot see.

---

## EOH Generation — Knowledge Domain

<!-- provenance:table "EOH generation — knowledge domain" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `KNOWLEDGE_EOH_BASE` | 523612102.71 | embodied knowledge-hours (STOCK) at the ε=0 reference, at KNOWLEDGE_REFERENCE_POPULATION | derived-then-FROZEN<br>form: recovered from the O*NET 30.3 / BLS spine already shipped in reference/data/ by inverting the documented log-minmax normalization of f_training: 11,001.3 h/worker embodied training stock over 751 occupations → 5,501.0 h/person at E/P = 0.500 → de-anchored to ε=0 by ÷ kbs(ε*)·cpu(ε*). Anchor and base are solved TOGETHER at the fixed point ε* = 0.3828 (scenarios/knowledge_base.epsilon_ref_fixed_point, 6 damped iterations), because a one-shot anchor cannot be self-consistent when the constant it sets sits inside the quantity that checks it. FROZEN against data-vintage churn; it FOLLOWS internal drift, because a change to any constant inside total_eoh changes the derivation's own inputs. Re-anchored 2026-08-09 (Finding E, ε* 0.4522), 2026-08-10 (the AGE_GROUPS elderly revalue, ε* 0.3828), 2026-08-16 (SKILL_WORKING_LIFE_YEARS measured at 37.5, ε* 0.38689) and 2026-08-17 (the Phase-4b frame resolution, ε* 0.386619). THE THIRD RE-ANCHOR IS THE CHEAPEST AND THE MOST REASSURING: a 6.7% rise in the renewal rate moved this constant by −2.0%, because the fixed point absorbs most of it. The coupling is real and it is damped, which is the property a one-shot anchor could not demonstrate. THE FOURTH IS SMALLER STILL — +0.13% — and it says something about the model rather than about this constant: the ecological domain was corrected DOWNWARD by 464× and the knowledge base barely moved, because ecological is so small a share of total_eoh that even a 464× error in it is nearly invisible to everything downstream. That is the domain-balance defect restated as a sensitivity, and it converged in ONE iteration. | an O*NET/BLS vintage refresh moves it mechanically; the ANCHOR resolves by whatever settles Finding B. The capital-inventory route is unusable (Finding A).<br>THE ANCHORING ASSUMPTION IS THE UNCERTAINTY, NOT THE MEASUREMENT. Across ε_ref ∈ [0.2, 0.6] the constant moves 7.13×, against only 1.20× from the per-capita route. What the fixed point does NOT fix: the anchor is still 937.3 h/person·yr of US PAID labour, so it removes the self-inconsistency, not the US-specificity or the paid-labour convention — and the full-labour reading has no solution at all (supply exceeds the whole obligation; Finding B). tests/test_knowledge_base.py asserts the frozen value still matches the live derivation, so a registry refresh fails loudly rather than drifting. |
| `KNOWLEDGE_EPS_EXPONENT` | 2.0 | dimensionless exponent | placeholder<br>form: physics — knowledge EOH grows superlinearly with ε, because complexity compounds. The exponent is asserted. | measured knowledge-maintenance hours against an automation index at three or more points, which is what distinguishes an exponent from a slope. |
| `KNOWLEDGE_REFERENCE_POPULATION` | 1000000.0 | persons | convention<br>form: a stated denominator, not a claim about the world — the population KNOWLEDGE_EOH_BASE is quoted at. It exists because knowledge EOH was population-INVARIANT: the same absolute number came back at 1M and at 300M, so the domain's share of total EOH fell as 1/population while every other domain scaled. 1e6 is the repo-wide default population, so this reproduces prior output exactly at the default. | n/a — a convention is settled by declaring it, which this does. |
| `SKILL_DECAY_RATE` | 0.1 | fraction of the knowledge stock renewed per year | placeholder<br>form: DEPRECATED as of Block K-IV — retained, not deleted, per the additive-not-destructive rule. Nothing defaults to it; the default renewal rate is SKILL_TRANSMISSION_RATE. Kept because it is the value every pre-K-IV result in this repo was produced at, so reproducing an old figure means passing it explicitly rather than guessing what it was. | **RETIRED** — superseded by SKILL_TRANSMISSION_RATE + SKILL_CPD_RATE<br>nothing. It is not awaiting a measurement; the measurement happened and replaced it. The split that did so is SKILL_TRANSMISSION_RATE (cohort turnover, now measured) and SKILL_CPD_RATE (Eurostat CVTS paid training hours), whose sum is 0.0294 against this 0.10. That gap is a finding, not an error to reconcile away. 2026-08-15: THE LAST COMPUTING PATH WENT. core/eoh_fulfillment .eoh_to_teh_pipeline was passing a bare 0.10 literal — an unbound COPY of this value, not a read of it — straight into total_eoh(), overriding the SKILL_TRANSMISSION_RATE default that knowledge_eoh() had already adopted. The pipeline was computing knowledge EOH 4× the direct path. 2026-08-16: RETIRED, and the gate had to learn a distinction first. The last PARAMETER DEFAULT was `decay=` on knowledge_base_from_registry, which set the reported arc level under the refuted doctrine; it now points at SKILL_TRANSMISSION_RATE. What remains is four reads in two modules, all of the same shape — this value printed BESIDE the split so the disagreement stays visible. That is a documented negative result, not a second parameter running in parallel, and the old gate could not tell the two apart because it asked "is it mentioned?". `baseline_in:` states the claim, and `problems()` checks it: every reader named, and — the condition that cannot be waived — no parameter default anywhere, verified by AST rather than by regex. Retiring it this way keeps the credibility finding on the CLI (`scenario run knowledge_base`) instead of exiling it to research/ to make a counter go down.<br>IT WAS NEVER A RENEWAL RATE. At 0.10 against the measured 11,001 h/worker stock it implies 1,100 h/worker·yr — 55% of the H_REF work-year spent forever re-acquiring knowledge already held. No time-use or training series reports anything close. It was also CONFLATING two rates that Block K-III separates: transmission (cohort turnover) and CPD (staying current while working). |
| `SKILL_WORKING_LIFE_YEARS` | 37.5 | years, entry to retirement | measured (Tier B)<br>form: Eurostat `lfsi_dwl_a`, "duration of working life" — the average number of years a person aged 15 is expected to remain in the labour force (employed or unemployed), computed from life expectancy and age-specific participation rates. That IS the cohort-exit construction this constant needs, published annually. EU 2025: 37.5 years overall, 39.5 men, 35.4 women. The EU aggregate is adopted rather than either sex-specific figure. | a US duration-of-working-life series on the Eurostat construction — age-specific participation rates against a current life table. CPS and NCHS both publish the inputs; nobody publishes the product.<br>TIER B, NOT A, FOR A NAMED REASON: the series is EU-27, while the knowledge domain's ε_ref anchor is US paid labour (937.3 h/person·yr). No current US equivalent exists to reconcile it against — BLS ceased publishing worklife tables, and the last (Smith 1986) rests on 1979–80 labour-force behaviour, which is older than the gap it would close. The jurisdiction mismatch is therefore unavoidable rather than a shortcut, and it is the whole of the Tier B reservation. Direction is not withheld: EU participation among older workers runs below the US, so 37.5 is more likely an UNDERSTATEMENT of a US working life, which makes transmission an OVERSTATEMENT — the conservative side, since it raises the renewal obligation rather than flattering it. |
| `SKILL_TRANSMISSION_RATE` | 0.0266666666667 | fraction of the knowledge stock renewed per year | derived<br>form: 1 / SKILL_WORKING_LIFE_YEARS = 0.02667. Transmission is the stock being re-created as cohorts retire — knowledge dies with people, which is the entropy this domain measures (framing accepted by the author 2026-08-08). Adopted as the default renewal rate in Block K-IV because it is the LOWER of the two credible doctrines and the only one containing no CHOSEN component. | n/a — it inherits SKILL_WORKING_LIFE_YEARS's standing, which is now a measurement rather than a choice.<br>THE FIRST ANCHORED DERIVATION IN THE FILE. Until 2026-08-16 this was `derived` from a `placeholder`, which the chain audit found by tracing the graph rather than reading one level — and it mattered more than the tag suggested, because the working life has ZERO direct consumers in core/land/scenarios and reached 14 call sites only through this constant. Every blast-radius scan that looks at code read it as inert. Now that the parent is measured, `band_from` can be claimed and the transitive gate (utils/provenance.unanchored_ancestors) verifies it. |
| `SKILL_CPD_RATE` | 0.0027 | fraction of stock renewed per year by continuing practice | bounded<br>form: the recurring hours a WORKING practitioner spends staying current — the term O*NET structurally cannot supply, because it measures the hours to REACH competency, never the hours to HOLD it. ~30 h/worker·yr economy-wide against an 11,001 h stock gives 0.0027, from the licensure scale (US state boards mandate 20–50 h per two-year cycle for licensed occupations, ~a quarter of employment) and Eurostat CVTS (~25 h per participating employee·yr at ~40% participation). | **band** ≈10–30 h/worker·yr economy-wide — US state boards mandate 20–50 h per two-year cycle for licensed occupations (~a quarter of employment), and Eurostat CVTS reports ~25 h per participating employee·yr at ~40% participation. Against the measured 11,001 h/worker stock that is ≈0.0009–0.0027.<br>**errs** LOW. At the top of that band, and then EXCLUDED from the shipped default anyway, so the adopted renewal rate understates the obligation by ~10.8% deliberately — the same posture the thermal layer takes when it withholds a budget whose sign is undetermined: prefer a defensible understatement to an unbacked completion.<br>Eurostat CVTS (paid training hours per employee, all sectors), the single public series that measures this term directly.<br>THE LEAST-GROUNDED NUMBER IN BLOCK K-III, and EXCLUDED FROM THE DEFAULT — not denied. skill_renewal_rate() still returns the sum and a caller who wants the fuller obligation passes it. The adopted default therefore UNDERSTATES renewal by ~10.8%, deliberately, so no CHOSEN number rides in the shipped arc — the same posture the thermal layer takes when it withholds a budget whose sign is undetermined. |
<!-- /provenance:table -->

**Closed 2026-08-08 (Block K-IV), re-anchored 2026-08-09 (Finding E).** The
pointer used to name O\*NET/BLS training hours, and the registry already carried
them: `f_training` is tagged "log-minmax of measured hours", so
`hours = exp(lo + f·(hi−lo))` inverts it exactly. Employment-weighted mean
**11,001 h/worker** over 751 occupations / 157.79 M employment → 5,501 h/person at
E/P = 0.500, de-anchored by ÷ kbs(ε\*)·cpu(ε\*). **Residual uncertainty is the
ANCHOR, not the measurement**: 7.13× across ε_ref ∈ [0.2, 0.6] against 1.20× from
the per-capita route. Sweep with `arc --knowledge-epsilon-ref`.

**The renewal-rate split (Blocks K-III/K-IV).** `SKILL_DECAY_RATE` = 0.10 was
conflating two orthogonal rates: transmission (cohort turnover, derivable) and CPD
(staying current, not in O\*NET). Set independently they sum to **0.0277 against
the shipped 0.10** — and against the measured 11,001 h/worker stock, 0.10 implies
**1,100 h/worker·yr = 55% of the `H_REF` 2,000 h work-year, every year, forever**.
No time-use or training series supports it; the shipped value was never a renewal
rate. The author's decision (2026-08-08) was to adopt **the lower rate**:
transmission alone, the only doctrine containing no CHOSEN component. This
deliberately **understates** renewal by ~10.8% rather than let a judgement call
ride in the shipped arc.

**Not in `data.py`, so outside the coverage gate.** The `skill_decay_rate`
*parameter* in `EohParams` now defaults to **0.025** (bound to
`SKILL_TRANSMISSION_RATE`), not the 0.10 module constant. Parameter defaults are a
second surface with its own provenance question, and the gate covers `data.py` only.


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
> derivation) took 0.779× off the base. The 2026-08-10 AGE_GROUPS elderly
> revalue then cut personal EOH 11.76% and moved the fixed point AGAIN, taking
> the base up 1.397× to 1.089× the original K-IV value. The share now runs
> **98.9% → 46.1%**. The table below is the current picture; the pre-adoption
> figures are kept in the second table for comparison.
>
> **CORRECTED 2026-08-10.** This block previously reported the share as
> 98.9% → **78.6%** and drew a finding from it — that the two moves "pulled in
> opposite directions" and personal's share at ε = 0.99 "ended HIGHER than after
> K-IV, not lower (56.2% → 78.6%)". **That was wrong, and so was the finding.**
> Measured against `arc --domain-shares` at the shipped constants, personal ends
> at **46.1%**, not 78.6% — *lower* than the 56.2% K-IV left it, not higher. The
> ε = 0.40 and ε = 0.99 columns of the table below were wrong in the same pass
> (infrastructure and knowledge were also transposed at the top of the arc). The
> ε = 0 column was correct throughout. **The two moves compounded in the same
> direction: both cut personal's share at the top of the arc.**
>
> This is worth recording rather than quietly patching. The provenance gate
> covers tag blocks in `data.py`; it cannot check a hand-written share table in
> prose, and this section says so a few paragraphs down. Here is that residual
> producing not a stale number but an **inverted conclusion** — the kind of
> error the gate was built to make impossible for constants and demonstrably
> still permits for narrative.
>
> **What is still open.** `ECOLOGICAL_BASE_RATE` is untouched and the ecological
> domain is still ~0.04% of total EOH at 0.61 h/person·yr — the "relative anchor
> summed with absolute counts" defect is unresolved. And personal still dominates
> the LOW arc (98.9% at ε=0), where there is no apparatus for knowledge to attach
> to, so `PERSONAL_EOH_BASE` and ATUS still own the denominator there. **Two of
> the three original consequences stand**: ε remains a personal-domain number at
> low ε, and the thermal obligation is still ~0.1% of the ledger.
>
> **THE ECOLOGICAL GAP IS NOW MEASURED RATHER THAN ASSERTED** (2026-08-15,
> `scenarios/ecological_floor.py`). The level cannot be fixed — no
> stewardship-hours census exists in this repo, and picking a value to produce a
> respectable share is the fitted-residual error the personal floor was built to
> refuse. So the question was inverted instead, which the data *can* answer:
> **what stewardship intensity would a given EOH share require?**
>
> | Ecological share of total EOH | Required stewardship | Against the anchor |
> |---|---|---|
> | *shipped anchor* | **0.37 h/ha·yr** | — |
> | 1% | 9.4 h/ha·yr | 25× |
> | 5% | 48.9 h/ha·yr | **132×** |
> | 10% | 103.3 h/ha·yr | 280× |
> | 25% | 309.9 h/ha·yr | 839× |
>
> *(at a planetary-average 1.65 ha/person — a figure that is wrong for any actual
> collective and is there only to state the inversion at a stated scale.)*
>
> The anchor implies **under one labour-hour per hectare per year across all
> land** — every biome and condition class, cropland included. Stated that way it
> does not need refuting: it plainly is not an absolute stewardship figure, which
> is what its own tag says. So "low by 2–3 orders" is not merely plausible, it is
> what the arithmetic requires — and the claim is now falsifiable by any census
> that reports agency FTEs per hectare. The intake path exists:
> `ecological_statutory_floor()` takes the census in physical units and
> **excludes** unpriced parcels rather than costing them at zero, and
> `floor_from_census()` reports the ratio against this anchor.
>
> Reproduce with `python3 utils/eoh_cli.py arc --domain-shares` and
> `python3 utils/eoh_cli.py scenario run ecological_floor`.

### Current (post-K-IV, re-anchored three times to the ε_ref fixed point)

Canonical-arc figures, re-measured 2026-08-16 from
`python3 utils/eoh_cli.py --no-color arc --domain-shares --points 100`:

| Domain | ε = 0 | ε = 0.40 | ε = 0.99 |
|---|---|---|---|
| personal | 98.9% | 84.4% | 45.2% |
| infrastructure | 0.0% | 5.4% | 7.7% |
| knowledge | 1.1% | 10.2% | **47.1%** |
| ecological | <0.1% | <0.1% | <0.1% |

*At the top of the arc knowledge is now the LARGEST single domain — 47.1%
against personal's 45.2%. It crossed over on 2026-08-16, when
`SKILL_WORKING_LIFE_YEARS` was measured at 37.5 years (Eurostat `lfsi_dwl_a`)
against the chosen 40: the renewal rate rose 6.7% and knowledge rose with it,
while personal did not move at all. The previous reading of this table — "now
co-equal with personal", 46.0% against 46.1% — held for six days.*

*This is worth stating plainly because the crossing is not robust. The two
domains are within two points of each other, the constant that separates them
is a 6.7% correction, and knowledge's level is set by an anchor that has now
moved four times, none of them for a knowledge-domain reason. Read the ordering
as "personal and knowledge are the same size at the top of the arc, and which
one leads depends on a constant we have measured once"; do not build an
argument on which side is ahead. Infrastructure never exceeds 7.7%.*

*The ε = 0 column reads 98.9% personal / 0.0% infrastructure because Block III
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

## Retag log (2026-08-09)

The migration finished: 101 constants that appeared nowhere in this document, and
nine tables still on the retired binary scheme. No *value* changed — verified
constant-by-constant against the previous commit, 228 compared, 0 differences.

### The CHOSEN split (added 2026-08-09, after the migration)

`CHOSEN` was retired into `bounded` / `placeholder` / `normative`. The reasoning is
in [The tag scheme](#the-tag-scheme) above; the counts are 14 / 106 / 60. Notable
placements:

| Went to | Examples | Why |
|---|---|---|
| **bounded** | `PERSONAL_EOH_BASE` (band 390–1006, errs HIGH), `INFRA_MAINT_RATE` (OECD 0.02–0.04), `THERMAL_LAMBDA_FEEDBACK` (1.2–1.7 across AR6/historical), `SKILL_CPD_RATE` (10–30 h/worker·yr from licensure + CVTS), `DEP_RATE` (0.045–0.05 against the derived 1/20) | A measured band exists and the pick sits inside it. The band travels with the number, and so does the direction of error. |
| **normative** | `M_BAND_*`, `M_MAX`, `M_FLOOR`, `DIV_RATE`, `ESTATE_*`, `ACCUMULATION_CEILING_MULTIPLIER`, `THERMAL_PROGRAMME_YEARS`, `CDR_ALLOCATION_BASIS`, all 10 dashboard thresholds, all 5 `MEMBERSHIP_*`, the GUF permitted ranges and subsidy schedule | Decisions. `THERMAL_PROGRAMME_YEARS` calls itself "an ETHICAL choice"; the dashboard block's own header says these govern "when the framework raises its hand, not what is physically true". |
| **placeholder** | `ABATEMENT_HALF_CAPITAL_TEH`, `ECOLOGICAL_BASE_RATE`, `THERMAL_DT_LO`, `THERMAL_IOTA_FLOOR_*`, `CONTESTABILITY_MIN_VIABLE_POPULATION`, 46 of the 51 `GUF_*`, `CAPITAL_MACHINE_PROFILES` | Nothing constrains them yet. **This is the list to drive down.** |
| **convention** | the eight `CANONICAL_*` arc constants | An ideal-arc reference *frame*, not a claim about any trajectory — their own pointer already said "nothing, and by design", which is what a convention is. |

Two judgement calls worth flagging, since both could reasonably go the other way:
`CONTESTABILITY_CHI_CRIT` = 1.00 is very nearly definitional (χ < 1 means exit is
notional) but is tagged `normative`, because declaring 1.0 the breach point is still
the framework's declaration. And `ETA_LAND_MASK_THRESHOLD` = 0.50 is a threshold on a
*measured* ERA5 field, tagged `normative` because where the line falls decides which
collectives bear an allocation.

### Tags that moved

| Parameter(s) | Was | Now | Why |
|---|---|---|---|
| `M_BAND_LOW`, `M_BAND_HIGH`, `M_BAND_TARGET`, `M_MAX` | Physics | **CHOSEN** | The justification given was "below 1.8 the differential between labor tiers is too small to reflect real skill differentials" — an argument about fairness and legitimacy, not about entropy. A **constitutional** commitment: the strongest reason to hold it, and no reason to call it physics. |
| `ALPHA_SCALE` | Physics | **derived** | Genuinely computed as `M_MAX − 1`; it moves when the cap moves. Inherits `M_MAX`'s standing. |
| `DEP_RATE`, `DIV_RATE` | Physics | **CHOSEN** (`physics` form) | That capital depreciates and that a payout/renewal split exists are structural. 4.5% and 40% are not. |
| `H_MIN`, `COMPETENCY_THRESHOLD` | Physics | **CHOSEN** | Both are single economy-wide numbers standing in for domain-specific quantities. `COMPETENCY_THRESHOLD`'s three significant figures imply a precision nothing supplies. |
| `CONTESTABILITY_CHI_CRIT`, `CONTESTABILITY_PHI_FLOOR`, `CONTESTABILITY_K_FLOOR_FRACTION` | Physics | **CHOSEN** | Proposed functional forms, never calibrated — as the block header always said. χ ≥ 1 is definitional, but the invariant it served is superseded by §8.9. |
| `MEMBERSHIP_MIN_HOURS_CRIT_FRACTION` | *Physics-adjacent* | **CHOSEN** | An ad-hoc fifth tag, now retired. The vocabulary is closed and tested. |
| all 51 `GUF_*` | (undocumented) | **CHOSEN** | See the NLSA warning below. |
| `COASEAN_COMMONS_TITHE`, `COASEAN_INDIVISIBLE_RESERVE_FRACTION`, `RECAL_CAPITAL_OUTPUT_RATIO`, `RECAL_ACCOUNT_CREDIT_SHARE` | Calibration | **convention** | Each names a specific external instrument — Italian Law 59/1992's 3% mutual-fund contribution, the statutory ~30% indivisible reserve, Piketty's β, Mondragon's internal capital accounts. Naming a real instrument is stronger than "calibration". |
| `INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT` | measured | **convention** | 23 CFR 650 is a regulation, not a measurement. It resolves by adopting a different jurisdiction's code, which is a legitimate change rather than a correction. |
| `H_REF`, `KNOWLEDGE_REFERENCE_POPULATION`, `SECONDS_PER_YEAR` | Calibration / physics | **convention** | Stated denominators. `SECONDS_PER_YEAR` is the Julian year; the choice matters at the fourth significant figure. |
| `CO2_PPM_TO_GT` | physics | **derived** | Arithmetic from atmospheric mass and molar masses — derivable, but not itself a structural claim. |
| `SKILL_TRANSMISSION_RATE`, `PP_INDEX_WARN_SLOPE`, `BASKET_EOH_CONTENT`, `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE`, `MEMBERSHIP_VESTING_WARN_YEARS`, `FORMATION_DEPRECIATION_RATE`, `BASE_LIFETIME_EARNINGS_TEH` | Calibration | **derived** | Each is computed from, or defined equal to, another constant. Three of them (`RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE`, `MEMBERSHIP_VESTING_WARN_YEARS`, `BASE_LIFETIME_EARNINGS_TEH`) restate a literal instead of binding to their source, and should be bound. |

**Net distribution over all 228 constants:** `CHOSEN` 190 (83.3%), `measured` 13,
`derived` 9, `convention` 8, `derived-then-FROZEN` 6, **`physics` 2**. Two. The
scheme's own definition of *physics* is demanding, and applying it honestly leaves
almost nothing: `A_EARTH_M2` and `SIGMA_SB`.

### Drifts this pass found and fixed

| What | Was | Now |
|---|---|---|
| `KNOWLEDGE_EOH_BASE` (doc) | 490,107,421 | 533,620,818.74 — re-anchored twice: the ε_ref fixed point (2026-08-09) then the AGE_GROUPS elderly revalue (2026-08-10) |
| `CARE_SIGMOID_DEFAULTS` (doc) | start_share 0.30, inflection 0.55 | 0.05 / 0.45 — the doc had never matched the code |
| membership min-hours thresholds (prose) | 750 / 1500 h/yr | 500 / 1,000 — fractions of `PERSONAL_EOH_BASE`, stale since the reprice |
| per-capita personal EOH (prose) | 1,500 × 1.475 = 2,213 | 1,000 × 1.475 = **1,475** |
| `RECAL_FOUNDING_LABOR_HOURS` rationale | "≈ 2/3 of `PERSONAL_EOH_BASE`" | it is now **100%** of it; the reprice moved the base and orphaned the rationale |

The last three are *derived products* restated in sentences, which no
value-equality check can see. That is why the gate includes a curated test over
exactly those figures — the drift hid where the structured check could not look.

### Findings, reported rather than smoothed

**NLSA cites this framework's own document.** The Ground Use Fee block attributes
every constant to "NLSA Technical Manual TM-0042, Seventh Edition", and the
template's own header reads *"Based on NLSA from HOURSFramework"*. It is written in
the register of an external standard. Those citations establish a functional **form**
the framework asserts and supply **no external evidence for a value**, so equation
numbers now appear only under `form:`, never `resolves_by:`. Citing one's own design
document as a source is precisely the authority-borrowing the scheme exists to
prevent, and to a reader who has not opened the template it reads as provenance.

**Two constants describe the same physical quantity and disagree 4.6×.**
`GUF_ECO_KAPPA_CARBON` = 2.750 TEH per tonne-CO₂eq (land layer) against
`CDR_LABOR_HOURS_PER_TONNE` = 0.6 h per tonne (thermal layer). One is wrong and
nothing reconciles them. Two further duplications: `DEP_RATE` 0.045 against
`FORMATION_DEPRECIATION_RATE` 0.05 (both aggregate capital depreciation, the second
derived from `CAPITAL_MACHINE_PROFILES`), and `CONTESTABILITY_CAPITAL_YIELD_RATE`
0.10 against the 0.20 implied by `1/RECAL_CAPITAL_OUTPUT_RATIO −
FORMATION_DEPRECIATION_RATE`.

**Four constants are calibrated to a target, and now say so on their own line:**
`GUF_USE_*` (scaled ×100 so aggregate GUF matches levy revenue at mid-arc),
`DEFAULT_SEGMENTS` (segment means set so the weighted mean hits 2.10, the top of the
band), `TRUST_BASE_TEH` (sized so the dividend covers the obligations it must fund),
and `CAPITAL_MACHINE_PROFILES` (tiers set to bracket the mid-arc ε they are supposed
to produce). All four are the `_ECOLOGICAL_SPIKE_INTENSITY` pattern the 2026-08-05
pass named; they were simply not looked at then.

**`LEVY_SUFFICIENCY_WARN` cannot fire on the shipped configuration.** It warns when
the levy covers < 2% of the guarantee, and `SUFF_LEVY_RATE` covers ≈2% at canonical
defaults. An indicator calibrated to the value it watches will not warn about the
configuration it was drawn around.

---

## Multipliers (Condition II)

> **Retagged 2026-08-09.** These carried `Physics`, justified by statements like
> "below 1.8 the differential between labor tiers is too small to reflect real skill
> differentials". That is an argument about fairness and legitimacy, not about how
> entropy works — a **constitutional** commitment, which is the strongest possible
> reason to hold it and no reason at all to call it physics. Mislabelling the band as
> physics hid the one number most in need of argument: it is the load-bearing surface
> of the skill-differential wound in `notes/historical-autopsy.md`.

<!-- provenance:table "Multipliers — constitutional band (Condition II)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `M_BAND_LOW` | 1.8 | dimensionless multiplier | normative<br>form: physics-adjacent in one respect only — a band must EXIST for Condition II to be checkable. Where its edges sit is not implied by that. | **decided by** a charter decision on the tolerable spread of labour valuation. The measured route now exists and disagrees usefully: the O*NET/BLS reference multiplier (mult-5.1.0) produces a population-weighted mean from measured factors, and handoffs/multipliers-v5/FALSIFIABILITY.md records that the band PASS is a construction artifact of the normalization (±2.8× across normalizations) with no empirical content. So the band cannot be validated against the measurement — it can only be chosen and then honoured.<br>_no measurement settles this_ |
| `M_BAND_HIGH` | 2.1 | dimensionless multiplier | normative<br>form: physics-adjacent in one respect only — a band must EXIST for Condition II to be checkable. Where its edges sit is not implied by that. | **decided by** a charter decision on the tolerable spread of labour valuation. The measured route now exists and disagrees usefully: the O*NET/BLS reference multiplier (mult-5.1.0) produces a population-weighted mean from measured factors, and handoffs/multipliers-v5/FALSIFIABILITY.md records that the band PASS is a construction artifact of the normalization (±2.8× across normalizations) with no empirical content. So the band cannot be validated against the measurement — it can only be chosen and then honoured.<br>_no measurement settles this_ |
| `M_BAND_TARGET` | 2.1 | dimensionless multiplier | normative<br>form: physics-adjacent in one respect only — a band must EXIST for Condition II to be checkable. Where its edges sit is not implied by that. | **decided by** a charter decision on the tolerable spread of labour valuation. The measured route now exists and disagrees usefully: the O*NET/BLS reference multiplier (mult-5.1.0) produces a population-weighted mean from measured factors, and handoffs/multipliers-v5/FALSIFIABILITY.md records that the band PASS is a construction artifact of the normalization (±2.8× across normalizations) with no empirical content. So the band cannot be validated against the measurement — it can only be chosen and then honoured.<br>_no measurement settles this_ |
| `MEAN_MULTIPLIER_REFERENCE` | 1.99641978545 | dimensionless multiplier | measured (Tier B)<br>form: the employment-weighted mean of the O*NET 30.3/BLS reference registry — 751 occupations, 94.2% of US employment, one weight per occupation (reference.onet_multipliers.registry_segments). Bound by TEST, not by expression: data.py sits below reference/ and cannot import it, the same constraint AGE_WEIGHT_ELDERLY and GUF_ECO_KAPPA_CARBON are bound under. TestMeasuredMeanIsBoundToTheRegistry fails whichever side moves alone. | an O*NET/BLS vintage refresh moves it mechanically; a non-US occupational registry would test whether 1.9964 travels.<br>TIER B — the registry is a large, well-sourced measurement, but it is US employment, and handoffs/multipliers-v5/FALSIFIABILITY.md records that the BAND pass is a construction artifact of the normalization (±2.8× across normalizations). So this value is evidence about the workforce and is NOT evidence that the band is right; it lands inside [1.8, 2.1] on its own terms, which is a result rather than a construction, and that is the whole of what it establishes. |
| `M_MAX` | 6.0 | dimensionless multiplier | normative<br>form: physics — a hard cap must exist, or TEH accumulation is unbounded in the tier dimension. Its LEVEL is the choice. | **decided by** a charter decision on maximum permitted labour-valuation inequality. 6.0 is a 6:1 ratio against the floor; that is the substantive commitment and it should be argued as a distributional limit, not derived.<br>_no measurement settles this_ |
| `ALPHA_SCALE` | 5.0 | dimensionless (sum of the four alpha coefficients) | derived<br>form: Σαᵢ = M_MAX − 1, so that perfect scores on all four factors land exactly on the cap. Genuinely computed from M_MAX rather than pinned — it moves when the cap moves. | n/a — it inherits M_MAX's standing, which is CHOSEN. Nothing additional is owed here beyond settling the cap. |
| `ALPHA_IMPACT_EOH_REDUCTION_WEIGHT` | 0.4 | fraction | normative<br>form: derived only in that the three weights are constrained to sum to 1.0. | **decided by** nothing measures the relative importance of EOH reduction, domain breadth and reserve capacity against each other — it is a judgement about what the collective values in a role. Sweep it: scenarios/multiplier_sensitivity.py already provides the harness, and the shipped sweep is ±0.10 per weight.<br>_no measurement settles this_ |
| `ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT` | 0.35 | fraction | normative<br>form: derived only in that the three weights are constrained to sum to 1.0. | **decided by** nothing measures the relative importance of EOH reduction, domain breadth and reserve capacity against each other — it is a judgement about what the collective values in a role. Sweep it: scenarios/multiplier_sensitivity.py already provides the harness, and the shipped sweep is ±0.10 per weight.<br>_no measurement settles this_ |
| `ALPHA_IMPACT_RESILIENCE_WEIGHT` | 0.25 | fraction | normative<br>form: derived only in that the three weights are constrained to sum to 1.0. | **decided by** nothing measures the relative importance of EOH reduction, domain breadth and reserve capacity against each other — it is a judgement about what the collective values in a role. Sweep it: scenarios/multiplier_sensitivity.py already provides the harness, and the shipped sweep is ±0.10 per weight.<br>_no measurement settles this_ |
<!-- /provenance:table -->

### Multiplier governance and anti-gaming safeguards

The sortition, scarcity-dampening and sunset machinery. Scarcity is **endogenous** —
raising a multiplier can itself resolve the scarcity that justified it — so the
rolling window and supply lag are structurally required even though their lengths
are asserted.

<!-- provenance:table "Multiplier governance and anti-gaming safeguards" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `GOVERNANCE_MIN_ASSESSORS` | 3 | count of assessors | normative | **decided by** a charter decision on panel size. Three is the smallest panel that can break a tie, which is an argument rather than a measurement; sortition literature on minimum panel size for stable outcomes would strengthen it.<br>_no measurement settles this_ |
| `GOVERNANCE_IRR_WARN_THRESHOLD` | 0.7 | inter-rater reliability coefficient | bounded<br>form: the WARN/CRIT pair on assessment agreement. | **band** the conventional inter-rater agreement reading — κ ≥ 0.80 good, 0.67–0.80 tentative, below 0.67 unreliable (Krippendorff; Landis–Koch)<br>**errs** LOW. Both thresholds sit BELOW the conventional bar — 0.70 WARN against a 0.80 'good' line, 0.50 CRIT against 0.67 'unreliable' — so the gate is more permissive than the literature would set it. That is the unsafe direction for assessment quality, and it should be argued or tightened.<br>convention exists and is close at hand — these sit near the established Krippendorff/Cohen κ reading (≥0.80 good, 0.67–0.80 tentative, below that unreliable). Adopting a cited standard would move both to `convention`; as written they are the framework's own rounder numbers. |
| `GOVERNANCE_IRR_CRIT_THRESHOLD` | 0.5 | inter-rater reliability coefficient | bounded<br>form: the WARN/CRIT pair on assessment agreement. | **band** the conventional inter-rater agreement reading — κ ≥ 0.80 good, 0.67–0.80 tentative, below 0.67 unreliable (Krippendorff; Landis–Koch)<br>**errs** LOW. Both thresholds sit BELOW the conventional bar — 0.70 WARN against a 0.80 'good' line, 0.50 CRIT against 0.67 'unreliable' — so the gate is more permissive than the literature would set it. That is the unsafe direction for assessment quality, and it should be argued or tightened.<br>convention exists and is close at hand — these sit near the established Krippendorff/Cohen κ reading (≥0.80 good, 0.67–0.80 tentative, below that unreliable). Adopting a cited standard would move both to `convention`; as written they are the framework's own rounder numbers. |
| `SCARCITY_ROLLING_WINDOW` | 3 | periods | placeholder<br>form: physics-adjacent — SOME smoothing is structurally required, because scarcity is endogenous to the multiplier that responds to it and an unsmoothed feedback oscillates. The window LENGTH is the choice. | the observed autocorrelation of occupational vacancy series. BLS JOLTS measures exactly this and is not yet ingested; three periods is the framework's assertion about how long the oscillation is. |
| `SCARCITY_SUPPLY_LAG_YEARS` | 3 | years | bounded | **band** weeks to ~10 years across occupations (O*NET job-zone training times, already shipped in reference/data/)<br>**errs** WITHHELD. A single economy-wide lag cannot err in one direction when the true quantity is per-occupation and spans two orders of magnitude. 3 years is implausibly uniform, and the honest fix is to make it per-occupation rather than to move the point.<br>measured time from a wage/valuation signal to a completed training pipeline, by occupation. Programme lengths are published (O*NET job-zone training times are already shipped in reference/data/), so this is one of the more readily settled constants in the block — and three years is implausibly uniform across occupations that range from weeks to a decade. |
| `SCARCITY_SEVERE_THRESHOLD` | 0.8 | normalized scarcity score ∈ [0,1] | normative | **decided by** a charter decision on when scarcity becomes an emergency worth naming. It gates a label, not an allocation.<br>_no measurement settles this_ |
| `TRAINING_VALIDATION_TOLERANCE` | 1.5 | ratio of mandated to median observed training duration | placeholder<br>form: the anti-gaming test — a credential mandating far more training than practitioners actually needed is rent extraction wearing a training claim. | the distribution of mandated-vs-actual training ratios across licensed occupations. O*NET training data plus licensure requirements would give the empirical spread, and the tolerance should sit at its upper tail rather than at a round 1.5. |
| `ARTIFICIAL_SCARCITY_PASS_RATE_FLOOR` | 0.3 | fraction | placeholder<br>form: the pass-rate floor and the quality differential that can excuse falling below it — a gate is artificial unless the failures are really unqualified. | observed licensure pass rates paired with a measured competency differential between passers and failers. Board pass rates are published; the competency half is the missing instrument, and without it the excuse cannot be tested — only asserted. |
| `ARTIFICIAL_SCARCITY_QUALITY_THRESHOLD` | 0.2 | fraction | placeholder<br>form: the pass-rate floor and the quality differential that can excuse falling below it — a gate is artificial unless the failures are really unqualified. | observed licensure pass rates paired with a measured competency differential between passers and failers. Board pass rates are published; the competency half is the missing instrument, and without it the excuse cannot be tested — only asserted. |
| `TIER_ASSESSMENT_INTERVAL_YEARS` | 5 | years | normative<br>form: the sunset clock — a tier assessment that never expires becomes a property right, which is the failure mode notes/historical-autopsy.md names. | **decided by** a charter decision on revalidation cadence, with abundant precedent in professional recertification cycles (commonly 2–10 years). Several other constants are pinned to it (CONTESTABILITY_VESTING_YEARS), so moving it moves them.<br>_no measurement settles this_ |
| `DEFAULT_SEGMENTS` | <list: 4 items> | fractions of workforce and dimensionless multipliers | placeholder | **RETIRED** — superseded by hours_eoh.reference.onet_multipliers.registry_segments<br>nothing further — the measured path replaced it 2026-08-16. `registry_segments()` (O*NET 30.3/BLS, 751 occupations, 94.2% of US employment) is now the default in core/multipliers.py and core/dashboard.py; this list survives only as the synthetic comparison, reachable by passing it explicitly. WHAT THE SWAP FOUND: the default mean moved 2.100 -> 1.9964 (-4.93%) and NOT ONE TEST FAILED. The Condition II baseline — the quantity this whole block exists to govern — was entirely unpinned, exactly as GUF_PSI_NORM's fee-curve peak was. TestMeasuredWorkforceIsTheDefault is now that pin. The measured mean sits INSIDE [1.8, 2.1] on its own evidence, where the synthetic set sat exactly ON the 2.10 ceiling because it was built to. A default calibrated to the target it is checked against cannot test anything, which is why "in_band: True" meant strictly less before this change than after it.<br>CALIBRATED TO A TARGET — the segment means were set so the weighted mean lands on 2.10, the top of the constitutional band, at ε=0. Same class as the GUF_USE_* rates: a value reverse-engineered from a desired outcome. ON THE THIRD MODULE NAMED IN baseline_in: scenarios/measured.py names this constant in module prose only, never in code. `operative_consumers` matches source TEXT, so it over-counts — the safe direction for a gate, so the module is declared rather than the matcher loosened. It earned its keep immediately: it caught that measured.py's layer paragraph still asserted "DEFAULT_SEGMENTS remains the core default" after that stopped being true. |
<!-- /provenance:table -->

---

## Registration Sigmas

<!-- provenance:table "Registration sigmoids" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CARE_SIGMOID_DEFAULTS` | {'start_share': 0.05, 'inflection': 0.45, 'rate': 8.0, 'saturation': 0.95} | start_share/saturation fractions; inflection in ε; rate dimensionless | placeholder<br>form: physics-adjacent in shape only — admission to a collective ledger plausibly follows slow onset, mid-range acceleration and saturation below 1.0 (some care stays informal at any automation level). Every one of the four numbers is asserted. | the measured formal/informal split of care labour against an automation index — the share of care hours that pass through a paid or recorded channel. ATUS separates household care from paid care and is now partly ingested (reference/atus_time_use.py), so the start_share is the most nearly reachable of the four; the inflection needs a cross-country panel.<br>docs/parameter_provenance.md's Registration table still lists start_share 0.30 and inflection 0.55 against the 0.05 and 0.45 shipped here — caught by this migration, corrected in the generated table. |
| `PRODUCTION_SIGMOID_DEFAULTS` | {'base': 0.15, 'growth': 0.84, 'rate': 20.0, 'inflection': 0.1} | base/growth fractions; inflection in ε; rate dimensionless | placeholder<br>form: base + growth × logistic(rate × (ε − inflection)). Physics-adjacent in SHAPE only: admission plausibly follows slow onset then acceleration. The four numbers are asserted. | the share of production hours passing through a recorded channel, against an automation index — the same instrument the care sigmoid needs, read on a different labour category.<br>the base carries a written physical argument (min3, resolved) that the others do not — organised trade and grain accounting exist at subsistence but are a minority of production labour, giving ~25% total registration at ε=0 rather than the 70% an earlier value implied. |
| `STEWARDSHIP_SIGMOID_DEFAULTS` | {'base': 0.05, 'growth': 0.9, 'rate': 10.0, 'inflection': 0.4} | base/growth fractions; inflection in ε; rate dimensionless | placeholder<br>form: base + growth × logistic(rate × (ε − inflection)). | the recorded share of communal maintenance labour — shared wells, paths, drainage — against an automation index.<br>the rate was RAISED from 6.0 to 10.0 to hold logistic(0) ≈ 0.018, so the ε=0 value stays near the floor instead of contributing a spurious 8% baseline. That makes it a tuned value, and until this migration it was invisible to the shadow-constant scan because 10.0 sits in the `utils.provenance._INNOCUOUS` set while its two siblings here were counted. |
| `PERSONAL_SIGMOID_DEFAULTS` | {'start_share': 0.0, 'saturation': 0.95, 'rate': 7.0, 'inflection': 0.65} | start/saturation fractions; inflection in ε; rate dimensionless | placeholder<br>form: start + (saturation − start) × logistic(rate × (ε − inflection)). | the share of personal-domain hours delivered through collective systems against an automation index. `reference/atus_time_use.py` measures the numerator's high-ε end; the low-ε end needs a low-capital time-use survey.<br>start is 0.0 by construction — at subsistence, personal needs are met privately and the collective ledger recognises none of it. The saturation below 1.0 is a claim that some personal EOH stays private at any automation level (grief, intimacy), which is a normative reading wearing a placeholder's tag; it is not something a dataset settles. |
| `KNOWLEDGE_SIGMOID_DEFAULTS` | {'base': 0.0, 'saturation': 0.8, 'rate': 5.0, 'inflection': 0.7} | base/saturation fractions; inflection in ε; rate dimensionless | placeholder<br>form: base + (saturation − base) × logistic(rate × (ε − inflection)). | the share of knowledge-work hours subject to formal verification against an automation index — harder than the other four, because the denominator (what counts as knowledge work) is itself contested.<br>saturation 0.80 asserts that tacit skill, judgement and creative insight are never fully admissible however automated verification becomes. The late inflection asserts that peer review, credentialing and automated audit need mature automation to operate at scale. Both are arguments, not measurements. |
| `LABOR_CATEGORY_DEFAULTS` | <dict: 7 keys> | shares of total labour, dimensionless; exponent dimensionless | placeholder<br>form: production declines linearly in ε; care grows as base + growth × ε^exponent and is capped; stewardship takes the residual. All three are floored. | an occupational time series split into these three categories against an automation index. The O*NET/BLS registry already carries the occupational side; the split into production/care/stewardship is a mapping this repo has not made.<br>NOT a sigmoid — the composite weights that `total_registration_share` uses to combine the categories. Migrated with them because they share a consumer and were equally invisible. The care exponent 1.5 is the only shape parameter here: concave-up, so care's share accelerates rather than rising linearly, which is the claim that complexity drives care demand faster than automation displaces production. |
<!-- /provenance:table -->

---

## Fiscal Parameters

<!-- provenance:table "Fiscal architecture" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `SUFF_LEVY_RATE` | 0.0125 | fraction of labor income | normative | **decided by** charter. RETAGGED 2026-08-09 from placeholder, after running the derivation its old pointer named. min_levy_for_solvency() returns cover_expenditures_rate = None at EVERY ε on the canonical configuration: the dividend alone runs a surplus (630M TEH against a 397M peak expenditure at ε=0), so the levy rate REQUIRED for solvency is zero throughout. This constant is therefore not a mis-calibrated solvency figure awaiting measurement — it is a redistributive commitment, and deriving it would set it to 0, which is a different policy rather than a better calibration.<br>_no measurement settles this_<br>at canonical ε=0.40 it raises ≈6.2M TEH/yr against a 307M TEH guarantee — it does not fund the guarantee and was never sized to; the Trust dividend does. That is the whole finding, and it is why the solvency derivation cannot set it. What a charter would weigh instead: the levy's incidence on labour income at low ε, where labour income is nearly all income. |
| `SUFF_GUARANTEE_EPS_DECAY` | 0.5 | fraction, per ε unit | normative | **decided by** nothing measures how fast a guarantee floor should shrink as automation rises; it is a distributional commitment about who carries the transition. Argue it, do not fit it.<br>_no measurement settles this_ |
| `TRUST_BASE_TEH` | 35000000000.0 | TEH (at the 1M reference population) | instance | **you supply** your collective Trust's actual balance, or a capital inventory in TEH for the jurisdiction being modelled. Intake path: research/epsilon_inverse.capital_for_epsilon() makes an inventory-first reading possible; scale by population against the 1M reference. Every fiscal function takes trust_balance as an argument, so nothing requires editing this constant — pass your own.<br>**shipped default** THE CRITICAL SOLVENCY KNOB, and it is sized backwards — chosen so the annual dividend (Trust × DEP_RATE × DIV_RATE = 630M TEH) covers the stewardship, ecological and guarantee obligations at mid-arc. Calibrated to a target, like GUF_USE_* and DEFAULT_SEGMENTS. It is the most-consumed constant in the repo (77 call sites outside data.py), so every canonical solvency result rests on it and none of them is evidence about YOUR fisc. |
| `DEP_RATE` | 0.045 | fraction of Trust per year | bounded<br>form: physics — the capital the Trust represents really does deteriorate, so a depreciation term must exist. The RATE is not structural. | **band** 0.045–0.05 per year. The upper end is FORMATION_DEPRECIATION_RATE, derived in this file from CAPITAL_MACHINE_PROFILES design lives (≈20 yr → δ ≈ 1/20) — the same physical quantity reached a second way.<br>**errs** LOW. Understating depreciation overstates the Trust's durability and therefore its dividend, which flatters solvency: the unsafe direction. The two constants should be reconciled to one derivation rather than left 11% apart.<br>a weighted mean design life over the actual capital inventory. FORMATION_DEPRECIATION_RATE (0.05) in this file derives exactly that from CAPITAL_MACHINE_PROFILES design lives — so the repo holds two aggregate depreciation rates, 0.045 and 0.05, on the same physical quantity. They should be reconciled to one derivation. |
| `DIV_RATE` | 0.4 | fraction of annual depreciation | normative<br>form: the dividend/renewal split. That a split exists is structural — pay out everything and the Trust erodes; retain everything and it never circulates. | **decided by** a charter decision on the payout ratio. It is the framework's central distributional lever and belongs in deliberation, not measurement.<br>_no measurement settles this_ |
| `MEANINGFUL_ACTIVITY_TEH_BASE` | 120.0 | TEH per recipient per year (at ε=0) | normative<br>form: base × (1 + scale × ε²) — quadratic so non-participants gain real purchasing power as the labour pool shrinks. Also serves as the sufficiency basket cost at ε=0, so basket_price(0) = 120 TEH/yr. | **decided by** a charter decision on discretionary provision above biological reimbursement — this is what a collective thinks a life beyond subsistence costs, which is the same question PERSONAL_EOH_SUFFICIENCY asks in hours. The two should be reconciled; at present they are set independently.<br>_no measurement settles this_ |
| `MEANINGFUL_ACTIVITY_TEH_SCALE` | 1.5 | TEH per recipient per year (at ε=0) | normative<br>form: base × (1 + scale × ε²) — quadratic so non-participants gain real purchasing power as the labour pool shrinks. Also serves as the sufficiency basket cost at ε=0, so basket_price(0) = 120 TEH/yr. | **decided by** a charter decision on discretionary provision above biological reimbursement — this is what a collective thinks a life beyond subsistence costs, which is the same question PERSONAL_EOH_SUFFICIENCY asks in hours. The two should be reconciled; at present they are set independently.<br>_no measurement settles this_ |
| `CAPITAL_STOCK_DEFAULT` | 2000000000.0 | TEH (at the 1M reference population) | instance | **you supply** your gross fixed capital stock, converted to TEH at the TEH/currency exchange rate you choose (the model does not determine it). Intake path: research/epsilon_inverse.capital_for_epsilon() inverts an ε target into the capital that produces it, so an inventory and an ε can be checked against each other rather than assumed apart.<br>**shipped default** 2,000 TEH/capita, and Block III established that the ε=0 endpoint carries NO apparatus — so this default describes a MID-ARC collective, not a subsistence one. Callers passing it at low ε are asserting capital the arc says is not there. |
| `BASKET_EOH_CONTENT` | 1000.0 | personal EOH hours per sufficiency basket | derived<br>form: DEFINED equal to PERSONAL_EOH_BASE — one basket covers one person-year. Was a literal 1500.0 duplicating it; bound to the constant on 2026-08-06 so the two cannot drift apart under repricing. | n/a — it inherits PERSONAL_EOH_BASE's standing by construction, and the binding is the point: this is the repricing-hazard fix, not a free value. |
<!-- /provenance:table -->

---

## Labor Parameters (Condition IV)

<!-- provenance:table "Labor and Condition IV" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `ESSENTIAL_DOMAINS` | <list: 7 items> | list of domain names | normative<br>form: physics-adjacent — a civilization does have a set of functions whose failure is not survivable, so the CATEGORY is structural. Which seven, and the fact that there are seven, is not. | **decided by** a criticality analysis for the jurisdiction being modelled — national critical-infrastructure sector designations are the nearest external analogue, and they do not agree with each other on the list either.<br>_no measurement settles this_ |
| `COMPETENCY_THRESHOLD` | 0.155 | fraction of workforce certified per essential domain | placeholder | an observed relationship between practitioner density and recovery time from a domain outage. The Mission Statement asserts 15.5%; the three significant figures imply a precision nothing supplies, which is itself the tell. Workforce composition series plus outage post-mortems would settle it. |
| `H_MIN` | 260 | hours per year | placeholder<br>form: 5 h/wk × 52 wk. Below some floor a practitioner stops maintaining competency, which is structural; the level is the choice. | measured skill-retention against practice hours by domain — the currency-of-practice literature in aviation and surgery measures exactly this and reports domain-specific thresholds, which is the point: one economy-wide 260 cannot be right for both a surgeon and a farmhand. |
| `H_MIN_ALLOCATION` | <dict: 3 keys> | fractions of H_MIN, summing to 1.0 | normative | **decided by** a charter decision on how the minimum obligation is apportioned. The three-way split is a policy design; nothing measures it.<br>_no measurement settles this_ |
<!-- /provenance:table -->

`H_MIN` is one economy-wide floor, and the currency-of-practice literature (aviation,
surgery) reports domain-*specific* retention thresholds — so 260 h/yr cannot be right
for both a surgeon and a farmhand. `COMPETENCY_THRESHOLD`'s three significant figures
imply a precision nothing supplies, which is its own tell.

### Reference hours

<!-- provenance:table "Reference and workforce" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `H_REF` | 2000 | hours/year per worker | convention<br>form: a stated normalizer — 50 weeks × 40 h. Used to convert workforce-hours to TEH, not a claim about how long anyone works. | n/a as a convention. If it were read as a measurement of actual hours worked it would be wrong in most jurisdictions (OECD average annual hours run ~1,400–2,200), which is precisely why it is tagged as the denominator it is. |
<!-- /provenance:table -->

`H_REF` is a **convention**, not a measurement of hours worked: OECD average annual
hours run ~1,400–2,200, so read as a measurement it would be wrong nearly everywhere.
Note `BASE_LIFETIME_EARNINGS_TEH` uses 2,080 h (40 × 52, no leave) instead — the repo
carries two work-year conventions and they are not reconciled.

---

## Capital and Asset Lifecycle

Maintenance profiles for EOH compounding, the machine-capacity sub-model that makes ε
emergent from physical state, and the condition-decay constants.

<!-- provenance:table "Capital and asset lifecycle" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `ASSET_TYPES` | <dict: 6 keys> | maint_rate fraction of capital/yr; threshold_age years; compound_exp dimensionless | placeholder<br>form: physics — post-threshold maintenance escalates as a power law rather than linearly, and the ORDERING across asset classes (software fastest to fail, stone slowest) is a defensible engineering claim. The exponents are not. | measured maintenance and failure curves by asset class. The infrastructure floor shows the route — a physical condition census in crew-hours rather than money (INFRA_TREATMENT_HOURS_*). Design lives here are order-of-magnitude right; nothing measures the compounding exponents. |
| `ASSET_FULL_NEGLECT_DECAY` | 0.2 | fraction of condition per period | placeholder<br>form: the two arms of the maintenance response in core/capital.asset_condition. Under-maintenance: condition *= (1 − deficit_fraction × NEGLECT_DECAY), so NEGLECT_DECAY is the drop at TOTAL neglect. Over-maintenance: condition += surplus × RESTORE_RATE × condition, bounded by the initial condition — you may not build a better asset by polishing it. | an infrastructure condition-rating panel with maintenance spending per asset — FHWA NBI bridge condition ratings carry exactly this (condition rating 0–9 by structure by year, against reported maintenance expenditure). FIELD: the year-on-year rating change for structures at zero-versus-adequate maintenance. NOT the ASCE report-card grades, which are an aggregate letter and cannot resolve a per-period rate.<br>THE ASYMMETRY IS THE CLAIM AND IT IS THE DEFENSIBLE PART — neglect costs 4x what surplus effort recovers, which is the entropy argument applied to one asset: degradation is spontaneous and repair is not. The LEVELS are desk estimates. Migrated from core/capital.py 2026-08-27, where both were shadow constants and a +7% move failed no test. |
| `ASSET_OVER_MAINT_RESTORE_RATE` | 0.05 | fraction of condition per period | placeholder<br>form: the over-maintenance arm of the same response — condition += surplus × RESTORE_RATE × condition, bounded above by the initial condition. See ASSET_FULL_NEGLECT_DECAY for the pair and for why the 4x asymmetry between them is the defensible part. | as for ASSET_FULL_NEGLECT_DECAY — FHWA NBI condition ratings against maintenance expenditure. FIELD: the rating change for structures maintained ABOVE their assessed need, which is the rarer half of that panel and the reason this arm is the weaker of the two. |
| `MATURATION_BASE_GROWTH_RATE` | 50.0 | EOH capacity per year; EOH capacity per TEH^exponent; dimensionless | placeholder<br>form: core/capital.maturation_update — capacity_delta = BASE_GROWTH × years + EDU_COEFFICIENT × investment**EDU_EXPONENT × (1 + MATURATION_AUTO_LEVERAGE × ε) BASE_GROWTH is maturation without schooling; the education arm has diminishing returns via the exponent. | as for MATURATION_EDU_* — PIAAC proficiency by age for adults at a FIXED level of completed education, which isolates ageing from schooling.<br>the schooling-free arm — maturation that happens with age alone. Migrated from core/capital.py 2026-08-27 as a shadow constant. |
| `MATURATION_EDU_COEFFICIENT` | 5.0 | EOH capacity per TEH^exponent; dimensionless | placeholder<br>form: the education arm of maturation_update — EDU_COEFFICIENT × investment**EDU_EXPONENT × (1 + MATURATION_AUTO_LEVERAGE × ε) | returns to schooling measured as CAPACITY, not earnings — earnings embed the wage structure this framework replaces, so a Mincer coefficient is the WRONG INSTRUMENT here for the same reason BLS Employee Tenure was wrong for SKILL_WORKING_LIFE_YEARS. FIELD: PIAAC numeracy and literacy proficiency by years of education — capability measured directly.<br>EDU_EXPONENT = 0.5 is a SQUARE ROOT, the strongest diminishing return short of a logarithm, and it is the term deciding whether education investment ever saturates. Pinned by SHAPE (test_capital.TestMaturationShape), not level. Both migrated from core/capital.py 2026-08-27 as shadow constants. |
| `MATURATION_EDU_EXPONENT` | 0.5 | EOH capacity per TEH^exponent; dimensionless | placeholder<br>form: the education arm of maturation_update — EDU_COEFFICIENT × investment**EDU_EXPONENT × (1 + MATURATION_AUTO_LEVERAGE × ε) | returns to schooling measured as CAPACITY, not earnings — earnings embed the wage structure this framework replaces, so a Mincer coefficient is the WRONG INSTRUMENT here for the same reason BLS Employee Tenure was wrong for SKILL_WORKING_LIFE_YEARS. FIELD: PIAAC numeracy and literacy proficiency by years of education — capability measured directly.<br>EDU_EXPONENT = 0.5 is a SQUARE ROOT, the strongest diminishing return short of a logarithm, and it is the term deciding whether education investment ever saturates. Pinned by SHAPE (test_capital.TestMaturationShape), not level. Both migrated from core/capital.py 2026-08-27 as shadow constants. |
| `CAPITAL_MACHINE_PROFILES` | <dict: 11 keys> | EOH eliminated per TEH of capital per year; TEH per capita; years; condition ∈ [0,1] | placeholder | measured EOH-elimination rates per capital class — the labour-hours a unit of each capital type actually displaces per year. This is the same instrument the food conservation test used at one stage (scenarios/food_conservation.py found a 62× collapse in production labour), so the method is proven and the coverage is what is missing. Note research/thermal_capital.py already treats the same inventory as dual-output; a measured pass should settle both fields at once.<br>CALIBRATED TO A TARGET, on its own admission — the tiers were set so that "standard" across all types totals ~2000 TEH/person (matching CAPITAL_STOCK_DEFAULT) and implies ε ≈ 0.18, with "advanced" implying ε ≈ 0.48, so the table brackets the mid-arc by construction. That makes ε emergent from a capital stock whose profile was chosen to produce the ε expected of it. The circularity is documented, not resolved. |
| `COND_DECAY_SLOPE` | 0.7 | fraction of condition (slope over full design life; floor level) | placeholder<br>form: linear decay to a floor. Physics in one respect — an end-of-life asset is degraded but still operational, so the floor must be above zero (full write-down is a separate explicit event via execute_writedown). The linearity is a simplification; real condition curves are convex. | measured condition ratings against age by asset class. Bridge inventories publish exactly this (the NBIS condition data behind INFRA_TREATMENT_HOURS_* is the same source), so this is reconcilable against data the repo already reaches for elsewhere. |
| `COND_DECAY_FLOOR` | 0.3 | fraction of condition (slope over full design life; floor level) | placeholder<br>form: linear decay to a floor. Physics in one respect — an end-of-life asset is degraded but still operational, so the floor must be above zero (full write-down is a separate explicit event via execute_writedown). The linearity is a simplification; real condition curves are convex. | measured condition ratings against age by asset class. Bridge inventories publish exactly this (the NBIS condition data behind INFRA_TREATMENT_HOURS_* is the same source), so this is reconcilable against data the repo already reaches for elsewhere. |
| `ENV_MONITORING_SATURATION_TEH_PER_CAPITA` | 500.0 | TEH per capita of environmental-monitoring capital | placeholder | an observed relationship between monitoring investment and detected fraction of ecological deferral. This constant governs how much deferred ecological EOH is VISIBLE, so it sets what the ledger can see rather than what is there — the honest pointer is a detection-rate study, and until then monitoring capability is an assumption about the framework's own eyesight. |
<!-- /provenance:table -->

> **`CAPITAL_MACHINE_PROFILES` is calibrated to a target, on its own admission.** The
> tiers were set so that "standard" across all types totals ~2,000 TEH/person
> (matching `CAPITAL_STOCK_DEFAULT`) and implies ε ≈ 0.18, with "advanced" implying
> ε ≈ 0.48 — so the table brackets the mid-arc *by construction*. That makes ε
> emergent from a capital stock whose profile was chosen to produce the ε expected of
> it. The circularity is documented here, not resolved.

---

## TEH Destruction and ε-Scaling

The D1–D6 destruction constants and the named ε-scaling slopes that were previously
anonymous literals in `eoh_fulfillment.py` and `simulation.py`.

<!-- provenance:table "TEH destruction and ε-scaling" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CAPITAL_FAILURE_RATE` | 0.005 | fraction of capital stock per year | placeholder<br>form: catastrophic failure beyond recoverability, triggering D1 write-down. | observed catastrophic-failure rates by asset class. Insurance and asset-registry loss data measure this directly; ASSET_TYPES in this file already carries per-class threshold ages, so a measured pass should produce a per-class rate rather than one economy-wide 0.5%. |
| `CAPITAL_WRITEDOWN_MONITORING_SLOPE` | 0.3 | fraction of the failure rate removable at ε=1 | placeholder<br>form: better monitoring at high ε reduces catastrophic failure — structurally right in direction (detected degradation is repairable degradation), asserted in magnitude. | measured failure-rate reduction attributable to condition monitoring. Note this shares the framework's monitoring-eyesight assumption with ENV_MONITORING_SATURATION_TEH_PER_CAPITA and neither is measured. |
| `LABOR_INCOME_MIN_TEH` | 100000000.0 | TEH per period (at the 1M reference population) | convention<br>form: a numerical guard, not an economic claim — it keeps period labour income from reaching zero and producing division-by-zero at high ε, which the ε-coherence rule requires every function to survive. | — |
| `WORKFORCE_FRACTION_MIN` | 0.05 | fraction of population in the workforce | placeholder<br>form: the minimum workforce retained at any automation level. Structural in direction — full automation still needs someone, which Condition IV asserts as distributed competency — and asserted in level. | the minimum staffing that holds ESSENTIAL_DOMAINS above COMPETENCY_THRESHOLD; that makes it derivable from two other constants in this file rather than independent, and it is currently set independently of both. |
| `ANNUAL_DEATH_RATE` | 0.01 | fraction of population per year | bounded<br>form: crude death rate. EXOGENOUS — nothing in the model links mortality to the deferred personal-EOH deficit that core/eoh_fulfillment.py now tracks, so a severe unserved survival obligation and this rate are independent. That is a known limit, stated because the deficit reports HOURS, not outcomes. | **band** ≈0.007–0.011 per year across developed-world crude death rates (UN WPP / national vital statistics)<br>**errs** NEITHER. Near the top of the band, and directly measurable — one of the cheapest debts in this file to close. The real limit is not the value: mortality is EXOGENOUS, and nothing links it to the deferred personal-EOH deficit the fulfillment layer now tracks.<br>national vital statistics or UN WPP for the jurisdiction being modelled. 1%/yr is a plausible developed-world crude rate and directly measurable, making this one of the cheaper CHOSEN debts to close. |
| `ESTATE_INHERITANCE_FRACTION` | 0.35 | fraction of the excess above reserve | normative<br>form: the D5 split on death — inherited (circulatory), levied to Trust (circulatory), and the remainder written down. Note the three shares are a distributional design, and RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE deliberately reuses the 0.15 levy fraction so capital estates get the same treatment as TEH estates rather than a new rule. | **decided by** a charter decision on inheritance. There is no measurement of what fraction of an estate SHOULD pass to heirs; comparative inheritance-tax schedules give precedent for the range, not the value.<br>_no measurement settles this_ |
| `ESTATE_LEVY_FRACTION` | 0.15 | fraction of the excess above reserve | normative<br>form: the D5 split on death — inherited (circulatory), levied to Trust (circulatory), and the remainder written down. Note the three shares are a distributional design, and RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE deliberately reuses the 0.15 levy fraction so capital estates get the same treatment as TEH estates rather than a new rule. | **decided by** a charter decision on inheritance. There is no measurement of what fraction of an estate SHOULD pass to heirs; comparative inheritance-tax schedules give precedent for the range, not the value.<br>_no measurement settles this_ |
| `ESTATE_PERSONAL_RESERVE_YEARS` | 10.0 | years of basket cost | normative<br>form: the unconditionally preserved personal reserve — the part of an estate D5 never touches. | **decided by** a charter decision. It is a commitment about how much security a person may hold beyond their own lifetime without it being reclaimed.<br>_no measurement settles this_ |
| `ACCUMULATION_CEILING_MULTIPLIER` | 3.5 | multiple of base lifetime earnings | normative<br>form: the D6 accumulation ceiling above which excess TEH is committed to capital formation rather than sitting in perpetual savings. Disabled by default. | **decided by** a charter decision on the maximum permitted accumulation — the framework's most direct statement about tolerable wealth concentration, and it belongs in deliberation. Note it interacts with M_MAX: a 6× multiplier cap and a 3.5× accumulation cap are two different answers to the same question and have not been reconciled.<br>_no measurement settles this_ |
| `BASE_LIFETIME_EARNINGS_TEH` | 87360.0 | TEH over a career | derived<br>form: 2080 TEH/yr × 42-yr career at a 1× multiplier = 87,360. Note the 2080 differs from H_REF's 2000 (2080 = 40 h × 52 wk, with no leave), so the repo carries two work-year conventions; this one is the FTE-hours convention the multiplier registry also uses. | n/a — arithmetic from a stated career length and work-year. The career length (42 yr) is close to SKILL_WORKING_LIFE_YEARS (40) and should probably be bound to it rather than restated. |
<!-- /provenance:table -->

`ANNUAL_DEATH_RATE` is **exogenous**: nothing links mortality to the deferred
personal-EOH deficit that `core/eoh_fulfillment.py` now tracks, so a severe unserved
survival obligation and this rate are independent. The deficit reports *hours*, not
outcomes, and this is why.

---

## Human Capital and Population

<!-- provenance:table "Human capital and population" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `ELDERLY_EOH_EPSILON_FACTOR` | 0.05 | fraction shift per ε unit | placeholder<br>form: automation improves medicine, so lives lengthen and the elderly fraction grows. Direction is arguable; the magnitude is asserted, and it is secondary to the dominant ε effect in the fulfillment split. | a longitudinal life-expectancy series against a measured automation index. |
| `INFANT_EOH_EPSILON_FACTOR` | 0.1 | fraction shift per ε unit | placeholder<br>form: infant personal EOH declines with automation — formula feeding, monitoring and sanitation displace caregiver hours. This is the abatement claim of Block II applied to one age group, and note it runs OPPOSITE to care's low abatability; the two have not been reconciled. | ATUS childcare hours per child against a capital index, which is the same cut AGE_GROUPS needs. |
| `HUMAN_CAPITAL_NATURAL_DECAY` | 0.005 | fraction of condition per year | placeholder<br>form: annual health-condition decay, higher for the elderly. Direction is biological; the 3× ratio between them is asserted. | measured functional-decline rates by age — NHATS/HRS carry exactly this and are already named as the pointer for the AGE_GROUPS care weights, so one dataset closes both. |
| `HUMAN_CAPITAL_ELDERLY_DECAY` | 0.015 | fraction of condition per year | placeholder<br>form: annual health-condition decay, higher for the elderly. Direction is biological; the 3× ratio between them is asserted. | measured functional-decline rates by age — NHATS/HRS carry exactly this and are already named as the pointer for the AGE_GROUPS care weights, so one dataset closes both. |
| `MATURATION_AUTO_LEVERAGE` | 0.3 | dimensionless leverage coefficient per ε unit | placeholder<br>form: automation amplifies the return on education — leverage = 1 + factor × ε. | measured returns to schooling against an automation index. The direction is contested in the literature (automation may raise the return to skill or hollow the middle), so the sign is not safe to assume either. |
| `CAPACITY_DECLINE_ONSET_AGE` | 50 | years of age | placeholder<br>form: the three breakpoints of the piecewise capacity-decline schedule in core/population._capacity_decline_rate — no decline below onset, then early, mid and late phases. A step schedule is itself an approximation: real functional decline is continuous and accelerating, and the steps are a readable stand-in for a curve nobody here has fitted. | NHATS or HRS functional-limitation prevalence by single year of age. FIELD: the age at which ADL/IADL limitation prevalence first departs from its plateau, and the two inflections above it. The same dataset is already the named pointer for HUMAN_CAPITAL_*_DECAY and the AGE_GROUPS care weights, so one ingest closes all three. Grip strength (NHANES, mean kg by age) bounds the PHYSICAL axis only and would understate cognitive decline.<br>CAPACITY_DECLINE_MID_AGE is BOUND to the AGE_GROUP_RANGES elderly boundary rather than restating 65, so the two cannot drift apart. The onset at 50 is deliberately NOT the retirement age — the claim is biological capacity, not labour-force status, and conflating them would be the wrong-instrument error this repo keeps finding (a participation series measures whether people DO work, not what they are capable of). |
| `CAPACITY_DECLINE_MID_AGE` | 65 | years of age | placeholder<br>form: the three breakpoints of the piecewise capacity-decline schedule in core/population._capacity_decline_rate — no decline below onset, then early, mid and late phases. A step schedule is itself an approximation: real functional decline is continuous and accelerating, and the steps are a readable stand-in for a curve nobody here has fitted. | NHATS or HRS functional-limitation prevalence by single year of age. FIELD: the age at which ADL/IADL limitation prevalence first departs from its plateau, and the two inflections above it. The same dataset is already the named pointer for HUMAN_CAPITAL_*_DECAY and the AGE_GROUPS care weights, so one ingest closes all three. Grip strength (NHANES, mean kg by age) bounds the PHYSICAL axis only and would understate cognitive decline.<br>CAPACITY_DECLINE_MID_AGE is BOUND to the AGE_GROUP_RANGES elderly boundary rather than restating 65, so the two cannot drift apart. The onset at 50 is deliberately NOT the retirement age — the claim is biological capacity, not labour-force status, and conflating them would be the wrong-instrument error this repo keeps finding (a participation series measures whether people DO work, not what they are capable of). |
| `CAPACITY_DECLINE_LATE_AGE` | 80 | years of age | placeholder<br>form: the three breakpoints of the piecewise capacity-decline schedule in core/population._capacity_decline_rate — no decline below onset, then early, mid and late phases. A step schedule is itself an approximation: real functional decline is continuous and accelerating, and the steps are a readable stand-in for a curve nobody here has fitted. | NHATS or HRS functional-limitation prevalence by single year of age. FIELD: the age at which ADL/IADL limitation prevalence first departs from its plateau, and the two inflections above it. The same dataset is already the named pointer for HUMAN_CAPITAL_*_DECAY and the AGE_GROUPS care weights, so one ingest closes all three. Grip strength (NHANES, mean kg by age) bounds the PHYSICAL axis only and would understate cognitive decline.<br>CAPACITY_DECLINE_MID_AGE is BOUND to the AGE_GROUP_RANGES elderly boundary rather than restating 65, so the two cannot drift apart. The onset at 50 is deliberately NOT the retirement age — the claim is biological capacity, not labour-force status, and conflating them would be the wrong-instrument error this repo keeps finding (a participation series measures whether people DO work, not what they are capable of). |
| `CAPACITY_DECLINE_EARLY_RATE` | 0.015 | fraction of capacity lost per year | placeholder<br>form: annual fractional loss of entropy-reduction capacity within each phase. The ORDERING (early < mid < late) is the claim and is biologically well-founded; the three LEVELS and the ~2.7x and ~1.75x steps between them are desk estimates. | as for the breakpoints above — NHATS/HRS by single year of age. FIELD: the year-on-year change in mean functional capacity within each band, NOT the prevalence level, which answers a different question.<br>these govern a SHAPE, so they are pinned by shape tests (test_population.TestCapacityDeclineShape) rather than by their levels — a +7% perturbation of any of them moved no test at all before 2026-08-27, which is how they were found. |
| `CAPACITY_DECLINE_MID_RATE` | 0.04 | fraction of capacity lost per year | placeholder<br>form: annual fractional loss of entropy-reduction capacity within each phase. The ORDERING (early < mid < late) is the claim and is biologically well-founded; the three LEVELS and the ~2.7x and ~1.75x steps between them are desk estimates. | as for the breakpoints above — NHATS/HRS by single year of age. FIELD: the year-on-year change in mean functional capacity within each band, NOT the prevalence level, which answers a different question.<br>these govern a SHAPE, so they are pinned by shape tests (test_population.TestCapacityDeclineShape) rather than by their levels — a +7% perturbation of any of them moved no test at all before 2026-08-27, which is how they were found. |
| `CAPACITY_DECLINE_LATE_RATE` | 0.07 | fraction of capacity lost per year | placeholder<br>form: annual fractional loss of entropy-reduction capacity within each phase. The ORDERING (early < mid < late) is the claim and is biologically well-founded; the three LEVELS and the ~2.7x and ~1.75x steps between them are desk estimates. | as for the breakpoints above — NHATS/HRS by single year of age. FIELD: the year-on-year change in mean functional capacity within each band, NOT the prevalence level, which answers a different question.<br>these govern a SHAPE, so they are pinned by shape tests (test_population.TestCapacityDeclineShape) rather than by their levels — a +7% perturbation of any of them moved no test at all before 2026-08-27, which is how they were found. |
<!-- /provenance:table -->

`INFANT_EOH_EPSILON_FACTOR` says infant personal EOH *declines* with automation —
which is Block II's abatement claim applied to one age group, and it runs **opposite**
to care's low abatability (`PERSONAL_EOH_COMPONENTS`, care abatability 0.25). The two
have not been reconciled.

---

## Dashboard Health Thresholds

**Every constant in this block is `CHOSEN`, and that is the honest reading rather than
a gap.** These set where an indicator turns YELLOW or RED — they govern when the
framework raises its hand, not what is physically true. A threshold is a judgement
about tolerable risk by construction, so "measure it" is the wrong demand; the right
demand is that each be *argued*, and that the quantity it watches be measured. Where a
threshold could be derived from a modelled quantity rather than picked, the pointer
says so.

<!-- provenance:table "Dashboard health thresholds" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `DEFERRED_RATIO_WARN` | 0.1 | fraction of EOH deferred | normative | **decided by** an observed relationship between deferral and unrecoverable degradation — the point past which deferred maintenance stops being catch-up work and becomes replacement. scenarios/recovery.py models the recovery side, so the crossover is derivable in-model rather than needing new data.<br>_no measurement settles this_ |
| `DEFERRED_RATIO_CRIT` | 0.25 | fraction of EOH deferred | normative | **decided by** an observed relationship between deferral and unrecoverable degradation — the point past which deferred maintenance stops being catch-up work and becomes replacement. scenarios/recovery.py models the recovery side, so the crossover is derivable in-model rather than needing new data.<br>_no measurement settles this_ |
| `REGISTRATION_WARN` | 0.35 | registration share (fraction of human EOH admitted to the ledger) | normative | **decided by** a charter decision on the minimum ledger coverage that keeps TEH circulating meaningfully. Note these are ε-INVARIANT while total_registration_share(ε) is low by design at low ε, so at subsistence the indicator reads RED for a state the framework considers correct.<br>_no measurement settles this_ |
| `REGISTRATION_CRIT` | 0.2 | registration share (fraction of human EOH admitted to the ledger) | normative | **decided by** a charter decision on the minimum ledger coverage that keeps TEH circulating meaningfully. Note these are ε-INVARIANT while total_registration_share(ε) is low by design at low ε, so at subsistence the indicator reads RED for a state the framework considers correct.<br>_no measurement settles this_ |
| `COMPOUNDING_WARN` | 0.2 | fraction of original EOH added by compounding | normative | **decided by** the compounding rate at which ASSET_TYPES' power-law escalation outruns any feasible maintenance response — derivable from that table plus a labour-supply constraint, so this is a wiring debt rather than a data debt.<br>_no measurement settles this_ |
| `COMPOUNDING_CRIT` | 0.5 | fraction of original EOH added by compounding | normative | **decided by** the compounding rate at which ASSET_TYPES' power-law escalation outruns any feasible maintenance response — derivable from that table plus a labour-supply constraint, so this is a wiring debt rather than a data debt.<br>_no measurement settles this_ |
| `PP_INDEX_WARN` | 1.05 | purchasing-power index (1.0 = parity) | normative<br>form: the threshold is ε-scaled, threshold = 1 + slope × ε, because purchasing power is expected to RISE across the arc — so a flat 1.05 would pass trivially at high ε. | **decided by** a charter decision on how much purchasing-power gain the arc is expected to deliver before the absence of it counts as a warning.<br>_no measurement settles this_ |
| `PP_INDEX_WARN_SLOPE` | 0.125 | purchasing-power index per ε unit | derived<br>form: (PP_INDEX_WARN − 1.0) / 0.40 — the slope through the ε=0.40 reference point that makes the threshold 1.0 at ε=0. | n/a — it inherits PP_INDEX_WARN's standing by construction. |
| `LEVY_SUFFICIENCY_WARN` | 0.02 | fraction of the sufficiency guarantee covered by levy | normative | **decided by** a charter decision on the minimum share of the guarantee that current labour should fund, rather than the Trust dividend. That is a real solvency question and deserves a threshold argued independently of the default.<br>_no measurement settles this_<br>set at 2%, and the shipped SUFF_LEVY_RATE covers ≈2% of the guarantee at canonical defaults — so this indicator is calibrated to sit just at the value it watches. It will not warn about the configuration it was drawn around. |
| `CARE_ADMISSION_GREEN_FRAC` | 0.2 | fraction of care-registration saturation | normative | **decided by** a charter decision on how much care must be on the ledger before admission counts as working. The quantity watched resolves with CARE_SIGMOID_DEFAULTS; the thresholds are the framework's own bar.<br>_no measurement settles this_ |
| `CARE_ADMISSION_YELLOW_FRAC` | 0.1 | fraction of care-registration saturation | normative | **decided by** a charter decision on how much care must be on the ledger before admission counts as working. The quantity watched resolves with CARE_SIGMOID_DEFAULTS; the thresholds are the framework's own bar.<br>_no measurement settles this_ |
<!-- /provenance:table -->

Two honest problems visible in the table above:

- **`LEVY_SUFFICIENCY_WARN` is calibrated to the value it watches.** It warns when the
  levy covers < 2% of the guarantee, and the shipped `SUFF_LEVY_RATE` covers ≈2% at
  canonical defaults. It will not warn about the configuration it was drawn around.
- **`REGISTRATION_WARN`/`_CRIT` are ε-invariant** while `total_registration_share(ε)`
  is low *by design* at low ε — so at subsistence the indicator reads RED for a state
  the framework considers correct.

---

## Ground Use Fee (NLSA — `land/guf.py`)

The largest single block in `data.py` (51 constants) and, before 2026-08-09, entirely
absent from this document.

> **Provenance warning.** "NLSA" is the National Land Stewardship Authority, and its
> Technical Manual TM-0042 is a document of **this framework** — the template's own
> header reads "Based on NLSA from HOURSFramework". It is written in the register of an
> external standard, and every constant in the block cites it by equation number.
>
> Those citations establish a functional **form** the framework asserts. They supply
> **no external evidence for a value.** So an "NLSA Eq. N" reference appears only under
> `form:`, never under `resolves_by:`, and every value constant in the block is
> `CHOSEN`. Citing one's own design document as a source is exactly the
> authority-borrowing the tag scheme exists to prevent, and the equation numbers read
> like external provenance to anyone who has not opened the template.

<!-- provenance:table "Ground Use Fee (land/guf.py)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `GUF_PSI_A` | 0.8 | dimensionless | placeholder<br>form: NLSA Eq. 18 — the framework's own claim that land's labour-content cost peaks mid-arc and is low at both extremes. | a ground-fee-vs-automation panel across jurisdictions at differing automation levels. Nothing in the repo constrains the rise and fall speeds independently of one another, so sweep them jointly until it does. NOTE such a panel would now have to justify Ψ existing at all alongside α, not merely its shape parameters.<br>THESE NO LONGER GOVERN THE SHIPPED FEE (2026-08-20, author decision). `land/guf.psi_application` defaults to `retired` (Ψ ≡ 1) and the fee's only automation response is now α(ε) = labor_content_scaling inside U. The whole family remains LIVE, not retired, because `psi_policy="bell"` still applies it and the NLSA §4.4 boundary conditions are still pinned against it — but nothing in the default path reads the curve. The audit that retired it: the ε→0.99 end duplicated α's own stated rationale (combined discount 273× for one mechanism), and the ε=0 floor was a claim about institutional COLLECTION CAPACITY pointing opposite to α's cost claim. See handoffs/guf_redefinition.md §17. |
| `GUF_PSI_B` | 1.2 | dimensionless | placeholder<br>form: NLSA Eq. 18 — the framework's own claim that land's labour-content cost peaks mid-arc and is low at both extremes. | a ground-fee-vs-automation panel across jurisdictions at differing automation levels. Nothing in the repo constrains the rise and fall speeds independently of one another, so sweep them jointly until it does. NOTE such a panel would now have to justify Ψ existing at all alongside α, not merely its shape parameters.<br>THESE NO LONGER GOVERN THE SHIPPED FEE (2026-08-20, author decision). `land/guf.psi_application` defaults to `retired` (Ψ ≡ 1) and the fee's only automation response is now α(ε) = labor_content_scaling inside U. The whole family remains LIVE, not retired, because `psi_policy="bell"` still applies it and the NLSA §4.4 boundary conditions are still pinned against it — but nothing in the default path reads the curve. The audit that retired it: the ε→0.99 end duplicated α's own stated rationale (combined discount 273× for one mechanism), and the ε=0 floor was a claim about institutional COLLECTION CAPACITY pointing opposite to α's cost claim. See handoffs/guf_redefinition.md §17. |
| `GUF_PSI_FLOOR` | 0.02 | fraction of the reference fee | placeholder | the lowest ground-use fee observed in a highly-automated jurisdiction that still levies one. The floor asserts the fee never reaches zero, which is a policy commitment awaiting an observed analogue. |
| `GUF_PSI_NORM` | 3.76527397188 | dimensionless | derived<br>form: the normalization that puts Ψ's peak at exactly 1.0. Ψ(ε) = N·ε^a·(1−ε)^b + floor peaks at ε* = a/(a+b), so N = (1 − floor) / (ε*^a · (1−ε*)^b). It now MOVES when a, b or the floor move, which is the whole point — it was pinned, and a pinned normalization of two live parameters is a stale value waiting to happen. | — |
| `GUF_ALPHA_ZETA` | 0.8 | dimensionless | placeholder<br>form: NLSA Eq. 19–20 — labour content declines with automation to an irreducible human-judgment floor. | measured labour-hours per parcel-administration task against an automation index. The O*NET/BLS spine already shipped in reference/data/ covers the occupations but has never been cut to land administration. |
| `GUF_ALPHA_FLOOR` | 0.05 | dimensionless | placeholder<br>form: NLSA Eq. 19–20 — labour content declines with automation to an irreducible human-judgment floor. | measured labour-hours per parcel-administration task against an automation index. The O*NET/BLS spine already shipped in reference/data/ covers the occupations but has never been cut to land administration. |
| `GUF_LVI_W_CENTRALITY` | 0.35 | fraction | instance<br>form: NLSA Eq. 3 — the four weights are constrained to sum to 1.0. The split between them is constrained by nothing. | **you supply** a hedonic regression of parcel transaction values on the four sub-indices FOR YOUR JURISDICTION. These weights ARE that regression's coefficients, so this is a well-defined study rather than an aspiration — it is the standard land-valuation method. Land value is local by construction: no national or global figure substitutes.<br>**shipped default** an even-handed split (0.35/0.30/0.20/0.15) summing to 1.0, standing in for a regression nobody has run here. The ORDER encodes a claim (centrality dominates, natural amenity least) that your own regression may invert. |
| `GUF_LVI_W_TRANSIT` | 0.3 | fraction | instance<br>form: NLSA Eq. 3 — the four weights are constrained to sum to 1.0. The split between them is constrained by nothing. | **you supply** a hedonic regression of parcel transaction values on the four sub-indices FOR YOUR JURISDICTION. These weights ARE that regression's coefficients, so this is a well-defined study rather than an aspiration — it is the standard land-valuation method. Land value is local by construction: no national or global figure substitutes.<br>**shipped default** an even-handed split (0.35/0.30/0.20/0.15) summing to 1.0, standing in for a regression nobody has run here. The ORDER encodes a claim (centrality dominates, natural amenity least) that your own regression may invert. |
| `GUF_LVI_W_SERVICES` | 0.2 | fraction | instance<br>form: NLSA Eq. 3 — the four weights are constrained to sum to 1.0. The split between them is constrained by nothing. | **you supply** a hedonic regression of parcel transaction values on the four sub-indices FOR YOUR JURISDICTION. These weights ARE that regression's coefficients, so this is a well-defined study rather than an aspiration — it is the standard land-valuation method. Land value is local by construction: no national or global figure substitutes.<br>**shipped default** an even-handed split (0.35/0.30/0.20/0.15) summing to 1.0, standing in for a regression nobody has run here. The ORDER encodes a claim (centrality dominates, natural amenity least) that your own regression may invert. |
| `GUF_LVI_W_NATURAL_AMENITY` | 0.15 | fraction | instance<br>form: NLSA Eq. 3 — the four weights are constrained to sum to 1.0. The split between them is constrained by nothing. | **you supply** a hedonic regression of parcel transaction values on the four sub-indices FOR YOUR JURISDICTION. These weights ARE that regression's coefficients, so this is a well-defined study rather than an aspiration — it is the standard land-valuation method. Land value is local by construction: no national or global figure substitutes.<br>**shipped default** an even-handed split (0.35/0.30/0.20/0.15) summing to 1.0, standing in for a regression nobody has run here. The ORDER encodes a claim (centrality dominates, natural amenity least) that your own regression may invert. |
| `GUF_USE_RESIDENTIAL_PRIMARY` | 10.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_RESIDENTIAL_SECONDARY` | 21.5 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_AGRICULTURAL_ACTIVE` | 2.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_AGRICULTURAL_FALLOW` | 5.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_COMMERCIAL_RETAIL` | 30.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_COMMERCIAL_OFFICE` | 22.5 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_INDUSTRIAL_LIGHT` | 17.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_INDUSTRIAL_HEAVY` | 37.5 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_INSTITUTIONAL` | 1.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_USE_CONSERVATION_CREDIT` | -6.0 | TEH per Standard Land Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 9 — midpoints of the manual's per-category ranges. | a stewardship-cost census — collective labour-hours per year actually attributable to servicing each use category (roads, utilities, inspection, dispute resolution), divided by land area. That measures the quantity the fee is DEFINED as, so it settles the levels and the ratios in one instrument rather than calibrating one against the other.<br>CALIBRATED TO A TARGET, and retagged on that basis (2026-08-09). These were scaled ×100 from the template's abstract unit values so that aggregate GUF over a 1M-population inventory (~400k residential + 20k commercial parcels) lands co-equal with levy revenue at mid-arc: residential ≈ 9.3M TEH/yr, commercial ≈ 4.1M, total ≈ 13.4M against levy ≈ 6.2M (≈2.2×). A value reverse-engineered from a desired outcome is CHOSEN under this scheme's own precedent — _ECOLOGICAL_SPIKE_INTENSITY was retagged for the same reason on 2026-08-05 — whatever the ratios between categories rest on. |
| `GUF_DEMAND_ETA_RESIDENTIAL` | 0.15 | dimensionless elasticity | placeholder<br>form: NLSA Eq. 11–13 — fee sensitivity to occupancy pressure, by land class. | measured fee-to-occupancy elasticity by land class — vacancy and turnover response in a jurisdiction that has actually varied its ground fees. |
| `GUF_DEMAND_ETA_COMMERCIAL` | 0.25 | dimensionless elasticity | placeholder<br>form: NLSA Eq. 11–13 — fee sensitivity to occupancy pressure, by land class. | measured fee-to-occupancy elasticity by land class — vacancy and turnover response in a jurisdiction that has actually varied its ground fees. |
| `GUF_DEMAND_D_MAX` | 1.8 | dimensionless multiplier | normative<br>form: NLSA Eq. 11–13 — a constitutional CEILING on D(p), not an estimate of it. | **decided by** a charter decision, not a measurement. It bounds how far demand pressure may lift a fee above its reference; 1.80 is the framework's own judgement about tolerable variation and should be argued, not fitted.<br>_no measurement settles this_ |
| `GUF_ZONE_MIN` | 0.8 | dimensionless multiplier | normative<br>form: NLSA §2.4.1 — the permitted band for a collective's local zone adjustment: governance headroom, not an estimated quantity. | **decided by** a charter decision on how much local discretion the schedule allows. No measurement settles a permitted range — the honest pointer is the deliberation, and pretending otherwise would be the error.<br>_no measurement settles this_ |
| `GUF_ZONE_MAX` | 1.25 | dimensionless multiplier | normative<br>form: NLSA §2.4.1 — the permitted band for a collective's local zone adjustment: governance headroom, not an estimated quantity. | **decided by** a charter decision on how much local discretion the schedule allows. No measurement settles a permitted range — the honest pointer is the deliberation, and pretending otherwise would be the error.<br>_no measurement settles this_ |
| `GUF_ECO_KAPPA_WATER_FILTRATION` | 1.65 | TEH per megalitre per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | crew-hours to operate treatment capacity delivering equivalent filtration — a plant staffing schedule, not a valuation study. |
| `GUF_ECO_KAPPA_FLOOD_ATTENUATION` | 0.006 | TEH per cubic metre of retention per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | crew-hours to build and maintain engineered retention of equal volume, amortized over its design life. |
| `GUF_ECO_KAPPA_CARBON` | 0.6 | TEH per tonne CO₂-equivalent per year, at ε=0.40 | measured (Tier D)<br>form: adopted EQUAL to CDR_LABOR_HOURS_PER_TONNE — labour-hours per tonne removed, from operator staffing disclosures. Supersedes the NLSA Eq. 14–15 midpoint. | operator staffing disclosures, jointly with the thermal layer. Tier D — one plant, and the sink-reversal question above is unresolved. |
| `GUF_ECO_KAPPA_AIR_QUALITY` | 5.5 | TEH per tonne particulate per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | operating hours for filtration capacity of equal removal rate. |
| `GUF_ECO_KAPPA_POLLINATION` | 1.0 | TEH per hectare-equivalent per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | measured hand-pollination labour per hectare, which is the one service in this table with a directly observed human-substitute cost (Sichuan pear orchards, Maoxian). |
| `GUF_ECO_KAPPA_BIODIVERSITY` | 0.35 | TEH per Habitat Quality Unit per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | nothing yet, and this is the weakest of the seven — a Habitat Quality Unit is a framework construct, so the pointer has to define the unit before it can price it. Managed-reserve staffing per unit area is the nearest observable. |
| `GUF_ECO_KAPPA_THERMAL` | 0.03 | TEH per cooling-degree-day per year, at ε=0.40 | placeholder<br>form: NLSA Eq. 14–15. | operating and maintenance hours for mechanical cooling delivering the same degree-day offset. Note the thermal layer treats this quantity as a physical budget rather than a service (research/thermal.py) — the two readings have not been reconciled. |
| `GUF_ECO_BETA_WATER_FILTRATION` | 0.8 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_FLOOD_ATTENUATION` | 0.7 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_CARBON` | 0.9 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_AIR_QUALITY` | 1.0 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_POLLINATION` | 0.6 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_BIODIVERSITY` | 0.7 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_BETA_THERMAL` | 0.8 | dimensionless exponent | placeholder<br>form: NLSA Eq. 15 — how fast each service's replacement cost falls with automation. The ORDERING is an argument the framework makes (physical treatment automates readily; pollination and biodiversity resist it, the same Baumol logic that bounds care abatability in Block II); the magnitudes are not constrained by anything. | per-service labour intensity of the replacement task measured at two or more automation levels. Until then the ordering is the claim and the values are placeholders that happen to encode it. |
| `GUF_ECO_KAPPA_FLOOR_FRACTION` | 0.1 | fraction of the reference κ | placeholder | the residual human oversight hours in the most automated environmental-management operation observable. Same structural claim as GUF_ALPHA_FLOOR and PERSONAL_EOH_COMPONENTS' care abatability ceiling — that judgment does not automate to zero — reached here for a third time and still without a measurement behind any of the three. |
| `GUF_ECOSYSTEM_SERVICES` | <dict: 7 keys> | dict of service name -> {kappa_ref: TEH/unit/yr, beta: exponent, unit: str} | derived<br>form: PAIRS each ecosystem service's replacement cost with its own automation exponent, both bound to the constants above rather than restated. The unit string is carried because κ is meaningless without it — 0.6 TEH/tonne-CO₂eq and 0.006 TEH/m³ are not comparable magnitudes, and a caller supplying a volume in the wrong unit gets a silently wrong surcharge. | —<br>this registry is a BINDING, not a measurement. Six of the seven κ are placeholders and the seventh (carbon) is Tier D; the β ORDERING is an argument the framework makes and the magnitudes are unconstrained. Naming the services does not ground them — it makes them reachable, which is the precondition for grounding them. |
| `SLU_HECTARES` | 0.01 | hectares per Standard Land Unit | convention<br>form: 1 SLU = 100 m² = 0.01 ha, by the NLSA definition of the unit. | —<br>the definition was carried in PROSE ONLY — "1 SLU = 100 m²" appears in land/guf.py's module header and in three docstrings, and nowhere as a value anything could read. Nothing needed it while GUF worked entirely in SLU; ecosystem service volumes arrive per HECTARE (i-Tree, FIA and every ecological survey report per unit area), so linking a service profile to a parcel needs the conversion to exist. Third prose-only number named this session, after WORLD_POPULATION and REFERENCE_FRAME_POPULATION. |
| `GUF_SERVICE_PROFILE_DECLARED` | {'carbon': 2.0, 'air_quality': 0.005} | dict of service name -> volume per hectare per year | instance | **you supply** an ecological survey of YOUR OWN land. The two services here are the ones with a public instrument that reports the right quantity in the right units per unit area: carbon      — USDA Forest Service FIA carbon estimates, or EPA GHG Inventory LULUCF by land class. FIELD: net annual sequestration per hectare by forest type. Not the stock. air_quality — i-Tree Eco / i-Tree Landscape. FIELD: annual pollution removal (PM2.5/PM10) by canopy, mass per unit area. The other five registered services are deliberately ABSENT rather than guessed: water filtration and pollination are modelled (InVEST) not measured, thermal's cooling-degree-day is a climate variable rather than a service volume, and biodiversity's "HQU" is not a standard unit anywhere — it needs a DEFINITION before it needs data.<br>**shipped default** ORDER-OF-MAGNITUDE PLACEHOLDERS, and they are not a measurement of anywhere. They exist so E(p,ε) can be exercised at a stated scale and so the ×100 calibration can be re-run with the ecological term switched ON — which has never been done, because E has been zero in every scenario the package ships. Round values are used deliberately: false precision here would read as a measurement, and the discipline reference/personal_basket.py holds is that an invented figure entering beside a measured one becomes indistinguishable from it afterwards. Treat any number computed from this profile as a SENSITIVITY, never as a result. |
| `GUF_SERVICE_RETENTION_BY_USE` | <dict: 10 keys> | fraction of natural service retained, by use category | instance<br>form: ρ_s(p) in NLSA Eq. 14 — E = Σ V_s · κ_s(ε) · (1 − ρ_s). ρ = 1 means the developed state still delivers the service in full and the parcel owes NO ecosystem surcharge; ρ = 0 means total displacement. | **you supply** impervious-surface fraction for YOUR parcels. Intake path: the USGS/MRLC National Land Cover Database publishes it directly — FIELD: NLCD Percent Developed Imperviousness, 30 m raster — and for services delivered by soil and vegetation ρ ≈ 1 − impervious_fraction is a defensible first mapping. It is measured, gridded, and already aligned to land class, which is more than any of the seven κ values can say.<br>**shipped default** ORDERED PLACEHOLDERS. The RANKING is argued (sealed surface destroys soil and canopy function; agriculture keeps soil but loses canopy; conservation keeps nearly all); the MAGNITUDES are not constrained by anything here. Do not quote a level. The ranking is what a first NLCD pass would confirm or refute, and refuting the ranking would be the interesting result.<br>THE AUTHOR'S REFRAMING IS ALREADY IN THIS TERM. Under "nature in balance asks little of us; GUF is the cost of resetting land for human use", E is structurally a DISTURBANCE measure — undisturbed land keeps ρ ≈ 1 and owes nothing, and the fee rises precisely as use displaces function. That is why `conservation` sits at 0.95 and `industrial_heavy` at 0.02: the ordering IS the claim, and it is the same shape as the 27× disturbance gradient the stewardship census found independently (federal parks 0.161 → urban 4.349 h/ha·yr, notes/guf-restoration-derivation.md §2c). Before this existed, ρ defaulted to 0.0 EVERYWHERE — asserting that every parcel, including conservation land, displaces its services totally. That is the upper bound on E, not a neutral default. |
| `GUF_USE_SCALE_FACTOR` | 100.0 | dimensionless multiplier | convention<br>form: the factor GUF_USE_* were scaled by, from the NLSA template's abstract per-category values. Stated in the GUF_USE_* tag block; named here so the servicing census can quote it without restating it. | —<br>AND THERE IS A SECOND REASON, found 2026-08-18 (`eoh scenario run guf_magnitude`). This factor scales a PER-SLU coefficient, and SLUs are an area unit, so the fee it governs is proportional to ground area and to nothing else. Re-cut by what each servicing occupation's cost actually follows, only 41.9% of the measured hours scale with area; 44.5% scale with parcel count and 13.6% with throughput. No value of this factor lets a one-basis fee track a three-basis cost. The area-scaling half alone implies ×1.18, against the ×2.82 that falls out of dividing every servicing hour by area because the fee offers nowhere else to put them. |
| `RESTORATION_BOUNDING_ASSUMPTION_H_PER_HA` | 100.0 | labour-hours per hectare | convention<br>form: the restoration cost the Phase-0 bounding exercise ASSUMED, retained as the declared comparison point for the derived figure that replaced it. | —<br>A SUPERSEDED ESTIMATE, NOT A SUPERSEDED CONSTANT — which is why this is `convention` and not `retired`. It never governed shipped output; it was a figure used in an analysis ("a plausible restoration figure, prairie seeding/planting") to bound whether a legacy restoration backlog could move the ecological domain. Deriving it from ASAE field capacity instead gives 0.87–4.81 h/ha over a whole restoration lifetime, so THE GUESS WAS 21–115× TOO HIGH. It is kept because the correction is the finding: the conclusion it supported — that no basis rebalances the domains — holds a fortiori, and a reader who saw only the derived figure could not tell that the earlier reasoning had been checked rather than quietly dropped. WHY IT WAS SO FAR OUT, which is the transferable part: most of a restoration's DOLLAR cost is not labour — it is seed, plant material, design and survey — so reasoning from a remembered cost-per-acre and converting at a wage prices all of that as labour. The same defect that made NRCS EQIP payment schedules unusable. |
| `RESTORATION_AMORTIZATION_YEARS` | 50.0 | years | convention<br>form: the horizon a one-off restoration is amortised over when expressed as an annual obligation. | —<br>a REPORTING FRAME, not a claim about how long restoration takes — the same role GUF_WRITEDOWN_AMORTIZATION_YEARS plays for write-downs, and it carries the same value for the same reason. Every figure derived through it scales inversely with it, which is asserted in the tests rather than left for a reader to assume. |
| `GUF_INFRA_MU_TRANSIT` | 0.5 | per kilometre | placeholder<br>form: NLSA Eq. 16 — exponential decay of infrastructure benefit with distance. | measured catchment gradients — transit ridership, utility connection cost, and park usage against distance. All three are routinely measured by transport and planning agencies; none has been ingested here. |
| `GUF_INFRA_MU_UTILITIES` | 0.2 | per kilometre | placeholder<br>form: NLSA Eq. 16 — exponential decay of infrastructure benefit with distance. | measured catchment gradients — transit ridership, utility connection cost, and park usage against distance. All three are routinely measured by transport and planning agencies; none has been ingested here. |
| `GUF_INFRA_MU_PUBLIC_SPACE` | 0.8 | per kilometre | placeholder<br>form: NLSA Eq. 16 — exponential decay of infrastructure benefit with distance. | measured catchment gradients — transit ridership, utility connection cost, and park usage against distance. All three are routinely measured by transport and planning agencies; none has been ingested here. |
| `GUF_CHI_EXTERNAL` | 0.3 | fraction of infrastructure burden attributed externally | placeholder<br>form: NLSA Eq. 25b. | a federation cost-allocation study — the share of a parcel's infrastructure benefit physically supplied by a neighbouring collective. In the polycentric model (research/coasean.py) this is a settlement question between collectives, so it resolves by agreement as much as by measurement. |
| `GUF_REVIEW_CYCLE_CAP` | 0.1 | fraction increase per 5-year review cycle | normative<br>form: NLSA Eq. 21. | **decided by** a charter decision. A rate cap is a commitment about how fast a leaseholder can be asked to absorb change, which is deliberation, not measurement. Precedent exists in statutory rent-review caps.<br>_no measurement settles this_ |
| `GUF_SUBSIDY_LOWER_THRESHOLD` | 0.4 | fraction | normative<br>form: NLSA Eq. 24 — a taper from a lower income threshold to a floor rate. | **decided by** a charter decision on the subsidy schedule. Distributional thresholds are political commitments; the measurable input is the income distribution they are applied to, not the thresholds themselves.<br>_no measurement settles this_ |
| `GUF_SUBSIDY_FLOOR_RATE` | 0.25 | fraction | normative<br>form: NLSA Eq. 24 — a taper from a lower income threshold to a floor rate. | **decided by** a charter decision on the subsidy schedule. Distributional thresholds are political commitments; the measurable input is the income distribution they are applied to, not the thresholds themselves.<br>_no measurement settles this_ |
| `GUF_AFFORDABILITY_THRESHOLD` | 0.25 | fraction of income | normative<br>form: NLSA Eq. 24 — the accessibility test on a primary residence. | **decided by** a charter decision, with a strong external analogue: 25% mirrors the housing-cost-burden convention in national housing statistics (the US 30% burden threshold is the better-known variant). Adopting a published threshold explicitly would move this to `convention`.<br>_no measurement settles this_ |
| `GUF_SOIL_CREDIT_RATE` | 0.05 | TEH per Standard Land Unit per unit Soil Health Index gain | placeholder<br>form: NLSA Eq. 26. | measured labour-hours of soil-building practice (cover cropping, reduced tillage, amendment) per unit index gain — an agronomic trial with a labour diary. Agricultural extension services run the trials; the labour column is the part usually missing. |
| `GUF_WRITEDOWN_AMORTIZATION_YEARS` | 50.0 | years | placeholder<br>form: NLSA Eq. 28 — Y_r, the design life over which replacement infrastructure is amortized. | engineering design lives for the specific replacement asset class. ASSET_TYPES in this file already carries measured-order threshold ages for comparable classes, so this one is reconcilable against a table we ship. |
| `GUF_EOH_ACCUMULATION_THRESHOLD` | 0.3 | fraction of ecological EOH left unfulfilled | placeholder<br>form: NLSA §9.8 — the preventive monitoring trigger. | an observed relationship between deferred stewardship and ecosystem regime shift. ECOLOGICAL_THRESHOLD in this file makes the same class of claim on the state variable rather than the deferral rate, and neither is measured; both would resolve from the same ecological time series. |
<!-- /provenance:table -->

Three findings the migration produced here, reported rather than smoothed:

1. **The `GUF_USE_*` reference rates are calibrated to a target.** They were scaled
   ×100 from the template's abstract unit values so aggregate GUF over a 1M-population
   inventory lands co-equal with levy revenue at mid-arc (≈13.4M against ≈6.2M TEH/yr,
   ≈2.2×). Under this scheme's own precedent — `_ECOLOGICAL_SPIKE_INTENSITY`, retagged
   on 2026-08-05 for being reverse-engineered from a target — that makes all ten
   `CHOSEN`. Ten constants in the fiscal spine moved from implied-derived to
   admittedly-chosen.
2. **`GUF_ECO_KAPPA_CARBON` (2.750 TEH/tonne-CO₂eq) and `CDR_LABOR_HOURS_PER_TONNE`
   (0.6 h/tonne) are the same quantity reached from two layers — a 4.6×
   disagreement inside one repo.** One of them is wrong and nothing currently
   reconciles them.
3. **The κ table's common debt is the money→hours step.** Ecosystem-service
   replacement cost is a well-established quantity, but it is published in *money*, and
   this repo's own infrastructure work found that conversion convention-dominated
   ~10.26× while every physical knob read ×1.000. So each pointer names a **labour**-hours
   engineering estimate of the replacement task, not a valuation study — the same
   discipline the infrastructure floor adopted.

---

---

## Canonical Trajectory Constants (data.py `CANONICAL_*` prefix)

These define the ideal-arc reference. A real simulation diverges from this arc;
canonical_physical_state(ε) is for testing and cross-sectional analysis only.

<!-- provenance:table "Canonical trajectory" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CANONICAL_CAPITAL_GROWTH_SLOPE` | 2.0 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_MONITORING_CAPABILITY_BASE` | 0.5 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_MONITORING_CAPABILITY_SLOPE` | 0.5 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE` | 9.0 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_KNOWLEDGE_COMPLEXITY_EXP` | 2.0 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_CAPITAL_AGE_DRIFT` | 0.2 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_ECOSYSTEM_HEALTH_BASE` | 0.9 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
| `CANONICAL_ECOSYSTEM_HEALTH_DRIFT` | -0.2 | mixed — see each line; slopes are per ε unit, bases are in the governed quantity's own units | convention<br>form: these define the IDEAL ARC, not a prediction. A real simulation diverges from it, and divergence is the point of modelling — canonical_physical_state(ε) exists for arc testing and cross-sectional analysis, so these constants are a deliberately smooth reference rather than a claim about any actual trajectory. That is why they are one family: they share a single epistemic status. | —<br>nothing, and by design — an ideal arc is a reference frame, not a measurement. What CAN be measured is how far an actual trajectory sits from it, which is what the scenario layer reports. Treat these as the axis, not the data. |
<!-- /provenance:table -->

---

## Contestability Parameters (Workstream B — `research/contestability.py`)

Added to support the contestability instrumentation (originally the bare
invariant χ(ε) = P(ε)/K_entry(ε) ≥ 1, since superseded by the §8.9
time-to-finance/two-arm form — see the Recalibration and §8.9c sections
below; the χ machinery remains as documented negative results).
See `hours-reconciliation.md §8` and `notes/workstream b.md` for derivation.

<!-- provenance:table "Contestability (reconciliation §8)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CONTESTABILITY_K0_TEH` | 1800.0 | TEH per person | placeholder<br>form: K_entry(0) — the founding cost of a viable alternative collective at ε=0. Set at ≈1.2× the annual sufficiency guarantee per person. | observed founding capitalization of real cooperatives and intentional communities per member. Mondragon and the Italian co-op sector (already cited in this file for COASEAN_COMMONS_TITHE and the indivisible reserve) both publish enough to bound it, which makes this one of the more closable debts here. |
| `CONTESTABILITY_K_SLOPE` | 1.6 | fraction of K₀ per ε unit | placeholder<br>form: the ADVERSARIAL increasing-returns regime — K_entry rises with automation because incumbents' capital advantage compounds. Chosen as the default because it is the hostile case; the replicable regime is the optimistic one. | measured entry costs in an industry across an automation transition.<br>the regime is the honest uncertainty, not the slope (reconciliation §8.5). Nothing in the data settles which regime a real automation arc follows, and the two give opposite answers about whether exit stays viable. |
| `CONTESTABILITY_K_FLOOR_FRACTION` | 0.1 | fraction of K₀ | placeholder<br>form: in the replicable regime K_entry falls, but not to zero — there is always some minimum founding cost. Structural in that respect, asserted in level. | the cheapest observed viable founding, which is the empirical floor. |
| `CONTESTABILITY_CHI_WARN` | 1.2 | dimensionless χ ratio | normative<br>form: CRIT at 1.00 is definitional, not chosen — χ < 1 means the portable endowment cannot cover entry, so exit is notional rather than substantive. WARN at 1.20 is an early-warning margin and is chosen. | **decided by** n/a — SUPERSEDED. §8.9 replaced the ratio with a TIME (t_exit ≤ one vesting period), because a stock target against a flow yields a time, not a ratio. core/dashboard.py now demotes χ to a YELLOW advisory when exit_financeable is supplied.<br>_no measurement settles this_ |
| `CONTESTABILITY_CHI_CRIT` | 1.0 | dimensionless χ ratio | normative<br>form: CRIT at 1.00 is definitional, not chosen — χ < 1 means the portable endowment cannot cover entry, so exit is notional rather than substantive. WARN at 1.20 is an early-warning margin and is chosen. | **decided by** n/a — SUPERSEDED. §8.9 replaced the ratio with a TIME (t_exit ≤ one vesting period), because a stock target against a flow yields a time, not a ratio. core/dashboard.py now demotes χ to a YELLOW advisory when exit_financeable is supplied.<br>_no measurement settles this_ |
| `CONTESTABILITY_PHI_FLOOR` | 0.1 | fraction of automation value held in common | placeholder<br>form: φ(0) — even at subsistence some automation value is commonly held (the Trust baseline). | **RETIRED** — superseded by hours_eoh.research.recalibration — §8.9b makes φ(ε) emerge from the charter formation share under a stated policy (dilution / target / escalated) rather than from a floor plus a power law. Kept for the superseded arm.<br>— |
| `CONTESTABILITY_PHI_EXPONENT` | 1.5 | dimensionless power | placeholder<br>form: sub-linear growth of commonization early in the arc (ε^1.5 rather than ε), asserting that political-economy constraints make rapid commonization hard. | **RETIRED** — superseded by hours_eoh.research.recalibration — the charter-formation model, as above.<br>— |
| `CONTESTABILITY_G_PRIV` | 0.03 | fraction per year | instance<br>form: g_priv, the private capital growth rate. The Piketty-inversion condition requires dτ/dε ≥ 0, i.e. the Trust must grow faster than private capital. | **you supply** real capital returns net of depreciation for the jurisdiction being modelled. Piketty's r series is the standard source and gives 4–5% historically — well above this 3%, so supplying your own makes the Piketty-inversion condition HARDER to satisfy, not easier.<br>**shipped default** 3%/yr, chosen below the historical range. Read the note above first: §8.9c found endogenous g_priv turns negative past ε≈0.5, so this fixed rate is not the operative reading in the adopted model and is retained for the §8.3 comparison.<br>at canonical defaults the levy-alone path to that condition is infeasible (levy_fraction ≫ 1) — the adversarial finding of reconciliation §8.3, and §8.9 showed the failure was the miscalibrated cash-Trust frame rather than the levy. §8.9c then found endogenous g_priv turns NEGATIVE past ε≈0.5, so this fixed 3% is not the operative reading in the adopted model. |
| `CONTESTABILITY_CAPITAL_YIELD_RATE` | 0.2 | fraction per year | derived<br>form: gross return on automated capital, 1/ν − δ = 1/RECAL_CAPITAL_OUTPUT_RATIO − FORMATION_DEPRECIATION_RATE = 0.25 − 0.05. Used as automated_output_teh = ε × capital_stock × yield. The same identity is already written out in FORMATION_DEPRECIATION_RATE's own block. | — |
| `CONTESTABILITY_VESTING_YEARS` | 5.0 | years of federation tenure | normative<br>form: linear vesting of the Trust dividend. Tenure is FEDERATION-wide (reconciliation §8.7b): moving between collectives never resets the clock or forfeits vested balance, and the sufficiency floor never vests at all — it is membership-independent (§8.1). Matches TIER_ASSESSMENT_INTERVAL_YEARS. | **decided by** a charter decision. Shorter vesting strengthens the marginal member's exit directly, so this is the cheapest lever on contestability the framework has — which is exactly why it belongs in deliberation and not in a data pointer.<br>_no measurement settles this_ |
<!-- /provenance:table -->

## Coasean Federation Parameters (Workstream D / Phase 3 — `research/coasean.py`)

<!-- provenance:table "Coasean federation (reconciliation §§6–7)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `COASEAN_N_MAX` | 20 | number of collectives | placeholder<br>form: N(0) — the collective count at maximum fragmentation, consolidating toward N=1 as ε→1 (the existing single-ledger model is that limit case). | an institutional study of collective scale against coordination technology — the empirical form of Coase's boundary-of-the-firm question.<br>a working hypothesis from reconciliation §6, explicitly NOT derived from institutional data. The real count depends on governance, geography and transaction-cost structure, which is the Coasean question the block is named for. |
| `COASEAN_BOUNDARY_EXPONENT` | 1.0 | dimensionless exponent | placeholder<br>form: N(ε) = max(1, round(N_max × (1−ε)^exp)). Linear by default: the count consolidates in proportion to automation. Higher values front-load consolidation. | as for COASEAN_N_MAX — the same study settles both, and neither is independently identifiable without it. |
| `COASEAN_RESERVE_FRACTION` | 0.1 | fraction of period TEH creation | placeholder<br>form: each collective's inter-collective reserve, consumed by settlement_check() for imbalance settlement. Analogous to a central-bank FX reserve ratio. | observed reserve ratios in monetary unions and clearing systems, which is a real and well-documented comparator. |
| `COASEAN_IMBALANCE_CEILING` | 0.5 | fraction of the debtor collective's reserve | placeholder<br>form: the bilateral net-flow credit ceiling (the paper's bilateral-imbalance-ceiling sketch, reconciliation §9-item-4). Within it trade continues on credit; beyond it settlement from reserve is required. | observed bilateral credit limits in real clearing unions — the European Payments Union and regional ACUs set exactly this parameter, so the precedent is concrete. |
| `COASEAN_DEPRECIATION_SLOPE` | 0.2 | dimensionless slope | placeholder<br>form: factor = 1/(1 + slope × excess_ratio) — exchange-rate depreciation per unit of unsettled imbalance beyond the ceiling. Makes over-issuance a visible exchange rate movement, which is reconciliation §7's transition-regime claim: inflation between collectives shows up as FX, not as a broken price identity. | a proposed functional form, not calibrated from anything. Observed depreciation against payment-imbalance data would settle the slope; the FORM is the substantive claim and it is the part worth arguing. |
| `COASEAN_COMMONS_TITHE` | 0.03 | fraction of each collective's common-fund levy revenue | convention<br>form: the tithe passed up to the federation commons (reconciliation §8.7a). Adopted from Italian Law 59/1992, which requires cooperatives to contribute 3% of annual surplus to the mutualistic funds — a real statutory rate, and the only real-world calibration point for a federation-level mutual levy. Tagged `convention` rather than CHOSEN because it names a specific external instrument. | n/a as a convention. Departing from 3% would make it CHOSEN and require its own argument.<br>honest adversarial finding, reported not tuned — at 3% the commons floor coverage is tiny, so the federation commons cannot carry the sufficiency floor at the precedent rate. |
| `COASEAN_INDIVISIBLE_RESERVE_FRACTION` | 0.3 | fraction of a collective's trust | convention<br>form: the unallocated (indivisible) share, credited to no individual capital account, escheating to the federation commons on merger/split/dissolution (reconciliation §8.7c). Adopted from Italian co-op law's statutory ~30% indivisible legal reserve. The allocated remainder follows members' accounts. | n/a as a convention, per COASEAN_COMMONS_TITHE.<br>the model tracks no individual accounts, so a named fraction is the minimal honest allocated/unallocated split — a tenure-derived fraction would be false precision. Adversarial finding: consolidation escheat drains per-collective dividends, so the worst marginal χ worsens toward ε→1 even as total τ holds. |
| `CONTESTABILITY_MIN_VIABLE_POPULATION` | 5000.0 | persons | placeholder<br>form: the smallest population that can staff a viable alternative collective — run the four-domain EOH pipeline with a full age distribution and a governance quorum. Deliberately far below Coasean-efficient scale at any ε: a viable alternative need only clear MINIMUM scale, accepting a coordination-cost disadvantage. Requiring optimal scale would make the entry threat vacuous at high ε, because the "alternative" would have to be the whole economy. | NOT the derivation this line used to claim. COMPETENCY_THRESHOLD × len(ESSENTIAL_DOMAINS) = 0.155 × 7 = 1.085 is a fraction GREATER THAN ONE, so it yields no headcount at all without a further assumption the repo does not make — namely how many domains one worker may be certified in at once. Condition IV is a per-domain fraction of the workforce, not a partition of it. What would settle this: a minimum-certified-count per domain (an absolute, not a fraction) plus a multi-certification rate, which core/workforce.competency_reserve() would then close over a full age distribution. UNCALIBRATED research placeholder; checked 2026-08-09. |
| `CONTESTABILITY_UNDERWRITE_FRACTION` | 0.5 | fraction of the federation commons per period | normative<br>form: the ceiling on entry underwriting (§8.8 M2). The remainder stays as the sufficiency-floor backstop (§8.7a) — underwriting must never empty the fund that backs the floor. Underwritten capital moves commons → new collective trust, staying commonized and indivisible (§8.7c), never becoming a personal claim. | **decided by** a charter decision on the split between underwriting and backstop. It is a prudential limit, so it resolves by argument — but the ARGUMENT can be made quantitative: the backstop needs to cover the floor at the worst modelled drawdown, which is computable from the fiscal layer.<br>_no measurement settles this_ |
<!-- /provenance:table -->

## Recalibration Prototype (proposed §8.9 — `research/recalibration.py`)

<!-- provenance:table "Recalibration and charter formation (§8.9)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `RECAL_CAPITAL_OUTPUT_RATIO` | 4.0 | years (capital stock per unit annual output) | convention<br>form: ν in K(ε) = K₀ + ν·Y(ε). Adopted from Piketty's β (national capital / national income), observed at ≈4–6 across economies; the LOW end is taken as the adversarially-cheap-capital posture, because a smaller commons weakens the underwriting arm. Tagged `convention` because it names a specific measured external series and then picks its conservative edge. | the capital/income ratio for the jurisdiction being modelled. Moving to the middle of the observed range would strengthen the commons, so the choice is deliberately unflattering to the framework's own result.<br>this fixed §8.8 open item 3 at the root — the old frame held an ε=0-era stock fixed while ε rose, giving τ = 17.5 for a quantity DEFINED as a share ≤ 1. |
| `RECAL_EPSILON_RATE_PER_YEAR` | 0.02 | ε per year | placeholder<br>form: arc speed dε/dt — a ~50-year subsistence→post-scarcity transition. Converts per-ε acquisition needs into per-year flows, and faster arcs tighten acquisition feasibility LINEARLY, so this is a real lever on every §8.9 result. | UNCALIBRATED placeholder, and the obvious derivation is CIRCULAR — formation_feedback_simulation() takes epsilon_rate_per_year as an INPUT to build the target arc it then chases, so reading the realized pace back out is not independent of the constant being set. Measured 2026-08-09: the null anchor (s≡0) reaches ε=0.99 in 39 yr, implying 0.0254/yr against this 0.02 — a 27% disagreement that the circularity makes uninterpretable as it stands. What would settle it: a damped fixed-point solve over (rate, realized pace), the same shape as scenarios/knowledge_base.epsilon_ref_fixed_point(), which closed exactly this defect for the ε_ref anchor. |
| `RECAL_FOUNDING_FRACTION` | 0.666666666667 | fraction of PERSONAL_EOH_BASE | placeholder<br>form: the share of a person's entropy obligation that a floor-backed founder can redirect into building an alternative collective. Two-thirds leaves a third for their own personal EOH, which the sufficiency floor is meanwhile covering. | time-use data on discretionary hours available to recipients of an unconditional floor. The cash-transfer and basic-income literature measures exactly this — how recipients reallocate time — and would replace the fraction with an observed one. |
| `RECAL_FOUNDING_LABOR_HOURS` | 666.666666667 | hours per year | derived<br>form: RECAL_FOUNDING_FRACTION × PERSONAL_EOH_BASE = 666.67 h/yr. The sufficiency floor is what frees this labour — the floor IS the entry finance of the low-ε arc, which is the substantive §8.9 claim. | n/a — it inherits PERSONAL_EOH_BASE's and RECAL_FOUNDING_FRACTION's standing, both CHOSEN.<br>was a literal 1,000.0, which the 2026-08-06 reprice orphaned from its own stated derivation (see the block comment above). Binding it means a future reprice of PERSONAL_EOH_BASE moves it, as the rationale always implied. |
| `RECAL_EXIT_HORIZON_YEARS` | 5.0 | years | normative<br>form: exit must be financeable within one vesting period (= CONTESTABILITY_VESTING_YEARS): a member who joins can accumulate the means to leave by the time they fully vest. THIS IS THE RC4 FIX — a stock target (K_entry) against a flow (savable income) yields a TIME, not a ratio, and the retired χ = P/K_entry demanded the founding stock be covered by ONE year of flow, which made the invariant nearly unclosable. | **decided by** a charter decision, bound to the vesting period rather than set independently. The substantive commitment is "within one vesting period", not the number 5 — so this resolves whenever CONTESTABILITY_VESTING_YEARS does.<br>_no measurement settles this_ |
| `RECAL_ACCOUNT_CREDIT_SHARE` | 0.5 | fraction of the annual per-capita dividend | convention<br>form: the share credited to the member's individual capital account (a stock, per §8.7b) rather than paid as cash. Zero-interest per Condition III: the account is a sum of credits, never compounded. Adopted from Mondragon's internal capital accounts, which retain a share of each year's surplus to member accounts. | n/a as a convention — but the 0.50 is rounder than Mondragon's actual practice, so the precedent supports the MECHANISM more strongly than the level. |
| `RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE` | 0.15 | fraction of a decedent's private capital estate | derived<br>form: set EQUAL to ESTATE_LEVY_FRACTION — capital estates are treated exactly like TEH estates, so this is the existing D5 doctrine extended to capital rather than a new rule. That is the whole point of the value, and it should be bound to ESTATE_LEVY_FRACTION rather than restated as a literal. | n/a — it inherits ESTATE_LEVY_FRACTION's standing (a charter decision). |
| `RECAL_ESCALATION_ESTATE_SHARE` | 1.0 | fraction of a capital estate | normative<br>form: full generational conversion while a §8.9b charter escalation is active (Piketty's inheritance-tax instrument). No living holder is ever divested; conversion happens at mortality speed. | **decided by** a charter decision — the maximum is definitionally 1.0, so the only question is whether full conversion is the right escalation, not what number it is.<br>_no measurement settles this_<br>even at 1.0 the private-capital half-life is ≈69 years at the 1%/yr death rate, so φ → target is asymptotic over generations and the exit invariant never depends on reaching it. At canonical defaults the escalation NEVER fires. |
| `RECAL_ESCALATION_CAPACITY_FLOOR` | 10.0 | number of foundings financeable per period | normative<br>form: the underwriting capacity below which the charter escalates (with the adversarial regime observed) — the commons must always be able to finance about an order of magnitude more foundings than one, because a commons that can fund exactly one alternative is not a credible entry threat. | **decided by** a charter decision on the credible-threat margin.<br>_no measurement settles this_<br>UNCALIBRATED placeholder. At canonical defaults capacity stays ≈145–280, so the trigger never fires and this constant has never been exercised by a shipped run. |
<!-- /provenance:table -->

### Formation feedback (§8.9c — `research/formation.py`)

Who actually builds K(ε) under the charter share — the investment-disincentive loop
the static §8.9b model flagged as open.

<!-- provenance:table "Formation feedback (§8.9c)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `FORMATION_DEPRECIATION_RATE` | 0.05 | fraction per year | derived<br>form: derived from CAPITAL_MACHINE_PROFILES design lives (≈20 yr → δ ≈ 1/20) — the aggregate counterpart of the per-asset lifecycle in core/capital.py. Gross return on capital = 1/ν − δ = 0.25 − 0.05 = 0.20 at defaults, and the commons replacement cost δ·T_K is a ≈20–24% haircut on the gross dividend. | n/a — it inherits CAPITAL_MACHINE_PROFILES' standing, which is CHOSEN. See DEP_RATE (0.045) for the same physical quantity derived a second way; the two should be reconciled to one. |
| `FORMATION_HURDLE_RATE_MIN` | 0.02 | net return per year | placeholder<br>form: the linear private-supply curve — no formation below the hurdle rate, all needed formation supplied at or above the full-supply rate, heterogeneous hurdle rates in between. Implies the incentive-compatible charter share s* = 1 − 0.10/0.20 = 0.50. | UNCALIBRATED placeholders. No observed economy runs at zero interest with an accumulation ceiling, so there is no series to read these off — the counterfactual is the argument and the sensitivity is the honest output.<br>THE HURDLE IS LOW BECAUSE OF CONDITION III, and that is the finding, not an assumption: idle TEH earns zero interest and leaks via the accumulation ceiling (D6) and estate dissolution (D5), so the opportunity cost of investing is uniquely small and only risk compensation remains. A fiat-like 0.18 full-supply rate gives s* ≈ 0.10 — i.e. zero interest is what makes the charter affordable, quantified. Raising the hurdle toward fiat levels IS the Condition III counterfactual. |
| `FORMATION_FULL_SUPPLY_RATE` | 0.1 | net return per year | placeholder<br>form: the linear private-supply curve — no formation below the hurdle rate, all needed formation supplied at or above the full-supply rate, heterogeneous hurdle rates in between. Implies the incentive-compatible charter share s* = 1 − 0.10/0.20 = 0.50. | UNCALIBRATED placeholders. No observed economy runs at zero interest with an accumulation ceiling, so there is no series to read these off — the counterfactual is the argument and the sensitivity is the honest output.<br>THE HURDLE IS LOW BECAUSE OF CONDITION III, and that is the finding, not an assumption: idle TEH earns zero interest and leaks via the accumulation ceiling (D6) and estate dissolution (D5), so the opportunity cost of investing is uniquely small and only risk compensation remains. A fiat-like 0.18 full-supply rate gives s* ≈ 0.10 — i.e. zero interest is what makes the charter affordable, quantified. Raising the hurdle toward fiat levels IS the Condition III counterfactual. |
<!-- /provenance:table -->

## Membership-Terms Audit Thresholds (reconciliation §8.7e — `research/membership.py`)

<!-- provenance:table "Membership-terms audit thresholds (§8.7e)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `MEMBERSHIP_VESTING_WARN_YEARS` | 10.0 | years | derived<br>form: 2 × CONTESTABILITY_VESTING_YEARS — a dividend held hostage for twice the vesting period thins the marginal member's exit without formally breaching χ. Should be BOUND to that constant rather than restated as 10.0. | n/a — inherits CONTESTABILITY_VESTING_YEARS' standing. |
| `MEMBERSHIP_EXIT_NOTICE_WARN_YEARS` | 1.0 | years of exit notice | normative<br>form: WARN at one year (friction accumulating), CRIT at three. The CRIT is close to definitional under reconciliation §8.1: exit deferred three years is nominal, not substantive, so the term itself breaches the invariant whatever χ reads. | **decided by** a charter decision, with real precedent — cooperative and partnership withdrawal-notice periods are documented and would give an observed distribution to place these against.<br>_no measurement settles this_ |
| `MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS` | 3.0 | years of exit notice | normative<br>form: WARN at one year (friction accumulating), CRIT at three. The CRIT is close to definitional under reconciliation §8.1: exit deferred three years is nominal, not substantive, so the term itself breaches the invariant whatever χ reads. | **decided by** a charter decision, with real precedent — cooperative and partnership withdrawal-notice periods are documented and would give an observed distribution to place these against.<br>_no measurement settles this_ |
| `MEMBERSHIP_MIN_HOURS_WARN_FRACTION` | 0.5 | fraction of PERSONAL_EOH_BASE | normative<br>form: WARN above half the personal entropy load, CRIT at or above the whole of it. The CRIT is definitional rather than chosen: an obligation equal to a person's entire entropy load is compulsion, not a membership term (§9-item-7). | **decided by** a charter decision on the maximum obligation membership may impose.<br>_no measurement settles this_<br>THESE ARE FRACTIONS, SO THEY MOVED WITH THE REPRICE. At PERSONAL_EOH_BASE = 1000 they are 500 and 1,000 h/yr; docs/parameter_provenance.md still printed the pre-reprice 750 and 1500. Caught by this migration and corrected — and the reason the gate now includes a curated test over prose-restated derived figures, which a value-equality check cannot see. |
| `MEMBERSHIP_MIN_HOURS_CRIT_FRACTION` | 1.0 | fraction of PERSONAL_EOH_BASE | normative<br>form: WARN above half the personal entropy load, CRIT at or above the whole of it. The CRIT is definitional rather than chosen: an obligation equal to a person's entire entropy load is compulsion, not a membership term (§9-item-7). | **decided by** a charter decision on the maximum obligation membership may impose.<br>_no measurement settles this_<br>THESE ARE FRACTIONS, SO THEY MOVED WITH THE REPRICE. At PERSONAL_EOH_BASE = 1000 they are 500 and 1,000 h/yr; docs/parameter_provenance.md still printed the pre-reprice 750 and 1500. Caught by this migration and corrected — and the reason the gate now includes a curated test over prose-restated derived figures, which a value-equality check cannot see. |
| `MEMBERSHIP_DIVIDEND_POLICY_WARN` | 0.25 | fraction of the pro-rata dividend | normative<br>form: distributing less than a quarter of the pro-rata dividend to accounts → WARN, because retention rebuilds the undistributed-commons honeypot INSIDE the collective that the indivisible-reserve escheat rule exists to defuse. | **decided by** a charter decision on minimum distribution.<br>_no measurement settles this_ |
<!-- /provenance:table -->

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

The four assessment factors themselves are **not** `data.py` constants — they are
per-occupation columns in the shipped registry, so they sit outside the coverage
gate: `f_training`, `f_demand`, `f_scarcity`, `f_impact`, each ∈[0,1], measured from
O\*NET 30.3 education+training (T), abilities/skills/work-context burden (D), BLS EP
openings+growth (S), and O\*NET+BLS impact sub-components (I), over 751 occupations
and 94.2% of US employment. Loaded via `hours_eoh.reference.onet_multipliers`; their
provenance is in
[`multiplier_provenance_v5.csv`](hours_eoh/reference/data/multiplier_provenance_v5.csv).

The map that turns them into a multiplier is in `data.py`:

<!-- provenance:table "Multipliers — measured geometric map (mult-5.1.0)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `M_FLOOR` | 1.0 | dimensionless multiplier | normative<br>form: the constitutional floor of the geometric map — one hour of the least demanding registered labour mints exactly one TEH. | **decided by** a charter decision on the floor. It is arguably the framework's cleanest normative commitment (an hour is an hour at the floor) and needs no measurement — but it is a commitment, not a measured minimum.<br>_no measurement settles this_ |
| `M_GEOMETRIC_R` | 3.2 | dimensionless ratio | derived-then-FROZEN<br>form: solved once at the reference epoch from {M_FLOOR, the band, the measured composite distribution} so that the mapped mean lands in the band. | an O*NET/BLS vintage refresh re-solves it mechanically. It is NOT a knob — re-deriving it per vintage restores the circularity the freeze exists to break. Note the consequence recorded in handoffs/multipliers-v5/ FALSIFIABILITY.md: because R is solved to make the band pass, the band pass carries no empirical content. The rank ordering and pairwise ratios do. |
| `M_COMPOSITE_Z_LO` | 0.153073096218 | composite score, dimensionless | derived-then-FROZEN<br>form: the observed composite range at the reference epoch, used to normalize z = clip((composite − Z_LO)/(Z_HI − Z_LO), 0, 1). | an O*NET/BLS vintage refresh. Frozen for the same reason as R. |
| `M_COMPOSITE_Z_HI` | 0.740198609448 | composite score, dimensionless | derived-then-FROZEN<br>form: the observed composite range at the reference epoch, used to normalize z = clip((composite − Z_LO)/(Z_HI − Z_LO), 0, 1). | an O*NET/BLS vintage refresh. Frozen for the same reason as R. |
| `M_FACTOR_WEIGHTS` | (0.3, 0.25, 0.2, 0.25) | fraction | normative | **decided by** no measurement stands behind the split between the four assessment factors — it is what the collective decides a labour-hour's value turns on. Sweep ±0.10 each; scenarios/multiplier_sensitivity.py runs it and reports that rank ordering survives while absolute levels do not.<br>_no measurement settles this_ |
| `M_IMPACT_SUBDOMAIN_WEIGHTS` | (0.3, 0.25, 0.25, 0.2) | fraction | normative | **decided by** as for M_FACTOR_WEIGHTS — a governance judgement, swept not fitted.<br>_no measurement settles this_ |
| `M_IMPACT_COMPOSITE_LO` | 0.331749422563 | impact composite score, dimensionless | derived-then-FROZEN<br>form: the observed impact-composite range at the reference epoch; the impact composite is affine outer-normalized against these bounds. | an O*NET/BLS vintage refresh. |
| `M_IMPACT_COMPOSITE_HI` | 0.751958294388 | impact composite score, dimensionless | derived-then-FROZEN<br>form: the observed impact-composite range at the reference epoch; the impact composite is affine outer-normalized against these bounds. | an O*NET/BLS vintage refresh. |
| `M_EPOCH_WEIGHT_ANCHORS` | <dict: 4 keys> | fraction, per ε anchor | normative | **decided by** the ε-dependence of the weighting is a governance judgement, not a measurement. The DIRECTION is argued (training matters less as skills stop being scarce; impact matters more as fewer hours carry more consequence); the four anchor vectors are illustrative.<br>_no measurement settles this_ |
<!-- /provenance:table -->

The map: `composite = Σ wᵢ·fᵢ`; `m = M_FLOOR · M_GEOMETRIC_R ** z`. It has **no
free parameters** — floor constitutional, R and z-range derived-then-frozen,
curvature deleted (`core/multipliers.py:reference_multiplier`).

### CHOSEN constants — each with its epistemic pointer

Every remaining CHOSEN carries the evidence that would resolve it. The `data.py`
constants are in the generated table above (`M_FACTOR_WEIGHTS`,
`M_EPOCH_WEIGHT_ANCHORS`, `M_IMPACT_SUBDOMAIN_WEIGHTS`). The load-bearing ones
**outside** `data.py` — registry-level knobs, so outside the coverage gate, with
sweep ranges in
[`multiplier_provenance_v5.csv`](hours_eoh/reference/data/multiplier_provenance_v5.csv):

| Parameter | Default | Epistemic pointer (`resolves_by`) |
|---|---|---|
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

<!-- provenance:table "Thermal sink — budget chain (P0)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `A_EARTH_M2` | 5.101e+14 | m² | physics<br>form: Earth surface area. Definitional geometry. | n/a — structural |
| `SIGMA_SB` | 5.670374419e-08 | W·m⁻²·K⁻⁴ | physics<br>form: the Stefan–Boltzmann constant. A physical constant of nature. | n/a — structural |
| `EARTH_EMISSION_TEMPERATURE_K` | 255.0 | kelvin | derived<br>form: Earth's effective emission temperature — the blackbody temperature that radiates the absorbed solar flux. Computable as (S₀(1−α)/4σ)^¼ from the solar constant and planetary albedo; neither is carried here, so the standard value is adopted and the derivation is stated rather than run. | nothing — a standard geophysical quantity. It moves only if the solar constant or planetary albedo is revised, and carrying those two would let this be computed rather than adopted.<br>EXISTS TO GIVE SIGMA_SB SOMETHING TO DO. `SIGMA_SB` is one of only two `physics`-tagged constants in this file and was read by NOTHING until 2026-08-17 — the headline "only 2 constants are physics" was true and neither was doing any work. Paired with this temperature it yields the Planck feedback 4σT³ = 3.761 W·m⁻²·K⁻¹, which bounds THERMAL_LAMBDA_FEEDBACK from above (research/thermal_lambda.planck_feedback). Before that, the Planck term lived as the prose "Planck-only ≈ 3.2" in this file's λ note and in thermal_path_c.json — a number governing the model from inside a comment, the same shape as WORLD_POPULATION and SLU_HECTARES. |
| `SECONDS_PER_YEAR` | 31557600.0 | seconds | convention<br>form: Δt_s for a one-year period — 365.25 d, the Julian year. A stated denominator; the choice between Julian, tropical and calendar years is a convention and matters at the 4th significant figure. | — |
| `THERMAL_LAMBDA_FEEDBACK` | 1.2 | W·m⁻²·K⁻¹ | bounded (Tier C)<br>form: the EQUILIBRIUM climate feedback parameter. FRAME DISCIPLINE: it pairs only with the equilibrium budget λ·ΔT − F. The historical 1.492 pairs with a transient reading the framework rejects; mixing them inflates the allowance ~6×, and thermal_lambda.budget_forcing_headroom() refuses it. | **band** 1.2–1.7 W·m⁻²·K⁻¹ — AR6-implied 1.310 at ECS 3.0 K, historical energy-budget ratio 1.492, and regression 1.693 ± 0.472 over 53 yr, the last two derived from the shipped IGCC series (research/thermal_lambda.py).<br>**errs** LOW, deliberately the conservative side: a LOWER λ means a SMALLER budget and a LARGER obligation, so 1.2 is not flattering the framework. But the band is not the real uncertainty — λ_equilibrium cannot be assessed from the shipped data at all, because converting historical to equilibrium needs the pattern effect. Across AR6's likely ECS range the budget runs from ZERO to ~11× the shipped case; never publish a ψ*-derived figure without λ and that band.<br>an assessed ECS with uncertainty — an EXTERNAL input, not a rearrangement of what we already hold.<br>BEST GUESS, AND IT STAYS ONE (checked 2026-08-05): λ_equilibrium CANNOT be assessed from the shipped data. Two independent estimators of the HISTORICAL feedback agree — 1.492 (ratio) and 1.693 ± 0.472 (regression, 53 yr) — but converting historical to equilibrium needs the pattern effect, which requires pattern-forced model experiments or paleoclimate constraints. Neither is derivable from ERF, EEI and GMST. The value is unchanged but its POSITION is now derived: it sits below the AR6-implied 1.310 (ECS 3.0 K) and below the historical energy-budget estimate, so 1.2 is the CONSERVATIVE side — a lower λ means a smaller budget and a LARGER obligation, and it was not flattering the result. SENSITIVITY IS FIRST-CLASS: across AR6's likely ECS range the budget runs from ZERO (ECS 5 K) to ~11× the shipped case. Never publish a ψ*-derived figure without λ and that band. |
| `THERMAL_F_GHG` | 3.0 | W·m⁻² | bounded (Tier C)<br>form: anthropogenic well-mixed GHG forcing, at the order of AR6. Lowering it raises the budget, which is finding F3: decarbonization and automation headroom trade against each other. | **band** 3.0–3.585 W·m⁻², from AR6-order to the measured IGCC 2025a well-mixed GHG ERF<br>**errs** LOW, AND THIS IS THE UNSAFE DIRECTION. Lowering F raises the budget, so 3.0 against the measured 3.585 overstates the allowance and understates the obligation. Superseded in practice by THERMAL_F_NET_ERF / THERMAL_F_WMGHG_ERF (measured, Tier A); this P0 constant is retained only for the scaffolding bound.<br>a published forcing assessment — already done, see the Path C block.<br>SUPERSEDED IN PRACTICE by the Path C measured values (THERMAL_F_WMGHG_ERF = 3.585, IGCC 2025a, Tier A). This P0 constant is retained for the scaffolding bound. |
| `THERMAL_F_ALB` | 0.0 | W·m⁻² | placeholder (Tier D)<br>form: net anthropogenic albedo forcing. Defaults to ZERO, which is a placeholder standing in for a quantity that is not zero — land-use albedo change is a real forcing term (IGCC assesses it at roughly −0.2 W·m⁻²). | the land-use albedo term from the same IGCC synthesis already shipped in reference/data/ for the other forcing constants — reachable from data in hand.<br>the default understates the budget rather than overstating it, so it errs toward a larger obligation, which is the framework's preferred direction of error. |
| `THERMAL_DT_LO` | 2.0 | K | placeholder (Tier D)<br>form: the assessed habitability threshold. | a habitability assessment naming the variable that actually binds — not a GMST round number.<br>THE SINGLE MOST LEVERAGED INPUT IN THE WHOLE THERMAL LAYER. It sets the overage, the drawdown job and the obligation, and it is the framework's own judgment rather than a measurement. 2.0 K is adopted because it keeps results stable and lands inside the indeterminate band, NOT because it is assessed. It may well be judged too HIGH later, and every downward revision ENLARGES the obligation (1.5 K is ~1.5× the job). Assess in land extremes and convert by ÷THERMAL_TXX_PER_GMST per C6. |
| `THERMAL_COMMONS_RESERVE` | 0.2 | fraction of the thermal budget | normative<br>form: r — the share held in reserve rather than allocated. RATCHETED DOWN ONLY, which is the governance property that matters more than the level: a reserve that can be raised again is not a commitment. | **decided by** a charter decision on precautionary margin. No measurement settles how much of a planetary budget to leave unspent.<br>_no measurement settles this_ |
| `THERMAL_ANTHROPOGENIC_DISSIPATION_W` | 2e+13 | W (global total) | measured (Tier C)<br>form: the present Φ_other reference — anthropogenic heat dissipation not attributable to modelled automation capital, ~0.04 W·m⁻² when spread over A_EARTH_M2. | a global energy-balance inventory. The order is well established from primary energy consumption; the split between Φ_other and Φ_auto is the framework's own partition and is where the uncertainty sits. |
| `THERMAL_IOTA_FLOOR_PERSONAL` | 360000.0 | joules per EOH fulfilled | placeholder (Tier D)<br>form: the per-domain thermodynamic MINIMUM joules to fulfill one EOH by machine (E27). Ordering follows the handoff: personal and infrastructure carry real caloric and enthalpy floors, while knowledge's Landauer floor is astronomically lower (finding F6). One EOH is one hour of entropy-obligation-equivalent, and the J/EOH mapping is the open quantity. | measured ι via the handoff §13.1 ladder D→C→B. Path C (research/thermal_path_c.py) already bypasses these entirely — ι and EOH_total cancel in ε_max = ε_current · budget / Φ_auto — so the measured route exists and these are retained for the provable bound, not for reported results.<br>THE GATING UNCERTAINTY OF THE P0 LAYER, and a floor-based bound can only OVERSTATE ε_max (real ι ≥ ι_floor) — so a floor bound < 1 would be CONCLUSIVE (F2), while a bound ≥ 1 is inconclusive and points to the measured-ι ladder rather than to changing these numbers. At non-degenerate constants the bound comes back ε_max ≫ 1 → INCONCLUSIVE, which is the honest P0 result: the thermodynamic floor is too low to bind automation. |
| `THERMAL_IOTA_FLOOR_INFRASTRUCTURE` | 360000.0 | joules per EOH fulfilled | placeholder (Tier D)<br>form: the per-domain thermodynamic MINIMUM joules to fulfill one EOH by machine (E27). Ordering follows the handoff: personal and infrastructure carry real caloric and enthalpy floors, while knowledge's Landauer floor is astronomically lower (finding F6). One EOH is one hour of entropy-obligation-equivalent, and the J/EOH mapping is the open quantity. | measured ι via the handoff §13.1 ladder D→C→B. Path C (research/thermal_path_c.py) already bypasses these entirely — ι and EOH_total cancel in ε_max = ε_current · budget / Φ_auto — so the measured route exists and these are retained for the provable bound, not for reported results.<br>THE GATING UNCERTAINTY OF THE P0 LAYER, and a floor-based bound can only OVERSTATE ε_max (real ι ≥ ι_floor) — so a floor bound < 1 would be CONCLUSIVE (F2), while a bound ≥ 1 is inconclusive and points to the measured-ι ladder rather than to changing these numbers. At non-degenerate constants the bound comes back ε_max ≫ 1 → INCONCLUSIVE, which is the honest P0 result: the thermodynamic floor is too low to bind automation. |
| `THERMAL_IOTA_FLOOR_ECOLOGICAL` | 36000.0 | joules per EOH fulfilled | placeholder (Tier D)<br>form: the per-domain thermodynamic MINIMUM joules to fulfill one EOH by machine (E27). Ordering follows the handoff: personal and infrastructure carry real caloric and enthalpy floors, while knowledge's Landauer floor is astronomically lower (finding F6). One EOH is one hour of entropy-obligation-equivalent, and the J/EOH mapping is the open quantity. | measured ι via the handoff §13.1 ladder D→C→B. Path C (research/thermal_path_c.py) already bypasses these entirely — ι and EOH_total cancel in ε_max = ε_current · budget / Φ_auto — so the measured route exists and these are retained for the provable bound, not for reported results.<br>THE GATING UNCERTAINTY OF THE P0 LAYER, and a floor-based bound can only OVERSTATE ε_max (real ι ≥ ι_floor) — so a floor bound < 1 would be CONCLUSIVE (F2), while a bound ≥ 1 is inconclusive and points to the measured-ι ladder rather than to changing these numbers. At non-degenerate constants the bound comes back ε_max ≫ 1 → INCONCLUSIVE, which is the honest P0 result: the thermodynamic floor is too low to bind automation. |
| `THERMAL_IOTA_FLOOR_KNOWLEDGE` | 1e-06 | joules per EOH fulfilled | placeholder (Tier D)<br>form: the per-domain thermodynamic MINIMUM joules to fulfill one EOH by machine (E27). Ordering follows the handoff: personal and infrastructure carry real caloric and enthalpy floors, while knowledge's Landauer floor is astronomically lower (finding F6). One EOH is one hour of entropy-obligation-equivalent, and the J/EOH mapping is the open quantity. | measured ι via the handoff §13.1 ladder D→C→B. Path C (research/thermal_path_c.py) already bypasses these entirely — ι and EOH_total cancel in ε_max = ε_current · budget / Φ_auto — so the measured route exists and these are retained for the provable bound, not for reported results.<br>THE GATING UNCERTAINTY OF THE P0 LAYER, and a floor-based bound can only OVERSTATE ε_max (real ι ≥ ι_floor) — so a floor bound < 1 would be CONCLUSIVE (F2), while a bound ≥ 1 is inconclusive and points to the measured-ι ladder rather than to changing these numbers. At non-degenerate constants the bound comes back ε_max ≫ 1 → INCONCLUSIVE, which is the honest P0 result: the thermodynamic floor is too low to bind automation. |
<!-- /provenance:table -->

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
and national records ship in [`reference/data/thermal_path_c.json`](hours_eoh/reference/data/thermal_path_c.json)
with per-input provenance tiers (A retrieved / B constant / C training-data-unverified
/ D framework placeholder) — **the weakest data drives the strongest finding, so
read the tiers before citing.** Structural constants added to `data.py`:

<!-- provenance:table "Thermal sink — Path C measured inputs" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `A_LAND_CLAIMED_M2` | 1.35e+14 | m² | measured (Tier B)<br>form: land area ex-Antarctica — the denominator for land-allocated ψ*. Geographic rather than a free parameter, but the EXCLUSION of Antarctica is a framework decision about what land can bear an allocation, not a measurement. | a standard geographic dataset; the figure is not in dispute. What is in dispute is the exclusion rule, which ETA_LAND_MASK_THRESHOLD also touches. |
| `THERMAL_F_NET_ERF` | 3.366 | W·m⁻² | measured (Tier A)<br>form: TOTAL effective radiative forcing, IGCC 2025a p50 at time = 2025 — the BUDGET basis per C4, because natural forcing consumes the habitability allowance regardless of cause. Verified 2026-08-03 against the shipped synthesis timeseries (`total` column). Correction C5 replaced AR6 2019-baseline Tier C values; the recalled 2.72 was right for the wrong year. | an annual IGCC refresh. Guardrail I quantity — measured, published with uncertainty, never negotiated. |
| `THERMAL_F_NET_ERF_P05` | 2.602 | W·m⁻² | measured (Tier A)<br>form: the IGCC 2025a p05/p95 bounds on total ERF. This band is what makes the determinacy map computable — the layer withholds a budget where its sign is undetermined across the band rather than reporting the p50 alone. | an annual IGCC refresh. |
| `THERMAL_F_NET_ERF_P95` | 4.102 | W·m⁻² | measured (Tier A)<br>form: the IGCC 2025a p05/p95 bounds on total ERF. This band is what makes the determinacy map computable — the layer withholds a budget where its sign is undetermined across the band rather than reporting the p50 alone. | an annual IGCC refresh. |
| `THERMAL_F_ANTHRO_ERF` | 3.104 | W·m⁻² | measured (Tier A)<br>form: anthropogenic ERF alone, including aerosol cooling — the REMOVABLE forcing, hence the defensible F3 gain basis. Carried separately from the budget basis because decarbonization gain and budget consumption are different questions: only the anthropogenic part is removable by labour. | an annual IGCC refresh. |
| `THERMAL_F_WMGHG_ERF` | 3.585 | W·m⁻² | measured (Tier A)<br>form: well-mixed GHG ERF alone (IGCC 2025a `wmghg`) — the forward-looking basis as aerosol cooling declines. | an annual IGCC refresh. |
<!-- /provenance:table -->

<!-- provenance:table "Thermal sink — drawdown chain" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CO2_FORCING_COEFFICIENT` | 5.645 | W·m⁻² per ln(C/C₀) | measured (Tier A)<br>form: DERIVED by OLS of the IGCC 2025a CO₂ ERF series on ln(concentration) over 350–426 ppm (n=38) — the range a drawdown actually traverses. Self-validating: the fitted intercept implies C₀ = 279.8 ppm against the accepted pre-industrial 278. Myhre's classic 5.35 runs 5.2% low over this range. | an IGCC vintage refresh re-fits it. Moved from recalled to derived in the measurement spine pass. |
| `CO2_CONCENTRATION_PPM` | 425.65 | ppm | measured (Tier A)<br>form: IGCC 2025a annual mean at 2025. | an annual refresh. |
| `CO2_PPM_TO_GT` | 7.82 | GtCO₂ per ppm | derived<br>form: atmospheric mass 5.148e18 kg × 1e-6 × (44.01/28.96 molar ratio). Derivable arithmetic from physical constants, not fitted to anything. | n/a — it follows from atmospheric mass and molar masses. |
| `CDR_GROSS_REMOVAL_FACTOR` | 1.8 | dimensionless gross/net ratio | placeholder (Tier D)<br>form: removing CO₂ from the air lets ocean and land sinks OUTGAS back, so the gross tonnage removed exceeds the concentration drop achieved. | ESM CDR reversibility experiments (Zickfeld et al.).<br>OMITTING IT WOULD UNDERSTATE THE OBLIGATION ~2× and bias the solvency gate toward passing — exactly the wrong error, which is why a Tier D placeholder is carried rather than the term dropped. |
| `CDR_ENERGY_GJ_PER_TONNE` | 4.0 | GJ per tonne CO₂ removed | bounded (Tier C)<br>form: DAC-order energy intensity; recalled range 2–6. | **band** 2–6 GJ per tonne CO₂, DAC-order<br>**errs** NEITHER. Mid-band, and it does not affect the EOH obligation at all — the energy term cancels out of it (EOH = gross tonnes × labour-hours/tonne), so it drives only the programme's own dissipation.<br>published plant LCA. Together with CDR_LABOR_HOURS_PER_TONNE this DERIVES ι_drawdown = (GJ/t)/(h/t) ≈ 6.7e9 J/EOH, so the framework's drawdown ι is a function of two plant observables rather than a third free placeholder. |
| `THERMAL_PROGRAMME_YEARS` | 40.0 | years | normative<br>form: the horizon over which the drawdown obligation is discharged. 40 yr keeps the programme inside a single lifetime of responsibility: the generation that incurred the debt discharges it, rather than booking the benefit and willing the work to people who did not choose it. | **decided by** nothing measurable. This is an ETHICAL choice about who bears the work, not a technical one, and it should be argued as such — which is why the pointer says so rather than naming a study that would not settle it.<br>_no measurement settles this_<br>A REAL LEVER — the obligation scales as 1/horizon, so 30 yr is 1.33× the annual load and 100 yr is 0.4×. |
<!-- /provenance:table -->

<!-- provenance:table "Thermal sink — allocation doctrine" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CDR_ALLOCATION_BASIS` | 'responsibility' | policy switch — "responsibility" | normative<br>form: how the global drawdown job is split across collectives. "responsibility" (cumulative emissions) is chosen over "population" because a collective cannot burden others with the consequences of choices it made. See allocation_share(). | **decided by** nothing measurable — a governance decision, not physics. Both options are implemented so the choice is visible and reversible rather than baked in.<br>_no measurement settles this_ |
| `CDR_RESPONSIBILITY_BASIS` | 'incl_luc' | policy switch — "incl_luc" | normative<br>form: which cumulative-CO₂ measure weights responsibility. "incl_luc" (fossil + cement + land-use change) is the whole atmospheric burden the drawdown must remove, and it matches the forcing coefficient, which was fitted to a concentration record that already reflects land use. "fossil" has lower uncertainty but leaves ~33% of the burden unallocated. | **decided by** consumption-based allocation once trade data supports it. Recorded for live implementations to settle, not resolved by the model.<br>_no measurement settles this_<br>A LIVE EQUITY QUESTION and a sign-off item. Including land use moves substantial burden onto collectives that were often converting land under external demand, and the framework cannot yet trade-adjust — OWID consumption-based emissions begin only in 1990, far too short for a cumulative measure. |
| `ETA_BASIS` | 'clear_sky' | policy switch — "clear_sky" | normative<br>form: which radiative-efficiency field weights a collective's land allocation. Clear-sky measures the STRUCTURAL radiative transparency of the column, which is what "this land's share of the sink" should mean. All-sky η credits a collective for being cloudy — cloud cover is not a policy lever, is partly endogenous to warming, and is the noisiest part of the field, so an all-sky rule rewards weather. | **decided by** a governance decision on what the allocation is meant to track. The FIELDS themselves are measured (ERA5, 258 collectives); the choice between them is not.<br>_no measurement settles this_<br>NOT COSMETIC — the two differ by up to 0.27 in η (RMS 0.051, p95 0.085), so all-sky is reported alongside as the physical reality check and the per-collective gap must stay visible. |
| `ETA_LAND_MASK_THRESHOLD` | 0.5 | ERA5 land-sea-mask fraction ∈ [0,1] | normative<br>form: lsm ≥ this counts as land (§5 decision 1: territorial sea excluded). | **RETIRED** — superseded by hours_eoh.research.thermal_path_c.load_eta_land — the shipped η dataset it returns records, in its own `_method.weighting` field, "cos(latitude) x land FRACTION (lsm), not a binary threshold, so partial coastal cells contribute their actual land area".<br>**decided by** superseded. The continuous-fraction weighting is the operative decision and it lives with the data that implements it, which is the right place for a method choice the generation step makes.<br>_no measurement settles this_<br>THE SHIPPED DATA CONTRADICTED THIS CONSTANT AND NOTHING RECORDED IT (found 2026-08-17 by a dead-code sweep). Its `form:` asserted that "the ERA5 mask is a fraction, so a THRESHOLD IS REQUIRED"; the η dataset that actually shipped states in its own method field that it used the continuous land fraction and explicitly NOT a binary threshold. The generation step answered the question this constant was posed to settle, and answered it the other way — so §5 decision 1 was superseded in practice while still being carried here as live governance. It is retired rather than wired, because wiring it would REINTRODUCE the binary threshold the data deliberately avoided: partial coastal cells would flip to all-or-nothing instead of contributing their actual land area, which is strictly worse and would silently change every per-collective η. The wider lesson is that the provenance gate proves a constant is DOCUMENTED, not that it is USED — this one was tagged, audited, and contradicted by the dataset it governed. |
| `CDR_UNATTRIBUTED_POLICY` | 'pro_rata' | policy switch — "pro_rata" | normative<br>form: what happens to emissions belonging to no territory — international shipping and aviation, 46 GtCO₂ / 2.49% of the cumulative fossil total. "pro_rata" redistributes across collectives in proportion to existing shares, so shares sum to 1 and no part of the obligation is left without a bearer: we all inherited the world as it is. "unallocated" leaves the gap open, which means the commons silently absorbs it — and silence is the objection. | **decided by** consumption-based allocation once trade data supports it. OWID's begins in 1990, and 1990-forward is where the framework will start when it does.<br>_no measurement settles this_ |
<!-- /provenance:table -->

<!-- provenance:table "Thermal sink — observed climate state" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CDR_LABOR_HOURS_PER_TONNE` | 0.6 | labour-hours per tonne CO₂ removed | measured (Tier D)<br>form: a ~1 Mt/yr plant at ~300 staff × 2000 h. Together with CDR_ENERGY_GJ_PER_TONNE this DERIVES ι_drawdown ≈ 6.7e9 J/EOH — ~4 orders above the infrastructure ι floor, as expected: drawdown is energy-intensive and labour-thin. | operator staffing disclosures.<br>A CANDIDATE FOR THE DOMAIN-BALANCE DEFECT. Either ECOLOGICAL_BASE_RATE is low by 2–3 orders or this is, or both; nothing in current data settles it. GUF_ECO_KAPPA_CARBON reached the SAME quantity from the land layer at 2.750, a 4.58× disagreement inside one repo; it is now bound EQUAL to this constant (2026-08-09, author decision), so this figure carries both layers and a staffing refresh moves both. TestCarbonKappaReconciliation enforces it. |
| `THERMAL_F_NATURAL_ERF` | 0.262 | W·m⁻² | measured (Tier A)<br>form: solar + volcanic ERF at 2025 (IGCC 2025a `natural`). Consumes budget per C4 but is NOT removable by labour, so it is the floor on achievable forcing and the wedge between the budget basis and the F3 gain basis (§10.1). | an annual IGCC refresh. |
| `THERMAL_GMST_OBSERVED` | 1.23 | K (GMST anomaly) | measured (Tier A)<br>form: observed GMST anomaly, 2015–2024 mean (IGCC 2025a). Paired with the committed F/λ to expose the pipeline — the warming already bought and not yet delivered (§10.3). | an annual refresh. |
| `THERMAL_TXX_PER_GMST` | 1.48 | K per K (dTXx/dGMST) | measured (Tier A)<br>form: land extreme amplification (C6). OLS on the ERA5/Berkeley/HadEX3 mean TXx series against GMST, 1950–2025, n = 76, slope 1.483. Per-dataset spread 1.33–1.57 is the honest uncertainty. | annual refresh. Guardrail I quantity. |
| `THERMAL_U_FLOOR` | 0.5 | utilization fraction | placeholder<br>form: the utilization boundary separating the Standing-exposure regime. | observed variance in Φ and ψ* — a measured quantity, not a chosen value, and it should stop being a constant once that variance is characterized. |
| `THERMAL_EPS_CURRENT` | 0.4 | ε (dimensionless automation fraction) | bounded<br>form: the framework's current-equilibrium ε for Eq. C1 — set to the arc midpoint. | **band** 0.2–0.6, the range global_ceiling() reports ε_max over, so the chosen point always travels with its sensitivity<br>**errs** NEITHER. ε_max is directly PROPORTIONAL to this, so the band matters more than the point — and the deeper objection is that ε is meant to be an observable, not an input. Superseded wherever an inventory exists: thermal_capital.epsilon_current_from_inventory() derives it from the same capital that produces Φ.<br>a measured world capital inventory in TEH.<br>SUPERSEDED WHERE AN INVENTORY EXISTS. thermal_capital.epsilon_current_from_inventory() derives ε from the same capital that produces Φ, via civilization_epsilon, and capital_thermal_ceiling() now defaults to that. This constant survives for global ε_max, where no measured world capital inventory in TEH exists — and there global_ceiling() reports a band over ε_current ∈ [0.2, 0.6] so the chosen value travels with its sensitivity. |
<!-- /provenance:table -->

Also derived in this layer but **not** a `data.py` constant, so outside the
coverage gate:

| Parameter | Default | Units | Kind | `resolves_by` |
|---|---|---|---|---|
| λ_historical (derived) | 1.492 | W·m⁻²·K⁻¹ | measured (**Tier A**) | `(F − N)/ΔT` from IGCC 2025a total ERF, Earth energy imbalance and GMST. Four windows 1995–2024 agree within 5% (1.466–1.537), so it is a property of the data not the window. Band 0.52–2.44, dominated by **aerosol** forcing uncertainty. Pattern effect vs AR6-implied equilibrium: **+0.182**, the expected sign and scale — an independent check the derivation behaves. **Not for the budget.** |

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

<!-- provenance:table "Capital thermal profiles (§12.2 dual-output)" -->
| Parameter | Default | Units | Tag | What would settle it |
|---|---|---|---|---|
| `CAPITAL_THERMAL_PROFILES` | <dict: 11 keys> | power_intensity W per TEH; embodied_energy J per TEH | placeholder (Tier D)<br>form: the two new physical fields per capital type that turn a capital stock into a thermal load Φ_auto. Kept as a SEPARATE parallel dict rather than merged into CAPITAL_MACHINE_PROFILES, so the established EOH capital model stays visibly distinct from the experimental thermal overlay. | power intensity ← measured energy-use intensity by capital class (IEA end-use / sectoral energy balances); embodied energy ← LCA inventories (ecoinvent, EPDs). Both are Path-D placeholders awaiting exactly those two sources.<br>relative ORDERING is defensible (compute and industry heavy; software and monitoring light); the absolute scale is anchored only to order-of-consistency with Path C's measured ~2200 W·person⁻¹ net-additive dissipation, NOT fitted. |
| `THERMAL_GRID_KAPPA_DEFAULT` | 0.93 | dimensionless net-thermal-addition coefficient | measured (Tier C)<br>form: κ̄ of the grid serving the capital (§8.1). Default = world fossil+nuclear share (Path C, 2025). A fully flux-redirecting grid → 0, because renewable generation redirects an existing flux rather than adding a new one. | the PHYSICAL grid mix serving the capital, not procurement contracts — a collective buying renewable certificates on a fossil grid still dissipates fossil heat, and κ̄ measures the electrons, not the paperwork. |
<!-- /provenance:table -->

`machine_dissipation_from_capital` derives Φ_auto = Σ (teh·condition·power_intensity
+ teh·embodied/(design_life·Δt_s))·κ̄ — the thermal twin of
`machine_eoh_from_capital`, reusing its resolved stock (DRY). **Honest status:** the
intensities are CHOSEN placeholders — relative ordering defensible (compute/industry
heavy), absolute scale anchored only to order-of-consistency with Path C's measured
~2200 W·person⁻¹ (a well-invested standard-tier collective reads ~3200 W·person⁻¹,
within ~1.5×; NOT fitted). Path-B-shaped structure on Path-D magnitudes: the
deliverable is the closed loop (one inventory → {ε, Φ, U, thermal ceiling}), not the
numbers. Advisory only.
