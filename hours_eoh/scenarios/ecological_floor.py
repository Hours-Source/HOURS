"""
Ecological domain balance — how far off is the anchor, and what would settle it?

THE DEFECT. `ECOLOGICAL_BASE_RATE` is documented as a RELATIVE anchor — it "does
not represent an absolute ecosystem-specific count" — but `total_eoh()` sums it
with absolute counts and then divides the result into ε. At defaults the
ecological domain is **under 0.1% of total EOH**, so it cannot move ε, and the
planetary thermal obligation it carries books at roughly one part in a thousand
of the ledger. Every result that depends on the ecological domain's SHARE is
conditioned on a number that was never meant to carry a level.

WHAT THIS MODULE DOES NOT DO. It does not fix the constant. No stewardship-hours
census exists in this repo — there is no measured hours-per-hectare figure
anywhere — and picking one to make the share look reasonable is precisely the
fitted-residual error the personal floor was built to refuse. A number chosen to
produce a target share would afterwards be indistinguishable from a measured one.

WHAT IT DOES INSTEAD — INVERT THE QUESTION. Rather than asking "what is the
ecological obligation?", which the data cannot answer, it asks:

    What stewardship intensity, in labour-hours per hectare per year, would the
    ecological domain have to carry for it to be X% of total EOH?

That is answerable exactly, from quantities the model already has. It converts an
unbounded "we don't know" into a falsifiable number: any future census of agency
FTEs per hectare either clears the required figure or it does not. Same move as
`research/epsilon_inverse.capital_for_epsilon` (sweep the economy, not the score)
and `scenarios/food_conservation.uncounted_headroom` (price the missing sectors
and see what closing the gap would demand).

THE READING AT DEFAULTS. The anchor implies a stewardship intensity of roughly
**0.3 h/ha·yr** — about eighteen minutes per hectare per year, all biomes, all
condition classes, including cropland. Reaching even a 5% share of total EOH
requires roughly **two orders of magnitude** more. So the "low by 2–3 orders"
hypothesis in `data.py` is not merely plausible; it is what the arithmetic
requires, and the shortfall is now quantified rather than asserted.

Reference: reconciliation §9 (domain balance); the infrastructure floor's
determinacy result (doctrine spread 1.000, scenarios/infrastructure_floor.py).
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import ecological_statutory_floor, total_eoh
from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.data import ECOLOGICAL_BASE_RATE, LAND_HECTARES_PER_CAPITA

#: The 1M reference population the whole repo quotes at, and `total_eoh`'s own
#: default. Named here rather than repeated as a literal at four call sites.
REFERENCE_POPULATION: float = 1_000_000.0

#: Shares of total EOH to invert for. 5% is the point at which the domain could
#: plausibly move ε at all; 10% and 25% bracket "comparable to infrastructure"
#: and "co-equal with the other non-personal domains".
DEFAULT_TARGET_SHARES: tuple[float, ...] = (0.01, 0.05, 0.10, 0.25)


def _eoh_at(epsilon: float, population: float) -> dict:
    """Total EOH on the canonical arc, mapped the way `arc` maps it.

    The keyword mapping is explicit and not `**state` because
    `canonical_physical_state` uses different key names, and because
    `knowledge_complexity` (the corpus size) and `knowledge_base` (the base RATE)
    are one keyword apart — the pair that produced the Block K-IV under-reporting
    bug for the whole life of the `arc` command.
    """
    state = canonical_physical_state(epsilon)
    return total_eoh(
        capital_stock=state["capital_stock_teh"],
        capital_age_ratio=state["capital_age_ratio"],
        ecosystem_health=state["ecosystem_health"],
        monitoring_capability=state["monitoring_capability"],
        age_distribution=state["age_distribution"],
        knowledge_complexity=state["knowledge_base_size"],
        knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        population=population,
    )


def implied_stewardship_intensity(
    epsilon: float = 0.40,
    population: float = REFERENCE_POPULATION,
    hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
) -> dict:
    """
    What the shipped anchor implies, per hectare of stewarded land.

        intensity = ecological_eoh / (population · hectares_per_capita)

    units: labour-hours per hectare per year. This is the number a stewardship
    census would have to reproduce for `ECOLOGICAL_BASE_RATE` to be right.
    """
    eoh = _eoh_at(epsilon, population)

    hectares = population * hectares_per_capita
    eco = eoh["ecological"]

    return {
        "epsilon": epsilon,
        "ecological_eoh": eco,
        "total_eoh": eoh["total"],
        "ecological_share": eco / eoh["total"] if eoh["total"] > 0.0 else 0.0,
        "ecological_h_per_capita": eco / population if population > 0.0 else 0.0,
        "hectares_total": hectares,
        "hours_per_hectare_year": eco / hectares if hectares > 0.0 else 0.0,
    }


def required_stewardship_intensity(
    target_share: float,
    epsilon: float = 0.40,
    population: float = REFERENCE_POPULATION,
    hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
) -> dict:
    """
    The inversion: hours per hectare per year for ecological to be `target_share`.

    Governing equation. Raising the ecological term raises the total too, so the
    share is not linear in it. Holding the other three domains fixed at R:

        share = E / (R + E)   ⇒   E = share · R / (1 − share)

    and the intensity is E over stewarded hectares. `target_share` must be < 1;
    at share → 1 the required obligation diverges, which is the correct behaviour
    (ecological cannot be the whole obligation while the other domains persist).

    units: labour-hours per hectare per year.
    """
    if not 0.0 <= target_share < 1.0:
        raise ValueError(f"target_share must be in [0, 1), got {target_share}")

    eoh = _eoh_at(epsilon, population)

    rest = eoh["total"] - eoh["ecological"]
    required_eoh = target_share * rest / (1.0 - target_share)

    hectares = population * hectares_per_capita
    current = implied_stewardship_intensity(epsilon, population, hectares_per_capita)
    required_intensity = required_eoh / hectares if hectares > 0.0 else 0.0
    current_intensity = current["hours_per_hectare_year"]

    return {
        "target_share": target_share,
        "epsilon": epsilon,
        "required_ecological_eoh": required_eoh,
        "required_h_per_capita": (
            required_eoh / population if population > 0.0 else 0.0
        ),
        "required_hours_per_hectare_year": required_intensity,
        "current_hours_per_hectare_year": current_intensity,
        "shortfall_factor": (
            required_intensity / current_intensity if current_intensity > 0.0 else 0.0
        ),
    }


def domain_balance_report(
    epsilon: float = 0.40,
    population: float = REFERENCE_POPULATION,
    hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
    target_shares: tuple[float, ...] = DEFAULT_TARGET_SHARES,
) -> dict:
    """
    The full reading: where the anchor sits, and what each target share demands.

    Returns the current intensity, one row per target share, and a verdict stating
    the order of magnitude involved. Reports; changes nothing.
    """
    current = implied_stewardship_intensity(epsilon, population, hectares_per_capita)
    rows = [
        required_stewardship_intensity(s, epsilon, population, hectares_per_capita)
        for s in target_shares
    ]

    five = next((r for r in rows if r["target_share"] == 0.05), rows[-1])
    factor = five["shortfall_factor"]
    orders = f"{factor:.0f}×" if factor < 1000 else f"{factor:.2e}×"

    verdict = (
        f"the shipped anchor implies {current['hours_per_hectare_year']:.2f} "
        f"h/ha·yr of stewardship across ALL land — cropland, forest and "
        f"wilderness alike — and the ecological domain is "
        f"{current['ecological_share'] * 100:.2f}% of total EOH. Reaching a "
        f"{five['target_share'] * 100:.0f}% share needs "
        f"{five['required_hours_per_hectare_year']:.1f} h/ha·yr, a factor of "
        f"{orders}. Nothing in this repo measures stewardship hours, so this "
        f"does not settle the level — it states what a census would have to "
        f"find for the anchor to be right, and how far that is from where it "
        f"currently sits."
    )

    return {
        "epsilon": epsilon,
        "hectares_per_capita": hectares_per_capita,
        "ecological_base_rate": ECOLOGICAL_BASE_RATE,
        "current": current,
        "requirements": rows,
        "verdict": verdict,
    }


def floor_from_census(land_census: list[dict], population: float = REFERENCE_POPULATION) -> dict:
    """
    Run a real land census through the currency-free floor and compare it.

    The intake path. When a stewardship-hours census exists — agency FTEs per
    hectare, or the GUF parcel inventory × measured crew-hours — this is where it
    enters, and the comparison against the anchor is the falsification.

    Unpriced parcels are EXCLUDED, not costed at zero, so `coverage` must be read
    before `floor_h_per_capita` is compared to anything.
    """
    floor = ecological_statutory_floor(land_census)
    anchor = implied_stewardship_intensity(population=population)

    return {
        "floor_hours": floor["floor_hours"],
        "floor_h_per_capita": (
            floor["floor_hours"] / population if population > 0.0 else 0.0
        ),
        "coverage": floor["coverage"],
        "mean_hours_per_hectare": floor["mean_hours_per_hectare"],
        "unpriced": floor["unpriced"],
        "anchor_h_per_capita": anchor["ecological_h_per_capita"],
        "anchor_hours_per_hectare": anchor["hours_per_hectare_year"],
        "ratio_to_anchor": (
            floor["mean_hours_per_hectare"] / anchor["hours_per_hectare_year"]
            if anchor["hours_per_hectare_year"] > 0.0
            else 0.0
        ),
    }
