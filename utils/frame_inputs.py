"""
frame_inputs — the inputs a frame-aware command runs on, and WHERE EACH CAME FROM.

An institution running a scenario on its own frame needs to know, for every
input, whether the number knows anything about that frame. Each resolved input
carries a label:

    supplied   given on the command line or in a --frame-file
    measured   read from a dataset the repo ships for a declared frame
               (e.g. --frame us: Census ages, MTUS capacity, BEA capital)
    derived    computed from other inputs — `derived_from` names them, including
               any framework default it leans on (as `default:NAME`, e.g. a
               per-head intensity). A derived value prints as "derived" only
               when every root is supplied or measured; "derived (partly from
               defaults)" when the lineage is mixed; "derived (from defaults)"
               when it knows nothing about the frame either
    default    the framework's reference value, not a statement about the frame

Precedence, highest first: a command-line flag, then the --frame-file, then
the built-in --frame's data, then the default. --frame and --frame-file are
exclusive: a frame is one statement.

ε IS NOT IMPUTED FROM PARTIAL DATA. It comes from a flag, from the frame
file's own `epsilon` (a number, or {"low", "high"}), or — for a built-in frame
with readings — from the repo's two instruments
(`labour_epsilon.instrument_comparison`). A frame file with capital but no
reading gets the reference ε, labelled a default: the capital route refuses a
default currency rate, and so does this.

THE FRAME FILE is JSON with any of the keys in `FRAME_FILE_KEYS`; anything else
is refused, as are age shares that do not name every AGE_GROUPS group or do not
sum to 1. `eoh frame show --frame us --format json` writes one to start from.

Shared by `corridor band` and `scenario run`, so the two cannot resolve the
same frame two ways. Presentation layer: imports freely, imported by no
package module.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from hours_eoh.data import (
    A_LAND_CLAIMED_M2,
    AGE_GROUP_RANGES,
    AGE_GROUPS,
    JURISDICTION_FRAMES,
    M2_PER_HECTARE,
    MEASURED_CAPACITY_H_YR,
    REFERENCE_FRAME_POPULATION,
    RETIREMENT_REGISTER_AGE,
    RETIREMENT_YEARS_IN_COLLECTIVE,
    THERMAL_ANTHROPOGENIC_DISSIPATION_W,
    THERMAL_DT_LO,
    WORLD_POPULATION,
)

KINDS = ("supplied", "measured", "derived", "default")

#: The reference ε, used only when nothing measured or supplied exists — and
#: then printed as a default.
EPSILON_REFERENCE = 0.40

#: Built-in frames: the declared jurisdiction (data.JURISDICTION_FRAMES), the
#: Path C collective, and the MTUS country whose latest sample is its capacity.
FRAMES: dict[str, dict[str, str]] = {
    "us": {"jurisdiction": "us_mainland", "path_c": "United States", "mtus": "US"},
}

#: What a --frame-file may state.
FRAME_FILE_KEYS = frozenset({
    "name", "note", "population", "age_fractions", "epsilon", "capital_teh",
    "land_hectares", "adult_capacity_h_yr", "utilization", "trust_balance",
    "retirement_age", "retired_share", "years_in_collective",
    # 2026-10-04: the physical state a constructed (or measured) frame states,
    # and whether its people, rather than the GUF, carry its ecological work.
    "ecosystem_health", "capital_age_ratio", "ecological_carried_by_people",
})


# ---------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------

def label(kind: str, source: str, derived_from: tuple[str, ...] = ()) -> dict:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    return {"kind": kind, "source": source, "derived_from": list(derived_from)}


def effective_kind(labels: dict[str, dict], key: str) -> str:
    """A derived input's kind by its ROOTS: plain "derived" only when every root
    is supplied or measured. `default:NAME` entries are default roots — the
    framework intensities a derivation leans on."""
    lab = labels[key]
    if lab["kind"] != "derived":
        return str(lab["kind"])
    roots: list[str] = []
    stack = list(lab["derived_from"])
    while stack:
        k = stack.pop()
        if k.startswith("default:"):
            roots.append("default")
        elif k not in labels:
            raise KeyError(f"{key} derives from {k!r}, which is not a resolved input")
        elif labels[k]["kind"] == "derived":
            stack.extend(labels[k]["derived_from"])
        else:
            roots.append(labels[k]["kind"])
    if roots and all(r == "default" for r in roots):
        return "derived (from defaults)"
    return "derived (partly from defaults)" if "default" in roots else "derived"


# ---------------------------------------------------------------------------
# the frame file
# ---------------------------------------------------------------------------

def load_frame_file(path: str | Path) -> dict[str, Any]:
    """Read and validate a frame file. Refuses, never patches."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: a frame file is a JSON object")
    unknown = set(data) - FRAME_FILE_KEYS
    if unknown:
        raise SystemExit(f"{path}: unknown keys {sorted(unknown)}; a frame file may "
                         f"state {sorted(FRAME_FILE_KEYS)}")
    for k in ("population", "capital_teh", "land_hectares", "adult_capacity_h_yr"):
        if k in data and not (isinstance(data[k], (int, float)) and data[k] > 0):
            raise SystemExit(f"{path}: {k} must be a positive number")
    for k in ("utilization", "trust_balance", "years_in_collective"):
        if k in data and not (isinstance(data[k], (int, float)) and data[k] >= 0):
            raise SystemExit(f"{path}: {k} must be a non-negative number")
    if "retirement_age" in data and not (isinstance(data["retirement_age"], (int, float))
                                         and data["retirement_age"] > 0):
        raise SystemExit(f"{path}: retirement_age must be a positive number")
    if "retired_share" in data and not (isinstance(data["retired_share"], (int, float))
                                        and 0.0 <= data["retired_share"] <= 1.0):
        raise SystemExit(f"{path}: retired_share must be in [0, 1]")
    for k in ("ecosystem_health", "capital_age_ratio"):
        if k in data and not (isinstance(data[k], (int, float)) and 0.0 <= data[k] <= 1.0):
            raise SystemExit(f"{path}: {k} must be in [0, 1]")
    if "ecological_carried_by_people" in data and not isinstance(
            data["ecological_carried_by_people"], bool):
        raise SystemExit(f"{path}: ecological_carried_by_people must be true or false")
    for k in ("name", "note"):
        if k in data and not isinstance(data[k], str):
            raise SystemExit(f"{path}: {k} must be text")
    if "age_fractions" in data:
        a = data["age_fractions"]
        if not isinstance(a, dict) or set(a) != set(AGE_GROUPS):
            raise SystemExit(f"{path}: age_fractions must name exactly {sorted(AGE_GROUPS)}")
        if any(not isinstance(v, (int, float)) or v < 0 for v in a.values()) or not math.isclose(
                sum(a.values()), 1.0, rel_tol=1e-6):
            raise SystemExit(f"{path}: age_fractions must be non-negative and sum to 1")
    if "epsilon" in data:
        e = data["epsilon"]
        ok = (isinstance(e, (int, float)) and 0.0 <= e <= 1.0) or (
            isinstance(e, dict) and set(e) == {"low", "high"}
            and all(isinstance(e[k], (int, float)) for k in e) and 0.0 <= e["low"] <= e["high"] <= 1.0)
        if not ok:
            raise SystemExit(f"{path}: epsilon must be a number in [0, 1] or "
                             "{\"low\": a, \"high\": b} with 0 ≤ a ≤ b ≤ 1")
    return data


# ---------------------------------------------------------------------------
# arguments
# ---------------------------------------------------------------------------

def add_frame_arguments(p: argparse.ArgumentParser) -> None:
    """The frame flags shared by every frame-aware command."""
    g = p.add_mutually_exclusive_group()
    g.add_argument("--frame", choices=sorted(FRAMES), default=None,
                   help="A built-in frame: inputs read from the datasets the repo "
                        "ships for it (us = contiguous-48 US: Census ages, MTUS "
                        "capacity, both ε instruments, Path C). Flags override it")
    g.add_argument("--frame-file", default=None, dest="frame_file", metavar="PATH",
                   help="YOUR frame, as JSON (keys: " + ", ".join(sorted(FRAME_FILE_KEYS))
                        + "), or a SHIPPED frame by name (`eoh frame shipped` lists "
                        "them). Start from `eoh frame show --frame us --format json`")
    p.add_argument("--ages", choices=["shipped", "census"], default=None,
                   help="Age mix: 'shipped' = AGE_GROUPS fractions, 'census' = US "
                        "Census single-year ages (latest year) grouped to "
                        "AGE_GROUP_RANGES (default: the frame's, else shipped)")
    p.add_argument("--adult-capacity", type=float, default=None, dest="adult_capacity",
                   metavar="H", help="Hours per adult-year of labour (default: the "
                   "frame's MTUS measurement, else the all-frame median)")
    p.add_argument("--retirement-age", type=float, nargs="?", default=None,
                   const=float(RETIREMENT_REGISTER_AGE), dest="retirement_age",
                   metavar="AGE",
                   help="Model RETIREMENT AS A REGISTER EVENT: members past AGE are "
                        "added to the guarantee (a governance choice, off by "
                        f"default; the bare flag uses {RETIREMENT_REGISTER_AGE}). "
                        "Must be within the elderly band")
    p.add_argument("--years-in-collective", type=float, default=None,
                   dest="years_in_collective", metavar="Y",
                   help="Retirees' years in the collective, read through the "
                        "framework's vesting curve (linear, full at "
                        "CONTESTABILITY_VESTING_YEARS); 0 → no retiree claim "
                        f"(default {RETIREMENT_YEARS_IN_COLLECTIVE:g})")
    p.add_argument("--bea-usd-per-teh", type=float, default=None,
                   dest="bea_usd_per_teh", metavar="RATE",
                   help="Read capital from the BEA US inventory at this "
                        "currency-per-TEH rate. US frame only. No default: the "
                        "rate is a judgement (conversion_band() bounds it)")


def frame_flags_given(args: argparse.Namespace) -> list[str]:
    """The frame flags this run set — for refusing them where nothing reads them."""
    names = {"frame": "--frame", "frame_file": "--frame-file", "ages": "--ages",
             "adult_capacity": "--adult-capacity", "bea_usd_per_teh": "--bea-usd-per-teh",
             "retirement_age": "--retirement-age",
             "years_in_collective": "--years-in-collective"}
    return [flag for attr, flag in names.items() if getattr(args, attr, None) is not None]


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------

#: SHIPPED FRAME FILES (2026-10-04, author: "all frames including the USA or
#: from any country or constructed scenarios can be tested"). A frame file is
#: the one intake; these ship with the repo, each GENERATED from the module
#: that owns it (`eoh frame shipped --write`), and a test holds every file to
#: its source. `--frame-file NAME` finds one by name. A constructed frame is
#: fictitious on purpose — some extreme, to test bounds and how the framework
#: handles collapse — and says so in its `note`; its values read "supplied".
SHIPPED_FRAMES_DIR = Path(__file__).resolve().parents[1] / "hours_eoh" / "reference" / "data" / "frames"


def shipped_frame_sources() -> dict[str, Any]:
    """name → the function whose output IS that shipped file."""
    from hours_eoh.indust_no_eco_params import indust_frame
    return {"indust_overbuilt": indust_frame}


def frame_file_path(name_or_path: str) -> Path:
    """A path as given, else a shipped frame by name."""
    p = Path(name_or_path)
    if p.exists():
        return p
    shipped = SHIPPED_FRAMES_DIR / f"{name_or_path}.json"
    if shipped.exists():
        return shipped
    raise SystemExit(f"{name_or_path}: no such file, and no shipped frame by that name "
                     f"(shipped: {', '.join(sorted(shipped_frame_sources()))})")


def write_shipped_frames() -> list[Path]:
    """Regenerate every shipped frame file from its source."""
    SHIPPED_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for name, src in shipped_frame_sources().items():
        path = SHIPPED_FRAMES_DIR / f"{name}.json"
        path.write_text(json.dumps(src(), indent=2) + "\n", encoding="utf-8")
        out.append(path)
    return out


def _frame_file(args: argparse.Namespace) -> dict[str, Any]:
    path = getattr(args, "frame_file", None)
    return load_frame_file(frame_file_path(path)) if path else {}


def _span(r: dict) -> str:
    return (f"{r['low']:.3f}" if r["low"] == r["high"]
            else f"{r['low']:.3f}–{r['high']:.3f}")


def resolve_epsilon(args: argparse.Namespace) -> dict:
    """
    The ε to run at, with its range and label.

    Returns {"value", "low", "high", "margin", "margin_kind", "source", "kind",
    and "instruments" when read from them}. `margin_kind` is "span" when the
    range is a measurement band, "disagreement" when the instruments are
    DIVERGENT (the midpoint is then a reading neither gives), None for a point.
    """
    if getattr(args, "epsilon", None) is not None:
        e = float(args.epsilon)
        return {"value": e, "low": e, "high": e, "margin": 0.0, "margin_kind": None,
                "kind": "supplied", "source": "--epsilon"}
    ff = _frame_file(args)
    if "epsilon" in ff:
        e = ff["epsilon"]
        lo, hi = (float(e), float(e)) if not isinstance(e, dict) else (float(e["low"]), float(e["high"]))
        return {"value": 0.5 * (lo + hi), "low": lo, "high": hi, "margin": 0.5 * (hi - lo),
                "margin_kind": "span" if hi > lo else None,
                "kind": "supplied", "source": f"frame file {args.frame_file}"}
    if getattr(args, "frame", None) == "us":
        from hours_eoh.scenarios.labour_epsilon import instrument_comparison
        rate = getattr(args, "bea_usd_per_teh", None)
        c = instrument_comparison(capital_rates=(rate,) if rate is not None else None)
        lo = min(c["labour"]["low"], c["capital"]["low"])
        hi = max(c["labour"]["high"], c["capital"]["high"])
        divergent = c["verdict"] == "DIVERGENT"
        return {"value": 0.5 * (lo + hi), "low": lo, "high": hi, "margin": 0.5 * (hi - lo),
                "margin_kind": "disagreement" if divergent else "span",
                "kind": "measured",
                "source": (f"US instruments — labour {_span(c['labour'])}, "
                           f"capital {_span(c['capital'])} ({c['verdict']}); "
                           + ("instruments disagree — span shown, midpoint is not a reading"
                              if divergent else "midpoint ± half-span")),
                "instruments": {"labour": [c["labour"]["low"], c["labour"]["high"]],
                                "capital": [c["capital"]["low"], c["capital"]["high"]],
                                "verdict": c["verdict"]}}
    return {"value": EPSILON_REFERENCE, "low": EPSILON_REFERENCE, "high": EPSILON_REFERENCE,
            "margin": None, "margin_kind": None, "kind": "default",
            "source": "EPSILON_REFERENCE — no measured reading for this frame"}


def resolve_inputs(args: argparse.Namespace, epsilon: float) -> tuple[dict[str, Any], dict[str, dict]]:
    """
    Every frame input at `epsilon`: (values, labels). Values are flat so a
    caller passes them straight on; labels say where each came from.

    `capital_teh` is the stock AT `epsilon` when derived (the canonical arc at
    the population), so a caller running at several ε re-resolves per ε; a
    supplied or measured stock is used as given at every ε.
    """
    from hours_eoh.core.eoh_generation import resolve_capital_stock
    from hours_eoh.core.fiscal import resolve_trust_balance
    from hours_eoh.scenarios.feasibility import capacity_weighted_adult_share

    ff = _frame_file(args)
    fname = getattr(args, "frame", None)
    frame = FRAMES.get(fname) if fname else None
    jur = JURISDICTION_FRAMES[frame["jurisdiction"]] if frame else None
    src_ff = f"frame file {getattr(args, 'frame_file', None)}"
    v: dict[str, Any] = {"frame": fname or (ff.get("name") if ff else None)}
    lab: dict[str, dict] = {}

    # population
    if getattr(args, "population", None) is not None:
        v["population"], lab["population"] = float(args.population), label("supplied", "--population")
    elif "population" in ff:
        v["population"], lab["population"] = float(ff["population"]), label("supplied", src_ff)
    elif jur:
        v["population"], lab["population"] = jur["population"], label(
            "measured", f"JURISDICTION_FRAMES['{frame['jurisdiction']}']")  # type: ignore[index]
    else:
        v["population"], lab["population"] = REFERENCE_FRAME_POPULATION, label(
            "default", "REFERENCE_FRAME_POPULATION")
    pop = v["population"]

    # ages
    ages_flag = getattr(args, "ages", None)
    if ages_flag is not None:
        census = ages_flag == "census"
        src, kind = f"--ages {ages_flag}", "supplied"
    elif "age_fractions" in ff:
        census, src, kind = False, src_ff, "supplied"
    else:
        census = bool(frame)
        src, kind = (("Census, latest year, via care_demand.population_shares", "measured")
                     if census else ("AGE_GROUPS fractions", "default"))
    if census:
        from hours_eoh.reference.care_demand import population_shares
        v["age_fractions"] = population_shares(AGE_GROUP_RANGES)
    elif "age_fractions" in ff and ages_flag is None:
        v["age_fractions"] = {g: float(x) for g, x in ff["age_fractions"].items()}
    else:
        v["age_fractions"] = None                 # the shipped mix, as every function defaults
    v["ages"] = "census" if census else ("frame file" if v["age_fractions"] is not None else "shipped")
    lab["age_fractions"] = label("default" if ages_flag == "shipped" else kind, src)

    # adult capacity → labour supply per head
    if getattr(args, "adult_capacity", None) is not None:
        v["adult_capacity_h_yr"], lab["adult_capacity_h_yr"] = float(args.adult_capacity), label(
            "supplied", "--adult-capacity")
    elif "adult_capacity_h_yr" in ff:
        v["adult_capacity_h_yr"], lab["adult_capacity_h_yr"] = float(ff["adult_capacity_h_yr"]), label(
            "supplied", src_ff)
    elif frame and frame.get("mtus"):
        from hours_eoh.reference.mtus_time_use import capacity_frames
        frames = capacity_frames()
        latest = max(s for s in frames if s.startswith(frame["mtus"]))
        v["adult_capacity_h_yr"], lab["adult_capacity_h_yr"] = frames[latest], label(
            "measured", f"MTUS {latest} (mtus_time_use.capacity_frames)")
    else:
        v["adult_capacity_h_yr"], lab["adult_capacity_h_yr"] = MEASURED_CAPACITY_H_YR, label(
            "default", "MEASURED_CAPACITY_H_YR (all-frame median)")
    v["adult_share"] = capacity_weighted_adult_share(v["age_fractions"])
    lab["adult_share"] = label("derived", "capacity_weighted_adult_share", ("age_fractions",))
    v["labor_supply_per_capita"] = v["adult_capacity_h_yr"] * v["adult_share"]
    lab["labor_supply_per_capita"] = label("derived", "adult capacity × adult share",
                                           ("adult_capacity_h_yr", "adult_share"))

    # capital
    rate = getattr(args, "bea_usd_per_teh", None)
    cap_flag = getattr(args, "capital_stock", None)
    if rate is not None:
        if fname != "us" or (jur and pop != jur["population"]):
            raise SystemExit("--bea-usd-per-teh reads the whole-US inventory; it "
                             "needs --frame us at the US population")
        if cap_flag is not None:
            raise SystemExit("--bea-usd-per-teh and --capital-stock both set capital")
        from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory
        v["capital_teh"] = float(epsilon_from_inventory(rate)["capital_teh"])
        lab["capital_teh"] = label("measured", f"BEA US inventory at {rate} $/TEH")
        v["capital_derived"] = False
    elif cap_flag is not None:
        v["capital_teh"], lab["capital_teh"] = float(cap_flag), label("supplied", "--capital-stock")
        v["capital_derived"] = False
    elif "capital_teh" in ff:
        v["capital_teh"], lab["capital_teh"] = float(ff["capital_teh"]), label("supplied", src_ff)
        v["capital_derived"] = False
    else:
        v["capital_teh"] = resolve_capital_stock(None, epsilon, population=pop)
        lab["capital_teh"] = label("derived", "canonical arc at ε and population",
                                   ("epsilon", "population", "default:canonical_physical_state"))
        v["capital_derived"] = True

    # land and residual dissipation (thermal)
    share = pop / WORLD_POPULATION
    if getattr(args, "land_m2", None) is not None:
        v["land_m2"], lab["land_m2"] = float(args.land_m2), label("supplied", "--land-m2")
    elif "land_hectares" in ff:
        v["land_m2"], lab["land_m2"] = float(ff["land_hectares"]) * M2_PER_HECTARE, label(
            "supplied", src_ff)
    elif jur:
        v["land_m2"], lab["land_m2"] = jur["land_hectares"] * M2_PER_HECTARE, label(
            "measured", f"JURISDICTION_FRAMES['{frame['jurisdiction']}']")  # type: ignore[index]
    else:
        v["land_m2"], lab["land_m2"] = A_LAND_CLAIMED_M2 * share, label(
            "derived", "equal per-head share of A_LAND_CLAIMED_M2",
            ("population", "default:equal per-head share"))
    if getattr(args, "phi_other", None) is not None:
        v["phi_other_w"], lab["phi_other_w"] = float(args.phi_other), label("supplied", "--phi-other")
    else:
        v["phi_other_w"], lab["phi_other_w"] = THERMAL_ANTHROPOGENIC_DISSIPATION_W * share, label(
            "derived", "equal per-head share of THERMAL_ANTHROPOGENIC_DISSIPATION_W",
            ("population", "default:equal per-head share"))

    # thermal utilization and threshold
    dt = getattr(args, "delta_t_lo", None)
    dt = THERMAL_DT_LO if dt is None else dt
    v["delta_t_lo"] = dt
    from hours_eoh.research.thermal_path_c import all_collectives_utilization, determinacy_zone
    v["thermal_zone"] = determinacy_zone(dt)["zone"]
    if getattr(args, "utilization", None) is not None:
        v["utilization"], lab["utilization"] = float(args.utilization), label("supplied", "--utilization")
    elif "utilization" in ff:
        v["utilization"], lab["utilization"] = float(ff["utilization"]), label("supplied", src_ff)
    elif frame and frame.get("path_c"):
        rows = {c["name"]: c for c in all_collectives_utilization(delta_t_lo=dt)}
        v["utilization"] = float(rows[frame["path_c"]]["utilization"])
        lab["utilization"] = label("measured", f"Path C '{frame['path_c']}' at ΔT_lo {dt:.2f} K")
    else:
        # A missing input is a ROW, not a silence (2026-10-03): without it the
        # measured thermal ceiling drops out of the band with nothing said.
        v["utilization"] = None
        lab["utilization"] = label(
            "default", "not supplied — the measured thermal ceiling is not run; pass "
                       "--utilization or put `utilization` in the frame file")

    _resolve_retirement(args, ff, src_ff, v, lab)
    _resolve_ecology(ff, src_ff, v, lab)

    # Trust
    tb = getattr(args, "trust_balance", None)
    if tb is not None:
        v["trust_balance"], lab["trust_balance"] = float(tb), label("supplied", "--trust-balance")
    elif "trust_balance" in ff:
        v["trust_balance"], lab["trust_balance"] = float(ff["trust_balance"]), label("supplied", src_ff)
    else:
        v["trust_balance"] = resolve_trust_balance(None, pop)
        lab["trust_balance"] = label("derived", "TRUST_BASE_TEH per head × population",
                                     ("population", "default:TRUST_BASE_TEH"))
        v["trust_derived"] = True
    v.setdefault("trust_derived", False)
    return v, lab


def _resolve_ecology(ff: dict[str, Any], src_ff: str,
                     v: dict[str, Any], lab: dict[str, dict]) -> None:
    """
    The frame's physical state and who carries its ecological work (2026-10-04).

      ecosystem_health, capital_age_ratio — supplied by the frame file, else
          the framework's reference state (defaults);
      ecological_carried_by_people — off by default: under the adopted
          partition the recurring ecological work is the land holder's, through
          the GUF. A frame that declares it ON has its PEOPLE carry it as labour:
          the recurring flow returns to the domain, and the health DEFICIT
          (1 − health, 1 = reference condition) over the frame's land is priced
          as a restoration stock by `restoration_cost.pristine_gap_obligation`
          (high corner, `DEFAULT_AMORTIZATION_YEARS`) — the reading
          `ecological_spike` gives a collapse. Off, nothing is derived: a frame
          at the reference health does not grow a stock nobody declared.
    """
    from hours_eoh.data import CANONICAL_CAPITAL_AGE_BASE, ECOSYSTEM_HEALTH_DEFAULT
    for key, dflt, name in (("ecosystem_health", ECOSYSTEM_HEALTH_DEFAULT, "ECOSYSTEM_HEALTH_DEFAULT"),
                            ("capital_age_ratio", CANONICAL_CAPITAL_AGE_BASE, "CANONICAL_CAPITAL_AGE_BASE")):
        if key in ff:
            v[key], lab[key] = float(ff[key]), label("supplied", src_ff)
        else:
            v[key], lab[key] = dflt, label("default", name)
    carried = bool(ff.get("ecological_carried_by_people", False))
    v["ecological_carried_by_people"] = carried
    lab["ecological_carried_by_people"] = (
        label("supplied", src_ff) if "ecological_carried_by_people" in ff else
        label("default", "off — the GUF carries the recurring ecological work (partition 4e/4f)"))
    v["ecological_response"] = "domain" if carried else "guf"
    if not carried:
        v["restoration_eoh"] = 0.0
        lab["restoration_eoh"] = label("default", "none — the frame does not declare its "
                                       "ecological work carried by its people")
        return
    from hours_eoh.scenarios.restoration_cost import deficit_obligation
    v["restoration_eoh"] = deficit_obligation(v["land_m2"] / M2_PER_HECTARE,
                                              1.0 - v["ecosystem_health"])
    lab["restoration_eoh"] = label(
        "derived", "health deficit over the frame's land, priced by "
        "pristine_gap_obligation and spread over DEFAULT_AMORTIZATION_YEARS",
        ("ecosystem_health", "land_m2", "default:pristine_gap_obligation high corner",
         "default:DEFAULT_AMORTIZATION_YEARS"))


def _resolve_retirement(args: argparse.Namespace, ff: dict[str, Any], src_ff: str,
                        v: dict[str, Any], lab: dict[str, dict]) -> None:
    """
    The retirement register (2026-10-03): OFF unless --retirement-age or the
    frame file asks for it, because whether retirement is a register event is
    the collective's governance choice. When on:

      retired_share — supplied (frame file), else MEASURED from Census
                      single-year ages when the frame has them, else the
                      frame's elderly share × the Census within-band profile
                      (derived, partly from defaults — the move data.py makes
                      for the elderly capacity weight);
      years         — supplied, else RETIREMENT_YEARS_IN_COLLECTIVE (default),
                      read through core.fiscal.vested_fraction.

    An age below the elderly band is refused: retirees here are elderly, and
    the shocks have no way to take people out of working age by age alone.
    """
    from hours_eoh.core.fiscal import vested_fraction
    flag_age = getattr(args, "retirement_age", None)
    on = flag_age is not None or "retirement_age" in ff or "retired_share" in ff
    if not on:
        v.update(retirement_age=None, retired_share=0.0, years_in_collective=None,
                 retiree_vested_fraction=1.0)
        lab["retired_share"] = label("default", "retirement register OFF — a governance "
                                     "choice; pass --retirement-age to model it")
        return
    band_lo, band_hi = AGE_GROUP_RANGES["elderly"]
    if flag_age is not None:
        age, lab["retirement_age"] = float(flag_age), label("supplied", "--retirement-age")
    elif "retirement_age" in ff:
        age, lab["retirement_age"] = float(ff["retirement_age"]), label("supplied", src_ff)
    else:
        age, lab["retirement_age"] = float(RETIREMENT_REGISTER_AGE), label(
            "default", "RETIREMENT_REGISTER_AGE")
    if age < band_lo:
        raise SystemExit(f"retirement age {age:g} is below the elderly band ({band_lo}); "
                         "retirees are modelled within it")
    v["retirement_age"] = age
    if "retired_share" in ff and flag_age is None:
        v["retired_share"], lab["retired_share"] = float(ff["retired_share"]), label(
            "supplied", src_ff)
    else:
        from hours_eoh.reference.care_demand import population_shares
        span = (int(math.ceil(age)), band_hi)
        if v["ages"] == "census":
            v["retired_share"] = population_shares({"r": span})["r"]
            lab["retired_share"] = label(
                "measured", f"Census, latest year, ages {span[0]}+ (population_shares)")
        else:
            ratio = (population_shares({"r": span})["r"]
                     / population_shares({"e": (band_lo, band_hi)})["e"])
            elderly = (AGE_GROUPS["elderly"]["fraction"] if v["age_fractions"] is None
                       else v["age_fractions"]["elderly"])
            v["retired_share"] = elderly * ratio
            lab["retired_share"] = label(
                "derived", f"elderly share × Census within-band share aged {span[0]}+",
                ("age_fractions", "retirement_age", "default:US Census within-band profile"))
    if "years_in_collective" in ff and getattr(args, "years_in_collective", None) is None:
        years, lab["years_in_collective"] = float(ff["years_in_collective"]), label(
            "supplied", src_ff)
    elif getattr(args, "years_in_collective", None) is not None:
        years, lab["years_in_collective"] = float(args.years_in_collective), label(
            "supplied", "--years-in-collective")
    else:
        years, lab["years_in_collective"] = RETIREMENT_YEARS_IN_COLLECTIVE, label(
            "default", "RETIREMENT_YEARS_IN_COLLECTIVE")
    v["years_in_collective"] = years
    v["retiree_vested_fraction"] = vested_fraction(years)
    lab["retiree_vested_fraction"] = label(
        "derived", "vested_fraction (linear, full at CONTESTABILITY_VESTING_YEARS)",
        ("years_in_collective", "default:CONTESTABILITY_VESTING_YEARS"))


def labelled_inputs(values: dict[str, Any], labels: dict[str, dict],
                    epsilon: dict) -> dict[str, dict]:
    """{key: {value, kind, source, derived_from}} — the JSON form, and the
    template a frame file is written from. ε is included with its range."""
    allk = {**labels, "epsilon": {"kind": epsilon["kind"], "source": epsilon["source"],
                                  "derived_from": []}}
    out: dict[str, dict] = {}
    for k, lab in labels.items():
        out[k] = {"value": values.get(k), "kind": effective_kind(allk, k),
                  "source": lab["source"], "derived_from": lab["derived_from"]}
    e = {"value": epsilon["value"], "kind": epsilon["kind"], "source": epsilon["source"],
         "derived_from": []}
    if epsilon["high"] > epsilon["low"]:
        e["range"] = [epsilon["low"], epsilon["high"]]
        e["margin_kind"] = epsilon["margin_kind"]
    out["epsilon"] = e
    return out


def print_inputs(rows: dict[str, dict], epsilon: dict | None, ends: str | None = None,
                 frame: str | None = None, file: Any = None) -> None:
    """
    The Inputs block: ε first — a point, a span with its margin, or a labelled
    DISAGREEMENT — then every other input with its value and kind. `ends` is
    the caller's one-line reading at both ends of the ε range (a verdict, or
    the outcomes), printed under ε.
    """
    import sys as _sys
    from utils.formatters import bold, fmt_float
    stream = file or _sys.stdout

    def say(line: str) -> None:
        stream.write(line + "\n")

    say(bold("Inputs") + "  (kinds: supplied · measured · derived [partly / from "
          "defaults] · default)" + (f"   frame: {frame}" if frame else ""))
    e = epsilon
    if e is None:
        say("  ε: swept by the scenario — not an input")
    elif e["high"] > e["low"]:
        if e.get("margin_kind") == "disagreement":
            say(f"  ε: span [{e['low']:.3f}, {e['high']:.3f}] — run at {e['value']:.3f}, "
                  f"NOT a reading  — {e['kind']}: {e['source']}")
        else:
            say(f"  ε: {e['value']:.3f} ± {e['margin']:.3f}  [{e['low']:.3f}, {e['high']:.3f}]"
                  f"  — {e['kind']}: {e['source']}")
        if ends:
            say(f"     at both ends of the range: {ends}")
    else:
        say(f"  ε: {e['value']:.3f}  — {e['kind']}: {e['source']}")
    width = max([24] + [len(k) for k in rows])
    for k, r in rows.items():
        if k == "epsilon":
            continue
        val = r["value"]
        if isinstance(val, dict):
            shown = ", ".join(f"{g} {x:.3f}" for g, x in val.items())
        elif val is None:
            shown = "shipped AGE_GROUPS mix" if k == "age_fractions" else "—"
        elif isinstance(val, float) and math.isinf(val):
            shown = "∞"
        elif isinstance(val, float) and abs(val) >= 1e6:
            shown = fmt_float(val)
        elif isinstance(val, float) and abs(val) >= 1e3:
            shown = f"{val:,.1f}"
        elif isinstance(val, float):
            shown = f"{val:.4g}"
        else:
            shown = str(val)
        say(f"  {k:{width}s} {shown}  — {r['kind']}: {r['source']}"
              + (f" (from {', '.join(r['derived_from'])})" if r["derived_from"] else ""))


def frame_file_from(rows: dict[str, dict]) -> dict[str, Any]:
    """A frame file that reproduces these inputs — what `frame show --format
    json` writes for an institution to edit. Derived values are left out, so
    the file states only what the frame KNOWS and the rest re-derives."""
    out: dict[str, Any] = {}
    keep = {"population": "population", "age_fractions": "age_fractions",
            "adult_capacity_h_yr": "adult_capacity_h_yr", "capital_teh": "capital_teh",
            "utilization": "utilization", "trust_balance": "trust_balance",
            "retirement_age": "retirement_age", "retired_share": "retired_share",
            "years_in_collective": "years_in_collective",
            "ecosystem_health": "ecosystem_health", "capital_age_ratio": "capital_age_ratio",
            "ecological_carried_by_people": "ecological_carried_by_people"}
    for k, fk in keep.items():
        r = rows.get(k)
        if r and r["kind"] in ("supplied", "measured") and r["value"] is not None:
            # A non-finite U (unbudgeted at the threshold in force) is a reading
            # OF the threshold, not of the frame, and is not valid JSON either:
            # left out, so the frame file stays standard JSON (2026-10-03).
            if isinstance(r["value"], float) and not math.isfinite(r["value"]):
                continue
            out[fk] = r["value"]
    if "land_m2" in rows and rows["land_m2"]["kind"] in ("supplied", "measured"):
        out["land_hectares"] = rows["land_m2"]["value"] / M2_PER_HECTARE
    e = rows.get("epsilon")
    if e and e["kind"] in ("supplied", "measured"):
        out["epsilon"] = ({"low": e["range"][0], "high": e["range"][1]} if "range" in e
                          else e["value"])
    return out
