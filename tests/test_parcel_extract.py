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


class TestServicePointDenominatorIsNotBuildable:
    """
    THE MEASUREMENT THAT SETTLES HALF THE TWO-TERM SPLIT (2026-08-30).

    `scenarios/use_split` proposed splitting the per-parcel term: `P_title` per
    legal parcel (deed, assessment, boundary) and `P_service` per SERVICE POINT
    (refuse, metering, inspection) — because consolidating a hundred apartments
    into one parcel removes a hundred deeds but not one refuse collection.

    `P_title` is buildable now: the parcel count is complete and clean.
    `P_service` is not, and the reason is NOT the 47.6% coverage. `numunits`
    carries OTHER COLUMNS — see `TestTheContaminationIsOtherColumns` — and the
    national total moves across an order of magnitude depending on an exclusion
    cap that nothing justifies.
    """

    def test_the_verdict_is_not_buildable(self):
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert v["buildable"] is False
        assert "NOT buildable" in str(v["verdict"])

    def test_the_cap_moves_the_answer_by_an_order_of_magnitude(self):
        """
        The finding, as a number: a denominator whose value depends on an
        unprincipled threshold is not a measurement.
        """
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert float(v["ratio_span"]) > 10.0, (
            "if the span ever fell below an order of magnitude the field might "
            "be usable with a stated cap, and this verdict should be revisited"
        )

    def test_the_plausible_cap_is_flagged_as_the_trap(self):
        """
        A cap of 1,000 gives ~0.9× the US housing stock — close enough to look
        settled. Adopting it BECAUSE it looks settled is fitting to a target,
        which is what `DEFAULT_SEGMENTS` and `GUF_USE_SCALE_FACTOR` both did.
        """
        from hours_eoh.reference.parcels import (
            NUMUNITS_CAP_SENSITIVITY, US_HOUSING_UNITS_2020)
        by_cap = {c: u for c, _, u in NUMUNITS_CAP_SENSITIVITY}
        assert 0.8 < by_cap[1_000] / US_HOUSING_UNITS_2020 < 1.1, (
            "the plausible-looking cap must stay plausible-looking, or the "
            "warning about it stops making sense"
        )
        assert by_cap[1_000_000] / US_HOUSING_UNITS_2020 > 10.0

    def test_the_sensitivity_table_is_monotone(self):
        """A higher cap admits more rows, so the summed total may only rise."""
        from hours_eoh.reference.parcels import NUMUNITS_CAP_SENSITIVITY
        caps = [c for c, _, _ in NUMUNITS_CAP_SENSITIVITY]
        sums = [u for _, _, u in NUMUNITS_CAP_SENSITIVITY]
        above = [a for _, a, _ in NUMUNITS_CAP_SENSITIVITY]
        assert caps == sorted(caps)
        assert sums == sorted(sums), "raising the cap cannot lower the total"
        assert above == sorted(above, reverse=True), "raising the cap admits more rows"

    def test_a_third_of_built_parcels_carry_no_unit_count(self):
        """
        The second, independent reason. A parcel with buildings and no unit
        count is genuinely MISSING data — distinct from a parcel with neither,
        where zero service points is at least arguable.
        """
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert 0.25 < float(v["missing_on_built"]) < 0.40

    def test_no_units_column_reached_the_extract(self):
        """
        The measurement's practical consequence: nothing derived from
        `numunits` is shipped, so no caller can pick it up believing it settled.
        """
        header = DATA_FILE.read_text(encoding="utf-8").splitlines()[0]
        assert "unit" not in header.lower()


class TestTheContaminationIsOtherColumns:
    """
    THE MECHANISM, IDENTIFIED (2026-08-30). The tail is not a heavy tail of a
    real distribution — it is other columns pasted into `numunits`, one county
    at a time. That matters for the verdict rather than merely colouring it: a
    cap is the wrong instrument at ANY threshold, because it is not trimming
    outliers, it is guessing which rows came from the wrong source column.
    """

    def test_camden_alone_is_most_of_the_national_total(self):
        """
        A single constant, 2,040,202, on 22,342 rows — and that product is 86%
        of every unit the census claims. Arithmetic, not inference.
        """
        from hours_eoh.reference.parcels import NUMUNITS_NATIONAL_TOTAL
        assert 2_040_202 * 22_342 == 45_582_193_084
        share = 45_582_193_084 / NUMUNITS_NATIONAL_TOTAL
        assert 0.85 < share < 0.88

    def test_the_record_holder_is_its_own_land_area(self):
        """
        Lee County FL parcel 14452400000060010: 140.542 acres of college
        campus, and `numunits` is that area in hundredths of a square foot.
        """
        sq_ft = 140.542 * 43_560.0
        assert 612_196_539 / sq_ft == pytest.approx(100.0, rel=1e-4)

    def test_each_leak_names_what_the_column_actually_holds(self):
        """
        A leak recorded without its mechanism is a magnitude observation, and
        magnitude is exactly what must NOT drive an exclusion.
        """
        from hours_eoh.reference.parcels import NUMUNITS_COLUMN_LEAKS
        assert len(NUMUNITS_COLUMN_LEAKS) >= 3
        for fips, county, holds in NUMUNITS_COLUMN_LEAKS:
            assert len(fips) == 5 and fips.isdigit()
            assert county and len(holds) > 15, f"{county} does not say what it holds"


class TestExclusionCleansTheTailAndNotTheNumerator:
    """
    THE QUESTION THIS ANSWERS (2026-08-30): would dropping the worst counties
    let the rest support a placeholder? Half of it, and the half it does not
    support is the half that matters.

    The exclusion rule is mechanism-based — a value repeated on >=1% of rows,
    or >=1% of rows matching parcel or building area to within 2% — and was
    DECLARED BEFORE its outcome was seen, because choosing exclusions by size
    is the cap trap at county resolution.
    """

    def test_the_exclusion_cleans_the_tail_decisively(self):
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert float(v["parcels_retained"]) > 0.98, "an exclusion this cheap is the point"
        assert float(v["cleaned_reduction"]) > 100.0, "232x, and it is why this was worth measuring"
        assert 1.0 < float(v["cleaned_ratio"]) < 2.5, (
            "the cleaned total must stay in the plausible band — above the "
            "residential stock, because commercial suites count too, but not "
            "wildly above it"
        )

    def test_the_exclusion_does_not_move_the_missing_numerator(self):
        """
        THE FINDING. 31.59% of built parcels carry no unit count before
        exclusion; 31.61% after. The two defects are ORTHOGONAL — cleaning the
        tail buys a plausible total and not one row of the numerator.
        """
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        before = float(v["missing_on_built"])
        after = float(v["missing_on_built_retained"])
        assert abs(after - before) < 0.005, (
            "if exclusion ever DID move the coverage gap, the two defects "
            "would share a cause and this verdict should be revisited"
        )

    def test_the_gap_cannot_be_imputed_from_the_populating_counties(self):
        """
        The move that would turn a lower bound into a band, measured and
        refused: the counties that populate the field are denser than those
        that do not, so their rate is measured exactly where it is least
        transferable. Applied nationally it gives ~2.9x the housing stock.
        """
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert v["imputable"] is False
        assert float(v["imputed_ratio"]) > 2.0, (
            "the imputed total must stay implausible, or the reason for "
            "refusing the imputation stops holding"
        )

    def test_the_cleaned_figure_is_reported_as_a_lower_bound(self):
        from hours_eoh.reference.parcels import service_point_denominator_verdict
        v = service_point_denominator_verdict()
        assert v["buildable"] is False
        assert "LOWER BOUND" in str(v["verdict"])
