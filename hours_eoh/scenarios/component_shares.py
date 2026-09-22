"""
The personal obligation's four components, measured against observed time use —
and why it is a BOUND rather than a closure.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. `PERSONAL_EOH_COMPONENTS` is untouched and
`TestComponentSharesChangeNothing` fails the moment that stops being true.

WHAT THIS IS FOR. Phase 2's headline — the human fraction at ε=0.99 is 10.2×
the uniform figure — is weighted by care's **62.1% share of the personal
obligation**, and that share is a `placeholder`: the desk estimate's own four
terms, 208/156/208/936 over 1508. So the pending Phase 2 sign-off rests on a
number nothing measures. This module asks what the one instrument the repo owns
says about it.

WHAT IT FINDS. At the shipped defaults (ATUS 2025, the latest comparable year)
and under the mapping declared below, care is **25.7%** of mapped personal time
— 0.41× the desk share — and shelter 35.6% against a desk 10.3%. At the observed
care share Phase 2's factor is **4.82×** rather than 10.22×. Every figure quoted
in this module is pinned live by `TestTheQuotedFiguresAreStillTrue`.

WHY THAT IS A BOUND AND NOT A REPLACEMENT — THREE REASONS, AND THE THIRD IS
DECISIVE:

  1. OBSERVED IS NOT OBLIGATION. `observed = obligation − deferred + extraction`
     is the identification problem `scenarios/personal_floor` states; one
     observable, three unknowns.
  2. ONE COUNTRY, ONE DEVELOPMENT LEVEL. The desk shares are the obligation at
     AUTARKY. ATUS measures a high-capital society.
  3. **CARE HAS BEEN MARKETISED, and it moves the result in exactly this
     direction.** Daycare and residential elder care shift care out of unpaid
     time use into paid employment, and ATUS codes 03/04 count unpaid care only.
     So observed unpaid care UNDERSTATES the care obligation in a rich country —
     which is precisely the finding. The confound cannot be separated with this
     data, so the observed share is a LOWER bound on care's true share and the
     4.82× is a LOWER bound on Phase 2's factor.

THE ABATABILITIES CANNOT BE REACHED AT ALL, and their own pointers say why:
every one names cross-development variation (WHO/UNICEF JMP, GBD, "across
development levels"). `ABATEMENT_HALF_CAPITAL_TEH` is worse — its `resolves_by`
wants two or more CAPITAL levels, and 22 years of US deepening is 22 points at
one saturated level.

ONE ACQUISITION CLOSES ALL OF IT, and the repo has already named it three times
(`reference/atus_time_use`, `docs/theory/prior_art`, `AGE_WEIGHT_INFANT`): a
cross-country time-use panel spanning development levels — HETUS/MTUS. It would
settle the component shares, the abatabilities, K_half, the extraction wedge and
the infant age-weight band together.

Layer: scenarios/ — imports core/, data and reference/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.data import (
    CARE_AUTOMATION_FLOOR,
    COMPONENT_CODES_MTUS,
    PERSONAL_EOH_COMPONENTS,
)
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.reference import mtus_time_use as mtus

__all__ = [
    "COMPONENT_CODES",
    "EXCLUDED_CODES",
    "observed_shares",
    "share_comparison",
    "abatability_direction",
    "phase_2_sensitivity",
    "shares_report",
    "SHELTER_DESTINATIONS",
    "SHELTER_DESTINATION_VOCAB",
    "shelter_decomposition",
    "SHELTER_MTUS_HYPOTHESES",
    "SHELTER_MTUS_GUESSES",
    "MTUS_CODE_LABELS",
    "MTUS_LABELS_SOURCE",
    "shelter_frame_check",
]

#: THE ASSUMED MAPPING — one declared judgement, isolated so it can be argued
#: with, on the `STEWARDSHIP_ATTRIBUTIONS` and `SCALING_BASIS` precedent. ATUS
#: tier-2 activity codes onto the four components of the personal obligation.
#:
#: Nothing in ATUS is coded by "obligation component"; this is an attribution and
#: not a measurement. The measured inputs are the hours.
#:
#: `0399` and `0499` are ATUS residual "other" categories and are absent from
#: some survey years entirely (17/22 and 18/22) because nobody reported the
#: activity. They are kept — a category with zero reported time is zero, not
#: missing — and the accessor returns 0.0 for a code the year does not carry.
COMPONENT_CODES: dict[str, tuple[str, ...]] = {
    # Caring for and helping household (03*) and non-household (04*) members.
    "care": ("0301", "0302", "0303", "0304", "0305", "0399",
             "0401", "0402", "0403", "0404", "0405", "0499"),
    # Food and drink preparation, presentation and clean-up.
    "nutrition": ("0202",),
    # Interior/exterior upkeep of the dwelling and its equipment.
    "shelter": ("0201", "0203", "0204", "0207", "0208"),
    # Health-directed time: children's health, and medical/care services.
    "health": ("0303", "0804"),
}

#: EXCLUDED, NOT ASSIGNED — the discipline `personal_statutory_floor`
#: established. Each is real time that plausibly serves the obligation and
#: cannot be attributed to ONE component without inventing a split.
EXCLUDED_CODES: dict[str, str] = {
    "0205": "lawn, garden and houseplants — amenity, shelter upkeep, or food production",
    "0206": "animals and pets — not a component of the human obligation as defined",
    "0209": "household management — overhead across all four, no basis to split it",
    "0701": "consumer purchases — groceries sit inside a total dominated by other retail",
    "0805": "personal care services — self-maintenance rather than an obligation component",
}

#: `0303` (children's health) is DELIBERATELY in both `care` and `health`. It is
#: care delivered FOR a health purpose and either attribution is defensible, so
#: the overlap is declared rather than resolved by fiat. It is ~2 h/person·yr
#: against a mapped total near 745, so no reported figure turns on it — and
#: `share_comparison` reports the overlap so a reader can see it is small.
_OVERLAPPING = ("0303",)


#: WHERE EACH HOUR OF THE SHELTER COMPONENT PHYSICALLY BELONGS — the second
#: declared judgement in this module, isolated on the same precedent as
#: `COMPONENT_CODES` above, `STEWARDSHIP_ATTRIBUTIONS` and `SCALING_BASIS`.
#:
#: WHY IT EXISTS. The basket's shelter component is quantified in m² AND
#: degree-days, and 85% of what its code set measures is interior cleaning and
#: laundry — which scale with area and occupancy and not with degree-days at all.
#: Cleaning a house does not get harder when it is cold. The component's quantity
#: and its measured delivery are answering different questions, and no single
#: `hours_per_unit` can carry both. This table is what makes that visible, and it
#: is what a boundary decision should cite instead of an estimate.
#:
#: THE FOUR DESTINATIONS, and each is a different disposal:
#:   "structure"    envelope repair and improvement. ALREADY charged by
#:                  `infrastructure_eoh`: `capital_inventory` carries $34.4T of
#:                  private residential structures on the `building` profile, so
#:                  these hours are the one genuine overlap with another domain.
#:   "thermal"      the residual heat balance — the body-heat / R-value /
#:                  degree-days chain. The ONLY part the degree-days intensity
#:                  governs.
#:   "not_shelter"  in the code set and not the component. Vehicle repair is
#:                  transport capital; it double-counts nothing, because consumer
#:                  durables are excluded BY NAME from `capital_inventory`.
#:   "upkeep"       cleaning, laundry, appliances, textiles, storage. Scales with
#:                  area and occupancy. This is what the component actually is.
#:
#: THIS IS AN ATTRIBUTION, NOT A MEASUREMENT. The hours are measured; which
#: destination a 6-digit code serves is argued. Disagree with a row by editing
#: the row.
#:
#: MEASURED ON ATUS, WHICH IS THE WRONG FRAME FOR A FLOOR and the caveat is not
#: decoration: the shares below are US, high-capital. A collective that burns
#: wood and hauls water plausibly spends far more of its shelter time on the
#: thermal line and far less on laundry, and the thermal share is exactly the one
#: that would rise. MTUS codes (20,21,22) are the frame-consistent source and
#: this composition has NOT been checked against them.
SHELTER_DESTINATIONS: dict[str, str] = {
    # 0201 — household interior
    "020101": "upkeep",       # interior cleaning
    "020102": "upkeep",       # laundry
    "020103": "upkeep",       # sewing, repairing and maintaining textiles
    "020104": "upkeep",       # storing interior household items, incl. food
    "020199": "upkeep",       # household interior, n.e.c.
    # 0203 — interior maintenance, repair and decoration
    "020301": "structure",    # interior arrangement, decoration and repairs
    "020302": "structure",    # building and repairing furniture
    "020303": "thermal",      # heating and cooling
    "020399": "structure",    # interior maintenance, n.e.c.
    # 0204 — exterior maintenance, repair and decoration
    "020401": "upkeep",       # exterior cleaning
    "020402": "structure",    # exterior repair, improvements and decoration
    "020499": "structure",    # exterior maintenance, n.e.c.
    # 0207 — vehicles
    "020701": "not_shelter",  # vehicle repair and maintenance (by self)
    "020799": "not_shelter",  # vehicles, n.e.c.
    # 0208 — appliances, tools and toys
    "020801": "upkeep",       # appliance, tool and toy set-up, repair, maintenance
    "020899": "upkeep",       # appliances and tools, n.e.c.
}

#: Closed, so a fifth destination is a deliberate act rather than a typo.
SHELTER_DESTINATION_VOCAB: frozenset[str] = frozenset(
    {"upkeep", "structure", "thermal", "not_shelter"}
)


def shelter_decomposition(year: int | None = None) -> dict:
    """
    The shelter component split by where each hour physically belongs.

    REPORTING ONLY — it moves no constant and prices nothing. What it exists to
    do is make a boundary decision citable: the overlap with `infrastructure_eoh`
    is a measured share rather than an impression, and so is the share the
    degree-days intensity actually governs.

    Codes present in `SHELTER_DESTINATIONS` but absent from the survey year
    return 0.0 rather than being dropped — a category nobody reported is zero,
    not missing, which is the accessor convention `COMPONENT_CODES` already uses.

    Returns hours per person 15+ per year by destination and by code, the share
    each destination takes, and `unclassified` — which must be empty, because a
    6-digit code inside the shelter groups that nobody has placed would be
    silently excluded from the component without anyone having argued for it.
    """
    from hours_eoh.reference import atus_time_use as _atus

    y = _atus.latest_year() if year is None else year
    groups = COMPONENT_CODES["shelter"]
    labels = _atus.tier3_labels()
    in_groups = tuple(c for c in labels if c[:4] in groups)

    by_code: dict[str, dict] = {}
    by_destination: dict[str, float] = {d: 0.0 for d in SHELTER_DESTINATION_VOCAB}
    unclassified: list[str] = []
    for code in in_groups:
        hours = float(_atus.tier3_hours_per_person_15plus(y, (code,)))
        dest = SHELTER_DESTINATIONS.get(code)
        if dest is None:
            unclassified.append(code)
            continue
        by_destination[dest] += hours
        by_code[code] = {"label": labels[code], "destination": dest, "hours": hours}

    total = sum(by_destination.values())
    return {
        "year": y,
        "total_hours_per_person_15plus": total,
        "by_destination": by_destination,
        "destination_share": {
            d: (h / total if total > 0.0 else 0.0) for d, h in by_destination.items()
        },
        "by_code": by_code,
        "unclassified": unclassified,
        "overlaps_infrastructure": by_destination["structure"],
        "governed_by_degree_days": by_destination["thermal"],
        "frame": (
            "ATUS, United States, high-capital. The wrong frame for a floor: a "
            "collective that burns wood and hauls water plausibly spends more on "
            "the thermal line and less on laundry. MTUS (20,21,22) is the "
            "frame-consistent source and this composition is unchecked against it."
        ),
        "reporting_only": True,
    }


#: THE THREE MTUS CODES, TAKEN FROM THE SET THEY DECOMPOSE rather than retyped.
#: `COMPONENT_CODES_MTUS["shelter"]` is the validated aggregate; this check asks
#: what is inside it, so if that set ever changes this check follows it.
_SHELTER_CODES: tuple[int, ...] = COMPONENT_CODES_MTUS["shelter"]
_C20, _C21, _C22 = _SHELTER_CODES

#: THE MTUS CODEBOOK, READ. `utils/mtus_ingest.py` says in its own header that
#: **no codebook ships with the data file** — the byte layout and the ACT_*
#: aggregations were both DERIVED by solving against `mtus_esp.csv`, which
#: carries twelve aggregate columns and no per-code labels. That is true of the
#: DATA and was wrongly read as true of the STUDY: the labels are published, in
#: the MTUS User Guide, Table 2 "Harmonised activity codes (69-category)".
#:
#:   MAIN/SEC 20   Cleaning
#:   MAIN/SEC 21   Laundry, ironing, clothing repair
#:   MAIN/SEC 22   Home/vehicle maintenance/improvement
#:   MAIN/SEC 23   Other domestic work
#:
MTUS_LABELS_SOURCE: str = (
    "MTUS User Guide, October 2020 (Release 7.0), Table 2 'Harmonised activity "
    "codes (69-category)' — "
    "https://www.timeuse.org/sites/default/files/2021-02/User%20Guide_2021.pdf "
    "(read 2026-09-10, verbatim)"
)

#: DERIVED FROM THE PUBLISHED TABLE rather than retyped beside it (2026-09-21).
#: The whole 69-category frame now lives in `reference/mtus_time_use`, verified
#: against the file's own ACT_* aggregates. Keeping a second hand-typed copy of
#: three of its rows is the copy-of-a-value failure this repo has found six
#: times, so this selects from the one table instead. The SCOPE is unchanged —
#: still exactly the shelter codes, which `shares_report` and
#: `tests/scenarios/test_component_shares.py` both depend on.
MTUS_CODE_LABELS: dict[int, str] = {
    c: mtus.ACTIVITY_LABELS[c] for c in _SHELTER_CODES
}

# AND THE SAME GUIDE'S 25-CATEGORY LIST GROUPS THEM DIFFERENTLY FROM THIS REPO.
# Table 3 reads "Cleanetc — Cleaning, laundry, regular housework — main20+21+23"
# and "Maintain — Maintain home/vehicle, re-fuel — main22". So MTUS's own
# housework aggregate is {20,21,23} while COMPONENT_CODES_MTUS["shelter"] is
# {20,21,22}: it EXCLUDES 23 (other domestic work) and INCLUDES 22. The
# aggregate still reproduces ATUS at 0.9757, so this is not a defect — it is a
# difference the validation absorbed and nobody had looked at. Recorded here
# rather than as a constant, because nothing reads it and a constant nothing
# reads is a tag block with no consumer.

#: ONE MAPPING PER CODE, PICKED FROM THE LABEL ABOVE AND WRITTEN DOWN BEFORE
#: BEING RUN. Not a sweep: the label decides the target, so there is exactly one
#: candidate per code and no room to keep trying until something clears.
#: ATUS targets are 6-digit, from `SHELTER_DESTINATIONS`' own code list.
SHELTER_MTUS_HYPOTHESES: tuple[tuple[int, tuple[str, ...], str], ...] = (
    (_C20, ("020101", "020401"), "Cleaning → ATUS interior + exterior cleaning"),
    (_C21, ("020102", "020103"), "Laundry, ironing, clothing repair → laundry + textile repair"),
    (
        _C22,
        ("020301", "020302", "020303", "020399", "020402", "020499", "020701", "020799"),
        "Home/vehicle maintenance/improvement → ATUS 0203 + 0204 + 0207",
    ),
)

#: WHAT WAS TRIED BEFORE THE GUIDE WAS READ, kept unrepaired. Every `why` string
#: named what a code MEANS — "interior maintenance", "vehicles and appliances" —
#: and every one was a label supplied from the ATUS side and never read. The
#: labels were one fetch away. Kept because the near-miss is the finding, and
#: because a reader comparing the two lists can see how plausible the invented
#: ones looked.
SHELTER_MTUS_GUESSES: tuple[tuple[int, tuple[str, ...], str], ...] = (
    (_C20, ("0201",), "GUESS: household interior"),
    (_C20, ("0201", "0209"), "GUESS: interior plus household management"),
    (_C21, ("0203", "0204"), "GUESS: interior and exterior maintenance"),
    (_C21, ("0203", "0204", "0207", "0208"), "GUESS: maintenance plus vehicles and appliances"),
    (_C22, ("0207", "0208"), "GUESS: vehicles and appliances"),
    (_C22, ("0205", "0206"), "GUESS: lawn/garden and pets — both EXCLUDED from the basket"),
    (_C22, ("0205",), "GUESS: lawn/garden alone"),
)

#: THE REMAINDER, AND IT IS ARITHMETIC RATHER THAN A SECOND MEASUREMENT.
#: Once the AGGREGATE identifies and code 21 identifies, the other two are
#: pinned as a BLOCK by subtraction: m20+m22 = agg·a_full − r21·a21, so their
#: joint ratio is DETERMINED and carries no information about how the pair
#: splits. Verified numerically — reconstructing it from the aggregate and the
#: 21 result alone reproduces the measured 1.0416 exactly.
#:
#: So this is not a prediction that was confirmed, and an earlier version of
#: this module presented it as one. **What it is: the resolution the source
#: actually offers.** MTUS can speak about {21} and about the remainder, and
#: about neither member of the remainder alone. The one thing the number does
#: add is the GAP from the aggregate — 1.0416 against 0.9757 — which is the
#: label-declared targets excluding 020104, 020199 and 0208.
_REMAINDER_BLOCK: tuple[int, ...] = (_C20, _C22)

#: Samples read as low- and high-capital for the composition test. Named rather
#: than derived from a threshold: no capital series is attached to MTUS here, so
#: this is an attribution like every other in this module.
_LOW_CAPITAL_PREFIXES = ("ZA", "BG")
_HIGH_CAPITAL_PREFIXES = ("US", "NL", "DK", "NO")




def shelter_frame_check(
    tolerance: float = 0.05,
    composition_tolerance: float = 0.10,
    since: int = 2000,
) -> dict:
    """
    Can the shelter decomposition be transferred to the frame the base declares?

    REPORTING ONLY. `shelter_decomposition` is measured on ATUS — United States,
    high-capital — and the floor is an unassisted construction, so the split is
    evidence from the wrong end of the arc. MTUS is the frame-consistent source.

    WHAT MTUS RESOLVES, AND IT IS TWO BLOCKS RATHER THAN THREE CODES
    ----------------------------------------------------------------
    The AGGREGATE control passes first, or a failure below is a bug in this
    comparison rather than a fact about MTUS: (20,21,22) →
    (0201,0203,0204,0207,0208) reproduces ATUS at 0.9757, spread 0.0677, checked
    against `validate_code_mapping()` live.

    Then one mapping per code, each PICKED FROM THE PUBLISHED LABEL in
    `MTUS_CODE_LABELS` and written down before being run. Code 21 — laundry,
    ironing and clothing repair — IDENTIFIES on its own; 20 and 22 do not, and
    they miss in opposite directions. Every figure is in `trials`.

    Once the aggregate holds and 21 holds, **the other two are pinned as a BLOCK
    by subtraction** and their joint ratio is arithmetic, not a second
    measurement — see `_REMAINDER_BLOCK`, and `pair_is_forced_by_the_aggregate`,
    which says so in the return value. The opposite-direction misses are the
    same fact read per code. So MTUS speaks about {21} and about the remainder,
    and about neither 20 nor 22 alone. **That is the resolution the source
    offers; a seam between the two classifications is the plausible reading of
    WHY, and it is not established here.**

    AND THAT REVERSES THE LABEL-FREE READING
    -----------------------------------------
    Asked without labels — do the three codes hold the same shares at low and
    high capital? — the answer is no, and `composition_shift` gives the move.
    Asked at the resolution MTUS can identify, the answer is yes:
    `composition_shift_by_block` is inside `composition_tolerance`, which is one
    statement and not two, since the two blocks share a degree of freedom —
    **code 21's share of the set is stable across capital.** The whole of the
    per-code move lies inside the remainder, where the split is unresolved.

    A label-free test on an unidentified partition cannot tell a real
    reallocation from a boundary moving, and here it reported one as the other.
    Two further checks say the same: `ranges_separate` is False on every code,
    so a difference of means on 3 samples against 23 never cleared the
    within-group spread either.

    WHAT IS STILL NOT SETTLED, AND IT IS RESOLUTION RATHER THAN DISAGREEMENT
    ------------------------------------------------------------------------
    `SHELTER_DESTINATIONS` splits the component into upkeep / structure /
    thermal / not_shelter. **Upkeep and structure both sit inside the
    remainder** — interior cleaning next to interior repair — so the identified
    blocks cannot price the destination split. MTUS does not contradict the ATUS
    composition; it cannot see it. The option-D re-scoping therefore stays
    PROVISIONAL for a narrower reason than "MTUS disagrees", which is what the
    first run of this function concluded.

    Args:
        tolerance: how far a mean ratio may sit from 1.0 to count as identified.
        composition_tolerance: how far a share may move between the low- and
            high-capital groups before the composition is called
            non-transferable.
        since: year floor applied to BOTH groups. An earlier version applied it
            to the high-capital group only, which left BG1965 inside "low
            capital" and every pre-2000 US and NL sample outside "high" — a time
            confound wearing a capital label. At the default the low group is
            BG2001, ZA2000, ZA2010.
    """
    from hours_eoh.reference import atus_time_use as _atus
    from hours_eoh.reference import mtus_time_use as _mtus
    from hours_eoh.scenarios.automation_floors import validate_code_mapping

    # The control's target, read from the function that establishes it rather
    # than retyped here. A restated figure is the drift this repo keeps catching.
    _shipped_ratio = float(validate_code_mapping()["shelter"]["mean_ratio"])

    per = _mtus.codes_by_sample()
    years = {r.year for r in _atus.survey_years()}
    pairs = sorted(
        ((s, int(s[2:6])) for s in per if s.startswith("US") and int(s[2:6]) in years),
        key=lambda x: x[1],
    )

    def _atus_minutes(year: int, groups: tuple[str, ...]) -> float:
        """Prefix match, so a group may be a 4-digit family or a 6-digit code.
        The guessed hypotheses were written at 4 digits and the ones read from
        the codebook at 6 — matching on `c[:4]` alone threw away exactly the
        resolution the labels call for."""
        day = _atus.tier3_minutes_per_day(year)
        return sum(v for c, v in day.items() if any(c.startswith(g) for g in groups))

    def _score(codes: tuple[int, ...], groups: tuple[str, ...]) -> dict:
        rs = []
        for sample, year in pairs:
            m = sum(per[sample][c] for c in codes if per[sample].get(c) is not None)
            a = _atus_minutes(year, groups)
            if m > 0.0 and a > 0.0:
                rs.append(m / a)
        mean = sum(rs) / len(rs) if rs else 0.0
        return {
            "n_years": len(rs),
            "mean_ratio": mean,
            "spread": (max(rs) - min(rs)) if rs else 0.0,
            "within_tolerance": abs(mean - 1.0) <= tolerance,
        }

    aggregate = _score(_SHELTER_CODES, COMPONENT_CODES["shelter"])

    trials = [
        {
            "mtus_code": c,
            "mtus_label": MTUS_CODE_LABELS[c],
            "atus_target": g,
            "why": why,
            **_score((c,), g),
        }
        for c, g, why in SHELTER_MTUS_HYPOTHESES
    ]
    by_code = {t["mtus_code"]: t for t in trials}

    guesses = [
        {
            "mtus_code": c,
            "atus_target": g,
            "guessed_label": why,
            "identification": "VOID — this label was invented, not read",
            **_score((c,), g),
        }
        for c, g, why in SHELTER_MTUS_GUESSES
    ]

    # The remainder, scored directly. Its value is forced — see `_REMAINDER_BLOCK`.
    pair_targets = tuple(
        g for c, gs, _w in SHELTER_MTUS_HYPOTHESES if c in _REMAINDER_BLOCK for g in gs
    )
    pair = _score(_REMAINDER_BLOCK, pair_targets)
    opposite = (
        by_code[_REMAINDER_BLOCK[0]]["mean_ratio"] - 1.0
    ) * (by_code[_REMAINDER_BLOCK[1]]["mean_ratio"] - 1.0) < 0.0

    identified_codes = tuple(t["mtus_code"] for t in trials if t["within_tolerance"])
    #: The partitions MTUS can speak about: every code that identified alone,
    #: plus the remainder they leave. Anything not in one of these is unresolved.
    blocks: tuple[tuple[int, ...], ...] = tuple(
        (c,) for c in identified_codes if c not in _REMAINDER_BLOCK
    ) + ((_REMAINDER_BLOCK,) if pair["within_tolerance"] else ())

    def _shares(prefixes: tuple[str, ...]) -> dict:
        rows = []
        for sample, d in sorted(per.items()):
            if not sample.startswith(prefixes) or int(sample[2:6]) < since:
                continue
            vals = [v for c in _SHELTER_CODES if (v := d.get(c)) is not None]
            if len(vals) != len(_SHELTER_CODES):
                continue
            total = sum(vals)
            rows.append((sample, total, [v / total for v in vals]))
        n = len(rows)
        share = [
            sum(r[2][i] for r in rows) / n if n else 0.0
            for i in range(len(_SHELTER_CODES))
        ]
        # THE WITHIN-GROUP RANGE, because a difference of means on n=3 against
        # n=23 says nothing if the ranges overlap. Reported per code so the
        # reader can see whether a between-group shift clears the noise.
        rng = [
            (min(r[2][i] for r in rows), max(r[2][i] for r in rows)) if n else (0.0, 0.0)
            for i in range(len(_SHELTER_CODES))
        ]
        return {
            "samples": [r[0] for r in rows],
            "n_samples": n,
            "total_minutes_per_day": sum(r[1] for r in rows) / n if n else 0.0,
            "code_share": share,
            "code_share_range": rng,
            "block_share": [
                sum(sum(r[2][_SHELTER_CODES.index(c)] for c in b) for r in rows) / n
                if n else 0.0
                for b in blocks
            ],
        }

    low = _shares(_LOW_CAPITAL_PREFIXES)
    high = _shares(_HIGH_CAPITAL_PREFIXES)

    def _shift(key: str) -> list[float]:
        return [
            (low[key][i] / high[key][i] - 1.0) if high[key][i] else 0.0
            for i in range(len(high[key]))
        ]

    code_shift, block_shift = _shift("code_share"), _shift("block_share")
    # At a tolerance strict enough that nothing identifies there are no blocks,
    # so the verdict has no block figure to quote. Say that rather than crash or
    # quote a code-level number in a block-level sentence.
    block_line = (
        f"code {blocks[0][0]}'s share moves {block_shift[0]:+.1%}"
        if blocks else "NOTHING IDENTIFIES at this tolerance, so there is no block to read"
    )
    #: True where the two groups' within-group ranges do not overlap — the
    #: minimum a difference of means on 3 vs 23 samples has to clear.
    separated = [
        low["code_share_range"][i][0] > high["code_share_range"][i][1]
        or high["code_share_range"][i][0] > low["code_share_range"][i][1]
        for i in range(len(_SHELTER_CODES))
    ]

    return {
        "aggregate": aggregate,
        "aggregate_reproduces": abs(aggregate["mean_ratio"] - _shipped_ratio) < 0.01,
        "code_labels": MTUS_CODE_LABELS,
        "labels_source": MTUS_LABELS_SOURCE,
        "trials": trials,
        "identified_codes": identified_codes,
        "guesses_made_before_reading_the_codebook": guesses,
        "since": since,
        "remainder_block": _REMAINDER_BLOCK,
        "pair": pair,
        "pair_is_forced_by_the_aggregate": True,
        "why_pair_is_forced": (
            "m20+m22 = aggregate x a_full - r21 x a21, so once the aggregate and "
            "21 identify the remainder's ratio is determined by subtraction and "
            "carries no information about how it splits; reconstructing it from "
            "those two alone reproduces the measured value exactly. It is the "
            "RESOLUTION available, not a prediction that was confirmed"
        ),
        "pair_misses_are_opposite": opposite,
        "remainder_identifies": pair["within_tolerance"],
        "seam_is_the_plausible_reading_not_a_result": opposite,
        "identified_blocks": blocks,
        "low_capital": low,
        "high_capital": high,
        "composition_shift": code_shift,
        "composition_shift_by_block": block_shift,
        "ranges_separate": separated,
        "composition_transfers": max(
            (abs(x) for x in block_shift), default=0.0
        ) < composition_tolerance,
        "composition_transfers_by_code": max(abs(x) for x in code_shift) < composition_tolerance,
        "destination_split_resolvable": False,
        "why_not_resolvable": (
            "upkeep and structure both sit inside the {20,22} block — interior "
            "cleaning next to interior repair — so the identified blocks cannot "
            "price SHELTER_DESTINATIONS' split"
        ),
        "verdict": (
            f"MTUS carries shelter's TOTAL at the frame the base declares "
            f"({aggregate['mean_ratio']:.4f}) and resolves it into TWO blocks, "
            f"not three codes: {{21}} laundry and clothing care, which identifies "
            f"on its own at {by_code[_C21]['mean_ratio']:.4f}, and the REMAINDER "
            f"{{20,22}} at {pair['mean_ratio']:.4f} — which is arithmetic once the "
            f"first two hold, not a second measurement. At that resolution the "
            f"composition TRANSFERS across capital ({block_line}), which REVERSES the label-free reading that "
            f"code 22's {code_shift[2]:+.1%} was a real reallocation: the whole of "
            f"it lies inside the unresolved remainder, and it never cleared the "
            f"within-group spread either. What MTUS still cannot do is price the "
            f"destination split, because upkeep and structure share the "
            f"remainder — so the option-D re-scoping stays PROVISIONAL on "
            f"resolution rather than on disagreement. What would settle it is a "
            f"survey at the declared frame with ATUS-level (6-digit) "
            f"granularity, or MTUS national micro-data below the harmonised "
            f"aggregates"
        ),
        "reporting_only": True,
    }


def observed_shares(year: int | None = None) -> dict:
    """
    Observed component shares of mapped personal time use, from ATUS.

    Governing sums, per component c:

        hours(c)  = Σ_{code ∈ COMPONENT_CODES[c]} hours_per_person_15plus(code)
        share(c)  = hours(c) / Σ_c hours(c)

    units: labour-hours per person aged 15+ per year, and dimensionless shares.

    ε-behaviour: NONE. This is a census of a present-day economy and carries no
    automation scaling; the ε-dependence lives in `phase_2_sensitivity`, which
    applies the shares to the automation floor.

    Worked example (2025, the shipped default): care 191.5, nutrition 259.8,
    shelter 265.2, health 28.7, mapped total 745.2 h/person15+·yr — care 25.7%.

    Args:
        year: ATUS survey year. Defaults to the latest comparable year.
    """
    y = atus.latest_year() if year is None else year
    hours = {
        c: atus.hours_per_person_15plus(y, codes)
        for c, codes in COMPONENT_CODES.items()
    }
    total = sum(hours.values())
    excluded = sum(
        atus.hours_per_person_15plus(y, (code,)) for code in EXCLUDED_CODES
    )
    return {
        "year":            y,
        "hours":           hours,
        "shares":          {c: h / total for c, h in hours.items()},
        "mapped_total":    total,
        "excluded_hours":  excluded,
        "excluded_share_of_all": excluded / (total + excluded),
        "overlap_hours": sum(
            atus.hours_per_person_15plus(y, (code,)) for code in _OVERLAPPING
        ),
    }


def share_comparison(year: int | None = None) -> dict:
    """
    Observed shares against the desk estimate, component by component.

    units: dimensionless shares and their ratio.

    THE RATIO IS THE FINDING and the level is not: at the 2025 default care
    reads 0.41× the desk share and shelter 3.44×, and both are far outside
    anything a mapping choice explains. The direction is what the marketisation
    confound also predicts, so the disagreement is real and its SIZE is not
    settled.
    """
    obs = observed_shares(year)
    rows = []
    for c, desk_spec in PERSONAL_EOH_COMPONENTS.items():
        desk = float(desk_spec["share"])
        seen = obs["shares"][c]
        rows.append({
            "component":  c,
            "observed":   seen,
            "desk":       desk,
            "ratio":      seen / desk,
            "abatability": float(desk_spec["abatability"]),
        })
    return {
        "year":  obs["year"],
        "rows":  rows,
        "mapped_total": obs["mapped_total"],
        "excluded_hours": obs["excluded_hours"],
        "overlap_hours": obs["overlap_hours"],
        "care_observed": obs["shares"]["care"],
        "care_desk":     float(PERSONAL_EOH_COMPONENTS["care"]["share"]),
        "is_a_bound":    True,
        "bound_reason": (
            "observed is not obligation; one country at one development level; "
            "and care has been MARKETISED out of unpaid time use, which moves "
            "the result in exactly this direction. The observed care share is "
            "therefore a LOWER bound on care's true share."
        ),
    }


def _spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation. n is 4 here, so this is a direction, not a p-value."""
    n = len(xs)
    rx = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: xs[i]))}
    ry = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: ys[i]))}
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def abatability_direction(
    start: int = 2003,
    end: int | None = None,
) -> dict:
    """
    Does `abatability` predict how each component moved over 22 years of capital
    deepening? Measured, not argued.

    Governing comparisons:

        change(c) = hours(c, end) / hours(c, start) − 1
        ρ_change  = Spearman(abatability, change)          a(K) predicts ρ < 0
        ρ_share   = Spearman(abatability, observed share)  Block II predicts ρ < 0

    units: dimensionless.

    WHAT IT FINDS (2003 → 2025, the shipped defaults). ρ_change is **+0.400**
    where a(K) predicts negative: nutrition — abatability 0.85, the second most
    abatable — ROSE **+33.7%**, while care, the LEAST abatable, fell **−20.7%**,
    the largest fall of the four. Block II's anti-correlation prediction is
    **−1.000** in the desk table (by construction — the table was built that way)
    and reads **+0.800** against observed shares.

    THIS DOES NOT REFUTE a(K), AND THE MODULE WILL NOT SAY THAT IT DOES. The
    mapped TOTAL moved −2.9% over the period, which is consistent with a(K)
    being SATURATED in a rich economy — where the predicted change is small
    anyway. What is not explained by saturation is the composition, and the
    marketisation confound reaches that directly. It is reported as an anomaly
    with a named alternative explanation, which is the honest state.
    """
    e = atus.latest_year() if end is None else end
    # Parallel typed lists alongside the report rows: the rows dict is
    # heterogeneous, so reading floats back out of it loses the type.
    names: list[str] = []
    ab: list[float] = []
    change: list[float] = []
    rows: list[dict] = []
    t0 = t1 = 0.0
    for c, codes in COMPONENT_CODES.items():
        h0 = atus.hours_per_person_15plus(start, codes)
        h1 = atus.hours_per_person_15plus(e, codes)
        a = float(PERSONAL_EOH_COMPONENTS[c]["abatability"])
        names.append(c)
        ab.append(a)
        change.append(h1 / h0 - 1.0)
        t0 += h0
        t1 += h1
        rows.append({
            "component":   c,
            "abatability": a,
            "hours_start": h0,
            "hours_end":   h1,
            "change":      h1 / h0 - 1.0,
        })
    obs = observed_shares(e)["shares"]
    return {
        "start": start, "end": e, "rows": rows,
        "mapped_total_start": t0,
        "mapped_total_end":   t1,
        "mapped_total_change": t1 / t0 - 1.0,
        "spearman_abatability_vs_change": _spearman(ab, change),
        "spearman_abatability_vs_desk_share": _spearman(
            ab, [float(PERSONAL_EOH_COMPONENTS[n]["share"]) for n in names]
        ),
        "spearman_abatability_vs_observed_share": _spearman(
            ab, [float(obs[n]) for n in names]
        ),
        "refutes_abatement": False,
        "note": (
            "The mapped total moved only -2.9%, which is consistent with a(K) "
            "being SATURATED in a rich economy. The composition is not explained "
            "by saturation, and care marketisation reaches it directly. Reported "
            "as an anomaly with a named alternative, not as a refutation."
        ),
    }


def phase_2_sensitivity(epsilon: float = 0.99, year: int | None = None) -> dict:
    """
    What the care share is worth to Phase 2's headline.

    Governing comparison, at automation level ε:

        f(share) = share·[c + (1 − c)(1 − ε)] + (1 − share)·(1 − ε)
        factor   = f(share) / (1 − ε)

    where c is `CARE_AUTOMATION_FLOOR`.

    units: dimensionless.

    Worked example (ε=0.99, 2025 default): at the desk share 62.1% the factor is
    10.22×; at the observed 25.7% it is 4.82×. **The finding survives the swap — it is
    order-of-magnitude-class either way — and its LEVEL does not.** Both are
    lower bounds, because the observed care share is itself one.

    Raises:
        ValueError: if epsilon is outside [0.0, 1.0].
    """
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError(f"epsilon must be in [0.0, 1.0], got {epsilon}")

    uniform = 1.0 - epsilon
    c = CARE_AUTOMATION_FLOOR

    def factor(share: float) -> float:
        f = share * (c + (1.0 - c) * uniform) + (1.0 - share) * uniform
        return f / uniform if uniform else float("inf")

    desk = float(PERSONAL_EOH_COMPONENTS["care"]["share"])
    seen = observed_shares(year)["shares"]["care"]
    return {
        "epsilon":            epsilon,
        "care_share_desk":     desk,
        "care_share_observed": seen,
        "factor_at_desk":      factor(desk),
        "factor_at_observed":  factor(seen),
        "survives_the_swap":   factor(seen) > 4.0,
        "note": (
            "Both are LOWER bounds: the observed care share is itself a lower "
            "bound, because marketised care leaves unpaid time use. The "
            "order-of-magnitude finding survives the swap; the level does not."
        ),
    }


def shares_report(year: int | None = None) -> dict:
    """The report. CLI: `eoh scenario run component_shares`."""
    cmp_ = share_comparison(year)
    direction = abatability_direction()
    sens = phase_2_sensitivity(0.99, year)
    return {
        "comparison":  cmp_,
        "direction":   direction,
        "sensitivity": sens,
        "mapping": {
            "components": COMPONENT_CODES,
            "excluded":   EXCLUDED_CODES,
            "overlap":    _OVERLAPPING,
        },
        "verdict": (
            f"ATUS {cmp_['year']} puts care at {cmp_['care_observed']:.1%} of "
            f"mapped personal time against a desk share of "
            f"{cmp_['care_desk']:.1%} — {cmp_['care_observed'] / cmp_['care_desk']:.2f}×. "
            f"Phase 2's factor at ε=0.99 moves "
            f"{sens['factor_at_desk']:.2f}× → {sens['factor_at_observed']:.2f}×, so the "
            f"order-of-magnitude finding survives and its level does not. This "
            f"is a BOUND, not a closure: observed is not obligation, it is one "
            f"country at one development level, and marketised care leaves "
            f"unpaid time use in exactly this direction. A cross-country "
            f"time-use panel (HETUS/MTUS) would settle the shares, the "
            f"abatabilities, K_half, the extraction wedge and the infant "
            f"age-weight band together."
        ),
        "reporting_only": True,
    }
