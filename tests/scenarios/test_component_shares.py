"""Tests for scenarios/component_shares.py: the desk shares measured against observed
time use, and why the result is a BOUND.

Discipline: * the ASSUMED mapping is tested for completeness, and it names only codes
the extract has (the `unused_innocuous_names` lesson); * findings are asserted as SIGNS
and ORDERINGS, because the levels move with the ATUS vintage; * every figure the module
quotes in prose is pinned live; * `TestComponentSharesChangeNothing` pins that this is
reporting only.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import CARE_AUTOMATION_FLOOR, PERSONAL_EOH_COMPONENTS
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.data import COMPONENT_CODES_MTUS
from hours_eoh.scenarios.component_shares import (
    SHELTER_DESTINATIONS,
    SHELTER_DESTINATION_VOCAB,
    shelter_decomposition,
    shelter_frame_check,
    SHELTER_MTUS_HYPOTHESES,
    SHELTER_MTUS_GUESSES,
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
        """A code nobody has would add zero hours silently, so every mapped code must
        exist in some survey year. The check spans ALL years: `0399` and `0499` report
        zero time in some years, and a latest-year check rejected them.
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
        """EXCLUDED IS NOT ZERO. The excluded time is about 30% of all observed time, so
        hiding it would make the mapped total look like the whole personal obligation.
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

    def test_the_bound_is_two_sided_and_the_lower_side_survives(self):
        """ADOPTED 2026-09-22 (author). Paid care added back at face value OVERSHOOTS,
        so the true share is bracketed. That adds an upper side and retracts nothing:
        some care is bought, so the unpaid reading still understates.
        """
        c = share_comparison()
        assert c["bound_is_two_sided"] is True
        assert "OVERSHOOTS" in c["upper_bound_reason"]
        assert "LOWER bound" in c["bound_reason"]

    def test_the_upper_side_is_declared_unquantified_and_says_why(self):
        """`obligation_work` uses an EMPLOYMENT share as an hours share, in its own
        words. Part-time work concentrates in the personal-care groups that would carry
        the bracket, so a number from that conversion would be a known-biased upper
        side.
        """
        c = share_comparison()
        assert c["upper_bound_quantified"] is False
        assert "EMPLOYMENT" in c["why_upper_not_quantified"]

    def test_quantifying_the_upper_side_must_flip_the_flag(self):
        """A numeric upper share fails this test until `upper_bound_quantified` is True.
        So the claim and the number cannot drift apart (mode 10).
        """
        c = share_comparison()
        numeric_upper = any(
            k for k, v in c.items()
            if "upper" in k and isinstance(v, (int, float))
            and not isinstance(v, bool)
        )
        assert numeric_upper is c["upper_bound_quantified"], (
            "a numeric upper-side key exists while upper_bound_quantified is "
            "False (or vice versa) — the reported value is not the applied one"
        )

    def test_the_sensitivity_carries_the_same_two_sidedness(self):
        s = phase_2_sensitivity(0.99)
        assert s["bound_is_two_sided"] is True
        assert s["upper_bound_quantified"] is False
        assert "TWO-SIDED" in s["note"]


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
        """The correlation is −1.000 exactly, because the table was BUILT to encode the
        prediction. The pin stops anyone reading it as independent evidence.
        """
        d = abatability_direction()
        assert d["spearman_abatability_vs_desk_share"] == pytest.approx(-1.0)

    def test_the_observed_correlation_has_the_opposite_sign(self):
        d = abatability_direction()
        assert d["spearman_abatability_vs_observed_share"] > 0.0

    def test_it_refuses_to_call_this_a_refutation(self):
        """The mapped total barely moved, which fits a(K) being SATURATED in a rich
        economy. The composition is the anomaly, and the named alternative explains it
        too. The module must report the anomaly without the stronger conclusion.
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
        """This had to be measured before the Phase 2 sign-off, because the headline
        roughly halves on a placeholder nothing measures.
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
    """The module's docstrings quote derived figures. Each is pinned against its live
    value, because prose left behind by its source is how this repo's claims go stale.
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
    """REPORTING ONLY: `PERSONAL_EOH_COMPONENTS` stays as it is."""

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
    """The table that a shelter boundary decision cites. These tests pin the DISCIPLINE
    (every code placed, a closed vocabulary, the judgement isolated, the frame
    declared), not the shares, which move with the survey year
    ([record](record/personal.md#shelter-decomposed)).
    """

    def test_every_code_in_the_shelter_groups_is_placed(self) -> None:
        """An unclassified 6-digit code in the shelter groups would drop out of the
        component with no argument made for it.
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
        """The judgement stays inside shelter. A code from another component here would
        be a second, hidden attribution.
        """
        groups = set(COMPONENT_CODES["shelter"])
        stray = {c for c in SHELTER_DESTINATIONS if c[:4] not in groups}
        assert not stray, f"non-shelter codes classified: {sorted(stray)}"

    def test_the_overlap_and_the_thermal_share_are_reported_separately(self) -> None:
        """A boundary decision turns on two numbers that must stay apart. `structure` is
        the part another domain already charges; `thermal` is the part the degree-days
        intensity governs.
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
        """Most of the shelter code set is cleaning and laundry, which scale with area
        and occupancy, not degree-days. So the component's quantity does not match its
        measured delivery, which is why it needs re-scoping. The test asserts an
        ordering.
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
        """ATUS is US and high-capital, and the floor is an unassisted construction. So
        this composition is evidence about the wrong end of the arc, and it must say so.
        """
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


class TestShelterFrameCheck:
    """
    Whether the ATUS decomposition transfers to the frame the base declares.
    It does not, and these pin the NEGATIVE result — which is the load-bearing
    one, because it is what keeps the re-scoping provisional.
    """

    def test_the_control_reproduces_the_known_aggregate(self) -> None:
        """This runs first. The aggregate mapping is known to reproduce ATUS at 0.9757 /
        0.0677; if the function cannot recover that, a per-code failure is a bug in the
        comparison, not a fact about MTUS.
        """
        r = shelter_frame_check()
        assert r["aggregate_reproduces"], (
            f"the control gives {r['aggregate']['mean_ratio']:.4f}, not 0.9757 — "
            "fix the comparison before reading any result below it"
        )
        assert r["aggregate"]["within_tolerance"]

    def test_the_labels_were_read_and_are_cited(self) -> None:
        """Every MTUS label must ship with its source. The first run scored seven labels
        supplied from the ATUS side and never read; the MTUS User Guide publishes them
        ([record](record/personal.md#shelter-frame-check-mtus)).
        """
        r = shelter_frame_check()
        assert set(r["code_labels"]) == set(COMPONENT_CODES_MTUS["shelter"])
        assert r["code_labels"][21] == "Laundry, ironing, clothing repair"
        assert "timeuse.org" in r["labels_source"] and "Table 2" in r["labels_source"]
        for g in r["guesses_made_before_reading_the_codebook"]:
            assert g["identification"].startswith("VOID"), g

    def test_one_mapping_per_code_picked_from_the_label(self) -> None:
        """Not a sweep. The label decides the target, so each code has one candidate and
        no room to keep trying until something clears.
        """
        assert len(SHELTER_MTUS_HYPOTHESES) == len(COMPONENT_CODES_MTUS["shelter"])
        assert {c for c, _g, _w in SHELTER_MTUS_HYPOTHESES} == set(
            COMPONENT_CODES_MTUS["shelter"]
        )
        for _c, groups, why in SHELTER_MTUS_HYPOTHESES:
            assert groups and not why.startswith("GUESS:")

    def test_laundry_identifies_alone(self) -> None:
        """The one code that maps cleanly across both classifications. If it
        stops doing so, the seam has moved somewhere new and every block below
        needs re-deriving rather than the number updating."""
        r = shelter_frame_check()
        t = next(t for t in r["trials"] if t["mtus_code"] == 21)
        assert t["within_tolerance"], t
        assert 21 in r["identified_codes"]

    def test_the_remainder_is_forced_and_the_module_says_so(self) -> None:
        """Once the aggregate and code 21 identify, m20 + m22 is fixed by subtraction,
        so a prediction about the pair cannot fail. An earlier version asserted one. The
        test rebuilds the pair from the other two, and the module must call the value
        forced, not a second measurement
        ([record](record/personal.md#shelter-frame-check-mtus)).
        """
        r = shelter_frame_check()
        assert r["pair_is_forced_by_the_aggregate"] is True
        assert "subtraction" in r["why_pair_is_forced"]
        assert r["remainder_identifies"]
        assert r["identified_blocks"] == ((21,), (20, 22))

        # the reconstruction, so the claim of forcing is checked and not asserted
        from hours_eoh.reference import atus_time_use as A
        from hours_eoh.reference import mtus_time_use as M

        per = M.codes_by_sample()
        years = {y.year for y in A.survey_years()}
        pairs = sorted(
            (s, int(s[2:6])) for s in per if s.startswith("US") and int(s[2:6]) in years
        )

        def atus_minutes(year, groups):
            day = A.tier3_minutes_per_day(year)
            return sum(v for c, v in day.items() if any(c.startswith(g) for g in groups))

        target = {c: g for c, g, _w in SHELTER_MTUS_HYPOTHESES}
        pair_target = target[20] + target[22]
        rebuilt = []
        for sample, year in pairs:
            a_full = atus_minutes(year, COMPONENT_CODES["shelter"])
            a21 = atus_minutes(year, target[21])
            a_pair = atus_minutes(year, pair_target)
            agg = sum(per[sample][c] for c in (20, 21, 22)) / a_full
            r21 = per[sample][21] / a21
            rebuilt.append((agg * a_full - r21 * a21) / a_pair)
        assert abs(sum(rebuilt) / len(rebuilt) - r["pair"]["mean_ratio"]) < 1e-9, (
            "the remainder is NOT reconstructible from the aggregate and 21 — "
            "then it does carry independent information and this module's "
            "'forced by subtraction' claim is wrong"
        )

    def test_the_composition_transfers_at_the_resolution_mtus_identifies(self) -> None:
        """Per code the shares seem to move; per identified BLOCK they do not, because
        the move lies inside the {20, 22} seam. A label-free test on an unidentified
        partition cannot tell a real reallocation from a moving boundary
        ([record](record/personal.md#shelter-frame-check-mtus)).
        """
        r = shelter_frame_check()
        assert not r["composition_transfers_by_code"]
        assert r["composition_transfers"], (
            "the composition no longer transfers at BLOCK level; that would be "
            "a real reallocation rather than a seam and the ATUS split would be "
            "in genuine conflict with MTUS"
        )
        assert max(abs(x) for x in r["composition_shift_by_block"]) < 0.05

    def test_the_between_group_difference_does_not_clear_the_within_group_range(self) -> None:
        """The second, independent reason the per-code reading was wrong: it is
        a difference of means on 3 samples against 23, and no code's ranges
        separate. Reported so nobody quotes the shift as a measured contrast."""
        r = shelter_frame_check()
        assert not any(r["ranges_separate"])
        for lo, hi in zip(r["low_capital"]["code_share_range"],
                          r["high_capital"]["code_share_range"]):
            assert lo[0] <= lo[1] and hi[0] <= hi[1]

    def test_the_year_floor_is_symmetric(self) -> None:
        """An earlier version applied it to the high-capital group only, leaving
        BG1965 inside 'low capital' — a time confound wearing a capital label."""
        r = shelter_frame_check()
        for group in ("low_capital", "high_capital"):
            for sample in r[group]["samples"]:
                assert int(sample[2:6]) >= 2000, (r[group]["samples"], group)

    def test_both_tolerances_and_the_year_floor_are_live_arguments(self) -> None:
        """Stated rather than buried — so each has to be able to change the
        verdict it governs, or it is decoration on a hardcoded decision."""
        assert shelter_frame_check(composition_tolerance=1e-9)["composition_transfers"] is False
        assert shelter_frame_check(composition_tolerance=1.0)["composition_transfers"] is True
        strict = shelter_frame_check(tolerance=1e-9)
        assert strict["identified_codes"] == ()
        assert strict["identified_blocks"] == () and "NOTHING IDENTIFIES" in strict["verdict"]
        assert shelter_frame_check(tolerance=1.0)["identified_codes"] == (20, 21, 22)
        early = shelter_frame_check(since=1960)["low_capital"]["samples"]
        assert "BG1965" in early and "BG1965" not in shelter_frame_check()["low_capital"]["samples"]

    def test_the_destination_split_is_declared_unresolvable(self) -> None:
        """MTUS does not CONTRADICT the ATUS composition — it cannot see it.
        Upkeep and structure share the {20,22} block. Stating that is what keeps
        'provisional' from being read as 'disputed'."""
        r = shelter_frame_check()
        assert r["destination_split_resolvable"] is False
        assert "upkeep" in r["why_not_resolvable"] and "structure" in r["why_not_resolvable"]

    def test_the_verdict_names_what_would_settle_it(self) -> None:
        v = shelter_frame_check()["verdict"].lower()
        assert "provisional" in v
        assert "6-digit" in v or "granularity" in v
        assert "micro-data" in v
        assert "resolution" in v, (
            "the verdict must say the block is RESOLUTION and not disagreement, "
            "or 'provisional' reads as 'MTUS contradicts the ATUS split'"
        )
        # NOT "codebook" — an earlier version required the verdict to name the
        # missing codebook as a blocker. It is read and cited now, so requiring
        # it here would keep a settled item declared open.
