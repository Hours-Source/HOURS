"""
Tests for hours_eoh.reference — reference data package.

Validates that all practitioner histories and workforce snapshots are
well-formed, compatible with their respective consumers, and structurally
isolated (no imports from the domain package).
"""

import importlib
import inspect
import sys

import pytest

from hours_eoh.reference.practitioners import (
    PRACTITIONER_HISTORIES,
    SEVERE_SCARCITY_EXAMPLE,
    RECOVERING_EXAMPLE,
    STABLE_EXAMPLE,
)
from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS
from hours_eoh.core.multipliers import scarcity_score, population_weighted_mean_multiplier
from hours_eoh.data import M_BAND_LOW, M_BAND_HIGH


# ---------------------------------------------------------------------------
# Practitioner histories
# ---------------------------------------------------------------------------

class TestPractitionerHistories:

    def test_all_occupations_present(self):
        expected = {
            "community_care_worker", "ecological_steward", "civil_engineer",
            "neurosurgeon", "general_educator", "restoration_ecologist",
        }
        assert set(PRACTITIONER_HISTORIES.keys()) == expected

    def test_histories_have_minimum_length(self):
        for occ, history in PRACTITIONER_HISTORIES.items():
            assert len(history) >= 3, (
                f"{occ}: history must have >= 3 entries for rolling window, got {len(history)}"
            )

    def test_all_practitioners_non_negative(self):
        for occ, history in PRACTITIONER_HISTORIES.items():
            for t, (p, d) in enumerate(history):
                assert p >= 0, f"{occ} period {t}: practitioner_count={p} must be >= 0"

    def test_all_demand_positive(self):
        for occ, history in PRACTITIONER_HISTORIES.items():
            for t, (p, d) in enumerate(history):
                assert d > 0, f"{occ} period {t}: demand_eoh={d} must be > 0"

    def test_histories_pass_scarcity_score(self):
        for occ, history in PRACTITIONER_HISTORIES.items():
            result = scarcity_score(history)
            assert 0.0 <= result["scarcity"] <= 1.0, (
                f"{occ}: scarcity={result['scarcity']} out of [0, 1]"
            )

    def test_neurosurgeon_severe_scarcity(self):
        result = scarcity_score(PRACTITIONER_HISTORIES["neurosurgeon"])
        assert result["status"] == "SEVERE_SCARCITY", (
            f"neurosurgeon should trigger SEVERE_SCARCITY, got {result['status']}"
        )

    def test_general_educator_zero_scarcity(self):
        result = scarcity_score(PRACTITIONER_HISTORIES["general_educator"])
        assert result["scarcity"] == pytest.approx(0.0), (
            f"general_educator oversupply should give scarcity=0, got {result['scarcity']}"
        )

    def test_ecological_steward_rising_trend(self):
        # Rolling window average should be higher than the earliest period's raw scarcity
        history = PRACTITIONER_HISTORIES["ecological_steward"]
        earliest_p, earliest_d = history[0]
        earliest_raw = max(0.0, 1.0 - earliest_p / earliest_d)
        result = scarcity_score(history)
        assert result["scarcity"] > earliest_raw, (
            "Rising scarcity history: current scarcity should exceed earliest raw value"
        )

    def test_civil_engineer_recovering(self):
        # Most recent entry should have lower raw scarcity than earliest
        history = PRACTITIONER_HISTORIES["civil_engineer"]
        first_p, first_d = history[0]
        last_p, last_d = history[-1]
        first_raw = max(0.0, 1.0 - first_p / first_d)
        last_raw = max(0.0, 1.0 - last_p / last_d)
        assert last_raw < first_raw, (
            "Recovering history: most-recent raw scarcity should be lower than earliest"
        )

    def test_civil_engineer_supply_discount_reduces_scarcity(self):
        # With elasticity > 0, scarcity should be lower than without
        history = PRACTITIONER_HISTORIES["civil_engineer"]
        no_discount = scarcity_score(history, supply_elasticity=0.0)
        with_discount = scarcity_score(history, supply_elasticity=0.15)
        assert with_discount["scarcity"] <= no_discount["scarcity"]

    def test_convenience_aliases_match(self):
        assert SEVERE_SCARCITY_EXAMPLE is PRACTITIONER_HISTORIES["neurosurgeon"]
        assert RECOVERING_EXAMPLE is PRACTITIONER_HISTORIES["civil_engineer"]
        assert STABLE_EXAMPLE is PRACTITIONER_HISTORIES["community_care_worker"]


# ---------------------------------------------------------------------------
# Workforce snapshots
# ---------------------------------------------------------------------------

class TestWorkforceSnapshots:

    def test_all_snapshots_present(self):
        expected = {"reference", "below_band", "above_band", "high_epsilon", "low_epsilon"}
        assert set(WORKFORCE_SNAPSHOTS.keys()) == expected

    def test_fractions_sum_to_one(self):
        for name, segs in WORKFORCE_SNAPSHOTS.items():
            total = sum(s["fraction"] for s in segs)
            assert abs(total - 1.0) < 1e-6, (
                f"WORKFORCE_SNAPSHOTS['{name}'] fractions sum to {total:.8f}"
            )

    def test_all_fractions_positive(self):
        for name, segs in WORKFORCE_SNAPSHOTS.items():
            for seg in segs:
                assert seg["fraction"] > 0, (
                    f"{name}/{seg['name']}: fraction={seg['fraction']} must be > 0"
                )

    def test_all_multipliers_positive(self):
        for name, segs in WORKFORCE_SNAPSHOTS.items():
            for seg in segs:
                assert seg["mean_mu"] >= 1.0, (
                    f"{name}/{seg['name']}: mean_mu={seg['mean_mu']} must be >= 1.0"
                )

    def test_snapshots_pass_mean_multiplier(self):
        for name, segs in WORKFORCE_SNAPSHOTS.items():
            m = population_weighted_mean_multiplier(segs)
            assert m > 0, f"{name}: mean_multiplier={m} should be > 0"

    def test_reference_m_near_1_98(self):
        m = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["reference"])
        assert abs(m - 1.98) < 0.05, f"reference M={m:.4f} should be ≈ 1.98"

    def test_below_band_m_below_floor(self):
        m = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["below_band"])
        assert m < M_BAND_LOW, f"below_band M={m:.4f} should be < {M_BAND_LOW}"

    def test_above_band_m_above_ceiling(self):
        m = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["above_band"])
        assert m > M_BAND_HIGH, f"above_band M={m:.4f} should be > {M_BAND_HIGH}"

    def test_high_epsilon_m_above_reference(self):
        m_ref = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["reference"])
        m_hi = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["high_epsilon"])
        assert m_hi > m_ref, "high_epsilon M should exceed reference M"

    def test_low_epsilon_m_below_reference(self):
        m_ref = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["reference"])
        m_lo = population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS["low_epsilon"])
        assert m_lo < m_ref, "low_epsilon M should be below reference M"


# ---------------------------------------------------------------------------
# Layer isolation — reference modules must not import from hours_eoh domain
# ---------------------------------------------------------------------------

#: Every module in `reference/`. New reference modules go here, not into a
#: private copy of this check in their own test file.
REFERENCE_MODULES = [
    "hours_eoh.reference.practitioners",
    "hours_eoh.reference.workforce",
    "hours_eoh.reference.onet_knowledge",
    "hours_eoh.reference.onet_multipliers",
    "hours_eoh.reference.atus_time_use",
    "hours_eoh.reference.mtus_time_use",
    "hours_eoh.reference.care_demand",
    "hours_eoh.reference.land_stewardship",
    "hours_eoh.reference.personal_basket",
    "hours_eoh.reference.servicing",
    "hours_eoh.reference.restoration",
    "hours_eoh.reference.parcels",
]


def test_every_reference_module_is_on_the_isolation_list():
    """The list above is hand-maintained, so it can silently fall behind — and
    did: `care_demand` and `land_stewardship` were both added without being
    registered, which meant neither was ever checked for domain imports."""
    import pathlib

    on_disk = {
        f"hours_eoh.reference.{p.stem}"
        for p in pathlib.Path("hours_eoh/reference").glob("*.py")
        if p.stem != "__init__"
    }
    assert on_disk == set(REFERENCE_MODULES), (
        f"unregistered: {sorted(on_disk - set(REFERENCE_MODULES))}; "
        f"stale: {sorted(set(REFERENCE_MODULES) - on_disk)}"
    )


class TestLayerIsolation:

    def _get_module_imports(self, module_name: str) -> set[str]:
        mod = importlib.import_module(module_name)
        source = inspect.getsource(mod)
        imports: set[str] = set()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.add(stripped)
        return imports

    def _has_domain_import(self, imports: set[str]) -> bool:
        # CLAUDE.md: "reference/ imports nothing from the package". data.py is on
        # this list deliberately — a reference module that reads a calibration
        # constant is no longer independent of the thing it calibrates.
        domain_prefixes = (
            "from hours_eoh.core",
            "from hours_eoh.land",
            "from hours_eoh.scenarios",
            "from hours_eoh.data",
            "from hours_eoh.params",
            "import hours_eoh.core",
        )
        return any(
            any(imp.startswith(p) for p in domain_prefixes)
            for imp in imports
        )

    @pytest.mark.parametrize("module_name", REFERENCE_MODULES)
    def test_no_domain_imports(self, module_name):
        imports = self._get_module_imports(module_name)
        assert not self._has_domain_import(imports), (
            f"{module_name} must not import from hours_eoh domain modules"
        )
