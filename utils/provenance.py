"""
Provenance scanner for ``hours_eoh/data.py``.

Every module-level constant in ``data.py`` carries an inline provenance tag block
stating where its value comes from and what would change it. This module reads
those blocks, checks them against the scheme's own rules, and renders them as the
shipped audit CSV and as the generated tables in
``docs/parameter_provenance.md``.

The tag scheme is defined in ``docs/parameter_provenance.md`` §"The tag scheme":

    physics      a structural claim about how entropy works
    measured     read from an external empirical source
    derived      computed from measured inputs by a stated formula
    bounded      picked inside a MEASURED band — the band is evidence, the point
                 is not. Must state its ``band`` and which way it ``errs``.
    placeholder  no measurement stands behind it at all. The real debt.
    normative    a decision, not measurable even in principle. Must state
                 ``decided_by``, and may NOT claim a ``resolves_by``.

plus two working sub-labels, ``derived-then-FROZEN`` (a derived value pinned at a
reference epoch so it stays comparable across data vintages) and ``convention``
(a stated denominator, not a claim about the world).

The ``bounded`` / ``placeholder`` / ``normative`` split replaced a single
``CHOSEN`` tag (author decision 2026-08-09). One tag was covering three different
epistemic states, and lumping them distorted the picture in both directions: it
made the calibration set look like 83% guesswork while *hiding* which constants
are the actual debts. Worse, it filed charter decisions under "awaiting
measurement" — a category error, since no dataset will ever settle what fraction
of an estate should pass to heirs. ``normative`` therefore takes ``decided_by``
and is forbidden a ``resolves_by``: the forbidding is the point.

``tier`` (A–D) is a *confidence sub-qualifier*, not a rival scheme: the thermal
block already writes "measured (Tier A)". It is valid only where there is a source
to grade — ``measured``, ``bounded`` and ``placeholder``. A ``physics`` claim is
not more or less well-sourced, it is structural or it is wrong; and a ``normative``
decision has no source at all.

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

import ast
import csv
import fnmatch
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --- the scheme -------------------------------------------------------------

#: The seven tags. Anything else is a scheme violation, not a new category.
#:
#: ``instance`` was split out of ``placeholder`` (2026-08-09) for the same reason
#: ``normative`` was: no dataset in this framework's future retires a value that
#: describes *the jurisdiction being modelled*. A capital inventory is not a
#: measurement the framework owes — it is the input an institution brings, and
#: filing it under "unmeasured" both overstates the framework's debt and hides
#: the intake path from the analyst who has to supply it.
TAGS: frozenset[str] = frozenset(
    {
        "physics", "measured", "derived", "bounded",
        "placeholder", "normative", "instance",
    }
)

#: Declared working sub-labels (docs/parameter_provenance.md §"The tag scheme").
SUB_LABELS: frozenset[str] = frozenset({"derived-then-FROZEN", "convention"})

VALID_TAGS: frozenset[str] = TAGS | SUB_LABELS

#: Retired tags, kept named so the error message can say what to use instead.
RETIRED_TAGS: dict[str, str] = {
    "CHOSEN": "bounded (inside a measured band), placeholder (no measurement) or "
              "normative (a decision, not measurable)",
    "Physics": "physics",
    "Calibration": "bounded, placeholder or normative",
    "Physics-adjacent": "physics, or normative if it is a commitment",
}

#: Confidence sub-qualifier, valid only where a source can be more or less good.
TIERS: frozenset[str] = frozenset({"A", "B", "C", "D"})
TIER_ELIGIBLE_TAGS: frozenset[str] = frozenset(
    {"measured", "bounded", "placeholder"}
)

#: Tags that must name the evidence which would settle the value.
NEEDS_POINTER: frozenset[str] = frozenset({"bounded", "placeholder"})

#: A bounded value's band IS its evidence, and the direction it errs in is what
#: several of this framework's most leveraged picks rest on ("erring high is the
#: mortality-minimising error"). Both are required so a bounded constant with no
#: stated band cannot masquerade as better-founded than a placeholder.
NEEDS_BAND: frozenset[str] = frozenset({"bounded"})

#: A decision is accountable to whoever made it, not to a future dataset.
NEEDS_DECIDER: frozenset[str] = frozenset({"normative"})

#: An ``instance`` constant must name what the institution measures AND what the
#: shipped number is. Both, because the risk of this tag is precisely that it
#: launders "35B is a desk figure" into "the institution will supply it" — every
#: canonical result in this repo was produced at the shipped default, and
#: ``default:`` is where that stays visible.
NEEDS_SUPPLIER: frozenset[str] = frozenset({"instance"})

#: Claiming a measurement would settle a charter decision is the category error
#: this split exists to correct, so the field is refused rather than ignored.
#: Same for ``instance``: no dataset settles another jurisdiction's capital stock.
FORBIDS_POINTER: frozenset[str] = frozenset({"normative", "instance"})

#: Leading token of ``errs:`` — which way the pick is wrong if it is wrong.
#: WITHHELD is a real epistemic state here, not an escape hatch: the thermal layer
#: already refuses to publish a budget whose sign is undetermined.
ERR_DIRECTIONS: frozenset[str] = frozenset({"HIGH", "LOW", "NEITHER", "WITHHELD"})

FIELDS: frozenset[str] = frozenset(
    {
        "tag", "units", "tier", "form", "family", "note",
        "resolves_by",   # bounded / placeholder: what would settle it
        "band",          # bounded: the measured range it was picked inside
        "band_from",     # bounded/derived: the constants an ANCHORED band rests on
        "baseline_in",   # retired: modules that may still read it as a REFUTED baseline
        "errs",          # bounded: HIGH | LOW | NEITHER | WITHHELD, and why
        "decided_by",    # normative: who or what decides it
        "precedent",     # normative: an external analogue that informs, not settles
        "supplied_by",   # instance: what the institution measures, and the intake path
        "default",       # instance: what the SHIPPED number is, and what rests on it
        "superseded_by", # any tag: the live replacement; marks this one not-live
    }
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
    band: str = ""
    band_from: str = ""
    baseline_in: str = ""
    errs: str = ""
    decided_by: str = ""
    precedent: str = ""
    supplied_by: str = ""
    default: str = ""
    superseded_by: str = ""
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
    band: str
    errs: str
    decided_by: str
    precedent: str
    note: str
    block: str
    line: int
    #: Name of the glob this record inherited its block from, "" if its own.
    family: str = ""
    supplied_by: str = ""
    default: str = ""
    superseded_by: str = ""
    #: Constants an ANCHORED band/derivation rests on, comma-separated. Gated:
    #: no named ancestor may be a placeholder, transitively.
    band_from: str = ""
    #: Modules that may still read a RETIRED constant as a refuted baseline,
    #: comma-separated repo-relative paths. Gated: see ``problems``.
    baseline_in: str = ""

    @property
    def err_direction(self) -> str:
        """Leading token of ``errs``, or "" — which way the pick is wrong."""
        head = self.errs.split(".", 1)[0].split()[0] if self.errs.strip() else ""
        return head.strip(".,:").upper() if head else ""

    @property
    def retired(self) -> bool:
        """True when a live replacement exists, so this value governs nothing.

        A retired constant is kept, not deleted (the additive-not-destructive
        rule): it is the value every earlier result in this repo was produced
        at, so reproducing an old figure means passing it explicitly. It is not
        debt, because no measurement of it would change any current output.
        """
        return bool(self.superseded_by)


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
            band=fields.get("band", ""),
            band_from=fields.get("band_from", ""),
            baseline_in=fields.get("baseline_in", ""),
            errs=fields.get("errs", ""),
            decided_by=fields.get("decided_by", ""),
            precedent=fields.get("precedent", ""),
            supplied_by=fields.get("supplied_by", ""),
            default=fields.get("default", ""),
            superseded_by=fields.get("superseded_by", ""),
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
                        band=source_block.band,
                        band_from=source_block.band_from,
                        baseline_in=source_block.baseline_in,
                        errs=source_block.errs,
                        decided_by=source_block.decided_by,
                        precedent=source_block.precedent,
                        note=source_block.note,
                        block=block_name,
                        line=i + 1,
                        family=inherited,
                        supplied_by=source_block.supplied_by,
                        default=source_block.default,
                        superseded_by=source_block.superseded_by,
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


def _replacement_exists(target: str, scanned: Scan) -> bool:
    """Does ``superseded_by``'s target actually exist?

    A retired constant is usually replaced by another constant, but sometimes by
    a whole measured pathway (``DEFAULT_SEGMENTS`` → the O*NET/BLS registry), so
    a dotted module path is accepted too. Checked on the filesystem rather than
    by importing: this runs inside the gate, and a provenance check must not be
    able to execute package code as a side effect.
    """
    if "." not in target:
        return target in scanned.by_name
    parts = target.split(".")
    root = DATA_PY.parent.parent
    for k in range(len(parts), 0, -1):
        stem = root.joinpath(*parts[:k])
        if stem.with_suffix(".py").is_file() or (stem / "__init__.py").is_file():
            return True
    return False



#: Tags that cannot anchor a derivation. `placeholder` is the debt itself;
#: `instance` is supplied per-jurisdiction so it anchors nothing general.
UNANCHORED_TAGS: frozenset[str] = frozenset({"placeholder"})


def unanchored_ancestors(
    name: str, scanned: "Scan", _seen: frozenset[str] | None = None
) -> list[str]:
    """Placeholder ancestors of ``name``, following ``band_from`` TRANSITIVELY.

    THE ONE-LEVEL CHECK IS NOT ENOUGH, and this is not hypothetical. ``derived``
    is defined as inheriting "its authority from the measurements beneath it",
    so an input tagged ``derived`` can still bottom out on a placeholder two or
    three steps down. Both anchored-inversion candidates examined on 2026-08-15
    had exactly that shape:

        CONTESTABILITY_CAPITAL_YIELD_RATE
          <- FORMATION_DEPRECIATION_RATE  (derived)
            <- CAPITAL_MACHINE_PROFILES   (PLACEHOLDER)

        ECOLOGICAL_BASE_RATE  <- the thermal drawdown chain
            <- CDR_GROSS_REMOVAL_FACTOR   (PLACEHOLDER)

    A one-level check passes both. Only walking the chain catches them, and
    hand-tracing is what caught them the first time — which is the argument for
    doing it in code.

    Returns the offending chains as "A -> B -> C" strings, empty if anchored.
    Cycles terminate rather than recurse.
    """
    seen = _seen or frozenset()
    if name in seen:
        return []
    rec = scanned.by_name.get(name)
    if rec is None:
        return []
    if rec.tag in UNANCHORED_TAGS:
        return [name]

    out: list[str] = []
    for parent in (a.strip() for a in rec.band_from.split(",") if a.strip()):
        for chain in unanchored_ancestors(parent, scanned, seen | {name}):
            out.append(f"{name} -> {chain}")
    return out


def parameter_default_consumers(
    name: str, root: Path | None = None
) -> list[str]:
    """Operative-layer functions that take ``name`` as a PARAMETER DEFAULT.

    This is the precise form of the thing the retirement gate is actually
    worried about. ``operative_consumers`` answers "is it mentioned?", which
    conflates two very different reads:

        decay: float = SKILL_DECAY_RATE      <- a second parameter, running in
                                                parallel with its replacement
        "shipped": SKILL_DECAY_RATE          <- the refuted baseline, reported
                                                so the disagreement stays visible

    The first is the failure mode ``superseded_by`` exists to prevent: a caller
    who passes nothing silently gets the old value. The second is a documented
    negative result, and the repo keeps several on purpose
    (``contestability_ceiling_bare_chi`` is the standing precedent).

    Parsed with ``ast`` rather than matched with a regex, because this is the
    check a ``baseline_in:`` claim is allowed to bypass — so it has to be one
    that cannot be dodged by reformatting the line.
    """
    base = root or PACKAGE_ROOT.parent
    hits: list[str] = []
    for layer in OPERATIVE_LAYERS:
        for path in sorted(base.glob(f"hours_eoh/{layer}/**/*.py")):
            if path == DATA_PY:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - repo does not ship these
                continue
            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                args = node.args
                defaults = list(args.defaults) + [
                    d for d in args.kw_defaults if d is not None
                ]
                for default in defaults:
                    for sub in ast.walk(default):
                        if isinstance(sub, ast.Name) and sub.id == name:
                            hits.append(
                                f"{path.relative_to(base)}:{node.lineno}"
                                f" ({node.name})"
                            )
    return sorted(set(hits))


#: Numbers that carry no calibration claim — identities, unit conversions, and
#: the small integers that index, guard or count. Flagging these would bury the
#: cases that matter under arithmetic.
_INNOCUOUS: frozenset[float] = frozenset(
    {0.0, 1.0, 2.0, -1.0, 0.5, 100.0, 3.0, 4.0, 10.0, 12.0, 24.0, 60.0, 1000.0}
)


@dataclass(frozen=True)
class Shadow:
    """A domain constant that lives outside ``data.py``."""

    module: str
    line: int
    name: str
    value: str
    #: True when the value is computed from a name imported from ``data.py`` —
    #: an alias, which is the FIX for a shadow rather than an instance of one.
    bound: bool


def shadow_constants(root: Path | None = None) -> list[Shadow]:
    """Module-level numeric constants in operative layers, outside ``data.py``.

    THE COVERAGE FIGURE HAS THE WRONG DENOMINATOR, AND THIS IS WHY.
    ``eoh provenance check`` reports "236/236 constants tagged (100.0%)", which
    is true and narrower than it reads: it means 236 constants *in data.py*. A
    named numeric constant declared anywhere else is in no count this repo
    publishes, carries no tag, has no ``resolves_by``, and cannot appear in the
    debt summary — while being read by exactly the same domain logic.

    This is not hypothetical. Every one of these has already cost something:

        TRANSMISSION_WORKING_LIFE_YEARS = 40.0   scenarios/knowledge_base.py
            A duplicate of SKILL_WORKING_LIFE_YEARS carrying its own copy of the
            same wrong pointer. When the source was measured at 37.5 the two
            diverged silently and broke a structural identity by exactly
            40/37.5. Bound 2026-08-16.
        _ECOLOGICAL_SPIKE_INTENSITY = 5.0        core/eoh_generation.py
            Covered by the 2026-08-09 retag log, which the gate could not reach.

    A constant whose expression references a ``data.py`` import is reported with
    ``bound=True``: that is an alias, the intended shape, and the remedy for the
    rest.

    Scoped to ``OPERATIVE_LAYERS``. ``reference/`` is excluded because it holds
    measured data rather than calibration, and ``research/`` because it is
    explicitly not stable API.
    """
    base = root or PACKAGE_ROOT.parent
    out: list[Shadow] = []
    for layer in OPERATIVE_LAYERS:
        for path in sorted(base.glob(f"hours_eoh/{layer}/**/*.py")):
            if path == DATA_PY:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover
                continue
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and (
                    "data" in node.module.split(".")
                ):
                    imported |= {a.name for a in node.names}

            for node in tree.body:
                targets: list[ast.expr]
                value: ast.expr | None
                if isinstance(node, ast.AnnAssign):
                    targets, value = [node.target], node.value
                elif isinstance(node, ast.Assign):
                    targets, value = list(node.targets), node.value
                else:
                    continue
                if value is None:
                    continue
                nums = [
                    s.value
                    for s in ast.walk(value)
                    if isinstance(s, ast.Constant)
                    and isinstance(s.value, (int, float))
                    and not isinstance(s.value, bool)
                    and float(s.value) not in _INNOCUOUS
                ]
                if not nums:
                    continue
                refs = {
                    s.id for s in ast.walk(value) if isinstance(s, ast.Name)
                } & imported
                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    bare = target.id.lstrip("_")
                    if not bare.isupper() or len(bare) < 2:
                        continue
                    out.append(
                        Shadow(
                            module=str(path.relative_to(base)),
                            line=node.lineno,
                            name=target.id,
                            value=", ".join(repr(n) for n in nums[:4]),
                            bound=bool(refs),
                        )
                    )
    return out


def repeated_default_literals(
    root: Path | None = None, min_sites: int = 3
) -> list[tuple[str, float, list[str]]]:
    """Bare numeric defaults repeated under the same parameter name.

    THE SECOND SHADOW CLASS, and the one with no name at all. A literal written
    into the same parameter of many independent functions is a constant by
    behaviour — every caller who omits the argument gets it — while being
    invisible to every tool that looks for constants, because nobody declared
    one. It is how ``= 1500.0`` survived the ``PERSONAL_EOH_BASE`` reprice in
    five generators at once, and how ``skill_decay_rate = 0.10`` kept the
    pipeline running knowledge EOH 4× the direct path.

    Repetition is the filter that makes this usable. Value equality alone
    returns 230 candidates against ``data.py`` and almost all are coincidence
    (a 50-year amortization is not a 50-draw Monte Carlo). The same NAME at the
    same VALUE across separate modules is not coincidence.

    Returns ``(parameter, value, sites)`` sorted by site count, descending.
    """
    base = root or PACKAGE_ROOT.parent
    seen: dict[tuple[str, float], list[str]] = {}
    for layer in OPERATIVE_LAYERS:
        for path in sorted(base.glob(f"hours_eoh/{layer}/**/*.py")):
            if path == DATA_PY:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                args = node.args
                pairs = (
                    list(zip(args.args[-len(args.defaults):], args.defaults))
                    if args.defaults
                    else []
                )
                pairs += [
                    (a, d)
                    for a, d in zip(args.kwonlyargs, args.kw_defaults)
                    if d is not None
                ]
                for arg, default in pairs:
                    if not isinstance(default, ast.Constant):
                        continue
                    v = default.value
                    if not isinstance(v, (int, float)) or isinstance(v, bool):
                        continue
                    if float(v) in _INNOCUOUS:
                        continue
                    seen.setdefault((arg.arg, float(v)), []).append(
                        f"{path.relative_to(base)}:{node.lineno}"
                    )
    return sorted(
        (
            (name, value, sites)
            for (name, value), sites in seen.items()
            if len(sites) >= min_sites
        ),
        key=lambda row: -len(row[2]),
    )


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

    for rec in scanned.records:
        if not rec.band_from.strip():
            continue
        for missing in (a.strip() for a in rec.band_from.split(",") if a.strip()):
            if missing not in scanned.by_name:
                found.append(
                    f"{rec.name}: band_from names '{missing}', which is not a "
                    f"constant in data.py."
                )
        for chain in unanchored_ancestors(rec.name, scanned):
            found.append(
                f"{rec.name}: band_from is not anchored — {chain} is a "
                f"placeholder. A band resting on unmeasured input launders a "
                f"guess; state the dependency in `form:` instead of claiming a "
                f"band."
            )

    # `baseline_in:` — a RETIRED constant that operative code still reads as the
    # refuted comparison. Three conditions, and the middle one is the whole
    # point: a baseline claim buys exemption from "no readers", never from "no
    # parameter defaults", because a default is exactly how an old value keeps
    # governing output after everyone stops thinking about it.
    for rec in scanned.records:
        declared = [m.strip() for m in rec.baseline_in.split(",") if m.strip()]
        if declared and not rec.retired:
            found.append(
                f"{rec.name}: declares baseline_in but is not retired. The "
                f"field exempts a SUPERSEDED constant from the no-readers "
                f"rule; on a live one it claims nothing. Add superseded_by, or "
                f"drop the field."
            )
            continue
        if not declared:
            continue

        defaults = parameter_default_consumers(rec.name)
        if defaults:
            found.append(
                f"{rec.name}: baseline_in claims it is only a refuted "
                f"baseline, but it is a PARAMETER DEFAULT at "
                f"{', '.join(defaults[:5])}. A caller who passes nothing gets "
                f"the superseded value — that is a second parameter running in "
                f"parallel, which is what retirement is supposed to end. Point "
                f"the default at the replacement."
            )

        undeclared = sorted(
            {
                hit.split(":", 1)[0]
                for hit in operative_consumers(rec.name)
            }
            - set(declared)
        )
        if undeclared:
            found.append(
                f"{rec.name}: baseline_in does not cover {', '.join(undeclared)}"
                f", which read it. Every operative reader of a retired constant "
                f"must be named, so the exemption stays as narrow as the "
                f"comparison it is granted for."
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

        if r.tag in RETIRED_TAGS:
            found.append(
                f"{where}: tag '{r.tag}' is RETIRED — use "
                f"{RETIRED_TAGS[r.tag]}."
            )
        elif r.tag not in VALID_TAGS:
            found.append(
                f"{where}: tag '{r.tag}' is not in the scheme "
                f"({', '.join(sorted(VALID_TAGS))})."
            )

        if not r.units:
            found.append(f"{where}: no units declared.")

        # A retired constant owes no pointer, band or decider: those obligations
        # exist so a LIVE value can be improved, and nothing downstream reads
        # this one. What it does owe — a replacement that exists — is checked
        # below, unconditionally.
        if r.tag in NEEDS_POINTER and not r.resolves_by and not r.retired:
            found.append(
                f"{where}: tag is '{r.tag}' but no resolves_by — a value no "
                "measurement stands behind must name the evidence that would "
                "settle it."
            )

        if r.tag in NEEDS_BAND and not r.retired:
            if not r.band:
                found.append(
                    f"{where}: tag is 'bounded' but no band — a bounded value's "
                    "band IS its evidence. Without one it is a placeholder "
                    "claiming to be better founded than it is."
                )
            if not r.errs:
                found.append(
                    f"{where}: tag is 'bounded' but no errs — state which way the "
                    "pick is wrong if it is wrong, and why that is the safe "
                    f"direction. Start with one of {', '.join(sorted(ERR_DIRECTIONS))}."
                )
            elif r.err_direction not in ERR_DIRECTIONS:
                found.append(
                    f"{where}: errs starts with '{r.err_direction}', not one of "
                    f"{', '.join(sorted(ERR_DIRECTIONS))}."
                )

        if r.tag in NEEDS_DECIDER and not r.decided_by and not r.retired:
            found.append(
                f"{where}: tag is 'normative' but no decided_by — a decision is "
                "accountable to whoever makes it."
            )

        if r.tag in FORBIDS_POINTER and r.resolves_by:
            if r.tag == "instance":
                found.append(
                    f"{where}: tag is 'instance' but it claims a resolves_by. No "
                    "dataset settles another jurisdiction's value — this "
                    "framework never measures it, the deploying institution "
                    "does. Use supplied_by for what they measure."
                )
            else:
                found.append(
                    f"{where}: tag is 'normative' but it claims a resolves_by. No "
                    "dataset settles a decision — that category error is what the "
                    "normative tag exists to correct. Use decided_by, or precedent "
                    "for an external analogue that informs without settling."
                )

        if r.tag in NEEDS_SUPPLIER:
            if not r.supplied_by:
                found.append(
                    f"{where}: tag is 'instance' but no supplied_by — name what "
                    "the institution measures and the intake path in this repo, "
                    "or the analyst cannot act on the tag."
                )
            if not r.default:
                found.append(
                    f"{where}: tag is 'instance' but no default — state what the "
                    "SHIPPED number represents. Without it the tag launders an "
                    "unmeasured default into 'the institution will supply it', "
                    "while every canonical result here was produced at that "
                    "default."
                )

        for field_name, value in (("supplied_by", r.supplied_by), ("default", r.default)):
            if value and r.tag not in NEEDS_SUPPLIER:
                found.append(
                    f"{where}: {field_name} declared on a '{r.tag}' constant — "
                    "that field marks a value the deploying institution supplies, "
                    "which is what 'instance' tags."
                )

        if r.superseded_by:
            target = r.superseded_by.split()[0].rstrip(",;:")
            if not _replacement_exists(target, scanned):
                found.append(
                    f"{where}: superseded_by names '{target}', which is neither "
                    "a constant in data.py nor a module in this package. A "
                    "retired constant must point at a live replacement that "
                    "actually exists, or the pointer rots exactly where nobody "
                    "is looking."
                )

        if r.band and r.tag not in NEEDS_BAND:
            found.append(
                f"{where}: band declared on a '{r.tag}' constant — a band means "
                "the value was picked inside measured bounds, which is what "
                "'bounded' marks."
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


@dataclass(frozen=True)
class DebtSummary:
    """What is grounded, what is owed, what is a decision, and what is an input.

    The point of the bounded/placeholder/normative split. ``normative`` constants
    are deliberately NOT counted as debt — they are commitments, and no measurement
    retires them, so counting them as unmeasured overstates the model's ignorance
    while understating which constants actually need work.

    ``instance`` and ``retired`` are excluded on the same reasoning, and the same
    reasoning bounds the claim: an instance default is not the framework's debt,
    but it is not evidence either, which is why ``instance_defaults_unmeasured``
    is reported rather than quietly folded into ``grounded``. A retired constant
    governs nothing, so measuring it would change no output.
    """

    total: int
    grounded: int
    bounded: int
    placeholder: int
    normative: int
    instance: int
    retired: int
    err_directions: dict[str, int]

    @property
    def debt(self) -> int:
        return self.bounded + self.placeholder

    @property
    def live(self) -> int:
        """Constants that govern a current output."""
        return self.total - self.retired

    def share(self, n: int) -> float:
        return 100.0 * n / self.total if self.total else 0.0


def debt_summary(scanned: Scan) -> DebtSummary:
    live = [r for r in scanned.records if not r.retired]
    counts: dict[str, int] = {}
    for r in live:
        counts[r.tag] = counts.get(r.tag, 0) + 1
    directions: dict[str, int] = {}
    for r in live:
        if r.tag == "bounded":
            directions[r.err_direction] = directions.get(r.err_direction, 0) + 1
    return DebtSummary(
        total=len(scanned.records),
        grounded=sum(
            counts.get(t, 0)
            for t in ("physics", "measured", "derived",
                      "derived-then-FROZEN", "convention")
        ),
        bounded=counts.get("bounded", 0),
        placeholder=counts.get("placeholder", 0),
        normative=counts.get("normative", 0),
        instance=counts.get("instance", 0),
        retired=sum(1 for r in scanned.records if r.retired),
        err_directions=dict(sorted(directions.items())),
    )


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
    "band",
    "errs",
    "resolves_by",
    "decided_by",
    "precedent",
    "supplied_by",
    "default",
    "superseded_by",
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
                r.band,
                r.errs,
                r.resolves_by,
                r.decided_by,
                r.precedent,
                r.supplied_by,
                r.default,
                r.superseded_by,
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
        "| Parameter | Default | Units | Tag | What would settle it |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        tag = r.tag
        if r.tier:
            tag = f"{tag} (Tier {r.tier})"
        if r.form:
            tag = f"{tag}<br>form: {_cell(r.form)}"

        # A normative constant is answerable to a decider, not to a dataset. Saying
        # so in the table is the whole point of separating the tags.
        parts: list[str] = []
        if r.tag == "normative":
            parts.append(f"**decided by** {_cell(r.decided_by)}")
            if r.precedent:
                parts.append(f"precedent: {_cell(r.precedent)}")
            parts.append("_no measurement settles this_")
        elif r.tag == "instance":
            parts.append(f"**you supply** {_cell(r.supplied_by)}")
            parts.append(f"**shipped default** {_cell(r.default)}")
        else:
            if r.band:
                parts.append(f"**band** {_cell(r.band)}")
            if r.errs:
                parts.append(f"**errs** {_cell(r.errs)}")
            if r.resolves_by:
                parts.append(_cell(r.resolves_by))
            elif r.tag == "physics":
                parts.append("n/a — structural")
            elif not parts:
                parts.append("—")
        if r.superseded_by:
            parts.insert(0, f"**RETIRED** — superseded by {_cell(r.superseded_by)}")
        if r.note:
            parts.append(_cell(r.note))

        out.append(
            f"| `{r.name}` | {_cell(r.value)} | {_cell(r.units)} | "
            f"{_cell(tag)} | {'<br>'.join(parts)} |"
        )
    return "\n".join(out)


# --- claims made about constants outside data.py ----------------------------

PACKAGE_ROOT = DATA_PY.parent
GUIDES_DIR = PROVENANCE_DOC.parent / "guides"

#: A constant named in prose with a value attached: ``PERSONAL_EOH_BASE = 1500``,
#: ``TRUST_BASE_TEH = 35B``, ``DEP_RATE ≈ 0.045``. Backticks and markdown
#: emphasis around the name are tolerated because that is how docs write it.
_DOC_CLAIM = re.compile(
    r"`?\*{0,2}([A-Z][A-Z0-9_]{3,})\*{0,2}`?\s*(?:=|≈|:)\s*"
    r"([0-9][0-9_,]*(?:\.[0-9]+)?)\s*([BMk])?\b"
)

_SUFFIX = {"B": 1e9, "M": 1e6, "k": 1e3}


def doc_constant_claims(text: str) -> list[tuple[str, float, str]]:
    """Every ``NAME = number`` claim in a prose document.

    Returns ``(name, parsed_value, as_written)``. Names not defined in
    ``data.py`` are the caller's problem to filter — a doc may legitimately
    name a params key or a local variable.
    """
    out: list[tuple[str, float, str]] = []
    for m in _DOC_CLAIM.finditer(text):
        raw = m.group(2).replace(",", "").replace("_", "")
        try:
            value = float(raw)
        except ValueError:  # pragma: no cover - regex guarantees a number
            continue
        if m.group(3):
            value *= _SUFFIX[m.group(3)]
        out.append((m.group(1), value, m.group(0).strip()))
    return out


def stale_doc_claims(
    text: str, scanned: Scan, *, rel_tol: float = 1e-9
) -> list[str]:
    """Claims in ``text`` that contradict the value ``data.py`` actually holds.

    This is the check the generated-table machinery cannot make. Tables are
    rendered from the source and so are current by construction; hand-written
    prose that names a constant and quotes a number is where drift hides — it
    is exactly how the implementation guide came to advertise
    ``PERSONAL_EOH_BASE = 1500`` for three days after the reprice to 1000.
    """
    values = scanned.by_name
    bad: list[str] = []
    for name, claimed, written in doc_constant_claims(text):
        record = values.get(name)
        if record is None:
            continue
        try:
            actual = float(record.value)
        except ValueError:
            continue  # a dict/list constant: no scalar claim to check
        if actual == claimed:
            continue
        if actual and abs(actual - claimed) <= rel_tol * abs(actual):
            continue
        bad.append(f"{written!r} but data.py has {name} = {record.value}")
    return bad


#: Layers whose code is an operative path. ``research/`` is excluded on purpose:
#: keeping a superseded arm callable, next to the adopted one, is what that layer
#: is for (``contestability_ceiling_bare_chi`` is the standing precedent).
OPERATIVE_LAYERS: tuple[str, ...] = ("core", "land", "scenarios")


def operative_consumers(name: str, root: Path | None = None) -> list[str]:
    """Operative-layer lines that read ``name``, as ``path:line``.

    Holds ``superseded_by`` to its word. A retired constant that ``core/`` still
    reads is not retired — it is a second, older parameter running in parallel
    with its replacement, which is strictly worse than never having split it.

    Scoped to ``OPERATIVE_LAYERS`` rather than the whole package because the
    honest claim is layer-shaped: nothing on the stable path may depend on a
    value the framework has moved off, while ``research/`` may keep the old arm
    to report the disagreement.
    """
    base = root or PACKAGE_ROOT.parent
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    hits: list[str] = []
    for layer in OPERATIVE_LAYERS:
        for path in sorted(base.glob(f"hours_eoh/{layer}/**/*.py")):
            if path == DATA_PY:
                continue
            for n, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                code = line.split("#", 1)[0]
                if pattern.search(code):
                    hits.append(f"{path.relative_to(base)}:{n}")
    return hits


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
