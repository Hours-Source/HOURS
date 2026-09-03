"""
Phase 2 — per-component automation, the care contradiction's fix.

ADOPTED 2026-09-01 (author sign-off, notes/phase-2-per-component-automation.md).
`per_component` is the DEFAULT; `uniform` stays reachable and reproduces every
pre-flip number exactly — the Phase 4d/4e/4f pattern, where the superseded
policy survives under its own name so a published figure can be REPRODUCED
rather than merely disbelieved.

Discipline:
  * ε=0 is the control — with nothing automated a floor ON automation cannot
    bite, so the two responses MUST coincide there;
  * the floor is read from `data.py`, never restated;
  * an automation floor is NOT an abatability, and the two are pinned apart.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_fulfillment import (
    AUTOMATION_RESPONSES,
    eoh_to_teh_pipeline,
    human_eoh_per_domain,
    personal_human_fraction,
)
from hours_eoh.data import (
    CARE_AUTOMATION_FLOOR,
    PERSONAL_AUTOMATION_FLOORS,
    PERSONAL_EOH_COMPONENTS,
)

ARC = (0.0, 0.40, 0.99)
_DOMAINS = ("personal", "infrastructure", "ecological", "knowledge")


def _eoh() -> dict:
    return {"personal": 1.0e9, "infrastructure": 1.0e8,
            "ecological": 0.0, "knowledge": 5.0e7}


class TestTheAdoptedDefault:
    """
    ADOPTED 2026-09-01 (author sign-off). `per_component` is the default and
    `uniform` stays reachable — the Phase 4d/4e/4f pattern, where the superseded
    policy survives under its own name so a figure published before the flip can
    be REPRODUCED rather than merely disbelieved.

    This class asserted the opposite until the flip, and both halves are kept:
    the adopted default, and that the old one still reconstructs exactly.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_uniform_is_still_exactly_one_minus_epsilon(self, epsilon):
        """The superseded policy, reachable and unchanged."""
        assert personal_human_fraction(epsilon, "uniform") == 1.0 - epsilon

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_default_is_per_component_everywhere_it_is_offered(self, epsilon):
        import inspect
        for fn in (personal_human_fraction, human_eoh_per_domain,
                   eoh_to_teh_pipeline):
            default = (inspect.signature(fn)
                       .parameters["automation_response"].default)
            assert default == "per_component", fn.__name__
        r = human_eoh_per_domain(_eoh(), epsilon)
        assert r["automation_response"] == "per_component"

    @pytest.mark.parametrize("epsilon", ARC)
    def test_only_the_personal_domain_differs_from_the_old_policy(self, epsilon):
        """
        The flip touches personal EOH and nothing else — no floor is measured
        for the other three domains and none was invented.
        """
        new = human_eoh_per_domain(_eoh(), epsilon)
        old = human_eoh_per_domain(_eoh(), epsilon, automation_response="uniform")
        for d in ("infrastructure", "ecological", "knowledge"):
            assert new[d] == old[d]
        if epsilon > 0.0:
            assert new["personal"] > old["personal"]


class TestTheControlAtZeroAutomation:
    """
    THE CONTROL, and it is what makes the divergence a finding rather than an
    artefact. With nothing automated, a floor ON automation cannot bite.
    """

    def test_both_responses_coincide_exactly_at_epsilon_zero(self):
        assert personal_human_fraction(0.0, "uniform") == 1.0
        assert personal_human_fraction(0.0, "per_component") == pytest.approx(1.0)

    def test_the_pipeline_coincides_at_epsilon_zero(self):
        a = eoh_to_teh_pipeline(epsilon=0.0)["teh_created"]
        b = eoh_to_teh_pipeline(
            epsilon=0.0, automation_response="per_component"
        )["teh_created"]
        assert a == pytest.approx(b, rel=1e-12)


class TestPerComponentHonoursTheDeclaredFloors:

    def test_the_governing_equation_reproduces_by_hand(self):
        """
        Σ share_c · [f_c + (1 − f_c)(1 − ε)], computed independently from the
        data rather than from the implementation.
        """
        eps = 0.99
        expected = sum(
            float(spec["share"]) * (
                PERSONAL_AUTOMATION_FLOORS.get(name, 0.0)
                + (1.0 - PERSONAL_AUTOMATION_FLOORS.get(name, 0.0)) * (1.0 - eps)
            )
            for name, spec in PERSONAL_EOH_COMPONENTS.items()
        )
        assert personal_human_fraction(eps, "per_component") == pytest.approx(expected)

    def test_the_divergence_is_an_order_of_magnitude_at_the_top(self):
        """SIGN and MAGNITUDE-CLASS; the level moves with the share and floor."""
        u = personal_human_fraction(0.99, "uniform")
        c = personal_human_fraction(0.99, "per_component")
        assert c > u
        assert c / u > 5.0

    def test_it_reads_the_floor_and_does_not_restate_it(self):
        """
        The shadow-literal lesson. If the floor moves, this must move with it.
        """
        assert PERSONAL_AUTOMATION_FLOORS["care"] == CARE_AUTOMATION_FLOOR

    def test_only_the_personal_domain_moves(self):
        """
        Nothing measures a floor for infrastructure, ecological or knowledge,
        and inventing one would be the guessing this refuses.
        """
        a = human_eoh_per_domain(_eoh(), 0.99, automation_response="uniform")
        b = human_eoh_per_domain(_eoh(), 0.99, automation_response="per_component")
        assert b["personal"] > a["personal"]
        for d in ("infrastructure", "ecological", "knowledge"):
            assert b[d] == a[d]

    def test_the_response_is_reported_not_inferred(self):
        b = human_eoh_per_domain(_eoh(), 0.40, automation_response="per_component")
        assert b["automation_response"] == "per_component"
        assert b["personal_human_fraction"] == pytest.approx(
            personal_human_fraction(0.40, "per_component")
        )

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_fraction_stays_a_fraction_across_the_arc(self, epsilon):
        for response in AUTOMATION_RESPONSES:
            f = personal_human_fraction(epsilon, response)
            assert 0.0 <= f <= 1.0

    def test_it_is_monotone_falling_in_epsilon(self):
        for response in AUTOMATION_RESPONSES:
            vals = [personal_human_fraction(e, response)
                    for e in (0.0, 0.2, 0.4, 0.6, 0.8, 0.99)]
            assert vals == sorted(vals, reverse=True)


class TestAnAutomationFloorIsNotAnAbatability:
    """
    THE WRONG-INSTRUMENT GUARD. `abatability` is the most infrastructure can
    REMOVE — a(K), ε-free by construction (Block II). An automation floor is who
    does the work that REMAINS. Conflating them would repeat the
    SKILL_WORKING_LIFE_YEARS error, and the two tables are deliberately
    separate.
    """

    def test_the_two_tables_are_not_the_same_numbers(self):
        care = PERSONAL_EOH_COMPONENTS["care"]
        assert care["abatability"] != PERSONAL_AUTOMATION_FLOORS["care"], (
            "if these ever coincide, check it is a coincidence and not a "
            "conflation — they answer different questions"
        )

    def test_the_floors_table_covers_only_what_is_measured(self):
        """
        TWO floors now: care (a charter decision) and nutrition (adopted
        2026-09-03 from the food-system labour construction). The absence of the
        other two is still an ADMISSION, not a zero, and the constant's tag
        block says so.
        """
        assert set(PERSONAL_AUTOMATION_FLOORS) == {"care", "nutrition"}
        missing = set(PERSONAL_EOH_COMPONENTS) - set(PERSONAL_AUTOMATION_FLOORS)
        assert missing == {"shelter", "health"}, (
            "shelter and health carry no floor; adding one moves the arc the "
            "same way nutrition just did, so the shipped figures still err LOW"
        )

    def test_an_unlisted_component_reduces_to_uniform(self):
        """
        A component with no floor must behave exactly as the uniform split does.

        Written over EVERY floored component rather than over `care` alone: the
        first version hardcoded the one entry the table then had, and broke the
        moment nutrition was adopted. Summing the table cannot go stale.
        """
        eps = 0.99
        expected = 0.0
        for name, spec in PERSONAL_EOH_COMPONENTS.items():
            share = float(spec["share"])
            floor = PERSONAL_AUTOMATION_FLOORS.get(name, 0.0)
            expected += share * (floor + (1.0 - floor) * (1.0 - eps))
        assert personal_human_fraction(eps, "per_component") == pytest.approx(expected)

        unfloored = set(PERSONAL_EOH_COMPONENTS) - set(PERSONAL_AUTOMATION_FLOORS)
        assert unfloored, "the test is vacuous if every component is floored"

    def test_adding_a_floor_can_only_raise_the_human_fraction(self):
        """
        The direction that makes the shipped figure a LOWER bound: any further
        floor moves the arc the same way.
        """
        assert (personal_human_fraction(0.99, "per_component")
                > personal_human_fraction(0.99, "uniform"))


class TestItIsReachableFromTheDocumentedEntryPoint:
    """
    The stranded-parameter failure, which this repo has found FOUR times —
    `personal_standard`, `ecological_health_response`, `knowledge_base_size`,
    `restoration_obligation` — each reaching `total_eoh` and stopping at
    `eoh_to_teh_pipeline`, the path the implementation guide tells institutions
    to run.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_switch_reaches_teh_created(self, epsilon):
        a = eoh_to_teh_pipeline(
            epsilon=epsilon, automation_response="uniform"
        )["teh_created"]
        b = eoh_to_teh_pipeline(
            epsilon=epsilon, automation_response="per_component"
        )["teh_created"]
        if epsilon == 0.0:
            assert a == pytest.approx(b, rel=1e-12), "the ε=0 control"
        else:
            assert b > a, "the switch must reach the minted TEH"

    def test_an_unknown_response_raises(self):
        with pytest.raises(ValueError):
            personal_human_fraction(0.40, "nonsense")
        with pytest.raises(ValueError):
            human_eoh_per_domain(_eoh(), 0.40, automation_response="nonsense")

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            personal_human_fraction(1.5)
