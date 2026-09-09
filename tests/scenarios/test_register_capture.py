"""
The register's failure model and the drift monitor.

The monitor is the framework's answer to its own worst comparative exposure, so
these tests are written against the ways a check like this usually fails rather
than against the ways it usually passes: a threshold that cannot fire, a
signature that cannot distinguish capture from growth, and an identity that
double-counts an aggregate key.
"""

from __future__ import annotations

import inspect

import pytest

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.scenarios.register_capture import (
    MINT_DOMAINS,
    capture_channels,
    capture_report,
    capture_scenario,
    drift_monitor,
    mint_decomposition,
)

ARC = [0.0, 0.40, 0.90, 0.99]


class TestTheDecompositionIsAnIdentity:

    @pytest.mark.parametrize("eps", ARC)
    def test_the_mint_reconstructs_from_its_domains(self, eps: float) -> None:
        d = mint_decomposition(eps)
        assert d["reconciles"], (
            f"at ε={eps} the domain reconstruction {d['reconstructed_mint']:.6e} "
            f"does not match teh_created {d['teh_created']:.6e}"
        )

    def test_the_aggregate_key_is_excluded_and_including_it_would_break_this(self) -> None:
        """
        `registration_by_domain` carries a `non_personal` key ALONGSIDE the
        domains it aggregates. Summing the dict naively double-counts, and the
        identity above is what catches it — so this pins that the trap is real
        rather than a remembered caution.
        """
        p = eoh_to_teh_pipeline(epsilon=0.40)
        assert "non_personal" in p["registered_eoh_by_domain"]
        assert "non_personal" not in MINT_DOMAINS

        honest = sum(float(p["registered_eoh_by_domain"][d]) for d in MINT_DOMAINS)
        naive = sum(float(v) for v in p["registered_eoh_by_domain"].values())
        assert naive > honest, "the aggregate key no longer double-counts; retire this guard"
        assert honest * float(p["mean_multiplier"]) == pytest.approx(
            float(p["teh_created"]), rel=1e-9)


class TestTheCaptureSignature:

    @pytest.mark.parametrize("eps", ARC)
    def test_a_registration_decision_never_moves_the_obligation(self, eps: float) -> None:
        """The signature the monitor keys on. This is not an accident of the
        implementation — `total_eoh` accepts no registration argument at all, and
        the next test binds that."""
        ch = capture_channels(eps)
        if ch["widest"] is None:
            pytest.skip(f"no live channel at ε={eps}")
        s = capture_scenario(ch["widest"], 0.01, eps)
        assert s["obligation_change"] == 0.0
        assert s["mint_change"] > 0.0

    def test_total_eoh_still_takes_no_registration_argument(self) -> None:
        """If this ever fails, the signature stops being diagnostic: the
        obligation could then move in response to a registration decision and
        `obligation_change == 0` would no longer mean anything."""
        params = set(inspect.signature(total_eoh).parameters)
        assert not {p for p in params if "registration" in p or "registered" in p}, params

    def test_the_refusal_direction_is_modelled_too(self) -> None:
        """A register that REFUSES has a victim rather than a beneficiary, and
        the same arithmetic describes it. A model that only represents admission
        would miss half the governance question — appeal against refusal is
        outline item 4."""
        s = capture_scenario("personal", -0.01, 0.40)
        assert s["mint_change"] < 0.0
        assert s["obligation_change"] == 0.0

    def test_a_share_outside_the_unit_interval_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a decision"):
            capture_scenario("personal", 0.99, 0.40)
        with pytest.raises(ValueError, match="must be one of"):
            capture_scenario("not_a_domain", 0.01, 0.40)


class TestTheChannelRanking:

    def test_personal_is_the_widest_channel_at_the_reference(self) -> None:
        """Not a shipped constant — a measured consequence of the obligation mix:
        personal is the largest domain AND the least registered, so it carries
        both the most mint and the most headroom."""
        ch = capture_channels(0.40)
        assert ch["widest"] == "personal"
        personal = next(c for c in ch["channels"] if c["domain"] == "personal")
        assert personal["share_of_mint"] > 0.5
        assert personal["headroom"] > 0.5

    def test_a_domain_with_no_obligation_behind_it_is_not_a_channel(self) -> None:
        """Ecological registers at the same share as infrastructure but carries
        no obligation under the shipped Phase 4e/4f default, so its headroom is
        not reachable. Ranking on share alone would put it level with
        infrastructure and be wrong."""
        ch = capture_channels(0.40)
        eco = next(c for c in ch["channels"] if c["domain"] == "ecological")
        assert eco["headroom"] > 0.0
        assert eco["mint_if_fully_admitted"] == 0.0
        assert ch["widest"] != "ecological"

    def test_the_ranking_is_epsilon_dependent_and_not_one_answer(self) -> None:
        """The obligation mix moves across the arc, so which decision is most
        consequential moves with it. A caller quoting one ranking as 'the
        framework's' would be quoting a point on a curve."""
        seen = {round(c["mint_if_fully_admitted"], 6)
                for eps in ARC for c in capture_channels(eps)["channels"]
                if c["domain"] == "personal"}
        assert len(seen) > 1, "the personal channel did not move across the arc"


class TestTheMonitorCanFireAndCanNotFire:
    """
    Both directions, because a threshold that cannot fire is `LEVY_SUFFICIENCY_WARN`
    again and a threshold that always fires is no better.
    """

    def test_it_does_not_fire_inside_the_declared_threshold(self) -> None:
        r = drift_monitor(baseline_share=0.16, observed_share=0.17, threshold=0.05)
        assert r["breached"] is False
        assert r["unexplained"] is False
        assert "within" in r["verdict"]

    def test_it_fires_outside_the_declared_threshold(self) -> None:
        r = drift_monitor(baseline_share=0.16, observed_share=0.30, threshold=0.05)
        assert r["breached"] is True
        assert r["unexplained"] is True

    def test_it_fires_downward_too(self) -> None:
        """A register that stops admitting is also drifting. Monitoring only the
        inflationary direction is the asymmetry outline item 5 warns about —
        nobody is visibly harmed by a wrongly-ADMITTED obligation, so that is the
        direction usually watched, and the refusal direction is the one with a
        person on the other end."""
        r = drift_monitor(baseline_share=0.30, observed_share=0.16, threshold=0.05)
        assert r["breached"] is True
        assert r["drift"] < 0.0

    def test_a_breach_explained_by_the_obligation_is_not_the_signature(self) -> None:
        """The distinction the monitor exists to draw. A collective that
        automates fast will breach a tight threshold legitimately, and reporting
        that as capture would make the monitor useless within one arc."""
        moved = drift_monitor(baseline_share=0.16, observed_share=0.30,
                              threshold=0.05, obligation_change=5.0)
        assert moved["breached"] is True
        assert moved["unexplained"] is False
        assert "moved too" in moved["verdict"]

    def test_the_threshold_is_required_and_has_no_default(self) -> None:
        """THE PIN THAT MATTERS. A shipped threshold calibrated to the shipped
        configuration is a warning that cannot fire — failure mode 9 applied to
        the framework's own worst exposure. The collective declares it."""
        sig = inspect.signature(drift_monitor)
        assert sig.parameters["threshold"].default is inspect.Parameter.empty
        with pytest.raises(TypeError):
            drift_monitor(baseline_share=0.16, observed_share=0.30)  # type: ignore[call-arg]

    def test_a_zero_threshold_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a declaration"):
            drift_monitor(baseline_share=0.16, observed_share=0.17, threshold=0.0)


class TestTheReportStatesItsOwnLimits:

    def test_it_declares_what_it_does_not_establish(self) -> None:
        r = capture_report(0.40)
        assert r["reporting_only"] is True
        limits = " ".join(r["what_this_does_not_establish"]).lower()
        assert "no actor" in limits or "incentive" in limits
        assert "bounded" in limits, (
            "the report must say that a monitor makes drift VISIBLE and does not "
            "BOUND capture — that gap is what §7's falsifier actually asks for"
        )

    def test_it_names_what_the_monitor_needs_and_that_none_is_shipped(self) -> None:
        r = capture_report(0.40)
        needs = " ".join(r["what_the_monitor_needs"]).lower()
        assert "threshold" in needs and "ships neither" in needs
