"""
ATUS care-by-recipient-age ingest — raw microdata → the shipped care extracts.

Companion to `utils/atus_ingest.py`, which cuts ATUS by ACTIVITY. This one cuts
it by RECIPIENT, which is the cut `AGE_GROUPS`' epistemic pointer asks for and
the one nothing in the repo had made. Run it ONCE when the raw BLS files change;
the repo ships only the small derived CSVs it writes.

    python3 utils/atus_care_ingest.py [--raw rawdata/atus] [--out hours_eoh/reference/data]

Outputs (all committed):
    atus_care_by_age_0325.csv     roster route — care received per person-day by
                                  single year of recipient age, active and
                                  passive, at three attribution settings
    atus_care_eldercare_1125.csv  module route — eldercare minutes by recipient
                                  age, household and non-household
    atus_care_rivalry_0325.csv    care time by dependant count, and the fitted ρ
    atus_care_coverage_0325.csv   care that could NOT be attributed, and why

CARE IS JOINT PRODUCTION — the problem this script exists to solve
------------------------------------------------------------------
An hour spent minding two children is not two hours of care, and it is not half
an hour each. Measured over the file, care time scales as

    T(n) = T(1) · n^ρ

in the number of dependants, with ρ ≈ 0.25 for ACTIVE care (primary diary
activities) and ρ ≈ 0.10 for PASSIVE care (secondary childcare, eldercare
minutes). ρ=1 would be fully rivalrous, ρ=0 fully shared. Attribution therefore
gives each of n recipients

    duration × n^(ρ−1)

which reproduces equal-split at ρ=1 and per-recipient duplication at ρ=0. All
three are written as separate columns so the corner readings stay checkable and
nobody has to trust this script's ρ to use its output.

ρ is estimated from CASE-LEVEL totals against dependant counts, which does not
depend on attribution — so there is no circularity between the exponent and the
allocation that uses it.

ACTIVE vs PASSIVE is ATUS's own distinction, not one imposed here: primary care
activities (TRTIER1P 03/04) are the active column; TRTCCTOT_LN (secondary
childcare, "child in your care during this activity") and TRTEC_LN (eldercare
minutes during an activity) are the passive column. Passive is roughly 4× active
and nearly non-rivalrous, which is what "being on call" should look like.

UNREACHABLE IS NOT ZERO
-----------------------
A care activity with no roster-joinable recipient is EXCLUDED carrying its
reason, never costed at zero — the discipline of
`core.eoh_generation.personal_statutory_floor`. Two reasons dominate and both
are large: `non_household` (tier1 04 care, whose recipients are not on the
household roster by construction) and `no_lineno` (who-rows recording presence
without an identifiable person). Magnitudes go to the coverage file so a reader
sees the size of what the curve does not cover.

WEIGHTS — the same trap `atus_ingest.py` documents
---------------------------------------------------
`TUFNWGTP` is zero for 2020; BLS ships `TU20FWGT` for the 2019–20 period. 2020
is flagged not-comparable (collection suspended mid-March to mid-May) and is
never silently pooled. Both behaviours are imported from `atus_ingest` rather
than restated, so the two extracts cannot drift apart on the weighting rule.

UNITS: minutes per person-day. Numerator is weighted care minutes attributed to
persons of age a; denominator is weighted person-days of exposure at age a. No
annualizing convention and no 15+ bridge is applied here — those are the
caller's, exactly as in `reference/atus_time_use.py`.
"""

from __future__ import annotations

import argparse
import collections
import csv
import math
import sys
from pathlib import Path

# Allow running directly from repo root without install (as utils/eoh_cli.py does)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.atus_ingest import (  # noqa: E402
    DEFAULT_WEIGHT,
    NON_COMPARABLE_YEARS,
    SPECIAL_WEIGHT_YEARS,
)

#: ATUS tier-1 codes for care. 03 = caring for and helping HOUSEHOLD members,
#: 04 = caring for and helping NON-household members.
CARE_TIER1: frozenset[str] = frozenset({"03", "04"})

#: Secondary childcare is collected for children under this age only, so ages
#: 13–17 carry no passive measure. Stated here because it is a real hole in the
#: curve, not a detail of the file format.
SECONDARY_CHILDCARE_MAX_AGE: int = 12

#: Dependant counts the rivalry exponent is fitted over. Beyond 4 the cell counts
#: thin out and household composition stops being comparable.
RIVALRY_FIT_COUNTS: tuple[int, ...] = (1, 2, 3, 4)

#: Age at or above which a roster member can be a care PROVIDER. Used only for
#: the adults-per-household count that limit 1 in the module docstring needs.
ADULT_AGE: int = 18

#: Tier-2 code for sleeping, EXCLUDED from self-maintenance.
#:
#: Personal EOH is the labour required to resist entropy for a person, not the
#: hours that person exists. Sleep is ~8.5 h/day and consumes nobody's working
#: time, so counting it would swamp every other term and make an adult's own
#: obligation four times an infant's total care. It is the single most
#: consequential exclusion in this file.
SLEEP_TIER2: str = "0101"

#: Tier-1 codes making up self-provided personal maintenance: 01 personal care
#: (less sleep) and 02 household activities. What a person does to serve their
#: OWN entropy obligation, as against care they receive from someone else.
SELF_MAINTENANCE_TIER1: frozenset[str] = frozenset({"01", "02"})

_MISSING = {"-1", "-2", "-3", ""}


def _int(cell: str) -> int | None:
    """ATUS uses negative sentinels for missing; treat them as absent, not zero."""
    if cell in _MISSING:
        return None
    try:
        value = int(cell)
    except ValueError:
        return None
    return None if value < 0 else value


def _read_respondents(resp_path: Path) -> dict[str, tuple[int, float]]:
    """TUCASEID → (year, weight), dropping cases with no usable weight."""
    out: dict[str, tuple[int, float]] = {}
    with resp_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        i_case, i_year = idx["TUCASEID"], idx["TUYEAR"]
        weight_cols = {
            name: idx[name]
            for name in {DEFAULT_WEIGHT, *SPECIAL_WEIGHT_YEARS.values()}
        }
        for row in reader:
            year = int(row[i_year])
            column = weight_cols[SPECIAL_WEIGHT_YEARS.get(year, DEFAULT_WEIGHT)]
            weight = float(row[column])
            if weight > 0.0:
                out[row[i_case]] = (year, weight)
    return out


def _read_roster(rost_path: Path) -> tuple[
    dict[tuple[str, str], int], dict[str, list[int]]
]:
    """``(caseid, lineno) → age`` and ``caseid → [ages]``."""
    by_line: dict[tuple[str, str], int] = {}
    by_case: dict[str, list[int]] = collections.defaultdict(list)
    with rost_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        i_case, i_line, i_age = idx["TUCASEID"], idx["TULINENO"], idx["TEAGE"]
        for row in reader:
            age = _int(row[i_age])
            if age is None:
                continue
            by_line[(row[i_case], row[i_line])] = age
            by_case[row[i_case]].append(age)
    return by_line, dict(by_case)


def _read_activities(act_path: Path) -> tuple[
    dict[tuple[str, str], tuple[str, int]],
    dict[str, float],
    dict[str, float],
    dict[str, float],
]:
    """Care activities, plus per-case passive childcare and eldercare minutes.

    Returns ``((caseid, activity_n) → (tier1, minutes), caseid → own-household
    secondary childcare minutes, caseid → secondary childcare for children NOT
    on the roster, caseid → eldercare minutes)``. Passive care is recorded
    against the ACTIVITY the respondent was doing at the time — cooking, driving —
    so it is summed to the case rather than joined to a care activity.
    """
    care: dict[tuple[str, str], tuple[str, int]] = {}
    secondary: dict[str, float] = collections.defaultdict(float)
    off_roster: dict[str, float] = collections.defaultdict(float)
    eldercare: dict[str, float] = collections.defaultdict(float)
    with act_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        i_case, i_act = idx["TUCASEID"], idx["TUACTIVITY_N"]
        i_t1, i_dur = idx["TRTIER1P"], idx["TUACTDUR24"]
        # TRTOHH_LN, not TRTCCTOT_LN. The total counts secondary childcare for
        # ALL children under 13 including non-household ones, while the
        # denominator here is the household roster — so the total would put
        # minutes over a population that does not contain their recipients.
        # TRTOHH_LN is the own-household measure and matches the denominator.
        i_cc, i_all = idx["TRTOHH_LN"], idx["TRTCCTOT_LN"]
        i_ec = idx["TRTEC_LN"]
        for row in reader:
            case = row[i_case]
            if row[i_t1] in CARE_TIER1:
                minutes = _int(row[i_dur])
                if minutes is not None:
                    care[(case, row[i_act])] = (row[i_t1], minutes)
            cc = _int(row[i_cc])
            if cc:
                secondary[case] += cc
            total_cc = _int(row[i_all])
            if total_cc:
                off_roster[case] += total_cc - (cc or 0)
            ec = _int(row[i_ec])
            if ec:
                eldercare[case] += ec
    return care, dict(secondary), dict(off_roster), dict(eldercare)


def _read_who(
    who_path: Path,
    care: dict[tuple[str, str], tuple[str, int]],
    roster: dict[tuple[str, str], int],
) -> tuple[dict[tuple[str, str], list[int]], collections.Counter[str]]:
    """Recipient ages present at each care activity, and why rows were dropped."""
    ages: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    dropped: collections.Counter[str] = collections.Counter()
    with who_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        i_case, i_act, i_line = idx["TUCASEID"], idx["TUACTIVITY_N"], idx["TULINENO"]
        for row in reader:
            key = (row[i_case], row[i_act])
            if key not in care:
                continue
            age = roster.get((row[i_case], row[i_line]))
            if age is None:
                # TULINENO = -1: someone was present but is not on the household
                # roster, so their age is unknowable from this file. Counted, not
                # dropped silently.
                dropped["no_lineno"] += 1
                continue
            ages[key].append(age)
    return dict(ages), dropped


def _share(n: int, rho: float) -> float:
    """Each of ``n`` joint recipients' share of one unit of care time.

    ``share = n^(−ρ)``, so ρ=1 (fully rivalrous — attention divides) gives each
    recipient 1/n, and ρ=0 (fully shared — a bedtime story read to two children
    is a whole story each) gives each the full duration.

    NOT IDENTIFIED, and this is the honest limit of the ρ column. The measured
    exponent conflates two things this data cannot separate: the care TECHNOLOGY
    (how rival attention actually is) and the behavioural RESPONSE (whether
    parents add time to compensate for a second child). Under full compensation
    the two exactly cancel and care received per child is invariant to family
    size; under none, it falls as 1/n. The truth is between, and nothing here
    adjudicates it — which is why the split and duplicate corners are written as
    their own columns rather than being interpolated away.
    """
    if n <= 0:
        return 0.0
    return float(n) ** (-rho)


def _fit_rho(means: dict[int, float]) -> float:
    """Least-squares ρ through the origin on log T(n)/T(1) against log n.

    Through the origin because T(1)/T(1) = 1 is an identity, not an observation —
    fitting an intercept would let the curve miss the one point it cannot miss.
    """
    base = means.get(1)
    if not base:
        return float("nan")
    num = den = 0.0
    for n in RIVALRY_FIT_COUNTS:
        if n == 1 or n not in means or means[n] <= 0.0:
            continue
        x = math.log(n)
        num += x * math.log(means[n] / base)
        den += x * x
    return num / den if den else float("nan")


def _self_maintenance(sum_path: Path) -> dict[tuple[int, int], dict[str, float]]:
    """``(year, respondent age) → weighted self-maintenance minutes and days``.

    The other half of a person's obligation. `AGE_GROUPS`' `eoh_weight` is the
    personal EOH a person GENERATES, and care received from others is only part
    of it — an adult serves most of their own obligation themselves, which
    appears in the diary as their own activity rather than as anyone's care.
    Reading the age profile off care alone would say an infant generates 25× a
    working-age adult, because it counts everything done FOR the infant and
    nothing an adult does for themselves.

    15+ ONLY. ATUS does not survey children, so self-maintenance below 15 is
    unmeasured — not zero. It is plausibly near zero for an infant and clearly
    not for a twelve-year-old, and nothing here can say where between.
    """
    out: dict[tuple[int, int], dict[str, float]] = collections.defaultdict(
        lambda: {"minutes": 0.0, "days": 0.0}
    )
    with sum_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        columns = [
            (i, name[1:5])
            for name, i in idx.items()
            if name.startswith("t") and name[1:].isdigit() and len(name) == 7
        ]
        keep = [
            (i, t2) for i, t2 in columns
            if t2[:2] in SELF_MAINTENANCE_TIER1 and t2 != SLEEP_TIER2
        ]
        i_year, i_age = idx["TUYEAR"], idx["TEAGE"]
        weight_cols = {
            name: idx[name]
            for name in {DEFAULT_WEIGHT, *SPECIAL_WEIGHT_YEARS.values()}
        }
        for row in reader:
            year = int(row[i_year])
            weight = float(row[weight_cols[SPECIAL_WEIGHT_YEARS.get(year, DEFAULT_WEIGHT)]])
            if weight <= 0.0:
                continue
            cell = out[(year, int(row[i_age]))]
            cell["days"] += weight
            for i, _t2 in keep:
                value = row[i]
                if value != "0":
                    cell["minutes"] += weight * float(value)
    return dict(out)


def ingest(raw_dir: Path, out_dir: Path) -> list[Path]:
    """Read the raw ATUS files and write the four care extracts."""
    paths = {
        "act": raw_dir / "act" / "atusact_0325.dat",
        "who": raw_dir / "who" / "atuswho_0325.dat",
        "rost": raw_dir / "rost" / "atusrost_0325.dat",
        "rostec": raw_dir / "rostec" / "atusrostec_1125.dat",
        "resp": raw_dir / "resp" / "atusresp_0325.dat",
        "sum": raw_dir / "sum" / "atussum_0325.dat",
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"missing raw ATUS file ({name}): {path}")

    respondents = _read_respondents(paths["resp"])
    roster_line, roster_case = _read_roster(paths["rost"])
    care, secondary, off_roster, eldercare = _read_activities(paths["act"])
    recipient_ages, dropped = _read_who(paths["who"], care, roster_line)

    # --- rivalry: case-level care totals against dependant count --------------
    # Independent of attribution, which is what keeps ρ non-circular.
    kids_per_case = {
        case: sum(1 for a in ages if a <= SECONDARY_CHILDCARE_MAX_AGE)
        for case, ages in roster_case.items()
    }
    active_case: dict[str, float] = collections.defaultdict(float)
    for (case, _act), (tier1, minutes) in care.items():
        if tier1 == "03":
            active_case[case] += minutes

    rivalry: dict[str, dict[int, list[float]]] = {
        "active": collections.defaultdict(list),
        "passive": collections.defaultdict(list),
    }
    for case, total in active_case.items():
        n = kids_per_case.get(case, 0)
        if n:
            rivalry["active"][min(n, max(RIVALRY_FIT_COUNTS))].append(total)
    for case, total in secondary.items():
        n = kids_per_case.get(case, 0)
        if n:
            rivalry["passive"][min(n, max(RIVALRY_FIT_COUNTS))].append(total)

    means = {
        kind: {n: sum(v) / len(v) for n, v in counts.items() if v}
        for kind, counts in rivalry.items()
    }
    rho = {kind: _fit_rho(m) for kind, m in means.items()}

    # --- roster route: care received per person-day by recipient age ----------
    # Three attribution settings side by side. "rho" is the measured joint
    # reading; "split" (ρ=1) and "dup" (ρ=0) are the corner cases, kept so the
    # output does not require trusting the fitted exponent.
    settings = {"rho": rho, "split": {"active": 1.0, "passive": 1.0},
                "dup": {"active": 0.0, "passive": 0.0}}
    # split = ρ1 = each recipient gets 1/n, so attributed care equals observed
    # care (the supply-conserving reading). dup = ρ0 = each gets the full
    # duration (the non-rival reading, and the one that reads as INDIVIDUAL
    # demand: what this person's care actually looked like). The curve is built
    # on dup and the joint saving is carried separately by ρ, rather than being
    # folded into the curve where it could not be seen.
    numer: dict[tuple[int, int], dict[str, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float)
    )
    person_days: dict[tuple[int, int], float] = collections.defaultdict(float)
    excluded: dict[str, dict[str, float]] = collections.defaultdict(
        lambda: {"activities": 0.0, "minutes": 0.0}
    )

    for (case, act), (tier1, minutes) in care.items():
        meta = respondents.get(case)
        if meta is None:
            excluded["no_weight"]["activities"] += 1
            excluded["no_weight"]["minutes"] += minutes
            continue
        year, weight = meta
        ages = recipient_ages.get((case, act), [])
        if not ages:
            reason = "non_household" if tier1 == "04" else "no_roster_match"
            excluded[reason]["activities"] += 1
            excluded[reason]["minutes"] += minutes * weight
            continue
        for label, exponents in settings.items():
            share = _share(len(ages), exponents["active"])
            for age in ages:
                numer[(year, age)][f"active_{label}"] += weight * minutes * share

    # Passive childcare: recorded against whatever the respondent was doing, so
    # it is attributed across the household's own under-13s rather than joined
    # to an activity.
    for case, passive_minutes in secondary.items():
        meta = respondents.get(case)
        if meta is None:
            continue
        year, weight = meta
        kids = [a for a in roster_case.get(case, [])
                if a <= SECONDARY_CHILDCARE_MAX_AGE]
        if not kids:
            excluded["secondary_no_child_on_roster"]["activities"] += 1
            excluded["secondary_no_child_on_roster"]["minutes"] += passive_minutes * weight
            continue
        excluded["secondary_off_roster_children"]["minutes"] += (
            off_roster.get(case, 0.0) * weight
        )
        for label, exponents in settings.items():
            share = _share(len(kids), exponents["passive"])
            for age in kids:
                numer[(year, age)][f"passive_{label}"] += weight * passive_minutes * share

    for case, (year, weight) in respondents.items():
        for age in roster_case.get(case, []):
            person_days[(year, age)] += weight

    # --- eldercare module route ----------------------------------------------
    elder_recipients: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    with paths["rostec"].open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        i_case, i_age, i_hh = idx["TUCASEID"], idx["TEAGE_EC"], idx["TRELHH"]
        for row in reader:
            elder_age = _int(row[i_age])
            if elder_age is not None:
                elder_recipients[row[i_case]].append((elder_age, row[i_hh]))

    elder: dict[tuple[int, int, str], dict[str, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float)
    )
    for case, recips in elder_recipients.items():
        meta = respondents.get(case)
        if meta is None:
            continue
        year, weight = meta
        elder_minutes = eldercare.get(case, 0.0)
        share = _share(len(recips), rho["passive"])
        for age, in_hh in recips:
            cell = elder[(year, age, in_hh)]
            cell["minutes"] += weight * elder_minutes * share
            cell["recipient_days"] += weight
            cell["n_records"] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    by_age_path = out_dir / "atus_care_by_age_0325.csv"
    with by_age_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        columns = [f"{kind}_{label}" for kind in ("active", "passive")
                   for label in settings]
        writer.writerow(["year", "recipient_age", *columns, "person_days",
                         "passive_measured", "comparable"])
        for (year, age) in sorted(person_days):
            days = person_days[(year, age)]
            cell = numer.get((year, age), {})
            # UNREACHABLE IS NOT ZERO. ATUS collects secondary childcare for
            # under-13s only, so ages 13+ have no passive measure at all. Writing
            # 0.0 there would state that nobody supervises a 15-year-old, which
            # is a claim this file has no basis for and the curve would read as
            # measured. The cells are left EMPTY and flagged.
            passive_ok = age <= SECONDARY_CHILDCARE_MAX_AGE
            out_row: list[object] = [year, age]
            for column in columns:
                if column.startswith("passive_") and not passive_ok:
                    out_row.append("")
                elif days:
                    out_row.append(f"{cell.get(column, 0.0) / days:.6f}")
                else:
                    out_row.append("")
            out_row += [f"{days:.1f}", "true" if passive_ok else "false",
                    "false" if year in NON_COMPARABLE_YEARS else "true"]
            writer.writerow(out_row)
    written.append(by_age_path)

    elder_path = out_dir / "atus_care_eldercare_1125.csv"
    with elder_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "recipient_age", "household_member",
                         "minutes_per_recipient_day", "recipient_days",
                         "n_records", "comparable"])
        for key in sorted(elder):
            year, age, in_hh = key
            cell = elder[key]
            days = cell["recipient_days"]
            writer.writerow([
                year, age, in_hh,
                f"{cell['minutes'] / days:.6f}" if days else "",
                f"{days:.1f}", int(cell["n_records"]),
                "false" if year in NON_COMPARABLE_YEARS else "true",
            ])
    written.append(elder_path)

    rivalry_path = out_dir / "atus_care_rivalry_0325.csv"
    with rivalry_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["kind", "dependants", "mean_minutes_per_case_day",
                         "n_cases", "fitted_rho"])
        for kind in ("active", "passive"):
            for n in RIVALRY_FIT_COUNTS:
                values = rivalry[kind].get(n, [])
                if not values:
                    continue
                writer.writerow([
                    kind, n, f"{sum(values) / len(values):.4f}", len(values),
                    f"{rho[kind]:.6f}",
                ])
    written.append(rivalry_path)

    self_path = out_dir / "atus_self_maintenance_0325.csv"
    with self_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "age", "minutes_per_day", "person_days",
                         "comparable"])
        for (year, age), cell in sorted(_self_maintenance(paths["sum"]).items()):
            days = cell["days"]
            writer.writerow([
                year, age,
                f"{cell['minutes'] / days:.6f}" if days else "",
                f"{days:.1f}",
                "false" if year in NON_COMPARABLE_YEARS else "true",
            ])
    written.append(self_path)

    coverage_path = out_dir / "atus_care_coverage_0325.csv"
    with coverage_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["reason", "activities", "weighted_minutes", "note"])
        notes = {
            "non_household": "tier1 04 care — recipient is not on the household "
                             "roster by construction, so their age is unknowable "
                             "from these files",
            "no_roster_match": "tier1 03 care where no person present matched the "
                               "roster",
            "no_lineno": "who-rows recording presence with TULINENO = -1",
            "no_weight": "case carries no usable final weight",
            "secondary_no_child_on_roster": "secondary childcare recorded with no "
                                            "under-13 on the household roster",
            "secondary_off_roster_children": "TRTCCTOT_LN minus TRTOHH_LN — "
                                             "secondary childcare for children "
                                             "not on this household's roster, so "
                                             "outside the curve's denominator",
        }
        for reason in sorted(excluded):
            entry = excluded[reason]
            writer.writerow([reason, int(entry["activities"]),
                             f"{entry['minutes']:.1f}", notes.get(reason, "")])
        for reason, count in sorted(dropped.items()):
            writer.writerow([reason, count, "", notes.get(reason, "")])
    written.append(coverage_path)

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="rawdata/atus", type=Path)
    parser.add_argument("--out", default="hours_eoh/reference/data", type=Path)
    args = parser.parse_args(argv)

    for path in ingest(args.raw, args.out):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
