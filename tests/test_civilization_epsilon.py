"""
Tests for civilization.py — endogenous ε derivation from physical capital state.

Covers:
  - machine_eoh_from_capital(): capital shorthand resolution and EOH aggregation
  - civilization_epsilon(): full pipeline producing ε + breakdown

Key invariants:
  - ε ∈ [0, 1] always
  - More / better capital → higher ε (monotonicity)
  - Tier shorthand, explicit spec, and mixed forms produce consistent results
  - machine_eoh_total ≤ gross total_eoh (ε ≤ 1 is enforced by compute_epsilon)
  - No capital → ε = 0
  - All breakdown dicts have expected keys
"""

from __future__ import annotations

import pytest

from hours_eoh.core.civilization import (
    civilization_epsilon,
    machine_eoh_from_capital,
    _resolve_capital_entry,
)
from hours_eoh.data import CAPITAL_MACHINE_PROFILES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

POPULATION = 1_000_000


def _full_stack(tier: str) -> dict:
    """All capital types at the given tier."""
    return {t: tier for t in CAPITAL_MACHINE_PROFILES}


# ---------------------------------------------------------------------------
# _resolve_capital_entry
# ---------------------------------------------------------------------------

class TestResolveCapitalEntry:
    def test_tier_string_resolves_teh_from_per_capita(self):
        r = _resolve_capital_entry("power_grid", "standard", POPULATION)
        profile = CAPITAL_MACHINE_PROFILES["power_grid"]
        expected_teh = profile["tiers"]["standard"]["teh_per_capita"] * POPULATION
        assert r["teh_value"] == pytest.approx(expected_teh)

    def test_tier_string_uses_default_age_and_condition(self):
        r = _resolve_capital_entry("medical_systems", "basic", POPULATION)
        td = CAPITAL_MACHINE_PROFILES["medical_systems"]["tiers"]["basic"]
        assert r["age"] == pytest.approx(td["default_age"])
        assert r["condition"] == pytest.approx(td["default_condition"])

    def test_explicit_teh_value(self):
        r = _resolve_capital_entry("power_grid", {"teh_value": 5e8, "age": 20}, POPULATION)
        assert r["teh_value"] == pytest.approx(5e8)

    def test_explicit_derives_condition_from_age_when_absent(self):
        design_life = CAPITAL_MACHINE_PROFILES["power_grid"]["design_life"]  # 40
        r = _resolve_capital_entry("power_grid", {"teh_value": 5e8, "age": 20}, POPULATION)
        # age_fraction = 20/40 = 0.5 → condition = 1 - 0.7*0.5 = 0.65
        assert r["condition"] == pytest.approx(0.65)

    def test_explicit_condition_overrides_derivation(self):
        r = _resolve_capital_entry("power_grid", {"teh_value": 5e8, "age": 20, "condition": 0.90}, POPULATION)
        assert r["condition"] == pytest.approx(0.90)

    def test_tier_with_age_override(self):
        r = _resolve_capital_entry("power_grid", {"tier": "standard", "age": 30}, POPULATION)
        assert r["age"] == pytest.approx(30)
        # teh_value still from tier
        expected_teh = CAPITAL_MACHINE_PROFILES["power_grid"]["tiers"]["standard"]["teh_per_capita"] * POPULATION
        assert r["teh_value"] == pytest.approx(expected_teh)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown capital type"):
            _resolve_capital_entry("flux_capacitor", "standard", POPULATION)

    def test_unknown_tier_raises(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            _resolve_capital_entry("power_grid", "ultra", POPULATION)

    def test_explicit_without_teh_raises(self):
        with pytest.raises(ValueError, match="teh_value"):
            _resolve_capital_entry("power_grid", {"age": 10}, POPULATION)

    def test_condition_clamped_to_unit_interval(self):
        r = _resolve_capital_entry("power_grid", {"teh_value": 1e8, "condition": 1.5}, POPULATION)
        assert r["condition"] <= 1.0

    def test_condition_floor_at_end_of_design_life(self):
        design_life = CAPITAL_MACHINE_PROFILES["building"]["design_life"]
        r = _resolve_capital_entry("building", {"teh_value": 1e8, "age": design_life * 2}, POPULATION)
        assert r["condition"] >= 0.30  # floor


# ---------------------------------------------------------------------------
# machine_eoh_from_capital
# ---------------------------------------------------------------------------

class TestMachineEohFromCapital:
    def test_empty_capital_returns_zeros(self):
        result = machine_eoh_from_capital({}, POPULATION)
        assert result["machine_eoh_total"] == 0.0
        assert result["capital_stock_teh"] == 0.0
        assert result["annual_eoh_eliminated"] == 0.0
        assert result["annual_personal_eoh_fulfilled"] == 0.0

    def test_single_type_explicit(self):
        result = machine_eoh_from_capital(
            {"power_grid": {"teh_value": 1e9, "condition": 1.0, "age": 0}},
            POPULATION,
        )
        p = CAPITAL_MACHINE_PROFILES["power_grid"]
        expected_elim    = 1e9 * 1.0 * p["eoh_elimination_rate"]
        expected_personal = 1e9 * 1.0 * p["personal_fulfillment_rate"]
        assert result["annual_eoh_eliminated"]        == pytest.approx(expected_elim)
        assert result["annual_personal_eoh_fulfilled"] == pytest.approx(expected_personal)
        assert result["machine_eoh_total"] == pytest.approx(expected_elim + expected_personal)

    def test_condition_scales_output(self):
        full = machine_eoh_from_capital(
            {"medical_systems": {"teh_value": 5e8, "condition": 1.0, "age": 0}}, POPULATION
        )
        half = machine_eoh_from_capital(
            {"medical_systems": {"teh_value": 5e8, "condition": 0.5, "age": 0}}, POPULATION
        )
        assert half["machine_eoh_total"] == pytest.approx(full["machine_eoh_total"] * 0.5)

    def test_multiple_types_sum_correctly(self):
        result = machine_eoh_from_capital(
            {
                "power_grid":      {"teh_value": 1e9, "condition": 0.9, "age": 0},
                "medical_systems": {"teh_value": 5e8, "condition": 0.8, "age": 0},
            },
            POPULATION,
        )
        pg = CAPITAL_MACHINE_PROFILES["power_grid"]
        ms = CAPITAL_MACHINE_PROFILES["medical_systems"]
        expected = (
            1e9 * 0.9 * (pg["eoh_elimination_rate"] + pg["personal_fulfillment_rate"])
            + 5e8 * 0.8 * (ms["eoh_elimination_rate"] + ms["personal_fulfillment_rate"])
        )
        assert result["machine_eoh_total"] == pytest.approx(expected)

    def test_tier_shorthand_scales_with_population(self):
        pop_small = 500_000
        pop_large = 2_000_000
        r_small = machine_eoh_from_capital({"power_grid": "standard"}, pop_small)
        r_large = machine_eoh_from_capital({"power_grid": "standard"}, pop_large)
        # teh_value is 4× larger → EOH is 4× larger
        assert r_large["capital_stock_teh"] == pytest.approx(r_small["capital_stock_teh"] * 4.0)
        assert r_large["machine_eoh_total"] == pytest.approx(r_small["machine_eoh_total"] * 4.0)

    def test_capital_age_ratio_weighted_correctly(self):
        # Single type, known age/design_life
        result = machine_eoh_from_capital(
            {"power_grid": {"teh_value": 1e9, "age": 20, "condition": 0.85}},
            POPULATION,
        )
        dl = CAPITAL_MACHINE_PROFILES["power_grid"]["design_life"]  # 40
        assert result["capital_age_ratio"] == pytest.approx(20 / dl)

    def test_by_type_breakdown_present(self):
        result = machine_eoh_from_capital(
            {"power_grid": "standard", "computing_ai": "advanced"},
            POPULATION,
        )
        assert "power_grid"   in result["by_type"]
        assert "computing_ai" in result["by_type"]
        entry = result["by_type"]["power_grid"]
        assert "eoh_eliminated"     in entry
        assert "personal_fulfilled" in entry
        assert "combined_eoh"       in entry


# ---------------------------------------------------------------------------
# civilization_epsilon — core invariants
# ---------------------------------------------------------------------------

class TestCivilizationEpsilonInvariants:
    def test_no_capital_gives_zero_epsilon(self):
        result = civilization_epsilon({"population": POPULATION})
        assert result["epsilon"] == pytest.approx(0.0)

    def test_epsilon_in_unit_interval(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": _full_stack("standard"),
        })
        assert 0.0 <= result["epsilon"] <= 1.0

    def test_more_capital_gives_higher_epsilon(self):
        r_basic    = civilization_epsilon({"population": POPULATION, "capital": _full_stack("basic")})
        r_standard = civilization_epsilon({"population": POPULATION, "capital": _full_stack("standard")})
        r_advanced = civilization_epsilon({"population": POPULATION, "capital": _full_stack("advanced")})
        assert r_basic["epsilon"] < r_standard["epsilon"] < r_advanced["epsilon"]

    def test_standard_stack_epsilon_in_expected_range(self):
        # Standard full stack should give ε ≈ 0.15–0.30 (mid-development baseline)
        result = civilization_epsilon({"population": POPULATION, "capital": _full_stack("standard")})
        assert 0.10 <= result["epsilon"] <= 0.35

    def test_advanced_stack_epsilon_above_standard(self):
        r = civilization_epsilon({"population": POPULATION, "capital": _full_stack("advanced")})
        assert r["epsilon"] > 0.30

    def test_machine_eoh_le_gross_total(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": _full_stack("advanced"),
        })
        gross_total = result["eoh_gross"]["total"]
        machine_total = result["machine_eoh"]["total"]
        assert machine_total <= gross_total * 1.001  # tolerance for float


# ---------------------------------------------------------------------------
# civilization_epsilon — result structure
# ---------------------------------------------------------------------------

class TestCivilizationEpsilonStructure:
    def test_required_top_level_keys(self):
        result = civilization_epsilon({"capital": {"power_grid": "standard"}})
        for key in ("epsilon", "physical_state", "eoh_gross", "machine_eoh",
                    "pipeline", "fiscal", "workforce", "warnings"):
            assert key in result, f"Missing key: {key}"

    def test_machine_eoh_keys(self):
        result = civilization_epsilon({"capital": {"power_grid": "standard"}})
        m = result["machine_eoh"]
        assert "total" in m
        assert "system_eliminated" in m
        assert "personal_fulfilled" in m
        assert "by_type" in m

    def test_pipeline_keys(self):
        result = civilization_epsilon({"capital": {"power_grid": "standard"}})
        pipe = result["pipeline"]
        assert "teh_created" in pipe
        assert "total_eoh" in pipe
        assert "epsilon" in pipe

    def test_eoh_gross_domains(self):
        result = civilization_epsilon({"capital": {"power_grid": "standard"}})
        for domain in ("personal", "infrastructure", "ecological", "knowledge", "total"):
            assert domain in result["eoh_gross"]

    def test_warnings_list(self):
        result = civilization_epsilon({})
        assert isinstance(result["warnings"], list)
        assert len(result["warnings"]) > 0  # no capital warning expected

    def test_no_warning_for_normal_capital(self):
        result = civilization_epsilon({"capital": _full_stack("standard")})
        assert all("post-scarcity" not in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# civilization_epsilon — physical state handling
# ---------------------------------------------------------------------------

class TestCivilizationEpsilonPhysicalState:
    def test_population_scales_eoh(self):
        r1 = civilization_epsilon({"population": 1_000_000, "capital": {}})
        r2 = civilization_epsilon({"population": 2_000_000, "capital": {}})
        # personal EOH scales linearly with population
        assert r2["eoh_gross"]["personal"] == pytest.approx(
            r1["eoh_gross"]["personal"] * 2.0, rel=0.01
        )

    def test_degraded_ecosystem_increases_eco_eoh(self):
        r_healthy  = civilization_epsilon({"ecosystem_health": 0.90, "capital": {}})
        r_degraded = civilization_epsilon({"ecosystem_health": 0.30, "capital": {}})
        assert r_degraded["eoh_gross"]["ecological"] > r_healthy["eoh_gross"]["ecological"]

    def test_degraded_capital_gives_lower_epsilon(self):
        r_good = civilization_epsilon({
            "population": POPULATION,
            "capital": {"power_grid": {"teh_value": 1e9, "condition": 1.0, "age": 0}},
        })
        r_worn = civilization_epsilon({
            "population": POPULATION,
            "capital": {"power_grid": {"teh_value": 1e9, "condition": 0.4, "age": 0}},
        })
        assert r_worn["epsilon"] < r_good["epsilon"]

    def test_monitoring_capability_from_env_monitoring(self):
        # With environmental_monitoring capital, monitoring_capability exceeds base
        r_no_env = civilization_epsilon({
            "population": POPULATION,
            "capital": {"power_grid": "standard"},
        })
        r_env = civilization_epsilon({
            "population": POPULATION,
            "capital": {
                "power_grid": "standard",
                "environmental_monitoring": "advanced",
            },
        })
        assert (
            r_env["physical_state"]["monitoring_capability"]
            > r_no_env["physical_state"]["monitoring_capability"]
        )

    def test_explicit_monitoring_override(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": {},
            "monitoring_capability": 0.75,
        })
        assert result["physical_state"]["monitoring_capability"] == pytest.approx(0.75)

    def test_pipeline_epsilon_matches_derived(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": _full_stack("standard"),
        })
        assert result["pipeline"]["epsilon"] == pytest.approx(result["epsilon"])


# ---------------------------------------------------------------------------
# civilization_epsilon — mixed and edge inputs
# ---------------------------------------------------------------------------

class TestCivilizationEpsilonMixedInputs:
    def test_mixed_tier_and_explicit(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": {
                "power_grid":      "standard",   # tier shorthand
                "medical_systems": {"teh_value": 3e8, "age": 10, "condition": 0.80},  # explicit
                "computing_ai":    {"tier": "advanced", "age": 3},  # tier + override
            },
        })
        assert 0.0 < result["epsilon"] < 1.0
        assert "power_grid"      in result["machine_eoh"]["by_type"]
        assert "medical_systems" in result["machine_eoh"]["by_type"]
        assert "computing_ai"    in result["machine_eoh"]["by_type"]

    def test_all_tiers_valid_for_each_type(self):
        for type_name in CAPITAL_MACHINE_PROFILES:
            for tier in CAPITAL_MACHINE_PROFILES[type_name].get("tiers", {}):
                result = machine_eoh_from_capital({type_name: tier}, POPULATION)
                assert result["machine_eoh_total"] >= 0.0, (
                    f"{type_name}:{tier} produced negative machine_eoh"
                )

    def test_high_capital_capped_at_one(self):
        # Extreme over-specification should not produce ε > 1
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": {t: {"teh_value": 1e15, "condition": 1.0, "age": 0}
                        for t in CAPITAL_MACHINE_PROFILES},
        })
        assert result["epsilon"] <= 1.0

    def test_fiscal_solvency_present(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": _full_stack("standard"),
        })
        assert "solvent" in result["fiscal"]

    def test_workforce_workers_needed_positive(self):
        result = civilization_epsilon({
            "population": POPULATION,
            "capital": _full_stack("standard"),
        })
        assert result["workforce"]["total_workers_needed"] > 0
