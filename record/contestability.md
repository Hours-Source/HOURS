# Contestability and the Coasean layer

**Scope.** §§8.7–8.9c: the three-channel exit invariant, recalibration, the φ
policies, formation feedback, membership terms, the federation and the
exchange-accounting layer.

---

## Live state

- **The adopted invariant is `exit_financing()`** — time-to-finance-exit within
  one vesting period, across three channels: labour at low ε, commons
  underwriting in the mid-arc trough, dividend savings at high ε.
  `trust_required_for_chi()` and `levy_schedule_for_chi()` are **SUPERSEDED** and
  kept as documented negative results.
- **Bare χ is superseded by §8.9.** `research/corridor.contestability_ceiling()`
  runs the three-channel test; the old form survives as
  `contestability_ceiling_bare_chi()` and `contestability_axes()` reports the
  disagreement. At defaults the corridor is **OPEN**; under `--bare-chi` it still
  closes, reproducing the earlier result on demand.
- **`phi_policy` defaults to `dilution`** — the commons' share attaches to NEW
  capital at commissioning, with a no-sale ratchet on private capital.
  `"target"` (purchase) and `"escalated"` stay reachable; escalation **never
  fires at canonical defaults**.
- **The doctrine trade-off REVERSED and nothing caught it.** §8.9b recorded
  dilution paying ≈13% *below* the purchase model; at current constants it pays
  ≈13% **above** — same magnitude, inverted sign, crossover moved from ε≈0.45 to
  ε≈0.05. The tests pinned the *φ* ordering, which never moved, and nothing
  pinned the *dividend* ordering, which is what the doctrine argument turns on.
  Now pinned as the SIGN; levels are calibration and will move again.
  **Re-run `recalibrated_arc(phi_policy=...)` before citing any level.**
- **Zero interest is what makes the charter affordable, quantified**: s\* = 0.50
  under Condition III against ≈0.10 fiat-like; a fiat world must drive the
  dividend to zero mid-arc to hold the canonical pace.
- **Holdings are conserved across a transfer at rate 1 and move by the
  revaluation otherwise** — booked, not engineered away. False before 2026-09-30
  and untested ([settled-through-the-book](#settled-through-the-book)).
- **The federation SETTLES on `registered_rate`** (author, 2026-09-30) — m_b/m_a,
  capture-neutral, band-bounded only while both sides honour Condition II; the
  floor is reported beside it, never applied. `basis="parity"` reproduces
  pre-adoption figures. [base-adopted](#base-adopted).
- **The N=1 anchor is exact**: `teh_created_delta == 0.0` against a direct
  single-ledger call. If that stops being exact, every N>1 result is measuring the
  scaffold rather than the model.

## Open

- **~~Parity REWARDS register capture; WHICH BASE replaces it is the author's~~
  — SETTLED 2026-09-30** *(pointer)* (author decision): **registered settles,
  the floor is reported beside it as purchasing power.** `parity_rate` kept as
  the superseded form. See [contestability.md § base-adopted](#base-adopted).
- **What disciplines a deficit beyond reserve under base settlement** *(person)* —
  `settlement_check` depreciates the debtor's rate, and §5 forbids any non-base
  rate crossing a boundary as a settlement price. Nothing APPLIES the factor
  today (it is reported only), so nothing violates §5. *Settles by:* the author
  choosing a standing claim in the book, suspension, or the factor as a signal
  only — and the answer may retire `COASEAN_DEPRECIATION_SLOPE`.
- **~~Which ε the floor reading uses~~ — SETTLED 2026-09-30** *(pointer)*:
  observed. See
  [fulfilment.md § floor-reads-observed-epsilon](fulfilment.md#floor-reads-observed-epsilon).
- **On the shipped constructor the federation is at mutual recognition** *(caveat)* —
  one multiplier, every settlement rate 1.0; regime 2 is Condition II divergence
  only (`multiplier_schedule` is the lever). No measured cross-collective
  multiplier differences exist in the repo.
- **~~The Condition II correction rule~~ — SETTLED 2026-09-30** *(pointer)*:
  off the top. Unsynchronised recalibration is still regime-2 movement. See
  [fulfilment.md § registered-work-access](fulfilment.md#registered-work-access).
- **Underwriting governance** *(person)* — who decides, and on what terms.
- **Supply-curve calibration** *(gap)* for `research/formation.py`'s linear private
  supply between `FORMATION_HURDLE_RATE_MIN` and `FORMATION_FULL_SUPPLY_RATE`.
- **Typed-capital integration** *(gap)* with `core/civilization.py`; intermediate
  priority policies between share-first and dividend-first are unbuilt.
- **The investment-disincentive feedback on K(ε) is not simulated** *(gap)*, and is
  flagged as such.
- **~~`utils/corridor_cmd.py --available-labor` defaults to 1.0e9~~ — SETTLED
  2026-09-04** *(pointer)* (bound to the feasibility frame). See
  [verification.md § Open](verification.md#open).

## Cross-area entries

| Entry | Also | Why |
|---|---|---|
| [frame-seam-closed-exchange-layer](#frame-seam-closed-exchange-layer) | [ecological](ecological.md#live-state), [verification](verification.md#live-state) | The sixth frame-seam instance sat on the documented intake path, and the gate could not see it because it was keyed to the primitive rather than the wrapper |
| [section-8-9c-formation-feedback](#section-8-9c-formation-feedback) | [fulfilment](fulfilment.md#live-state) | Closes the K(ε) circularity — ε derived from realized capacity rather than supplied |

**A degeneracy worth knowing.** `make_federation`'s only heterogeneity lever was
`ecosystem_health`, and after Phases 4e/4f collectives differing only in health
are IDENTICAL in the ledger. The constructor now takes a `capital_schedule`,
which moves per-capita output directly and produces real terms of trade. This is
the domain-balance defect seen from the exchange layer — see
[ecological.md § History](ecological.md#history).

---

## History

<!-- record-index: generated by utils/record_index.py, do not hand-edit -->

| 10 entries, newest first | |
|---|---|
| [base-adopted](#base-adopted) | REGISTERED SETTLES, THE FLOOR IS READ BESIDE IT — AND THE FEDERATION IS NOW AT MUTUAL RECOGNITI… |
| [settled-through-the-book](#settled-through-the-book) | REGISTERED AND FLOOR RUN THROUGH THE BOOK — AND THE BOOK'S TRANSFER CREATED MONEY ON EVERY LEG |
| [settlement-base-candidates](#settlement-base-candidates) | SETTLING PER TEH DISCIPLINES CAPTURE AND DOES NOT BOUND THE CROSS-RATE; THE BASES THAT ARE BOUN… |
| [register-federation](#register-federation) | CAPTURE IN ONE COLLECTIVE IS REWARDED BY THE FEDERATION, NOT DISCIPLINED BY IT |
| [frame-seam-closed-exchange-layer](#frame-seam-closed-exchange-layer) | THE FRAME SEAM CLOSED ON THE INTAKE PATH, AND THE EXCHANGE-ACCOUNTING LAYER STARTED |
| [federation-contestability-closure](#federation-contestability-closure) | Federation contestability closure implemented |
| [section-8-8-closure-mechanisms](#section-8-8-closure-mechanisms) | §8.8 closure mechanisms built, pending author sign-off |
| [section-8-9-recalibration](#section-8-9-recalibration) | §8.9 recalibration prototype built |
| [section-8-9b-charter-formation](#section-8-9b-charter-formation) | §8.9b charter-formation doctrine built |
| [section-8-9c-formation-feedback](#section-8-9c-formation-feedback) | §8.9c formation feedback built |

<!-- /record-index -->
Newest first, verbatim as written. Anchors are stable — link to a specific entry
as `record/contestability.md#<slug>`.

<a id="base-adopted"></a>

**REGISTERED SETTLES, THE FLOOR IS READ BESIDE IT — AND THE FEDERATION IS NOW AT MUTUAL RECOGNITION UNTIL MULTIPLIERS DIFFER** (2026-09-30, author decision, AWol: "registered settles and floor is reported beside it as purchasing power until something requires us to back track"). `research/exchange.py` (`registered_rate`, `settlement_terms`, `settlement_matrix`, `SETTLEMENT_BAND_BOUNDS`), `research/coasean.py` (`exchange_rates(basis=)`, `RATE_BASES`, `make_federation(multiplier_schedule=)`, `run_collective_period(mean_multiplier=)`, `simulate_federation(rate_basis=)`), `research/register_federation.py` (`settlement_response`), `utils/coasean_cmd.py` (`--rate-basis`).
- **DEFAULT FLIPPED, PARITY KEPT REACHABLE** — the `per_component`/`uniform` and `dilution`/`target` precedent. Blast radius measured before the flip: six coasean tests pinned parity as the federation's rate. Each was READ: all asserted that capital (or health) heterogeneity produces non-unity rates and non-zero inter-inflation, which is structurally false under registered — every collective inherits one multiplier. They now pin parity explicitly, and registered counterparts pin the adopted behaviour: capital drift moves no settlement rate; multiplier drift does, by exactly the ratio.
- **THE CONSTRUCTOR DEGENERACY, ONE LEVER OVER.** `make_federation` could not make the adopted basis say anything, as it once could not make parity move with health. `multiplier_schedule` is the lever; unsupplied, `run_collective_period` passes `MEAN_MULTIPLIER_REFERENCE` — the pipeline's own default, bound by name — so the N=1 anchor is byte-identical.
- **A DISCOVERY PREMIUM IS REFUSED ON THE SETTLEMENT BASIS** (§5), not applied-and-reported (mode 10). The premium seam survives under `basis="parity"`, where it lived.
- **ONE FORMULA, THREE PLACES** — `exchange.registered_rate` is canonical; `coasean.exchange_rates` calls it; `settlement_base`'s `registered` candidate cannot import it without a cycle and is bound to it by test (mode 4). The floor reading in `settlement_terms` is bound to `settlement_base`'s `floor` the same way — which caught an inverted ratio in my first draft (floor(ε_a)/floor(ε_b) instead of floor(ε_b)/floor(ε_a)) before it shipped.
- **PROSE RETIRED:** `coasean`'s module docstring and `three_regime_inflation`'s regime 2 said "an over-issuing collective sees its unit depreciate". On the adopted basis: through the multiplier it depreciates; through the register it is neutral; capital and ε do not move it. `register_federation` now opens with a status note — its finding is about parity, which still rewards capture, and is kept as the documented defect. CLAUDE.md §5's "currently prices parity … currently REWARDS capture" struck and dated.
- **SURFACED, NOT DECIDED:** `settlement_check`'s depreciation factor, if ever applied, would be a non-base rate crossing a boundary. Nothing applies it; the question of what disciplines a deficit under base settlement is now [open](#open) and may retire `COASEAN_DEPRECIATION_SLOPE`.
- **PLACEHOLDERS TOUCHED, NONE RETIRED, AND WHY.** Five placeholders are on this path: `COASEAN_RESERVE_FRACTION`, `COASEAN_IMBALANCE_CEILING`, `COASEAN_DEPRECIATION_SLOPE`, `GOODS_PRICE_FLOOR`, `SERVICES_PRICE_FLOOR`. None was low-hanging by the test "the `resolves_by` points at something already in the repo": the price floors name input-output non-labour shares and the repo's BEA data is fixed assets only; the reserve and ceiling name clearing-union practice (the EPU is cited), and no clearing-union data is in the repo — whether the EPU's quota is even the same quantity as a fraction of a reserve has to be read from the source before anything is bound to it (mode 8), which makes it a lead, not low-hanging; the slope's mechanism is now in question, above.

<a id="settled-through-the-book"></a>

**REGISTERED AND FLOOR RUN THROUGH THE BOOK — AND THE BOOK'S TRANSFER CREATED MONEY ON EVERY LEG** (2026-09-30, author: "stick with registered and floor as the main focus"). `research/settlement_base.py` (registered/floor section), `research/exchange.py` (`FederationBook.transfer` sender leg, `Ledger.EXTERNAL`, `Ledger.holdings`), `tests/test_settlement_base.py` (+31), `tests/test_exchange.py` (+2, one rewritten). 5,049 pass (1 skipped), mypy clean on 103 files. Read as FOCUS, not adoption: `parity_rate` unchanged.
- **THE DEFECT, FOUND BY RUNNING CAPTURE THROUGH THE BOOK.** `FederationBook.transfer` posted the sender leg reserve → the sender's OWN circulation. What was sent abroad stayed spendable at home while the receiver also gained it: **every transfer created holdings, at every rate including 1.** The live-state claim "at rate = 1 conservation holds exactly, and that is the test" was false, and its test could not fail — it summed `money_supply()` (issuance net of destruction), which no transfer posting touches, so it passed at rate 1.5 as well (verified). Mode 2 and mode 12 together. Now the sender leg posts to a declared `external_settlement` contra-account, a `holdings()` method gives the quantity a transfer actually moves, and the rewritten test plus two new ones fail 3/3 if the old leg is restored.
- **AND A MISLABEL, DOCUMENTED RATHER THAN RENAMED.** The docstring said `fx_revaluation` held amount·(rate−1); the account holds the receiver's whole inflow, −amount·rate, and `test_exchange` pinned −1500 for a 1000 @ 1.5 transfer while the docstring promised 500. The name is kept (the report and its tests read it); the docstring now says what it holds, and the revaluation proper is the returned `fx`. Mode 10.
- **REGISTERED'S BOUND IS THE BAND'S, AND CONDITIONAL.** r = m_b/m_a lies in **[0.857, 1.167]** = [M_BAND_LOW/M_BAND_HIGH, M_BAND_HIGH/M_BAND_LOW] only when both collectives honour Condition II — and `build_collective` enforces nothing; any multiplier mints. `registered_settlement` runs `condition_ii_check` on both sides and reports a breach beside the rate, never clamps. The check reads m, not the rate: two collectives equally above band settle at par. **At the shipped multiplier every registered rate is 1.0 — that IS mutual recognition,** the regime [register-federation](#register-federation) recorded as reporting nothing whatever happens in any register. Across the five `reference/workforce.py` compositions — ILLUSTRATIVE band positions, not measurements (mode 8) — **three are out of band, and the third is the finding: `high_epsilon`, written as the NATURAL high-ε workforce (base tier automated away), sits at ≈2.22 with nobody gaming anything.** If registered settles, high-ε members are flagged by their skill mix and the bound fails where the arc is heading. 12 of the 18 breach pairs leave the bound. (In-band pairs staying inside it is algebra, not a result, and is not cited as one.)
- **THE FLOOR READS THE SUPPLIED ε, AND THAT IS A SEAM.** Every `floor_price`/`basket_price` call in `core/` and `scenarios/` passes the capability index a collective STATES; the physical machine share is the OBSERVED ε, strictly lower away from zero because care resists automation. On the observed ε the floor's high-ε advantage over subsistence falls from **5.57× to 2.86×** at capability 0.99 (observed 0.861). `floor_observed` is carried as a seventh candidate, capture-neutral structurally. Which ε the floor price is a function of is repo-wide theory — handed over, not switched.
- **THE TWO COMPOSE AS A RATIO, NOT A PRODUCT.** `purchasing_gain` = floor rate / registered rate — baskets on the far side per basket the same hours bought at home; the product would be (TEH_b/TEH_a)². Clean because `floor_price` reads no multiplier (mode 11 checked). Bounded by band ratio × floor spread when both are in band.
- **THROUGH THE BOOK, CAPTURE:** under registered, floor and floor_observed the honest collective receives exactly what was sent and federation holdings are conserved to zero at every key ε; under parity holdings grow by exactly sent·(r−1), and at subsistence a transfer of half the smaller ceiling pushes the honest RECEIVER past its ceiling. A first version sent the capturer's own ceiling and breached the receiver at rate 1 — capture enlarges the capturer's reserve, and each ceiling is a fraction of its own — so that breach said nothing about the rate and was dropped.
- **MUTATIONS:** floor_observed → supplied ε (4 fail), band check → rate bound (1), sender leg restored (8), gain → product (1).
- **WHAT THE AUTHOR DECIDES:** registered or floor as THE settlement price, or registered as settlement with floor as the purchasing-power reading beside it; for floor, supplied or observed ε; for registered, whether mutual recognition at a common multiplier is acceptable, and whether a band breach suspends settlement or only reports — given the natural high-ε composition breaches it. (The book test that neutral bases do not breach cannot fail at rate 1 with a half-ceiling transfer; the parity half is the evidence.)

<a id="settlement-base-candidates"></a>

**SETTLING PER TEH DISCIPLINES CAPTURE AND DOES NOT BOUND THE CROSS-RATE; THE BASES THAT ARE BOUNDED ARE BLIND TO ISSUANCE** (2026-09-30). `research/settlement_base.py` + `tests/test_settlement_base.py`, 79 tests. 5,016 pass (1 skipped), mypy clean on 103 files. **REPORTING ONLY; `parity_rate` UNCHANGED** — `test_register_federation` is the retire-signal and must fire only once a base is chosen. Awaiting the author's choice of base.
- **THE QUESTION §5 LEAVES OPEN.** The rule says settle on the obligation-anchored base and names the failure — *a base EOH here is your entire collective there* — but not the equation. Six backings compared, rate = backing(a)/backing(b): `parity` (mint per person, the current form; ≡ `exchange.parity_rate`, pinned), `obligation` (total EOH per TEH), `human` (human-served EOH per TEH), `registered` (= 1/m), `floor` (baskets per TEH at `floor_price(ε)`), `obligation_parity` (total EOH per PERSON — §5 read literally, not a per-TEH backing).
- **CAPTURE (ε=0.40, +5pp personal admission, obligation asserted identical):** parity **1.2724** rewarded; obligation and human **0.7859** disciplined — exactly 1/mint-ratio, proportional rather than punitive, at every reporting point; registered, floor and obligation_parity neutral. Parity's reward peaks at subsistence (3.48× at ε=0) where the register is nearly empty.
- **BUT THE PER-TEH BASES DO NOT BOUND THE ARC.** Max cross-rate over all ε-pairs on a 101-point grid, fixed 0.40 frame / canonical arc: parity **15.3 / 29.2**, obligation **12.2 / 21.2**, human **46.0 / 79.0**, floor 5.57 / 5.53, obligation_parity **1.53 / 1.72**, registered 1.0. The obligation base does not shrink parity's spread by an order — it REVERSES it: the subsistence collective's unit becomes the hard one (strong side at ε≈0.72, between reporting points; reading it off the six `ARC_REPORTING_POINTS` understates it only 0.6% here, parity's by 3.8%).
- **§5's "BECAUSE", EVALUATED (mode 13).** *Floor bounded by obligation, obligation bounded by population, SO the cross-rate is bounded.* Per-capita obligation spans only **1.72×** across the whole arc — the premise holds, and the SO **holds for any base that reads the obligation or the floor directly** (`obligation_parity` 1.72×, `floor` 5.5×). It **fails for any base converted through the mint**: TEH-per-EOH spans **21.2×**, driven by a registration share spanning **79×** and partly offset by the human fraction (7.5×). Any base converted through the mint inherits the register's arc. (The obligation base's max rate IS the mint-per-EOH spread by definition — the decomposition adds the two factors behind it, not a second test.)
- **THE TRADE-OFF, AND THE FORK.** The only bounded base that sees the collective, `obligation_parity`, is capture-neutral STRUCTURALLY (`total_eoh` takes no registration parameter) — and blind to issuance: a multiplier 10% above the shipped one settles at exactly 1.0, where every per-TEH base depreciates it to 0.909 and parity rewards it 1.10. Separately, `obligation` vs `human` is the question *does machine-fulfilled obligation back a TEH?* — at ε=0.90 a 4×-capital collective settles at 1.0588 under one and 0.9896 under the other, opposite sides of par. Both pinned; neither chosen. A base measured against the published registration schedule at the collective's own ε would separate discipline from boundedness, but settles against a policy curve rather than physics — named, not built.
- **TWO PASSES ARE IDENTITIES AND ARE FLAGGED AS SUCH (mode 2).** `registered` is 1.0 for any two collectives at the shipped multiplier, so it is informative only in `multiplier_response`; `floor` reads ε and nothing else. `BY_CONSTRUCTION` travels in the output. A third near-miss was caught while building: the natural acquisition "discount" (cost at r=1 over cost at r) is identically r — dropped, and a test keeps it dropped.
- **THE LAND PROBE IS INERT ON THE SHIPPED PATH.** 3× land per person moves no base because ecological EOH is 0.0 everywhere shipped ([ecological](ecological.md#live-state)); pinned as a property of the current calibration that should fail if the level is resolved. 10× population at fixed intensity moves none, to 1e-12.
- **VERIFIED BY BREAKING IT.** Five mutations, each confirmed present in the loaded source, run with `PYTHONDONTWRITEBYTECODE=1`: obligation→registered (15 fail), obligation_parity→mint (9), search grid→reporting points (4), neutral verdict loosened (4), human→total (**0 — survived**; the fork test was added and it now fails 2).
- **WHAT IT DOES NOT ESTABLISH:** that any base clears a real trade (no goods layer); anything about actors; a threshold for "your entire collective" — the report gives rate spread and years-of-mint, and where that becomes the §5 failure is the author's reading.

<a id="register-federation"></a>

**CAPTURE IN ONE COLLECTIVE IS REWARDED BY THE FEDERATION, NOT DISCIPLINED BY IT** (2026-09-09). `research/register_federation.py` + `tests/test_register_federation.py`, 12 tests. 4,380 pass, mypy clean on 101 files. **REPORTING ONLY.** Answers outline item 8 of the register-governance front.
- **THE ARCHITECTURE ADVERTISES THE OPPOSITE, AND ONE OF ITS TWO MECHANISMS DELIVERS IT.** `three_regime_inflation` states *"an over-issuing collective sees its unit depreciate against its neighbors"* — transition inflation carried honestly as an exchange-rate movement. That is true of `settlement_check` and **false of parity**, and the prose does not distinguish them.
- **PARITY HAS NO REAL-OUTPUT TERM, SO OVER-ISSUANCE AND PRODUCTIVITY ARE THE SAME OBSERVATION.** `productivity(c) = teh_created(c)/population(c)`. Two collectives identical in frame, ε and physical state, one admitting 5pp more of its personal obligation: the obligation is **identical** and the capturing unit **appreciates 1.2724×**. It scales with the capture and reverses for under-registration, so the defect is symmetric — a register that admits too little is penalised the same way.
- **THE DISCIPLINE IS REAL BUT NOT AUTOMATIC, because it engages through a channel domestic capture does not use.** `settlement_check` depreciates a debtor past its credit ceiling, and offsets the parity gain only past a bilateral deficit around **2× the reserve** (1.5× still leaves the capturer ahead at 1.0604). **Inside the ceiling the factor is exactly 1.0** — and a register captured to admit its own population's obligation mints TEH earned and spent at home, so it need run no deficit at all.
- **BOTH RECOGNITION REGIMES COST SOMETHING AND NEITHER IS RECOMMENDED.** Mutual recognition: one unit, no pairwise rate, **the exchange layer reports nothing whatever happens in any register** and every holder is diluted. No recognition: visible in principle, but what parity shows is the capturer looking MORE productive. **Visibility is not discipline.**
- **THE FINDING RETIRES ITSELF IF IT STOPS BEING TRUE.** Mutating parity so it no longer reads minted TEH fails seven of the twelve tests, including the one that asserts capture is rewarded — so if a real-output term is ever added, the suite says so rather than the claim outliving its truth.
- **WHAT IT DOES NOT ESTABLISH:** that any federation has done this (no actor, incentive or defection is modelled); that `settlement_check` is miscalibrated (its form is explicitly proposed, and the crossing moves with the slope); or that federation is a mistake — no-recognition remains the only regime where capture is visible at all.

<a id="frame-seam-closed-exchange-layer"></a>

**THE FRAME SEAM CLOSED ON THE INTAKE PATH, AND THE EXCHANGE-ACCOUNTING LAYER STARTED** (2026-08-21, readiness audit). `hours_eoh/research/exchange.py` + `tests/test_exchange.py` (57 tests) + frame plumbing in `core/fiscal.fiscal_snapshot` and `core/dashboard.system_dashboard`. Shadow constants held at 57; the new module introduces no constant outside `data.py`.
- **THE SIXTH INSTANCE OF THE FRAME DEFECT WAS SITTING ON THE DOCUMENTED INSTITUTIONAL INTAKE PATH.** `implementation_guide.md` tells an institution to run `eoh_to_teh_pipeline()` **and** `fiscal_snapshot()`. The pipeline resolved the ecological area from population (Phase 4b); `fiscal_snapshot` took its requirement from `ECOLOGICAL_BASE_RATE` — the whole contiguous US — whatever population it was passed. **The guide's own copy-paste example, run verbatim, disagreed with itself by 92.8×** (pipeline 8.29e3 vs fiscal 7.69e5) and reported `solvent: True` either way. At a 5M-person frame the overstatement of `teh_required` is 63.8×.
- **THE GATE COULD NOT SEE IT BECAUSE IT WAS KEYED TO THE BOTTOM OF THE CHAIN.** `test_ecological_scale_resolution` matched calls named `ecological_eoh*`/`ecological_scale` inside functions with a `population` param. `fiscal_snapshot` reaches the anchor through `ecological_allocation`, a wrapper with **neither**. THE LESSON: *a gate keyed to the primitive does not see a caller that enters the chain one wrapper up.* `ecological_allocation` is now in `_SCALE_CALLS`.
- **MY FIRST FIX TO THE GATE MADE IT GREEN AGAINST THE VERY DEFECT IT WAS BEING EXTENDED FOR.** I added `eco_eoh_override` to `_FRAME_KWARGS` — but callers pass it as `eco_eoh_override=eco_eoh_override`, a pass-through whose value is normally `None`, so the kwarg's **presence** discharged the rule. Reintroducing the defect left the gate passing. **Presence of a parameter is not the parameter being in force** — the same shape as `psi` vs `psi_applied`, and as shape-without-a-declared-label in the baseline gate. Caught only by running the bite test, which is why the bite test is not optional.
- **BLAST RADIUS WAS EXACTLY ONE TEST, AND IT WAS A KNOWN-STALE CLAIM.** `test_thermal_load.test_carrying_the_obligation_reduces_coverage` still carried the **3.5** that `test_thermal_solvency` had already corrected to ~1,626× on 2026-08-17 — same cause, same stale figure, sibling not updated. Framed consistently it is **~1,162×**; now asserted as an ORDER OF MAGNITUDE, since pinning the level is what let the stale 3.5 survive its own correction.
- **`ecological_allocation` KEEPS THE US ANCHOR WHEN CALLED DIRECTLY, and that is pinned.** It has no population in scope, so the declared reference frame is right for it; `base_rate` became `None`-able so area is reachable without moving any existing caller, and **passing both RAISES** (the `total_eoh` precedent).
- **THE EXCHANGE MECHANISM WAS NEVER BROKEN — ITS CONSTRUCTOR COULD NOT DRIVE IT.** `make_federation` exposes one heterogeneity lever, `ecosystem_health_schedule`, and that routes through a domain worth **0.00017%** of total EOH: across the entire plausible health range (0.40→0.95) rates span **1.3e-5 at ε=0.20, falling to 2.5e-6 at ε=0.70** — parity to five decimals. Build collectives differing in CAPITAL and the same parity equation gives **0.67–1.49**. So this is the domain-balance defect seen from the exchange layer, and it is a constructor limitation, not a broken price signal. Both directions are pinned, the degenerate one explicitly as a property of the CURRENT calibration that should fail if the ecological level is ever resolved.
- **`CollectiveFrame` HAS NO DEFAULT LAND AREA.** A default would reintroduce the unstated pairing the class exists to refuse; `per_capita_land()` makes the ratio assumption a visible call. `build_collective` **refuses** kwargs that restate a frame quantity — a frame that can be overridden piecemeal is not a frame — and passes the ecological obligation from pipeline to fiscal **by value**, so the two entry points cannot diverge at all.
- **THE FEDERATION TOTAL IS NOT CONSERVED ACROSS A TRANSFER AT ANY RATE ≠ 1, AND THAT IS BOOKED RATHER THAN ENGINEERED AWAY.** Each collective's TEH is its own unit of account, so each ledger balances independently and the difference lands in a declared `fx_revaluation` account. Forcing aggregate conservation would assert a single currency while claiming to model several. At rate = 1 conservation holds exactly, and that is the test.
- **THE N=1 ANCHOR IS EXACT: `teh_created_delta == 0.0`** against a direct single-ledger call, at every arc point and at a foreign frame. If it ever stops being exact, every N>1 result is measuring the scaffold rather than the model.
- **STALE COUNTS REFRESHED**: "229 constants" (×4 across the guide and the provenance doc) → **265**; README "2,608 tests" → current. CLAUDE.md's own status did not mention the **`instance` tag** (12 constants) at all — it is the institutional-intake concept in the repo and was undersold.

<a id="federation-contestability-closure"></a>

**Federation contestability closure implemented** (reconciliation §8.7 addendum, decided and built 2026-07-10): two-tier Trust — `simulate_federation(commons=True)` tracks a federation commons (levy tithe + consolidation escheats) and per-collective per-period χ; `merge_collectives()`/`split_collective()` boundary events with indivisible-reserve escheat and TEH-conservation postconditions; `portable_endowment_federated()`, `exit_value()`, `contestability_margin_federated()` in `research/contestability.py` (tenure is federation-wide); `research/membership.py` `MembershipTerms` + `contestability_audit()` (the §8.7e math/contract line); CLI `coasean simulate --dynamics --commons ...` and `contestability audit`. Honest adversarial findings at defaults (reported, not tuned): commons floor coverage is tiny at a 3% tithe; consolidation escheat drains per-collective dividends so the worst marginal χ worsens toward ε→1 while total τ holds.

<a id="section-8-8-closure-mechanisms"></a>

**§8.8 closure mechanisms built, pending author sign-off** (2026-07-17, 1595 tests): the Phase 4 findings answered research-tier behind default-off flags — M1 universal unvested commons dividend (`portable_endowment_federated(..., commons_balance)`, Alaska PF precedent; escheat becomes a stabilizer), M2 entry underwriting (`entry_underwriting()`, `commons_seed_required()`; combined invariant `exit_financeable ⇔ χ_marginal ≥ 1 OR entry_capacity ≥ 1`; holds at every period of the canonical adversarial arc with a seed of ~0.05% of the Trust base), M3 physically-consistent levy base (`machine_output_teh(ε)=ε·total_eoh`; the static base understates ~12× at high ε). `simulate_federation(commons_dividend=True)`, audit flags `commons_dividend`/`underwriting_policy`. Proposal + sign-off items in `notes/contestability-closure-proposal.md` — **gates the website language rewrite** (do not publish "χ ≥ 1 across the arc" unqualified). Honest remainders: χ_marginal alone stays CRIT at high ε (commons-financed, not self-financed exit); levy growth steps stay infeasible even under M3; piketty_ok still fails at the canonical run's 20% levy.

<a id="section-8-9-recalibration"></a>

**§8.9 recalibration prototype built** (2026-07-26, 1657 tests; adopted-in-principle by the author, formal doc edit pending): `research/recalibration.py` resolves the §8.8 honest remainders at root. RC4 fixed — time-to-finance-exit (`exit_financing()`, t_exit ≤ one vesting period) + accumulating §8.7b capital account (`capital_account_stock()`, Mondragon, zero-interest) replace the flow/stock χ; `trust_required_for_chi()`/`levy_schedule_for_chi()` marked SUPERSEDED (kept as documented negative results). Open-item-3 fixed — K(ε)=K₀+ν·Y(ε) (ν=Piketty β≈4) with the commons OWNING share φ(ε) (Meade social dividend): τ=φ≤1 and dτ/dε≥0 structural; piketty_ok's failure was the miscalibrated cash-Trust frame. Self-financing dropped as the test (author decision): three channels — labor (low ε, the floor feeds founders), commons underwriting (mid-arc trough ε≈0.2–0.55), dividend savings (high ε, D≈1,873 TEH/p·yr at 0.99 from measured machine output). `recalibrated_arc()`: financeable at every point, channel arcs labor→underwritten→self. New honest findings: acquisition infeasible from commons income for ε≲0.15 (initial endowment φ₀·K₀ carries it); endogenous g_priv turns negative past ε≈0.5 (the §8.2 commonization made visible). CLI `contestability recal`; §8.9 addendum in `notes/contestability-closure-proposal.md` with updated comms wording.

<a id="section-8-9b-charter-formation"></a>

**§8.9b charter-formation doctrine built** (2026-07-26, 1736 tests; doctrine bundle agreed with the author): `phi_policy` on `research/recalibration.py` — `"dilution"` (default doctrine: the commons' share attaches to NEW capital at commissioning, resource-license/Georgist model; `formation_share_required()` s(ε) ≈ 0.17 early, crossing 1 at ε≈0.48; private capital follows a no-sale ratchet), `"target"` (§8.9a purchase model, regression anchor), `"escalated"` (charter escalation: adversarial regime observed + capacity < `RECAL_ESCALATION_CAPACITY_FLOOR` → s=1 and capital-estate escheat → `RECAL_ESCALATION_ESTATE_SHARE`; latches; NEVER fires at canonical defaults). Generational conversion via `estate_conversion_flow()` (0.15 = `ESTATE_LEVY_FRACTION`, D5 extended to capital). `formation_levy_rate()`: the compensated bridge ≈ 1% of labor output, sunset by ε≈0.2. Honest findings: **φ under dilution caps BELOW the target and "φ→1" survives only asymptotically** (half-life ≈69 yr even at full escheat). **THE DOCTRINE TRADE-OFF REVERSED AND NOTHING CAUGHT IT (found 2026-08-15).** §8.9b recorded the cost of no-forced-sales as a dividend "≈13% below the purchase model" with a crossover at ε≈0.45. At current constants the crossover is at **ε≈0.05** and dilution pays MORE across essentially the whole arc: **D(0.99) 2,155 vs target's 1,906 — ≈13% ABOVE**, same magnitude, inverted sign. Mechanism unchanged and it was always in the note: target BUYS its share so acquisition consumes commons income before distribution (income 2.758e9 − 8.517e8 reinvestment), while dilution's share attaches to new capital at commissioning for free (2.155e9, nothing withheld). Target ends with the larger base (φ 0.987 vs 0.771) and the smaller payout. **"The price of never forcing a sale" is no longer paid in dividend — only in the capped φ.** Why it went unnoticed: the tests pinned the *φ* ordering, which never moved, and nothing pinned the *dividend* ordering, which is what the doctrine argument turns on. Now pinned by `TestPhiActual::test_dilution_pays_MORE_than_target_despite_the_smaller_share` (asserts the SIGN; levels are calibration and will move again). Re-run `recalibrated_arc(phi_policy=...)` before citing any level. Trough narrows to ε≈0.05–0.27, self-financing from ε≈0.30; invariant holds at every arc point under all three policies; investment-disincentive feedback on K(ε) not simulated (flagged). §8.9b addendum + comms wording in the proposal note.

<a id="section-8-9c-formation-feedback"></a>

**§8.9c formation feedback built** (2026-07-26, 1775 tests): `research/formation.py` closes the K(ε) circularity — formation is financed or doesn't happen (linear private supply between `FORMATION_HURDLE_RATE_MIN`/`FORMATION_FULL_SUPPLY_RATE`; s* = 1−r_full/r_gross = 0.50), commons co-funds from NET income (replacement correction: δ·T_K ≈ 20–24% dividend haircut, `commons_income_statement(net_of_replacement=True)`), ε derived from realized capacity. Null anchor (s≡0) reproduces canonical 47-yr pace. Verdicts (asserted): share-first holds canonical pace with ZERO delay but dividend pays (D≈113 vs static 302 at ε≈0.4; self-financing onset ε≈0.86 not 0.30 — do NOT quote the §8.9b onset); dividend-first crawls (ε≈0.60 at 120 yr, never completes); exit invariant holds every simulated year under both priorities and the fiat counterfactual (capacity doesn't depend on the dividend). CONDITION III FINDING: s* = 0.50 zero-interest vs ≈0.10 fiat-like; fiat world must drive the dividend to zero mid-arc to hold pace — zero interest is what makes the charter affordable, quantified. §8.9b funding hole (s=1 attracts no private funding → commons pays all cap-region formation) closed and visible. CLI `contestability formation`. §8.9c addendum + amended comms wording in proposal note. Open: typed-capital integration (civilization.py), supply-curve calibration, intermediate priority policies.

