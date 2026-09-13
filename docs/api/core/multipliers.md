# Multipliers

**Module:** `hours_eoh/core/multipliers.py`

Implements Condition II — skill-tier multipliers grounded in entropy-reduction leverage. The multiplier is the factor by which one hour of a worker's labor is scaled when creating TEH.

---

## `population_weighted_mean_multiplier(…)` → `float`

The population-weighted mean multiplier across workforce segments, each a fraction of the workforce with its mean multiplier. Fractions are normalized if they do not sum to exactly 1.

```python
from hours_eoh.core.multipliers import population_weighted_mean_multiplier

mean = population_weighted_mean_multiplier()   # the shipped DEFAULT_SEGMENTS
# or pass your own workforce segments: population_weighted_mean_multiplier(segments=[...])
```

**Band target:** 1.8–2.1, with a recommended target of 2.1. This is monitored by [Condition II](conditions.md).

---

## `multiplier_band_check(mean_multiplier, …)` → `dict`

Verifies the population-weighted mean is within the band (`band_low=1.8`, `band_high=2.1` by default). Out of band, the status says which way: below the band means raising low-tier multipliers, above it means tightening high-tier assignments.

```python
from hours_eoh.core.multipliers import multiplier_band_check

check = multiplier_band_check(mean_multiplier=2.05)
# Returns: {"in_band", "mean_multiplier", "band_low", "band_high", "target",
#           "distance_to_target", "status"}
print(check["in_band"], check["status"])
```

---

## `tier_multiplier(training, demand, scarcity, impact, …)` → `float`

A tier multiplier from the four-factor assessment in the paper's additive form, `m = 1 + α₁·T + α₂·D + α₃·S + α₄·I`, each factor in `[0, 1]`. The multiplier sets the **floor wage rate**, not an economy-wide price.

The multiplier system applies to all entropy-reduction labor uniformly — care, production, and stewardship workers all receive the same framework. What changes across the arc is which tier classifications are most in demand.

---

## `epoch_alpha_weights(epsilon)` → `tuple[float, float, float, float]`

!!! warning "Deprecated"
    The additive form is superseded by the geometric map used for the measured O\*NET/BLS reference multiplier: `epoch_factor_weights()` → `composite_from_factors()` → `reference_multiplier()`. This function is kept for backward compatibility.

The absolute α coefficients (training, demand, scarcity, impact) for `tier_multiplier()`'s additive form, adapted to ε.
