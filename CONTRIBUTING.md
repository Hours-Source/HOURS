# Contributing to HOURS

## Development Setup

```bash
git clone https://github.com/Hours-Source/HOURS
cd HOURS
pip install -e ".[dev]"
```

Verify the environment:

```bash
python3 -m pytest tests/ -q    # 1040 tests should pass
python3 -m mypy hours_eoh/
```

Requires Python ≥ 3.10.

---

## Architecture Rules

The framework enforces strict layer separation. Violations cause import errors or silent coupling that corrupts the design.

| Layer | May import from | Never imports from |
|-------|----------------|-------------------|
| `core/` | `data.py`, `params.py`, other `core/` modules | `land/`, `scenarios/`, `research/` |
| `land/` | `core/` | `scenarios/`, `research/` |
| `scenarios/` | `core/` | `land/`, `research/` |
| `research/` | `core/` (re-exports only) | `scenarios/`, `land/` |

New scenario code goes in `scenarios/`. `core/stress.py` is a backward-compat shim — do not add to it.

---

## Writing New Functions

### EOH generation functions

Take **physical state** as primary inputs: `capital_stock`, `ecosystem_health`, `population_age_distribution`, `knowledge_base_size`, `monitoring_capability`.

```python
def my_eoh_function(
    capital_stock: float,
    ecosystem_health: float,
    # ...
    epsilon: float | None = None,  # optional backward compat only
    p: EohParams = ...,
) -> float:
```

When `epsilon` is provided for backward compat, use `canonical_physical_state(epsilon)` to derive the physical state. Do not use ε as a proxy for unspecified physical assumptions in new code.

### Fulfillment, registration, fiscal, and price functions

Take **ε** directly — the machine/human split and fiscal mechanisms are genuinely ε-driven.

### All functions must

- Produce physically meaningful output at ε = 0, ε = 0.40, ε = 0.90, and ε = 0.99
- Not depend on human labor volume being large (post-scarcity has near-zero human EOH)
- Degrade gracefully as ε → 1.0 — no discontinuities, no division-by-zero
- Use named constants from `data.py` exclusively — **no anonymous numeric literals**
- Include a comment referencing the relevant Mission Statement section
- Have tests verifying behavior at the four key ε values and monotonicity where expected
- Be included in `dashboard.py` or carry an explicit comment explaining why it is research-only

### `data.py` is the single source of truth

Every numeric literal in domain logic must be a named constant defined in `data.py`. Canonical trajectory constants use the `CANONICAL_` prefix. No inline numbers.

---

## Testing Requirements

Tests live in `tests/`. New tests for scenario modules live in `tests/scenarios/`.

Every PR must pass:

```bash
python3 -m pytest tests/ -q
python3 -m mypy hours_eoh/
```

**Test at the four key ε values.** A function that produces correct results at ε = 0.40 but breaks at the extremes is a calibration artifact, not a valid implementation.

Test names follow the existing phase convention: `TestClassName::test_description`. New module tests should be grouped in a `Test` class.

---

## Code Style

- No comments explaining *what* code does — well-named identifiers do that.
- Add a comment only when the *why* is non-obvious: a hidden constraint, a physical invariant, a specific mission statement reference.
- No docstrings longer than one short line.
- `mypy --strict` must pass cleanly.
- No anonymous constants. If you add a calibrated number, it goes in `data.py` first.

---

## Physical Grounding

Every EOH function must have a physical basis traceable to observable reality — sensor data, engineering standards, material science, ecological monitoring, or public health data. EOH rates are not policy variables. If a rate is not auditable against the physical world, it does not belong in `core/`.

---

## Opening Issues

When filing a bug or gap:

- State which ε value(s) reveal the problem
- Include the minimal function call that reproduces it
- Note which Structural Condition (I–IV) or Design Principle is violated, if applicable

Feature proposals should reference the Mission Statement section they extend.

---

## Commit Messages

One subject line (≤72 characters). Focus on *why*, not *what*. The diff shows what changed; the message should say why it needed to change.

No emojis, no `[TYPE]:` prefixes.
