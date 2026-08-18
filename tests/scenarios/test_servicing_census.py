"""
Tests for the servicing-cost census (Phase 2).

The census runs the instrument `GUF_USE_*`'s own `resolves_by` names. It is
REPORTING ONLY — `TestCensusChangesNothing` is the discipline that keeps it so.
"""

import math

import pytest

from hours_eoh.data import SLU_HECTARES
from hours_eoh.land.guf import USE_CATEGORIES
from hours_eoh.reference import land_stewardship, servicing
from hours_eoh.scenarios.servicing_census import (
    SHIPPED_SCALE_FACTOR,
    census,
    census_report,
    realized_vs_measured,
    shipped_vs_measured,
)

SCOPES = ["core", "broad", "urban_upper"]


class TestInputsAreMeasured:

    def test_employment_comes_from_the_multiplier_registry(self):
        """Same file the multiplier uses, so the two cannot drift."""
        emp = servicing.load_registry_employment()
        assert len(emp) > 700
        for att in servicing.SERVICING_ATTRIBUTIONS:
            assert att["occ6"] in emp, att["title"]

    def test_land_use_comes_from_ers_mlu(self):
        lu = servicing.load_land_use()
        assert "Land in urban areas" in lu
        for scope, classes in servicing.SERVICED_LAND_CLASSES.items():
            for name in classes:
                assert name in lu, f"{scope}: {name}"

    def test_hours_per_worker_is_derived_not_chosen(self):
        h = census("core")["hours_per_worker_year"]
        assert 1_800.0 < h < 1_950.0
        assert h != 2_080.0 and h != 1_800.0


class TestTheAssumedMappingIsIsolated:

    def test_every_attribution_carries_a_basis(self):
        for att in servicing.SERVICING_ATTRIBUTIONS:
            assert att["basis"].strip()
            assert att["function"] in {
                "roads", "utilities", "inspection", "dispute_resolution"
            }

    def test_the_four_resolves_by_functions_are_all_represented(self):
        got = {a["function"] for a in servicing.SERVICING_ATTRIBUTIONS}
        assert got == {"roads", "utilities", "inspection", "dispute_resolution"}

    def test_exclusions_are_named_with_reasons(self):
        assert servicing.EXCLUDED_OCCUPATIONS
        for exc in servicing.EXCLUDED_OCCUPATIONS:
            assert exc["reason"].strip()
            assert exc["occ6"] not in {a["occ6"] for a in servicing.SERVICING_ATTRIBUTIONS}

    def test_the_manufacturing_qc_false_positive_is_excluded(self):
        """
        519061 Inspectors, Testers, Sorters is manufacturing QC and matches any
        regex for 'inspect'. It is the largest false positive available and
        would nearly quadruple the inspection function alone.
        """
        excluded = {e["occ6"] for e in servicing.EXCLUDED_OCCUPATIONS}
        assert "519061" in excluded
        attributed = {a["occ6"] for a in servicing.SERVICING_ATTRIBUTIONS}
        assert "519061" not in attributed


class TestDisjointFromStewardship:
    """
    Servicing and stewardship are different quantities and must not double-count:
    what the BUILT ENVIRONMENT costs to hold, against what the LAND costs to hold.
    """

    def test_no_occupation_appears_in_both_censuses(self):
        serv = {a["occ6"] for a in servicing.SERVICING_ATTRIBUTIONS}
        stew: set[str] = set()
        for att in land_stewardship.STEWARDSHIP_ATTRIBUTIONS:
            stew.update(att["occupations"])
        assert serv.isdisjoint(stew), f"double-counted: {serv & stew}"


class TestCensusArithmetic:

    def test_every_scope_resolves(self):
        for scope in SCOPES:
            c = census(scope)
            assert c["workers"] > 0
            assert c["serviced_hectares"] > 0
            assert math.isfinite(c["hours_per_hectare_year"])
            assert c["missing_from_registry"] == []

    def test_teh_per_slu_is_the_hectare_rate_times_the_conversion(self):
        for scope in SCOPES:
            c = census(scope)
            assert c["teh_per_slu_year"] == pytest.approx(
                c["hours_per_hectare_year"] * SLU_HECTARES, rel=1e-12
            )

    def test_broad_adds_workers_and_area_relative_to_core(self):
        core, broad = census("core"), census("broad")
        assert broad["workers"] > core["workers"]
        assert broad["serviced_hectares"] > core["serviced_hectares"]

    def test_scope_barely_moves_the_rate(self):
        """
        A CONTRAST WITH THE STEWARDSHIP CENSUS, where scope was worth 41× and the
        definition — not the measurement — was what stayed unresolved. Here the
        broad scope adds ~29% more workers and ~34% more area and they roughly
        cancel, so the servicing rate is robust to the judgement.
        """
        core, broad = census("core")["hours_per_hectare_year"], census("broad")["hours_per_hectare_year"]
        assert max(core, broad) / min(core, broad) < 1.2

    def test_urban_upper_is_an_upper_bound(self):
        """
        Every core worker charged to urban land alone. Must exceed the core rate,
        and it errs AGAINST the overshoot finding — the true urban rate is lower.
        """
        assert census("urban_upper")["hours_per_hectare_year"] > \
               census("core")["hours_per_hectare_year"]
        assert census("urban_upper")["workers"] == census("core")["workers"]

    def test_bad_scope_rejected(self):
        with pytest.raises(ValueError, match="scope"):
            census("everywhere")


class TestTheFinding:

    def test_shipped_table_exceeds_the_measured_rate(self):
        cmp_ = shipped_vs_measured("core")
        assert cmp_["shipped_over_measured_mean"] > 10.0
        assert cmp_["implied_scale_factor"] < SHIPPED_SCALE_FACTOR
        assert cmp_["overshoot_factor"] > 1.0

    def test_rural_lands_near_the_census_and_urban_does_not(self):
        """
        THE PHASE 2 RESULT, and it is a shape finding rather than a level one:
        the ×100 is roughly right for low-density land and far out for dense
        land. Asserted as an ORDERING and a band, not a level — the levels are
        calibration and will move.
        """
        r = {x["archetype"]: x for x in realized_vs_measured()["rows"]}
        assert 0.5 < r["rural"]["ratio"] < 3.0
        assert r["urban"]["ratio"] > 10.0
        assert r["urban"]["ratio"] > r["rural"]["ratio"]

    def test_urban_is_compared_against_the_urban_scope(self):
        r = {x["archetype"]: x for x in realized_vs_measured()["rows"]}
        assert r["urban"]["compared_against"] == "urban_upper"
        assert r["rural"]["compared_against"] == "core"

    def test_report_states_what_it_cannot_settle(self):
        rep = census_report("core")
        assert "RATIOS" in rep["what_this_does_not_settle"]
        assert rep["scope_spread_factor"] >= 1.0


class TestCensusChangesNothing:
    """REPORTING ONLY. Phase 2 measures the ×100; it does not retire it."""

    def test_use_categories_are_untouched(self):
        assert USE_CATEGORIES["residential_primary"] == 10.0
        assert USE_CATEGORIES["industrial_heavy"] == 37.5
        assert USE_CATEGORIES["conservation"] == -6.0

    def test_shipped_scale_factor_is_still_one_hundred(self):
        assert SHIPPED_SCALE_FACTOR == 100.0


class TestArcCoherence:

    def test_realized_comparison_resolves_across_the_arc(self):
        for eps in (0.0, 0.40, 0.90, 0.99):
            r = realized_vs_measured(eps)
            for row in r["rows"]:
                assert math.isfinite(row["realised_h_per_ha"])
                assert row["realised_h_per_ha"] >= 0.0
