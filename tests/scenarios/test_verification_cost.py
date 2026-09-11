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
        """
        A search that only ever returns an endpoint is a threshold, not a search.

        **THIS TEST'S ORIGINAL FIXTURE DID NOT CROSS MIDWAY** (found 2026-09-10).
        It set the per-capita rate to the mean of the obligation at ε=0 and
        ε=0.99. Because the obligation only grows ~5% over the arc, that mean
        sits ABOVE the ε=0 obligation: the ratio is **1.026 at ε=0** and the
        crossing is at zero. The assertion `0.0 < crossover` passed anyway,
        because a bisection seeded at `lo=0.0` converges toward zero without
        ever reaching it — the invariant was manufactured by the implementation
        (failure mode 2), and the test that was supposed to prove the search is
        not a clamp was checking floating-point convergence instead.

        A genuine interior crossing needs the NON-MONOTONE basis, which is what
        `per_registered` is and what `TestTheCrossoverSearchSeesMidArcExcursions`
        was built around.
        """
        base = VC.verification_hours_per_capita("core")
        monkeypatch.setattr(VC, "verification_hours_per_capita",
                            lambda scope="core": base * 100)
        c = VC.verification_crossover(basis="per_registered")
        assert c["ratio_at_zero"] < 1.0, (
            "the fixture must not already be over at ε=0, or 'midway' is not "
            "what is being tested — the defect this docstring records"
        )
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


class TestThePeakIsNotReadOffTheReportingPoints:
    """
    THE DEFECT THIS CLASS EXISTS FOR, and it shipped for two days.

    `verification_report` computed `peak_share_of_obligation` as `max` over the
    four arc reporting points and the verdict called it "the peak". The
    `per_registered` ratio turns where registered EOH peaks, at ε≈0.765 — which
    sits BETWEEN the 0.40 and 0.90 reporting points, so the four-point maximum
    understated it by ~18% at core scope and ~17% at broad, and both understated
    figures were published in the anchor comparison as "peak".

    That is the ε=0.40 trap one point over: measured where the defect is
    invisible. `verification_arc`'s own docstring names the trap.
    """

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_peak_exceeds_the_reporting_point_maximum(self, scope):
        r = VC.verification_report(scope)
        assert r["peak_share_of_obligation"] > r["reporting_point_max"], (
            "if these are equal the peak is being read off the reporting "
            "points again and the search grid has stopped doing anything"
        )

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_peak_lies_strictly_between_two_reporting_points(self, scope):
        """
        Stronger than "not ON a point": the peak must sit in the OPEN interval
        the four points cannot see into. `0.99·i/200` never lands exactly on
        0.40 or 0.90, so an equality test could only ever fire at the endpoints
        and would be weaker than its own docstring.
        """
        peak = VC.verification_report(scope)["peak_epsilon"]
        assert 0.40 < peak < 0.90, (
            f"peak at ε={peak}: outside (0.40, 0.90) the four reporting points "
            "bracket it, and the dense grid stops being what finds it"
        )

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_peak_is_on_the_basis_that_turns(self, scope):
        assert VC.verification_report(scope)["peak_basis"] == "per_registered", (
            "per_capita is monotone and its maximum IS an endpoint; the peak "
            "only hides between points on the basis that turns"
        )

    def test_refining_the_grid_does_not_move_the_peak(self):
        """
        `PEAK_SEARCH_POINTS` is numerics, not a parameter — `test_tolerances`'
        rule. Doubling the resolution must not move the reported peak by more
        than the grid can resolve.
        """
        coarse = VC.verification_report("core")["peak_share_of_obligation"]
        fine = max(
            row["verification_over_obligation"]
            for b in ("per_capita", "per_registered")
            for row in VC.verification_arc(
                scope="core", basis=b,
                points=tuple(i / 2000 for i in range(1980)) + (0.99,),
            )
        )
        assert fine == pytest.approx(coarse, rel=2e-3), (
            "the grid is selecting the answer, which makes it a parameter"
        )


class TestTheCrossoverSearchSeesMidArcExcursions:
    """
    THE SECOND GATE THAT DID NOT BITE, found the same day as the first and one
    function over.

    `verification_crossover` decided "no crossover" from `ratio(0) < 1 and
    ratio(0.99) < 1`. That is valid only for a MONOTONE ratio, and
    `per_registered` is not monotone — it turns where registered EOH peaks. So
    there is a band of rates whose cost exceeds the obligation across the middle
    of the arc and is back below it at both ends, and the search returned None
    for every one of them.

    Measured on the shipped configuration before the fix: at 110x the rate the
    ratio peaks at 1.25 and the answer was None. **§7's falsifier was
    unfalsifiable in exactly the region where the extremum hides.**
    """

    @staticmethod
    def _at_rate(monkeypatch, multiple):
        base = VC.verification_hours_per_capita("core")
        monkeypatch.setattr(VC, "verification_hours_per_capita",
                            lambda scope="core": base * multiple)

    @pytest.mark.parametrize("multiple", (100, 110, 120))
    def test_a_crossing_that_does_not_reach_either_endpoint_is_found(
        self, monkeypatch, multiple
    ):
        self._at_rate(monkeypatch, multiple)
        c = VC.verification_crossover(basis="per_registered")
        assert c["peak_ratio"] > 1.0, "the fixture must actually cross"
        assert c["ratio_at_zero"] < 1.0 and c["ratio_at_top"] < 1.0, (
            "and it must NOT cross at either endpoint, or the old endpoint "
            "test would have caught it and this gate proves nothing"
        )
        assert c["crossover_epsilon"] is not None, (
            "the excursion was missed — the search is reading the endpoints "
            "again and 'no crossover' is a property of the search"
        )
        assert 0.0 < c["crossover_epsilon"] < 0.99

    def test_the_excursion_reports_where_it_comes_back_under(self, monkeypatch):
        self._at_rate(monkeypatch, 110)
        c = VC.verification_crossover(basis="per_registered")
        assert c["returns_below_at"] is not None
        assert c["returns_below_at"] > c["crossover_epsilon"], (
            "an excursion that never returns is a different finding from one "
            "that does, and the page would say different things about them"
        )

    def test_a_crossing_that_persists_still_reports_no_exit(self, monkeypatch):
        self._at_rate(monkeypatch, 150)
        c = VC.verification_crossover(basis="per_registered")
        assert c["crossover_epsilon"] is not None
        assert c["returns_below_at"] is None, (
            "the ratio is still above 1.0 at ε=0.99, so there is no return"
        )

    def test_the_shipped_configuration_still_finds_nothing(self):
        """The fix must not manufacture the crossing it was built to detect."""
        for scope in ("core", "broad"):
            for basis in ("per_capita", "per_registered"):
                c = VC.verification_crossover(scope=scope, basis=basis)
                assert c["crossover_epsilon"] is None
                assert c["peak_ratio"] < 1.0


class TestTheNetFractionFalsifier:
    """
    §7's falsifier is a crossover at ratio 1.0, and the net-energy literature's
    result is that such a test fires far too late. What matters is the fraction
    of gross obligation left for entropy reduction, and it degrades
    non-linearly. A register consuming 20% of what it verifies has not crossed
    over and has lost the audit claim anyway.

    The FLOOR is the caller's argument. A threshold this module shipped would be
    calibrated to the configuration it is then checked against — the defect
    `LEVY_SUFFICIENCY_WARN` has, applied to the anchor's central audit claim.
    """

    def test_the_floor_is_required_and_has_no_default(self):
        import inspect
        sig = inspect.signature(VC.net_fraction_falsifier)
        assert sig.parameters["floor"].default is inspect.Parameter.empty, (
            "a shipped floor is a threshold calibrated to the target it checks"
        )

    @pytest.mark.parametrize("bad", (0.0, 1.0, -0.1, 1.5))
    def test_a_floor_outside_the_unit_interval_raises(self, bad):
        with pytest.raises(ValueError):
            VC.net_fraction_falsifier(bad)

    def test_it_fires_on_a_tight_floor_and_does_not_on_a_loose_one(self):
        """Both directions, or the gate proves nothing."""
        tight = VC.net_fraction_falsifier(0.99, scope="broad")
        loose = VC.net_fraction_falsifier(0.80, scope="broad")
        assert tight["breach_epsilon"] is not None, "cannot fire"
        assert loose["breach_epsilon"] is None, "cannot NOT fire"

    def test_the_minimum_net_fraction_sits_at_the_ratio_peak(self):
        """net = 1 − ratio, so their extrema must coincide. If they drift
        apart, the two are not being computed from the same quantity."""
        for scope in ("core", "broad"):
            nf = VC.net_fraction_falsifier(0.99, scope=scope)
            cr = VC.verification_crossover(scope=scope, basis="per_registered")
            assert nf["min_at_epsilon"] == pytest.approx(cr["peak_epsilon"])
            assert nf["min_net_fraction"] == pytest.approx(
                1.0 - cr["peak_ratio"]
            )

    def test_a_tighter_floor_breaches_strictly_earlier(self):
        """
        Direction, not just presence: a higher floor is a stricter standard, so
        it must be breached at a LOWER ε. Measured at broad scope the series is
        0.634 / 0.549 / 0.465 / 0.371 for floors 0.975 / 0.98 / 0.985 / 0.99 —
        strictly decreasing, which is what makes the floor a dial rather than a
        switch.
        """
        breaches = [
            VC.net_fraction_falsifier(f, scope="broad")["breach_epsilon"]
            for f in (0.975, 0.98, 0.985, 0.99)
        ]
        assert all(b is not None for b in breaches)
        assert breaches == sorted(breaches, reverse=True)
        assert len(set(breaches)) == len(breaches), "a dial, not a switch"


class TestTheRegistrantScopeSensitivityIsNotAnEstimate:
    """
    THE CONDITIONAL THAT KEEPS §7's ANSWER HONEST.

    The census is apparatus-side. This asks what the answer becomes if the
    registrant side is added at a stated multiple — and refuses to pick one.
    """

    def test_the_multiple_is_required_and_has_no_default(self):
        import inspect
        sig = inspect.signature(VC.registrant_scope_sensitivity)
        assert sig.parameters["registrant_multiple"].default is (
            inspect.Parameter.empty
        ), (
            "a shipped multiple turns a transferred judgement from one "
            "adversarial money-denominated case into a constant"
        )

    @pytest.mark.parametrize("bad", (0.0, -1.0))
    def test_a_non_positive_multiple_raises(self, bad):
        with pytest.raises(ValueError):
            VC.registrant_scope_sensitivity(bad)

    def test_it_never_claims_to_be_measured(self):
        r = VC.registrant_scope_sensitivity(40.0)
        assert r["is_measured"] is False
        for token in ("adversarial", "7.7x", "40x"):
            assert token in r["judgement"], (
                f"{token!r} dropped from the declared judgement; the caveats "
                "are what stop this being read as a measurement"
            )

    def test_the_units_matching_multiple_crosses_at_broad_and_not_at_core(self):
        """
        THE FINDING, PINNED IN BOTH DIRECTIONS. ~40x is the one comparison in
        matching units — workers against workers. At broad scope it crosses; at
        core it does not. Neither "the falsifier fires" nor "it does not" is
        warranted, and a test that pinned only one of these would settle by
        presentation a question the measurement does not settle.
        """
        core = VC.registrant_scope_sensitivity(40.0, scope="core")
        broad = VC.registrant_scope_sensitivity(40.0, scope="broad")
        assert core["crosses"] is False
        assert broad["crosses"] is True
        assert 0.0 < broad["crossover_epsilon"] < 0.99

    def test_the_apparatus_figure_is_unchanged_by_the_sensitivity(self):
        """The conditional must not move what was actually measured."""
        for scope in ("core", "broad"):
            measured = VC.verification_crossover(
                scope=scope, basis="per_registered"
            )["peak_ratio"]
            for m in (1.0, 40.0, 100.0):
                r = VC.registrant_scope_sensitivity(m, scope=scope)
                assert r["apparatus_peak"] == pytest.approx(measured)

    def test_the_registrant_side_ADDS_to_the_apparatus_rather_than_replacing_it(
        self,
    ):
        """
        THE STRUCTURE, PINNED — a mutation to `a * m` from `a * (1 + m)` passed
        every other test in this class, because at m=40 the two differ by 2.5%
        and both still cross at broad and not at core.

        The two sides are disjoint by construction: one is an occupation and
        the other is definitionally not. So the registrant side is ADDITIONAL,
        and as the multiple vanishes the combined figure must return the
        measured apparatus — not zero.
        """
        for scope in ("core", "broad"):
            apparatus = VC.registrant_scope_sensitivity(
                1.0, scope=scope
            )["apparatus_peak"]
            tiny = VC.registrant_scope_sensitivity(1e-9, scope=scope)
            assert tiny["combined_peak"] == pytest.approx(apparatus, rel=1e-6), (
                "a vanishing registrant side left the apparatus uncounted, so "
                "the term is replacing the census rather than adding to it"
            )
            for m in (1.0, 23.0, 40.0):
                r = VC.registrant_scope_sensitivity(m, scope=scope)
                assert r["combined_peak"] == pytest.approx(
                    apparatus * (1.0 + m)
                ), "the composition is not additive"
                assert r["combined_peak"] > apparatus * m

    def test_a_larger_multiple_never_reduces_the_combined_cost(self):
        prev = 0.0
        for m in (1.0, 10.0, 23.0, 40.0, 80.0):
            peak = VC.registrant_scope_sensitivity(m)["combined_peak"]
            assert peak > prev
            prev = peak


class TestTheReportSaysWhatItIsAVERDICTABOUT:
    """
    MODE 10 — the reported value read as something narrower than it is.

    The report's verdict said "verification cost stays below the obligation
    everywhere on the arc". True of the APPARATUS, and read by the CLI as an
    answer about verification. Meanwhile the page it feeds says the answer is
    undetermined. The key is now `apparatus_verdict` and the scope caveat
    travels beside it carrying the multiple at which the scope would cross.
    """

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_verdict_names_the_apparatus(self, scope):
        r = VC.verification_report(scope)
        assert "APPARATUS" in r["apparatus_verdict"]
        assert r["verdict"] == r["apparatus_verdict"], "the alias diverged"

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_scope_caveat_is_present_and_names_the_instrument(self, scope):
        r = VC.verification_report(scope)
        assert "does not answer §7" in r["scope_verdict"].lower()
        assert "registrant_scope_sensitivity" in r["scope_verdict"]

    @pytest.mark.parametrize("scope", ("core", "broad"))
    def test_the_crossing_multiple_agrees_with_the_sensitivity(self, scope):
        """
        Computed from the peak as 1/peak − 1, and checked against the function
        that actually sweeps it. Two accounts of one number is the shape that
        let `psi` diverge from `psi_applied`, so they must agree.
        """
        m = VC.verification_report(scope)["crossing_registrant_multiple"]
        assert VC.registrant_scope_sensitivity(
            m * 1.001, scope=scope
        )["crosses"] is True
        assert VC.registrant_scope_sensitivity(
            m * 0.999, scope=scope
        )["crosses"] is False

    def test_the_measured_multiple_straddles_the_two_scopes(self):
        """
        THE FINDING, STATED AS A THRESHOLD RATHER THAN A VERDICT. The only
        measured registrant multiple is ~40x. Broad crosses above ~34x, core
        only above ~87x. So 40x sits BETWEEN them — which is exactly why
        neither "fires" nor "does not fire" can be asserted.
        """
        core = VC.verification_report("core")["crossing_registrant_multiple"]
        broad = VC.verification_report("broad")["crossing_registrant_multiple"]
        assert broad < 40.0 < core, (
            f"the measured 40x no longer straddles the scopes "
            f"(broad {broad:.1f}, core {core:.1f}); the page's 'undetermined' "
            "sentence has become either true by default or false"
        )


class TestTheCorridorReportsWhichBoundActuallyBinds:
    """
    THE FINDING: §7's falsifier tests the NON-BINDING constraint over 96% of
    the arc.

    Three bounds, all expressed as the registrant multiple at which they bind,
    so they are comparable:

      ratio     verification equals the obligation — §7's test, institutional.
      clearing  obligation + verification exceeds the labour a population can
                supply. An hour documenting is an hour not fulfilling.
      physical  verification alone exceeds total labour supply. The only bound
                with no institution in it.

    The clearing bound is tighter than the ratio bound everywhere below
    ε≈0.96, and nothing checked which bound bit before this existed.
    """

    ARC = (0.0, 0.20, 0.40, 0.70, 0.90)

    def test_the_multiple_is_required_and_moves_no_bound(self):
        import inspect
        sig = inspect.signature(VC.verification_feasibility_corridor)
        assert sig.parameters["registrant_multiple"].default is (
            inspect.Parameter.empty
        )
        a = VC.verification_feasibility_corridor(1.0)
        b = VC.verification_feasibility_corridor(500.0)
        for key in ("ratio_bound", "clearing_bound", "physical_bound"):
            assert a[key] == pytest.approx(b[key]), (
                f"{key} moved with the declared multiple; a threshold that "
                "depends on the assertion being tested is not a threshold"
            )

    @pytest.mark.parametrize("epsilon", ARC)
    @pytest.mark.parametrize("basis", ("per_capita", "per_registered"))
    def test_clearing_binds_before_ratio_across_the_low_arc(self, epsilon, basis):
        r = VC.verification_feasibility_corridor(
            1.0, epsilon=epsilon, basis=basis
        )
        assert r["clearing_bound"] < r["ratio_bound"], (
            f"at ε={epsilon} the ratio bound is now tighter than clearing. "
            "§7's falsifier would then be testing the binding constraint, "
            "which it was not when this was written."
        )
        assert r["binding_bound"] == "clearing_bound"

    def test_the_ratio_bound_does_take_over_at_the_top(self):
        """Both directions. A bound that never binds is not a bound."""
        r = VC.verification_feasibility_corridor(1.0, epsilon=0.99)
        assert r["binding_bound"] == "ratio_bound"

    @pytest.mark.parametrize("epsilon", ARC + (0.99,))
    def test_the_physical_bound_is_never_the_tightest(self, epsilon):
        """
        It is the bound with no institution in it, so it is the one that cannot
        be argued away — and it is always the loosest, which is why the other
        two are where the argument lives. If it ever binds first, verification
        alone is consuming a population's entire labour supply and the other
        two have stopped meaning anything.
        """
        r = VC.verification_feasibility_corridor(1.0, epsilon=epsilon)
        assert r["physical_bound"] > r["clearing_bound"]
        assert r["binding_bound"] != "physical_bound"

    def test_the_measured_analogue_breaks_three_of_the_four_configurations(self):
        """
        ~40x is the one registrant multiple measured in matching units. It sits
        INSIDE the corridor's spread rather than clear of it:

            broad/per_capita      9.3x  -> broken
            broad/per_registered 23.9x  -> broken
            core /per_capita     24.8x  -> broken
            core /per_registered 61.5x  -> survives

        Three of four. That is the sentence §7's "two orders of magnitude
        clear" was hiding, and it is why neither verdict is assertable.
        """
        pts = tuple(i / 50 for i in range(50)) + (0.99,)
        tightest = {}
        for scope in ("core", "broad"):
            for basis in ("per_capita", "per_registered"):
                rows = VC.which_binds_across_the_arc(
                    scope=scope, basis=basis, points=pts
                )
                tightest[(scope, basis)] = min(
                    r["binding_multiple"] for r in rows
                )
        broken = [k for k, v in tightest.items() if v < 40.0]
        assert len(broken) == 3, (
            f"the 40x analogue now breaks {len(broken)} of 4 configurations, "
            f"not 3: {tightest}. The page states three."
        )
        assert ("core", "per_registered") not in broken, (
            "the one configuration that survives is core/per_registered; if "
            "that changes, the framework has no surviving configuration and "
            "the page must say so"
        )

    def test_it_never_claims_to_be_measured(self):
        r = VC.verification_feasibility_corridor(40.0)
        assert r["is_measured"] is False
        assert "edges and no centre" in r["note"]


class TestWhatWouldCloseTheBand:
    """
    "Usable" is the kind of word that gets asserted beside evidence rather than
    computed from it. Three conditions, each checkable, all required.
    """

    def test_the_shipped_state_is_open_edges(self):
        r = VC.corridor_is_usable()
        assert r["verdict"] == "open_edges"
        assert r["conditions"]["1_multiple_is_measured"] is False
        assert r["conditions"]["3_declared_value_sits_inside_with_margin"] is None, (
            "condition 3 must be UNDETERMINABLE, not False, while 1 is unmet — "
            "reporting it as failed would claim a result nothing establishes"
        )

    def test_the_band_is_already_bounded_by_three_instruments(self):
        r = VC.corridor_is_usable()
        assert r["conditions"]["2_bounded_by_independent_instruments"] is True
        assert r["independent_instruments"] == 3

    def test_it_can_close(self):
        """A verdict that can only ever be `open_edges` is not a verdict."""
        r = VC.corridor_is_usable(registrant_multiple=5.0,
                                  multiple_error_factor=1.5)
        assert r["verdict"] == "closed_and_usable"
        assert all(v is True for v in r["conditions"].values())

    def test_the_transferred_figure_does_not_close_it(self):
        """
        40x widened by its own 7.7x error bar is 308x against a binding bound
        of ~62x. **A value inside the band with an error bar wider than its
        margin has not been shown to be inside it** — that is the whole reason
        condition 3 widens before it compares.
        """
        r = VC.corridor_is_usable(registrant_multiple=40.0,
                                  multiple_error_factor=7.7)
        assert r["verdict"] == "open_edges"
        assert r["conditions"]["1_multiple_is_measured"] is True
        assert r["conditions"]["3_declared_value_sits_inside_with_margin"] is False

    def test_the_error_bar_is_what_decides_it(self):
        """Same multiple, different error bar, different verdict."""
        tight = VC.corridor_is_usable(registrant_multiple=20.0,
                                      multiple_error_factor=1.2)
        loose = VC.corridor_is_usable(registrant_multiple=20.0,
                                      multiple_error_factor=7.7)
        assert tight["verdict"] == "closed_and_usable"
        assert loose["verdict"] == "open_edges"

    def test_it_names_the_instrument_that_would_close_it(self):
        assert "Standard Cost Model" in VC.corridor_is_usable()["what_would_close_it"]
