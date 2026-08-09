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
            print(bold("Tags"))
            print(table(
                ["tag", "count", "share"],
                [[t, str(n), f"{100.0 * n / tagged:.1f}%"] for t, n in counts.items()],
                indent=2,
            ))
            chosen = counts.get("CHOSEN", 0)
            if chosen:
                print(dim(f"  CHOSEN is the honest debt: {chosen} constants "
                          f"({100.0 * chosen / tagged:.1f}%) await measurement, "
                          f"each naming what would settle it."))

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
    print(green("No scheme violations. Every constant carries a tag and units, "
                "and every CHOSEN constant names its epistemic pointer."))


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
