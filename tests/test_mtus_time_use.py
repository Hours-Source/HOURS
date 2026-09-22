"""
The published MTUS activity frame, and the check that makes it evidence.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS FILE EXISTS. `utils/mtus_ingest.py` derived the ACT_* aggregations by
SOLVING against the file's own columns, because no codebook ships with the DATA.
That is true of the data and was once read as true of the STUDY — the labels are
published, and three of them were read on 2026-09-10. The whole 69-category
table was read on 2026-09-21.

A TRANSCRIBED TABLE IS NOT A MEASUREMENT. What makes it evidence is that summing
the published blocks reproduces the file's own aggregates, on data this repo
ships: `mtus_codes_by_sample.csv` (per-code) against `mtus_domestic_by_sample.csv`
(the ACT_* columns), both cut at ages 18-69, so they are commensurable. If a
label block is wrong, the sum misses.

These tests use ONLY committed extracts. The original verification ran against
`rawdata/` at ages 15+ and reached ratio 1.0000 on five samples; that data is
gitignored, so the check is re-expressed here against what ships.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import CHILDCARE_CODES_MTUS, COMPONENT_CODES_MTUS
from hours_eoh.reference import mtus_time_use as mtus

#: The published blocks, and the aggregate each must reproduce. These are the
#: four VERIFIED at ratio 1.0000 when the table was read, and none of them had
#: been identified before it.
#:
#: `undom` is DELIBERATELY ABSENT. `utils/mtus_ingest.py` records {18..25, 27}
#: as "exact on AM2008, 93% on KR2004", so it does not hold across samples;
#: an earlier version of this file asserted it anyway and failed, which is
#: asserting past what was measured — the block was never part of the 1.0000
#: verification. It stays out until someone measures it.
BLOCKS: tuple[tuple[str, tuple[int, ...], str], ...] = (
    ("work",   tuple(range(7, 15)),  "work_minutes_per_day"),
    ("educa",  tuple(range(15, 18)), "educa_minutes_per_day"),
    ("chcare", tuple(range(28, 32)), "chcare_minutes_per_day"),
    ("travel", tuple(range(62, 69)), "travel_minutes_per_day"),
)


def _domestic() -> dict[str, dict]:
    return {str(r["sample"]): r for r in mtus.domestic_by_sample()}


class TestTheFrameIsCompleteAndClosed:

    def test_every_code_from_1_to_69_is_labelled(self):
        assert set(mtus.ACTIVITY_LABELS) == set(range(1, 70))

    def test_no_label_is_empty(self):
        assert all(v.strip() for v in mtus.ACTIVITY_LABELS.values())

    def test_the_source_names_the_table_and_the_read(self):
        s = mtus.ACTIVITY_LABELS_SOURCE
        assert "69-category" in s and "2026-09-21" in s


class TestTheLabelsReproduceTheFilesOwnAggregates:
    """
    The claim is not that the labels were copied correctly. It is that the code
    sets they imply recover MTUS's own aggregates — which a wrong block cannot.
    """

    @pytest.mark.parametrize("name,codes,column", BLOCKS)
    def test_the_block_sums_to_its_aggregate(self, name, codes, column):
        dom = _domestic()
        checked = 0
        for sample, per_code in mtus.codes_by_sample().items():
            row = dom.get(sample)
            if row is None:
                continue
            target = float(row[column])
            if target <= 0.0:
                continue          # sample does not carry the aggregate
            got = sum(per_code.get(c, 0.0) for c in codes)
            assert got == pytest.approx(target, rel=2e-3), (
                f"{name} block {codes} misses {column} on {sample}: "
                f"{got:.4f} vs {target:.4f}"
            )
            checked += 1
        assert checked >= 40, f"only {checked} samples checked for {name}"

    def test_a_wrong_block_would_be_caught(self):
        """The check must be able to FAIL, or it certifies nothing."""
        dom = _domestic()
        sample, per_code = next(iter(mtus.codes_by_sample().items()))
        wrong = sum(per_code.get(c, 0.0) for c in range(7, 14))   # drops code 14
        target = float(dom[sample]["work_minutes_per_day"])
        assert wrong != pytest.approx(target, rel=2e-3)


class TestTheFrameAgreesWithTheShippedCodeSets:

    def test_childcare_codes_carry_their_published_labels(self):
        """
        A transcription pin, and a caution. An earlier version asserted that
        every childcare label contains "child"; code 29 is "Teach, help with
        homework" and names none. The block is evidence because it reproduces
        ACT_CHCARE, NOT because the words look right — reading the words is how
        the earlier MTUS session went wrong.
        """
        assert tuple(CHILDCARE_CODES_MTUS) == (28, 29, 30, 31)
        assert [mtus.ACTIVITY_LABELS[c] for c in CHILDCARE_CODES_MTUS] == [
            "Physical, medical child care",
            "Teach, help with homework",
            "Read to, talk or play with child",
            "Supervise, accompany, other child care",
        ]

    def test_nutrition_and_shelter_carry_theirs(self):
        assert mtus.ACTIVITY_LABELS[18] == "Food preparation, cooking"
        assert mtus.ACTIVITY_LABELS[20] == "Cleaning"
        for c in COMPONENT_CODES_MTUS["nutrition"] + COMPONENT_CODES_MTUS["shelter"]:
            assert c in mtus.ACTIVITY_LABELS

    def test_the_shelter_labels_are_selected_not_retyped(self):
        """`component_shares.MTUS_CODE_LABELS` must be a VIEW of this table."""
        from hours_eoh.scenarios.component_shares import MTUS_CODE_LABELS
        assert MTUS_CODE_LABELS == {
            c: mtus.ACTIVITY_LABELS[c] for c in COMPONENT_CODES_MTUS["shelter"]
        }


class TestThereIsNoHealthCategory:
    """
    PINNED AS A NEGATIVE FINDING, so a future session does not re-run the search.
    `data.py` says the health component "has no clean MTUS counterpart. Absent,
    not zero." Reading the published frame confirms it: no entry names medicine,
    health, a doctor or a hospital. The nearest is 25, which the guide's prose
    describes as receiving personal services "(e.g. visiting the hairdresser,
    doctor)" — the ATUS 0805 analogue this repo deliberately EXCLUDES.
    """

    def test_no_label_names_a_medical_activity_on_its_own(self):
        hits = {c: v for c, v in mtus.ACTIVITY_LABELS.items()
                if any(w in v.lower() for w in ("health", "doctor", "hospital", "medic"))}
        # 28 is "Physical, medical child care" — medical, but childcare, and it
        # is already spoken for by CHILDCARE_CODES_MTUS.
        assert set(hits) == {28}, f"unexpected medical-looking codes: {hits}"

    def test_the_nearest_candidate_is_a_bundled_services_code(self):
        assert mtus.ACTIVITY_LABELS[25] == "Consume personal care services"
