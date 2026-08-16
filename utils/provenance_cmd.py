"""
provenance — where every constant in ``data.py`` comes from, and what would move it.

The provenance scheme (docs/parameter_provenance.md §"The tag scheme") asks every
constant to declare a tag, its units, and — when the tag is ``CHOSEN`` — the
specific evidence that would take it off ``CHOSEN``. This command reads those
declarations straight from the source and reports them.

Four subcommands:

  check   coverage and every scheme violation, non-zero exit if any. This is the
          same check the test suite runs, so the CLI and pytest cannot disagree
          about what "clean" means.
  csv     the shipped public-audit CSV (stdout, or --write to regenerate the
          file in reference/data/)
  table   the generated markdown table for one reporting block
  doc     regenerate the marked table regions in docs/parameter_provenance.md
"""

from __future__ import annotations

import argparse
import sys

from utils import provenance as pv
from utils.formatters import bold, dim, green, red, table, yellow


def build_parser(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p = sub.add_parser(
        "provenance",
        help="Provenance tags for every data.py constant: coverage, audit CSV, doc tables",
    )
    sub2 = p.add_subparsers(dest="provenance_cmd", required=True)

    chk = sub2.add_parser(
        "check", help="Coverage and scheme violations (exit 1 if any)"
    )
    chk.add_argument(
        "--quiet", action="store_true",
        help="Print only the summary line and any violations",
    )
    chk.set_defaults(func=_check)

    csv_p = sub2.add_parser("csv", help="The public-audit CSV")
    csv_p.add_argument(
        "--write", action="store_true",
        help=f"Regenerate {pv.AUDIT_CSV.name} in reference/data/ instead of printing",
    )
    csv_p.set_defaults(func=_csv)

    tbl = sub2.add_parser("table", help="Generated markdown table for one block")
    tbl.add_argument(
        "block", nargs="?",
        help="Reporting block name; omit to list the blocks that exist",
    )
    tbl.set_defaults(func=_table)

    doc = sub2.add_parser(
        "doc", help="Regenerate the marked table regions in the provenance doc"
    )
    doc.add_argument(
        "--write", action="store_true",
        help="Write the doc in place instead of reporting whether it is current",
    )
    doc.set_defaults(func=_doc)

    shadow = sub2.add_parser(
        "shadow",
        help="Domain constants OUTSIDE data.py — what the coverage figure omits",
    )
    shadow.add_argument(
        "--min-sites", type=int, default=3,
        help="Report a repeated parameter default at this many sites or more",
    )
    shadow.set_defaults(func=_shadow)


def _shadow(args: argparse.Namespace) -> None:
    scanned = pv.load()
    tagged, total = pv.coverage(scanned)
    found = pv.shadow_constants()
    free = [s for s in found if not s.bound]
    aliases = [s for s in found if s.bound]

    print(bold("Shadow constants — declared outside data.py, so untagged"))
    print(
        dim(
            "  `provenance check` reports coverage over data.py. These are domain\n"
            "  constants the same layers read, carrying no tag, no resolves_by, and\n"
            "  appearing in no debt figure. Four known defects came from exactly this."
        )
    )
    by_module: dict[str, list[pv.Shadow]] = {}
    for s in free:
        by_module.setdefault(s.module, []).append(s)
    for module in sorted(by_module, key=lambda m: (-len(by_module[m]), m)):
        print(f"\n  {module}  ({len(by_module[module])})")
        for s in by_module[module]:
            print(f"    :{s.line:<5} {s.name:<44} {s.value}")

    if aliases:
        print(f"\n  {green('Bound to a data.py constant')} — the intended shape:")
        for s in aliases:
            print(f"    {s.module}:{s.line}  {s.name}")

    rows = pv.repeated_default_literals(min_sites=args.min_sites)
    if rows:
        print()
        print(bold("De-facto constants — a literal repeated as the same parameter"))
        print(
            dim(
                "  Nobody declared these, so nothing that looks for constants can see\n"
                "  them; every caller who omits the argument gets one anyway. This is\n"
                "  how `= 1500.0` survived the PERSONAL_EOH_BASE reprice in five\n"
                "  generators at once."
            )
        )
        for name, value, sites in rows:
            files = len({s.split(":", 1)[0] for s in sites})
            print(f"    {name:<26} = {value:<14g} {len(sites):>3} sites, "
                  f"{files:>2} files")

    wider = total + len(free)
    print()
    print(bold("The denominator"))
    print(f"  data.py, tagged and gated      : {tagged}/{total}  "
          f"{green('100.0%')}")
    print(f"  shadow constants, untagged     : {len(free)}")
    print(f"  {'coverage over both':<31}: {tagged}/{wider}  "
          f"{red(f'{tagged / wider:.1%}') if tagged / wider < 0.9 else ''}")
    print(
        dim(
            "\n  The 100% figure is true and narrower than it reads. Lowering the\n"
            "  shadow count means moving those constants into data.py with a tag\n"
            "  block — a migration, not a rename, because each one then has to say\n"
            "  what would settle it. tests/test_provenance.py ratchets the count so\n"
            "  it cannot grow in the meantime."
        )
    )


def _check(args: argparse.Namespace) -> None:
    scanned = pv.load()
    tagged, total = pv.coverage(scanned)
    issues = pv.problems(scanned)

    pct = 100.0 * tagged / total if total else 0.0
    head = f"Provenance coverage: {tagged}/{total} constants tagged ({pct:.1f}%)"
    print(bold(head if issues else green(head)))

    if not args.quiet:
        counts = pv.tag_counts(scanned)
        if counts:
            print()
            print(bold("Tags") + dim("  (every constant, retired ones included)"))
            print(table(
                ["tag", "count", "share"],
                [[t, str(n), f"{100.0 * n / tagged:.1f}%"] for t, n in counts.items()],
                indent=2,
            ))

        d = pv.debt_summary(scanned)
        if d.total:
            def row(label: str, n: int, meaning: str) -> list[str]:
                return [label, str(n), f"{d.share(n):.1f}%", meaning]

            print()
            print(bold("Where the model stands")
                  + dim("  (live constants only — a retired value governs nothing)"))
            print(table(
                ["", "count", "share", "what it means"],
                [
                    row("grounded", d.grounded,
                        "structural, measured, derived, or a stated convention"),
                    row("bounded", d.bounded,
                        "picked inside a measured band — the band is the evidence"),
                    row("placeholder", d.placeholder,
                        "no measurement behind it at all — THE DEBT"),
                    row("normative", d.normative,
                        "a decision; no dataset retires it"),
                    row("instance", d.instance,
                        "YOU supply it — your jurisdiction, not our measurement"),
                    row("retired", d.retired,
                        "superseded; governs no current output"),
                ],
                indent=2,
            ))
            print(dim(f"  Debt = bounded + placeholder = {d.debt} "
                      f"({d.share(d.debt):.1f}%) of {d.total}, over {d.live} live "
                      f"constants. The {d.normative} normative constants are NOT "
                      "debt — they are commitments, and counting them as "
                      "unmeasured would be a category error."))
            if d.instance:
                print(dim(f"  The {d.instance} instance constants are not this "
                          "framework's debt either, but their SHIPPED defaults "
                          "are not evidence: every canonical result here was "
                          "produced at them. See the `default:` field."))
            if d.err_directions:
                dirs = ", ".join(f"{k} {v}" for k, v in d.err_directions.items())
                print(dim(f"  Bounded picks err: {dirs}"))

        blocks = scanned.blocks()
        if blocks:
            print()
            print(bold("Blocks"))
            print(table(
                ["block", "constants"],
                [[b, str(len(scanned.in_block(b)))] for b in blocks],
                indent=2,
            ))

    if issues:
        print()
        print(red(bold(f"{len(issues)} scheme violation(s):")))
        for issue in issues:
            print(f"  ● {issue}")
        sys.exit(1)

    print()
    print(green(
        "No scheme violations. Every constant carries a tag and units; every "
        "bounded value states its band and which way it errs; every placeholder "
        "names what would settle it; every normative constant names its decider "
        "without pretending a dataset could; every instance constant names both "
        "what you supply and what the shipped default is; and every retired one "
        "points at a replacement that exists."
    ))


def _csv(args: argparse.Namespace) -> None:
    scanned = pv.load()
    text = pv.audit_csv(scanned)
    if not args.write:
        sys.stdout.write(text)
        return
    current = (
        pv.AUDIT_CSV.read_text(encoding="utf-8") if pv.AUDIT_CSV.exists() else ""
    )
    pv.AUDIT_CSV.write_text(text, encoding="utf-8")
    verb = "unchanged" if current == text else "updated"
    print(f"{pv.AUDIT_CSV.relative_to(pv.AUDIT_CSV.parents[4])}: {verb} "
          f"({len(scanned.records)} rows)")


def _table(args: argparse.Namespace) -> None:
    scanned = pv.load()
    if not args.block:
        print(bold("Reporting blocks in data.py"))
        print(table(
            ["block", "constants"],
            [[b, str(len(scanned.in_block(b)))] for b in scanned.blocks()],
            indent=2,
        ))
        return
    rows = scanned.in_block(args.block)
    if not rows:
        print(red(f"No block named {args.block!r}. Known blocks: "
                  + ", ".join(scanned.blocks())))
        sys.exit(1)
    print(pv.doc_table(rows))


def _doc(args: argparse.Namespace) -> None:
    scanned = pv.load()
    current = pv.PROVENANCE_DOC.read_text(encoding="utf-8")
    rendered = pv.render_doc(scanned, current)

    markers = pv.doc_markers(current)
    missing = [b for b in scanned.blocks() if b not in markers]
    unknown = [b for b in markers if b not in scanned.blocks()]

    if missing:
        print(yellow(f"blocks with no table marker in the doc: {', '.join(missing)}"))
    if unknown:
        print(red(f"table markers naming no block in data.py: {', '.join(unknown)}"))

    if rendered == current:
        print(green(f"{pv.PROVENANCE_DOC.name}: tables are current "
                    f"({len(markers)} generated region(s))."))
        return

    if args.write:
        pv.PROVENANCE_DOC.write_text(rendered, encoding="utf-8")
        print(f"{pv.PROVENANCE_DOC.name}: regenerated {len(markers)} table region(s).")
    else:
        print(red(f"{pv.PROVENANCE_DOC.name}: tables are STALE. "
                  "Run 'eoh provenance doc --write'."))
        sys.exit(1)
