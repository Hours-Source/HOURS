"""
Tests for hours_eoh.research.exchange

The exchange-accounting layer: declared frames, the parity floor, double-entry
books per collective, and the N=1 anchor that keeps the whole thing tied to the
single-ledger model.

Structure mirrors what the module claims:
  TestCollectiveFrame          — the frame refuses to be half-stated
  TestBuildCollective          — the frame reaches BOTH core calls
  TestParityRate               — the floor rate, and the heterogeneity it needs
  TestLedger                   — double-entry invariants
  TestFederationBook           — cross-collective postings and the FX seam
  TestN1AccountingAnchor       — reproduces the single ledger exactly
  TestArcCoherence             — ε ∈ {0, 0.4, 0.99}, per CONTRIBUTING.md
"""

import pytest

from hours_eoh.data import LAND_HECTARES_PER_CAPITA
from hours_eoh.research.exchange import (
    CollectiveFrame,
    Entry,
    FederationBook,
    Ledger,
    build_collective,
    n1_accounting_anchor,
    parity_rate,
    rate_matrix,
)

ARC = (0.0, 0.40, 0.99)


def _frame(cid=0, pop=1e6, ha=None, cap=None, **kw):
    return CollectiveFrame(
        collective_id=cid,
        population=pop,
        land_hectares=ha if ha is not None else pop * LAND_HECTARES_PER_CAPITA,
        capital_stock_teh=cap if cap is not None else 2000.0 * pop,
        **kw,
    )


# ---------------------------------------------------------------------------

class TestCollectiveFrame:

    def test_land_area_has_no_default(self):
        """
        THE POINT OF THE CLASS. A default land area would reintroduce exactly the
        unstated pairing it exists to refuse — the defect found six times.
        """
        with pytest.raises(TypeError):
            CollectiveFrame(collective_id=0, population=1e6, capital_stock_teh=2e9)

    @pytest.mark.parametrize("bad", ["population", "land_hectares", "capital_stock_teh"])
    def test_the_three_extensive_quantities_must_be_positive(self, bad):
        kw = dict(collective_id=0, population=1e6, land_hectares=1.65e6,
                  capital_stock_teh=2e9)
        kw[bad] = 0.0
        with pytest.raises(ValueError, match=bad):
            CollectiveFrame(**kw)

    @pytest.mark.parametrize("bad", ["capital_age_ratio", "ecosystem_health"])
    def test_the_intensive_ratios_are_bounded(self, bad):
        with pytest.raises(ValueError, match=bad):
            _frame(**{bad: 1.5})

    def test_per_capita_land_makes_the_ratio_a_visible_call(self):
        f = CollectiveFrame.per_capita_land(0, 5e6, capital_stock_teh=1e10)
        assert f.land_hectares == pytest.approx(5e6 * LAND_HECTARES_PER_CAPITA)
        assert f.hectares_per_capita == pytest.approx(LAND_HECTARES_PER_CAPITA)

    def test_intensities_are_what_a_frame_holds_fixed(self):
        """
        Two frames at very different scales but one intensity describe the same
        economy — the property `CAPITAL_STOCK_DEFAULT`'s "at the 1M reference
        population" units were stating and no caller was honouring.
        """
        small = _frame(0, pop=1e6)
        large = _frame(1, pop=335e6)
        assert small.capital_per_capita == pytest.approx(large.capital_per_capita)
        assert small.hectares_per_capita == pytest.approx(large.hectares_per_capita)

    def test_the_frame_is_immutable(self):
        with pytest.raises(Exception):
            _frame().population = 2e6


# ---------------------------------------------------------------------------

class TestBuildCollective:

    def test_the_frame_reaches_both_core_calls(self):
        """
        The seam closed on 2026-08-20: pipeline and fiscal must resolve ONE
        ecological obligation, not two.
        """
        c = build_collective(_frame(pop=5e6, ha=12e6), 0.40)
        assert c.fiscal["ecological"]["ecological_eoh_total"] == pytest.approx(
            c.pipeline["eoh_by_domain"]["ecological"], rel=1e-12
        )

    def test_land_area_actually_moves_the_ecological_domain(self):
        """
        A frame that is accepted but ignored is worse than no frame. Doubling the
        land doubles the standing obligation.
        """
        a = build_collective(_frame(0, pop=1e6, ha=6e6), 0.40)
        b = build_collective(_frame(1, pop=1e6, ha=12e6), 0.40)
        assert b.pipeline["eoh_by_domain"]["ecological"] == pytest.approx(
            2.0 * a.pipeline["eoh_by_domain"]["ecological"], rel=1e-9
        )

    @pytest.mark.parametrize(
        "kw", ["population", "capital_stock", "ecological_area_hectares",
               "ecosystem_health", "capital_age_ratio"],
    )
    def test_overriding_a_frame_quantity_is_refused(self, kw):
        """A frame that can be overridden piecemeal is not a frame."""
        with pytest.raises(ValueError, match="frame's to state"):
            build_collective(_frame(), 0.40, **{kw: 1.0})

    def test_non_frame_kwargs_still_pass_through(self):
        c = build_collective(_frame(), 0.40, personal_standard="sufficiency")
        assert c.teh_created > 0.0

    def test_reserve_is_the_declared_fraction_of_what_was_minted(self):
        """
        Pinned to the CONSTANT, not to a range. `0 < reserve < teh_created` left
        COASEAN_RESERVE_FRACTION free to move from 0.10 to 0.50 undetected —
        found by mutating it during the 2026-08-27 test review.
        """
        from hours_eoh.data import COASEAN_RESERVE_FRACTION

        c = build_collective(_frame(), 0.40)
        assert c.reserve == pytest.approx(
            c.teh_created * COASEAN_RESERVE_FRACTION, rel=1e-12
        )


# ---------------------------------------------------------------------------

class TestParityRate:

    def test_identical_collectives_trade_at_parity(self):
        a = build_collective(_frame(0), 0.40)
        b = build_collective(_frame(1), 0.40)
        assert parity_rate(a, b) == pytest.approx(1.0, rel=1e-12)

    def test_capital_heterogeneity_produces_a_real_spread(self):
        """
        THE FINDING THIS MODULE EXISTS FOR. `make_federation` exposes only
        ecosystem_health, which moves a domain worth ~0.00017% of total EOH, so
        every rate it can produce sits within 1.3e-5 of parity. Capital moves the
        rate by tens of percent — the mechanism was always sound; the constructor
        could not drive it.
        """
        poor = build_collective(_frame(0, cap=1e9), 0.40)
        rich = build_collective(_frame(1, cap=4e9), 0.40)
        r = parity_rate(poor, rich)
        assert r < 0.95, f"expected a real spread, got {r}"
        assert 0.5 < r < 1.0

    def test_the_health_lever_is_degenerate_and_that_is_recorded(self):
        """
        Pinned as a PROPERTY OF THE CURRENT CALIBRATION, not as desirable. If the
        ecological level is ever resolved this test should fail and be updated —
        that is the signal, not a regression.
        """
        sick = build_collective(_frame(0, ecosystem_health=0.40), 0.40)
        well = build_collective(_frame(1, ecosystem_health=0.95), 0.40)
        assert abs(parity_rate(sick, well) - 1.0) < 1e-4

    def test_premium_layers_above_the_floor(self):
        a, b = build_collective(_frame(0), 0.40), build_collective(_frame(1), 0.40)
        assert parity_rate(a, b, premium=0.25) == pytest.approx(
            1.25 * parity_rate(a, b), rel=1e-12
        )

    def test_a_rate_cannot_go_non_positive(self):
        a, b = build_collective(_frame(0), 0.40), build_collective(_frame(1), 0.40)
        with pytest.raises(ValueError, match="> -1"):
            parity_rate(a, b, premium=-1.0)

    def test_reciprocity_holds_exactly_at_zero_premium(self):
        a = build_collective(_frame(0, cap=1e9), 0.40)
        b = build_collective(_frame(1, cap=4e9), 0.40)
        assert parity_rate(a, b) * parity_rate(b, a) == pytest.approx(1.0, rel=1e-12)

    def test_rate_matrix_covers_every_ordered_pair_but_no_self_pair(self):
        cs = [build_collective(_frame(i, cap=(i + 1) * 1e9), 0.40) for i in range(3)]
        m = rate_matrix(cs)
        assert len(m) == 3 * 2
        assert not any(i == j for i, j in m)


# ---------------------------------------------------------------------------

class TestLedger:

    def test_a_posting_moves_value_and_nothing_else(self):
        L = Ledger(0)
        L.mint(1000.0)
        assert L.balance(Ledger.CIRCULATION) == pytest.approx(1000.0)
        assert L.balance(Ledger.ISSUANCE) == pytest.approx(-1000.0)

    def test_the_book_balances_to_zero_after_every_posting(self):
        """
        STATING THE GAP, because this assertion is close to an identity.

        `post()` writes both legs from one `Entry`, so every posting adds +a to
        one account and −a to another and the signed total is zero for ANY
        inputs — 200 random postings with arbitrary accounts and amounts still
        return True. That is the DESIGN working (a one-legged posting is
        unconstructible), but it means this test guards the `Entry` type and the
        float accumulation, not the accounting logic. The tests that actually
        constrain behaviour are the DIRECTIONAL ones below.

        Same failure mode as `epoch_alpha_weights`' sum-to-ALPHA_SCALE, found in
        the same review — and found here in code written during that review,
        which is the honest reason to keep saying it out loud.
        """
        L = Ledger(0)
        for amt in (1000.0, 250.0, 17.5):
            L.mint(amt)
            assert L.balances_to_zero()
        L.destroy(500.0)
        assert L.balances_to_zero()

    def test_the_zero_sum_check_detects_a_one_legged_posting(self):
        """
        The thing the identity above cannot show: that `balances_to_zero` would
        actually catch a book someone corrupted. `Entry` forbids a one-legged
        posting, so this injects the shape a future `post_raw` bug would create.
        """
        from types import SimpleNamespace

        L = Ledger(0)
        L.mint(1000.0)
        assert L.balances_to_zero()
        L.entries.append(SimpleNamespace(debit="circulation", credit=None, amount=50.0))
        assert not L.balances_to_zero(), (
            "a posting with only one leg must break the trial balance"
        )

    def test_money_supply_is_minted_minus_destroyed(self):
        L = Ledger(0)
        L.mint(1000.0)
        L.destroy(150.0)
        assert L.money_supply() == pytest.approx(850.0)
        assert L.balance(Ledger.CIRCULATION) == pytest.approx(850.0)

    def test_negative_amounts_are_refused(self):
        with pytest.raises(ValueError, match="reverse the"):
            Entry(debit="a", credit="b", amount=-1.0)

    def test_an_entry_cannot_name_one_account_twice(self):
        with pytest.raises(ValueError, match="must differ"):
            Entry(debit="a", credit="a", amount=1.0)

    def test_trial_balance_lists_every_account_touched(self):
        L = Ledger(0)
        L.mint(100.0)
        L.destroy(10.0)
        assert set(L.trial_balance()) == {
            Ledger.CIRCULATION, Ledger.ISSUANCE, Ledger.DESTRUCTION
        }

    def test_the_zero_sum_tolerance_is_scale_relative(self):
        """A federation at 1e10 TEH cannot be held to an absolute 1e-9."""
        L = Ledger(0)
        L.mint(1e10)
        assert L.balances_to_zero()


# ---------------------------------------------------------------------------

class TestFederationBook:

    def _book(self):
        cs = [build_collective(_frame(i, cap=(i + 1) * 2e9), 0.40) for i in range(2)]
        return FederationBook.from_collectives(cs), cs

    def test_every_book_balances_independently(self):
        book, _ = self._book()
        assert book.all_balance()

    def test_minting_reproduces_each_collectives_teh_created(self):
        book, cs = self._book()
        for c in cs:
            assert book.ledger(c.collective_id).money_supply() == pytest.approx(
                c.teh_created, rel=1e-12
            )

    def test_the_reserve_is_earmarked_not_extra(self):
        """circulation + reserve reconstructs the total minted."""
        book, cs = self._book()
        for c in cs:
            L = book.ledger(c.collective_id)
            assert L.balance(L.CIRCULATION) + L.balance(L.RESERVE) == pytest.approx(
                c.teh_created, rel=1e-12
            )

    def test_a_transfer_leaves_both_books_balanced(self):
        book, _ = self._book()
        book.transfer(0, 1, amount=1000.0, rate=1.5)
        assert book.all_balance()

    def test_the_fx_difference_is_named_not_hidden(self):
        """
        At rate != 1 the federation total is NOT conserved, and that is correct —
        it is a revaluation. The test is that it lands in a DECLARED account
        rather than in a discrepancy.
        """
        book, _ = self._book()
        out = book.transfer(0, 1, amount=1000.0, rate=1.5)
        assert out == {"sent": 1000.0, "received": 1500.0, "fx": 500.0}
        assert book.ledger(1).balance(Ledger.FX) == pytest.approx(-1500.0)
        assert book.all_balance()

    def test_a_unit_rate_conserves_across_the_federation(self):
        book, cs = self._book()
        before = sum(book.ledger(c.collective_id).money_supply() for c in cs)
        book.transfer(0, 1, amount=1000.0, rate=1.0)
        after = sum(book.ledger(c.collective_id).money_supply() for c in cs)
        assert after == pytest.approx(before, rel=1e-12)

    @pytest.mark.parametrize(
        "kw,msg",
        [
            (dict(sender=0, receiver=0, amount=1.0, rate=1.0), "must differ"),
            (dict(sender=0, receiver=1, amount=0.0, rate=1.0), "amount must be > 0"),
            (dict(sender=0, receiver=1, amount=1.0, rate=0.0), "rate must be > 0"),
        ],
    )
    def test_malformed_transfers_are_refused(self, kw, msg):
        book, _ = self._book()
        with pytest.raises(ValueError, match=msg):
            book.transfer(**kw)

    def test_settlement_report_covers_every_collective(self):
        book, cs = self._book()
        book.transfer(0, 1, amount=1000.0, rate=1.2)
        rep = book.settlement_report()
        assert set(rep) == {c.collective_id for c in cs}
        for row in rep.values():
            assert {"reserve", "earmarked", "imbalance", "fx_revaluation",
                    "minted", "ceiling", "breached"} <= set(row)

    def test_nothing_is_breached_at_rest(self):
        """
        THE ASSERTION THAT WAS MISSING, and its absence hid a real defect
        (found 2026-08-27). `settlement_report` compared the STANDING RESERVE
        against the ceiling. The reserve is COASEAN_RESERVE_FRACTION (0.10) of
        what was minted and the ceiling was COASEAN_IMBALANCE_CEILING x that
        (0.05), so `breached` was unconditionally 1.0 for every collective
        before a single trade.

        The old test asserted only that the KEYS existed, never a value — so a
        flag that could not help firing passed as covered. That is failure mode
        5 inverted: a threshold that always fires carries as little information
        as one that never can.
        """
        book, _ = self._book()
        for cid, row in book.settlement_report().items():
            assert row["imbalance"] == pytest.approx(0.0, abs=1e-6), (
                f"collective {cid} has an imbalance before trading: {row}"
            )
            assert not row["breached"], f"collective {cid} breached at rest: {row}"

    def test_a_large_enough_transfer_does_breach(self):
        """And the converse: the flag must be REACHABLE, or it is decoration."""
        book, cs = self._book()
        earmark = book.settlement_report()[0]["earmarked"]
        book.transfer(0, 1, amount=0.9 * earmark, rate=1.0)
        rep = book.settlement_report()
        assert rep[0]["breached"], f"drawing 90% of the earmark must breach: {rep[0]}"
        assert rep[0]["imbalance"] < 0.0, "the sender's position must go negative"

    def test_a_small_transfer_does_not_breach(self):
        book, _ = self._book()
        earmark = book.settlement_report()[0]["earmarked"]
        book.transfer(0, 1, amount=0.1 * earmark, rate=1.0)
        assert not book.settlement_report()[0]["breached"]


# ---------------------------------------------------------------------------

class TestN1AccountingAnchor:
    """
    If N=1 does not reproduce the single ledger, every N>1 result is measuring
    the scaffold rather than the model.
    """

    def test_the_anchor_holds_exactly(self):
        a = n1_accounting_anchor()
        assert a["pipeline_match"]
        assert a["solvent_match"]
        assert a["book_balances"]
        assert a["money_supply_match"]
        assert a["teh_created_delta"] == 0.0

    @pytest.mark.parametrize("eps", ARC)
    def test_the_anchor_holds_across_the_arc(self, eps):
        a = n1_accounting_anchor(epsilon=eps)
        assert a["teh_created_delta"] == pytest.approx(0.0, abs=1e-6)
        assert a["book_balances"]

    def test_the_anchor_holds_at_a_foreign_frame(self):
        a = n1_accounting_anchor(population=5e6, capital_stock_teh=1e10)
        assert a["pipeline_match"] and a["money_supply_match"]


# ---------------------------------------------------------------------------

class TestArcCoherence:
    """ε-coherence is mandatory: meaningful output across the whole arc."""

    @pytest.mark.parametrize("eps", ARC)
    def test_a_collective_is_well_formed_at_every_epsilon(self, eps):
        c = build_collective(_frame(pop=5e6, ha=12e6), eps)
        assert c.teh_created > 0.0
        assert c.teh_per_capita > 0.0
        assert c.reserve >= 0.0

    @pytest.mark.parametrize("eps", ARC)
    def test_parity_is_defined_and_positive_at_every_epsilon(self, eps):
        a = build_collective(_frame(0, cap=1e9), eps)
        b = build_collective(_frame(1, cap=4e9), eps)
        r = parity_rate(a, b)
        assert r > 0.0
        assert r == pytest.approx(1.0 / parity_rate(b, a), rel=1e-9)

    @pytest.mark.parametrize("eps", ARC)
    def test_the_book_balances_at_every_epsilon(self, eps):
        cs = [build_collective(_frame(i, cap=(i + 1) * 2e9), eps) for i in range(3)]
        book = FederationBook.from_collectives(cs)
        book.transfer(0, 2, amount=100.0, rate=parity_rate(cs[0], cs[2]))
        assert book.all_balance()


# ---------------------------------------------------------------------------

class TestLayerIsolation:

    def test_nothing_in_core_land_or_scenarios_imports_this(self):
        """research/ is experimental; the stable layers must not depend on it."""
        import pathlib
        pkg = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh"
        offenders = [
            str(p.relative_to(pkg.parent))
            for layer in ("core", "land", "scenarios")
            for p in (pkg / layer).rglob("*.py")
            if "research.exchange" in p.read_text()
        ]
        assert not offenders, f"stable layers importing research/exchange: {offenders}"


class TestParityIsScaleFree:
    """
    THE GAP THIS CLOSES, found by mutating the module during the 2026-08-27 test
    review: `teh_per_capita` could drop `/ self.frame.population` entirely and
    all 57 tests still passed.

    The reason is the ε=0.40 trap in a new place. Every collective the other
    tests compare has the SAME population (1e6), so the division cancels on both
    sides of the ratio and the bug is invisible at exactly the point everything
    was measured. The fix is not a tighter tolerance — it is comparing
    collectives that DIFFER in the quantity the code divides by.

    The property: an exchange rate is a ratio of INTENSIVE quantities, so two
    collectives with identical intensity and different size must trade at
    exactly parity. If that fails, the rate is reading collective SIZE as
    economic strength, which is the same category error as pairing one
    jurisdiction's population with another's land.
    """

    def test_same_intensity_different_size_trades_at_exact_parity(self):
        small = build_collective(CollectiveFrame(0, 1e6, 1.65e6, 2e9), 0.40)
        big = build_collective(CollectiveFrame(1, 1e7, 1.65e7, 2e10), 0.40)
        assert big.frame.population == 10.0 * small.frame.population
        assert parity_rate(small, big) == pytest.approx(1.0, rel=1e-9)

    def test_per_capita_output_is_invariant_to_size(self):
        small = build_collective(CollectiveFrame(0, 1e6, 1.65e6, 2e9), 0.40)
        big = build_collective(CollectiveFrame(1, 1e7, 1.65e7, 2e10), 0.40)
        assert big.teh_per_capita == pytest.approx(small.teh_per_capita, rel=1e-9)
        assert big.teh_created > 5.0 * small.teh_created, (
            "the ABSOLUTE totals must differ, or the test proves nothing"
        )

    @pytest.mark.parametrize("eps", ARC)
    def test_scale_freedom_holds_across_the_arc(self, eps):
        small = build_collective(CollectiveFrame(0, 1e6, 1.65e6, 2e9), eps)
        big = build_collective(CollectiveFrame(1, 1e7, 1.65e7, 2e10), eps)
        assert parity_rate(small, big) == pytest.approx(1.0, rel=1e-9)

    def test_a_size_difference_alone_does_not_move_the_book(self):
        """The same claim one layer up: minting scales, the RATE does not."""
        cs = [
            build_collective(CollectiveFrame(0, 1e6, 1.65e6, 2e9), 0.40),
            build_collective(CollectiveFrame(1, 4e6, 6.6e6, 8e9), 0.40),
        ]
        book = FederationBook.from_collectives(cs)
        assert book.ledger(1).money_supply() == pytest.approx(
            4.0 * book.ledger(0).money_supply(), rel=1e-9
        )
        assert parity_rate(cs[0], cs[1]) == pytest.approx(1.0, rel=1e-9)
