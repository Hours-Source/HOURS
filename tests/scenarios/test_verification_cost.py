"""
Verification cost against the obligation it serves — `scenarios/verification_cost.py`.

WHAT IS AT STAKE. `anchor_comparison_draft.md` §7 states a falsification
condition in as many words: *if verification cost, once costed, exceeds the
obligation it verifies at any point on the arc, the anchor is not cheaper to
audit than the incumbents.* Phase 1 counted the workers; this module puts them
beside the obligation, and `verification_crossover()` is the answer.

WHAT THESE TESTS PIN. Not the level — it is a bound at US institutional density
and it will move. They pin that **the search can fail**, that the frame is
declared and honoured, that the two scaling bases are both reported and neither
adopted, and that the whole thing changes no shipped number.

THE FIRST OF THOSE IS THE ONE THAT MATTERS. A crossover search that can only
ever return None answers §7 by construction, which would make the framework's
own falsifier unfalsifiable — the `LEVY_SUFFICIENCY_WARN` failure, applied to
the anchor's central claim. `test_the_search_can_find_a_crossover` forces one.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import REFERENCE_FRAME_POPULATION, US_REFERENCE_POPULATION
from hours_eoh.scenarios import verification_cost as VC
from hours_eoh.scenarios.obligation_accounts import obligation_accounts

ARC = (0.0, 0.40, 0.90, 0.99)
BASES = ("per_capita", "per_registered")


class TestTheFalsifierCanActuallyFire:
    """
    RECURRING FAILURE MODE 9, asked in both directions: can it fire, and can it
    NOT fire? A §7 answer produced by a search incapable of finding anything is
    not an answer.
    """

    def test_it_reports_no_crossover_on_the_shipped_census(self):
        """The result as measured. Stated as a fact, not as a pass."""
        for scope in ("core", "broad"):
            for basis in BASES:
                c = VC.verification_crossover(scope=scope, basis=basis)
                assert c["crossover_epsilon"] is None, (
                    f"{scope}/{basis} now crosses at {c['crossover_epsilon']} — "
                    "§7's falsification condition is met and the anchor page "
                    "must stop claiming the audit advantage past that ε"
                )

    def test_the_search_can_find_a_crossover(self, monkeypatch):
        """
        THE FALSIFIABILITY CHECK. Force the rate above the obligation and the
        bisection must locate the crossing. Without this, "no crossover" is a
        property of the search rather than of the framework.
        """
        monkeypatch.setattr(VC, "verification_hours_per_capita", lambda scope="core": 5_000.0)
        c = VC.verification_crossover()
        assert c["crossover_epsilon"] is not None
        assert 0.0 <= c["crossover_epsilon"] <= 0.99
        assert c["ratio_at_zero"] > 1.0

    def test_a_rate_that_crosses_midway_is_located_not_clamped(self, monkeypatch):
        """A search that only ever returns an endpoint is a threshold, not a search."""
        at_zero = obligation_accounts(0.0)["obligation"] / REFERENCE_FRAME_POPULATION
        at_top = obligation_accounts(0.99)["obligation"] / REFERENCE_FRAME_POPULATION
        monkeypatch.setattr(
            VC, "verification_hours_per_capita",
            lambda scope="core": (at_zero + at_top) / 2.0,
        )
        c = VC.verification_crossover()
        assert c["crossover_epsilon"] is not None
        assert 0.0 < c["crossover_epsilon"] < 0.99, (
            f"crossover landed on an endpoint ({c['crossover_epsilon']}), which "
            "is what a clamp does rather than a bisection"
        )


class TestBothBasesAreReportedAndNeitherIsAdopted:
    """
    The two readings disagree about the ε-DIRECTION, which is the only thing
    §7 turns on. Presenting one as the answer would settle by presentation a
    question no measurement here settles.
    """

    def test_the_ratio_falls_under_per_capita(self):
        rows = VC.verification_arc(basis="per_capita")
        ratios = [r["verification_over_obligation"] for r in rows]
        assert ratios == sorted(ratios, reverse=True), (
            "a fixed per-person rate against a growing obligation must give a "
            "falling share"
        )

    def test_the_ratio_rises_then_turns_under_per_registered(self):
        """
        It follows the register, and registered EOH is hump-shaped: the
        registration share saturates while human EOH collapses.
        """
        rows = VC.verification_arc(basis="per_registered")
        ratios = [r["verification_over_obligation"] for r in rows]
        assert ratios[0] < ratios[1] < ratios[2], "must rise while the ledger fills"
        assert ratios[3] < ratios[2], "and turn where registered EOH peaks"

    def test_the_two_bases_disagree_at_the_ends_and_meet_at_the_reference(self):
        pc = VC.verification_arc(basis="per_capita")
        pr = VC.verification_arc(basis="per_registered")
        assert pc[1]["verification_over_obligation"] == pytest.approx(
            pr[1]["verification_over_obligation"], rel=1e-9
        ), "ε=0.40 is the declared reference point; the bases must agree there"
        assert pc[0]["verification_over_obligation"] != pytest.approx(
            pr[0]["verification_over_obligation"], rel=1e-3
        ), "if they agree everywhere, one of them is not implemented"

    def test_neither_basis_is_adopted(self):
        u = VC.which_basis_is_unsettled()
        assert u["adopted"] is None
        assert len(u["settles_by"]) > 60
        for key in ("per_capita", "per_registered", "why_it_matters"):
            assert len(u[key]) > 80

    def test_an_unknown_basis_raises(self):
        with pytest.raises(ValueError, match="basis must be"):
            VC.verification_account(0.40, basis="whatever")


class TestTheFrameIsDeclaredAndHonoured:
    """
    RECURRING FAILURE MODE 6. The census is counted over the US population and
    the package's extensives are stated at 1M. A per-capita rate is the only
    thing that survives the move, and this pins that it actually does.
    """

    def test_the_us_census_declares_its_frame(self):
        c = VC.verification_hours_us()
        assert c["frame"] == "US"
        assert c["frame_population"] == US_REFERENCE_POPULATION

    def test_the_rate_is_frame_invariant_and_the_total_is_not(self):
        rate = VC.verification_hours_per_capita()
        small = VC.verification_account(0.40, population=1.0e6)
        large = VC.verification_account(0.40, population=335.0e6)
        assert small["rate_per_capita"] == pytest.approx(rate, rel=1e-12)
        assert large["rate_per_capita"] == pytest.approx(rate, rel=1e-12)
        assert large["verification"] == pytest.approx(
            small["verification"] * 335.0, rel=1e-9
        )

    def test_the_ratio_is_frame_invariant(self):
        """
        Both sides scale with population, so a share must not. This is the check
        that would have caught `teh_per_capita` dropping its divisor — the two
        collectives compared must DIFFER in the quantity being divided out.
        """
        small = VC.verification_account(0.40, population=1.0e6)
        large = VC.verification_account(0.40, population=50.0e6)
        assert small["verification_over_obligation"] == pytest.approx(
            large["verification_over_obligation"], rel=1e-9
        )

    def test_the_hours_conversion_is_shared_with_the_servicing_census(self):
        """One account of hours-per-worker-year, not two."""
        from hours_eoh.scenarios.food_conservation import hours_per_worker_year
        assert VC.verification_hours_us()["hours_per_worker_year"] == pytest.approx(
            hours_per_worker_year(), rel=1e-12
        )


class TestTheBoundsSurviveTheConversion:

    def test_core_stays_below_broad_at_every_arc_point(self):
        for e in ARC:
            for basis in BASES:
                c = VC.verification_account(e, scope="core", basis=basis)
                b = VC.verification_account(e, scope="broad", basis=basis)
                assert c["verification"] < b["verification"], f"at ε={e}, {basis}"

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_term_is_meaningful_across_the_whole_arc(self, epsilon):
        r = VC.verification_account(epsilon)
        assert r["verification"] > 0.0
        assert 0.0 < r["verification_over_obligation"] < 1.0
        assert r["delivery_with_verification"] > r["delivery"]


class TestTheVerdictIsComputedNotRestated:
    """
    RECURRING FAILURE MODE 13. A verdict written beside the numbers drifts from
    them; this one is derived from them and must change when they do.
    """

    def test_the_verdict_reports_the_measured_peak(self):
        r = VC.verification_report()
        assert f"{r['peak_share_of_obligation']:.2%}" in r["verdict"]

    def test_the_verdict_flips_when_a_crossover_appears(self, monkeypatch):
        monkeypatch.setattr(VC, "verification_hours_per_capita", lambda scope="core": 5_000.0)
        r = VC.verification_report()
        assert "does not hold" in r["verdict"]
        assert "§7" in r["verdict"]

    def test_the_report_carries_its_own_caveats(self):
        r = VC.verification_report()
        assert r["direction_of_error"]["netted"] is None
        assert len(r["cannot_settle"]) >= 4
        assert r["adopted"] is False


class TestVerificationChangesNothing:
    """
    REPORTING ONLY, pinned. Phase 3 — whether the term enters `total_eoh` — is
    the theory change, and importing this module must not be it.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_accounts_are_untouched_by_this_module(self, epsilon):
        before = obligation_accounts(epsilon)
        VC.verification_report()
        after = obligation_accounts(epsilon)
        assert before == after

    @pytest.mark.parametrize("epsilon", ARC)
    def test_total_eoh_does_not_carry_the_term(self, epsilon):
        from hours_eoh.core.eoh_generation import total_eoh
        acc = VC.verification_account(epsilon)
        assert total_eoh(epsilon=epsilon)["total"] == pytest.approx(
            acc["obligation"] + acc["delivery"] + acc["stock"], rel=1e-9
        ), "the partition still closes without verification, so it is not adopted"

    def test_nothing_in_core_or_land_imports_it(self):
        import pathlib
        import hours_eoh
        root = pathlib.Path(hours_eoh.__file__).resolve().parent
        offenders = [
            p.relative_to(root).as_posix()
            for d in ("core", "land")
            for p in (root / d).rglob("*.py")
            if "verification_cost" in p.read_text(encoding="utf-8", errors="ignore")
        ]
        assert not offenders, f"{offenders} import a scenario; the layer rule forbids it"
