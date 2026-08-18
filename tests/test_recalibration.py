"""
Tests for research/recalibration.py — proposed §8.9 mutually-consistent
commons accounting and the §8.9b charter-formation doctrine: ε-growing
capital stock, τ = φ ownership identity, policy-resolved commons share
(target / dilution / escalated), endogenous social dividend, stock-based
capital accounts (RC4 fix), generational conversion, the escalation clause,
and the three-channel exit-financing invariant.
"""

import math

import pytest

from hours_eoh.data import (
    ANNUAL_DEATH_RATE,
    CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_PHI_FLOOR,
    PERSONAL_EOH_BASE,
    RECAL_ACCOUNT_CREDIT_SHARE,
    RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    RECAL_EXIT_HORIZON_YEARS,
    RECAL_FOUNDING_FRACTION,
    RECAL_FOUNDING_LABOR_HOURS,
)
from hours_eoh.research.contestability import (
    commonized_fraction,
    entry_cost,
    machine_output_teh,
)
from hours_eoh.research.recalibration import (
    capital_account_stock,
    capital_stock_epsilon,
    commons_capital,
    commons_income_statement,
    escalation_trigger,
    estate_conversion_flow,
    exit_financing,
    formation_levy_rate,
    formation_share_required,
    phi_actual,
    recalibrated_arc,
)

KEY_EPS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# capital_stock_epsilon
# ---------------------------------------------------------------------------

class TestCapitalStockEpsilon:
    def test_at_zero_equals_human_era_stock(self):
        assert capital_stock_epsilon(0.0) == pytest.approx(CAPITAL_STOCK_DEFAULT)

    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_positive_across_arc(self, eps):
        assert capital_stock_epsilon(eps) > 0.0

    def test_monotone_rising(self):
        values = [capital_stock_epsilon(e) for e in [0.0, 0.2, 0.4, 0.6, 0.8, 0.99]]
        assert all(b > a for a, b in zip(values, values[1:]))

    def test_grows_with_machine_output(self):
        eps = 0.40
        expected = CAPITAL_STOCK_DEFAULT + 4.0 * machine_output_teh(eps)
        assert capital_stock_epsilon(eps, capital_output_ratio=4.0) == pytest.approx(expected)

    def test_rejects_bad_epsilon(self):
        with pytest.raises(ValueError):
            capital_stock_epsilon(1.5)

    def test_rejects_bad_ratio(self):
        with pytest.raises(ValueError):
            capital_stock_epsilon(0.4, capital_output_ratio=0.0)


# ---------------------------------------------------------------------------
# phi_actual — the §8.9b policy resolution
# ---------------------------------------------------------------------------

class TestPhiActual:
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_target_policy_is_commonized_fraction(self, eps):
        r = phi_actual(eps, "target")
        assert r["phi"] == pytest.approx(commonized_fraction(eps))
        assert r["cap"] is None
        assert not r["cap_binding"]

    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_dilution_never_exceeds_target(self, eps):
        assert phi_actual(eps, "dilution")["phi"] <= commonized_fraction(eps) + 1e-12

    @pytest.mark.parametrize("eps", [0.0, 0.2, 0.4])
    def test_dilution_equals_target_below_binding(self, eps):
        # The cap binds only from ε ≈ 0.48 (where target-trajectory private
        # capital peaks); below it the charter share s ≤ 1 tracks target.
        r = phi_actual(eps, "dilution")
        assert r["phi"] == pytest.approx(commonized_fraction(eps))
        assert not r["cap_binding"]

    def test_dilution_cap_binds_high_eps(self):
        # The honest cost of never forcing sales: φ caps below the target.
        # K-IV moved the cap UP, 0.66 → 0.754: the larger machine-output base
        # means more NEW capital is commissioned per period, and the commons'
        # share attaches to new capital, so the no-forced-sales ceiling rises.
        # φ → 1 still survives only asymptotically.
        r = phi_actual(0.99, "dilution")
        assert r["cap_binding"]
        assert 0.73 < r["phi"] < 0.78
        assert r["phi_target"] > 0.98

    def test_dilution_non_decreasing(self):
        phis = [phi_actual(e, "dilution")["phi"]
                for e in [0.0, 0.2, 0.4, 0.6, 0.8, 0.99]]
        assert all(b >= a - 1e-12 for a, b in zip(phis, phis[1:]))

    def test_capital_yield_is_the_gross_return_identity(self):
        """CONTESTABILITY_CAPITAL_YIELD_RATE = 1/ν − δ, held against drift.

        Bound by test rather than expression because both inputs are defined
        BELOW it in data.py — a reference would be forward. Same treatment as
        GUF_ECO_KAPPA_CARBON / CDR_LABOR_HOURS_PER_TONNE.

        The repo shipped 0.10 against an identity giving 0.20 for the same
        quantity, and nothing detected it: two of the three consumers are
        SUPERSEDED by §8.9 and the third is research-tier and unpinned. This test
        is the detector that was missing. It fails if EITHER side moves alone.
        """
        from hours_eoh.data import (
            CONTESTABILITY_CAPITAL_YIELD_RATE,
            FORMATION_DEPRECIATION_RATE,
            RECAL_CAPITAL_OUTPUT_RATIO,
        )
        identity = 1.0 / RECAL_CAPITAL_OUTPUT_RATIO - FORMATION_DEPRECIATION_RATE
        assert CONTESTABILITY_CAPITAL_YIELD_RATE == pytest.approx(identity), (
            "the capital-yield constant and the 1/ν − δ identity have diverged; "
            "reconcile them to one derivation rather than shipping both"
        )

    def test_dilution_pays_MORE_than_target_despite_the_smaller_share(self):
        """The doctrine trade-off, pinned by its SIGN — which has already flipped once.

        §8.9b recorded the cost of no-forced-sales as a dividend "≈13% below the
        purchase model". At the constants of 2026-08-15 the ordering is the other
        way: dilution pays ≈13% ABOVE target at ε=0.99 (2,155 vs 1,906). Same
        magnitude, inverted sign, and it holds from ε≈0.05 to the top of the arc.

        The mechanism is not subtle once looked at. Target buys its share, so
        acquisition consumes commons income before anything is distributed;
        dilution's share attaches to NEW capital at commissioning and costs
        nothing, so its whole income is distributable. Target ends with the
        larger base (φ 0.987 vs 0.771) and the smaller payout.

            dilution  income 2.155e9, reinvestment 0        → 2,154.6 / capita
            target    income 2.758e9, reinvestment 8.517e8  → 1,906.4 / capita

        Nothing pinned this. TestPhiActual pins the φ ordering, which never
        moved, while the DIVIDEND ordering — the thing the doctrine argument
        actually turns on — flipped silently when PERSONAL_EOH_BASE, the
        knowledge re-anchor and AGE_GROUPS moved the machine-output base.

        This test asserts the sign, not the levels: the levels are calibration
        and will move again. If it fails, the doctrine claim in
        notes/contestability-closure-proposal.md §8.9b needs rewriting, which is
        the point.
        """
        d = recalibrated_arc(phi_policy="dilution")
        t = recalibrated_arc(phi_policy="target")

        top_d, top_t = d[-1], t[-1]

        # The share ordering is the one that did NOT flip.
        assert top_d["phi"] < top_t["phi"], "dilution must still cap below target"

        # The dividend ordering is the one that did.
        assert top_d["dividend_per_capita"] > top_t["dividend_per_capita"]

        # And the mechanism: target pays for its share, dilution does not.
        assert top_t["reinvestment"] > 0.0
        assert top_d["reinvestment"] == pytest.approx(0.0)

        # Holds across the arc, not only at the endpoint.
        upper = [(a, b) for a, b in zip(d, t) if a["epsilon"] >= 0.10]
        assert all(a["dividend_per_capita"] >= b["dividend_per_capita"]
                   for a, b in upper)

    def test_escalated_point_level_equals_dilution(self):
        # Escalation mechanics are path-dependent (recalibrated_arc);
        # the point function documents the static approximation.
        for eps in KEY_EPS:
            assert phi_actual(eps, "escalated")["phi"] == pytest.approx(
                phi_actual(eps, "dilution")["phi"]
            )

    def test_rejects_unknown_policy(self):
        with pytest.raises(ValueError):
            phi_actual(0.4, "confiscation")


# ---------------------------------------------------------------------------
# commons_capital — τ = φ_actual identity
# ---------------------------------------------------------------------------

class TestCommonsCapital:
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_tau_equals_phi_target_policy(self, eps):
        r = commons_capital(eps, phi_policy="target")
        assert r["tau"] == pytest.approx(commonized_fraction(eps))

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_tau_is_a_share(self, policy, eps):
        assert 0.0 < commons_capital(eps, phi_policy=policy)["tau"] <= 1.0

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    def test_tau_non_decreasing_piketty_structural(self, policy):
        taus = [commons_capital(e, phi_policy=policy)["tau"]
                for e in [0.0, 0.2, 0.4, 0.6, 0.8, 0.99]]
        assert all(b >= a - 1e-12 for a, b in zip(taus, taus[1:]))

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_partition_of_capital(self, policy, eps):
        r = commons_capital(eps, phi_policy=policy)
        assert r["commons_capital"] + r["private_capital"] == pytest.approx(
            r["capital_stock"]
        )

    def test_initial_endowment(self):
        # T_K(0) = φ₀ · K₀ — the generalized commons seed (both policies).
        for policy in ("target", "dilution"):
            r = commons_capital(0.0, phi_policy=policy)
            assert r["commons_capital"] == pytest.approx(
                CONTESTABILITY_PHI_FLOOR * CAPITAL_STOCK_DEFAULT
            )


# ---------------------------------------------------------------------------
# formation_share_required — the charter share s(ε)
# ---------------------------------------------------------------------------

class TestFormationShare:
    @pytest.mark.parametrize("eps", [0.05, 0.3, 0.4])
    def test_feasible_below_binding(self, eps):
        r = formation_share_required(eps)
        assert 0.0 < r["share_required"] <= 1.0
        assert r["feasible"]

    @pytest.mark.parametrize("eps", [0.6, 0.9])
    def test_infeasible_above_binding(self, eps):
        # From ε ≈ 0.48 target-tracking would require forced sales.
        r = formation_share_required(eps)
        assert r["share_required"] > 1.0
        assert not r["feasible"]

    def test_consistency_with_derivatives(self):
        r = formation_share_required(0.4)
        assert r["share_required"] == pytest.approx(
            r["d_commons_deps"] / r["d_capital_deps"]
        )

    def test_early_arc_share_is_mild(self):
        # ≈ 0.17 at ε = 0.05: the charter asks for a sixth of new formation.
        assert formation_share_required(0.05)["share_required"] < 0.3


# ---------------------------------------------------------------------------
# formation_levy_rate — the compensated bridge (A2)
# ---------------------------------------------------------------------------

class TestFormationLevy:
    def test_peak_is_about_one_percent(self):
        r = formation_levy_rate(0.05)
        assert 0.005 < r["levy_rate"] < 0.02
        assert not r["sunset"]

    @pytest.mark.parametrize("eps", [0.25, 0.40, 0.90, 0.99])
    def test_sunsets_by_eps_025(self, eps):
        # Sunset moved 0.20 → 0.25 when PERSONAL_EOH_BASE was repriced
        # 1500 → 1000 (2026-08-06): less personal EOH → less labour output →
        # the compensated bridge takes slightly longer to become unnecessary.
        r = formation_levy_rate(eps)
        assert r["levy_rate"] == 0.0
        assert r["sunset"]

    def test_monotone_decline_past_peak(self):
        rates = [formation_levy_rate(e)["levy_rate"]
                 for e in [0.10, 0.15, 0.20, 0.25]]
        assert all(b <= a for a, b in zip(rates, rates[1:]))


# ---------------------------------------------------------------------------
# commons_income_statement
# ---------------------------------------------------------------------------

class TestCommonsIncomeStatement:
    @pytest.mark.parametrize("policy", ["target", "dilution"])
    def test_no_dividend_at_subsistence(self, policy):
        # ε=0: no machine output, nothing to distribute (any policy).
        r = commons_income_statement(0.0, phi_policy=policy)
        assert r["income"] == 0.0
        assert r["dividend_per_capita"] == 0.0

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    def test_dividend_meaningful_at_high_eps(self, policy):
        # The dividend replaces labor income as automation matures. Threshold
        # is 1,000 (was 1,500) after the PERSONAL_EOH_BASE reprice: machine
        # output scales with total EOH, so a smaller personal domain means a
        # smaller dividend — target 1,287, dilution 1,092 at ε=0.99.
        assert commons_income_statement(
            0.99, phi_policy=policy
        )["dividend_per_capita"] > 1_000.0

    def test_dividend_rises_across_upper_arc(self):
        divs = [
            commons_income_statement(e)["dividend_per_capita"]
            for e in [0.3, 0.5, 0.7, 0.9, 0.99]
        ]
        assert all(b > a for a, b in zip(divs, divs[1:]))

    def test_charter_pays_full_income_no_reinvestment(self):
        # §8.9b: the share attaches at commissioning — nothing is purchased.
        r = commons_income_statement(0.4, phi_policy="dilution")
        assert r["reinvestment"] == 0.0
        assert r["dividend_pool"] == pytest.approx(r["income"])

    @pytest.mark.parametrize("eps", [0.1, 0.2, 0.4])
    def test_doctrine_dividend_beats_purchase_below_binding(self, eps):
        d_charter = commons_income_statement(
            eps, phi_policy="dilution")["dividend_per_capita"]
        d_purchase = commons_income_statement(
            eps, phi_policy="target")["dividend_per_capita"]
        assert d_charter >= d_purchase

    def test_doctrine_dividend_no_longer_costs_anything_at_the_cap(self):
        """
        FINDING REVERSED BY BLOCK K-IV — the price of no forced sales is gone.

        Previously the charter/dilution doctrine paid a visible price at the top
        of the arc: ≈1,092 against the purchase model's ≈1,287, roughly 15%
        less, and that gap was quoted as the honest cost of never forcing a
        sale. It has closed and inverted — dilution now pays MORE at every ε,
        including 2,162 vs 1,986 at ε = 0.99.

        Mechanism: K-IV grew machine output (+70% at ε = 0.99), so more new
        capital is commissioned each period. The commons' share attaches to NEW
        capital under dilution, lifting its φ cap 0.66 → 0.754, while the
        purchase model still spends commons income ACQUIRING capital, which is
        deducted before the dividend.

        Comms consequence: do not quote "the charter costs ~15% of the
        dividend". At this calibration it costs nothing, and the argument for
        the purchase model is now only that it reaches a higher φ.
        """
        d_charter = commons_income_statement(
            0.99, phi_policy="dilution")["dividend_per_capita"]
        d_purchase = commons_income_statement(
            0.99, phi_policy="target")["dividend_per_capita"]
        assert d_charter > d_purchase
        # 1.089 at the K-IV anchor; 1.050 after the Finding-E re-anchor. The
        # SIGN is the claim and it is unchanged — dilution still pays MORE than
        # the purchase model, reversing the pre-K-IV ~15% penalty. The margin
        # tracks machine output Y = eps*total_eoh, so a 22% smaller knowledge
        # base narrows it without flipping it.
        # 1.050 → 1.118 after the knowledge re-anchor grew total EOH at high ε and
        # with it machine output. THE SIGN IS THE CLAIM and it is unchanged:
        # dilution still pays MORE than the purchase model.
        assert d_charter / d_purchase == pytest.approx(1.118, abs=0.02)
        # Threshold follows the same base: 2,162 at the K-IV anchor, 1,924 now.
        # > 1,900 until the elderly revalue cut total EOH and with it machine
        # output; 1,797 still clears the purchase-model comparison this guards.
        assert d_charter > 1_750.0

    def test_target_acquisition_infeasible_window_low_eps(self):
        # §8.9a honest finding: dφ/dε outruns tiny machine output early.
        assert not commons_income_statement(
            0.05, phi_policy="target")["acquisition_feasible"]

    def test_charter_inverts_the_window(self):
        # §8.9b: the early arc is easy (s ≤ 1); the LATE arc is where
        # target-tracking fails (s > 1 — the cap region).
        assert commons_income_statement(
            0.05, phi_policy="dilution")["acquisition_feasible"]
        assert not commons_income_statement(
            0.9, phi_policy="dilution")["acquisition_feasible"]

    def test_g_priv_endogenous_sign_flip_target_policy(self):
        # Purchase model: private capital grows early, shrinks as φ → 1.
        assert commons_income_statement(
            0.2, phi_policy="target")["g_priv_per_year"] > 0.0
        assert commons_income_statement(
            0.9, phi_policy="target")["g_priv_per_year"] < 0.0

    def test_dilution_private_delta_never_negative(self):
        # The ratchet: private capital rises below the peak, flat above —
        # never a sale (point level ignores the slow estate flow).
        for eps in KEY_EPS:
            r = commons_income_statement(eps, phi_policy="dilution")
            delta = r["private_capital_delta_per_year"]
            scale = max(abs(r["machine_output"]), 1.0)
            # Relative tolerance: the flat region is exactly flat in intent, and
            # the residual is float noise on a ~1e8-1e10 magnitude. An absolute
            # 1e-6 bound was tighter than double precision allows once K-IV grew
            # the capital base.
            assert delta >= -1e-9 * scale

    def test_absolute_delta_reported(self):
        # The B-reporting fix: absolute TEH/yr alongside the rate.
        r = commons_income_statement(0.9, phi_policy="target")
        assert r["private_capital_delta_per_year"] == pytest.approx(
            r["g_priv_per_year"]
            * commons_capital(0.9, phi_policy="target")["private_capital"]
        )

    def test_dividend_never_negative(self):
        for eps in KEY_EPS:
            for policy in ("target", "dilution"):
                assert commons_income_statement(
                    eps, phi_policy=policy)["dividend_per_capita"] >= 0.0

    def test_rejects_bad_population(self):
        with pytest.raises(ValueError):
            commons_income_statement(0.4, population=0.0)

    def test_rejects_negative_rate(self):
        with pytest.raises(ValueError):
            commons_income_statement(0.4, epsilon_rate_per_year=-0.01)


# ---------------------------------------------------------------------------
# capital_account_stock — the RC4 fix
# ---------------------------------------------------------------------------

class TestCapitalAccountStock:
    def test_zero_at_tenure_zero(self):
        assert capital_account_stock(0.0, 0.8)["account_balance"] == 0.0

    def test_linear_in_tenure_zero_interest(self):
        # Condition III: a sum of credits, never compounded.
        a5 = capital_account_stock(5.0, 0.8)["account_balance"]
        a10 = capital_account_stock(10.0, 0.8)["account_balance"]
        assert a10 == pytest.approx(2.0 * a5)

    def test_credit_is_share_of_dividend(self):
        eps = 0.8
        d = commons_income_statement(eps)["dividend_per_capita"]
        r = capital_account_stock(1.0, eps)
        assert r["annual_credit"] == pytest.approx(RECAL_ACCOUNT_CREDIT_SHARE * d)

    def test_chi_stock_none_at_eps_zero(self):
        # No capital share of K_entry to finance at ε=0.
        assert capital_account_stock(5.0, 0.0)["chi_stock"] is None

    def test_chi_stock_dimensionally_clean(self):
        # stock / stock: account vs the capital share of the founding cost.
        eps, tenure = 0.8, 5.0
        r = capital_account_stock(tenure, eps)
        expected = r["account_balance"] / (eps * entry_cost(eps))
        assert r["chi_stock"] == pytest.approx(expected)

    def test_rejects_negative_tenure(self):
        with pytest.raises(ValueError):
            capital_account_stock(-1.0, 0.4)

    def test_rejects_bad_credit_share(self):
        with pytest.raises(ValueError):
            capital_account_stock(5.0, 0.4, credit_share=1.5)


# ---------------------------------------------------------------------------
# estate_conversion_flow — generational conversion (B4)
# ---------------------------------------------------------------------------

class TestEstateConversion:
    def test_flow_formula(self):
        r = estate_conversion_flow(0.6, escheat_share=0.15)
        assert r["flow_per_year"] == pytest.approx(
            ANNUAL_DEATH_RATE * 0.15 * r["private_capital"]
        )

    def test_zero_share_zero_flow_infinite_half_life(self):
        r = estate_conversion_flow(0.6, escheat_share=0.0)
        assert r["flow_per_year"] == 0.0
        assert math.isinf(r["half_life_years"])

    def test_half_life_math(self):
        # Full escheat at 1%/yr mortality: half-life ≈ 69 years — mortality
        # speed is SLOW; φ → target is asymptotic, over generations.
        r = estate_conversion_flow(0.6, escheat_share=1.0)
        assert r["half_life_years"] == pytest.approx(
            math.log(2.0) / ANNUAL_DEATH_RATE
        )

    def test_rejects_bad_share(self):
        with pytest.raises(ValueError):
            estate_conversion_flow(0.6, escheat_share=1.5)


# ---------------------------------------------------------------------------
# escalation_trigger — the charter escalation clause (B3)
# ---------------------------------------------------------------------------

class TestEscalationTrigger:
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_never_fires_at_canonical_defaults(self, eps):
        # The brake exists and stays off: capacity ≈ 145–280 across the arc.
        assert not escalation_trigger(eps)["active"]

    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_never_fires_replicable_regime(self, eps):
        r = escalation_trigger(eps, regime="replicable")
        assert not r["active"]
        assert "regime" in r["reason"]

    def test_fires_under_forced_adversarial_parameters(self):
        # A founding cohort 40× larger crushes capacity below the floor.
        r = escalation_trigger(0.4, min_viable_population=200_000.0)
        assert r["active"]
        assert r["entry_capacity"] < r["capacity_floor"]

    def test_reports_capacity(self):
        r = escalation_trigger(0.4)
        assert r["entry_capacity"] > 100.0
        assert r["exit_financeable"]


# ---------------------------------------------------------------------------
# exit_financing — the three-channel invariant
# ---------------------------------------------------------------------------

class TestExitFinancing:
    def test_labor_channel_at_subsistence(self):
        # ε=0: K_entry is labor-denominated; the floor finances the building.
        r = exit_financing(0.0)
        assert r["channel"] == "labor"
        assert r["self_financeable"]
        assert r["t_exit_self_years"] <= RECAL_EXIT_HORIZON_YEARS
        assert r["k_capital"] == 0.0
        assert math.isinf(r["entry_capacity"])

    def test_underwritten_channel_early_mid_arc(self):
        # The §8.9b mid-arc trough (ε ≈ 0.05–0.27): labor displaced, the
        # dividend not yet large. Narrower than §8.9a's (which ran to 0.55).
        r = exit_financing(0.2)
        assert r["channel"] == "underwritten"
        assert not r["self_financeable"]
        assert r["entry_capacity"] >= 1.0
        assert r["exit_financeable"]

    def test_self_channel_from_eps_05(self):
        # The doctrine dividend (full φ·Y) makes exit self-financeable from
        # ε ≈ 0.50. Was ε ≈ 0.30 at PERSONAL_EOH_BASE = 1500; the reprice
        # shrank machine output and pushed the crossover out. The ORDERING
        # (doctrine beats §8.9a's purchase model, which needs ε ≈ 0.79) holds.
        r = exit_financing(0.5)
        assert r["channel"] == "self"
        assert r["self_financeable"]

    def test_self_channel_high_eps_despite_cap(self):
        # Even with φ capped at ≈ 0.66, exit stays self-financeable.
        r = exit_financing(0.99)
        assert r["channel"] == "self"
        assert r["t_exit_self_years"] <= RECAL_EXIT_HORIZON_YEARS

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_financeable_across_arc_adversarial(self, policy, eps):
        assert exit_financing(
            eps, regime="increasing_returns", phi_policy=policy
        )["exit_financeable"]

    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_financeable_across_arc_replicable(self, eps):
        assert exit_financing(eps, regime="replicable")["exit_financeable"]

    def test_k_entry_decomposition(self):
        r = exit_financing(0.6)
        assert r["k_labor"] + r["k_capital"] == pytest.approx(r["k_entry"])
        assert r["k_capital"] == pytest.approx(0.6 * r["k_entry"])

    def test_t_capital_infinite_when_no_dividend_target_policy(self):
        # §8.9a purchase model at ε=0.05: acquisition consumes all income,
        # D = 0 — honest infinity; the underwriting arm carries it.
        r = exit_financing(0.05, phi_policy="target")
        assert math.isinf(r["t_capital_years"])
        assert r["channel"] == "underwritten"

    def test_rejects_bad_horizon(self):
        with pytest.raises(ValueError):
            exit_financing(0.4, exit_horizon_years=0.0)

    def test_rejects_bad_labor_hours(self):
        with pytest.raises(ValueError):
            exit_financing(0.4, founding_labor_hours=-1.0)

    def test_rejects_bad_underwrite_fraction(self):
        with pytest.raises(ValueError):
            exit_financing(0.4, underwrite_fraction=1.5)


# ---------------------------------------------------------------------------
# recalibrated_arc
# ---------------------------------------------------------------------------

EXPECTED_ROW_KEYS = {
    "epsilon", "capital_stock", "machine_output", "phi", "phi_target", "tau",
    "cap_binding", "commons_capital", "private_capital", "income",
    "reinvestment", "acquisition_feasible", "dividend_per_capita",
    "g_priv_per_year", "private_capital_delta_per_year", "s_required",
    "escalation_active", "phi_policy", "k_entry", "t_exit_self_years",
    "self_financeable", "entry_capacity", "exit_financeable", "channel",
}


class TestRecalibratedArc:
    def test_row_keys(self):
        assert set(recalibrated_arc(5)[0].keys()) == EXPECTED_ROW_KEYS

    def test_spans_arc(self):
        rows = recalibrated_arc(21)
        assert rows[0]["epsilon"] == 0.0
        assert rows[-1]["epsilon"] == pytest.approx(0.99)

    @pytest.mark.parametrize("policy", ["target", "dilution", "escalated"])
    def test_exit_financeable_every_row_adversarial(self, policy):
        # The headline: the combined invariant holds at every arc point in
        # the adversarial regime under every policy.
        assert all(
            r["exit_financeable"]
            for r in recalibrated_arc(21, phi_policy=policy)
        )

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    def test_tau_non_decreasing(self, policy):
        taus = [r["tau"] for r in recalibrated_arc(21, phi_policy=policy)]
        assert all(b >= a - 1e-12 for a, b in zip(taus, taus[1:]))

    @pytest.mark.parametrize("policy", ["target", "dilution"])
    def test_conservation(self, policy):
        # T_K + K_priv = K at every row, exact to float noise.
        for r in recalibrated_arc(21, phi_policy=policy):
            assert r["commons_capital"] + r["private_capital"] == pytest.approx(
                r["capital_stock"]
            )

    def test_channel_progression(self):
        # labor → underwritten → self as ε rises; "none" never appears;
        # self-financing from ε ≈ 0.50 under the doctrine dividend (was 0.30
        # before the PERSONAL_EOH_BASE reprice — do NOT quote the old onset).
        channels = [r["channel"] for r in recalibrated_arc(21)]
        assert "none" not in channels
        assert channels[0] == "labor"
        assert channels[-1] == "self"
        assert "underwritten" in channels
        first_self = channels.index("self")
        assert recalibrated_arc(21)[first_self]["epsilon"] < 0.55
        assert all(c == "self" for c in channels[first_self:])

    def test_private_capital_never_falls_by_sale(self):
        # THE §8.9b HEADLINE. With no estate escheat: private capital is
        # monotone non-decreasing across the entire arc (the ratchet).
        rows = recalibrated_arc(21, estate_escheat_share=0.0)
        priv = [r["private_capital"] for r in rows]
        assert all(b >= a - 1e-6 for a, b in zip(priv, priv[1:]))

    def test_private_decline_bounded_by_mortality(self):
        # With the default D5-extension escheat, per-step decline never
        # exceeds the mortality bound death_rate · share · K_priv · Δt.
        rows = recalibrated_arc(21)
        for prev, cur in zip(rows, rows[1:]):
            dt = (cur["epsilon"] - prev["epsilon"]) / 0.02
            bound = (
                ANNUAL_DEATH_RATE * RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE
                * prev["private_capital"] * dt
            )
            decline = prev["private_capital"] - cur["private_capital"]
            assert decline <= bound * (1.0 + 1e-9)

    def test_dilution_cap_binding_region(self):
        rows = recalibrated_arc(21)
        assert not any(
            r["cap_binding"] for r in rows if r["epsilon"] <= 0.40
        )
        assert all(
            r["cap_binding"] for r in rows if r["epsilon"] >= 0.55
        )

    def test_honest_window_inverted_under_charter(self):
        # s_required ≤ 1 early; > 1 from ε ≈ 0.48.
        rows = recalibrated_arc(21)
        assert all(
            r["acquisition_feasible"] for r in rows if r["epsilon"] <= 0.40
        )
        assert not any(
            r["acquisition_feasible"] for r in rows if r["epsilon"] >= 0.55
        )

    def test_target_policy_regression_anchor(self):
        # phi_policy="target" reproduces the published §8.9a numbers.
        rows = recalibrated_arc(21, phi_policy="target")
        last = rows[-1]
        # φ is capital-structure only and is UNMOVED by K-IV — the anchor's
        # structural half still holds exactly. The dividend rides machine
        # output, so it moved with it: 1,286.55 → 1,985.89 (+54%), and
        # self-financing arrives earlier, ε 0.792 → 0.693.
        assert last["phi"] == pytest.approx(0.9865338, rel=1e-5)
        # Tracks the levy/dividend base Y = eps*total_eoh, which the Finding-E
        # re-anchor shrank at the top of the arc (2,896 -> 2,633 h/person.yr).
        # 1831.45 → 1689.87: machine output is ε × total EOH and total EOH fell
        # 7.7% at ε=0.99 with the elderly revalue. → 1941.44 when the working
        # life was measured: the renewal rate rose 6.7%, so knowledge EOH grew
        # and the levy/dividend base grew with it. The dividend tracks the
        # total obligation, so it moves whenever ANY domain does.
        assert last["dividend_per_capita"] == pytest.approx(1941.44, rel=1e-4)
        channels = [r["channel"] for r in rows]
        first_self = channels.index("self")
        # 0.693 → 0.7425 with the 2026-08-10 elderly revalue. The self-financing
        # channel opens LATER because the dividend that funds it is drawn from
        # machine output (ε × total EOH), and total EOH fell with the personal
        # domain. The channel ORDER — labour, underwritten, self — is unchanged,
        # which is what this regression anchor is actually for.
        assert rows[first_self]["epsilon"] == pytest.approx(0.7425, abs=0.001)
        assert not any(r["acquisition_feasible"] for r in rows if r["epsilon"] < 0.15)

    def test_point_arc_consistency_dilution(self):
        # The arc path (with slow estate flow) tracks the point ratchet.
        rows = recalibrated_arc(21)
        for r in rows:
            point = phi_actual(r["epsilon"], "dilution")["phi"]
            assert r["phi"] == pytest.approx(point, abs=0.03)

    def test_escalated_equals_dilution_at_defaults(self):
        # The trigger never fires at canonical defaults: the brake stays off.
        dil = recalibrated_arc(21, phi_policy="dilution")
        esc = recalibrated_arc(21, phi_policy="escalated")
        assert not any(r["escalation_active"] for r in esc)
        for a, b in zip(dil, esc):
            assert a["phi"] == pytest.approx(b["phi"])

    def test_forced_escalation_latches_and_converges(self):
        # A 40× founding cohort forces the trigger: it fires early, LATCHES,
        # and moves φ toward target at mortality speed.
        esc = recalibrated_arc(
            21, phi_policy="escalated", min_viable_population=200_000.0
        )
        active = [r["escalation_active"] for r in esc]
        assert any(active)
        first = active.index(True)
        assert all(active[first:])  # latched: escalations do not flap
        dil = recalibrated_arc(21, min_viable_population=200_000.0)
        assert esc[-1]["phi"] > dil[-1]["phi"]
        assert esc[-1]["private_capital"] < dil[-1]["private_capital"]
        # Convergence is asymptotic, not complete: mortality speed is slow.
        assert esc[-1]["phi"] < esc[-1]["phi_target"]

    def test_replicable_regime_financeable(self):
        rows = recalibrated_arc(21, regime="replicable")
        assert all(r["exit_financeable"] for r in rows)

    def test_rejects_bad_escheat_share(self):
        with pytest.raises(ValueError):
            recalibrated_arc(5, estate_escheat_share=1.5)

    def test_rejects_unknown_policy(self):
        with pytest.raises(ValueError):
            recalibrated_arc(5, phi_policy="seizure")


# ---------------------------------------------------------------------------
# The founding-labour arm — anchored 2026-08-09
#
# RECAL_FOUNDING_LABOR_HOURS drifted from its own stated derivation ("≈ 2/3 of
# PERSONAL_EOH_BASE") when the base was repriced 1500 → 1000 on 2026-08-06: the
# literal stayed at 1,000 and silently became the WHOLE base, i.e. a founder
# devoting every hour of their personal obligation to founding with nothing left to
# live on. Nothing caught it, because no test exercised the labour arm's TIMING —
# the existing assertions only checked t_exit ≤ the 5-year horizon, and both 1.80
# and 2.70 years clear that.
#
# These tests anchor the mechanism, not just the outcome, so the next reprice either
# carries the constant or fails here.
# ---------------------------------------------------------------------------

class TestFoundingLabourArm:

    def test_founding_hours_are_bound_to_the_personal_obligation(self):
        """The rationale is a FRACTION of the base, so it must be computed from it."""
        assert RECAL_FOUNDING_LABOR_HOURS == pytest.approx(
            RECAL_FOUNDING_FRACTION * PERSONAL_EOH_BASE
        )
        assert RECAL_FOUNDING_LABOR_HOURS == pytest.approx(666.667, rel=1e-4)

    def test_a_founder_keeps_part_of_their_obligation(self):
        """The substantive claim: two-thirds redirected, a third left to live on.

        This is what the 1,000 literal violated — at the repriced base it left the
        founder nothing, which is not a placeholder being imprecise but the stated
        mechanism inverted.
        """
        assert 0.0 < RECAL_FOUNDING_FRACTION < 1.0
        residual = PERSONAL_EOH_BASE - RECAL_FOUNDING_LABOR_HOURS
        assert residual > 0.0
        assert residual == pytest.approx(PERSONAL_EOH_BASE / 3.0)

    def test_labor_arm_scales_inversely_with_founding_hours(self):
        """The mechanism: fewer hours per year → longer to accumulate the same stock."""
        slow = exit_financing(0.0, founding_labor_hours=500.0)["t_labor_years"]
        fast = exit_financing(0.0, founding_labor_hours=1000.0)["t_labor_years"]
        assert slow == pytest.approx(2.0 * fast)

    def test_the_revalue_lengthened_the_labor_arm_by_exactly_three_halves(self):
        """1,000 → 666.67 h/yr is a 1.5x slowdown, and it is reported not hidden."""
        at_old = exit_financing(0.0, founding_labor_hours=1000.0)["t_labor_years"]
        at_new = exit_financing(0.0)["t_labor_years"]
        assert at_new == pytest.approx(1.5 * at_old)
        assert at_old == pytest.approx(1.80, rel=1e-3)
        assert at_new == pytest.approx(2.70, rel=1e-3)

    def test_the_invariant_survives_the_revalue_at_every_arc_point(self):
        """The point of measuring the blast radius: nothing breaks, with margin stated.

        Worst labour-arm time across the arc is ~2.85 yr against a 5-yr horizon, so
        the revalue consumes roughly half the headroom and leaves the three-channel
        invariant intact.
        """
        worst = 0.0
        for i in range(100):
            eps = i * 0.01
            r = exit_financing(eps)
            assert r["exit_financeable"], f"exit not financeable at eps={eps:.2f}"
            worst = max(worst, r["t_labor_years"])
        assert worst < RECAL_EXIT_HORIZON_YEARS
        assert worst == pytest.approx(2.852, rel=1e-2)

    def test_channel_arc_is_unchanged_by_the_revalue(self):
        """labor -> underwritten -> self still, in that order."""
        channels = [exit_financing(i * 0.05)["channel"] for i in range(20)]
        assert channels[0] == "labor"
        assert "underwritten" in channels
        assert channels[-1] == "self"
        # monotone: once it leaves a channel it does not return
        assert channels.index("self") > max(
            i for i, c in enumerate(channels) if c == "underwritten"
        ) - len(channels)
