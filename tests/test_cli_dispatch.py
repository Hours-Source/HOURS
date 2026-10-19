"""The CLI dispatch gate.

WHY THIS EXISTS. On 2026-08-17 an audit found THREE registered scenarios
(`demographic_shock`, `maintenance_crisis`, `recovery`) that raised TypeError on every
call, with every unit test green. The suite ran the scenario FUNCTIONS directly, and
nothing ran the DISPATCH that calls them. A registered scenario is a user-facing
promise.

This gate walks the registry itself, not a hand-kept list, so a new scenario is covered
by construction (the `OPERATIVE_LAYERS` lesson).
"""

from __future__ import annotations

import argparse

import pytest

from utils.scenario_cmd import _SCENARIOS as SCENARIOS, _dispatch, build_parser


def _default_args(name: str) -> argparse.Namespace:
    """Build the argparse namespace the CLI would produce with no flags."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_parser(sub)
    return parser.parse_args(["scenario", "run", name])


class TestEveryRegisteredScenarioRuns:
    """
    The registry is the source of truth. If `scenario list` advertises it, it
    must run at its documented defaults.
    """

    @pytest.mark.parametrize("name", sorted(SCENARIOS))
    def test_scenario_dispatches_without_error(self, name: str) -> None:
        result = _dispatch(_default_args(name))
        # dict or list — `guf_sweep` legitimately returns a sequence of rows.
        # What is being asserted is that it RAN and produced something, which is
        # exactly what the three broken scenarios could not do.
        assert isinstance(result, (dict, list)), (
            f"{name} returned {type(result).__name__}"
        )
        assert result, f"{name} returned an empty result"

    def test_the_registry_is_not_empty_and_is_covered(self) -> None:
        """Guards the gate itself: a parametrisation over an empty or shrinking registry
        would pass and test nothing. The test asserts `exercised` beside `passes`, as
        the provenance flow trace does.
        """
        assert len(SCENARIOS) >= 30

    def test_the_three_that_were_broken_are_covered_by_name(self) -> None:
        """
        Named explicitly so the regression is legible in the diff rather than
        only implied by the parametrisation. Each failed differently:
        `demographic_shock` passed an argument that does not exist;
        `maintenance_crisis` and `recovery` omitted required ones.
        """
        for name in ("demographic_shock", "maintenance_crisis", "recovery"):
            assert name in SCENARIOS
            assert isinstance(_dispatch(_default_args(name)), (dict, list))


class TestDispatchAndRegistryAgree:

    def test_every_registered_name_has_a_dispatch_branch(self) -> None:
        """A registered name with no branch falls through the dispatch chain without a
        crash, so it would pass the smoke test above while doing nothing. This test
        checks it separately.
        """
        unhandled = []
        for name in sorted(SCENARIOS):
            result = _dispatch(_default_args(name))
            if result is None:
                unhandled.append(name)
        assert not unhandled, f"registered but not dispatched: {unhandled}"

    def test_an_unregistered_name_is_refused(self) -> None:
        with pytest.raises((KeyError, ValueError, SystemExit)):
            _dispatch(_default_args("not_a_scenario"))






def test_an_empty_compound_shock_says_so_on_stderr(capsys):
    """`scenario run compound_shock` with defaults applies no shock; it read
    STABLE (2026-10-03). The hint goes to stderr so json/csv stay parseable."""
    from utils.eoh_cli import build_parser as cli_parser
    args = cli_parser().parse_args(["scenario", "run", "compound_shock", "--format", "json"])
    args.func(args)
    out = capsys.readouterr()
    assert "no component enabled" in out.err
    import json
    assert json.loads(out.out)["combined_outcome"] == "NO_SHOCK"
    args = cli_parser().parse_args(["scenario", "run", "compound_shock",
                                    "--automation-fraction-lost", "0.5"])
    args.func(args)
    assert "no component enabled" not in capsys.readouterr().err





class TestAnAcceptedEpsilonMovesTheOutput:
    """--epsilon is refused where the output does not depend on it, and where accepted
    it must move the output (author, Option A, 2026-10-04). The test runs every scenario
    and re-derives the `_EPSILON_FREE` list, so the list cannot go stale.
    """

    @pytest.mark.parametrize("name", sorted(SCENARIOS))
    def test_epsilon_is_read_or_refused(self, name: str) -> None:
        import json
        from utils.scenario_cmd import _EPSILON_FREE, _READS, FRAME_AWARE

        def run(eps: str) -> str:
            parser = argparse.ArgumentParser()
            build_parser(parser.add_subparsers(dest="cmd"))
            a = parser.parse_args(["scenario", "run", name, "--epsilon", eps])
            return json.dumps(_dispatch(a), default=str, sort_keys=True)

        refused = (name in _EPSILON_FREE or name == "feasibility"
                   or (name in FRAME_AWARE and "epsilon" not in _READS[name]))
        if refused:
            with pytest.raises(SystemExit):
                run("0.2")
        else:
            assert run("0.2") != run("0.7"), f"{name} accepts --epsilon and ignores it"


class TestCoaseanJsonIsOneDocument:
    """`coasean --format json` printed its EXPERIMENTAL banner (and the
    federation's ε/N header) into stdout, so no subcommand's output parsed
    (2026-10-14). The banner goes to stderr under json; the table form is
    byte-identical."""

    @pytest.mark.parametrize("sub", ["n1-check", "count", "federation", "simulate"])
    def test_stdout_parses_and_the_banner_is_on_stderr(self, capsys, sub):
        import json
        from utils.eoh_cli import build_parser
        a = build_parser().parse_args(["coasean", "--format", "json", sub])
        a.func(a)
        out = capsys.readouterr()
        json.loads(out.out)
        assert "EXPERIMENTAL" in out.err

    def test_the_federation_is_frame_invariant_per_capita(self, capsys):
        """It passed the 1M-reference stock beside --population."""
        import json
        from utils.eoh_cli import build_parser
        per = []
        for pop in ("1000000", "10000000"):
            a = build_parser().parse_args(["coasean", "--format", "json", "federation",
                                           "--population", pop])
            a.func(a)
            rows = json.loads(capsys.readouterr().out)
            per.append(sum(r["teh"] for r in rows) / float(pop))
        assert per[0] == pytest.approx(per[1], rel=1e-12)
