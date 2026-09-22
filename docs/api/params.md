# Parameters & Constants

## EohParams

**Module:** `hours_eoh/params.py`

`EohParams` is a mutable parameter container with change tracking. It is what the CLI's `params set` / `params show` persist and read; library functions take their inputs as explicit keyword arguments with `data.py` defaults, so pass a changed value to the function you are calling rather than expecting a container to reach it.

```python
from hours_eoh.params import EohParams

p = EohParams()                                          # default values
p.set("suff_levy_rate", 0.03, reason="high-levy charter")  # calibration-path change, recorded in history

with p.temporary(suff_levy_rate=0.05):                   # sweep code — restores on exit, no history
    print(p["suff_levy_rate"])                           # 0.05 inside the block
print(p["suff_levy_rate"], len(p.history))               # back to 0.03; one history entry
```

### Key methods

| Method | Description |
|--------|-------------|
| `p.set(key, value, reason=...)` | Persist a parameter change; records in change history |
| `p.temporary(**overrides)` | Context manager for sweep code — restores state on exit |
| `p.diff()` | Show all active overrides relative to defaults |
| `p.reset()` | Clear all overrides |

**Rule:** Use `p.set()` for calibration-path changes. Use `p.temporary()` in sweep/scenario code — it restores state on exit and adds no history entries.

---

## data.py — Named Constants

**Module:** `hours_eoh/data.py`

Single source of truth for all named constants. No anonymous numeric literals anywhere in domain logic. Every calibrated value must be a named constant here before use.

### Key constant groups

**EOH Generation**

| Constant | Value | Description |
|----------|-------|-------------|
| `CANONICAL_CAPITAL_STOCK_BASE` | — | Base capital stock on canonical arc |
| `CANONICAL_ECOSYSTEM_HEALTH_BASE` | — | Baseline ecosystem health index |
| `CANONICAL_KNOWLEDGE_BASE_SIZE` | — | Baseline knowledge units |
| `PERSONAL_EOH_BASE` | — | Per-person biological entropy obligation |

**Fiscal**

| Constant | Description |
|----------|-------------|
| `DEFAULT_LEVY_RATE` | Default labor levy rate |
| `SUFFICIENCY_TEH_FLOOR` | Nominal TEH floor for sufficiency guarantee |
| `ACCUMULATION_CEILING_MULTIPLIER` | TEH accumulation cap multiplier |

**GUF / Land**

| Constant | Description |
|----------|-------------|
| `GUF_PSI_A` | Ψ(ε) shape parameter a = 0.8 |
| `GUF_PSI_B` | Ψ(ε) shape parameter b = 1.2 |
| `GUF_PSI_FLOOR` | Ψ(ε) floor = 0.02 |
| `GUF_ALPHA_FLOOR` | α(ε) floor = 0.05 |
| `GUF_SOIL_CREDIT_RATE` | c_soil credit rate = 0.05 |
| `GUF_WRITEDOWN_AMORTIZATION_YEARS` | Y_r = 50 years |
| `GUF_EOH_ACCUMULATION_THRESHOLD` | Warning threshold = 0.30 |
| `GUF_USE_RESIDENTIAL_PRIMARY` | 10.0 TEH/SLU/yr (recalibrated ×100 from 0.10) |
| `GUF_USE_COMMERCIAL_RETAIL` | 30.0 TEH/SLU/yr (recalibrated ×100 from 0.30) |

All `GUF_USE_*` constants were recalibrated ×100 so that aggregate GUF for a 1 M-population territory (~420 k parcels) would land co-equal with levy revenue at ε = 0.40. **That target is withdrawn** (author, 2026-09-16): GUF is a *portion* of Trust inflow alongside the labour levy and the estate levy, never owed an equality with any of them. The ×100 is unchanged — withdrawing a target is not a licence to refit — and what would settle the level is still the unrun servicing census.

**Conditions and Simulation**

| Constant | Description |
|----------|-------------|
| `MULTIPLIER_BAND_TARGET` | Target population-weighted multiplier = 2.1 |
| `MULTIPLIER_BAND_MIN` | Lower band = 1.8 |
| `MULTIPLIER_BAND_MAX` | Upper band (design) = 2.1 |
| `MULTIPLIER_MAX` | Individual cap = 6.0 |
| `COMPETENCY_RESERVE_THRESHOLD` | Condition IV minimum = 0.155 (15.5%) |
| `WORKFORCE_FRACTION_MIN` | Minimum workforce fraction = 0.05 (used by `simulate_period` workforce decay) |

Add new constants to `data.py` before using them anywhere in the codebase. Use the `CANONICAL_` prefix for canonical trajectory constants.
