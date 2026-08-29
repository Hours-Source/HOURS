"""
Jurisdiction frames — pairing a population with the land it is responsible for.

REPORTING ONLY. Nothing here is consumed by a generation function and no
shipped number moves. Introduced 2026-08-17 as Phase 0 of the GUF
restoration-cost derivation (notes/guf-restoration-derivation.md).

THE DEFECT THIS MAKES VISIBLE
-----------------------------
`ECOLOGICAL_BASE_RATE` is the obligation for the WHOLE contiguous US —
765,495,267 ha — while the default population across the package is 1,000,000.
Nothing in the code connects the two, so the ecological domain is divided by a
millionth of the population that lives on the land it is keyed to.

The consequence is that the reported ecological SHARE is frame-dependent by a
factor of 335, and the shipped default is the flattering end of it:

    shipped pairing (1M people, whole-US land) : 0.0448 %
    honest US pairing (335M people, same land) : 0.000146 %

Both are computed from identical constants. Neither is a measurement error —
the model was asked two different questions and the question was never stated.

WHY THIS IS REPORTING-ONLY AND NOT A FIX
----------------------------------------
Making the default frame consistent would move the ecological anchor by 335x,
which is a calibration change requiring author sign-off (CLAUDE.md §3). The
honest interim position is to make the mismatch VISIBLE and let every caller
state its frame, rather than to silently pick the other end of a 335x range.

This is the `personal_floor` / `land_stewardship` posture: measure it, report
it, change nothing, and let the number argue for itself.

Layer: scenarios/ — imports core/ and data.py, imported by neither.
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    ECOLOGICAL_BASE_RATE,
    FRAME_CONSISTENCY_TOLERANCE,
    JURISDICTION_FRAMES,
    REFERENCE_FRAME_POPULATION,
    US_MAINLAND_HECTARES,
    US_REFERENCE_POPULATION,
)




def frame_for(name: str) -> dict[str, float]:
    """
    The declared (population, land_hectares) pairing for a named jurisdiction.

    Raises KeyError with the available names rather than returning a default,
    because silently substituting a frame is the failure this module exists to
    surface.
    """
    if name not in JURISDICTION_FRAMES:
        raise KeyError(
            f"unknown frame {name!r}; declared frames are "
            f"{sorted(JURISDICTION_FRAMES)}"
        )
    return dict(JURISDICTION_FRAMES[name])


def hectares_per_capita(population: float, land_hectares: float) -> float:
    """Land per person — the quantity that decides whether a pairing is coherent."""
    if population <= 0.0:
        raise ValueError(f"population must be > 0, got {population}")
    return land_hectares / population


def frame_check(
    population: float,
    land_hectares: float = US_MAINLAND_HECTARES,
) -> dict:
    """
    Is this population/area pairing coherent, and which declared frame is it?

    Governing comparison:

        ha_per_capita   = land_hectares / population
        mismatch_factor = ha_per_capita / (nearest declared frame's ha_per_capita)

    Returns the nearest declared frame and whether the pairing sits within
    FRAME_CONSISTENCY_TOLERANCE of it. A pairing that matches nothing is not an
    error — a collective may hold any ratio — but an UNDECLARED one is worth
    knowing about, because the shipped default is exactly that case.
    """
    hpc = hectares_per_capita(population, land_hectares)

    nearest, nearest_ratio = None, None
    for name, f in JURISDICTION_FRAMES.items():
        f_hpc = f["land_hectares"] / f["population"]
        ratio = hpc / f_hpc
        if nearest_ratio is None or abs(ratio - 1.0) < abs(nearest_ratio - 1.0):
            nearest, nearest_ratio = name, ratio

    assert nearest is not None and nearest_ratio is not None
    consistent = abs(nearest_ratio - 1.0) <= FRAME_CONSISTENCY_TOLERANCE
    return {
        "population":          population,
        "land_hectares":       land_hectares,
        "hectares_per_capita": hpc,
        "nearest_frame":       nearest,
        "ratio_to_nearest":    nearest_ratio,
        "consistent":          consistent,
    }


def shipped_default_mismatch() -> dict:
    """
    The mismatch as shipped: 1M people carrying the whole contiguous US.

    This is the specific pairing every package default produces, and it is not
    a frame anyone declared. Reported as its own function because it is the
    finding, not an example.
    """
    shipped_pop = 1_000_000.0
    shipped = frame_check(shipped_pop, US_MAINLAND_HECTARES)
    honest = frame_check(US_REFERENCE_POPULATION, US_MAINLAND_HECTARES)
    return {
        "shipped_population":        shipped_pop,
        "shipped_hectares_per_capita": shipped["hectares_per_capita"],
        "honest_hectares_per_capita":  honest["hectares_per_capita"],
        "population_mismatch_factor":  US_REFERENCE_POPULATION / shipped_pop,
        "shipped_is_declared_frame":   shipped["consistent"],
        "honest_is_declared_frame":    honest["consistent"],
        "verdict": (
            f"the shipped default divides the whole contiguous US "
            f"({US_MAINLAND_HECTARES:,.0f} ha) by {shipped_pop:,.0f} people, giving "
            f"{shipped['hectares_per_capita']:,.1f} ha/person against the actual "
            f"{honest['hectares_per_capita']:.3f}. That is a factor of "
            f"{US_REFERENCE_POPULATION / shipped_pop:,.0f}, and because the "
            f"ecological obligation does not scale with population while every "
            f"other domain does, it is the factor by which the shipped "
            f"ecological SHARE is flattered. No number here is wrong; the frame "
            f"was never stated."
        ),
    }


def at_frame(name: str, epsilon: float, **overrides: float) -> dict:
    """
    Run `total_eoh` at a declared frame — population and land area together.

    This is the function the implementation guide should point an institution
    at: it makes the pairing an explicit argument instead of an accident of two
    unrelated defaults. Any keyword is forwarded to `total_eoh`, so sims vary
    size and population freely; what they cannot do is vary one silently.
    """
    f = frame_for(name)
    # THE THIRD EXTENSIVE QUANTITY. Land and population are the pairing this
    # module was built for, but CAPITAL_STOCK_DEFAULT is itself declared "at the
    # 1M reference population", so leaving it unscaled models the US with the
    # capital stock of a million people — 5.97 TEH/capita against 2,000. The
    # per-capita capital intensity is what the frame holds fixed, not the
    # absolute stock. Found by the frame-invariance test, which failed at 5.7%
    # while both other domains agreed exactly.
    scale = f["population"] / REFERENCE_FRAME_POPULATION
    kw: dict = {
        "epsilon": epsilon,
        "population": f["population"],
        "ecological_area_hectares": f["land_hectares"],
        "capital_stock": CAPITAL_STOCK_DEFAULT * scale,
    }
    # An explicit override wins over the frame — including the ecological scale,
    # so a caller can hold land fixed while sweeping population and see the
    # share move for the reason this module exists to show.
    kw.update(overrides)
    if "ecological_base" in overrides:
        kw.pop("ecological_area_hectares", None)

    # As in scenarios/ecological_floor: this module reports what an UNDECLARED
    # frame costs the ecological SHARE, which is only a live quantity under the
    # pre-partition policy. Phases 4e/4f empty the domain by default, and a
    # share of zero is frame-invariant for the wrong reason.
    kw.setdefault("ecological_standing_response", "domain")
    kw.setdefault("ecological_health_response", "domain")
    d = total_eoh(**kw)
    pop = float(kw["population"])
    return {
        "frame":                  name,
        "epsilon":                epsilon,
        "population":             pop,
        "land_hectares":          f["land_hectares"],
        "hectares_per_capita":    f["land_hectares"] / pop,
        "total_eoh":              d["total"],
        "ecological_eoh":         d["ecological"],
        "ecological_share":       d["ecological"] / d["total"],
        "ecological_h_per_capita": d["ecological"] / pop,
        "personal_h_per_capita":  d["personal"] / pop,
    }


def frame_report(epsilon: float = 0.40) -> dict:
    """
    Every declared frame side by side, plus the undeclared shipped pairing.

    The point of the table is that the ecological SHARE column moves by two
    orders of magnitude across rows that are all computed from the same
    constants at the same ε.
    """
    rows = []
    for name in JURISDICTION_FRAMES:
        r = at_frame(name, epsilon)
        rows.append({
            "frame":                name,
            "population":           r["population"],
            "land_hectares":        r["land_hectares"],
            "hectares_per_capita":  r["hectares_per_capita"],
            "ecological_share":     r["ecological_share"],
            "ecological_h_per_cap": r["ecological_h_per_capita"],
            "personal_h_per_cap":   r["personal_h_per_capita"],
            "declared":             True,
        })

    # The shipped pairing, which is not a declared frame.
    # Same policy as `at_frame` above, for the same reason: the undeclared row
    # exists to be COMPARED with the declared ones, so both sides must be
    # evaluated where the ecological share is a live quantity.
    shipped = total_eoh(epsilon=epsilon, population=1_000_000.0,
                        ecological_standing_response="domain",
                        ecological_health_response="domain")
    rows.append({
        "frame":                "SHIPPED DEFAULT (undeclared)",
        "population":           1_000_000.0,
        "land_hectares":        US_MAINLAND_HECTARES,
        "hectares_per_capita":  US_MAINLAND_HECTARES / 1_000_000.0,
        "ecological_share":     shipped["ecological"] / shipped["total"],
        "ecological_h_per_cap": shipped["ecological"] / 1_000_000.0,
        "personal_h_per_cap":   shipped["personal"] / 1_000_000.0,
        "declared":             False,
    })

    shares = [r["ecological_share"] for r in rows]
    spread = max(shares) / min(shares) if min(shares) > 0 else float("inf")

    return {
        "epsilon":       epsilon,
        "rows":          rows,
        "share_spread":  spread,
        "mismatch":      shipped_default_mismatch(),
        "anchor_hours":  ECOLOGICAL_BASE_RATE,
        "verdict": (
            f"the ecological share spans {spread:,.0f}x across frames computed "
            f"from IDENTICAL constants at ε={epsilon}. The spread is not "
            f"uncertainty about the world — it is the model being asked an "
            f"unstated question, because ECOLOGICAL_BASE_RATE is keyed to a "
            f"fixed area while every other domain scales with population. "
            f"Declaring the frame is what makes the ecological number mean "
            f"anything; it does not make it larger."
        ),
    }
