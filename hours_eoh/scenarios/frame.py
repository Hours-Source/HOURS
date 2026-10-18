"""
Jurisdiction frames — pairing a population with the land it is responsible for.

REPORTING ONLY. No generation function reads this module, and no shipped
number moves. It began on 2026-08-17 as Phase 0 of the GUF restoration-cost
derivation.

THE DEFECT THIS MADE VISIBLE, NOW CLOSED
----------------------------------------
`ECOLOGICAL_BASE_RATE` is the obligation for the WHOLE contiguous US:
765,495,267 ha. The default population across the package is 1,000,000. When
this module was written nothing connected the two, so the code divided the
ecological domain by a millionth of the population that lives on that land.

So the reported ecological SHARE depended on the frame by a factor of the US
population over 1M. `shipped_default_mismatch()` still computes that factor
(339.6 since the mainland's own Census figure, 2026-10-15). The shipped default
was the flattering end of it. As first measured, at 335M:

    shipped pairing (1M people, whole-US land) : 0.0448 %
    honest US pairing (335M people, same land) : 0.000146 %

Identical constants gave both. Neither was a measurement error: the model
answered two different questions, and nobody stated the question.

PHASE 4b CLOSED IT (2026-08-17, `record/ecological.md`). The default now
resolves its ecological area from the population (× LAND_HECTARES_PER_CAPITA).
That is the planetary ratio, so the undeclared default COINCIDES with the
`global` frame. The spread left in `frame_report` is the frames' own land per
person, not a frame nobody chose.

WHY IT STAYS REPORTING-ONLY
---------------------------
The module never changed the anchor. It made the mismatch VISIBLE and lets
every caller state its frame. This is the `personal_floor` /
`land_stewardship` posture: measure it, report it, change nothing, and let the
number argue for itself.

Layer: scenarios/ — imports core/ and data.py, imported by neither.
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    ECOLOGICAL_BASE_RATE,
    FRAME_CONSISTENCY_TOLERANCE,
    JURISDICTION_FRAMES,
    LAND_HECTARES_PER_CAPITA,
    REFERENCE_FRAME_POPULATION,
    US_MAINLAND_HECTARES,
    US_MAINLAND_POPULATION,
)
from hours_eoh.core.eoh_generation import resolve_capital_stock




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
    error, because a collective may hold any ratio. But an UNDECLARED one is
    worth knowing about, because the shipped default was exactly that case
    before Phase 4b.
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
    The mismatch as first shipped: 1M people carrying the whole contiguous US.

    Every package default produced this pairing until Phase 4b (2026-08-17),
    and nobody declared it as a frame. It has its own function because it is
    the finding, not an example. Since Phase 4b the default resolves its land
    from the population, so this is the pairing the fix removed.
    """
    shipped_pop = 1_000_000.0
    shipped = frame_check(shipped_pop, US_MAINLAND_HECTARES)
    honest = frame_check(US_MAINLAND_POPULATION, US_MAINLAND_HECTARES)
    return {
        "shipped_population":        shipped_pop,
        "shipped_hectares_per_capita": shipped["hectares_per_capita"],
        "honest_hectares_per_capita":  honest["hectares_per_capita"],
        "population_mismatch_factor":  US_MAINLAND_POPULATION / shipped_pop,
        "shipped_is_declared_frame":   shipped["consistent"],
        "honest_is_declared_frame":    honest["consistent"],
        "verdict": (
            f"before Phase 4b (2026-08-17) the shipped default divided the whole "
            f"contiguous US ({US_MAINLAND_HECTARES:,.0f} ha) by {shipped_pop:,.0f} "
            f"people, giving {shipped['hectares_per_capita']:,.1f} ha/person "
            f"against the actual {honest['hectares_per_capita']:.3f}. That is a "
            f"factor of {US_MAINLAND_POPULATION / shipped_pop:,.0f}. The "
            f"ecological obligation scales with area while every other domain "
            f"scales with population, so it was the factor that flattered the "
            f"shipped ecological SHARE. The default now resolves "
            f"{LAND_HECTARES_PER_CAPITA:g} ha/person from the population, so "
            f"this pairing is what the fix removed."
        ),
    }


def at_frame(name: str, epsilon: float, **overrides: float) -> dict:
    """
    Run `total_eoh` at a declared frame — population and land area together.

    The implementation guide should point an institution at this function. It
    makes the pairing an explicit argument instead of an accident of two
    unrelated defaults. It forwards any keyword to `total_eoh`, so sims vary
    size and population freely; they cannot vary one silently.
    """
    f = frame_for(name)
    # THE THIRD EXTENSIVE QUANTITY. Land and population are the pairing this
    # module was built for, but CAPITAL_STOCK_DEFAULT is itself declared "at the
    # 1M reference population", so leaving it unscaled models the US with the
    # capital stock of a million people — 5.97 TEH/capita against 2,000. The
    # per-capita capital intensity is what the frame holds fixed, not the
    # absolute stock. Found by the frame-invariance test, which failed at 5.7%
    # while both other domains agreed exactly.
    #
    # AND IT MUST BE THE STOCK AT THIS ε, not the ε=0 base (2026-09-09). Until
    # the capital-path decision this line passed `CAPITAL_STOCK_DEFAULT * scale`
    # and `infrastructure_eoh` then multiplied it by (1 + 2ε) — so the ε growth
    # arrived from the callee. A supplied stock is no longer rescaled, so
    # passing the base alone would freeze every declared frame at subsistence
    # capital while the undeclared default resolved along the arc, and the two
    # would stop agreeing. Resolve the arc's stock at this ε FIRST, then scale
    # it by the frame's population: what the frame holds fixed is the per-capita
    # intensity, at whatever point on the arc it is asked about.
    scale = f["population"] / REFERENCE_FRAME_POPULATION
    kw: dict = {
        "epsilon": epsilon,
        "population": f["population"],
        "ecological_area_hectares": f["land_hectares"],
        "capital_stock": resolve_capital_stock(None, epsilon) * scale,
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

    The table computes every row from the same constants at the same ε. Before
    Phase 4b the ecological SHARE column moved by two orders of magnitude
    across it. Now it moves only by the frames' land per person (about 1.37×,
    2026-10-18), and the undeclared row matches `global`.
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
    # The land the default APPLIES, not the whole-US area it applied before
    # Phase 4b: `total_eoh` resolves an omitted area as population ×
    # LAND_HECTARES_PER_CAPITA (2026-10-18; the row reported the old area).
    shipped_land = 1_000_000.0 * LAND_HECTARES_PER_CAPITA
    rows.append({
        "frame":                "SHIPPED DEFAULT (undeclared)",
        "population":           1_000_000.0,
        "land_hectares":        shipped_land,
        "hectares_per_capita":  shipped_land / 1_000_000.0,
        "ecological_share":     shipped["ecological"] / shipped["total"],
        "ecological_h_per_cap": shipped["ecological"] / 1_000_000.0,
        "personal_h_per_cap":   shipped["personal"] / 1_000_000.0,
        "declared":             False,
    })

    shares = [r["ecological_share"] for r in rows]
    spread = max(shares) / min(shares) if min(shares) > 0 else float("inf")
    land = [r["hectares_per_capita"] for r in rows]

    return {
        "epsilon":       epsilon,
        "rows":          rows,
        "share_spread":  spread,
        "mismatch":      shipped_default_mismatch(),
        "anchor_hours":  ECOLOGICAL_BASE_RATE,
        "verdict": (
            f"the ecological share spans {spread:,.2f}x across frames computed "
            f"from IDENTICAL constants at ε={epsilon}; land per person spans "
            f"{min(land):.3g}–{max(land):.3g} ha. The ecological obligation is "
            f"keyed to area while every other domain scales with population, so "
            f"a frame's share follows its land per person. Declaring the frame "
            f"is what makes the ecological number mean anything; it does not "
            f"make it larger."
        ),
    }
