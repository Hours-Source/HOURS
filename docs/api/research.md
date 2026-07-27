# Research (Experimental)

**Package:** `hours_eoh/research/`

!!! warning "Not stable API"
    The `research/` package is experimental territory. Functions here are re-exports from `core/` with explanatory context, or experimental implementations not yet ready for `scenarios/`. Do not import `research/` from `core/`, `land/`, or `scenarios/`.

---

## investment.py — Investment Optimization

Re-exports `rank_investment_candidates()` and `optimal_investment()` from `hours_eoh/core/eoh_dynamics.py` with additional research context.

```python
from hours_eoh.research.investment import rank_investment_candidates, optimal_investment
```

See [EOH Dynamics](core/dynamics.md#investment-ranking) for function documentation.

---

## writedown.py — Ecological Write-Down

Re-exports the §9 write-down functions from `hours_eoh/land/guf.py`.

```python
from hours_eoh.research.writedown import (
    rebuilding_surcharge,
    ground_use_fee_writedown,
    eoh_accumulation_warning,
)
```

**Architectural rationale:** The original eco-collapse-1 placeholder described TEH destruction analogous to D1 (capital write-down). Analysis showed this is architecturally wrong — TEH created for completed stewardship labor is legitimate; the labor happened. Ecological collapse does not retroactively invalidate it.

The correct mechanism is GUF-layer baseline reset + rebuilding surcharge:

- **Restoration pathway:** V_s baselines reset to recovery target. Revenue maintained.
- **Abandonment pathway:** Rebuilding surcharge R_b(p,ε) distributes replacement infrastructure cost across affected parcels.
- **Preventive signal:** `eoh_accumulation_warning()` triggers before collapse.

GUF revenue in all cases flows to the Trust's ecological allocation — funding the response without any TEH destruction event on the ledger.

See [GUF Framework §9](../theory/guf_framework.md#9-ecological-write-down-events-and-the-guf) and [Land — GUF Module](land.md#ecological-write-down-nlsa-9).

---

## contestability.py — Contestability Invariant (Workstream B)

Implements the contestability invariant χ(ε) = P(ε) / K_entry(ε) ≥ 1 from
`hours-reconciliation.md §8`. All functions are experimental — the regime
parameters are uncertain and the model uses population-average P rather than
individually tenure-vested endowments (see module docstring).

```python
from hours_eoh.research.contestability import (
    portable_endowment,
    entry_cost,
    contestability_margin,
    commonized_fraction,
    trust_capital_ratio,
    tau_gradient_check,
    min_levy_for_pi,
    chi_arc,
)
```

### `portable_endowment(epsilon, population, trust_balance) → dict`

Per-capita portable endowment P(ε) — the TEH a member can carry out if they exit
the collective. Two components: sufficiency guarantee (what the collective owes
them regardless) + Trust dividend per capita.

Returns keys: `p`, `guarantee_per_person`, `trust_dividend_per_capita`,
`capital_fulfilled_per_person`, `epsilon`.

### `entry_cost(epsilon, regime, k0, k_slope) → float`

Sunk cost of founding a viable alternative collective at automation level ε.

- **`increasing_returns`** (adversarial): `K_entry = K₀ × (1 + k_slope × ε)` — cost
  rises with ε as automated capital becomes more valuable and harder to replicate.
- **`replicable`** (optimistic): `K_entry = max(K₀ × (1 − k_slope × ε), floor × K₀)` —
  cost falls as replication technology improves.

### `contestability_margin(epsilon, population, trust_balance, regime, ...) → dict`

χ = P / K_entry. Returns `chi`, `p`, `k_entry`, `status` (OK/WARN/CRIT),
`passes` (bool), `regime`, `epsilon`, `guarantee_per_person`, `trust_dividend_per_capita`.

`status = "CRIT"` when χ < `CONTESTABILITY_CHI_CRIT` (1.0) — exit is notional.
`status = "WARN"` when χ < `CONTESTABILITY_CHI_WARN` (1.2) — χ is eroding.

### `commonized_fraction(epsilon) → float`

φ(ε) = `PHI_FLOOR + (1 − PHI_FLOOR) × ε^PHI_EXPONENT`. Fraction of automation
value held in common (via Trust). Must approach 1 as ε → 1 for the invariant to
hold in the long run. At ε=0.99: φ ≈ 0.997.

### `trust_capital_ratio(trust_balance, capital_stock) → float`

τ = T / K. The Piketty-inversion condition requires dτ/dε ≥ 0 — Trust must
grow at least as fast as private capital for the commonized fraction to rise.

### `tau_gradient_check(eps_lo, eps_hi, trust_lo, trust_hi, cap_lo, cap_hi) → dict`

Checks whether dτ/dε ≥ 0 between two arc points. Returns `dtau_deps`, `tau_lo`,
`tau_hi`, `passes`. A negative gradient means private capital is growing faster
than Trust — the Piketty failure mode.

### `min_levy_for_pi(epsilon, trust_balance, capital_stock, g_priv) → dict`

Minimum levy required to maintain dτ/dε ≥ 0 (the Piketty-inversion condition).
Returns `levy_required_teh`, `automated_output_teh`, `levy_as_fraction_of_automated_output`,
`feasible`, `epsilon`.

**The adversarial finding**: at canonical defaults, `levy_as_fraction_of_automated_output ≈ 21`
at ε=0.40. The required levy exceeds total automated output — commonization through
structural ownership (φ → 1) is necessary, not just redistribution via levy.
This is a theoretical finding, not a calibration error.

### `chi_arc(n_points, regime, population, trust_balance, capital_stock) → list[dict]`

Arc sweep of the contestability invariant. Returns one dict per ε point with keys:
`epsilon`, `p`, `k_entry`, `chi_population_avg`, `chi_marginal`, `phi`, `tau`,
`levy_fraction`, `levy_feasible`, `status`.

The `chi_population_avg` key name flags that this is a population-average estimate,
not individually tenure-vested; `chi_marginal` is the tenure-0 member's margin.

### `portable_endowment_individual(epsilon, tenure_years, ...) → dict`

Tenure-vested individual endowment: `P_ind = S + v(tenure)·D + savings`,
`v = min(1, tenure/vesting_years)`. Tenure is **federation** tenure (§8.7b) —
moving between collectives never resets the clock. The marginal member
(tenure 0, savings 0) holds the floor S only.

### `levy_schedule_for_chi(n_points, regime, ...) → list[dict]` / `trust_required_for_chi(...)`

The derived common-fund levy schedule: the Trust balance required at each ε to
hold χ ≥ target, and the per-step levy needed to fund it, with feasibility
against automated output.

### Two-tier (federation) functions — reconciliation §8.7

```python
from hours_eoh.research.contestability import (
    portable_endowment_federated,
    exit_value,
    contestability_margin_federated,
)
```

- **`portable_endowment_federated(epsilon, collective_trust, collective_population, federation_population, tenure_years, ...)`** —
  two-tier P: the sufficiency floor S is federation-guaranteed and never vests;
  the dividend claim is held against the member's own collective's trust.
  Identical to `portable_endowment_individual` when federation == collective.
- **`exit_value(guarantee_per_person, dividend_vested, savings, rate)`** —
  value commanded on exit across a collective boundary: the floor crosses at
  par (federation-denominated); only the capital account converts at the
  inter-collective exchange rate (§8.7 b+d).
- **`contestability_margin_federated(epsilon, collective_trust, collective_population, ..., commons_balance)`** —
  per-collective χ and χ_marginal under the two-tier P; same status thresholds
  and key shape as `contestability_margin`. With `commons_balance > 0` the
  §8.8 closure applies: χ_marginal includes the universal commons dividend,
  and the result carries `entry_capacity` and `exit_financeable`.

### Closure mechanisms — proposed §8.8 (pending author sign-off)

The Phase 4 adversarial findings (escheat drains dividends; the marginal
member's χ is unclosable by any levy) are answered by three mechanisms:

```python
from hours_eoh.research.contestability import (
    entry_underwriting, commons_seed_required, machine_output_teh,
)
```

- **M1 — universal commons dividend**: `portable_endowment_federated(...,
  commons_balance=C)` adds `D_fed = C·DEP_RATE·DIV_RATE/fed_pop` to P
  **unvested** (Alaska Permanent Fund precedent). Escheat then converts
  tenure-gated collective dividends into universal ones — the §8.7c escheat
  becomes a stabilizer instead of a drain.
- **M2 — entry underwriting**: `entry_underwriting(epsilon, commons_balance,
  regime, ...)` — the commons capitalizes new collectives' trusts (capital
  stays commonized; §8.7c respected). `entry_capacity = deployable /
  (min_viable_pop · K_entry)`; the **combined invariant** is
  `exit_financeable ⇔ χ_marginal ≥ 1 OR entry_capacity ≥ 1` (self-financed
  exit at low ε, commons-financed entry at high ε — Baumol's threat made
  credible). `commons_seed_required()` (≈1.8e7 TEH, ~0.05% of the Trust base)
  closes the ε≈0 window before escheat inflows begin.
- **M3 — physically-consistent levy base**:
  `levy_schedule_for_chi(..., levy_base="machine_output")` uses
  `machine_output_teh(ε) = ε·total_eoh(ε)` — the pipeline's own measure of
  automated production — instead of the static `ε·K·yield` base, which
  understates it ~12× at high ε. The growth steps of the schedule remain
  honestly infeasible; M3 removes the calibration artifact, it does not
  manufacture feasibility.

**CLI access**: `eoh contestability arc`, `stress`, `levy [--levy-base]`, and
`audit [--commons-dividend --underwriting-policy]`.
**Dashboard integration**: `eoh dashboard` shows χ with color-coded PASS/FAIL.

---

## recalibration.py — Recalibration Prototype (proposed §8.9 / §8.9b)

Resolves the three §8.8 "honest remainders" at their causes rather than tuning
their symptoms, and encodes the §8.9b charter-formation doctrine. Both
adopted-in-principle by the author 2026-07-26; formal reconciliation-doc edit
pending.

```python
from hours_eoh.research.recalibration import (
    capital_stock_epsilon, phi_actual, commons_capital,
    formation_share_required, formation_levy_rate, commons_income_statement,
    capital_account_stock, estate_conversion_flow, escalation_trigger,
    exit_financing, recalibrated_arc,
)
```

**`phi_policy` — the §8.9b doctrine switch** (on every share-dependent
function; default `"dilution"`):

- **`"dilution"` (doctrine)** — charter formation: the commons' share attaches
  to NEW capital at commissioning (`formation_share_required()` gives s(ε):
  ≈ 0.17 early, crossing 1 at ε ≈ 0.48); nothing is purchased, the dividend is
  the full φ·Y, and private capital follows a no-sale ratchet — it can rise,
  never falls by sale. Honest cost: φ caps at ≈ 0.66 by ε = 0.99 (target
  0.99); the exit invariant still holds at every arc point, with
  self-financing from ε ≈ 0.30. `formation_levy_rate()` quantifies the
  compensated-bridge variant (≈ 1% of labor-era output, sunset by ε ≈ 0.2).
- **`"target"`** — the §8.9a purchase model (regression anchor; reproduces
  the published §8.9 numbers, including the early-arc acquisition
  infeasibility window that the charter doctrine removes).
- **`"escalated"`** — dilution + the charter escalation clause
  (`escalation_trigger()`): if the adversarial regime is observed AND
  contestability degrades (capacity < `RECAL_ESCALATION_CAPACITY_FLOOR` or
  the invariant failing), the charter takes all new formation (s = 1) and
  the capital-estate escheat (`estate_conversion_flow()`, D5 extended to
  capital at `ESTATE_LEVY_FRACTION`) rises to full generational conversion.
  The trigger latches; at canonical defaults it never fires. Mortality speed
  is slow (half-life ≈ 69 yr at full escheat): §8.2's "φ must be ABLE to
  → 1" survives as an asymptotic capability the invariant never depends on.

- **`capital_stock_epsilon(epsilon, population, capital_output_ratio)`** —
  K(ε) = K₀ + ν·Y(ε): the stock grows with the machine output it must produce
  (ν = Piketty's β ≈ 4). Fixes the τ = 17.5 incoherence (§8.8 open item 3) at
  the root.
- **`commons_capital(epsilon, ...)`** — ownership accounting (Meade
  social-dividend model): the commons OWNS share φ(ε) of K(ε), so
  τ = φ ≤ 1 by construction and dτ/dε ≥ 0 (Piketty inversion) is
  **structural**, not levy-contingent. T_K(0) = φ₀·K₀ is the generalized
  commons seed.
- **`commons_income_statement(epsilon, ..., phi_policy)`** — the annual
  income statement. Under the doctrine ("dilution") the full φ·Y distributes
  as the universal dividend (0 at ε=0, ≈1,606 TEH/person·yr at ε=0.99);
  under "target" income first funds share purchase (D ≈ 1,873 at 0.99, but
  with the ε ≲ 0.15 acquisition-infeasibility window). `g_priv` is
  endogenous, reported as both a rate and an absolute flow
  (`private_capital_delta_per_year` — a rate on a vanishing base is
  theatrical).
- **`capital_account_stock(tenure_years, epsilon, ...)`** — the RC4 fix for
  §8.7b: a genuine accumulating stock (sum of dividend credits, zero-interest
  per Condition III; Mondragon internal-account precedent), with the
  dimensionally-clean `chi_stock = account / (ε·K_entry)`.
- **`exit_financing(epsilon, ...)`** — the §8.9 invariant. K_entry decomposes
  by the machine share of work: (1−ε)·K_entry is founders' own labor (the
  floor feeds them while they build), ε·K_entry is embodied capital financed
  by dividend savings or commons underwriting.
  `exit_financeable ⇔ t_exit_self ≤ RECAL_EXIT_HORIZON_YEARS OR
  entry_capacity ≥ 1` — time-to-finance replaces the retired flow/stock χ.
- **`recalibrated_arc(n_points, regime, ..., phi_policy, estate_escheat_share)`**
  — the "where things stand" table; path-integrates the capital split under
  the charter policies (TEH conservation asserted). At defaults (dilution,
  adversarial) the invariant holds at every arc point, with the financing
  channel arcing labor → underwritten → self: each channel strongest where
  the physics puts it, and the mid-arc trough (ε ≈ 0.05–0.27 under the
  doctrine dividend — labor displaced, dividend not yet large) carried by
  underwriting.

**Open item — CLOSED by §8.9c** (see formation.py below): the charter
share's investment-disincentive feedback on K(ε) is now simulated.

---

## formation.py — Formation Feedback (proposed §8.9c)

Closes the K(ε) circularity: formation is FINANCED or it does not happen,
and ε is derived from the capital actually formed.

```python
from hours_eoh.research.formation import (
    private_return, investment_supply_fraction, incentive_compatible_share,
    formation_feedback_simulation, formation_verdict,
)
```

- **Supply analytics** — r_priv(s) = (1−s)(1/ν−δ); linear supply f(s)
  between `FORMATION_HURDLE_RATE_MIN` and `FORMATION_FULL_SUPPLY_RATE`;
  the incentive-compatible share s* = 1 − r_full/r_gross = **0.50** at
  defaults. The charter is genuinely free below s* (crossed at ε ≈ 0.33).
- **`formation_feedback_simulation(n_years, priority, ...)`** — year-by-year
  forward simulation: charter share endogenous, private supply f(s),
  commons co-funding from net income (gross φ·Y minus own replacement
  δ·T_K), ε capacity-derived (lagged). `charter_share_override=0.0` is the
  null anchor: reproduces the canonical ~50-yr arc pace exactly.
- **`formation_verdict(rows)`** — the §8.9c verdicts (all asserted in
  tests): **share-first** priority holds the canonical pace with zero
  delay, but the dividend pays (D ≈ 113 vs static 302 at ε ≈ 0.4;
  self-financing onset moves from ε ≈ 0.30 to ≈ 0.86 — underwriting
  carries the transition). **Dividend-first** never stalls but crawls:
  ε ≈ 0.60 after 120 years. The exit invariant holds at every simulated
  year under both priorities — capacity does not depend on the dividend.
- **The Condition III finding** — zero interest is the doctrine's
  structural ally: s* = 0.50 at zero-interest returns vs ≈ 0.10 at
  fiat-like returns, and the fiat counterfactual must drive the dividend
  to literally zero mid-arc to hold pace. Quantified, tested.

**CLI access**: `eoh contestability formation`.

**Superseded**: `trust_required_for_chi()` and `levy_schedule_for_chi()` are
retained unchanged as documented negative results of the retired bare-χ
invariant (the trust-growth path cannot close it; that is why underwriting
exists).

**CLI access**: `eoh contestability recal`.

---

## coasean.py — Coasean Collective Federation (Workstream D)

The federation of N(ε) collectives from reconciliation §§6–7, with the §8.7
two-tier Trust. The collective count is emergent
(`N(ε) = max(1, round(N_max·(1−ε)^exp))`); N=1 reproduces the single-ledger
results exactly (`n1_regression_anchor()`).

```python
from hours_eoh.research.coasean import (
    Collective, coasean_collective_count, make_federation,
    exchange_rates, bilateral_imbalances, settlement_check,
    three_regime_inflation, simulate_federation,
    merge_collectives, split_collective,
)
```

Phases 1–3 cover the federation factory, pairwise exchange rates, the
three-regime inflation metric (within-collective floor-impossibility at all ε;
inter-collective relative inflation as FX in transition; system-wide
impossibility as the ε→1 limit), settlement rules, and Trust/capital dynamics
with the §8.3 Piketty-inversion check.

### Phase 4 — boundary events and the federation commons (§8.7)

- **`merge_collectives(absorber, absorbed, rate, indivisible_fraction) → dict`** —
  the absorbed collective dissolves; its indivisible reserve
  (`COASEAN_INDIVISIBLE_RESERVE_FRACTION`, default 0.30) escheats to the
  federation commons; allocated accounts carry over converted at `rate`.
  TEH-conserving by construction (`conserved` flag; §8.7d).
- **`split_collective(parent, fractions, ...) → dict`** — the parent dissolves;
  its indivisible portion escheats; successors receive the allocated share
  pro-rata by population fractions. Same conservation postcondition.
- **`simulate_federation(..., commons=True, commons_tithe, commons_start, regime)`** —
  two-tier simulation: a levy tithe (`COASEAN_COMMONS_TITHE`, default 0.03,
  Italian Law 59/1992 precedent) plus consolidation escheats fund a commons
  balance that backs the sufficiency floor as **reinsurance, not payer**
  (`commons_floor_coverage`). Per-collective χ is computed each period; the
  record carries `chi_min`, `chi_marginal_min`, `chi_worst_collective`,
  `chi_status_worst`. τ counts both tiers: `(T + commons)/K`.

**Honest findings at defaults** (report, don't tune): commons floor coverage
is tiny at a 3% tithe, and consolidation escheat migrates trust from
collective dividends to the commons across the arc, so `chi_marginal_min`
worsens toward ε→1 while total τ holds.

### Phase 4b — contestability closure (proposed §8.8)

`simulate_federation(..., commons_dividend=True, commons_start=seed)` answers
the findings above: the commons pays its yield as a universal unvested
dividend (M1), per-collective χ includes it, and every record carries
`entry_capacity` and `exit_financeable` (M2 — reported whenever
`commons=True`). With `commons_start = commons_seed_required()` the combined
invariant `exit_financeable` holds at **every** period of the canonical
adversarial arc (asserted in tests). χ_marginal alone remains CRIT at high ε
— exit is commons-financed there, not self-financed, and the output says so.

**CLI access**: `eoh coasean n1-check | count | federation | simulate`
(simulate flags: `--dynamics --g-priv --levy-rate --commons --commons-tithe
--regime --commons-dividend --commons-start`).

---

## membership.py — Membership-Terms Audit (§8.7e)

The math/contract line: code owns the invariants; collectives own the terms;
the audit checks any proposed terms against the invariant. *The code is the
constitutional court, not the legislature.*

```python
from hours_eoh.research.membership import MembershipTerms, contestability_audit
```

### `MembershipTerms` (TypedDict, all fields optional)

`vesting_years`, `admission_cost_teh`, `exit_notice_years`,
`minimum_hours_annual`, `dividend_policy_fraction`.

### `contestability_audit(terms, epsilon, collective_trust, ..., commons_balance, regime) → dict`

Mimics the `assess_tier()` validator pattern (OK/WARN/CRIT escalation,
warnings list, `passes = worst != "CRIT"`). The core check: **admission cost
adds to K_entry** (a sunk buy-in the exiting marginal member must fund), so
`χ_marginal = S / (K_entry + admission)` — CRIT below 1.0. Exit notice,
minimum hours, vesting length, and dividend retention are checked against the
`MEMBERSHIP_*` thresholds in `data.py`; an empty commons WARNs (the floor is
unbacked) while coverage adequacy is reported without escalation.

§8.8 closure flags (both default off — §8.7e escalations unchanged):
`commons_dividend=True` adds the universal commons dividend to P;
`underwriting_policy=True` lets a commons with `entry_capacity ≥ 1`
(computed against `k_eff`, so admission charges shrink it) waive the
χ_marginal CRIT to WARN — exit stays financeable, but by federation policy
rather than arithmetic in the member's hands, and the warning says so.

**CLI access**: `eoh contestability audit` (terms from `--terms-json PATH|-`
or inline flags; `--commons-dividend --underwriting-policy`).
