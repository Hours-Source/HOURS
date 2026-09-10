"""
Tests for scenarios/component_shares.py — the desk shares measured against
observed time use, and why it is a BOUND.

Discipline:
  * the ASSUMED mapping is tested for completeness and for naming only codes
    the extract has — the `unused_innocuous_names` lesson;
  * findings are asserted as SIGNS and ORDERINGS; the levels move with the ATUS
    vintage;
  * every figure the module quotes in prose is pinned live, because a derived
    number restated in a docstring is how this repo's claims have gone stale;
  * `TestComponentSharesChangeNothing` pins that this is reporting only.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import CARE_AUTOMATION_FLOOR, PERSONAL_EOH_COMPONENTS
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.scenarios.component_shares import (
    SHELTER_DESTINATIONS,
    SHELTER_DESTINATION_VOCAB,
    shelter_decomposition,
    COMPONENT_CODES,
    EXCLUDED_CODES,
    abatability_direction,
    observed_shares,
    phase_2_sensitivity,
    share_comparison,
    shares_report,
)


class TestTheMappingIsDeclaredAndHonest:

    def test_it_covers_exactly_the_four_components(self):
        assert set(COMPONENT_CODES) == set(PERSONAL_EOH_COMPONENTS)

    def test_every_mapped_code_exists_in_the_extract(self):
        """
        A mapping that names a code nobody has is a mapping nobody reviews —
        and it would silently contribute zero hours.

        Checked across ALL survey years, not the latest. `0399` and `0499` are
        ATUS residual "other" categories with genuinely zero reported time in
        some years (17/22 and 18/22), so a latest-year check rejects two real
        codes — which is how this test first failed.
        """
        present = set()
        for row in atus.survey_years():
            present |= set(atus.minutes_per_day(row.year))
        for component, codes in COMPONENT_CODES.items():
            for code in codes:
                assert code in present, f"{component}: {code} is in no survey year"

    def test_a_code_absent_from_a_year_contributes_zero_not_an_error(self):
        """
        The consequence of the above: the accessor must tolerate a code the year
        does not carry, or the residual categories would break the latest year.
        """
        assert atus.hours_per_person_15plus(atus.latest_year(), ("0399",)) == 0.0

    def test_every_excluded_code_exists_and_says_why(self):
        present = set()
        for row in atus.survey_years():
            present |= set(atus.minutes_per_day(row.year))
        for code, reason in EXCLUDED_CODES.items():
            assert code in present, f"excluded {code} is in no survey year"
            assert len(reason) > 20, f"{code} is excluded without a reason"

    def test_excluded_is_not_zero_and_is_material(self):
        """
        EXCLUDED IS NOT ZERO. The excluded time is large — roughly a third of
        what is mapped — so hiding it would make the mapped total look like the
        whole personal obligation.
        """
        o = observed_shares()
        assert o["excluded_hours"] > 0.0
        assert 0.2 < o["excluded_share_of_all"] < 0.5

    def test_the_overlap_is_declared_and_small(self):
        """
        `0303` sits in both `care` and `health` deliberately. Declared rather
        than resolved by fiat, and reported so a reader can see it is small.
        """
        o = observed_shares()
        assert o["overlap_hours"] > 0.0
        assert o["overlap_hours"] / o["mapped_total"] < 0.01

    def test_no_excluded_code_is_also_mapped(self):
        mapped = {c for codes in COMPONENT_CODES.values() for c in codes}
        assert not (mapped & set(EXCLUDED_CODES))


class TestTheDisagreementWithTheDeskEstimate:

    def test_care_reads_far_below_the_desk_share(self):
        """SIGN and magnitude-class. The level moves with the ATUS vintage."""
        rows = {r["component"]: r for r in share_comparison()["rows"]}
        assert rows["care"]["ratio"] < 0.6
        assert rows["care"]["observed"] < rows["care"]["desk"]

    def test_shelter_reads_far_above_it(self):
        rows = {r["component"]: r for r in share_comparison()["rows"]}
        assert rows["shelter"]["ratio"] > 2.0

    def test_the_shares_sum_to_one(self):
        assert sum(observed_shares()["shares"].values()) == pytest.approx(1.0)

    def test_it_is_reported_as_a_bound_and_names_the_confound(self):
        """
        The decisive caveat: marketised care leaves unpaid time use, which moves
        the result in exactly the observed direction. Without it a reader would
        take this as a replacement for the desk share.
        """
        c = share_comparison()
        assert c["is_a_bound"] is True
        assert "MARKETISED" in c["bound_reason"]
        assert "LOWER bound" in c["bound_reason"]


class TestTheAbatabilityDirection:

    def test_the_change_correlation_runs_against_the_prediction(self):
        """
        a(K) predicts more-abatable components fall MORE. Measured over 22 years
        of capital deepening the rank correlation is positive.
        """
        d = abatability_direction()
        assert d["spearman_abatability_vs_change"] > 0.0

    def test_the_most_abatable_food_component_ROSE(self):
        rows = {r["component"]: r for r in abatability_direction()["rows"]}
        assert rows["nutrition"]["abatability"] >= 0.85
        assert rows["nutrition"]["change"] > 0.0, (
            "nutrition rising is the anomaly; if it ever falls, the finding "
            "weakens and this module should be re-read"
        )

    def test_the_desk_anti_correlation_is_perfect_by_construction(self):
        """
        −1.000 exactly, because the table was BUILT to encode the prediction.
        Pinned so nobody reads it as independent evidence for it.
        """
        d = abatability_direction()
        assert d["spearman_abatability_vs_desk_share"] == pytest.approx(-1.0)

    def test_the_observed_correlation_has_the_opposite_sign(self):
        d = abatability_direction()
        assert d["spearman_abatability_vs_observed_share"] > 0.0

    def test_it_refuses_to_call_this_a_refutation(self):
        """
        The mapped total barely moved, which is consistent with a(K) being
        SATURATED in a rich economy — so the total is not evidence against it.
        The composition is, and the named alternative reaches that too. The
        module must report the anomaly without claiming the stronger conclusion.
        """
        d = abatability_direction()
        assert d["refutes_abatement"] is False
        assert "SATURATED" in d["note"]
        assert abs(d["mapped_total_change"]) < 0.10


class TestWhatItIsWorthToPhase2:

    def test_the_order_of_magnitude_finding_survives_the_swap(self):
        s = phase_2_sensitivity(0.99)
        assert s["survives_the_swap"] is True
        assert s["factor_at_observed"] > 4.0

    def test_but_the_level_does_not(self):
        """
        The reason this had to be measured before the Phase 2 sign-off: the
        headline roughly halves on a placeholder nothing measures.
        """
        s = phase_2_sensitivity(0.99)
        assert s["factor_at_observed"] < 0.7 * s["factor_at_desk"]

    def test_the_two_factors_are_the_governing_equation(self):
        s = phase_2_sensitivity(0.99)
        c = CARE_AUTOMATION_FLOOR
        for key, share in (("factor_at_desk", s["care_share_desk"]),
                           ("factor_at_observed", s["care_share_observed"])):
            expected = (share * (c + (1 - c) * 0.01) + (1 - share) * 0.01) / 0.01
            assert s[key] == pytest.approx(expected)

    def test_both_are_lower_bounds_and_it_says_so(self):
        assert "LOWER bounds" in phase_2_sensitivity(0.99)["note"]

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            phase_2_sensitivity(1.5)


class TestTheQuotedFiguresAreStillTrue:
    """
    The module's docstrings quote derived figures. This repo has been caught
    five times by a derived number restated in prose and left behind when its
    source moved, so each is pinned against its live value.
    """

    def test_the_care_share_and_ratio(self):
        c = share_comparison()
        assert c["care_observed"] == pytest.approx(0.257, abs=0.002)
        assert c["care_observed"] / c["care_desk"] == pytest.approx(0.41, abs=0.01)

    def test_the_phase_2_factors(self):
        s = phase_2_sensitivity(0.99)
        assert s["factor_at_desk"] == pytest.approx(18.2547, abs=0.02)
        assert s["factor_at_observed"] == pytest.approx(8.1426, abs=0.02)

    def test_the_direction_figures(self):
        d = abatability_direction()
        rows = {r["component"]: r for r in d["rows"]}
        assert d["spearman_abatability_vs_change"] == pytest.approx(0.400, abs=0.001)
        assert d["spearman_abatability_vs_observed_share"] == pytest.approx(0.800, abs=0.001)
        assert rows["nutrition"]["change"] == pytest.approx(0.337, abs=0.005)
        assert rows["care"]["change"] == pytest.approx(-0.207, abs=0.005)
        assert d["mapped_total_change"] == pytest.approx(-0.029, abs=0.003)

    def test_the_mapped_total(self):
        assert observed_shares()["mapped_total"] == pytest.approx(745.2, abs=1.0)


class TestComponentSharesChangeNothing:
    """REPORTING ONLY. `PERSONAL_EOH_COMPONENTS` is untouched."""

    def test_the_desk_table_is_not_modified(self):
        before = {k: dict(v) for k, v in PERSONAL_EOH_COMPONENTS.items()}
        shares_report()
        assert {k: dict(v) for k, v in PERSONAL_EOH_COMPONENTS.items()} == before

    def test_the_module_declares_itself_reporting_only(self):
        import hours_eoh.scenarios.component_shares as mod
        assert "REPORTING ONLY" in (mod.__doc__ or "")

    def test_it_names_what_would_close_the_placeholders(self):
        """
        A finding that names no route to closure is a complaint. One acquisition
        closes all of these and the repo has already named it three times.
        """
        import hours_eoh.scenarios.component_shares as mod
        doc = " ".join((mod.__doc__ or "").split())
        assert "HETUS/MTUS" in doc
        assert "HETUS/MTUS" in shares_report()["verdict"]


class TestShelterDecomposition:
    """
    The table a shelter boundary decision cites, so the boundary is informed
    rather than arbitrary. These pin the DISCIPLINE — every code placed, a closed
    vocabulary, the judgement isolated and the frame declared — not the shares,
    which move with the survey year.
    """

    def test_every_code_in_the_shelter_groups_is_placed(self) -> None:
        """
        A 6-digit code inside the shelter groups that nobody classified would be
        silently dropped from the component without anyone having argued for it —
        the same failure the obligation-work registry and the basket's own
        COMPONENT_STATUS guard against.
        """
        r = shelter_decomposition()
        assert r["unclassified"] == [], (
            f"unplaced shelter codes: {r['unclassified']}. Place them in "
            "SHELTER_DESTINATIONS or they leave the component unaccounted for"
        )

    def test_the_vocabulary_is_closed(self) -> None:
        stray = set(SHELTER_DESTINATIONS.values()) - SHELTER_DESTINATION_VOCAB
        assert not stray, f"undeclared destination(s): {sorted(stray)}"
        assert set(SHELTER_DESTINATION_VOCAB) == set(shelter_decomposition()["by_destination"])

    def test_the_classification_only_covers_the_shelter_groups(self) -> None:
        """The judgement is isolated to shelter. A code from another component
        appearing here would be a second, hidden attribution."""
        groups = set(COMPONENT_CODES["shelter"])
        stray = {c for c in SHELTER_DESTINATIONS if c[:4] not in groups}
        assert not stray, f"non-shelter codes classified: {sorted(stray)}"

    def test_the_overlap_and_the_thermal_share_are_reported_separately(self) -> None:
        """
        The two numbers a boundary decision turns on, and they must not be
        collapsed: `structure` is the part another domain already charges, and
        `thermal` is the part the degree-days intensity governs. They are
        different questions with different answers.
        """
        r = shelter_decomposition()
        assert r["overlaps_infrastructure"] == r["by_destination"]["structure"]
        assert r["governed_by_degree_days"] == r["by_destination"]["thermal"]
        assert r["overlaps_infrastructure"] != r["governed_by_degree_days"]
        # AND THE THERMAL LINE MUST BE NON-EMPTY. Found by mutation: moving
        # "heating and cooling" into `structure` took thermal to 0.0 and every
        # other assertion here still passed, because 0.0 is both different from
        # structure and less than it. A zero thermal line means the degree-days
        # intensity on the shelter row governs NOTHING measured — which is a
        # finding that has to be stated, not a state the suite should accept.
        assert r["governed_by_degree_days"] > 0.0, (
            "no shelter hours are classified `thermal`, so the degree-days "
            "intensity governs nothing measured. Either a code was reclassified "
            "or the survey stopped reporting heating and cooling — say which"
        )

    def test_upkeep_dominates_and_that_is_the_finding(self) -> None:
        """
        THE REASON THE COMPONENT NEEDS RE-SCOPING. Most of what the shelter code
        set measures is cleaning and laundry, which scale with area and occupancy
        rather than with degree-days — so the component's quantity (m² AND
        degree-days) does not match its measured delivery. Asserted as an
        ordering, since the levels move with the survey year.
        """
        d = shelter_decomposition()["by_destination"]
        assert d["upkeep"] > d["structure"] + d["not_shelter"] + d["thermal"], (
            "upkeep no longer dominates the shelter component; the quantity/"
            "delivery mismatch this table was built to show may have changed"
        )
        assert d["thermal"] < d["structure"], (
            "the thermal line now exceeds structure — the degree-days intensity "
            "governs more than it did, and the re-scoping argument needs redoing"
        )

    def test_the_frame_is_declared_as_the_wrong_one(self) -> None:
        """ATUS is US and high-capital. The floor is an unassisted construction,
        so this composition is evidence about the wrong end of the arc and must
        say so — the thermal share is the one that would rise at the other end."""
        frame = shelter_decomposition()["frame"].lower()
        assert "atus" in frame and "high-capital" in frame
        assert "mtus" in frame and "unchecked" in frame

    def test_it_reports_and_prices_nothing(self) -> None:
        assert shelter_decomposition()["reporting_only"] is True
        from hours_eoh.reference.personal_basket import COMPONENT_STATUS
        assert COMPONENT_STATUS["shelter"]["status"] == "open", (
            "shelter was priced while this decomposition still says the "
            "component's quantity does not match its delivery"
        )
