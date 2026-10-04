"""
US primary energy use — what the US frame's thermal reading is computed from.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS (2026-10-04). The US frame's thermal utilization came from the
Path C national records (`reference/data/path_c_inputs.json`), whose own
`_WARNING` says the energy figures "are from model training data and were NOT
verified" — tier C. The US record also paired whole-US energy with whole-US
land, where the frame is the contiguous 48. This module holds the figures from
EIA's State Energy Data System, fetched and read for this, so the frame's
reading names a source it can be checked against.

SOURCE. EIA State Energy Data System (SEDS), consumption in billion Btu,
`use_all_btu.csv` (eia.gov/state/seds/sep_use/total/csv/use_all_btu.csv),
data year 2024, status "2024F", fetched 2026-10-04. Series: TETCB total
energy; CLTCB coal, NNTCB natural gas, PMTCB petroleum (the fossil fuels);
NUETB nuclear electric power. Cross-check, same day: EIA Monthly Energy Review
Table 1.3 gives US 2024 total primary energy 94.582 quadrillion Btu against
SEDS's 94.543, and petroleum "excluding biofuels" 35.590 against SEDS's
PMTCB 35.594 — so biofuels are not counted as fossil here.

WHAT COUNTS AS DISSIPATING. `thermal_path_c.collective_dissipation_density`
counts fossil + nuclear as net-additive heat (κ = 1) and the rest as ≈ 0, so
only the fossil and nuclear figures reach the reading. EIA states nuclear at
its thermal input, which is the heat that is dissipated; how EIA counts
non-combustion renewables does not reach the reading at all.

THE FRAME. Contiguous 48 = US − Alaska − Hawaii, by subtraction within one
table and one year, matching `JURISDICTION_FRAMES["us_mainland"]`'s land.

Layer: reference/ — pure data, imports nothing from the package.
"""

from __future__ import annotations

__all__ = [
    "SEDS_YEAR", "SEDS_SOURCE", "BTU_TO_J", "SEDS_BILLION_BTU",
    "contiguous_48_energy_ej", "contiguous_48_fossil_nuclear_share",
]

SEDS_YEAR: int = 2024
SEDS_SOURCE: str = ("EIA State Energy Data System, use_all_btu.csv, 2024 (status 2024F), "
                    "fetched 2026-10-04")

#: The International Table Btu, in joules — the unit EIA's British thermal unit
#: is defined in. A unit definition, not a measurement.
BTU_TO_J: float = 1055.05585262

#: MEASURED, billion Btu, 2024: {state: {series: value}}.
SEDS_BILLION_BTU: dict[str, dict[str, float]] = {
    "US": {"TETCB": 94_543_438.0, "CLTCB": 7_910_833.0, "NNTCB": 34_165_378.0, "PMTCB": 35_593_684.0, "NUETB": 8_165_019.0},
    "AK": {"TETCB": 760_053.0, "CLTCB": 18_333.0, "NNTCB": 460_589.0, "PMTCB": 271_264.0, "NUETB": 0.0},
    "HI": {"TETCB": 271_819.0, "CLTCB": 0.0, "NNTCB": 125.0, "PMTCB": 250_419.0, "NUETB": 0.0},
}


def _contiguous(series: str) -> float:
    s = SEDS_BILLION_BTU
    return s["US"][series] - s["AK"][series] - s["HI"][series]


def contiguous_48_energy_ej() -> float:
    """Total primary energy of the contiguous 48, EJ/yr."""
    return _contiguous("TETCB") * 1.0e9 * BTU_TO_J / 1.0e18


def contiguous_48_fossil_nuclear_share() -> float:
    """Fossil + nuclear over total, contiguous 48 — the share
    `collective_dissipation_density` counts as net-additive heat."""
    dissipating = sum(_contiguous(k) for k in ("CLTCB", "NNTCB", "PMTCB", "NUETB"))
    return dissipating / _contiguous("TETCB")
