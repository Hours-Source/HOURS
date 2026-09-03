"""
Tests for scenarios/feasibility.py — the labor-feasibility ceiling.

The headline assertion is uncomfortable and deliberately so: on the repo's own
constants, ε = 0 is not a feasible state. These tests pin that, pin the
arithmetic that produces it, and pin the direction of every lever so the result
cannot be quietly tuned away without a test going red.

Arc coverage at ε ∈ {0.0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.data import AGE_GROUPS, H_REF, PERSONAL_EOH_BASE
from hours_eoh.scenarios.feasibility import (
    SUBSISTENCE_ADULT_SHARE_BAND,
    SUBSISTENCE_CAPACITY_BAND,
    age_weight_mean,
    feasibility_check,
    feasible_epsilon,
    identify_base,
    implied_human_hours,
    labor_supply_per_capita,
    over_determination_report,
)

ARC = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# the age weighting — the factor a naive test would miss
# ---------------------------------------------------------------------------

def test_age_weight_mean_matches_shipped_groups():
    assert age_weight_mean() == pytest.approx(1.3528)


def test_base_is_per_equivalent_not_per_capita():
    """The base is per working-age-EQUIVALENT: at 1000 it asserts 1475 h/p·yr."""
    per_capita = PERSONAL_EOH_BASE * age_weight_mean()
    assert per_capita == pytest.approx(PERSONAL_EOH_BASE * 1.3528)
    assert per_capita > PERSONAL_EOH_BASE
    c = feasibility_check(epsilon=0.0)
    assert c["personal_demand_per_capita"] == pytest.approx(per_capita)


def test_age_weighting_raises_demand_without_raising_supply():
    """Infant/elderly weight is caregiver labour — adults still supply all of it."""
    flat = {k: {**v, "eoh_weight": 1.0} for k, v in AGE_GROUPS.items()}
    assert age_weight_mean(flat) < age_weight_mean()
    # supply depends only on capacity × share, never on the weights
    assert labor_supply_per_capita(2000.0, 0.6) == pytest.approx(1200.0)


# ---------------------------------------------------------------------------
# supply side
# ---------------------------------------------------------------------------

def test_supply_is_capacity_times_share():
    assert labor_supply_per_capita(2000.0, 0.55) == pytest.approx(1100.0)


def test_supply_defaults_to_the_models_own_working_age_share():
    assert labor_supply_per_capita(2000.0) == pytest.approx(
        2000.0 * AGE_GROUPS["working_age"]["fraction"]
    )


def test_supply_rejects_bad_inputs():
    for cap, share in [(0.0, 0.6), (-1.0, 0.6), (2000.0, 0.0), (2000.0, 1.5)]:
        with pytest.raises(ValueError):
            labor_supply_per_capita(cap, share)


# ---------------------------------------------------------------------------
# THE FINDING — self-consistency fails on the repo's own constants
# ---------------------------------------------------------------------------

def test_epsilon_zero_is_infeasible_on_the_repos_own_constants():
    """No external data: H_REF × workforce_fraction vs PERSONAL_EOH_BASE."""
    c = feasibility_check(adult_capacity_h_yr=float(H_REF), adult_share=0.5,
                          epsilon=0.0)
    # 1000.0 until 2026-09-02, when H_REF moved 2000 -> 2080: the old value had
    # a two-week leave policy baked into a stated normalizer, and the base is
    # now the policy-free calendar. Supply rises 4%, which LOOSENS the test —
    # so the finding surviving is worth more than it was before.
    assert c["supply_per_capita"] == pytest.approx(1040.0)
    assert c["feasible"] is False
    # 2.29 at PERSONAL_EOH_BASE = 1500; 1.55 after the 2026-08-06 reprice to
    # 1000; 1.4404 before the H_REF move. Still over-determined at every one of
    # them — three independent changes in the loosening direction have narrowed
    # the gap and none has closed it.
    assert c["demand_supply_ratio"] == pytest.approx(1.3830, rel=0.01)


def test_implied_ceiling_is_far_below_the_shipped_base():
    c = feasibility_check(adult_capacity_h_yr=float(H_REF), adult_share=0.5,
                          epsilon=0.0)
    # The ceiling is (L − R)/w. R, the non-personal requirement, grew when Block
    # K-IV put knowledge on its measured footing, so the ceiling fell
    # 626.6 → 618.3 → 674.47. The SUPPLY term L had never moved until
    # 2026-09-02, when H_REF went 2000 → 2080 and lifted it 4%: 674.47 → 705.60.
    # That is the first time this ceiling has risen, and it is still 29% below
    # the shipped base.
    assert c["implied_base_ceiling"] == pytest.approx(705.60, rel=0.01)
    # > 1.5 until the elderly revalue; 1.42 still means the shipped base is
    # 42% above what the labour supply can serve at ε=0.
    assert c["base_overshoot"] > 1.35


def test_supply_side_resolution_demands_an_implausible_working_day():
    """The other way to close it, priced so it can be judged."""
    c = feasibility_check(adult_capacity_h_yr=float(H_REF), adult_share=0.6,
                          epsilon=0.0)
    assert c["hours_per_adult_required"] == pytest.approx(2400.63, rel=0.01)
    # 7.08 h/day before the elderly revalue, 6.33 after — still every day of
    # the year with no rest days, which is the point.
    assert c["hours_per_adult_required"] / 365.0 > 6.0  # h/day, no rest days


def test_report_flags_over_determination():
    r = over_determination_report()
    assert r["over_determined"] is True
    assert "OVER-DETERMINED" in r["verdict"]
    assert "cannot both hold" in r["verdict"]


# ---------------------------------------------------------------------------
# the subsistence sweep — generous at the top end, still infeasible
# ---------------------------------------------------------------------------

def test_subsistence_sweep_clears_only_at_implausible_labour_budgets():
    """
    TWO cases now clear, and which two is the whole finding.

    History, because the sign of each move matters:
      PERSONAL_EOH_BASE 1500   no case feasible
      repriced to 1000         exactly one clears, ratio 0.99, at 2,600 h/yr
                               adult capacity — ABOVE the modern full-time
                               reference — and a 0.60 adult share
      KNOWLEDGE_EOH_BASE       that case now reads 1.0019 and fails
      AGE_GROUPS elderly       w 1.475 → 1.3528 cuts personal demand 11.76%
      2.5 → 1.48 (2026-08-10)  and TWO cases clear, best ratio 0.889

    The over-determination is REDUCED, not resolved, and the two cases that
    clear are the two most generous corners in the sweep: 2,600 h/yr adult
    capacity (7.1 h/day every day, above the modern full-time reference) at
    both adult shares. Every case at a plausible labour budget still fails,
    and the central reading — 1,387 demand against 1,000 supply, ratio 1.39 —
    is still infeasible.

    The honest statement moved from "infeasible everywhere in the sweep" to
    "feasible only where the labour budget is implausible".
    """
    # 2026-09-01: ONE survivor, not two. AGE_WEIGHT_CHILD took the MTUS
    # self-maintenance measurement for ages 6-14 (1.5 -> 1.82), which raises
    # per-capita demand, and the second survivor stopped clearing. The finding
    # hardened rather than moved: fewer corners clear than before.
    r = over_determination_report()
    feasible = [c for c in r["subsistence_cases"] if c["feasible"]]
    assert len(feasible) == 1, [c["supply_per_capita"] for c in feasible]
    # The survivor sits at the top of the capacity band, not in its middle.
    for case in feasible:
        assert case["supply_per_capita"] > 1_400.0
    assert r["best_ratio"] == pytest.approx(0.9233, abs=0.01)
    assert r["worst_ratio"] > 2.0


def test_sweep_covers_a_capacity_above_the_modern_reference():
    """The test must not rest on a stingy labour budget.

    THE SOFTENING IS WITHDRAWN (2026-09-01). The 2026-08-10 elderly revalue had
    made the most generous corner CLEAR, and this test was rewritten then to
    assert that. AGE_WEIGHT_CHILD taking the MTUS measurement for ages 6-14
    reverses it: at 2,600 h/yr per adult — 7.1 hours every day of the year with
    no rest days — and the most favourable adult share, subsistence STILL does
    not clear. Ratio 1.0073, only just over, which is why it flipped on a 3.6%
    demand change and why the ORDERING is asserted rather than the level.
    """
    assert max(SUBSISTENCE_CAPACITY_BAND) > 2080.0
    generous = feasibility_check(adult_capacity_h_yr=max(SUBSISTENCE_CAPACITY_BAND),
                                 adult_share=min(SUBSISTENCE_ADULT_SHARE_BAND),
                                 epsilon=0.0)
    assert generous["feasible"] is False
    assert generous["demand_supply_ratio"] > 1.0
    # And it is CLOSE — a corner that fails by 0.7% is not a robust failure,
    # so the claim is that nothing plausible clears, not that nothing can.
    assert generous["demand_supply_ratio"] < 1.05
    # The capacity it would need is not a working year anyone observes.
    assert max(SUBSISTENCE_CAPACITY_BAND) / 365.0 > 7.0

    # At the repo's own labour constants the answer is still no.
    shipped = feasibility_check(epsilon=0.0)
    assert shipped["feasible"] is False


def test_implied_ceiling_band_brackets_the_user_estimate():
    """A per-capita ceiling of ~1,000–1,300 h/person·yr, as the hand arithmetic gives.

    Expressed as PERSONAL_EOH_BASE (per working-age-equivalent) that is the
    ceiling band ÷ 1.475 — which is why the two figures look different.
    """
    r = over_determination_report()
    lo, hi = r["ceiling_band"]
    # 387.8–998.0 post-K-IV (was 390–1006): the whole band shifted down ~0.8%
    # as the non-personal requirement grew. The conclusion is unchanged.
    assert 380.0 < lo < 450.0
    assert 1050.0 < hi < 1200.0
    # per-capita form, which is what the hand estimate produces
    assert 1400.0 < hi * age_weight_mean() < 1550.0


# ---------------------------------------------------------------------------
# lever directions — the result must respond correctly, not be hard-coded
# ---------------------------------------------------------------------------

def test_ratio_falls_as_capacity_rises():
    ratios = [feasibility_check(adult_capacity_h_yr=c, adult_share=0.6,
                                epsilon=0.0)["demand_supply_ratio"]
              for c in (1200.0, 1800.0, 2600.0)]
    assert ratios == sorted(ratios, reverse=True)


def test_lowering_the_base_restores_feasibility():
    """The instrument discriminates: a small enough base passes."""
    assert feasibility_check(2000.0, 0.5, 0.0, personal_base=1500.0)["feasible"] is False
    assert feasibility_check(2000.0, 0.5, 0.0, personal_base=500.0)["feasible"] is True


def test_ceiling_is_the_break_even_base():
    """Setting the base to the implied ceiling lands exactly on feasibility."""
    c = feasibility_check(2000.0, 0.5, 0.0)
    at_ceiling = feasibility_check(2000.0, 0.5, 0.0,
                                   personal_base=c["implied_base_ceiling"])
    assert at_ceiling["feasible"] is True
    assert at_ceiling["demand_supply_ratio"] == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# ε-coherence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", ARC)
def test_arc_coherent(eps):
    c = feasibility_check(2000.0, 0.5, epsilon=eps)
    for k in ("supply_per_capita", "total_demand_per_capita",
              "demand_supply_ratio", "implied_base_ceiling"):
        assert math.isfinite(c[k]) and c[k] >= 0.0


def test_ratio_is_monotone_decreasing_in_epsilon():
    """Machines take share; humans carry (1−ε). ε=0 is the hardest test."""
    ratios = [feasibility_check(2000.0, 0.5, epsilon=e)["demand_supply_ratio"]
              for e in ARC]
    assert ratios == sorted(ratios, reverse=True)
    assert ratios[0] > 1.0 and ratios[-1] < 1.0


def test_feasibility_crosses_over_within_the_arc():
    c0 = feasibility_check(2000.0, 0.5, epsilon=0.0)
    c9 = feasibility_check(2000.0, 0.5, epsilon=0.90)
    assert c0["feasible"] is False and c9["feasible"] is True


def test_feasible_epsilon_is_the_crossover():
    e = feasible_epsilon(2000.0, 0.5)
    assert 0.30 < e < 0.45   # 0.58 before the reprice, 0.38 after
    just_below = feasibility_check(2000.0, 0.5, epsilon=e - 0.01)
    just_above = feasibility_check(2000.0, 0.5, epsilon=min(e + 0.01, 0.99))
    assert just_below["feasible"] is False
    assert just_above["feasible"] is True


def test_closed_form_understates_the_crossover():
    """Automation creates infrastructure demand as well as relieving demand.

    The naive ε_feas = 1 − L/D(0) treats the inventory as fixed. It is not:
    infrastructure and knowledge EOH both rise with ε, so the true crossover sits
    above the linear estimate. Pinned because the closed form is the obvious
    shortcut and it is wrong in a specific direction.
    """
    d0 = feasibility_check(2000.0, 0.5, epsilon=0.0)
    naive = 1.0 - d0["supply_per_capita"] / d0["total_demand_per_capita"]
    actual = feasible_epsilon(2000.0, 0.5)
    assert actual > naive
    # K-IV WIDENED this gap from 0.024 to 0.080, strengthening the test's point:
    # knowledge EOH is now a materially ε-growing term, so treating the
    # inventory as fixed understates the crossover by more than it used to.
    assert naive == pytest.approx(0.3057, abs=0.005)
    # 0.441 at the K-IV anchor; 0.425 after the Finding-E re-anchor. The CLAIM
    # is the gap against the naive closed form (0.360), which the smaller
    # non-personal load narrows without closing.
    # crossover 0.425 → 0.335: less personal demand to automate away, so the
    # arc reaches feasibility earlier.
    assert actual == pytest.approx(0.36795, abs=0.005)
    assert actual - naive > 0.05


def test_feasible_epsilon_returns_zero_when_already_feasible():
    assert feasible_epsilon(2000.0, 0.5, personal_base=300.0) == 0.0


def test_feasible_epsilon_agrees_with_the_corridor_survival_floor():
    """Cross-check against the instrument that has been reporting this all along.

    corridor.survival_floor_epsilon scopes survival to the personal domain only,
    so it sits just below this module's total-demand figure. Both say the same
    thing: 'subsistence' needs automation.
    """
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.research.corridor import survival_floor_epsilon
    corridor_floor = survival_floor_epsilon(total_eoh(epsilon=0.0), 1.0e9)
    ours = feasible_epsilon(2000.0, 0.5)
    assert corridor_floor > 0.0
    assert corridor_floor < ours
    # The gap widened 0.08 → 0.137 with Block K-IV, and necessarily so: the
    # corridor floor is scoped to the PERSONAL domain alone, while this module
    # is total-demand, and K-IV grew a NON-personal domain. The two instruments
    # measure different things and should diverge exactly here. Both still say
    # the same thing — subsistence needs automation.
    assert ours - corridor_floor < 0.20


def test_rejects_bad_epsilon_and_population():
    with pytest.raises(ValueError):
        feasibility_check(epsilon=1.0)
    with pytest.raises(ValueError):
        feasibility_check(epsilon=-0.1)
    with pytest.raises(ValueError):
        feasibility_check(population=0.0)


# ---------------------------------------------------------------------------
# identification — the non-circular route
# ---------------------------------------------------------------------------

def test_identity_recovers_the_base_from_M_and_H():
    """B = (M + H − R)/w, with M B-free and H measured. No circularity."""
    r = identify_base(machine_eoh_per_capita=265.6,
                      observed_human_hours_per_capita=613.2)
    # 536.2 post-K-IV (was 544.0): R rises, so B = (M + H − R)/w falls. Still
    # comfortably inside the independent supply-ceiling band, which is the
    # point of the two-instrument agreement.
    assert r["implied_base"] == pytest.approx(587.0538, abs=2.0)
    assert r["implied_epsilon"] == pytest.approx(0.302, abs=0.005)


def test_identified_base_lands_inside_the_feasibility_band():
    """Two independent routes agree: supply ceiling and accounting identity."""
    r = identify_base(265.6, 613.2)
    band = over_determination_report()["ceiling_band"]
    assert band[0] < r["implied_base"] < band[1]
    assert r["implied_base"] < PERSONAL_EOH_BASE  # both land far below shipped


def test_epsilon_is_a_by_product_not_an_input():
    """ε = M/(M+H) uses no B at all — which is why the circle is broken."""
    a = identify_base(265.6, 613.2)
    b = identify_base(265.6, 613.2, residual_per_capita=0.0)
    assert a["implied_epsilon"] == pytest.approx(b["implied_epsilon"])
    assert a["implied_base"] != pytest.approx(b["implied_base"])


def test_identification_is_a_lower_bound_under_deficit():
    """Unserved obligation raises true B, so the identity under-reads.

    Adding 400 h/person·yr of previously-unserved obligation to the served total
    is what a deficit correction looks like; B rises by that ÷ w.
    """
    served_only = identify_base(265.6, 613.2)["implied_base"]
    with_deficit = identify_base(265.6, 613.2 + 400.0)["implied_base"]
    assert with_deficit > served_only
    assert with_deficit - served_only == pytest.approx(400.0 / age_weight_mean())
    assert identify_base(265.6, 613.2)["assumes_zero_deficit"] is True


def test_identification_rejects_bad_inputs():
    with pytest.raises(ValueError):
        identify_base(-1.0, 600.0)
    with pytest.raises(ValueError):
        identify_base(200.0, -1.0)
    with pytest.raises(ValueError):
        identify_base(200.0, 600.0, population=0.0)


# ---------------------------------------------------------------------------
# the overidentifying test — a claim time-use data can refute
# ---------------------------------------------------------------------------

def test_shipped_base_predicts_an_unobserved_working_day():
    """B=1500 predicts 7.1 h/adult/day of entropy labour at advanced capital."""
    p = implied_human_hours(machine_eoh_per_capita=741.4, personal_base=1500.0)
    assert p["human_per_adult_day"] == pytest.approx(6.28, abs=0.2)


def test_predicted_hours_fall_as_capital_rises():
    days = [implied_human_hours(m, personal_base=1500.0)["human_per_adult_day"]
            for m in (102.9, 265.6, 741.4)]
    assert days == sorted(days, reverse=True)


def test_a_lower_base_predicts_observable_hours():
    """The instrument discriminates: B≈600 predicts a day time-use could confirm."""
    p = implied_human_hours(machine_eoh_per_capita=265.6, personal_base=600.0)
    assert 2.0 < p["human_per_adult_day"] < 4.0


def test_prediction_is_never_negative():
    p = implied_human_hours(machine_eoh_per_capita=1e6, personal_base=600.0)
    assert p["human_per_capita"] == 0.0
