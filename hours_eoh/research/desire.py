"""
Desire economy — interface stub, NOT implemented (reconciliation §9-item-6).

EXPERIMENTAL TIER — this module contains no mechanics. Every function raises
NotImplementedError. It exists to anchor, in code, the open problem the
historical autopsy named as HOURS' weakest area and reconciliation §7
isolated as a distinct domain: the *want* economy.

The need/want split (reconciliation §7)
---------------------------------------
Entropy obligations — the *need* economy — may consolidate as ε rises: the
Coasean boundary grows with automation, and the need economy tends toward
few-or-one collectives (research/coasean.py models this arc). Desire —
novelty, art, status, play — is different in kind:

    Desire is dispersed private knowledge that only something market-like
    discovers, and it stays polycentric by nature. Even a mono-for-need
    endpoint remains poly-for-want. (reconciliation §7)

So the want economy is not a residual of the need economy; it is a distinct
domain with its own open design questions (§9-item-6):

1. How are want-goods priced? The floor-price machinery (core/prices.py) is
   derived from entropy obligations and does not apply — there is no EOH
   register for a poem. Pure discovery? Denominated in need-economy TEH, or
   in its own units?
2. How does the want economy stay contestable? The contestability invariant
   (research/contestability.py) is defined against K_entry for *entropy
   resistance* capacity. What is the sunk cost of entering the want economy,
   and does the χ ≥ 1 machinery transfer?
3. Where is the boundary? Care labor has both need components (biological
   EOH) and want components (relational quality). The split is not clean.

Why a stub and not a model
--------------------------
These are theory decisions, not refactors (CLAUDE.md §3: author sign-off for
theory changes). Inventing want-economy mechanics here would silently extend
the framework beyond what the reconciliation has decided. The interface below
records the *shape* of the questions; the answers belong to the author.

Nothing imports this module. When the theory is settled, implementations
replace the raises and this docstring's status note changes.

Mission Statement: reconciliation §7 (need/want split); §9-item-6 (the
desire economy, "the gap the autopsy named as HOURS' weakest").
"""

from __future__ import annotations

_NOT_IMPLEMENTED_MSG = (
    "The desire economy is an open theory problem (reconciliation §9-item-6). "
    "This interface stub anchors the question in code; the mechanics await "
    "author-level design decisions. See the module docstring."
)


def want_economy_share(epsilon: float) -> float:
    """
    Fraction of total economic activity in the want economy at automation level ε.

    OPEN QUESTION (§9-item-6): as the need economy automates (ε → 1), does the
    want economy's share of human attention and exchange grow toward 1 (needs
    are met by machines, wants dominate what humans trade), or does it stay
    bounded? The answer shapes what "post-scarcity" means for the framework.

    Args:
        epsilon: Automation level [0.0, 0.99] — of the NEED economy. Desire
            has no ε of its own; whether it should is part of the question.

    Raises:
        NotImplementedError: always — no mechanics exist yet.
    """
    raise NotImplementedError(_NOT_IMPLEMENTED_MSG)


def want_price_discovery(
    good_id: str,
    bids: list[float],
    epsilon: float,
) -> dict:
    """
    Discovered price of a want-good — no floor exists.

    OPEN QUESTION (§9-item-6): want-goods have no EOH register and therefore
    no floor price. Pricing is pure discovery. What this function should
    return — a clearing price, a distribution, an auction mechanism — is a
    design decision, as is whether want-goods trade in need-economy TEH or in
    collective-specific units (reconciliation §6, the live design fork).

    Args:
        good_id: Identifier of the want-good (art, novelty, status, play).
        bids: Observed willingness-to-pay, in TEH.
        epsilon: Need-economy automation level (context, not driver).

    Raises:
        NotImplementedError: always — no mechanics exist yet.
    """
    raise NotImplementedError(_NOT_IMPLEMENTED_MSG)


def want_contestability(epsilon: float, regime: str = "increasing_returns") -> dict:
    """
    Contestability of the want economy — does χ ≥ 1 transfer?

    OPEN QUESTION (§9-item-6): the contestability invariant
    (research/contestability.py) prices exit as the sunk cost of founding
    independent *entropy-resistance* capacity. The want economy's entry cost
    is different — reputation, audience, network position — and may
    concentrate even harder than automated capital (winner-take-all cultural
    markets). Whether the χ machinery transfers, and what P and K_entry mean
    for a want-market entrant, is unresolved.

    Args:
        epsilon: Need-economy automation level.
        regime: Entry-cost regime hypothesis (mirrors contestability.py).

    Raises:
        NotImplementedError: always — no mechanics exist yet.
    """
    raise NotImplementedError(_NOT_IMPLEMENTED_MSG)
