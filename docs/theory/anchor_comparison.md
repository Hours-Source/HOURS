# What Anchors a Unit of Account

!!! note "Status — published as work in progress, 2026-09-12"

    What is claimed here has been checked and run against the code. §6 is the
    open research front, §7 is what would make us abandon each claim, and §8 is
    what the anchor claims and at what strength. None of the three promises
    resolution.

### How to read this page

**Three habits this page keeps, because the alternative is the failure it is
trying to avoid:**

1. **A result and the sentence about it are different things, and both are
   checked.** Twice in one week the arithmetic was right and the sentence was
   wrong — a maximum over four sample points described as "the peak", and a
   falsifier answered for half of what it names. Both errors flattered the
   framework.
2. **A falsification condition that ran is kept, whatever it did.** §7 has one
   that **fired and was then answered**, and one that was **run, re-opened when
   its scope was checked, and answered again on a declared default**. Neither
   is struck for tidiness.
3. **Scope is stated wherever a number has one.** "No crossover" is not a claim
   about verification cost if the census measured only the apparatus, and this
   page says which it measured.

**Where a figure is calibration, this page gives its shape; where it is
structure, it gives the value.** A designed zero, an exact unit elasticity, a
verdict, a count of anchors — those are stated and will not drift. Everything
else names the function that computes it, and
`python3 utils/anchor_page_figures.py` prints the current values. The
structural statements on this page are checked against those functions by
`tests/test_anchor_page_figures.py`, so a sentence here that stops being true
fails the build.

[Prior Art](prior_art.md) audits this framework's ancestors — the labour-currency
lineage that died of the same wounds for two centuries. This page audits its
contemporaries: the anchors actually in use. Prior Art answers *why won't this
die the way Owen did.* This page answers *why this unit of account rather than a
dollar, an ounce, or a satoshi.*

---

## 1. The question

The tempting question is *why does entropy deserve monetary value?* It is the
wrong one. It invites a metaphysical argument this framework cannot win and does
not need, and no incumbent anchor could win it either.

The answerable question is narrower: **what constrains issuance, and can an
outsider inspect the constraint?** On that question every anchor has a real
answer, and the answers differ in ways that can be written down.

This shifts the burden usefully. The framework does not have to show that an hour
has intrinsic value. It has to show that a floor derived from registered
obligation is more inspectable than a floor derived from geology, decree,
protocol, or credit — and to say plainly where it is not.

What this page is not: an argument that HOURS is more valuable than the
alternatives, an argument about the worth of human life, or a prediction of
adoption.

---

## 2. What "anchor" means here

An **anchor** is what constrains issuance and supplies a reference frame. It is
not backing, not value, and not price.

**HOURS anchors the floor, not the price.** The computed number is the level
below which the collective guarantees that work is available and paid.
Discovery sets everything above it — `core/prices.floor_price()` takes a
`market_premium` argument that defaults to `0.0`, and that seam is where a
discovered price lives.

**Every comparison on this page is between floors and issuance constraints, not
between values.**

---

## 3. The candidates

Eight anchors, classified in `research/anchor_determinacy.py`. Each is
classified from its *own* definition at its advocates' strongest reading; no
rival is simulated. That is deliberate — a comparison whose rivals you model
yourself is the easiest thing in the world to rig, and the module carries a test
forbidding it to import anything outside `hours_eoh.core.*`.

Three properties are asked of each anchor:

- **Determinate** — does the issuance rule follow from what the anchor *is*?
- **Responsive** — does the monetary base move with the physical capacity of the
  people using it?
- **Registers obligation** — must an activity have fulfilled a recognised
  obligation before it can mint?

### 3.1 Gold

Scarce, durable, divisible, hard to counterfeit, legible for millennia. Issuance
is governed by geology. The structural weakness is that geology is indifferent to
the population using it: a new deposit does not feed anyone, and a depleted seam
does not make a civilization less able to feed itself.

*What it does better:* its audit is a scale. You can weigh an ounce; nobody has
to agree about what it fulfilled. That is a real advantage and this framework
does not have it.

**But gold's verification cost is lower, not zero** *(author decision,
2026-09-11)*. Assay, refining accreditation, vaulting and chain-of-custody are
incurred at every transfer boundary — a claim on gold that has never been
assayed is a claim on a belief about gold. The difference is **where the cost
sits**: gold's is per-transfer and borne privately by whoever assays; this
framework's is continuous, public, and partly measured. **A cost the holder can
see is this framework's own stated criterion**, so the comparison on this axis is
about placement and visibility rather than presence.

*That reframing changes no arithmetic.* Gold's cost is **unmeasured here** and is
**not claimed** to be comparable in size. HOURS' own is measured for the
apparatus — a **low single-digit percentage of the obligation** at its peak — and
priced for the registrant side by the register's declared recording cadence (§6).
What changed is that the gap has to be measured rather than conceded.

### 3.2 Fiat

Not "unbacked" — that is the weak criticism and this page declines it. Fiat is
supported by taxation, legal tender, central banking, payment infrastructure,
courts, and network effects, and it is defended by its own literature as a social
convention sustained by institutions rather than as a natural fact.

The precise criticism is narrower: the ultimate constraint is institutional
discretion rather than a measurable quantity, and that discretion is exercised on
a schedule the holder does not see.

The classification records fiat as **indeterminate**, not unresponsive. An anchor
whose issuance is discretionary has no capacity response that follows from what
it *is*; recording that as "unresponsive" would be a claim about monetary policy
this framework is not entitled to make. Treating it as indeterminate is what lets
the comparison run without modelling monetary policy at all.

*What it does better:* proven at civilizational scale for a century, with an
elastic crisis response that a floor-anchored system deliberately gives up.

### 3.3 Bitcoin and fixed-supply protocols

Scarcity from protocol consensus. The comparison that matters is a thought
experiment: if a civilization doubled its capacity to meet its obligations, the
base would not move; if it halved, likewise. Supply is indifferent to the thing
money is a claim on — which is the property its holders are buying.

*What it does better:* the issuance rule is fully specified and requires **no
measurement of the world at all** — exactly the measurement debt this framework
carries, and the reason a fixed-supply protocol can be audited by anyone with a
node while this framework requires a register somebody has to run.

**But a proof-of-work anchor's verification cost is not zero either** *(author
decision, 2026-09-11)*. It is the security budget, and it is the one number such
a system publishes continuously. Calling it zero misreads the design: it is not
an absence of verification cost, it is verification cost paid openly and by
construction — which is the same criterion this framework claims for itself. So
here too the comparison is about placement and visibility rather than presence.

*And here too it changes no arithmetic.* The protocol's cost is unmeasured on
this page and is not claimed to be smaller or larger than this framework's. The
measurement debt in the line above is the real concession and it stands.

### 3.4 Debt and credit money

Credit money anchors to *promised future* production; HOURS anchors to *past
fulfilment*. That is a real difference, and it comes with a real cost: things
must be built before the labour that pays for them occurs, so HOURS still needs
credit. The capital-formation mechanics carry it.

*What it does better:* it finances the future, which a fulfilment-anchored unit
does not do natively. This is a gap, not a concession.

### 3.5 Labour vouchers

Covered on the [Prior Art](prior_art.md) page — Warren, Owen's NELE, Ithaca, time
banking, the *trudoden*, Marx contra Gray. One point belongs here: a labour
voucher mints for hours worked, so a hole dug and refilled mints as readily as a
bridge repaired. HOURS registers the obligation *before* the labour, so surplus
effort against no registered obligation mints nothing.

### 3.6 Energy certificates

Covered under Technocracy on the Prior Art page. Its relevance here is as a
warning aimed at this page: a measurable anchor confers measurability on the
anchor, not on the human valuations the unit must carry.

### 3.7 Mutual credit

**The closest living relative, and the reason this framework's claim is narrower
than it first appears.** Mutual credit issues at the moment a bilateral
obligation is incurred and extinguishes when it is settled. Its base moves with
activity; it registers obligation; its rule follows from what it is. WIR Bank has
run on this basis in Switzerland since 1934.

On all three properties asked here, **mutual credit and HOURS are the same**. The
difference is not structural, it is one of scale: a bilateral obligation is
legible to the two parties, and does not obviously extend to a population where
the parties do not know each other. What HOURS proposes is a registration
apparatus that makes obligation legible at population scale — and that apparatus
is precisely what it must justify, since it is also its largest governance risk.

---

## 4. The comparison

| Anchor | Issuance constrained by | Moves with capacity? | Registers obligation? | Principal vulnerability |
|---|---|---|---|---|
| Gold | Geology | No — indifferent by design | No | No relation to the population using it |
| Bitcoin | Protocol consensus | No — indifferent by design | No | Same, by construction rather than by nature |
| Fiat | Institutional discretion | Indeterminate | No | The constraint is a decision, on an unseen schedule |
| Debt money | Credit creation against promised output | Indeterminate | No | Anchored to promises, not to fulfilment |
| Labour voucher | Hours worked | Yes | **No** | Mints for effort regardless of whether anything was owed |
| Energy certificate | Energy throughput | Yes | **No** | Same as voucher, with a physical unit |
| **Mutual credit** | Bilateral obligation incurred | **Yes** | **Yes** | Does not evidently scale beyond mutual acquaintance |
| **HOURS** | Registered obligation fulfilled | **Yes — see below** | **Yes** | Registration is the sole lever on issuance (§6) |

**The HOURS row does not win this table.** Two anchors hold all three properties,
and the other has ninety years of operating history that this one does not.

**And "moves with capacity" is narrower than it reads.** Measured on a
million-person frame at capability 0.40, halving each input moves minting by:

| Shock | Minting | Obligation |
|---|---|---|
| Labour halves | **−50%** | **0.0%** |
| Capital halves | **0.0%** | a few percent |
| Ecosystem health halves | **0.0%** | **0.0%** |

**The zeroes are structural; the non-zero obligation figure is calibration.**
Halving labour halves minting exactly, because registration is unit elastic
(**1.000**). The three 0.0% entries are designed and will not drift. The capital
figure is a calibrated magnitude, deliberately not quoted to a decimal — it has
moved twice — and `hours_shock_response()` returns all six live.

So the base responds to **labour alone** — not to capital and not to ecological
condition. The ecological blindness is deliberate, a charter commitment rather
than an omission (author decision, 2026-09-02); the capital figure is not a
commitment, it is a measurement, and it is the sharper of the two for §5.2's
claim about endogenous supply.

**Why supply must not respond to ecological condition.** If issuance rose as
ecosystems degraded, degradation would expand the money supply — the system
would pay itself for damage, and the incentive would point at destruction. If
issuance fell instead, a damaged collective would lose the capacity to fund its
own repair exactly when it needed it most. Neither sign is acceptable, so the
base is held blind on purpose.

The obligation does not vanish; it is **assigned elsewhere**. The recurring
ecological cost sits in the ground-use fee, where halving ecosystem health
roughly doubles the charge (`ecological_response_by_path()` for the live
figure) — borne by the holder of the land, at the point where the condition is
actually determined, and without touching what the currency is worth. Decompose
first, assign second: the reset cost is priced, and it is priced where the
decision to degrade is made.

---

## 5. What is actually claimed

Three claims. **Each is stated only as far as it has been checked**, with the
mechanism that carries it and the open edge that bounds it. The open edges are
where the work is pointed; none of them is assumed to close.

### 5.1 Obligation precedes issuance

No unit exists without a labour record against a registered obligation. One mint
call site exists across `core/`, `land/` and `scenarios/`, enforced by an AST
test rather than a text scan. Surplus labour against no obligation mints nothing
at any scale tried; zero registration mints exactly zero while the obligation
still stands. Registration binds hard rather than formally: at ε = 0.40 **most
of human EOH mints nothing** (`registration_leverage()` for the share).

*Open, and load-bearing:* `available_labor_eoh` defaults to unsupplied, so a
pipeline run without it mints from obligation **demanded**, not obligation
**served**. Supply the field and a labour shortfall is deferred rather than
minted; leave it unset and the middle link of the chain is assumed. The
institutional entry point, `collective_snapshot()`, accepts it as of this
publication and says in its verdict which of the two it computed — **an
institution that does not supply its labour data is measuring demand.**

*Open, and now priced on both sides:* verification is itself work, and it
appeared in none of the four EOH domains until it was counted. The **apparatus**
— the people whose job is verifying — is measured from occupational headcounts,
peaks at a **low single-digit percentage of the obligation**, and does not cross
it anywhere on the arc.

**That is not the same as verification being cheap**, because the hour a
registrant spends documenting their own fulfilment is nobody's occupation. That
side is priced by **how often the register records** — an `instance` each
collective declares, defaulting to **episodic** — and it is priced in the one
unit that does not depend on how the apparatus was counted: **share of the
obligation**. On the shipped default every episodic regime fits inside the
labour a population has left over, with an order of magnitude to spare. A
register that records *continuously* does not fit until mid-arc: human-performed
continuous recording runs at clinical-documentation intensity, and the cheap
machine-mediated regime needs a prior document that unpaid personal fulfilment
does not produce. §6 gives the verdicts.

*Still open:* the term is **reported beside the accounts, not added to them.**
For unpaid personal fulfilment the documentation hour is provably absent from the
base — the time diaries it is built on were kept where no register existed — so
adding it there would not double-count; for documentation embedded in paid work
it is already inside an occupational census. Whether the personal-side hour
enters the obligation is an author decision that has not been taken.

### 5.2 Supply is endogenous to the population

The monetary substrate is constrained by the capacity of the people using it.
Geology, protocol and decree are all exogenous to the civilization they serve;
this is not. It requires no physics claim to state.

*The open edge here:* as measured in §4 this is a **labour** response — capital
and ecological condition move minting not at all. "Capacity" in the strong sense
is not what the base tracks today, and closing that distance is live work rather
than a settled position. The obligation side does respond to capital, by a few
percent; what does not yet follow it through is the mint.

**And that capital response roughly halved on 2026-09-09**, when the capital path
was settled: the entry point had been scaling a supplied stock by (1 + 2ε) on top
of itself, so the infrastructure share of the obligation — and with it the
capital response — was overstated. **The correction runs against this
framework**, weakening the endogenous-supply claim on the axis §4 calls the
sharper of the two, and it is recorded here rather than left for a reader to
recompute.

*Checked against a real economy:* run over the BEA Fixed Assets inventory, the US
reads a **band across the middle of the arc** over the declared grid, with **none
of the cells saturating**. An earlier run had produced a saturated reading and
this page reported the property as unable to read the world; that reading took
the widest scope, the lowest conversion rate, consumer durables and defence
spending all at once, and it sits outside the grid entirely.

**It is corroborated, adjacently, by an instrument that shares none of its
data.** Read off ATUS time diaries — human hours against the obligation they
discharge, with no currency anywhere in the chain — the labour route lands
**below** the capital route and the two bands do **not** overlap, separated by a
gap small against either band's own width. The verdict is **ADJACENT**, which
is a weaker and truer word than agreeing; `instrument_comparison()` returns it
with the live bands. **The cross-check has a hole worth naming: both routes
divide by the same obligation**, so an error in what is owed would pass both.
What is checked is the machine/human split.

**What the retrodiction cannot do is return a single number, and the reason is
this framework's own argument.** Three judgements set the answer — the valuation
doctrine, the currency-per-hour conversion, and what counts as capital at all —
and converting a currency-denominated stock into hours IS a valuation. The
value-anchor argument is that a valuation transmits doctrine undamped while a
census cannot move at all, so the spread is the prediction, not noise. The other
figures on this page are computed on the canonical arc, which is a reference
frame rather than a measurement of anywhere. See §7.

*Open:* on the canonical arc personal EOH is **almost all** of the obligation at
ε = 0 and still **the largest domain** at ε = 0.99. So the property is very
largely a statement about one domain — the domain whose component shares are, by
the provenance table's own reckoning, among the least settled in the model.

### 5.3 ε is the share of obligation still dependent on human agency

Not an automation statistic. This is what lets the anchor survive its own
success: at high automation the obligation is still real and still measured, even
though little of it is human-fulfilled.

Two quantities carry this, and they are not the same:

- **Capability** — what machines are able to take. An input.
- **Observable ε** — `machine_eoh / total_eoh`. What the ledger records.

They diverge because some obligations keep a human share whatever machines can
do. At capability 0.99 the observable share stays **well short of 1**, and the
human share of the obligation is **many times the 1%** the parameter implies.

The consequence is that **the arc has a derived endpoint rather than a
conventional one**. The ceiling is

    1 − personal_share · Σ share_c · floor_c

**It is a function of the obligation MIX as well as of the floors, so it has to
be quoted with the state it was computed on.** On the subsistence mix, where
personal obligation is nearly everything, the shipped floors give the **lower**
ceiling; on the ε = 0.99 mix, where personal is a smaller share, the same floors
give a **higher** ceiling and therefore a smaller human residual.
`observable_epsilon_ceiling()` returns either.

**Quoting the low mix is the choice that flatters this argument**, and it should
be made deliberately or not at all. The ceiling a near-fully-automated society
actually faces is the one computed on ITS mix, which is the less favourable of
the two.

ε does not reach 1, **because care resists automation**.

*Open, and the ceiling errs HIGH:* two of four personal components carry an
automation floor — nutrition, from total human food labour against a measured
unassisted benchmark (an upper bound, since no unassisted frame survives), and
care, set by the ordering bound because the least automatable component cannot
coherently sit below the most. **Shelter and health carry none, which the model
reads as 0.0.** So the ceiling is an upper bound: every floor adopted so far has
lowered it, and every floor added can only lower it further.

---

## 6. The open research front

**This framework is work in progress, and this section is where the work
currently points.** The rows below are the questions that have *not* been
settled, each stated with the instrument that would settle it. They are the
research programme rather than a list of concessions — but naming them as
research is not a claim that this framework will resolve them. §7 says what
would make us abandon each.

| Front | What is established | What is open, and what would settle it |
|---|---|---|
| **Registration capture** | **The aggregate is bounded three ways.** `total_eoh` accepts no registration parameter, so registering cannot CREATE obligation — it relocates it, gated by test. The mint is registered × multiplier and registered ≤ human ≤ gross, so the ceiling is the obligation, which is population-determined. And supplying available labour makes the mint track what was SERVED, with the shortfall booked as deferral. **So capture cannot mint against work nobody does, and the exposure shrinks along the arc** as automation registers the obligation anyway. Registration is unit elastic on issuance and the only lever that moves it. | **What is unbounded is distribution, not volume.** A captured register admits one household's obligation and refuses another's; the aggregate, the obligation and the work are all untouched, and the excluded person is excluded. **Every figure in this framework is a per-capita aggregate, so it has no variable for that.** Settling it needs a distributional layer, which is downstream of exchange work not yet done at scale — parity today has no real-output term and there is no goods layer, so there is nothing yet for a distribution to be over. **A research area, not a measurement.** The contestability work addresses **exit**; this is **voice**. |
| **Measurement debt** | Every constant is tagged and published with its basis. Roughly two in five are placeholder or bounded, and most of those carry no confidence figure. Leverage runs *opposite* to confidence — the constants the results move most with are among the least confident — and that ordering is pinned by a test. | Measurement, constant by constant, ordered by leverage. The debt is disclosed and ratcheted so it cannot quietly grow; whether it can be paid down to where the anchor's claims need it is open. |
| **The personal floor** | Most of the obligation now carries a price from physical quantities — it was under a tenth until care and processing were priced as declared bounds. **Water resolves by declaration**: a village and a city beside one spring walk the same distance, so no survey of one population transfers to another; a collective declares its distance and `water_feasibility()` reports whether it fits and the furthest distance that still does. | **Shelter** is the same kind of unknown — instance data, not a missing survey. **Sanitation** has no named instrument and is the weakest component. **Health** is `below_min_epsilon` — **undefined rather than unmeasured** below the apparatus that delivers it, and the floor says so rather than imputing it. |
| **Automation floors** | Two of four components carry a floor, and both move the ceiling. Neither is a measurement of its own component: nutrition's bounds from **above**, care's from **below**. | Shelter and health are not yet reached, so the ceiling errs high. The instrument is a time-use split of each component into hours whose value depends on a human performing them — and for care specifically a stated-preference survey, which is not in this repo. |
| **Reading ε off a real economy** | Run against the BEA fixed-asset inventory, and §7's retrodiction falsifier is answered: a band across the declared grid, none of it saturating. An earlier saturated reading was three undeclared judgements compounding, not a miscalibrated model. | **A second instrument exists and the two are ADJACENT, not overlapping.** Read off time diaries with no currency in the chain, the labour route lands below the capital route with a gap small against either band's width. What is open is that gap, and that **both routes divide by the same obligation**, so an error in `total_eoh` passes both undetected. A third instrument that does not divide by `total_eoh` would be a genuine check, and there is no candidate. |
| ~~Ecological blindness~~ | **Settled 2026-09-02 (charter).** Supply is blind to ecological condition by design: a responsive base would pay for degradation or defund repair, depending on sign. The obligation is carried by the ground-use fee, where the holder makes the decision. | Closed. Kept visible because the 0.0% response is real and a reader will find it. |
| **Verification cost** | **The apparatus is measured** — the occupations that decide what counts and check it was done, excluding by name those already charged through the ground-use fee — at two scopes, with no weight to tune, peaking at a low single-digit percentage of the obligation. **The framework knows which constraint binds:** not §7's ratio test, which is the loose one over nearly all of the arc, but obligation plus verification against the labour a population can supply. **The registrant side is priced by declaration.** Register cadence is an `instance` defaulting to **episodic**, which errs toward the costlier reading on purpose, and on that default `corridor_is_usable()` returns **`closed_and_usable`**. | A **continuous** register returns **`open_edges`** below the crossover, and `cadence_feasibility()` reports where that crossover sits. What would settle the registrant side outright is a measured multiple for a *fulfilment* register — the Standard Cost Model's time term, hours per record; the two adjacent analogues disagree by two orders of magnitude, which is why the cadence decides rather than either analogue. **`broad` is not an upper bound:** verification as a fraction of many jobs rather than the whole of a few — Wallis and North's in-house cell — is unbuilt. And part of the cost is a **governance choice**: a register re-reviewing annually costs several times one re-reviewing every five years for identical physical obligation. *(An earlier revision transferred the registrant analogue as a ratio to the apparatus and read the audit claim as undetermined; that transfer embedded another institution's staffing, and is superseded by pricing in share of the obligation.)* |

The first row still bites hardest against §3.2, though it bites less than it
did. This framework's criticism of fiat is that issuance rests on discretion the
holder cannot see. Its own issuance rests on a register, and the property that
disqualifies the hole-digger — that only registered obligation mints — is the
same property that concentrates capture risk in whoever maintains the register.
The volume a captured register can mint is now bounded; who it admits is not.
That is a live problem with an unbuilt solution, and it is stated here rather
than left for a reader to find.

---

## 7. What would change our mind

**These are live falsification conditions, not rhetorical ones.** Each is stated
so that it could actually happen, and none of them is one this framework is
confident of surviving.

- If raising personal-floor coverage makes the floor contradict its own base
  constant, the anchor is measuring something other than what it claims.
- ~~If a retrodiction produces an implausible ε, the endogenous-supply property
  is not reading the world it says it reads.~~ **FIRED, THEN ANSWERED
  (2026-09-09).** It really did fire: an early run gave a saturated reading for
  a US where most adults work, and this page listed the condition as untested
  for a month afterwards. Run properly over the BEA Fixed Assets inventory the US
  reads a band across the middle of the arc, with no cell saturating.

  **The saturated reading was three undeclared judgements compounding**, not a
  miscalibrated model: valuation doctrine, currency conversion and scope, any two
  of which together pass a factor of three. Kept rather than deleted, because a
  falsifier that fired and was then answered is worth more than one that never
  ran — and because the answer is a GRID and not a number. **It re-opens the
  moment anyone quotes a single ε for a real economy**, which is why the
  conversion rate is a required input with no default anywhere in the code.

  The remaining honest limit, **narrowed and not closed**: a second instrument
  exists that does not use currency at all, and the two are ADJACENT. What it
  does NOT do is confirm the level: **both routes divide by the same
  `total_eoh`**, so the cross-check covers the machine/human SPLIT and not the
  denominator — and the denominator carries the largest measurement debt on the
  page.
- **If verification cost, once costed, leaves too little of the obligation for
  actual entropy reduction at any point on the arc, the anchor is not cheaper to
  audit than the incumbents.** **RUN, RE-OPENED, AND ANSWERED ON THE SHIPPED
  DEFAULT — NOT STRUCK, because the declaration can re-open it.**

  At apparatus scope it never fired: no crossover under either scaling basis.
  **But that was the answer for the apparatus, not for verification**, and the
  registrant's own documentation hour is nobody's occupation. Priced by the
  register's declared cadence in share of the obligation, the shipped episodic
  register fits with room to spare and `corridor_is_usable()` returns
  `closed_and_usable`; a continuous register returns `open_edges` until
  mid-arc. **So the falsifier's answer depends on a declaration the collective
  makes**, and the framework reports both rather than choosing for it.

  **The threshold was wrong as well as the scope.** A crossover test at ratio
  1.0 fires far too late: what matters is the fraction of the obligation left for
  actual entropy reduction, and it degrades non-linearly. A register consuming a
  fifth of what it verifies has not crossed over and has lost the audit claim
  anyway. `net_fraction_falsifier(floor)` answers at a **caller-declared** bound,
  with no default shipped — a threshold chosen here would be calibrated against
  the configuration it is then checked on. It re-opens if a measured multiple for
  a fulfilment register lands outside the corridor, or if the register's
  throughput basis is adopted and the cost turns out to chase the ledger faster
  than the ledger grows.
- **If a governance model of the register cannot bound WHO it admits below the
  discretion this page criticises in §3.2, the comparison in §4 favours fiat on
  the axis this framework claims as its own.** *(Narrowed 2026-09-12: the
  volume a captured register can mint is structurally bounded — §6 and §8a — so
  what this condition now tests is distribution.)*

---

## 8. What the anchor claims, and at what strength

**Adopted 2026-09-11 (author decision).** *A verdict may not outrank the weakest
input it rests on.* Everything on this page sits in one of three tiers, and the
tier is not a style choice — it is determined by the provenance tag of the
weakest constant feeding the claim, which `data.py` carries for every constant
and `utils/verdict_ladder.py` computes.

| Tier | What it rests on | How this page states it | Example |
|---|---|---|---|
| **Certain** | physics, or arithmetic that closes | Flatly, no hedge | `obligation + delivery + stock == total_eoh` to float equality; registration is unit elastic on the money supply |
| **Instance** | a census or a declaration — **only as good as that census** | As a declared measurement with its frame, checkable for FEASIBILITY within a stable bound, never as a universal | The verification census of US workers; ε read off BEA assets or ATUS diaries; the register's cadence; the distance to water |
| **Possible** | anything downstream of an unmeasured value | **"Possible" — and that is the ceiling** | Everything resting on the personal base, the automation floors, or the ground-use ratios |

**"Possible" is not a hedge; it is the honest maximum.** No economic model
untested in the world has earned more, and every predecessor in *Prior Art*
claimed more before it died. Every headline function in this framework rests on
at least one placeholder, so none of its central results is entitled to more.
What the framework offers instead of a forecast is a **stable corridor**: it does
not tell a collective its population, its land, its capital or its governance
form — each is an instance the collective *declares* — and what it supplies is
the bound, so the collective can check whether its own declaration is feasible
and where it stops being so. **That is a checks-and-balances system, not a
prediction**, and it is the shape the framework already adopted for ε on
2026-08-01: *success is a stable measurable corridor, not ε → 1.*

**This is also why the core is built to be optimised around rather than shipped
as final.** A core that overclaims cannot absorb a measurement that contradicts
it — the overclaim has to be retracted first, publicly, which is what makes
frameworks defend their constants instead of measuring them. A core that says
*possible, within these bounds* absorbs a new measurement as a narrowing. New
data and new exchange mechanisms should be able to enter without the core being
rewritten, and the ladder is what makes that true.

---

## 8a. What HOURS adds that no other anchor on this page has

**Adopted 2026-09-12 (author decision, AWol).** Three properties that follow
from the *structure* rather than from calibration, so they do not drift and none
of the seven rivals in §3 holds them.

- **Issuance cannot be created by the act of registering.** `total_eoh` accepts
  no registration parameter at all: admitting an obligation RELOCATES it from
  off-ledger to on-ledger and never manufactures it. So the ledger cannot mint
  by deciding to, which is a different and stronger property than a base that
  merely *happens* to be fixed.
- **Issuance cannot run ahead of work actually done.** Supply the labour
  available and the mint tracks what was SERVED, booking the shortfall as
  deferral rather than as money. **This is the property that disqualifies the
  hole-digger, applied to the register itself.** Gold and bitcoin cannot
  over-issue either — but because their base is *indifferent* to whether
  anything was done, which buys the same safety by giving up the responsiveness
  §5.2 claims. HOURS is the only anchor here that is both responsive and unable
  to issue against work not performed.
- **The exposure shrinks as the thing it is exposed to arrives.** Capture room
  — how much more of the obligation is admittable — is largest at subsistence
  and smallest at high automation, because automation registers the obligation
  anyway. An anchor whose worst governance case is at the *beginning* of its own
  trajectory is in a better position than one whose worst case is at the end.

**None of this makes capture harmless**, and §6 says exactly which half is
unbounded and why the framework cannot see it. What these three do is convert
"capture is unbounded" — which this page conceded for months — into "the volume
is bounded and the distribution is not", which is narrower, defensible, and
points at different work.

---

## 8b. What the anchor does not claim

Commitments, not open questions. No measurement retires them.

- **Not thermodynamics.** Only a handful of constants are tagged physics.
  "Entropy obligation" is a disciplined organising frame for recurring
  maintenance demand.
- **Not the price.** A floor, with discovery above it.
- **Not the elimination of trust.** Trust relocates — from institutional
  discretion to measurement, registration, verification and governance. That is
  the transparency commitment, stated up front rather than conceded under
  pressure.
- **Not system-wide inflation impossibility.** A within-collective floor
  property, with the ε→1 case as its limit.
- **Not "backed by human labour."** The committed phrasing is *the capacity of
  humans to fulfil registered obligations*.
- **Not unique.** Mutual credit holds the same three properties. The claim is
  about scale, and it is unproven at scale.

---

## 9. Sources

External claims below are cited from secondary reading and are **not yet verified
against the primary sources**; none is quoted, and no figure on this page depends
on one.

- Coase (1937) — the collective boundary.
- Baumol, Panzar and Willig (1982) — contestability.
- Wallis and North (1988) — transaction costs as intermediate, and the in-house
  measurement cell §6 names as unbuilt.
- WIR Bank, Switzerland, 1934– — the mutual-credit precedent in §3.7.
- Sinsky et al. (2016) — clinical documentation time, the structural analogue for
  a register that records continuously.
- Central-bank literature on money as a social convention, for §3.2. A specific
  citation is needed before that sentence is published in a stronger form.
- ILO measurement work on unpaid domestic labour, for the point that a monetary
  system decides which activity becomes legible rather than creating its value.

Every internal figure is computed from the repository and is reproducible:
`research/anchor_determinacy.py` for §§3–4, `scenarios/verification_cost.py` for
the verification rows, `scenarios/labour_epsilon.py` and
`scenarios/capital_retrodiction.py` for §5.2, `core/eoh_fulfillment.py` for
§5.3, `scenarios/personal_floor.py` for coverage, and
`python3 utils/eoh_cli.py provenance check` for the constant counts.
`python3 utils/anchor_page_figures.py` prints them all in one place.
