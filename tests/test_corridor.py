"""
Tests for the stability corridor (research/corridor.py).

The reframed success criterion: a stable feasible band [ε_suff, ε_max], NOT ε → 1.
Covers the survival floor (E22), the invariant ceilings, corridor composition,
and stability over a horizon.

Arc coverage at ε ∈ {0.0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.research.corridor import (
    survival_floor_epsilon,
    survival_inventory,
    survival_floor,
    overbuild_floor,
    Floor,
    contestability_ceiling,
    contestability_ceiling_bare_chi,
    contestability_axes,
    thermal_ceiling,
    corridor,
    corridor_stability,
    Ceiling,
    CorridorReport,
)

ARC = [0.0, 0.40, 0.90, 0.99]
POP = 1_000_000.0
L_AVAIL = 1.0e9  # ~50% workforce × 2000 h/yr


# ---------------------------------------------------------------------------
# survival floor — E22
# ---------------------------------------------------------------------------

def test_survival_floor_zero_when_labor_covers():
    eoh = {"personal": 500.0, "infrastructure": 100.0, "ecological": 10.0, "knowledge": 1.0}
    # abundant labor covers survival → ε_suff = 0
    assert survival_floor_epsilon(eoh, available_labor_eoh=1e6) == 0.0


def test_survival_floor_positive_when_labor_short():
    eoh = {"personal": 1000.0, "infrastructure": 0.0, "ecological": 0.0, "knowledge": 0.0}
    # survival 1000, labor 400, total 1000 → (1000-400)/1000 = 0.6
    assert survival_floor_epsilon(eoh, available_labor_eoh=400.0) == pytest.approx(0.6)


@pytest.mark.parametrize("eps", ARC)
def test_survival_floor_in_unit_interval_across_arc(eps):
    es = survival_floor_epsilon(total_eoh(epsilon=eps), L_AVAIL)
    assert 0.0 <= es <= 1.0


def test_survival_floor_rejects_bad_inputs():
    with pytest.raises(ValueError):
        survival_floor_epsilon({"personal": 0.0}, available_labor_eoh=1.0)
    with pytest.raises(ValueError):
        survival_floor_epsilon({"personal": 10.0}, available_labor_eoh=-1.0)


def test_survival_floor_widening_domains_raises_it():
    eoh = {"personal": 500.0, "infrastructure": 500.0, "ecological": 0.0, "knowledge": 0.0}
    narrow = survival_floor_epsilon(eoh, 100.0, survival_domains=("personal",))
    wide = survival_floor_epsilon(eoh, 100.0, survival_domains=("personal", "infrastructure"))
    assert wide > narrow


# ---------------------------------------------------------------------------
# ceilings
# ---------------------------------------------------------------------------

def test_adopted_contestability_ceiling_nonbinding_at_defaults():
    # §8.9 three-channel test: exit is financeable at every ε in the adversarial
    # regime, so contestability does not bound the corridor at defaults.
    c = contestability_ceiling(POP, regime="increasing_returns")
    assert c["name"] == "contestability"
    assert c["binding"] is False
    assert c["epsilon_ceiling"] is None


@pytest.mark.parametrize("policy", ["dilution", "target"])
def test_adopted_contestability_ceiling_across_charter_policies(policy):
    c = contestability_ceiling(POP, regime="increasing_returns", phi_policy=policy)
    assert c["binding"] is False


def test_bare_chi_ceiling_nonbinding_when_well_capitalized():
    c = contestability_ceiling_bare_chi(POP, 5.0e11, regime="increasing_returns")
    assert c["binding"] is False
    assert c["epsilon_ceiling"] is None
    assert "SUPERSEDED" in c["status"]


def test_bare_chi_ceiling_binds_when_thin_trust():
    c = contestability_ceiling_bare_chi(POP, 5.0e10, regime="increasing_returns")
    assert c["name"] == "contestability_bare_chi"
    assert c["binding"] is True
    assert c["epsilon_ceiling"] is not None
    assert 0.0 <= c["epsilon_ceiling"] <= 0.99


def test_axes_disagree_at_thin_trust_and_the_adopted_axis_governs():
    """The migration finding, pinned.

    The retired bare-χ axis binds at thin trust; the adopted §8.9 axis does not
    bind at all. The recorded "corridor CLOSED at defaults" result came from the
    former. If this test ever starts passing with agree=True, the disagreement
    has been resolved and the corridor docs need re-reading.
    """
    cmp = contestability_axes(POP, 5.0e10, regime="increasing_returns")
    assert cmp["bare_chi"]["binding"] is True
    assert cmp["adopted"]["binding"] is False
    assert cmp["agree"] is False
    assert "AXES DISAGREE" in cmp["note"]


def test_axes_agree_when_well_capitalized():
    cmp = contestability_axes(POP, 5.0e11, regime="increasing_returns")
    assert cmp["agree"] is True
    assert cmp["adopted"]["binding"] is False
    assert cmp["bare_chi"]["binding"] is False


def test_thermal_ceiling_advisory_at_p0():
    # P0 thermal is INCONCLUSIVE or UNBUDGETED → non-binding advisory
    c = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    assert c["binding"] is False
    assert c["name"] == "thermal"


# ---------------------------------------------------------------------------
# corridor composition
# ---------------------------------------------------------------------------

def _ceiling(name: str, eps: float | None, binding: bool) -> Ceiling:
    return Ceiling(name=name, epsilon_ceiling=eps, binding=binding, status="test")


def test_corridor_open_when_no_binding_ceiling():
    rep = corridor(0.3, [_ceiling("thermal", None, False)])
    assert rep["epsilon_max"] == 1.0
    assert rep["binding_ceiling"] is None
    assert rep["feasible"] is True
    assert rep["success"] is True  # success without reaching ε=1


def test_corridor_bounded_by_tightest_ceiling():
    rep = corridor(0.3, [_ceiling("contestability", 0.7, True),
                         _ceiling("ecological", 0.55, True)])
    assert rep["epsilon_max"] == pytest.approx(0.55)
    assert rep["binding_ceiling"] == "ecological"
    assert rep["width"] == pytest.approx(0.25)
    assert rep["success"] is True


def test_corridor_closed_when_floor_exceeds_ceiling():
    # A closed corridor is a reportable result, not a bug: the survival floor sits
    # above the tightest ceiling, so no ε satisfies both. Composition-level test —
    # the ceiling is supplied, not derived, precisely because which contestability
    # axis produced it is the caller's decision (see the axes tests above).
    rep = corridor(0.52, [_ceiling("contestability", 0.29, True)])
    assert rep["feasible"] is False
    assert rep["success"] is False
    assert rep["width"] < 0.0
    assert "closed" in rep["note"]


def test_corridor_success_does_not_require_epsilon_1():
    # a feasible band topping out well below 1 is still a success
    rep = corridor(0.2, [_ceiling("thermal", 0.6, True)])
    assert rep["epsilon_max"] == pytest.approx(0.6)
    assert rep["success"] is True


def test_corridor_end_to_end_on_the_adopted_axis():
    """End-to-end on the axis that governs: the corridor is OPEN at defaults."""
    es = survival_floor_epsilon(total_eoh(epsilon=0.40), L_AVAIL)
    t = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    rep = corridor(es, [contestability_ceiling(POP), t])
    assert rep["feasible"] is True
    assert rep["success"] is True
    assert rep["binding_ceiling"] is None


def test_corridor_end_to_end_on_the_superseded_axis_still_closes():
    """The retired axis, run deliberately: thin trust still closes the corridor.

    Kept as the regression anchor for the pre-migration result so the earlier
    finding stays reproducible and attributable to the test that produced it.
    """
    es = survival_floor_epsilon(total_eoh(epsilon=0.40), L_AVAIL)
    t = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    adv = corridor(es, [contestability_ceiling_bare_chi(POP, 5.0e10), t])
    assert adv["feasible"] is False
    good = corridor(es, [contestability_ceiling_bare_chi(POP, 5.0e11), t])
    assert good["success"] is True


# ---------------------------------------------------------------------------
# stability over horizon
# ---------------------------------------------------------------------------

def _report(width: float) -> CorridorReport:
    es = 0.3
    return corridor(es, [_ceiling("x", es + width, True)])


def test_stability_stable():
    s = corridor_stability([_report(0.3), _report(0.31), _report(0.29), _report(0.3)])
    assert s["verdict"] == "STABLE"
    assert s["all_feasible"] is True


def test_stability_breached():
    s = corridor_stability([_report(0.3), _report(-0.1)])
    assert s["verdict"] == "BREACHED"
    assert s["all_feasible"] is False


def test_stability_narrowing():
    s = corridor_stability([_report(0.4), _report(0.3), _report(0.15)])
    assert s["verdict"] == "NARROWING"


def test_stability_rejects_empty():
    with pytest.raises(ValueError):
        corridor_stability([])


# ---------------------------------------------------------------------------
# The survival-floor correction (Block I, 2026-08-06)
#
# ε_suff was being computed from an inventory at the OPERATING personal standard
# — a sufficiency-shaped number — and reported as a survival floor. At the
# survival standard the floor is 0: subsistence survives without automation.
# ---------------------------------------------------------------------------

def test_survival_floor_is_zero_at_the_survival_standard():
    """The correction. Subsistence survives with no automation, as it did."""
    assert survival_floor_epsilon(survival_inventory(epsilon=0.0), L_AVAIL) == 0.0


def test_the_three_standards_give_three_different_floors():
    """All three are meaningful; only the first is a survival floor."""
    from hours_eoh.core.eoh_generation import total_eoh as _t
    surv = survival_floor_epsilon(survival_inventory(epsilon=0.0), L_AVAIL)
    oper = survival_floor_epsilon(_t(epsilon=0.0), L_AVAIL)
    suff = survival_floor_epsilon(
        _t(epsilon=0.0, personal_standard="sufficiency"), L_AVAIL)
    assert surv == 0.0
    # 0.306 → 0.2449: a lower w means the operating standard demands fewer
    # per-capita hours, so less automation is needed to reach it.
    assert oper == pytest.approx(0.25927, abs=0.005)
    # 0.530 → 0.4862: the sufficiency standard is unchanged, but a lower w means
    # fewer per-capita hours are owed, so less automation reaches it.
    # MOVED 2026-09-09 by the capital-path decision (reading (e)): an unspecified
    # capital stock resolves along the canonical arc, so the infrastructure term
    # falls at low ε and every ratio computed against total EOH moves with it.
    assert suff == pytest.approx(0.50522, abs=0.005)
    assert surv < oper < suff


@pytest.mark.parametrize("eps", ARC)
def test_survival_floor_stays_zero_across_the_arc(eps):
    """Automation only ever relieves the survival floor; it never creates one."""
    assert survival_floor_epsilon(survival_inventory(epsilon=eps), L_AVAIL) == 0.0


def test_survival_inventory_rejects_a_conflicting_standard():
    with pytest.raises(TypeError):
        survival_inventory(personal_standard="sufficiency")


def test_corridor_opens_fully_on_the_survival_floor():
    """With ε_suff = 0 and nothing binding above, the band is the whole arc."""
    es = survival_floor_epsilon(survival_inventory(epsilon=0.40), L_AVAIL)
    rep = corridor(es, [contestability_ceiling(POP),
                        thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)])
    assert rep["epsilon_suff"] == 0.0
    assert rep["width"] == pytest.approx(1.0)
    assert rep["success"] is True


# ---------------------------------------------------------------------------
# Block III — two lower bounds, not one
#
# A collective can be infeasible for two independent reasons: it cannot survive,
# or it is not worth being in. The band's floor is the max over both.
# ---------------------------------------------------------------------------

class TestTwoFloors:

    def test_scalar_floor_is_backward_compatible(self):
        rep = corridor(0.3, [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == pytest.approx(0.3)
        assert rep["binding_floor"] == "survival"

    def test_no_binding_floor_reports_none(self):
        rep = corridor([survival_floor(survival_inventory(epsilon=0.40), L_AVAIL)],
                       [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == 0.0
        assert rep["binding_floor"] is None

    def test_modest_apparatus_does_not_bind(self):
        f = overbuild_floor(1.9e9, POP)
        assert f["binding"] is False
        assert f["epsilon_floor"] == 0.0
        assert "pays at any" in f["status"]

    def test_huge_apparatus_binds_the_floor(self):
        f = overbuild_floor(1.0e11, POP)
        assert f["binding"] is True
        assert 0.0 < f["epsilon_floor"] < 1.0
        assert "worth being in only at" in f["status"]

    def test_binding_floor_is_the_max(self):
        surv = Floor(name="survival", epsilon_floor=0.20, binding=True, status="x")
        over = Floor(name="overbuild", epsilon_floor=0.55, binding=True, status="y")
        rep = corridor([surv, over], [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == pytest.approx(0.55)
        assert rep["binding_floor"] == "overbuild"

    def test_overbuild_can_close_a_corridor_survival_would_not(self):
        """The new failure mode: not 'we would die' but 'we are better off apart'."""
        surv = Floor(name="survival", epsilon_floor=0.0, binding=False, status="x")
        over = overbuild_floor(1.0e11, POP)
        rep = corridor([surv, over], [_ceiling("contestability", 0.30, True)])
        assert rep["feasible"] is False
        assert rep["binding_floor"] == "overbuild"
        assert "overbuild floor exceeds" in rep["note"]

    def test_floors_are_echoed_for_audit(self):
        floors = [survival_floor(survival_inventory(epsilon=0.40), L_AVAIL),
                  overbuild_floor(1.9e9, POP)]
        rep = corridor(floors, [_ceiling("thermal", None, False)])
        assert [f["name"] for f in rep["floors"]] == ["survival", "overbuild"]

    @pytest.mark.parametrize("eps", ARC)
    def test_arc_coherent_with_both_floors(self, eps):
        floors = [survival_floor(survival_inventory(epsilon=eps), L_AVAIL),
                  overbuild_floor(1.9e9, POP)]
        rep = corridor(floors, [contestability_ceiling(POP)])
        assert 0.0 <= rep["epsilon_suff"] <= 1.0
        assert rep["success"] is True


class TestTheBandCommandTravelsWithTheFrame:
    """`corridor band` defaulted capital (1.9e9 TEH), land (1.86e10 m²) and
    residual dissipation (2.5e9 W) to fixed 1M-collective totals beside a
    settable --population; at 1e4 the overbuild floor bound at ε 0.754 on 100x
    the capital intensity (mode 6, 2026-10-03). Unsupplied, each now resolves
    against the population, and the thermal inventory travels with it."""

    @staticmethod
    def _band(*flags: str) -> dict:
        import io, json
        from contextlib import redirect_stdout
        from utils.eoh_cli import build_parser
        args = build_parser().parse_args(["corridor", "band", "--format", "json", *flags])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    @pytest.mark.parametrize("eps", ["0.0", "0.40", "0.90", "0.99"])
    def test_the_default_verdict_is_frame_invariant(self, eps):
        reps = [self._band("--population", p, "--epsilon", eps) for p in ("1e4", "1e6", "1e7")]
        for key in ("epsilon_suff", "epsilon_max", "binding_floor", "binding_ceiling"):
            assert len({str(r[key]) for r in reps}) == 1, key
        floors = [{f["name"]: f["epsilon_floor"] for f in r["floors"]} for r in reps]
        for f in floors[1:]:
            assert f == pytest.approx(floors[0])

    def test_a_supplied_stock_is_used_as_given(self):
        """The overbuild floor can still bind: 1e12 TEH at 1M is a real overbuild."""
        r = self._band("--capital-stock", "1e12")
        assert r["binding_floor"] == "overbuild"
        assert r["epsilon_suff"] > 0.5


class TestTheBandOnARealFrame:
    """`corridor band --frame us` (2026-10-03): US population and land, Census
    ages, the BEA inventory at a stated rate, and the Path C utilization."""

    _band = staticmethod(TestTheBandCommandTravelsWithTheFrame._band)

    def test_the_frame_fills_every_input_from_the_repo(self):
        from hours_eoh.data import JURISDICTION_FRAMES, M2_PER_HECTARE
        from hours_eoh.research.thermal_path_c import all_collectives_utilization
        r = self._band("--frame", "us", "--epsilon", "0.41")
        inp, us = r["inputs"], JURISDICTION_FRAMES["us_mainland"]
        assert inp["population"] == us["population"]
        assert inp["land_m2"] == pytest.approx(us["land_hectares"] * M2_PER_HECTARE)
        assert inp["ages"] == "census"
        u = {c["name"]: c for c in all_collectives_utilization()}["United States"]["utilization"]
        assert inp["utilization"] == pytest.approx(u)
        assert "thermal_measured" in [c["name"] for c in r["ceilings"]]

    def test_the_bea_capital_is_the_inventory_at_the_rate(self):
        from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory
        r = self._band("--frame", "us", "--bea-usd-per-teh", "20")
        assert r["inputs"]["capital_teh"] == pytest.approx(
            epsilon_from_inventory(20.0)["capital_teh"])

    @pytest.mark.parametrize("flags", [
        ("--bea-usd-per-teh", "20"),
        ("--frame", "us", "--population", "1e6", "--bea-usd-per-teh", "20"),
        ("--frame", "us", "--capital-stock", "1e12", "--bea-usd-per-teh", "20"),
    ])
    def test_the_us_inventory_refuses_another_frame(self, flags):
        with pytest.raises(SystemExit):
            self._band(*flags)

    def test_the_note_drops_the_missing_iota_caveat_when_measured(self):
        assert "needs measured ι" in self._band()["note"]
        assert "needs measured ι" not in self._band("--utilization", "0.42")["note"]

    def test_a_measured_utilization_can_bind(self):
        """The measured ceiling is live, not decorative: in contact it binds."""
        r = self._band("--utilization", "1.84")
        assert r["binding_ceiling"] == "thermal_measured"

    def test_the_default_band_is_unchanged_by_the_new_flags(self):
        r = self._band()
        assert r["inputs"]["ages"] == "shipped" and r["inputs"]["utilization"] is None
        assert [c["name"] for c in r["ceilings"]] == ["contestability", "thermal"]


class TestHeadroom:
    """The band printed "no / —" with no distance to binding (2026-10-03).
    `overbuild_capital_limit` and the CLI's headroom column supply it."""

    _band = staticmethod(TestTheBandCommandTravelsWithTheFrame._band)

    @staticmethod
    def _arc_capital(eps: float = 0.40, pop: float = 1e6) -> float:
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        return resolve_capital_stock(None, eps, population=pop)

    def test_the_capital_limit_is_the_obligation_tests_crossing(self):
        from hours_eoh.core.autarky import overbuild_check
        from hours_eoh.research.corridor import overbuild_capital_limit
        k = overbuild_capital_limit(self._arc_capital(), 1e6)
        assert k is not None and k > self._arc_capital()
        assert overbuild_check(k * 0.999, 1e6, epsilon=0.0)["obligation_test"]
        assert not overbuild_check(k * 1.001, 1e6, epsilon=0.0)["obligation_test"]

    def test_it_is_where_the_floor_starts_to_bind(self):
        from hours_eoh.research.corridor import overbuild_capital_limit, overbuild_floor
        k = overbuild_capital_limit(self._arc_capital(), 1e6)
        assert not overbuild_floor(k * 0.999, 1e6)["binding"]
        assert overbuild_floor(k * 1.001, 1e6)["binding"]

    def test_the_limit_is_per_capita_invariant_and_start_free(self):
        from hours_eoh.research.corridor import overbuild_capital_limit
        per = [overbuild_capital_limit(s * p, p) / p
               for p in (1e5, 1e6, 335e6) for s in (100.0, 2_400.0, 10_000.0)]
        assert max(per) == pytest.approx(min(per), rel=1e-5)

    def test_none_once_the_stock_already_fails(self):
        from hours_eoh.research.corridor import overbuild_capital_limit
        assert overbuild_capital_limit(1e12, 1e6) is None

    def test_the_band_reports_each_distance(self):
        from hours_eoh.data import THERMAL_U_FLOOR
        from hours_eoh.research.corridor import (
            DEFAULT_SURVIVAL_DOMAINS, overbuild_capital_limit, survival_inventory)
        from hours_eoh.scenarios.feasibility import labor_supply_per_capita
        h = self._band("--utilization", "0.25")["headroom"]
        need = sum(survival_inventory(population=1e6, epsilon=0.40)[d]
                   for d in DEFAULT_SURVIVAL_DOMAINS)
        assert h["survival"]["labour_cover"] == pytest.approx(labor_supply_per_capita() * 1e6 / need)
        # the frame's labelled default age (2026-10-04), not overbuild_check's own 0.50
        from hours_eoh.data import CANONICAL_CAPITAL_AGE_BASE, ECOSYSTEM_HEALTH_DEFAULT
        assert h["overbuild"]["capital_limit_teh"] == pytest.approx(overbuild_capital_limit(
            self._arc_capital(), 1e6, capital_age_ratio=CANONICAL_CAPITAL_AGE_BASE,
            ecosystem_health=ECOSYSTEM_HEALTH_DEFAULT))
        assert h["thermal_measured"]["to_exposure"] == pytest.approx(THERMAL_U_FLOOR / 0.25)
        assert h["thermal_measured"]["to_contact"] == pytest.approx(4.0)





def test_one_threshold_drives_both_thermal_rows():
    """`--delta-t-lo` reached only Path C at first; P0 kept its own default."""
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.research.corridor import thermal_ceiling
    band = TestTheBandCommandTravelsWithTheFrame._band
    for dt in ("2.0", "3.0", "4.0"):
        r = band("--delta-t-lo", dt)
        p0 = next(c for c in r["ceilings"] if c["name"] == "thermal")
        inp = r["inputs"]
        assert p0 == thermal_ceiling(
            inp["land_m2"], inp["phi_other_w"], epsilon=0.40,
            eoh_by_domain=total_eoh(epsilon=0.40, population=inp["population"]),
            delta_t_lo=float(dt))
    assert len({str(band("--delta-t-lo", d)["ceilings"]) for d in ("2.0", "4.0")}) == 2


class TestTheEchoAndTheWarning:
    """2026-10-03: a ceiling that binds AT the current ε reports the input back
    (the echo), and no budget is a warning with a direction, not a bound."""

    _band = staticmethod(TestTheBandCommandTravelsWithTheFrame._band)

    def test_json_says_when_the_ceiling_is_the_current_epsilon(self):
        """Data, not wording: json readers need the flag (it was table-only)."""
        assert self._band("--utilization", "1.5", "--epsilon", "0.41")["epsilon_max_is_current"]
        assert not self._band("--utilization", "0.25")["epsilon_max_is_current"]

    def test_the_us_frame_is_open_with_a_directed_warning(self):
        r = self._band("--frame", "us", "--epsilon", "0.41")
        tm = next(c for c in r["ceilings"] if c["name"] == "thermal_measured")
        if r["inputs"]["thermal_zone"] == "determinate_unbudgeted":
            assert not tm["binding"] and "decarbonise" in tm["status"]
            assert r["binding_ceiling"] is None
            assert "a warning with a direction" in r["note"]
            assert r["headroom"]["thermal_measured"]["regime"] == "unbudgeted"


class TestTheEpsilonReading:
    """`--frame us` ran at the 0.40 reference silently (2026-10-03). Unsupplied,
    ε now comes from the frame's two instruments as a point ± margin, the band
    is checked at both ends, and with no reading the default is labelled."""

    _band = staticmethod(TestTheBandCommandTravelsWithTheFrame._band)

    def test_the_frame_reads_both_instruments(self):
        from hours_eoh.scenarios.labour_epsilon import instrument_comparison
        c = instrument_comparison()
        lo = min(c["labour"]["low"], c["capital"]["low"])
        hi = max(c["labour"]["high"], c["capital"]["high"])
        e = self._band("--frame", "us")["epsilon_reading"]
        assert (e["low"], e["high"]) == pytest.approx((lo, hi))
        assert e["value"] == pytest.approx((lo + hi) / 2)
        assert e["margin"] == pytest.approx((hi - lo) / 2)
        assert c["verdict"] in e["source"]
        assert isinstance(e["verdict_holds_across_range"], bool)

    def test_a_stated_rate_narrows_the_capital_arm_to_it(self):
        from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory
        e = self._band("--frame", "us", "--bea-usd-per-teh", "15.94")["epsilon_reading"]
        assert e["instruments"]["capital"] == pytest.approx(
            [epsilon_from_inventory(15.94)["epsilon"]] * 2)

    def test_a_supplied_epsilon_is_used_as_given(self):
        e = self._band("--frame", "us", "--epsilon", "0.33")["epsilon_reading"]
        assert e["value"] == 0.33 and e["margin"] == 0.0
        assert e["kind"] == "supplied" and e["source"] == "--epsilon"

    def test_without_a_reading_the_default_is_labelled(self):
        from utils.frame_inputs import EPSILON_REFERENCE
        e = self._band()["epsilon_reading"]
        assert e["value"] == EPSILON_REFERENCE and e["margin"] is None
        assert e["kind"] == "default"
        assert e["source"].startswith("EPSILON_REFERENCE")

    def test_the_inventory_is_taken_at_the_reading(self):
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        r = self._band("--frame", "us")
        e, inp = r["epsilon_reading"], r["inputs"]
        assert inp["capital_teh"] == pytest.approx(
            resolve_capital_stock(None, e["value"], population=inp["population"]))


def test_instrument_comparison_reads_the_conversion_band():
    """The default capital rates were rounded copies of the band's ends plus a
    hand midpoint; three rates are kept because they set the grid's 18 cells."""
    from hours_eoh.scenarios.capital_retrodiction import conversion_band
    from hours_eoh.scenarios.labour_epsilon import instrument_comparison
    b = conversion_band()
    c = instrument_comparison()
    assert tuple(c["capital"]["rates"]) == pytest.approx(
        (b["low"], 0.5 * (b["low"] + b["high"]), b["high"]))
    assert c["grid"]["cells_total"] == 18


@pytest.mark.parametrize("flags", [
    ("--frame", "us", "--bea-usd-per-teh", "15.94"),
    ("--frame", "us"),
])
def test_a_divergent_reading_is_labelled_a_disagreement(flags):
    """The margin is labelled by the instruments' OWN verdict: a disagreement
    when DIVERGENT, a span otherwise (the `margin_kind` json readers get)."""
    r = TestTheBandCommandTravelsWithTheFrame._band(*flags)
    e = r["epsilon_reading"]
    divergent = e["instruments"]["verdict"] == "DIVERGENT"
    assert e["margin_kind"] == ("disagreement" if divergent else "span")
