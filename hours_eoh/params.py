"""
EohParams: Single mutable parameter container for the EOH → TEH model.

Every calibration-path change goes through p.set() to maintain an audit
trail. Exploratory/sweep code uses p.temporary() context manager.

The key design here describe the state of the four entropy domains and the
registration boundary, not the labor-supply structure. EOH demand drives TEH creation;
labor supply is the response, this response was modeled in a TEH only framework.

Mission Statement: §"Entropy Obligation Hours — Accounting Framework"
"""

from __future__ import annotations
import contextlib
from copy import deepcopy
from collections.abc import Iterator
from typing import Any

from hours_eoh.data import (
    PERSONAL_EOH_BASE, INFRA_MAINT_RATE, INFRA_AGE_FACTOR_MAX,
    ECOLOGICAL_BASE_RATE, ECOLOGICAL_THRESHOLD,
    KNOWLEDGE_EOH_BASE, KNOWLEDGE_EPS_EXPONENT, SKILL_TRANSMISSION_RATE,
    M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET, M_MAX,
    CARE_SIGMOID_DEFAULTS, H_REF, H_MIN,
    CAPITAL_FAILURE_RATE,
    COMPETENCY_THRESHOLD,
    SUFF_LEVY_RATE, TRUST_BASE_TEH, DEP_RATE, DIV_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE, MEANINGFUL_ACTIVITY_TEH_SCALE,
    CAPITAL_STOCK_DEFAULT,
)

# ---------------------------------------------------------------------------
# Default parameter values
# ---------------------------------------------------------------------------
EOH_DEFAULTS: dict[str, Any] = {
    # --- Population & Workforce ---
    "population":           1_000_000,
    "workforce_fraction":   0.50,          # fraction of pop that is employed
    "h_ref":                H_REF,         # reference work-year hours
    "h_min":                H_MIN,         # minimum annual obligation (Condition IV)

    # --- Personal EOH domain ---
    "personal_eoh_base":    PERSONAL_EOH_BASE,   # hours/year, working-age reference

    # --- Infrastructure EOH domain ---
    "capital_stock_teh":       CAPITAL_STOCK_DEFAULT,  # total capital stock in TEH at ε=0
    "infra_maintenance_rate":  INFRA_MAINT_RATE,
    "capital_age_ratio":       0.50,              # mean(current_age / design_life)
    "infra_age_factor_max":    INFRA_AGE_FACTOR_MAX,

    # --- Ecological EOH domain ---
    "ecosystem_health":     0.70,                 # 0=collapsed, 1=pristine
    "ecological_base_rate": ECOLOGICAL_BASE_RATE,
    "ecological_threshold": ECOLOGICAL_THRESHOLD,
    "deferred_ecological":  0.0,                  # accumulated deferred EOH (hours)

    # --- Knowledge EOH domain ---
    "knowledge_complexity":      1.0,              # relative scale of knowledge base
    "skill_decay_rate":          SKILL_TRANSMISSION_RATE,  # K-IV: cohort-turnover renewal; SKILL_DECAY_RATE deprecated
    "knowledge_eoh_base":        KNOWLEDGE_EOH_BASE,
    "knowledge_eps_exponent":    KNOWLEDGE_EPS_EXPONENT,

    # --- Multipliers (Condition II) ---
    "M_target": M_BAND_TARGET,
    "M_low":    M_BAND_LOW,
    "M_high":   M_BAND_HIGH,
    "m_max":    M_MAX,

    # --- Registration sigmoid ---
    "care_sigmoid_start":       CARE_SIGMOID_DEFAULTS["start_share"],
    "care_sigmoid_inflection":  CARE_SIGMOID_DEFAULTS["inflection"],
    "care_sigmoid_rate":        CARE_SIGMOID_DEFAULTS["rate"],
    "care_sigmoid_saturation":  CARE_SIGMOID_DEFAULTS["saturation"],

    # --- Labor category weights (for total_registration_share) ---
    "care_weight":        0.30,
    "production_weight":  0.45,
    "stewardship_weight": 0.25,

    # --- TEH Destruction ---
    "capital_failure_rate": CAPITAL_FAILURE_RATE,

    # --- Fiscal ---
    "suff_levy_rate":              SUFF_LEVY_RATE,
    "trust_base":                  TRUST_BASE_TEH,
    "dep_rate":                    DEP_RATE,
    "div_rate":                    DIV_RATE,
    "meaningful_activity_teh_base":  MEANINGFUL_ACTIVITY_TEH_BASE,   # discretionary bonus at ε=0 (TEH/yr)
    "meaningful_activity_teh_scale": MEANINGFUL_ACTIVITY_TEH_SCALE,  # quadratic ε-growth factor

    # --- Competency (Condition IV) ---
    "competency_threshold": COMPETENCY_THRESHOLD,
}


class EohParams:
    """
    Mutable parameter container for the EOH → TEH model.

    Change-tracking via set() maintains an audit trail for every calibration
    decision. Use temporary() for sweep/exploratory code that should not
    pollute the history.

    Usage::

        p = EohParams()
        p.set("ecosystem_health", 0.50, phase=3, reason="calibration")
        with p.temporary(ecosystem_health=0.30):
            result = some_function(p)   # uses 0.30; history untouched
        # p["ecosystem_health"] is back to 0.50 here
    """

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = deepcopy(EOH_DEFAULTS)
        self._history: list[dict] = []
        if overrides:
            for k, v in overrides.items():
                self.set(k, v, phase=0, reason="init_override")

    # -- Access -----------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        if key not in self._data:
            raise KeyError(f"Unknown parameter: {key!r}")
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value, phase=-1, reason="direct_assign")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    # -- Mutation ---------------------------------------------------------------

    def set(self, key: str, value: Any, *, phase: int = -1, reason: str = "") -> None:
        """Set a parameter and record the change in history."""
        old = self._data.get(key)
        self._data[key] = value
        self._history.append({
            "key": key, "old": old, "new": value,
            "phase": phase, "reason": reason,
        })

    def update(self, d: dict[str, Any], *, phase: int = -1, reason: str = "") -> None:
        """Set multiple parameters with a shared phase/reason."""
        for k, v in d.items():
            self.set(k, v, phase=phase, reason=reason)

    @contextlib.contextmanager
    def temporary(self, **overrides: Any) -> Iterator[EohParams]:
        """
        Context manager: apply overrides, restore on exit. No history entries.
        Safe for use in sweep and simulation code.
        """
        saved = {k: self._data[k] for k in overrides if k in self._data}
        unknown = {k for k in overrides if k not in self._data}
        if unknown:
            raise KeyError(f"Unknown parameters in temporary(): {unknown}")
        self._data.update(overrides)
        try:
            yield self
        finally:
            self._data.update(saved)

    # -- Introspection ----------------------------------------------------------

    def clone(self) -> "EohParams":
        """Deep copy preserving state and history."""
        c = EohParams()
        c._data = deepcopy(self._data)
        c._history = deepcopy(self._history)
        return c

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._data)

    def diff_from_defaults(self) -> dict[str, dict]:
        """Return parameters that differ from defaults."""
        result = {}
        for k, v in self._data.items():
            default = EOH_DEFAULTS.get(k)
            if v != default:
                result[k] = {"default": default, "current": v}
        return result

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    # -- Convenience properties -------------------------------------------------

    @property
    def workforce(self) -> float:
        """Total employed workforce."""
        return self._data["population"] * self._data["workforce_fraction"]

    @property
    def care_sigmoid_params(self) -> dict[str, float]:
        return {
            "start_share": self._data["care_sigmoid_start"],
            "inflection":  self._data["care_sigmoid_inflection"],
            "rate":        self._data["care_sigmoid_rate"],
            "saturation":  self._data["care_sigmoid_saturation"],
        }

    def __repr__(self) -> str:
        return (f"EohParams(population={self._data['population']:,}, "
                f"workforce_fraction={self._data['workforce_fraction']}, "
                f"capital_stock_teh={self._data['capital_stock_teh']:.2e})")
