"""
The CLI's labour income is the mint — `utils/arc_cmd.py` and `utils/params_cmd.py`.

Not named for a module (it covers two in `utils/`); listed in CLAUDE.md's test
index for that reason.

Both passed `registered_eoh × 2200.0` to `fiscal_snapshot` as labour income
from the initial commit — ~1,100× the mint — so the `arc` command's `solvent`
column could not report insolvency for any Trust, and `params`' impact rows
reported a surplus ~100× high (2026-09-30). These pin that the labour income
IS the mint, and that the solvency column can fire.
"""

from __future__ import annotations

import pytest

from utils.arc_cmd import _sweep


def test_the_sweep_reports_the_mint_it_computes():
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    rows = _sweep(3, 1.0e6, None)
    for r in rows:
        assert r["teh_created"] == pytest.approx(
            eoh_to_teh_pipeline(r["epsilon"], population=1.0e6)["teh_created"], rel=1e-12)


def test_solvency_can_fire():
    """Mode 9, the question the ×2200 income failed: with no inheritance the
    top of the arc is insolvent on the real mint."""
    rows = _sweep(3, 1.0e6, 0.0)
    assert rows[-1]["epsilon"] == pytest.approx(0.99)
    assert rows[-1]["solvent"] is False


def test_and_can_hold():
    rows = _sweep(3, 1.0e6, None)
    assert all(r["solvent"] for r in rows)


def test_params_impact_rows_use_the_mint_too():
    """The same ×2200 literal sat in `utils/params_cmd._impact_row`."""
    from hours_eoh.core.fiscal import fiscal_snapshot
    from hours_eoh.params import EohParams
    from utils.params_cmd import _impact_row
    p = EohParams()
    d = p.to_dict()
    row = _impact_row(p, 0.40)
    snap = fiscal_snapshot(
        epsilon=0.40, population=float(d["population"]), labor_income=row["teh_created"],
        capital_stock_teh=float(d["capital_stock_teh"]),
        capital_age_ratio=float(d["capital_age_ratio"]),
        levy_rates={"sufficiency": float(d["suff_levy_rate"])},
        dep_rate=float(d["dep_rate"]), div_rate=float(d["div_rate"]),
    )
    assert row["surplus_deficit"] == pytest.approx(snap["trust"]["surplus_deficit"], rel=1e-12)
