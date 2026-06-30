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
`epsilon`, `p`, `k_entry`, `chi_population_avg`, `phi`, `tau`, `levy_fraction`,
`levy_feasible`, `status`.

The `chi_population_avg` key name flags that this is a population-average estimate,
not individually tenure-vested.

**CLI access**: `eoh contestability arc` and `eoh contestability stress`.
**Dashboard integration**: `eoh dashboard` shows χ with color-coded PASS/FAIL.
