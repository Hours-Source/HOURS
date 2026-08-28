"""
Insensitivity tests for the three numerics-only tolerances (2026-08-28).

THESE ARE A DIFFERENT CLASS FROM A PIN, and conflating them would be an error.
A 2026-08-28 mutation sweep reported `_STALL_TOL_TEH`, `_RATCHET_STEP` and
`_CONVERGENCE_TOLERANCE` as "unpinned" — no test failed when they moved 7%. For
the first two that is the CORRECT state and pinning them would be wrong: they
are numerical hygiene, and their own comments say "Numerics only". The
meaningful question is the opposite one.

    A pin asks:            does the result change when this changes?  (it must)
    An insensitivity test: does the result change when this changes?  (it must NOT)

If a "numerics only" constant does move a reported result, it is not numerics —
it is an undeclared parameter, and that is what these tests detect.

`_CONVERGENCE_TOLERANCE` is deliberately NOT in that class: it is a REPORTING
threshold that decides when a trajectory is declared converged, so it is
supposed to change the verdict. It gets a reachability test instead.
"""

import pytest

import hours_eoh.research.formation as formation
import hours_eoh.research.recalibration as recal
import hours_eoh.scenarios.long_run as long_run


class TestNumericsOnlyToleranceAreInert:

    def test_the_stall_tolerance_does_not_change_the_verdict(self):
        """A stall tolerance that moves the answer is a stall THRESHOLD."""
        base = formation.formation_feedback_simulation(n_years=40)
        original = formation._STALL_TOL_TEH
        try:
            for scale in (0.01, 100.0):
                formation._STALL_TOL_TEH = original * scale
                got = formation.formation_feedback_simulation(n_years=40)
                assert got[-1]["eps_actual"] == pytest.approx(
                    base[-1]["eps_actual"], rel=1e-9
                ), f"stall tolerance x{scale} moved the arc"
                assert [r["stalled"] for r in got] == [r["stalled"] for r in base], (
                    f"stall tolerance x{scale} changed which years count as stalled"
                )
        finally:
            formation._STALL_TOL_TEH = original

    def test_the_ratchet_grid_step_does_not_change_phi(self):
        """
        A quadrature grid must be fine enough that halving it changes nothing
        material. If refining the grid moves φ, the reported value is a
        discretisation artefact rather than the quantity.
        """
        base = recal.phi_actual(0.60)["phi"]
        original = recal._RATCHET_STEP
        try:
            recal._RATCHET_STEP = original / 4.0
            refined = recal.phi_actual(0.60)["phi"]
        finally:
            recal._RATCHET_STEP = original
        assert refined == pytest.approx(base, rel=1e-3), (
            f"phi moved from {base} to {refined} on a 4x finer grid — the grid "
            "is too coarse and the shipped value is a discretisation artefact"
        )


class TestTheConvergenceThresholdIsAJudgement:
    """
    NOT an insensitivity test. `_CONVERGENCE_TOLERANCE` decides when a fiscal
    trajectory is DECLARED converged, so it is supposed to move the verdict —
    what matters is that it can fire and can fail to fire.
    """

    def test_the_threshold_is_reachable_in_both_directions(self):
        original = long_run._CONVERGENCE_TOLERANCE
        try:
            long_run._CONVERGENCE_TOLERANCE = 1.0        # everything converges
            loose = long_run.automation_transition_trajectory(n_periods=12)
            long_run._CONVERGENCE_TOLERANCE = 1e-12      # nothing does
            tight = long_run.automation_transition_trajectory(n_periods=12)
        finally:
            long_run._CONVERGENCE_TOLERANCE = original
        assert loose["convergence_period"] is not None, (
            "at a tolerance of 1.0 every step must count as converged"
        )
        assert tight["convergence_period"] is None, (
            "at 1e-12 nothing should — a threshold giving the same verdict at "
            "both ends is not deciding anything"
        )
