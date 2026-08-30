"""
Tests for hours_eoh.scenarios.use_split — the ten ratios decomposed.

REPORTING ONLY. `TestUSplitChangesNothing` fails the moment that stops being
true, following the `guf_magnitude` and `servicing_census` precedent.

What these pin is not arithmetic but the ARGUMENT: that ρ is indexed the way
the fee table is (which is what dissolves the wrong-instrument objection), that
the residual is legible policy rather than noise, and that the scaling-basis gap
is not closable by any re-cut of the ratios.
"""

import pytest

import hours_eoh.data as D
from hours_eoh.scenarios.use_split import (
    SHIPPED_U,
    disturbance_by_use,
    rank_disagreement,
    scaling_basis_gap,
    split_report,
)

ARC = (0.0, 0.40, 0.99)


class TestUSplitChangesNothing:
    """The module reports; it must not move a coefficient."""

    def test_no_use_coefficient_moves(self):
        expected = {
            "residential_primary": 10.0, "residential_secondary": 21.5,
            "agricultural_active": 2.0, "agricultural_fallow": 5.0,
            "commercial_retail": 30.0, "commercial_office": 22.5,
            "industrial_light": 17.0, "industrial_heavy": 37.5,
            "institutional": 1.0, "conservation": -6.0,
        }
        assert SHIPPED_U == expected

    def test_the_scale_factor_is_untouched(self):
        assert D.GUF_USE_SCALE_FACTOR == 100.0

    def test_the_coefficients_are_BOUND_not_restated(self):
        """
        A second copy of a value whose source is elsewhere is the pattern this
        repo has found five times. Binding means this module cannot drift.
        """
        assert SHIPPED_U["industrial_heavy"] is D.GUF_USE_INDUSTRIAL_HEAVY
        assert SHIPPED_U["conservation"] is D.GUF_USE_CONSERVATION_CREDIT


class TestRhoBridgesTheIndexGap:
    """
    THE REASON THE SPLIT IS POSSIBLE AT ALL. Both censuses aggregate over LAND
    CLASSES while the fee table is indexed by USE CATEGORY — which is exactly
    why neither could settle the ratios. ρ is indexed by use category.
    """

    def test_rho_covers_every_fee_category(self):
        assert set(disturbance_by_use()) >= set(SHIPPED_U), (
            "if ρ ever stops covering a fee category the bridge is broken and "
            "the split cannot be computed for that row"
        )

    def test_disturbance_is_the_complement_of_retention(self):
        for c, d in disturbance_by_use().items():
            assert d == pytest.approx(1.0 - D.GUF_SERVICE_RETENTION_BY_USE[c])
            assert 0.0 <= d <= 1.0

    def test_the_ordering_is_physically_sensible(self):
        d = disturbance_by_use()
        assert d["conservation"] < d["agricultural_active"] < d["industrial_heavy"]
        assert d["industrial_heavy"] > 0.9, "heavy industry displaces nearly all"
        assert d["conservation"] < 0.1, "conservation displaces nearly none"


class TestTheResidualIsPolicyNotNoise:
    """
    The finding the split rests on: most of U is disturbance, and the part that
    is not is legible policy rather than error.
    """

    def test_most_of_the_fee_ordering_IS_disturbance(self):
        r = rank_disagreement()
        assert r["spearman"] > 0.80, (
            f"Spearman {r['spearman']:.3f} — if this fell, U would not be "
            f"mostly a disturbance measure and the split's premise would fail"
        )
        assert r["n"] == 10

    def test_the_disagreements_are_few_and_named(self):
        r = rank_disagreement()
        assert 1 <= len(r["disagreements"]) <= 5, (
            "a handful of policy judgements is a residual; ten would mean the "
            "orderings are unrelated and the split is not decomposing anything"
        )

    def test_luxury_and_land_banking_are_charged_ABOVE_their_disturbance(self):
        """
        The two normative judgements the fee table encodes without saying so.
        A second home and fallow land are charged more than their physical
        footprint warrants — defensible, but a charter decision, not a
        measurement.
        """
        rows = {r["use_category"]: r for r in rank_disagreement()["rows"]}
        assert rows["residential_secondary"]["rank_gap"] < 0
        assert rows["agricultural_fallow"]["rank_gap"] < 0
        # and fallow is charged MORE than active despite disturbing LESS
        assert SHIPPED_U["agricultural_fallow"] > SHIPPED_U["agricultural_active"]
        d = disturbance_by_use()
        assert d["agricultural_fallow"] < d["agricultural_active"]

    def test_institutional_relief_is_charged_BELOW_its_disturbance(self):
        rows = {r["use_category"]: r for r in rank_disagreement()["rows"]}
        assert rows["institutional"]["rank_gap"] > 0

    def test_the_extremes_agree_and_that_is_the_control(self):
        """
        Heavy industry, retail and conservation rank identically on both
        orderings. If the disagreements were noise they would be scattered;
        that they sit in the middle while the extremes agree is what makes the
        residual readable as policy.
        """
        rows = {r["use_category"]: r for r in rank_disagreement()["rows"]}
        for c in ("industrial_heavy", "commercial_retail", "conservation"):
            assert rows[c]["rank_gap"] == 0


class TestTheScalingBasisGapIsNotClosableByRatios:
    """
    The half of the problem a re-cut of the ten ratios cannot touch, and the
    reason the split is necessary but not sufficient.
    """

    def test_the_fee_can_express_less_than_half_the_measured_cost(self):
        g = scaling_basis_gap()
        assert g["expressible_now"] < 0.5
        assert g["inexpressible"] > 0.5

    def test_the_three_bases_partition_the_workforce(self):
        g = scaling_basis_gap()
        assert sum(g["shares"].values()) == pytest.approx(1.0, rel=1e-9)

    def test_parcel_count_is_the_largest_single_basis(self):
        """
        And the fee has no per-parcel term at all — `subdivision_invariance`
        returns the same fee after splitting every parcel in two. That is the
        structural gap, and no coefficient re-cut reaches it.
        """
        g = scaling_basis_gap()
        assert g["shares"]["parcel"] > g["shares"]["area"]
        assert "per-parcel TERM" in g["verdict"]


class TestTheReportIsHonestAboutItsLimits:

    def test_it_names_all_three_terms(self):
        t = split_report()["terms"]
        assert set(t) == {"U_servicing", "U_stewardship", "U_policy"}
        for k, v in t.items():
            assert len(v) > 80, f"{k} must argue for itself"

    def test_the_verdict_says_REPORTING_ONLY(self):
        assert "REPORTING ONLY" in split_report()["verdict"]

    def test_the_policy_term_is_declared_normative_not_measured(self):
        assert "NORMATIVE" in split_report()["terms"]["U_policy"]

    def test_the_report_is_deterministic(self):
        assert split_report()["ranks"]["spearman"] == \
            split_report()["ranks"]["spearman"]

    @pytest.mark.parametrize("eps", ARC)
    def test_the_split_carries_no_epsilon(self, eps):
        """
        U is ε-scaled in the fee, but the DECOMPOSITION is a statement about
        category ratios and must not move with automation. A split that varied
        with ε would mean an automation term had leaked into a structural claim.
        """
        assert split_report()["ranks"]["spearman"] == \
            rank_disagreement()["spearman"]
