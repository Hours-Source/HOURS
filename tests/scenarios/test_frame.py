"""
Tests for scenarios/frame.py — jurisdiction frames (Phase 0).

The module is REPORTING ONLY, so the most important test in this file is
`TestFrameChangesNothing`: the same discipline as `TestPIChangesNothing`.
"""

import math

import pytest

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    JURISDICTION_FRAMES,
    LAND_HECTARES_PER_CAPITA,
    US_MAINLAND_HECTARES,
    US_REFERENCE_POPULATION,
    WORLD_POPULATION,
)
from hours_eoh.scenarios.frame import (
    FRAME_CONSISTENCY_TOLERANCE,
    REFERENCE_FRAME_POPULATION,
    at_frame,
    frame_check,
    frame_for,
    frame_report,
    hectares_per_capita,
    shipped_default_mismatch,
)

KEY_EPSILONS = [0.0, 0.40, 0.99]


class TestFramesAreBoundNotRestated:
    """
    Every frame value must come FROM the constant that already carries it. A
    restated 335,000,000 would be the sixth copy-of-a-value-whose-source-is-
    elsewhere in this repo's history.
    """

    def test_us_frame_is_the_us_constants(self):
        f = frame_for("us_mainland")
        assert f["population"] == US_REFERENCE_POPULATION
        assert f["land_hectares"] == US_MAINLAND_HECTARES

    def test_global_frame_derives_from_the_per_capita_constant(self):
        f = frame_for("global")
        assert f["population"] == WORLD_POPULATION
        assert f["land_hectares"] == pytest.approx(
            WORLD_POPULATION * LAND_HECTARES_PER_CAPITA, rel=1e-12
        )
        # and therefore reproduces the shipped per-capita figure exactly
        assert hectares_per_capita(**f) == pytest.approx(
            LAND_HECTARES_PER_CAPITA, rel=1e-12
        )

    def test_reference_1m_carries_the_us_ratio_not_the_us_area(self):
        """
        The consistent million-person frame. The whole point is that it is NOT
        the whole contiguous US, which is what the shipped default pairs with.
        """
        f = frame_for("reference_1m")
        assert f["population"] == 1_000_000.0
        assert hectares_per_capita(**f) == pytest.approx(
            US_MAINLAND_HECTARES / US_REFERENCE_POPULATION, rel=1e-12
        )
        assert f["land_hectares"] < US_MAINLAND_HECTARES / 100.0

    def test_unknown_frame_raises_rather_than_defaulting(self):
        with pytest.raises(KeyError, match="unknown frame"):
            frame_for("atlantis")


class TestTheMismatchIsReported:

    def test_shipped_default_is_not_a_declared_frame(self):
        """THE FINDING. 1M people holding the whole contiguous US."""
        m = shipped_default_mismatch()
        assert m["shipped_is_declared_frame"] is False
        assert m["honest_is_declared_frame"] is True
        assert m["population_mismatch_factor"] == pytest.approx(335.0, rel=1e-9)
        assert m["shipped_hectares_per_capita"] > 700.0
        assert m["honest_hectares_per_capita"] == pytest.approx(2.285, abs=1e-3)

    def test_declared_frames_are_self_consistent(self):
        for name in JURISDICTION_FRAMES:
            f = frame_for(name)
            chk = frame_check(f["population"], f["land_hectares"])
            assert chk["consistent"], f"{name} is not consistent with itself"
            assert chk["ratio_to_nearest"] == pytest.approx(1.0, abs=FRAME_CONSISTENCY_TOLERANCE)


class TestDeclaringTheFrameMakesTheShareInVARIANT:
    """
    The result worth keeping. Once population and land travel together, the
    ecological share stops depending on the frame — because ecological and
    personal then scale by the same factor. The 424x spread in the shipped
    table is entirely the UNDECLARED pairing, not a real range.
    """

    def test_share_is_frame_invariant_across_declared_frames(self):
        for eps in KEY_EPSILONS:
            shares = [at_frame(n, eps)["ecological_share"] for n in JURISDICTION_FRAMES]
            # us_mainland and reference_1m carry an identical ha/person ratio, so
            # they must agree to float precision despite a 335x population gap.
            us = at_frame("us_mainland", eps)["ecological_share"]
            ref = at_frame("reference_1m", eps)["ecological_share"]
            assert us == pytest.approx(ref, rel=1e-9)
            # global differs only by its different land-per-person ratio (1.65
            # vs 2.285), so the whole declared spread stays inside ~2x.
            assert max(shares) / min(shares) < 2.0

    def test_the_default_is_no_longer_an_outlier_at_all(self):
        """
        PHASE 4b CLOSED THIS COMPLETELY, and the result is sharper than the fix
        aimed at. When this module was written the shipped default sat 464x
        above every declared frame, because it paired the whole contiguous US
        with a million people.

        The default now resolves its ecological area from the population through
        LAND_HECTARES_PER_CAPITA — which is the planetary ratio — so it does not
        merely fall into the declared range, it COINCIDES with the `global`
        frame to float precision. The whole remaining spread across the table is
        1.385x, and that is the honest difference between 1.65 and 2.285
        hectares per person rather than a frame nobody chose.
        """
        r = frame_report(0.40)
        undeclared = [x for x in r["rows"] if not x["declared"]]
        assert len(undeclared) == 1
        glob = next(x for x in r["rows"] if x["frame"] == "global")
        # at_frame pins the pre-partition policy (see scenarios/frame.py), so the
        # comparison must too, or it compares a live share against a zero one.
        assert undeclared[0]["ecological_share"] == pytest.approx(
            glob["ecological_share"], rel=1e-12
        )
        assert r["share_spread"] < 2.0

    def test_per_capita_ecological_hours_are_tiny_at_every_declared_frame(self):
        """
        The magnitude finding, pinned. Under every declared frame the ecological
        obligation is well under one hour per person per year, against personal
        at ~1,300. This is the number the GUF derivation exists to replace, and
        it must not drift unnoticed while that work happens.
        """
        for eps in KEY_EPSILONS:
            for name in JURISDICTION_FRAMES:
                r = at_frame(name, eps)
                assert 0.0 < r["ecological_h_per_capita"] < 1.0
                assert r["personal_h_per_capita"] > 1_000.0


class TestFrameChangesNothing:
    """
    REPORTING ONLY. Phase 0 introduces a vocabulary, not a calibration change.
    If this class ever fails, the frame work has started moving numbers and
    needs the sign-off the note reserves for it.
    """

    def test_shipped_totals_are_untouched(self):
        # Re-pinned by Phase 4b (2026-08-17): the default now resolves the
        # ecological area from the population instead of assuming the whole
        # contiguous US, and KNOWLEDGE_EOH_BASE followed that internal drift to
        # its fixed point (its tag block says it does). Both are the change, not
        # a regression — what this class guards is that nothing moves WITHOUT a
        # recorded mechanism.
        expected = {
            0.0:  1437433591.3146708,
            0.40: 1594839428.9158642,
            0.99: 2512156421.097694,
        }
        for eps, want in expected.items():
            assert total_eoh(epsilon=eps)["total"] == want

    def test_at_frame_agrees_with_a_hand_built_call(self):
        """
        at_frame must be a convenience over the public API, not a second path —
        and the hand-built call has to carry ALL THREE extensive quantities.
        Population and land are the obvious pair; capital is the one that hides,
        because CAPITAL_STOCK_DEFAULT is stated at the 1M reference population
        and looks like a plain default until the frame moves.
        """
        for eps in KEY_EPSILONS:
            f = frame_for("us_mainland")
            direct = total_eoh(
                # at_frame pins the pre-partition policy; match it or the two
                # sides differ by the whole relocated obligation.
                ecological_standing_response="domain",
                ecological_health_response="domain",
                epsilon=eps,
                population=f["population"],
                ecological_area_hectares=f["land_hectares"],
                capital_stock=CAPITAL_STOCK_DEFAULT
                * (f["population"] / REFERENCE_FRAME_POPULATION),
            )
            via = at_frame("us_mainland", eps)
            assert via["total_eoh"] == direct["total"]
            assert via["ecological_eoh"] == direct["ecological"]

    def test_capital_per_capita_is_what_the_frame_holds_fixed(self):
        """
        The frame preserves capital INTENSITY, not the absolute stock. Without
        this, at_frame("us_mainland") models 335M people on the capital of 1M
        (5.97 TEH/capita against 2,000) and the ecological share reads 5.7% off.
        """
        ref_intensity = CAPITAL_STOCK_DEFAULT / REFERENCE_FRAME_POPULATION
        for name in JURISDICTION_FRAMES:
            f = frame_for(name)
            scaled = CAPITAL_STOCK_DEFAULT * (f["population"] / REFERENCE_FRAME_POPULATION)
            assert scaled / f["population"] == pytest.approx(ref_intensity, rel=1e-12)

    def test_overrides_reach_total_eoh(self):
        base = at_frame("us_mainland", 0.40)["total_eoh"]
        moved = at_frame("us_mainland", 0.40, personal_base=2000.0)["total_eoh"]
        assert moved != base

    def test_explicit_ecological_base_override_does_not_trip_the_guard(self):
        # Supplying an absolute base must drop the frame's area rather than
        # sending both into total_eoh, which refuses the combination.
        r = at_frame("us_mainland", 0.40, ecological_base=1_000_000.0)
        assert math.isfinite(r["ecological_eoh"])
        # `at_frame` evaluates at the pre-partition policy (see frame.py), so
        # the supplied base scales the full baseline. What this test guards is
        # the base/area GUARD, not the level.
        assert r["ecological_eoh"] == pytest.approx(1_000_000.0 / 0.70, rel=1e-9)


class TestArcCoherence:

    def test_every_frame_resolves_across_the_arc(self):
        for eps in [0.0, 0.40, 0.90, 0.99]:
            for name in JURISDICTION_FRAMES:
                r = at_frame(name, eps)
                assert math.isfinite(r["total_eoh"]) and r["total_eoh"] > 0.0
                assert 0.0 < r["ecological_share"] < 1.0

    def test_zero_population_rejected(self):
        with pytest.raises(ValueError, match="population"):
            hectares_per_capita(0.0, 1.0e6)
