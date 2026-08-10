"""
Block K-II — the measured knowledge base: recovery, back-derivation, band.

Covers `reference/onet_knowledge.py` (pure measurement) and
`scenarios/knowledge_base.py` (the back-derivation bridge). K-II is REPORTING
ONLY: the tests assert that it changes nothing, alongside asserting the numbers.
"""

import importlib
import inspect
import math

import pytest

from hours_eoh.core.eoh_generation import knowledge_eoh, skill_renewal_rate
from hours_eoh.data import (
    KNOWLEDGE_EOH_BASE,
    KNOWLEDGE_REFERENCE_POPULATION,
    SKILL_CPD_RATE,
    SKILL_DECAY_RATE,
    SKILL_TRANSMISSION_RATE,
    SKILL_WORKING_LIFE_YEARS,
)
from hours_eoh.reference.onet_knowledge import (
    occupation_training_hours,
    train_log_bounds,
    training_hours,
    workforce_training_stock,
)
from hours_eoh.scenarios.knowledge_base import (
    DEFAULT_EPSILON_REF_BAND,
    KEY_EPSILONS,
    domain_share_projection,
    embodied_stock_per_capita,
    employment_to_population,
    knowledge_base_band,
    knowledge_base_from_registry,
    epsilon_ref_fixed_point,
    labour_residual_epsilon,
    measured_knowledge_flow_per_capita,
    renewal_doctrine_comparison,
)


# ===========================================================================
# reference/onet_knowledge.py — the inversion
# ===========================================================================

class TestTrainingHoursInversion:

    def test_bounds_are_the_frozen_reference(self):
        lo, hi = train_log_bounds()
        assert lo == pytest.approx(6.647103615221381)
        assert hi == pytest.approx(10.524612487449065)

    def test_endpoints_recover_the_documented_range(self):
        assert training_hours(0.0) == pytest.approx(770.55, rel=1e-4)
        assert training_hours(1.0) == pytest.approx(37220.41, rel=1e-4)

    def test_monotone_in_f_training(self):
        prev = 0.0
        for i in range(21):
            h = training_hours(i / 20.0)
            assert h > prev
            prev = h

    def test_out_of_range_rejected(self):
        for bad in (-0.01, 1.01):
            with pytest.raises(ValueError, match="f_training must be in"):
                training_hours(bad)

    def test_inversion_is_exact_against_the_stored_factor(self):
        """The registry stores a monotone transform; we apply its inverse."""
        lo, hi = train_log_bounds()
        for row in occupation_training_hours()[:50]:
            recovered = (math.log(row["training_hours"]) - lo) / (hi - lo)
            assert recovered == pytest.approx(row["f_training"], abs=1e-9)


class TestWorkforceTrainingStock:

    def test_headline_figures(self):
        s = workforce_training_stock()
        assert s["n_occupations"] == 751
        assert s["covered_employment"] == pytest.approx(157_793_700.0)
        assert s["mean_hours_per_worker"] == pytest.approx(11_001.3, rel=1e-4)
        assert s["total_stock_hours"] == pytest.approx(1.7359e12, rel=1e-3)

    def test_mean_is_face_plausible_as_fte_years(self):
        """~5.3 FTE-years at 2,080 h/yr. A sanity check, not a validation."""
        s = workforce_training_stock()
        assert 4.0 < s["mean_hours_per_worker"] / 2080.0 < 7.0

    def test_winsor_tails_are_exactly_one_percent_per_side(self):
        """8 of 751 per tail is what 1/99 winsorization predicts — the designed
        baseline, not a defect. If this moves, the registry vintage changed."""
        s = workforce_training_stock()
        assert s["n_winsorized_low"] == 8
        assert s["n_winsorized_high"] == 8

    def test_clipped_employment_share_is_small(self):
        s = workforce_training_stock()
        assert s["winsorized_employment_share"] < 0.05

    def test_stock_equals_sum_over_occupations(self):
        rows = occupation_training_hours()
        s = workforce_training_stock()
        assert sum(r["employment"] * r["training_hours"] for r in rows) == \
            pytest.approx(s["total_stock_hours"])

    def test_returned_rows_are_defensive_copies(self):
        first = occupation_training_hours()
        first[0]["training_hours"] = -1.0
        assert occupation_training_hours()[0]["training_hours"] > 0.0


class TestReferenceLayerIsolation:
    """`reference/` is pure data — it may not import the domain layers."""

    def test_no_domain_imports(self):
        mod = importlib.import_module("hours_eoh.reference.onet_knowledge")
        source = inspect.getsource(mod)
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "hours_eoh.core" not in stripped
                assert "hours_eoh.land" not in stripped
                assert "hours_eoh.scenarios" not in stripped
                assert "hours_eoh.data" not in stripped


# ===========================================================================
# scenarios/knowledge_base.py — the back-derivation
# ===========================================================================

class TestPerCapitaRoutes:

    def test_two_routes_and_their_spread(self):
        registry = employment_to_population("registry")
        repo = employment_to_population("repo")
        assert registry == pytest.approx(0.500, abs=0.01)
        assert repo == pytest.approx(0.600)
        assert 1.15 < repo / registry < 1.25, "documented spread is 1.20x"

    def test_unknown_route_rejected(self):
        with pytest.raises(ValueError, match="route must be"):
            employment_to_population("guesswork")

    def test_measured_flow_matches_the_worked_example(self):
        flow = measured_knowledge_flow_per_capita("registry")
        assert flow["flow_per_capita_h_yr"] == pytest.approx(137.5, rel=1e-2)
        assert measured_knowledge_flow_per_capita("repo")["flow_per_capita_h_yr"] \
            == pytest.approx(165.0, rel=1e-2)

    def test_non_positive_working_life_rejected(self):
        with pytest.raises(ValueError, match="working_life_years must be positive"):
            measured_knowledge_flow_per_capita(working_life_years=0.0)


class TestBackDerivation:

    def test_reproduces_the_measured_flow_at_the_anchor(self):
        """
        The defining property, restated for K-III: at ε_ref, applying the
        TRANSMISSION rate to the derived base reproduces the measured flow —
        because the measured flow is itself stock x transmission. Under any
        other renewal doctrine the arc sits proportionally higher, which is the
        sensitivity the split exposes rather than hides.
        """
        for eps_ref in (0.2, 0.4, 0.6, 0.9):
            d = knowledge_base_from_registry(eps_ref)
            k_at_ref = (d["base_rate"] * _complexity(eps_ref) * SKILL_TRANSMISSION_RATE
                        / KNOWLEDGE_REFERENCE_POPULATION)
            assert k_at_ref == pytest.approx(d["flow_per_capita_h_yr"], rel=1e-9)

    def test_base_rate_falls_with_epsilon_ref(self):
        bases = [knowledge_base_from_registry(e)["base_rate"]
                 for e in (0.2, 0.4, 0.6)]
        assert bases[0] > bases[1] > bases[2]

    def test_epsilon_ref_out_of_range_rejected(self):
        for bad in (-0.01, 1.0):
            with pytest.raises(ValueError, match="epsilon_ref must be in"):
                knowledge_base_from_registry(bad)

    # NOTE (K-III): the K-II anchor `test_arc_is_decay_invariant` was REMOVED,
    # not weakened. It asserted that base_rate rescales with the decay while the
    # arc stays put — true only because the K-II derivation divided by a decay it
    # had not used to build the flow. With base_rate correctly decay-free the
    # relationship inverts: base_rate is invariant and the arc scales with d.
    # The replacements are TestBaseRateIsTheEmbodiedStock::test_base_rate_is_decay_free
    # and TestRenewalDoctrineComparison::test_arc_is_linear_in_the_renewal_rate.

    def test_arc_figures_by_doctrine_at_the_default_anchor(self):
        """
        Both doctrines pinned, so the renewal rate's leverage is explicit. The
        transmission figures are K-II's and must not have moved; the default
        figures are 4x higher purely because SKILL_DECAY_RATE is 4x the
        measurable rate.
        """
        d = knowledge_base_from_registry(0.40)
        base = d["base_rate"]

        def arc(rate: float, eps: float) -> float:
            return base * _complexity(eps) * rate / KNOWLEDGE_REFERENCE_POPULATION

        assert arc(SKILL_TRANSMISSION_RATE, 0.0) == pytest.approx(12.3, rel=2e-2)
        assert arc(SKILL_TRANSMISSION_RATE, 0.40) == pytest.approx(137.5, rel=1e-2)
        assert arc(SKILL_TRANSMISSION_RATE, 0.99) == pytest.approx(1192.0, rel=1e-2)

        k = d["knowledge_h_per_capita"]
        assert k[0.0] == pytest.approx(49.0, rel=2e-2)
        assert k[0.40] == pytest.approx(550.1, rel=1e-2)
        assert k[0.99] == pytest.approx(4770.0, rel=1e-2)

    def test_finite_across_the_arc(self):
        for eps_ref in (0.0, 0.40, 0.90, 0.99):
            d = knowledge_base_from_registry(eps_ref)
            assert math.isfinite(d["base_rate"]) and d["base_rate"] > 0.0
            for v in d["knowledge_h_per_capita"].values():
                assert math.isfinite(v) and v > 0.0


class TestBand:

    def test_epsilon_ref_dominates_the_measurement(self):
        """The headline: the anchoring assumption beats the data by ~6x."""
        b = knowledge_base_band()
        assert b["epsilon_ref_spread"] == pytest.approx(7.13, rel=2e-2)
        assert b["route_spread"] == pytest.approx(1.20, rel=2e-2)
        assert b["dominant_uncertainty"] == "epsilon_ref"
        assert b["epsilon_ref_spread"] > 5.0 * b["route_spread"]

    def test_band_spans_every_combination(self):
        b = knowledge_base_band()
        assert len(b["rows"]) == len(DEFAULT_EPSILON_REF_BAND) * 2
        assert b["base_rate_low"] < b["base_rate_high"]

    def test_adopted_constant_sits_inside_the_band(self):
        """Post-K-IV: the shipped constant IS a point in this band (ε_ref=0.40,
        registry route). Before adoption the whole band sat >500× above it."""
        b = knowledge_base_band()
        assert b["base_rate_low"] <= KNOWLEDGE_EOH_BASE <= b["base_rate_high"]

    def test_adopted_constant_matches_the_live_derivation(self):
        """
        THE FREEZE CHECK. KNOWLEDGE_EOH_BASE is derived-then-FROZEN at the
        2026-07-29 epoch. If an O*NET/BLS refresh moves the registry, this fails
        loudly rather than letting the constant drift away from its derivation.

        Re-anchored 2026-08-09 (Finding E) and again 2026-08-10: the derivation
        is checked at the FIXED POINT ε* = 0.3828, not at K-IV's one-shot 0.40,
        because a one-shot anchor is not a fixed point of its own derivation —
        adopting the base it produces moves total EOH, which moves the labour
        residual that corroborated the anchor in the first place. The second
        re-anchor was triggered from OUTSIDE the knowledge domain, by the
        AGE_GROUPS elderly revalue.
        """
        live = knowledge_base_from_registry(
            0.3828218221664429, route="registry", decay=SKILL_TRANSMISSION_RATE
        )["base_rate"]
        assert KNOWLEDGE_EOH_BASE == pytest.approx(live, rel=1e-6)

    def test_empty_inputs_rejected(self):
        with pytest.raises(ValueError, match="epsilon_refs must not be empty"):
            knowledge_base_band(epsilon_refs=())
        with pytest.raises(ValueError, match="routes must not be empty"):
            knowledge_base_band(routes=())


class TestDomainShareProjection:

    def test_projection_pairs_the_measured_base_with_the_split_rate(self):
        """Adopting a measured stock while keeping a rate that implies 55% of a
        work-year would be incoherent — the projection pairs both."""
        assert domain_share_projection()["decay"] == pytest.approx(
            skill_renewal_rate()["total"]
        )

    def test_knowledge_becomes_material_and_personal_falls(self):
        p = domain_share_projection()
        rows = {r["epsilon"]: r for r in p["rows"]}
        assert rows[0.0]["personal_share"] == pytest.approx(0.943, abs=0.01)
        # 0.489 → 0.457: personal fell 11.76% with the elderly revalue while the
        # other domains held, so its share at the top of the arc fell with it.
        assert rows[0.99]["personal_share"] == pytest.approx(0.457, abs=0.01)
        # 0.437 → 0.464, the same mechanism seen from the other side: knowledge
        # did not grow, the total it is a share of shrank.
        assert rows[0.99]["knowledge_share"] == pytest.approx(0.464, abs=0.01)

    def test_delivers_the_behaviour_the_docstring_asserts(self):
        """knowledge_eoh's own reference says human labor at ε→1 is 'almost
        entirely care, judgment, and knowledge maintenance'. Post-K-IV the
        domain is the largest non-personal one at the top of the arc — the
        behaviour the model asserted for years and never delivered."""
        rows = {r["epsilon"]: r for r in domain_share_projection()["rows"]}
        top = rows[0.99]
        assert top["knowledge_share"] > top["infrastructure_share"]
        assert top["knowledge_share"] > 0.35

    def test_does_not_fix_domain_balance_on_its_own(self):
        """Honest limit, asserted so it cannot be quietly overstated later."""
        p = domain_share_projection()
        lo, hi = p["personal_share_range"]
        assert hi > 0.90, "personal still dominates the low arc"

    def test_shares_sum_to_one(self):
        for r in domain_share_projection()["rows"]:
            total = (r["personal_share"] + r["infrastructure_share"]
                     + r["ecological_share"] + r["knowledge_share"])
            assert total == pytest.approx(1.0)


class TestRenewalRateSplit:
    """
    Block K-III: SKILL_DECAY_RATE was conflating cohort transmission with
    continuing practice. These tests pin the components AND the discrepancy the
    split exposes — the discrepancy is the finding, not a defect to reconcile.
    """

    def test_components_sum_to_total(self):
        s = skill_renewal_rate()
        assert s["total"] == pytest.approx(s["transmission"] + s["cpd"])

    def test_transmission_is_derived_from_working_life(self):
        """Derived, not chosen: it is 1/working_life and nothing else."""
        assert SKILL_TRANSMISSION_RATE == pytest.approx(1.0 / SKILL_WORKING_LIFE_YEARS)
        assert skill_renewal_rate()["transmission"] == pytest.approx(0.025)

    def test_split_does_not_reproduce_the_shipped_rate(self):
        """
        THE FALSIFICATION TEST. The components are set INDEPENDENTLY from
        evidence; they are not back-solved to sum to 0.10. If a future edit
        tunes either one to close the gap, this fails and the reconciliation
        becomes visible instead of silent.
        """
        s = skill_renewal_rate()
        assert s["total"] == pytest.approx(0.0277)
        assert s["total"] != pytest.approx(SKILL_DECAY_RATE, rel=0.5), (
            "components must NOT be tuned to reproduce the shipped placeholder"
        )
        assert s["ratio_to_shipped"] == pytest.approx(0.277, rel=1e-3)

    def test_measurable_component_dominates(self):
        """Transmission (derivable) is ~90% of the total; CPD (not in O*NET,
        the weakest input) carries only the remaining tenth."""
        assert skill_renewal_rate()["transmission_share"] > 0.85

    def test_negative_components_rejected(self):
        with pytest.raises(ValueError, match="transmission must be non-negative"):
            skill_renewal_rate(transmission=-0.01)
        with pytest.raises(ValueError, match="cpd must be non-negative"):
            skill_renewal_rate(cpd=-0.01)

    def test_split_is_epsilon_free(self):
        """Neither component is ε-driven — ageing and field churn do not wait
        for automation, and cpu already carries the apparatus's complexity."""
        assert skill_renewal_rate()["total"] == pytest.approx(
            skill_renewal_rate()["total"]
        )
        for eps in (0.0, 0.40, 0.99):
            k_split = knowledge_eoh(1.0, skill_renewal_rate()["total"], epsilon=eps)
            k_manual = knowledge_eoh(
                1.0, SKILL_TRANSMISSION_RATE + SKILL_CPD_RATE, epsilon=eps
            )
            assert k_split == pytest.approx(k_manual)


class TestRenewalDoctrineComparison:

    def test_shipped_rate_is_not_credible_against_the_measured_stock(self):
        """
        The K-III headline. d = 0.10 on an 11,001 h stock means every worker
        spends over half of every working year re-acquiring knowledge they
        already hold. Asserted so it cannot be quietly restored.
        """
        d = renewal_doctrine_comparison()["doctrines"]
        assert d["shipped"]["work_year_share"] > 0.50
        assert d["shipped"]["credible"] is False
        assert d["split"]["credible"] is True
        assert d["transmission"]["credible"] is True

    def test_shipped_is_roughly_four_times_the_components(self):
        r = renewal_doctrine_comparison()
        assert r["shipped_over_split"] == pytest.approx(3.61, rel=2e-2)

    def test_transmission_doctrine_reproduces_the_k2_arc(self):
        """
        CONTINUITY CHECK. K-II's arc was built at the transmission rate; the
        decay-free base fix must leave it exactly where it was.
        """
        k = renewal_doctrine_comparison()["doctrines"]["transmission"]["knowledge_h_per_capita"]
        assert k[0.0] == pytest.approx(12.3, rel=2e-2)
        assert k[0.40] == pytest.approx(137.5, rel=1e-2)
        assert k[0.99] == pytest.approx(1192.0, rel=1e-2)

    def test_arc_is_linear_in_the_renewal_rate(self):
        """base_rate is now the STOCK, so the arc scales with d exactly."""
        d = renewal_doctrine_comparison()["doctrines"]
        ratio = d["shipped"]["renewal_rate"] / d["transmission"]["renewal_rate"]
        for eps in KEY_EPSILONS:
            assert d["shipped"]["knowledge_h_per_capita"][eps] == pytest.approx(
                d["transmission"]["knowledge_h_per_capita"][eps] * ratio
            )


class TestBaseRateIsTheEmbodiedStock:
    """
    K-III corrects a K-II inconsistency: the derivation built the flow at the
    transmission rate but divided by SKILL_DECAY_RATE, returning a base 4x
    smaller than the stock K-I documented it as.
    """

    def test_base_rate_is_decay_free(self):
        a = knowledge_base_from_registry(0.40, decay=SKILL_DECAY_RATE)
        b = knowledge_base_from_registry(0.40, decay=1.0 / 40.0)
        assert a["base_rate"] == pytest.approx(b["base_rate"]), (
            "base_rate is the embodied stock — no renewal rate may enter it"
        )

    def test_base_rate_recovers_the_stock_at_the_anchor(self):
        """base_rate · kbs(ε_ref) · cpu(ε_ref) / P_ref == measured stock/capita."""
        for eps_ref in (0.0, 0.2, 0.40, 0.6, 0.9):
            d = knowledge_base_from_registry(eps_ref)
            recovered = d["base_rate"] * _complexity(eps_ref) / KNOWLEDGE_REFERENCE_POPULATION
            assert recovered == pytest.approx(d["embodied_stock_per_capita"], rel=1e-9)

    def test_embodied_stock_matches_the_registry(self):
        assert embodied_stock_per_capita("registry") == pytest.approx(5500.7, rel=1e-3)
        assert embodied_stock_per_capita("repo") == pytest.approx(6600.8, rel=1e-3)


class TestKIVAdoption:
    """
    Block K-IV adopted the measurement. `TestKIIChangesNothing` — which pinned
    the pre-adoption constants and existed to fail the moment K-II started
    adopting — was REPLACED by these, deliberately, when adoption happened.
    """

    def test_constant_is_the_measured_value_not_the_placeholder(self):
        assert KNOWLEDGE_EOH_BASE != 100_000.0
        # 4.9010742e8 was the K-IV value at the one-shot ε_ref = 0.40. Finding E
        # cut it to 0.779× that; the 2026-08-10 elderly revalue moved the fixed
        # point again and put it at 1.089×, back above the K-IV figure.
        assert KNOWLEDGE_EOH_BASE == pytest.approx(5.3362082e8, rel=1e-6)

    def test_default_renewal_rate_is_the_lower_credible_doctrine(self):
        """
        "Use the lower rate" (author, 2026-08-08): transmission alone, the
        lowest of the three doctrines and the only one containing no CHOSEN
        component. CPD is excluded from the default, NOT denied — the constant
        and skill_renewal_rate() still carry it.
        """
        from hours_eoh.params import EohParams
        assert EohParams()["skill_decay_rate"] == pytest.approx(SKILL_TRANSMISSION_RATE)
        assert SKILL_TRANSMISSION_RATE < skill_renewal_rate()["total"]
        assert SKILL_TRANSMISSION_RATE < SKILL_DECAY_RATE

    def test_adopted_default_understates_the_split_by_a_known_margin(self):
        """The deliberate understatement, quantified so it stays visible."""
        split = skill_renewal_rate()["total"]
        assert SKILL_TRANSMISSION_RATE / split == pytest.approx(0.903, abs=0.01)

    def test_deprecated_placeholder_is_retained_not_deleted(self):
        """Additive-not-destructive: every pre-K-IV figure in this repo was
        produced at 0.10, so reproducing one means passing it explicitly."""
        assert SKILL_DECAY_RATE == 0.10


def _unit(epsilon: float) -> float:
    return knowledge_eoh(1.0, SKILL_DECAY_RATE, epsilon=epsilon, base_rate=1.0,
                         population=KNOWLEDGE_REFERENCE_POPULATION)


def _complexity(epsilon: float) -> float:
    """kbs(ε)·cpu(ε) — the decay-free response."""
    return knowledge_eoh(1.0, 1.0, epsilon=epsilon, base_rate=1.0,
                         population=KNOWLEDGE_REFERENCE_POPULATION)


# ===========================================================================
# Finding E — the ε_ref fixed point (approved 2026-08-09)
# ===========================================================================

class TestLabourResidual:

    def test_paid_labour_gives_the_documented_residual(self):
        """US 2025 paid labour, 937.3 h/person·yr, against the shipped base.

        0.4522 → 0.3828 after the 2026-08-10 elderly revalue and the knowledge
        re-anchor that followed it. At the fixed point this equals ε*, which is
        what makes it a fixed point.
        """
        eps = labour_residual_epsilon(937.3, KNOWLEDGE_EOH_BASE)
        assert eps == pytest.approx(0.3828, abs=0.005)

    def test_full_labour_has_no_solution(self):
        """
        FINDING B, encoded. Paid + unpaid labour (1,701.1 h/person·yr) exceeds
        the ENTIRE obligation at ε=0, so no ε explains it. The solver must
        return None rather than clamping to zero — "no anchor fits this" and
        "the anchor is zero" are different claims.
        """
        assert labour_residual_epsilon(1701.1, KNOWLEDGE_EOH_BASE) is None

    def test_residual_is_decreasing_in_observed_hours(self):
        """More labour supplied ⇒ less must be machine-fulfilled."""
        low = labour_residual_epsilon(600.0, KNOWLEDGE_EOH_BASE)
        high = labour_residual_epsilon(1200.0, KNOWLEDGE_EOH_BASE)
        assert low is not None and high is not None
        assert low > high

    def test_negative_hours_rejected(self):
        with pytest.raises(ValueError, match="must be non-negative"):
            labour_residual_epsilon(-1.0, KNOWLEDGE_EOH_BASE)


class TestEpsilonRefFixedPoint:

    def test_converges_to_the_adopted_anchor(self):
        r = epsilon_ref_fixed_point(937.3)
        assert r["converged"] is True
        # 0.4522 → 0.3828 with the 2026-08-10 elderly revalue.
        assert r["epsilon_fixed_point"] == pytest.approx(0.3828, abs=0.001)

    def test_the_fixed_point_reproduces_the_shipped_constant(self):
        """
        THE ADOPTION CHECK, and the repo's coupling detector.

        The shipped base must BE the fixed point's base. It has now been
        re-anchored twice — Finding E (2026-08-09, ε* 0.4522) and the AGE_GROUPS
        elderly revalue (2026-08-10, ε* 0.3828) — and the second re-anchor is
        the more instructive one, because its cause was a constant in a
        DIFFERENT DOMAIN.

        This constant is defined by a fixed-point condition over `total_eoh`,
        so it is conditional on every constant entering that total. This test
        therefore fires whenever anything upstream moves, and that firing is
        the FEATURE: it is the only thing standing between the repo and a
        silently stale derived constant. Expect it to fire again when domain
        balance is fixed and when abatement becomes the default generation
        path. Both should trip it; neither should be worked around.
        """
        r = epsilon_ref_fixed_point(937.3)
        assert r["base_rate"] == pytest.approx(KNOWLEDGE_EOH_BASE, rel=1e-6)
        assert r["is_shipped_anchor"] is True

    def test_it_is_actually_a_fixed_point(self):
        """The defining property: the anchor it derives AT equals the anchor the
        labour residual IMPLIES given the base that derivation produces."""
        r = epsilon_ref_fixed_point(937.3)
        implied = labour_residual_epsilon(937.3, r["base_rate"])
        assert implied == pytest.approx(r["epsilon_fixed_point"], abs=1e-3)

    def test_the_k4_anchor_was_not_one(self):
        """
        FINDING E, stated as a test. K-IV derived at ε_ref = 0.40 because the
        labour residual corroborated it at 0.391 — and the adoption then moved
        the residual to 0.470. A one-shot anchor cannot be self-consistent when
        the constant it sets sits inside the quantity that checks it.
        """
        k4_base = knowledge_base_from_registry(
            0.40, route="registry", decay=SKILL_TRANSMISSION_RATE
        )["base_rate"]
        # 0.470 at the pre-revalue w; 0.376 now. The ARGUMENT is unchanged and
        # is in fact reinforced: the anchor moved again, for a third reason.
        assert labour_residual_epsilon(937.3, k4_base) == pytest.approx(0.376, abs=0.005)
        assert k4_base == pytest.approx(4.9010742e8, rel=1e-6)

    def test_independent_of_the_starting_anchor(self):
        """A fixed point is a property of the map, not of where you start."""
        results = [
            epsilon_ref_fixed_point(937.3, epsilon_start=start)["epsilon_fixed_point"]
            for start in (0.20, 0.40, 0.70)
        ]
        for value in results:
            assert value == pytest.approx(results[0], abs=1e-3)

    def test_re_anchor_moved_the_base_by_the_documented_factor(self):
        """Against the K-IV base, the fixed point of comparison across re-anchors.

        0.779× at the Finding-E adoption (2026-08-09); 1.089× after the elderly
        revalue moved the fixed point again (2026-08-10). The base has now
        crossed ABOVE the K-IV value it was first cut below — the anchor is a
        genuinely moving quantity, not a one-time correction.
        """
        r = epsilon_ref_fixed_point(937.3)
        assert r["base_rate"] / 4.9010742e8 == pytest.approx(1.089, abs=0.005)
        assert KNOWLEDGE_EOH_BASE / 4.9010742e8 == pytest.approx(1.089, abs=0.005)

    def test_flags_when_the_shipped_constant_stops_being_the_fixed_point(self):
        """
        The self-check K-IV lacked. Change the observed-hours input — or let a
        registry vintage or an upstream total-EOH shift move things — and the
        shipped constant is no longer the fixed point, and this says so instead
        of silently reporting a stale anchor.
        """
        r = epsilon_ref_fixed_point(800.0)
        assert r["is_shipped_anchor"] is False
        assert "NOT a fixed point" in r["note"]

    def test_over_determined_input_reports_finding_b_not_a_failure(self):
        r = epsilon_ref_fixed_point(1701.1)
        assert r["epsilon_fixed_point"] is None
        assert r["converged"] is False
        assert "Finding B" in r["note"]
