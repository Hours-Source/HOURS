"""
`utils/frame_inputs.py` — the inputs a frame-aware command runs on, each
labelled supplied / measured / derived / default, shared by `corridor band`,
`scenario run` and `frame show` (2026-10-03).

Not named for a package module (it covers `utils/`); listed in CLAUDE.md's
test index for that reason. The test that matters most is the ROUND TRIP: a
frame file written by `frame show --frame us --format json` must reproduce
`--frame us` in every frame-aware scenario — and must STOP reproducing it when
one of its values is edited, or the round trip is passing on shared defaults.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from utils.eoh_cli import build_parser
from utils.frame_inputs import (
    EPSILON_REFERENCE, effective_kind, label, load_frame_file,
)
from utils.scenario_cmd import _FLAG_INPUT, _READS, FRAME_AWARE, _dispatch, outcome_of

_SCENARIO_FLAGS = {
    "automation_failure": [],
    "demographic_shock": ["--shock-type", "aging", "--shock-magnitude", "0.2"],
    "ecological_spike": [],
    "compound_shock": ["--automation-fraction-lost", "0.5"],
    "capital_loss": ["--capital-fraction-lost", "0.3"],
    "overbuild": [],
    "maintenance_crisis": [],
    "recovery": [],
    "labor_income_shock": ["--income-fraction", "0.7"],
    "trust_stress": ["--periods", "3"],
    "measured_sim": ["--periods", "2"],
    "indust_baseline": [],
    "indust_recovery": ["--periods", "3"],
    "canonical_arc": ["--periods", "3"],
    "transition": ["--periods", "3"],
    "thermal_load": [],
    "arc_stability": [],
    "stationarity": [],
    "ecological_floor": [],
    "care_delay": [],
    "verification_band": [],
    "frame": [],
    "guf_magnitude": [],
    "guf_writedown": [],
    "guf_integration": [],
    "capacity_breakdown": [],
    "stationarity_drawdown": ["--periods", "3"],
    "reserve_plan": [],
    "registered_work": [],
    "mint_reach": [],
    "collective": [],
}


def _args(*argv: str):
    return build_parser().parse_args(list(argv))


def _scenario(name: str, *flags: str) -> dict:
    return _dispatch(_args("scenario", "run", name, *_SCENARIO_FLAGS[name], *flags))


def _frame_json(*flags: str) -> dict:
    buf = io.StringIO()
    a = _args("frame", "show", *flags, "--format", "json")
    with redirect_stdout(buf):
        a.func(a)
    return json.loads(buf.getvalue())


def _labels(*flags: str) -> dict:
    buf = io.StringIO()
    a = _args("frame", "show", *flags, "--format", "labels")
    with redirect_stdout(buf):
        a.func(a)
    return json.loads(buf.getvalue())


def _strip(r: dict) -> dict:
    """The scenario's numbers, without where the inputs came from."""
    # `outcomes_across_capital` re-runs a DERIVED rate's band; a file states
    # the stock itself, so it has no band to re-run (2026-10-04).
    out = {k: v for k, v in r.items()
           if k not in ("inputs", "frame", "epsilon_reading", "outcomes_across_capital",
                        "capital_source", "capital_age_source")}
    e = r["epsilon_reading"]                       # None when the scenario sweeps ε
    out["_eps"] = None if e is None else (e["value"], e["low"], e["high"])
    return out


class TestTheLabels:

    def test_with_no_frame_nothing_is_measured(self):
        rows = _labels()
        kinds = {k: r["kind"] for k, r in rows.items()}
        assert "measured" not in kinds.values() and "supplied" not in kinds.values()
        assert kinds["epsilon"] == "default" and rows["epsilon"]["value"] == EPSILON_REFERENCE
        assert all(k == "default" or k == "derived (from defaults)" for k in kinds.values())

    def test_the_us_frame_reads_the_repos_us_data(self):
        from hours_eoh.data import AGE_GROUP_RANGES, JURISDICTION_FRAMES
        from hours_eoh.reference.care_demand import population_shares
        from hours_eoh.reference.mtus_time_use import capacity_frames
        from hours_eoh.scenarios.labour_epsilon import instrument_comparison
        rows = _labels("--frame", "us")
        assert rows["population"] == {**rows["population"], "kind": "measured",
                                      "value": JURISDICTION_FRAMES["us_mainland"]["population"]}
        assert rows["age_fractions"]["kind"] == "measured"
        assert rows["age_fractions"]["value"] == pytest.approx(population_shares(AGE_GROUP_RANGES))
        caps = capacity_frames()
        latest = max(s for s in caps if s.startswith("US"))
        assert rows["adult_capacity_h_yr"]["value"] == pytest.approx(caps[latest])
        assert latest in rows["adult_capacity_h_yr"]["source"]
        c = instrument_comparison()
        assert rows["epsilon"]["kind"] == "measured"
        assert rows["epsilon"]["range"] == pytest.approx(
            [min(c["labour"]["low"], c["capital"]["low"]), max(c["labour"]["high"], c["capital"]["high"])])

    def test_a_default_ingredient_shows_in_the_kind(self):
        rows = _labels("--frame", "us")
        assert rows["labor_supply_per_capita"]["kind"] == "derived"          # all roots measured
        # A charter choice is a default, said so (2026-10-04) — not "derived
        # (partly from defaults)", which read as missing data.
        assert rows["trust_balance"]["kind"] == "default"
        assert rows["trust_balance"]["source"].startswith("charter choice")
        # BEA's stock at the conversion band's midpoint: the midpoint is the default.
        assert rows["capital_teh"]["kind"] == "derived (partly from defaults)"

    def test_effective_kind_walks_the_lineage(self):
        labs = {"a": label("measured", "x"), "b": label("default", "y"),
                "c": label("derived", "z", ("a",)), "d": label("derived", "w", ("c", "b")),
                "e": label("derived", "v", ("b", "default:K"))}
        assert effective_kind(labs, "c") == "derived"
        assert effective_kind(labs, "d") == "derived (partly from defaults)"
        assert effective_kind(labs, "e") == "derived (from defaults)"
        with pytest.raises(KeyError):
            effective_kind({"x": label("derived", "s", ("missing",))}, "x")

    def test_precedence_flag_then_file_then_frame_then_default(self, tmp_path: Path):
        f = tmp_path / "f.json"
        f.write_text(json.dumps({"population": 2.0e6}))
        assert _labels("--frame-file", str(f))["population"]["value"] == 2.0e6
        assert _labels("--frame-file", str(f), "--population", "3e6")["population"] == {
            **_labels("--frame-file", str(f), "--population", "3e6")["population"],
            "value": 3.0e6, "kind": "supplied", "source": "--population"}
        assert _labels("--frame", "us", "--population", "3e6")["population"]["kind"] == "supplied"


class TestTheFrameFile:

    @pytest.mark.parametrize("body", [
        {"populaton": 1e6},                                       # unknown key
        {"population": -1},
        {"age_fractions": {"infant": 1.0}},
        {"age_fractions": {"infant": 0.2, "child": 0.2, "working_age": 0.2, "elderly": 0.2}},
        {"epsilon": 1.5},
        {"epsilon": {"low": 0.6, "high": 0.2}},
        {"epsilon": "0.4"},
    ])
    def test_a_bad_file_is_refused_not_patched(self, tmp_path: Path, body):
        f = tmp_path / "f.json"
        f.write_text(json.dumps(body))
        with pytest.raises(SystemExit):
            load_frame_file(f)

    def test_epsilon_is_not_imputed_from_partial_data(self, tmp_path: Path):
        """Capital without a reading gets the reference ε, labelled default."""
        f = tmp_path / "f.json"
        f.write_text(json.dumps({"population": 5e6, "capital_teh": 5e10}))
        e = _labels("--frame-file", str(f))["epsilon"]
        assert e["kind"] == "default" and e["value"] == EPSILON_REFERENCE

    def test_the_template_is_standard_json(self):
        text = json.dumps(_frame_json("--frame", "us"))
        json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_the_round_trip_reproduces_the_frame(self, tmp_path: Path, name):
        f = tmp_path / "us.json"
        f.write_text(json.dumps(_frame_json("--frame", "us")))
        assert _strip(_scenario(name, "--frame-file", str(f))) == _strip(_scenario(name, "--frame", "us"))

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_and_an_edited_file_does_not(self, tmp_path: Path, name):
        """Mode 12: break the round trip and watch it fail."""
        body = _frame_json("--frame", "us")
        body["population"] = body["population"] * 0.5
        body["age_fractions"] = {"infant": 0.05, "child": 0.12, "working_age": 0.55, "elderly": 0.28}
        # and ε: per-head and ε-only scenarios rightly ignore the two above
        body["epsilon"] = 0.55
        f = tmp_path / "edited.json"
        f.write_text(json.dumps(body))
        assert _strip(_scenario(name, "--frame-file", str(f))) != _strip(_scenario(name, "--frame", "us"))


class TestScenarioRunOnAFrame:

    def test_outcomes_are_reported_at_both_ends(self):
        from hours_eoh.data import AGE_GROUP_RANGES
        from hours_eoh.reference.care_demand import population_shares
        from hours_eoh.scenarios.shocks import demographic_shock
        r = _scenario("demographic_shock", "--frame", "us")
        e = r["epsilon_reading"]
        acr = r["outcomes_across_epsilon"]
        assert set(acr) == {f"{x:.3f}" for x in (e["low"], e["value"], e["high"])}
        direct = demographic_shock(e["high"], "aging", 0.2, population=335e6,
                                   age_fractions=population_shares(AGE_GROUP_RANGES),
                                   labor_supply_per_capita=r["inputs"]["labor_supply_per_capita"]["value"])
        assert acr[f"{e['high']:.3f}"] == direct["outcome"]

    def test_a_scenario_that_reads_no_frame_refuses_frame_flags(self):
        with pytest.raises(SystemExit):
            _dispatch(_args("scenario", "run", "sweep", "--frame", "us"))
        with pytest.raises(SystemExit):
            # (labor_income_shock read no age mix until 2026-10-14; recovery's
            # backlog still does not depend on one.)
            _dispatch(_args("scenario", "run", "recovery", "--ages", "census"))

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_a_frame_flag_the_scenario_does_not_read_is_refused(self, name):
        """`overbuild` accepted --ages and --retirement-age and printed them as
        inputs while reading population and capital only (mode 5)."""
        argv = {"--ages": ["census"], "--adult-capacity": ["2300"],
                "--retirement-age": [], "--years-in-collective": ["5"],
                "--bea-usd-per-teh": ["15.94"], "--capital-stock": ["1e12"],
                "--epsilon": ["0.5"], "--thermal-obligation": ["1e8"],
                "--hectares-per-capita": ["2.0"]}
        for flag, inp in _FLAG_INPUT.items():
            run = lambda: _scenario(name, "--frame", "us", flag, *argv[flag])  # noqa: E731
            if inp in _READS[name]:
                assert run()
            else:
                with pytest.raises(SystemExit):
                    run()

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_the_inputs_shown_are_what_the_scenario_reads(self, name):
        from utils.scenario_cmd import _READS_IF_STATED
        rows = _scenario(name, "--frame", "us")["inputs"]
        shown = set(rows)
        assert ("epsilon" in shown) is ("epsilon" in _READS[name])
        assert _READS[name] & set(_labels("--frame", "us")) <= shown
        for k in shown - _READS[name] - set(_READS_IF_STATED.get(name, ())):
            # only what a read input derives from
            assert any(k in rows[r]["derived_from"] for r in shown)

    @pytest.mark.parametrize("name", ["labor_income_shock", "trust_stress", "measured_sim",
                                      "indust_baseline", "canonical_arc", "transition",
                                      "thermal_load", "stationarity"])
    def test_the_population_takers_are_frame_invariant(self, name):
        """Every scenario that takes a population is on the frame since
        2026-10-03; per head, one economy reads the same at any size. Not here:
        `arc_stability`, `care_delay`, `verification_band` and
        `ecological_floor` report ONLY per-head figures or shares, so a
        population cannot move a total and "reached" is unobservable — their
        invariance is by construction."""
        def flat(r: dict) -> dict:
            """The scalars, plus the first row of a period table, where a
            trajectory keeps its totals."""
            out = dict(r)
            for tab in ("summary_table", "trajectory", "period_results"):
                if isinstance(r.get(tab), list) and r[tab] and isinstance(r[tab][0], dict):
                    out.update({f"{tab}[0].{k}": v for k, v in r[tab][0].items()})
            return out
        runs = [(p, flat(_scenario(name, "--population", str(p)))) for p in (1e5, 1e6, 1e7)]
        nums = [k for k, v in runs[0][1].items()
                if isinstance(v, float) and not isinstance(v, bool)
                and k.rsplit(".", 1)[-1] not in ("epsilon", "epsilon_start", "epsilon_end",
                                                 "epsilon_delta", "income_fraction")]
        for k in nums:                     # a total is invariant per head, a ratio as is
            per = [r[k] / p for p, r in runs]
            raw = [r[k] for _, r in runs]
            assert (max(per) == pytest.approx(min(per), rel=1e-6, abs=1e-12)
                    or max(raw) == pytest.approx(min(raw), rel=1e-6, abs=1e-12)), k
        # and the population REACHED it: a run that ignores it is "invariant as
        # is" everywhere (found by dropping population= from one call).
        assert any(runs[0][1][k] != pytest.approx(runs[2][1][k], rel=1e-6) for k in nums)
        verdicts = [{k: v for k, v in r.items()
                     if isinstance(v, bool) or k in ("outcome", "verdict")} for _, r in runs]
        assert verdicts[0] == verdicts[1] == verdicts[2]

    def test_the_thermal_obligation_travels_with_the_frame(self):
        """It was the 1M frame's flow beside a settable population (mode 6)."""
        from hours_eoh.research.thermal_solvency import solvency_at_epsilon
        r = _scenario("thermal_load", "--frame", "us")
        from hours_eoh.data import US_MAINLAND_POPULATION
        assert r["thermal_obligation"] == solvency_at_epsilon(
            0.40, population=US_MAINLAND_POPULATION)["thermal_flow_eoh"]
        assert r["inputs"]["thermal_obligation_eoh"]["kind"] != "supplied"

    def test_off_the_frame_unread_population_and_capital_are_refused(self):
        for argv in (["sweep", "--population", "5e6"], ["use_split", "--capital-stock", "1e9"]):
            with pytest.raises(SystemExit):
                _dispatch(_args("scenario", "run", *argv))

    def test_collective_keeps_the_archetype_off_a_frame(self):
        """Without a frame it is the urban archetype; a frame INPUT flag would
        pair the archetype's parcels with another frame's people."""
        with pytest.raises(SystemExit):
            _dispatch(_args("scenario", "run", "collective", "--ages", "census"))
        assert _dispatch(_args("scenario", "run", "collective"))["population"] == 30_000.0
        assert _dispatch(_args("scenario", "run", "collective",
                               "--population", "1000000"))["population"] == 1e6

    def test_collective_on_a_frame_runs_on_the_frames_land_and_labour(self):
        """Since 2026-10-14 the entry point runs on a frame: its land, not the
        archetype's parcels; its labour supply as the hours the mint may pay;
        its age mix to both halves; and — the author's decision the same day —
        a fee priced as stationarity prices it over the frame's own parcels.
        Since 2026-10-15 (author: "ship the per-parcel half first") that fee is
        P(ε) × the private parcels, the area part NOT SUPPLIED — no longer an
        urban sample's mean. Checked against `collective_snapshot` called
        directly on the frame's own values."""
        from hours_eoh.core.simulation import make_economy_state
        from hours_eoh.land.collective import PER_PARCEL_BASIS, per_parcel_guf
        from hours_eoh.reference.parcels import contiguous_48_private_parcels
        from hours_eoh.scenarios.collective import collective_snapshot
        r = _scenario("collective", "--frame", "us")
        inp = {k: row["value"] for k, row in r["inputs"].items()}
        land_ha = inp["land_m2"] / 1e4
        assert r["land_hectares"] == pytest.approx(land_ha)
        # the PRIVATE parcels pay: the collective does not pay itself
        assert r["parcel_count"] == inp["parcel_count"] == contiguous_48_private_parcels()["central"]
        assert r["guf_basis"] == PER_PARCEL_BASIS and "NOT SUPPLIED" in r["guf_basis"]
        assert r["labour_supplied"] is True
        eps = r["epsilon_reading"]["value"]
        assert r["guf_assessed"] == per_parcel_guf(eps, inp["parcel_count"]) > 0.0
        direct = collective_snapshot(
            make_economy_state(population=inp["population"], epsilon=eps,
                               capital_stock_teh=inp["capital_teh"],
                               trust_balance=inp["trust_balance"],
                               capital_age_ratio=inp["capital_age_ratio"],
                               ecosystem_health=inp["ecosystem_health"]),
            land_hectares=land_ha, age_fractions=inp["age_fractions"],
            available_labor_eoh=inp["labor_supply_per_capita"] * inp["population"],
            guf_parcel_count=inp["parcel_count"])
        assert r["guf_revenue"] == direct["guf"]["revenue"]
        assert r["teh_created"] == pytest.approx(direct["pipeline"]["teh_created"], rel=1e-12)
        assert r["trust_end"] == pytest.approx(direct["fiscal"]["trust"]["trust_end"], rel=1e-12)

    def test_three_scenarios_mint_one_figure_on_the_us_frame(self):
        """THE SHARED PATH, READ SEVERAL WAYS (2026-10-14; the name is the
        first version's — it grew to five mints, three guarantees, two fees). `reserve_plan`
        minted 156.46B where `collective` and `automation_failure` minted
        155.78B on the same frame: its pipeline read the shipped pyramid. One
        frame, one mint, one guarantee — by equality, not tolerance."""
        c = _scenario("collective", "--frame", "us")
        r = _scenario("reserve_plan", "--frame", "us")
        a = _scenario("automation_failure", "--frame", "us")
        li = _scenario("labor_income_shock", "--frame", "us")
        s = _scenario("stationarity", "--frame", "us")
        assert (c["teh_created"] == r["mint"] == a["mint_before"] == li["baseline_income"]
                == s["here | mint"])
        assert r["guarantee_here"] == a["guarantee_before"] == s["here | guarantee owed"]
        # and ONE FEE (author, 2026-10-14: the entry point follows stationarity)
        assert c["guf_revenue"] == s["here | land fee"]

    def test_land_is_fixed_and_only_the_people_move(self):
        """Author, 2026-10-14: on a named frame the land — and its parcels —
        stay the jurisdiction's unless a frame file states more; --population
        moves only the people. Land per head is the fixed land over them."""
        a = _labels("--frame", "us")
        b = _labels("--frame", "us", "--population", "1e6")
        assert a["land_m2"]["value"] == b["land_m2"]["value"]
        assert a["parcel_count"]["value"] == b["parcel_count"]["value"]
        assert "FIXED under --population" in b["land_m2"]["source"]
        fa = _scenario("ecological_floor", "--frame", "us")
        fb = _scenario("ecological_floor", "--frame", "us", "--population", "1e6")
        ha = fa["inputs"]["hectares_per_capita"]["value"]
        hb = fb["inputs"]["hectares_per_capita"]["value"]
        from hours_eoh.data import US_MAINLAND_POPULATION
        assert hb == pytest.approx(ha * US_MAINLAND_POPULATION / 1e6, rel=1e-12)
        # the fee is ASSESSED on the land's parcels, so it does not move; what
        # is COLLECTED is bounded by what the fewer people are minted, and the
        # rest is reported unpaid (2026-10-15, author: "you can't pay what
        # isn't minted"). At 1M on US land the ceiling binds; at 335M it does not.
        ca = _scenario("collective", "--frame", "us")
        cb = _scenario("collective", "--frame", "us", "--population", "1e6")
        assert ca["parcel_count"] == cb["parcel_count"]
        assert ca["guf_assessed"] == cb["guf_assessed"]
        assert ca["guf_unpaid"] == 0.0 and ca["guf_revenue"] == ca["guf_assessed"]
        assert cb["guf_revenue"] == cb["guf_payable_ceiling"] < cb["teh_created"]
        assert cb["guf_unpaid"] == pytest.approx(cb["guf_assessed"] - cb["guf_revenue"], rel=1e-12)
        # the measured per-parcel half on a NAMED frame only: with no frame,
        # stationarity keeps its urban sample (2026-10-15)
        assert "NOT SUPPLIED" in _scenario("stationarity", "--frame", "us")["verdict"]
        assert "sample mean" in _scenario("stationarity")["verdict"]
        # and stationarity, on the same frame, collects the same fee
        sb = _scenario("stationarity", "--frame", "us", "--population", "1e6")
        assert sb["here | land fee"] == pytest.approx(cb["guf_revenue"], rel=1e-12)
        assert sb["here | land fee unpaid"] == pytest.approx(cb["guf_unpaid"], rel=1e-12)

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_the_health_flags_are_refused_where_nothing_reads_them(self, name):
        """`overbuild --frame us --ecosystem-health-before 0.4` printed the
        same figures as without it (2026-10-14): neither health flag is a
        frame input, so the unread-flag refusal could not see them."""
        from utils.scenario_cmd import _HEALTH_AFTER_READERS
        # On the US frame the fee carries the ecological work, so BEFORE
        # reaches only the spike (and compound_shock with --ecology-collapse).
        for flag, readers in (("--ecosystem-health-before", {"ecological_spike"}),
                              ("--ecosystem-health-after", _HEALTH_AFTER_READERS)):
            run = lambda: _scenario(name, "--frame", "us", flag, "0.4")  # noqa: E731
            if name in readers:
                assert run()
            else:
                with pytest.raises(SystemExit):
                    run()

    @pytest.mark.parametrize("name", ["automation_failure", "demographic_shock",
                                      "capital_loss", "ecological_spike"])
    def test_where_a_health_flag_is_accepted_it_moves_the_run(self, tmp_path: Path, name):
        """The other half: accepted means applied — on a frame whose people
        carry the ecological work, where the health reaches the labour."""
        body = {**_frame_json("--frame", "us"), "ecological_carried_by_people": True}
        f = tmp_path / "people.json"
        f.write_text(json.dumps(body))
        assert (_strip(_scenario(name, "--frame-file", str(f), "--ecosystem-health-before", "0.45"))
                != _strip(_scenario(name, "--frame-file", str(f))))
        if name == "ecological_spike":
            assert (_strip(_scenario(name, "--frame", "us", "--ecosystem-health-after", "0.1"))
                    != _strip(_scenario(name, "--frame", "us")))

    def test_without_a_frame_the_age_mix_resolves_to_the_shipped_branch(self):
        """Why passing the frame's mix unconditionally left every no-frame run
        byte-identical (checked by cmp on 19 scenarios, 2026-10-14): unstated,
        it resolves to None — the shipped-mix branch in every function — not to
        a dict equal to the shipped mix, which takes a recomputing branch."""
        from utils.frame_inputs import resolve_inputs
        v, lab = resolve_inputs(_args("scenario", "run", "arc_stability"), 0.4)
        assert v["age_fractions"] is None and lab["age_fractions"]["kind"] == "default"

    def test_feasibility_still_reads_adult_capacity(self):
        r = _dispatch(_args("scenario", "run", "feasibility", "--adult-capacity", "2300"))
        assert r

    def test_the_ecological_spike_reads_the_population(self):
        """It ran at 1M whatever --population said until 2026-10-03."""
        a = _scenario("ecological_spike", "--population", "1e5")
        b = _scenario("ecological_spike", "--population", "1e7")
        assert a["added_human_eoh"] / 1e5 == pytest.approx(b["added_human_eoh"] / 1e7, rel=1e-6)
        assert a["added_human_eoh"] != pytest.approx(b["added_human_eoh"])

    def test_overbuild_capital_travels_with_the_frame(self):
        """--capital-stock defaulted to a fixed 1.9e9 beside --population."""
        v = [_scenario("overbuild", "--population", p) for p in ("1e4", "1e6", "1e7")]
        assert len({r["verdict"] for r in v}) == 1
        per = [r["overhead"] / p for r, p in zip(v, (1e4, 1e6, 1e7))]
        assert max(per) == pytest.approx(min(per), rel=1e-9)


class TestTheFramesAgesReachTheShock:
    """Found by breaking it: with the CLI dropping the age mix, every test above
    still passed — the round trip compares two runs that both dropped it, and
    the edited file also changed the population. These bind the mix itself."""

    def test_the_applied_pyramid_is_the_frames(self):
        from hours_eoh.data import AGE_GROUP_RANGES
        from hours_eoh.reference.care_demand import population_shares
        r = _scenario("demographic_shock", "--frame", "us")
        assert r["age_fractions_before"] == pytest.approx(population_shares(AGE_GROUP_RANGES))

    @pytest.mark.parametrize("name", [n for n in FRAME_AWARE if "age_fractions" in _READS[n]])
    def test_an_ages_only_edit_moves_every_shock(self, tmp_path: Path, name):
        body = _frame_json("--frame", "us")
        body["age_fractions"] = {"infant": 0.05, "child": 0.12, "working_age": 0.55, "elderly": 0.28}
        f = tmp_path / "ages.json"
        f.write_text(json.dumps(body))
        assert _strip(_scenario(name, "--frame-file", str(f))) != _strip(_scenario(name, "--frame", "us"))


class TestTheEndUserPath:
    """Run as an institution would: CLI flags and output streams, not helpers."""

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_each_scenario_reports_its_outcome_across_epsilon(self, name):
        """The outcome key per scenario was once corrupted by a bad edit and no
        test noticed: only demographic_shock's was checked."""
        from utils.scenario_cmd import _OUTCOME_KEY
        r = _scenario(name, "--frame", "us")
        if _OUTCOME_KEY[name] is None or "epsilon" not in _READS[name]:
            assert "outcomes_across_epsilon" not in r      # swept, or no single verdict
            return
        acr = r["outcomes_across_epsilon"]
        assert acr[f"{r['epsilon_reading']['value']:.3f}"] == outcome_of(name, r)
        assert all(isinstance(o, str) for o in acr.values())

    def test_the_three_tables_name_the_same_scenarios(self):
        """A regex once rewrote `_OUTCOME_KEY`; twice in one day a substitution
        aimed at the help strings landed in a table."""
        from utils.scenario_cmd import _OUTCOME_KEY
        assert set(FRAME_AWARE) == set(_OUTCOME_KEY) == set(_READS) == set(_SCENARIO_FLAGS)
        # and the VALUES: a third substitution landed in this table (2026-10-04)
        assert all(k is None or k.isidentifier() for k in _OUTCOME_KEY.values())

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_csv_stays_parseable(self, capsys, name):
        import csv
        a = _args("scenario", "run", name, *_SCENARIO_FLAGS[name], "--frame", "us", "--format", "csv")
        a.func(a)
        out = capsys.readouterr()
        rows = list(csv.reader(io.StringIO(out.out)))
        assert rows and "Inputs" not in out.out
        assert "Inputs" in out.err                     # the labels went to stderr

    def test_a_missing_utilization_is_a_row_not_a_silence(self, tmp_path: Path):
        f = tmp_path / "us.json"
        f.write_text(json.dumps(_frame_json("--frame", "us")))
        u = _labels("--frame-file", str(f))["utilization"]
        assert u["value"] is None and u["kind"] == "default"
        assert "--utilization" in u["source"]


class TestTheRetirementRegisterByCLI:

    def test_off_unless_asked(self):
        r = _labels("--frame", "us")["retired_share"]
        assert r["value"] == 0.0 and r["kind"] == "default" and "OFF" in r["source"]

    def test_census_ages_measure_the_retired_share(self):
        from hours_eoh.data import AGE_GROUP_RANGES, RETIREMENT_REGISTER_AGE
        from hours_eoh.reference.care_demand import population_shares
        rows = _labels("--frame", "us", "--retirement-age")
        hi = AGE_GROUP_RANGES["elderly"][1]
        assert rows["retirement_age"]["value"] == RETIREMENT_REGISTER_AGE
        assert rows["retired_share"]["kind"] == "measured"
        assert rows["retired_share"]["value"] == pytest.approx(
            population_shares({"r": (RETIREMENT_REGISTER_AGE, hi)})["r"])
        assert rows["retiree_vested_fraction"]["value"] == 1.0

    def test_band_only_ages_lean_on_the_census_profile_and_say_so(self):
        rows = _labels("--retirement-age", "70")
        assert rows["retired_share"]["kind"] == "derived (partly from defaults)" or \
            rows["retired_share"]["kind"] == "derived (from defaults)"
        assert 0.0 < rows["retired_share"]["value"] < 0.17

    def test_zero_years_runs_and_vests_nothing(self):
        r = _scenario("demographic_shock", "--frame", "us", "--retirement-age",
                      "--years-in-collective", "0")
        off = _scenario("demographic_shock", "--frame", "us")
        assert r["inputs"]["retiree_vested_fraction"]["value"] == 0.0
        assert r["guarantee_before"] == off["guarantee_before"]

    def test_below_the_elderly_band_is_refused(self):
        with pytest.raises(SystemExit):
            _labels("--frame", "us", "--retirement-age", "60")

    def test_commands_that_read_no_guarantee_refuse_it(self):
        with pytest.raises(SystemExit):
            a = _args("corridor", "band", "--frame", "us", "--retirement-age")
            a.func(a)
        with pytest.raises(SystemExit):
            _dispatch(_args("scenario", "run", "labor_income_shock", "--retirement-age"))

    def test_the_register_round_trips_through_a_frame_file(self, tmp_path: Path):
        body = _frame_json("--frame", "us", "--retirement-age", "--years-in-collective", "3")
        assert {"retirement_age", "retired_share", "years_in_collective"} <= set(body)
        f = tmp_path / "ret.json"
        f.write_text(json.dumps(body))
        a = _scenario("demographic_shock", "--frame-file", str(f))
        b = _scenario("demographic_shock", "--frame", "us", "--retirement-age",
                      "--years-in-collective", "3")
        assert a["guarantee_before"] == pytest.approx(b["guarantee_before"])


def _federation(*flags: str) -> dict:
    buf = io.StringIO()
    a = _args("coasean", "--format", "json", "federation", *flags)
    with redirect_stdout(buf):
        a.func(a)
    return json.loads(buf.getvalue())


class TestTheFrameDividesIntoItsCollectives:
    """`coasean federation --frame us --split us_states` (2026-10-15): each
    state at its share of the frame, through the frame's own path."""

    _ADDS = ("population", "parcel_count", "teh_created", "guf_assessed",
             "guf_relocated_obligation")

    @pytest.mark.parametrize("eps", ["0", "0.40", "0.90", "0.99"])
    def test_the_split_adds_up_to_the_frame_and_differs_within(self, eps, tmp_path: Path):
        whole = _federation("--frame", "us", "--epsilon", eps, "--split", "us_states")
        for k in self._ADDS:
            assert whole["total"][k] == pytest.approx(whole["frame_as_one"][k], rel=1e-9), k
        # A unit's own land and parcels reach its run: the fee per head differs.
        per_head = [r["guf_assessed"] / r["population"] for r in whole["collectives"]]
        assert max(per_head) > 1.5 * min(per_head) > 0.0
        one = tmp_path / "one.json"
        one.write_text(json.dumps({"collectives": [
            {"id": "us", "population": 1, "land_hectares": 1, "parcel_count": 1}]}))
        alone = _federation("--frame", "us", "--epsilon", eps, "--split", str(one))
        assert ({k: v for k, v in alone["collectives"][0].items() if k not in ("id", "label")}
                == {k: v for k, v in alone["frame_as_one"].items() if k not in ("id", "label")})

    def test_the_cap_binds_per_collective(self):
        """At 3M people on US land the land-rich states cannot pay their fee
        while the whole frame can: a min does not add, so the split collects
        less. Reported, not reconciled."""
        r = _federation("--frame", "us", "--epsilon", "0.40", "--split", "us_states",
                        "--population", "3000000")
        assert r["frame_as_one"]["guf_unpaid"] == 0.0
        assert any(c["guf_unpaid"] > 0.0 for c in r["collectives"])
        assert r["total"]["guf_collected"] < r["frame_as_one"]["guf_collected"]

    @pytest.mark.parametrize("flags", [
        ("--split", "us_states"),                                  # no frame
        ("--frame", "us", "--split", "us_states", "--n", "3"),     # two counts
        ("--frame-file", "indust_overbuilt", "--split", "us_states"),  # another frame's
        ("--frame", "us", "--split", "BAD"),                       # a bad file
    ])
    def test_refusals(self, flags, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"collectives": [{"id": "a", "population": 0,
                                                    "land_hectares": 1, "parcel_count": 1}]}))
        with pytest.raises(SystemExit):
            _federation(*[str(bad) if f == "BAD" else f for f in flags])


class TestShippedAndConstructedFrames:
    """Frame files are the one intake (author, 2026-10-04): any country's, or a
    constructed scenario's — fictitious on purpose, to test bounds and
    collapse. `indust_overbuilt` ships, generated from the archetype module."""

    def test_every_shipped_file_is_its_source(self):
        """The census pattern: the JSON is regenerated, never hand-typed, so the
        file cannot drift from the constants it states."""
        from utils.frame_inputs import (SHIPPED_FRAMES_DIR, SHIPPED_SPLITS_DIR,
                                        shipped_frame_sources, shipped_split_sources)
        for d, sources in ((SHIPPED_FRAMES_DIR, shipped_frame_sources()),
                           (SHIPPED_SPLITS_DIR, shipped_split_sources())):
            for name, src in sources.items():
                assert json.loads((d / f"{name}.json").read_text()) == src(), name

    def test_a_shipped_frame_is_found_by_name_and_reads_supplied(self):
        lab = _labels("--frame-file", "indust_overbuilt")
        for k in ("population", "capital_teh", "ecosystem_health", "capital_age_ratio"):
            assert lab[k]["kind"] == "supplied", k
        with pytest.raises(SystemExit):
            _labels("--frame-file", "no_such_frame")

    @pytest.mark.parametrize("body", [{"ecosystem_health": 1.5}, {"capital_age_ratio": -0.1},
                                      {"ecological_carried_by_people": "yes"}, {"note": 3}])
    def test_bad_ecology_keys_are_refused(self, tmp_path: Path, body):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(body))
        with pytest.raises(SystemExit):
            load_frame_file(f)

    def test_restoration_is_derived_only_when_the_frame_declares_it(self, tmp_path: Path):
        """Gate on the declaration, not on health < 1: the US frame at the
        reference health grows no stock nobody asked for."""
        from hours_eoh.data import M2_PER_HECTARE
        from hours_eoh.scenarios.restoration_cost import deficit_obligation
        us = _labels("--frame", "us")
        assert us["restoration_eoh"]["value"] == 0.0 and us["restoration_eoh"]["kind"] == "default"
        body = _frame_json("--frame", "us")
        body.update(ecosystem_health=0.5, ecological_carried_by_people=True)
        f = tmp_path / "carried.json"
        f.write_text(json.dumps(body))
        lab = _labels("--frame-file", str(f))
        land_ha = lab["land_m2"]["value"] / M2_PER_HECTARE
        assert lab["restoration_eoh"]["value"] == deficit_obligation(land_ha, 0.5) > 0.0

    @pytest.mark.parametrize("name", ["automation_failure", "demographic_shock", "capital_loss"])
    def test_carried_ecology_reaches_the_shock(self, tmp_path: Path, name):
        """Declared carried by people, the restoration and the recurring flow
        are labour: the same frame asks more of its people than with the GUF
        carrying it."""
        body = _frame_json("--frame", "us")
        body.update(ecosystem_health=0.2)
        guf, ppl = tmp_path / "guf.json", tmp_path / "ppl.json"
        guf.write_text(json.dumps(body))
        ppl.write_text(json.dumps({**body, "ecological_carried_by_people": True}))
        a = _scenario(name, "--frame-file", str(guf))
        b = _scenario(name, "--frame-file", str(ppl))
        assert "restoration_eoh" in b["inputs"] and "restoration_eoh" not in a["inputs"]
        assert _strip(a) != _strip(b)

    def test_the_archetype_runs_the_band_and_the_shocks(self):
        for name in ("automation_failure", "capital_loss", "overbuild", "maintenance_crisis"):
            r = _scenario(name, "--frame-file", "indust_overbuilt")
            assert r["inputs"]["capital_age_ratio"]["value"] == 0.75



class TestTheFrameStateReachesTheRun:
    """The three seams of 2026-10-04 and the reads the nine claim, each by the
    output it moves (the mode-6 entry in CLAUDE.md names this class)."""

    def test_the_spike_prices_the_frames_land(self):
        from hours_eoh.data import M2_PER_HECTARE
        from hours_eoh.scenarios.restoration_cost import DEFAULT_AMORTIZATION_YEARS, deficit_obligation
        r = _scenario("ecological_spike", "--frame", "us")
        land_ha = r["inputs"]["land_m2"]["value"] / M2_PER_HECTARE
        assert r["restoration_eoh_high"] == pytest.approx(deficit_obligation(
            land_ha, r["health_before"] - r["health_after"], DEFAULT_AMORTIZATION_YEARS, "high"))

    def test_maintenance_prices_the_frames_stock_age(self, tmp_path: Path):
        body = _frame_json("--frame-file", "indust_overbuilt")
        young = tmp_path / "young.json"
        young.write_text(json.dumps({**body, "capital_age_ratio": 0.1}))
        old = _scenario("maintenance_crisis", "--frame-file", "indust_overbuilt")
        new = _scenario("maintenance_crisis", "--frame-file", str(young))
        assert old["annual_eoh"] > new["annual_eoh"]                      # the upkeep
        assert old["overbuild_margin_before"] != new["overbuild_margin_before"]  # the floor

    def test_the_frames_health_reaches_a_compound_without_a_collapse(self, tmp_path: Path):
        body = _frame_json("--frame", "us")
        f = tmp_path / "carried.json"
        f.write_text(json.dumps({**body, "ecological_carried_by_people": True}))
        sick = tmp_path / "sick.json"
        sick.write_text(json.dumps({**body, "ecological_carried_by_people": True,
                                    "ecosystem_health": 0.2}))
        a = _scenario("compound_shock", "--frame-file", str(f), "--automation-fraction-lost", "0.5")
        b = _scenario("compound_shock", "--frame-file", str(sick), "--automation-fraction-lost", "0.5")
        assert _strip(a) != _strip(b)

    @pytest.mark.parametrize("name", ["arc_stability", "stationarity"])
    def test_adult_capacity_reaches_the_arc_checks(self, name):
        a = _scenario(name, "--frame", "us")
        b = _scenario(name, "--frame", "us", "--adult-capacity", "1200")
        assert _strip(a) != _strip(b)


class TestOneAgePerFrame:
    """Author, 2026-10-04: the stock's age follows the frame — stated, or the
    canonical 0.30, labelled default — in every scenario that reads it. Before,
    `overbuild` read its margin at overbuild_check's own 0.50 and
    `maintenance_crisis` at 0.30 on the same frame."""

    @pytest.mark.parametrize("flags", [(), ("--frame", "us"), ("--frame-file", "indust_overbuilt")])
    def test_overbuild_and_maintenance_read_one_margin(self, flags):
        a = _scenario("overbuild", *flags)
        b = _scenario("maintenance_crisis", *flags)
        assert a["net_vs_autarky"] == pytest.approx(b["overbuild_margin_before"])
        assert a["inputs"]["capital_age_ratio"]["value"] == b["inputs"]["capital_age_ratio"]["value"]

    @pytest.mark.parametrize("name", ["arc_stability", "stationarity", "labor_income_shock",
                                      "trust_stress", "measured_sim", "canonical_arc",
                                      "transition", "thermal_load"])
    def test_the_frames_age_reaches_the_arc_checks(self, tmp_path: Path, name):
        """2026-10-07: resolved, labelled, and passed to neither."""
        body = _frame_json("--frame", "us")
        young = tmp_path / "young.json"
        young.write_text(json.dumps({**body, "capital_age_ratio": 0.1}))
        assert (_strip(_scenario(name, "--frame-file", str(young)))
                != _strip(_scenario(name, "--frame", "us")))



class TestTheUsAgeIsMeasured:
    """2026-10-04: `--frame us` reads its stock's age off BEA
    (`capital_retrodiction.stock_age_ratio`) instead of the canonical 0.30 —
    labelled measured, outranked by a stated value, absent elsewhere. Moving it
    0.30 → 0.594 passed the whole suite, so it is pinned here."""

    def test_the_us_frame_reads_the_function(self):
        from hours_eoh.scenarios.capital_retrodiction import stock_age_ratio
        row = _labels("--frame", "us")["capital_age_ratio"]
        assert row["kind"] == "measured"
        assert row["value"] == stock_age_ratio("government")["ratio"]

    def test_only_a_frame_with_a_reading_gets_one(self):
        assert _labels()["capital_age_ratio"]["kind"] == "default"

    def test_the_round_trip_carries_it_and_an_edit_wins(self, tmp_path: Path):
        """--frame and --frame-file are exclusive, so an institution states its
        own age by editing the US frame's file: the edit is what runs."""
        body = _frame_json("--frame", "us")
        f = tmp_path / "us.json"
        f.write_text(json.dumps(body))
        assert _labels("--frame-file", str(f))["capital_age_ratio"]["value"] == \
            _labels("--frame", "us")["capital_age_ratio"]["value"]
        f.write_text(json.dumps({**body, "capital_age_ratio": 0.42}))
        row = _labels("--frame-file", str(f))["capital_age_ratio"]
        assert (row["kind"], row["value"]) == ("supplied", 0.42)

    def test_the_data_reaches_it(self, monkeypatch):
        """Broken on purpose: age the largest covered row and the frame moves."""
        from hours_eoh.scenarios import capital_retrodiction as CR
        before = _labels("--frame", "us")["capital_age_ratio"]["value"]
        rows = [dict(r) for r in CR.AGE_ROWS]
        big = max((r for r in rows if r["life"]), key=lambda r: r["usd_b"]
                  if r["line"] != "Private residential structures and equipment" else 0)
        big["age"] *= 2
        monkeypatch.setattr(CR, "AGE_ROWS", tuple(rows))
        assert _labels("--frame", "us")["capital_age_ratio"]["value"] > before


class TestTheUsStockIsBea:
    """2026-10-04: `--frame us` reads its capital off BEA's inventory at
    `conversion_band()`'s midpoint instead of the canonical arc (742B TEH
    against ~2.7T), and re-runs each verdict at both ends of the band."""

    def test_the_stock_is_the_inventory_at_the_band_midpoint(self):
        from hours_eoh.scenarios.capital_retrodiction import conversion_band, epsilon_from_inventory
        b = conversion_band()
        from hours_eoh.data import US_MAINLAND_POPULATION
        from hours_eoh.reference.capital_inventory import BEA_POPULATION
        row = _labels("--frame", "us")["capital_teh"]
        # Per head × the frame's people: the national inventory over
        # BEA_POPULATION (the 2024 Census) × the mainland's 339.6M, 2.742T —
        # 0.11% under the national stock (2026-10-15).
        assert row["value"] == pytest.approx(
            epsilon_from_inventory(0.5 * (b["low"] + b["high"]))["capital_teh"]
            * US_MAINLAND_POPULATION / BEA_POPULATION)
        assert row["kind"].startswith("derived") and "default:conversion_band midpoint" in row["derived_from"]

    def test_both_ends_of_the_band_are_run(self):
        from hours_eoh.scenarios.capital_retrodiction import conversion_band
        b = conversion_band()
        r = _scenario("overbuild", "--frame", "us")
        assert set(r["outcomes_across_capital"]) == {f"{b['low']:.2f}", f"{b['high']:.2f}"}

    def test_the_ends_are_different_stocks(self):
        """Broken on purpose: the re-run must reach the stock, not repeat the midpoint."""
        from hours_eoh.scenarios.capital_retrodiction import conversion_band
        b = conversion_band()
        lo = _labels_at_rate(b["low"])
        hi = _labels_at_rate(b["high"])
        assert lo > hi, "a lower rate converts the same dollars into more TEH"

    @pytest.mark.parametrize("flag", [("--capital-stock", "1e12"), ("--bea-usd-per-teh", "20")])
    def test_a_stated_stock_or_rate_overrides_it(self, flag):
        r = _scenario("overbuild", "--frame", "us", *flag)
        assert "outcomes_across_capital" not in r
        assert r["inputs"]["capital_teh"]["kind"] in ("supplied", "derived")

    @pytest.mark.parametrize("rate,outside", [("7.25", True), ("19.56", False), ("38.21", True)])
    def test_a_rate_outside_the_band_is_flagged_not_refused(self, rate, outside):
        row = _labels("--frame", "us", "--bea-usd-per-teh", rate)["capital_teh"]
        assert ("OUTSIDE conversion_band()" in row["source"]) is outside
        assert row["value"] > 0

    def test_both_bea_paths_read_alike(self):
        """The default midpoint and a stated rate are the same stock times a
        rate: one label form, differing only in where the rate came from."""
        mid = _labels("--frame", "us")["capital_teh"]
        own = _labels("--frame", "us", "--bea-usd-per-teh", "15.94")["capital_teh"]
        assert mid["source"].split(" at ")[0] == own["source"].split(" at ")[0]
        assert own["kind"] == "derived" and "supplied" in own["source"]
        assert mid["kind"] == "derived (partly from defaults)"
        assert mid.get("fixed_stock") and own.get("fixed_stock")


def _labels_at_rate(rate: float) -> float:
    from utils.frame_inputs import resolve_inputs
    a = _args("frame", "show", "--frame", "us")
    a._capital_rate = rate
    return resolve_inputs(a, 0.4)[0]["capital_teh"]


class TestTheUsEnergyIsEia:
    """2026-10-04: the US frame's thermal utilization reads EIA SEDS energy
    for the contiguous 48 on the frame's own land, through the existing
    `collective_utilization` — not the Path C record its dataset flags as
    unverified (tier C), on whole-US land."""

    def test_the_contiguous_48_is_a_subtraction_within_one_table(self):
        from hours_eoh.reference import energy_use as E
        s = E.SEDS_BILLION_BTU
        for k in ("TETCB", "CLTCB", "NNTCB", "PMTCB", "NUETB"):
            assert s["US"][k] >= s["AK"][k] + s["HI"][k] >= 0.0
        for st in s.values():
            assert sum(st[k] for k in ("CLTCB", "NNTCB", "PMTCB", "NUETB")) <= st["TETCB"]
        assert 0.0 < E.contiguous_48_fossil_nuclear_share() < 1.0

    def test_the_frame_reads_it_on_its_own_land(self):
        from hours_eoh.reference.energy_use import (
            contiguous_48_energy_ej, contiguous_48_fossil_nuclear_share)
        from hours_eoh.research.thermal_path_c import collective_utilization
        r = _band_json("--frame", "us", "--delta-t-lo", "3.0")["inputs"]
        want = collective_utilization("United States", contiguous_48_energy_ej(), r["land_m2"],
                                      contiguous_48_fossil_nuclear_share(), delta_t_lo=3.0)
        assert r["utilization"] == pytest.approx(want["utilization"])

    def test_the_data_reaches_it(self, monkeypatch):
        """Broken on purpose: double the energy and the utilization doubles."""
        from hours_eoh.reference import energy_use as E
        base = _band_json("--frame", "us", "--delta-t-lo", "3.0")["inputs"]["utilization"]
        real = E.contiguous_48_energy_ej()
        monkeypatch.setattr(E, "contiguous_48_energy_ej", lambda: 2 * real)
        moved = _band_json("--frame", "us", "--delta-t-lo", "3.0")["inputs"]["utilization"]
        assert moved == pytest.approx(2 * base, rel=1e-3)

    def test_unbudgeted_says_so(self):
        assert "UNBUDGETED" in _labels("--frame", "us")["utilization"]["source"]


def _band_json(*flags: str) -> dict:
    buf = io.StringIO()
    a = _args("corridor", "band", "--format", "json", *flags)
    with redirect_stdout(buf):
        a.func(a)
    return json.loads(buf.getvalue())


class TestEveryClaimedInputMovesItsReader:
    """
    A SCENARIO MAY NOT LIST AN INPUT IT DOES NOT READ (2026-10-14). The Inputs
    block is a claim: "this run read these". Edited ALONE in a frame file on the
    US frame, each input must move every scenario that lists it — or the
    listing is the reported-not-applied shape (mode 10) and the input may be
    stranded (mode 5). The first run of this check found 15 pairs that did not
    move: ecosystem health and land in four shocks (the fee carries that work),
    the Trust in thermal_load, labour capacity in reserve_plan, land in
    labor_income_shock, and B0's health in overbuild. Exempt by NAME, each with
    its reason — never by pattern.
    """

    EDITS = {
        "age_fractions": {"age_fractions": {"infant": 0.05, "child": 0.12,
                                            "working_age": 0.55, "elderly": 0.28}},
        "capital_age_ratio": {"capital_age_ratio": 0.1},
        "trust_balance": {"trust_balance": 1.0e12},     # the frame file states none
        "parcel_count": "half",
        "adult_capacity_h_yr": {"adult_capacity_h_yr": 1500.0},
        "ecosystem_health": {"ecosystem_health": 0.4},
        "capital_teh": "half",
        "population": "half",
        "land_m2": "half",
        # 2% of the land moved from cropland (no target) to urban (the highest)
        "land_use_fractions": "shift",
    }
    #: Per-head or share reports: the population reaches them and, by design,
    #: moves no figure ("reaching, and correctly moving nothing").
    EXEMPT = {("population", "care_delay"), ("population", "verification_band"),
              ("population", "recovery")}

    @staticmethod
    def _edited(tmp_path: Path, inp: str, edit, body: dict) -> str:
        key = "land_hectares" if inp == "land_m2" else inp
        if edit == "shift":
            lu = dict(body[key])
            lu["Total cropland"] -= 0.02
            lu["Land in urban areas"] += 0.02
            new = {key: lu}
        else:
            new = ({key: body[key] * 0.5} if edit == "half" else edit)
        f = tmp_path / f"{inp}.json"
        f.write_text(json.dumps({**body, **new}))
        return str(f)

    @pytest.mark.parametrize("inp", list(EDITS))
    def test_each_listed_input_moves_its_reader(self, tmp_path: Path, inp):
        from utils.scenario_cmd import _READS_IF_STATED
        body = _frame_json("--frame", "us")
        f = self._edited(tmp_path, inp, self.EDITS[inp], body)
        readers = [n for n in FRAME_AWARE
                   if inp in set(_READS[n]) | set(_READS_IF_STATED.get(n, ()))
                   and (inp, n) not in self.EXEMPT]
        assert readers
        still = [n for n in readers
                 if _strip(_scenario(n, "--frame-file", f)) == _strip(_scenario(n, "--frame", "us"))]
        assert not still, f"{inp} is listed as read but moves nothing in {still}"

    @pytest.mark.parametrize("inp", ["ecosystem_health", "land_m2"])
    def test_where_the_people_carry_the_work_health_and_land_move_the_shocks(
            self, tmp_path: Path, inp):
        from utils.scenario_cmd import _READS_IF_PEOPLE_CARRY
        body = {**_frame_json("--frame", "us"), "ecological_carried_by_people": True}
        base = tmp_path / "people.json"
        base.write_text(json.dumps(body))
        f = self._edited(tmp_path, inp, self.EDITS[inp], body)
        for n in _READS_IF_PEOPLE_CARRY:
            if n == "compound_shock":
                continue      # needs a component enabled; its readers are the shocks'
            a = _scenario(n, "--frame-file", str(base))
            assert inp in a["inputs"], n                    # listed where it reads
            assert _strip(_scenario(n, "--frame-file", f)) != _strip(a), n
