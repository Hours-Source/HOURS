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
        for key in ("scenario", "epsilon", "total_eoh", "automation_eoh",
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

    def test_automation_eoh_equals_epsilon_times_total(self):
        result = automation_failure_shock(epsilon=0.40)
        assert result["automation_eoh"] == pytest.approx(
            result["total_eoh"] * 0.40, rel=1e-4
        )

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
        assert r["labor_income"] == pytest.approx(
            _mint_income(0.40, 1.0e6, resolve_capital_stock(None, 0.40, population=1.0e6), 0.30),
            rel=1e-12)
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

        def spy(**kw):
            seen.update(kw)
            return real(**kw)

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
