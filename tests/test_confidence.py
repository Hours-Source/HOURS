"""The confidence field: how much of a value is MEASURED rather than chosen.

WHY IT EXISTS (author decision, 2026-09-01). A placeholder is not a failure: the
arithmetic needs a number, and a number picked for a stated reason is better than none.
But `placeholder` covers everything from a bare guess to a value that holds most of a
measurement. `confidence: 0–100` tells them apart:

    0    picked so the arithmetic can run; nothing measured
    100  fully data-backed

**IT NEVER LICENSES A STRONGER TAG.** A constant at 70 is still a placeholder, only a
better-picked one.

Every value must say what is measured and what is not; otherwise the figure is a second
guess on top of the first. `AGE_WEIGHT_CHILD` at 70 names both terms of its ratio as
measured and the bridge between them as chosen. `ABATEMENT_HALF_CAPITAL_TEH` at 5 says
only the order of magnitude is bounded.

IT IS A RATCHET, NOT A BLANKET RULE. A backfill of every placeholder at once would
invent numbers, which is the failure the field exists to expose. So the count WITHOUT a
confidence may not rise, and it falls as constants are revisited
([record](record/provenance.md#confidence-test-history)).
"""

from __future__ import annotations

import re

import pytest

from utils import provenance as pv

#: Tags for which a confidence figure is meaningful. `measured`, `derived`,
#: `physics` and `convention` are not on the list: their epistemic state is the
#: tag itself, and `normative` is a decision that no measurement settles.
from utils.provenance import SOFT_TAGS  # noqa: E402 — one definition, shared with utils/census.py

#: Constants without a confidence figure. May not RISE. Lowering it means
#: revisiting a constant and stating what is measured in it, which is real work
#: and not a rename. 131 when the field shipped; 126 after the first leverage
#: review annotated the five biggest levers; 125 after the next.
#:
#: RAISED TO 133 ON 2026-09-09, AND THIS IS THE ONE MOVE THE RATCHET IS NOT
#: DESIGNED FOR, so the accounting is written out rather than asserted.
#:
#: Splitting the five registration sigmoids replaced 5 composite constants with
#: 20 fields. Under one tag each dict counted ONCE toward this baseline while
#: covering four numbers, so the old 125 was UNDERSTATING the backlog four-fold
#: across those five entries. The 20 land as 13 `placeholder`, 4 `normative` and
#: 3 `convention` — and the last seven are not awaiting measurement at all, which
#: the shared tag had also concealed.
#:
#:     125 − 5 (the dicts, now `derived`) + 13 (the fields that really are
#:     unmeasured) = 133
#:
#: NO NEW UNCERTAINTY WAS CREATED; uncertainty that was already there is now
#: counted where it lives. A ratchet that forbade this would penalise honest
#: disaggregation and reward leaving composites whole, which is the opposite of
#: what it is for — and the `29 dict/tuple constants` open item asks for exactly
#: this pass over the remaining composites, so the same move is expected again.
#: Each future raise states its own arithmetic here or it is not a raise, it is
#: a leak.
#: LOWERED TO 131 ON 2026-09-16, and a fall states its arithmetic for the same
#: reason a raise does — an unexplained move is a leak whichever way it runs.
#:
#: `DEFAULT_SEGMENTS` and `SKILL_DECAY_RATE` were retagged `placeholder` ->
#: `baseline`: both are refuted values kept RUNNABLE as comparisons, and
#: `placeholder` means "no measurement stands behind it", which was the opposite
#: of true. The measurement happened, it replaced them, and they are the control
#: it replaced. Neither carried a confidence figure, so both were in this count.
#:
#:     133 - 2 (retagged out of SOFT_TAGS entirely) = 131
#:
#: NO BACKLOG WAS CLEARED. Nothing was measured and nothing was annotated; two
#: constants stopped being counted as debt because they were never debt. The
#: same caution the 2026-09-09 raise states applies mirrored: a ratchet that let
#: retagging shed debt silently would reward relabelling over measuring, so the
#: tag carries its own gate (`compares:`, `expected:`, and the named test must
#: exist) and the arithmetic is written here.
#: LOWERED 131 -> 130 on 2026-10-04: COND_DECAY_SLOPE (placeholder, no
#: confidence) was RETIRED, replaced by BLS's age-efficiency curve, whose two
#: β are `convention` with a cited source — a placeholder replaced by a method.
#: LOWERED 130 -> 129 on 2026-10-15: US_REFERENCE_POPULATION (placeholder, no
#: confidence) closed at the 2024 Census and is `measured`.
#: LOWERED 129 -> 125 on 2026-10-16, four leaving the pool by the author's
#: retags (record/provenance.md#placeholders-audited): THERMAL_F_ALB measured at
#: IGCC 2025a, BASKET_THERMAL_DEGREE_DAYS_PER_YEAR `instance`, and
#: COASEAN_RESERVE_FRACTION / COASEAN_IMBALANCE_CEILING `normative`. The fifth
#: retag, GUF_WRITEDOWN_AMORTIZATION_YEARS to `bounded`, stays in the pool.
BASELINE_WITHOUT = 125

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
        """This docstring states the rule and no test enforces it: the ratchet cannot tell a considered
        figure from a typed one. It makes each new figure a visible act in a diff, as
        `_INNOCUOUS_NAMES` does.
        """
        import tests.test_confidence as mod
        assert "RATCHET, NOT A BLANKET RULE" in (mod.__doc__ or "")


class TestTheFiguresThatShipped:
    """These tests pin ORDERINGS, not levels. The finding is that confidence runs
    against leverage: the model's biggest levers are its least-measured constants.
    """

    def test_leverage_and_confidence_run_OPPOSITE(self):
        """The most leveraged constants carry the lowest confidence. PERSONAL_EOH_BASE
        (elasticity 0.94) is at 40, the GUF alpha pair (0.73, 0.59) at 10, and
        SERVICES_PRICE_DECLINE_EXPONENT (0.54) at 5. AGE_WEIGHT_CHILD, the best measured
        at 70, ranked sixth by leverage in the first review
        ([record](record/provenance.md#confidence-test-history)).
        """
        assert self._value("AGE_WEIGHT_CHILD") > self._value("PERSONAL_EOH_BASE")
        assert self._value("PERSONAL_EOH_BASE") > self._value("GUF_ALPHA_ZETA")
        assert self._value("GUF_ALPHA_ZETA") > self._value(
            "SERVICES_PRICE_DECLINE_EXPONENT"
        )

    def _value(self, name: str) -> int:
        record = next(r for r in _soft_records() if r.name == name)
        return int(_LEAD.match(record.confidence).group(1))

    def test_the_child_weight_is_the_best_measured_of_the_four(self) -> None:
        """Both terms of its ratio are measured; only the bridge is chosen."""
        assert self._value("AGE_WEIGHT_CHILD") > self._value("AGE_WEIGHT_INFANT")

    def test_the_infant_weight_ranks_below_it_and_the_reason_is_structural(self) -> None:
        """For ages 0–2 the self-maintenance term is already counted as care received. A
        survey of under-3s would therefore not close the gap by itself.
        """
        record = next(r for r in _soft_records() if r.name == "AGE_WEIGHT_INFANT")
        assert "double-counted" in record.confidence or "double" in record.confidence

    def test_the_abatement_pace_is_near_zero_and_more_time_use_will_not_move_it(self) -> None:
        record = next(r for r in _soft_records()
                      if r.name == "ABATEMENT_HALF_CAPITAL_TEH")
        assert self._value("ABATEMENT_HALF_CAPITAL_TEH") <= 10
        assert "capital" in record.confidence.lower()
