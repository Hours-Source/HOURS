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
