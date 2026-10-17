"""The `record/` index, kept honest.

The status log was split by subject area on 2026-09-03, when CLAUDE.md had reached
304.5k characters against a 150k context limit
([record](record/verification.md#the-record-split)). State and evidence now route by
area under `record/`. The recurring failure modes stay in CLAUDE.md, because they do not
belong to an area.

WHAT THIS GUARDS:

  * The index globs the directory from disk. A hand-kept index falls behind
    the directory it indexes (the `unused_innocuous_names` failure).
  * A README row may not call an area migrated while its file is a stub, or the
    reverse. Either direction sends a reader to the wrong place.
  * Every cross-area link must resolve. An entry is filed once and linked from
    other areas, so a dangling `#slug` sends a reader nowhere.
  * The LIVE SURFACE has a budget, and history has none. History is the
    evidence that stops a defect being rediscovered; what degrades as it grows
    is NAVIGABILITY, which `utils/record_index.py` answers with a generated
    index, not a deletion.

STATED GAPS. This does not check that an area file's *content* belongs to its area, or
that every entry left in CLAUDE.md has an area to go to; the migration is manual. It
checks links INTO `record/`, not links out of it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORD_DIR = REPO_ROOT / "record"
README = RECORD_DIR / "README.md"

#: The marker a not-yet-migrated stub carries. Kept as a constant so the stub
#: template and this gate cannot drift apart.
STUB_MARKER = "## MIGRATION STATUS — not yet migrated"


def _area_files() -> list[pathlib.Path]:
    return sorted(p for p in RECORD_DIR.glob("*.md") if p.name != "README.md")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _migration_rows() -> dict[str, str]:
    """`{filename: migrated cell}` from the README's area table."""
    rows: dict[str, str] = {}
    for line in _readme().splitlines():
        m = re.match(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|.*\|\s*(.+?)\s*\|$", line)
        if m:
            rows[m.group(2)] = m.group(3).strip()
    return rows


class TestTheIndexMatchesTheDirectory:

    def test_the_directory_is_not_empty(self) -> None:
        """A gate over an empty directory passes and guards nothing."""
        assert len(_area_files()) >= 2

    def test_the_readme_exists_and_is_the_index(self) -> None:
        assert README.is_file()
        assert "## The areas" in _readme()

    @pytest.mark.parametrize("path", _area_files(), ids=lambda p: p.name)
    def test_every_area_file_is_linked_from_the_readme(
        self, path: pathlib.Path
    ) -> None:
        assert f"]({path.name})" in _readme(), (
            f"record/{path.name} exists but nothing links to it from "
            "record/README.md. A file the index does not name is a file "
            "nobody opens."
        )

    def test_every_linked_file_exists(self) -> None:
        missing = [name for name in _migration_rows()
                   if not (RECORD_DIR / name).is_file()]
        assert not missing, (
            f"record/README.md links to files that do not exist: {missing}"
        )


class TestTheMigrationStatusIsTrue:
    """The README row and the file are two accounts of one status, so the test holds
    them equal. `psi` once reported one value while another was applied.
    """

    @pytest.mark.parametrize("path", _area_files(), ids=lambda p: p.name)
    def test_a_stub_is_not_advertised_as_migrated(
        self, path: pathlib.Path
    ) -> None:
        cell = _migration_rows().get(path.name)
        assert cell is not None, f"record/{path.name} has no row in the README table"
        is_stub = STUB_MARKER in path.read_text(encoding="utf-8")
        claims_migrated = "yes" in cell.lower()
        assert is_stub != claims_migrated, (
            f"record/{path.name}: README says migrated={cell!r} but the file "
            f"{'IS' if is_stub else 'is NOT'} a stub. Update whichever is wrong "
            "— a reader sent to a stub, or told to look in CLAUDE.md for "
            "content that has already moved, loses either way."
        )

    def test_a_migrated_file_carries_the_sections_the_readme_promises(self) -> None:
        for path in _area_files():
            if STUB_MARKER in (text := path.read_text(encoding="utf-8")):
                continue
            for heading in ("## Live state", "## Open", "## History"):
                assert heading in text, (
                    f"record/{path.name} is marked migrated but has no "
                    f"{heading!r} section. The README states this shape; a file "
                    "that does not follow it makes the convention advisory."
                )


class TestTheClaimsRegisterStillSeesTheRecord:
    """The split is safe only while the claims register reads both homes. If it stopped,
    the claims that moved to `record/` would go unchecked while every test passed.
    """

    def test_the_register_corpus_includes_the_record_directory(self) -> None:
        from tests.test_claims_register import _text
        text = _text()
        for path in _area_files():
            head = path.read_text(encoding="utf-8").splitlines()[0]
            assert head in text, (
                f"tests/test_claims_register._text() does not include "
                f"record/{path.name}. Claims that moved there are unchecked."
            )


def _slug(heading: str) -> str:
    """GitHub-style anchor slug for a markdown heading."""
    out = "".join(c for c in heading.lower() if c.isalnum() or c in " -_")
    return "-".join(out.split())


def _targets(path: pathlib.Path) -> set[str]:
    """Anchor ids a file offers: explicit `<a id=...>` plus heading slugs."""
    text = path.read_text(encoding="utf-8")
    ids = set(re.findall(r'<a id="([^"]+)"></a>', text))
    ids |= {_slug(m.group(1))
            for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.M)}
    return ids


def _links_into_record() -> list[tuple[pathlib.Path, pathlib.Path, str]]:
    """`(source, target file, fragment)` for every markdown link into `record/`.

    Same-file links (`](#frag)`) are matched explicitly. The first version matched only
    `](file.md#frag)`, and breaking an anchor that four same-file links used left the
    gate GREEN (mode 12).
    """
    sources = [*RECORD_DIR.glob("*.md"), REPO_ROOT / "CLAUDE.md"]
    found = []
    for src in sources:
        text = src.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\((?:record/)?([a-z_]*\.md)?(#[^)\s]+)?\)", text):
            name, frag = m.group(1), (m.group(2) or "")[1:]
            if name is None and not frag:
                continue
            target = RECORD_DIR / name if name else src
            if target.parent != RECORD_DIR or not target.is_file():
                continue
            found.append((src, target, frag))
    return found


class TestEveryCrossLinkResolves:
    """An entry is filed once and linked, never duplicated: two copies are two accounts
    of one quantity (`psi` against `psi_applied`). Linking is safe only while the links
    resolve.
    """

    def test_there_are_cross_links_to_check(self) -> None:
        """A link checker over zero links passes and guards nothing."""
        fragments = [f for _, _, f in _links_into_record() if f]
        assert len(fragments) >= 5

    def test_same_file_links_are_covered(self) -> None:
        """The case the first version of this gate could not see at all."""
        same = [f for src, tgt, f in _links_into_record() if src == tgt and f]
        assert len(same) >= 4

    def test_every_fragment_resolves(self) -> None:
        bad = []
        for src, tgt, frag in _links_into_record():
            if frag and frag not in _targets(tgt):
                bad.append(f"{src.name} -> {tgt.name}#{frag}")
        assert not bad, (
            "these cross-links point at anchors that do not exist:\n  "
            + "\n  ".join(bad)
            + "\n\nAdd the anchor, or fix the link. A dangling pointer sends a "
              "reader nowhere and looks exactly like a working one."
        )


class TestAnEntryIsFiledOnce:

    def test_no_entry_headline_appears_in_two_area_files(self) -> None:
        """
        Duplication is the alternative to cross-linking and it is the wrong one:
        the two copies drift, and nothing says which is canonical.
        """
        seen: dict[str, str] = {}
        clashes = []
        for path in _area_files():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("**") and len(line) > 40:
                    key = line[:60]
                    if key in seen and seen[key] != path.name:
                        clashes.append(f"{key!r}: {seen[key]} and {path.name}")
                    seen[key] = path.name
        assert not clashes, "entries duplicated across area files:\n  " + "\n  ".join(clashes)


class TestEveryFileCanBeNavigated:
    """Each area file carries an index that lets a reader jump to one entry instead of
    scanning the history. The index is GENERATED, so it cannot drift from what it
    indexes.
    """

    def test_every_migrated_file_carries_a_current_index(self) -> None:
        from utils.record_index import is_stub, rebuilt
        stale = []
        for path in _area_files():
            text = path.read_text(encoding="utf-8")
            if is_stub(text):
                continue
            if rebuilt(text) != text:
                stale.append(path.name)
        assert not stale, (
            f"these record/ indexes are stale: {stale}. "
            "Run `python3 utils/record_index.py --write`. Never hand-edit the "
            "generated region — the marker says so, and a hand-edited index is "
            "a second account of the entries it lists (corpus F-008)."
        )

    def test_the_index_lists_every_entry_and_invents_none(self) -> None:
        from utils.record_index import entries, is_stub, split_history
        import re
        for path in _area_files():
            text = path.read_text(encoding="utf-8")
            if is_stub(text):
                continue
            _, hist = split_history(text)
            anchors = {a for a, _ in entries(hist)}
            listed = set(re.findall(r"^\| \[([a-z0-9-]+)\]\(#", hist, re.M))
            assert listed == anchors, (
                f"record/{path.name}: index lists {sorted(listed - anchors)} "
                f"that do not exist and omits {sorted(anchors - listed)}"
            )


class TestTheLiveSurfaceStaysASummary:
    """The budget catches an area file that grows a SECOND history inside its summary,
    which is how CLAUDE.md reached 304,500 characters. When set, it codified a
    regularity and bound nothing. On 2026-10-17 several files sit within 100 characters
    of it ([record](record/verification.md#ste-docstrings)).
    """

    def test_each_live_surface_is_within_budget(self) -> None:
        from utils.record_index import LIVE_SURFACE_MAX, report
        over = [(n, live) for n, live, _, _ in report() if live > LIVE_SURFACE_MAX]
        assert not over, (
            f"live surface over budget ({LIVE_SURFACE_MAX:,} chars): {over}. "
            "Move the detail into an entry under `## History` and leave a "
            "pointer — do not raise the budget to fit a summary that has "
            "become a second history."
        )

    def test_the_budget_is_not_vacuous(self) -> None:
        """A budget far above every real value would pass while guarding nothing."""
        from utils.record_index import LIVE_SURFACE_MAX, report
        largest = max(live for _, live, _, _ in report())
        assert LIVE_SURFACE_MAX < largest * 2, (
            "the live-surface budget has drifted far above what any file uses; "
            "it now passes unconditionally"
        )

    def test_the_size_report_covers_every_migrated_file(self) -> None:
        """
        REPORTING ONLY — there is deliberately no history ceiling. This asserts
        the reporter itself cannot go silently blind, which is the failure a
        report with nothing checking it always has.
        """
        from utils.record_index import is_stub, report
        migrated = {p.name for p in _area_files()
                    if not is_stub(p.read_text(encoding="utf-8"))}
        assert {n for n, _, _, _ in report()} == migrated
        assert all(h > 0 and e > 0 for _, _, h, e in report())


class TestTheFailureModesCiteTheCorpus:
    """CLAUDE.md's failure modes and the portable corpus hold the same knowledge at two
    altitudes, joined by the `*(corpus F-0NN)*` markers. This test checks the FORM only.
    Resolution needs the corpus, which lives outside every repo, so
    `~/.claude/corpus/check.py` checks that half.

    The first insertion of the markers went in malformed for modes 10–13, and nothing
    noticed: counting them found 13, parsing them found 9
    ([record](record/verification.md#the-record-split)).
    """

    _MODE = re.compile(r"^\s*(\d+)\. \*\*(.+?)\*\* \*\(corpus ((?:F-\d{3}(?:, )?)+)\)\*",
                       re.M | re.S)

    def _section(self) -> str:
        text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        return text[text.index("## Recurring failure modes"):
                    text.index("---\n\n## Current status")]

    def test_every_numbered_mode_carries_a_wellformed_citation(self) -> None:
        sec = self._section()
        numbered = {m.group(1) for m in re.finditer(r"^\s*(\d+)\. \*\*", sec, re.M)}
        cited = {m.group(1) for m in self._MODE.finditer(sec)}
        assert numbered == cited, (
            f"modes with no PARSEABLE corpus citation: {sorted(numbered - cited, key=int)}. "
            "A marker that is present but malformed counts as present to a grep "
            "and as absent to a reader — check the placement, not the count."
        )

    def test_there_are_modes_to_check(self) -> None:
        assert len(self._MODE.findall(self._section())) >= 13
