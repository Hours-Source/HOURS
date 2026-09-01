"""
The confidence field: how much of a value is MEASURED rather than chosen.

WHY IT EXISTS (author decision, 2026-09-01). A placeholder is not a failure —
the arithmetic needs a number to run at all, and a number picked for a stated
reason is better than none. But `placeholder` is one word covering everything
from a bare guess to a value that has absorbed most of a measurement, and a
reader cannot tell those apart. `confidence: 0–100` does:

    0    picked so the arithmetic can run; nothing measured
    100  fully data-backed

**IT NEVER LICENSES A STRONGER TAG.** A constant at 70 is still a placeholder —
just a better-picked one. The guard is exactly that it cannot claim to be done.

WHY A LOW NUMBER IS STILL WORTH STATING. Everything downstream is fitted against
these constants, so a value that moves from 0% to 3% measured moves whatever is
fitted to it fractionally closer to something real, and a value at 70% moves it a
long way. An undocumented guess is a 0 that does not say so.

EVERY VALUE MUST SAY WHAT IS MEASURED AND WHAT IS NOT, or the figure is a second
guess layered on the first. `AGE_WEIGHT_CHILD` at 70 names both terms of its
ratio as measured and the definitional bridge as chosen; `ABATEMENT_HALF_CAPITAL_TEH`
at 5 says the order of magnitude is bounded and nothing else is.

IT IS A RATCHET, NOT A BLANKET RULE. 135 constants carry `placeholder` or
`bounded` and backfilling all of them at once would be inventing 131 more
numbers — the exact failure the field exists to expose. So the count WITHOUT a
confidence may not rise, and it falls as constants are revisited.
"""

from __future__ import annotations

import re

import pytest

from utils import provenance as pv

#: Tags for which a confidence figure is meaningful. `measured`, `derived`,
#: `physics` and `convention` are not on the list: their epistemic state is the
#: tag itself, and `normative` is a decision that no measurement settles.
SOFT_TAGS = frozenset({"placeholder", "bounded"})

#: Constants without a confidence figure, at the moment the field shipped. May
#: not RISE. Lowering it means revisiting a constant and stating what is
#: measured in it, which is real work and not a rename.
BASELINE_WITHOUT = 131

_LEAD = re.compile(r"^\s*(\d{1,3})\b")


def _soft_records() -> list[pv.Record]:
    scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
    return [r for r in scan.records if r.tag in SOFT_TAGS]


def _annotated() -> list[pv.Record]:
    return [r for r in _soft_records() if r.confidence]


class TestTheFieldIsWellFormed:

    def test_confidence_is_a_known_field(self) -> None:
        assert "confidence" in pv.FIELDS

    def test_every_value_leads_with_a_number_in_range(self) -> None:
        for record in _annotated():
            match = _LEAD.match(record.confidence)
            assert match, f"{record.name}: confidence must open with 0-100"
            value = int(match.group(1))
            assert 0 <= value <= 100, f"{record.name}: {value} out of range"

    def test_every_value_says_what_is_measured(self) -> None:
        """
        A bare number is a second guess layered on the first. The basis is what
        makes the figure auditable.
        """
        for record in _annotated():
            _, _, basis = record.confidence.partition(" ")
            assert len(basis.strip()) > 40, (
                f"{record.name}: confidence states a number without saying what "
                f"is measured and what is not"
            )

    def test_it_is_only_used_where_it_means_something(self) -> None:
        """
        `measured`, `derived`, `physics` and `convention` carry their epistemic
        state in the tag; `normative` is a decision no dataset settles, and its
        own rule already forbids a `resolves_by`. A confidence figure on any of
        those would be noise.
        """
        scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
        wrong = [
            r.name for r in scan.records
            if r.confidence and r.tag not in SOFT_TAGS
        ]
        assert not wrong, f"confidence on tags where it means nothing: {wrong}"


class TestItNeverLicensesAStrongerTag:
    """The guard the author asked for: a better pick is still a placeholder."""

    def test_a_high_confidence_placeholder_is_still_a_placeholder(self) -> None:
        high = [r for r in _annotated()
                if int(_LEAD.match(r.confidence).group(1)) >= 60]
        assert high, "expected at least one well-measured placeholder to exist"
        for record in high:
            assert record.tag in SOFT_TAGS
            assert record.resolves_by, (
                f"{record.name}: confidence {record.confidence[:3]} but no "
                f"resolves_by — a high figure does not mean it is done"
            )

    def test_the_scheme_says_so_where_a_reader_will_look(self) -> None:
        doc = " ".join((pv.__doc__ or "").split())
        assert "never licenses a stronger tag" in doc.lower()
        assert "0 is a number picked to let the arithmetic run" in doc


class TestTheRatchet:

    def test_the_unannotated_count_does_not_grow(self) -> None:
        without = [r for r in _soft_records() if not r.confidence]
        assert len(without) <= BASELINE_WITHOUT, (
            f"{len(without)} placeholder/bounded constants carry no confidence, "
            f"above the {BASELINE_WITHOUT} baseline. A new one must state what "
            f"is measured in it."
        )

    def test_the_baseline_is_honest_about_the_backlog(self) -> None:
        """
        `exercised` asserted alongside `passes`: if the scan stopped finding
        soft-tagged constants the ratchet would pass while checking nothing.
        """
        assert len(_soft_records()) >= 100
        assert len(_annotated()) >= 4

    def test_lowering_it_requires_real_work(self) -> None:
        """
        Documented rather than enforced, because it cannot be enforced: the
        ratchet cannot tell a considered figure from a typed one. What it can do
        is make adding one a visible act in a diff, which is the
        `_INNOCUOUS_NAMES` discipline — masking must be DECLARED.
        """
        import tests.test_confidence as mod
        assert "RATCHET, NOT A BLANKET RULE" in (mod.__doc__ or "")


class TestTheFiguresThatShipped:
    """
    Pinned as ORDERINGS, not levels. What matters is that the four constants
    this session touched are ranked by how much of each is actually measured.
    """

    def _value(self, name: str) -> int:
        record = next(r for r in _soft_records() if r.name == name)
        return int(_LEAD.match(record.confidence).group(1))

    def test_the_child_weight_is_the_best_measured_of_the_four(self) -> None:
        """Both terms of its ratio are measured; only the bridge is chosen."""
        assert self._value("AGE_WEIGHT_CHILD") > self._value("AGE_WEIGHT_INFANT")

    def test_the_infant_weight_ranks_below_it_and_the_reason_is_structural(self) -> None:
        """
        Its self-maintenance term is not merely unmeasured — for ages 0–2 it is
        already counted on the care-received side, so a survey of under-3s would
        not on its own close it.
        """
        record = next(r for r in _soft_records() if r.name == "AGE_WEIGHT_INFANT")
        assert "double-counted" in record.confidence or "double" in record.confidence

    def test_the_abatement_pace_is_near_zero_and_more_time_use_will_not_move_it(self) -> None:
        record = next(r for r in _soft_records()
                      if r.name == "ABATEMENT_HALF_CAPITAL_TEH")
        assert self._value("ABATEMENT_HALF_CAPITAL_TEH") <= 10
        assert "capital" in record.confidence.lower()
