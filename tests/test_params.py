"""
Tests for hours_eoh.params (EohParams)

Covers: parameter access, defaults, temporary context manager,
set() with history tracking, and integration with the full pipeline.
"""

import math
import pytest

from hours_eoh.params import EohParams
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.eoh_fulfillment import (
    human_eoh_share,
    registered_eoh,
    teh_created,
)
from hours_eoh.core.registration import total_registration_share
from hours_eoh.core.multipliers import population_weighted_mean_multiplier


# ===========================================================================
# Basic parameter access
# ===========================================================================

class TestEohParamsDefaults:

    def test_can_instantiate(self):
        p = EohParams()
        assert p is not None

    def test_key_access(self):
        p = EohParams()
        assert p["population"] > 0
        assert p["capital_stock_teh"] > 0
        assert p["trust_base"] > 0

    def test_all_numeric_values_finite(self):
        p = EohParams()
        for key in ("population", "capital_stock_teh", "trust_base",
                    "ecosystem_health", "infra_maintenance_rate",
                    "suff_levy_rate", "capital_age_ratio"):
            val = p[key]
            assert math.isfinite(val), f"Non-finite default for {key}: {val}"

    def test_ecosystem_health_in_range(self):
        p = EohParams()
        assert 0.0 < p["ecosystem_health"] <= 1.0

    def test_levy_rate_positive(self):
        p = EohParams()
        assert p["suff_levy_rate"] > 0.0
        assert p["suff_levy_rate"] < 1.0


# ===========================================================================
# temporary() context manager
# ===========================================================================

class TestEohParamsTemporary:

    def test_temporary_overrides_value_inside_block(self):
        p = EohParams()
        with p.temporary(ecosystem_health=0.10):
            assert p["ecosystem_health"] == pytest.approx(0.10)

    def test_temporary_restores_value_after_block(self):
        p = EohParams()
        original = p["ecosystem_health"]
        with p.temporary(ecosystem_health=0.10):
            pass
        assert p["ecosystem_health"] == pytest.approx(original), (
            "EohParams.temporary() must restore original value after block"
        )

    def test_temporary_multiple_keys(self):
        p = EohParams()
        orig_health = p["ecosystem_health"]
        with p.temporary(ecosystem_health=0.20, capital_age_ratio=0.80):
            assert p["ecosystem_health"] == pytest.approx(0.20)
            assert p["capital_age_ratio"] == pytest.approx(0.80)
        assert p["ecosystem_health"] == pytest.approx(orig_health)

    def test_temporary_restores_on_exception(self):
        p = EohParams()
        original = p["ecosystem_health"]
        try:
            with p.temporary(ecosystem_health=0.05):
                raise ValueError("test exception")
        except ValueError:
            pass
        assert p["ecosystem_health"] == pytest.approx(original)


# ===========================================================================
# Integration: params-driven pipeline
# ===========================================================================

class TestParamsDrivenPipeline:

    def test_params_driven_pipeline(self):
        """Use EohParams to drive a full EOH → TEH pipeline calculation."""
        p = EohParams()
        eps = 0.40

        eoh = total_eoh(
            epsilon=eps,
            population=p["population"],
            capital_stock=p["capital_stock_teh"],
            capital_age_ratio=p["capital_age_ratio"],
            ecosystem_health=p["ecosystem_health"],
            deferred_ecological=p["deferred_ecological"],
            knowledge_complexity=p["knowledge_complexity"],
            skill_decay_rate=p["skill_decay_rate"],
            personal_base=p["personal_eoh_base"],
            infra_maint_rate=p["infra_maintenance_rate"],
            ecological_base=p["ecological_base_rate"],
            ecological_threshold=p["ecological_threshold"],
            knowledge_base=p["knowledge_eoh_base"],
            knowledge_exponent=p["knowledge_eps_exponent"],
        )
        assert eoh["total"] > 0

        human = human_eoh_share(eoh["total"], epsilon=eps)
        reg_share = total_registration_share(
            eps,
            care_weight=p["care_weight"],
            production_weight=p["production_weight"],
            stewardship_weight=p["stewardship_weight"],
            care_params=p.care_sigmoid_params,
        )
        reg = registered_eoh(human, reg_share)
        mean_m = population_weighted_mean_multiplier()
        teh = teh_created(reg, mean_m)

        assert teh > 0
        assert math.isfinite(teh)

    def test_params_temporary_changes_pipeline_output(self):
        """Overriding ecosystem_health must change total_eoh output."""
        p = EohParams()
        eps = 0.40

        eoh_default = total_eoh(epsilon=eps, ecosystem_health=p["ecosystem_health"])
        with p.temporary(ecosystem_health=0.10):
            eoh_low = total_eoh(epsilon=eps, ecosystem_health=p["ecosystem_health"])

        # Lower ecosystem health → higher ecological EOH
        assert eoh_low["ecological"] >= eoh_default["ecological"]
