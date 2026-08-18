"""
Thermal Sink EOH — the climate feedback parameter λ, derived and framed.

λ was the layer's largest unquantified lever: Tier C, never stated in the
handoff's §4, and worth a several-fold swing in the budget. Unlike ΔT_max it is
genuinely measurable — and measurable from data the repo already ships.

    λ_historical = ( F − N ) / ΔT                        [W·m⁻²·K⁻¹]

F is total effective radiative forcing, N the Earth energy imbalance, ΔT the GMST
anomaly. All three are in IGCC 2025a, so this moves λ from recalled to derived.

λ IS NOT ONE NUMBER — the point of this module. The energy-budget estimate is the
HISTORICAL feedback, which runs high relative to the EQUILIBRIUM feedback because
warming has so far been concentrated where feedbacks are more stabilising (the
pattern effect). Each pairs with exactly one budget frame:

    equilibrium λ  →  equilibrium budget  λ·ΔT_max − F   (commitment accounting)
    historical λ   →  a transient reading, which the framework REJECTS: it shows a
                      larger near-term budget precisely by spending the pipeline
                      (handoff §10.3)

Putting λ_historical into the equilibrium budget inflates it roughly sixfold at
ΔT_max = 3.0 K. That is the single largest way to overstate the thermal
allowance, so `budget_forcing_headroom` REFUSES the combination rather than
returning a number nobody could interpret.

Derived values (full provenance in reference/data/climate_feedback.json):
    λ_historical   1.492, windows 1.466–1.537 — under 5% spread, not window-sensitive
    λ_equilibrium  1.2 shipped (implies ECS 3.28 K), AR6-implied 1.310
    pattern effect +0.182 — positive as expected, an independent check that the
                   derivation behaves

The shipped 1.2 turns out to be CONSERVATIVE for the framework: a lower λ means a
smaller budget and a larger obligation, so the pre-existing constant was not
flattering the result.

Layer: research/ — reads shipped reference data; not imported by core/.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from hours_eoh.data import (
    EARTH_EMISSION_TEMPERATURE_K,
    SIGMA_SB,
    THERMAL_LAMBDA_FEEDBACK,
    THERMAL_TXX_PER_GMST,
    A_EARTH_M2,
    THERMAL_F_NET_ERF,
    THERMAL_F_NET_ERF_P05,
    THERMAL_F_NET_ERF_P95,
)

Frame = Literal["equilibrium", "historical"]

_DATA = Path(__file__).resolve().parents[1] / "reference" / "data" / "climate_feedback.json"


@lru_cache(maxsize=1)
def load_climate_feedback() -> dict:
    """The shipped λ derivation, with its frame discipline and uncertainty band."""
    with _DATA.open(encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


class LambdaChoice(TypedDict):
    frame: Frame
    value: float
    band: tuple[float, float]
    tier: str
    pairs_with: str
    caveat: str | None


def lambda_for_frame(frame: Frame = "equilibrium") -> LambdaChoice:
    """
    The λ appropriate to a budget frame, with the band it must be quoted against.

    "equilibrium" returns the shipped 1.2. Its tier is unchanged, but its POSITION
    is now known rather than assumed: it sits below the AR6-implied 1.310 and well
    below the derived historical 1.492, which is the conservative side.

    "historical" returns the derived 1.492 with a caveat naming what it must not
    be used for.

    units: W·m⁻²·K⁻¹.

    Raises:
        ValueError: on an unknown frame.
    """
    d = load_climate_feedback()
    if frame == "equilibrium":
        eq = d["equilibrium"]
        return LambdaChoice(
            frame=frame,
            value=eq["shipped_default"],
            band=(eq["ar6_ranges"]["likely_66pct"]["lambda"][0],
                  eq["ar6_ranges"]["likely_66pct"]["lambda"][1]),
            tier="C (value) bracketed by A (AR6-implied 1.310, derived historical 1.492)",
            pairs_with="the equilibrium budget λ·ΔT_max − F — commitment accounting",
            caveat=None,
        )
    if frame == "historical":
        h = d["historical"]
        return LambdaChoice(
            frame=frame,
            value=h["central"],
            band=(h["band_from_forcing_uncertainty"][0], h["band_from_forcing_uncertainty"][1]),
            tier=h["tier"],
            pairs_with="a transient reading of the budget, which this framework rejects",
            caveat=("derived from the historical energy budget and biased high by the pattern "
                    "effect; in the equilibrium budget it inflates the allowance ~6x"),
        )
    raise ValueError(f"unknown frame: {frame!r}")


def budget_forcing_headroom(
    delta_t_max: float,
    frame: Frame = "equilibrium",
    f_total: float = THERMAL_F_NET_ERF,
    lam: float | None = None,
) -> float:
    """
    Residual forcing headroom λ·ΔT_max − F (W·m⁻²), with the frame enforced.

    An explicit `lam` overrides the frame's value — but a historical-magnitude λ
    under the equilibrium frame RAISES, because that pairing is the framework's
    largest single overstatement risk and must never happen by accident.

    units: W·m⁻². May be negative — the unbudgeted regime.

    Worked example (ΔT_max = 3.0 K, F = 3.366): equilibrium λ = 1.2 gives
    0.234 W·m⁻²; the historical 1.492 would give 1.110, ~4.7× the headroom and
    ~6× the budget once the reserve is applied. Same arithmetic, different
    question, and only one of them is the question the framework asks.

    Raises:
        ValueError: if an explicitly-passed λ is historical-magnitude while the
            frame is equilibrium.
    """
    choice = lambda_for_frame(frame)
    value = choice["value"] if lam is None else lam
    if lam is not None and frame == "equilibrium":
        hist = load_climate_feedback()["historical"]["central"]
        if lam >= hist - 1e-9:
            raise ValueError(
                f"λ = {lam} is historical-magnitude (≥ {hist}) but frame='equilibrium'. "
                "The historical feedback pairs with a transient budget; in the equilibrium "
                "budget it inflates the allowance several-fold. Pass frame='historical' "
                "deliberately, or use an equilibrium λ."
            )
    return value * delta_t_max - f_total


def lambda_sensitivity(
    delta_t_max: float,
    f_total: float = THERMAL_F_NET_ERF,
    a_earth: float = A_EARTH_M2,
) -> list[dict]:
    """
    The budget across the plausible λ range — a FIRST-CLASS output, not a footnote.

    λ is the second-largest lever after ΔT_max, and the budget does not merely
    shift across its range, it changes several-fold. Any ψ*-derived figure
    published without this band overstates how well the allowance is known.

    Returns one row per λ of interest — shipped default, AR6-implied, both ends of
    the AR6 likely range, and the derived historical value flagged as
    frame-mismatched — each with the resulting budget and its ratio to the
    shipped-default case.

    units: W·m⁻²·K⁻¹ in; watts and W·m⁻² out.
    """
    d = load_climate_feedback()
    eq = d["equilibrium"]
    lk = eq["ar6_ranges"]["likely_66pct"]["lambda"]
    vl = eq["ar6_ranges"]["very_likely_90pct"]["lambda"]
    candidates: list[tuple[str, float, Frame, str | None]] = [
        ("shipped default", eq["shipped_default"], "equilibrium", None),
        ("AR6 best estimate (ECS 3.0 K)", eq["ar6_implied"]["lambda"], "equilibrium", None),
        ("AR6 likely-high sensitivity (ECS 4.0)", lk[0], "equilibrium", None),
        ("AR6 likely-low sensitivity (ECS 2.5)", lk[1], "equilibrium", None),
        ("AR6 very-likely-high (ECS 5.0)", vl[0], "equilibrium",
         "90% bound — the conservative corner"),
        ("derived historical", d["historical"]["central"], "historical",
         "FRAME MISMATCH if used in the equilibrium budget — shown for scale only"),
    ]
    rows: list[dict] = []
    for label, lam, frame, note in candidates:
        headroom = lam * delta_t_max - f_total
        rows.append({
            "label": label,
            "lambda": lam,
            "frame": frame,
            "headroom_w_m2": round(headroom, 4),
            "budget_tw": round(max(0.0, headroom) * a_earth / 1e12, 1),
            "unbudgeted": headroom <= 0.0,
            "note": note,
        })
    base = next(r["budget_tw"] for r in rows if r["label"] == "shipped default")
    for r in rows:
        r["vs_shipped"] = None if base <= 0.0 else round(r["budget_tw"] / base, 2)
    return rows


# ---------------------------------------------------------------------------
# The two-axis determinacy map
# ---------------------------------------------------------------------------

DeterminacyZone = Literal["determinate_unbudgeted", "indeterminate", "determinate_budgeted"]


def determinacy_map(
    delta_t_lo: float,
    lam_band: tuple[float, float] | None = None,
    f_band: tuple[float, float] | None = None,
    txx_per_gmst: float = THERMAL_TXX_PER_GMST,
    confidence: Literal["likely", "very_likely"] = "likely",
) -> dict:
    """
    The determinacy map carrying BOTH uncertain axes — forcing and λ.

    A budget exists iff λ·ΔT_max > F. Determinacy requires the WHOLE parameter
    box to agree, so the thresholds are set by its corners:

        determinately UNBUDGETED   ΔT ≤ F_lo / λ_hi   (the most favourable corner
                                                       still yields no budget)
        determinately BUDGETED     ΔT ≥ F_hi / λ_lo   (the least favourable corner
                                                       still yields one)

    THIS WIDENS THE INDETERMINATE BAND. It cannot do otherwise: adding an
    uncertain axis can only make agreement across the box harder. At AR6's LIKELY
    ECS range (2.5–4.0 K, the default) the band goes from 1.25 K wide to 2.52 K,
    and the determinately-unbudgeted threshold drops from 2.17 K to 1.66 K GMST —
    3.21 K to 2.45 K in land extremes.

    `confidence="very_likely"` carries the 90% range instead (ECS 2.0–5.0),
    giving 1.32 K GMST / 1.96 K TXx and a 3.90 K band. Report it alongside where
    a verdict sits close to a boundary.

    Observed land TXx is already ~1.8 K, so even on the likely range the margin
    between where the world is and the strongest determinate claim is about
    0.65 K — and on the very-likely range it is 0.16 K. The single-axis map's
    3.21 K claim was resting on a λ held fixed at a value nobody had assessed.

    λ DOMINATES. Holding one axis fixed at its centre, forcing alone contributes
    1.25 K of indeterminate width and λ alone 2.57 K — λ is worth ~2.1× as much.
    Narrowing λ therefore buys about twice the determinacy that narrowing the
    forcing estimate would, which is where assessment effort should go.

    units: K (GMST) and K (land TXx via C6). Bands default to the shipped IGCC
    forcing p05/p95 and the AR6 likely ECS range; pass narrower ones to see what
    a tighter assessment would buy.

    Returns:
        dict with `zone`, both thresholds in GMST and TXx, per-axis attribution,
        and `vs_single_axis` giving the cost of carrying λ honestly.

    Raises:
        ValueError: if either band is inverted or non-positive.
    """
    d = load_climate_feedback()
    key = "likely_66pct" if confidence == "likely" else "very_likely_90pct"
    ar6 = d["equilibrium"]["ar6_ranges"][key]
    lam_lo, lam_hi = lam_band or (ar6["lambda"][0], ar6["lambda"][1])
    f_lo, f_hi = f_band or (THERMAL_F_NET_ERF_P05, THERMAL_F_NET_ERF_P95)
    if not (0.0 < lam_lo <= lam_hi) or not (0.0 < f_lo <= f_hi):
        raise ValueError("bands must be positive and ordered (lo, hi)")

    unbudgeted_below = f_lo / lam_hi
    budgeted_above = f_hi / lam_lo
    if delta_t_lo <= unbudgeted_below:
        zone: DeterminacyZone = "determinate_unbudgeted"
    elif delta_t_lo >= budgeted_above:
        zone = "determinate_budgeted"
    else:
        zone = "indeterminate"

    lam_c = d["equilibrium"]["shipped_default"]
    f_c = THERMAL_F_NET_ERF
    width_forcing = (f_hi - f_lo) / lam_c            # λ fixed at centre
    width_lambda = f_c * (1.0 / lam_lo - 1.0 / lam_hi)   # F fixed at centre
    single_lo, single_hi = f_lo / lam_c, f_hi / lam_c

    return {
        "delta_t_lo": delta_t_lo,
        "zone": zone,
        "robust": zone != "indeterminate",
        "lambda_band": (lam_lo, lam_hi),
        "confidence": confidence,
        "forcing_band": (f_lo, f_hi),
        "unbudgeted_below_k": unbudgeted_below,
        "budgeted_above_k": budgeted_above,
        "unbudgeted_below_txx_k": unbudgeted_below * txx_per_gmst,
        "budgeted_above_txx_k": budgeted_above * txx_per_gmst,
        "indeterminate_width_k": budgeted_above - unbudgeted_below,
        "attribution": {
            "forcing_width_k": width_forcing,
            "lambda_width_k": width_lambda,
            "lambda_over_forcing": width_lambda / width_forcing if width_forcing > 0 else None,
            "dominant_axis": "lambda" if width_lambda > width_forcing else "forcing",
        },
        "vs_single_axis": {
            "single_unbudgeted_below_k": single_lo,
            "single_budgeted_above_k": single_hi,
            "single_width_k": single_hi - single_lo,
            "widening_factor": ((budgeted_above - unbudgeted_below) / (single_hi - single_lo)
                                if single_hi > single_lo else None),
            "note": "carrying λ can only WIDEN the band — determinacy needs the whole box "
                    "to agree, so an extra uncertain axis never buys agreement",
        },
    }


def determinacy_gain_from_tightening(
    lam_band: tuple[float, float],
    f_band: tuple[float, float] | None = None,
) -> dict:
    """
    What a tighter λ assessment would buy, in kelvin of recovered determinacy.

    The framework's strongest claim — "below this threshold there is no budget,
    robustly" — is bounded by `unbudgeted_below_k`, and that bound is set by the
    λ upper edge alone (F_lo/λ_hi). Constraining λ from above is therefore worth
    more than any other single measurement the thermal layer could acquire.

    units: K. Returns the thresholds under the supplied band and the shift
    against AR6's likely range.
    """
    base = determinacy_map(0.0)
    tight = determinacy_map(0.0, lam_band=lam_band, f_band=f_band)
    return {
        "lambda_band": lam_band,
        "unbudgeted_below_k": tight["unbudgeted_below_k"],
        "unbudgeted_below_txx_k": tight["unbudgeted_below_txx_k"],
        "gain_vs_ar6_likely_k": tight["unbudgeted_below_k"] - base["unbudgeted_below_k"],
        "indeterminate_width_k": tight["indeterminate_width_k"],
        "width_reduction_k": base["indeterminate_width_k"] - tight["indeterminate_width_k"],
    }


class ThermalVerdict(TypedDict):
    delta_t_lo: float
    zone: DeterminacyZone
    robust: bool
    claim: str
    budget_tw: float | None          # None when the framework cannot report a sign
    overage_tw: float | None
    what_would_resolve: str | None


def thermal_verdict(
    delta_t_lo: float,
    lam_band: tuple[float, float] | None = None,
    f_band: tuple[float, float] | None = None,
    confidence: Literal["likely", "very_likely"] = "likely",
) -> ThermalVerdict:
    """
    THE HEADLINE. What the framework can determinately say at this threshold —
    and, where it cannot, saying so instead of returning a number.

    Every ψ*-derived figure the thermal layer produces is conditional on a
    (λ, F) pair. Reporting one without its determinacy verdict presents a point
    estimate from inside a band where the sign itself is undetermined. Leading
    with determinacy inverts that: the zone comes first, and the numbers are
    released only where they mean something.

        determinate UNBUDGETED   every (λ, F) in the box gives no budget. The
                                 framework's strongest available claim: all
                                 net-additive dissipation is overshoot, and the
                                 overage is reportable.
        INDETERMINATE            the box spans both regimes. `budget_tw` is None
                                 by design — not missing, but withheld, because
                                 asserting either sign would exceed the data.
        determinate BUDGETED     every corner yields a budget; it is reportable
                                 as a lower bound.

    This is a HARDER standard than the single-axis map in
    research.thermal_path_c.determinacy_zone, which holds λ fixed at an
    unassessed value and reports a determinate zone roughly three times wider
    than the evidence supports.

    units: watts for the budget and overage; K for the threshold.

    Worked example (ΔT_lo = 3.0 K): INDETERMINATE. The single-axis map calls the
    same threshold indeterminate too, but its determinate-unbudgeted boundary sits
    at 3.21 K in land extremes against the two-axis 1.96 K — and observed land TXx
    is already ~1.8 K.
    """
    from hours_eoh.research.thermal_overage import thermal_overage

    m = determinacy_map(delta_t_lo, lam_band, f_band, confidence=confidence)
    lam_lo, lam_hi = m["lambda_band"]
    f_lo, f_hi = m["forcing_band"]
    zone = m["zone"]

    if zone == "determinate_unbudgeted":
        o = thermal_overage(delta_t_lo)
        return ThermalVerdict(
            delta_t_lo=delta_t_lo, zone=zone, robust=True,
            claim=("No thermal budget, robustly: every forcing/λ pair in the assessed "
                   "box leaves the allowance consumed before any waste heat. All "
                   "net-additive dissipation is overshoot."),
            budget_tw=0.0,
            overage_tw=round(o["overage_w"] / 1e12, 1),
            what_would_resolve=None,
        )
    if zone == "determinate_budgeted":
        worst = (lam_lo * delta_t_lo - f_hi) * A_EARTH_M2 / 1e12
        return ThermalVerdict(
            delta_t_lo=delta_t_lo, zone=zone, robust=True,
            claim=(f"A thermal budget exists robustly; at least {worst:,.0f} TW survives "
                   "the least favourable corner of the assessed box."),
            budget_tw=round(worst, 1), overage_tw=None, what_would_resolve=None,
        )
    a = m["attribution"]
    return ThermalVerdict(
        delta_t_lo=delta_t_lo, zone=zone, robust=False,
        claim=("INDETERMINATE — the assessed uncertainty spans both regimes, so the "
               "framework cannot report the sign of the budget at this threshold. A "
               "number here would be a point estimate from inside a band that contains "
               "both 'no budget' and 'ample budget'."),
        budget_tw=None, overage_tw=None,
        what_would_resolve=(
            f"determinacy returns below {m['unbudgeted_below_k']:.2f} K or above "
            f"{m['budgeted_above_k']:.2f} K GMST. λ contributes "
            f"{a['lambda_over_forcing']:.1f}x the width that forcing does, so a tighter "
            "assessed λ buys back more determinate zone than any other single "
            "measurement — [1.10, 1.45] would recover ~1.96 K of it."),
    )


# ---------------------------------------------------------------------------
# The Planck bound — the one part of λ that is physics (2026-08-17)
# ---------------------------------------------------------------------------

def planck_feedback(t_emission: float = EARTH_EMISSION_TEMPERATURE_K) -> float:
    """
    The blackbody Planck feedback, derived rather than recalled.

    Governing equation — differentiate Stefan–Boltzmann with respect to T:

        E   = σ · T⁴
        λ_P = dE/dT = 4 · σ · T³

    units: W·m⁻²·K⁻¹.

    Worked example: at Earth's emission temperature of 255 K,
    4 × 5.670374419e-8 × 255³ = **3.761 W·m⁻²·K⁻¹**.

    WHY THIS EXISTS. `SIGMA_SB` is one of only two `physics`-tagged constants in
    the package and, until this function, was read by NOTHING — not by the
    thermal layer, not by a test, and it was not duplicated as a literal either.
    Meanwhile "Planck-only ≈ 3.2" appeared as PROSE in two places
    (`data.py`'s THERMAL_LAMBDA_FEEDBACK note and `thermal_path_c.json`), where
    nothing could read it, check it, or age it. That is the same shape as
    `WORLD_POPULATION`, `SLU_HECTARES` and `REFERENCE_FRAME_POPULATION` — a
    number governing the model while living in a comment.

    THE BLACKBODY VALUE IS NOT THE PLANCK FEEDBACK, and the gap is the point.
    3.761 assumes a single emitting surface at 255 K. The real Planck response
    integrates over the atmospheric temperature profile and is ≈3.2 — the prose
    figure. So this is an UPPER bound on the Planck term, and therefore a
    conservative upper bound on λ itself: it errs in the direction of allowing
    MORE λ than physics does, which is the safe direction for a gate.
    """
    if t_emission <= 0.0:
        raise ValueError(f"t_emission must be > 0 K, got {t_emission}")
    return 4.0 * SIGMA_SB * t_emission ** 3


def lambda_admissibility(
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    t_emission: float = EARTH_EMISSION_TEMPERATURE_K,
) -> dict:
    """
    Is a climate feedback parameter physically admissible?

    Governing inequality:

        λ_total = λ_Planck − (water vapour + lapse rate + albedo + cloud)
        ⇒  λ_total < λ_Planck        whenever net feedbacks are amplifying

    Every assessed feedback except lapse rate is amplifying, and the net is
    robustly amplifying across every generation of assessment. So the Planck
    term is a CEILING on λ, and a λ at or above it would imply net stabilising
    feedbacks stronger than the blackbody response — not a tuning question but a
    physical impossibility.

    WHY IT MATTERS HERE. λ is, in this repo's own words, "THE most leveraged
    parameter after delta_T_lo: every threshold is F/λ, linear in 1/λ". It is
    carried as a chosen value inside an assessed range with no physical anchor
    of any kind. This supplies the one anchor that exists — not to narrow the
    range, which physics cannot do, but to say where the range CANNOT go.

    Returns the bound, the margin, and `implied_net_feedback` — the amplifying
    feedback strength the shipped λ implies, which is the quantity a reader can
    actually sanity-check against the literature.
    """
    bound = planck_feedback(t_emission)
    return {
        "lambda": lam,
        "planck_bound": bound,
        "t_emission_k": t_emission,
        "admissible": lam < bound,
        "ratio_to_planck": lam / bound,
        "implied_net_feedback": bound - lam,
        "note": (
            "λ < λ_Planck is required because net feedbacks are amplifying. The "
            "bound is the BLACKBODY Planck term (3.761 at 255 K); the real "
            "Planck response is ≈3.2, so this ceiling is deliberately loose and "
            "errs toward admitting too much λ rather than too little."
        ),
    }
