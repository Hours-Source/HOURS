# Multipliers

**Module:** `hours_eoh/core/multipliers.py`

Implements Condition II — skill-tier multipliers grounded in entropy-reduction leverage. The multiplier is the factor by which one hour of a worker's labor is scaled when creating TEH.

---

## `population_weighted_mean_multiplier(multiplier_distribution, p)` → `float`

Computes the population-weighted average multiplier from a distribution of tier assignments.

```python
from hours_eoh.core.multipliers import population_weighted_mean_multiplier

mean = population_weighted_mean_multiplier({"1": 0.40, "2": 0.35, "3": 0.25}, p=p)
```

**Band target:** 1.8–2.1, with a recommended target of 2.1. This is monitored by [Condition II](conditions.md).

---

## `multiplier_band_check(mean_multiplier, p)` → `dict`

Verifies the population-weighted mean is within the band.

```python
from hours_eoh.core.multipliers import multiplier_band_check

check = multiplier_band_check(mean_multiplier=2.05, p=p)
# Returns: {"in_band": True, "mean": 2.05, "target": 2.1, ...}
```

---

## `tier_multiplier(tier, p)` → `float`

Returns the multiplier for a given skill tier.

The multiplier system applies to all entropy-reduction labor uniformly — care, production, and stewardship workers all receive the same multiplier framework. What changes across the arc is which tier classifications are most in demand.

---

## `epoch_alpha_weights(epsilon, p)` → `dict`

Returns the relative weighting of the four-factor assessment (training, demand, scarcity, societal impact) at a given ε. The absolute factors don't change; only their relative weighting shifts as the economy evolves from production-dominant to stewardship-dominant.
