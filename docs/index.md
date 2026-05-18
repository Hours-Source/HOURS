# HOURS EOH Framework

**HOURS** is a mathematical framework for a currency system — *Entropy Obligation Hours (EOH) → Time-Equivalent Hours (TEH)* — that remains coherent, physically grounded, and fiscally solvent across the full civilizational transition from subsistence to post-scarcity.

> "An economy is the organized effort of a civilization to resist entropy — in its people, in its infrastructure, in its ecosystems, and in its knowledge."

---

## What This Is

A civilization can be described by a single observable: **ε (epsilon)** — the fraction of entropy obligations fulfilled by machines rather than human bodies.

| ε | State | What it means |
|---|-------|---------------|
| 0.00 | Subsistence | All entropy resistance is human labor. TEH barely circulates. |
| 0.40 | Transition midpoint | Automation handles ~40% of EOH. The primary design reference. |
| 0.90 | High automation | Prices collapse toward raw material costs. Care labor dominates. |
| 0.99 | Effective post-scarcity | Automation handles nearly all EOH. Human labor near-zero. |

ε is not a policy lever. It is an *observed* state of the world — measured from capital stock and machine capacity. Every function in this framework must produce physically meaningful output across the full arc from ε = 0 to ε = 0.99.

---

## Four Entropy Domains

The economy organizes resistance to entropy across four physical domains:

<div class="grid cards" markdown>

-   **Personal**

    Biological needs: food, shelter, healthcare, sanitation. Scales with population and age structure.

-   **Infrastructure**

    Buildings, roads, power grids, water systems, communications. Grows with automation-embodied capital.

-   **Ecological**

    Soil fertility, water cycles, pollination, fisheries, climate stability. Co-equal Trust obligation.

-   **Knowledge**

    Skills, institutional memory, standards, software, training. Accelerates at high ε as complexity compounds.

</div>

---

## The EOH → TEH Pipeline

```
Physical state → total_eoh()            # entropy obligation from physics
              → human_eoh_per_domain()  # ε drives the machine/human split
              → registration boundary   # EOH admitted to the collective ledger
              → × worker multiplier     # TEH enters circulation
```

EOH generation is pure physics — functions take actual physical state (capital stock, ecosystem health, age distribution, knowledge base) and return entropy obligations. EOH fulfillment is where ε belongs — the machine/human split, registration curves, and fiscal mechanics are genuinely ε-driven.

---

## Structural Conditions

Four conditions define system integrity. All must hold at every ε:

| Condition | Rule | Enforced by |
|-----------|------|-------------|
| **I — Ledger Identity** | TEH supply = created − destroyed | `condition_i_check()` |
| **II — Multiplier Band** | Skill multipliers within physics-grounded band | `condition_ii_check()` |
| **III — Zero Interest** | Balances grow through labor only, never passively | `condition_iii_balance_growth_check()` |
| **IV — Distributed Competency** | Human reserve in every essential domain | `condition_iv_check()` |

The system dashboard gives a one-call health check:

```python
from hours_eoh.core.dashboard import system_dashboard
from hours_eoh.params import EohParams

snapshot = system_dashboard(epsilon=0.40, p=EohParams())
print(snapshot["overall"])  # GREEN / YELLOW / RED
```

---

## Get Started

=== "Install"

    ```bash
    git clone https://github.com/Hours-Source/HOURS
    cd HOURS
    pip install -e ".[dev]"
    ```

    Requires Python ≥ 3.10. No external service dependencies.

=== "First Code"

    ```python
    from hours_eoh.core.trajectory import canonical_physical_state
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.params import EohParams

    p = EohParams()
    state = canonical_physical_state(0.40)
    eoh = total_eoh(**state, p=p)
    result = eoh_to_teh_pipeline(0.40, p=p)
    print(f"EOH:  {eoh['total_eoh']:.3e}")
    print(f"TEH created: {result['teh_created']:.1f}")
    ```

=== "Arc Coherence Check"

    ```python
    from hours_eoh.scenarios.sweep import epsilon_sweep

    results = epsilon_sweep()
    assert all(r["fiscally_solvent"] for r in results)
    print(f"Arc coherent across {len(results)} ε values")
    ```

=== "CLI"

    ```bash
    # Full arc sweep
    python3 utils/eoh_cli.py arc --points 10

    # System health at ε = 0.40
    python3 utils/eoh_cli.py dashboard --epsilon 0.40

    # GUF for a 3.5 SLU parcel
    python3 utils/eoh_cli.py guf calculate \
        --area 3.5 --location 0.629 --use residential_primary --epsilon 0.40
    ```

---

## Where to Go Next

<div class="grid cards" markdown>

-   **Theory**

    The mathematical foundations: what an economy is, the ε arc, the four entropy domains, structural conditions, EOH accounting, and the 9 design principles.

    [:octicons-arrow-right-24: Read the theory](theory/overview.md)

-   **Developer Reference**

    Complete API documentation for all modules — `core/`, `land/`, `scenarios/`, and `research/`. Includes worked code examples for every function.

    [:octicons-arrow-right-24: Browse the API](api/index.md)

-   **Quick Start Guide**

    Install, run the pipeline, check the dashboard, and run your first scenario. Annotated CLI examples for every command.

    [:octicons-arrow-right-24: Quick start](guides/quickstart.md)

-   **Ground Use Fee Framework**

    The full mathematical specification for the GUF — 14 functions, worked example at ε = 0.40, ecological write-down pathways, and the §9 rebuilding surcharge.

    [:octicons-arrow-right-24: GUF specification](theory/guf_framework.md)

</div>

---

## Running Tests

```bash
python3 -m pytest tests/ -q           # 998 tests
python3 -m mypy hours_eoh/            # type checking
```
