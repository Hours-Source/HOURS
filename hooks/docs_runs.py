"""MkDocs hook: run the CLI commands a page displays, at build time.

A page marks a run with one line:

    <!-- eoh-run: scenario run collective --frame us -->

The hook runs `python3 utils/eoh_cli.py --no-color <args>` from the repo root and
puts the command and its output in a text block in place of the marker. The
output is NOT committed. A copy of a run in `docs/` is a set of derived figures
in prose, and they go stale with the next constant that moves (failure mode 13).
So each published run is the run of the commit the site was built from.

A command that exits non-zero or prints nothing raises, and so does a marker
that is not on its own line. So does a local `params set` baseline
(`utils/_params_state.json`): the CLI applies it to every command, so a local
build would publish runs under someone's overrides. Run `params reset` first. The strict docs build in CI then fails instead of
publishing a page with a broken run.

**Its gap:** pytest does not run this hook. The CI docs job
(`mkdocs build --strict`) is its gate, and `tests/test_doc_examples.py` does not
see the marker's arguments.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKER = re.compile(r"^<!-- eoh-run: (.+?) -->[ \t]*$", re.M)


PARAMS_STATE = os.path.join(REPO_ROOT, "utils", "_params_state.json")


def run_block(args: str) -> str:
    """Run one CLI command and return it with its output as a text block."""
    if os.path.exists(PARAMS_STATE):
        raise RuntimeError(
            "docs_runs: utils/_params_state.json holds a local `params set` "
            "baseline, which the CLI applies to every run. Run "
            "`python3 utils/eoh_cli.py params reset` before building the docs.")
    cmd = [sys.executable, "utils/eoh_cli.py", "--no-color", *shlex.split(args)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                          timeout=300)
    out = proc.stdout.rstrip()
    if proc.returncode != 0 or not out:
        raise RuntimeError(
            f"docs_runs: `eoh {args}` exited {proc.returncode} with "
            f"{len(out)} characters of output:\n{proc.stderr[-2000:]}")
    return f"```text\n$ eoh {args}\n{out}\n```"


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    """Replace each run marker on the page with the run's output."""
    out = MARKER.sub(lambda m: run_block(m.group(1)), markdown)
    if "<!-- eoh-run:" in out:
        # A marker not on its own line would stay an invisible HTML comment.
        raise RuntimeError("docs_runs: an `eoh-run` marker is not on its own line "
                           f"in {getattr(getattr(page, 'file', None), 'src_path', page)}")
    return out
