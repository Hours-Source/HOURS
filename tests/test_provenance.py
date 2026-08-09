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
    src = "# tag: Physics-adjacent | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("is not in the scheme" in p for p in issues)


def test_chosen_without_a_pointer_is_a_violation():
    """The scheme's central rule: CHOSEN must name what would settle it."""
    src = "# tag: CHOSEN | units: fraction\nALPHA: float = 1.0\n"
    issues = pv.problems(pv.scan(src, {"ALPHA": 1.0}))
    assert any("no resolves_by" in p for p in issues)


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
        "# tag: CHOSEN | units: fraction\n"
        "# resolves_by: a study\n"
        "ALPHA: float = 0.5\n"
    )
    text = pv.audit_csv(pv.scan(src, {"ALPHA": 0.5}))
    lines = text.strip().splitlines()

    assert lines[0] == ",".join(pv.CSV_COLUMNS)
    assert len(lines) == 2
    assert lines[1] == "ALPHA,0.5,fraction,CHOSEN,,,Demo,a study,"


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
            if r.tag in pv.NEEDS_POINTER and not r.resolves_by]
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
    assert figures["age-weighted mean w"] == pytest.approx(1.475)
    assert figures["personal EOH per capita"] == pytest.approx(1475.0)
    assert figures["membership min-hours WARN"] == pytest.approx(500.0)
    assert figures["membership min-hours CRIT"] == pytest.approx(1000.0)
    # 2 × CONTESTABILITY_VESTING_YEARS, per the constant's own stated derivation
    from hours_eoh import data
    assert figures["membership vesting WARN"] == pytest.approx(
        2 * data.CONTESTABILITY_VESTING_YEARS
    )


def test_doc_does_not_print_the_pre_reprice_derived_figures():
    """The specific stale figures this migration found, kept out.

    If PERSONAL_EOH_BASE is repriced again these strings change legitimately —
    update them here together with the prose, which is the point: the test forces
    the doc and the constant to move in the same commit.
    """
    doc = pv.PROVENANCE_DOC.read_text(encoding="utf-8")
    stale = {
        "750 h/yr": "membership min-hours WARN at the pre-reprice base",
        "= 2,213 h/yr·person": "per-capita personal EOH at the pre-reprice base",
        "490,107,421": "KNOWLEDGE_EOH_BASE before the ε_ref fixed-point re-anchor",
    }
    found = [f"{s!r} ({why})" for s, why in stale.items() if s in doc]
    assert not found, "stale derived figure(s) in the doc: " + "; ".join(found)
