"""
The machine-capability index and the observed machine share are two quantities.

WHY THIS EXISTS (author decision, 2026-09-01). `epsilon` was doing two jobs: as
an INPUT it says what machines are capable of taking, and as an OBSERVABLE it is
DEFINED as the machine share of obligation. Under `uniform` they are identical by
construction, so the distinction could not be seen. Phase 2 separated them — the
personal domain now keeps a floored human share — and the observed share is
strictly below the supplied index everywhere except zero.

That matters beyond bookkeeping. The value-anchor argument states that ε is "the
share of civilization's obligation still dependent on human agency". At a high
index the parameter reports the machines and the ledger reports a materially
larger human residual. Publishing the first as the second is the
reported-vs-applied defect, one layer up from the code.

THE PAYOFF: the arc's endpoint stops being a convention. Under `uniform` nothing
caps automation and the ceiling is exactly 1.0. Under `per_component` the ceiling
is `1 - personal_share · Σ share_c · floor_c` and sits strictly below 1 — a
CONSEQUENCE of the declared floors.

NO LEVEL IS RESTATED HERE, and `TestNoFigureIsRestatedInProse` enforces that.
Both quantities move with the floors table and the component shares, both live;
the five figures that used to sit in `core/eoh_fulfillment`'s docstrings were
stale from the day `NUTRITION_AUTOMATION_FLOOR` was adopted and nothing failed.
Call `observable_epsilon()` and `observable_epsilon_ceiling()` for the numbers.
"""

from __future__ import annotations

import inspect
import re

import pytest

import hours_eoh.core.eoh_fulfillment as _fulfillment
from hours_eoh.core.eoh_fulfillment import (
    eoh_to_teh_pipeline,
    human_eoh_per_domain,
    observable_epsilon,
    observable_epsilon_ceiling,
    personal_human_fraction,
)
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.data import (
    CARE_AUTOMATION_FLOOR, PERSONAL_AUTOMATION_FLOORS, PERSONAL_EOH_COMPONENTS,
)

ARC = (0.0, 0.40, 0.90, 0.99)
_DOMAINS = ("personal", "infrastructure", "ecological", "knowledge")


def _eoh_at(capability: float) -> dict:
    """Total EOH on the canonical arc, mapped keyword by keyword.

    NOT `**state` and not a signature filter. `canonical_physical_state` names
    two of its keys differently from `total_eoh` — `capital_stock_teh` against
    `capital_stock`, `knowledge_base_size` against `knowledge_complexity` — so a
    filter silently DROPS both and freezes the two largest non-personal domains
    at their defaults for the whole arc. This helper is the instrument every
    figure below is read off, which is why it maps explicitly, the way
    `scenarios/ecological_floor._eoh_at` documents and for the same reason.
    """
    state = canonical_physical_state(capability)
    return total_eoh(
        capital_stock=state["capital_stock_teh"],
        capital_age_ratio=state["capital_age_ratio"],
        ecosystem_health=state["ecosystem_health"],
        monitoring_capability=state["monitoring_capability"],
        age_distribution=state["age_distribution"],
        knowledge_complexity=state["knowledge_base_size"],
        knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
    )


class TestUniformIsTheDegenerateCase:
    """
    THE CONTROL. Under the superseded response the split is exactly (1-c) on
    every domain, so the share recovered from it MUST be the number fed in. If
    this ever fails, the divergence measured below is an arithmetic artefact
    rather than the separation it claims to be.
    """

    @pytest.mark.parametrize("capability", ARC)
    def test_observed_equals_capability_under_uniform(self, capability):
        dom = _eoh_at(capability)
        assert observable_epsilon(dom, capability, "uniform") == pytest.approx(
            capability, rel=1e-12, abs=1e-12
        )

    def test_the_uniform_ceiling_is_exactly_one(self):
        """Nothing floors automation under the uniform response."""
        dom = _eoh_at(0.99)
        assert observable_epsilon_ceiling(dom, "uniform") == pytest.approx(1.0, abs=1e-12)


class TestTheInstrumentTransmitsTheCanonicalState:
    """
    THE HELPER EVERY FIGURE BELOW IS READ OFF, checked before it is trusted.

    `_eoh_at` used to build its state by filtering `canonical_physical_state`
    against `total_eoh`'s signature. Two keys are named differently on the two
    sides — `capital_stock_teh`/`capital_stock` and
    `knowledge_base_size`/`knowledge_complexity` — so the filter dropped both
    and froze infrastructure and knowledge at their defaults for the entire arc.
    Every shape below still held, because a shape survives a frozen domain; the
    LEVELS did not, and the levels are what the value-anchor section quotes.
    """

    def test_no_capital_on_the_arc_means_no_maintenance_obligation(self):
        """The canonical arc starts at zero capital, so infrastructure EOH is
        exactly zero there. A dropped `capital_stock` shows up as the default
        stock's maintenance appearing out of nothing."""
        assert _eoh_at(0.0)["infrastructure"] == 0.0

    def test_both_dropped_keys_move_an_output(self):
        """The filtered call is RECONSTRUCTED here and shown to differ, so this
        fails the moment the helper reverts to a signature filter."""
        state = canonical_physical_state(0.99)
        as_filtered = total_eoh(
            capital_age_ratio=state["capital_age_ratio"],
            ecosystem_health=state["ecosystem_health"],
            monitoring_capability=state["monitoring_capability"],
            age_distribution=state["age_distribution"],
            knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        )
        got = _eoh_at(0.99)
        assert got["infrastructure"] != pytest.approx(as_filtered["infrastructure"]), (
            "capital_stock is not reaching total_eoh"
        )
        assert got["knowledge"] > 5.0 * as_filtered["knowledge"], (
            "knowledge_complexity is not reaching total_eoh"
        )


class TestNoFigureIsRestatedInProse:
    """
    THE GATE FOR RECURRING FAILURE MODE 13. Five derived figures sat in
    `core/eoh_fulfillment`'s docstrings — a capability→observed table, a gap of
    0.081, a ceiling of 0.917 — and every one of them was stale from the day
    `NUTRITION_AUTOMATION_FLOOR` was adopted. Nothing failed, because nothing
    pinned them: the suite pins shapes, and a restated number is not a shape.

    Pinning the values instead would be the wrong fix — they move with two live
    measurements, so the pin would need updating on every improvement and would
    read as a result. The durable rule is that a derived level does not appear
    in prose AT ALL; the reader calls the function.

    SCOPED to the three docstrings that carried the drift, and to decimals of
    three or more places, so a share like `0.99` or a rate stays sayable.
    """

    _RESULT_LIKE = re.compile(r"\d\.\d{3,}")

    @pytest.mark.parametrize("obj", (
        pytest.param(_fulfillment, id="module"),
        pytest.param(observable_epsilon, id="observable_epsilon"),
        pytest.param(observable_epsilon_ceiling, id="observable_epsilon_ceiling"),
    ))
    def test_no_restated_result_in_the_docstring(self, obj):
        doc = inspect.getdoc(obj) or ""
        found = self._RESULT_LIKE.findall(doc)
        assert not found, (
            f"{getattr(obj, '__name__', obj)} restates derived levels {found}. "
            "Call observable_epsilon()/observable_epsilon_ceiling() instead — "
            "these figures drifted once already and nothing caught it."
        )


class TestTheTwoQuantitiesDiverge:

    def test_they_coincide_only_at_zero(self):
        dom = _eoh_at(0.0)
        assert observable_epsilon(dom, 0.0) == pytest.approx(0.0, abs=1e-12)

    @pytest.mark.parametrize("capability", (0.40, 0.90, 0.99))
    def test_observed_is_strictly_below_capability(self, capability):
        dom = _eoh_at(capability)
        assert observable_epsilon(dom, capability) < capability

    def test_the_gap_widens_along_the_arc(self):
        gaps = [c - observable_epsilon(_eoh_at(c), c) for c in ARC]
        assert gaps == sorted(gaps), "the two accounts should separate, not converge"

    def test_the_gap_is_material_at_the_top(self):
        """
        SIGN and MAGNITUDE-CLASS, not a level. The level moves with the care
        share and the floor, both of which are live measurements.
        """
        gap = 0.99 - observable_epsilon(_eoh_at(0.99), 0.99)
        assert gap > 0.05


class TestTheCeilingIsAConsequenceOfTheFloors:
    """
    This is the claim that ε does not reach 1 BECAUSE care resists automation,
    rather than by convention.
    """

    @pytest.mark.parametrize("capability", ARC)
    def test_the_ceiling_is_below_one(self, capability):
        assert observable_epsilon_ceiling(_eoh_at(capability)) < 1.0

    def test_the_ceiling_reproduces_from_the_floors_by_hand(self):
        """
        ceiling = 1 - personal_share · Σ share_c · floor_c, computed from the
        data rather than from the implementation.
        """
        dom = _eoh_at(0.99)
        gross = sum(dom[d] for d in _DOMAINS)
        residual_personal = personal_human_fraction(1.0, "per_component")
        expected = 1.0 - (dom["personal"] / gross) * residual_personal
        assert observable_epsilon_ceiling(dom) == pytest.approx(expected, rel=1e-12)

    def test_removing_the_floor_removes_the_ceiling(self):
        """
        The falsification: with no floor there is nothing to cap automation, and
        the ceiling must go to exactly 1. That is what makes the floor the cause.
        """
        dom = _eoh_at(0.99)
        assert observable_epsilon_ceiling(dom, "uniform") == pytest.approx(1.0, abs=1e-12)
        assert observable_epsilon_ceiling(dom, "per_component") < 0.99

    def test_the_residual_traces_to_the_floored_components(self):
        """
        At full capability the human residual is exactly the share-weighted sum
        of the floors. Written over the TABLE rather than over `care` alone:
        the first version hardcoded the single entry the table then had and
        broke when nutrition was adopted on 2026-09-03.
        """
        expected = sum(
            float(PERSONAL_EOH_COMPONENTS[name]["share"]) * floor
            for name, floor in PERSONAL_AUTOMATION_FLOORS.items()
        )
        assert personal_human_fraction(1.0, "per_component") == pytest.approx(expected)

    def test_care_is_still_part_of_that_residual(self):
        """The original claim, kept: care alone cannot account for all of it."""
        care = PERSONAL_EOH_COMPONENTS["care"]
        care_only = float(care["share"]) * CARE_AUTOMATION_FLOOR
        total = personal_human_fraction(1.0, "per_component")
        assert 0.0 < care_only < total, (
            "care must contribute to the residual without exhausting it, now "
            "that a second component carries a floor"
        )

    def test_the_ceiling_depends_on_the_obligation_MIX(self):
        """
        Not a pure function of capability: a care-heavier obligation has a lower
        ceiling. Pinned because it is the property that makes the ceiling an
        empirical quantity rather than a constant.
        """
        light = {"personal": 1.0, "infrastructure": 9.0,
                 "ecological": 0.0, "knowledge": 0.0}
        heavy = {"personal": 9.0, "infrastructure": 1.0,
                 "ecological": 0.0, "knowledge": 0.0}
        assert observable_epsilon_ceiling(heavy) < observable_epsilon_ceiling(light)

    def test_it_is_a_lower_bound_on_the_residual(self):
        """
        Two of the four personal components carry a floor and two carry none —
        shelter and health are ABSENT, not zero. Adding one for another
        component must lower the ceiling further, so the shipped figure errs
        HIGH and is an upper bound on itself.
        """
        import hours_eoh.core.eoh_fulfillment as m
        dom = _eoh_at(0.99)
        before = observable_epsilon_ceiling(dom)
        extra = {**m.PERSONAL_AUTOMATION_FLOORS, "health": 0.10}
        original = m.PERSONAL_AUTOMATION_FLOORS
        try:
            m.PERSONAL_AUTOMATION_FLOORS = extra
            after = observable_epsilon_ceiling(dom)
        finally:
            m.PERSONAL_AUTOMATION_FLOORS = original
        assert after < before


class TestBothAreReportedAndNeitherIsInferred:
    """
    The reported-vs-applied guard. A caller must be able to see which quantity
    it is holding without recomputing it.
    """

    @pytest.mark.parametrize("capability", ARC)
    def test_the_split_reports_both(self, capability):
        r = human_eoh_per_domain(_eoh_at(capability), capability)
        assert r["machine_capability"] == capability
        assert r["epsilon"] == capability, "the historical alias still means the input"
        assert r["epsilon_observable"] == pytest.approx(
            observable_epsilon(_eoh_at(capability), capability)
        )

    @pytest.mark.parametrize("capability", ARC)
    def test_the_observed_human_fraction_is_reported_too(self, capability):
        dom = _eoh_at(capability)
        r = human_eoh_per_domain(dom, capability)
        gross = sum(dom[d] for d in _DOMAINS)
        assert r["human_fraction_observed"] == pytest.approx(r["total"] / gross)
        assert r["epsilon_observable"] == pytest.approx(
            1.0 - r["human_fraction_observed"]
        )

    @pytest.mark.parametrize("capability", ARC)
    def test_the_pipeline_reports_both(self, capability):
        r = eoh_to_teh_pipeline(epsilon=capability)
        assert r["machine_capability"] == capability
        assert 0.0 <= r["epsilon_observable"] <= 1.0
        if capability > 0.0:
            assert r["epsilon_observable"] < capability


class TestTheAliasIsOneQuantityUnderTwoNames:

    def test_either_name_gives_the_same_result(self):
        a = eoh_to_teh_pipeline(epsilon=0.90)["teh_created"]
        b = eoh_to_teh_pipeline(machine_capability=0.90)["teh_created"]
        assert a == b

    def test_supplying_both_with_different_values_raises(self):
        with pytest.raises(ValueError, match="two names for one quantity"):
            eoh_to_teh_pipeline(epsilon=0.40, machine_capability=0.90)
        with pytest.raises(ValueError, match="two names for one quantity"):
            human_eoh_per_domain(_eoh_at(0.4), 0.40, machine_capability=0.90)

    def test_supplying_both_with_the_same_value_is_allowed(self):
        """Migrating a caller should not be punished for being explicit."""
        r = eoh_to_teh_pipeline(epsilon=0.40, machine_capability=0.40)
        assert r["machine_capability"] == 0.40

    def test_supplying_neither_raises_on_the_entry_point(self):
        with pytest.raises(ValueError, match="supply epsilon"):
            eoh_to_teh_pipeline()

    def test_the_split_keeps_its_historical_default(self):
        """`human_eoh_per_domain` defaulted to 0.40 and still does."""
        assert human_eoh_per_domain(_eoh_at(0.40))["machine_capability"] == 0.40


class TestTheObservableIgnoresTheLabourConstraint:
    """
    A labour shortfall is DEFERRED, not machine-fulfilled. Computing the share
    after rationing would credit machines with obligation that simply went
    unserved — what machines take does not depend on whether the people exist to
    do the rest.
    """

    def test_rationing_does_not_move_the_observed_machine_share(self):
        free = eoh_to_teh_pipeline(epsilon=0.40)
        tight = eoh_to_teh_pipeline(epsilon=0.40, available_labor_eoh=1.0e8)
        assert tight["deferred_total"] > 0.0, "the constraint must actually bind"
        assert tight["epsilon_observable"] == pytest.approx(
            free["epsilon_observable"], rel=1e-12
        )


class TestUndefinedRatherThanZero:

    def test_zero_obligation_raises(self):
        empty = {d: 0.0 for d in _DOMAINS}
        with pytest.raises(ValueError, match="undefined"):
            observable_epsilon(empty, 0.40)
