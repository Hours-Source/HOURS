"""
multiplier — tier multiplier assessment and arc sweep.

  eoh multiplier assess  --epsilon ε --training T --demand D --scarcity S --impact I
                         [--eoh-reduction F --domain-coverage F --resilience F]
                         [--assessors N] [--irr F] [--sortition] [--no-sortition]
                         [--review-epoch Y] [--current-epoch Y]
                         [--format table|json]

  eoh multiplier arc     [--training T] [--demand D] [--scarcity S] [--impact I]
                         [--points N] [--format table|csv|json]

'assess' shows the four-factor breakdown at one ε: each αᵢ coefficient, factor
score, and αᵢ·fᵢ contribution to m(c) = 1 + α₁·T + α₂·D + α₃·S + α₄·I.
Optional governance inputs trigger sortition / IRR / sunset checks.

'arc' sweeps ε across [0, 0.99] at a fixed factor vector, showing how each
coefficient and its contribution shifts across the automation arc.
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.core.multipliers import (
    assess_tier,
    compute_impact_score,
    epoch_alpha_weights,
    tier_multiplier,
    multiplier_band_check,
)
from hours_eoh.data import (
    M_BAND_LOW, M_BAND_HIGH, M_MAX, ALPHA_SCALE,
    GOVERNANCE_MIN_ASSESSORS,
    GOVERNANCE_IRR_WARN_THRESHOLD, GOVERNANCE_IRR_CRIT_THRESHOLD,
)
from utils.formatters import (
    bold, green, yellow, red, dim, fmt_float, fmt_eps, table as fmt_table,
)

_FACTOR_NAMES = ["training", "demand", "scarcity", "impact"]
_FACTOR_SYMBOLS = ["T", "D", "S", "I"]
_ALPHA_LABELS = ["α₁(T)", "α₂(D)", "α₃(S)", "α₄(I)"]


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "multiplier",
        help="Tier multiplier four-factor breakdown and arc sweep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    sub2 = p.add_subparsers(dest="mul_cmd", required=True)

    # ------------------------------------------------------------------ assess
    a = sub2.add_parser(
        "assess",
        help="Four-factor breakdown at a single ε",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Compute m(c) = 1 + α₁·T + α₂·D + α₃·S + α₄·I at the given ε,\n"
            "showing each coefficient and its factor contribution.\n\n"
            "Impact sub-questions (--eoh-reduction, --domain-coverage, --resilience)\n"
            "derive the impact score I(c) if provided; otherwise --impact is used directly."
        ),
    )
    a.add_argument("--epsilon", type=float, default=0.40, metavar="ε",
                   help="Automation level [0, 0.99] (default: 0.40)")
    a.add_argument("--training",  type=float, default=0.50, metavar="T",
                   help="Training requirement ∈ [0,1] (default: 0.50)")
    a.add_argument("--demand",    type=float, default=0.50, metavar="D",
                   help="EOH demand intensity ∈ [0,1] (default: 0.50)")
    a.add_argument("--scarcity",  type=float, default=0.50, metavar="S",
                   help="Practitioner scarcity ∈ [0,1] (default: 0.50)")
    a.add_argument("--impact",    type=float, default=0.50, metavar="I",
                   help="EOH impact score ∈ [0,1] (default: 0.50, overridden by sub-questions)")

    # impact sub-questions
    a.add_argument("--eoh-reduction",   type=float, default=None, dest="eoh_reduction",
                   metavar="F", help="EOH reduction fraction sub-question ∈ [0,1]")
    a.add_argument("--domain-coverage", type=float, default=None, dest="domain_coverage",
                   metavar="F", help="Domain coverage sub-question ∈ [0,1]")
    a.add_argument("--resilience",      type=float, default=None, dest="resilience",
                   metavar="F", help="Resilience contribution sub-question ∈ [0,1]")

    # governance
    a.add_argument("--assessors",     type=int,   default=None, dest="assessors",
                   metavar="N", help=f"Number of assessors (warn if < {GOVERNANCE_MIN_ASSESSORS})")
    a.add_argument("--irr",           type=float, default=None,
                   metavar="F", help="Inter-rater reliability ∈ [0,1]")
    a.add_argument("--sortition",     action="store_true", default=None, dest="sortition",
                   help="Assessors were randomly selected (default: True if not overridden)")
    a.add_argument("--no-sortition",  action="store_false", dest="sortition",
                   help="Assessors were NOT randomly selected (triggers governance warning)")
    a.add_argument("--review-epoch",  type=int, default=None, dest="review_epoch",
                   metavar="Y", help="Year of last assessment (for sunset check)")
    a.add_argument("--current-epoch", type=int, default=None, dest="current_epoch",
                   metavar="Y", help="Current year (for sunset check)")
    a.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    a.set_defaults(func=_assess)

    # ------------------------------------------------------------------ arc
    r = sub2.add_parser(
        "arc",
        help="Alpha coefficient and factor-contribution arc sweep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Sweep ε ∈ [0, 0.99] at a fixed factor vector and show how each\n"
            "αᵢ coefficient and αᵢ·fᵢ contribution shifts across the automation arc."
        ),
    )
    r.add_argument("--training",  type=float, default=0.65, metavar="T",
                   help="Fixed training factor ∈ [0,1] (default: 0.65)")
    r.add_argument("--demand",    type=float, default=0.55, metavar="D",
                   help="Fixed demand factor ∈ [0,1] (default: 0.55)")
    r.add_argument("--scarcity",  type=float, default=0.30, metavar="S",
                   help="Fixed scarcity factor ∈ [0,1] (default: 0.30)")
    r.add_argument("--impact",    type=float, default=0.45, metavar="I",
                   help="Fixed impact factor ∈ [0,1] (default: 0.45)")
    r.add_argument("--points", type=int, default=20, metavar="N",
                   help="Number of ε points (default: 20)")
    r.add_argument("--format", choices=["table", "csv", "json"], default="table", dest="fmt")
    r.set_defaults(func=_arc)

    # ---------------------------------------------------------------- sensitivity
    s = sub2.add_parser(
        "sensitivity",
        help="Robustness of the measured reference multiplier to its CHOSEN constants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Sweep the CHOSEN constants of the measured (O*NET/BLS) reference\n"
            "multiplier and report robustness. PRIMARY metrics are falsifiable\n"
            "(Spearman rank correlation vs the frozen ordering; pairwise-ratio\n"
            "drift). SECONDARY metrics (band verdict, spread) are construction\n"
            "artifacts of the normalization choice — reported, but not evidence.\n"
            "See the multiplier falsifiability pass."
        ),
    )
    s.add_argument("--delta", type=float, default=0.10, metavar="D",
                   help="Weight perturbation magnitude (default: 0.10)")
    s.add_argument("--draws", type=int, default=300, metavar="N",
                   help="Dirichlet Monte-Carlo draws (default: 300)")
    s.add_argument("--seed", type=int, default=0, help="RNG seed (default: 0)")
    s.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    s.set_defaults(func=_sensitivity)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _assess(args: argparse.Namespace) -> None:
    # Derive impact from sub-questions if all three are provided
    impact = args.impact
    impact_derived = False
    if all(v is not None for v in [args.eoh_reduction, args.domain_coverage, args.resilience]):
        impact = compute_impact_score(
            eoh_reduction_fraction=args.eoh_reduction,
            domain_coverage=args.domain_coverage,
            resilience_contribution=args.resilience,
        )
        impact_derived = True

    # Build governance dict
    governance = None
    gov_fields = {
        "assessor_count": args.assessors,
        "irr_score":      args.irr,
        "sortition_flag": args.sortition,
        "review_epoch":   args.review_epoch,
        "current_epoch":  args.current_epoch,
    }
    active = {k: v for k, v in gov_fields.items() if v is not None}
    if active:
        governance = active  # type: ignore[assignment]

    result = assess_tier(
        training=args.training,
        demand=args.demand,
        scarcity=args.scarcity,
        impact=impact,
        epsilon=args.epsilon,
        governance=governance,
    )

    if args.fmt == "json":
        out = dict(result)
        if impact_derived:
            out["impact_derived"] = True
            out["impact_sub_questions"] = {
                "eoh_reduction": args.eoh_reduction,
                "domain_coverage": args.domain_coverage,
                "resilience": args.resilience,
            }
        print(json.dumps(out, indent=2, default=str))
        return

    # -- table output --
    a1, a2, a3, a4 = result["alpha_coefficients"]
    factors = [args.training, args.demand, args.scarcity, impact]
    alphas  = [a1, a2, a3, a4]
    contributions = [a * f for a, f in zip(alphas, factors)]

    # Header
    print(bold(f"Multiplier assessment — ε={fmt_eps(args.epsilon)}"))
    print()

    # Four-factor breakdown table
    factor_rows = []
    for name, sym, alpha, score, contrib in zip(
        _FACTOR_NAMES, _FACTOR_SYMBOLS, alphas, factors, contributions
    ):
        factor_rows.append([
            f"{name} ({sym})",
            f"{score:.3f}",
            f"{alpha:.4f}",
            f"{contrib:.4f}",
        ])
    # Totals row
    factor_rows.append(["─" * 16, "─" * 6, "─" * 7, "─" * 8])
    factor_rows.append([
        "base",
        "",
        "",
        "1.0000",
    ])
    factor_rows.append([
        "m(c) = 1 + Σαᵢfᵢ",
        "",
        f"Σ={sum(alphas):.4f}",
        f"{result['multiplier']:.4f}",
    ])
    print(fmt_table(["factor", "score", "α coeff", "α·f contrib"], factor_rows))

    if impact_derived:
        print()
        print(dim(f"  impact derived from sub-questions: "
                  f"eoh_reduction={args.eoh_reduction:.3f}  "
                  f"domain_coverage={args.domain_coverage:.3f}  "
                  f"resilience={args.resilience:.3f}"))

    # Band check
    print()
    m = result["multiplier"]
    if m < M_BAND_LOW:
        band_label = yellow(f"BELOW BAND [{M_BAND_LOW},{M_BAND_HIGH}]")
    elif m > M_BAND_HIGH:
        band_label = yellow(f"ABOVE BAND [{M_BAND_LOW},{M_BAND_HIGH}]")
    else:
        band_label = green(f"IN BAND [{M_BAND_LOW},{M_BAND_HIGH}]")
    print(f"  m = {bold(f'{m:.4f}')}   {band_label}   cap = {M_MAX}")

    # Governance
    gov_status = result["governance_status"]
    if gov_status == "OK":
        gov_label = green("OK")
    elif gov_status == "WARN":
        gov_label = yellow("WARN")
    else:
        gov_label = red("CRIT")
    print(f"  governance = {gov_label}", end="")
    if result["warnings"]:
        print()
        for w in result["warnings"]:
            print(f"    {yellow('!')} {w}")
    else:
        print()

    if result["sunset_check"]:
        sc = result["sunset_check"]
        print(f"  sunset: {sc['elapsed']} yr elapsed / {sc['interval_years']} yr interval"
              f" — {sc['status']}")


def _arc(args: argparse.Namespace) -> None:
    n = args.points
    T, D, S, I = args.training, args.demand, args.scarcity, args.impact

    rows_data = []
    for i in range(n):
        eps = i / (n - 1) * 0.99 if n > 1 else 0.40
        a1, a2, a3, a4 = epoch_alpha_weights(eps)
        m = tier_multiplier(T, D, S, I, alpha_coefficients=(a1, a2, a3, a4))
        band_pass = M_BAND_LOW <= m <= M_BAND_HIGH
        rows_data.append({
            "epsilon": eps,
            "alpha_train":  a1, "alpha_demand": a2,
            "alpha_scarcity": a3, "alpha_impact": a4,
            "contrib_train":   a1 * T, "contrib_demand":   a2 * D,
            "contrib_scarcity": a3 * S, "contrib_impact":  a4 * I,
            "multiplier": m,
            "in_band": band_pass,
        })

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    if args.fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows_data[0].keys()))
        writer.writeheader()
        writer.writerows(rows_data)
        return

    # table — two sections: coefficients, then contributions
    print(bold(
        f"Multiplier arc — T={T:.2f}  D={D:.2f}  S={S:.2f}  I={I:.2f}"
        f"  [{n} points]"
    ))
    print(dim(f"  m(c) = 1 + α₁·T + α₂·D + α₃·S + α₄·I   "
              f"band=[{M_BAND_LOW},{M_BAND_HIGH}]   cap={M_MAX}"))
    print()

    coeff_rows = []
    for r in rows_data:
        coeff_rows.append([
            fmt_eps(r["epsilon"]),
            f"{r['alpha_train']:.4f}",
            f"{r['alpha_demand']:.4f}",
            f"{r['alpha_scarcity']:.4f}",
            f"{r['alpha_impact']:.4f}",
            f"{r['alpha_train']+r['alpha_demand']+r['alpha_scarcity']+r['alpha_impact']:.4f}",
            (green if r["in_band"] else yellow)(f"{r['multiplier']:.4f}"),
        ])
    print(fmt_table(
        ["ε", "α₁(T)", "α₂(D)", "α₃(S)", "α₄(I)", "Σα", "m(c)"],
        coeff_rows,
    ))

    print()
    print(bold("Factor contributions αᵢ·fᵢ"))
    contrib_rows = []
    for r in rows_data:
        contrib_rows.append([
            fmt_eps(r["epsilon"]),
            f"{r['contrib_train']:.4f}",
            f"{r['contrib_demand']:.4f}",
            f"{r['contrib_scarcity']:.4f}",
            f"{r['contrib_impact']:.4f}",
            f"{r['contrib_train']+r['contrib_demand']+r['contrib_scarcity']+r['contrib_impact']:.4f}",
            (green if r["in_band"] else yellow)(f"{r['multiplier']:.4f}"),
        ])
    print(fmt_table(
        ["ε", "α₁T", "α₂D", "α₃S", "α₄I", "Σ", "m(c)"],
        contrib_rows,
    ))
    print(dim(f"  green = in band [{M_BAND_LOW},{M_BAND_HIGH}]"))


def _sensitivity(args: argparse.Namespace) -> None:
    from hours_eoh.scenarios.multiplier_sensitivity import sensitivity_report

    rep = sensitivity_report(delta=args.delta, n_draws=args.draws, seed=args.seed)

    if args.fmt == "json":
        print(json.dumps(rep, indent=2))
        return

    print(bold("Reference multiplier — sensitivity to CHOSEN constants"))
    print(dim(
        "  measured O*NET/BLS registry (751 occs). PRIMARY = falsifiable "
        "(rank/pairwise);\n  SECONDARY = convention (band/spread) per FALSIFIABILITY.md."
    ))
    base_mean = bold(f"{rep['baseline_weighted_mean']:.4f}")
    print(f"  baseline: weighted mean = {base_mean}"
          f"   spread = {rep['baseline_spread_ratio']:.3f}:1")

    def _sweep_table(title: str, results: list) -> None:
        print()
        print(bold(title))
        rows = []
        for p in results:
            band = green(p["band_verdict"]) if p["band_verdict"] == "IN" else red(p["band_verdict"])
            sp = p["spearman_vs_baseline"]
            sp_s = (green if sp > 0.95 else yellow if sp > 0.85 else red)(f"{sp:.4f}")
            rows.append([
                p["label"], sp_s, f"{p['min_pairwise_ratio_drift']:.3f}",
                f"{p['weighted_mean']:.3f}", band, f"{p['clip_fraction']:.3f}",
            ])
        print(fmt_table(
            ["perturbation", "ρ(rank)", "ratio_drift", "wmean", "band", "clip"],
            rows,
        ))

    _sweep_table("Factor-weight sweep (±delta)", rep["factor_weight_sweep"])
    _sweep_table("Impact sub-domain sweep (±delta)", rep["impact_subdomain_sweep"])
    _sweep_table("ε arc (epoch_factor_weights)", rep["epsilon_arc"])

    mc = rep["monte_carlo"]
    print()
    print(bold(f"Dirichlet Monte-Carlo ({mc['n_draws']} draws, conc={mc['concentration']:g})"))
    print(f"  Spearman  p5={mc['spearman_p5']:.3f}  median={mc['spearman_median']:.3f}"
          f"  min={mc['spearman_min']:.3f}   {dim('(rank ordering — falsifiable)')}")
    print(f"  band pass fraction = {mc['band_pass_fraction']:.2f}   "
          f"ratio drift p95 = {mc['ratio_drift_p95']:.3f}")

    print()
    print(dim("  Not swept from the registry alone:"))
    for item in rep["not_swept"]:
        print(dim(f"    · {item}"))
