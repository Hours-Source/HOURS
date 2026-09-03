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

from hours_eoh.data import COMPONENT_CODES_MTUS, MAPPING_TOLERANCE
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.reference import mtus_time_use as mtus
from hours_eoh.scenarios.component_shares import COMPONENT_CODES

#: Components carrying no entry in `PERSONAL_AUTOMATION_FLOORS`. `care` is
#: excluded because its floor is a charter decision, not a measurement gap.
UNFLOORED: tuple[str, ...] = ("nutrition", "shelter", "health")

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
    for component in UNFLOORED:
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
    codes = COMPONENT_CODES_MTUS[component]
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
        "components": floor_direction(),
        "trends": {c: activity_trends(c) for c in UNFLOORED},
        "produces_a_floor_value": False,
        "what_would_settle_it": (
            "cross-development time use (HETUS/MTUS), which supplies the CAPITAL "
            "variation this window lacks — the same acquisition "
            "ABATEMENT_HALF_CAPITAL_TEH names, and it closes both together"
        ),
    }
