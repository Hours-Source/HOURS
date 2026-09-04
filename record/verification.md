# The gates, and the checks on the checks

**Scope.** The gate modules themselves, test-suite audits, mutation sweeps and
pin coverage, the claims register, the wiring gate, the mint-path and stock
identities.

**The distilled lessons are NOT here.** They live in `CLAUDE.md` § Recurring
failure modes, loaded every session, because they do not belong to an area — the
frame seam was found in six subsystems, the stranded parameter in four. This file
is their **evidence**: the sessions in which each was found, with the numbers.

Migrated from `CLAUDE.md` § Current status on 2026-09-03. Entries are verbatim.

---

## Live state

- **Twelve gates ship**, indexed in `CLAUDE.md` § Test file index under *"Gates —
  they check the repo, not a module"*. The `record/` split added
  `tests/test_record_index.py` (34 tests — index staleness, cross-link
  resolution, the live-surface budget, and the failure-mode citation form) and
  widened the corpus in `tests/test_claims_register.py` to span `record/*.md`.
- **Two gates live OUTSIDE the repo, because what they check does.**
  `~/.claude/corpus/check.py` validates the portable corpus and that every
  `F-0NN` this file cites resolves; `~/.claude/corpus/check_memory.py` validates
  that session-memory pointers reach real `record/` anchors, that commit shas
  named there exist, and that no entry is filed in two stores. Neither can run
  in CI — memory and the corpus are not inside any repo — so they are manual and
  say so.
- **Exactly ONE mint call site** across `core/`, `land/` and `scenarios/`,
  enforced by AST and not grep *(gated)* — four of the five textual matches in
  this repo are prose.
- **The stock is an identity, not a bound**: `supply = endowment + Σcreated −
  Σdestroyed`, exactly, over 120 periods, against three independent accounts.
  `teh_supply()` implements the tighter bound the theory wants, **has zero callers
  and raises on the shipped trajectory** *(gated)*; a new caller is a test
  failure, which is the safe holding state.
- **The wiring ratchet stands at 12** *(gated)* — parameters accepted, inert at
  every configuration tried, and never passed by name in the suite. The count may
  not rise, and each is declared with its reason.
- **No constant in `data.py` is denominated in currency** *(gated)* — so the
  monetised route is currency-free too, and the real distinction is CENSUS versus
  VALUATION, not the presence of a price.
- **Measured pin coverage (2026-08-27), and the two gaps compound**: 0 of 232
  `data.py` scalars unpinned, **34 of 63 shadow constants** unpinned at the time
  of the sweep. `data.py` is 100% tagged AND 100% pinned; outside it, 0% tagged
  and 46% pinned. Later work took the shadow figure to 9 of 38, all nine
  deliberate.

## Open

- **The compensating-mechanism audit** (review §15) is unbuilt.
- **Dynamic stability / oscillation** (review §6) is unbuilt. `arc_stability`
  answers stationarity, **not** whether the coupled capital→automation→income→
  formation loop oscillates. Nothing tests for limit cycles.
- **The claims register checks that an open item is DECLARED, never that it is
  still OPEN.** That gap let a `STILL OPEN` line sit stale for a day while the
  file asserted the adoption two entries above it — the first instance the
  register did not catch. *Settles by:* a predicate per open item, which is the
  same shape as `LIVE_CLAIMS` and has not been built.
- **The shadow ratchet cannot catch its own bound being loosened.** `len(_DECLARED)
  <= 8` passes if the bound is simply raised — verified, that mutation does not
  bite. Recorded rather than papered over: raising it is a visible act in a diff,
  and a meta-ratchet moves the same problem up one level.
- **`utils/corridor_cmd.py --available-labor` still defaults to 1.0e9**, the
  fourth artefact of the retired work-year convention. Declared, not yet changed.

## Cross-area entries

Filed here on primary subject; each also bears on another area.

| Entry | Also | Why |
|---|---|---|
| [neighbouring-questions-three-defects](#neighbouring-questions-three-defects) | [fulfilment](fulfilment.md) | Three defects in `arc_stability` — mixed standards, an inadmissible standard, and a default off by 10⁶ — all of which passed 36 tests in their own file |
| [doctrine-invariance-was-circular](#doctrine-invariance-was-circular) | [provenance § Live state](provenance.md#live-state) | The currency-denomination scan it rests on is a provenance scan |
| [test-suite-audited-pin-coverage](#test-suite-audited-pin-coverage) | [provenance § Live state](provenance.md#live-state) | The measured pin-coverage baseline, and the shadow-constant denominator it pairs with |
| [branch-merge-ready](#branch-merge-ready) | [ecological](ecological.md#history) | The merge review that found three stale `STILL OPEN` lines — the failure that prompted the claims register |

See also [provenance.md § Cross-area entries](provenance.md#cross-area-entries)
for the two gates filed there.

*(gated)* marks a line checked against the code by
`tests/test_claims_register.py`.

---

## History
<a id="the-record-split"></a>

**THE STATUS LOG SPLIT BY SUBJECT AREA — AND THE END-TO-END CHECKS FOUND THREE DEFECTS THE GATES DID NOT** (2026-09-03/04, merged `b2892ac`). `CLAUDE.md` **304,528 → 40,215** chars against a 150,000 limit; nine area files under `record/`, 85 entries, **0 deleted**. 3,977 tests pass, mypy clean on 90 files.
- **THE SPLIT IS BY RETRIEVAL QUESTION, NOT BY DATE.** Filing by date would have cleared the limit and left the file still mostly journal. State and evidence ROUTE by area; the recurring failure modes STAY in `CLAUDE.md`, loaded every session.
- **THE LESSONS MUST NOT ROUTE, and that is the one thing area-filing cannot do.** The frame seam was found in six subsystems, the stranded parameter in four, a status note outliving its decision in nine places. **Filing a lesson under the area where it was LAST found means the session most likely to repeat it is exactly the one that does not load that file.** Routing optimises for what you are working on; lessons are needed for what you are about to break somewhere you are not looking.
- **THE REGISTER HAD TO BE WIDENED FIRST OR THE SPLIT WOULD HAVE BLINDED IT.** `_text()` now reads `CLAUDE.md` PLUS every `record/*.md`. Narrowing it back fails **12** tests — up from 4 after the first area moved, which is the measure of how quietly this could have gone wrong.
- **HISTORY IS UNBOUNDED BY DESIGN AND THE SUMMARY IS NOT.** Capping history trades a known cost — a large read — for an unknown one, a lesson nobody can reach. What degrades is NAVIGABILITY, so `utils/record_index.py` generates a per-file entry index instead. The live surface is budgeted at 6,000 chars: nine files written independently landed between 4,058 and 4,996 with no coordination, whether the area carried 3 entries or 18, **so the budget codifies a regularity rather than imposing one** and binds on nothing today. `test_the_budget_is_not_vacuous` fails if it is raised far enough to stop guarding — the meta-ratchet the shadow ratchet explicitly cannot have.
- **THE STRUCTURAL CHECKS FOUND THREE DEFECTS, ALL IN WORK COMMITTED THE SAME DAY, AND NONE OF THEM BY A GATE.** (1) Four corpus citations were inserted after the OPENING `**` for the two-digit modes — **counting the markers found 13, parsing them found 9.** (2) The thermal build log was promoted to `record/` and left standing in memory, **98% duplicated**, which is F-008 committed by the change meant to prevent it. (3) A shadowed variable in `check.py`. **The gates that shipped with each change all passed.**
- **SO THE CONSERVATION AUDIT IS THE ONE WORTH REPEATING AFTER ANY STRUCTURAL CHANGE**: 87 of 87 pre-split entry headlines still present, and all 16 substantive claims from the six blocks deliberately restructured survive. Retrieval verified in three hops — README → area → index row → entry — on a fact buried in a 2026-08-30 parcel entry.
- **AND THE SELF-VERIFICATION PATTERN IS NOW A CORPUS FINDING (F-038).** Four times in one session I verified with a cheaper instrument than the consumer uses: counted markers a reader parses, grepped one link form when two exist, and ran two mutations whose replacement never applied. **The cheap instrument agrees with the expensive one right up to the case that matters.**

<!-- record-index: generated by utils/record_index.py, do not hand-edit -->

| 11 entries, newest first | |
|---|---|
| [the-record-split](#the-record-split) | THE STATUS LOG SPLIT BY SUBJECT AREA — AND THE END-TO-END CHECKS FOUND THREE DEFECTS THE GATES… |
| [stock-is-an-identity](#stock-is-an-identity) | THE STOCK IS AN IDENTITY, NOT A BOUND — AND THE PROPOSITION THE ANCHOR RESTED ON WAS FALSE AT F… |
| [doctrine-invariance-was-circular](#doctrine-invariance-was-circular) | THE DOCTRINE-INVARIANCE EVIDENCE WAS CIRCULAR, AND THE CLAIM IT SUPPORTED WAS THE WRONG ONE |
| [one-mint-path-gated](#one-mint-path-gated) | ONE MINT PATH GATED — AND THE CHAIN'S MIDDLE LINK IS ASSUMED, NOT VERIFIED, ON THE DEFAULT PATH |
| [float-equality-across-a-restructured-sum](#float-equality-across-a-restructured-sum) | A TEST THAT PASSED HERE AND FAILED ELSEWHERE — BIT-EXACT FLOAT EQUALITY ACROSS A RESTRUCTURED S… |
| [wiring-gate-defect-fixed](#wiring-gate-defect-fixed) | THE ONE REAL DEFECT THE WIRING GATE FOUND IS FIXED — A ROUND TRIP THAT CANCELLED, AND THE SEVEN… |
| [the-wiring-gate](#the-wiring-gate) | THE WIRING GATE — AND IT CATCHES NONE OF THE THREE DEFECTS THAT PROMPTED IT, WHICH IS THE FINDI… |
| [neighbouring-questions-three-defects](#neighbouring-questions-three-defects) | CHECKING WHETHER THE NEIGHBOURING QUESTIONS WERE REACHABLE FOUND THREE DEFECTS IN PHASE 1 — ALL… |
| [the-claims-register](#the-claims-register) | THE CLAIMS REGISTER — CLAUDE.md's CHECKABLE ASSERTIONS ARE NOW CHECKED |
| [branch-merge-ready](#branch-merge-ready) | BRANCH `fix/findings-and-domain-balance` IS MERGE-READY |
| [test-suite-audited-pin-coverage](#test-suite-audited-pin-coverage) | THE TEST SUITE AUDITED AGAINST ITS OWN FAILURE MODES, AND THE PIN COVERAGE MEASURED |

<!-- /record-index -->
Newest first, verbatim as written. Anchors are stable — link to a specific entry
as `record/verification.md#<slug>`.

<a id="stock-is-an-identity"></a>

**THE STOCK IS AN IDENTITY, NOT A BOUND — AND THE PROPOSITION THE ANCHOR RESTED ON WAS FALSE AT FOUNDING** (2026-09-01). `tests/test_stock_is_bounded.py`, 16 tests, 3,744 pass, mypy clean on 88 files. **REPORTING ONLY — no code outside tests changed.**
- **WHAT HOLDS: `supply = endowment + Σcreated − Σdestroyed`, EXACTLY, over 120 periods.** Verified against THREE independent accounts — the per-period reported flows, the state's own cumulative counters, and the reported supply — at `rel=1e-12`. Not vacuous: reconstructing from reported flows catches a path that moves TEH without reporting it, which the state's internal consistency would not.
- **WHAT DOES NOT HOLD: `supply ≤ Σcreated`, which is what the value-anchor draft asserted.** The economy begins holding a Trust balance plus embodied capital that **no registered fulfilment created** — `teh_created_cumulative` is 0.0 at founding against an endowment of 37e9, **more than 100× the first period's mint**. The attractive claim, that nothing stands which fulfilment did not create, is FALSE at period 0.
- **IT IS TRUE LATER, AND THAT IS WHY THE POSITION SURVIVES.** Destruction outpaces creation early — 19.86e9 destroyed against 15.75e9 created over 40 periods — so the founding stock TURNS OVER, and cumulative fulfilment overtakes everything standing partway through the horizon. The claim is a long-run one and §2 of the draft now makes it as one instead of asserting it flatly.
- **AND IT SURFACED TWO ACCOUNTS OF ONE QUANTITY.** `core/eoh_fulfillment.teh_supply()` implements exactly the tighter bound and RAISES *"Ledger violation: destroyed > created — impossible in a correct system"*. It is named in its own module's pipeline docstring as the supply step. **It has ZERO callers, and it raises on the shipped model's own canonical trajectory** — handed the 40-period cumulative flows it refuses them. It describes an economy with no endowment; `simulate_period` computes `teh_endowment + created − destroyed` instead. Pinned rather than deleted, because it is the bound the theory WANTS, and a new caller is now a test failure.
- **CONDITION III PINNED AS BEHAVIOUR, NOT DOCTRINE.** With no inflows the Trust balance must FALL — if it rose, something would be paying a return on a holding. And the dividend RATE is identical at 1e9 and 1e11, so the scaling is drawdown rather than yield; a super-linear response would be interest. Adding a 3% yield fails 2 tests.
- **THE OFF-BY-ONE THAT ONLY A GROWING SERIES CATCHES.** `run_simulation`'s `states[i]` is the state AFTER `period_results[i]` — the initial state is not in the list. My first version zipped `states[1:]` and failed; **that misalignment passes silently for any constant flow** and was caught only because minting grows period on period. Written into the test.
- **THREE MUTATIONS RUN AND ALL THREE BITE**: supply gaining TEH with no reported flow fails 1; the state counter drifting from the reports fails 2; the Trust paying a yield fails 2. The first was asserted present in the executed source before being believed — the dead-branch lesson from the doctrine work.

<a id="doctrine-invariance-was-circular"></a>

**THE DOCTRINE-INVARIANCE EVIDENCE WAS CIRCULAR, AND THE CLAIM IT SUPPORTED WAS THE WRONG ONE** (2026-09-01). `tests/test_doctrine_invariance.py`, 14 tests, 3,728 pass, mypy clean on 88 files. **REPORTING ONLY — no code outside tests changed.**
- **`floor_spread == 1.000` CANNOT FAIL.** The doctrine parameter reaches only a `discretionary_eoh` term added ABOVE the floor, and the floor is `Σ count × hours_per_unit_year`. `doctrine_floor_invariance`'s own docstring says it: *"1.000 by construction of the design"*. The value-anchor draft was leading with that figure as the framework's strongest evidence, and **an assertion the implementation enforces unconditionally is not evidence** — failure mode 6, on the claim the section was built around.
- **AND "NO PRICE ANYWHERE IN THE CHAIN" IS TRUE AND DISTINGUISHES NOTHING.** Measured: **no constant in `data.py` is denominated in currency** — the only three matches on a monetary regex are price RATIOS and years-of-basket. So the monetised route is currency-free too. **The real distinction is CENSUS versus VALUATION**: counting bridges needs no convention, valuing them needs replacement vs depreciated vs historical. §2 of the draft now argues that instead, which is sharper and survives the obvious rebuttal.
- **THE VALUATION ROUTE TRANSMITS THE DOCTRINE UNDAMPED, AND THAT IS NOW REPRODUCIBLE FROM THE PACKAGE.** One physical stock under three valuation ratios gives an output spread of **3.363636 against an input ratio of 3.363636 — exact.** Nothing damps it anywhere. Expressed as RATIOS, not dollars, so no figure is invented; the previous 10.26× lived only in a gitignored handoff, which is why the anchor's headline rested half on an artifact no reader could open.
- **THE FALSIFIABLE REPLACEMENTS.** The census route ignores monetary fields added to its buckets (someone COULD make it read them); refuses a bucket carrying a valuation and no count rather than treating it as zero; is extensive in the census; and is **invariant to how the census is AGGREGATED** — splitting every bucket in two moves nothing, asserted at tolerance rather than `==`, which is the `subdivision_invariance` lesson.
- **THE SCENARIO'S PARAMETER IS LIVE EVEN THOUGH ITS FLOOR RESULT IS STRUCTURAL**, and that pairing is what stops the whole thing being vacuous: `total_spread > 1.0` while `floor_spread == 1.0`. A doctrine moves the TOTAL and not the FLOOR, which is the design claim; if it moved neither, the invariance would be evidence of a dead parameter.
- **A MUTATION THAT DOES NOT RUN IS A FALSE PASS, AND IT IS THE MORE DANGEROUS DIRECTION.** Damping the valuation route by mutating `capital_stock *` reported the test as NOT biting — the string sits inside an `if epsilon is not None` branch and the test calls with `epsilon=None`. **The edit applied, the suite passed, and the conclusion "this test is weak" was wrong.** The ε=0.40 trap with the TOOL as the victim rather than the test. Re-run on the executed return line, with the mutation asserted present in the LOADED source first, it bites. Recorded in the agent corpus (F-016).
- **FOUR MUTATIONS RUN AND ALL FOUR BITE**: the floor reading a valuation field, the floor becoming aggregation-dependent, the valuation route damping the doctrine, and a currency-denominated constant appearing.

<a id="one-mint-path-gated"></a>

**ONE MINT PATH GATED — AND THE CHAIN'S MIDDLE LINK IS ASSUMED, NOT VERIFIED, ON THE DEFAULT PATH** (2026-09-01). `tests/test_one_mint_path.py`, 25 tests, 3,714 pass, mypy clean on 88 files. **REPORTING ONLY — no code outside tests changed.**
- **THE CLAIM WAS STATED IN PROSE IN SEVERAL PLACES AND CHECKED NOWHERE.** The value-anchor argument's whole defence against labour vouchers and energy certificates is that an hour mints nothing unless a registered obligation existed and was met. Nothing enforced it. Now: exactly ONE mint call site across `core/`, `land/` and `scenarios/`, enforced by **AST and not grep** — four of the five textual matches in this repo are prose, so a text scan would have reported five mints and been ignored.
- **THE HOLE-DIGGER TEST, RUN.** Surplus labour mints nothing at 1e10, 1e12 or 1e15 EOH — the mint saturates on the OBLIGATION, not on the hours offered — and a real shortage mints less and reports the deficit. Zero registration mints exactly 0 while the obligation still exists. **Registration is heavily binding rather than a formality: 82.3% of human EOH mints nothing at ε=0.40**, which is a measurement, not an identity, and is pinned as a majority rather than a level.
- **FIVE FISCAL LEVERS PERTURBED AND NONE REACHES THE MINT** — levy rate, Trust base, dividend rate, depreciation rate, estate fraction. The fiscal layer decides who HOLDS TEH, never how much exists. The Trust is a DRAWDOWN and is pinned as one: with no inflows, `trust_end == trust_start − dividend` exactly, so nothing is created on the way out.
- **AND THE GATE CANNOT BE SATISFIED WHILE THE ARITHMETIC MOVES UNDER ANOTHER NAME.** `fiscal.stewardship_allocation` computes `human_eoh × mean_multiplier`, which is character-for-character the mint and is not one — it is a REQUIREMENT in TEH units so it can be compared against the Trust. Pinned as not-minting, and pinned as a requirement: starve it and `teh_allocated` goes to 0 with the whole amount reported as a funding gap.
- **THE FINDING: `available_labor_eoh` DEFAULTS TO UNSUPPLIED, SO THE PIPELINE MINTS FROM DEMANDED HUMAN EOH RATHER THAN SERVED.** The module's own docstring has said so all along — *"the pipeline assumes every hour of human-carried EOH gets worked — a demand figure reported as fulfillment"* — but the anchor argument says **VERIFIED** fulfilment, and the default path does not verify. Measured at its sharpest: **at population = 0 the default path still mints 95,669,542.59 TEH**, because infrastructure and knowledge obligations do not depend on anyone existing; supply `available_labor_eoh=0.0` and it mints **exactly 0.00** with 81,000,000 EOH booked as deferred.
- **SO AN INSTITUTION THAT DOES NOT SUPPLY ITS LABOUR DATA IS MEASURING DEMAND AND CALLING IT FULFILMENT.** This is not a defect in the constraint — it is a statement about which path has to be run for the chain's middle link to mean anything, and the implementation guide does not currently say it at the intake table. `notes/value-anchor.md` §2 now states the limit instead of claiming the verification.
- **THREE MUTATIONS RUN AND ALL THREE BITE**: a second mint call added in `core/fiscal` fails 1; a levy rate reaching the mint fails 5; surplus labour inflating the mint fails 1. Restoration verified by re-running, not by inspecting the file.

<a id="float-equality-across-a-restructured-sum"></a>

**A TEST THAT PASSED HERE AND FAILED ELSEWHERE — BIT-EXACT FLOAT EQUALITY ACROSS A RESTRUCTURED SUM** (2026-08-31). Reported from another machine: 6 failures in `test_guf_magnitude`, none reproducible locally at HEAD, at the pushed commit, in isolation, or in reverse file order. **The count identified the cause.** 3,630 pass, mypy clean on 87 files, provenance 292/292, shadow held at 33.
- **THE FAILING COUNT IS THE DIAGNOSIS.** Simulating the obvious suspect — `parcel_rate` not forwarded through `_GUF_SPREAD_KEYS`, e.g. from stale bytecode — fails **SEVEN** tests, including `test_bell_remains_reachable`. The report showed **SIX**, with the bell test passing. That rules the forwarding out and leaves the other candidate.
- **`subdivision_invariance` ASSERTED `after == before` ON FLOATS**, comparing a fee summed over **10,000 parcels** against the same fee summed over **20,000 halved** ones. **Floating-point addition is not associative**, so the two accumulations may differ in the last ulp. It held on this machine — even with the summation reversed — and did not on another. **Exactly those six tests fail under that reading and the bell test does not**, which is the reported signature precisely.
- **THE `==` PREDATES THE PER-PARCEL TERM.** `invariant` has been `after == before` since `subdivision_invariance` was written; Phase 2's `area_only_invariant` copied the same unsound assertion into a second place. Both now compare against `SUBDIVISION_FP_TOLERANCE`.
- **THE CLAIM IS UNDAMAGED, AND A TEST ENFORCES THAT.** The tolerance must separate a parcel-blind **1.0** from a per-parcel **1.1194** — eleven orders of magnitude — and `test_the_tolerance_cannot_hide_the_effect_it_must_distinguish` fails if it ever gets within 1e-9 of the effect. **A tolerance wide enough to absorb the finding is worse than none**, which is the `GOODS_PRICE_FLOOR` lesson (`abs=0.02` on a floor of `0.05` let a 40% move pass).
- **BOTH OPEN DETECTORS FROM THE WIRING AUDIT ARE CLOSED, RATCHET 11 → 8.** `epsilon_sweep(jump_threshold=)` now has a test that it CAN fire — 0 flags at the default, more as it lowers, and every flagged row exceeding its own threshold. `planetary_budget(a_earth=)` is pinned as a **proportionality above the P0 clamp** (double the area, double the budget), paired with its companion showing the inertness AT the clamp is the clamp and not the area, so neither reading can be quoted alone.
- **THE SHADOW RATCHET FIRED ON THE NEW TOLERANCE AND IT WAS MIGRATED, NOT EXEMPTED** — `SUBDIVISION_FP_TOLERANCE` into `data.py`, tagged `convention`, NUMERICS ONLY. Third time this session a gate has bitten on my own new code.
- **AND THE GATE STATES ONE MORE LIMIT: IT CANNOT CATCH ITS OWN RATCHET BEING LOOSENED.** `len(_DECLARED) <= 8` passes if the bound is simply raised — verified, that mutation does not bite. Recorded rather than papered over: raising it is a visible act in a diff, and a meta-ratchet would move the same problem up one level.

<a id="wiring-gate-defect-fixed"></a>

**THE ONE REAL DEFECT THE WIRING GATE FOUND IS FIXED — A ROUND TRIP THAT CANCELLED, AND THE SEVENTH FRAME SEAM** (2026-08-31). `hours_per_worker_year` no longer takes a population; `reference/atus_time_use.population_15_plus()` added; 4 tests; ratchet **11 → 10**. 3,624 pass, mypy clean on 87 files. **THE VALUE DID NOT MOVE — 1874.428397952944, to float precision.**
- **THE PARAMETER WAS A ROUND TRIP.** `hours_per_capita(..., total_population)` multiplies by `population_15_plus / total_population`, and the return multiplied `total_population` straight back in. **The answer was 1,874.4284 at EVERY population**, so a caller reframing to another country got the same number while believing they had reframed it. Seventh instance of the frame seam, and the first found by a gate rather than by an audit.
- **THE VALUE COULD NOT MOVE, WHICH IS THE PROOF THE DIAGNOSIS WAS RIGHT.** A cancelling parameter cannot have been affecting the answer, so removing it must be exactly value-neutral — pinned at `rel=1e-12`. If it ever moves, the removal was not a pure cancellation and the derivation needs re-reading.
- **THE FRAME DID NOT VANISH, IT MOVED TO WHERE IT BELONGS.** Hours per worker does not depend on how many NON-workers there are, so the ratio is population-free by construction. **Both callers keep their own `total_population`** — they use it for their own per-capita conversions, which are live and pinned as such.
- **THE FIX IS IN THE SHAPE OF THE NUMERATOR, NOT IN A COEFFICIENT.** The equation is now `paid hours per person 15+ × population_15_plus / total employment` — a 15+ AGGREGATE built directly, instead of converting down to per-capita and multiplying a population back. `population_15_plus(year)` is exposed for exactly that reason and its docstring names the round trip as the thing to avoid.
- **THE GATE FIRED ON ITS OWN STALENESS CHECK THE MOMENT THE PARAMETER STOPPED EXISTING** — `test_every_declaration_names_something_still_inert`, the `unused_innocuous_names` discipline, working within minutes of the fix rather than going stale like the allowlist entries that prompted it.
- **AND THE DECLARATION IS STRUCK THROUGH, NOT DELETED.** The `_DECLARED` entry became a comment recording what the defect was, so the shape stays visible; the ratchet bound dropped 11 → 10, which is what a real fix looks like against that counter.

<a id="the-wiring-gate"></a>

**THE WIRING GATE — AND IT CATCHES NONE OF THE THREE DEFECTS THAT PROMPTED IT, WHICH IS THE FINDING** (2026-08-31, `tests/test_parameter_wiring.py`, 10 tests). An audit for the session's repeated failure: **tests pinning the shape of the OUTPUT while the WIRING behind it was wrong.** 3,620 pass, mypy clean on 87 files.
- **THE SCOPE IS NARROWER THAN THE MOTIVATION AND THE GATE SAYS SO IN ITS OWN DOCSTRING.** Verified by reintroducing all three: the ratchet stays GREEN on the mixed standards, the 10⁶ capital default, and the inert `personal_base`. **A gate that reads as covering more than it does is the failure this repo already names**, so what it CANNOT catch is written down and pinned by a test: a wrong-but-live default (no inertness probe reaches it), a parameter that SHOULD exist and does not (the mixed-standard defect had no parameter at all), and a parameter a test names but under-pins (stage 2 filters anything the suite passes by name).
- **WHAT IT DOES CATCH IS REAL, AND IT FOUND ONE DEFECT IMMEDIATELY.** `scenarios/food_conservation.hours_per_worker_year(total_population=)` **STRUCTURALLY CANCELS** — `hours_per_capita(..., total_population)` divides by it and the return multiplies by it, so it is a round trip and the answer is **1,874.4284 at every population**. The docstring's governing equation advertises a dependency that is void, and **a caller reframing to another population gets the same number silently** — the frame-seam shape found six times. Reported, not yet decided: document-and-pin the cancellation, or remove the parameter.
- **AND TWO DETECTORS NOTHING HAD EVER EXERCISED.** `epsilon_sweep(jump_threshold=)` is live — **0 discontinuities at the default 5.0, 29 at 0.05, 498 at 0.001** — and no test has ever passed it, so nothing checks the detector can fire. `planetary_budget(a_earth=)` is the only one of five physics parameters `test_thermal` does not exercise above the P0 clamp.
- **STATIC ANALYSIS CANNOT REACH THIS CLASS**, which is why the probe is dynamic: `personal_base` WAS referenced in the body — forwarded into a call that ignored it.
- **THE TWO-STAGE FILTER IS WHAT MAKES IT USABLE, AND "INERT AT DEFAULTS" IS NOT "UNPINNED".** `planetary_budget`'s defaults sit on a clamp (λ·ΔT = 2.4 against F_ghg = 3.0, so **P0 = 0.0**), which makes all five of its physics parameters inert THERE — and `test_thermal` correctly pins both sides of that clamp. Flagging them would have got the gate suppressed within a week. So: inert at every configuration tried **AND** never passed by name in the suite. 43 → 11.
- **THE FIRST VERSION FELL INTO THE TRAP IT WAS BUILT TO FIND.** It called every function with no arguments — which for `total_eoh` is `epsilon=None`, the ε=0 branch, where `knowledge_exponent` is raised to the ZEROTH POWER and cannot bite — and reported a live parameter as inert. **The ε=0.40 trap inside the tool for finding it.** Now several configurations are tried and a parameter must be inert at all of them.
- **AND THE SECOND VERSION RETURNED `None` FOR EVERY STRING**, so `standard: str` — the very parameter whose threading defect prompted the audit — was unprobed. Strings are now perturbed through their DECLARED ENUM (`STANDARDS`, `AUTOMATION_RESPONSES`, `PSI_POLICIES`): if the defining module holds a tuple containing the default, another member is tried.
- **THE 11 SPLIT FOUR WAYS AND ONLY ONE IS A DEFECT**: 1 real (above), 2 unexercised detectors, 4 numerics/near-threshold where inert IS correct, and 4 **inert by ADOPTED POLICY** — the two `total_eoh` ecological intake fields (Phase 4e/4f emptied the domain) and both `capacity_floor` parameters (§8.9b escalation never fires at canonical defaults). Each is declared with its reason and the count may not rise.

<a id="neighbouring-questions-three-defects"></a>

**CHECKING WHETHER THE NEIGHBOURING QUESTIONS WERE REACHABLE FOUND THREE DEFECTS IN PHASE 1 — ALL SHIPPED, ALL PASSING** (2026-08-30). Prompted by "are `canonical_arc_trajectory` and `corridor` accessible?" Both ARE — `scenario run canonical_arc`, `corridor band`, `corridor axes` all run clean. **The pointers were fine; the module that named them was not.** 42 tests on `arc_stability`, 3,552 pass, mypy clean on 86 files.
- **DEFECT 1 — ONE VERDICT, TWO STANDARDS, UNDECLARED.** Conditions 1 and 3 ran at `collapsed` (feasibility's own default, 1000) while condition 2 ran at `sufficiency` (overbuild's own default, 1500). **This is the category error CLAUDE.md already records once** — *a SURVIVAL feasibility test applied to a SUFFICIENCY number* — and it is why `corridor band --standard` exists. Now threaded through all three and reported.
- **DEFECT 2 — `collapsed` IS NOT ADMISSIBLE AT ALL, and `core/autarky` says so in as many words**: *"an abated value cannot be the autarky reference; use 'sufficiency' (F_a) or 'survival' (S_a)"*. It is F_a·(1 − a) — the apparatus is already baked in — so it cannot be the counterfactual FOR the apparatus. `STANDARDS = ("survival", "sufficiency")` and `collapsed` now RAISES.
- **DEFECT 3, THE WORST — `capital_stock_teh` IS TOTAL, NOT PER CAPITA, AND MY DEFAULT WAS OFF BY 10⁶.** `overbuild_check`'s own docstring says *"Total apparatus capital"* and it divides by population itself; my default of `2000.0` over 1e6 people modelled **0.002 TEH/capita**. So `delivery_pays` was True everywhere — **not because the apparatus always pays, but because there was no apparatus.** Condition 2 was structurally unable to bind and the three-condition verdict was really two. Now `CAPITAL_STOCK_DEFAULT` (2e9), and at 2.5e10 it correctly reads `overbuilt`.
- **A FOURTH, SMALLER ONE: a silently-ignored parameter of my own making.** I passed `personal_base` into `feasibility_check` and read only `supply_per_capita`, which does not depend on it — supply is 1,200.0 at every standard. Replaced with a direct `labor_supply_per_capita()` call, which is honest about what is needed. **And the `source:` field in `CONDITIONS` still named `feasibility_check` after the call was gone** — a pointer outliving its call, in the module written to catch that.
- **EVERY ONE OF THESE PASSED ALL 36 TESTS IN ITS OWN FILE.** Three times in one session the suite failed to catch a defect in the module it covers: mixed standards, a 10⁶ units error in a default, and an inert parameter. **The tests pinned the shape of the output and never the wiring behind it.**
- **THE FIX THAT GENERALISES: pin the observable that only the wiring can move.** The band could not see condition 2 — it is driven by conditions 1 and 3 — so a standard stuck on its own default was invisible. `autarky_reference` is the one field of the overbuild test that moves with the standard (780,960,000 survival vs 1,952,400,000 sufficiency), and pinning THAT is what makes the threading falsifiable. Five mutations now bite where four did not.
- **AND THE TWO MODULES DO NOT CONTRADICT — STATING THE STANDARD IS WHAT MAKES THAT VISIBLE.** Corridor asks which ε are SURVIVABLE; `arc_stability` asks where the system could STAND STILL, which additionally requires the delivery cost covered. **Stability is therefore strictly stronger, and it is now pinned as an inequality at every standard**: survival — corridor floor 0.000, band [0.000, 0.990]; sufficiency — corridor floor 0.424, band **[0.487, 0.990]**. The earlier reported band of [0.171, 0.990] was the undeclared-standard figure and is superseded.
- **`eoh scenario run arc_stability --standard {survival,sufficiency}`**, and the report carries BOTH bands at every invocation — the `SCOPES` precedent, so neither corner can be quoted alone.

<a id="the-claims-register"></a>

**THE CLAIMS REGISTER — CLAUDE.md's CHECKABLE ASSERTIONS ARE NOW CHECKED** (2026-08-29, `tests/test_claims_register.py`, 23 tests). Eight live claims in this file carry a predicate against the code: the two partition defaults, the empty ecological domain, provenance 292/292, the shadow ratchet at 33, GUF as its own revenue line, the remote-end zero, and the clipped conservation credit.
- **THE FAILURE IT TARGETS HAPPENED EIGHT TIMES IN TWO WEEKS, and never as a wrong number** — always a RIGHT number that stopped being right and was never revisited. Three stale `STILL OPEN` lines at the merge review; five retracted claims still shipping in docstrings and runtime verdicts. `land_stewardship` printed "BELOW the anchor" for **eleven days** after this file recorded it as 223× ABOVE.
- **IT IS THE DATASET-GOVERNANCE PATTERN APPLIED TO THE FILE A NEW SESSION READS FIRST.** That gate fingerprints a dataset's stated method so a regenerated file breaks the build until the constants are re-checked, on the recorded principle that *"a review that cannot go stale is not a control."* Same shape here: a claim whose anchor text is edited FAILS rather than silently passing, which forces the re-check.
- **THE HISTORICAL RECORD IS DELIBERATELY NOT CHECKED, and that distinction is load-bearing.** `shadow 57 → 46 → 38` are three correct historical entries; a naive "every number must match live" gate would fire on all three, get suppressed within a week, and leave the repo worse than before. Only claims of a declared shape are checked.
- **THE OPEN-ITEM DISCIPLINE IS THE HALF THAT CATCHES NEW DRIFT.** An item is either struck through (closed, kept visible so the shape stays legible) or declared with **what would settle it**. A third state — open, unlisted, quietly false — is what the gate forbids, and it is exactly the state all three stale lines were in. Only **THE TEN RATIOS** is genuinely open now.
- **THE GATE STATES ITS OWN GAPS AND FAILS IF THAT ADMISSION IS EDITED OUT.** It does NOT check the suite's own test count or mypy's file count — counting passing tests from inside the suite is circular — and those are the two figures most likely to drift. Saying so is the repo's own rule: an undocumented gap makes a checker read as stronger than it is. Five mutations verified to bite, including the removal of that admission.

<a id="branch-merge-ready"></a>

**BRANCH `fix/findings-and-domain-balance` IS MERGE-READY** (2026-08-29): 24 commits, a clean fast-forward onto main, nothing uncommitted. **Verified by re-running every gate AND both mutation surfaces**: 3,363 tests, mypy clean on 82 files, provenance 292/292 with no scheme violations, shadow ratchet at 33, baseline flow trace clean, 35/35 scenarios dispatch, and the documented intake path runs from a clean import outside the repo. **`data.py`: 0 of 254 scalars unpinned. Shadow: 9 of 38, the same nine as before the work, all deliberate** (3 numerics-only tolerances, 4 form-pinned placeholders, 2 archetype constants pinned relationally). Six spot-check mutations against this branch's own guarantees all bite, including 15 tests each for silently reverting Phase 4e or 4f.
- **THE MERGE REVIEW FOUND THREE STALE `STILL OPEN` LINES IN THIS FILE, and they are the pattern this repo keeps catching.** The GUF two-call pattern (closed by the assembly point), Phase 4e (adopted the following day), and "23 of the 34" shadow constants (every named item done in batches 2–3). Each was true when written; none was revisited when the work landed. **Struck through rather than deleted**, so the shape stays visible: a status note outliving the decision it describes is the same failure as a docstring outliving its defect, and this file is the one a new session reads first.
- **STILL GENUINELY OPEN, both needing the GUF asset intake**: the `retired` Ψ policy giving ε=0 the highest fee (a contradiction in the parcel inventory, not the multiplier), and the ten `GUF_USE_*` ratios (no occupational data is coded by the land use it serves).

<a id="test-suite-audited-pin-coverage"></a>

**THE TEST SUITE AUDITED AGAINST ITS OWN FAILURE MODES, AND THE PIN COVERAGE MEASURED** (2026-08-27). 3,220 tests pass, mypy clean on 81 files, shadow count held at 57. Four defects found and fixed, two of them in code written during the audit itself.
- **PIN COVERAGE MEASURED BY MUTATION, AND THE TWO GAPS COMPOUND EXACTLY.** Every scalar constant was perturbed +7% and the suite re-run: **0 of 232 `data.py` constants are unpinned. 34 of 63 SHADOW constants are.** So the surface the provenance gate cannot see is also the surface the tests do not hold — `data.py` is 100% tagged and 100% pinned; outside it, 0% tagged and 46% pinned. **Quote the pair, never the 100% alone.** (Method limit: scalars only — dicts like `LABOR_CATEGORY_DEFAULTS` are outside the sweep and were checked by hand; and "pinned" means a LEVEL move is detected, not that the right property is.)
- **AN ASSERTION CAN BE ENFORCED BY THE IMPLEMENTATION RATHER THAN BY THE CONSTANTS — failure mode 6 in an ORDINARY UNIT TEST, not a gate.** All three tests of `epoch_alpha_weights` asserted the coefficients sum to `ALPHA_SCALE`, are positive, and number four. Every one is an IDENTITY: `a / total * ALPHA_SCALE` makes the sum unconditional and `max(_ALPHA_FACTOR_MIN, a)` makes positivity unconditional. **Setting all eight α constants to absurd values (99, −7, −11 …) leaves the sum at exactly 5.0 and every weight positive at ε ∈ {0, 0.4, 0.99}, and all three tests still pass.** So eight of the 57 shadow constants — Workstream A's own epoch-adaptive assessment function — were pinned by nothing, along with all four shape claims in their docstring.
- **THE DELTA, RUN NOT ARGUED: invert `_ALPHA_TRAINING_SLOPE` so the training weight FALLS with automation — the exact reverse of the documented mechanism — and the three pre-existing tests all pass while the six new shape tests fail.** New `TestEpochAlphaWeightsShape` pins the four docstring claims as SHAPE (training and scarcity monotone rising, impact monotone falling, demand peaking in the INTERIOR near 0.40) plus the published example values, and asserts the dominant factor CHANGES across the arc — without which the ε argument is decorative. Verified to bite on five separate mutations. The docstring's own numbers were checked and are still exactly right; the code was never wrong, only unguarded.
- **THE LIVE PATH WAS ALREADY FINE, which is why this is a contained finding.** `epoch_alpha_weights` is deprecated in favour of the geometric map, and `test_reference_multiplier` DOES pin `epoch_factor_weights`' impact rise, its ε=0.40 anchor and its clamping. A deprecated function with unfalsifiable tests still deserves the fix: it is exported, it consumes eight named constants, and its passing tests were counted as coverage of them.
- **A TEST DOCUMENTING A DEFECT OUTLIVED THE DEFECT AND BECAME A TAUTOLOGY.** `TestTheAnchorIsKeyedToNothing::test_ecological_eoh_ignores_population_and_area` still read `# No area or population parameter exists to pass` — false since 2026-08-16 — and asserted `ecological_eoh(0.82) == ecological_eoh(0.82)`, which cannot fail for any deterministic function. It also restated `ECOLOGICAL_BASE_RATE` as the bare literal `500_000.0`, the shadow-literal pattern, inside the file documenting an anchor defect. Replaced with the two load-bearing properties: the no-area path resolves to the DECLARED frame (bound to the constant), and the with-area path is LINEAR in area — the extensive behaviour whose absence was the original defect.
- **THE PRICE FLOORS WERE UNPINNED AND THEY MOVE SHIPPED OUTPUT.** `GOODS_PRICE_FLOOR`, `SERVICES_PRICE_FLOOR` and `_SERVICES_PRICE_DECLINE_EXPONENT` are shadow constants in `core/prices.py`; +7% moved outputs and no test failed. Now pinned as asymptotic behaviour and ordering. **Writing them corrected my own misreading**: I first asserted services sits ON its floor by ε=0.99. It does not — the 0.35 exponent leaves it at **0.360, 1.8× its floor**, reaching 0.20 only as ε→1, while linear goods is on its floor already. *The two ratios reach their floors at completely different rates, and that difference IS the labour-bearing claim.* Pinning my assumption would have baked a misreading into the suite.
- **I REPRODUCED THE α DEFECT IN THE EXCHANGE LEDGER WHILE DIAGNOSING IT.** `balances_to_zero()` was an identity over `post()`: every `Entry` writes both legs, so 200 random postings with arbitrary accounts still sum to zero. `balances_to_zero` now also checks each entry HAS both legs — the realistic one-legged-posting bug — which is the part that can actually fail, and the docstring says which half is the identity.
- **A MUTATION SWEEP OF MY OWN MODULE FOUND TWO MORE.** `teh_per_capita` could drop `/ population` entirely and **all 57 tests passed** — because every collective being compared had the SAME population, so the division cancelled on both sides of the ratio. That is the ε=0.40 trap in a new place: measured at exactly the point where the defect is invisible. Closed by `TestParityIsScaleFree` (same intensity, 10× size → exact parity), which now catches it in 6 tests. `COASEAN_RESERVE_FRACTION` was likewise unpinned behind `0 < reserve < teh_created`.
- **AND A THRESHOLD THAT COULD NOT HELP FIRING — failure mode 5 INVERTED.** `settlement_report` compared the STANDING reserve against the ceiling: reserve is 0.10 of minted, ceiling was 0.50 × that = 0.05, so `breached` was **unconditionally true for every collective before a single trade**. The test asserted only that the KEYS existed, never a value. The imbalance is now the DEVIATION from the earmark, with tests for at-rest (not breached), a large transfer (breached) and a small one (not) — reachable in both directions.
- **GATES CHECKED AND FOUND SOUND**: `test_reference_data` globs `reference/` from disk and cross-checks the registered list, so it cannot fall behind again; `test_cli_dispatch` walks the registry and asserts it is non-empty and covered, so an empty registry cannot pass vacuously; `_DECLARED_EXEMPT` has no stale entries; `unused_innocuous_names` and `masked_constants` are both asserted. **Across 2,924 test functions: 3 with no assertion, 3 apparent tautologies (2 are legitimate `x == x` NaN checks), 1 broad tolerance.** The suite is in good shape; the gaps are concentrated exactly where the shadow constants are.
- **A METHOD HAZARD WORTH REMEMBERING: STALE BYTECODE SILENTLY FALSIFIED A BITE TEST.** Restoring a mutated module with `cp` did not reliably invalidate `__pycache__`, so `inspect.getsource` showed correct source while the LOADED code object was still the mutated one — `parity_rate` returned the inverse of what its own source said. It surfaced as a test that failed in the suite and passed alone. **Run mutation testing with `PYTHONDONTWRITEBYTECODE=1`**, and treat "passes alone, fails in suite" as a bytecode or state-leak question before a logic one. Also: `git status` cannot verify the restoration of an UNTRACKED file — it prints `??` whatever the contents.

