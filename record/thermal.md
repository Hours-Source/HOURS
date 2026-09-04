# The planetary radiative layer

**Scope.** The P0 bound, Path C, λ and its Planck ceiling, the drawdown chain and
the solvency gate, responsibility allocation, η from ERA5, capital dual-output —
and the measurement-spine merge that founded the layer.

Migrated from `CLAUDE.md` § Current status on 2026-09-03. Entries are verbatim.

---

## Live state

- **The thermal obligation is a STOCK carried in the ecological domain**, opt-in
  and defaulting to 0.0. It is the one ecological service labour cannot restore
  and is unattributable to any parcel, so it falls OUT of the pristine/current
  partition rather than being wedged into it. See
  [ecological.md § Live state](ecological.md#live-state).
- **λ has a physical ceiling and it is enforced.** `planck_feedback()` derives
  λ_P = 4σT³ = 3.761 W·m⁻²·K⁻¹ from `SIGMA_SB` × `EARTH_EMISSION_TEMPERATURE_K`;
  net feedbacks are amplifying, so λ < λ_Planck is required. **Shipped λ = 1.2 is
  admissible at 0.319 of the bound**, implying 2.561 W·m⁻²·K⁻¹ of net amplifying
  feedback — the quantity a reader can check against the literature. The bound is
  deliberately LOOSE (blackbody 3.761 against the real ≈3.2), erring toward
  admitting too much λ rather than too little. **This is the only physical anchor
  λ has**, and λ is the most leveraged parameter after `delta_T_lo`.
- **The layer withholds the budget where the sign is undetermined.** Carrying λ
  honestly widens the indeterminate band 2×, and that is reported rather than
  resolved.
- **`epsilon_current` is derived where an inventory exists**; global ε_max keeps a
  chosen `epsilon_current` and travels with its sensitivity band, because no
  measured world capital inventory in TEH exists.

## Open

- **`CDR_LABOR_HOURS_PER_TONNE` (0.6, Tier D) now owns any residual discrepancy
  between the thermal and land layers.** The ecological anchor can no longer
  absorb it — Phase 4f settled that disjunct. *Settles by:* operator staffing data
  beyond the current n=1.
- **The `GUF_ECO_KAPPA_*` constants are engineered-route figures.** Restoration
  implies κ_carbon 0.009–0.048 h/tonne against a shipped 0.6 — a 12–69× gap that
  is a MEASUREMENT of how much cheaper biological replacement is, not an
  inconsistency to reconcile. CONDITIONAL on a placeholder V_s. See
  [ecological.md#phase-3-restoration-cost](ecological.md#phase-3-restoration-cost).
- **λ_equilibrium is not assessable from this data**, and marginal-capacity η was
  built three ways and none is usable. Both are declared limits, not gaps to
  close opportunistically.
- **Capital thermal intensities are Path-D placeholders** — they need IEA/LCA
  data.

## Cross-area entries

| Entry | Also | Why |
|---|---|---|
| [measurement-spine-merged](#measurement-spine-merged) | [provenance](provenance.md#history), [personal](personal.md#history) | The merge covers the multiplier and infrastructure spines as well as thermal; filed here because thermal is its largest component |
| [audit-closures](#audit-closures) | [contestability](contestability.md#history), [ecological](ecological.md#history), [provenance](provenance.md#history) | Six gaps across four areas — the corridor contestability axis, thermal ε_current, the four-tag migration, domain balance, the thermal obligation made reachable, and orphan registration |

---

## History

Newest first, verbatim as written. Anchors are stable — link to a specific entry
as `record/thermal.md#<slug>`.

<a id="measurement-spine-merged"></a>

**Measurement spine merged** (`f2a242e`, 2026-08-05, 12 commits): measured inputs replacing chosen constants across the multiplier (O\*NET 30.3/BLS, 751 occupations, 94.2% of employment), infrastructure (currency-free statutory floor from a physical condition census, doctrine-invariant at spread 1.000 vs the monetized path's 10.26×), and thermal (P0 bound, Path C, corridor, capital dual-output, C5 forcing correction, overage/debt reframing, drawdown chain + solvency gate, responsibility allocation over the full 1750–2024 record, η from ERA5 for 258 collectives, derived λ, ε inversion via `capital_for_epsilon`, maintain-vs-replace). Two constants moved from recalled to derived (CO₂ forcing coefficient, λ_historical). What the branch DECLINED to claim is recorded with equal weight: λ_equilibrium is not assessable from this data; marginal-capacity η was built three ways and none is usable; carrying λ honestly widens the indeterminate band 2× and the layer now withholds the budget where the sign is undetermined.

<a id="audit-closures"></a>

**Audit closures** (2026-08-05, branch `fix/audit-close-now`): six gaps found by auditing the framework against its own claims, all closed with no new data.
- **Corridor contestability axis migrated.** `research/corridor.py` was still taking its ceiling from the bare χ = P/K_entry that §8.9 superseded, so the recorded "corridor CLOSED at defaults" finding was produced by a retired invariant. `contestability_ceiling()` now runs the adopted three-channel `exit_financing()` test; the old form survives as `contestability_ceiling_bare_chi()` and `contestability_axes()` reports the disagreement. At defaults the corridor is **OPEN** (nothing binds); under `--bare-chi` it still closes at ε_suff 0.517 vs ceiling 0.290, reproducing the earlier result on demand. `core/dashboard.py` gained `exit_financeable`, which governs the contestability flag when supplied and demotes χ to a YELLOW advisory (χ alone keeps pre-§8.9 behavior).
- **Thermal ε_current derived where an inventory exists.** `thermal_capital.epsilon_current_from_inventory()` + `capital_thermal_ceiling(epsilon_current=None)` default to deriving ε from the same capital that produces Φ, via `civilization_epsilon`. Global ε_max keeps a chosen ε_current — no measured world capital inventory in TEH exists — but `global_ceiling()` now returns `epsilon_max_band`/`binds_within_band` over ε_current ∈ [0.2, 0.6], so the chosen constant travels with its sensitivity. H = B/Φ_auto stays the headline.
- **Provenance four-tag migration finished** for the EOH-generation block, with a retag log. 13 constants now carry epistemic pointers where 6 previously claimed structural status.
- **Domain balance documented** (see below) with regression tests and `arc --domain-shares`.
- **Thermal obligation made reachable**: `scenarios/thermal_load.py` + `scenario run thermal_load`, `--thermal-obligation` on `arc` and `dashboard`.
- **Orphans registered**: `measured_sim`, `multiplier_sensitivity`, `infra_floor`, `thermal_load` in `scenario list`; new `corridor` CLI (`band`, `axes`).

