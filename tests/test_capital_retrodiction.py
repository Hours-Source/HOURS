"""
Reading ε off a real economy — `reference/capital_inventory` + `scenarios/capital_retrodiction`.

WHAT IS AT STAKE. §7 of the anchor comparison carries a live falsifier — *if a
retrodiction produces an implausible ε, the endogenous-supply property is not
reading the world it says it reads* — and it HAD FIRED. The only run against a
real economy gave ε = 0.777–1.000, saturated, for a US where 158M people work,
and `record/thermal.md` concluded the machine profiles were miscalibrated by ~3×.

These tests pin the retraction and, more importantly, the reason for it: the
saturated reading is one corner of a grid spanned by three judgements nobody had
declared. What must not move without someone noticing is that all three stay
DECLARED, that the conversion rate stays an intake field with no default, and
that the saturation check can still fire.

THE LAST OF THOSE IS THE ONE THAT MATTERS. "No cell saturates" is worthless if
saturation is unreachable. `test_the_saturation_check_can_fire` forces it.
"""

from __future__ import annotations

import pytest

from hours_eoh.reference import capital_inventory as CI
from hours_eoh.scenarios import capital_retrodiction as CR


class TestTheInventoryMatchesWhatBeaPublished:
    """Mode 8: a source is a lead until you check it measures the quantity."""

    def test_the_productive_scope_reproduces_private_nonresidential(self):
        """BEA Table 1.1 2024: equipment 9,281.9 + structures 21,194.2 + IPP 5,423.8."""
        assert CI.scope_total("productive") == pytest.approx(35_899.9, rel=0.03)

    def test_the_government_scope_adds_government_nondefence(self):
        """Table 7.1 total 21,272.0 less defence 2,330.2 less residential 599.4."""
        added = CI.scope_total("government") - CI.scope_total("productive")
        assert added == pytest.approx(21_272.0 - 2_330.2 - 599.4, rel=0.05)

    def test_the_residential_scope_adds_housing(self):
        added = CI.scope_total("residential") - CI.scope_total("government")
        assert added == pytest.approx(34_376.6 + 599.4, rel=0.01)

    def test_the_scopes_are_strictly_nested(self):
        p, g, r = (CI.scope_total(s) for s in ("productive", "government", "residential"))
        assert p < g < r
        assert r / p == pytest.approx(2.5, abs=0.3), (
            "the scope judgement is worth ~2.5x; if that changes the "
            "decomposition of the old 3x claim changes with it"
        )

    def test_water_treatment_exists_only_in_the_government_scope(self):
        """
        A shipped machine profile with NO private counterpart. A productive-only
        run silently zeroes it, which is why the scope is a judgement and not a
        detail.
        """
        assert "water_treatment" not in CI.capital_by_profile("productive")
        assert CI.capital_by_profile("government")["water_treatment"] > 0.0


class TestTheJudgementsStayDeclared:

    @pytest.mark.parametrize("row", CI.PROFILE_MAP, ids=lambda r: r["line"][:28])
    def test_every_mapped_line_carries_its_basis(self, row):
        assert len(row["basis"]) > 30, f"{row['line']} was assigned without an argument"
        assert row["scope"] in CI.SCOPES

    @pytest.mark.parametrize("row", CI.EXCLUDED_LINES, ids=lambda r: r["line"][:28])
    def test_every_exclusion_carries_its_reason(self, row):
        assert len(row["reason"]) > 60

    def test_defence_is_excluded_by_name(self):
        """Military capital discharges no obligation in any of the four domains.
        A judgement, so it is named rather than filtered."""
        assert any(e["line"] == "National defense" for e in CI.EXCLUDED_LINES)

    def test_nothing_excluded_is_also_mapped(self):
        mapped = {r["line"] for r in CI.PROFILE_MAP}
        assert not (mapped & {e["line"] for e in CI.EXCLUDED_LINES})

    def test_every_profile_used_is_a_real_machine_profile(self):
        from hours_eoh.data import CAPITAL_MACHINE_PROFILES
        used = {r["profile"] for r in CI.PROFILE_MAP}
        assert used <= set(CAPITAL_MACHINE_PROFILES), (
            f"unknown profiles: {sorted(used - set(CAPITAL_MACHINE_PROFILES))}"
        )

    def test_the_ages_are_measured_not_assumed(self):
        """Replaces the `age: 10.0` placeholder every earlier run of this used."""
        assert CI.MEASURED_AGES["private_structures"] == pytest.approx(28.6)
        assert CI.MEASURED_AGES["government_equipment"] == pytest.approx(8.7)
        assert CR.epsilon_from_inventory(20.0)["age_years"] != 10.0


class TestTheConversionRateIsIntakeAndNotADefault:
    """
    THE DESIGN POINT. Converting a currency-denominated stock into TEH IS the
    valuation step §2 argues against. Requiring the rate at the API boundary is
    that argument enforced; shipping one would bury the doctrine.
    """

    def test_it_cannot_be_called_without_a_rate(self):
        with pytest.raises(TypeError):
            CR.epsilon_from_inventory()          # type: ignore[call-arg]

    @pytest.mark.parametrize("bad", (0.0, -1.0))
    def test_a_nonpositive_rate_is_refused_with_the_reason(self, bad):
        with pytest.raises(ValueError, match="no default"):
            CR.epsilon_from_inventory(bad)

    def test_the_band_declares_it_is_not_a_default(self):
        band = CR.conversion_band()
        assert band["is_a_default"] is False
        assert band["spread"] == pytest.approx(band["high"] / band["low"])
        assert band["spread"] > 1.3, "four conventions that agreed would not be a band"

    def test_the_band_is_four_conventions_not_an_error_bar(self):
        band = CR.conversion_band()
        assert len(band["by_convention"]) == 4
        assert band["compensation_multiple_source"].count("NOT IN THIS REPO") == 1, (
            "the compensation multiple is external, and saying so is the reason "
            "the rate is bounded here rather than derived"
        )

    def test_no_function_falls_back_to_the_band(self):
        """A default hidden behind a helper is still a default."""
        import ast, inspect, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(CR.epsilon_from_inventory)))
        fn = tree.body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)):
            fn.body = fn.body[1:]                      # drop the docstring, keep the code
        called = {n.func.id for n in ast.walk(ast.Module(body=fn.body, type_ignores=[]))
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "conversion_band" not in called, (
            "the band is reachable from the derivation, so it can become a "
            "default by accident"
        )


class TestTheFalsifierIsRetractedForAStatedReason:

    def test_no_cell_of_the_declared_grid_saturates(self):
        r = CR.retrodiction_report()
        assert r["saturated_cells"] == 0, (
            f"{r['saturated_cells']} cells saturate — §7's retrodiction falsifier "
            "is firing again and the anchor page must say so"
        )

    def test_the_saturation_check_can_fire(self):
        """
        MODE 9, both directions. "Nothing saturates" is a result only if
        saturation is reachable. A rate an order of magnitude too low puts the
        widest scope over the top, exactly as the original run did.
        """
        hot = CR.epsilon_from_inventory(1.5, scope="residential")
        assert hot["epsilon"] >= 0.99, (
            "the derivation cannot reach saturation at any rate, so 'no cell "
            "saturates' says nothing about the framework"
        )

    def test_the_interior_is_a_credible_reading(self):
        """Government scope at current cost — the defensible middle."""
        for e in CR.retrodiction_report()["interior_epsilon"]:
            assert 0.30 < e < 0.75, f"interior ε {e} is outside a credible band"

    def test_epsilon_falls_as_the_rate_rises(self):
        """More currency per TEH means fewer TEH of capital means less automation."""
        eps = [CR.epsilon_from_inventory(r)["epsilon"] for r in (16.0, 21.0, 30.0)]
        assert eps[0] > eps[1] > eps[2]

    def test_each_judgement_moves_the_answer(self):
        """If any of the three were inert it would not need declaring."""
        base = CR.epsilon_from_inventory(20.0, scope="government", doctrine="current_cost")
        assert CR.epsilon_from_inventory(20.0, scope="productive")["epsilon"] != base["epsilon"]
        assert CR.epsilon_from_inventory(20.0, doctrine="historical_cost")["epsilon"] != base["epsilon"]
        assert CR.epsilon_from_inventory(30.0)["epsilon"] != base["epsilon"]


class TestTheDoctrineSpreadIsEvidenceForSection2:
    """
    BEA publishes two valuations of ONE unchanging physical stock. §2 predicts a
    valuation route transmits doctrine undamped and a census cannot move at all.
    This is that prediction, observed on the framework's own retrodiction.
    """

    def test_the_two_valuations_of_one_stock_differ(self):
        d = CR.doctrine_spread()
        assert d["aggregate"] == pytest.approx(1.78, abs=0.05)

    def test_the_spread_varies_by_asset_class(self):
        d = CR.doctrine_spread()
        assert d["widest_class"][0] == "structures"
        assert d["widest_class"][1] > d["narrowest_class"][1] * 1.5

    def test_the_doctrine_moves_epsilon(self):
        cc = CR.epsilon_from_inventory(20.0, doctrine="current_cost")["epsilon"]
        hc = CR.epsilon_from_inventory(20.0, doctrine="historical_cost")["epsilon"]
        assert cc > hc, "the more generous valuation must imply more machine capital"


class TestTheUnallocatedLineIsBoundedNotIgnored:
    """
    Government equipment carries no by-type breakdown outside defence in ANY BEA
    Fixed Assets table — 7.1 and 7.5 both single-line it. So it is placed, and
    the placement is bounded rather than defended.
    """

    def test_moving_it_anywhere_barely_moves_epsilon(self):
        s = CR.unallocated_sensitivity(20.0)
        assert s["span"] < 0.02, f"the placement now matters: span {s['span']}"
        assert s["share_of_scope"] < 0.02

    def test_it_is_smaller_than_the_judgements_that_are_declared(self):
        s = CR.unallocated_sensitivity(20.0)
        band = CR.conversion_band()
        assert s["span"] < (band["spread"] - 1.0), (
            "an unmeasured line worth more than a declared judgement would have "
            "to be acquired rather than bounded"
        )

    def test_it_names_what_would_close_it_and_why_that_is_not_needed(self):
        assert "Census of Governments" in str(CI.UNALLOCATED["what_would_close_it"])
        assert "function" in str(CI.UNALLOCATED["what_would_close_it"])
        assert len(str(CI.UNALLOCATED["why_it_does_not_need_closing"])) > 80


class TestRetrodictionChangesNothing:
    """REPORTING ONLY. Adopting any of this into the model is a separate act."""

    def test_the_report_refuses_a_point_estimate(self):
        r = CR.retrodiction_report()
        assert r["point_estimate"] is None
        assert r["adopted"] is False

    def test_the_verdict_is_computed_from_the_grid(self):
        r = CR.retrodiction_report()
        assert f"{r['epsilon_min']:.3f}" in r["verdict"]
        assert f"{r['epsilon_max']:.3f}" in r["verdict"]

    def test_it_states_its_own_gaps(self):
        assert len(CI.what_this_cannot_settle()) >= 5

    def test_nothing_in_core_or_land_imports_it(self):
        import pathlib
        import hours_eoh
        root = pathlib.Path(hours_eoh.__file__).resolve().parent
        for name in ("capital_inventory", "capital_retrodiction"):
            offenders = [
                p.relative_to(root).as_posix()
                for d in ("core", "land")
                for p in (root / d).rglob("*.py")
                if name in p.read_text(encoding="utf-8", errors="ignore")
            ]
            assert not offenders, f"{offenders} import {name}"
