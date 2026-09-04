# Contestability and the Coasean layer

**Scope.** §§8.7–8.9c: the three-channel exit invariant, recalibration, the φ
policies, formation feedback, membership terms, the federation and the
exchange-accounting layer.

Migrated from `CLAUDE.md` § Current status on 2026-09-03. Entries are verbatim.

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
- **The federation total is not conserved across a transfer at any rate ≠ 1, and
  that is booked rather than engineered away** — each collective's TEH is its own
  unit of account, and the difference lands in a declared `fx_revaluation`
  account. At rate = 1 conservation holds exactly, and that is the test.
- **The N=1 anchor is exact**: `teh_created_delta == 0.0` against a direct
  single-ledger call. If that stops being exact, every N>1 result is measuring the
  scaffold rather than the model.

## Open

- **Underwriting governance** — who decides, and on what terms.
- **Supply-curve calibration** for `research/formation.py`'s linear private
  supply between `FORMATION_HURDLE_RATE_MIN` and `FORMATION_FULL_SUPPLY_RATE`.
- **Typed-capital integration** with `core/civilization.py`; intermediate
  priority policies between share-first and dividend-first are unbuilt.
- **The investment-disincentive feedback on K(ε) is not simulated**, and is
  flagged as such.
- **`utils/corridor_cmd.py --available-labor` still defaults to 1.0e9**, a
  retired work-year artefact. See [verification.md § Open](verification.md#open).

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

Newest first, verbatim as written. Anchors are stable — link to a specific entry
as `record/contestability.md#<slug>`.

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

