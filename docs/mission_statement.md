# HOURS

## The North Star

Build a mathematical framework for a currency system that remains coherent and equitable across the full transition from subsistence to post-scarcity — and that makes that transition legible, continuous, and just.

A single parameter, ε (epsilon), tracks where a civilization sits between two physical attractors:

- **ε = 0 — Subsistence.** All entropy resistance is human labor. No surplus. Personal EOH is entirely private. The collective ledger sees almost nothing. TEH barely circulates. Prices reflect the full weight of human toil.
- **ε = 1 — Post-scarcity.** All entropy resistance is automated. Human labor is optional. Personal EOH is entirely collective. Prices approach zero. TEH destruction approaches zero despite full consumption. The currency measures judgment, care, and the maintenance of the systems that sustain abundance.

ε is not a policy lever. It is an observed state of the world — the measured degree to which physical entropy obligations are fulfilled by machines rather than human bodies. Every mechanism in this framework is answerable to a single question: *how does this behave across the full arc from ε = 0 to ε = 1?*

**ε is derived, not input.** The physical state of a civilization — its capital stock, ecosystem health, population structure, and knowledge base — determines what EOH demands exist. ε is derived by comparing actual machine fulfillment to that physical demand. This distinction matters for how functions are structured: EOH generation functions take the physical state of the world as input and return entropy obligations as output. ε belongs in the fulfillment layer — where it correctly captures the machine/human split — and in registration and fiscal mechanisms that adapt to how automated the civilization has become. Using ε as a proxy for unspecified physical state inside EOH generation functions conflates measurement with mechanism and prevents modeling civilizations that deviate from the ideal arc.

If a function cannot answer that question — if it produces discontinuities, undefined behavior, or physically impossible results at the extremes — it is incomplete.

---

## Theoretical Foundation

### What an economy is

An economy is the organized effort of a civilization to resist entropy — in its people, in its infrastructure, in its ecosystems, and in its knowledge. Every person needs food, shelter, and care. Every building decays. Every ecosystem drifts toward depletion without stewardship. Every skill atrophies, every institution forgets, every standard drifts. The work of civilization is holding all of this together against the constant pull of disorder.

Labor is not the point of the economy. Labor is what entropy demands. The point is survival, maintenance, and eventually flourishing. Currency, in this framework, measures one thing: how much entropy-resistance a person has contributed.

### The transition curve

The framework's primary object is the transition itself — not any particular point on it, but the continuous arc from ε = 0 to ε = 1. This transition is not a policy choice, a historical stage, or a development theory. It is a physical consequence of how entropy obligations get fulfilled. As machines take over more of the work that entropy demands, human labor is progressively liberated. The transition describes that liberation quantitatively.

**What changes with ε:**

| Quantity | ε = 0 | ε = 0.40 | ε = 0.99 |
|----------|-------|----------|----------|
| Human share of EOH fulfillment | 100% | 60% | 1% |
| Personal EOH on collective ledger | ~0% | ~14% | ~87% |
| TEH prices (relative to ε=0) | 1.0× | ~0.72× | ~0.11× |
| Care registration share | ~5% | rising | ~95% |
| Source of TEH destruction | income-driven | mixed | biology-anchored |

These are illustrative numbers not hard limits.

**What does not change with ε:** The physical reality of entropy. Personal bodies still need food, water, shelter, and care regardless of how automated the production systems are. Infrastructure still degrades. Ecological systems still require stewardship. Knowledge still atrophies. The four entropy domains are invariant. What changes is who — or what — fulfills the obligations they generate.

**What ε does not determine:** The physical state of the capital stock, ecosystem, and population. A civilization could reach high automation with an aging, neglected capital base — or low automation with rich ecological infrastructure. ε measures the fulfillment split, not the quality or quantity of the physical assets. The ideal arc (the canonical trajectory) describes expected physical state at each ε for a civilization that invests optimally, but real civilizations diverge. EOH functions measure the physical state they are given; ε tells them how much of the resulting obligation falls on humans versus machines.

**The arc must be coherent at both extremes.** The ledger at ε = 0 sees almost no registered activity — most personal EOH is private, most production is household-scale, and TEH barely circulates. The framework must remain well-defined in this regime, not merely degrade gracefully to it. At ε = 0.99, prices have collapsed, human labor is near-zero, and TEH destruction approaches zero despite full real consumption. The ledger must remain solvent, the floor must still rise, and the account identity must still hold. Any mechanism that only works at ε = 0.40 (the current calibration reference) is calibrated for a moment, not for the arc.

**D3's shape is the signature of the transition.** Terminal TEH destruction rises as ε grows — more personal EOH moves onto the collective ledger, more goods are priced and consumed within the system. Then it falls as basket prices collapse faster than registration grows. That rise-then-fall arc across the ε range is what a mechanism that correctly expresses the transition looks like. D2 was income-driven and calibrated to the middle of the arc — it could not produce this shape. Every mechanism should be interrogated for whether it expresses the transition's arc or merely approximates one point on it.

### Why the hour is the right unit

Entropy is measured in time. Systems degrade over time. Biological needs recur on time cycles. Maintenance is scheduled in time. The hour is not an arbitrary social convention — it is the natural unit of the phenomenon the economy exists to manage. One TEH represents one hour of verified human contribution to the collective resistance of entropy.

### Humans as capital stock

Every person is an entropy-generating system. A living human requires food, water, shelter, temperature regulation, sanitation, and healthcare simply to continue existing. These needs constitute personal Entropy Obligation Hours (EOH) — the labor the physical world demands to keep one person alive and functional.

At ε = 0, nearly all human labor goes toward fulfilling personal EOH. This is subsistence economics described honestly: humanity laboring to resist its own entropy. As automation rises, the human labor required to meet personal EOH declines. At near-full automation, personal EOH approaches zero in human-labor terms — not because biology changed, but because machines handle the work.

This means the entire arc of economic development is humanity's progressive liberation from its own entropy. The HOURS framework measures that liberation honestly and ensures its benefits reach everyone.

### The four entropy domains

All entropy obligations fall into four categories:

**Personal EOH** — the entropy of human bodies. Biological needs: food, water, shelter, warmth, healthcare, sanitation. This is the base layer. Every person generates personal EOH simply by being alive. A newborn generates maximum personal EOH relative to their capacity to fulfill any. At ε = 0, this domain consumes nearly all labor; nearly all of it is private and off-ledger. At ε = 1, personal EOH is fully on the collective ledger and entirely fulfilled by automated systems.

**Infrastructure EOH** — the entropy of built systems. Buildings, roads, bridges, power grids, water systems, communication networks. Infrastructure exists to reduce personal EOH collectively — piped water eliminates per-person water-fetching labor. Each piece of infrastructure trades its own EOH (maintenance burden) for a larger reduction in aggregate personal EOH. The economic logic of infrastructure investment: build what generates less EOH than it eliminates.

**Ecological EOH** — the entropy of natural systems civilization depends on. Soil fertility, water cycles, pollination, climate stability, fisheries, forests. These have historically been treated as free — no EOH accounting at all — which is precisely why they are collapsing. Ecological EOH makes the obligation visible: nature generates entropy that someone must address, and ignoring it does not eliminate the obligation but defers it with compounding consequences.

**Knowledge EOH** — the entropy of information systems. Skills atrophy. Institutional memory fades. Training becomes outdated. Software rots. Standards drift. At high automation, almost all remaining human contribution is knowledge maintenance, transmission, and judgment. This domain is the least obvious but becomes dominant as the other three are increasingly handled by machines. It is also the hardest to verify — unlike a repaired bridge or enriched soil, knowledge maintenance lacks straightforward physical indicators. Admitting knowledge EOH to the collective ledger will require careful consideration in implementation to ensure that verification standards are rigorous without being so burdensome that they discourage the labor the system most needs at high automation.

---

## The Three Economies

The HOURS framework spans three economic zones on the transition curve. These are always present simultaneously in a real economy — care and production and stewardship all happen at any ε — but each zone defines which mechanisms are load-bearing, which fiscal flows are primary, and which behaviors the ledger must handle correctly. As ε rises, the center of gravity moves along this progression, and the framework must carry all three zones coherently at every point.

### The care economy — foundation

The care economy is the system's capital formation layer, present at every level of automation. Humans are the system's primary capital stock. Producing and maintaining that capital — raising children, educating, training, healing, mentoring, governing, sustaining each other — is the economy's deepest and most permanent function.

A newborn is the highest-EOH-density event in the system: maximum personal entropy obligation, zero entropy-reduction capacity, requiring years of intensive labor investment before contributing to the collective effort. The return on that investment is not monetary — it is the eventual entropy-reduction capacity of a trained, capable adult who will spend decades fulfilling EOH across all four domains. This makes care labor not a late-stage luxury but the system's primary capital investment.

Aging is gradual capital depreciation. Personal EOH increases (more healthcare, more assistance) while entropy-reduction capacity decreases (less output, slower adaptation). The system accounts for this without treating people as disposable when their net entropy position turns negative. Every person retains dignity and sufficiency regardless of their EOH balance. This is the ethical commitment that separates the framework from pure efficiency logic.

At low automation, care labor is embedded in subsistence — parents raise children while farming, and most of this labor remains internal to the household, unregistered by the collective ledger. As automation rises, the collective's dependence on human capital quality drives progressive registration of care labor along a sigmoid curve — slow at first, accelerating through the mid-automation range as systemic complexity demands it, and reaching full registration well before post-scarcity. The currency measures relational labor. The floor becomes a platform. The conditional tier evolves to recognize contribution broadly defined.

### The production economy — middle zone

The production economy uses human capital (built by care) to create goods, infrastructure, and systems that reduce aggregate EOH. Production labor is the most legible form of entropy resistance — goods made, structures built, systems constructed — and is therefore the first layer most collectives admit to the ledger. The currency measures that labor honestly. Prices tell you how much human life went into making something. The multiplier rewards investment in capability. The floor guarantees that no one is disposable.

The production economy's defining logic is EOH reduction through capital creation. A factory is valuable not because it generates profit but because it reduces the total human labor required to meet personal entropy obligations. If a factory's infrastructure EOH (maintenance burden) exceeds the personal EOH it eliminates (labor savings it provides), it is a net loss and should be written down.

This zone shrinks as automation expands — not because it becomes less important, but because machines increasingly handle production under human direction. The focal priority at this stage is building infrastructure that maximizes EOH reduction per unit of maintenance obligation, creating the capital base that the stewardship economy will maintain.

### The stewardship economy — upper zone

The stewardship economy is where automation takes civilization. Machines produce goods. Humans maintain the machines, the infrastructure, the ecological systems, and the knowledge base that make abundance possible. The currency measures that maintenance labor. Prices tell you how much human judgment and care sustains the systems everyone depends on.

The stewardship economy's defining logic is EOH fulfillment rather than EOH reduction. The capital stock exists; entropy acts on it; humans ensure it continues functioning. The Trust and the Stewardship Allocation — the mechanism that directs labor toward fulfilling entropy obligations generated by the capital stock — become the economy's fiscal center of gravity.

This zone grows as the capital stock grows under automation, peaks in the mid-to-high automation range, and stabilizes as automated systems increasingly handle their own maintenance under human oversight. The focal priority at this stage is efficient EOH fulfillment and the development of monitoring, judgment, and intervention skills — ensuring that the systems sustaining abundance remain trustworthy.

### The ε arc

At ε = 0 (subsistence): Nearly all labor is personal EOH fulfillment, most of it internal to the household and unregistered by the collective ledger. The formal monetary economy is small. Personal EOH on-ledger is near-zero. The ledger operates in a minimal-registration regime and must be defined here, not merely degrade gracefully to it. Focus: building infrastructure that begins reducing personal EOH burden and expanding the scope of collectively registered labor.

At ε = 0.40 (current equilibrium): Production has substantially reduced personal EOH. A growing capital stock generates increasing infrastructure and ecological EOH. Production and stewardship labor are well-established in the collective ledger. The collective's growing complexity creates increasing demand for quality human capital. Focus: scaling production, beginning the shift toward stewardship capacity, and progressively admitting care labor to the ledger as the collective's stake in human capital formation rises.

At ε = 0.90 (near-post-scarcity): Automation handles most production and much stewardship. Personal EOH in human-labor terms is low. Care labor is broadly registered and compensated. Focus: maintaining distributed competency, sustaining ecological systems, and fully recognizing care as the economy's core function.

At ε = 0.99 (effective post-scarcity): Remaining human labor is almost entirely care, judgment, and knowledge maintenance — all registered, all compensated. Prices have collapsed. TEH supply contracts on both the creation side (little human labor) and the destruction side (cheap goods require less TEH to purchase). The ledger must remain solvent and the floor must still rise even as both sides of the account shrink. Focus: ensuring the floor rises with automation, sustaining the knowledge EOH domain, and preserving the human capacity to intervene when automated systems fail.

Every function, parameter, and mechanism in this codebase must work across all points on this arc — or degrade gracefully from one to the next without requiring structural redesign.

---

## Structural Conditions

We assert that a TEH-denominated economy achieves stable, inflation-proof operation if and only if the first three conditions are maintained simultaneously. The fourth condition is not required for monetary stability but is strongly recommended for civilizational resilience.

### Condition I — Ledger Identity

Every unit of currency (TEH) in circulation must correspond to a verified record of entropy-reduction labor performed. Currency is created only through registered work — the fulfillment of entropy obligations across any of the four domains — and destroyed through terminal consumption (when a good or service is consumed in its final use) or capital write-down (when an asset degrades beyond recoverable function). The total supply must always equal cumulative creation minus cumulative destruction, with no exceptions. This structural linkage between money and entropy-reduction labor prevents the inflationary dynamics common in conventional monetary systems.

Spending that transfers TEH between parties (buyer to seller) is circulatory, not destructive. Levies and fiscal mechanisms that collect TEH are circulatory — they redirect TEH into capital investment, stewardship allocation, and social programs, but do not destroy it. Only terminal consumption and capital write-down remove TEH from existence.

The ledger identity must hold at ε = 0 (where barely any TEH is created or destroyed) and at ε = 0.99 (where both creation and destruction approach zero from price collapse). A verification mechanism that works only in the middle of the arc is incomplete.

### Condition II — Multiplier Band

An independent governing body assigns skill-tier multipliers to recognized occupations based on entropy-reduction leverage — how many hours of entropy obligation does one hour of this person's labor address? The four-factor assessment (training requirements, demand intensity, practitioner scarcity, and measurable societal impact) measures four aspects of this leverage. A Tier 1 worker fulfilling personal EOH reduces entropy at a near 1:1 ratio. A high-tier engineer designing water infrastructure works one hour but reduces thousands of personal EOH hours across a population.

The population-weighted average multiplier should be maintained within a defined band — a range of 1.8–2.1 with a target of 2.1 is recommended for modern economies. Individual multipliers may extend higher for rare specializations, with a recommended maximum of 6.0, but the band must be calibrated to balance entropy-reduction incentives against excessive income disparity. Grounding the multiplier in measurable entropy-reduction leverage rather than social convention makes it harder to corrupt politically while maintaining its role as an incentive for human capital development.

### Condition III — Zero Interest

Stored currency may not generate additional currency through any mechanism. No lending at interest, investment returns, or financial instruments that produce currency without corresponding labor. Account balances change only through earnings and expenditures. This condition eliminates passive wealth accumulation and requires that monetary stabilization be achieved through alternative policy tools rather than interest-rate manipulation.

Entropy compounds in physical reality — a neglected roof generates escalating obligations. The monetary system measures that reality honestly. Adding monetary interest would be measuring entropy that does not exist. Condition III ensures the currency reflects only real entropy resistance, never fictional growth.

### Condition IV — Distributed Competency (system resilience) *[recommended]*

Conditions I–III define the foundational monetary architecture. Condition IV is not structurally required for the currency to function, but is strongly recommended for any implementation intended to operate over the long term. Without it, the system remains monetarily sound but vulnerable to catastrophic fragility when automated systems fail.

If humans are the system's capital stock and automation handles the majority of EOH fulfillment, then automation failure means the full entropy burden returns to human labor instantaneously. The Sufficiency Guarantee (Principle 5) promises a floor of real purchasing power — but purchasing power requires goods and services to exist. If automation fails and no human workforce can step in, the floor becomes a nominal promise the real economy cannot honor. Condition IV is what makes the floor credible under stress.

A minimum share of the workforce must maintain certified competency across essential infrastructure domains such as agriculture, construction, energy, water, healthcare, manufacturing, and logistics. A threshold of approximately 15.5% of the workforce is recommended, with domain-specific allocations scaled to societal need. This ensures that human capacity to operate critical systems is preserved regardless of automation levels. Funding is supported through a minimum annual labor obligation — 260 hours per year is recommended — divided among competency rotation, stewardship service, and regular employment.

Any modification to the framework should consider its impact on distributed competency even when this condition is not formally adopted.

---

## Entropy Obligation Hours (EOH) — Accounting Framework

### EOH as demand signal

EOH are not currency. They are the unit of measurement for the labor demand that physical reality generates. Every element of the capital stock — including every living person — generates EOH continuously through the action of entropy. When a worker fulfills an entropy obligation that has been registered in the collective ledger, the EOH is retired and real TEH is created through verified labor.

EOH measures what the world needs. TEH measures what a worker earns for providing it. Fulfillment of EOH creates TEH at the worker's applicable multiplier rate — 100 EOH of infrastructure maintenance performed by a Tier 3 worker at a 3.0 multiplier creates 300 TEH. The multiplier system applies to all entropy-reduction labor uniformly.

### The dual ledger

The system tracks two quantities: TEH (entropy resistance performed) and EOH (entropy resistance owed to physical reality). The gap between accumulated EOH and fulfilled EOH constitutes deferred maintenance — a deficit that is visible, quantifiable, and structurally distinct from monetary debt. No one earns TEH from this deficit existing. No one charges interest on it. It persists until labor is directed toward it or the underlying capital fails.

### EOH and compounding

Unfulfilled EOH may generate additional EOH. A roof neglected for five years does not need five years of routine maintenance — it needs replacement, which demands more labor than the original maintenance would have. This resembles interest but is fundamentally distinct in three ways: it measures physical reality rather than enforcing a social convention; it rewards no party and punishes all through degraded systems; and its behavior is nonlinear and discontinuous rather than smooth and exponential. Long periods of slow accumulation are punctuated by sharp threshold failures — a pattern that bears no resemblance to compound interest curves.

The zero-interest condition (Condition III) prohibits arbitrary human mechanisms that generate currency without labor. EOH compounding generates obligation without labor. The TEH are created only when someone actually does the work.

### EOH and automation

At any automation level, the total EOH generated by the capital stock (including human capital) remains determined by physics. What changes is the share fulfilled by human labor versus machines. At ε = 0, all EOH fulfillment is human labor — though only the share registered in the collective ledger generates TEH; the remainder is private subsistence. At ε = 0.99, only 1% of registered EOH fulfillment requires human labor, and only that 1% creates TEH. The remaining 99% is handled by automation — the entropy obligation was real, it was met, but no monetary event occurred because no human labored.

This means the TEH supply contracts naturally with automation. But so do TEH-denominated prices, because less human labor goes into everything. Purchasing power remains stable or increases. The system contracts on both the supply side and the cost side simultaneously, producing the automatic floor-rise described in Principle 5.

The contraction is coherent only if the destruction side contracts correctly too. At ε = 0.99, goods are nearly free — terminal consumption destroys almost no TEH per basket consumed. The ledger approaches a near-zero steady state: near-zero creation, near-zero destruction, near-zero net. The account identity must hold in this regime, and the fiscal system must remain solvent within it.

### The registration boundary

Not all entropy resistance is an economic event. EOH exists at every scale — individual, household, community, nation, world — but TEH is created only when labor fulfills EOH that has been registered in the collective ledger. The collective is the organizing unit of the monetary system: a nation, a federation, or any body whose members are accounted for within its ledger.

**Self-care is a zero event.** A person who cooks their own dinner has resisted their own entropy, but no monetary event occurs. The EOH was generated and fulfilled within the same individual. The collective ledger does not see it.

**Household EOH is private.** A family unit has its own entropy obligations on its shared capital — the vehicles it operates, the food it may produce. Labor exchanged within the household to maintain these assets is real but internal. It does not enter the collective ledger and does not generate TEH.

**Land is held by the collective.** All land belongs to the collective, with stewards assigned exclusive use through leasing deeds. The structures built on that land generate infrastructure EOH that falls to the assigned stewards to manage outside the collective ledger — maintaining a home is a private stewardship obligation. In the final stages of automation, as the system approaches full EOH coverage, housing and land-based EOH may be registered to the collective ledger, zeroing out all remaining private EOH obligations. Until that point, the steward bears the entropy cost of the structures they inhabit and use.

**Collective EOH generates TEH.** When the collective registers a person as a member, that person's existence creates personal EOH in the collective ledger. A mother caring for three children is fulfilling registered EOH — the children are members of the collective, their personal entropy is accounted for, and the labor sustaining them is recognized as entropy resistance performed on behalf of the collective. That labor generates TEH.

**Care labor policy requires further modeling.** Because care-directed personal EOH (feeding, sheltering) involves tight creation-destruction cycles — TEH created through care labor and destroyed through the dependent's terminal consumption in close succession — the implementation must be designed to avoid both gaming and excessive ledger burden. One approach is a diminishing stipend per dependent child up to a defined maximum per care provider, covering the period of highest dependency (approximately ages 0–6), after which the child enters a different system of collective care such as formal education. The registered EOH per dependent is itself a function of automation: at ε = 0, the EOH burden per child in human-labor terms is highest (all care is manual); as automation rises, per-child EOH in human-labor terms decreases as automated systems handle more of the physical care burden. The specific structure of care compensation is a policy question with significant implications for incentives, equity, and ledger integrity, and will require careful modeling across epsilon levels.

The boundary between private and collective EOH is registration. The collective decides which obligations it recognizes, and that recognition is what makes labor economic. This means the scope of the monetary economy is defined by the scope of the collective ledger — what it counts, it compensates; what it doesn't count remains a private zero event.

**The registration boundaries are themselves functions of ε.** At ε = 0, most labor is internal to the family unit — subsistence, private, unregistered. The formal collective economy is small. As automation and institutional capacity grow, more categories of EOH become registered. Care labor that was always happening becomes visible, recognized, and compensated. Personal EOH that was entirely private begins to move onto the collective ledger as automated capital systems become capable of fulfilling it at scale. Each registration boundary follows its own sigmoid — different inflection points, different rates — but all are monotonically non-decreasing: the collective cannot un-admit an obligation once recognized.

**Collective demand drives care registration.** The admission of care labor to the ledger is not only a matter of verification capacity — it is driven by the collective's own increasing dependence on the quality of its human capital. At ε = 0, the collective has minimal complex systems and therefore minimal demand for specialized human capability. A subsistence community needs hands, not credentials. As automation rises, the collective's systems grow more complex: stewardship requires trained judgment, knowledge maintenance requires deep education, and the entire infrastructure of abundance depends on a pipeline of capable adults. The collective's stake in how children are raised, educated, and prepared scales with the complexity of what those children will eventually need to maintain.

This suggests that the share of care EOH admitted to the collective ledger — particularly children's personal EOH — is itself a function of the automation level, following a sigmoid curve. At low ε, admission is minimal (formal education, public health). Through the mid-automation range, admission accelerates as the collective's complexity demands quality human capital. Full registration of care EOH is likely required well before full automation and post-scarcity. The precise start, inflection, and saturation points of this sigmoid require further modeling, but the shape is clear: slow onset, rapid mid-range acceleration, and full registration reached before ε reaches 1.0.

### Regenerative offset

Some labor reduces future EOH rather than fulfilling current EOH. Composting enriches soil, reducing future agricultural labor needs. Preventive maintenance extends asset life, lowering future obligation generation rates. The system should distinguish between maintenance labor (fulfills existing EOH) and regenerative labor (reduces future EOH generation rates), as this distinction carries significant implications for long-term stewardship planning and capital investment decisions.

### Guardrail I — Physical grounding

EOH generation rates must be derived from measurable physical indicators — sensor data, engineering standards, material science, ecological monitoring, public health data — not from political discretion or fiscal convenience. Rates should be auditable against observable reality. When the assessment says a bridge generates 200 EOH per year, that figure must trace to inspectable conditions, not to a budgetary target. If EOH rates become politically negotiable, the system loses its claim to measuring reality and begins manufacturing obligation — which, while not interest, occupies the same structural territory of artificial demand creation.

### Guardrail II — Capital write-down

When capital degrades beyond the point where maintenance labor can restore function, the associated EOH must be formally written off. Irrecoverable capital cannot carry an indefinite maintenance obligation. The write-down recognizes a permanent loss of physical capacity — not a monetary event, but an acknowledgment that the asset no longer exists in maintainable form. The written-off EOH is replaced either by a new, larger EOH reflecting the labor needed to rebuild from scratch, or by zero if the capital is abandoned entirely. This mechanism prevents EOH from accumulating beyond what is physically meaningful and ensures the ledger reflects the actual state of the capital stock.

For human capital, death is a write-down. The person's personal EOH vanishes, but their entropy-reduction capacity also vanishes — every EOH they were fulfilling must be redistributed to other workers or to automation. The system must account for this redistribution without treating the event as merely an accounting adjustment.

### Guardrail III — Governance independence

The body that assesses EOH generation rates must be constitutionally independent, with structural protections equivalent to those given the multiplier body under Condition II. Whoever controls EOH assessment controls the economy's labor demand signal and therefore controls a significant channel of TEH creation. This power must not be subject to short-term political pressure. Assessment methodology, rate-setting procedures, and audit standards should be publicly transparent and subject to independent technical review.

---

## Design Principles

### 1. One hour of human entropy resistance is the invariant unit

The base unit does not change. What changes is what that hour is *for*. In the care economy, an hour sustains people. In the production economy, an hour builds systems that reduce aggregate EOH. In the stewardship economy, an hour maintains systems against entropy. The ledger, the multiplier, and the three foundational structural conditions hold across all three layers. Where adopted, Condition IV (Distributed Competency) should be evaluated for compatibility with any proposed extension. Any proposed extension that requires abandoning the time-base is solving the wrong problem.

### 2. The system must never depend on production for survival

The fiscal architecture — specifically the Trust, the Stewardship Allocation, and the Sufficiency Guarantee — must remain solvent under any automation level, including full automation of all physical production. Revenue streams pegged to economic output (levies on all labor, L) are supplementary. Revenue streams pegged to the capital stock's entropy obligations (the Stewardship Allocation) are foundational — not because capital earns a return, but because the size of the capital stock determines how much stewardship labor is needed. When modeling any new mechanism, ask: does this still work when output(ε) approaches the stewardship-only floor?

### 3. Distributed labor competency is a resilience requirement

Automation is not irreversible. Systems fail. Supply chains break. Energy grids collapse. Pandemics disable workforces that maintain automated systems. If automation handles 99% of EOH fulfillment and then fails, the full entropy burden returns to human labor instantaneously. This is the case for Condition IV: an economy that cannot fall back on distributed human competency across essential domains is an economy one cascading failure away from collapse — regardless of how sound its monetary architecture is.

The resilience case calls for: a minimum population with current training in essential production skills (agriculture, construction, energy, water, healthcare, manufacturing, and logistics), a rotation or revalidation mechanism that keeps those skills active rather than theoretical, and structural incentives for hands-on competency even when automation makes it economically unnecessary.

The variable-h framework already supports this: the minimum hours obligation (h_min) can be directed toward competency-maintenance labor. The multiplier system can recognize and incentivize maintenance of essential skills. The code must model this resilience layer explicitly — not as an afterthought, but as a recommended structural condition that complements the three foundational conditions and should be considered in all system modifications.

### 4. The multiplier measures entropy-reduction leverage

In the care economy, the multiplier answers: how much does this person's labor contribute to building the entropy-reduction capacity of others? In the production economy, it answers: how many hours of aggregate EOH does one hour of this person's labor eliminate? In the stewardship economy, it answers: how efficiently does this person maintain systems against entropy? The four-factor assessment function (training, demand, scarcity, impact) measures four dimensions of this leverage across all three layers without structural change — only the relative weighting of factors shifts as the economy evolves.

### 5. The floor rises with automation; it never falls

As automation reduces the human labor content of the Sufficiency basket, the Guarantee's purchasing power increases automatically. This is not a policy decision — it is a mathematical consequence of the system's structure. TEH-denominated prices fall as automation handles more EOH, so the same nominal TEH buys more. The nominal TEH amount may remain constant while the real standard of living it provides grows. Any proposed modification that would allow the floor to decline in real terms — through basket redefinition, regional manipulation, or conditional erosion — violates the system's core commitment. Model it, flag it, reject it.

### 6. Care is capital formation

Raising children, educating, training, healing, and mentoring are not peripheral activities that the economy supports. They are the economy's primary capital investment — the process by which the system builds the entropy-reduction workforce it depends on. A child requires years of high-EOH investment before contributing any entropy-reduction capacity. The return on that investment is measured in decades of contribution across all four entropy domains. Any framework modification that undervalues care labor or treats it as economically secondary misunderstands the system's capital structure.

### 7. Every mechanism must have a graceful degradation path

No mechanism should require a discrete "switch" from one economic zone to another. The displacement model should smoothly transition from "retrain into other production sectors" to "retrain into stewardship and care." The variable-h behavioral model should smoothly accommodate satiated consumption. As automation fulfills a growing share of EOH, the human labor share should contract continuously — never abruptly. If a function produces discontinuities, infinities, or undefined behavior as automation approaches 1.0, it is incomplete. Different automation stages require different focal priorities — but the transition between them must be smooth.

### 8. The code is the constitution's test bench

The papers describe a system. The code tests whether that system is self-consistent, fiscally solvent, and robust to shocks. Every claim in the papers should be verifiable by running a function. Every parameter should be sweepable to find its failure boundary. The dashboard is not a summary — it is a structural integrity check. If the dashboard shows green, the system works. If it shows red, the papers have a problem, not the code.

### 9. Every mechanism must express the arc, not just a point on it

The current calibration reference (ε = 0.40) is a validation anchor, not a design target. Any mechanism that is calibrated only to produce correct results at ε = 0.40 is incomplete. The test is whether it produces *meaningful, physically grounded results at both extremes*:

- At **ε = 0**: the system should express a near-zero collective economy. TEH barely circulates. Most EOH is private. Registration shares are near their floor values. The ledger must be well-defined and solvent in this regime, not merely degrade gracefully to it.
- At **ε = 0.99**: the system should express a near-zero-price economy. Human labor is negligible. Basket prices have collapsed. TEH creation and destruction both approach zero. The floor must still rise. The account identity must still hold. The fiscal system must still be solvent.

A mechanism that gives the right answer at ε = 0.40 but breaks at the extremes is a calibration artifact. A mechanism that gives the right answer at both extremes and everywhere in between is an expression of the transition. The framework's validity is measured by coherence across the full arc, not by accuracy at any single point.

---

## For Every Function You Write

Before committing any new function, verify:

- **If it generates EOH** (measures what entropy demands from physical reality): it takes physical state as primary inputs — capital stock, ecosystem health, population age distribution, knowledge base size, monitoring capability. ε is not a primary input here. It may be accepted as an optional parameter that looks up canonical physical-state defaults for backward compatibility or arc testing, but the function must work correctly when called with actual physical state and no ε.
- **If it computes fulfillment, registration, prices, or fiscal values** (models how the civilization responds to entropy demand): it takes ε as a mechanism parameter. The human/machine split, registration curves, and fiscal mechanisms are genuinely ε-driven.
- It produces **physically meaningful output at ε = 0** (subsistence: near-zero collective economy, private EOH, minimal ledger activity)
- It produces **physically meaningful output at ε = 0.40** (current equilibrium: production/stewardship mix)
- It produces **physically meaningful output at ε = 0.90** (near-post-scarcity: care-dominant, automation-heavy)
- It produces **physically meaningful output at ε = 0.99** (effective post-scarcity: prices collapsed, labor near-zero, fiscal contraction)
- It does not depend on output(ε) being large (the stewardship economy has low output)
- It does not assume all workers are engaged in production
- It accounts for all four entropy domains where relevant (personal, infrastructure, ecological, knowledge)
- It respects the three foundational structural conditions (ledger identity, multiplier band, zero interest) and considers Condition IV (distributed competency) where adopted
- It has a clear paper section reference in its comment header
- It is included in the dashboard or has an explicit reason for exclusion
- It degrades gracefully as automation approaches 1.0 — and is also defined at automation near 0.0
- Its behavior at the extremes expresses the physical logic of the transition, not an artifact of midpoint calibration
