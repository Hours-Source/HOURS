"""One mint path: the register is what disqualifies the hole-digger.

The value-anchor argument's defence against labour vouchers and energy certificates is
that an hour mints nothing unless a registered obligation existed and was met. Person A
digs a hole for eight hours, Person B fills it in, and the civilization gains nothing:
no obligation was registered, and nobody had to judge the work useless. The same test
kills energy accounting, which still counts the joules spent on the hole. The claim was
stated in prose and checked nowhere
([record](record/verification.md#one-mint-path-gated)).

STRUCTURAL AND MEASURED. `teh_created` is `registered_eoh × multiplier`, so "zero
registration mints nothing" and "linear in registered" are IDENTITIES of the formula.
They are pinned because the formula is the claim, and a future floor or bonus term would
break them. The other three classes are not identities: registration binds hard in
practice, surplus labour mints nothing, and no fiscal or land lever reaches the mint.

WHAT THIS DOES NOT CLAIM: on the default path the pipeline mints from human EOH that is
DEMANDED, not SERVED (`TestFulfilmentIsAssumedUnlessLabourIsSupplied`). That gap bounds
what the anchor argument may say.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

import hours_eoh.data as D
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline, teh_created

ARC = (0.0, 0.40, 0.90, 0.99)
REPO = pathlib.Path(__file__).resolve().parent.parent

#: The single shipped mint. Adding a second call is a monetary-architecture
#: change and must be a visible act in a diff, not an import.
THE_ONE_MINT = "hours_eoh/core/eoh_fulfillment.py"


class TestTheHoleDiggerMintsNothing:
    """
    STRUCTURAL — identities of `teh_created = registered_eoh × multiplier`.
    Pinned because that formula IS the claim: a floor, a bonus or a
    participation term added later would break these and should.
    """

    def test_no_registration_no_money(self):
        r = eoh_to_teh_pipeline(
            epsilon=0.40, registration_share=0.0, personal_registration_share=0.0
        )
        assert r["teh_created"] == 0.0
        assert r["total_eoh"] > 0.0, "the obligation must still exist"

    def test_the_mint_is_linear_in_registered_obligation(self):
        assert teh_created(0.0, 2.0) == 0.0
        assert teh_created(200.0, 2.0) == 2.0 * teh_created(100.0, 2.0)

    @pytest.mark.parametrize("capability", ARC)
    def test_the_mint_is_exactly_registered_times_the_multiplier(self, capability):
        r = eoh_to_teh_pipeline(epsilon=capability)
        assert r["teh_created"] == pytest.approx(
            r["registered_eoh"] * r["mean_multiplier"], rel=1e-12
        )


class TestRegistrationIsBindingNotAFormality:
    """
    MEASURED, not structural. If registration admitted nearly everything the
    gate would be decorative and the hole-digger defence would be nominal.
    """

    @pytest.mark.parametrize("capability", ARC)
    def test_most_human_obligation_mints_nothing(self, capability):
        r = eoh_to_teh_pipeline(epsilon=capability)
        assert r["registered_eoh"] < r["human_eoh"]
        assert r["registration_share"] < 1.0

    def test_the_unregistered_share_is_a_majority_at_the_reference_point(self):
        """
        SIGN and MAGNITUDE-CLASS. The level moves with the registration curves;
        that a clear majority of human obligation is off-ledger does not.
        """
        r = eoh_to_teh_pipeline(epsilon=0.40)
        assert r["registration_share"] < 0.5


class TestSurplusLabourMintsNothing:
    """THE HOLE-DIGGER, RUN. Labour beyond the registered obligation must not create
    TEH, because the mint saturates on the obligation, not on the hours offered. Not an
    identity: it depends on the rationing path only ever REDUCING what is served.
    """

    def test_the_mint_saturates_on_the_obligation(self):
        unconstrained = eoh_to_teh_pipeline(epsilon=0.40)["teh_created"]
        for labour in (1.0e10, 1.0e12, 1.0e15):
            r = eoh_to_teh_pipeline(epsilon=0.40, available_labor_eoh=labour)
            assert r["teh_created"] == pytest.approx(unconstrained, rel=1e-12)
            assert r["deferred_total"] == pytest.approx(0.0, abs=1e-6)

    def test_scarce_labour_mints_less_and_the_shortfall_is_reported(self):
        """The other direction: a real constraint must bite and be visible."""
        tight = eoh_to_teh_pipeline(epsilon=0.40, available_labor_eoh=1.0e9)
        loose = eoh_to_teh_pipeline(epsilon=0.40)
        assert tight["teh_created"] < loose["teh_created"]
        assert tight["deferred_total"] > 0.0


class TestOneMintPath:
    """
    THE GATE. A second mint path is a monetary-architecture change; this makes
    adding one fail rather than merge.
    """

    def test_exactly_one_call_site_across_the_operative_layers(self):
        """
        AST, not grep: a docstring mentioning `teh_created()` is not a call, and
        four of the five textual matches in this repo are prose.
        """
        sites: list[str] = []
        for layer in ("core", "land", "scenarios"):
            for path in sorted((REPO / "hours_eoh" / layer).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "teh_created"):
                        sites.append(f"{path.relative_to(REPO)}:{node.lineno}")
        assert len(sites) == 1, (
            f"expected exactly one mint; found {len(sites)}: {sites}. "
            f"A second path that creates TEH is a change to the monetary "
            f"architecture, not a refactor."
        )
        assert sites[0].startswith(THE_ONE_MINT)

    @pytest.mark.parametrize("constant,value", [
        ("SUFF_LEVY_RATE", 0.50),
        ("TRUST_BASE_TEH", 1.0e12),
        ("DIV_RATE", 0.90),
        ("DEP_RATE", 0.50),
        ("ESTATE_LEVY_FRACTION", 0.90),
    ])
    def test_no_fiscal_lever_reaches_the_mint(self, constant, value):
        """
        The fiscal layer is circulatory: it decides who HOLDS TEH, never how much
        exists. If a levy, the Trust, the dividend or an estate rule ever moved
        `teh_created`, that would be a second mint wearing a transfer's clothes.
        """
        base = eoh_to_teh_pipeline(epsilon=0.40)["teh_created"]
        original = getattr(D, constant)
        try:
            setattr(D, constant, value)
            assert eoh_to_teh_pipeline(epsilon=0.40)["teh_created"] == base
        finally:
            setattr(D, constant, original)

    def test_converting_eoh_to_teh_units_is_not_minting(self):
        """`fiscal.stewardship_allocation` computes `human_eoh × mean_multiplier`, which
        looks like the mint and is not: it is a REQUIREMENT in TEH, for comparison with
        the Trust. The test pins that it stays out of `teh_created`, or the AST gate
        could pass while the arithmetic ran elsewhere under another name.
        """
        from hours_eoh.core.fiscal import stewardship_allocation
        alloc = stewardship_allocation(
            capital_stock_teh=2.0e9, capital_age_ratio=0.50,
            epsilon=0.40, available_teh=1.0e9,
        )
        assert alloc["teh_required"] > 0.0
        assert eoh_to_teh_pipeline(epsilon=0.40)["teh_created"] != alloc["teh_required"]

        # And it is a REQUIREMENT: raising it does not create TEH, it creates a
        # funding gap. That is the whole difference between the two operations.
        starved = stewardship_allocation(
            capital_stock_teh=2.0e9, capital_age_ratio=0.50,
            epsilon=0.40, available_teh=0.0,
        )
        assert starved["teh_allocated"] == 0.0
        assert starved["funding_gap"] == pytest.approx(starved["teh_required"])


class TestTheTrustDrawsDownRatherThanCreates:

    def test_the_guarantee_leaves_the_balance(self):
        """`trust_end = start − guarantee + inflows`. The guarantee is a DRAWDOWN of a
        held stock, so with no inflows the balance falls by exactly the guarantee. Until
        2026-09-15 the dividend left the balance instead, whether or not anything was
        owed.
        """
        from hours_eoh.core.fiscal import trust_management
        t = trust_management(trust_balance=1.0e10, levy_revenue=0.0,
                             stewardship_cost=0.0, guarantee_cost=4.0e8)
        assert t["trust_end"] == pytest.approx(t["trust_start"] - 4.0e8, rel=1e-12)
        quiet = trust_management(trust_balance=1.0e10, levy_revenue=0.0,
                                 stewardship_cost=0.0, guarantee_cost=0.0)
        assert quiet["trust_end"] == pytest.approx(quiet["trust_start"], rel=1e-12)

    def test_inflows_move_the_balance_one_for_one(self):
        from hours_eoh.core.fiscal import trust_management
        a = trust_management(trust_balance=1.0e10, levy_revenue=0.0,
                             stewardship_cost=0.0, guarantee_cost=0.0)
        b = trust_management(trust_balance=1.0e10, levy_revenue=1.0e6,
                             stewardship_cost=0.0, guarantee_cost=0.0)
        assert b["trust_end"] - a["trust_end"] == pytest.approx(1.0e6, rel=1e-9)


class TestFulfilmentIsAssumedUnlessLabourIsSupplied:
    """THE HONEST GAP, and it bounds what the anchor argument may claim. The chain is
    "obligation → VERIFIED fulfilment → claim", and on the default path the middle step
    is assumed: `available_labor_eoh` defaults to None, so the pipeline mints from
    DEMANDED human EOH, as its own docstring says.

    At its sharpest: supply an apparatus and NO population, and the default path still
    mints, because an infrastructure obligation needs the apparatus, not people. Supply
    the labour constraint and it mints nothing. An institution must run that path to
    make the verification real.

    Restated 2026-09-16, when the capital frame closed: the cases now supply the
    apparatus explicitly, because a resolved stock scales with population
    ([record](record/fulfilment.md#capital-frame-closed)). Only the infrastructure
    obligation outlives its people; knowledge scales with them.
    """

    #: The apparatus the arc resolves at ε=0.40 in the reference frame. Supplied
    #: EXPLICITLY here, because that is the whole point: a stock that is named is
    #: the actual stock and is never rescaled by population.
    APPARATUS_TEH = 2.4e9

    def test_with_no_population_but_an_apparatus_the_default_path_still_mints(self):
        r = eoh_to_teh_pipeline(
            epsilon=0.40, population=0.0, capital_stock=self.APPARATUS_TEH
        )
        assert r["teh_created"] > 0.0
        assert abs(r["teh_created"] / 6.7649e7 - 1.0) < 1e-4  # 6.378e7 before 2026-10-04: the default stock age became the measured US one (0.50 → 0.591)
        assert r["labor_constrained"] is False
        assert r["eoh_by_domain"]["personal"] == 0.0
        assert r["eoh_by_domain"]["knowledge"] == 0.0, (
            "knowledge scales with the people who carry the corpus — it was "
            "never part of the 'does not depend on anyone existing' claim"
        )
        assert abs(r["eoh_by_domain"]["infrastructure"] / 9.546e7 - 1.0) < 1e-9, (  # 9.0e7 before
            "the obligation that remains is the apparatus's, and only its"
        )

    def test_with_the_constraint_supplied_it_mints_exactly_nothing(self):
        r = eoh_to_teh_pipeline(
            epsilon=0.40, population=0.0, capital_stock=self.APPARATUS_TEH,
            available_labor_eoh=0.0,
        )
        assert r["teh_created"] == 0.0
        assert r["deferred_total"] > 0.0, "the obligation is deferred, not erased"
        assert abs(r["deferred_total"] / 5.7276e7 - 1.0) < 1e-9  # 5.4e7 before the measured age

    def test_the_two_paths_disagree_and_that_is_the_finding(self):
        assumed = eoh_to_teh_pipeline(
            epsilon=0.40, population=0.0, capital_stock=self.APPARATUS_TEH
        )["teh_created"]
        verified = eoh_to_teh_pipeline(
            epsilon=0.40, population=0.0, capital_stock=self.APPARATUS_TEH,
            available_labor_eoh=0.0,
        )["teh_created"]
        assert assumed > verified == 0.0

    def test_with_no_apparatus_and_no_population_nothing_is_resolved(self):
        """The frame change itself. Before 2026-09-16 this minted 3.3964e8 TEH, because
        zero people still resolved the 1M-reference apparatus. The frame holds capital
        INTENSITY fixed, so zero people is zero apparatus; the test above shows a named
        apparatus still generates its obligation, so this zero is the frame, not a
        silent pipeline.
        """
        r = eoh_to_teh_pipeline(epsilon=0.40, population=0.0)
        assert r["teh_created"] == 0.0
        assert r["eoh_by_domain"]["infrastructure"] == 0.0
