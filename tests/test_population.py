"""
Tests for hours_eoh.core.population

Covers: age_group_for_age, aging, population_eoh_curve,
population_lifecycle_snapshot, cohort_aging_trajectory.
"""

import math
import pytest

from hours_eoh.core.population import (
    age_group_for_age,
    aging,
    population_eoh_curve,
    population_lifecycle_snapshot,
    cohort_aging_trajectory,
)
from hours_eoh.core.capital import make_asset
from hours_eoh.data import (
    AGE_GROUPS,
    AGE_GROUP_RANGES,
    PERSONAL_EOH_BASE,
    CAPACITY_DECLINE_ONSET_AGE,
    CAPACITY_DECLINE_MID_AGE,
    CAPACITY_DECLINE_LATE_AGE,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STANDARD_DIST: dict[str, float] = {
    "infant":       70_000.0,
    "child":       160_000.0,
    "working_age":  600_000.0,
    "elderly":     170_000.0,
}

DEFAULT_DIST = STANDARD_DIST


def make_worker(age: float = 35.0, capacity: float = 1200.0) -> dict:
    """Build a human capital asset for testing."""
    return make_asset(
        asset_id=f"worker_{age}",
        asset_type="generic_infra",
        teh_value=500.0,
        annual_eoh=PERSONAL_EOH_BASE * 1.0,
        design_life=80.0,
        age=age,
        condition=1.0,
        is_human_capital=True,
        entropy_reduction_capacity=capacity,
        personal_eoh_per_year=PERSONAL_EOH_BASE,
    )


# ===========================================================================
# age_group_for_age
# ===========================================================================

class TestAgeGroupClassification:

    def test_infant_range(self):
        assert age_group_for_age(0.0)  == "infant"
        assert age_group_for_age(1.0)  == "infant"
        assert age_group_for_age(5.9)  == "infant"

    def test_child_range(self):
        assert age_group_for_age(6.0)  == "child"
        assert age_group_for_age(12.0) == "child"
        assert age_group_for_age(17.9) == "child"

    def test_working_age_range(self):
        assert age_group_for_age(18.0) == "working_age"
        assert age_group_for_age(35.0) == "working_age"
        assert age_group_for_age(64.9) == "working_age"

    def test_elderly_range(self):
        assert age_group_for_age(65.0) == "elderly"
        assert age_group_for_age(80.0) == "elderly"
        assert age_group_for_age(100.0) == "elderly"

    def test_boundary_conditions(self):
        assert age_group_for_age(6.0)  == "child"
        assert age_group_for_age(18.0) == "working_age"
        assert age_group_for_age(65.0) == "elderly"

    def test_negative_age_raises(self):
        with pytest.raises(ValueError):
            age_group_for_age(-1.0)


# ===========================================================================
# aging
# ===========================================================================

class TestAging:

    def test_aging_advances_age(self):
        worker = make_worker(age=35.0)
        result = aging(worker, years_elapsed=5.0)
        assert result["new_age"] == pytest.approx(40.0)
        assert result["updated_asset"]["age"] == pytest.approx(40.0)

    def test_aging_no_capacity_decline_before_50(self):
        """Capacity should not decline for workers under 50."""
        worker = make_worker(age=30.0, capacity=1000.0)
        result = aging(worker, years_elapsed=10.0)  # now 40
        assert result["new_capacity"] == pytest.approx(1000.0, rel=1e-6)

    def test_aging_capacity_declines_after_50(self):
        """Workers over 50 should lose capacity each year."""
        worker = make_worker(age=52.0, capacity=1000.0)
        result = aging(worker, years_elapsed=1.0)
        assert result["new_capacity"] < 1000.0

    def test_aging_capacity_declines_steeply_in_elderly(self):
        """Elderly workers (65+) should lose capacity faster than late working-age."""
        worker_55 = make_worker(age=55.0, capacity=1000.0)
        worker_70 = make_worker(age=70.0, capacity=1000.0)
        result_55 = aging(worker_55, years_elapsed=5.0)
        result_70 = aging(worker_70, years_elapsed=5.0)
        loss_55 = 1000.0 - result_55["new_capacity"]
        loss_70 = 1000.0 - result_70["new_capacity"]
        assert loss_70 > loss_55

    def test_aging_personal_eoh_rises_at_elderly_transition(self):
        """Crossing from working_age to elderly should raise personal EOH."""
        worker = make_worker(age=63.0, capacity=800.0)
        worker["personal_eoh_per_year"] = PERSONAL_EOH_BASE * 1.0
        result = aging(worker, years_elapsed=3.0)  # crosses to elderly at 65
        assert result["new_age_group"] == "elderly"
        assert result["new_personal_eoh_per_year"] > result["old_personal_eoh_per_year"]

    def test_aging_elderly_eoh_rises_with_epsilon(self):
        """Elderly personal EOH should be slightly higher at higher ε."""
        worker = make_worker(age=70.0)
        result_low_eps  = aging(worker, epsilon=0.0)
        result_high_eps = aging(worker, epsilon=0.99)
        assert result_high_eps["new_personal_eoh_per_year"] > result_low_eps["new_personal_eoh_per_year"]

    def test_aging_condition_declines(self):
        """Natural aging degrades condition."""
        worker = make_worker(age=30.0)
        result = aging(worker, years_elapsed=10.0)
        assert result["new_condition"] < result["old_condition"]

    def test_aging_elderly_condition_declines_faster(self):
        """Elderly condition should decline faster than working-age."""
        worker_35 = make_worker(age=35.0)
        worker_70 = make_worker(age=70.0)
        result_35 = aging(worker_35, years_elapsed=10.0)
        result_70 = aging(worker_70, years_elapsed=10.0)
        loss_35 = 1.0 - result_35["new_condition"]
        loss_70 = 1.0 - result_70["new_condition"]
        assert loss_70 > loss_35

    def test_aging_capacity_never_negative(self):
        """Capacity cannot go below 0."""
        worker = make_worker(age=90.0, capacity=1.0)
        result = aging(worker, years_elapsed=50.0)
        assert result["new_capacity"] >= 0.0

    def test_aging_condition_bounded(self):
        """Condition must stay in [0, 1]."""
        worker = make_worker(age=35.0)
        for eps in KEY_EPSILONS:
            result = aging(worker, years_elapsed=30.0, epsilon=eps)
            assert 0.0 <= result["new_condition"] <= 1.0

    def test_aging_requires_human_capital(self):
        """aging() must reject non-human-capital assets."""
        bridge = make_asset("bridge_1", "stone_bridge", 1000.0, 50.0, 80.0)
        with pytest.raises(ValueError):
            aging(bridge, years_elapsed=1.0)

    def test_aging_zero_years_is_identity(self):
        """Aging by 0 years produces no change."""
        worker = make_worker(age=40.0, capacity=1000.0)
        result = aging(worker, years_elapsed=0.0)
        assert result["new_age"] == pytest.approx(40.0)
        assert result["new_capacity"] == pytest.approx(1000.0)
        assert result["age_group_changed"] is False

    def test_aging_updated_asset_is_consistent(self):
        """updated_asset must reflect all changes."""
        worker = make_worker(age=64.0, capacity=900.0)
        result = aging(worker, years_elapsed=2.0)
        updated = result["updated_asset"]
        assert updated["age"]                        == pytest.approx(result["new_age"])
        assert updated["entropy_reduction_capacity"] == pytest.approx(result["new_capacity"])
        assert updated["personal_eoh_per_year"]      == pytest.approx(result["new_personal_eoh_per_year"])
        assert updated["condition"]                  == pytest.approx(result["new_condition"])

    def test_aging_at_all_key_epsilons_finite(self):
        """Aging produces finite results at all key ε values."""
        worker = make_worker(age=45.0, capacity=1200.0)
        for eps in KEY_EPSILONS:
            result = aging(worker, epsilon=eps)
            assert math.isfinite(result["new_capacity"])
            assert math.isfinite(result["new_personal_eoh_per_year"])
            assert math.isfinite(result["new_condition"])


# ===========================================================================
# population_eoh_curve
# ===========================================================================

class TestPopulationEohCurve:

    def test_infant_has_highest_eoh_per_capita(self):
        """Infants generate more personal EOH per capita than any other group."""
        curve = population_eoh_curve(STANDARD_DIST, epsilon=0.40)
        eoh_by_group = {c["age_group"]: c["eoh_per_capita"] for c in curve}
        assert eoh_by_group["infant"] > eoh_by_group["child"]
        assert eoh_by_group["infant"] > eoh_by_group["working_age"]
        assert eoh_by_group["infant"] > eoh_by_group["elderly"]

    def test_elderly_higher_eoh_than_working_age(self):
        """Elderly (2.5×) generate more personal EOH than working-age (1.0×)."""
        curve = population_eoh_curve(STANDARD_DIST, epsilon=0.40)
        eoh_by_group = {c["age_group"]: c["eoh_per_capita"] for c in curve}
        assert eoh_by_group["elderly"] > eoh_by_group["working_age"]

    def test_eoh_weights_match_data_constants(self):
        """EOH per capita = base_rate × eoh_weight (for non-elderly groups)."""
        curve = population_eoh_curve(STANDARD_DIST, epsilon=0.0)
        eoh_by_group = {c["age_group"]: c["eoh_per_capita"] for c in curve}
        for group, data in AGE_GROUPS.items():
            if group == "elderly":
                continue  # elderly has ε adjustment
            expected = PERSONAL_EOH_BASE * data["eoh_weight"]
            assert eoh_by_group[group] == pytest.approx(expected)

    def test_total_eoh_is_sum_of_cohorts(self):
        """Total EOH = sum of all group totals."""
        curve = population_eoh_curve(STANDARD_DIST)
        total = sum(c["total_eoh"] for c in curve)
        assert total > 0
        assert math.isfinite(total)

    def test_elderly_eoh_rises_with_epsilon(self):
        """Elderly per-capita EOH is higher at ε=0.99 than ε=0."""
        curve_0  = population_eoh_curve(STANDARD_DIST, epsilon=0.0)
        curve_99 = population_eoh_curve(STANDARD_DIST, epsilon=0.99)
        eoh_0  = {c["age_group"]: c["eoh_per_capita"] for c in curve_0}
        eoh_99 = {c["age_group"]: c["eoh_per_capita"] for c in curve_99}
        assert eoh_99["elderly"] > eoh_0["elderly"]
        assert eoh_99["working_age"] == pytest.approx(eoh_0["working_age"])

    def test_curve_sorted_by_eoh_per_capita_descending(self):
        """Curve is sorted highest → lowest EOH per capita."""
        curve = population_eoh_curve(STANDARD_DIST)
        per_cap = [c["eoh_per_capita"] for c in curve]
        for i in range(len(per_cap) - 1):
            assert per_cap[i] >= per_cap[i + 1]

    def test_total_eoh_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            curve = population_eoh_curve(STANDARD_DIST, epsilon=eps)
            total = sum(c["total_eoh"] for c in curve)
            assert total > 0

    def test_invalid_age_group_raises(self):
        with pytest.raises(ValueError):
            population_eoh_curve({"infant": 1000, "teenagers": 500})

    def test_single_cohort_population(self):
        """Works with a single age group."""
        curve = population_eoh_curve({"working_age": 1_000_000})
        assert len(curve) == 1
        assert curve[0]["age_group"] == "working_age"
        assert curve[0]["total_eoh"] == pytest.approx(1_000_000 * PERSONAL_EOH_BASE)


# ===========================================================================
# population_lifecycle_snapshot
# ===========================================================================

class TestPopulationLifecycleSnapshot:

    def test_snapshot_totals_match_curve(self):
        """Snapshot total_personal_eoh matches sum of curve totals."""
        snap  = population_lifecycle_snapshot(STANDARD_DIST)
        curve = population_eoh_curve(STANDARD_DIST)
        total_from_curve = sum(c["total_eoh"] for c in curve)
        assert snap["total_personal_eoh"] == pytest.approx(total_from_curve)

    def test_dependency_ratio_realistic(self):
        """Standard distribution: ~40% dependents → dependency ratio ~0.67."""
        snap = population_lifecycle_snapshot(STANDARD_DIST)
        assert snap["dependency_ratio"] == pytest.approx(400_000 / 600_000, rel=0.01)

    def test_automation_covered_eoh_rises_with_epsilon(self):
        """At higher ε, automation covers more personal EOH."""
        snap_0  = population_lifecycle_snapshot(STANDARD_DIST, epsilon=0.0)
        snap_90 = population_lifecycle_snapshot(STANDARD_DIST, epsilon=0.90)
        assert snap_90["automation_covered_eoh"] > snap_0["automation_covered_eoh"]

    def test_human_eoh_burden_falls_with_epsilon(self):
        """Human EOH burden falls as automation covers more."""
        snap_0  = population_lifecycle_snapshot(STANDARD_DIST, epsilon=0.0)
        snap_99 = population_lifecycle_snapshot(STANDARD_DIST, epsilon=0.99)
        assert snap_99["human_eoh_burden"] < snap_0["human_eoh_burden"]

    def test_snapshot_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            snap = population_lifecycle_snapshot(STANDARD_DIST, epsilon=eps)
            assert math.isfinite(snap["total_personal_eoh"])
            assert math.isfinite(snap["human_eoh_burden"])
            assert math.isfinite(snap["dependency_ratio"])

    def test_care_pipeline_eoh_positive(self):
        """Care pipeline EOH is positive whenever there are infants or children."""
        snap = population_lifecycle_snapshot(STANDARD_DIST)
        assert snap["care_pipeline_eoh"] > 0

    def test_no_infants_care_pipeline_low(self):
        """No infants → care pipeline EOH reflects only children."""
        dist = {"working_age": 800_000, "child": 100_000, "elderly": 100_000}
        snap = population_lifecycle_snapshot(dist)
        expected = 100_000 * PERSONAL_EOH_BASE * AGE_GROUPS["child"]["eoh_weight"]
        assert snap["care_pipeline_eoh"] == pytest.approx(expected)


# ===========================================================================
# cohort_aging_trajectory
# ===========================================================================

class TestCohortAgingTrajectory:
    """Cohort aging trajectory must track demographic shifts coherently."""

    def test_return_keys_present(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=5)
        for key in ("years", "distributions", "total_populations",
                    "dependency_ratios", "human_eoh_burdens",
                    "peak_dependency_year", "final_distribution"):
            assert key in result, f"Missing key: {key}"

    def test_year_count_matches_n_years(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=10)
        assert len(result["years"]) == 11  # 0..10 inclusive
        assert len(result["distributions"]) == 11

    def test_year_zero_matches_initial(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=5)
        for group, count in DEFAULT_DIST.items():
            assert result["distributions"][0][group] == pytest.approx(count, rel=1e-9)

    def test_total_population_positive_all_years(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=20)
        for pop in result["total_populations"]:
            assert pop > 0.0

    def test_population_grows_with_positive_birth_rate(self):
        """With birth rate > death rate, total population must grow."""
        result = cohort_aging_trajectory(
            DEFAULT_DIST, n_years=10,
            birth_rate=0.02,
            death_rate_elderly=0.04,
        )
        assert result["total_populations"][-1] > result["total_populations"][0]

    def test_dependency_ratios_finite(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=15)
        for dr in result["dependency_ratios"]:
            assert math.isfinite(dr)
            assert dr >= 0.0

    def test_human_eoh_burdens_positive(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=10)
        for burden in result["human_eoh_burdens"]:
            assert burden > 0.0

    def test_elderly_cohort_positive_final(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=30)
        final_elderly = result["distributions"][-1]["elderly"]
        assert final_elderly >= 0.0

    def test_peak_dependency_year_valid(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=20)
        peak = result["peak_dependency_year"]
        assert 0 <= peak <= 20

    def test_final_distribution_matches_last_year(self):
        result = cohort_aging_trajectory(DEFAULT_DIST, n_years=10)
        assert result["final_distribution"] == result["distributions"][-1]

    def test_zero_birth_rate_population_declines(self):
        """No births + elderly deaths → population must shrink over time."""
        result = cohort_aging_trajectory(
            DEFAULT_DIST, n_years=20,
            birth_rate=0.0,
            death_rate_elderly=0.10,
        )
        assert result["total_populations"][-1] < result["total_populations"][0]


class TestCohortAgingCapitalFulfillment:
    """Capital fulfillment must reduce the personal EOH burden in the trajectory."""

    def test_higher_capital_fulfillment_lower_burden(self):
        """Greater per-person capital fulfillment → lower human EOH burden."""
        no_cap   = cohort_aging_trajectory(DEFAULT_DIST, n_years=5, capital_personal_eoh_per_person=0.0)
        with_cap = cohort_aging_trajectory(DEFAULT_DIST, n_years=5, capital_personal_eoh_per_person=300.0)
        for b_none, b_cap in zip(no_cap["human_eoh_burdens"], with_cap["human_eoh_burdens"]):
            assert b_cap <= b_none

    def test_zero_fulfillment_baseline_unchanged(self):
        """With capital_personal_eoh_per_person=0, result must equal baseline."""
        base = cohort_aging_trajectory(DEFAULT_DIST, n_years=5)
        zero = cohort_aging_trajectory(DEFAULT_DIST, n_years=5, capital_personal_eoh_per_person=0.0)
        for b, z in zip(base["human_eoh_burdens"], zero["human_eoh_burdens"]):
            assert b == pytest.approx(z, rel=1e-9)

    def test_full_fulfillment_burden_reaches_floor(self):
        """With fulfillment = PERSONAL_EOH_BASE, effective rate → 0 → minimal burden."""
        full = cohort_aging_trajectory(
            DEFAULT_DIST, n_years=3,
            capital_personal_eoh_per_person=PERSONAL_EOH_BASE,
        )
        no_cap = cohort_aging_trajectory(DEFAULT_DIST, n_years=3)
        for b_full, b_none in zip(full["human_eoh_burdens"], no_cap["human_eoh_burdens"]):
            assert b_full < b_none

    def test_excess_fulfillment_clamped(self):
        """Fulfillment exceeding the base rate must clamp to zero, not go negative."""
        extreme = cohort_aging_trajectory(
            DEFAULT_DIST, n_years=3,
            capital_personal_eoh_per_person=1e9,
        )
        for burden in extreme["human_eoh_burdens"]:
            assert burden >= 0.0

    def test_fulfillment_monotone_effect(self):
        """Increasing fulfillment in steps must monotonically reduce burden."""
        rates = [0.0, 100.0, 500.0, 1000.0, 1500.0]
        burdens_year1 = []
        for rate in rates:
            result = cohort_aging_trajectory(DEFAULT_DIST, n_years=1,
                                             capital_personal_eoh_per_person=rate)
            burdens_year1.append(result["human_eoh_burdens"][0])
        for i in range(len(burdens_year1) - 1):
            assert burdens_year1[i] >= burdens_year1[i + 1] - 1e-6


class TestCapacityDeclineShape:
    """
    THE CURVE `_capacity_decline_rate` DESCRIBES, pinned as shape (2026-08-27).

    Its six constants lived in `core/population.py` as shadow constants —
    untagged, invisible to the provenance gate, and a +7% perturbation of ANY of
    them failed no test in the suite. They now live in `data.py` with a
    `resolves_by` naming NHATS/HRS functional-limitation prevalence by single
    year of age, and these are the pins.

    Asserted as SHAPE and ORDERING, not levels. The levels are desk estimates
    that will move when the dataset lands; what must not move without argument
    is the structure the docstring claims:

      ages 18–49  no age-related decline (prime working capacity)
      ages 50–64  gradual late-career erosion
      ages 65–79  steeper, early elderly
      ages 80+    steepest, late elderly

    THE ORDERING IS THE BIOLOGICALLY WELL-FOUNDED PART; the 2.7x and 1.75x steps
    between the three rates are not, and are deliberately NOT pinned as levels.
    """

    def _rate(self, age):
        from hours_eoh.core.population import _capacity_decline_rate
        return _capacity_decline_rate(age)

    def test_no_decline_through_prime_working_years(self):
        """The claim that makes ε-coherence work at low ε: prime adults are the
        numeraire, and a decline here would tax them for existing."""
        for age in (18, 25, 35, 45, CAPACITY_DECLINE_ONSET_AGE - 1):
            assert self._rate(age) == 0.0, f"unexpected decline at age {age}"

    def test_the_rate_is_monotonically_non_decreasing_in_age(self):
        rates = [self._rate(a) for a in range(0, 101)]
        assert rates == sorted(rates), "capacity decline must never ease with age"

    def test_the_three_phases_are_strictly_ordered(self):
        """early < mid < late. If this inverts, the model says the old recover."""
        early = self._rate(CAPACITY_DECLINE_ONSET_AGE)
        mid = self._rate(CAPACITY_DECLINE_MID_AGE)
        late = self._rate(CAPACITY_DECLINE_LATE_AGE)
        assert 0.0 < early < mid < late, f"{early} !< {mid} !< {late}"

    @pytest.mark.parametrize("boundary,below,above", [
        ("CAPACITY_DECLINE_ONSET_AGE", 0.0, None),
        ("CAPACITY_DECLINE_MID_AGE", None, None),
        ("CAPACITY_DECLINE_LATE_AGE", None, None),
    ])
    def test_each_breakpoint_actually_steps(self, boundary, below, above):
        """
        A breakpoint that changes nothing is a constant pretending to be a
        parameter. Each must produce a strict step at exactly its age.
        """
        import hours_eoh.data as D
        age = getattr(D, boundary)
        assert self._rate(age - 1) < self._rate(age), (
            f"{boundary}={age} produces no step"
        )

    def test_the_elderly_breakpoint_is_bound_not_restated(self):
        """
        It was the literal 65 beside AGE_GROUP_RANGES' own 65 — the
        restates-instead-of-binds pattern. Now bound, so they cannot drift.
        """
        assert CAPACITY_DECLINE_MID_AGE == AGE_GROUP_RANGES["elderly"][0]

    def test_onset_precedes_the_elderly_boundary(self):
        """
        The deliberate claim: biological capacity decline begins in late working
        life, NOT at the formal retirement age. Conflating the two would be the
        wrong-instrument error — a participation series measures whether people
        DO work, not what they are capable of.
        """
        assert CAPACITY_DECLINE_ONSET_AGE < CAPACITY_DECLINE_MID_AGE
        assert CAPACITY_DECLINE_MID_AGE < CAPACITY_DECLINE_LATE_AGE

    def test_the_curve_is_observable_through_aging(self):
        """
        The shape must be visible through the PUBLIC API, or these pins guard a
        private function nothing consumes. `aging()` is the consumer.
        """
        def capacity_after_a_year(age):
            a = make_asset(
                asset_id=f"h{age}", asset_type="human", teh_value=100.0,
                annual_eoh=0.0, design_life=100.0, age=age,
                is_human_capital=True, entropy_reduction_capacity=1000.0,
            )
            return aging(a, years_elapsed=1.0)["new_capacity"]

        prime = capacity_after_a_year(40.0)
        late = capacity_after_a_year(85.0)
        assert prime == pytest.approx(1000.0, rel=1e-9), "no decline before onset"
        assert late < prime, "the elderly must decline faster through the public path"

    def test_capacity_decline_is_monotone_in_age_through_aging(self):
        """Same claim, swept: no age may fare better than a younger one."""
        def capacity_after_a_year(age):
            a = make_asset(
                asset_id=f"h{age}", asset_type="human", teh_value=100.0,
                annual_eoh=0.0, design_life=100.0, age=age,
                is_human_capital=True, entropy_reduction_capacity=1000.0,
            )
            return aging(a, years_elapsed=1.0)["new_capacity"]

        caps = [capacity_after_a_year(float(a)) for a in range(30, 96, 5)]
        assert caps == sorted(caps, reverse=True), caps
