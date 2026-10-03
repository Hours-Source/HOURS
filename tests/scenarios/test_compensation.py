"""
scenarios/compensation — the compensating-mechanism audit (review §15): which
mechanisms can cover for each other, and where on the arc.

Pinned on the two TEH inflows: the levy and the GUF are REDUNDANT up to
ε ≈ 0.55, the levy is the SOLE mechanism to ≈ 0.97, and the top needs BOTH.
The causes are pinned beside the map, so the sentence about it is checked too
(failure mode 13).
"""

from __future__ import annotations

import pytest

from hours_eoh.land.collective import make_rural_collective, make_urban_collective
from hours_eoh.scenarios.compensation import (
    classify, compensation_map, inflow_mechanisms, minimal_sufficient_sets,
)
from hours_eoh.scenarios.stationarity import stationarity_at

URBAN = make_urban_collective(1000)


class TestTheClassifier:

    @pytest.mark.parametrize("sets,cls", [
        ([], "fails"), ([()], "unneeded"), ([("levy",)], "sole:levy"),
        ([("guf",), ("levy",)], "redundant"), ([("guf", "levy")], "joint"),
        ([("a",), ("b", "c")], "mixed"),
    ])
    def test_each_pattern(self, sets, cls):
        assert classify(sets) == cls

    def test_a_superset_of_a_passing_set_is_not_minimal(self):
        always = lambda eps, **kw: True                     # noqa: E731
        assert minimal_sufficient_sets(0.4, inflow_mechanisms(URBAN), always) == [()]
        assert classify(minimal_sufficient_sets(0.4, inflow_mechanisms(URBAN), always)) == "unneeded"


class TestTheInflowMap:

    @pytest.fixture(scope="class")
    def urban(self):
        return compensation_map(inflow_mechanisms(URBAN))

    def test_three_regimes_in_order(self, urban):
        classes = [c for c, _, _ in urban["runs"]]
        assert classes == ["redundant", "sole:levy", "joint"]
        edges = {c: (lo, hi) for c, lo, hi in urban["runs"]}
        assert edges["redundant"][0] == 0.0
        assert edges["redundant"][1] == pytest.approx(0.55, abs=0.015)
        assert edges["sole:levy"][1] == pytest.approx(0.97, abs=0.015)
        assert edges["joint"][1] == 0.99

    def test_rural_fails_at_the_top(self):
        runs = compensation_map(inflow_mechanisms(make_rural_collective(1000)))["runs"]
        assert runs[-1][0] == "fails" and runs[-1][1] == 0.99

    def test_the_map_is_frame_invariant(self, urban):
        for pop in (1.0e5, 1.0e7):
            assert compensation_map(inflow_mechanisms(URBAN), population=pop)["runs"] == urban["runs"]

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_without_either_inflow_nothing_stands_still(self, eps):
        assert not stationarity_at(eps, levy_rate=0.0)["stationary"]


class TestTheCausesPointTheRightWay:
    """The GUF falls along the arc while the guarantee rises; the levy follows
    the mint, which turns down near the top."""

    @staticmethod
    def _teh(eps):
        return stationarity_at(eps, guf_parcels=URBAN)["teh"]

    def test_the_guf_crosses_the_guarantee_at_the_redundant_edge(self):
        assert self._teh(0.55)["guf"] >= self._teh(0.55)["guarantee_owed"]
        assert self._teh(0.56)["guf"] < self._teh(0.56)["guarantee_owed"]
        assert self._teh(0.0)["guf"] > self._teh(0.99)["guf"]
        assert self._teh(0.0)["guarantee_owed"] < self._teh(0.99)["guarantee_owed"]

    def test_the_levy_crosses_the_guarantee_at_the_joint_edge(self):
        assert self._teh(0.97)["levy"] >= self._teh(0.97)["guarantee_owed"]
        assert self._teh(0.98)["levy"] < self._teh(0.98)["guarantee_owed"]
        assert self._teh(0.90)["levy"] > self._teh(0.99)["levy"]
