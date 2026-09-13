# What Anchors a Unit of Account

Every currency rests on something that limits how much of it can exist. For gold
it is geology; for a fixed-supply protocol, code; for fiat, the discretion of an
institution. This page asks what HOURS rests on, how that compares with the
anchors in use today, what HOURS has that they do not — and where it is weaker.

Its companion, [Prior Art](prior_art.md), audits the labour-currency schemes that
came before and asks *why this won't die the way Owen's exchange did.* This page
audits the contemporaries and asks *why this unit of account rather than a
dollar, an ounce, or a satoshi.* It is work in progress: the open questions are
set out near the end, each with what would settle it.

A figure on this page is given as a value only where it is structural — a
designed zero, an exact elasticity, a verdict. Where a figure depends on
calibration, the page describes its shape, and the current value is computed by
the code (see [Reproducing the figures](#reproducing-the-figures)).

---

## The question

The tempting question is *why does entropy deserve monetary value?* It is the
wrong one. It invites a metaphysical argument this framework cannot win and does
not need, and no incumbent anchor could win it either.

The answerable question is narrower: **what constrains issuance, and can an
outsider inspect the constraint?** Every anchor has a real answer, and the
answers differ in ways that can be written down.

That shifts the burden usefully. HOURS does not have to show that an hour has
intrinsic value. It has to show that a floor derived from registered obligation
is more inspectable than one derived from geology, decree, protocol or credit —
and to say plainly where it is not.

This page is not an argument that HOURS is more valuable than the alternatives,
an argument about the worth of human life, or a prediction of adoption.

---

## What an anchor is

An **anchor** is what constrains issuance and supplies a reference frame. It is
not backing, not value, and not price.

**HOURS anchors the floor, not the price.** The number it computes is the level
below which the collective guarantees that work is available and paid. Exchange
discovers everything above it; the floor-price calculation carries a market
premium, zero by default, and that is where a discovered price lives. **Every
comparison on this page is between floors and issuance constraints, not between
values.**

---

## The candidates

Eight anchors are compared. Each is classified from its *own* definition, at its
advocates' strongest reading, and no rival is simulated — a comparison whose
rivals you model yourself is the easiest thing in the world to rig.

Three properties are asked of each:

- **Determinate** — does the issuance rule follow from what the anchor *is*?
- **Responsive** — does the monetary base move with the physical capacity of the
  people using it?
- **Registers obligation** — must an activity have fulfilled a recognised
  obligation before it can mint?

### Gold

Scarce, durable, divisible, hard to counterfeit, legible for millennia. Issuance
is governed by geology, and geology is indifferent to the population using it: a
new deposit feeds no one, and a depleted seam does not make a civilization less
able to feed itself.

*What it does better:* its audit is a scale. You can weigh an ounce; nobody has
to agree about what it fulfilled. HOURS does not have that.

Gold's verification cost is lower, though, not zero. Assay, refining
accreditation, vaulting and chain of custody are paid at every transfer — a
claim on gold that has never been assayed is a claim on a belief about gold. The
difference is **where the cost sits and whether it can be seen**: gold's is paid
privately, per transfer; HOURS' is continuous, public and partly measured. Gold's
cost is not measured here, and is not claimed to be larger or smaller.

### Fiat

Not "unbacked" — that is the weak criticism, and this page declines it. Fiat is
supported by taxation, legal tender, central banking, payment infrastructure,
courts and network effects, and its own literature defends it as a social
convention sustained by institutions rather than a natural fact.

The precise criticism is narrower: the ultimate constraint is institutional
discretion rather than a measurable quantity, exercised on a schedule the holder
does not see. Fiat is therefore classified as **indeterminate** rather than
unresponsive — recording it as unresponsive would be a claim about monetary
policy this framework is not entitled to make.

*What it does better:* proven at civilizational scale for a century, with an
elastic crisis response that a floor-anchored system deliberately gives up.

### Bitcoin and fixed-supply protocols

Scarcity from protocol consensus. If a civilization doubled its capacity to meet
its obligations the base would not move, and if it halved, likewise. Supply is
indifferent to the thing money is a claim on — which is the property its holders
are buying.

*What it does better:* the issuance rule is fully specified and needs **no
measurement of the world at all**. Anyone with a node can audit it, where HOURS
needs a register somebody has to run. That measurement burden is a real
concession.

A proof-of-work anchor's verification cost is not zero either: it is the security
budget, published continuously and paid by construction — the same criterion of
visibility HOURS claims for itself. It is not measured here and is not claimed to
be smaller or larger than HOURS'.

### Debt and credit money

Credit money anchors to *promised future* production; HOURS anchors to *past
fulfilment*. The difference has a cost: things must be built before the labour
that pays for them occurs, so HOURS still needs credit, which its
capital-formation mechanics carry.

*What it does better:* it finances the future, which a fulfilment-anchored unit
does not do natively. That is a gap, not a concession.

### Labour vouchers

Covered on the [Prior Art](prior_art.md) page — Warren, Owen's exchange, Ithaca,
time banking, the *trudoden*. One point belongs here: a labour voucher mints for
hours worked, so a hole dug and refilled mints as readily as a bridge repaired.
HOURS registers the obligation *before* the labour, so effort against no
registered obligation mints nothing.

### Energy certificates

Covered under Technocracy on the Prior Art page. Its lesson applies to this page
too: a measurable anchor confers measurability on the anchor, not on the human
valuations the unit must carry.

### Mutual credit

**The closest living relative, and the reason the claim for HOURS is narrower
than it first appears.** Mutual credit issues when a bilateral obligation is
incurred and extinguishes when it is settled. Its base moves with activity, it
registers obligation, and its rule follows from what it is. WIR Bank has run on
this basis in Switzerland since 1934.

On all three properties, **mutual credit and HOURS are the same.** The difference
is scale: a bilateral obligation is legible to the two parties, and does not
obviously extend to a population whose members do not know each other. HOURS
proposes a registration apparatus that makes obligation legible at population
scale — and that apparatus is exactly what it must justify, since it is also its
largest governance risk.

---

## How they compare

| Anchor | Issuance constrained by | Moves with capacity? | Registers obligation? | Principal vulnerability |
|---|---|---|---|---|
| Gold | Geology | No — indifferent by design | No | No relation to the population using it |
| Bitcoin | Protocol consensus | No — indifferent by design | No | Same, by construction rather than by nature |
| Fiat | Institutional discretion | Indeterminate | No | The constraint is a decision, on an unseen schedule |
| Debt money | Credit creation against promised output | Indeterminate | No | Anchored to promises, not to fulfilment |
| Labour voucher | Hours worked | Yes | **No** | Mints for effort whether or not anything was owed |
| Energy certificate | Energy throughput | Yes | **No** | Same as the voucher, with a physical unit |
| **Mutual credit** | Bilateral obligation incurred | **Yes** | **Yes** | Does not evidently scale beyond mutual acquaintance |
| **HOURS** | Registered obligation fulfilled | **Yes — see below** | **Yes** | Registration is the only lever on issuance |

**HOURS does not win this table.** Two anchors hold all three properties, and the
other has ninety years of operating history that HOURS does not.

"Moves with capacity" is also narrower than it reads. On a million-person frame
at capability 0.40, halving each input moves minting and obligation by:

| Shock | Minting | Obligation |
|---|---|---|
| Labour halves | **−50%** | **0.0%** |
| Capital halves | **0.0%** | a few percent |
| Ecosystem health halves | **0.0%** | **0.0%** |

The zeros are designed and do not drift. Halving labour halves minting exactly,
because registration is unit elastic (**1.000**). The capital figure on the
obligation side is a calibrated magnitude and is described rather than quoted.

So the base responds to **labour alone** — not to capital, and not to ecological
condition. The first of those is a limit of the model; the second is deliberate.

**Why supply must not respond to ecological condition.** If issuance rose as
ecosystems degraded, degradation would expand the money supply and the system
would pay itself for damage. If issuance fell, a damaged collective would lose
the means to fund its own repair exactly when it needed them. Neither sign is
acceptable, so the base is held blind on purpose.

The obligation does not vanish; it is **assigned elsewhere**. The recurring
ecological cost sits in the Ground Use Fee, where halving ecosystem health roughly
doubles the charge — borne by the holder of the land, at the point where the
decision to degrade is made, and without touching what the currency is worth.

---

## What HOURS adds

Three properties follow from the *structure* of HOURS rather than from its
calibration, so they do not drift — and none of the other seven anchors holds
them.

- **Issuance cannot be created by the act of registering.** The obligation is
  computed without any reference to registration: admitting an obligation moves
  it from off-ledger to on-ledger and never manufactures it. The ledger cannot
  mint by deciding to, which is a stronger property than a base that merely
  happens to be fixed.
- **Issuance cannot run ahead of work actually done.** Given the labour
  available, the mint tracks what was served and books any shortfall as
  deferred obligation rather than as money. This is the property that
  disqualifies the hole-digger, applied to the register itself. Gold and bitcoin
  cannot over-issue either, but only because their base is indifferent to
  whether anything was done — they buy that safety by giving up responsiveness.
  HOURS is the only anchor here that is both responsive and unable to issue
  against work not performed.
- **The exposure shrinks as automation arrives.** How much more of the obligation
  a captured register could admit is largest at subsistence and smallest at high
  automation, because automation registers the obligation anyway. An anchor whose
  worst governance case comes at the *start* of its trajectory is better placed
  than one whose worst case comes at the end.

**None of this makes capture harmless.** It turns "capture is unbounded" into "the
volume is bounded and the distribution is not" — narrower, defensible, and
pointing at different work (see [Where the work points](#where-the-work-points)).

---

## What HOURS claims

Three claims, each stated only as far as it has been checked, with the open edge
that bounds it.

### Obligation precedes issuance

No unit exists without a labour record against a registered obligation. There is
exactly one place in the code where currency is minted, enforced by a test that
reads the code's structure rather than searching its text. Labour against no
obligation mints nothing at any scale tried; zero registration mints exactly
zero while the obligation still stands. Registration binds hard: at ε = 0.40
**most of human EOH mints nothing.**

*The open edge:* if an institution does not supply its available labour, the
model mints from obligation **demanded** rather than obligation **served**,
assuming the middle link of the chain. Supplied, a labour shortfall is deferred
rather than minted, and the institutional snapshot says which of the two it
computed. **An institution that does not supply its labour data is measuring
demand.**

Verification is itself work, and it is costed on both sides. The people whose job
is verifying — the apparatus — are counted from occupational headcounts and peak
at **a low single-digit percentage of the obligation**, never crossing it on the
arc. The hours a registrant spends documenting their own fulfilment belong to no
occupation; they are priced by how often the register records, as a share of the
obligation. On the default, episodic register every regime fits inside the labour
a population has left over, with **an order of magnitude to spare**. A register
that records *continuously* does not fit until mid-arc. Whether that documentation
hour should be added to the obligation itself is not yet decided.

### Supply is endogenous to the population

The monetary base is constrained by the capacity of the people using it.
Geology, protocol and decree are all external to the civilization they serve;
this is not. Stating it needs no physics claim.

*The open edge:* as the shock table shows, this is a **labour** response.
Capital and ecological condition do not move minting. The obligation responds to
capital by a few percent, but the mint does not yet follow it — so "capacity" in
the strong sense is not what the base tracks today.

**Read against a real economy**, the US capital stock (BEA Fixed Assets) places
the US in a **band across the middle of the arc**, with none of the declared grid
saturating. A second instrument that shares none of that data — time diaries,
with no currency anywhere in the chain — lands **below** the capital reading, and
the two bands do not overlap, separated by a gap small against either band's
width. The verdict is **ADJACENT**: weaker than agreement, and the accurate word.
Both routes divide by the same obligation, though, so an error in what is owed
would pass both; what the cross-check confirms is the machine/human split.

The reading is a band and not a number because three judgements set it — the
valuation doctrine, the currency-per-hour conversion, and what counts as capital
— and converting a currency-denominated stock into hours *is* a valuation. The
spread is the prediction, not noise, which is why the conversion rate is a
required input with no default anywhere in the code. Everything else on this page
is computed on the canonical arc, a reference frame rather than a measurement of
anywhere.

*A further limit:* on the canonical arc, personal EOH is almost all of the
obligation at ε = 0 and still the largest domain at ε = 0.99. The property is
therefore very largely a statement about one domain — the domain whose component
shares are among the least settled in the model.

### ε is the share of obligation still dependent on human agency

Not an automation statistic. This is what lets the anchor survive its own
success: at high automation the obligation is still real and still measured, even
though little of it is fulfilled by people.

Two quantities carry this, and they differ:

- **Capability** — what machines are able to take. An input.
- **Observable ε** — the machine share of the obligation the ledger records.

They diverge because some obligations keep a human share whatever machines can
do. At capability 0.99 the observable share stays **well short of 1**, and the
human share is **many times the 1%** the parameter implies. ε does not reach 1,
**because care resists automation.**

So the arc has a derived endpoint rather than a conventional one:

    1 − personal_share · Σ share_c · floor_c

The ceiling depends on the **mix** of obligations as well as the floors, so it has
to be quoted with the state it was computed on. On the subsistence mix, where
personal obligation is nearly everything, the shipped floors give the **lower**
ceiling; on the ε = 0.99 mix they give a **higher** one, and so a smaller human
residual. Quoting the subsistence mix flatters the argument. The ceiling a
near-fully-automated society actually faces is the one computed on its own mix,
which is the less favourable of the two.

*The open edge — the ceiling errs high:* two of the four personal components
carry an automation floor. Nutrition's is an upper bound, taken from human food
labour against an unassisted benchmark; care's is set by ordering, since the
least automatable component cannot sit below the most. **Shelter and health carry
none, and the model reads them as 0.0.** Every floor adopted so far has lowered
the ceiling, and every floor added can only lower it further.

---

## How strongly HOURS claims it

*A verdict may not outrank the weakest input it rests on.* Every claim here sits in
one of three tiers, set by the provenance of the weakest constant feeding it —
which the framework records for every constant and computes for every function.

| Tier | What it rests on | How it is stated | Example |
|---|---|---|---|
| **Certain** | Physics, or arithmetic that closes | Flatly | The obligation, delivery and stock accounts sum exactly to the total; registration is unit elastic on the money supply |
| **Instance** | A census or a declaration — only as good as that census | As a declared measurement with its frame, checkable for feasibility within a bound, never as a universal | The count of US verification workers; ε read off capital or time use; the register's cadence; the distance to water |
| **Possible** | Anything downstream of an unmeasured value | **"Possible" — and that is the ceiling** | Everything resting on the personal base, the automation floors, or the Ground Use Fee ratios |

**"Possible" is not a hedge; it is the honest maximum.** No economic model untested
in the world has earned more, and every predecessor in Prior Art claimed more
before it died. Every headline result in HOURS rests on at least one placeholder,
so none is entitled to more.

What HOURS offers instead of a forecast is a **stable corridor**. It does not tell
a collective its population, its land, its capital or its form of governance —
each is something the collective declares. It supplies the bounds, so a
collective can check whether its own declaration is feasible and where it stops
being so. That is a system of checks, not a prediction.

It is also why the core is built to be improved rather than finished. A core that
overclaims cannot absorb a measurement that contradicts it; the overclaim has to
be retracted first, which is what drives frameworks to defend their constants
instead of measuring them. A core that says *possible, within these bounds*
absorbs a new measurement as a narrowing.

### What HOURS does not claim

- **Not thermodynamics.** Only a handful of constants rest on physics. "Entropy
  obligation" is a disciplined organising frame for recurring maintenance demand.
- **Not the price.** A floor, with discovery above it.
- **Not the elimination of trust.** Trust relocates — from institutional
  discretion to measurement, registration, verification and governance. That is
  the transparency commitment.
- **Not system-wide inflation impossibility.** A within-collective floor
  property, with the ε→1 case as its limit.
- **Not "backed by human labour."** The phrasing is *the capacity of humans to
  fulfil registered obligations*.
- **Not unique.** Mutual credit holds the same three properties. The claim is
  about scale, and it is unproven at scale.

---

## Where the work points

HOURS is heading toward a corridor a collective can check its own declarations
against, not a forecast. The questions below are what stands between here and
there. They are a research programme rather than a list of concessions — and
naming them as research is not a promise that they will be resolved.

| Question | Where it stands | What would settle it |
|---|---|---|
| **Capture of the register** | The volume is bounded: registering cannot create obligation, the mint cannot exceed the obligation, and with labour supplied it cannot exceed what was served. The exposure shrinks along the arc. | **Who** a captured register admits is not bounded. Every figure in the model is a per-capita aggregate, so it has no variable for one household admitted and another refused. It needs a distributional layer, which in turn needs exchange with a real-output term and a goods layer — neither exists yet. The contestability work addresses **exit**; this is **voice**. |
| **Measurement debt** | Every constant is tagged and published with its basis. Roughly two in five are placeholder or bounded, most without a confidence figure, and the constants the results move most with are among the least confident. | Measurement, constant by constant, in order of leverage. The debt is ratcheted so it cannot quietly grow; whether it can be paid down far enough is open. |
| **The personal floor** | Most of the obligation carries a price from physical quantities. Water resolves by declaration: a collective states its distance to water and the floor reports whether it fits. | Shelter is instance data of the same kind. Sanitation has no named instrument and is the weakest component. Health is undefined — not unmeasured — below the apparatus that delivers it, and is reported that way rather than imputed. |
| **Automation floors** | Two of four components carry one: nutrition bounded from above, care from below. | Shelter and health, so the ceiling errs high. The instrument is a time-use split of each component into hours whose value depends on a person doing them — and for care, a stated-preference survey. |
| **Reading ε off a real economy** | Two independent instruments, capital and time use, give **ADJACENT** bands. | Both divide by the same obligation, so an error there passes both. A third instrument that does not would be a genuine check; there is no candidate. |
| **Verification cost** | The apparatus is measured at two scopes and peaks at a low single-digit percentage of the obligation. The registrant side is priced by the register's declared cadence, defaulting to episodic, and on that default the corridor closes (`closed_and_usable`). | A continuous register leaves the corridor with `open_edges` until mid-arc. A measured hours-per-record figure for a *fulfilment* register would settle the registrant side outright; the two nearest analogues disagree by two orders of magnitude. Verification spread thinly across many jobs is not yet counted, so the broad scope is not an upper bound. And part of the cost is a governance choice: re-reviewing annually costs several times re-reviewing every five years for the same obligation. |

Capture bites hardest against the criticism this page makes of fiat. Fiat's
issuance rests on discretion the holder cannot see; HOURS' rests on a register,
and the property that disqualifies the hole-digger — only registered obligation
mints — is the same property that concentrates capture risk in whoever maintains
the register. The volume a captured register can mint is bounded; who it admits
is not. That is a live problem with an unbuilt solution.

---

## What would change our mind

These are live conditions, each stated so it could actually happen.

- **If raising personal-floor coverage makes the floor contradict its own base
  constant**, the anchor is measuring something other than what it claims. With
  most of the floor now priced, this can happen.
- **If a real economy reads an implausible ε**, the endogenous-supply property is
  not reading the world it claims to. Against the US capital stock it reads a band
  across the middle of the arc. The condition returns the moment anyone quotes a
  single ε for a real economy: the three judgements behind the band compound, and
  any two together pass a factor of three.
- **If verification leaves too little of the obligation for actual entropy
  reduction anywhere on the arc**, HOURS is not cheaper to audit than the
  incumbents. The test is the fraction left over, not whether verification
  exceeds what it verifies — a register consuming a fifth of the obligation has
  lost the audit claim without crossing over. The bound is declared by whoever
  applies the test, not shipped. On the default, episodic register the condition
  is met with room to spare; on a continuous register it is not met until
  mid-arc; and it returns if a measured figure for a fulfilment register lands
  outside that range, or if verification is found to scale with the register's
  throughput and grows faster than the ledger does.
- **If no governance model of the register can bound *who* it admits below the
  discretion criticised in fiat**, the comparison favours fiat on the axis HOURS
  claims as its own.

---

## Sources

External claims are cited from secondary reading and have not yet been checked
against the primary sources; none is quoted, and no figure on this page depends
on one.

- Coase (1937) — the collective boundary.
- Baumol, Panzar and Willig (1982) — contestability.
- Wallis and North (1988) — transaction costs, and the in-house measurement of
  verification spread across many jobs.
- WIR Bank, Switzerland, 1934– — the mutual-credit precedent.
- Sinsky et al. (2016) — clinical documentation time, the analogue for a register
  that records continuously.
- Central-bank literature on money as a social convention, for the account of
  fiat. A specific citation is needed before that account is stated more strongly.
- ILO measurement work on unpaid domestic labour, for the point that a monetary
  system decides which activity becomes legible rather than creating its value.

### Reproducing the figures

Every internal figure is computed from the repository.
`python3 utils/anchor_page_figures.py` prints the current value behind each shape
on this page, and `tests/test_anchor_page_figures.py` checks this page's
structural statements against it. The underlying calculations are in
`research/anchor_determinacy.py` (the candidates and the shock table),
`scenarios/verification_cost.py` (verification), `scenarios/capital_retrodiction.py`
and `scenarios/labour_epsilon.py` (reading ε off a real economy),
`core/eoh_fulfillment.py` (observable ε and its ceiling) and
`scenarios/personal_floor.py` (the personal floor).
