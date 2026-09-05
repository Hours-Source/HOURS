"""
The frailty socket: an intake contract with no default, and its stated scope.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import AGE_GROUPS
from hours_eoh.scenarios.frailty import frailty_care_load, morbidity_direction

GOOD = {
    "frailty_years_per_capita": 0.35,
    "care_hours_per_frailty_year": 1200.0,
    "source": "illustrative fixture — not a measurement",
    "covers_institutional": True,
}


class TestThereIsNoDefault:
    """
    The point of the socket. A shipped care number is a rationing rule, and the
    framework has no standing to write one — the deploying collective does.
    `pristine_gap_obligation` set the precedent: no default inventory, pinned.
    """

    @pytest.mark.parametrize("drop", sorted(GOOD))
    def test_every_field_is_required(self, drop) -> None:
        intake = {k: v for k, v in GOOD.items() if k != drop}
        with pytest.raises(ValueError, match="missing"):
            frailty_care_load(intake)  # type: ignore[arg-type]

    def test_zero_is_rejected_because_excluded_is_not_zero(self) -> None:
        for field in ("frailty_years_per_capita", "care_hours_per_frailty_year"):
            with pytest.raises(ValueError, match="not a low-care"):
                frailty_care_load({**GOOD, field: 0.0})  # type: ignore[arg-type]

    def test_an_unsourced_intake_is_rejected(self) -> None:
        """A guess wearing a measurement's clothes is the thing to catch."""
        with pytest.raises(ValueError, match="source"):
            frailty_care_load({**GOOD, "source": "   "})  # type: ignore[arg-type]


class TestItReportsItsOwnScope:

    def test_the_share_of_care_is_computed_not_restated(self) -> None:
        """
        It comes from `AGE_GROUPS`' care weights, so it moves if the care keys
        move. Restating the measured 7.5–11.6% as a literal is the drift this
        repo has caught nine times.
        """
        r = frailty_care_load(GOOD)
        expected = (
            sum(g["fraction"] * g["care_weight"] for g in AGE_GROUPS.values()
                if g["care_key"] == "frailty")
            / sum(g["fraction"] * g["care_weight"] for g in AGE_GROUPS.values())
        )
        assert r["share_of_care"] == pytest.approx(expected)

    def test_the_socket_settles_a_minority_of_care(self) -> None:
        """The scope that keeps it from being oversold."""
        r = frailty_care_load(GOOD)
        assert 0.05 < r["share_of_care"] < 0.20, (
            f"frailty care is {r['share_of_care']:.1%} of the model's care "
            "obligation. If it has become the dominant term the care keys have "
            "moved, and record/personal.md's 'an eighth of care' needs redoing."
        )

    def test_the_product_is_what_the_model_consumes(self) -> None:
        r = frailty_care_load(GOOD)
        assert r["hours_per_capita"] == pytest.approx(
            GOOD["frailty_years_per_capita"] * GOOD["care_hours_per_frailty_year"])


class TestMorbidityDirectionIsAnswerableNow:
    """
    The question the retired elderly ε-drift asserted an answer to. It is not
    answered here — it is made answerable, which is the whole difference.
    """

    def test_expansion_and_compression_are_both_reachable(self) -> None:
        early = GOOD
        expansion = {**GOOD, "frailty_years_per_capita": 0.42}
        compression = {**GOOD, "frailty_years_per_capita": 0.30}
        assert morbidity_direction(early, expansion)["direction"] == "expansion"
        assert morbidity_direction(early, compression)["direction"] == "compression"
        assert morbidity_direction(early, GOOD)["direction"] == "stationary"

    def test_the_hours_ratio_can_oppose_the_frailty_ratio(self) -> None:
        """
        Why the report returns both. Frailty-years can fall while intensity
        rises, so a compression verdict does NOT imply falling care hours, and
        reading one number would give the opposite answer.
        """
        later = {**GOOD, "frailty_years_per_capita": 0.30,
                 "care_hours_per_frailty_year": 1800.0}
        r = morbidity_direction(GOOD, later)
        assert r["direction"] == "compression"
        assert r["hours_ratio"] > 1.0

    def test_it_refuses_to_report_a_rate(self) -> None:
        r = morbidity_direction(GOOD, {**GOOD, "frailty_years_per_capita": 0.42})
        assert "SIGN ONLY" in r["note"]
        assert "per_year" not in r and "rate" not in r

    def test_institutional_coverage_travels_with_the_comparison(self) -> None:
        """
        ATUS-style household frames exclude the institutional population, which
        is where the terminal window sits. Comparing a frame that covers it with
        one that does not measures the frame, not the morbidity.
        """
        household_only = {**GOOD, "covers_institutional": False}
        r = morbidity_direction(GOOD, household_only)
        assert r["both_cover_institutional"] is False
