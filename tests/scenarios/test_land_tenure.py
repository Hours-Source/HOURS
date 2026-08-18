"""
Tests for the pristine/current partition (4d) and the tenure rule (4c).

Both are author-signed-off (2026-08-17). The partition assigns the STOCK to the
ecological domain and the FLOW to GUF; the tenure rule assigns unheld land to
the federation rather than leaving it uncollected.
"""

import math

import pytest

from hours_eoh.core.eoh_generation import (
    ecological_eoh,
    ecological_eoh_breakdown,
    total_eoh,
)
from hours_eoh.scenarios.land_tenure import allocate_by_tenure, tenure_allocation
from hours_eoh.scenarios.restoration_cost import pristine_gap_obligation

ARC = [0.0, 0.40, 0.90, 0.99]

_INVENTORY = [
    {"class": "degraded cropland", "hectares": 50e6, "deficit": 0.6},
    {"class": "degraded rangeland", "hectares": 80e6, "deficit": 0.3},
]


# ===========================================================================
# 4d — the pristine gap as the domain's STOCK term
# ===========================================================================

class TestTheDomainCarriesTwoStocks:
    """
    Under the partition the ecological domain carries exactly two terms, and
    both are stocks: thermal (non-restorable) and restoration (the pristine gap).
    Everything recurring is GUF.
    """

    def test_restoration_is_opt_in_and_defaults_to_zero(self):
        for eps in ARC:
            b = ecological_eoh_breakdown(0.70, eps)
            assert b["restoration"] == 0.0

    def test_restoration_adds_to_the_domain(self):
        for eps in ARC:
            base = ecological_eoh(0.70, eps)
            loaded = ecological_eoh(0.70, eps, restoration_obligation=1000.0)
            assert loaded - base == pytest.approx(1000.0, rel=1e-12)

    def test_total_is_the_sum_of_its_named_parts(self):
        b = ecological_eoh_breakdown(
            0.70, 0.40, deferred=5000.0,
            thermal_obligation=250.0, restoration_obligation=1000.0,
        )
        assert b["total"] == pytest.approx(
            b["baseline"] + b["spike"] + b["visible_deferred"]
            + b["thermal"] + b["restoration"], rel=1e-12
        )

    def test_the_two_stocks_are_independent(self):
        """A thermal obligation must not move the restoration term or vice versa."""
        t = ecological_eoh_breakdown(0.70, 0.40, thermal_obligation=500.0)
        r = ecological_eoh_breakdown(0.70, 0.40, restoration_obligation=500.0)
        assert t["restoration"] == 0.0
        assert r["thermal"] == 0.0
        assert t["total"] == pytest.approx(r["total"], rel=1e-12)

    def test_it_reaches_the_domain_through_total_eoh(self):
        base = total_eoh(epsilon=0.40)["ecological"]
        # ecological_eoh takes it directly; total_eoh does not expose it yet,
        # so this pins the CURRENT reach honestly rather than implying more.
        assert ecological_eoh(0.70, 0.40, restoration_obligation=100.0) > base


class TestPristineGapObligation:

    def test_governing_equation(self):
        r = pristine_gap_obligation(_INVENTORY, amortization_years=50.0)
        cost = r["lifetime_h_per_ha"]
        expected = sum(
            e["hectares"] * e["deficit"] * cost / 50.0 for e in _INVENTORY
        )
        assert r["annual_hours"] == pytest.approx(expected, rel=1e-12)

    def test_deficit_zero_owes_nothing(self):
        """Land at reference condition owes no restoration — the partition's point."""
        r = pristine_gap_obligation(
            [{"class": "pristine", "hectares": 1e9, "deficit": 0.0}]
        )
        assert r["annual_hours"] == 0.0

    def test_scales_with_area_deficit_and_inversely_with_horizon(self):
        base = pristine_gap_obligation(_INVENTORY, amortization_years=50.0)["annual_hours"]
        half = pristine_gap_obligation(_INVENTORY, amortization_years=25.0)["annual_hours"]
        assert half == pytest.approx(2.0 * base, rel=1e-12)

        doubled = [{**e, "hectares": e["hectares"] * 2} for e in _INVENTORY]
        assert pristine_gap_obligation(doubled)["annual_hours"] == pytest.approx(
            2.0 * base, rel=1e-12
        )

    def test_band_corners_bracket_each_other(self):
        lo = pristine_gap_obligation(_INVENTORY, corner="low")["annual_hours"]
        hi = pristine_gap_obligation(_INVENTORY, corner="high")["annual_hours"]
        assert lo < hi

    def test_out_of_range_deficit_rejected(self):
        for bad in (-0.01, 1.01):
            with pytest.raises(ValueError, match="deficit must be in"):
                pristine_gap_obligation([{"class": "x", "hectares": 1.0, "deficit": bad}])

    def test_bad_horizon_and_corner_rejected(self):
        with pytest.raises(ValueError, match="amortization_years"):
            pristine_gap_obligation(_INVENTORY, amortization_years=0.0)
        with pytest.raises(ValueError, match="corner"):
            pristine_gap_obligation(_INVENTORY, corner="middle")

    def test_the_inventory_has_no_default(self):
        """
        THE DISCIPLINE. Phase 3 measured the cost PER HECTARE RESTORED; this
        needs the HECTARES NEEDING RESTORATION, which is a land-condition survey
        this package does not ship. A default would put a fitted number where a
        measurement belongs.
        """
        with pytest.raises(TypeError):
            pristine_gap_obligation()  # type: ignore[call-arg]
        assert pristine_gap_obligation([])["annual_hours"] == 0.0


# ===========================================================================
# 4c — unowned land is federation
# ===========================================================================

class TestNothingIsUncollected:
    """
    The decision, operationalised: a land obligation with no member holder goes
    to the federation. `uncollected` is structurally zero, not merely small.
    """

    def test_the_split_is_exhaustive(self):
        for frac in (0.0, 0.25, 0.5, 1.0):
            r = allocate_by_tenure(1000.0, frac)
            assert r["federation_hours"] + r["member_hours"] == pytest.approx(
                1000.0, rel=1e-12
            )
            assert r["uncollected_hours"] == 0.0

    def test_wholly_unheld_land_goes_entirely_to_the_federation(self):
        r = allocate_by_tenure(1000.0, 1.0)
        assert r["federation_hours"] == 1000.0
        assert r["member_hours"] == 0.0

    def test_wholly_held_land_owes_the_federation_nothing(self):
        r = allocate_by_tenure(1000.0, 0.0)
        assert r["federation_hours"] == 0.0
        assert r["member_hours"] == 1000.0

    def test_out_of_range_inputs_rejected(self):
        with pytest.raises(ValueError, match="federation_fraction"):
            allocate_by_tenure(100.0, 1.5)
        with pytest.raises(ValueError, match="obligation_hours"):
            allocate_by_tenure(-1.0, 0.5)


class TestTenureAllocationAcrossLandClasses:

    def test_allocation_is_exhaustive_across_every_class(self):
        r = tenure_allocation(45.92, {"Miscellaneous other land": 1.0})
        assert r["federation_hours"] + r["member_hours"] == pytest.approx(
            r["total_hours"], rel=1e-12
        )
        assert r["uncollected_hours"] == 0.0

    def test_undeclared_classes_are_REPORTED_not_folded_away(self):
        """
        An omitted tenure fraction defaults to wholly member-held, which
        understates the federation's obligation. That is the unsafe direction
        for provisioning it, so the omissions are returned.
        """
        r = tenure_allocation(45.92, {"Miscellaneous other land": 1.0})
        assert len(r["classes_without_declared_tenure"]) >= 5
        assert "Land in urban areas" in r["classes_without_declared_tenure"]

    def test_total_land_is_excluded_from_the_class_sum(self):
        """ERS carries a 'Total land' row; summing it would double the area."""
        r = tenure_allocation(1.0, {})
        names = [x["land_use"] for x in r["by_class"]]
        assert "Total land" not in names
        assert r["total_hours"] == pytest.approx(
            sum(x["hectares"] for x in r["by_class"]), rel=1e-12
        )

    def test_unknown_class_raises_rather_than_being_ignored(self):
        with pytest.raises(KeyError, match="unknown land classes"):
            tenure_allocation(1.0, {"Atlantis": 1.0})

    def test_zero_intensity_gives_zero_obligation(self):
        r = tenure_allocation(0.0, {"Miscellaneous other land": 1.0})
        assert r["total_hours"] == 0.0
        assert r["federation_share"] == 0.0

    def test_negative_intensity_rejected(self):
        with pytest.raises(ValueError, match="intensity"):
            tenure_allocation(-1.0, {})

    def test_federal_land_is_the_central_case_not_an_exception(self):
        """
        Parks are not unowned — the federation holds them and owes what any
        holder owes. Declaring them raises the federation's share; it does not
        move the obligation off the books.
        """
        without = tenure_allocation(45.92, {})
        with_parks = tenure_allocation(
            45.92, {"Land in rural parks and wildlife areas": 0.67}
        )
        assert with_parks["federation_hours"] > without["federation_hours"]
        assert with_parks["total_hours"] == pytest.approx(
            without["total_hours"], rel=1e-12
        )


class TestPartitionChangesNothing:
    """4d and 4c are structure. No shipped number moves."""

    def test_shipped_totals_are_untouched(self):
        expected = {
            0.0:  1390564529.0250847,
            0.40: 1593258132.7079391,
            0.99: 2883949145.115244,
        }
        for eps, want in expected.items():
            assert total_eoh(epsilon=eps)["total"] == want

    def test_arc_coherence_with_both_stocks_loaded(self):
        for eps in ARC:
            v = ecological_eoh(
                0.70, eps, thermal_obligation=100.0, restoration_obligation=200.0
            )
            assert math.isfinite(v) and v > 0.0


# ===========================================================================
# 4e — the health response relocated to the reset cost
# ===========================================================================

from hours_eoh.scenarios.land_tenure import health_response_relocation

HEALTHS = [1.0, 0.9, 0.7, 0.5, 0.3, 0.2]


class TestTheDecompositionIsExact:
    """
    baseline = rate/health = rate + rate·(1−health)/health. An algebraic
    identity, so it moves no number by itself — what it does is make the two
    halves separately assignable.
    """

    def test_standing_plus_degradation_is_the_baseline(self):
        for h in HEALTHS:
            b = ecological_eoh_breakdown(h, 0.40)
            assert b["standing"] + b["degradation_response"] == pytest.approx(
                b["baseline"], rel=1e-12
            )

    def test_standing_is_health_independent(self):
        vals = {ecological_eoh_breakdown(h, 0.40)["standing"] for h in HEALTHS}
        assert len(vals) == 1

    def test_at_pristine_health_the_degradation_response_is_EXACTLY_zero(self):
        """
        The partition's central claim, arriving as algebra rather than
        assertion: land in reference condition owes nothing beyond its own
        standing obligation.
        """
        b = ecological_eoh_breakdown(1.0, 0.40)
        assert b["degradation_response"] == 0.0
        assert b["spike"] == 0.0
        assert b["relocatable_to_guf"] == 0.0


class TestDefaultReproducesPre4e:
    """Opt-in, the same treatment thermal_obligation received at its sign-off."""

    def test_default_mode_is_domain(self):
        assert ecological_eoh_breakdown(0.70, 0.40)["health_response"] == "domain"

    def test_default_total_is_the_pre_4e_formula(self):
        for h in HEALTHS:
            b = ecological_eoh_breakdown(h, 0.40)
            assert b["total"] == pytest.approx(
                b["baseline"] + b["spike"] + b["visible_deferred"]
                + b["thermal"] + b["restoration"], rel=1e-12
            )

    def test_shipped_totals_untouched(self):
        expected = {
            0.0:  1390564529.0250847,
            0.40: 1593258132.7079391,
            0.99: 2883949145.115244,
        }
        for eps, want in expected.items():
            assert total_eoh(epsilon=eps)["total"] == want

    def test_bad_mode_rejected(self):
        with pytest.raises(ValueError, match="health_response"):
            ecological_eoh_breakdown(0.70, 0.40, health_response="somewhere")


class TestRelocationConservesAndIsHealthInvariant:

    def test_the_obligation_is_conserved_at_every_health(self):
        """Only the ADDRESS changes: nothing is created or destroyed."""
        for h in HEALTHS:
            r = health_response_relocation(h)
            assert r["conserved"]
            assert r["domain_total_after"] + r["relocated_to_guf"] == pytest.approx(
                r["domain_total_before"], rel=1e-12
            )

    def test_the_domain_becomes_health_INVARIANT(self):
        """
        THE POINT OF 4e. After relocation the domain owes the same whatever
        condition the land is in — condition changes what the HOLDER owes, not
        what the domain does. Before 4e the domain rose 3.6x from health 1.0 to
        health 0.3.
        """
        totals = [health_response_relocation(h)["domain_total_after"] for h in HEALTHS]
        assert max(totals) == pytest.approx(min(totals), rel=1e-12)

        before = [health_response_relocation(h)["domain_total_before"] for h in HEALTHS]
        assert max(before) / min(before) > 3.0

    def test_the_relocated_share_rises_with_degradation(self):
        """
        The property that makes the health response a DISTURBANCE measure. If
        the share did not rise as condition falls, relocating it to the reset
        cost would not be justified.
        """
        shares = [health_response_relocation(h)["relocated_share"] for h in HEALTHS]
        assert shares == sorted(shares)
        assert shares[0] == 0.0            # pristine
        assert shares[-1] > 0.7            # badly degraded

    def test_guf_mode_reaches_total_eoh(self):
        base = total_eoh(epsilon=0.40, ecosystem_health=0.70)["ecological"]
        moved = total_eoh(epsilon=0.40, ecosystem_health=0.70,
                          ecological_health_response="guf")["ecological"]
        assert moved < base

    def test_stocks_are_untouched_by_the_relocation(self):
        """thermal and restoration are stocks and must not move sides."""
        g = ecological_eoh_breakdown(
            0.30, 0.40, health_response="guf",
            thermal_obligation=100.0, restoration_obligation=200.0,
        )
        assert g["thermal"] == 100.0
        assert g["restoration"] == 200.0
        assert g["total"] == pytest.approx(
            g["standing"] + g["visible_deferred"] + 100.0 + 200.0, rel=1e-12
        )

    def test_arc_coherence_in_both_modes(self):
        for mode in ("domain", "guf"):
            for eps in ARC:
                for h in (0.99, 0.70, 0.20):
                    v = ecological_eoh(0.70 if h is None else h, eps,
                                       health_response=mode)
                    assert math.isfinite(v) and v > 0.0


class TestOneLoaderOverOneCSV:
    """
    2026-08-17: `reference/servicing` had grown a second dict loader over the
    same MLU CSV, and the two disagreed on whether the aggregate "Total land"
    row belongs in a mapping. It does not — summing such a mapping doubles the
    area. No live figure was wrong, but one consumer already carried a
    `if name == "Total land": continue` workaround, which is a duplicate
    announcing itself.
    """

    def test_the_dict_projection_matches_the_row_loader(self):
        from hours_eoh.reference.land_stewardship import (
            land_hectares_by_class,
            load_land_use,
        )
        rows = load_land_use()
        by_class = land_hectares_by_class()
        assert set(by_class) == {r["land_use"] for r in rows}
        for r in rows:
            assert by_class[r["land_use"]] == r["area_hectares"]

    def test_servicing_delegates_rather_than_re_reading(self):
        from hours_eoh.reference.land_stewardship import land_hectares_by_class
        from hours_eoh.reference.servicing import load_land_use as servicing_loader
        assert servicing_loader() == land_hectares_by_class()

    def test_the_aggregate_row_is_excluded_from_the_mapping(self):
        from hours_eoh.reference.land_stewardship import land_hectares_by_class
        assert "Total land" not in land_hectares_by_class()

    def test_the_classes_partition_total_land_exactly(self):
        """
        The property the exclusion protects. If the aggregate leaked back into
        the mapping this sum would be 2x the total, and every area-weighted
        figure downstream would halve.
        """
        from hours_eoh.reference.land_stewardship import (
            land_hectares_by_class,
            total_land_hectares,
        )
        assert sum(land_hectares_by_class().values()) == pytest.approx(
            total_land_hectares(), rel=1e-9
        )

    def test_tenure_allocation_needs_no_workaround(self):
        """The consumer that carried the skip now gets a clean mapping."""
        r = tenure_allocation(1.0, {})
        assert "Total land" not in [x["land_use"] for x in r["by_class"]]
        assert len(r["by_class"]) == 9
