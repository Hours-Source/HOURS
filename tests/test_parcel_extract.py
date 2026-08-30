"""
Tests for hours_eoh.reference.parcels — the county parcel extract.

The deliverable is the parcel COUNT, which is the denominator the per-parcel
term needs and which `scenarios/use_split` showed no re-cut of the ten ratios
could reach. What these pin is that the count is complete, that the area column
is not mistaken for land area, and that no use-category judgement has been
smuggled into a file whose whole value is that it carries none.
"""

import pathlib

import pytest

from hours_eoh.reference.parcels import (
    DATA_FILE,
    PARCEL_VINTAGE,
    STATE_LAND_AREA_KM2,
    county_count,
    land_area_validation,
    load_county_parcels,
    national_parcel_count,
    parcels_by_state,
)


class TestTheCensusIsComplete:
    """The claim that makes this usable as a denominator at all."""

    def test_the_extract_ships(self):
        assert DATA_FILE.exists(), "the derived CSV is committed; the 68 GB raw is not"
        assert DATA_FILE.stat().st_size < 1_000_000, (
            "an extract that grows past ~1 MB has stopped being an extract"
        )

    def test_every_county_is_present(self):
        """~3,143 US counties plus territory equivalents."""
        assert 3_100 <= county_count() <= 3_300, county_count()

    def test_the_national_count_matches_the_census(self):
        """
        Pinned exactly: this is the file's own row count, so a mismatch means
        the ingest dropped or duplicated rows rather than that the world moved.
        """
        assert national_parcel_count() == 160_573_137

    def test_all_fifty_states_plus_dc_are_represented(self):
        by_state = parcels_by_state()
        assert len(by_state) >= 51, f"only {len(by_state)} state FIPS present"
        for fips in ("48", "06", "12", "36", "02", "15"):  # TX CA FL NY AK HI
            assert by_state.get(fips, 0) > 0, f"state {fips} missing"

    def test_the_largest_states_rank_as_expected(self):
        """
        A cheap external check: parcel counts should track population and
        development, so TX and CA lead. If this inverted, the geography
        assignment would be suspect.
        """
        by_state = parcels_by_state()
        top = sorted(by_state, key=lambda k: -by_state[k])[:3]
        assert set(top) == {"48", "06", "12"}, top

    def test_geography_is_never_blank(self):
        for r in load_county_parcels():
            assert r["statefp"] and r["countyfp"], r


class TestTheAreaColumnIsNotLandArea:
    """
    THE LIMITATION, PINNED SO IT CANNOT BE QUIETLY FORGOTTEN. Summed parcel
    footprints exceed the land area of six of the twelve checked states.
    """

    def test_some_states_sum_to_more_than_they_contain(self):
        rows = land_area_validation()
        exceeding = [r for r in rows if r["exceeds_land"]]
        assert exceeding, (
            "if no state exceeded its land area the over-count would have been "
            "fixed, and the docstrings claiming otherwise would be stale"
        )
        assert len(exceeding) >= 4

    def test_florida_is_the_worst_and_by_roughly_a_third(self):
        """
        Asserted as a band, not a level: it moves with every vintage. What must
        not change silently is that a state can exceed its own area at all.
        """
        fl = next(r for r in land_area_validation() if r["statefp"] == "12")
        assert 1.2 < float(fl["ratio"]) < 1.5, fl

    def test_federal_land_states_UNDER_count_for_the_opposite_reason(self):
        """
        Alaska and Utah are thinly parcelised because much of them is federal.
        Both directions are pinned so the column is not read as merely noisy —
        it is biased in a legible way.
        """
        rows = {r["statefp"]: r for r in land_area_validation()}
        assert float(rows["02"]["ratio"]) < 0.2, "Alaska is barely parcelised"
        assert float(rows["49"]["ratio"]) < 0.8, "Utah is federal-heavy"

    def test_the_validation_covers_both_kinds_of_state(self):
        """A validation list containing only over-counters would suggest the
        conclusion had been selected for."""
        ratios = [float(r["ratio"]) for r in land_area_validation()]
        assert max(ratios) > 1.0 and min(ratios) < 0.5

    def test_the_reference_areas_are_plausible(self):
        """Guards a typo in the carried gazetteer figures."""
        assert STATE_LAND_AREA_KM2["48"] > STATE_LAND_AREA_KM2["06"]  # TX > CA
        assert STATE_LAND_AREA_KM2["02"] == max(STATE_LAND_AREA_KM2.values())  # AK


class TestNoJudgementIsSmuggledIn:
    """
    The extract's value is that it carries no mapping. `usedesc` is 41.2% filled
    free text from 3,230 county systems, and normalising it is a separate
    project — bundling it here would make the count unciteable.
    """

    #: Checked against the FILE's header, not the loader's output. The first
    #: version of this test read `set(load_county_parcels()[0])` — but the
    #: loader builds a fixed dict from named keys, so an extra column in the
    #: CSV is silently ignored and the test passed with `usedesc` added to the
    #: file. It guarded the loader, not the extract. Found by the bite test,
    #: which is why the bite test is not optional.
    DECLARED_COLUMNS = [
        "statefp", "countyfp", "parcels", "area_m2", "area_parcels",
        "government_parcels", "ownertype_known",
    ]

    def _header(self) -> list[str]:
        first = DATA_FILE.read_text(encoding="utf-8").splitlines()[0]
        return first.split(",")

    def test_there_is_no_use_category_column_IN_THE_FILE(self):
        forbidden = {"usecode", "usedesc", "use_category", "zoningcode",
                     "iucnclass", "naicscode"}
        present = forbidden & set(self._header())
        assert not present, (
            f"a use-category mapping has entered the extract: {sorted(present)}. "
            "`usedesc` is 41.2% filled free text from 3,230 county systems; "
            "normalising it is a separate project with a real judgement in it, "
            "and a count carrying a judgement is not citeable as a count."
        )

    def test_the_file_header_is_exactly_the_declared_seven(self):
        assert self._header() == self.DECLARED_COLUMNS

    def test_the_loader_exposes_exactly_what_the_file_declares(self):
        assert set(load_county_parcels()[0]) == set(self.DECLARED_COLUMNS)

    def test_no_national_total_is_stored(self):
        """
        Callers sum the rows. A stored total is a second copy of a value whose
        source is elsewhere — the pattern this repo has found five times.
        """
        text = DATA_FILE.read_text(encoding="utf-8")
        assert "160573137" not in text and "160,573,137" not in text


class TestOwnershipIsAPairNotAFraction:
    """
    `government_parcels` and `ownertype_known` ship together because an
    unpopulated owner type is not a private owner — the coverage-inflation trap
    `scenarios/land_stewardship` guards against.
    """

    def test_known_never_exceeds_total_and_government_never_exceeds_known(self):
        for r in load_county_parcels():
            assert r["ownertype_known"] <= r["parcels"], r
            assert r["government_parcels"] <= r["ownertype_known"], r

    def test_ownership_coverage_is_partial_and_that_is_visible(self):
        rows = load_county_parcels()
        known = sum(int(r["ownertype_known"]) for r in rows)
        total = sum(int(r["parcels"]) for r in rows)
        assert 0.7 < known / total < 0.95, (
            "coverage is ~81.5%; a caller dividing government by TOTAL rather "
            "than by KNOWN understates public holding by that factor"
        )

    def test_government_parcels_are_a_usable_tenure_signal(self):
        """
        Phase 4c's tenure split names BLM Public Land Statistics as its
        resolves_by; this is a second, independent route to the same question.
        """
        g = sum(int(r["government_parcels"]) for r in load_county_parcels())
        assert g == 3_231_732

    def test_area_parcels_never_exceeds_parcels(self):
        for r in load_county_parcels():
            assert r["area_parcels"] <= r["parcels"], r


class TestTheVintageIsDeclared:

    def test_the_vintage_is_named(self):
        """A refreshed extract must be a visible change, not a silent one."""
        assert PARCEL_VINTAGE == "NATIONWIDE_SAMPLE_Q3_R2"
