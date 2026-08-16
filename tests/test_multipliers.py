"""
Tests for hours_eoh.core.multipliers

Covers: population_weighted_mean_multiplier, multiplier_band_check,
tier_multiplier, epoch_alpha_weights.
"""

import pytest

from hours_eoh.core.multipliers import (
    population_weighted_mean_multiplier,
    multiplier_band_check,
    tier_multiplier,
    epoch_alpha_weights,
    scarcity_score,
    validate_training_duration,
    detect_artificial_scarcity,
    tier_expiry_check,
    reclassification_impact,
    compute_impact_score,
    assess_tier,
)
from hours_eoh.data import (
    DEFAULT_SEGMENTS, M_BAND_LOW, M_BAND_HIGH,
    SCARCITY_SEVERE_THRESHOLD, TIER_ASSESSMENT_INTERVAL_YEARS,
    ALPHA_SCALE,
    ALPHA_IMPACT_EOH_REDUCTION_WEIGHT, ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT,
    ALPHA_IMPACT_RESILIENCE_WEIGHT,
    GOVERNANCE_IRR_WARN_THRESHOLD, GOVERNANCE_IRR_CRIT_THRESHOLD,
    GOVERNANCE_MIN_ASSESSORS,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


class TestMeasuredWorkforceIsTheDefault:
    """THE PIN THAT WAS MISSING, and its absence is the finding.

    Swapping the default workforce from the synthetic `DEFAULT_SEGMENTS` to the
    measured O*NET/BLS registry moved the Condition II mean 2.100 → 1.9964
    (−4.93%) and **the full suite stayed green**. The quantity the multiplier
    block exists to govern was pinned nowhere — the same shape as the
    `GUF_PSI_NORM` fee-curve peak, found the same way, a week apart.

    Two things are asserted, and the second is the one that matters:
    the level, so the swap cannot silently reverse; and that the measured mean
    sits inside the band on its OWN evidence rather than on the band's.
    """

    def test_default_is_the_measured_registry_not_the_synthetic_tiers(self):
        from hours_eoh.reference.onet_multipliers import registry_segments

        assert population_weighted_mean_multiplier() == pytest.approx(
            population_weighted_mean_multiplier(registry_segments()), rel=1e-12
        )
        assert population_weighted_mean_multiplier() == pytest.approx(
            1.9964, abs=0.001
        )

    def test_measured_mean_is_bound_to_the_registry(self):
        """MEAN_MULTIPLIER_REFERENCE is bound by TEST, not by expression.

        `data.py` sits below `reference/` and cannot import it — the same
        constraint `AGE_WEIGHT_ELDERLY` and `GUF_ECO_KAPPA_CARBON` are bound
        under. So this fails whichever side moves alone: an O*NET/BLS vintage
        refresh that changes the registry mean, or an edit to the constant that
        is not backed by one.

        It matters more than a usual freeze check because this constant is now
        the default `mean_multiplier` in eleven core functions — the EOH→TEH
        pipeline, teh_created, three fiscal functions, both price functions,
        the simulation engine and condition_ii. It is the rate at which all TEH
        is minted.
        """
        from hours_eoh.data import MEAN_MULTIPLIER_REFERENCE
        from hours_eoh.reference.onet_multipliers import registry_segments

        assert MEAN_MULTIPLIER_REFERENCE == pytest.approx(
            population_weighted_mean_multiplier(registry_segments()), rel=1e-12
        )

    def test_the_operating_mean_is_not_the_band_target(self):
        """The check and the thing checked must not be the same number.

        Until 2026-08-16 eleven core functions defaulted to a bare 2.10 — which
        is M_BAND_TARGET, a NORMATIVE charter decision, standing in for the
        measured rate at which TEH is minted. Condition II then verified a
        measured economy against a target it had been seeded with.

        The two are now distinct, and this test exists to keep them that way.
        If a future edit makes them equal again it is either a coincidence worth
        stating explicitly or the same error returning.
        """
        from hours_eoh.data import MEAN_MULTIPLIER_REFERENCE, M_BAND_TARGET

        assert MEAN_MULTIPLIER_REFERENCE != M_BAND_TARGET
        assert MEAN_MULTIPLIER_REFERENCE < M_BAND_TARGET, (
            "the measured workforce sits BELOW the charter target — if this "
            "flips, Condition II's headroom argument needs rewriting"
        )

    def test_the_measured_mean_is_inside_the_band_on_its_own_evidence(self):
        """`in_band: True` meant strictly less before this change than after.

        DEFAULT_SEGMENTS' means were reverse-engineered so the weighted mean
        landed on 2.10 — the band's own ceiling — so the check could not fail
        and told you nothing. The measured mean is not built from the band and
        lands 0.104 BELOW the target, inside [1.8, 2.1] because the measured
        workforce happens to be, which is a result rather than a construction.
        """
        measured = population_weighted_mean_multiplier()
        check = multiplier_band_check(measured)
        assert check["in_band"] is True
        assert check["mean_multiplier"] < M_BAND_HIGH, (
            "measured mean must sit strictly inside the band, not on its ceiling"
        )
        assert population_weighted_mean_multiplier(DEFAULT_SEGMENTS) == \
            pytest.approx(M_BAND_HIGH, abs=1e-9), (
                "the synthetic set sat exactly ON the ceiling — that is what "
                "'calibrated to a target' means, and why it is now superseded"
            )


class TestMultiplierSystem:

    def test_synthetic_segments_still_reproduce_their_calibrated_mean(self):
        """DEFAULT_SEGMENTS is retired, not deleted: it is the comparison the
        measured default is measured against, and reproducing a pre-2026-08-16
        figure means passing it explicitly."""
        mean = population_weighted_mean_multiplier(DEFAULT_SEGMENTS)
        assert mean == pytest.approx(2.10, abs=0.01), (
            f"Default segments should produce mean ≈ 2.10, got {mean:.4f}"
        )

    def test_multiplier_band_check_passes_for_in_range(self):
        """Condition II passes for mean within [1.8, 2.1]."""
        for m in [1.8, 1.9, 2.0, 2.1]:
            result = multiplier_band_check(m)
            assert result["in_band"] is True, f"Mean={m} should be in band"
            assert result["status"] == "OK"

    def test_multiplier_band_check_fails_below_band(self):
        result = multiplier_band_check(1.5)
        assert result["in_band"] is False
        assert result["status"] == "BELOW_BAND"

    def test_multiplier_band_check_fails_above_band(self):
        result = multiplier_band_check(2.5)
        assert result["in_band"] is False
        assert result["status"] == "ABOVE_BAND"

    def test_tier_multiplier_at_all_zeros_returns_one(self):
        """Zero factors → base multiplier of 1.0."""
        m = tier_multiplier(0.0, 0.0, 0.0, 0.0)
        assert m == pytest.approx(1.0)

    def test_tier_multiplier_at_all_ones_returns_m_max(self):
        """Maximum factors → m_max (clamped)."""
        m = tier_multiplier(1.0, 1.0, 1.0, 1.0)
        assert m == pytest.approx(6.0)

    def test_tier_multiplier_rejects_out_of_range_factors(self):
        with pytest.raises(ValueError):
            tier_multiplier(1.5, 0.5, 0.5, 0.5)

    def test_tier_multiplier_mission_statement_example(self):
        """
        High-tier infrastructure engineer: high on all four factors.
        Should produce a multiplier well above 2.0.
        """
        m = tier_multiplier(training=0.8, demand=0.7, scarcity=0.6, impact=0.9)
        assert m > 2.0, f"High-leverage engineer should have m > 2.0, got {m:.2f}"

    def test_epoch_alpha_coefficients_sum_to_alpha_scale(self):
        for eps in KEY_EPSILONS:
            coefficients = epoch_alpha_weights(eps)
            assert sum(coefficients) == pytest.approx(ALPHA_SCALE, abs=1e-6), (
                f"Alpha coefficients must sum to ALPHA_SCALE={ALPHA_SCALE} at ε={eps}, "
                f"got {sum(coefficients):.6f}"
            )

    def test_epoch_alpha_weights_all_positive(self):
        for eps in KEY_EPSILONS:
            weights = epoch_alpha_weights(eps)
            assert all(w > 0 for w in weights), (
                f"All alpha weights must be positive at ε={eps}"
            )


class TestScarcityScore:

    EXPECTED_KEYS = {
        "scarcity", "raw_current", "rolling_mean", "supply_adjusted",
        "window_size", "supply_discount_applied", "status",
    }

    def test_result_keys_present(self):
        result = scarcity_score([(100, 200)])
        assert self.EXPECTED_KEYS == set(result.keys())

    def test_single_entry_basic(self):
        # 100 practitioners, 200 demand → raw scarcity = 0.5
        result = scarcity_score([(100, 200)])
        assert result["raw_current"] == pytest.approx(0.5)
        assert result["rolling_mean"] == pytest.approx(0.5)
        assert result["scarcity"] == pytest.approx(0.5)
        assert result["window_size"] == 1
        assert result["supply_discount_applied"] is False

    def test_rolling_window_uses_last_n(self):
        # Five entries; first two have scarcity 0.9, last three have 0.1
        # With window=3, only last three should be averaged
        history = [(10, 100), (10, 100), (90, 100), (90, 100), (90, 100)]
        result = scarcity_score(history, window=3)
        assert result["window_size"] == 3
        assert result["rolling_mean"] == pytest.approx(0.1, abs=0.01)

    def test_window_larger_than_history(self):
        # window=10 but only 2 entries — should use both without error
        history = [(50, 100), (60, 100)]
        result = scarcity_score(history, window=10)
        assert result["window_size"] == 2

    def test_supply_response_discount_reduces_scarcity(self):
        # High elasticity should reduce scarcity below rolling_mean
        history = [(50, 200)]  # raw = 0.75
        result = scarcity_score(history, supply_elasticity=0.5, supply_lag_years=3)
        assert result["supply_discount_applied"] is True
        assert result["supply_adjusted"] < result["rolling_mean"]
        assert result["scarcity"] < result["rolling_mean"]

    def test_zero_elasticity_no_discount(self):
        history = [(50, 200)]
        result = scarcity_score(history, supply_elasticity=0.0)
        assert result["supply_discount_applied"] is False
        assert result["supply_adjusted"] == pytest.approx(result["rolling_mean"])

    def test_full_employment_zero_scarcity(self):
        # Practitioners meet or exceed demand → scarcity = 0
        history = [(200, 100), (150, 100)]
        result = scarcity_score(history)
        assert result["scarcity"] == pytest.approx(0.0)
        assert result["status"] == "OK"

    def test_severe_scarcity_status(self):
        # 5 practitioners for 100 demand → raw = 0.95 > threshold
        result = scarcity_score([(5, 100)])
        assert result["scarcity"] > SCARCITY_SEVERE_THRESHOLD
        assert result["status"] == "SEVERE_SCARCITY"

    def test_normal_scarcity_status_ok(self):
        # 50 practitioners for 100 demand → raw = 0.5
        result = scarcity_score([(50, 100)])
        assert result["status"] == "OK"

    def test_scarcity_in_unit_interval(self):
        test_cases = [(0, 100), (50, 100), (100, 100), (150, 100), (5, 100)]
        for practitioners, demand in test_cases:
            result = scarcity_score([(practitioners, demand)])
            assert 0.0 <= result["scarcity"] <= 1.0, (
                f"scarcity out of [0,1] for ({practitioners}, {demand}): {result['scarcity']}"
            )

    def test_empty_history_raises(self):
        with pytest.raises(ValueError, match="history"):
            scarcity_score([])

    def test_zero_demand_raises(self):
        with pytest.raises(ValueError, match="demand_eoh"):
            scarcity_score([(10, 0)])

    def test_negative_practitioners_raises(self):
        with pytest.raises(ValueError, match="practitioner"):
            scarcity_score([(-1, 100)])


class TestAntiGamingSafeguards:

    # --- validate_training_duration ---

    def test_training_valid_within_tolerance(self):
        # mandated=5, median=4 → ratio=1.25 < tolerance=1.5 → passes
        result = validate_training_duration(5.0, 4.0)
        assert result["passes"] is True
        assert result["status"] == "OK"
        assert result["ratio"] == pytest.approx(1.25)

    def test_training_inflation_flagged(self):
        # mandated=9, median=4 → ratio=2.25 > tolerance=1.5 → flagged
        result = validate_training_duration(9.0, 4.0)
        assert result["passes"] is False
        assert result["status"] == "TRAINING_INFLATION"

    def test_training_exact_boundary_passes(self):
        # mandated=6, median=4 → ratio=1.5 exactly at tolerance → passes
        result = validate_training_duration(6.0, 4.0)
        assert result["passes"] is True
        assert result["ratio"] == pytest.approx(1.5)

    def test_training_returns_all_fields(self):
        result = validate_training_duration(5.0, 4.0, tolerance_factor=2.0)
        assert set(result.keys()) == {
            "mandated_years", "median_competency_years", "ratio",
            "tolerance_factor", "passes", "status",
        }
        assert result["tolerance_factor"] == pytest.approx(2.0)

    def test_training_zero_mandated_passes(self):
        # A role with no training requirement is valid; ratio = 0 always passes.
        result = validate_training_duration(0.0, 4.0)
        assert result["passes"] is True
        assert result["ratio"] == pytest.approx(0.0)

    def test_training_negative_mandated_raises(self):
        with pytest.raises(ValueError):
            validate_training_duration(-1.0, 4.0)

    def test_training_zero_median_raises(self):
        with pytest.raises(ValueError):
            validate_training_duration(5.0, 0.0)

    # --- detect_artificial_scarcity ---

    def test_detect_scarcity_ok(self):
        # Normal pass rate, no quality data → OK
        result = detect_artificial_scarcity(0.60)
        assert result["passes"] is True
        assert result["status"] == "OK"
        assert result["trigger"] is None

    def test_detect_scarcity_below_floor(self):
        # pass_rate=0.20 < floor=0.30 → ARTIFICIAL_SCARCITY
        result = detect_artificial_scarcity(0.20)
        assert result["passes"] is False
        assert result["status"] == "ARTIFICIAL_SCARCITY"
        assert result["trigger"] == "pass_rate_below_floor"

    def test_detect_scarcity_floor_boundary_ok(self):
        # pass_rate exactly at floor → not flagged by trigger 1
        result = detect_artificial_scarcity(0.30)
        assert result["status"] in ("OK", "ARTIFICIAL_SCARCITY_RISK")

    def test_detect_scarcity_low_quality_differential(self):
        # pass_rate=0.5 (above floor), quality_diff=0.05 < threshold=0.20 → RISK
        result = detect_artificial_scarcity(0.50, quality_differential=0.05)
        assert result["passes"] is False
        assert result["status"] == "ARTIFICIAL_SCARCITY_RISK"
        assert result["trigger"] == "low_quality_differential"

    def test_detect_scarcity_high_quality_differential(self):
        # quality_diff above threshold → OK despite moderate pass rate
        result = detect_artificial_scarcity(0.40, quality_differential=0.50)
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_detect_scarcity_trigger1_takes_precedence(self):
        # Both triggers could fire — trigger 1 (floor) wins
        result = detect_artificial_scarcity(0.10, quality_differential=0.05)
        assert result["status"] == "ARTIFICIAL_SCARCITY"
        assert result["trigger"] == "pass_rate_below_floor"

    def test_detect_scarcity_returns_all_fields(self):
        result = detect_artificial_scarcity(0.50, quality_differential=0.30)
        assert set(result.keys()) == {
            "pass_rate", "floor", "quality_differential", "quality_threshold",
            "passes", "status", "trigger",
        }

    def test_detect_scarcity_invalid_pass_rate_raises(self):
        with pytest.raises(ValueError):
            detect_artificial_scarcity(1.5)

    def test_detect_scarcity_invalid_quality_diff_raises(self):
        with pytest.raises(ValueError):
            detect_artificial_scarcity(0.5, quality_differential=-0.1)

    # --- tier_expiry_check ---

    def test_tier_expiry_current(self):
        # elapsed=3, interval=5 → CURRENT, remaining=2
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2023)
        assert result["status"] == "CURRENT"
        assert result["expired"] is False
        assert result["elapsed"] == 3
        assert result["remaining"] == 2

    def test_tier_expiry_exact_boundary(self):
        # elapsed=5 equals interval=5 → OVERDUE
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2025)
        assert result["status"] == "OVERDUE"
        assert result["expired"] is True
        assert result["remaining"] == 0

    def test_tier_expiry_overdue(self):
        # elapsed=7, interval=5 → OVERDUE, remaining=-2
        result = tier_expiry_check(assigned_epoch=2018, current_epoch=2025)
        assert result["status"] == "OVERDUE"
        assert result["remaining"] == -2

    def test_tier_expiry_just_assigned(self):
        # elapsed=0 → CURRENT, remaining=interval
        result = tier_expiry_check(assigned_epoch=2025, current_epoch=2025)
        assert result["status"] == "CURRENT"
        assert result["elapsed"] == 0
        assert result["remaining"] == TIER_ASSESSMENT_INTERVAL_YEARS

    def test_tier_expiry_custom_interval(self):
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2023, interval_years=2)
        assert result["status"] == "OVERDUE"
        assert result["elapsed"] == 3
        assert result["remaining"] == -1

    def test_tier_expiry_returns_all_fields(self):
        result = tier_expiry_check(2020, 2023)
        assert set(result.keys()) == {
            "assigned_epoch", "current_epoch", "interval_years",
            "elapsed", "remaining", "expired", "status",
        }

    def test_tier_expiry_invalid_epoch_raises(self):
        with pytest.raises(ValueError, match="current_epoch"):
            tier_expiry_check(assigned_epoch=2025, current_epoch=2020)


class TestReclassificationImpact:

    # Reference segments: DEFAULT_SEGMENTS-like distribution with M ≈ 2.10
    _SEGMENTS = [
        {"name": "base",     "fraction": 0.20, "mean_mu": 1.20},
        {"name": "standard", "fraction": 0.50, "mean_mu": 1.87},
        {"name": "advanced", "fraction": 0.25, "mean_mu": 2.80},
        {"name": "elite",    "fraction": 0.05, "mean_mu": 4.50},
    ]

    def test_no_change_delta_zero(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["m_delta"] == pytest.approx(0.0)
        assert result["m_after"] == pytest.approx(result["m_before"])

    def test_upward_reclassification_raises_m(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 3.20}],
        )
        assert result["m_after"] > result["m_before"]
        assert result["m_delta"] > 0.0

    def test_downward_reclassification_lowers_m(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "standard", "new_mean_mu": 1.50}],
        )
        assert result["m_after"] < result["m_before"]
        assert result["m_delta"] < 0.0

    def test_passes_when_m_stays_in_band(self):
        # Starting M ≈ 2.10; reduce advanced 2.80 → 2.70 → new M ≈ 2.075 (in band)
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 2.70}],
        )
        assert result["passes"] is True
        assert result["band_after"]["in_band"] is True

    def test_fails_when_m_leaves_band(self):
        # Large upward shift: elite 4.50 → 6.00 + advanced bump → M > 2.1
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "elite", "new_mean_mu": 6.00},
             {"name": "advanced", "new_mean_mu": 4.00}],
        )
        assert result["passes"] is False
        assert result["band_after"]["status"] == "ABOVE_BAND"

    def test_absorption_to_ceiling_positive_in_band(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["absorption_remaining"]["to_ceiling"] >= 0.0

    def test_absorption_to_floor_positive_in_band(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["absorption_remaining"]["to_floor"] >= 0.0

    def test_further_drift_budget_upward(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 2.90}],
        )
        # upward change → budget = to_ceiling
        assert result["absorption_remaining"]["further_drift_budget"] == pytest.approx(
            result["absorption_remaining"]["to_ceiling"]
        )

    def test_further_drift_budget_downward(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "standard", "new_mean_mu": 1.70}],
        )
        # downward change → budget = to_floor
        assert result["absorption_remaining"]["further_drift_budget"] == pytest.approx(
            result["absorption_remaining"]["to_floor"]
        )

    def test_result_keys_present(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert {"segments_before", "segments_after", "m_before", "m_after", "m_delta",
                "band_before", "band_after", "passes", "changes_applied",
                "absorption_remaining"} == set(result.keys())
        assert {"to_ceiling", "to_floor", "further_drift_budget"} == set(
            result["absorption_remaining"].keys()
        )

    def test_invalid_segment_name_raises(self):
        with pytest.raises(ValueError):
            reclassification_impact(
                self._SEGMENTS,
                [{"name": "nonexistent", "new_mean_mu": 2.0}],
            )

    def test_segments_not_mutated(self):
        import copy
        original = copy.deepcopy(self._SEGMENTS)
        reclassification_impact(self._SEGMENTS, [{"name": "advanced", "new_mean_mu": 3.50}])
        assert self._SEGMENTS == original

    def test_multiple_changes(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "base", "new_mean_mu": 1.30},
             {"name": "standard", "new_mean_mu": 2.00}],
        )
        # Both changes are applied
        after_names = {s["name"]: s["mean_mu"] for s in result["segments_after"]}
        assert after_names["base"] == pytest.approx(1.30)
        assert after_names["standard"] == pytest.approx(2.00)


class TestTierMultiplierAdditiveFormula:

    def test_formula_is_additive_single_factor(self):
        """Single non-zero coefficient: m = 1 + a1*T, strictly additive."""
        m = tier_multiplier(0.5, 0.0, 0.0, 0.0, alpha_coefficients=(2.0, 0.0, 0.0, 0.0))
        assert m == pytest.approx(2.0), (
            f"Expected 1 + 2.0×0.5 = 2.0, got {m}"
        )

    def test_cap_still_enforced_with_large_coefficients(self):
        """Huge coefficients with all-ones factors must clamp to M_MAX."""
        from hours_eoh.data import M_MAX
        m = tier_multiplier(1.0, 1.0, 1.0, 1.0, alpha_coefficients=(10.0, 10.0, 10.0, 10.0))
        assert m == pytest.approx(M_MAX)

    def test_floor_at_zero_factors(self):
        """All-zero factors always produce exactly 1.0 regardless of coefficients."""
        m = tier_multiplier(0.0, 0.0, 0.0, 0.0, alpha_coefficients=(3.0, 1.0, 0.5, 0.5))
        assert m == pytest.approx(1.0)

    def test_arc_coherence_coefficients(self):
        """At each key ε, epoch_alpha_weights() returns positive coefficients summing to ALPHA_SCALE."""
        for eps in KEY_EPSILONS:
            coefficients = epoch_alpha_weights(eps)
            assert len(coefficients) == 4
            assert all(c > 0 for c in coefficients), (
                f"All coefficients must be positive at ε={eps}: {coefficients}"
            )
            assert sum(coefficients) == pytest.approx(ALPHA_SCALE, abs=1e-6), (
                f"Coefficients must sum to ALPHA_SCALE={ALPHA_SCALE} at ε={eps}"
            )


class TestComputeImpactScore:

    def test_weighted_sum_known_values(self):
        """I = w_eoh×0.8 + w_cov×0.6 + w_res×0.4 with default weights."""
        expected = (
            ALPHA_IMPACT_EOH_REDUCTION_WEIGHT * 0.8
            + ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT * 0.6
            + ALPHA_IMPACT_RESILIENCE_WEIGHT * 0.4
        )
        result = compute_impact_score(
            eoh_reduction_fraction=0.8,
            domain_coverage=0.6,
            resilience_contribution=0.4,
        )
        assert result == pytest.approx(expected, abs=1e-9)

    def test_all_ones_returns_one(self):
        assert compute_impact_score(1.0, 1.0, 1.0) == pytest.approx(1.0)

    def test_all_zeros_returns_zero(self):
        assert compute_impact_score(0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            compute_impact_score(1.5, 0.5, 0.5)

    def test_weight_mismatch_raises(self):
        with pytest.raises(ValueError):
            compute_impact_score(0.5, 0.5, 0.5, w_eoh=0.5, w_cov=0.5, w_res=0.5)


class TestAssessTier:

    def test_governance_ok_all_valid_inputs(self):
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
            governance={
                "sortition_flag":     True,
                "assessor_count":     5,
                "irr_score":          0.85,
                "adversarial_review": True,
            },
        )
        assert result["governance_status"] == "OK"
        assert result["passes_governance"] is True
        assert result["warnings"] == []
        assert result["multiplier"] >= 1.0

    def test_governance_warn_low_assessors(self):
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
            governance={"assessor_count": GOVERNANCE_MIN_ASSESSORS - 1},
        )
        assert result["governance_status"] == "WARN"
        assert result["passes_governance"] is True
        assert any("assessor_count" in w for w in result["warnings"])

    def test_governance_warn_irr_below_warn_threshold(self):
        irr = GOVERNANCE_IRR_WARN_THRESHOLD - 0.05
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
            governance={"irr_score": irr},
        )
        assert result["governance_status"] == "WARN"
        assert result["passes_governance"] is True

    def test_governance_crit_irr_below_crit_threshold(self):
        irr = GOVERNANCE_IRR_CRIT_THRESHOLD - 0.05
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
            governance={"irr_score": irr},
        )
        assert result["governance_status"] == "CRIT"
        assert result["passes_governance"] is False

    def test_no_governance_returns_ok(self):
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
        )
        assert result["governance_status"] == "OK"
        assert result["warnings"] == []
        assert result["sunset_check"] is None

    def test_sunset_check_wired_when_epochs_provided(self):
        result = assess_tier(
            training=0.5, demand=0.4, scarcity=0.2, impact=0.3, epsilon=0.40,
            governance={"review_epoch": 2010, "current_epoch": 2025},
        )
        assert result["sunset_check"] is not None
        assert result["sunset_check"]["status"] == "OVERDUE"
        assert any("expired" in w.lower() or "overdue" in w.lower()
                   or "elapsed" in w.lower() for w in result["warnings"])

    def test_result_keys_present(self):
        result = assess_tier(
            training=0.3, demand=0.3, scarcity=0.2, impact=0.2, epsilon=0.40,
        )
        assert set(result.keys()) == {
            "multiplier", "alpha_coefficients", "governance_status",
            "warnings", "passes_governance", "sunset_check", "inputs",
        }
