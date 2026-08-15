"""
Tests for the provenance scanner and the coverage gate over ``hours_eoh/data.py``.

utils/provenance.py: scan, live_constants, problems, audit_csv, doc_table, render_doc

Two halves, and the split matters:

  * The PARSER tests run against synthetic source strings. They pin the inline
    format's behaviour — family globs, orphaned blocks, continuations, the
    scheme's own rules — independently of what ``data.py`` currently says, so a
    tagging change cannot quietly redefine what the format means.

  * The GATE tests run against the real ``data.py``. They are what stops
    provenance coverage regressing: a constant added without a tag, a CHOSEN
    constant with no epistemic pointer, or a value changed without regenerating
    the audit CSV and the doc tables all fail here.
"""

from __future__ import annotations

import re

import pytest

from utils import provenance as pv


# ---------------------------------------------------------------------------
# parser — synthetic source
# ---------------------------------------------------------------------------

def test_parses_tag_units_and_pointer():
    src = (
        "# tag: CHOSEN | units: fraction\n"
        "# resolves_by: a survey nobody has run\n"
        "ALPHA: float = 0.5\n"
    )
    scanned = pv.scan(src, {"ALPHA": 0.5})

    assert [r.name for r in scanned.records] == ["ALPHA"]
    rec = scanned.by_name["ALPHA"]
    assert rec.tag == "CHOSEN"
    assert rec.units == "fraction"
    assert rec.resolves_by == "a survey nobody has run"
    assert rec.value == "0.5"
    assert not scanned.untagged


def test_continuation_lines_join_the_previous_field():
    src = (
        "# tag: CHOSEN | units: hours\n"
        "# resolves_by: the first clause,\n"
        "#   the second clause,\n"
        "#   and the third.\n"
        "ALPHA: float = 1.0\n"
    )
    rec = pv.scan(src, {"ALPHA": 1.0}).by_name["ALPHA"]
    assert rec.resolves_by == "the first clause, the second clause, and the third."


def test_field_line_beats_continuation_when_it_names_a_known_field():
    """A wrapped pointer can contain a colon; only known field names open a field."""
    src = (
        "# tag: CHOSEN | units: K\n"
        "# resolves_by: an assessment naming the variable: the one that binds\n"
        "# form: physics — the functional shape is structural\n"
        "ALPHA: float = 2.0\n"
    )
    rec = pv.scan(src, {"ALPHA": 2.0}).by_name["ALPHA"]
    assert rec.resolves_by == "an assessment naming the variable: the one that binds"
    assert rec.form == "physics — the functional shape is structural"


def test_unindented_prose_closes_the_block_rather_than_joining_a_field():
    """A wrong pointer is worse than a missing one — nothing downstream can tell.

    Continuations must be indented. Un-indented prose between the block and the
    constant ends the block, so trailing commentary cannot be swept into
    ``resolves_by`` and shipped in the audit CSV as though someone wrote it there.
    """
    src = (
        "# tag: CHOSEN | units: fraction\n"
        "# resolves_by: the real pointer\n"
        "# Some unrelated prose about the history of this constant.\n"
        "ALPHA: float = 0.5\n"
    )
    rec = pv.scan(src, {"ALPHA": 0.5}).by_name["ALPHA"]
    assert rec.resolves_by == "the real pointer"


def test_family_glob_covers_the_following_run():
    src = (
        "# tag: measured | tier: A | units: W | family: GAMMA_*\n"
        "# resolves_by: IGCC 2025a\n"
        "GAMMA_ONE: float = 1.0\n"
        "GAMMA_TWO: float = 2.0\n"
        "GAMMA_THREE: float = 3.0\n"
    )
    scanned = pv.scan(src, {"GAMMA_ONE": 1.0, "GAMMA_TWO": 2.0, "GAMMA_THREE": 3.0})

    assert len(scanned.records) == 3
    assert all(r.tag == "measured" and r.tier == "A" for r in scanned.records)
    assert all(r.family == "GAMMA_*" for r in scanned.records)
    assert not scanned.untagged


def test_family_run_ends_at_the_first_non_matching_constant():
    src = (
        "# tag: measured | units: W | family: GAMMA_*\n"
        "GAMMA_ONE: float = 1.0\n"
        "DELTA: float = 2.0\n"
        "GAMMA_TWO: float = 3.0\n"
    )
    scanned = pv.scan(src, {"GAMMA_ONE": 1.0, "DELTA": 2.0, "GAMMA_TWO": 3.0})

    assert [r.name for r in scanned.records] == ["GAMMA_ONE"]
    # DELTA breaks the run, so GAMMA_TWO is NOT silently swept in behind it.
    assert scanned.untagged == ["DELTA", "GAMMA_TWO"]


def test_untagged_constant_is_reported_not_skipped():
    scanned = pv.scan("ALPHA: float = 1.0\n", {"ALPHA": 1.0})
    assert scanned.untagged == ["ALPHA"]
    assert not scanned.records
    assert any("no provenance tag block" in p for p in pv.problems(scanned))


def test_family_glob_matching_nothing_is_an_orphan():
    """A renamed or deleted constant must not leave its tag block claiming coverage."""
    src = (
        "# tag: CHOSEN | units: fraction | family: DELETED_*\n"
        "# resolves_by: something\n"
        "ALPHA: float = 1.0\n"
    )
    scanned = pv.scan(src, {"ALPHA": 1.0})

    assert scanned.untagged == ["ALPHA"]
    assert len(scanned.orphans) == 1
    assert scanned.orphans[0].family == "DELETED_*"
    assert any("matched no following constant" in p for p in pv.problems(scanned))


def test_tag_block_attached_to_nothing_is_an_orphan():
    src = (
        "# tag: CHOSEN | units: fraction\n"
        "# resolves_by: something\n"
        "# tag: physics | units: m\n"
        "ALPHA: float = 1.0\n"
    )
    scanned = pv.scan(src, {"ALPHA": 1.0})

    assert [r.name for r in scanned.records] == ["ALPHA"]
    assert scanned.by_name["ALPHA"].tag == "physics"
    assert len(scanned.orphans) == 1
    assert any("attached to no constant" in p for p in pv.problems(scanned))


def test_block_directive_sections_the_constants_that_follow():
    src = (
        "# provenance-block: First\n"
        "# tag: physics | units: m\n"
        "ALPHA: float = 1.0\n"
        "# provenance-block: Second\n"
        "# tag: physics | units: s\n"
        "BETA: float = 2.0\n"
    )
    scanned = pv.scan(src, {"ALPHA": 1.0, "BETA": 2.0})

    assert scanned.blocks() == ["First", "Second"]
    assert [r.name for r in scanned.in_block("Second")] == ["BETA"]


def test_constants_before_any_directive_are_unsectioned():
    scanned = pv.scan("# tag: physics | units: m\nALPHA: float = 1.0\n", {"ALPHA": 1.0})
    assert scanned.by_name["ALPHA"].block == pv.UNSECTIONED


# ---------------------------------------------------------------------------
# parser — the scheme's own rules
# ---------------------------------------------------------------------------

def test_tag_outside_the_scheme_is_a_violation():
    src = "# tag: vibes | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("is not in the scheme" in p for p in issues)


@pytest.mark.parametrize("retired", sorted(pv.RETIRED_TAGS))
def test_retired_tags_are_rejected_with_the_replacement_named(retired):
    """A rejection that does not say what to use instead just gets worked around."""
    src = f"# tag: {retired} | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("RETIRED" in p and pv.RETIRED_TAGS[retired] in p for p in issues)


def test_placeholder_without_a_pointer_is_a_violation():
    """A value no measurement stands behind must name what would settle it."""
    src = "# tag: placeholder | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no resolves_by" in p for p in issues)


# --- the bounded / placeholder / normative split ---------------------------

def test_bounded_requires_a_band():
    """Without a band, 'bounded' is a placeholder claiming to be better founded."""
    src = ("# tag: bounded | units: fraction\n"
           "# errs: HIGH. because\n"
           "# resolves_by: a study\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no band" in p for p in issues)


def test_bounded_requires_a_direction_of_error():
    src = ("# tag: bounded | units: fraction\n"
           "# band: 0.5–1.5 (some series)\n"
           "# resolves_by: a study\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no errs" in p for p in issues)


def test_errs_must_open_with_a_known_direction():
    src = ("# tag: bounded | units: fraction\n"
           "# band: 0.5–1.5\n"
           "# errs: probably a bit off\n"
           "# resolves_by: a study\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("not one of" in p and "HIGH" in p for p in issues)


@pytest.mark.parametrize("direction", sorted(pv.ERR_DIRECTIONS))
def test_every_declared_direction_is_accepted(direction):
    src = (f"# tag: bounded | units: fraction\n"
           f"# band: 0.5–1.5\n"
           f"# errs: {direction}. and here is why that is the safe side\n"
           f"# resolves_by: a study\n"
           f"ALPHA: float = 1.0\n")
    assert pv.problems(pv.scan(src, {"ALPHA": 1.0})) == []


def test_err_direction_is_parsed_off_the_leading_token():
    src = ("# tag: bounded | units: fraction\n"
           "# band: 0.5–1.5\n"
           "# errs: WITHHELD. the sign is undetermined across the band\n"
           "# resolves_by: a study\n"
           "ALPHA: float = 1.0\n")
    rec = pv.scan(src, {"ALPHA": 1.0}).by_name["ALPHA"]
    assert rec.err_direction == "WITHHELD"


def test_band_on_a_non_bounded_tag_is_a_violation():
    """A band means the value was picked inside measured bounds — that IS bounded."""
    src = ("# tag: placeholder | units: fraction\n"
           "# band: 0.5–1.5\n"
           "# resolves_by: a study\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("band declared on a 'placeholder'" in p for p in issues)


def test_normative_requires_a_decider():
    src = "# tag: normative | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no decided_by" in p for p in issues)


def test_normative_may_not_claim_a_resolves_by():
    """THE CATEGORY FIX. No dataset settles what fraction of an estate should
    pass to heirs; claiming one would settle it is the error the tag corrects."""
    src = ("# tag: normative | units: fraction\n"
           "# decided_by: charter\n"
           "# resolves_by: a study that will never exist\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("claims a resolves_by" in p for p in issues)


def test_normative_may_carry_a_precedent_instead():
    """An external analogue can inform a decision without settling it."""
    src = ("# tag: normative | units: fraction of income\n"
           "# decided_by: charter — the accessibility test on a primary residence\n"
           "# precedent: housing-cost-burden conventions (the US 30% threshold)\n"
           "ALPHA: float = 0.25\n")
    scanned = pv.scan(src, {"ALPHA": 0.25})
    assert pv.problems(scanned) == []
    assert scanned.by_name["ALPHA"].precedent.startswith("housing-cost-burden")


def test_normative_needs_no_pointer_and_no_band():
    src = ("# tag: normative | units: dimensionless\n"
           "# decided_by: charter — maximum permitted valuation inequality\n"
           "ALPHA: float = 6.0\n")
    assert pv.problems(pv.scan(src, {"ALPHA": 6.0})) == []


def test_tier_is_refused_on_normative():
    """A decision has no source to grade."""
    src = ("# tag: normative | tier: A | units: dimensionless\n"
           "# decided_by: charter\n"
           "ALPHA: float = 1.0\n")
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("qualifies how good a source is" in p for p in issues)


def test_tier_is_allowed_on_bounded_and_placeholder():
    for tag, extra in (
        ("bounded", "# band: 1–2\n# errs: LOW. safe side\n# resolves_by: x\n"),
        ("placeholder", "# resolves_by: x\n"),
    ):
        src = f"# tag: {tag} | tier: C | units: m\n{extra}ALPHA: float = 1.0\n"
        assert pv.problems(pv.scan(src, {"ALPHA": 1.0})) == [], tag


# --- debt summary ----------------------------------------------------------

def test_debt_summary_excludes_normative_from_the_debt():
    """The whole point of the split: a commitment is not an unpaid measurement."""
    src = (
        "# tag: normative | units: a\n# decided_by: charter\nA: float = 1.0\n"
        "# tag: placeholder | units: b\n# resolves_by: x\nB: float = 1.0\n"
        "# tag: bounded | units: c\n# band: 1–2\n# errs: LOW. safe\n"
        "# resolves_by: x\nC: float = 1.0\n"
        "# tag: physics | units: d\nD: float = 1.0\n"
    )
    d = pv.debt_summary(pv.scan(src, {k: 1.0 for k in "ABCD"}))
    assert d.total == 4
    assert d.normative == 1
    assert d.placeholder == 1
    assert d.bounded == 1
    assert d.grounded == 1
    assert d.debt == 2, "debt is bounded + placeholder only"
    assert d.share(d.debt) == pytest.approx(50.0)


def test_debt_summary_counts_error_directions():
    src = (
        "# tag: bounded | units: a\n# band: 1–2\n# errs: HIGH. x\n"
        "# resolves_by: x\nA: float = 1.0\n"
        "# tag: bounded | units: b\n# band: 1–2\n# errs: LOW. x\n"
        "# resolves_by: x\nB: float = 1.0\n"
        "# tag: bounded | units: c\n# band: 1–2\n# errs: LOW. x\n"
        "# resolves_by: x\nC: float = 1.0\n"
    )
    d = pv.debt_summary(pv.scan(src, {k: 1.0 for k in "ABC"}))
    assert d.err_directions == {"HIGH": 1, "LOW": 2}


def test_physics_needs_no_pointer():
    src = "# tag: physics | units: m2\nALPHA: float = 1.0\n"
    assert pv.problems(pv.scan(src, {"ALPHA": 1.0})) == []


def test_missing_units_is_a_violation():
    src = "# tag: physics\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no units declared" in p for p in issues)


def test_unknown_tier_is_a_violation():
    src = "# tag: measured | tier: Z | units: W\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("tier 'Z' is not one of" in p for p in issues)


def test_tier_on_a_physics_constant_is_a_violation():
    """Tier grades how good a source is; a structural claim has no source to grade."""
    src = "# tag: physics | tier: A | units: m2\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("qualifies how good a source is" in p for p in issues)


def test_sub_labels_are_accepted_tags():
    for label in sorted(pv.SUB_LABELS):
        src = f"# tag: {label} | units: hours\nALPHA: float = 1.0\n"
        assert pv.problems(pv.scan(src, {"ALPHA": 1.0})) == [], label


# ---------------------------------------------------------------------------
# value rendering
# ---------------------------------------------------------------------------

def test_short_values_render_literally():
    assert pv.format_value(0.5) == "0.5"
    assert pv.format_value(2000) == "2000"
    assert pv.format_value((0.30, 0.25, 0.20, 0.25)) == "(0.3, 0.25, 0.2, 0.25)"


def test_float_noise_is_not_printed():
    """A derived float's binary representation tells a reader nothing useful."""
    assert pv.format_value((1.05 - 1.0) / 0.40) == "0.125"
    assert pv.format_value(381_962_855.27) == "381962855.27"
    assert pv.format_value(5.670374419e-8) == "5.670374419e-08"


def test_big_tables_render_as_a_shape_summary():
    """The audit CSV exists to expose a tag; a 4 kB dict in one cell defeats that."""
    big = {f"k{i}": {"a": i, "b": i * 2, "c": "x" * 20} for i in range(12)}
    assert pv.format_value(big) == "<dict: 12 keys>"
    assert pv.format_value(["a" * 30, "b" * 30, "c" * 30]) == "<list: 3 items>"


def test_values_come_from_the_module_not_the_expression():
    """Computed constants must report what they evaluate to."""
    src = "# tag: derived | units: dimensionless\nALPHA: float = M_MAX - 1.0\n"
    rec = pv.scan(src, {"ALPHA": 5.0}).by_name["ALPHA"]
    assert rec.value == "5.0"


# ---------------------------------------------------------------------------
# rendering — CSV and doc tables
# ---------------------------------------------------------------------------

def test_audit_csv_has_a_header_and_one_row_per_record():
    src = (
        "# provenance-block: Demo\n"
        "# tag: placeholder | units: fraction\n"
        "# resolves_by: a study\n"
        "ALPHA: float = 0.5\n"
    )
    text = pv.audit_csv(pv.scan(src, {"ALPHA": 0.5}))
    lines = text.strip().splitlines()

    assert lines[0] == ",".join(pv.CSV_COLUMNS)
    assert len(lines) == 2
    assert lines[1] == "ALPHA,0.5,fraction,placeholder,,,Demo,,,a study,,,,,,"


def test_audit_csv_carries_the_band_and_the_error_direction():
    """The audit file is the whole point of `band` and `errs` being fields."""
    src = (
        "# provenance-block: Demo\n"
        "# tag: bounded | units: h/yr\n"
        "# band: 390–1006 (two instruments)\n"
        "# errs: HIGH. erring high is the mortality-minimising error\n"
        "# resolves_by: the identity route\n"
        "ALPHA: float = 1000.0\n"
    )
    row = pv.audit_csv(pv.scan(src, {"ALPHA": 1000.0})).strip().splitlines()[1]
    assert "390–1006 (two instruments)" in row
    assert "mortality-minimising" in row


def test_audit_csv_carries_the_decider_for_a_normative_constant():
    src = (
        "# provenance-block: Demo\n"
        "# tag: normative | units: dimensionless\n"
        "# decided_by: charter — maximum permitted valuation inequality\n"
        "ALPHA: float = 6.0\n"
    )
    row = pv.audit_csv(pv.scan(src, {"ALPHA": 6.0})).strip().splitlines()[1]
    assert "charter" in row


def test_doc_table_escapes_pipes_in_prose():
    src = (
        "# tag: CHOSEN | units: fraction\n"
        "# resolves_by: either A | or B\n"
        "ALPHA: float = 0.5\n"
    )
    rendered = pv.doc_table(pv.scan(src, {"ALPHA": 0.5}).records)
    body = rendered.splitlines()[2]
    assert r"either A \| or B" in body
    # 5 cells → 6 unescaped delimiters; the prose pipe must not be one of them.
    assert body.count("|") - body.count(r"\|") == 6


def test_doc_table_of_nothing_says_so():
    assert "No constants" in pv.doc_table([])


def test_render_doc_replaces_marked_regions_and_leaves_prose_alone():
    src = (
        "# provenance-block: Demo\n"
        "# tag: physics | units: m2\n"
        "ALPHA: float = 1.0\n"
    )
    scanned = pv.scan(src, {"ALPHA": 1.0})
    doc = (
        "Prose above, which is where the argument lives.\n\n"
        '<!-- provenance:table "Demo" -->\n'
        "stale table content\n"
        "<!-- /provenance:table -->\n\n"
        "Prose below.\n"
    )
    out = pv.render_doc(scanned, doc)

    assert "stale table content" not in out
    assert "`ALPHA`" in out
    assert out.startswith("Prose above, which is where the argument lives.")
    assert out.endswith("Prose below.\n")


def test_render_doc_is_idempotent():
    src = "# provenance-block: Demo\n# tag: physics | units: m2\nALPHA: float = 1.0\n"
    scanned = pv.scan(src, {"ALPHA": 1.0})
    doc = '<!-- provenance:table "Demo" -->\nx\n<!-- /provenance:table -->\n'
    once = pv.render_doc(scanned, doc)
    assert pv.render_doc(scanned, once) == once


def test_doc_markers_lists_requested_blocks_in_order():
    doc = (
        '<!-- provenance:table "Second" -->\na\n<!-- /provenance:table -->\n'
        '<!-- provenance:table "First" -->\nb\n<!-- /provenance:table -->\n'
    )
    assert pv.doc_markers(doc) == ["Second", "First"]


# ---------------------------------------------------------------------------
# live_constants — the denominator of the gate
# ---------------------------------------------------------------------------

def test_live_constants_counts_annotated_module_level_assignments():
    src = (
        "ALPHA: float = 1.0\n"
        "BETA: int = 2\n"
        "def f() -> None:\n"
        "    LOCAL: float = 3.0\n"       # indented — not module level
        "lowercase_name: float = 4.0\n"  # not a constant
        "GAMMA = 5.0\n"                  # unannotated
    )
    assert pv.live_constants(src) == ["ALPHA", "BETA"]


def test_live_constants_reads_the_real_data_module():
    names = pv.live_constants()
    assert "PERSONAL_EOH_BASE" in names
    assert "GUF_PSI_A" in names
    assert len(names) == len(set(names)), "a constant is defined twice in data.py"


# ---------------------------------------------------------------------------
# THE GATE — run against the real data.py, no allowlist
#
# These are what stop provenance coverage from regressing. There is deliberately
# no known-untagged exemption list: the migration landed all 228 constants first,
# so the gate is unconditional from the day it ships. Adding an exemption list
# later would be the regression these tests exist to prevent.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scanned() -> pv.Scan:
    return pv.load()


def test_every_constant_carries_a_tag(scanned):
    """Add a constant to data.py without a '# tag:' block and this fails."""
    tagged = {r.name for r in scanned.records}
    missing = [n for n in pv.live_constants() if n not in tagged]
    assert not missing, (
        f"{len(missing)} data.py constant(s) with no provenance tag block: "
        f"{', '.join(missing)}. Add '# tag: … | units: …' immediately above each "
        "(and 'resolves_by:' if the tag is CHOSEN). See utils/provenance.py."
    )


def test_no_stale_tags(scanned):
    """A deleted or renamed constant must not leave its tag block behind."""
    assert not scanned.orphans, "\n".join(
        f"data.py:{o.line}: "
        + (f"family glob {o.family!r} matched no following constant"
           if o.family else "tag block attached to no constant")
        for o in scanned.orphans
    )


def test_coverage_is_total(scanned):
    tagged, total = pv.coverage(scanned)
    assert tagged == total, f"provenance coverage {tagged}/{total}"


def test_tag_vocabulary_is_closed(scanned):
    """No sixth tag creeps in. 'Physics-adjacent' was one; it is retired."""
    outside = sorted({r.tag for r in scanned.records} - pv.VALID_TAGS)
    assert not outside, (
        f"tag(s) outside the scheme: {outside}. The vocabulary is "
        f"{sorted(pv.VALID_TAGS)} — extend utils.provenance.VALID_TAGS "
        "deliberately, with a docs/parameter_provenance.md entry, or fix the tag."
    )


def test_every_chosen_constant_names_its_epistemic_pointer(scanned):
    """The scheme's central rule, enforced rather than aspired to.

    docs/parameter_provenance.md: "Every CHOSEN constant carries an epistemic
    pointer — the specific evidence or measurement that would move it off CHOSEN."
    """
    bare = [r.name for r in scanned.records
            if r.tag in pv.NEEDS_POINTER and not r.resolves_by and not r.retired]
    assert not bare, (
        f"{len(bare)} CHOSEN constant(s) with no resolves_by: {', '.join(bare)}"
    )


def test_every_constant_declares_units(scanned):
    bare = [r.name for r in scanned.records if not r.units]
    assert not bare, f"{len(bare)} constant(s) with no units: {', '.join(bare)}"


def test_tier_only_qualifies_a_source_bearing_tag(scanned):
    """Tier grades how good a source is; a structural claim has none to grade."""
    bad = [(r.name, r.tag, r.tier) for r in scanned.records
           if r.tier and (r.tier not in pv.TIERS or r.tag not in pv.TIER_ELIGIBLE_TAGS)]
    assert not bad, f"misapplied tier(s): {bad}"


def test_scheme_reports_no_violations(scanned):
    """The aggregate check, sharing one definition with `eoh provenance check`."""
    assert pv.problems(scanned) == []


def test_audit_csv_is_current(scanned):
    """The shipped public-audit CSV must match a fresh render.

    Change a value or a tag without regenerating and this fails:
        python3 utils/eoh_cli.py provenance csv --write
    """
    assert pv.AUDIT_CSV.exists(), f"{pv.AUDIT_CSV} is not shipped"
    assert pv.AUDIT_CSV.read_text(encoding="utf-8") == pv.audit_csv(scanned), (
        "reference/data/constant_provenance.csv is stale — run "
        "'python3 utils/eoh_cli.py provenance csv --write'"
    )


def test_generated_doc_tables_are_current(scanned):
    """THE DRIFT KILLER.

    Every table region in docs/parameter_provenance.md is generated from data.py.
    A value or tag change that skips the doc fails here:
        python3 utils/eoh_cli.py provenance doc --write
    """
    current = pv.PROVENANCE_DOC.read_text(encoding="utf-8")
    assert pv.render_doc(scanned, current) == current, (
        "docs/parameter_provenance.md generated tables are stale — run "
        "'python3 utils/eoh_cli.py provenance doc --write'"
    )


def test_every_block_has_a_doc_table(scanned):
    """A new provenance-block must be given a home in the doc, not left invisible."""
    markers = pv.doc_markers(pv.PROVENANCE_DOC.read_text(encoding="utf-8"))
    orphaned = [b for b in scanned.blocks() if b not in markers]
    assert not orphaned, (
        f"block(s) with no table marker in docs/parameter_provenance.md: "
        f"{orphaned}. Add '<!-- provenance:table \"<name>\" -->' / "
        "'<!-- /provenance:table -->' under a heading."
    )


def test_doc_table_markers_all_name_a_real_block(scanned):
    markers = pv.doc_markers(pv.PROVENANCE_DOC.read_text(encoding="utf-8"))
    unknown = [m for m in markers if m not in scanned.blocks()]
    assert not unknown, f"marker(s) naming no data.py block: {unknown}"


def test_no_constant_is_left_unsectioned(scanned):
    """Every constant sits under a '# provenance-block:' directive."""
    strays = [r.name for r in scanned.records if r.block == pv.UNSECTIONED]
    assert not strays, (
        f"{len(strays)} constant(s) before any provenance-block directive: "
        f"{', '.join(strays)}"
    )


# ---------------------------------------------------------------------------
# prose-restated derived figures — the residual the generated tables cannot see
#
# Generated tables cover the structured fields. Free prose can still go stale, and
# the worst case is a DERIVED PRODUCT restated in a sentence: when
# PERSONAL_EOH_BASE was repriced 1,500 → 1,000, the doc kept printing the
# membership thresholds as 750/1500 h/yr and the per-capita load as 2,213, because
# no value-equality check can see a number that is a product of two constants.
#
# This is a bounded, curated guard over exactly those figures — not a fuzzy scan.
# ---------------------------------------------------------------------------

def _derived_prose_figures() -> dict[str, float]:
    from hours_eoh import data
    # Still in scenarios/, not core/population.py — notes/repo-tidy-backlog.md §1
    # proposes the move but it has not landed.
    from hours_eoh.scenarios.feasibility import age_weight_mean
    w = age_weight_mean()
    return {
        "age-weighted mean w": w,
        "personal EOH per capita": data.PERSONAL_EOH_BASE * w,
        "membership min-hours WARN": data.MEMBERSHIP_MIN_HOURS_WARN_FRACTION
        * data.PERSONAL_EOH_BASE,
        "membership min-hours CRIT": data.MEMBERSHIP_MIN_HOURS_CRIT_FRACTION
        * data.PERSONAL_EOH_BASE,
        "membership vesting WARN": data.MEMBERSHIP_VESTING_WARN_YEARS,
    }


def test_derived_prose_figures_are_the_values_the_doc_prints():
    """Pins the products the doc restates in prose, so a reprice cannot orphan them."""
    figures = _derived_prose_figures()
    # w moved 1.475 → 1.3016 with the AGE_GROUPS elderly revalue (2026-08-10).
    assert figures["age-weighted mean w"] == pytest.approx(1.3016)
    assert figures["personal EOH per capita"] == pytest.approx(1301.6)
    assert figures["membership min-hours WARN"] == pytest.approx(500.0)
    assert figures["membership min-hours CRIT"] == pytest.approx(1000.0)
    # 2 × CONTESTABILITY_VESTING_YEARS, per the constant's own stated derivation
    from hours_eoh import data
    assert figures["membership vesting WARN"] == pytest.approx(
        2 * data.CONTESTABILITY_VESTING_YEARS
    )


def _doc_live_prose() -> str:
    """The doc minus its retag logs.

    A retag log is a historical record and must be free to quote the value it
    replaced — that is what makes the retag auditable. Live prose must not. So the
    stale-figure check reads everything *except* the logs.
    """
    doc = pv.PROVENANCE_DOC.read_text(encoding="utf-8")
    out, skipping = [], False
    for line in doc.splitlines(keepends=True):
        if line.startswith("## "):
            skipping = line.startswith("## Retag log")
        if not skipping:
            out.append(line)
    return "".join(out)


def test_retag_logs_are_excluded_from_the_stale_figure_scan():
    """Guard the guard: if the log headings are renamed, the exclusion must fail loudly."""
    doc = pv.PROVENANCE_DOC.read_text(encoding="utf-8")
    assert "## Retag log" in doc, "no retag log — _doc_live_prose() excludes nothing"
    assert len(_doc_live_prose()) < len(doc), "exclusion removed nothing"


def test_live_prose_does_not_print_the_pre_reprice_derived_figures():
    """The specific stale figures this migration found, kept out of live prose.

    These are DERIVED PRODUCTS restated in sentences — a value-equality check
    cannot see them, which is exactly where the reprice drift hid. If
    `PERSONAL_EOH_BASE` is repriced again these strings change legitimately;
    update them here together with the prose, which is the point of the test:
    the doc and the constant have to move in the same commit.
    """
    prose = _doc_live_prose()
    stale = {
        "750 h/yr": "membership min-hours WARN at the pre-reprice base",
        "= 2,213 h/yr·person": "per-capita personal EOH at the pre-reprice base",
        "490,107,421": "KNOWLEDGE_EOH_BASE before the ε_ref fixed-point re-anchor",
    }
    found = [f"{s!r} ({why})" for s, why in stale.items() if s in prose]
    assert not found, "stale derived figure(s) in live prose: " + "; ".join(found)


def _domain_shares_at(epsilons: tuple[float, ...]) -> dict[float, dict[str, float]]:
    """Domain shares of total EOH, via the same path `arc --domain-shares` prints.

    Deliberately reuses ``utils.arc_cmd._sweep`` rather than recomputing. A second
    implementation here could drift from the CLI, and then the test would be
    checking the doc against a third number nobody sees.
    """
    from utils.arc_cmd import _sweep
    from hours_eoh.data import CAPITAL_STOCK_DEFAULT, TRUST_BASE_TEH

    population = 1_000_000.0
    rows = _sweep(100, population, TRUST_BASE_TEH)
    del CAPITAL_STOCK_DEFAULT  # documented as the sweep's own default

    out: dict[float, dict[str, float]] = {}
    for target in epsilons:
        row = min(rows, key=lambda r: abs(r["epsilon"] - target))
        total = row["total_eoh"] or 1.0
        out[target] = {
            "personal": row["personal_eoh"] / total,
            "infrastructure": row["infra_eoh"] / total,
            "knowledge": row["knowledge_eoh"] / total,
            "ecological": row["eco_eoh"] / total,
        }
    return out


def test_domain_balance_table_restates_the_shares_the_model_computes():
    """The doc's Current table must equal what `arc --domain-shares` prints.

    THIS IS THE TEST THAT WAS MISSING. On 2026-08-10 the table's ε=0.40 and
    ε=0.99 columns were wrong (infrastructure and knowledge were also transposed
    at the top of the arc), and the paragraph above it drew a FINDING from the
    error — that the two moves "pulled in opposite directions" and personal's
    share ended HIGHER at ε=0.99. It ended lower. Both moves cut it.

    A value-equality check over `data.py` cannot see this: the shares are not
    constants, they are computed products restated in a hand-written markdown
    table. That is the residual the coverage gate explicitly does not close, and
    here it produced an inverted conclusion rather than a stale number.

    Tolerance is 1 percentage point — the doc quotes to 0.1pp, and this test
    exists to catch a table that is wrong, not one rounded differently.
    """
    doc = pv.PROVENANCE_DOC.read_text(encoding="utf-8")

    marker = "### Current (post-K-IV, re-anchored twice to the ε_ref fixed point)"
    assert marker in doc, (
        "the Current domain-balance section was renamed — this test no longer "
        "checks anything, so update the marker deliberately"
    )
    section = doc.split(marker, 1)[1].split("### ", 1)[0]

    stated: dict[str, list[float]] = {}
    for line in section.splitlines():
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] in {
            "personal", "infrastructure", "knowledge", "ecological"
        }:
            stated[cells[0]] = [
                float("nan") if c.startswith("<") else float(c.rstrip("%"))
                for c in cells[1:]
            ]

    assert set(stated) == {"personal", "infrastructure", "knowledge", "ecological"}, (
        f"could not parse the Current table; got rows {sorted(stated)}"
    )

    computed = _domain_shares_at((0.0, 0.40, 0.99))
    for domain, values in stated.items():
        for col, target in enumerate((0.0, 0.40, 0.99)):
            claimed = values[col]
            actual = computed[target][domain] * 100.0
            if claimed != claimed:  # "<0.1" cell — assert only that it IS small
                assert actual < 0.1, (
                    f"{domain} at ε={target} is {actual:.2f}%, but the doc says <0.1%"
                )
                continue
            assert abs(claimed - actual) <= 1.0, (
                f"{domain} at ε={target}: doc says {claimed:.1f}%, model computes "
                f"{actual:.1f}%. Re-run `eoh arc --domain-shares --points 100` and "
                f"update the table AND the prose above it — the prose draws a "
                f"conclusion from these numbers."
            )


# --- the instance tag -------------------------------------------------------


def test_instance_requires_both_what_you_supply_and_what_shipped():
    """`instance` must not become a place to hide an unmeasured default.

    The tag's whole risk is that it launders "35B is a desk figure" into "the
    institution will supply it". `default:` is the field that stops it, so a
    missing one is a scheme violation, not a style lapse.
    """
    src = (
        "# provenance-block: Demo\n"
        "# tag: instance | units: TEH\n"
        "# supplied_by: your capital inventory\n"
        "ALPHA: float = 1.0\n"
    )
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no default" in i for i in issues), issues

    src_no_supplier = (
        "# provenance-block: Demo\n"
        "# tag: instance | units: TEH\n"
        "# default: a desk figure\n"
        "ALPHA: float = 1.0\n"
    )
    issues = pv.problems(pv.scan(src_no_supplier, {"ALPHA": 1.0}))
    assert any("no supplied_by" in i for i in issues), issues


def test_instance_may_not_claim_a_resolves_by():
    """No dataset this framework could gather settles another jurisdiction's value."""
    src = (
        "# provenance-block: Demo\n"
        "# tag: instance | units: TEH\n"
        "# supplied_by: your capital inventory\n"
        "# default: a desk figure\n"
        "# resolves_by: some future study\n"
        "ALPHA: float = 1.0\n"
    )
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("claims a resolves_by" in i for i in issues), issues


def test_supplier_fields_are_refused_on_other_tags():
    src = (
        "# provenance-block: Demo\n"
        "# tag: placeholder | units: TEH\n"
        "# resolves_by: a study\n"
        "# supplied_by: your inventory\n"
        "ALPHA: float = 1.0\n"
    )
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("supplied_by declared on a 'placeholder'" in i for i in issues), issues


def test_every_instance_constant_names_its_intake_path_and_its_default(scanned):
    """The real data.py, with no allowlist."""
    for r in scanned.records:
        if r.tag == "instance":
            assert r.supplied_by, f"{r.name}: instance with no supplied_by"
            assert r.default, f"{r.name}: instance with no default"


# --- superseded_by ----------------------------------------------------------


def test_superseded_by_must_name_something_that_exists():
    src = (
        "# provenance-block: Demo\n"
        "# tag: placeholder | units: TEH\n"
        "# superseded_by: NO_SUCH_CONSTANT\n"
        "ALPHA: float = 1.0\n"
    )
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("neither a constant in data.py nor a module" in i for i in issues), issues


def test_superseded_by_accepts_a_module_path():
    """Sometimes a whole measured pathway replaces a constant, not another constant."""
    src = (
        "# provenance-block: Demo\n"
        "# tag: placeholder | units: TEH\n"
        "# superseded_by: hours_eoh.scenarios.measured\n"
        "ALPHA: float = 1.0\n"
    )
    assert not pv.problems(pv.scan(src, {"ALPHA": 1.0}))


def test_retired_constants_have_no_operative_consumers(scanned):
    """`retired` is verified, not asserted.

    A constant excluded from the debt count on the grounds that it governs no
    current output must actually govern none. This check falsified two of the
    four retirement claims made on 2026-08-09 — `DEFAULT_SEGMENTS` was the live
    default in `core/multipliers.py`, and `SKILL_DECAY_RATE` was still read by
    `core/eoh_generation.py` — and both were returned to the debt count rather
    than the check being loosened.
    """
    for r in scanned.records:
        if not r.retired:
            continue
        hits = pv.operative_consumers(r.name)
        assert not hits, (
            f"{r.name} is marked superseded_by {r.superseded_by!r} but "
            f"{', '.join(pv.OPERATIVE_LAYERS)} still read it at "
            f"{', '.join(hits[:5])}. Either rewire those callers to the "
            "replacement, or drop superseded_by and count it as debt."
        )


# --- the guides -------------------------------------------------------------
#
# `docs/parameter_provenance.md` is safe by construction: its tables are
# GENERATED from data.py. `docs/guides/` is not — it is hand-written prose, it
# is the first thing an outside analyst reads, and until 2026-08-09 it advertised
# `PERSONAL_EOH_BASE = 1500` three days after the reprice to 1000, told
# institutions to keep six constants at their defaults as "physics" when only two
# constants in the whole repo are physics, and pointed them at a deprecated
# parameter. None of that was catchable by the existing gate, because the
# existing gate never looked outside data.py.


def _guide_docs():
    return sorted(pv.GUIDES_DIR.glob("*.md"))


def test_there_are_guides_to_check():
    """Guard the guard: an empty glob must not read as a pass."""
    assert _guide_docs(), f"no guides found under {pv.GUIDES_DIR}"


@pytest.mark.parametrize("path", _guide_docs(), ids=lambda p: p.name)
def test_guides_do_not_quote_stale_constant_values(path, scanned):
    """Every `NAME = number` claim in a guide must match data.py.

    This is a value-equality check, so it sees the class of drift that actually
    happened — a constant repriced in data.py while the sentence naming it in a
    guide stayed put. It cannot see a derived product restated in prose; that
    residual is covered for the provenance doc by the curated stale-figure test
    above, and remains a human problem here, which the guides say plainly.
    """
    stale = pv.stale_doc_claims(path.read_text(encoding="utf-8"), scanned)
    assert not stale, f"{path.name} quotes stale value(s): " + "; ".join(stale)


@pytest.mark.parametrize("path", _guide_docs(), ids=lambda p: p.name)
def test_guides_do_not_use_the_retired_tag_vocabulary(path):
    """The binary Physics|Calibration scheme is retired; guides must not teach it.

    It is not a cosmetic rename. That scheme is what let six constitutional
    commitments and desk estimates be filed as "physics" and handed to an
    analyst as things not to touch.
    """
    text = path.read_text(encoding="utf-8")
    banned = {
        "physics/calibration split": "the retired binary scheme",
        "physics parameters)": "presents a tag as a class of parameter",
        "calibration parameters)": "presents a tag as a class of parameter",
    }
    found = [f"{s!r} ({why})" for s, why in banned.items() if s in text.lower()]
    assert not found, f"{path.name} uses retired provenance vocabulary: " + "; ".join(found)


@pytest.mark.parametrize("path", _guide_docs(), ids=lambda p: p.name)
def test_guides_do_not_name_constants_that_no_longer_exist(path, scanned):
    """A guide pointing at a deleted or renamed constant sends an analyst nowhere."""
    text = path.read_text(encoding="utf-8")
    known = set(scanned.by_name)
    # Only backticked ALL-CAPS identifiers, so prose words and headings are safe.
    named = set(re.findall(r"`([A-Z][A-Z0-9_]{4,})`", text))
    # Names that look like constants but belong to other namespaces.
    exempt = {"AGE_GROUPS_DEFAULT", "TEH", "EOH", "GUF", "NLSA", "ATUS", "CHOSEN"}
    missing = sorted(
        n for n in named - known - exempt
        # A trailing underscore is a PREFIX reference ("prefixed `CANONICAL_`"),
        # not a claim that a constant by that name exists.
        if "_" in n and not n.endswith("_")
    )
    assert not missing, (
        f"{path.name} names constant(s) not in data.py: {', '.join(missing)}"
    )
