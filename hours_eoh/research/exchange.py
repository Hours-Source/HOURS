"""
Exchange accounting — a double-entry book for a federation of collectives.

SPDX-License-Identifier: AGPL-3.0-or-later

WHAT THIS IS FOR. `research/coasean.py` models the federation as an ECONOMICS
question: how many collectives, at what exchange rates, with what settlement
rules. This module asks the ACCOUNTING question underneath it — can every TEH in
that federation be traced to the labour that minted it or the mechanism that
destroyed it, with the books balancing at every step. Those are different
questions and they need different invariants. Economics asks whether a rate is
right; accounting asks whether the entries add up whatever the rate is.

WHY IT DOES NOT BUILD ON `make_federation`. The coasean factory exposes exactly
one heterogeneity lever — `ecosystem_health_schedule` — and the ecological domain
is ~0.00017% of total EOH, so every exchange rate it can produce is pinned at
parity to five decimal places:

    health spread 0.40 → 0.95, the whole plausible range:
        ε=0.20  rates ∈ [0.999993, 1.000007]
        ε=0.70  rates ∈ [0.999999, 1.000001]

That is the domain-balance defect seen from the exchange layer, and it is a
CONSTRUCTOR limitation rather than a broken price signal: build collectives that
differ in capital and the same parity equation gives rates spanning 0.67–1.49.
So this module takes its collectives from a declared FRAME and drives the core
pipeline directly.

THE FRAME IS THE PRECONDITION, NOT A CONVENIENCE. Population, land and capital
are all extensive: pairing one jurisdiction's population with another's land
silently rescales a domain, and this repo has found that defect six times, most
recently on the documented institutional intake path (`fiscal_snapshot`,
2026-08-20, 92.8× inside the implementation guide's own worked example). An
exchange rate is a RATIO of two collectives' per-capita output, so an undeclared
frame on either side lands directly in the rate with nothing to flag it.
`CollectiveFrame` therefore has no default land area — the frame must be stated.

STATUS: experimental, per `research/__init__.py`. The API is not stable.

Layer note: imports from `core/` and `data.py` only. Nothing in `core/`,
`land/` or `scenarios/` imports this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    COASEAN_IMBALANCE_CEILING,
    COASEAN_RESERVE_FRACTION,
    LAND_HECTARES_PER_CAPITA,
    TRUST_BASE_TEH,
)
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot

__all__ = [
    "CollectiveFrame",
    "Collective",
    "Entry",
    "Ledger",
    "FederationBook",
    "build_collective",
    "parity_rate",
    "rate_matrix",
    "n1_accounting_anchor",
]


# ---------------------------------------------------------------------------
# The frame
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CollectiveFrame:
    """
    The extensive quantities that must travel together, declared as one object.

    Governing rule (not an equation — a well-formedness condition):

        a frame is (population, land_hectares, capital_stock_teh) for ONE
        jurisdiction; no member may be taken from a different one.

    THE DEFECT THIS EXISTS TO PREVENT. Every one of the six instances this repo
    has found had the same shape: a caller scaled one quantity with `population`
    and let another resolve to a default keyed to a different jurisdiction. The
    ecological domain is the usual casualty because its default anchor is the
    whole contiguous US (765,495,267 ha) while the package default population is
    1e6 — a ratio of 335 that nothing connected. Bundling the three into a single
    frozen value makes the mismatch impossible to express rather than merely
    detectable after the fact.

    Units
    -----
    population        : persons
    land_hectares     : hectares under this collective's stewardship
    capital_stock_teh : TEH (labour-hours of embodied value)
    trust_balance     : TEH
    capital_age_ratio : dimensionless ∈ [0, 1] — mean age / design life
    ecosystem_health  : dimensionless ∈ [0, 1] — 1.0 = pristine

    `land_hectares` has NO DEFAULT. That is deliberate: a default here would
    reintroduce exactly the unstated pairing the class exists to refuse. Use
    `CollectiveFrame.per_capita_land(...)` if you genuinely only know a ratio —
    it makes the assumption a visible call rather than a silent fallback.

    Worked example
    --------------
    >>> f = CollectiveFrame(collective_id=0, population=5e6,
    ...                     land_hectares=12e6, capital_stock_teh=1e10)
    >>> round(f.capital_per_capita, 1)
    2000.0
    >>> round(f.hectares_per_capita, 1)
    2.4
    """

    collective_id:     int
    population:        float
    land_hectares:     float
    capital_stock_teh: float
    trust_balance:     float = TRUST_BASE_TEH
    capital_age_ratio: float = 0.50
    ecosystem_health:  float = 0.70
    label:             str = ""

    def __post_init__(self) -> None:
        for name in ("population", "land_hectares", "capital_stock_teh"):
            if getattr(self, name) <= 0.0:
                raise ValueError(
                    f"{name} must be > 0 — a frame with no {name} is not a "
                    f"jurisdiction, got {getattr(self, name)!r}"
                )
        if self.trust_balance < 0.0:
            raise ValueError(f"trust_balance must be >= 0, got {self.trust_balance!r}")
        for name in ("capital_age_ratio", "ecosystem_health"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v!r}")

    @classmethod
    def per_capita_land(
        cls,
        collective_id: int,
        population: float,
        hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
        **kwargs: Any,
    ) -> "CollectiveFrame":
        """
        Build a frame from a land RATIO rather than an absolute area.

        The default is the planetary average (~1.65 ha/person, world land ex
        Antarctica over world population) and is the WRONG number for any actual
        collective — it is offered so that a caller who has only a ratio states
        one explicitly instead of inheriting an anchor nobody chose.
        """
        return cls(
            collective_id=collective_id,
            population=population,
            land_hectares=population * hectares_per_capita,
            **kwargs,
        )

    @property
    def capital_per_capita(self) -> float:
        """TEH of capital per person — the intensity a frame holds fixed."""
        return self.capital_stock_teh / self.population

    @property
    def hectares_per_capita(self) -> float:
        """Hectares of stewarded land per person."""
        return self.land_hectares / self.population


# ---------------------------------------------------------------------------
# The collective
# ---------------------------------------------------------------------------

@dataclass
class Collective:
    """
    One collective: its frame, its ε, and one period's core-pipeline outputs.

    `pipeline` and `fiscal` are the unmodified returns of
    `core.eoh_fulfillment.eoh_to_teh_pipeline` and `core.fiscal.fiscal_snapshot`,
    both driven WITH the frame stated, so a single collective is exactly the
    single-ledger model and nothing else. That is what makes
    `n1_accounting_anchor()` a regression anchor rather than a re-implementation.
    """

    frame:    CollectiveFrame
    epsilon:  float
    pipeline: dict = field(default_factory=dict)
    fiscal:   dict = field(default_factory=dict)

    @property
    def collective_id(self) -> int:
        return self.frame.collective_id

    @property
    def teh_created(self) -> float:
        """TEH minted this period (registered EOH × mean multiplier)."""
        return float(self.pipeline["teh_created"])

    @property
    def teh_per_capita(self) -> float:
        """
        Per-capita output — the quantity an exchange rate is a ratio OF.

        Units: TEH per person per year. This is the intensive quantity, which is
        why the frame must be right: dividing one jurisdiction's output by
        another's population produces a per-capita figure belonging to neither.
        """
        return self.teh_created / self.frame.population

    @property
    def reserve(self) -> float:
        """
        TEH earmarked for inter-collective settlement (COASEAN_RESERVE_FRACTION).

        Held out of circulation, so it is a claim against this collective's own
        issuance rather than new money.
        """
        return self.teh_created * COASEAN_RESERVE_FRACTION


def build_collective(
    frame: CollectiveFrame,
    epsilon: float,
    **pipeline_kwargs: Any,
) -> Collective:
    """
    Run one period of the core pipeline for a declared frame.

    Governing chain (all of it in `core/`, none of it re-implemented here):

        total_eoh(frame)  →  human split at ε  →  registration  →  teh_created
        fiscal_snapshot(frame, ε)              →  levies, allocations, solvency

    THE FRAME IS PASSED TO BOTH CALLS, and the ecological obligation is passed
    from the first to the second by value (`eco_eoh_override`) rather than being
    recomputed. Recomputation is what allowed the two entry points to disagree by
    92.8× before 2026-08-20; passing the value makes divergence impossible rather
    than merely unlikely.

    ε-behaviour
    -----------
    ε=0.00 → registration is minimal, teh_created is small but positive
    ε=0.40 → reference point; teh_created near its arc maximum
    ε=0.99 → human labour near zero, teh_created collapses toward the floor

    Args:
        frame: The declared jurisdiction.
        epsilon: Automation level ∈ [0, 0.99].
        **pipeline_kwargs: Forwarded to `eoh_to_teh_pipeline`. Anything that
            would restate a frame quantity is refused rather than silently
            preferred — see Raises.

    Raises:
        ValueError: If `pipeline_kwargs` restates a quantity the frame owns.
            A frame that can be overridden piecemeal is not a frame.
    """
    owned = {
        "population", "capital_stock", "ecological_area_hectares",
        "ecological_base", "capital_age_ratio", "ecosystem_health",
    }
    clash = owned & set(pipeline_kwargs)
    if clash:
        raise ValueError(
            f"these are the frame's to state, not the caller's: {sorted(clash)}. "
            "Build a different CollectiveFrame instead of overriding one — a "
            "frame that can be overridden piecemeal is not a frame."
        )

    pipe = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=frame.population,
        capital_stock=frame.capital_stock_teh,
        capital_age_ratio=frame.capital_age_ratio,
        ecosystem_health=frame.ecosystem_health,
        ecological_area_hectares=frame.land_hectares,
        **pipeline_kwargs,
    )
    fisc = fiscal_snapshot(
        trust_balance=frame.trust_balance,
        labor_income=pipe["teh_created"],
        capital_stock_teh=frame.capital_stock_teh,
        capital_age_ratio=frame.capital_age_ratio,
        population=frame.population,
        epsilon=epsilon,
        ecosystem_health=frame.ecosystem_health,
        eco_eoh_override=pipe["eoh_by_domain"]["ecological"],
    )
    return Collective(frame=frame, epsilon=epsilon, pipeline=pipe, fiscal=fisc)


# ---------------------------------------------------------------------------
# Rates — the floor, and discovery above it
# ---------------------------------------------------------------------------

def parity_rate(a: Collective, b: Collective, premium: float = 0.0) -> float:
    """
    The FLOOR exchange rate between two collectives, with discovery above it.

    Governing equation:

        r(a, b) = [ teh_created(a)/pop(a) ] / [ teh_created(b)/pop(b) ] · (1 + premium)

    This is the exchange-rate analogue of the floor price (reconciliation §3):
    a computed reference the ledger can back, with discovered deviation layered
    on top. The parity leg is what the collectives' own measured output supports;
    `premium` is everything else — preference, reserves, balance of trade — and
    is supplied, never derived. The module does not pretend to discover it.

    Interpretation:
        r > 1 → one unit of a's TEH buys more than one unit of b's
        r = 1 → parity
        r < 1 → b's currency is the harder money

    Units: dimensionless (TEH_b per TEH_a).

    Worked example — the heterogeneity `make_federation` cannot express:
        two collectives, same population and land, capital 1e9 vs 4e9 TEH
        → r ≈ 0.67 at ε=0.40, against ≈ 1.000003 for the widest possible
          ecosystem-health spread.

    Raises:
        ValueError: If `premium` ≤ −1 (a rate cannot go non-positive).
    """
    if premium <= -1.0:
        raise ValueError(f"premium must be > -1, got {premium!r}")
    return (a.teh_per_capita / b.teh_per_capita) * (1.0 + premium)


def rate_matrix(
    collectives: Iterable[Collective],
    premiums: dict[tuple[int, int], float] | None = None,
) -> dict[tuple[int, int], float]:
    """
    All pairwise floor rates, keyed (id_i, id_j) for i ≠ j.

    Reciprocity holds exactly at zero premium — r(i,j) · r(j,i) == 1 to float
    precision — and is BROKEN by asymmetric premiums, which is correct: a premium
    is a claim about one direction of trade. `FederationBook.transfer` records the
    difference rather than assuming it away.
    """
    cs = list(collectives)
    prem = premiums or {}
    for pair, p in prem.items():
        if p <= -1.0:
            raise ValueError(f"premium for pair {pair} must be > -1, got {p!r}")
    return {
        (a.collective_id, b.collective_id): parity_rate(
            a, b, prem.get((a.collective_id, b.collective_id), 0.0)
        )
        for a in cs
        for b in cs
        if a.collective_id != b.collective_id
    }


# ---------------------------------------------------------------------------
# The book
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Entry:
    """
    One double-entry posting, in ONE collective's unit of account.

    Units: `amount` is TEH of the ledger's own collective. A cross-collective
    flow is TWO entries in TWO ledgers, never one entry spanning both — that is
    what makes the FX difference explicit instead of hidden in a rounding term.
    """

    debit:  str
    credit: str
    amount: float
    memo:   str = ""

    def __post_init__(self) -> None:
        if self.amount < 0.0:
            raise ValueError(
                f"amount must be >= 0, got {self.amount!r} — reverse the "
                "debit/credit pair instead of posting a negative"
            )
        if self.debit == self.credit:
            raise ValueError(f"debit and credit must differ, both are {self.debit!r}")


class Ledger:
    """
    A single-currency double-entry ledger for one collective.

    THE INVARIANT: every posting moves value between two accounts, so the signed
    balances always sum to exactly zero. Minting and destruction are not
    exceptions to this — they are postings against DECLARED contra-accounts
    (`issuance`, `destruction`), which is what lets the book state where every
    TEH came from and where it went instead of treating creation as an
    unexplained inflow.

    Account convention: debit POSITIVE, credit NEGATIVE. `issuance` therefore
    runs negative (it has supplied TEH to the economy) and `destruction` runs
    positive (it has absorbed TEH). Both are correct signs, not errors.

    Condition III (zero interest) is a property this ledger can CHECK but does
    not enforce by construction: balances change only by posting, so a balance
    that grew without an entry is impossible, and `condition_iii_holds()` tests
    that every credit into a member account is traceable to labour or transfer.

    Worked example
    --------------
    >>> L = Ledger(collective_id=0)
    >>> _ = L.mint(1000.0, "period 1 registered labour")
    >>> _ = L.destroy(150.0, "D2 consumption")
    >>> round(L.balance("circulation"), 6)
    850.0
    >>> L.balances_to_zero()
    True
    """

    ISSUANCE    = "issuance"
    DESTRUCTION = "destruction"
    CIRCULATION = "circulation"
    RESERVE     = "reserve"
    FX          = "fx_revaluation"

    def __init__(self, collective_id: int) -> None:
        self.collective_id = collective_id
        self.entries: list[Entry] = []
        #: TEH earmarked for settlement when the book was opened. The imbalance
        #: a ceiling applies to is the DEVIATION of the reserve from this, not
        #: the reserve itself — see FederationBook.settlement_report.
        self.earmarked: float = 0.0

    # -- posting ---------------------------------------------------------

    def post(self, debit: str, credit: str, amount: float, memo: str = "") -> Entry:
        """Record one posting. The only way a balance can change."""
        e = Entry(debit=debit, credit=credit, amount=amount, memo=memo)
        self.entries.append(e)
        return e

    def mint(self, amount: float, memo: str = "") -> Entry:
        """
        TEH enters circulation: registered EOH × mean multiplier.

        Debits circulation, credits issuance. The issuance account's growing
        negative balance IS the money supply, stated as a claim rather than
        appearing from nowhere.
        """
        return self.post(self.CIRCULATION, self.ISSUANCE, amount, memo or "mint")

    def destroy(self, amount: float, memo: str = "") -> Entry:
        """
        TEH leaves circulation via D1–D6 (write-down, consumption, estate, ceiling).

        Debits destruction, credits circulation.
        """
        return self.post(self.DESTRUCTION, self.CIRCULATION, amount, memo or "destroy")

    # -- reading ---------------------------------------------------------

    def balance(self, account: str) -> float:
        """Signed balance of one account: debits positive, credits negative."""
        total = 0.0
        for e in self.entries:
            if e.debit == account:
                total += e.amount
            if e.credit == account:
                total -= e.amount
        return total

    def accounts(self) -> set[str]:
        """Every account named by a posting. Malformed legs are skipped here and
        caught by `balances_to_zero`, which is where they should be reported."""
        out: set[str] = set()
        for e in self.entries:
            if e.debit:
                out.add(e.debit)
            if e.credit:
                out.add(e.credit)
        return out

    def trial_balance(self) -> dict[str, float]:
        """Every account and its signed balance — the readable form of the book."""
        return {a: self.balance(a) for a in sorted(self.accounts())}

    def balances_to_zero(self, tolerance: float = 1e-9) -> bool:
        """
        THE ACCOUNTING INVARIANT: every posting is two-legged and the signed
        balances sum to zero.

        THE WELL-FORMEDNESS CHECK IS THE REAL WORK, and it is here because the
        sum alone is close to an IDENTITY. `post()` writes both legs from one
        `Entry`, so the total is zero for any inputs — 200 random postings with
        arbitrary accounts and amounts still sum to zero. A test asserting only
        the sum guards the `Entry` type and the float accumulation, not the
        book. Checking that each entry actually HAS both legs is what would
        catch a future one-legged posting path, which is the realistic bug.

        (Found while reviewing this repo's tests on 2026-08-27 — the same shape
        as `epoch_alpha_weights`' sum-to-ALPHA_SCALE assertion, reproduced here
        in code written during that very review.)

        Scale-relative, because a federation at 1e10 TEH cannot be held to an
        absolute 1e-9: the tolerance is `tolerance × max(1, total posted)`.
        """
        for e in self.entries:
            if not getattr(e, "debit", None) or not getattr(e, "credit", None):
                return False
        posted = sum(e.amount for e in self.entries)
        return abs(sum(self.trial_balance().values())) <= tolerance * max(1.0, posted)

    def money_supply(self) -> float:
        """
        TEH outstanding = minted − destroyed = −balance(issuance) − balance(destruction).

        Equal to the sum of all non-contra account balances, which is the
        identity `test_money_supply_equals_the_real_accounts` pins.
        """
        return -self.balance(self.ISSUANCE) - self.balance(self.DESTRUCTION)


class FederationBook:
    """
    One `Ledger` per collective, plus the cross-collective postings between them.

    WHY NOT ONE LEDGER. Each collective's TEH is its own unit of account — that
    is what having an exchange rate MEANS. Summing them would be adding
    quantities in different units, the same category error as pairing one
    jurisdiction's population with another's land. So each book balances
    independently and a transfer posts a leg in each.

    THE HONEST CONSEQUENCE, stated rather than engineered away: at any rate ≠ 1
    the federation's TEH total is NOT conserved across a transfer. Sender parts
    with X, receiver gains X·r. This is a REVALUATION, not a leak, and it is
    booked to a declared `fx_revaluation` account on the receiving side so that
    both ledgers still balance to zero and the difference is nameable. A
    framework that quietly forced aggregate conservation here would be asserting
    a single currency while claiming to model several.

    Worked example
    --------------
    >>> book = FederationBook()
    >>> _, _ = book.open(0), book.open(1)
    >>> _ = book.ledger(0).mint(1000.0)
    >>> _ = book.transfer(0, 1, amount=100.0, rate=1.5, memo="trade")
    >>> book.all_balance()
    True
    >>> round(book.ledger(1).balance(Ledger.RESERVE), 6)
    150.0
    """

    def __init__(self) -> None:
        self.ledgers: dict[int, Ledger] = {}

    def open(self, collective_id: int) -> Ledger:
        """Open a book for a collective. Idempotent."""
        if collective_id not in self.ledgers:
            self.ledgers[collective_id] = Ledger(collective_id)
        return self.ledgers[collective_id]

    def ledger(self, collective_id: int) -> Ledger:
        return self.ledgers[collective_id]

    @classmethod
    def from_collectives(cls, collectives: Iterable[Collective]) -> "FederationBook":
        """
        Open a book per collective and mint each one's period output into it.

        The minted amount is `teh_created` straight from the core pipeline, and
        the reserve is moved out of circulation as a separate posting so that
        `circulation + reserve` reconstructs the total — the reserve is earmarked,
        not extra.
        """
        book = cls()
        for c in collectives:
            L = book.open(c.collective_id)
            L.mint(c.teh_created, f"period mint, ε={c.epsilon}")
            if c.reserve > 0.0:
                L.post(L.RESERVE, L.CIRCULATION, c.reserve, "settlement reserve")
                L.earmarked = c.reserve
        return book

    def transfer(
        self,
        sender: int,
        receiver: int,
        amount: float,
        rate: float,
        memo: str = "",
    ) -> dict[str, float]:
        """
        Move value between two collectives at a stated rate.

        Governing equations:

            sender leg  : reserve(sender)   −= amount
            receiver leg: reserve(receiver) += amount · rate
            fx booked   : amount · (rate − 1)      [receiver's fx_revaluation]

        Both ledgers still balance to zero afterwards; the asymmetry lives in a
        named account rather than in a discrepancy.

        Args:
            sender/receiver: collective ids; must differ and both be open.
            amount: TEH in the SENDER's unit. Must be > 0.
            rate: receiver-TEH per sender-TEH, from `parity_rate`. Must be > 0.

        Returns:
            dict with `sent`, `received`, `fx` — the three quantities a
            settlement report needs.
        """
        if sender == receiver:
            raise ValueError(f"sender and receiver must differ, both are {sender!r}")
        if amount <= 0.0:
            raise ValueError(f"amount must be > 0, got {amount!r}")
        if rate <= 0.0:
            raise ValueError(f"rate must be > 0, got {rate!r}")

        sl, rl = self.ledger(sender), self.ledger(receiver)
        note = memo or f"transfer {sender}->{receiver} @ {rate:.6f}"

        sl.post(sl.CIRCULATION, sl.RESERVE, amount, note)
        received = amount * rate
        rl.post(rl.RESERVE, rl.FX, received, note)

        return {"sent": amount, "received": received, "fx": received - amount}

    def all_balance(self, tolerance: float = 1e-9) -> bool:
        """Every collective's book balances independently."""
        return all(L.balances_to_zero(tolerance) for L in self.ledgers.values())

    def settlement_report(self) -> dict[int, dict[str, float]]:
        """
        Per-collective reserve position and its ceiling.

        `COASEAN_IMBALANCE_CEILING` caps a bilateral position as a fraction of
        the reserve; `breached` flags a collective whose net reserve movement has
        run past it. Reported, never enforced — the ceiling is a charter
        parameter and clamping it here would hide the state it exists to surface.
        """
        out: dict[int, dict[str, float]] = {}
        for cid, L in self.ledgers.items():
            reserve = L.balance(L.RESERVE)
            # THE IMBALANCE IS THE DEVIATION FROM THE EARMARK, NOT THE RESERVE.
            # Comparing the standing reserve against the ceiling made `breached`
            # fire for every collective AT REST, before any trade: the reserve is
            # COASEAN_RESERVE_FRACTION (0.10) of what was minted, while the
            # ceiling was COASEAN_IMBALANCE_CEILING x that (0.05), so the flag was
            # unconditionally true and said nothing. Failure mode 5 inverted — a
            # threshold that cannot help firing is as useless as one that cannot
            # fire. Found 2026-08-27 by asking of my own code the question that
            # audit asks of the shipped constants.
            imbalance = reserve - L.earmarked
            ceiling = COASEAN_IMBALANCE_CEILING * L.earmarked
            out[cid] = {
                "reserve": reserve,
                "earmarked": L.earmarked,
                "imbalance": imbalance,
                "fx_revaluation": L.balance(L.FX),
                "minted": -L.balance(L.ISSUANCE),
                "ceiling": ceiling,
                "breached": float(ceiling > 0.0 and abs(imbalance) > ceiling),
            }
        return out


# ---------------------------------------------------------------------------
# The regression anchor
# ---------------------------------------------------------------------------

def n1_accounting_anchor(
    epsilon: float = 0.40,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    trust_balance: float = TRUST_BASE_TEH,
    hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
) -> dict[str, Any]:
    """
    At N=1 this layer must reproduce the single-ledger model EXACTLY.

    This is the anchor the whole federation rests on: if one collective built
    through `CollectiveFrame` → `build_collective` → `FederationBook` does not
    agree to float precision with a direct `eoh_to_teh_pipeline` call at the same
    frame, then the exchange layer has introduced economics of its own, and any
    N>1 result is measuring the scaffold rather than the model.

    The frame here uses `hectares_per_capita` so the comparison call can be the
    package's own default path: `eoh_to_teh_pipeline` with no area resolves the
    area from population at exactly this ratio, so both sides describe one
    jurisdiction and the equality is meaningful rather than arranged.

    Returns:
        dict with `teh_created_delta`, `pipeline_match`, `solvent_match`,
        `book_balances`, `money_supply_match`, and both sides' raw values.
    """
    frame = CollectiveFrame.per_capita_land(
        collective_id=0,
        population=population,
        hectares_per_capita=hectares_per_capita,
        capital_stock_teh=capital_stock_teh,
        trust_balance=trust_balance,
    )
    coll = build_collective(frame, epsilon)

    ref = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=population,
        capital_stock=capital_stock_teh,
    )
    ref_fiscal = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=ref["teh_created"],
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=0.50,
        population=population,
        epsilon=epsilon,
        eco_eoh_override=ref["eoh_by_domain"]["ecological"],
    )

    book = FederationBook.from_collectives([coll])
    L = book.ledger(0)

    delta = abs(coll.teh_created - ref["teh_created"])
    return {
        "teh_created_delta":  delta,
        "pipeline_match":     delta < 1e-6,
        "solvent_match":      coll.fiscal["solvent"] == ref_fiscal["solvent"],
        "book_balances":      L.balances_to_zero(),
        "money_supply_match": abs(L.money_supply() - ref["teh_created"]) < 1e-6,
        "ref_teh_created":    ref["teh_created"],
        "fed_teh_created":    coll.teh_created,
        "ref_solvent":        ref_fiscal["solvent"],
        "fed_solvent":        coll.fiscal["solvent"],
        "federation_n":       1,
    }
