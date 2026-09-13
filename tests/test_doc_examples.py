"""
The published examples gate — every code block in README and `docs/` runs.

SPDX-License-Identifier: AGPL-3.0-or-later

WHAT PROMPTED IT (2026-09-12). A review executed every Python block in
`README.md` and `docs/`: **34 of 54 failed.** The first quick-start on the site's
front page raised on its second line, every example on the scenarios how-to page
used keyword names the functions had not accepted for months, and the CLI
reference listed scenario names the CLI rejects. Nothing checked any of it,
because `docs/` is prose to the test suite — and a page a reader copies from is
the one surface where a stale example costs someone else the afternoon.

This is the same move the repo made for provenance, claims and CLI dispatch:
make the published surface executable, then keep it green.

WHAT IT CHECKS
  * **Python blocks** — every ```python block on a page runs, in order, in ONE
    namespace per page, in a subprocess from the repo root. One namespace per
    page because pages are written as a walkthrough: a later block uses the
    `state` an earlier one built, and that is how a reader runs them.
  * **CLI lines** — every `python3 utils/eoh_cli.py …` line in a ```bash block
    PARSES against the real argparse tree. Parsed, not executed: parsing is what
    catches a renamed flag or scenario, and executing `params set` would mutate
    persisted state.

THE TEMPLATE CONVENTION, and why it is ratcheted. A block that is a signature
sketch rather than a runnable example opts out by starting with the line
`# template`. That is an escape hatch, so the count of templates is pinned: a
new one is a visible act in a diff, never a quiet way to turn a failure green.
CLI lines carrying placeholders (`[--opt]`, `<command>`, `NAME`, `KEY`, `PARAM`,
`ε`) are syntax, not examples, and are skipped by pattern — also counted.

WHAT IT CANNOT SEE, stated because a gate that hides its gaps reads as stronger
than it is:
  * **Output.** A block that runs and prints a stale number passes. Sample
    output pasted beside an example is not checked — which is why the pages now
    describe shape rather than quote figures wherever the figure is not the point.
  * **Prose.** A sentence naming a function that no longer exists is not a code
    block. `tests/test_claims_register.py` does not read `docs/` either.
  * **Doc blocks in `docs/parameter_provenance.md`**, which is generated and
    gated by `tests/test_provenance.py` instead.
  * **Runtime of CLI examples**, only their parse.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# CONTRIBUTING.md is published through a snippet include in docs/contributing.md,
# which this scan would otherwise see as one line — so it is read at its source.
PAGES = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"] + sorted(
    p for p in (ROOT / "docs").rglob("*.md")
    if p.name != "parameter_provenance.md"
)

_PY = re.compile(r"^([ \t]*)```python[ \t]*\n(.*?)^\1```", re.S | re.M)
_BASH = re.compile(r"^([ \t]*)```(?:bash|sh|shell)[ \t]*\n(.*?)^\1```", re.S | re.M)
TEMPLATE_MARK = "# template"
# `\[--?` and not `\[`: a bare bracket also matched the JSON literals real
# examples pass (`'[{"label": …}]'`), silently exempting them from the parse.
_CLI_PLACEHOLDER = re.compile(r"\[--?|<|\bNAME\b|\bKEY\b|\bVALUE\b|\bPARAM\b|ε|Δε|V1")

#: Pinned EXACTLY, not as ceilings: a ceiling with slack cannot fire when an
#: example quietly becomes a template (failure mode 9). Changing either is a
#: deliberate, reviewable act — see the docstring.
TEMPLATE_BLOCKS_ALLOWED = 5
CLI_PLACEHOLDER_LINES_ALLOWED = 23


def _dedent(code: str) -> str:
    import textwrap
    return textwrap.dedent(code)


def _python_blocks(page: Path) -> list[str]:
    return [_dedent(m.group(2)) for m in _PY.finditer(page.read_text(encoding="utf-8"))]


def _is_template(block: str) -> bool:
    return block.lstrip().startswith(TEMPLATE_MARK)


def _cli_lines(page: Path) -> list[str]:
    """Logical `eoh_cli.py` command lines, with backslash continuations joined."""
    out: list[str] = []
    for m in _BASH.finditer(page.read_text(encoding="utf-8")):
        joined = re.sub(r"\\\n\s*", " ", _dedent(m.group(2)))
        for line in joined.splitlines():
            line = line.split(" #", 1)[0].strip()
            line = re.split(r"\s[>|]\s", line, maxsplit=1)[0].strip()
            if line.startswith("python3 utils/eoh_cli.py"):
                out.append(line)
    return out


_RUNNER = r"""
import json, sys, traceback
blocks = json.loads(sys.stdin.read())
ns = {"__name__": "__doc_example__"}
for i, code in enumerate(blocks):
    try:
        exec(compile(code, f"<block {i}>", "exec"), ns)
    except BaseException as e:
        print(json.dumps({"block": i, "error": f"{type(e).__name__}: {e}",
                          "first_line": code.strip().splitlines()[0][:80]}))
        sys.exit(1)
print(json.dumps({"ran": len(blocks)}))
"""


def _pages_with_python() -> list[Path]:
    return [p for p in PAGES if any(not _is_template(b) for b in _python_blocks(p))]


@pytest.mark.parametrize(
    "page", _pages_with_python(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_every_python_block_on_the_page_runs(page: Path) -> None:
    runnable = [b for b in _python_blocks(page) if not _is_template(b)]
    r = subprocess.run(
        [sys.executable, "-c", _RUNNER],
        input=json.dumps(runnable), capture_output=True, text=True,
        cwd=ROOT, timeout=600,
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
             "PATH": "/usr/bin:/bin", "MPLBACKEND": "Agg"},
    )
    if r.returncode:
        detail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-800:]
        pytest.fail(
            f"{page.relative_to(ROOT)}: a published example no longer runs — "
            f"{detail}. Fix the example against the real signature (never the "
            f"function to fit the example), or mark a genuine sketch "
            f"`{TEMPLATE_MARK}`."
        )
    # A runner that exits 0 without executing is the false pass this repo has
    # been burned by; the count is the proof the blocks actually ran.
    assert json.loads(r.stdout.strip().splitlines()[-1]) == {"ran": len(runnable)}


#: Signature headings (`### \`fn(a, b)\``) and signature table rows (`| \`fn(a)\` |`).
_HEADING = re.compile(r"^(?:#{2,4} |\| )`(\w+)\(([^)]*)\)`", re.M)


def _api_headings() -> list[tuple[Path, str, list[str]]]:
    out = []
    for page in sorted((ROOT / "docs" / "api").rglob("*.md")):
        for m in _HEADING.finditer(page.read_text(encoding="utf-8")):
            args = [a.strip().split("=")[0].strip("* ") for a in m.group(2).split(",")]
            out.append((page, m.group(1), [a for a in args if a and a != "…"]))
    return out


def test_every_api_signature_heading_names_real_parameters() -> None:
    """
    The API reference's `### \\`fn(a, b)\\`` headings are signatures a reader
    codes against. On 2026-09-12, 95 of them named parameters the function did
    not have — most a `p` argument no function takes. Each heading must name a
    real package function, and every parameter it lists must exist.

    CANNOT SEE: the prose beneath a heading. A paragraph describing a retired
    behaviour under a correct signature passes.
    """
    import ast
    import importlib
    import inspect

    sys.path.insert(0, str(ROOT))
    defs: dict[str, list[str]] = {}
    for p in (ROOT / "hours_eoh").rglob("*.py"):
        mod = "hours_eoh." + ".".join(p.relative_to(ROOT / "hours_eoh").with_suffix("").parts)
        for n in ast.parse(p.read_text(encoding="utf-8")).body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                defs.setdefault(n.name, []).append(mod)

    wrong = []
    for page, name, args in _api_headings():
        mods = defs.get(name)
        if not mods:
            wrong.append(f"{page.relative_to(ROOT)}: {name} does not exist")
            continue
        params = set()
        for mod in mods:
            params |= set(inspect.signature(getattr(importlib.import_module(mod), name)).parameters)
        bad = [a for a in args if a not in params]
        if bad:
            wrong.append(f"{page.relative_to(ROOT)}: {name}({', '.join(bad)}) — not parameters")
    assert not wrong, "\n".join(wrong)


def _all_cli_lines() -> list[tuple[Path, str]]:
    return [(p, line) for p in PAGES for line in _cli_lines(p)]


@pytest.mark.parametrize(
    "page,line",
    [(p, l) for p, l in _all_cli_lines() if not _CLI_PLACEHOLDER.search(l)],
    ids=lambda x: x if isinstance(x, str) else str(x.relative_to(ROOT)),
)
def test_every_cli_example_parses(page: Path, line: str) -> None:
    sys.path.insert(0, str(ROOT))
    from utils.eoh_cli import build_parser

    argv = shlex.split(line)[2:]
    try:
        build_parser().parse_args(argv)
    except SystemExit:
        pytest.fail(
            f"{page.relative_to(ROOT)}: `{line}` is rejected by the CLI. A "
            "renamed flag or scenario in a reference page is a command a reader "
            "copies and watches fail."
        )


class TestTheEscapeHatchesAreRatcheted:
    def test_template_blocks_do_not_grow(self) -> None:
        n = sum(_is_template(b) for p in PAGES for b in _python_blocks(p))
        assert n == TEMPLATE_BLOCKS_ALLOWED, (
            f"{n} blocks are marked `{TEMPLATE_MARK}` against {TEMPLATE_BLOCKS_ALLOWED} "
            "allowed. A template is an example nobody runs; raise the bound "
            "deliberately, with the reason, or make the block runnable."
        )

    def test_placeholder_cli_lines_do_not_grow(self) -> None:
        n = sum(bool(_CLI_PLACEHOLDER.search(l)) for _, l in _all_cli_lines())
        assert n == CLI_PLACEHOLDER_LINES_ALLOWED, (
            f"{n} CLI lines are syntax sketches against "
            f"{CLI_PLACEHOLDER_LINES_ALLOWED} allowed."
        )


class TestTheGateBites:
    """A gate that has never fired is untested (failure mode 12)."""

    def test_a_broken_python_block_fails_the_runner(self) -> None:
        r = subprocess.run(
            [sys.executable, "-c", _RUNNER],
            input=json.dumps(["x = 1", "from hours_eoh.core.eoh_generation "
                              "import total_eoh\ntotal_eoh(no_such_kwarg=1)"]),
            capture_output=True, text=True, cwd=ROOT,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        )
        assert r.returncode == 1
        assert '"block": 1' in r.stdout

    def test_blocks_on_one_page_share_a_namespace(self) -> None:
        r = subprocess.run(
            [sys.executable, "-c", _RUNNER],
            input=json.dumps(["state = 41", "assert state + 1 == 42"]),
            capture_output=True, text=True, cwd=ROOT,
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        )
        assert r.returncode == 0, r.stdout

    def test_a_renamed_scenario_is_rejected(self) -> None:
        sys.path.insert(0, str(ROOT))
        from utils.eoh_cli import build_parser
        with pytest.raises(SystemExit):
            build_parser().parse_args(["scenario", "run", "labor-shock"])

    def test_the_gate_sees_python_blocks_at_all(self) -> None:
        assert sum(len(_python_blocks(p)) for p in PAGES) > 30
        assert len(_all_cli_lines()) > 30
        assert len(_api_headings()) > 100
