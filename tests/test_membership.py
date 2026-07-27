"""
Tests for hours_eoh/research/membership.py — the §8.7(e) membership-terms audit.

The audit is the constitutional court: it checks proposed MembershipTerms
against the contestability invariant without simulating them.

Arc tests use KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99] per repo convention.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    TRUST_BASE_TEH,
    PERSONAL_EOH_BASE,
    CONTESTABILITY_CHI_CRIT,
    MEMBERSHIP_MIN_HOURS_WARN_FRACTION,
    MEMBERSHIP_MIN_HOURS_CRIT_FRACTION,
)
from hours_eoh.research.contestability import entry_cost
from hours_eoh.research.membership import MembershipTerms, contestability_audit

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]
_POP = 1_000_000.0
_TRUST = TRUST_BASE_TEH
_COMMONS = 1e9  # non-empty commons so benign terms are not WARNed for backing


class TestContestabilityAudit:

    def test_benign_terms_pass_ok_at_low_eps(self):
        """Canonical terms at ε=0 with a backed floor: no warnings at all."""
        result = contestability_audit({}, 0.0, commons_balance=_COMMONS)
        assert result["audit_status"] == "OK"
        assert result["passes"] is True
        assert result["warnings"] == []

    def test_admission_cost_enters_k_entry(self):
        admission = 500.0
        result = contestability_audit(
            {"admission_cost_teh": admission}, 0.40, commons_balance=_COMMONS)
        assert result["k_entry_effective"] == pytest.approx(
            entry_cost(0.40) + admission)

    def test_high_admission_crit_at_high_eps(self):
        """Adversarial arc position: an admission fee that might be tolerable
        at subsistence breaches the invariant near post-scarcity."""
        result = contestability_audit(
            {"admission_cost_teh": 800.0}, 0.90, commons_balance=_COMMONS)
        assert result["chi_marginal"] < CONTESTABILITY_CHI_CRIT
        assert result["audit_status"] == "CRIT"
        assert result["passes"] is False

    def test_long_vesting_warns(self):
        result = contestability_audit(
            {"vesting_years": 12.0}, 0.0, commons_balance=_COMMONS)
        assert result["audit_status"] == "WARN"
        assert any("vesting_years" in w for w in result["warnings"])

    def test_exit_notice_warn_then_crit(self):
        warn = contestability_audit(
            {"exit_notice_years": 1.5}, 0.0, commons_balance=_COMMONS)
        assert warn["audit_status"] == "WARN"
        crit = contestability_audit(
            {"exit_notice_years": 4.0}, 0.0, commons_balance=_COMMONS)
        assert crit["audit_status"] == "CRIT"
        assert crit["passes"] is False

    def test_minimum_hours_warn_then_crit(self):
        warn_hours = MEMBERSHIP_MIN_HOURS_WARN_FRACTION * PERSONAL_EOH_BASE + 50.0
        warn = contestability_audit(
            {"minimum_hours_annual": warn_hours}, 0.0, commons_balance=_COMMONS)
        assert warn["audit_status"] == "WARN"
        crit_hours = MEMBERSHIP_MIN_HOURS_CRIT_FRACTION * PERSONAL_EOH_BASE
        crit = contestability_audit(
            {"minimum_hours_annual": crit_hours}, 0.0, commons_balance=_COMMONS)
        assert crit["audit_status"] == "CRIT"
        assert any("compulsion" in w for w in crit["warnings"])

    def test_dividend_retention_warns(self):
        result = contestability_audit(
            {"dividend_policy_fraction": 0.10}, 0.0, commons_balance=_COMMONS)
        assert result["audit_status"] == "WARN"
        assert any("honeypot" in w for w in result["warnings"])
        # Retention also scales the vested member's χ down.
        full = contestability_audit({}, 0.0, commons_balance=_COMMONS)
        assert result["chi_vested"] < full["chi_vested"]

    def test_empty_commons_warns(self):
        result = contestability_audit({}, 0.0, commons_balance=0.0)
        assert result["audit_status"] == "WARN"
        assert any("commons" in w for w in result["warnings"])

    def test_nonempty_commons_reports_coverage_without_warning(self):
        result = contestability_audit({}, 0.0, commons_balance=_COMMONS)
        assert result["commons_floor_coverage"] > 0.0
        assert not any("commons" in w for w in result["warnings"])

    def test_invalid_inputs_raise(self):
        with pytest.raises(ValueError, match="vesting_years"):
            contestability_audit({"vesting_years": 0.0}, 0.40)
        with pytest.raises(ValueError, match="admission_cost_teh"):
            contestability_audit({"admission_cost_teh": -1.0}, 0.40)
        with pytest.raises(ValueError, match="exit_notice_years"):
            contestability_audit({"exit_notice_years": -0.5}, 0.40)
        with pytest.raises(ValueError, match="minimum_hours_annual"):
            contestability_audit({"minimum_hours_annual": -10.0}, 0.40)
        with pytest.raises(ValueError, match="dividend_policy_fraction"):
            contestability_audit({"dividend_policy_fraction": 1.5}, 0.40)
        with pytest.raises(ValueError, match="epsilon"):
            contestability_audit({}, 1.5)

    def test_worst_severity_wins(self):
        """One CRIT among several WARNs → CRIT overall."""
        terms: MembershipTerms = {
            "vesting_years": 12.0,          # WARN
            "dividend_policy_fraction": 0.1,  # WARN
            "exit_notice_years": 4.0,       # CRIT
        }
        result = contestability_audit(terms, 0.0, commons_balance=_COMMONS)
        assert result["audit_status"] == "CRIT"
        assert len(result["warnings"]) >= 3

    def test_audit_at_key_epsilons(self):
        """Arc smoke: finite χ, valid statuses, monotone worsening of the
        marginal χ across the adversarial arc for identical terms."""
        chis = []
        for eps in KEY_EPSILONS:
            result = contestability_audit(
                {"admission_cost_teh": 200.0}, eps, commons_balance=_COMMONS)
            assert result["chi_marginal"] > 0.0
            assert result["audit_status"] in ("OK", "WARN", "CRIT")
            chis.append(result["chi_marginal"])
        assert chis == sorted(chis, reverse=True), (
            "identical terms should audit monotonically worse across the "
            f"increasing-returns arc, got {chis}")

    def test_terms_echoed_in_output(self):
        terms: MembershipTerms = {"admission_cost_teh": 250.0}
        result = contestability_audit(terms, 0.40, commons_balance=_COMMONS)
        echoed = result["terms"]
        assert echoed["admission_cost_teh"] == 250.0
        # Absent fields echoed at their canonical defaults.
        assert echoed["dividend_policy_fraction"] == 1.0
        assert echoed["exit_notice_years"] == 0.0


# ---------------------------------------------------------------------------
# §8.8 closure flags: commons dividend (M1) and underwriting policy (M2)
# ---------------------------------------------------------------------------

class TestAuditClosureFlags:

    def test_defaults_unchanged_with_commons_present(self):
        """Without the flags, a funded commons changes no §8.7e escalation."""
        old = contestability_audit(
            {"admission_cost_teh": 800.0}, 0.90, commons_balance=1e10)
        assert old["audit_status"] == "CRIT"
        assert old["passes"] is False
        # New keys are informational only.
        assert old["entry_capacity"] > 1.0
        assert old["exit_financeable"] is True

    def test_commons_dividend_raises_marginal_p(self):
        base = contestability_audit({}, 0.90, commons_balance=1e10)
        with_div = contestability_audit(
            {}, 0.90, commons_balance=1e10, commons_dividend=True)
        assert with_div["dividend_commons"] > 0.0
        assert with_div["p_marginal"] > base["p_marginal"]
        assert with_div["chi_marginal"] > base["chi_marginal"]

    def test_underwriting_policy_waives_crit_to_warn(self):
        result = contestability_audit(
            {"admission_cost_teh": 800.0}, 0.90, commons_balance=1e10,
            underwriting_policy=True)
        assert result["audit_status"] == "WARN"
        assert result["passes"] is True
        assert any("commons-financed" in w for w in result["warnings"])

    def test_underwriting_policy_cannot_waive_empty_commons(self):
        result = contestability_audit(
            {"admission_cost_teh": 800.0}, 0.90, commons_balance=0.0,
            underwriting_policy=True)
        assert result["audit_status"] == "CRIT"
        assert result["passes"] is False

    def test_admission_cost_shrinks_entry_capacity(self):
        """Capacity is computed against k_eff: terms that inflate admission
        shrink the number of foundings the commons can finance."""
        cheap = contestability_audit({}, 0.40, commons_balance=1e9)
        dear = contestability_audit(
            {"admission_cost_teh": 2_000.0}, 0.40, commons_balance=1e9)
        assert dear["entry_capacity"] < cheap["entry_capacity"]

    def test_closure_flags_at_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = contestability_audit(
                {}, eps, commons_balance=1e10,
                commons_dividend=True, underwriting_policy=True)
            assert result["passes"] is True, (
                f"funded commons + closure flags must keep terms passable "
                f"at ε={eps}")
