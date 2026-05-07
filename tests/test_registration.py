"""
Tests for hours_eoh.core.registration

Covers: care_registration_share, production_registration_share,
stewardship_registration_share, total_registration_share,
labor_category_weights, personal_eoh_registration_share,
knowledge_eoh_registration_share, validate_registration_trajectory.
"""

import math
import pytest

from hours_eoh.core.registration import (
    care_registration_share,
    production_registration_share,
    stewardship_registration_share,
    total_registration_share,
    labor_category_weights,
    personal_eoh_registration_share,
    knowledge_eoh_registration_share,
    validate_registration_trajectory,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# care_registration_share
# ===========================================================================

class TestCareRegistrationShare:

    def test_low_at_epsilon_zero(self):
        """At ε=0, care labor is largely unregistered (mostly household)."""
        share = care_registration_share(0.0)
        assert share < 0.15, (
            f"Care registration at ε=0 should be low, got {share:.3f}"
        )

    def test_rising_at_epsilon_40(self):
        """At ε=0.40, care admission is rising but not yet saturated."""
        share = care_registration_share(0.40)
        assert 0.20 < share < 0.75, (
            f"Care registration at ε=0.40 should be rising, got {share:.3f}"
        )

    def test_high_at_epsilon_90(self):
        """Care registration saturates well before ε=1.0."""
        share = care_registration_share(0.90)
        assert share > 0.85, (
            f"Care registration at ε=0.90 should be near saturation, got {share:.3f}"
        )

    def test_monotonically_increasing(self):
        """Sigmoid produces sensible shares across ε range."""
        epsilons = [i * 0.05 for i in range(20)]  # 0.0, 0.05, ..., 0.95
        shares = [care_registration_share(eps) for eps in epsilons]
        for i in range(len(shares) - 1):
            assert shares[i] <= shares[i + 1] + 1e-10, (
                f"Care registration must be monotonically increasing; "
                f"shares[{i}]={shares[i]:.4f} > shares[{i+1}]={shares[i+1]:.4f}"
            )


# ===========================================================================
# production_registration_share
# ===========================================================================

class TestProductionRegistrationShare:

    def test_high_early(self):
        """Production labor is admitted first; subsistence floor is low (~25%), near-full by ε=0.20."""
        share_0   = production_registration_share(0.0)
        share_20  = production_registration_share(0.20)
        share_40  = production_registration_share(0.40)
        assert 0.10 < share_0 < 0.40  # subsistence floor: formal economy is small at ε=0
        assert share_20 > 0.80         # near-complete before mid-automation
        assert share_40 > 0.97


# ===========================================================================
# stewardship_registration_share
# ===========================================================================

class TestStewardshipRegistrationShare:

    def test_rises_through_mid_automation(self):
        share_0  = stewardship_registration_share(0.0)
        share_50 = stewardship_registration_share(0.50)
        share_90 = stewardship_registration_share(0.90)
        assert share_0 < share_50 < share_90


# ===========================================================================
# total_registration_share
# ===========================================================================

class TestTotalRegistrationShare:

    def test_in_range_at_key_epsilons(self):
        for eps in KEY_EPSILONS:
            share = total_registration_share(eps)
            assert 0.0 <= share <= 1.0, (
                f"total_registration_share must be in [0,1] at ε={eps}, got {share:.4f}"
            )

    def test_rejects_bad_weights(self):
        with pytest.raises(ValueError):
            total_registration_share(0.40, care_weight=0.5, production_weight=0.5,
                                     stewardship_weight=0.5)  # sums to 1.5

    def test_default_uses_dynamic_weights_at_eps_040(self):
        """Result at ε=0.40 must equal explicit dynamic weights, not old hardcoded ones."""
        eps = 0.40
        weights = labor_category_weights(eps)
        dynamic = total_registration_share(
            eps,
            care_weight=weights["care"],
            production_weight=weights["production"],
            stewardship_weight=weights["stewardship"],
        )
        default = total_registration_share(eps)
        assert abs(dynamic - default) < 1e-9

    def test_default_differs_from_hardcoded_at_high_epsilon(self):
        """At ε=0.90, dynamic weights must produce a different (higher) share
        than the old hardcoded production-heavy 0.30/0.45/0.25 mix."""
        eps = 0.90
        old_hardcoded = total_registration_share(
            eps,
            care_weight=0.30,
            production_weight=0.45,
            stewardship_weight=0.25,
        )
        dynamic = total_registration_share(eps)
        assert abs(dynamic - old_hardcoded) > 0.01

    def test_monotone_increase_with_epsilon(self):
        """Registration share must be monotonically non-decreasing with ε."""
        epsilons = [0.0, 0.10, 0.20, 0.40, 0.60, 0.80, 0.90, 0.99]
        shares = [total_registration_share(e) for e in epsilons]
        for i in range(len(shares) - 1):
            assert shares[i] <= shares[i + 1] + 1e-9, (
                f"Registration share decreased from ε={epsilons[i]} to ε={epsilons[i+1]}: "
                f"{shares[i]:.4f} > {shares[i+1]:.4f}"
            )

    def test_output_in_valid_range_all_epsilons(self):
        """Registration share must be in [0, 1] for all ε."""
        for eps in KEY_EPSILONS:
            share = total_registration_share(eps)
            assert 0.0 <= share <= 1.0, f"Out of range at ε={eps}: {share}"

    def test_explicit_override_still_accepted(self):
        """Explicit weight overrides must still be used and validated."""
        result = total_registration_share(
            0.40,
            care_weight=0.50,
            production_weight=0.30,
            stewardship_weight=0.20,
        )
        manual = (
            0.50 * care_registration_share(0.40)
            + 0.30 * production_registration_share(0.40)
            + 0.20 * stewardship_registration_share(0.40)
        )
        assert abs(result - manual) < 1e-9

    def test_explicit_weights_not_summing_to_one_raises(self):
        """Explicit weights that don't sum to 1.0 must raise ValueError."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            total_registration_share(0.40, care_weight=0.5, production_weight=0.5,
                                     stewardship_weight=0.5)

    def test_care_dominates_at_high_epsilon(self):
        """At ε=0.99, care weight must be the largest labor category."""
        weights = labor_category_weights(0.99)
        assert weights["care"] > weights["production"]
        assert weights["care"] > weights["stewardship"]

    def test_production_near_floor_at_high_epsilon(self):
        """At ε=0.99, production weight must be near its minimum floor."""
        weights = labor_category_weights(0.99)
        assert weights["production"] < 0.10

    def test_backward_compat_no_knowledge_weight(self):
        # Without knowledge_weight, result unchanged from pre-M3
        r1 = total_registration_share(0.60)
        r2 = total_registration_share(0.60, knowledge_weight=None)
        assert r1 == pytest.approx(r2, rel=1e-9)

    def test_knowledge_weight_lowers_composite_at_high_eps(self):
        # At high ε, knowledge registration is lower than care/production/stewardship
        r_without = total_registration_share(0.60)
        r_with    = total_registration_share(0.60, knowledge_weight=0.20)
        assert r_with < r_without, "Adding knowledge weight should lower the composite"

    def test_knowledge_weight_zero_matches_none(self):
        r_none = total_registration_share(0.40)
        r_zero = total_registration_share(0.40, knowledge_weight=0.0)
        assert r_zero == pytest.approx(r_none, rel=1e-4)

    def test_result_in_range_with_knowledge_weight(self):
        for eps in [0.0, 0.40, 0.80, 0.99]:
            r = total_registration_share(eps, knowledge_weight=0.15)
            assert 0.0 <= r <= 1.0


# ===========================================================================
# labor_category_weights
# ===========================================================================

class TestLaborCategoryWeights:

    def test_sum_to_one(self):
        for eps in KEY_EPSILONS:
            weights = labor_category_weights(eps)
            total = sum(weights.values())
            assert total == pytest.approx(1.0, abs=1e-6), (
                f"Labor category weights must sum to 1.0 at ε={eps}, got {total}"
            )


# ===========================================================================
# personal_eoh_registration_share
# ===========================================================================

class TestPersonalEOHRegistration:
    """personal_eoh_registration_share: demand boundary, not labor registration."""

    def test_near_zero_at_eps_zero(self):
        """At ε=0, personal EOH is almost entirely private → near-zero registration."""
        share = personal_eoh_registration_share(0.0)
        assert share < 0.02, f"Expected near-zero at ε=0, got {share:.4f}"

    def test_near_saturation_at_eps_99(self):
        """At ε=0.99, collective capital handles most personal EOH (> 85% of 0.95 saturation)."""
        share = personal_eoh_registration_share(0.99)
        assert share > 0.80, f"Expected near-saturation at ε=0.99, got {share:.4f}"

    def test_bounded_below_by_start_share(self):
        KEY_EPS_PERS = [0.0, 0.40, 0.65, 0.90, 0.99]
        for eps in KEY_EPS_PERS:
            share = personal_eoh_registration_share(eps)
            assert share >= 0.0 - 1e-9, f"Below start_share at ε={eps}: {share}"

    def test_bounded_above_by_saturation(self):
        KEY_EPS_PERS = [0.0, 0.40, 0.65, 0.90, 0.99]
        for eps in KEY_EPS_PERS:
            share = personal_eoh_registration_share(eps)
            assert share <= 0.95 + 1e-9, f"Above saturation at ε={eps}: {share}"

    def test_monotonically_non_decreasing(self):
        """Registration can only rise — the collective cannot un-admit personal EOH."""
        epsilons = [i * 0.05 for i in range(20)]
        shares = [personal_eoh_registration_share(e) for e in epsilons]
        for i in range(len(shares) - 1):
            assert shares[i] <= shares[i + 1] + 1e-9, (
                f"Non-monotone at ε={epsilons[i]:.2f}: {shares[i]:.4f} > {shares[i+1]:.4f}"
            )

    def test_inflection_at_065(self):
        """Growth is fastest at the inflection point ε=0.65."""
        delta = 0.01
        slopes = []
        for eps_center in [0.40, 0.50, 0.65, 0.75, 0.85]:
            lo = personal_eoh_registration_share(eps_center - delta)
            hi = personal_eoh_registration_share(eps_center + delta)
            slopes.append((eps_center, (hi - lo) / (2 * delta)))
        # Slope at 0.65 should be highest
        inflection_slope = dict(slopes)[0.65]
        for eps_c, slope in slopes:
            assert inflection_slope >= slope - 1e-6, (
                f"Slope at ε={eps_c} ({slope:.4f}) exceeds inflection slope ({inflection_slope:.4f})"
            )

    def test_custom_params_accepted(self):
        """User can override inflection, rate, saturation."""
        share_default = personal_eoh_registration_share(0.50)
        share_early   = personal_eoh_registration_share(0.50, inflection=0.30, rate=10.0)
        assert share_early > share_default

    def test_returns_float(self):
        KEY_EPS_PERS = [0.0, 0.40, 0.65, 0.90, 0.99]
        for eps in KEY_EPS_PERS:
            result = personal_eoh_registration_share(eps)
            assert isinstance(result, float)
            assert math.isfinite(result)


# ===========================================================================
# knowledge_eoh_registration_share
# ===========================================================================

class TestKnowledgeEohRegistrationShare:

    def test_near_zero_at_subsistence(self):
        share = knowledge_eoh_registration_share(0.0)
        assert share < 0.05, f"At ε=0, expected near-zero, got {share:.4f}"

    def test_saturation_below_one(self):
        share = knowledge_eoh_registration_share(0.99)
        assert share < 1.0
        assert share <= 0.85, "Saturation should be ~0.80, not approaching 1.0"

    def test_saturation_at_limit(self):
        share = knowledge_eoh_registration_share(0.99)
        assert share > 0.55, "Should be clearly above the midpoint by ε=0.99"
        assert share < 0.85

    def test_monotone_across_arc(self):
        eps_values = [0.0, 0.20, 0.40, 0.60, 0.70, 0.80, 0.90, 0.99]
        shares = [knowledge_eoh_registration_share(e) for e in eps_values]
        for i in range(len(shares) - 1):
            assert shares[i + 1] >= shares[i], (
                f"Non-monotone at ε={eps_values[i+1]}: {shares[i]:.4f} → {shares[i+1]:.4f}"
            )

    def test_late_inflection(self):
        # Inflection at ~0.70: share at 0.70 should be near midpoint (0.40 ≈ half of 0.80)
        share_70 = knowledge_eoh_registration_share(0.70)
        assert 0.35 < share_70 < 0.50, (
            f"At inflection ε=0.70, expected ~0.40, got {share_70:.4f}"
        )

    def test_slower_than_care_at_mid_arc(self):
        # Knowledge harder to verify than care → lower share at ε=0.60
        k = knowledge_eoh_registration_share(0.60)
        c = care_registration_share(0.60)
        assert k < c, f"Knowledge ({k:.3f}) should lag care ({c:.3f}) at ε=0.60"

    def test_lower_saturation_than_care(self):
        k = knowledge_eoh_registration_share(0.99)
        c = care_registration_share(0.99)
        assert k < c, "Knowledge saturation should be lower than care saturation"

    def test_output_in_range(self):
        for eps in [0.0, 0.20, 0.50, 0.80, 0.99]:
            s = knowledge_eoh_registration_share(eps)
            assert 0.0 <= s <= 1.0, f"Out of range at ε={eps}: {s}"


# ===========================================================================
# validate_registration_trajectory
# ===========================================================================

class TestValidateRegistrationTrajectory:
    """Trajectory validator must flag monotonicity violations and pass valid paths."""

    def test_monotone_increasing_path_valid(self):
        """Standard automation progression must be valid."""
        path = [0.0, 0.10, 0.20, 0.40, 0.60, 0.80, 0.99]
        result = validate_registration_trajectory(path)
        assert result["valid"] is True
        assert len(result["violations"]) == 0

    def test_return_keys_present(self):
        result = validate_registration_trajectory([0.0, 0.40, 0.90])
        for key in ("valid", "violations", "care_range", "production_range",
                    "total_range", "n_checked"):
            assert key in result, f"Missing key: {key}"

    def test_n_checked_equals_len_sequence(self):
        path = [0.10, 0.30, 0.60]
        result = validate_registration_trajectory(path)
        assert result["n_checked"] == 3

    def test_single_point_always_valid(self):
        result = validate_registration_trajectory([0.40])
        assert result["valid"] is True

    def test_empty_sequence_valid(self):
        result = validate_registration_trajectory([])
        assert result["valid"] is True
        assert result["n_checked"] == 0

    def test_care_range_bounds(self):
        """care_range must contain min and max of the trajectory."""
        path = [0.0, 0.50, 0.99]
        result = validate_registration_trajectory(path)
        assert result["care_range"][0] <= result["care_range"][1]

    def test_total_range_monotone_path(self):
        """On a monotone path, total_range[0] <= total_range[1]."""
        path = [0.0, 0.40, 0.90]
        result = validate_registration_trajectory(path)
        assert result["total_range"][0] <= result["total_range"][1]

    def test_care_params_override_accepted(self):
        """Custom care sigmoid params must be accepted without error."""
        path = [0.0, 0.40, 0.99]
        result = validate_registration_trajectory(
            path, care_params={"inflection": 0.50, "rate": 10.0}
        )
        assert result["valid"] is True
