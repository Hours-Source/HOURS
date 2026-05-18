# Extending the Library

## Layer Rules

Strict layer separation is enforced. Violations cause import errors or silent coupling that corrupts the design.

| Layer | May import from | Never imports from |
|---|---|---|
| `core/` | `data.py`, `params.py`, other `core/` modules | `land/`, `scenarios/`, `research/`, `utils/` |
| `land/` | `core/` | `scenarios/`, `research/`, `utils/` |
| `scenarios/` | `core/` | `land/`, `research/`, `utils/` |
| `research/` | `core/` (re-exports only) | `scenarios/`, `land/`, `utils/` |
| `utils/` | All layers freely | Never imported by any layer |

**Placement:**

- New physics + mechanics → `core/`
- New GUF/land mechanics → `land/`
- New applied scenario → `scenarios/`
- Experimental/research re-exports → `research/`
- New CLI commands → `utils/`

New scenario code goes in `scenarios/`. Do not add to `core/stress.py` (backward-compat shim only).

---

## Writing New Functions

### EOH Generation Functions

EOH generation is pure physics — functions take actual physical state as primary inputs.

```python
def my_eoh_function(
    capital_stock: float,
    ecosystem_health: float,
    population_age_distribution: dict[str, float],
    knowledge_base_size: float,
    epsilon: float | None = None,  # optional backward compat only
    p: EohParams = ...,
) -> float:
    # NLSA §N.N reference
    ...
```

When `epsilon` is provided for backward compat, use `canonical_physical_state(epsilon)` to derive unspecified physical state. Do not use ε as a proxy for physical assumptions in new code.

### Fulfillment, Registration, Fiscal, and Price Functions

These mechanisms are genuinely ε-driven — take ε directly.

```python
def my_fiscal_function(epsilon: float, p: EohParams = ...) -> float:
    ...
```

---

## The Function Checklist

Before committing any new function, verify every point:

**Input signature:**

- [ ] EOH generation: takes physical state as primary inputs; ε is optional backward compat only
- [ ] Fulfillment/registration/fiscal/prices: takes ε directly

**Arc coverage:**

- [ ] Physically meaningful at **ε = 0** (subsistence: near-zero collective economy, private EOH, minimal ledger)
- [ ] Physically meaningful at **ε = 0.40** (current equilibrium: calibration reference)
- [ ] Physically meaningful at **ε = 0.90** (near-post-scarcity: care-dominant, automation-heavy)
- [ ] Physically meaningful at **ε = 0.99** (effective post-scarcity: prices collapsed, labor near-zero)

**Structural requirements:**

- [ ] Does not depend on `output(ε)` being large
- [ ] Does not assume all workers are in production
- [ ] Accounts for all four entropy domains where relevant
- [ ] Respects Conditions I–III; considers Condition IV where adopted

**Code conventions:**

- [ ] Named constants from `data.py` exclusively — no anonymous numeric literals
- [ ] Comment referencing the relevant Mission Statement section
- [ ] Degrades gracefully as ε → 1.0 (no discontinuities, no division-by-zero)
- [ ] Well-defined at ε near 0.0

**Placement and tests:**

- [ ] Included in `dashboard.py` or carries an explicit comment explaining research-only status
- [ ] Tests at the four key ε values and monotonicity where expected

---

## Constants in data.py

Every numeric literal in domain logic must be a named constant in `data.py`.

```python
# data.py
MY_NEW_CONSTANT: float = 0.15  # brief physical rationale

# my_module.py
from hours_eoh.data import MY_NEW_CONSTANT

def my_function(epsilon: float) -> float:
    return MY_NEW_CONSTANT * (1 - epsilon)
```

Canonical trajectory constants use the `CANONICAL_` prefix.

---

## Testing Requirements

```bash
python3 -m pytest tests/ -q
python3 -m mypy hours_eoh/
```

Test at all four key ε values. A function that passes at ε = 0.40 but breaks at the extremes is a calibration artifact. Test naming: `TestClassName::test_description`. Group new module tests in a `Test` class.

---

## Code Style

- No comments explaining *what* code does — well-named identifiers do that
- Add a comment only when the *why* is non-obvious: a hidden constraint, a physical invariant, a Mission Statement reference
- No docstrings longer than one short line
- `mypy --strict` must pass cleanly
- No anonymous constants — they go in `data.py` first

---

## Opening Issues

When filing a bug or gap:

- State which ε value(s) reveal the problem
- Include the minimal function call that reproduces it
- Note which Structural Condition (I–IV) or Design Principle is violated, if applicable

Feature proposals should reference the Mission Statement section they extend.
