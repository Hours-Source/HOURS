"""
Tests for the λ derivation (research/thermal_lambda.py).

λ was the thermal layer's largest unquantified lever. These pin the derivation,
the frame discipline that keeps historical and equilibrium λ from being mixed,
and the sensitivity band that must travel with every ψ*-derived figure.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import THERMAL_LAMBDA_FEEDBACK
from hours_eoh.research.thermal_lambda import (
    budget_forcing_headroom,
    lambda_for_frame,
    lambda_sensitivity,
    load_climate_feedback,
)


# ---------------------------------------------------------------------------
# the derivation
# ---------------------------------------------------------------------------

def test_historical_lambda_is_derived_from_shipped_data():
    h = load_climate_feedback()["historical"]
    assert h["central"] == pytest.approx(1.492, rel=0.01)
    assert h["tier"] == "A"


def test_derivation_is_not_window_sensitive():
    """Four windows spanning 1995-2024 agree within 5% — the estimate is a
    property of the data, not of the window chosen."""
    w = load_climate_feedback()["historical"]["windows"]
    assert len(w) >= 4
    lo, hi = min(w.values()), max(w.values())
    assert (hi - lo) / lo < 0.05


def test_pattern_effect_has_the_expected_sign_and_scale():
    """Historical runs high because warming has been concentrated where feedbacks
    stabilise. A negative or huge value would mean the derivation is wrong."""
    d = load_climate_feedback()
    pe = d["pattern_effect"]["value"]
    assert 0.0 < pe < 0.5
    assert pe == pytest.approx(
        d["historical"]["central"] - d["equilibrium"]["ar6_implied"]["lambda"], abs=0.01)


def test_shipped_default_is_conservative():
    """The pre-existing 1.2 turns out to sit BELOW both the AR6-implied and the
    derived historical value — a lower λ means a smaller budget and a larger
    obligation, so the constant was not flattering the framework."""
    d = load_climate_feedback()
    assert THERMAL_LAMBDA_FEEDBACK == d["equilibrium"]["shipped_default"]
    assert THERMAL_LAMBDA_FEEDBACK < d["equilibrium"]["ar6_implied"]["lambda"]
    assert THERMAL_LAMBDA_FEEDBACK < d["historical"]["central"]
    assert d["equilibrium"]["implied_ecs_k"] == pytest.approx(3.28, abs=0.05)


# ---------------------------------------------------------------------------
# the frame discipline
# ---------------------------------------------------------------------------

def test_each_frame_carries_what_it_pairs_with():
    eq = lambda_for_frame("equilibrium")
    hi = lambda_for_frame("historical")
    assert eq["value"] < hi["value"]
    assert "commitment" in eq["pairs_with"]
    assert "rejects" in hi["pairs_with"]
    assert eq["caveat"] is None and hi["caveat"] is not None


def test_mixing_frames_is_refused_not_silently_computed():
    """The single largest way to overstate the allowance — so it raises."""
    with pytest.raises(ValueError, match="historical-magnitude"):
        budget_forcing_headroom(3.0, "equilibrium", lam=1.5)


def test_historical_frame_is_available_when_asked_for_deliberately():
    v = budget_forcing_headroom(3.0, "historical")
    assert v == pytest.approx(1.110, abs=0.01)
    assert v > budget_forcing_headroom(3.0, "equilibrium")


def test_equilibrium_lambda_below_the_guard_is_allowed():
    assert budget_forcing_headroom(3.0, "equilibrium", lam=1.31) == pytest.approx(
        1.31 * 3.0 - 3.366, abs=1e-9)


def test_rejects_unknown_frame():
    with pytest.raises(ValueError):
        lambda_for_frame("vibes")          # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# sensitivity as a first-class output
# ---------------------------------------------------------------------------

def test_sensitivity_spans_zero_to_an_order_of_magnitude():
    """The headline: across AR6's own likely range the budget runs from ZERO to
    ~11x the shipped case. λ uncertainty alone can close the budget."""
    rows = lambda_sensitivity(3.0)
    budgets = [r["budget_tw"] for r in rows]
    assert min(budgets) == 0.0
    assert max(budgets) / next(r["budget_tw"] for r in rows if r["label"] == "shipped default") > 5.0


def test_high_sensitivity_end_is_unbudgeted():
    """At ECS 5 K there is no thermal allowance at all at ΔT_max = 3.0 K — a
    finding about λ, entirely separate from the forcing-band determinacy map."""
    hi = next(r for r in lambda_sensitivity(3.0) if "likely-high" in r["label"])
    assert hi["unbudgeted"] is True
    assert hi["budget_tw"] == 0.0


def test_historical_row_is_flagged_as_frame_mismatched():
    row = next(r for r in lambda_sensitivity(3.0) if r["label"] == "derived historical")
    assert row["frame"] == "historical"
    assert "FRAME MISMATCH" in row["note"]
    assert row["vs_shipped"] > 4.0


def test_sensitivity_is_monotone_in_lambda():
    rows = sorted(lambda_sensitivity(3.0), key=lambda r: r["lambda"])
    hr = [r["headroom_w_m2"] for r in rows]
    assert all(a < b for a, b in zip(hr, hr[1:]))


# ---------------------------------------------------------------------------
# the two-axis determinacy map
# ---------------------------------------------------------------------------

from hours_eoh.research.thermal_lambda import (            # noqa: E402
    determinacy_gain_from_tightening,
    determinacy_map,
)


def test_carrying_lambda_can_only_widen_the_band():
    """Determinacy needs the WHOLE parameter box to agree, so an extra uncertain
    axis never buys agreement. This is the property that makes the two-axis map
    honest rather than convenient — it makes the framework's strongest claim
    HARDER to reach, not easier."""
    m = determinacy_map(3.0)
    v = m["vs_single_axis"]
    assert m["indeterminate_width_k"] > v["single_width_k"]
    assert v["widening_factor"] == pytest.approx(2.01, rel=0.02)
    assert m["unbudgeted_below_k"] < v["single_unbudgeted_below_k"]
    assert m["budgeted_above_k"] > v["single_budgeted_above_k"]


def test_two_axis_thresholds_on_the_likely_range():
    m = determinacy_map(3.0)
    assert m["confidence"] == "likely"
    assert m["lambda_band"] == pytest.approx((0.983, 1.572), abs=0.002)
    assert m["unbudgeted_below_k"] == pytest.approx(1.655, abs=0.01)
    assert m["unbudgeted_below_txx_k"] == pytest.approx(2.450, abs=0.01)
    assert m["zone"] == "indeterminate"


def test_very_likely_is_the_conservative_bound():
    m = determinacy_map(3.0, confidence="very_likely")
    assert m["lambda_band"] == pytest.approx((0.786, 1.965), abs=0.002)
    assert m["unbudgeted_below_txx_k"] == pytest.approx(1.960, abs=0.01)
    assert m["indeterminate_width_k"] > determinacy_map(3.0)["indeterminate_width_k"]


def test_the_ranges_are_labelled_correctly():
    """An earlier revision shipped ECS [2, 5] — AR6's VERY LIKELY range — labelled
    'likely'. That overstated the uncertainty and understated the framework's
    determinate claim, so the labelling is pinned."""
    r = load_climate_feedback()["equilibrium"]["ar6_ranges"]
    assert r["likely_66pct"]["ecs_k"] == [2.5, 4.0]
    assert r["very_likely_90pct"]["ecs_k"] == [2.0, 5.0]
    assert "_correction" in r


def test_the_unbudgeted_threshold_falls_near_present_land_extremes():
    """The uncomfortable consequence: with full AR6 λ uncertainty carried, the
    determinately-unbudgeted zone sits at ~1.96 K of land TXx, and observed land
    TXx is already ~1.8 K. The single-axis 3.21 K claim rested on a λ held fixed
    at a value nobody had assessed."""
    m = determinacy_map(3.0)
    assert 2.2 < m["unbudgeted_below_txx_k"] < 2.7           # likely range
    assert 1.8 < determinacy_map(3.0, confidence="very_likely")["unbudgeted_below_txx_k"] < 2.2


def test_lambda_dominates_the_indeterminacy():
    """Where to spend assessment effort: λ is worth ~2x the forcing estimate."""
    a = determinacy_map(3.0)["attribution"]
    assert a["dominant_axis"] == "lambda"
    assert a["lambda_over_forcing"] == pytest.approx(1.02, rel=0.1)
    vl = determinacy_map(3.0, confidence="very_likely")["attribution"]
    assert vl["lambda_over_forcing"] > a["lambda_over_forcing"]


def test_zones_at_the_extremes():
    assert determinacy_map(1.0)["zone"] == "determinate_unbudgeted"
    assert determinacy_map(6.0)["zone"] == "determinate_budgeted"
    assert determinacy_map(1.0)["robust"] and determinacy_map(3.0)["robust"] is False


def test_tightening_lambda_recovers_determinacy():
    """A tighter assessed λ buys back kelvin of determinate zone — the concrete
    argument for assessing it rather than carrying AR6's full likely range."""
    tight = determinacy_gain_from_tightening((1.10, 1.45))
    assert tight["gain_vs_ar6_likely_k"] > 0.0
    assert tight["width_reduction_k"] > 0.5
    assert tight["unbudgeted_below_txx_k"] > determinacy_map(3.0)["unbudgeted_below_txx_k"]


def test_map_rejects_inverted_bands():
    with pytest.raises(ValueError):
        determinacy_map(3.0, lam_band=(1.5, 1.0))
    with pytest.raises(ValueError):
        determinacy_map(3.0, f_band=(4.0, 2.0))


# ---------------------------------------------------------------------------
# the headline: determinacy first, numbers second
# ---------------------------------------------------------------------------

from hours_eoh.research.thermal_lambda import thermal_verdict     # noqa: E402


def test_indeterminate_withholds_the_number():
    """The point of leading with determinacy: where the box spans both regimes
    the budget is WITHHELD, not estimated. A number there would be a point
    estimate from inside a band containing both 'no budget' and 'ample budget'."""
    v = thermal_verdict(3.0)
    assert v["zone"] == "indeterminate"
    assert v["robust"] is False
    assert v["budget_tw"] is None and v["overage_tw"] is None
    assert "cannot report the sign" in v["claim"]


def test_indeterminate_says_what_would_resolve_it():
    v = thermal_verdict(3.0)
    assert v["what_would_resolve"] is not None
    assert "λ" in v["what_would_resolve"]


def test_determinate_unbudgeted_releases_the_overage():
    """The framework's strongest available claim, and the only zone where the
    overage means something."""
    v = thermal_verdict(1.0)
    assert v["zone"] == "determinate_unbudgeted"
    assert v["robust"] and v["budget_tw"] == 0.0
    assert v["overage_tw"] > 0.0
    assert v["what_would_resolve"] is None


def test_determinate_budgeted_reports_the_worst_corner():
    """A budget reported here is a LOWER bound — what survives the least
    favourable corner of the box, not the central estimate."""
    v = thermal_verdict(6.0)
    assert v["zone"] == "determinate_budgeted"
    assert v["budget_tw"] > 0.0
    central = (1.2 * 6.0 - 3.366) * 5.101e14 / 1e12
    assert v["budget_tw"] < central


def test_single_axis_is_marked_superseded():
    """It must remain callable — §4.2 was published against it — but must not be
    mistaken for the honest map."""
    from hours_eoh.research.thermal_path_c import determinacy_zone
    assert "SUPERSEDED" in determinacy_zone.__doc__
    assert "thermal_lambda" in determinacy_zone.__doc__
    assert determinacy_zone(3.0)["zone"] == "indeterminate"


# ===========================================================================
# The Planck bound — SIGMA_SB finally doing work (2026-08-17)
# ===========================================================================

from hours_eoh.data import EARTH_EMISSION_TEMPERATURE_K, SIGMA_SB, THERMAL_LAMBDA_FEEDBACK
from hours_eoh.research.thermal_lambda import lambda_admissibility, planck_feedback


class TestPlanckFeedbackIsDerivedNotRecalled:

    def test_it_is_the_derivative_of_stefan_boltzmann(self):
        """λ_P = dE/dT for E = σT⁴, evaluated from the constants themselves."""
        assert planck_feedback(255.0) == pytest.approx(
            4.0 * SIGMA_SB * 255.0 ** 3, rel=1e-15
        )

    def test_it_reproduces_the_worked_example(self):
        assert planck_feedback() == pytest.approx(3.7609, abs=1e-4)

    def test_it_uses_the_named_constants_not_literals(self):
        assert planck_feedback(EARTH_EMISSION_TEMPERATURE_K) == planck_feedback()

    def test_it_scales_as_the_cube_of_temperature(self):
        assert planck_feedback(510.0) == pytest.approx(8.0 * planck_feedback(255.0), rel=1e-12)

    def test_non_physical_temperature_rejected(self):
        for bad in (0.0, -1.0):
            with pytest.raises(ValueError, match="t_emission"):
                planck_feedback(bad)


class TestLambdaAdmissibility:
    """
    λ is the repo's most leveraged parameter after ΔT_lo and had no physical
    anchor of any kind. This supplies the only one that exists — not narrowing
    the assessed range, which physics cannot do, but stating where it cannot go.
    """

    def test_the_shipped_lambda_is_admissible(self):
        r = lambda_admissibility()
        assert r["admissible"]
        assert r["lambda"] == THERMAL_LAMBDA_FEEDBACK

    def test_a_lambda_above_the_planck_bound_is_refused(self):
        """
        Not a tuning question: λ ≥ λ_Planck implies net STABILISING feedbacks
        stronger than the blackbody response, which no assessment supports.
        """
        assert not lambda_admissibility(lam=4.0)["admissible"]
        assert not lambda_admissibility(lam=planck_feedback())["admissible"]

    def test_the_implied_net_feedback_is_reported(self):
        """The quantity a reader can check against the literature."""
        r = lambda_admissibility()
        assert r["implied_net_feedback"] == pytest.approx(
            r["planck_bound"] - r["lambda"], rel=1e-12
        )
        assert 2.0 < r["implied_net_feedback"] < 3.0

    def test_the_bound_is_deliberately_loose(self):
        """
        The blackbody Planck term (3.761) exceeds the real Planck response
        (≈3.2, the figure the repo carried as prose), so the ceiling errs toward
        admitting too much λ rather than too little — the safe direction.
        """
        assert planck_feedback() > 3.2
        assert "loose" in lambda_admissibility()["note"]
