"""
research/parcel_condition — the holder's debt, the bond, the index at 1, the
reserved floor and the low-ε flat fee (author, 2026-10-01;
`notes/parcel-condition-bond.md`).

THE POINT OF THE FILE is `TestTheLoopCreatesNoMoney`: over any sequence that
returns a parcel to the same physical condition, net TEH created is zero —
whether the holder settles or the Trust bears the restoration. A
register-declared write-down is the only door to net creation. Seven
mutations, each caught: skip the settlement, mint paper improvement, accept a
holder's reading, mint below the mark without settled debt, book the bond as
issuance, let a fire erase the holder's damage, ignore the reserve.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    BASKET_SHELTER_M2_PER_PERSON, COLLECTIVE_LAND_RESERVE_FACTOR,
    GUF_AFFORDABILITY_THRESHOLD, MEAN_MULTIPLIER_REFERENCE,
)
from hours_eoh.research.exchange import Ledger
from hours_eoh.research.parcel_condition import (
    BOND_ESCROW, REGISTER, ParcelLease, assess, collective_restore,
    declare_writedown, default_flat_fee, enter, exchange, exit_to_collective,
    land_reserve_hectares, log_improvement, reset_hours, residential_fee,
)

M = MEAN_MULTIPLIER_REFERENCE


def _parcel(seq="grassland_seeding", area_slu=100.0):
    return ParcelLease(parcel={"parcel_id": "p0", "area_slu": area_slu,
                               "location_value": 0.5,
                               "use_category": "residential_primary"},
                       sequence=seq)


def _net_created(ledger: Ledger) -> float:
    """TEH that exists now and did not before: issued minus destroyed."""
    return -ledger.balance(Ledger.ISSUANCE) - ledger.balance(Ledger.DESTRUCTION)


def _lease(lease, ledger, holder="A", bond=0.0):
    return enter(lease, holder, ledger=ledger, collective_held_ha=1e9,
                 reserve_ha=0.0, bond_teh=bond)


class TestTheIndexStartsAtOneAndOnlyTheRegisterReadsIt:

    def test_entry_reads_one_at_the_current_state(self):
        L, p = Ledger(0), _parcel()
        p.condition = 0.6                  # collective-held, below its mark
        _lease(p, L)
        assert p.condition == 1.0

    @pytest.mark.parametrize("fn", ["assess", "restore", "writedown"])
    def test_a_holder_reading_is_refused(self, fn):
        L, p = Ledger(0), _parcel()
        with pytest.raises(ValueError, match="register"):
            if fn == "assess":
                assess(p, 1.5, assessed_by="A")
            elif fn == "restore":
                collective_restore(p, 1.2, 10.0, ledger=L, assessed_by="A")
            else:
                declare_writedown(p, pre_event_condition=0.5, assessed_by="A")


class TestTheLoopCreatesNoMoney:
    """restore → private → destroy → abandon → collective → restore, many laps."""

    @pytest.mark.parametrize("degrade_to", [0.0, 0.4, 0.9])
    def test_settled_laps_net_to_zero(self, degrade_to):
        L, p = Ledger(0), _parcel()
        for _ in range(10):
            _lease(p, L)
            assess(p, degrade_to, assessed_by=REGISTER)
            exit_to_collective(p, ledger=L)
            gap = (1.0 - degrade_to) * reset_hours(p)
            collective_restore(p, 1.0, gap, ledger=L, assessed_by=REGISTER)
            assert p.condition == 1.0
        assert L.balance(Ledger.DESTRUCTION) > 0.0          # it did move money
        assert _net_created(L) == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.parametrize("can_pay_share", [0.0, 0.3, 1.0])
    def test_an_unpaid_debt_never_mints(self, can_pay_share):
        L, p = Ledger(0), _parcel()
        for _ in range(5):
            _lease(p, L)
            assess(p, 0.5, assessed_by=REGISTER)
            owed = 0.5 * reset_hours(p) * M
            exit_to_collective(p, ledger=L, holder_can_pay_teh=can_pay_share * owed)
            r = collective_restore(p, 1.0, 0.5 * reset_hours(p), ledger=L,
                                   assessed_by=REGISTER)
            assert r["trust_paid_hours"] == pytest.approx((1 - can_pay_share) * 0.5 * reset_hours(p))
        assert _net_created(L) <= 1e-9
        assert _net_created(L) == pytest.approx(0.0, abs=1e-6)

    def test_paper_improvement_mints_nothing(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L)
        assess(p, 1.5, assessed_by=REGISTER)            # gain, no hours logged
        assert exit_to_collective(p, ledger=L)["teh_minted"] == 0.0

    def test_hours_without_gain_mint_nothing(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L)
        log_improvement(p, 500.0)
        assert exit_to_collective(p, ledger=L)["teh_minted"] == 0.0

    def test_improvement_mints_the_lesser_and_raises_the_mark(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L)
        log_improvement(p, 1_000.0)
        assess(p, 1.3, assessed_by=REGISTER)
        out = exit_to_collective(p, ledger=L)
        assert out["improvement_hours_credited"] == pytest.approx(0.3 * reset_hours(p))
        assert out["teh_minted"] == pytest.approx(0.3 * reset_hours(p) * M)
        assert p.condition == 1.0
        # Degrading from the NEW mark and settling nets the improvement back out.
        _lease(p, L)
        assess(p, 0.7, assessed_by=REGISTER)
        exit_to_collective(p, ledger=L)
        assert _net_created(L) == pytest.approx(0.0, abs=1e-6)

    def test_only_a_register_writedown_creates_money(self):
        # A fire re-bases at 1, and restoring from the new base is improvement.
        L, p = Ledger(0), _parcel()
        declare_writedown(p, pre_event_condition=1.0, assessed_by=REGISTER)
        p.condition = 1.0
        collective_restore(p, 1.4, 0.4 * reset_hours(p), ledger=L, assessed_by=REGISTER)
        assert _net_created(L) == pytest.approx(0.4 * reset_hours(p) * M)


class TestExchangeCarriesTheParcel:

    def test_nothing_settles_and_the_last_holder_owes(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L, "A", bond=5.0)
        assess(p, 0.7, assessed_by=REGISTER)
        before = list(L.entries)
        exchange(p, "B")
        assert L.entries == before                # no posting at exchange
        assert (p.holder, p.condition, p.bond_teh) == ("B", 0.7, 5.0)
        out = exit_to_collective(p, ledger=L)
        assert out["holder"] == "B"
        assert out["debt_hours"] == pytest.approx(0.3 * reset_hours(p))


class TestTheWritedownErasesOnlyTheEvent:

    def test_the_holders_prior_damage_survives_the_fire(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L)
        declare_writedown(p, pre_event_condition=0.8, assessed_by=REGISTER)
        assert p.condition == 1.0
        out = exit_to_collective(p, ledger=L)
        assert out["debt_hours"] == pytest.approx(0.2 * reset_hours(p))


class TestTheBond:

    def test_it_pays_first_is_refunded_and_is_never_issuance(self):
        L, p = Ledger(0), _parcel()
        owed = 0.2 * reset_hours(p) * M
        _lease(p, L, bond=owed * 3)
        assert L.balance(BOND_ESCROW) == pytest.approx(owed * 3)
        assert L.balance(Ledger.ISSUANCE) == 0.0
        assess(p, 0.8, assessed_by=REGISTER)
        out = exit_to_collective(p, ledger=L, holder_can_pay_teh=0.0)
        assert out["teh_destroyed"] == pytest.approx(owed)
        assert out["bond_refunded"] == pytest.approx(owed * 2)
        assert L.balance(BOND_ESCROW) == pytest.approx(0.0)
        assert L.balances_to_zero()

    def test_the_default_bond_is_zero(self):
        L, p = Ledger(0), _parcel()
        _lease(p, L)
        assert p.bond_teh == 0.0 and L.entries == []


class TestUnpricedOwesAndMintsNothing:

    def test_no_sequence_no_money(self):
        L, p = Ledger(0), _parcel(seq=None)
        _lease(p, L)
        log_improvement(p, 100.0)
        assess(p, 0.0, assessed_by=REGISTER)
        out = exit_to_collective(p, ledger=L)
        assert (out["debt_hours"], out["teh_minted"]) == (0.0, 0.0)
        assert L.entries == []


class TestTheReservedFloor:

    def test_ground_over_the_whole_population(self):
        assert land_reserve_hectares(1.0e6) == pytest.approx(
            1.0e6 * BASKET_SHELTER_M2_PER_PERSON * COLLECTIVE_LAND_RESERVE_FACTOR / 1.0e4)
        assert land_reserve_hectares(1.0e6, factor=2.0) == pytest.approx(
            land_reserve_hectares(1.0e6) / 2.0)

    def test_a_lease_below_the_reserve_is_refused(self):
        p = _parcel(area_slu=100.0)                           # 1 ha
        with pytest.raises(ValueError, match="reserve"):
            enter(p, "A", ledger=Ledger(0), collective_held_ha=10.5, reserve_ha=10.0)
        enter(p, "A", ledger=Ledger(0), collective_held_ha=11.0, reserve_ha=10.0)
        assert p.holder == "A"


class TestTheFlatFeeHandsOverToTheGuf:

    def test_flat_until_the_guf_is_affordable(self):
        flat = default_flat_fee(80.0)
        assert flat == pytest.approx(GUF_AFFORDABILITY_THRESHOLD * 80.0)
        low = residential_fee(36.4, 80.0, flat)               # GUF > 25% of 80
        assert (low["regime"], low["charged"], low["burden"]) == ("flat", flat, False)
        high = residential_fee(24.8, 900.0, flat)
        assert (high["regime"], high["charged"]) == ("guf", 24.8)

    def test_a_flat_fee_above_falling_earnings_is_reported(self):
        assert residential_fee(36.4, 40.0, default_flat_fee(80.0))["burden"] is True

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_the_residential_guf_is_read_through_the_shipped_fee(self, eps):
        # ε enters through the GUF the caller passes; the hand-over is ε-free.
        from hours_eoh.land.guf import ground_use_fee
        guf = ground_use_fee(area_slu=2.5, location_value=0.75,
                             use_category="residential_primary", epsilon=eps)["guf_applied"]
        r = residential_fee(guf, guf / GUF_AFFORDABILITY_THRESHOLD, default_flat_fee(0.0))
        assert r["regime"] == "guf" and r["charged"] == guf
