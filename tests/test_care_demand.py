"""
Tests for the ATUS care-by-recipient-age measurement.

utils/atus_care_ingest.py, utils/census_age_ingest.py,
hours_eoh/reference/care_demand.py, hours_eoh/scenarios/care_curve.py

Three groups:

  * ATTRIBUTION tests pin the joint-production arithmetic against synthetic
    inputs, so the ρ machinery cannot quietly change meaning.
  * EXTRACT tests run against the shipped CSVs — shape, domain, and the
    unreachable-is-not-zero discipline.
  * REPORTING tests pin the findings themselves. If the measured weights move,
    these fail and the finding gets restated deliberately rather than drifting.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.data import AGE_GROUPS
from hours_eoh.reference import care_demand as cd
from hours_eoh.scenarios import care_curve
from utils import atus_care_ingest as ingest


# ---------------------------------------------------------------------------
# attribution — synthetic
# ---------------------------------------------------------------------------

def test_share_corners_are_split_and_duplicate():
    """ρ=1 divides attention; ρ=0 shares it whole. The corners define the scale."""
    assert ingest._share(4, 1.0) == pytest.approx(0.25)
    assert ingest._share(4, 0.0) == pytest.approx(1.0)
    assert ingest._share(1, 0.5) == pytest.approx(1.0)


def test_share_is_between_the_corners_at_a_measured_rho():
    """The whole point: care is neither fully rival nor fully shared."""
    split, dup = ingest._share(3, 1.0), ingest._share(3, 0.0)
    assert split < ingest._share(3, 0.27) < dup


def test_share_of_nobody_is_zero_not_an_error():
    assert ingest._share(0, 0.5) == 0.0


def test_rho_is_fitted_through_the_origin():
    """T(1)/T(1) = 1 is an identity, so the fit must not be free to miss it."""
    assert ingest._fit_rho({1: 10.0, 2: 20.0, 4: 40.0}) == pytest.approx(1.0)
    assert ingest._fit_rho({1: 10.0, 2: 10.0, 4: 10.0}) == pytest.approx(0.0)


def test_rho_without_a_base_is_not_a_number():
    assert math.isnan(ingest._fit_rho({2: 5.0}))


def test_negative_sentinels_are_missing_not_zero():
    """ATUS codes missing as -1/-2/-3; reading them as 0 would fabricate data."""
    assert ingest._int("-1") is None
    assert ingest._int("") is None
    assert ingest._int("0") == 0
    assert ingest._int("45") == 45


# ---------------------------------------------------------------------------
# the shipped extracts
# ---------------------------------------------------------------------------

def test_rivalry_is_between_the_corners_in_the_shipped_data():
    """The headline empirical claim: care is joint production.

    ρ=1 would mean each dependant needs their own time; ρ=0 that a second costs
    nothing. Both measured exponents sit strictly between, which is what makes
    the attribution question a measurement rather than a doctrine.
    """
    for kind in ("active", "passive"):
        rho = cd.rivalry_exponent(kind)
        assert 0.0 < rho < 1.0, f"{kind} ρ={rho} is at or outside a corner"
    assert cd.rivalry_exponent("active") > cd.rivalry_exponent("passive"), (
        "active care should be MORE rivalrous than passive supervision"
    )


def test_rivalry_table_rises_with_dependants():
    for kind in ("active", "passive"):
        table = cd.rivalry_table(kind)
        values = [table[n] for n in sorted(table)]
        assert values == sorted(values), f"{kind} care fell with more dependants"


def test_joint_cost_is_sub_additive():
    """Serving four costs less than four times serving one — the saving itself."""
    assert 1.0 < cd.joint_cost(4, "active") < 4.0


def test_care_falls_with_age_through_childhood():
    care = cd.care_by_age(care_curve.pooled_years())
    assert care[0]["active"] > care[5]["active"] > care[12]["active"]
    assert care[12]["active"] > care[17]["active"]


def test_passive_care_is_absent_above_twelve_not_zero():
    """UNREACHABLE IS NOT ZERO — the module's central discipline, on its own data.

    ATUS collects secondary childcare for under-13s only. A 0.0 there would
    assert that nobody supervises a fifteen-year-old, which no measurement here
    supports.
    """
    care = cd.care_by_age(care_curve.pooled_years())
    assert care[cd.PASSIVE_MAX_AGE]["passive"] is not None
    for age in (cd.PASSIVE_MAX_AGE + 1, 20, 70):
        assert care[age]["passive"] is None, f"age {age} passive should be absent"
        assert care[age]["total"] is None, "a total including an absent term"


def test_self_maintenance_is_absent_below_fifteen_not_zero():
    """ATUS surveys nobody younger. Zero would understate every child's obligation."""
    own = cd.self_maintenance_by_age(care_curve.pooled_years())
    assert min(own) >= cd.SELF_MAINTENANCE_MIN_AGE
    profile = cd.personal_profile(care_curve.pooled_years())
    assert profile[0]["self"] is None and profile[0]["total"] is None
    assert profile[40]["self"] is not None


def test_ages_are_top_coded_consistently():
    """Both ATUS age variables top-code at 85, and the denominator must match.

    Before this was handled, the 85 cell divided a top-coded numerator by the
    single-year population and reported 932 minutes per person-day — over 15
    hours, for an average.
    """
    care = cd.care_by_age(care_curve.pooled_years())
    assert max(care) == cd.ATUS_TOP_CODED_AGE
    elder = cd.elderly_per_capita(care_curve.pooled_years())
    assert max(elder) <= cd.ATUS_TOP_CODED_AGE
    for age, minutes in elder.items():
        assert 0.0 <= minutes < 24 * 60, f"age {age}: {minutes} min/person-day"


def test_every_care_figure_fits_inside_a_day():
    profile = cd.personal_profile(care_curve.pooled_years())
    for age, cell in profile.items():
        total = cell["total"]
        if total is not None:
            assert 0.0 < total < 24 * 60, f"age {age}: {total} min/day"


def test_attribution_orders_dup_above_split():
    """dup credits each recipient the full duration; split divides it."""
    years = care_curve.pooled_years()
    dup = cd.care_by_age(years, "dup")
    rho = cd.care_by_age(years, "rho")
    split = cd.care_by_age(years, "split")
    for age in (0, 3, 8):
        assert dup[age]["active"] > rho[age]["active"] > split[age]["active"]


def test_unknown_attribution_is_refused():
    with pytest.raises(ValueError, match="unknown attribution"):
        cd.care_by_age(None, "average")


def test_2020_is_excluded_by_default_and_reachable():
    assert 2020 not in cd.survey_years()
    assert 2020 in cd.survey_years(include_incomparable=True)


def test_coverage_names_a_reason_for_everything_it_drops():
    rows = cd.coverage()
    assert rows, "no coverage rows — exclusions are not being reported"
    for row in rows:
        assert row["reason"], "an exclusion with no reason"
        assert row["note"], f"{row['reason']} has no explanation"


def test_non_household_care_is_excluded_and_material():
    """The largest exclusion, and the one that makes the roster elderly figure wrong."""
    by_reason = {r["reason"]: r for r in cd.coverage()}
    assert "non_household" in by_reason
    assert int(by_reason["non_household"]["activities"]) > 10_000


def test_providers_per_household_refuses_rather_than_guesses():
    """Limit 1 is exposed, not silently applied."""
    with pytest.raises(NotImplementedError, match="ONE provider"):
        cd.providers_per_household()


def test_census_extract_partitions_the_population():
    shares = cd.population_shares(
        {name: g["range"] for name, g in AGE_GROUPS.items()}
    )
    assert sum(shares.values()) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# the findings
# ---------------------------------------------------------------------------

def test_care_alone_would_overstate_the_infant_weight_enormously():
    """Why `personal_profile` exists, demonstrated rather than asserted.

    Care received counts everything done FOR an infant and nothing an adult does
    for themselves, so on care alone an infant looks like ~25 working-age
    adults. This test pins the error the composition corrects.
    """
    profile = cd.personal_profile(care_curve.pooled_years())
    care_ratio = profile[0]["care"] / profile[40]["care"]
    assert care_ratio > 15.0, care_ratio
    total_ratio = profile[0]["care"] / float(profile[40]["total"])
    assert total_ratio < 4.0, total_ratio


def test_measured_weights_bracket_the_shipped_infant_and_child_values():
    """Infant and child are LOWER bounds and land just under their shipped values.

    Both bands contain ages ATUS does not survey, so their self-maintenance is
    missing and their totals can only rise. Reading just below 3.0 and 1.5 is
    therefore consistent with those weights, not evidence against them.
    """
    rows = {r["band"]: r for r in care_curve.implied_weights()["rows"]}
    for band in ("infant", "child"):
        row = rows[band]
        assert row["bound"] == "lower"
        assert 0.80 < row["ratio"] < 1.0, f"{band}: {row['ratio']}"


def test_the_elderly_weight_was_adopted_from_this_measurement():
    """The one band where both components are measured, and the one that moved.

    Adopted 2.5 → 1.48 on 2026-08-10. The shipped constant is the rounded
    measurement, so if a later ATUS vintage moves the measured value the two
    part company here rather than drifting quietly — the bind-by-test pattern
    `TestCarbonKappaReconciliation` uses, since data.py cannot import a
    measurement it sits below.
    """
    row = {r["band"]: r for r in care_curve.implied_weights()["rows"]}["elderly"]
    assert row["bound"] == "measured"
    assert round(float(row["implied_weight"]), 2) == AGE_GROUPS["elderly"]["eoh_weight"]


def test_the_institutional_caveat_is_why_this_is_a_lower_bound():
    """1.48 is the HOUSEHOLD-RESIDENT reading, and the gap is named not closed.

    ATUS covers the household population only, so the institutionalised
    elderly — who need the most care — are outside the frame entirely. The
    adopted weight is therefore a lower bound for the elderly population as a
    whole. What would close it is CMS Payroll-Based Journal staffing hours per
    resident-day; what would NOT is recipient-side activity monitoring, which
    measures the monitored person's own movement and physiology rather than
    anyone's care hours.
    """
    from utils import provenance as pv

    record = pv.load().by_name["AGE_WEIGHT_ELDERLY"]
    assert record.tag == "measured"
    assert record.tier == "B", "a survey with a named systematic exclusion is not Tier A"
    pointer = record.resolves_by
    assert "households only" in pointer, (
        "the institutional caveat left AGE_WEIGHT_ELDERLY's provenance block"
    )
    assert "Payroll-Based Journal" in pointer, (
        "the route that would close the gap is unnamed"
    )
    assert "TIHM" in pointer, (
        "the route that would NOT close it is unnamed, so someone will try it"
    )


def test_the_two_elderly_routes_disagree_by_an_order_of_magnitude():
    """Reported, never averaged. Averaging would produce a number describing nothing."""
    routes = care_curve.elderly_routes()
    assert routes["ratio"] > 5.0
    assert routes["module_minutes_per_person_day"] > routes[
        "roster_minutes_per_person_day"
    ]
    assert "ARTEFACT" in routes["note"]


def test_implied_w_is_below_the_shipped_bridge():
    weights = care_curve.implied_weights()
    assert weights["implied_w"] < weights["shipped_w"]


def test_measured_population_shares_are_close_to_the_shipped_fractions():
    """The fractions half of AGE_GROUPS: an OECD-shaped default, and near enough."""
    measured = care_curve.measured_population_shares()
    for band, group in AGE_GROUPS.items():
        assert abs(measured[band] - group["fraction"]) < 0.03, band


class TestOnlyTheElderlyWeightWasAdopted:
    """Exactly one weight moved, and the other three did not.

    Infant and child measure 2.55 and 1.35 against shipped 3.0 and 1.5, but
    both bands contain ages ATUS does not survey, so their totals are lower
    bounds that can only rise. Adopting a lower bound as a point estimate would
    revise those weights DOWN on the strength of a measurement that is missing
    a term — the opposite of what the evidence supports. They stay.
    """

    def test_the_unmeasured_bands_did_not_move(self):
        assert AGE_GROUPS["infant"]["eoh_weight"] == 3.0
        assert AGE_GROUPS["child"]["eoh_weight"] == 1.5

    def test_working_age_remains_the_numeraire(self):
        assert AGE_GROUPS["working_age"]["eoh_weight"] == 1.0

    def test_the_bridge_moved_by_the_documented_amount(self):
        """w 1.475 → 1.3016, −11.76%. Everything downstream of it moved with it."""
        w = sum(g["fraction"] * g["eoh_weight"] for g in AGE_GROUPS.values())
        assert w == pytest.approx(1.3016)
        assert w / 1.475 - 1.0 == pytest.approx(-0.1176, abs=5e-5)

    def test_the_fractions_were_not_touched(self):
        """The weights were revalued; the population split is a separate question.

        Moving both together would make the change in `w` impossible to
        attribute to either, and the fractions describe a jurisdiction rather
        than a measurement this framework owes.
        """
        assert [g["fraction"] for g in AGE_GROUPS.values()] == [0.07, 0.16, 0.60, 0.17]

    def test_no_core_module_imports_the_measurement(self):
        """The layer rule holds even after adoption.

        The VALUE crossed into `data.py`; the measurement module did not. `core/`
        still reads only `data.py`, so nothing on the stable path depends on a
        CSV in `reference/`.
        """
        import pathlib
        core = pathlib.Path(cd.__file__).resolve().parent.parent / "core"
        offenders = [
            p.name for p in core.glob("*.py")
            if "care_demand" in p.read_text(encoding="utf-8")
        ]
        assert not offenders, f"core/ reached for the measurement: {offenders}"


# --- the AGE_GROUPS split ---------------------------------------------------


class TestAgeGroupsSplit:
    """One constant carrying four epistemic states, separated 2026-08-10.

    `AGE_GROUPS` was tagged `placeholder` because a single tag reads its
    weakest element — so a chosen partition, jurisdiction data, a numeraire and
    two grades of measurement all inherited the tag of the worst one, and a
    reader learned nothing true about any of them.
    """

    def test_the_composite_is_byte_identical_to_its_parts(self):
        """The split is ADDITIVE: it renames nothing and moves no number."""
        from hours_eoh.data import (
            AGE_GROUP_FRACTIONS, AGE_GROUP_RANGES, AGE_WEIGHT_CHILD,
            AGE_WEIGHT_ELDERLY, AGE_WEIGHT_INFANT, AGE_WEIGHT_WORKING_AGE,
        )
        weights = {
            "infant": AGE_WEIGHT_INFANT, "child": AGE_WEIGHT_CHILD,
            "working_age": AGE_WEIGHT_WORKING_AGE, "elderly": AGE_WEIGHT_ELDERLY,
        }
        assert AGE_GROUPS == {
            name: {"range": AGE_GROUP_RANGES[name],
                   "fraction": AGE_GROUP_FRACTIONS[name],
                   "eoh_weight": weights[name]}
            for name in weights
        }

    def test_each_part_carries_its_own_epistemic_state(self):
        """The whole point of the split, asserted against the real data.py."""
        from utils import provenance as pv
        tags = {name: rec.tag for name, rec in pv.load().by_name.items()}
        assert tags["AGE_GROUP_RANGES"] == "convention"      # chosen, not found
        assert tags["AGE_GROUP_FRACTIONS"] == "instance"     # yours, not ours
        assert tags["AGE_WEIGHT_WORKING_AGE"] == "convention"  # the numeraire
        assert tags["AGE_WEIGHT_INFANT"] == "bounded"        # one-sided floor
        assert tags["AGE_WEIGHT_CHILD"] == "bounded"
        assert tags["AGE_WEIGHT_ELDERLY"] == "measured"      # both terms present
        assert tags["AGE_GROUPS"] == "derived"               # the composite

    def test_the_bounded_weights_state_a_one_sided_band(self):
        """A lower bound is not a band, and pretending otherwise would be worse
        than leaving them placeholders — so the band says which side is open."""
        from utils import provenance as pv
        by_name = pv.load().by_name
        for name in ("AGE_WEIGHT_INFANT", "AGE_WEIGHT_CHILD"):
            record = by_name[name]
            assert "one-sided" in record.band.lower(), name
            assert record.err_direction == "HIGH", name

    def test_the_fractions_name_the_census_as_the_intake_path(self):
        from utils import provenance as pv
        record = pv.load().by_name["AGE_GROUP_FRACTIONS"]
        assert "census" in record.supplied_by.lower()
        assert record.default, "an instance default with nothing said about it"
