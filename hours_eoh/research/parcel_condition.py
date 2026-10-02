"""
research/parcel_condition — WHO PAYS FOR WHAT A HOLDER DOES TO LAND.

The Phase 4 partition moved ecology to the Ground Use Fee so that destroying
land cannot mint. Land the collective holds does mint when restored, which
opens a loop (author, 2026-10-01):

    restore (mints) → private (GUF) → destroy → abandon → collective → restore (mints) → …

Every lap would create TEH and nobody would pay for the damage. This module is
the author's answer, decided 2026-10-01 (`notes/parcel-condition-bond.md`):

    * THE CONDITION INDEX STARTS AT 1. Every parcel enters at 1 = its current
      function, read by THE REGISTER, never the holder. No history is
      reconstructed. It falls when the parcel degrades and rises when it improves.
    * EXCHANGE CARRIES THE PARCEL. A transfer between holders settles nothing:
      the index, the logged improvement hours, the bond and the ongoing GUF
      pass to the new holder.
    * EXIT TO THE COLLECTIVE SETTLES TO 1. Below 1 the holder owes the
      restoration, in HOURS, converted at settlement and destroyed through the
      CAPITAL WRITE-DOWN (`core.capital.execute_writedown`, D1) — "for now, in
      future work shows a better path". The bond pays first; what neither
      covers is restored FROM THE TRUST AND NEVER MINTED. Above 1 the
      improvement MINTS TO THE HOLDER — the lesser of the condition gain priced
      in restoration hours and the improvement hours actually logged — and the
      mark rises.
    * A WRITE-DOWN RESETS TO 1. An exogenous event (wildfire, flood), declared
      by the register, re-bases the parcel at its post-event state. Damage the
      holder did before it is crystallised and owed at exit.
    * A RESERVED FLOOR of collective land, ground over the whole population,
      `COLLECTIVE_LAND_RESERVE_FACTOR` × the basket's shelter area per person.
      A lease that would take collective land below it is refused.
    * A FLAT RESIDENTIAL FEE at low ε, instanced, with the GUF taking over once
      it is affordable (`GUF_AFFORDABILITY_THRESHOLD` of earnings).
    * BOND AND UNPRICED RESTORATION DEFAULT TO 0, open to change when work
      shows what is needed. A parcel with no priced restoration sequence owes
      and mints nothing.

THE INVARIANT (`tests/test_parcel_condition.py`): over any sequence that
returns a parcel to the same physical condition, net TEH created is ZERO —
whether the holder settles (destruction matched by the restoration's mint) or
the Trust bears it (neither destroyed nor minted: a transfer out of the Trust,
which this ledger does not post). A register-declared write-down is the only
door that creates net TEH, and it is an honest loss.

THE MINT. Improvement and restoration TEH are computed by `teh_created`, the
one mint formula, and posted to a `research.exchange.Ledger`. The one-mint gate
(`tests/test_one_mint_path.py`) scans core/, land/ and scenarios/; this module
is research and outside it. Promoting it would add a second mint call site,
which is a monetary-architecture decision, not a refactor — the gate will say so.

NOT BUILT HERE (Phase C): the GUF does not yet read the condition index. The
flow (services lost each year while degraded) and the stock (the exit debt)
are two charges, and `soil_health_credit` already credits improvement while
held; wiring the index into the fee needs that netting decided first
(failure mode 11).

RESEARCH ONLY — not imported by core/, land/ or scenarios/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hours_eoh.core.capital import execute_writedown
from hours_eoh.core.eoh_fulfillment import teh_created
from hours_eoh.data import (
    BASKET_SHELTER_M2_PER_PERSON,
    COLLECTIVE_LAND_RESERVE_FACTOR,
    GUF_AFFORDABILITY_THRESHOLD,
    M2_PER_HECTARE,
    MEAN_MULTIPLIER_REFERENCE,
    SLU_HECTARES,
)
from hours_eoh.reference.restoration import restoration_hours_per_hectare
from hours_eoh.research.exchange import Ledger

#: The only assessor whose readings the module accepts.
REGISTER: str = "register"
#: The escrow account a bond is held in. A liability, never a Trust inflow.
BOND_ESCROW: str = "bond_escrow"
#: The mark every settled parcel reads.
MARK: float = 1.0


@dataclass
class ParcelLease:
    """
    One parcel's condition record. `parcel` is the standard GUF parcel dict
    (`land/collective.py` schema: `area_slu`, `location_value`, `use_category`,
    …), so the same record prices the fee.

    `sequence` names a `reference.restoration` sequence; None is UNPRICED and
    owes and mints nothing (author, 2026-10-01: unpriced is 0).
    """
    parcel: dict[str, Any]
    sequence: str | None = None
    condition: float = MARK
    holder: str | None = None                  # None = collective-held
    improvement_hours: float = 0.0             # logged on the PARCEL; carries on exchange
    bond_teh: float = 0.0
    pending_debt_hours: float = 0.0            # crystallised at a write-down during a lease
    restoration_credit_hours: float = 0.0      # settled debt — restorable WITH minting
    trust_borne_hours: float = 0.0             # unsettled debt — restored from the Trust, never minted
    history: list[dict] = field(default_factory=list)

    @property
    def area_ha(self) -> float:
        return float(self.parcel["area_slu"]) * SLU_HECTARES


def _require_register(assessed_by: str) -> None:
    if assessed_by != REGISTER:
        raise ValueError(
            f"condition is read by the register, not {assessed_by!r} — a "
            f"holder's own reading is how an entry is low-balled")


def reset_hours(lease: ParcelLease, corner: str = "high") -> float:
    """
    Hours to move this parcel's condition by one whole mark (1.0 of the index):
    the sequence's lifetime hours per hectare × area. 0.0 when unpriced.

    `debt = (1 − c) × reset_hours` is LINEAR in the index — a declared choice;
    deep degradation probably costs disproportionately.
    """
    if lease.sequence is None:
        return 0.0
    r = restoration_hours_per_hectare(lease.sequence)
    return float(r[f"lifetime_h_per_ha_{corner}"]) * lease.area_ha


def assess(lease: ParcelLease, condition: float, assessed_by: str) -> ParcelLease:
    """The register's reading, relative to the parcel's mark."""
    _require_register(assessed_by)
    if condition < 0.0:
        raise ValueError(f"condition must be >= 0, got {condition}")
    lease.condition = float(condition)
    lease.history.append({"event": "assess", "condition": lease.condition})
    return lease


def land_reserve_hectares(
    population: float,
    factor: float = COLLECTIVE_LAND_RESERVE_FACTOR,
) -> float:
    """
    Ground the collective holds back from private lease: every member's shelter
    area × `factor`, over the WHOLE population (author, 2026-10-01).

    units: hectares. ε-behaviour: none — a floor on land, not on automation.
    """
    if population < 0.0 or factor < 0.0:
        raise ValueError("population and factor must be >= 0")
    return population * BASKET_SHELTER_M2_PER_PERSON * factor / M2_PER_HECTARE


def enter(
    lease: ParcelLease,
    holder: str,
    *,
    ledger: Ledger,
    collective_held_ha: float,
    reserve_ha: float,
    bond_teh: float = 0.0,
) -> ParcelLease:
    """
    Lease a collective-held parcel to `holder`.

    Refused if it would take collective-held land below `reserve_ha`. The entry
    reads 1 at the parcel's CURRENT state: a parcel leased while below its mark
    is re-based, and the restoration it was owed is dropped with it (already
    destroyed TEH stays destroyed — conservative).
    """
    if lease.holder is not None:
        raise ValueError(f"{lease.parcel.get('parcel_id')} is held by {lease.holder}; use exchange()")
    if collective_held_ha - lease.area_ha < reserve_ha:
        raise ValueError(
            f"lease refused: collective land would fall to "
            f"{collective_held_ha - lease.area_ha:.4f} ha, below the reserve {reserve_ha:.4f} ha")
    if bond_teh < 0.0:
        raise ValueError("bond must be >= 0")
    lease.holder = holder
    lease.condition = MARK
    lease.improvement_hours = 0.0
    lease.pending_debt_hours = 0.0
    lease.restoration_credit_hours = 0.0
    lease.trust_borne_hours = 0.0
    lease.bond_teh = float(bond_teh)
    if bond_teh > 0.0:
        ledger.post(BOND_ESCROW, Ledger.CIRCULATION, bond_teh, f"bond {lease.parcel.get('parcel_id')}")
    lease.history.append({"event": "enter", "holder": holder, "bond_teh": bond_teh})
    return lease


def exchange(lease: ParcelLease, new_holder: str) -> ParcelLease:
    """
    Transfer between holders. NOTHING SETTLES: the index, the logged improvement
    hours, the bond and the ongoing GUF pass to `new_holder` (author,
    2026-10-01). The register's current reading is what the buyer takes on.
    """
    if lease.holder is None:
        raise ValueError("collective-held: use enter()")
    lease.history.append({"event": "exchange", "from": lease.holder, "to": new_holder,
                          "condition": lease.condition})
    lease.holder = new_holder
    return lease


def log_improvement(lease: ParcelLease, hours: float) -> ParcelLease:
    """Improvement work done on a held parcel, logged on the parcel."""
    if lease.holder is None:
        raise ValueError("collective work is registered at collective_restore()")
    if hours < 0.0:
        raise ValueError("hours must be >= 0")
    lease.improvement_hours += hours
    return lease


def exit_to_collective(
    lease: ParcelLease,
    *,
    ledger: Ledger,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    holder_can_pay_teh: float = float("inf"),
    corner: str = "high",
) -> dict:
    """
    Return a held parcel to the collective and settle it to 1.

    Below the mark: debt hours = pending + (1 − c) × reset, valued at settlement
    as `teh_created(hours, m)` — the TEH restoring them will mint — and destroyed
    through `execute_writedown`, bond first, then the holder up to
    `holder_can_pay_teh`. What is paid becomes `restoration_credit_hours`; what
    is not is `trust_borne_hours`.

    Above the mark: mints `teh_created(min(gain hours, logged hours), m)` to the
    holder, and the mark rises.

    Returns the settlement, including `teh_minted` and `teh_destroyed`.
    """
    if lease.holder is None:
        raise ValueError("already collective-held")
    holder = lease.holder
    reset = reset_hours(lease, corner)
    debt_hours = lease.pending_debt_hours + max(0.0, MARK - lease.condition) * reset
    debt_teh = teh_created(debt_hours, mean_multiplier)

    paid_teh = 0.0
    from_bond = min(lease.bond_teh, debt_teh)
    from_holder = min(max(0.0, holder_can_pay_teh), debt_teh - from_bond)
    if debt_teh > 0.0:
        paid_teh = execute_writedown({
            "asset_id": f"land_condition:{lease.parcel.get('parcel_id')}",
            "asset_type": "land_condition",
            "teh_value": from_bond + from_holder,
            "annual_eoh": 0.0,
        })["teh_destroyed"]
        if from_bond > 0.0:
            ledger.post(Ledger.DESTRUCTION, BOND_ESCROW, from_bond, "bond settles exit debt")
        if from_holder > 0.0:
            ledger.destroy(from_holder, "holder settles exit debt (D1)")
    refund = lease.bond_teh - from_bond
    if refund > 0.0:
        ledger.post(Ledger.CIRCULATION, BOND_ESCROW, refund, "bond returned")

    paid_hours = debt_hours * (paid_teh / debt_teh) if debt_teh > 0.0 else 0.0
    unpaid_hours = debt_hours - paid_hours

    gain_hours = max(0.0, lease.condition - MARK) * reset
    credit_hours = min(gain_hours, lease.improvement_hours)
    minted = teh_created(credit_hours, mean_multiplier)
    if minted > 0.0:
        ledger.mint(minted, f"improvement on exit to {holder}")

    if lease.condition > MARK:
        lease.condition = MARK                      # the mark rises
    lease.restoration_credit_hours += paid_hours
    lease.trust_borne_hours += unpaid_hours
    lease.pending_debt_hours = 0.0
    lease.improvement_hours = 0.0
    lease.bond_teh = 0.0
    lease.holder = None
    out = {
        "holder": holder, "debt_hours": debt_hours, "debt_teh": debt_teh,
        "teh_destroyed": paid_teh, "trust_borne_hours": unpaid_hours,
        "improvement_hours_credited": credit_hours, "teh_minted": minted,
        "bond_refunded": refund,
    }
    lease.history.append({"event": "exit", **out})
    return out


def collective_restore(
    lease: ParcelLease,
    to_condition: float,
    hours_worked: float,
    *,
    ledger: Ledger,
    assessed_by: str,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    corner: str = "high",
) -> dict:
    """
    Registered restoration of a collective-held parcel, read by the register.

    Hours go first to the gap below the mark: they MINT only against settled
    debt (`restoration_credit_hours`) and are otherwise paid from the Trust,
    never minted. Hours above the mark are improvement and mint the lesser of
    the gain and the hours worked; the mark then rises.
    """
    _require_register(assessed_by)
    if lease.holder is not None:
        raise ValueError("held parcels improve through log_improvement()")
    if hours_worked < 0.0:
        raise ValueError("hours must be >= 0")
    reset = reset_hours(lease, corner)
    c0, c1 = lease.condition, float(to_condition)
    below = max(0.0, min(c1, MARK) - c0) * reset
    above = max(0.0, c1 - max(c0, MARK)) * reset

    to_below = min(hours_worked, below)
    minted_below = min(to_below, lease.restoration_credit_hours)
    trust_paid = to_below - minted_below
    lease.restoration_credit_hours -= minted_below
    lease.trust_borne_hours = max(0.0, lease.trust_borne_hours - trust_paid)
    minted_above = min(hours_worked - to_below, above)

    minted = teh_created(minted_below + minted_above, mean_multiplier)
    if minted > 0.0:
        ledger.mint(minted, "registered collective restoration")
    lease.condition = MARK if c1 >= MARK else c1
    out = {"minted_hours": minted_below + minted_above, "teh_minted": minted,
           "trust_paid_hours": trust_paid}
    lease.history.append({"event": "collective_restore", **out})
    return out


def declare_writedown(
    lease: ParcelLease,
    *,
    pre_event_condition: float,
    assessed_by: str,
    corner: str = "high",
) -> ParcelLease:
    """
    An exogenous loss declared BY THE REGISTER re-bases the parcel at 1.

    During a lease, damage the holder did before the event (the register's
    `pre_event_condition`) is crystallised as `pending_debt_hours`, owed at
    exit — the event erases only the event. Restoration from the new base is
    improvement. Settled credit and Trust-borne hours below the OLD mark lapse
    with it (destroyed TEH stays destroyed — conservative).
    """
    _require_register(assessed_by)
    if lease.holder is not None:
        lease.pending_debt_hours += max(0.0, MARK - pre_event_condition) * reset_hours(lease, corner)
    lease.condition = MARK
    lease.restoration_credit_hours = 0.0
    lease.trust_borne_hours = 0.0
    lease.history.append({"event": "writedown", "pre_event_condition": pre_event_condition})
    return lease


def default_flat_fee(earned_per_residential_parcel: float) -> float:
    """
    The instanced flat residential fee's default: the affordable share of what a
    residential parcel's occupants earn at the collective's founding state,
    `GUF_AFFORDABILITY_THRESHOLD × earned`. Computed ONCE and stated by the
    collective — not re-read each period, or it would be a cap, not a flat fee.
    """
    return GUF_AFFORDABILITY_THRESHOLD * max(0.0, earned_per_residential_parcel)


def residential_fee(
    guf_applied: float,
    earned_per_residential_parcel: float,
    flat_fee: float,
) -> dict:
    """
    What a residential holder pays: the GUF once it is affordable
    (≤ `GUF_AFFORDABILITY_THRESHOLD` of earnings), the instanced flat fee
    before. `burden` reports a flat fee that is itself above the threshold —
    a collective whose earnings fell after it set the fee.
    """
    affordable = GUF_AFFORDABILITY_THRESHOLD * max(0.0, earned_per_residential_parcel)
    regime = "guf" if guf_applied <= affordable else "flat"
    charged = guf_applied if regime == "guf" else flat_fee
    return {"charged": charged, "regime": regime, "affordable": affordable,
            "burden": charged > affordable}
