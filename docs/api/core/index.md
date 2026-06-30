# Core — Physics Layer

**Package:** `hours_eoh/core/`

The `core/` package contains pure physics and mechanics — the stable API. It imports only from `data.py`, `params.py`, and other `core/` modules. Nothing imports from `core/` except the layers above it (`land/`, `scenarios/`, `research/`, `utils/`).

---

## Module Overview

| Module | What it models |
|--------|---------------|
| [`trajectory.py`](trajectory.md) | Canonical arc at each ε; ε derivation from physical state |
| [`eoh_generation.py`](eoh_generation.md) | Four EOH domain functions + `total_eoh()` — principled measurement from physical state |
| [`eoh_fulfillment.md`](eoh_fulfillment.md) | EOH → TEH pipeline; human/machine split; registration |
| [`multipliers.py`](multipliers.md) | Condition II: skill-tier multipliers, population-weighted band |
| [`fiscal.py`](fiscal.md) | Levies, allocations, sufficiency guarantee, trust mechanics |
| [`prices.py`](prices.md) | TEH prices, basket cost, purchasing power arc |
| [`capital.py`](capital.md) | Asset lifecycle, write-down, birth/death events |
| [`population.py`](capital.md) | Age distribution, aging, demographic events (on same page as capital) |
| [`eoh_dynamics.py`](dynamics.md) | Compounding, regenerative labor, investment ranking |
| [`workforce.py`](workforce.md) | Competency reserve, minimum hours allocation |
| [`civilization.py`](workforce.md) | Endogenous ε from capital stock (on same page as workforce) |
| [`conditions.py`](conditions.md) | Structural conditions I–IV enforcement |
| [`dashboard.py`](conditions.md) | EOH health, fiscal health, system dashboard (on same page as conditions) |
| [`simulation.py`](simulation.md) | Period simulation engine |

---

## The EOH → TEH Pipeline

```python
# Step 1: physical state → total EOH
state = canonical_physical_state(epsilon)        # or pass real tracked state
eoh = total_eoh(**state, p=p)

# Step 2: EOH → human/machine split
human_eoh = human_eoh_per_domain(eoh_dict, epsilon)

# Step 3: registration (different curves per domain)
# Personal: personal_eoh_registration_share(epsilon)  — near-zero at ε=0
# Other:    total_registration_share(epsilon)          — labor composite sigmoid
reg_share = total_registration_share(epsilon, p=p)
reg_eoh = registered_eoh(human_eoh, reg_share)

# Step 4: TEH creation
teh = teh_created(reg_eoh, mean_multiplier)

# Or use the full pipeline in one call:
result = eoh_to_teh_pipeline(epsilon, p=p)
```

**Key design invariant:** EOH generation takes physical state. EOH fulfillment takes ε. These two concerns must never be conflated. See [Design Principles](../../theory/design_principles.md#9-every-mechanism-must-express-the-arc-not-just-a-point-on-it).
