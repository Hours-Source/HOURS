"""
Tests for hours_eoh.scenarios.shocks at the canonical import location.

Covers: automation_failure_shock, demographic_shock, ecological_eoh_spike,
        labor_income_shock, compound_shock.
"""

import pytest
from hours_eoh.scenarios.shocks import (
    _LABOR_INCOME_AUTO_SLOPE, _LABOR_INCOME_BASE, _LABOR_INCOME_MIN)
from hours_eoh.scenarios.shocks import (
    automation_failure_shock,
    demographic_shock,
    ecological_eoh_spike,
    labor_income_shock,
    compound_shock,
)

VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


class TestAutomationFailureShock:
    def test_returns_expected_keys(self):
        result = automation_failure_shock(epsilon=0.40)
        for key in ("scenario", "epsilon", "total_eoh", "machine_eoh_lost",
                    "taken_up_eoh", "deferred_eoh", "deferred_personal_eoh",
                    "covered", "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert automation_failure_shock(0.40)["scenario"] == "automation_failure_shock"

    def test_outcome_is_valid(self):
        for eps in (0.0, 0.40, 0.80):
            result = automation_failure_shock(eps)
            assert result["outcome"] in VALID_OUTCOMES

    def test_low_epsilon_stable(self):
        result = automation_failure_shock(epsilon=0.10)
        assert result["outcome"] == "STABLE"

    def test_the_lost_load_is_the_observed_machine_share(self):
        # Retired 2026-09-30: this pinned `automation_eoh == total × ε`, the
        # capability index, which counts the labour care's automation floor
        # keeps human as if machines carried it.
        from hours_eoh.core.eoh_fulfillment import observable_epsilon
        for eps in (0.40, 0.90, 0.99):
            r = automation_failure_shock(epsilon=eps)
            assert r["machine_eoh_lost"] == pytest.approx(
                r["total_eoh"] - r["human_eoh_before"], rel=1e-12)
            assert r["machine_eoh_lost"] < r["total_eoh"] * eps

    def test_recommendation_is_string(self):
        result = automation_failure_shock(0.50)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10


class TestDemographicShock:
    def test_growth_shock_increases_eoh(self):
        result = demographic_shock(0.40, "growth", 0.20)
        assert result["eoh_after"] > result["eoh_before"]

    def test_decline_shock_decreases_eoh(self):
        result = demographic_shock(0.40, "decline", 0.20)
        assert result["eoh_after"] < result["eoh_before"]

    def test_aging_shock_changes_population(self):
        result = demographic_shock(0.40, "aging", 0.10)
        assert result["eoh_delta"] != 0.0

    def test_outcome_is_valid(self):
        for shock in ("growth", "decline", "aging"):
            result = demographic_shock(0.40, shock, 0.10)
            assert result["outcome"] in VALID_OUTCOMES

    def test_invalid_shock_type_raises(self):
        with pytest.raises(ValueError):
            demographic_shock(0.40, "flood", 0.10)

    def test_invalid_magnitude_raises(self):
        with pytest.raises(ValueError):
            demographic_shock(0.40, "growth", 1.5)

    def test_scenario_name(self):
        assert demographic_shock(0.40, "growth", 0.10)["scenario"] == "demographic_shock"


class TestEcologicalEohSpike:
    def test_threshold_crossed_detected(self):
        result = ecological_eoh_spike(
            epsilon=0.40,
            ecosystem_health_before=0.50,
            ecosystem_health_after=0.30,
        )
        assert result["threshold_crossed"] is True

    def test_no_threshold_cross_when_still_above(self):
        result = ecological_eoh_spike(
            epsilon=0.40,
            ecosystem_health_before=0.80,
            ecosystem_health_after=0.50,
        )
        assert result["threshold_crossed"] is False

    def test_spike_is_non_negative(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.30)
        assert result["eoh_spike"] >= 0.0

    def test_no_spike_when_health_improves(self):
        result = ecological_eoh_spike(0.40, 0.30, 0.70)
        assert result["eoh_spike"] == 0.0

    def test_outcome_is_valid(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.30)
        assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.50)
        assert result["scenario"] == "ecological_eoh_spike"


# ===========================================================================
# Labor Income Shock
# ===========================================================================

class TestLaborIncomeShock:

    def test_returns_expected_keys(self):
        result = labor_income_shock(0.40, 1.0)
        for key in ("scenario", "epsilon", "income_fraction",
                    "baseline_income", "shocked_income",
                    "trust_solvent_before", "trust_solvent_after",
                    "surplus_deficit_before", "surplus_deficit_after",
                    "surplus_deficit_delta", "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert labor_income_shock(0.40, 1.0)["scenario"] == "labor_income_shock"

    def test_full_income_baseline_is_stable(self):
        """income_fraction=1.0 (no shock) must match baseline solvency."""
        result = labor_income_shock(0.40, income_fraction=1.0)
        assert result["trust_solvent_before"] == result["trust_solvent_after"]

    def test_low_income_worsens_surplus_deficit(self):
        """Shocked income must produce equal or worse surplus_deficit than baseline."""
        r_full = labor_income_shock(0.40, income_fraction=1.0)
        r_half = labor_income_shock(0.40, income_fraction=0.50)
        assert r_half["surplus_deficit_after"] <= r_full["surplus_deficit_after"]

    def test_shocked_income_less_than_baseline(self):
        result = labor_income_shock(0.40, income_fraction=0.60)
        assert result["shocked_income"] <= result["baseline_income"]

    def test_outcome_is_valid(self):
        for frac in (1.0, 0.75, 0.50, 0.25):
            result = labor_income_shock(0.40, income_fraction=frac)
            assert result["outcome"] in VALID_OUTCOMES

    def test_recommendation_is_string(self):
        result = labor_income_shock(0.40, 0.70)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_invalid_fraction_raises(self):
        with pytest.raises(ValueError):
            labor_income_shock(0.40, income_fraction=1.5)

    def test_zero_fraction_raises(self):
        """income_fraction=0.0 is valid (total collapse → uses LABOR_INCOME_MIN floor)."""
        result = labor_income_shock(0.40, income_fraction=0.0)
        assert result["outcome"] in VALID_OUTCOMES

    def test_delta_is_non_positive_for_shock(self):
        """Any shock (income_fraction < 1.0) must not improve surplus_deficit vs. baseline."""
        r_base  = labor_income_shock(0.40, income_fraction=1.0)
        r_shock = labor_income_shock(0.40, income_fraction=0.50)
        assert r_shock["surplus_deficit_delta"] <= r_base["surplus_deficit_delta"] + 1e-6


# ===========================================================================
# Compound Shock
# ===========================================================================

class TestCompoundShock:

    def test_returns_expected_keys(self):
        result = compound_shock(0.40)
        for key in ("scenario", "epsilon", "individual_outcomes",
                    "combined_eoh_delta", "trust_absorbs_combined",
                    "combined_outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert compound_shock(0.40)["scenario"] == "compound_shock"

    def test_no_shocks_is_stable(self):
        """All shocks disabled → combined_outcome is STABLE."""
        result = compound_shock(0.40, ecology_collapse=False,
                                demographic_shock_spec=None,
                                automation_fraction_lost=0.0)
        assert result["combined_outcome"] == "STABLE"
        assert result["combined_eoh_delta"] == 0.0

    def test_combined_outcome_at_least_as_severe_as_worst_individual(self):
        """Combined outcome must be >= worst individual outcome in severity."""
        _severity = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
        result = compound_shock(
            0.60,
            ecology_collapse=True,
            ecosystem_health_before=0.50,
            ecosystem_health_after=0.25,
            demographic_shock_spec={"shock_type": "aging", "magnitude": 0.20},
        )
        worst_ind = max(
            (_severity[v] for v in result["individual_outcomes"].values()),
            default=0,
        )
        assert _severity[result["combined_outcome"]] >= worst_ind

    def test_ecology_collapse_adds_individual_outcome(self):
        result = compound_shock(0.40, ecology_collapse=True,
                                ecosystem_health_before=0.70,
                                ecosystem_health_after=0.30)
        assert "ecological_eoh_spike" in result["individual_outcomes"]

    def test_demographic_shock_spec_adds_individual_outcome(self):
        result = compound_shock(
            0.40,
            demographic_shock_spec={"shock_type": "growth", "magnitude": 0.20}
        )
        assert "demographic_shock" in result["individual_outcomes"]

    def test_automation_fraction_lost_adds_individual_outcome(self):
        result = compound_shock(0.40, automation_fraction_lost=0.50)
        assert "automation_failure_shock" in result["individual_outcomes"]

    def test_combined_eoh_delta_non_negative(self):
        result = compound_shock(
            0.40,
            ecology_collapse=True,
            ecosystem_health_before=0.70,
            ecosystem_health_after=0.30,
        )
        assert result["combined_eoh_delta"] >= 0.0

    def test_combined_outcome_is_valid(self):
        result = compound_shock(0.40)
        assert result["combined_outcome"] in VALID_OUTCOMES

    def test_recommendation_is_string(self):
        result = compound_shock(0.40, ecology_collapse=True,
                                ecosystem_health_before=0.70,
                                ecosystem_health_after=0.30)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_all_three_shocks_simultaneous(self):
        """Full compound — all three shocks active."""
        result = compound_shock(
            epsilon=0.50,
            ecology_collapse=True,
            ecosystem_health_before=0.55,
            ecosystem_health_after=0.25,
            demographic_shock_spec={"shock_type": "aging", "magnitude": 0.30},
            automation_fraction_lost=0.40,
        )
        assert len(result["individual_outcomes"]) == 3
        assert result["combined_outcome"] in VALID_OUTCOMES



class TestLaborIncomeAutomationSlope:
    """
    `_LABOR_INCOME_AUTO_SLOPE`, pinned (2026-08-28) — after making it
    observable at all.

    It is a shadow constant that a +7% move left undetected, and the reason was
    structural: `demographic_shock` computed `labor_income` from it and then
    DISCARDED it. ε drives the guarantee, the EOH total and the income
    together, so the income's own response cannot be recovered from any
    downstream figure — I tried, and the implied ratio came back 2.17 against an
    expected 0.60 because the other ε effects swamp it.

    The fix is the same one applied to `scenarios/maintenance.py` the same day:
    report the quantity the code already computes. A term that reaches the
    caller only through other terms is a term no test can hold.
    """

    # SINCE 2026-09-30 THIS IS THE LEGACY PATH. The default income is the mint
    # (wage doctrine); the proxy runs only when a base is passed, so these pin
    # it there. "Automation must reduce labour income" is true of the PROXY and
    # false of the mint, which rises until ε≈0.77 — see
    # TestShocksPayFromTheMint below.
    def _income(self, eps, base=_LABOR_INCOME_BASE):
        return demographic_shock(epsilon=eps, shock_type="growth",
                                 magnitude=0.1, labor_income_base=base)["labor_income"]

    def test_labor_income_falls_with_automation(self):
        vals = [self._income(e) for e in (0.0, 0.25, 0.5, 0.75, 0.99)]
        assert vals == sorted(vals, reverse=True), vals
        assert vals[-1] < vals[0], "the proxy's slope must reduce labour income"

    def test_the_decline_is_the_declared_fraction_of_base(self):
        """Binds the constant to the behaviour rather than restating 0.80."""
        base = _LABOR_INCOME_BASE
        for eps in (0.0, 0.25, 0.5):
            expected = max(_LABOR_INCOME_MIN,
                           base * (1.0 - eps * _LABOR_INCOME_AUTO_SLOPE))
            assert self._income(eps) == pytest.approx(expected, rel=1e-9)

    def test_income_never_falls_below_the_floor(self):
        for eps in (0.0, 0.5, 0.9, 0.99):
            assert self._income(eps) >= _LABOR_INCOME_MIN - 1e-6

    def test_the_floor_is_reachable_with_a_small_enough_base(self):
        """A floor that never binds is not a floor."""
        small = _LABOR_INCOME_MIN * 1.1
        assert self._income(0.99, base=small) == pytest.approx(
            _LABOR_INCOME_MIN, rel=1e-9
        )

    def test_the_slope_is_a_fraction_not_a_multiplier(self):
        """A slope ≥ 1 would zero labour income at ε=1 before the floor could
        act; a negative slope would mean automation RAISES labour income."""
        assert 0.0 < _LABOR_INCOME_AUTO_SLOPE < 1.0



class TestShocksPayFromTheMint:
    """
    2026-09-30: three shocks levied the Trust from the 2.2e9 proxy — ~81× the
    mint at ε=0, unscaled by population — and `compound_shock` applied the
    proxy's automation slope twice (mode 11). The default is now the mint.
    """

    KEY = (0.0, 0.40, 0.90, 0.99)

    @pytest.mark.parametrize("eps", KEY)
    def test_demographic_income_is_the_mint(self, eps):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        r = demographic_shock(epsilon=eps, shock_type="aging", magnitude=0.2)
        mint = eoh_to_teh_pipeline(
            eps, population=1_000_000.0,
            capital_stock=resolve_capital_stock(None, eps), capital_age_ratio=0.30,
        )["teh_created"]
        assert r["labor_income"] == pytest.approx(mint, rel=1e-12)

    def test_the_mint_rises_before_it_falls(self):
        """The proxy fell monotonically; the mint does not."""
        inc = [demographic_shock(epsilon=e, shock_type="growth", magnitude=0.1)["labor_income"]
               for e in (0.0, 0.40, 0.70, 0.99)]
        assert inc[0] < inc[1] < inc[2] and inc[3] < inc[2]

    def test_ecological_spike_income_travels_with_the_frame(self):
        """The proxy was 2.2e9 at every population. The mint scales."""
        from hours_eoh.scenarios.shocks import _mint_income
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        for pop in (1.0e5, 1.0e7):
            got = _mint_income(0.40, pop, resolve_capital_stock(None, 0.40, population=pop), 0.30)
            ref = _mint_income(0.40, 1.0e6, resolve_capital_stock(None, 0.40, population=1.0e6), 0.30)
            assert got / pop == pytest.approx(ref / 1.0e6, rel=1e-9)

    def test_the_spike_reports_the_mint_and_honours_an_explicit_income(self):
        from hours_eoh.scenarios.shocks import _mint_income
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        r = ecological_eoh_spike(0.40, 0.7, 0.3)
        # The after-state's mint (2026-10-01): restoration work registers, so it
        # sits ABOVE the pre-collapse mint, by less than the restoration hours
        # would mint at the multiplier cap `M_MAX`.
        before = _mint_income(0.40, 1.0e6, resolve_capital_stock(None, 0.40, population=1.0e6), 0.30)
        from hours_eoh.data import M_MAX
        assert before < r["labor_income"] < before + r["restoration_eoh_high"] * M_MAX
        assert ecological_eoh_spike(0.40, 0.7, 0.3, labor_income=1.0e10)["labor_income"] == 1.0e10
        low = ecological_eoh_spike(0.40, 0.7, 0.3, labor_income=1.0e6)["trust_surplus_deficit"]
        high = ecological_eoh_spike(0.40, 0.7, 0.3, labor_income=1.0e10)["trust_surplus_deficit"]
        assert high > low, "the income must reach the Trust"

    def test_compound_no_longer_applies_the_slope_twice(self, monkeypatch):
        """The demographic leg must resolve its OWN income: compound_shock used
        to hand it an already-sloped income as an ε=0 base (mode 11)."""
        import hours_eoh.scenarios.shocks as sh
        seen = {}
        real = sh.demographic_shock

        def spy(*args, **kw):
            seen.update(kw)
            return real(*args, **kw)

        monkeypatch.setattr(sh, "demographic_shock", spy)
        sh.compound_shock(0.90, demographic_shock_spec={"shock_type": "aging", "magnitude": 0.2})
        assert "labor_income_base" not in seen


class TestOneDegradedThreshold:
    """2026-09-30: DEGRADED was 5% of the Trust in `demographic_shock` and 10%
    in two others, unnamed. One constant, one reader."""

    def test_the_boundary_is_the_constant(self):
        from hours_eoh.data import SHOCK_DEGRADED_TRUST_FRACTION as F
        from hours_eoh.scenarios.shocks import _classify
        assert _classify(True, -1e9, 0.0) == "STABLE"
        assert _classify(False, -F * 1000.0, 1000.0) == "DEGRADED"
        assert _classify(False, -F * 1000.0 * 1.001, 1000.0) == "CRISIS"
        assert _classify(False, -1.0, 0.0) == "CRISIS", "no Trust, no runway"

    def test_no_shock_carries_its_own_copy(self):
        import inspect
        import hours_eoh.scenarios.shocks as sh
        src = inspect.getsource(sh)
        assert "trust_balance * 0.05" not in src and "trust_balance * 0.10" not in src

    def test_demographic_shock_reads_the_shared_boundary(self):
        """A deficit between 5% and 10% of the Trust: CRISIS under the old 5%,
        DEGRADED now. Searched, and FAILS rather than skips if the probe finds
        nothing — a skipped check is not a check."""
        import numpy as np
        from hours_eoh.data import SHOCK_DEGRADED_TRUST_FRACTION as F
        for tb in np.geomspace(1.0e5, 1.0e10, 60):
            r = demographic_shock(0.99, "growth", 0.2, trust_balance=float(tb))
            deficit = -r["surplus_deficit_after"]
            if not r["trust_solvent_after"] and 0.05 * tb < deficit <= F * tb:
                assert r["outcome"] == "DEGRADED"
                return
        raise AssertionError("no probe landed between 5% and 10% of the Trust")


class TestAgeDistributionIsFractions:
    """2026-09-30: `demographic_shock` and `epsilon_sweep` passed head COUNTS as
    `age_distribution`, which takes fractions — personal EOH population² ×
    weight, ~1e6× at 1M. Through `eoh_delta`, `compound_shock` added ~9.6e13
    phantom hours to the guarantee and reported CRISIS for any demographic
    shock at every ε. Nothing pinned it; these do."""

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_the_shock_obligation_is_total_eoh(self, eps):
        from hours_eoh.core.eoh_generation import resolve_capital_stock, total_eoh
        r = demographic_shock(eps, "growth", 0.2)
        ref = total_eoh(eps, population=1.0e6,
                        capital_stock=resolve_capital_stock(None, eps),
                        capital_age_ratio=0.30)["total"]
        assert r["eoh_before"] == pytest.approx(ref, rel=1e-12)

    def test_growth_scales_the_personal_obligation_by_the_growth(self):
        r = demographic_shock(0.0, "growth", 0.2)
        assert r["eoh_after"] / r["eoh_before"] == pytest.approx(1.2, rel=1e-9)

    def test_compound_matches_its_only_component(self):
        from hours_eoh.scenarios.shocks import compound_shock
        for eps in (0.0, 0.40, 0.90):
            spec = {"shock_type": "aging", "magnitude": 0.2}
            alone = demographic_shock(eps, **spec)["outcome"]
            assert compound_shock(eps, demographic_shock_spec=spec)["combined_outcome"] == alone

    def test_personal_eoh_refuses_head_counts(self):
        from hours_eoh.core.eoh_generation import personal_eoh
        with pytest.raises(ValueError, match="FRACTIONS"):
            personal_eoh(1.0e6, {"working_age": 6.0e5, "elderly": 4.0e5})


class TestShocksRunOnTheSharedPath:
    """2026-09-30, record/verification.md#parallel-paths (a): the shocks
    assembled their own EOH and fiscal layer. Each pin here fails if the
    defect the hand path carried returns."""

    POPS = (1.0e5, 1.0e6, 1.0e7)

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_automation_verdict_is_frame_invariant(self, eps):
        # A fixed 600,000-person workforce beside a settable population: the
        # same economy read coverage 4.118 / 0.412 / 0.041 at ε=0.40.
        rows = [automation_failure_shock(eps, population=p) for p in self.POPS]
        ratios = [r["coverage_ratio"] for r in rows]
        assert ratios == pytest.approx([ratios[1]] * 3, rel=1e-9), ratios
        assert len({r["outcome"] for r in rows}) == 1
        assert len({r["failure_boundary"] for r in rows}) == 1

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_automation_obligation_is_the_pipelines(self, eps):
        # A fixed knowledge base of 10.0 put knowledge EOH 10× the pipeline's
        # at ε=0; every other path resolves the corpus along the arc.
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.eoh_generation import (
            resolve_capital_stock, resolve_knowledge_base_size)
        r = automation_failure_shock(eps)
        ref = eoh_to_teh_pipeline(
            eps, capital_stock=resolve_capital_stock(None, eps, population=1.0e6),
            capital_age_ratio=0.30, ecosystem_health=0.70,
            knowledge_complexity=resolve_knowledge_base_size(None, eps))
        assert r["total_eoh"] == pytest.approx(ref["total_eoh"], rel=1e-12)

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_labor_income_baseline_is_the_unfloored_mint(self, eps):
        from hours_eoh.scenarios.shocks import _mint_income
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        for pop in self.POPS:
            cap = resolve_capital_stock(None, eps, population=pop)
            r = labor_income_shock(eps, 0.5, population=pop)
            assert r["baseline_income"] == pytest.approx(
                _mint_income(eps, pop, cap, 0.30), rel=1e-12)

    def test_total_income_collapse_reaches_zero(self):
        # The docstring's "0.0 = total income collapse" was floored at 3e8.
        assert labor_income_shock(0.40, 0.0)["shocked_income"] == 0.0

    @pytest.mark.parametrize("eps", [0.40, 0.90, 0.99])
    def test_the_guarantee_reads_the_held_register(self, eps):
        # Replaced 2026-10-01: the exactness of a Trust charge that no longer
        # exists. What matters now is that the guarantee's on-ledger share is
        # the REGISTER's, held apart from the capability (author, 2026-10-01).
        from hours_eoh.core.fiscal import fiscal_snapshot
        kw = dict(labor_income=3.0e8, capital_stock_teh=1.0e9,
                  capital_age_ratio=0.30, population=1.0e6)
        held = fiscal_snapshot(epsilon=0.0, registration_epsilon=eps, **kw)
        ref = fiscal_snapshot(epsilon=eps, **kw)
        lost = fiscal_snapshot(epsilon=0.0, **kw)
        assert held["guarantee"]["floor_fraction"] == ref["guarantee"]["floor_fraction"]
        assert held["guarantee"]["floor_fraction"] != lost["guarantee"]["floor_fraction"]
        assert fiscal_snapshot(epsilon=eps, registration_epsilon=None, **kw)[
            "trust"]["surplus_deficit"] == ref["trust"]["surplus_deficit"]

    @pytest.mark.parametrize("shock", ["growth", "decline", "aging"])
    def test_demographic_shock_travels_with_the_frame(self, shock):
        rows = [demographic_shock(0.40, shock, 0.2, population=p) for p in self.POPS]
        per_capita = [r["eoh_delta"] / r["population_before"] for r in rows]
        assert per_capita == pytest.approx([per_capita[1]] * 3, rel=1e-9)
        assert len({r["outcome"] for r in rows}) == 1

    def test_compound_runs_its_demographic_leg_at_its_own_population(self):
        # The leg was frameless at 1M while handed a Trust resolved at the
        # compound's population: at 100k an aging compound read DEGRADED while
        # its only component read STABLE.
        spec = {"shock_type": "aging", "magnitude": 0.1}
        for eps in (0.0, 0.40, 0.90, 0.99):
            alone = demographic_shock(eps, **spec, population=1.0e5)["outcome"]
            both = compound_shock(eps, demographic_shock_spec=spec, population=1.0e5)
            assert both["combined_outcome"] == alone

    def test_aging_moves_people_and_creates_none(self):
        # magnitude beyond the working-age share used to ADD elderly without
        # removing workers, growing the population. Refused, not clamped: a
        # clamp would satisfy the population check by construction (mode 2).
        r = demographic_shock(0.40, "aging", 0.5)
        assert r["population_after"] == r["population_before"]
        assert r["eoh_after"] != r["eoh_before"]
        with pytest.raises(ValueError, match="OUT of working age"):
            demographic_shock(0.40, "aging", 0.9)


class TestAutomationFailureCascade:
    """2026-09-30: an automation failure is the shared pipeline's own cascade —
    the OBSERVED machine load falls to people, is taken up within the measured
    labour supply L, and the rest is DEFERRED survival-first. Nothing is
    charged to the Trust: a balance cannot supply an hour of labour."""

    ARC = (0.0, 0.40, 0.90, 0.99)

    @pytest.mark.parametrize("eps", ARC)
    def test_every_lost_hour_is_taken_up_or_deferred(self, eps):
        r = automation_failure_shock(eps)
        assert r["taken_up_eoh"] + r["deferred_eoh"] == pytest.approx(
            r["machine_eoh_lost"], rel=1e-9, abs=1e-3)
        assert r["taken_up_eoh"] >= -1e-3 and r["deferred_eoh"] >= -1e-3

    def test_nothing_is_lost_where_machines_carried_nothing(self):
        r = automation_failure_shock(0.0)
        assert r["machine_eoh_lost"] == 0.0
        assert r["mint_after"] == r["mint_before"]
        assert r["outcome"] == "STABLE"

    @pytest.mark.parametrize("eps", [0.40, 0.90, 0.99])
    def test_the_register_stands_so_the_surge_mints(self, eps):
        # With the register read off the failed capability, the surge was
        # pushed off-ledger: at ε=0.40 the mint FELL 3.311e8 → 5.21e7 while
        # people worked 4.9e8 more hours.
        r = automation_failure_shock(eps)
        assert r["taken_up_eoh"] > 0.0
        assert r["mint_after"] > r["mint_before"]

    def test_the_register_parameter_moves_the_pipeline(self):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        held = eoh_to_teh_pipeline(machine_capability=0.0, registration_epsilon=0.90)
        same = eoh_to_teh_pipeline(machine_capability=0.0)
        ref = eoh_to_teh_pipeline(0.90)
        for d in ("personal", "infrastructure", "ecological", "knowledge"):
            # `non_personal` is an hours-weighted aggregate, not a share.
            assert held["registration_by_domain"][d] == ref["registration_by_domain"][d]
        assert held["teh_created"] > same["teh_created"]
        assert eoh_to_teh_pipeline(0.40, registration_epsilon=None)["teh_created"] == \
            eoh_to_teh_pipeline(0.40)["teh_created"]

    def test_all_three_verdicts_are_reachable(self):
        # Mode 9: CRISIS (the survival floor deferred) never fires at the
        # measured supply, so it is constructed: below the personal demand
        # per head the floor itself goes unserved.
        assert automation_failure_shock(0.40)["outcome"] == "STABLE"
        # DEGRADED: labour defers, and the care shortfall already there at ε=0.78
        # is not blamed on the shock (care is a domain since 2026-10-01).
        assert automation_failure_shock(0.78)["outcome"] == "DEGRADED"
        crisis = automation_failure_shock(0.90, labor_supply_per_capita=800.0)
        assert crisis["deferred_personal_eoh"] > 0.0
        assert crisis["outcome"] == "CRISIS"

    def test_no_labour_no_collective(self):
        r = automation_failure_shock(0.40, labor_supply_per_capita=0.0)
        assert r["outcome"] == "CRISIS"
        assert r["mint_after"] == 0.0

    def test_a_larger_failure_never_covers_more(self):
        cov = [automation_failure_shock(0.90, fraction_lost=f)["coverage_ratio"]
               for f in (0.25, 0.50, 0.75, 1.0)]
        assert all(a >= b - 1e-12 for a, b in zip(cov, cov[1:]))
        assert cov[0] == 1.0 and cov[-1] < 1.0

    def test_the_retired_literals_warn_and_change_nothing(self):
        base = automation_failure_shock(0.90)
        with pytest.warns(DeprecationWarning, match="deprecated"):
            old = automation_failure_shock(0.90, workforce_size=600_000.0,
                                           mean_entropy_reduction_capacity=1200.0,
                                           reserve_fraction=0.155)
        assert old["coverage_ratio"] == base["coverage_ratio"]

    def test_compound_of_one_is_that_shock(self):
        # One component in the one-state compound reproduces the shock alone.
        r = compound_shock(0.90, automation_fraction_lost=1.0)
        alone = automation_failure_shock(0.90)
        assert r["combined_eoh_delta"] == pytest.approx(alone["machine_eoh_lost"], rel=1e-9)
        assert r["combined_deferred_eoh"] == pytest.approx(alone["deferred_eoh"], rel=1e-9)
        assert r["automation_deferred_eoh"] == pytest.approx(alone["deferred_eoh"], rel=1e-12)
        assert r["combined_outcome"] == alone["outcome"]


class TestOneStateOneCascade:
    """2026-10-01, author: "lets proceed with your recommendations". Every
    shock is a change to one state run through one cascade; nothing is charged
    to the Trust; supply moves with the age mix; a collapse leaves restoration."""

    ARC = (0.0, 0.40, 0.90, 0.99)

    @pytest.mark.parametrize("eps", ARC)
    def test_a_collapse_leaves_its_restoration_in_the_domain(self, eps):
        # The domain was empty under the partition: the spike read 0 at every
        # population and the verdict came from the threshold flag alone.
        r = ecological_eoh_spike(eps, 0.70, 0.30)
        assert 0.0 < r["restoration_eoh_low"] < r["restoration_eoh_high"]
        assert r["eoh_spike"] == pytest.approx(r["restoration_eoh_high"], rel=1e-9)
        assert r["guf_flow_added_eoh"] > 0.0

    def test_the_restoration_travels_with_the_frame(self):
        rows = [ecological_eoh_spike(0.40, 0.70, 0.30, population=p) for p in (1e5, 1e6, 1e7)]
        per = [r["restoration_eoh_high"] / p for r, p in zip(rows, (1e5, 1e6, 1e7))]
        assert per == pytest.approx([per[1]] * 3, rel=1e-9)

    def test_no_collapse_no_restoration(self):
        r = ecological_eoh_spike(0.40, 0.50, 0.60)
        assert r["restoration_eoh_high"] == 0.0 and r["eoh_spike"] == 0.0

    def test_the_threshold_no_longer_decides_alone(self):
        r = ecological_eoh_spike(0.40, 0.70, 0.30)
        assert r["threshold_crossed"] and r["outcome"] == "STABLE"

    def test_supply_follows_the_age_mix(self):
        from hours_eoh.scenarios.feasibility import capacity_weighted_adult_share
        from hours_eoh.data import AGE_GROUPS
        base = {g: AGE_GROUPS[g]["fraction"] for g in AGE_GROUPS}
        aged = dict(base, working_age=base["working_age"] - 0.2,
                    elderly=base["elderly"] + 0.2)
        r = demographic_shock(0.40, "aging", 0.2)
        assert r["labor_supply_after"] / r["labor_supply_before"] == pytest.approx(
            capacity_weighted_adult_share(aged) / capacity_weighted_adult_share(), rel=1e-12)
        g = demographic_shock(0.40, "growth", 0.2)
        assert g["labor_supply_after"] / g["population_after"] == pytest.approx(
            g["labor_supply_before"] / g["population_before"], rel=1e-12)

    def test_the_adult_share_reads_a_supplied_mix(self):
        from hours_eoh.scenarios.feasibility import capacity_weighted_adult_share
        from hours_eoh.data import AGE_GROUPS
        base = {g: AGE_GROUPS[g]["fraction"] for g in AGE_GROUPS}
        assert capacity_weighted_adult_share(base) == capacity_weighted_adult_share()
        with pytest.raises(ValueError, match="unknown"):
            capacity_weighted_adult_share({"teen": 1.0})

    def test_aging_at_subsistence_breaks_the_survival_floor(self):
        # The finding, both ways: a 10-point shift from working age to elderly
        # defers personal obligation at ε=0 and is absorbed at ε=0.40.
        low = demographic_shock(0.0, "aging", 0.1)
        assert low["deferred_personal_eoh"] > 0.0 and low["outcome"] == "CRISIS"
        assert demographic_shock(0.40, "aging", 0.1)["outcome"] == "STABLE"

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90])
    def test_shocks_share_one_labour_pool(self, eps):
        spec = {"shock_type": "aging", "magnitude": 0.1}
        both = compound_shock(eps, demographic_shock_spec=spec, automation_fraction_lost=1.0)
        auto = automation_failure_shock(eps)
        dem = demographic_shock(eps, **spec)
        assert both["combined_deferred_eoh"] >= max(auto["deferred_eoh"], dem["deferred_eoh"]) - 1e-3
        sev = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
        assert sev[both["combined_outcome"]] >= max(sev[auto["outcome"]], sev[dem["outcome"]])

    def test_base_rate_is_retired(self):
        with pytest.warns(DeprecationWarning, match="base_rate"):
            ecological_eoh_spike(0.40, 0.70, 0.30, base_rate=1.0)


class TestCompetencyInTheShocks:
    """2026-10-01: Condition IV in hours (`condition_iv_coverage`) is read in
    every shock, for a collective certified at the Condition IV minimum of its
    OWN working-age headcount; a shock is charged only with shortfalls it
    CREATES. Until this date competency was declared untested."""

    def test_every_shock_tests_competency(self):
        for r in (automation_failure_shock(0.40), demographic_shock(0.40, "aging", 0.1),
                  ecological_eoh_spike(0.40, 0.7, 0.3),
                  compound_shock(0.40, automation_fraction_lost=0.5)):
            assert r["competency_tested"] is True
            from hours_eoh.data import ESSENTIAL_DOMAINS
            assert set(r["competency_coverage_after"]) == set(ESSENTIAL_DOMAINS)

    def test_a_shortfall_already_there_is_not_blamed_on_the_shock(self):
        # Inside the band where healthcare is short at the Condition IV minimum
        # before any shock, in both tiers. (Until the bridge's personal column
        # was derived, 2026-10-01, this case also "created" a logistics
        # shortfall — the old 0.20 logistics weight, gone with it.)
        r = automation_failure_shock(0.78)
        assert r["competency_short_before"] == ["care"]
        assert r["competency_personal_short_before"] == ["care"]
        assert r["competency_short_created"] == []
        assert r["competency_personal_short_created"] == []

    def test_aging_late_in_the_arc_shrinks_the_certified_pool(self):
        # Labour absorbs it; competency does not. TWO mechanisms, both
        # measured: aging raises healthcare demand and shrinks the certified
        # pool (a share of the smaller working-age headcount). Under the
        # DERIVED bridge (2026-10-01) demand alone leaves healthcare covered —
        # the shortfall is the pool's; under the old 0.80 weight demand alone
        # had already broken it. Capacity is linear in headcount, so the
        # coverage is the held-headcount coverage × the working-age ratio.
        from hours_eoh.scenarios import shocks as sh
        from hours_eoh.core.conditions import condition_iv_coverage
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        r = demographic_shock(0.99, "aging", 0.2)
        assert r["labour_outcome"] == "STABLE"
        assert r["competency_short_created"] == ["care"]
        # The shortfall is in the PERSONAL tier — the agents' own needs without
        # competent hands — so CRISIS, not DEGRADED (author, 2026-10-01).
        assert r["competency_personal_short_created"] == ["care"]
        assert r["outcome"] == "CRISIS"
        s0 = sh._base_state(0.99, 1.0e6, 0.70, None)
        s1 = sh._demographic_change(s0, "aging", 0.2)
        after = sh._run(s1, 0.99, resolve_capital_stock(None, 0.99, population=1.0e6), 0.30, None)
        held = condition_iv_coverage(sh._threshold_reserve(s0), after)["per_domain"]["care"]
        assert held["coverage_ratio"] >= 1.0
        ratio = s1["age_fractions"]["working_age"] / s0["age_fractions"]["working_age"]
        assert r["competency_coverage_after"]["care"] == pytest.approx(
            held["coverage_ratio"] * ratio, rel=1e-12)

    def test_mid_arc_failure_creates_no_shortfall(self):
        assert automation_failure_shock(0.40)["competency_short_created"] == []

    def test_competency_travels_with_the_frame(self):
        rows = [automation_failure_shock(0.90, population=p) for p in (1e5, 1e6, 1e7)]
        ratios = [r["competency_coverage_after"]["care"] for r in rows]
        assert ratios == pytest.approx([ratios[1]] * 3, rel=1e-9)
        assert len({tuple(r["competency_short_created"]) for r in rows}) == 1


class TestTheSurvivalTier:
    """2026-10-01, author: "the people (agent needs) should be what needs to be
    covered, the rest can build back over time as the arc climbs again". A
    shortfall the shock creates in the PERSONAL tier is CRISIS; elsewhere,
    DEGRADED."""

    def test_a_personal_tier_shortfall_is_crisis(self):
        r = automation_failure_shock(0.99)
        assert r["labour_outcome"] == "DEGRADED"
        assert r["competency_personal_short_created"] == ["care"]
        assert r["outcome"] == "CRISIS"

    def test_care_at_the_minimum_has_no_slack_for_lost_automation(self):
        # Machines carry part of care late in the arc. A care pool certified at
        # exactly the Condition IV minimum cannot take even a quarter of it
        # back: labour absorbs the loss (STABLE), competency does not (CRISIS).
        r = automation_failure_shock(0.90, fraction_lost=0.25)
        assert r["labour_outcome"] == "STABLE"
        assert r["competency_personal_short_created"] == ["care"]
        assert r["outcome"] == "CRISIS"

    def test_unattributed_hours_are_reported_not_counted_short(self):
        r = automation_failure_shock(0.40)
        assert r["competency_unattributed_eoh"] > 0.0
        assert "unattributed" not in r["competency_coverage_after"]
