"""
The CLI dispatch gate.

WHY THIS EXISTS. On 2026-08-17 an audit found THREE registered scenarios —
`demographic_shock`, `maintenance_crisis`, `recovery` — raising TypeError on
every invocation: one passed a `population` argument the function does not take,
and two omitted required arguments entirely. They had been broken for some time
and the 2,976-test suite was blind to them, because the suite exercises the
scenario FUNCTIONS directly and nothing exercised the DISPATCH that calls them.

That is the gap: a scenario can be registered, documented in `scenario list`,
and completely unrunnable, with every unit test green. The registry is a
user-facing promise and nothing was checking it.

This gate walks the registry itself rather than a hand-maintained list, so a
scenario added tomorrow is covered by construction — the `OPERATIVE_LAYERS`
lesson, where a hand-maintained list silently fell behind on two modules.
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
        """
        Guards the gate itself: a parametrisation over an empty or shrinking
        registry would pass while testing nothing. `exercised` is asserted
        alongside `passes`, the same discipline the provenance flow trace uses.
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
        """
        A registered name with no branch falls through the dispatch chain. What
        it returns then is not a crash, so it would pass the smoke test above
        while doing nothing — hence this is checked separately.
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
    """Option A (author, 2026-10-04): --epsilon is refused where the output does
    not depend on it, and anywhere it is accepted it must move the output — the
    rule frame flags already follow. Run, not read: this re-derives the
    `_EPSILON_FREE` list on every scenario, so the list cannot go stale."""

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
