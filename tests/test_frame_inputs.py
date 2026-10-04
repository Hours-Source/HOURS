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
    out = {k: v for k, v in r.items() if k not in ("inputs", "frame", "epsilon_reading")}
    e = r["epsilon_reading"]
    out["_eps"] = (e["value"], e["low"], e["high"])
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
        assert rows["trust_balance"]["kind"] == "derived (partly from defaults)"
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
            _dispatch(_args("scenario", "run", "labor_income_shock", "--ages", "census"))

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_a_frame_flag_the_scenario_does_not_read_is_refused(self, name):
        """`overbuild` accepted --ages and --retirement-age and printed them as
        inputs while reading population and capital only (mode 5)."""
        argv = {"--ages": ["census"], "--adult-capacity": ["2300"],
                "--retirement-age": [], "--years-in-collective": ["5"],
                "--bea-usd-per-teh": ["15.94"]}
        for flag, inp in _FLAG_INPUT.items():
            run = lambda: _scenario(name, "--frame", "us", flag, *argv[flag])  # noqa: E731
            if inp in _READS[name]:
                assert run()
            else:
                with pytest.raises(SystemExit):
                    run()

    @pytest.mark.parametrize("name", FRAME_AWARE)
    def test_the_inputs_shown_are_what_the_scenario_reads(self, name):
        rows = _scenario(name, "--frame", "us")["inputs"]
        shown = set(rows) - {"epsilon"}
        assert _READS[name] & set(_labels("--frame", "us")) <= shown
        for k in shown - _READS[name]:          # only what a read input derives from
            assert any(k in rows[r]["derived_from"] for r in shown)

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
        r = _scenario(name, "--frame", "us")
        acr = r["outcomes_across_epsilon"]
        assert acr[f"{r['epsilon_reading']['value']:.3f}"] == outcome_of(name, r)
        assert all(isinstance(o, str) for o in acr.values())

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
