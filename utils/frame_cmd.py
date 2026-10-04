"""
frame — show the inputs a frame resolves to, and write a frame file to start from.

  eoh frame show [--frame us | --frame-file PATH|NAME] [overrides] [--format table|json|labels]
  eoh frame shipped [--write]      the shipped frame files (constructed scenarios among them)

`table` prints every input with its kind (supplied · measured · derived ·
default). `json` writes a FRAME FILE: only what the frame states (supplied and
measured values) — derived values re-derive from it — so an institution can
take the US file, replace what it has measured for itself, and pass it back as
`--frame-file` to `corridor band` or `scenario run`. `labels` writes every
input with its label, for audit.
"""

from __future__ import annotations

import argparse
import json

from utils.frame_inputs import (
    add_frame_arguments, frame_file_from, labelled_inputs, print_inputs,
    resolve_epsilon, resolve_inputs,
)


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("frame", help="Resolve a frame's inputs; write a frame file")
    sub2 = p.add_subparsers(dest="frame_cmd", required=True)
    show = sub2.add_parser("show", help="Every input a frame resolves to, labelled")
    add_frame_arguments(show)
    show.add_argument("--epsilon", type=float, default=None, metavar="ε")
    show.add_argument("--population", type=float, default=None)
    show.add_argument("--capital-stock", type=float, default=None, dest="capital_stock",
                      metavar="TEH")
    show.add_argument("--trust-balance", type=float, default=None, dest="trust_balance")
    show.add_argument("--format", choices=["table", "json", "labels"], default="table",
                      dest="fmt")
    show.set_defaults(func=_show)
    sh = sub2.add_parser("shipped", help="List the shipped frame files; --write regenerates them")
    sh.add_argument("--write", action="store_true",
                    help="Regenerate every shipped frame from the module that owns it")
    sh.set_defaults(func=_shipped)


def _shipped(args: argparse.Namespace) -> None:
    from utils.frame_inputs import SHIPPED_FRAMES_DIR, shipped_frame_sources, write_shipped_frames
    if args.write:
        for p in write_shipped_frames():
            print(f"wrote {p.relative_to(SHIPPED_FRAMES_DIR.parents[3])}")
        return
    for name, src in shipped_frame_sources().items():
        body = src()
        print(f"{name}  — {body.get('note', '')}")
        print(f"    run: --frame-file {name}")


def rows_for(args: argparse.Namespace) -> tuple[dict, dict]:
    """(labelled inputs, ε reading) — what every frame-aware command resolves."""
    eps = resolve_epsilon(args)
    v, lab = resolve_inputs(args, eps["value"])
    return labelled_inputs(v, lab, eps), eps


def _show(args: argparse.Namespace) -> None:
    rows, eps = rows_for(args)
    if args.fmt == "json":
        print(json.dumps(frame_file_from(rows), indent=2))
    elif args.fmt == "labels":
        print(json.dumps(rows, indent=2, default=str))
    else:
        print_inputs(rows, eps, frame=args.frame or args.frame_file)
