"""
Which paid work discharges an obligation — the attribution the labour-side ε needs.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. ε can be read off a capital inventory (`capital_inventory`) or
off time use, and until now only the first had been tried. The second needs one
thing the first does not: a decision about which PAID work fulfils one of the
four EOH domains. Unpaid household time is measured directly by ATUS, but a
nurse's shift and an advertising executive's are both paid hours and only one of
them discharges an obligation.

**THE LABOUR ROUTE HAS ONE FREE PARAMETER WHERE THE CAPITAL ROUTE HAS THREE**,
and that is the point of building it. Reading ε off assets requires a valuation
doctrine (1.78×), a currency conversion (1.45×) and a scope of capital (2.54×).
Reading it off time use requires only this attribution: no currency appears
anywhere, so no valuation step happens. That is the census route beating the
valuation route on determinacy, measured on the framework's own retrodiction.

ATTRIBUTED AT THE SOC MAJOR-GROUP LEVEL, deliberately. The registry carries 747
detailed occupations and attributing each by hand would produce a false
precision: the judgement is about whether a KIND of work discharges an
obligation, and that judgement lives at the group. Two scopes bound it; there is
no weighted middle and no coefficient to tune.

DISJOINT FROM NOTHING, AND THAT IS NOT AN OVERSIGHT. `servicing.py` counts
highway and utility workers for the Ground Use Fee, and several appear here too.
That is NOT the double-application failure, because the two totals are never
summed: servicing asks what land costs to hold, this asks how much human labour
discharges obligation. The same hour legitimately answers both questions.
`verification.py` is the exception and IS excluded — the register is DELIVERY
cost, the apparatus that makes obligation legible, not the obligation itself.

Layer: reference/ — pure data, imports nothing from the package outside reference/.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

__all__ = [
    "OBLIGATION_GROUPS", "BROAD_GROUPS", "EXCLUDED_GROUPS", "SCOPES",
    "employment_by_major_group", "obligation_share", "what_this_cannot_settle",
]

_DATA = Path(__file__).parent / "data"


#: SOC major groups whose output IS one of the four domain obligations. The
#: membership test: **would this work exist if the obligation did not?**
OBLIGATION_GROUPS: tuple[dict, ...] = (
    {"soc": "29", "name": "Healthcare Practitioners and Technical", "domain": "personal/health",
     "basis": "Discharges the health component directly; the obligation is the patient's."},
    {"soc": "31", "name": "Healthcare Support", "domain": "personal/health+care",
     "basis": "Aides and assistants — the paid counterpart of the unpaid care ATUS measures."},
    {"soc": "35", "name": "Food Preparation and Serving", "domain": "personal/nutrition",
     "basis": "The paid half of the nutrition component; ATUS measures only the unpaid half."},
    {"soc": "45", "name": "Farming, Fishing, and Forestry", "domain": "personal/nutrition+ecological",
     "basis": "Production of the food the basket is denominated in, plus land stewardship."},
    {"soc": "47", "name": "Construction and Extraction", "domain": "infrastructure+personal/shelter",
     "basis": "Builds and renews the capital whose maintenance IS the infrastructure obligation."},
    {"soc": "49", "name": "Installation, Maintenance, and Repair", "domain": "infrastructure",
     "basis": "The infrastructure obligation is maintenance, and this is the occupation that is it."},
    {"soc": "37", "name": "Building and Grounds Cleaning and Maintenance", "domain": "infrastructure+shelter",
     "basis": "Keeps occupied space habitable — the shelter component's recurring cost."},
)

#: `broad` adds these at full headcount. Each is arguably discharging an
#: obligation and arguably serving something else; including a fraction would
#: need a weight nothing measures, so the scope takes all of it and reads as an
#: upper bound on obligation work — and therefore a LOWER bound on ε.
BROAD_GROUPS: tuple[dict, ...] = (
    {"soc": "25", "name": "Educational Instruction and Library", "domain": "knowledge",
     "basis": "Knowledge transmission is a domain. Held out of core because "
              "schooling also serves socialisation and childcare, which the "
              "personal domain already counts."},
    {"soc": "39", "name": "Personal Care and Service", "domain": "personal/care",
     "basis": "Childcare and eldercare belong; the group also carries fitness "
              "and grooming services, which are discovery above the floor."},
    {"soc": "53", "name": "Transportation and Material Moving", "domain": "infrastructure",
     "basis": "Delivery is how an obligation reaches the person owed it. Held "
              "out of core because most freight serves discretionary consumption."},
    {"soc": "51", "name": "Production", "domain": "personal+infrastructure",
     "basis": "Makes the goods that discharge obligations — and everything else."},
    {"soc": "33", "name": "Protective Service", "domain": "infrastructure",
     "basis": "Public safety is arguably a collective obligation and arguably a "
              "political choice; the framework has no domain that names it."},
)

#: Excluded BY NAME with the reason. A rule would not have caught the last one.
EXCLUDED_GROUPS: tuple[dict, ...] = (
    {"soc": "11", "name": "Management", "reason": "Coordinates work; does not itself discharge an obligation."},
    {"soc": "13", "name": "Business and Financial Operations", "reason":
        "Allocates and accounts for money. The framework's whole argument is "
        "that the monetary layer is not the obligation layer."},
    {"soc": "15", "name": "Computer and Mathematical", "reason":
        "Builds the apparatus rather than discharging the obligation — delivery "
        "cost in the obligation-accounts sense, not obligation."},
    {"soc": "17", "name": "Architecture and Engineering", "reason": "Designs the apparatus; same reading."},
    {"soc": "19", "name": "Life, Physical, and Social Science", "reason":
        "Knowledge CREATION rather than transmission. The knowledge domain is "
        "the cost of not losing what is known."},
    {"soc": "21", "name": "Community and Social Service", "reason":
        "Social workers and clergy. The closest call in the table: real care "
        "work sits here, and so does everything the framework declines to price."},
    {"soc": "23", "name": "Legal", "reason": "Adjudication and contract; institutional rather than physical."},
    {"soc": "27", "name": "Arts, Design, Entertainment, Sports, and Media", "reason":
        "Discovery above the floor by construction — the framework says so."},
    {"soc": "41", "name": "Sales and Related", "reason": "Moves goods between owners; discharges nothing."},
    {"soc": "43", "name": "Office and Administrative Support", "reason":
        "The largest single group at 11.5%, and the one whose exclusion moves "
        "the answer most. It is the paperwork of an economy, and the register's "
        "share of it is counted in `verification.py` as DELIVERY, not here."},
)

SCOPES: dict[str, dict] = {
    "core": {
        "groups": tuple(g["soc"] for g in OBLIGATION_GROUPS),
        "reading": "Work whose output IS a domain obligation. A LOWER bound on "
                   "obligation labour, and therefore an UPPER bound on ε.",
    },
    "broad": {
        "groups": tuple(g["soc"] for g in OBLIGATION_GROUPS) + tuple(g["soc"] for g in BROAD_GROUPS),
        "reading": "Adds every group arguably discharging an obligation, at full "
                   "headcount. An UPPER bound on obligation labour, and a LOWER "
                   "bound on ε.",
    },
}


def employment_by_major_group(
    employment: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """
    Employment in thousands by SOC major group. MEASURED — BLS Employment
    Projections via the multiplier registry, the same file the multiplier and
    both censuses read, so none of them can drift from the others.

    units: thousands of workers.
    """
    if employment is not None:
        src = dict(employment)
    else:
        with (_DATA / "multiplier_registry_v5.csv").open(newline="", encoding="utf-8") as fh:
            src = {r["occ6"]: float(r["ep_employment_k"])
                   for r in csv.DictReader(fh) if r.get("ep_employment_k")}
    out: dict[str, float] = {}
    for occ, emp in src.items():
        out[str(occ)[:2]] = out.get(str(occ)[:2], 0.0) + emp
    return out


def obligation_share(
    scope: str = "core",
    employment: Mapping[str, float] | None = None,
) -> dict:
    """
    The share of paid employment that discharges an obligation.

    Governing equation: `Σ employment[g] for g in SCOPES[scope] / Σ employment`.
    units: dimensionless share of total employment.

    THIS IS AN EMPLOYMENT SHARE USED AS AN HOURS SHARE, and the substitution is
    an assumption: it holds only if obligation-fulfilling occupations work
    average hours. Part-time is concentrated in food service and personal care,
    both of which are IN, so the share of HOURS is likely lower than the share of
    HEADS and this errs toward over-counting obligation labour — which pushes the
    derived ε DOWN. Stated because it is the assumption a reader would otherwise
    have to find.

    Raises:
        ValueError: on an unknown scope.
    """
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {sorted(SCOPES)}, got {scope!r}")
    by_group = employment_by_major_group(employment)
    total = sum(by_group.values())
    admitted = sum(by_group.get(g, 0.0) for g in SCOPES[scope]["groups"])
    return {
        "scope":            scope,
        "total_employment_k": total,
        "obligation_employment_k": admitted,
        "share":            admitted / total if total else 0.0,
        "groups":           SCOPES[scope]["groups"],
        "hours_assumption": "employment share used as hours share; errs toward over-counting",
    }


def what_this_cannot_settle() -> tuple[str, ...]:
    """The gaps, stated by the checker rather than found by a reader."""
    return (
        "Whether a KIND of work discharges an obligation. Group 21 (Community "
        "and Social Service) is the closest call and is excluded; group 43 "
        "(Office and Administrative Support) is 11.5% of employment and its "
        "exclusion moves the answer more than any other single decision.",
        "Whether obligation-fulfilling occupations work average hours. The share "
        "is measured in HEADS and used as HOURS, and part-time is concentrated "
        "in groups that are IN, so this errs toward over-counting.",
        "The boundary between an obligation and its apparatus. Computing and "
        "engineering build what discharges obligations without discharging any, "
        "which is the obligation/delivery split the accounts already draw — but "
        "drawn here on occupations rather than on capital.",
        "Whether the attribution is stable across economies. It is a reading of "
        "the US occupational structure, and a collective with a different "
        "division of labour would attribute differently.",
    )
