"""
ste_check — how much of each file's docstring prose meets the ASD-STE100 writing rules.

The default (CLAUDE.md § Docstrings): about 80% of each file's docstring sentences
meet the STE rules. Test docstrings are short STE. This tool measures that share.
It REPORTS. It does not gate, because §3 forbids tests of wording.

What it measures, per sentence:
  * LENGTH. At most 25 words (STE rule 6.1 for descriptive text). The 20-word
    limit for instructions is not separated: a docstring is almost all description.
  * PASSIVE VOICE. A form of "be" followed by a past participle (STE rule 3.1).

What it CANNOT measure (its gaps):
  * WORD CHOICE. The STE dictionary is licensed and is not shipped here, so
    approved and unapproved words are not checked. A sentence of 12 unapproved
    words passes.
  * MEANING. A short sentence that dropped a "because" or a direction passes.
    Read the diff; this tool cannot see a claim.
  * The passive check is a pattern. It misses irregular participles it does not
    list, and it flags an adjective after "is" when the word ends in -ed.

What it skips: code and equation lines, table rows, section headers
("Args:", "Returns:"), and `name: type` lines in a returns block. Technical
names (EOH, TEH, ε, `code`) count as one word each, as STE technical names do.

    python3 utils/ste_check.py tests/test_fiscal.py            # one file
    python3 utils/ste_check.py tests/ --below 80               # files under 80%
    python3 utils/ste_check.py tests/test_fiscal.py --sentences # each failing sentence
    python3 utils/ste_check.py hours_eoh/ --format json

"long" counts docstrings over SHORT_DOC_WORDS words of prose — the measure for
test docstrings, which should be short.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

#: STE rule 6.1: descriptive sentences have 25 words or fewer.
MAX_WORDS = 25
#: The share of compliant sentences the CLAUDE.md default asks of a file.
TARGET_SHARE = 0.80
#: A test docstring longer than this is not "short STE" (one to three sentences).
SHORT_DOC_WORDS = 60

_BE = r"(?:is|are|was|were|be|been|being|isn't|aren't|wasn't|weren't)"
_IRREGULAR = (
    "built|chosen|done|drawn|given|held|kept|known|made|met|paid|read|run|"
    "seen|set|shown|sold|taken|told|written|found|left|put|brought|thought|"
    "won|lost|cut|split|spent|bound|fed|led|sent|shut|struck|meant|understood"
)
_PASSIVE = re.compile(
    rf"\b{_BE}\s+(?:\w+ly\s+|not\s+|also\s+|then\s+|now\s+|still\s+|never\s+)*"
    rf"(?!(?:red|need|seed|bed|shed|hundred|indeed|speed|embed)\b)(?:\w+ed|{_IRREGULAR})\b",
    re.IGNORECASE)

_HEADER = re.compile(r"^\s*(Args|Arguments|Returns|Raises|Yields|Example|Examples|"
                     r"Note|Notes|Reference|References|See also|Parameters|"
                     r"Attributes|Governing equations?|Usage)\s*:?\s*$", re.IGNORECASE)
_ABBREV = re.compile(r"\b(e\.g|i\.e|etc|vs|cf|approx|Eq|Fig|No|St|Dr|al)\.", re.IGNORECASE)


def _is_code_line(line: str) -> bool:
    """A line of code, an equation or a table, not prose."""
    s = line.strip()
    if not s:
        return False
    if s.startswith(("|", "│", "+--", ">>>", "...", "```", "$ ", "python3 ", "eoh ")):
        return True
    if re.match(r"^[\"'{}\[\]()]", s) or s.endswith(("{", "}", "},", "],")):
        return True
    if re.match(r"^[\w.\[\]\"'()]+\s*[=≈≤≥<>]\s*\S", s) and not re.search(r"\s[a-z]{3,}\s[a-z]{3,}\s[a-z]{3,}", s):
        return True
    letters = sum(c.isalpha() for c in s)
    return letters < 0.5 * len(s)


def _prose(doc: str) -> str:
    """The docstring's prose: code, equation and table lines and headers removed."""
    keep: list[str] = []
    in_fence = False
    for line in doc.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or _HEADER.match(line) or _is_code_line(line):
            keep.append("")
            continue
        keep.append(line.strip())
    return "\n".join(keep)


def sentences(doc: str) -> list[str]:
    """The prose sentences of one docstring."""
    text = _prose(doc)
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        # Protect inline code, abbreviations and decimals from the splitter.
        protected = re.sub(r"`[^`]*`", lambda m: m.group(0).replace(".", "\0"), para)
        protected = _ABBREV.sub(lambda m: m.group(0).replace(".", "\0"), protected)
        protected = re.sub(r"(\d)\.(\d)", "\\1\0\\2", protected)
        for part in re.split(r"(?<=[.!?;:])\s+(?=[A-Z(*`\"'])|(?<=[.!?])\s+(?=-\s)|\s+[-*•]\s+", protected):
            part = part.replace("\0", ".").strip(" -*•")
            if len(words(part)) >= 3:
                out.append(part)
    return out


def words(sentence: str) -> list[str]:
    """Words, with inline code counted as one technical name."""
    s = re.sub(r"`[^`]*`", " CODE ", sentence)
    return re.findall(r"[^\W_][\w'’.\-/×→≈%]*", s)


def judge(sentence: str) -> list[str]:
    """The STE rules this sentence breaks; empty when it meets them."""
    faults = []
    n = len(words(sentence))
    if n > MAX_WORDS:
        faults.append(f"{n} words")
    if _PASSIVE.search(re.sub(r"`[^`]*`", "CODE", sentence)):
        faults.append("passive")
    return faults


def docstrings(path: Path) -> list[tuple[int, str, str]]:
    """(line, qualified name, docstring) for every docstring in a file."""
    tree = ast.parse(path.read_text())
    out: list[tuple[int, str, str]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                doc = ast.get_docstring(child)
                if doc:
                    out.append((child.lineno, name, doc))
                visit(child, name + ".")

    mod = ast.get_docstring(tree)
    if mod:
        out.append((1, "<module>", mod))
    visit(tree, "")
    return out


def check_file(path: Path) -> dict[str, Any]:
    """Every sentence in a file's docstrings, judged."""
    total = ok = 0
    failing: list[dict[str, Any]] = []
    long_docs: list[dict[str, Any]] = []
    for line, name, doc in docstrings(path):
        n = len(words(_prose(doc)))
        if n > SHORT_DOC_WORDS:
            long_docs.append({"line": line, "name": name, "words": n})
        for s in sentences(doc):
            total += 1
            faults = judge(s)
            if faults:
                failing.append({"line": line, "name": name, "faults": faults, "sentence": s})
            else:
                ok += 1
    return {
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        "sentences": total,
        "compliant": ok,
        "share": ok / total if total else 1.0,
        "failing": failing,
        "long_docstrings": long_docs,
    }


def _files(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = Path(t).resolve()
        out.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return [p for p in out if "__pycache__" not in p.parts]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="files or directories")
    ap.add_argument("--below", type=float, default=None,
                    help="list only files under this share, in percent")
    ap.add_argument("--sentences", action="store_true", help="print each failing sentence")
    ap.add_argument("--format", choices=("table", "json"), default="table")
    args = ap.parse_args(argv)

    results = [check_file(p) for p in _files(args.targets)]
    if args.below is not None:
        results = [r for r in results if r["share"] * 100 < args.below]
    results.sort(key=lambda r: r["share"])

    if args.format == "json":
        json.dump(results if args.sentences else
                  [{**{k: v for k, v in r.items() if k not in ("failing", "long_docstrings")},
                    "long_docstrings": len(r["long_docstrings"])} for r in results],
                  sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    tot = sum(r["sentences"] for r in results)
    n_long = sum(len(r["long_docstrings"]) for r in results)
    ok = sum(r["compliant"] for r in results)
    for r in results:
        print(f"{r['share']*100:6.1f}%  {r['compliant']:5d}/{r['sentences']:<5d}  "
              f"long {len(r['long_docstrings']):3d}  {r['file']}")
        if args.sentences:
            for f in r["failing"]:
                print(f"    L{f['line']} {f['name']}: [{', '.join(f['faults'])}] {f['sentence']}")
    if tot:
        print(f"\n{ok}/{tot} sentences meet the rules ({ok/tot*100:.1f}%) across "
              f"{len(results)} file(s); target {TARGET_SHARE*100:.0f}% per file. "
              f"{n_long} docstring(s) over {SHORT_DOC_WORDS} words. "
              "Word choice is not checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
