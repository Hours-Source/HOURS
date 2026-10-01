"""
The essential-domain bridge's personal column, DERIVED (2026-10-01, author:
"fix the domain mapping, as that seems to be an oversight on work that was done
to update the framework").

`scenarios/essential_bridge.personal_column` computes it from the personal
obligation's components and the repo's measured splits; `data.ESSENTIAL_BRIDGE_
PERSONAL` freezes it for core/. These pins hold the two together and hold each
declared choice in place, so a change to one is a visible act.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import ESSENTIAL_BRIDGE_PERSONAL, ESSENTIAL_DOMAINS, PERSONAL_EOH_COMPONENTS
from hours_eoh.scenarios.essential_bridge import UNATTRIBUTED, personal_column


@pytest.fixture(scope="module")
def derived():
    return personal_column()


def test_the_frozen_column_is_the_live_derivation(derived):
    assert set(ESSENTIAL_BRIDGE_PERSONAL) == set(derived["column"])
    for d, v in derived["column"].items():
        assert ESSENTIAL_BRIDGE_PERSONAL[d] == pytest.approx(v, rel=1e-12, abs=1e-15), d


def test_the_column_sums_to_one_including_the_unattributed(derived):
    assert sum(derived["column"].values()) == pytest.approx(1.0, abs=1e-12)
    assert set(derived["column"]) == set(ESSENTIAL_DOMAINS) | {UNATTRIBUTED}
    assert derived["column"][UNATTRIBUTED] > 0.0


def test_health_and_care_have_their_own_domains(derived):
    # Care is an essential domain since 2026-10-01 (author); until then it was
    # set against healthcare.
    share = {c: v["share"] for c, v in PERSONAL_EOH_COMPONENTS.items()}
    assert derived["column"]["healthcare"] == pytest.approx(share["health"], rel=1e-12)
    assert derived["column"]["care"] == pytest.approx(share["care"], rel=1e-12)


def test_nutrition_splits_by_the_floors_own_terms(derived):
    i = derived["inputs"]
    nutrition = i["component_shares"]["nutrition"]
    prod, proc = i["unassisted_production_h_yr"], i["unassisted_processing_h_yr"]
    assert derived["column"]["agriculture"] == pytest.approx(nutrition * prod / (prod + proc), rel=1e-12)
    assert derived["column"]["manufacturing"] == pytest.approx(nutrition * proc / (prod + proc), rel=1e-12)
    # The anchor NUTRITION_AUTOMATION_FLOOR adopts.
    assert i["processing_anchor"] == "FR1966"


def test_food_service_and_distribution_carry_none_of_the_obligation(derived):
    # Food service is excluded from the obligation (author, 2026-09-03) and the
    # floor's terms have no distribution stage: logistics, which held 0.20 of
    # the old column, holds none.
    assert derived["column"]["logistics"] == 0.0


def test_water_is_held_not_weighted(derived):
    # Not separable in the measured shelter frame; held (author: no new
    # placeholders), so it stays in the unattributed share.
    assert derived["column"]["water"] == 0.0


def test_shelter_splits_by_its_measured_destinations(derived):
    i = derived["inputs"]
    shelter = i["component_shares"]["shelter"]
    dest = i["shelter_destinations_h_yr"]
    total = sum(dest.values())
    assert derived["column"]["construction"] == pytest.approx(shelter * dest["structure"] / total, rel=1e-12)
    assert derived["column"]["energy"] == pytest.approx(shelter * dest["thermal"] / total, rel=1e-12)
    assert derived["column"][UNATTRIBUTED] == pytest.approx(shelter * dest["upkeep"] / total, rel=1e-12)


def test_the_bridge_in_force_uses_the_derived_column():
    from hours_eoh.core.eoh_generation import (
        UNATTRIBUTED_ESSENTIAL, _EOH_TO_ESSENTIAL_WEIGHTS_LEGACY, essential_weights)
    w = essential_weights()
    for d in ESSENTIAL_DOMAINS:
        assert w[d]["personal"] == ESSENTIAL_BRIDGE_PERSONAL[d]
    assert w[UNATTRIBUTED_ESSENTIAL]["personal"] == ESSENTIAL_BRIDGE_PERSONAL["unattributed"]
    for col in ("personal", "infrastructure", "ecological", "knowledge"):
        assert sum(row[col] for row in w.values()) == pytest.approx(1.0, abs=1e-12), col
    # The superseded table is still reachable for comparison.
    assert _EOH_TO_ESSENTIAL_WEIGHTS_LEGACY["healthcare"]["personal"] == 0.80


def test_unattributed_hours_are_not_a_shortfall():
    from hours_eoh.core.conditions import condition_iv_coverage
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.workforce import competency_reserve
    from hours_eoh.data import AGE_GROUPS, COMPETENCY_THRESHOLD
    wf = 1.0e6 * AGE_GROUPS["working_age"]["fraction"]
    res = competency_reserve({d: wf * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, wf)
    r = condition_iv_coverage(res, eoh_to_teh_pipeline(0.40))
    assert r["unattributed_eoh"] > 0.0
    assert "unattributed" not in r["per_domain"]


@pytest.mark.parametrize("eps", [0.40, 0.78])
def test_the_personal_reading_is_the_registered_personal_hours(eps):
    from hours_eoh.core.conditions import condition_iv_coverage
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.workforce import competency_reserve
    from hours_eoh.data import AGE_GROUPS, COMPETENCY_THRESHOLD
    wf = 1.0e6 * AGE_GROUPS["working_age"]["fraction"]
    res = competency_reserve({d: wf * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, wf)
    p = eoh_to_teh_pipeline(eps)
    r = condition_iv_coverage(res, p, demand="personal")
    reg_personal = p["registered_eoh_by_domain"]["personal"]
    assert r["per_domain"]["healthcare"]["demand_eoh"] == pytest.approx(
        reg_personal * ESSENTIAL_BRIDGE_PERSONAL["healthcare"], rel=1e-12)
    assert r["per_domain"]["water"]["demand_eoh"] == 0.0   # water's personal weight is held at 0


def test_with_a_care_domain_only_care_falls_short():
    # Care as its own domain (2026-10-01): healthcare is covered across the
    # arc; care, certified at the Condition IV minimum, falls just short in a
    # narrow band around ε=0.78 — in both readings.
    from hours_eoh.core.conditions import condition_iv_coverage
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.workforce import competency_reserve
    from hours_eoh.data import AGE_GROUPS, COMPETENCY_THRESHOLD
    wf = 1.0e6 * AGE_GROUPS["working_age"]["fraction"]
    res = competency_reserve({d: wf * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, wf)
    p = eoh_to_teh_pipeline(0.78)
    for reading in ("registered", "personal"):
        r = condition_iv_coverage(res, p, reading)
        assert r["domains_short"] == ["care"]
        assert 0.95 < r["per_domain"]["care"]["coverage_ratio"] < 1.0
