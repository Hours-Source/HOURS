"""
Provenance scanner for ``hours_eoh/data.py``.

Every module-level constant in ``data.py`` carries an inline provenance tag block
stating where its value comes from and what would change it. This module reads
those blocks, checks them against the scheme's own rules, and renders them as the
shipped audit CSV and as the generated tables in
``docs/parameter_provenance.md``.

The tag scheme is defined in ``docs/parameter_provenance.md`` §"The tag scheme":

    physics    a structural claim about how entropy works
    measured   read from an external empirical source
    derived    computed from measured inputs by a stated formula
    CHOSEN     set by judgement, not yet backed by measurement

plus two working sub-labels, ``derived-then-FROZEN`` (a derived value pinned at a
reference epoch so it stays comparable across data vintages) and ``convention``
(a stated denominator, not a claim about the world).

``tier`` (A–D) is a *confidence sub-qualifier*, not a rival scheme: the thermal
block already writes "measured (Tier A)". It is valid only on ``measured`` and
``CHOSEN`` — a ``physics`` claim is not more or less well-sourced, it is
structural or it is wrong.

Inline format
-------------

A tag block is a run of comment lines at column 0, immediately above the
constant, opened by ``# tag:``::

    # tag: CHOSEN | units: h/yr per working-age-equivalent
    # resolves_by: BLS American Time Use Survey, annual averages by activity
    #   code — household activities, caring for household members, health
    #   self-care.
    PERSONAL_EOH_BASE: float = 1000.0

The opening line carries ``|``-separated ``key: value`` pairs. Subsequent lines
open a new field (``resolves_by:``, ``units:``, ``form:``, ``tier:``,
``note:``) or continue the previous one when indented.

``family:`` takes a glob and covers the following *run* of constants matching
it, so a table of siblings shares one block::

    # tag: CHOSEN | units: fraction | family: GUF_LVI_W_*
    # form: derived — the four weights are constrained to sum to 1.0
    #   (NLSA Eq. 3); the split between them is not.
    # resolves_by: hedonic regression of parcel transaction values on the four
    #   sub-indices for the jurisdiction being modelled.
    GUF_LVI_W_CENTRALITY:      float = 0.35
    GUF_LVI_W_TRANSIT:         float = 0.30

The run ends at the first constant that does not match the glob.

``# provenance-block: <name>`` sets the reporting section for the constants that
follow, until the next directive. It is what the doc's table markers select on.

Tags are read from the *source text* — they are comments, so they do not survive
import. Values are read from the *imported module*, so computed constants
(``ALPHA_SCALE = M_MAX - 1.0``) report what they actually evaluate to rather than
their expression.
"""

from __future__ import annotations

import csv
import fnmatch
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --- the scheme -------------------------------------------------------------

#: The four tags. Anything else is a scheme violation, not a new category.
TAGS: frozenset[str] = frozenset({"physics", "measured", "derived", "CHOSEN"})

#: Declared working sub-labels (docs/parameter_provenance.md §"The tag scheme").
SUB_LABELS: frozenset[str] = frozenset({"derived-then-FROZEN", "convention"})

VALID_TAGS: frozenset[str] = TAGS | SUB_LABELS

#: Confidence sub-qualifier, valid only where a source can be more or less good.
TIERS: frozenset[str] = frozenset({"A", "B", "C", "D"})
TIER_ELIGIBLE_TAGS: frozenset[str] = frozenset({"measured", "CHOSEN"})

#: Tags whose whole point is that no measurement stands behind the value yet, so
#: the scheme requires each to name the evidence that would move it.
NEEDS_POINTER: frozenset[str] = frozenset({"CHOSEN"})

FIELDS: frozenset[str] = frozenset(
    {"tag", "units", "tier", "form", "resolves_by", "family", "note"}
)

UNSECTIONED = "(unsectioned)"

# --- source patterns --------------------------------------------------------

# Module-level annotated assignment at column 0. Everything in data.py is
# annotated, which is what makes a text scan reliable here.
_ASSIGN = re.compile(r"^(_?[A-Z][A-Z0-9_]*)\s*:\s*[^=]+=")
_TAG_OPEN = re.compile(r"^# *tag:", re.I)
_BLOCK_DIRECTIVE = re.compile(r"^# *provenance-block: *(.+?) *$")
_COMMENT = re.compile(r"^#")
_FIELD_LINE = re.compile(r"^# *(" + "|".join(sorted(FIELDS)) + r"): *(.*)$")
# A continuation is INDENTED (three or more spaces after the '#'). Un-indented
# prose therefore closes the block instead of being silently absorbed into
# whichever field came last — a wrong pointer in the audit CSV is worse than a
# missing one, because nothing downstream can tell it was never written.
_CONTINUATION = re.compile(r"^#\s{3,}(\S.*)$")

DATA_PY = Path(__file__).resolve().parent.parent / "hours_eoh" / "data.py"
AUDIT_CSV = (
    Path(__file__).resolve().parent.parent
    / "hours_eoh"
    / "reference"
    / "data"
    / "constant_provenance.csv"
)
PROVENANCE_DOC = (
    Path(__file__).resolve().parent.parent / "docs" / "parameter_provenance.md"
)

#: Longest value repr rendered literally; past this a shape summary is clearer
#: than 4 kB of nested table in one CSV cell.
_VALUE_REPR_LIMIT = 80


@dataclass(frozen=True)
class TagBlock:
    """One parsed tag block, before it is attached to any constant."""

    line: int
    tag: str = ""
    units: str = ""
    tier: str = ""
    form: str = ""
    resolves_by: str = ""
    family: str = ""
    note: str = ""


@dataclass(frozen=True)
class Record:
    """A constant and the provenance attached to it."""

    name: str
    value: str
    units: str
    tag: str
    tier: str
    form: str
    resolves_by: str
    note: str
    block: str
    line: int
    #: Name of the glob this record inherited its block from, "" if its own.
    family: str = ""


@dataclass
class Scan:
    """Everything a scan of ``data.py`` found, including what it could not place."""

    records: list[Record] = field(default_factory=list)
    #: Constants with no tag block. The coverage gate asserts this is empty.
    untagged: list[str] = field(default_factory=list)
    #: Tag blocks that attached to nothing (a deleted constant, or a `family:`
    #: glob that matches no following run).
    orphans: list[TagBlock] = field(default_factory=list)

    @property
    def by_name(self) -> dict[str, Record]:
        return {r.name: r for r in self.records}

    def blocks(self) -> list[str]:
        """Reporting sections, in the order they first appear in the source."""
        seen: list[str] = []
        for r in self.records:
            if r.block not in seen:
                seen.append(r.block)
        return seen

    def in_block(self, block: str) -> list[Record]:
        return [r for r in self.records if r.block == block]


# --- parsing ----------------------------------------------------------------


def _parse_tag_block(lines: Sequence[str], start: int) -> tuple[TagBlock, int]:
    """Read the comment run at ``start`` as a tag block.

    Returns the block and the index of the first line after it.
    """
    fields: dict[str, str] = {}
    last: str | None = None

    head = lines[start].lstrip("#").strip()
    for chunk in head.split("|"):
        if ":" not in chunk:
            continue
        key, _, val = chunk.partition(":")
        key = key.strip().lower()
        if key in FIELDS:
            fields[key] = val.strip()
            last = key

    i = start + 1
    while i < len(lines) and _COMMENT.match(lines[i]):
        # A second '# tag:' opens a new block, and a section directive ends this
        # one — neither is part of it.
        if _TAG_OPEN.match(lines[i]) or _BLOCK_DIRECTIVE.match(lines[i]):
            break
        m = _FIELD_LINE.match(lines[i])
        if m:
            key = m.group(1).lower()
            fields[key] = m.group(2).strip()
            last = key
            i += 1
            continue
        cont = _CONTINUATION.match(lines[i])
        if cont is None or last is None:
            break  # un-indented prose: the block is over
        fields[last] = f"{fields[last]} {cont.group(1).strip()}".strip()
        i += 1

    return (
        TagBlock(
            line=start + 1,
            tag=fields.get("tag", ""),
            units=fields.get("units", ""),
            tier=fields.get("tier", ""),
            form=fields.get("form", ""),
            resolves_by=fields.get("resolves_by", ""),
            family=fields.get("family", ""),
            note=fields.get("note", ""),
        ),
        i,
    )


def format_value(value: Any) -> str:
    """Render a constant's value for the audit CSV and the generated tables.

    Floats render to 12 significant figures. That is far more precision than any
    provenance claim carries, and it keeps binary-representation noise out of a
    document meant to be read — a *derived* constant like `PP_INDEX_WARN_SLOPE`
    evaluates to 0.1250000000000001, and printing that tells a reader nothing
    except that floats are binary. `data.py` remains the source of truth for the
    exact bits.

    Big nested tables get a shape summary: the CSV exists so an outside reader
    can check a *tag*, and a 4 kB dict in one cell defeats that.
    """
    if isinstance(value, float):
        text = f"{value:.12g}"
        # Keep it visibly a float: "5" would read as an int in the audit CSV.
        if not any(c in text for c in ".eEnif"):
            text += ".0"
        return text
    text = repr(value)
    if len(text) <= _VALUE_REPR_LIMIT:
        return text
    if isinstance(value, Mapping):
        return f"<dict: {len(value)} keys>"
    if isinstance(value, (list, tuple, set, frozenset)):
        return f"<{type(value).__name__}: {len(value)} items>"
    return text[: _VALUE_REPR_LIMIT - 1] + "…"


def scan(source: str, values: Mapping[str, Any] | None = None) -> Scan:
    """Scan ``data.py`` source text for tag blocks and the constants they cover.

    ``values`` supplies evaluated values (normally ``vars(hours_eoh.data)``); when
    omitted the value column reads ``"?"``, which is what the parser unit tests
    exercise.
    """
    lines = source.splitlines()
    out = Scan()
    block_name = UNSECTIONED
    pending: TagBlock | None = None
    family: TagBlock | None = None
    i = 0

    while i < len(lines):
        line = lines[i]

        directive = _BLOCK_DIRECTIVE.match(line)
        if directive:
            block_name = directive.group(1).strip()
            i += 1
            continue

        if _TAG_OPEN.match(line):
            if pending is not None:
                out.orphans.append(pending)
            parsed, i = _parse_tag_block(lines, i)
            if parsed.family:
                _retire_family(family, out)
                family, pending = parsed, None
            else:
                pending = parsed
            continue

        assign = _ASSIGN.match(line)
        if assign:
            name = assign.group(1)
            source_block: TagBlock | None = None
            inherited = ""
            if pending is not None:
                source_block, pending = pending, None
            elif family is not None and fnmatch.fnmatch(name, family.family):
                source_block, inherited = family, family.family
            else:
                _retire_family(family, out)
                family = None

            if source_block is None:
                out.untagged.append(name)
            else:
                raw = values.get(name, "?") if values is not None else "?"
                out.records.append(
                    Record(
                        name=name,
                        value=format_value(raw) if values is not None else "?",
                        units=source_block.units,
                        tag=source_block.tag,
                        tier=source_block.tier,
                        form=source_block.form,
                        resolves_by=source_block.resolves_by,
                        note=source_block.note,
                        block=block_name,
                        line=i + 1,
                        family=inherited,
                    )
                )
            i += 1
            continue

        i += 1

    if pending is not None:
        out.orphans.append(pending)
    _retire_family(family, out)
    return out


def _retire_family(block: TagBlock | None, out: Scan) -> None:
    """Close out a family block, recording it as an orphan if it covered nothing.

    A ``family:`` glob that matched nothing is the signature of a renamed or
    deleted constant, and it must surface — otherwise the block sits in the file
    looking like coverage it does not provide.
    """
    if block is not None and not any(r.family == block.family for r in out.records):
        out.orphans.append(block)


def load(data_py: Path | None = None) -> Scan:
    """Scan the shipped ``data.py``, with values from the imported module."""
    path = data_py or DATA_PY
    from hours_eoh import data as data_module

    return scan(path.read_text(encoding="utf-8"), vars(data_module))


def live_constants(source: str | None = None) -> list[str]:
    """Every module-level constant in ``data.py``, in file order.

    The denominator of the coverage gate. Read from source rather than from
    ``dir(module)`` so imported names (``PERSONAL_EOH_BASE`` re-exported
    elsewhere) cannot inflate it.
    """
    text = source if source is not None else DATA_PY.read_text(encoding="utf-8")
    return [
        m.group(1) for line in text.splitlines() if (m := _ASSIGN.match(line))
    ]


# --- the scheme's own rules, as checks --------------------------------------


def problems(scanned: Scan) -> list[str]:
    """Every way the scan violates the tag scheme, as readable one-liners.

    This is the single definition the CLI and the test suite share, so
    ``eoh provenance check`` and ``pytest`` cannot disagree about what "clean"
    means.
    """
    found: list[str] = []

    for name in scanned.untagged:
        found.append(
            f"{name}: no provenance tag block. Add '# tag: …' immediately above it."
        )

    for orphan in scanned.orphans:
        what = (
            f"family glob '{orphan.family}' matched no following constant"
            if orphan.family
            else "tag block attached to no constant"
        )
        found.append(f"data.py:{orphan.line}: {what}.")

    for r in scanned.records:
        where = f"{r.name} (data.py:{r.line})"
        if r.tag not in VALID_TAGS:
            found.append(
                f"{where}: tag '{r.tag}' is not in the scheme "
                f"({', '.join(sorted(VALID_TAGS))})."
            )
        if not r.units:
            found.append(f"{where}: no units declared.")
        if r.tag in NEEDS_POINTER and not r.resolves_by:
            found.append(
                f"{where}: tag is {r.tag} but no resolves_by — the scheme requires "
                "every CHOSEN constant to name the evidence that would move it."
            )
        if r.tier:
            if r.tier not in TIERS:
                found.append(
                    f"{where}: tier '{r.tier}' is not one of {', '.join(sorted(TIERS))}."
                )
            elif r.tag not in TIER_ELIGIBLE_TAGS:
                found.append(
                    f"{where}: tier '{r.tier}' on a '{r.tag}' constant — tier "
                    "qualifies how good a source is, so it applies only to "
                    f"{', '.join(sorted(TIER_ELIGIBLE_TAGS))}."
                )

    return found


def coverage(scanned: Scan, source: str | None = None) -> tuple[int, int]:
    """``(tagged, total)`` constants in ``data.py``."""
    total = len(live_constants(source))
    return len(scanned.records), total


def tag_counts(scanned: Scan) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in scanned.records:
        counts[r.tag] = counts.get(r.tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# --- rendering --------------------------------------------------------------

CSV_COLUMNS = (
    "constant",
    "value",
    "units",
    "tag",
    "tier",
    "form",
    "block",
    "resolves_by",
    "note",
)


def audit_csv(scanned: Scan) -> str:
    """The shipped public-audit CSV.

    Column order mirrors ``reference/data/multiplier_provenance_v5.csv`` so the
    two provenance files read the same way. Rows follow ``data.py`` order rather
    than being sorted, so a diff of this file localises to the block that
    changed.
    """
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for r in scanned.records:
        writer.writerow(
            [
                r.name,
                r.value,
                r.units,
                r.tag,
                r.tier,
                r.form,
                r.block,
                r.resolves_by,
                r.note,
            ]
        )
    return buf.getvalue()


def _cell(text: str) -> str:
    """Escape a value for a markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip() or "—"


def doc_table(records: Iterable[Record]) -> str:
    """Render records as the generated markdown table for the provenance doc."""
    rows = list(records)
    if not rows:
        return "_No constants in this block._"
    out = [
        "| Parameter | Default | Units | Tag | `resolves_by` (epistemic pointer) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        tag = r.tag
        if r.tier:
            tag = f"{tag} (Tier {r.tier})"
        if r.form:
            tag = f"{tag}<br>form: {_cell(r.form)}"
        pointer = r.resolves_by or ("n/a — structural" if r.tag == "physics" else "—")
        if r.note:
            pointer = f"{pointer}<br>{_cell(r.note)}"
        out.append(
            f"| `{r.name}` | {_cell(r.value)} | {_cell(r.units)} | "
            f"{_cell(tag)} | {_cell(pointer)} |"
        )
    return "\n".join(out)


# --- doc region rewriting ---------------------------------------------------

_CLOSE = "<!-- /provenance:table -->"

# The body may be empty (a freshly-placed marker pair with no table yet), so the
# separating newline is optional here and normalized on render.
_MARKER = re.compile(
    r"<!-- provenance:table +\"(?P<block>[^\"]+)\" +-->\n"
    r"(?P<body>.*?)"
    r"\n?" + re.escape(_CLOSE),
    re.S,
)


def render_doc(scanned: Scan, doc_text: str) -> str:
    """Replace every ``provenance:table`` marked region with a fresh table.

    Prose outside the markers is left exactly as written — that is where the
    epistemic argument lives, and it is not generated. Output is normalized, so
    re-rendering an already-rendered doc is a no-op, which is what lets the test
    suite compare regeneration against the committed file.
    """

    def replace(m: re.Match[str]) -> str:
        block = m.group("block")
        return (
            f'<!-- provenance:table "{block}" -->\n'
            f"{doc_table(scanned.in_block(block))}\n"
            f"{_CLOSE}"
        )

    return _MARKER.sub(replace, doc_text)


def doc_markers(doc_text: str) -> list[str]:
    """Block names the doc asks for, in document order."""
    return [m.group("block") for m in _MARKER.finditer(doc_text)]
