"""
Registration RELOCATES obligation; it never creates it.

WHY THIS EXISTS. TEH is minted against registered EOH, and registered EOH is a
SHARE of an obligation that already exists. Paid care substitutes for unpaid
care — if paid care did not cover care that someone would otherwise have done
unpaid, there would be no reason to pay for it. So the hours are the same hours:
registration moves them from off-ledger to on-ledger and makes them visible and
mintable. It does not add to the obligation, and it does not reduce it.

IF THAT EVER STOPS HOLDING, TEH IS MINTED AGAINST WORK THAT IS NOT THERE, and
the currency's anchor to physical entropy — the whole claim of the framework —
goes with it. The primitive `registered_eoh(human, share)` cannot break it
(`share <= 1.0` is validated there), which is exactly why the check belongs at
the PIPELINE, one level up: containment at a primitive says nothing about a
caller that changes the obligation on its way past. That is corpus F-037 —
wired to the primitive, unreachable from the documented entry point — so this
drives `eoh_to_teh_pipeline`, the path the implementation guide gives
institutions.

THE THREE PROPERTIES, and they are different claims:
  containment  registered <= human <= gross, per domain and in total
  invariance   moving the registration share does not move the obligation
  provenance   every minted TEH traces to registered hours and nothing else

STATED GAP: this checks the SHARE cannot create obligation. It does not check
the MULTIPLIER — `teh_created = registered x mean_multiplier` mints more TEH
than there are hours by construction, which is Condition II and a separate
question with its own tests. Containment here is about HOURS, not about TEH
volume.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

ARC = (0.0, 0.40, 0.90, 0.99)
DOMAINS = ("personal", "infrastructure", "ecological", "knowledge")


def _run(**kw):
    return eoh_to_teh_pipeline(**kw)


class TestRegistrationIsContained:

    @pytest.mark.parametrize("eps", ARC)
    def test_registered_never_exceeds_the_obligation_it_registers(self, eps) -> None:
        r = _run(epsilon=eps)
        gross = r["eoh_by_domain"]
        reg = r["registered_eoh_by_domain"]
        for d in DOMAINS:
            assert reg[d] <= gross[d] + 1e-6, (
                f"ε={eps} domain {d}: registered {reg[d]:,.1f} exceeds the "
                f"obligation {gross[d]:,.1f}. Registration would be MINTING "
                "against hours nobody owes."
            )

    @pytest.mark.parametrize("eps", ARC)
    def test_the_chain_gross_human_registered_is_ordered(self, eps) -> None:
        r = _run(epsilon=eps)
        assert r["registered_eoh"] <= r["human_eoh"] + 1e-6, (
            f"ε={eps}: registered {r['registered_eoh']:,.1f} exceeds human "
            f"{r['human_eoh']:,.1f} — a machine's hour cannot be registered as "
            "a person's."
        )
        assert r["human_eoh"] <= r["total_eoh"] + 1e-6

    @pytest.mark.parametrize("eps", ARC)
    def test_moving_the_share_does_not_move_the_obligation(self, eps) -> None:
        """
        THE INVARIANCE, AND IT IS THE LOAD-BEARING ONE. If registering more work
        raised total EOH, the ledger would be manufacturing its own demand: every
        increase in registration would create the obligation that justifies the
        TEH it mints. Registration is a VIEW over an obligation physics already
        fixed, so the obligation must be bit-identical across shares.
        """
        # HONEST ABOUT ITS OWN STRENGTH: today this CANNOT fail, because
        # `total_eoh` takes no registration parameter — the obligation is
        # computed before registration is consulted, so invariance is
        # structural rather than tested. That is failure mode 2, an assertion
        # the implementation enforces, and it is kept deliberately: the day
        # someone threads a registration term into generation, this is the test
        # that fires. Verified by inspection of `total_eoh`'s signature in
        # `test_generation_takes_no_registration_parameter` below, which is the
        # assertion actually doing work here.
        base = _run(epsilon=eps)
        for share in (0.0, 0.25, 0.75, 1.0):
            alt = _run(epsilon=eps, registration_share=share,
                       personal_registration_share=share)
            assert alt["total_eoh"] == base["total_eoh"], (
                f"ε={eps}, share={share}: total EOH moved from "
                f"{base['total_eoh']:,.1f} to {alt['total_eoh']:,.1f}. "
                "Registration created obligation."
            )
            assert alt["eoh_by_domain"] == base["eoh_by_domain"]
            assert alt["human_eoh"] == pytest.approx(base["human_eoh"], rel=1e-12)

    @pytest.mark.parametrize("eps", ARC)
    def test_a_share_of_zero_registers_nothing_and_mints_nothing(self, eps) -> None:
        """Subsistence: the entropy is resisted, no monetary event occurs."""
        r = _run(epsilon=eps, registration_share=0.0, personal_registration_share=0.0)
        assert r["registered_eoh"] == pytest.approx(0.0, abs=1e-9)
        assert r["teh_created"] == pytest.approx(0.0, abs=1e-9)
        assert r["total_eoh"] > 0.0, "the obligation does not vanish with the ledger"

    @pytest.mark.parametrize("eps", ARC)
    def test_every_minted_teh_traces_to_registered_hours(self, eps) -> None:
        r = _run(epsilon=eps)
        assert r["teh_created"] == pytest.approx(
            r["registered_eoh"] * r["mean_multiplier"], rel=1e-12), (
            "TEH was minted against something other than registered EOH x the "
            "multiplier — there is a second mint path."
        )

    def test_generation_takes_no_registration_parameter(self) -> None:
        """
        The structural fact the invariance test rests on, asserted directly so
        it cannot quietly stop being true. If generation ever accepts a
        registration term, the ledger can manufacture its own demand.
        """
        import inspect
        from hours_eoh.core.eoh_generation import total_eoh
        offenders = [p for p in inspect.signature(total_eoh).parameters
                     if "registration" in p or "registered" in p]
        assert not offenders, (
            f"`total_eoh` now accepts {offenders} — the obligation can depend on "
            "how much of it is registered, which lets registration create the "
            "demand that justifies the TEH it mints."
        )

    def test_the_stated_gap_is_still_stated(self) -> None:
        doc = __doc__ or ""
        assert "STATED GAP" in doc and "MULTIPLIER" in doc
