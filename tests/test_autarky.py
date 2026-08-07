"""
Tests for core/autarky.py and the abatement mechanism (Block II, 2026-08-06).

Three things are pinned here:

  1. ABATEMENT is real — infrastructure reduces the obligation, not only who
     serves it. Before Block II personal EOH was flat across the whole arc.
  2. The ANTI-CORRELATION prediction is TESTED, not assumed: abatability and
     sufficiency run opposite, so the residual at full abatement is dominated by
     care (the Baumol case).
  3. AGGREGATE OVERBUILD is now representable. Abatement saturates while overhead
     grows linearly, so there is an interior optimum and a size beyond which more
     apparatus is pure overhead. The pre-Block-II model could not express this.

Arc coverage at ε ∈ {0.0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.core.autarky import (
    autarky_reference,
    break_even_epsilon,
    overbuild_check,
    payback,
)
from hours_eoh.core.eoh_generation import (
    abated_personal_base,
    abatement_fraction,
    max_abatement,
    personal_base_for,
)
from hours_eoh.data import PERSONAL_EOH_COMPONENTS

ARC = [0.0, 0.40, 0.90, 0.99]
POP = 1_000_000.0


# ---------------------------------------------------------------------------
# the abatement mechanism
# ---------------------------------------------------------------------------

class TestAbatement:

    def test_component_shares_are_a_partition(self):
        assert sum(c["share"] for c in PERSONAL_EOH_COMPONENTS.values()) == pytest.approx(1.0)

    def test_a_max_is_derived_from_the_components(self):
        expected = sum(c["share"] * c["abatability"]
                       for c in PERSONAL_EOH_COMPONENTS.values())
        assert max_abatement() == pytest.approx(expected)
        assert max_abatement() == pytest.approx(0.4483, abs=0.001)

    def test_zero_capital_means_zero_abatement(self):
        """Autarky by definition: no apparatus, nothing abated."""
        assert abatement_fraction(0.0) == 0.0
        assert abated_personal_base(0.0) == pytest.approx(personal_base_for("sufficiency"))

    def test_half_capital_gives_half_of_a_max(self):
        from hours_eoh.data import ABATEMENT_HALF_CAPITAL_TEH
        assert abatement_fraction(ABATEMENT_HALF_CAPITAL_TEH) == pytest.approx(
            max_abatement() / 2.0)

    def test_abatement_saturates_and_never_reaches_one(self):
        assert abatement_fraction(1e12) < max_abatement()
        assert abatement_fraction(1e12) == pytest.approx(max_abatement(), rel=1e-6)
        assert max_abatement() < 1.0

    def test_abatement_is_monotone_in_capital(self):
        vals = [abatement_fraction(k) for k in (0, 100, 1000, 10_000, 1e6)]
        assert vals == sorted(vals)

    def test_abatement_is_epsilon_free(self):
        """a(K) is capital-driven so it composes with ε instead of double-counting."""
        import inspect
        assert "epsilon" not in inspect.signature(abatement_fraction).parameters

    def test_abating_the_collapsed_value_is_refused(self):
        with pytest.raises(ValueError, match="double-count"):
            abated_personal_base(1000.0, standard="collapsed")

    def test_rejects_bad_inputs(self):
        with pytest.raises(ValueError):
            abatement_fraction(-1.0)
        with pytest.raises(ValueError):
            abatement_fraction(100.0, half_capital=0.0)
        with pytest.raises(ValueError):
            abatement_fraction(100.0, a_max=1.5)


class TestAntiCorrelationPrediction:
    """The block's structural claim, TESTED rather than baked in.

    Abatability and sufficiency run opposite: infrastructure removes the
    survival-shaped work (hauling, gathering, preparing) and cannot remove care,
    because a child needs human attention. If these assertions fail, the
    prediction has been falsified by whatever changed the weights — which is the
    point of asserting it here instead of stating it in a docstring.
    """

    def test_care_is_the_least_abatable_component(self):
        worst = min(PERSONAL_EOH_COMPONENTS.items(),
                    key=lambda kv: kv[1]["abatability"])
        assert worst[0] == "care"

    def test_care_is_also_the_largest_component(self):
        biggest = max(PERSONAL_EOH_COMPONENTS.items(),
                      key=lambda kv: kv[1]["share"])
        assert biggest[0] == "care"

    def test_residual_at_full_abatement_is_dominated_by_care(self):
        residual = {k: v["share"] * (1.0 - v["abatability"])
                    for k, v in PERSONAL_EOH_COMPONENTS.items()}
        total = sum(residual.values())
        assert residual["care"] / total > 0.80

    def test_anti_correlation_holds_across_the_components(self):
        """Rank correlation between share and abatability must be negative."""
        items = sorted(PERSONAL_EOH_COMPONENTS.values(), key=lambda c: c["share"])
        abat = [c["abatability"] for c in items]
        # largest share has the lowest abatability
        assert abat[-1] == min(abat)

    def test_a_max_is_bounded_well_below_one_by_care(self):
        assert max_abatement() < 0.5
        care = PERSONAL_EOH_COMPONENTS["care"]
        assert care["share"] * (1.0 - care["abatability"]) > 0.4


# ---------------------------------------------------------------------------
# the autarky reference
# ---------------------------------------------------------------------------

class TestAutarkyReference:

    def test_reference_has_no_apparatus_terms(self):
        r = autarky_reference(POP)
        assert r["total"] == pytest.approx(r["personal"] + r["ecological"])

    def test_sufficiency_reference_exceeds_survival(self):
        assert (autarky_reference(POP, "sufficiency")["total"]
                > autarky_reference(POP, "survival")["total"])

    def test_collapsed_is_refused_as_a_reference(self):
        with pytest.raises(ValueError, match="abated value"):
            autarky_reference(POP, standard="collapsed")

    def test_rejects_bad_population(self):
        with pytest.raises(ValueError):
            autarky_reference(0.0)


# ---------------------------------------------------------------------------
# the overbuild test
# ---------------------------------------------------------------------------

class TestOverbuild:

    def test_no_apparatus_is_neutral_not_overbuilt(self):
        """The boundary case: zero apparatus is EQUIVALENT to autarky."""
        c = overbuild_check(0.0, POP, epsilon=0.0)
        assert c["verdict"] == "neutral"
        assert c["net_vs_autarky"] == pytest.approx(0.0)
        assert c["overhead"] == pytest.approx(0.0)

    def test_a_modest_apparatus_pays(self):
        c = overbuild_check(1.9e9, POP, epsilon=0.40)
        assert c["verdict"] == "pays"
        assert c["obligation_test"] is True
        assert c["net_vs_autarky"] > 0.0
        assert "all needs met effectively" in c["note"]

    def test_abatement_lowers_the_obligation(self):
        """The mechanism, visible: B(K) < B₀."""
        c = overbuild_check(1.9e9, POP, epsilon=0.40)
        assert c["obligation_with_apparatus"] < c["autarky_reference"]
        assert c["abatement"] > 0.0

    def test_an_enormous_apparatus_is_overbuilt(self):
        """Abatement saturates; overhead does not. This is the new capability."""
        c = overbuild_check(1.0e11, POP, epsilon=0.40)
        assert c["verdict"] == "overbuilt"
        assert c["obligation_test"] is False
        assert c["net_vs_autarky"] < 0.0
        assert "exceeds not having" in c["note"]

    def test_there_is_an_interior_optimum(self):
        """Pre-Block-II both terms were linear in K, so capital always paid and
        no optimum existed. Saturating abatement creates one."""
        nets = [overbuild_check(k * POP, POP, epsilon=0.40)["net_vs_autarky"]
                for k in (500, 4_145, 50_000)]
        assert nets[1] > nets[0]
        assert nets[1] > nets[2]

    def test_obligation_test_is_epsilon_free(self):
        """It compares obligations, so ε must not move it."""
        verdicts = {overbuild_check(1.9e9, POP, epsilon=e)["obligation_test"]
                    for e in ARC}
        assert verdicts == {True}

    def test_labour_test_relaxes_with_epsilon(self):
        saved = [overbuild_check(1.9e9, POP, epsilon=e)["labour_saved"] for e in ARC]
        assert saved == sorted(saved)

    def test_labour_and_obligation_tests_can_disagree(self):
        """A collective can be worth being in while its apparatus does not pay —
        automation masking overhead. Both are reported for exactly this case."""
        c = overbuild_check(1.0e11, POP, epsilon=0.95)
        assert c["obligation_test"] is False
        assert c["labour_test"] is True
        assert "still passes on automation" in c["note"]

    @pytest.mark.parametrize("eps", ARC)
    def test_arc_coherent(self, eps):
        c = overbuild_check(1.9e9, POP, epsilon=eps)
        for k in ("autarky_reference", "obligation_with_apparatus", "overhead",
                  "total", "labour_collective"):
            assert math.isfinite(c[k]) and c[k] >= 0.0

    def test_rejects_bad_inputs(self):
        with pytest.raises(ValueError):
            overbuild_check(-1.0, POP)
        with pytest.raises(ValueError):
            overbuild_check(1e9, 0.0)
        with pytest.raises(ValueError):
            overbuild_check(1e9, POP, epsilon=1.0)


class TestBreakEvenEpsilon:

    def test_zero_when_there_is_no_apparatus(self):
        assert break_even_epsilon(0.0, POP) == 0.0

    def test_rises_with_overhead(self):
        vals = [break_even_epsilon(k * POP, POP) for k in (500, 50_000, 100_000)]
        assert vals == sorted(vals)

    def test_zero_while_the_obligation_test_passes(self):
        """An apparatus that removes more than it costs is worth being in at
        every ε — there is nothing for automation to rescue."""
        k = 1.9e9
        assert overbuild_check(k, POP, epsilon=0.0)["obligation_test"] is True
        assert break_even_epsilon(k, POP) == 0.0

    def test_matches_the_labour_test_crossing(self):
        """Regression: the crossing must be derived against B₀, not B(K).

        Abatement makes those diverge, and deriving against B(K) reported a
        break-even that was too high — the labour test passed well below it.
        """
        k = 5.0e10
        e = break_even_epsilon(k, POP)
        assert e > 0.0
        assert overbuild_check(k, POP, epsilon=min(e + 0.02, 0.99))["labour_test"] is True
        if e > 0.02:
            assert overbuild_check(k, POP, epsilon=e - 0.02)["labour_test"] is False

    def test_stays_in_range(self):
        for k in (0.0, 1e9, 1e13):
            assert 0.0 <= break_even_epsilon(k, POP) < 1.0


# ---------------------------------------------------------------------------
# payback — "temporary overbuild" made decidable
# ---------------------------------------------------------------------------

class TestPayback:

    def test_a_paying_apparatus_repays_within_its_life(self):
        p = payback(1.9e9, POP, epsilon=0.40, design_life_years=40.0)
        assert p["pays_back_within_life"] is True
        assert p["payback_years"] < 40.0
        assert p["lifetime_return"] > 0.0

    def test_never_pays_back_when_labour_saving_is_negative(self):
        p = payback(1.0e13, POP, epsilon=0.0, design_life_years=40.0)
        assert p["annual_labour_saved"] <= 0.0
        assert p["payback_years"] == float("inf")
        assert p["pays_back_within_life"] is False
        assert "NEVER PAYS BACK" in p["verdict"]

    def test_payback_shortens_as_epsilon_rises(self):
        years = [payback(1.9e9, POP, epsilon=e)["payback_years"] for e in ARC]
        assert years == sorted(years, reverse=True)

    def test_short_life_can_fail_what_a_long_life_passes(self):
        """The temporal test doing its job: the same apparatus, two horizons."""
        k = 4.0e10
        short = payback(k, POP, epsilon=0.40, design_life_years=1.0)
        long = payback(k, POP, epsilon=0.40, design_life_years=200.0)
        assert short["pays_back_within_life"] is False
        assert long["pays_back_within_life"] is True
        assert "only a defence when the horizon actually closes" in short["verdict"]

    def test_rejects_bad_life(self):
        with pytest.raises(ValueError):
            payback(1e9, POP, design_life_years=0.0)
