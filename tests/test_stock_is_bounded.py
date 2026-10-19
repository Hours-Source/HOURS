"""The stock is bounded by the founding endowment PLUS cumulative fulfilment.

The value-anchor argument ends on a proposition: the circulating stock is bounded above
by cumulative registered fulfilment net of destruction, so each unit is a claim, not a
promise. It is the fourth of four things the anchor rests on, and nothing checked it.

**Checked, the proposition as drafted is FALSE at founding.** The economy starts with an
endowment (a Trust balance and a capital stock) that no registered fulfilment created.
The identity that holds is

    supply(t) = endowment + Σ created − Σ destroyed

so `supply ≤ Σ created` is a statement about the long run, not about period zero
([record](record/verification.md#stock-is-an-identity)).

TWO ACCOUNTS OF ONE QUANTITY. `core.eoh_fulfillment.teh_supply()` implements the tighter
bound, an economy with no endowment, and nothing calls it. It is pinned, not deleted: it
is the bound the theory wants, and its gap from what ships is the finding
([record](record/verification.md#teh-supply-guard-re-pointed)).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from hours_eoh.core.eoh_fulfillment import teh_supply
from hours_eoh.core.simulation import make_economy_state, run_simulation

REPO = pathlib.Path(__file__).resolve().parent.parent
PERIODS = 120


def _run(n: int = PERIODS):
    state = make_economy_state()
    return state, run_simulation(state, n_periods=n)


class TestTheStockIdentityHoldsEveryPeriod:
    """
    THE CONSERVATION LAW. Not vacuous: it accumulates the PER-PERIOD reported
    flows and compares them against the state's own cumulative counters and the
    reported supply. Three accounts that must agree. A path that moved TEH
    without reporting it breaks this even though the state would still be
    internally consistent.
    """

    def test_reported_flows_reconstruct_the_reported_supply(self):
        state, res = _run()
        endowment = state["teh_endowment"]
        created = destroyed = 0.0
        for row in res["period_results"]:
            created += row["teh_created"]
            destroyed += row["teh_destroyed"]
            assert row["teh_total_supply"] == pytest.approx(
                endowment + created - destroyed, rel=1e-12
            )

    def test_the_reported_flows_match_the_state_counters(self):
        """`states[i]` is the state AFTER `period_results[i]`; the list leaves out the
        initial state. An off-by-one would pass for any constant flow and fails only
        because minting grows.
        """
        state, res = _run()
        assert len(res["states"]) == len(res["period_results"])
        created = destroyed = 0.0
        for row, post in zip(res["period_results"], res["states"]):
            created += row["teh_created"]
            destroyed += row["teh_destroyed"]
            assert post["teh_created_cumulative"] == pytest.approx(created, rel=1e-12)
            assert post["teh_destroyed_cumulative"] == pytest.approx(destroyed, rel=1e-12)

    def test_net_is_the_difference_of_the_two_flows(self):
        _, res = _run(20)
        for row in res["period_results"]:
            assert row["teh_net"] == pytest.approx(
                row["teh_created"] - row["teh_destroyed"], rel=1e-12
            )

    def test_the_supply_never_goes_negative(self):
        _, res = _run()
        assert all(r["teh_total_supply"] > 0.0 for r in res["period_results"])


class TestTheFoundingEndowmentIsNotBackedByFulfilment:
    """THE HONEST LIMIT, measured: at founding the whole stock exists and nothing has
    been minted.
    """

    def test_at_founding_nothing_has_been_minted_and_the_stock_is_large(self):
        state = make_economy_state()
        assert state["teh_created_cumulative"] == 0.0
        assert state["teh_destroyed_cumulative"] == 0.0
        assert state["teh_endowment"] > 0.0

    def test_the_endowment_is_the_trust_plus_embodied_capital(self):
        """It is not an arbitrary number: it is what the founding actors hold."""
        state = make_economy_state()
        assert state["teh_endowment"] == pytest.approx(
            state["trust_balance"] + state["capital_embodied_teh"], rel=1e-9
        )

    def test_the_endowment_dwarfs_a_period_of_minting(self):
        """A magnitude class, not a level. An endowment small against annual minting
        would be a rounding detail; it is not, so the anchor argument must declare it.
        """
        state, res = _run(1)
        first_mint = res["period_results"][0]["teh_created"]
        assert state["teh_endowment"] / first_mint > 10.0

    def test_the_tighter_bound_is_FALSE_early(self):
        """`supply <= cumulative mint` — what the anchor argument wants — fails."""
        _, res = _run(10)
        created = 0.0
        for row in res["period_results"]:
            created += row["teh_created"]
        assert res["period_results"][-1]["teh_total_supply"] > created


class TestTheEndowmentTurnsOverInTheLongRun:
    """Restated 2026-09-17 (author decision). The founding stock is PRIOR WORK, brought
    by the people who form or join a collective; at subsistence it is nothing, and its
    level is an instance input. "Destruction outpaces creation early" held only at
    35,000 TEH/person: at 8,760 it never does, and at 0 there is nothing to retire.
    Cumulative creation overtaking the total supply holds at every level, so this class
    pins that ([record](record/fulfilment.md#inheritance-repriced-as-prior-work)).
    """

    def test_cumulative_minting_eventually_exceeds_the_standing_stock(self):
        _, res = _run()
        created = 0.0
        crossed = False
        for row in res["period_results"]:
            created += row["teh_created"]
            if created >= row["teh_total_supply"]:
                crossed = True
                break
        assert crossed, (
            "the founding endowment is never overtaken by registered fulfilment "
            "within the horizon — the anchor's bound would then be permanently "
            "false, not merely false at founding"
        )

    @pytest.mark.parametrize("prior_work,label", [
        (0.0, "subsistence founding — nothing brought"),
        (None, "the shipped estimate of current-world prior work"),
        (3.5e10, "four times it — the pre-2026-09-17 figure"),
    ])
    def test_the_overtaking_does_not_depend_on_how_much_was_brought(
        self, prior_work, label
    ):
        """The anchor claim is that nothing ultimately stands which registered
        fulfilment did not create. It must hold at EVERY level of prior work, or it
        describes one calibration. It replaces
        `test_destruction_outpaces_creation_early` (2026-09-17).
        """
        state = make_economy_state(trust_balance=prior_work)
        res = run_simulation(make_economy_state(trust_balance=prior_work),
                             n_periods=PERIODS)
        created = 0.0
        crossed = False
        for row in res["period_results"]:
            created += row["teh_created"]
            if created >= row["teh_total_supply"]:
                crossed = True
                break
        assert crossed, (
            f"registered fulfilment never overtook the standing stock within "
            f"{PERIODS} periods for {label} (endowment "
            f"{state['teh_endowment']:,.0f}) — the anchor's bound would then be "
            f"permanently false at this level of prior work, not merely false "
            f"at founding"
        )

    def test_destruction_is_real_rather_than_nominal(self):
        _, res = _run(20)
        assert all(r["teh_destroyed"] > 0.0 for r in res["period_results"])


class TestTheOrphanedSupplyFunctionContradictsTheShippedModel:
    """
    THE FINDING, pinned so it cannot change silently. `teh_supply` states the
    bound the theory wants and no longer describes the model that ships.
    """

    def test_it_is_called_by_nothing(self):
        sites: list[str] = []
        for layer in ("core", "land", "scenarios", "research"):
            for path in sorted((REPO / "hours_eoh" / layer).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "teh_supply"):
                        sites.append(f"{path.relative_to(REPO)}:{node.lineno}")
        assert sites == [], (
            f"teh_supply has acquired callers: {sites}. Its invariant is FALSE "
            f"for an economy with a founding endowment, so a new caller is "
            f"either a bug or a decision to model an endowment-free economy."
        )

    def test_its_identity_differs_from_the_shipped_one_by_the_endowment(self):
        """`teh_supply` computes created − destroyed and the shipped model endowment +
        created − destroyed, so they differ by exactly the endowment at any inheritance.
        The test asserts that difference. It once asserted that `teh_supply` RAISES,
        which stopped at 8,760 TEH/person while the endowment stayed 11.16e9
        ([record](record/verification.md#teh-supply-guard-re-pointed)).
        """
        state, res = _run(40)
        created = sum(r["teh_created"] for r in res["period_results"])
        destroyed = sum(r["teh_destroyed"] for r in res["period_results"])
        endowment = state["teh_endowment"]
        assert endowment > 0.0, (
            "the shipped model has no founding endowment — if that is now true, "
            "teh_supply is the correct account and this whole class retires"
        )
        unendowed = teh_supply(created, destroyed) if created >= destroyed else None
        shipped = res["period_results"][-1]["teh_total_supply"]
        assert unendowed is not None, (
            "teh_supply refused the shipped flows; the old form of this test "
            "covers that case and the difference below is unmeasurable"
        )
        assert shipped - unendowed == pytest.approx(endowment, rel=1e-9), (
            "the shipped supply must exceed the unendowed identity by exactly "
            "the founding endowment; if it does not, a third account exists"
        )

    def test_it_is_correct_for_the_economy_it_describes(self):
        """The function is not wrong; it is unendowed. Given flows from an economy that
        started at zero, it behaves as the anchor argument wants.
        """
        assert teh_supply(1000.0, 400.0) == pytest.approx(600.0)
        assert teh_supply(1000.0, 1000.0) == pytest.approx(0.0)


class TestNothingGrowsWithoutLabour:
    """
    CONDITION III, the fourth leg of the proposition. Balances move through
    labour income and expenditure, never through a yield on a holding.
    """

    def test_the_trust_has_no_interest_term(self):
        """Condition III forbids the balance itself moving the balance. For identical
        flows the movement must be the same at any size, so no term depends on the
        holding. Since 2026-09-15 unspent capacity stays, so a quiet period is FLAT, and
        flat is not a yield.
        """
        from hours_eoh.core.fiscal import trust_management
        def delta(balance):
            r = trust_management(trust_balance=balance, levy_revenue=1.0e6,
                                 stewardship_cost=0.0, guarantee_cost=4.0e5)
            return r["trust_end"] - r["trust_start"]
        assert delta(1.0e9) == pytest.approx(delta(1.0e11), rel=1e-12)
        assert delta(1.0e9) == pytest.approx(1.0e6 - 4.0e5, rel=1e-12)
        quiet = trust_management(trust_balance=1.0e10, levy_revenue=0.0,
                                 stewardship_cost=0.0, guarantee_cost=0.0)
        assert quiet["trust_end"] == pytest.approx(quiet["trust_start"], rel=1e-12), (
            "a quiet period must not GROW the balance; if it rose, something "
            "is paying a return on a holding"
        )

    def test_a_larger_holding_earns_no_premium_rate(self):
        """
        The dividend scales with the balance, which is drawdown, not interest —
        so the RATE must be identical at any size. A super-linear response would
        be a yield.
        """
        from hours_eoh.core.fiscal import trust_management
        small = trust_management(trust_balance=1.0e9, levy_revenue=0.0,
                                 stewardship_cost=0.0, guarantee_cost=0.0)
        large = trust_management(trust_balance=1.0e11, levy_revenue=0.0,
                                 stewardship_cost=0.0, guarantee_cost=0.0)
        assert (small["dividend"] / small["trust_start"]) == pytest.approx(
            large["dividend"] / large["trust_start"], rel=1e-12
        )
