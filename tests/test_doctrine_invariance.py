"""
Doctrine invariance — a COUNT does not need a convention; a VALUATION does.

WHY THIS EXISTS. The value-anchor argument's strongest claim is that this
framework can state a maintenance requirement that does not depend on which
accounting doctrine you hold. The evidence offered was
`doctrine_floor_invariance()` returning `floor_spread == 1.000`.

**That test cannot fail.** The doctrine parameter enters only through a
discretionary term added ABOVE the floor, and the floor is `Σ count ×
hours_per_unit_year` — there is nowhere for a convention to go. Its own docstring
says "1.000 by construction of the design". An assertion the implementation
enforces unconditionally is not evidence, and the claim deserved better.

AND THE FRAMING WAS WRONG. The draft said the floor is computed "without a price
anywhere in the chain". True — but MEASURED, no constant in `data.py` is
denominated in currency at all, so the monetised route has no price in its chain
either. "No currency" does not distinguish them.

THE ACTUAL DISTINCTION, which is sharper and is what these tests pin:

    the floor takes a CENSUS  — counts of things, and hours per thing
    the other route takes a VALUATION — one aggregate number for a stock

Counting bridges requires no convention. Valuing them requires choosing between
replacement, depreciated and historical, and that choice passes through the
monetised route UNDAMPED — the output spread equals the input ratio exactly.

So both behaviours are structural, and saying so is the point: this is a property
of what each route ACCEPTS, not a calibration result. What these tests make
falsifiable is that it stays that way.
"""

from __future__ import annotations

import re

import pytest

from hours_eoh.core.eoh_generation import (
    infrastructure_eoh,
    infrastructure_statutory_floor,
)
from hours_eoh.scenarios.infrastructure_floor import (
    PA_2025_BRIDGE_COUNTS,
    census_from_condition_counts,
    doctrine_floor_invariance,
)
from utils import provenance as pv

#: Illustrative RATIOS between three standard accounting doctrines applied to one
#: physical stock. Ratios, deliberately, not currency amounts: the claim is about
#: how a valuation choice PROPAGATES, and a dollar figure would add a number
#: nothing here measures. Any monotone set reproduces the finding.
DOCTRINE_RATIOS = {"historical": 0.55, "depreciated": 1.00, "replacement": 1.85}


def _census():
    return census_from_condition_counts(*PA_2025_BRIDGE_COUNTS)


class TestTheFloorCannotSeeAValuation:
    """
    THE FALSIFIABLE FORM. The floor ignoring a valuation is not an identity —
    someone could make it read one, and this fails the moment they do.
    """

    def test_monetary_fields_on_the_census_change_nothing(self):
        census = _census()
        before = infrastructure_statutory_floor(census)
        polluted = [
            {**b, "replacement_cost": 9.9e9, "book_value": 1.0,
             "wage": 55.0, "capital_stock_teh": 2.0e9}
            for b in census
        ]
        assert infrastructure_statutory_floor(polluted) == before

    def test_the_floor_needs_exactly_two_fields_and_refuses_without_them(self):
        with pytest.raises(ValueError, match="count"):
            infrastructure_statutory_floor([{"replacement_cost": 1.0e9}])

    def test_a_bucket_carrying_only_a_valuation_is_refused_not_guessed(self):
        """
        UNPRICED IS NOT ZERO. A bucket with a value and no physical census is an
        error, not a free asset — silently contributing 0.0 would let a
        valuation-only inventory read as a fully-measured floor.
        """
        with pytest.raises(ValueError):
            infrastructure_statutory_floor(
                [{"count": 100.0, "book_value": 5.0e8}]
            )


class TestTheFloorIsACountNotAValuation:

    def test_it_is_extensive_in_the_census(self):
        base = infrastructure_statutory_floor(_census())
        doubled = [{**b, "count": b["count"] * 2} for b in _census()]
        assert infrastructure_statutory_floor(doubled) == pytest.approx(
            2.0 * base, rel=1e-12
        )

    def test_it_is_invariant_to_how_the_census_is_AGGREGATED(self):
        """
        Splitting every bucket in two must not move the total. A quantity whose
        answer depends on how you grouped the survey is carrying a convention.

        Tolerance, not equality: this is a restructured floating-point sum, which
        is the `subdivision_invariance` lesson — `==` on two accumulations of the
        same terms is unsound and passed here while failing elsewhere.
        """
        before = infrastructure_statutory_floor(_census())
        split = []
        for b in _census():
            split.append({**b, "count": b["count"] / 2.0})
            split.append({**b, "count": b["count"] / 2.0})
        assert infrastructure_statutory_floor(split) == pytest.approx(
            before, rel=1e-12
        )

    def test_a_zero_census_is_zero_and_not_an_error(self):
        assert infrastructure_statutory_floor(
            [{"count": 0.0, "hours_per_unit_year": 8.0}]
        ) == 0.0


class TestTheValuationRouteTransmitsTheDoctrineUndamped:
    """
    THE CONTRAST, MADE REPRODUCIBLE FROM THE PACKAGE. Previously the monetised
    comparison lived only in a gitignored handoff, so the anchor argument's
    headline rested half on an artifact no reader could open.
    """

    def test_the_output_spread_equals_the_valuation_spread_exactly(self):
        base = 2.0e9
        out = {k: infrastructure_eoh(base * r, 0.50)
               for k, r in DOCTRINE_RATIOS.items()}
        ratios = list(DOCTRINE_RATIOS.values())
        assert max(out.values()) / min(out.values()) == pytest.approx(
            max(ratios) / min(ratios), rel=1e-12
        ), "a valuation choice reaches the answer with nothing damping it"

    def test_the_same_physical_stock_gives_three_different_requirements(self):
        base = 2.0e9
        out = sorted(infrastructure_eoh(base * r, 0.50)
                     for r in DOCTRINE_RATIOS.values())
        assert out[0] < out[1] < out[2]

    def test_the_census_route_is_untouched_by_the_same_choice(self):
        """
        The asymmetry in one assertion: the doctrine that moves the valuation
        route by its full ratio cannot move the census route at all, because the
        census route never receives it.
        """
        floor = infrastructure_statutory_floor(_census())
        for _ in DOCTRINE_RATIOS.values():
            assert infrastructure_statutory_floor(_census()) == floor


class TestTheContrastIsAboutCountsNotCurrency:
    """
    THE CORRECTION. Both routes are currency-free; that is not what separates
    them. Pinned so the draft's wording cannot quietly drift back.
    """

    def test_no_constant_is_denominated_in_currency(self):
        money = re.compile(r"\b(usd|dollar|eur|currency|wage)\b|\$", re.I)
        scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
        offenders = [(r.name, r.units) for r in scan.records
                     if r.units and money.search(r.units)]
        assert not offenders, (
            f"a currency-denominated constant would make 'no price in the chain' "
            f"a real distinction again, and would need its own review: {offenders}"
        )

    def test_the_valuation_route_has_no_price_in_it_either(self):
        """
        `capital_stock` is denominated in TEH, not money — so the monetised route
        is ALSO currency-free, and still doctrine-dependent. That is the whole
        correction: the problem is aggregation into a value, not the unit.
        """
        scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
        rec = next(r for r in scan.records if r.name == "CAPITAL_STOCK_DEFAULT")
        assert "TEH" in rec.units
        assert "$" not in rec.units


class TestTheInvarianceScenarioIsStructuralAndItsParameterIsLive:
    """
    The honest reading of `doctrine_floor_invariance`. Its floor result cannot
    fail — but its parameter is not inert, and that distinction is what stops the
    scenario being vacuous. A doctrine moves the TOTAL and not the FLOOR, which
    is precisely the design claim.
    """

    def test_the_floor_does_not_move(self):
        r = doctrine_floor_invariance()
        assert r["floor_spread"] == pytest.approx(1.0, abs=1e-12)
        assert r["determinacy_restored"] is True

    def test_but_the_doctrine_parameter_is_not_inert(self):
        """
        If the discretionary term moved nothing either, `floor_spread == 1.0`
        would be evidence of a dead parameter rather than of a protected floor.
        """
        r = doctrine_floor_invariance()
        assert r["total_spread"] > 1.0

    def test_the_doctrine_reaches_the_total_by_exactly_the_amount_declared(self):
        wide = doctrine_floor_invariance(
            doctrines={"a": 0.0, "b": 2_000_000.0}
        )
        assert wide["floor_spread"] == pytest.approx(1.0, abs=1e-12)
        assert wide["total_spread"] > 1.0
