"""
Can ATUS measure the personal automation floors? Measured, and the answer is no.

WHAT A FLOOR IS. `PERSONAL_AUTOMATION_FLOORS` holds, per personal-EOH component,
the fraction of the obligation that stays human-carried however high automation
goes. Only `care` has an entry, and that entry is a charter DECISION bound to
`CARE_AUTOMATION_FLOOR` (tag `normative`) rather than a measurement. Nutrition,
shelter and health carry none — and an absent floor is treated by the model as
0.0, i.e. fully automatable, which is an assumption nobody has checked.

WHY THIS MODULE EXISTS. That constant's `resolves_by` asks for "a time-use split
of each component's activities into those whose value depends on a HUMAN
performing them". This module runs the closest thing the repo's data can supply
— the six-digit ATUS series over 2003-2025 — and reports what it can and cannot
settle. **REPORTING ONLY. It produces no floor value, and a test enforces that.**

THE INSTRUMENT, AND THE ASYMMETRY THAT MAKES IT READABLE. Over the window,
household capital deepened. Two forces push observed UNPAID hours down:
automation, and marketisation (hiring a cleaner, eating out, paid childcare —
ATUS counts unpaid time only). They cannot be separated in this data. But they
point the SAME WAY, and that asymmetry is what makes the series informative in
one direction only:

  - hours ROSE   -> neither force took them. Evidence FOR a non-zero floor.
  - hours FELL   -> automation or marketisation, indistinguishable. Uninformative.

So a rise is a finding and a fall is not, and no reading of this module may
invert that.

THE SATURATION PROBLEM, WHICH IS THE REAL BLOCKER. The window is 22 years at ONE
development level, and the household automation that matters most had already
happened: washing machines and dishwashers were near-universal in the US well
before 2003. `saturation_evidence()` measures this against a stated control —
mean household size, which fell 4.04% and lowers per-person hours with no
automation involved. The result is weaker than a clean null and is reported as
measured: kitchen clean-up ROSE 15.1% despite dishwashers, while laundry fell
7.8%, which does clear the 4.04% demographic bar but leaves roughly 0.17 points
a year over 22 years. So the window carries at most a faint automation signal in
one probe and an inverted one in the other. That is not enough to calibrate a
floor against, and it is the reason this module returns no floor value.

This is the same blocker `ABATEMENT_HALF_CAPITAL_TEH` names: the quantity wants
two or more CAPITAL levels, and 22 years of US deepening is 22 points at one
saturated level. It resolves the same way, through cross-development time use.

Worked example (2003 vs 2025, hours per person 15+ per year):

    nutrition  food prep      145.8 -> 204.7   +40.4%   rose
               kitchen clean   46.4 ->  53.4   +15.1%   rose  (dishwashers)
    shelter    laundry         67.6 ->  62.3    -7.8%   fell  (vs -4.0% households)
               ext. repair     13.3 ->   4.7   -64.9%   fell  (marketisable)

Nutrition rose on every sub-activity, so its floor is not 0 — which is what the
model currently assumes for it. The level is not recoverable here.
"""

from __future__ import annotations

from hours_eoh.data import (
    CHILDCARE_CODES_MTUS, COMPONENT_CODES_MTUS, MAPPING_TOLERANCE,
    PERSONAL_AUTOMATION_FLOORS, PERSONAL_EOH_COMPONENTS,
)
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.reference import mtus_time_use as mtus
from hours_eoh.scenarios.component_shares import COMPONENT_CODES

#: Components carrying no entry in `PERSONAL_AUTOMATION_FLOORS`, DERIVED from
#: the table rather than restated beside it — a hardcoded list went stale the
#: moment nutrition was adopted on 2026-09-03, which is the `= 1500.0` shape.
UNFLOORED: tuple[str, ...] = tuple(
    c for c in PERSONAL_EOH_COMPONENTS if c not in PERSONAL_AUTOMATION_FLOORS
)

#: Components this module can measure a series for, floored or not. Nutrition
#: stays here after adoption: the series is what the floor was derived FROM, so
#: dropping it would remove the evidence for the value now shipped.
MEASURABLE: tuple[str, ...] = ("nutrition", "shelter", "health")

#: The two household activities whose automation is both canonical and OLDER
#: than the survey window. If these do not fall, the window is measuring a
#: saturated regime and cannot see automation at all.
SATURATED_PROBES: dict[str, str] = {
    "020102": "laundry — washing machines",
    "020203": "kitchen and food clean-up — dishwashers",
}

def _years() -> list[int]:
    return [r.year for r in atus.survey_years() if r.comparable and r.year != 2020]


def _codes_for(component: str) -> tuple[str, ...]:
    prefixes = COMPONENT_CODES[component]
    table = atus.tier3_minutes_per_day(_years()[-1])
    return tuple(sorted(c for c in table if c[:4] in prefixes))


def activity_trends(component: str, min_hours: float = 0.5) -> list[dict]:
    """
    Per six-digit activity, hours per person 15+ at each end of the window.

    `min_hours` drops activities too small at both ends to carry a reading;
    they are not aggregated into a residual, because a residual would let the
    dropped rows influence a conclusion they are too small to support.
    """
    ys = _years()
    first, last = ys[0], ys[-1]
    labels = atus.tier3_labels()
    rows = []
    for code in _codes_for(component):
        a = atus.tier3_hours_per_person_15plus(first, (code,))
        b = atus.tier3_hours_per_person_15plus(last, (code,))
        if a + b < min_hours:
            continue
        rows.append({
            "code": code,
            "label": labels.get(code, ""),
            "first_year": first,
            "last_year": last,
            "hours_first": a,
            "hours_last": b,
            "change": (b - a) / a if a > 0.0 else float("nan"),
            "direction": "rose" if b > a else "fell",
        })
    return sorted(rows, key=lambda r: -r["hours_last"])


def beyond_shrinkage(change: float, household_size_change: float) -> bool:
    """
    Does a per-person decline exceed what household shrinkage already explains?

    Extracted so the rule is testable on its own. On the shipped data no probe
    falls between the household-size change and zero, so the two candidate
    rules — "fell at all" and "fell faster than households" — agree on every
    observed value, and a test written only against the shipped probes cannot
    tell them apart. That is a threshold which cannot fire, so the boundary is
    exercised directly instead.
    """
    return change < household_size_change


def saturation_evidence() -> dict:
    """
    Did the canonical automated household activities decline over the window?

    THE CONTROL. Per-person hours fall when households shrink, with no
    automation involved at all: mean household size fell 4.04% across this
    window. So the rule applied here is that a probe carries an automation
    signal only if its per-person decline EXCEEDS the decline in household
    size. The rule is principled rather than tuned — a fall no larger than the
    demographic change explains itself — but it was stated after the data was
    seen, and it is the only threshold in this module.

    If neither probe clears that bar, the automation that mattered predates the
    sample and the series cannot measure what remains — which is the finding,
    not a caveat.
    """
    ys = _years()
    rows = {r.year: r for r in atus.survey_years() if r.comparable and r.year != 2020}
    hh_first = rows[ys[0]].mean_household_size
    hh_last = rows[ys[-1]].mean_household_size
    hh_change = (hh_last - hh_first) / hh_first

    probes = {}
    for code, what in SATURATED_PROBES.items():
        a = atus.tier3_hours_per_person_15plus(ys[0], (code,))
        b = atus.tier3_hours_per_person_15plus(ys[-1], (code,))
        change = (b - a) / a if a > 0.0 else float("nan")
        probes[code] = {
            "what": what,
            "hours_first": a,
            "hours_last": b,
            "change": change,
            # exceeds the demographic decline, so not explained by it
            "beyond_household_shrinkage": beyond_shrinkage(change, hh_change),
        }
    signal = any(p["beyond_household_shrinkage"] for p in probes.values())
    return {
        "probes": probes,
        "window": (ys[0], ys[-1]),
        "household_size_first": hh_first,
        "household_size_last": hh_last,
        "household_size_change": hh_change,
        "window_can_see_automation": signal,
        "verdict": (
            "at least one canonical automated activity fell faster than "
            "households shrank; the window may carry an automation signal"
            if signal else
            "neither canonical automated activity fell faster than households "
            "shrank across 22 years, and the dishwasher probe ROSE — the "
            "automation that mattered predates the window, so this series "
            "cannot measure what is left for machines to take"
        ),
    }


def floor_direction() -> dict[str, dict]:
    """
    Per unfloored component: does the series support a non-zero floor?

    Only a RISE supports one. A fall is jointly explained by automation and
    marketisation and supports nothing in either direction.
    """
    out = {}
    for component in MEASURABLE:
        rows = activity_trends(component)
        rose = [r for r in rows if r["direction"] == "rose"]
        fell = [r for r in rows if r["direction"] == "fell"]
        ys = _years()
        a = sum(r["hours_first"] for r in rows)
        b = sum(r["hours_last"] for r in rows)
        all_rose = bool(rows) and not fell
        out[component] = {
            "hours_first": a,
            "hours_last": b,
            "change": (b - a) / a if a > 0.0 else float("nan"),
            "n_rose": len(rose),
            "n_fell": len(fell),
            "every_activity_rose": all_rose,
            "supports_nonzero_floor": b > a,
            "reading": (
                "rose across every sub-activity under 22 years of capital "
                "deepening; the model's implied floor of 0.0 is the least "
                "supported reading"
                if all_rose else
                "rose in total; a non-zero floor is supported, the level is not"
                if b > a else
                "fell; automation and marketisation are not separable here, so "
                "this supports nothing in either direction"
            ),
        }
    return out


def atus_window_opens() -> int:
    """
    The first year the ATUS series can see.

    DERIVED from the extract rather than declared as a constant: restating 2003
    here would be a second account of a fact the data already carries, and it
    would silently stop being true if the extract ever reached further back.
    The MTUS series is split at this year to ask where the household-labour
    decline actually happened.
    """
    return min(_years())


def long_series(country: str = "US") -> dict:
    """
    Unpaid domestic work across the MTUS span, split at the ATUS window.

    This is the test the ATUS series cannot run. `saturation_evidence()` argues
    from two probes that the automation which mattered predates 2003; this
    measures it directly on 59 years of the same quantity.

    Worked example (US, ages 18-69, minutes per day):

        1965  170.7      1965 -> 2003   -27.5%   over 38 yr  (-0.723 %/yr)
        2003  123.8      2003 -> 2024    -2.3%   over 21 yr  (-0.108 %/yr)
        2024  121.0      94.3% of the whole fall is before the window opens
    """
    series = mtus.domestic_series(country)
    if len(series) < 2:
        raise ValueError(f"{country} has fewer than two MTUS samples")
    (y0, v0), (y1, v1) = series[0], series[-1]
    opens = atus_window_opens()
    inside = [p for p in series if p[0] >= opens]
    if not inside:
        raise ValueError(f"{country} has no sample inside the ATUS window")
    yw, vw = inside[0]

    def rate(a: tuple[int, float], b: tuple[int, float]) -> float:
        return ((b[1] - a[1]) / a[1]) / (b[0] - a[0]) if b[0] != a[0] else 0.0

    total_fall = v0 - v1
    return {
        "country": country,
        "series": series,
        "span": (y0, y1),
        "first": v0,
        "last": v1,
        "change": (v1 - v0) / v0,
        "window_opens": yw,
        "at_window": vw,
        "change_before_window": (vw - v0) / v0,
        "change_inside_window": (v1 - vw) / vw,
        "rate_before_window": rate((y0, v0), (yw, vw)),
        "rate_inside_window": rate((yw, vw), (y1, v1)),
        "share_of_fall_before_window": (v0 - vw) / total_fall if total_fall else float("nan"),
        "persisting_share": v1 / v0,
    }


def saturation_confirmed(country: str = "US") -> dict:
    """
    Did the ATUS window sit in the flat tail? Measured, rather than argued.

    `saturation_evidence()` reached this from two probes inside the window.
    This reaches it from the same quantity measured for 38 years BEFORE the
    window, which is the stronger form: the decline is real and it is nearly
    all outside the sample ATUS can see.
    """
    s = long_series(country)
    faster = (
        abs(s["rate_before_window"]) / abs(s["rate_inside_window"])
        if s["rate_inside_window"] else float("inf")
    )
    return {
        "share_of_fall_before_window": s["share_of_fall_before_window"],
        "rate_ratio": faster,
        "confirmed": s["share_of_fall_before_window"] > 0.5,
        "verdict": (
            f"{s['share_of_fall_before_window']:.1%} of the whole decline happened "
            f"before {s['window_opens']}, at {faster:.1f}x the rate inside the "
            "window — the ATUS series measures the flat tail of a response that "
            "had already happened"
        ),
    }


def aggregate_floor_bound(country: str = "US") -> dict:
    """
    What the long series bounds, and in which direction.

    `persisting_share` is the fraction of the earliest measured level still
    being worked at the end. It is an UPPER bound on the aggregate floor, and
    the direction is the whole point: the baseline is 1965, which already had
    washing machines and refrigerators, so the true unautomated level is HIGHER
    than the baseline and the floor measured against it is LOWER than this.

    It is an AGGREGATE — `ACT_UNDOM` is nutrition and shelter together — so it
    constrains no single component. What it does refute is a floor of 0.0 for
    the aggregate, which is what three absent entries currently mean.
    """
    s = long_series(country)
    return {
        "persisting_share": s["persisting_share"],
        "is_upper_bound": True,
        "baseline_year": s["span"][0],
        "why_upper_bound": (
            f"the baseline is {s['span'][0]}, which already carried substantial "
            "household automation; against a truly unautomated baseline the "
            "persisting share would be smaller"
        ),
        "is_an_aggregate": True,
        "constrains_a_single_component": False,
    }


def cross_country() -> dict:
    """
    Is the cross-section a capital gradient? Measured, and it is NOT.

    The obvious route to per-component floors is to compare rich against poor
    economies at a point in time. These samples refuse it: Korea reads the
    LOWEST unpaid domestic time of any country here despite being a high-income
    economy, Bulgaria ROSE 38.6% across its post-socialist transition as
    collective provision collapsed back into households, and South Africa sits
    mid-range and flat. Measurement convention, institutional change and culture
    move this quantity as much as capital does.

    So the within-country long series is the usable instrument and the
    cross-section is not — which is a finding about method, and it is why this
    module does not rank samples by development.
    """
    rows = mtus.domestic_by_sample()
    by_country: dict[str, list[tuple[int, float]]] = {}
    for r in rows:
        by_country.setdefault(str(r["country"]), []).append(
            (int(r["year"]), float(r["undom_minutes_per_day"]))
        )
    spans = {
        c: {
            "first_year": sorted(v)[0][0], "last_year": sorted(v)[-1][0],
            "first": sorted(v)[0][1], "last": sorted(v)[-1][1],
            "change": (sorted(v)[-1][1] - sorted(v)[0][1]) / sorted(v)[0][1],
        }
        for c, v in by_country.items() if len(v) > 1
    }
    levels = {c: sorted(v)[-1][1] for c, v in by_country.items()}
    rising = sorted(c for c, s in spans.items() if s["change"] > 0.0)
    return {
        "spans": spans,
        "latest_level": levels,
        "lowest_country": min(levels, key=lambda c: levels[c]),
        "highest_country": max(levels, key=lambda c: levels[c]),
        "countries_where_it_ROSE": rising,
        "is_a_capital_gradient": False,
        "verdict": (
            f"{len(rising)} of {len(spans)} countries with more than one sample "
            f"show unpaid domestic time RISING, and the lowest level of all is "
            f"{min(levels, key=lambda c: levels[c])}; the cross-section is not a "
            "capital gradient and must not be read as one"
        ),
    }


#: `childcare` is reachable by the series functions but is NOT in
#: COMPONENT_CODES_MTUS, because it does not map to a model component at the
#: bar the other two clear. Kept separate so nothing can claim it does.
_EXTRA_CODE_SETS: dict[str, tuple[int, ...]] = {"childcare": CHILDCARE_CODES_MTUS}


def _mtus_codes_for(name: str) -> tuple[int, ...]:
    """MTUS codes for a component or for one of the extra sets."""
    if name in COMPONENT_CODES_MTUS:
        return COMPONENT_CODES_MTUS[name]
    return _EXTRA_CODE_SETS[name]


def _median_abs_change(rep: dict) -> float:
    """
    Median absolute change across countries.

    Used instead of "does a majority fall": with seven countries a majority
    test turns 4-3 into a replication and 3-4 into none, which is a coin toss
    dressed as a finding. The magnitudes are not close — childcare moves 0.024
    at the median against nutrition's 0.163 — and that is the contrast.
    """
    changes = sorted(abs(row["change"]) for row in rep["countries"].values())
    mid = len(changes) // 2
    if len(changes) % 2:
        return changes[mid]
    return (changes[mid - 1] + changes[mid]) / 2.0


def childcare_identification() -> dict:
    """
    Verify the childcare code set against MTUS's OWN aggregate.

    This is a different and stronger kind of check than
    `validate_code_mapping()`: that one asks whether a code set reproduces an
    ATUS component, which is an outside target and can only ever be
    approximate. This one recovers MTUS's own definition, so it can be exact —
    and it is, on every sample.
    """
    aggregate = {
        str(r["sample"]): float(r["chcare_minutes_per_day"])
        for r in mtus.domestic_by_sample()
    }
    ratios = {}
    for sample in mtus.codes_by_sample():
        target = aggregate.get(sample, 0.0)
        if target <= 0.0:
            continue
        ratios[sample] = mtus.code_minutes(sample, CHILDCARE_CODES_MTUS) / target
    values = list(ratios.values())
    return {
        "codes": CHILDCARE_CODES_MTUS,
        "n_samples": len(values),
        "mean_ratio": sum(values) / len(values),
        "min_ratio": min(values),
        "max_ratio": max(values),
        "exact_everywhere": all(abs(r - 1.0) < 0.005 for r in values),
        "target": "the file's own ACT_CHCARE aggregate, not an outside survey",
    }


def childcare_is_not_the_care_component() -> dict:
    """
    How much of the model's `care` this actually covers — measured, so the
    scope limit travels with the series rather than sitting in a comment.

    The model's care is household AND non-household, children AND adults. The
    residual has no MTUS home: adult and non-household care are not carried as
    a separate harmonised aggregate, so no finer reading recovers them, and
    searching the code space for a set that happens to hit ATUS care would be
    fitting rather than identifying.
    """
    from hours_eoh.scenarios.component_shares import COMPONENT_CODES as ATUS_CODES
    care = ATUS_CODES["care"]
    household = tuple(c for c in care if c.startswith("03"))
    full, hh = [], []
    for year in _years():
        sample = f"US{year}"
        if sample not in mtus.codes_by_sample():
            continue
        table = atus.minutes_per_day(year)
        minutes = mtus.code_minutes(sample, CHILDCARE_CODES_MTUS)
        full.append(minutes / sum(table.get(c, 0.0) for c in care))
        hh.append(minutes / sum(table.get(c, 0.0) for c in household))
    mean_full = sum(full) / len(full)
    return {
        "n_years": len(full),
        "share_of_atus_care": mean_full,
        "spread": max(full) - min(full),
        "ratio_to_household_members_only": sum(hh) / len(hh),
        "clears_the_mapping_bar": abs(mean_full - 1.0) <= MAPPING_TOLERANCE / 4,
        "admitted_as_a_component": "childcare" in COMPONENT_CODES_MTUS,
        "what_is_missing": (
            "adult care and non-household care, which MTUS does not carry as a "
            "separate harmonised aggregate"
        ),
    }


def care_floor_corroboration() -> dict:
    """
    Childcare against nutrition, over the same spans and the same instrument.

    `CARE_AUTOMATION_FLOOR` is `normative` — a charter commitment that some
    fraction of care is relational and cannot be automated at any level. No
    dataset was ever cited for it. This does not measure the floor, but it does
    ask whether the series behaves the way a high floor would predict, using a
    component measured the same way as a contrast.

    The marketisation confound runs the RIGHT way here, which is unusual. Paid
    daycare and residential care move care OUT of unpaid time, so observed
    unpaid childcare should fall even if nothing were automated. It does not
    fall. That makes flatness harder to explain away, not easier.
    """
    child = component_long_series("childcare", "US")
    nutrition = component_long_series("nutrition", "US")
    rep_child = replication("childcare")
    rep_nut = replication("nutrition")
    return {
        "us_childcare_change": child["change"],
        "us_nutrition_change": nutrition["change"],
        "us_span": child["span"],
        "childcare_countries_falling": f"{rep_child['n_fell']}/{rep_child['n_countries']}",
        "nutrition_countries_falling": f"{rep_nut['n_fell']}/{rep_nut['n_countries']}",
        "childcare_is_flatter": abs(child["change"]) < abs(nutrition["change"]),
        "childcare_replicates_a_fall": rep_child["replicates"],
        "childcare_median_abs_change": _median_abs_change(rep_child),
        "nutrition_median_abs_change": _median_abs_change(rep_nut),
        "consistent_with_a_high_floor": (
            _median_abs_change(rep_child) < _median_abs_change(rep_nut) / 2.0
        ),
        "is_a_measurement_of_the_floor": False,
        "verdict": (
            f"US childcare moved {child['change']:+.1%} across "
            f"{child['span'][0]}-{child['span'][1]} against nutrition's "
            f"{nutrition['change']:+.1%} on the same instrument, and falls in "
            f"only {rep_child['n_fell']} of {rep_child['n_countries']} countries "
            f"against nutrition's {rep_nut['n_fell']}. That is what a high "
            "automation floor predicts; it does not measure one"
        ),
    }


def validate_code_mapping() -> dict[str, dict]:
    """
    Check the MTUS→component mapping against ATUS on the years both cover.

    The identification strategy: US samples are in both surveys, so the same
    population-year is coded twice, independently. If a set of MTUS codes is
    the component it claims to be, its level must track the ATUS family across
    every overlapping year — not once, which any coincidence supplies.

    THE SIGN OF THE RESIDUAL IS NOT PREDICTED, and an earlier version of this
    docstring wrongly claimed it was. MTUS here is ages 18-69 and ATUS is 15+:
    excluding teenagers pushes the MTUS figure UP, and excluding the over-69s —
    retired, at home, doing more housework — pushes it DOWN. Both operate and
    neither obviously dominates, so only the MAGNITUDE is evidence. Nutrition
    reads 1.015 and shelter 0.976; both are small, and that is the claim.
    """
    years = [y for y in _years() if f"US{y}" in mtus.codes_by_sample()]
    out: dict[str, dict] = {}
    for component, codes in COMPONENT_CODES_MTUS.items():
        target = COMPONENT_CODES[component]
        ratios = []
        for year in years:
            table = atus.minutes_per_day(year)
            atus_minutes = sum(table.get(c, 0.0) for c in target)
            if atus_minutes <= 0.0:
                continue
            ratios.append(mtus.code_minutes(f"US{year}", codes) / atus_minutes)
        mean = sum(ratios) / len(ratios)
        out[component] = {
            "codes": codes,
            "atus_target": target,
            "n_years": len(ratios),
            "mean_ratio": mean,
            "spread": max(ratios) - min(ratios),
            "within_tolerance": abs(mean - 1.0) <= MAPPING_TOLERANCE,
            "residual_is_small": abs(mean - 1.0) <= 0.05,
        }
    return out


def component_long_series(component: str, country: str = "US") -> dict:
    """
    One component's unpaid hours across the whole MTUS span.

    This is what `long_series()` could not do: `ACT_UNDOM` is nutrition and
    shelter together, and the six-digit coding separates them.

    Worked example (US nutrition, minutes per day, ages 18-69):

        1965  60.65      1965 -> 2003   -47.0%
        2003  32.13      2003 -> 2024   +29.0%   the ATUS window sees only this
        2024  41.46      minimum 30.98 in 2005 = 0.511 of the 1965 level
    """
    codes = _mtus_codes_for(component)
    table = mtus.codes_by_sample()
    series = sorted(
        (int(s[2:]), mtus.code_minutes(s, codes))
        for s in table
        if s.startswith(country) and s[2:].isdigit()
    )
    if len(series) < 2:
        raise ValueError(f"{country} has fewer than two samples in the code extract")
    (y0, v0), (y1, v1) = series[0], series[-1]
    ymin, vmin = min(series, key=lambda p: p[1])
    opens = atus_window_opens()
    inside = [p for p in series if p[0] >= opens]
    yw, vw = inside[0] if inside else (y1, v1)
    return {
        "component": component,
        "country": country,
        "series": series,
        "first": v0, "last": v1, "span": (y0, y1),
        "change": (v1 - v0) / v0,
        "change_before_window": (vw - v0) / v0,
        "change_inside_window": (v1 - vw) / vw,
        "minimum": vmin, "minimum_year": ymin,
        "floor_upper_bound": vmin / v0,
        "reversed_after_minimum": v1 > vmin,
    }


def component_floor_bounds(country: str = "US") -> dict[str, dict]:
    """
    Per-component UPPER bounds on the automation floor.

    The bound is the lowest level ever observed, as a share of the earliest.
    It is an UPPER bound twice over, and both directions are the same way:
    the baseline year already carried household automation, and marketisation
    removes unpaid hours that automation did not. So the true floor is below
    this, and a floor of 0.0 — what an absent entry means to the model — is not
    what the data shows.

    It is still not a floor VALUE. A minimum that was reached and then left is
    a level the series visited, not one it cannot pass.
    """
    out = {}
    for component in COMPONENT_CODES_MTUS:
        s = component_long_series(component, country)
        v = validate_code_mapping()[component]
        out[component] = {
            "floor_upper_bound": s["floor_upper_bound"],
            "minimum_year": s["minimum_year"],
            "baseline_year": s["span"][0],
            "is_upper_bound": True,
            "refutes_a_zero_floor": s["floor_upper_bound"] > 0.0,
            "mapping_mean_ratio": v["mean_ratio"],
            "mapping_is_strong": abs(v["mean_ratio"] - 1.0) <= 0.05,
            "reversed_after_minimum": s["reversed_after_minimum"],
        }
    return out


#: Countries whose series is moved by a known institutional change rather than
#: by capital, DECLARED before the replication is read rather than dropped when
#: it disagrees. BG spans the post-socialist transition, where collective and
#: workplace provision of meals, laundry and childcare collapsed back onto
#: households — a large move in the opposite direction with a cause that is not
#: automation. They are REPORTED alongside, never excluded from the count.
INSTITUTIONAL_BREAK: dict[str, str] = {
    "BG": "1965-2001 spans the post-socialist transition; collective provision "
          "of meals, laundry and childcare fell back onto households",
}


def replication(component: str = "nutrition") -> dict:
    """
    Does the US result hold in other countries? Each within-country series is
    an independent capital gradient.

    WHY THIS IS THE STRONG FORM. `cross_country()` showed the cross-SECTION is
    not a capital gradient — comparing rich against poor at a point in time
    measures convention and institutions too. A within-country series does not
    have that problem: the institutions are held roughly fixed and capital
    moves. Seven of them, run separately, is seven tests rather than one.

    THE COUNT IS REPORTED HONESTLY. Countries with a declared institutional
    break are counted in the denominator and flagged, not removed. A
    replication rate computed after dropping the disagreements is not one.

    Worked example (nutrition, minutes per day, ages 18-69):

        FR 1966-2009  77.6 -> 51.6   -33.6%
        US 1965-2024  60.7 -> 41.5   -31.6%
        CA 1992-2005  47.2 -> 39.5   -16.3%
        NL 1975-2000  60.3 -> 50.7   -15.9%
        KR 1999-2009  52.2 -> 48.4    -7.2%
        ZA 2000-2010  65.1 -> 66.4    +2.1%   flat, lowest capital here
        BG 1965-2001  45.4 -> 76.2   +67.7%   institutional break, declared
    """
    codes = _mtus_codes_for(component)
    table = mtus.codes_by_sample()
    by_country: dict[str, list[tuple[int, float]]] = {}
    for sample in table:
        if not sample[2:].isdigit():
            continue
        by_country.setdefault(sample[:2], []).append(
            (int(sample[2:]), mtus.code_minutes(sample, codes))
        )
    rows = {}
    for country, points in by_country.items():
        points = sorted(points)
        if len(points) < 2:
            continue
        (y0, v0), (y1, v1) = points[0], points[-1]
        rows[country] = {
            "span": (y0, y1),
            "first": v0,
            "last": v1,
            "change": (v1 - v0) / v0,
            "fell": v1 < v0,
            "institutional_break": INSTITUTIONAL_BREAK.get(country),
        }
    fell = [c for c, r in rows.items() if r["fell"]]
    rose = [c for c, r in rows.items() if not r["fell"]]
    rose_unexplained = [c for c in rose if c not in INSTITUTIONAL_BREAK]
    return {
        "component": component,
        "countries": rows,
        "n_countries": len(rows),
        "n_fell": len(fell),
        "fell": sorted(fell),
        "rose": sorted(rose),
        "rose_without_a_declared_break": sorted(rose_unexplained),
        "replication_rate": len(fell) / len(rows),
        "replicates": len(fell) > len(rows) / 2,
        "verdict": (
            f"{len(fell)} of {len(rows)} within-country series fall; the "
            f"{len(rose)} that do not are {', '.join(sorted(rose))}, of which "
            f"{len(INSTITUTIONAL_BREAK.keys() & set(rose))} carries a declared "
            "institutional break"
        ),
    }


def developed_convergence(component: str = "nutrition") -> dict:
    """
    Do the high-capital economies converge on a level?

    A single series' minimum is not a floor — nutrition reached 31.0 in 2005
    and left. But if independent economies with different cuisines, histories
    and institutions settle at a similar LEVEL, that is a much better floor
    signature than any one of them reaching a low point.

    THIS IS NOT YET A FLOOR VALUE, and the reason is stated rather than left
    for a reader to find: every figure here is UNPAID time, so a convergence in
    unpaid cooking may be a convergence in how much cooking is bought rather
    than in an irreducible core.

    THAT LIMIT IS NOW PARTLY ADDRESSED, AND ONLY PARTLY.
    `market_substitution_check()` runs the substitution test on the one country
    with the resolution for it: US preparation rose 33.8% over 2003-2025 while
    food bought ready to eat FELL 12.9% and groceries rose 13.7%, with eating
    flat. Food moved back into the home, so the recent rise is not the market
    unwinding into the measurement.

    What it does not reach is the part this claim rests on. ATUS opens in 2003,
    so the 1965-2005 FALL — where the converged level actually came from — is
    outside it; and the convergence is a CROSS-COUNTRY claim while the test is
    one country. MTUS cannot supply the others: its harmonised coding does not
    separate food bought ready to eat, and the best-matching code for that
    composite over the US overlap is a childcare code at ratio 0.97 with a
    spread of 0.34 — a spurious match, and the spread is the tell.

    "Developed" is taken as the countries WITHOUT a declared institutional
    break and above the median capital of this sample — which this module
    cannot measure, so it uses the ones whose series FELL, i.e. the ones that
    showed a capital response at all. That is a stated circularity, not a
    hidden one.
    """
    rep = replication(component)
    members = sorted(rep["fell"])
    levels = {c: rep["countries"][c]["last"] for c in members}
    lo, hi = min(levels.values()), max(levels.values())
    return {
        "component": component,
        "members": members,
        "levels": levels,
        "low": lo,
        "high": hi,
        "band_ratio": hi / lo if lo > 0 else float("nan"),
        "selection_is_circular": True,
        "is_a_floor_value": False,
        "why_not": (
            "every figure is UNPAID time; a convergence in unpaid cooking may "
            "be a convergence in how much is bought. Partly addressed for the "
            "US by market_substitution_check() — preparation rose while food "
            "bought ready to eat fell — but that covers 2003-2025 and one "
            "country, not the 1965-2005 fall the level came from and not the "
            "cross-country claim. MTUS carries no food-away-from-home code"
        ),
        "substitution_tested_for_us": True,
        "substitution_tested_cross_country": False,
    }


#: ATUS tier-3 codes for food obtained READY TO EAT rather than cooked at home.
#: A declared judgement, and a narrow one: buying a prepared meal (070103, which
#: ATUS separates from grocery shopping at 070101), paying someone to prepare
#: one (090102), and the travel that going out to eat costs (1811xx). Eating
#: itself (110101) is NOT here — it happens wherever the food came from and
#: says nothing about who prepared it.
FOOD_AWAY_CODES: tuple[str, ...] = ("070103", "090102", "181101", "181199")

#: Buying raw ingredients — the opposite direction. If preparation is moving
#: INTO the home, this should rise while FOOD_AWAY_CODES falls.
GROCERY_CODES: tuple[str, ...] = ("070101", "180701")

#: Total eating time, as the control. Marketisation changes where food is
#: PREPARED, not how much is eaten, so this should be roughly flat under either
#: reading — and if it moves sharply, something other than substitution is
#: happening and neither reading is safe.
EATING_CODES: tuple[str, ...] = ("110101",)


def market_substitution_check() -> dict:
    """
    Is the US nutrition series marketisation, or real preparation?

    THE LIMIT THIS ADDRESSES. `developed_convergence()` cannot tell an
    irreducible core from a convergence in how much cooking is BOUGHT, because
    every figure in this module is unpaid time. Spending data would separate
    them and is not in this repo — but ATUS carries a TIME signature for food
    obtained ready to eat, which is a partial substitute for it.

    THE TEST. If the 2003-2025 rise in home preparation were marketisation
    unwinding into the observation rather than real, buying prepared food would
    have moved WITH it. Measured, it moves against: preparation +33.7%, food
    bought ready to eat **-12.9%**, groceries +13.7%, and total eating time flat
    at +2.4%. Food moved back INTO the home. The rise is not a measurement
    artefact of the market.

    WHAT IT DOES NOT SETTLE, and it is most of the question. ATUS opens in 2003,
    so this covers the RECOVERY and not the 1965-2005 fall, which is where the
    level came from. And it is one country: the cross-country convergence is the
    claim that needs this most, and MTUS cannot supply it — its harmonised
    coding does not separate food bought ready to eat, and the best-matching
    code for this composite across the US overlap is a CHILDCARE code at a
    ratio of 0.97 with a spread of 0.34. A good ratio on a wild spread is a
    spurious match, and that is the tell.
    """
    years = [y for y in _years()]
    first, last = years[0], years[-1]

    def hours(year: int, codes: tuple[str, ...]) -> float:
        return atus.tier3_hours_per_person_15plus(year, codes)

    prep_codes = tuple(
        c for c in atus.tier3_minutes_per_day(last)
        if c[:4] in COMPONENT_CODES["nutrition"]
    )
    series = {}
    for label, codes in (
        ("preparation", prep_codes), ("bought_ready_to_eat", FOOD_AWAY_CODES),
        ("groceries", GROCERY_CODES), ("eating", EATING_CODES),
    ):
        a, b = hours(first, codes), hours(last, codes)
        series[label] = {"first": a, "last": b, "change": (b - a) / a}

    prep_rose = series["preparation"]["change"] > 0.0
    away_fell = series["bought_ready_to_eat"]["change"] < 0.0
    return {
        "window": (first, last),
        "series": series,
        "preparation_rose": prep_rose,
        "bought_food_fell": away_fell,
        "moves_against_each_other": prep_rose and away_fell,
        "eating_is_roughly_flat": abs(series["eating"]["change"]) < 0.10,
        "rise_is_marketisation": not (prep_rose and away_fell),
        "covers_the_fall": False,
        "is_cross_country": False,
        "verdict": (
            f"preparation {series['preparation']['change']:+.1%} against food "
            f"bought ready to eat {series['bought_ready_to_eat']['change']:+.1%} "
            f"and groceries {series['groceries']['change']:+.1%}, with eating "
            f"flat at {series['eating']['change']:+.1%} — food moved back INTO "
            "the home, so the rise is not the market unwinding into the "
            f"measurement. Covers {first}-{last} and one country only"
        ),
    }


#: What would retire the assumption in `nutrition_floor_estimate`, and it is NOT
#: an LSMS field. Corrected 2026-09-03 after checking rather than asserting: the
#: personal-obligation handoff says plainly that ATUS "measures the
#: processing/preparation term directly, WHICH LSMS CANNOT". LSMS-ISA v2.0 is a
#: harmonised agricultural PRODUCTIVITY dataset at household-season and plot
#: level; turning harvest into food is outside its scope, not a variable in it.
#: The earlier framing — "a single variable in a survey that already exists" —
#: was wrong, and wrong in the direction that made the gap look cheap.
PROCESSING_TERM_FIELD: str = (
    "hours per person per year on food PROCESSING at low capital — threshing, "
    "winnowing, pounding, milling, drying, storage, fuel collection, water for "
    "cooking, and cooking itself. NOT obtainable from LSMS-ISA, which measures "
    "the harvest and not the meal. Two partial routes exist: the raw LSMS WASH "
    "modules (30 waves, harness already built) reach water and fuel collection, "
    "which is 2 of the 9 activities; and TIME-USE surveys at low capital reach "
    "all of it, which is what MTUS already does approximately."
)

#: MTUS frames used to anchor the unassisted processing term instead of
#: assuming it. Each is unpaid food preparation (codes 18,19) in a lower-capital
#: economy or an earlier decade. NONE is unassisted — South Africa 2010 has
#: mills, electricity and shops — so every one is a LOWER bound on unassisted
#: processing, and therefore yields an UPPER bound on the floor.
PROCESSING_ANCHORS: tuple[str, ...] = ("ZA2000", "ZA2010", "BG2001", "FR1966")


def processing_sensitivity() -> dict:
    """
    What the unmeasured processing term does to the estimate.

    The one assumption in `nutrition_floor_estimate` is that unassisted
    processing equals current US processing. `reference.personal_basket` says
    processing plausibly EXCEEDS production in hand-powered systems, so the
    assumption is low and the estimate is an upper bound. This prices how far.
    """
    from hours_eoh.scenarios.food_conservation import conservation_test

    stages = {s["stage"]: s for s in conservation_test()["stages"]}
    unassisted_production = stages["production"]["lsms_hours"]
    if unassisted_production is None or unassisted_production <= 0.0:
        raise ValueError("no measured unassisted production benchmark")
    numerator = (
        stages["production"]["us_total_hours"] + stages["processing"]["us_total_hours"]
    )
    cases = {
        "assumed_equal_to_current_us": stages["processing"]["us_total_hours"],
        "equal_to_production": unassisted_production,
        "one_and_a_half_times_production": 1.5 * unassisted_production,
        "twice_production": 2.0 * unassisted_production,
    }
    out = {
        name: numerator / (unassisted_production + value)
        for name, value in cases.items()
    }
    shipped = out["assumed_equal_to_current_us"]
    return {
        "floors": out,
        "shipped_assumption": shipped,
        "lowest": min(out.values()),
        "shipped_is_the_highest": shipped == max(out.values()),
        "errs": "HIGH",
        "resolves_by": PROCESSING_TERM_FIELD,
    }


def anchored_processing_estimate() -> dict:
    """
    The floor with the processing term ANCHORED rather than assumed.

    `nutrition_floor_estimate` sets unassisted processing equal to current US
    processing (220.5 h/person-yr), which the handoff says is too low. MTUS
    supplies a measured alternative: unpaid food preparation in lower-capital
    economies and earlier decades, which runs 396-473 h/person-yr against the
    US 2024 figure of 252.

    EVERY ANCHOR IS A LOWER BOUND ON THE UNASSISTED TERM, so every floor here is
    an UPPER bound. None of these frames is unassisted — South Africa 2010 has
    mills, electricity and shops — so true unassisted processing exceeds all of
    them and the true floor is below all of these.

    The tightest bound comes from the LARGEST anchor, which is the opposite of
    the usual intuition: more unassisted processing means a bigger denominator
    and a smaller floor.
    """
    from hours_eoh.scenarios.food_conservation import conservation_test

    stages = {s["stage"]: s for s in conservation_test()["stages"]}
    unassisted_production = stages["production"]["lsms_hours"]
    if unassisted_production is None or unassisted_production <= 0.0:
        raise ValueError("no measured unassisted production benchmark")
    numerator = (
        stages["production"]["us_total_hours"] + stages["processing"]["us_total_hours"]
    )
    per_year = 365.25 / 60.0
    anchors = {}
    for sample in PROCESSING_ANCHORS:
        processing = mtus.code_minutes(sample, COMPONENT_CODES_MTUS["nutrition"]) * per_year
        anchors[sample] = {
            "processing_h_yr": processing,
            "floor": numerator / (unassisted_production + processing),
        }
    floors = {k: v["floor"] for k, v in anchors.items()}
    tightest = min(floors, key=lambda k: floors[k])
    return {
        "anchors": anchors,
        "assumed_estimate": numerator / (unassisted_production + stages["processing"]["us_total_hours"]),
        "anchored_range": (min(floors.values()), max(floors.values())),
        "tightest_bound": floors[tightest],
        "tightest_anchor": tightest,
        "every_anchor_is_a_lower_bound": True,
        "so_every_floor_is_an_upper_bound": True,
        "verdict": (
            f"anchoring the processing term on measured low-capital food "
            f"preparation gives {min(floors.values()):.3f}-{max(floors.values()):.3f} "
            f"against the assumed {numerator / (unassisted_production + stages['processing']['us_total_hours']):.3f}. "
            "No anchor is unassisted, so the true floor is below all of them"
        ),
    }


def nutrition_floor_estimate() -> dict:
    """
    A US-frame best guess at the nutrition automation floor, and its band.

    WHY THIS CONSTRUCTION AND NOT THE TIME SERIES. Everything else in this
    module measures UNPAID time, which cannot separate automation from
    marketisation. This one does not have that problem: it counts the TOTAL
    human labour serving the nutrition obligation, paid and unpaid, from
    `scenarios.food_conservation`. **A restaurant cook is human labour.** Moving
    preparation from a kitchen to a kitchen-for-hire shifts hours between the
    two buckets and leaves the total untouched, so marketisation cannot move
    this number at all. That is the whole reason it is worth computing.

    THE BENCHMARK IS MEASURED, NOT ASSUMED. The unassisted counterfactual for
    PRODUCTION is the LSMS smallholder figure the repo already carries — 330.9
    h/person-yr, rainfed, unassisted stratum, seven countries. Against it, US
    production retains **1.55%**: automation took essentially all of it.

    SERVICE IS EXCLUDED (author decision, 2026-09-03), and the reason is
    structural rather than a preference. **A floor is a lower bound, and service
    has no upper one.** There is no cap on how elaborately a meal can be
    prepared and presented; any number of methods can absorb any number of
    hours, and what those hours command is a market price. An unbounded quantity
    cannot be a floor — it is discovery ABOVE the floor, which is exactly the
    split `core.prices.floor_price` draws between the guaranteed level and the
    `market_premium` above it. Service belongs on the premium side.

    The measurement agrees with the argument: the unassisted benchmark carries
    ZERO service, so US service hours are an activity that did not previously
    exist rather than labour that survived automation. Including them asks what
    share of TODAY'S food labour is un-automatable, which is a different and
    weaker question than what share of the OBLIGATION is.

    Both figures are still returned — `estimate_including_service` is kept as
    the superseded reading so the 14-point difference the decision resolves
    stays visible, on the pattern the Ψ policies and `uniform` set.

    THE LOAD-BEARING ASSUMPTION, AND IT ERRS HIGH. The unassisted PROCESSING
    term is not measured, so this sets it equal to current US processing. But
    `reference.personal_basket` already names both the gap and its size:
    processing is "threshing, winnowing, pounding, milling, drying, storage,
    fuel collection, water for cooking, and cooking itself... **in hand-powered
    systems processing plausibly exceeds production labour**". Unassisted
    production is 330.9 h/person-yr and this assumption uses 220.5, so the
    denominator is almost certainly too small and **the estimate is an UPPER
    bound**. `processing_sensitivity()` prices it: at processing equal to
    production the floor is 0.341, at 1.5x it is 0.273, at 2x it is 0.227.

    So the honest reading is **0.409 as a ceiling, with the plausible range
    running down toward 0.23-0.34**, and the LSMS field below is what would
    replace the assumption with a measurement.

    **THIS IS A BEST GUESS, NOT A MEASUREMENT, AND IT IS NOT ADOPTED.**
    `PERSONAL_AUTOMATION_FLOORS` still carries no nutrition entry.
    """
    from hours_eoh.scenarios.food_conservation import conservation_test

    stages = {s["stage"]: s for s in conservation_test()["stages"]}
    production, processing, service = (
        stages["production"], stages["processing"], stages["service"]
    )
    unassisted_production = production["lsms_hours"]
    if unassisted_production is None or unassisted_production <= 0.0:
        # The whole estimate rests on this one measured benchmark. Without it
        # there is no denominator, and inventing one is the failure this module
        # exists to avoid.
        raise ValueError(
            "no measured unassisted production benchmark; the nutrition floor "
            "estimate has no denominator without it"
        )
    current = {k: v["us_total_hours"] for k, v in stages.items()}

    # Excluding service: what share of the SUBSISTENCE obligation stays human.
    num_core = current["production"] + current["processing"]
    den_core = unassisted_production + current["processing"]
    # Including service on both sides: what share of TODAY'S food labour is
    # un-automatable. Service enters the denominator only because it is in the
    # numerator; the unassisted economy has none of it.
    num_all = num_core + current["service"]
    den_all = den_core + current["service"]

    low, high = num_core / den_core, num_all / den_all
    paid = sum(v["us_paid_hours"] for v in stages.values())
    total = sum(current.values())
    return {
        "frame": "US, 2025, per person per year",
        "current_hours": current,
        "total_hours": total,
        "paid_share": paid / total,
        "unassisted_production_benchmark": unassisted_production,
        "production_retained": current["production"] / unassisted_production,
        "estimate_excluding_service": low,
        "estimate_including_service": high,
        "estimate": low,
        "service_excluded": True,
        "service_is_unbounded": True,
        "superseded_reading_including_service": high,
        "decision_cost": high - low,
        "unassisted_service_is_zero": service["lsms_hours"] == 0.0,
        "unassisted_processing_is_assumed": processing["lsms_hours"] is None,
        "marketisation_cannot_move_it": True,
        "is_a_measurement": False,
        "errs": "HIGH",
        "resolves_by": PROCESSING_TERM_FIELD,
        "is_adopted": "nutrition" in PERSONAL_AUTOMATION_FLOORS,
        "verdict": (
            f"US nutrition floor {low:.3f}, service EXCLUDED because it has no "
            f"upper bound and a floor is a lower one (including it gives "
            f"{high:.3f}). Production retains "
            f"{current['production'] / unassisted_production:.1%} of its "
            "unassisted level; preparation retains essentially all of its. A "
            "best guess on a measured production benchmark and an ASSUMED "
            "processing one — not a measurement, and not adopted"
        ),
    }


def report() -> dict:
    """Everything this scenario reports, in one call."""
    return {
        "window": tuple(_years()[i] for i in (0, -1)),
        "n_years": len(_years()),
        "saturation": saturation_evidence(),
        "long_series": long_series(),
        "saturation_confirmed": saturation_confirmed(),
        "aggregate_floor_bound": aggregate_floor_bound(),
        "cross_country": cross_country(),
        "code_mapping": validate_code_mapping(),
        "component_bounds": component_floor_bounds(),
        "replication": {c: replication(c) for c in COMPONENT_CODES_MTUS},
        "convergence": {c: developed_convergence(c) for c in COMPONENT_CODES_MTUS},
        "childcare_identification": childcare_identification(),
        "childcare_scope": childcare_is_not_the_care_component(),
        "care_floor_corroboration": care_floor_corroboration(),
        "market_substitution": market_substitution_check(),
        "nutrition_floor_estimate": nutrition_floor_estimate(),
        "processing_sensitivity": processing_sensitivity(),
        "anchored_processing": anchored_processing_estimate(),
        "components": floor_direction(),
        "trends": {c: activity_trends(c) for c in MEASURABLE},
        "produces_a_floor_value": False,
        "what_would_settle_it": (
            "cross-development time use (HETUS/MTUS), which supplies the CAPITAL "
            "variation this window lacks — the same acquisition "
            "ABATEMENT_HALF_CAPITAL_TEH names, and it closes both together"
        ),
    }
