"""
The work-year reference: one convention, policy-free, with the band reported.

WHY THIS EXISTS (author sign-off, 2026-09-02). `H_REF` described itself as "a
stated normalizer … not a claim about how long anyone works" and was 50 weeks ×
40 h — a two-week leave policy baked into the base. A normalizer carrying a
policy is not one: every deviation measured against it silently nets that policy
out. It is now the calendar, 40 × 52, and leave, part-time, actual hours and
surge are all REPORTED deviations against it.

The move also closed a defect the repo had documented and never fixed:
`BASE_LIFETIME_EARNINGS_TEH` used the literal 2080 while `H_REF` was 2000, and
said so in its own form field. **The value was identical either way** — 2080 × 42
= 87,360 — which is precisely what let two conventions coexist unnoticed.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from hours_eoh.data import (
    BASE_CAREER_YEARS,
    BASE_LIFETIME_EARNINGS_TEH,
    H_MIN,
    H_REF,
    WORK_YEAR_REFERENCE_POINTS,
)

DATA_PY = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh" / "data.py"


class TestTheBaseCarriesNoLeavePolicy:

    def test_h_ref_is_the_calendar(self):
        assert H_REF == 40 * 52 == 2080

    def test_it_is_not_the_old_fifty_week_value(self):
        """
        The retired 2000 = 50 wk × 40 h. If it ever returns, a leave policy has
        been put back inside a value whose own form calls it a normalizer.
        """
        assert H_REF != 2000

    def test_the_decision_is_recorded_where_the_value_is(self):
        """
        Checked against the WHOLE contiguous comment run above the value, not a
        fixed window of characters. The first version looked back 2,000 chars,
        which is a proxy for "in the block" that breaks the moment the block
        legitimately grows — as it did on 2026-09-03, when H_REF gained a note
        about being misread as a capacity default. A threshold that fails on
        honest growth gets widened until it means nothing.

        The parsed record is not the right instrument either: the scanner keeps
        only the LAST `note:`, so an assertion against `record.note` silently
        stops seeing every earlier one.
        """
        lines = DATA_PY.read_text(encoding="utf-8").splitlines()
        i = next(n for n, l in enumerate(lines) if l.startswith("H_REF: int ="))
        start = i
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        head = "\n".join(lines[start:i])
        assert "decided_by" in head, "a convention change needs its decision recorded"
        assert "US-NOMINAL" in head, (
            "2080 is the US convention; EU statutory leave gives 1,760-1,880. "
            "Presenting it as universal is the frame error in a new place."
        )


class TestTheTwoConventionsCannotDivergeAgain:

    def test_lifetime_earnings_is_bound_not_restated(self):
        assert BASE_LIFETIME_EARNINGS_TEH == float(H_REF) * BASE_CAREER_YEARS

    def test_the_bind_was_value_neutral(self):
        """
        87,360 both before and after. The defect survived BECAUSE the numbers
        agreed — pinning the value is what proves the fix changed only the
        coupling.
        """
        assert BASE_LIFETIME_EARNINGS_TEH == pytest.approx(87_360.0, rel=1e-12)

    def test_the_literal_2080_is_gone_from_that_expression(self):
        """
        The shadow-literal pattern: an expression that restates its source can
        drift from it, which is exactly what happened here for months.
        """
        text = DATA_PY.read_text(encoding="utf-8")
        line = next(l for l in text.splitlines()
                    if l.startswith("BASE_LIFETIME_EARNINGS_TEH"))
        assert "87_360" not in line and "2080" not in line, (
            f"restated rather than bound: {line}"
        )

    def test_career_years_is_deliberately_not_the_measured_working_life(self):
        """
        DELIBERATE. `SKILL_WORKING_LIFE_YEARS` is measured cohort exit (37.5);
        this is the span a lifetime-earnings reference is quoted over. Binding
        them would move the value 10.7% on a claim nobody has made, and the tag
        block has to say so rather than leaving it looking like an oversight.
        """
        from hours_eoh.data import SKILL_WORKING_LIFE_YEARS
        assert BASE_CAREER_YEARS != SKILL_WORKING_LIFE_YEARS
        text = DATA_PY.read_text(encoding="utf-8")
        i = text.index("BASE_CAREER_YEARS: float =")
        assert "DELIBERATELY NOT BOUND" in text[max(0, i - 1200):i]


class TestTheBandIsReportedRatherThanOneNumber:

    def test_nominal_is_unity(self):
        assert WORK_YEAR_REFERENCE_POINTS["nominal"] == 1.0

    def test_every_point_is_a_fraction_of_nominal(self):
        assert all(0.0 < v <= 1.0 for v in WORK_YEAR_REFERENCE_POINTS.values())

    def test_the_points_are_ordered_as_documented(self):
        p = WORK_YEAR_REFERENCE_POINTS
        assert p["nominal"] > p["eu_nominal"] > p["measured_actual"] > p["reduced_20pct"]

    def test_the_measured_actual_point_matches_the_derived_figure(self):
        """
        BOUND BY TEST, not by expression: `data.py` sits below `scenarios/`, so
        it cannot import the derivation — the `MEAN_MULTIPLIER_REFERENCE`
        precedent. If the ATUS figure is re-derived, this fails.
        """
        from hours_eoh.scenarios.food_conservation import hours_per_worker_year
        assert (hours_per_worker_year() / H_REF) == pytest.approx(
            WORK_YEAR_REFERENCE_POINTS["measured_actual"], abs=5e-4
        )

    def test_eu_nominal_is_five_weeks_of_leave(self):
        assert (40 * 47) / H_REF == pytest.approx(
            WORK_YEAR_REFERENCE_POINTS["eu_nominal"], abs=5e-4
        )

    def test_the_reduced_point_is_exactly_a_fifth_less(self):
        assert WORK_YEAR_REFERENCE_POINTS["reduced_20pct"] == pytest.approx(0.80)

    def test_eu_nominal_and_us_measured_actual_nearly_coincide(self):
        """
        The coincidence worth remembering: a European FULL-TIME year and an
        American ACTUAL year are within 0.3%. It is why the retired 2000 looked
        reasonable — it sat between the two nominals — and why quoting a single
        hours figure without saying which question it answers is unsafe.
        """
        p = WORK_YEAR_REFERENCE_POINTS
        assert abs(p["eu_nominal"] - p["measured_actual"]) < 0.005


class TestTheCompetencyFloorNeverBinds:
    """
    MEASURED 2026-09-02, and it is a positive result rather than a dead
    constant: the model never reaches an automation level at which ordinary work
    falls below the point where practitioners keep their skills.
    """

    def test_required_hours_stay_above_the_floor_across_the_arc(self):
        import inspect
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.trajectory import canonical_physical_state
        accepted = inspect.signature(eoh_to_teh_pipeline).parameters
        workers = 1_000_000 * 0.63 * 0.70
        for capability in (0.0, 0.40, 0.90, 0.99):
            state = {k: v for k, v in canonical_physical_state(capability).items()
                     if k in accepted}
            r = eoh_to_teh_pipeline(epsilon=capability, population=1_000_000, **state)
            assert r["human_eoh"] / workers > H_MIN

    def test_it_answers_a_different_question_from_the_work_year(self):
        """
        Competency retention, not labour supply. They do not belong on one
        ladder, and the tag block says so where a reader will look.
        """
        text = DATA_PY.read_text(encoding="utf-8")
        i = text.index("H_MIN: int =")
        head = text[max(0, i - 1600):i]
        assert "NEVER BINDS" in head
        assert "competency" in head.lower()
