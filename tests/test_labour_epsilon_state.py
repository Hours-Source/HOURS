"""
The obligation's STATE frame, the ε floor, and what they do to a ported reading.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS FILE EXISTS. `labour_epsilon` divided measured hours by the CANONICAL
arc's obligation at each iterate. The population half of that pin was measured
and found inert on 2026-09-18 — per-capita `total_eoh` is frame-invariant to the
last bit. The STATE half was never checked, and it is not inert: the canonical
arc holds no capital at ε = 0, so the obligation there is personal-only and a
labour-intensive economy's measured hours exceed it. The fixed point then floors
at zero and reports 0.0000 for an overshoot of any size.

These tests pin the repair and, more importantly, pin that the repair CHANGED
NOTHING for callers who do not use it.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    LOW_EPSILON_CAPITAL_PROBE_TEH_PER_CAPITA,
    REFERENCE_FRAME_POPULATION,
)
from hours_eoh.scenarios import labour_epsilon as LE

#: Broad-scope human hours per capita for three MTUS samples that clamp against
#: the canonical obligation, measured 2026-09-21 from the 15+ per-code cut.
#: CZ1965 is the test case the advisor named: -0.0001 at core, -0.2273 at broad.
CZ1965_BROAD_HUMAN_PC = 1670.0
RS1965_BROAD_HUMAN_PC = 1805.3
US2024_BROAD_HUMAN_PC = 1042.2


class TestTheDefaultReadingIsUnchanged:
    """The repair is additive. A caller who ignores it sees the same numbers."""

    def test_the_shipped_epsilons_are_bit_identical(self):
        assert repr(LE.labour_epsilon("core")["epsilon"]) == repr(0.40689963045285293)
        assert repr(LE.labour_epsilon("broad")["epsilon"]) == repr(0.21380613330205045)

    def test_the_shipped_intermediates_are_bit_identical(self):
        core = LE.labour_epsilon("core")
        assert repr(core["human_per_capita"]) == repr(911.3211693717458)
        assert repr(core["total_obligation_per_capita"]) == repr(1536.537854575224)

    def test_supplying_no_state_equals_supplying_an_empty_one(self):
        assert (LE.labour_epsilon("core", obligation_state={})["epsilon"]
                == LE.labour_epsilon("core")["epsilon"])

    def test_the_comparison_verdict_has_not_moved(self):
        c = LE.instrument_comparison()
        assert c["verdict"] == "ADJACENT"
        assert repr(c["gap"]) == repr(0.04568693284802028)

    def test_the_report_still_builds_its_verdict_string(self):
        r = LE.labour_epsilon_report()
        assert f"{r['comparison']['labour']['high']:.3f}" in r["verdict"]


class TestTheFloorIsReportedNotHidden:
    """
    `epsilon` is max(0, ·). A clamped reading says 0.0000 whether the overshoot
    is 0.0001 or 0.33, which is the reported-is-not-applied failure in miniature.
    """

    def test_an_unclamped_reading_agrees_with_its_raw_value(self):
        r = LE.labour_epsilon("core")
        assert r["clamped"] is False
        assert r["epsilon_raw"] == pytest.approx(r["epsilon"], abs=1e-12)

    def test_a_clamped_reading_keeps_the_overshoot(self):
        r = LE.labour_epsilon(
            "broad", population_15_plus_supplied=8e7,
            unpaid_per_15plus=1500.0, paid_per_15plus=1500.0,
            population=1e8,
        )
        assert r["clamped"] is True
        assert r["epsilon"] == 0.0
        assert r["epsilon_raw"] < 0.0, "the overshoot must survive the clamp"

    def test_the_raw_value_distinguishes_two_clamped_economies(self):
        """Both report ε = 0; only `epsilon_raw` says they differ."""
        deep = LE.low_epsilon_obligation_sensitivity(RS1965_BROAD_HUMAN_PC)
        shallow = LE.low_epsilon_obligation_sensitivity(CZ1965_BROAD_HUMAN_PC)
        d0, s0 = deep["rows"][0], shallow["rows"][0]
        assert d0["epsilon"] == s0["epsilon"] == 0.0
        assert d0["epsilon_raw"] < s0["epsilon_raw"]


class TestTheStateIsTheCallersToSupply:

    def test_supplying_capital_lifts_a_clamped_reading(self):
        """CZ1965 clamps against the canonical arc and does not against its own capital."""
        canonical = LE.labour_epsilon(
            "broad", population=1e8, population_15_plus_supplied=8e7,
            unpaid_per_15plus=1176.5, paid_per_15plus=1678.2,
        )
        assert canonical["clamped"] is True

        own = LE.labour_epsilon(
            "broad", population=1e8, population_15_plus_supplied=8e7,
            unpaid_per_15plus=1176.5, paid_per_15plus=1678.2,
            obligation_state={"capital_stock": 16_000.0 * REFERENCE_FRAME_POPULATION},
        )
        assert own["clamped"] is False
        assert own["epsilon"] > 0.0
        assert own["total_obligation_per_capita"] > canonical["total_obligation_per_capita"]

    def test_the_keys_come_from_total_eoh_not_from_a_copy(self):
        keys = LE.obligation_state_keys()
        assert "capital_stock" in keys and "ecosystem_health" in keys
        assert not (keys & LE.OBLIGATION_STATE_OWNED)

    @pytest.mark.parametrize("owned", ["epsilon", "population", "basis"])
    def test_the_keys_the_solve_owns_are_refused(self, owned):
        with pytest.raises(ValueError, match="owns them"):
            LE.labour_epsilon("core", obligation_state={owned: 0.3})

    def test_an_unknown_key_is_refused_by_name(self):
        with pytest.raises(ValueError, match="no such total_eoh parameter"):
            LE.labour_epsilon("core", obligation_state={"capital_stock_teh": 1.0})


class TestTheDiagnosticDoesNotChangeTheArc:

    def test_it_sweeps_the_declared_grid(self):
        s = LE.low_epsilon_obligation_sensitivity(US2024_BROAD_HUMAN_PC)
        assert [r["capital_per_capita"] for r in s["rows"]] == list(
            LOW_EPSILON_CAPITAL_PROBE_TEH_PER_CAPITA
        )
        assert s["reporting_only"] is True

    def test_the_obligation_rises_with_capital(self):
        s = LE.low_epsilon_obligation_sensitivity(US2024_BROAD_HUMAN_PC)
        tot = [r["total_obligation_per_capita"] for r in s["rows"]]
        assert tot == sorted(tot), "more capital must not lower the obligation"

    def test_a_deeply_clamped_economy_needs_more_capital_to_lift(self):
        """The ORDERING is the claim: RS1965 clamps harder than US1965."""
        rs = LE.low_epsilon_obligation_sensitivity(RS1965_BROAD_HUMAN_PC)
        us = LE.low_epsilon_obligation_sensitivity(US2024_BROAD_HUMAN_PC)
        assert us["unclamps_at"] is not None
        assert rs["unclamps_at"] is None or rs["unclamps_at"] > us["unclamps_at"]

    def test_the_canonical_arc_still_holds_no_capital_at_zero(self):
        """
        The theory claim this diagnostic exposes must still be TRUE, or the
        diagnostic is describing something that was quietly changed.
        """
        from hours_eoh.core.trajectory import canonical_physical_state
        assert canonical_physical_state(0.0)["capital_stock_teh"] == 0.0
