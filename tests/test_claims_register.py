"""
The claims register: CLAUDE.md's checkable assertions, checked.

WHY THIS EXISTS. This repo's most repeated failure is not a wrong number — it is
a RIGHT number that stopped being right and was never revisited. Across two
weeks it happened eight times that we know of:

    2026-08-29  three stale `STILL OPEN` lines in this very file — the GUF
                two-call pattern (closed by the assembly point), Phase 4e
                (adopted the following day), and "23 of the 34" shadow
                constants (every named item done in batches 2-3)
    2026-08-29  five retracted claims still shipping in docstrings and runtime
                verdicts, incl. `land_stewardship` printing "BELOW the anchor"
                for eleven days after CLAUDE.md recorded it as 223x ABOVE

Every one was true when written. None was revisited when the work landed.

THE REPO ALREADY SOLVED THIS ONCE, FOR DATASETS. `test_dataset_governance.py`
sha256-fingerprints each review-worthy claim so a regenerated dataset with a
changed method breaks the build until the constants are re-checked, with the
recorded lesson: *"a review that cannot go stale is not a control."* This is
that pattern applied to the file a new session reads first.

WHAT IT DELIBERATELY DOES NOT DO. CLAUDE.md is part status, part changelog, and
most of it is narrative. A gate that fired on prose edits would be suppressed
within a week, which is worse than no gate — so only claims of a DECLARED shape
are checked, and the historical record is left alone. That distinction is load
bearing: `shadow 57 -> 46 -> 38` are three correct historical entries and a
naive "every number must match live" check would fire on all of them.

STATED GAPS, because an undocumented gap makes a checker read as stronger than
it is (the repo's own rule):

  * The suite's own test count and mypy's file count are NOT checked. Counting
    passing tests from inside the suite is circular, and mypy needs a
    subprocess. They are the two figures most likely to drift, and this gate
    does not catch them.
  * Only the claims in LIVE_CLAIMS are checked. A new claim is not
    automatically covered — but `test_every_open_item_is_declared` means a new
    OPEN item cannot be added silently, which is where the staleness has
    actually occurred.
  * A claim whose ANCHOR text is edited fails loudly rather than silently
    passing. That is intended: it forces a re-check, exactly as the dataset
    fingerprints do.
  * The corpus is CLAUDE.md plus `record/*.md`. A claim moved to a file
    OUTSIDE those two homes stops being checked, silently. `record/README.md`
    is the index and `tests/test_record_index.py` keeps it honest, but nothing
    stops a third location being invented.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from typing import Callable

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
RECORD_DIR = REPO_ROOT / "record"


@dataclass(frozen=True)
class Claim:
    """A statement in CLAUDE.md that the code can answer."""

    anchor: str                 #: exact substring locating the claim
    check: Callable[[], bool]   #: the predicate the claim asserts
    why: str                    #: what goes wrong if it drifts


def _text() -> str:
    """
    CLAUDE.md PLUS every `record/*.md`.

    The status log was split by subject area on 2026-09-03 (CLAUDE.md was over
    the 150k-char context limit at 304.5k). A claim does not stop being checked
    because it moved into `record/` — reading CLAUDE.md alone after the split
    would have silently retired six anchors and three of the five closed open
    items, which is precisely the staleness this gate exists to forbid.
    """
    parts = [CLAUDE_MD.read_text(encoding="utf-8")]
    parts += [p.read_text(encoding="utf-8")
              for p in sorted(RECORD_DIR.glob("*.md"))]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# The register
# ---------------------------------------------------------------------------

def _standing_default_is_guf() -> bool:
    import inspect
    from hours_eoh.core.eoh_generation import ecological_eoh
    return (inspect.signature(ecological_eoh)
            .parameters["standing_response"].default == "guf")


def _health_default_is_guf() -> bool:
    import inspect
    from hours_eoh.core.eoh_generation import ecological_eoh
    return (inspect.signature(ecological_eoh)
            .parameters["health_response"].default == "guf")


def _domain_is_empty_by_default() -> bool:
    from hours_eoh.core.eoh_generation import ecological_eoh
    return ecological_eoh(0.70, 0.40, area_hectares=1.65e6) == 0.0


def _provenance_is_complete() -> bool:
    from utils import provenance as pv
    tagged, total = pv.coverage(pv.scan(pv.DATA_PY.read_text(encoding="utf-8")))
    return tagged == 304 and total == 304


def _shadow_count_is_33() -> bool:
    from utils import provenance as pv
    return len([s for s in pv.shadow_constants() if not s.bound]) == 33


def _guf_is_a_separate_revenue_line() -> bool:
    import inspect
    from hours_eoh.core.fiscal import trust_management
    p = inspect.signature(trust_management).parameters
    return "guf_revenue" in p and p["guf_revenue"].default == 0.0


def _remote_land_pays_nothing() -> bool:
    from hours_eoh.land.guf import ground_use_fee
    return all(
        ground_use_fee(area_slu=1.0, location_value=0.0,
                       use_category="residential_primary",
                       epsilon=e)["guf_applied"] == 0.0
        for e in (0.0, 0.40, 0.99)
    )


def _conservation_credit_is_clipped() -> bool:
    from hours_eoh.land.guf import ground_use_fee
    # 10 SLU = 0.1 ha. At 1 SLU the per-parcel term (adopted 2026-08-30)
    # exceeds the credit, which is the minimum-viable-conservation-parcel
    # consequence of pricing fragmentation, not a failure of the clamp.
    r = ground_use_fee(area_slu=10.0, location_value=0.75,
                       use_category="conservation", epsilon=0.0)
    return r["guf_formula"] < 0.0 and r["guf_applied"] == 0.0


# --- 2026-09-01: the Phase 2 adoption and the value-anchor hardening ----------

def _per_component_is_the_default() -> bool:
    import inspect
    from hours_eoh.core.eoh_fulfillment import (
        eoh_to_teh_pipeline, human_eoh_per_domain, personal_human_fraction)
    return all(
        inspect.signature(fn).parameters["automation_response"].default
        == "per_component"
        for fn in (personal_human_fraction, human_eoh_per_domain,
                   eoh_to_teh_pipeline)
    )


def _ecological_intensity_is_convention() -> bool:
    from utils import provenance as pv
    scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
    rec = next(r for r in scan.records if r.name == "ECOLOGICAL_INTENSITY_BASE")
    return rec.tag == "convention"


def _there_is_exactly_one_mint() -> bool:
    import ast
    root = REPO_ROOT
    sites = []
    for layer in ("core", "land", "scenarios"):
        for path in sorted((root / "hours_eoh" / layer).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "teh_created"):
                    sites.append(path)
    return len(sites) == 1


def _teh_supply_is_orphaned_and_refuses_the_shipped_trajectory() -> bool:
    import ast
    from hours_eoh.core.eoh_fulfillment import teh_supply
    from hours_eoh.core.simulation import make_economy_state, run_simulation
    root = REPO_ROOT
    for layer in ("core", "land", "scenarios", "research"):
        for path in sorted((root / "hours_eoh" / layer).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "teh_supply"):
                    return False
    rows = run_simulation(make_economy_state(), n_periods=40)["period_results"]
    try:
        teh_supply(sum(r["teh_created"] for r in rows),
                   sum(r["teh_destroyed"] for r in rows))
    except ValueError:
        return True
    return False


def _no_constant_is_currency_denominated() -> bool:
    import re
    from utils import provenance as pv
    money = re.compile(r"\b(usd|dollar|eur|currency|wage)\b|\$", re.I)
    scan = pv.scan(pv.DATA_PY.read_text(encoding="utf-8"))
    return not any(r.units and money.search(r.units) for r in scan.records)


def _the_uniform_ceiling_is_exactly_one() -> bool:
    import inspect
    from hours_eoh.core.eoh_fulfillment import observable_epsilon_ceiling
    from hours_eoh.core.eoh_generation import total_eoh
    from hours_eoh.core.trajectory import canonical_physical_state
    accepted = inspect.signature(total_eoh).parameters
    dom = total_eoh(**{k: v for k, v in canonical_physical_state(0.99).items()
                       if k in accepted})
    return (abs(observable_epsilon_ceiling(dom, "uniform") - 1.0) < 1e-12
            and observable_epsilon_ceiling(dom, "per_component") < 1.0)


def _human_fraction_is_the_real_share() -> bool:
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    r = eoh_to_teh_pipeline(epsilon=0.99)
    return (abs(r["human_fraction"] - r["human_eoh"] / r["total_eoh"]) < 1e-12
            and r["human_fraction"] > r["uniform_split_factor"])


def _the_wiring_ratchet_is_twelve() -> bool:
    from tests.test_parameter_wiring import _DECLARED
    return len(_DECLARED) == 12


#: Every live claim, its predicate, and what drifts if it goes unchecked.
#: HISTORICAL entries are deliberately absent — they were true when written and
#: are meant to stay as written.
LIVE_CLAIMS: tuple[Claim, ...] = (
    Claim(
        anchor='`ecological_standing_response` defaults to `"guf"`',
        check=_standing_default_is_guf,
        why="Phase 4f's adoption. This exact claim went stale for 4e once already.",
    ),
    Claim(
        anchor='`ecological_health_response` now also defaults to `"guf"`',
        check=_health_default_is_guf,
        why="Phase 4e's adoption — the line that WAS stale, for one day, in this file.",
    ),
    Claim(
        anchor="`ecological = 0.0` on every shipped path",
        check=_domain_is_empty_by_default,
        why=(
            "the partition's headline consequence. If a stock ever ships by "
            "default this becomes false and the domain-balance narrative with it."
        ),
    ),
    Claim(
        anchor="provenance 304/304",
        check=_provenance_is_complete,
        why=(
            "the coverage figure quoted to institutions; 265 -> 288 -> 292 -> 294 -> 296 -> 297 -> 299 -> 300. "
            "Anchored to the CURRENT entry, not a historical one: the old anchor "
            "matched six lines, five of them history, so the claim was checking a "
            "live number against text that must never be updated."
        ),
    ),
    Claim(
        anchor="shadow ratchet at 33",
        check=_shadow_count_is_33,
        why="the ratchet's bound. Quoted beside the 100% figure it qualifies.",
    ),
    Claim(
        anchor="GUF IS ITS OWN REVENUE LINE AND IS DELIBERATELY NOT FOLDED INTO THE LEVY",
        check=_guf_is_a_separate_revenue_line,
        why=(
            "`guf_stress` folded it into the levy for months. If the parameter "
            "goes, the claim silently reverts to the thing that was wrong."
        ),
    ),
    Claim(
        anchor="a parcel at L=0 pays **exactly 0.0 at every ε**",
        check=_remote_land_pays_nothing,
        why="the NLSA §4.4 boundary condition, and the reason that item is closed.",
    ),
    Claim(
        anchor="`guf_applied == 0.0` with `floor_applied=True`",
        check=_conservation_credit_is_clipped,
        why=(
            "a live charter question. If the floor is ever lifted this becomes "
            "false, and the open decision would read as still open when it is not."
        ),
    ),
    # --- 2026-09-01 -------------------------------------------------------
    Claim(
        anchor="`automation_response` defaults to **`per_component`**",
        check=_per_component_is_the_default,
        why=(
            "Phase 2's adoption. The flip is the care contradiction's fix and "
            "reverting it silently would restore a known contradiction as the "
            "default while every arc figure kept its new value."
        ),
    ),
    Claim(
        anchor="`ECOLOGICAL_INTENSITY_BASE` retagged `derived` → `convention`",
        check=_ecological_intensity_is_convention,
        why=(
            "the tag said `derived` while its own pointer said SUPERSEDED. If it "
            "drifts back the two halves disagree again, which is the state the "
            "sign-off was asked for."
        ),
    ),
    Claim(
        anchor="exactly ONE mint call site across `core/`, `land/` and `scenarios/`",
        check=_there_is_exactly_one_mint,
        why=(
            "the whole defence against labour vouchers. A second mint path is a "
            "monetary-architecture change, not a refactor."
        ),
    ),
    Claim(
        anchor="It has ZERO callers, and it raises on the shipped model's own canonical trajectory",
        check=_teh_supply_is_orphaned_and_refuses_the_shipped_trajectory,
        why=(
            "`teh_supply` states the bound the value-anchor argument WANTS and "
            "describes an economy with no endowment. A caller appearing, or the "
            "guard ceasing to fire, means the two accounts have silently merged."
        ),
    ),
    Claim(
        anchor="**no constant in `data.py` is denominated in currency**",
        check=_no_constant_is_currency_denominated,
        why=(
            "the correction that 'no price in the chain' distinguishes nothing. "
            "A currency-denominated constant would make it a real distinction "
            "again and needs its own review."
        ),
    ),
    Claim(
        anchor="against **exactly 1.000** under `uniform`",
        check=_the_uniform_ceiling_is_exactly_one,
        why=(
            "the arc endpoint is a CONSEQUENCE of the automation floors, not a "
            "convention. If the uniform ceiling stopped being 1.0, the floors "
            "would no longer be what caps it and the derivation would be lost."
        ),
    ),
    Claim(
        anchor="**`human_fraction` now means what it says**",
        check=_human_fraction_is_the_real_share,
        why=(
            "it reported the split factor and understated human labour 5.8x at "
            "the documented entry point. Reverting is invisible except here."
        ),
    ),
    Claim(
        anchor="Ratchet 10 → 12 on pure coverage",
        check=_the_wiring_ratchet_is_twelve,
        why=(
            "the rise was COVERAGE, not new debt — the entry point became "
            "probeable. If the count moves again the reason must be recorded, "
            "because no counter can tell an honest rise from a fresh copy."
        ),
    ),
)

# ---------------------------------------------------------------------------

class TestEveryLiveClaimStillHolds:

    @pytest.mark.parametrize("claim", LIVE_CLAIMS, ids=lambda c: c.anchor[:44])
    def test_the_claim_is_still_in_the_file(self, claim: Claim) -> None:
        """
        A claim that has been edited away is not thereby retired — it is
        unreviewed. Failing here forces the register and the file back into
        agreement, which is the dataset-fingerprint discipline.
        """
        assert _text().count(claim.anchor) >= 1, (
            f"CLAUDE.md no longer contains this claim:\n  {claim.anchor!r}\n"
            f"If it was deliberately removed, remove it from LIVE_CLAIMS too. "
            f"Why it is registered: {claim.why}"
        )

    @pytest.mark.parametrize("claim", LIVE_CLAIMS, ids=lambda c: c.anchor[:44])
    def test_the_code_still_agrees_with_the_claim(self, claim: Claim) -> None:
        assert claim.check(), (
            f"CLAUDE.md asserts this and the code no longer agrees:\n"
            f"  {claim.anchor!r}\n"
            f"Update the file — a status note that outlives the decision it "
            f"describes misdirects the next session, which reads this file "
            f"first. Why it is registered: {claim.why}"
        )


class TestOpenItemsCannotGoStaleSilently:
    """
    The specific failure this gate was built for. Three `STILL OPEN` lines were
    stale at the 2026-08-29 merge review — each true when written, none
    revisited when the work landed.
    """

    #: An open item is either CLOSED (struck through, kept visible so the shape
    #: stays legible) or genuinely open and named here with what would settle
    #: it. A third state — open, unlisted, and quietly false — is what this
    #: forbids.
    DECLARED_OPEN: dict[str, str] = {
        "THE TEN RATIOS": (
            "needs occupational data coded by the land use it serves, or a "
            "change to the fee's definition. Both censuses measure disturbance "
            "rather than servicing, so adopting either would repeat the "
            "SKILL_WORKING_LIFE_YEARS wrong-instrument error."
        ),
    }

    #: An ITEM is a bullet whose bold lead IS the marker. Prose that merely
    #: mentions the phrase mid-sentence is not an item.
    #:
    #: THE FIRST VERSION MATCHED THE SUBSTRING ANYWHERE AND FIRED ON ITS OWN
    #: DOCUMENTATION — the CLAUDE.md entry describing this gate says "three
    #: stale `STILL OPEN` lines", and a case-sensitive exclusion for that exact
    #: phrase missed it the moment the prose was rewritten in lower case. That
    #: is precisely the failure this module's docstring warns about: a gate that
    #: fires on prose edits gets suppressed within a week, which is worse than
    #: no gate. Anchoring to the bullet structure removes the whole class rather
    #: than adding another exclusion.
    _ITEM = re.compile(r"^- \*\*(~~)?STILL OPEN")

    def _open_lines(self) -> list[str]:
        out = []
        for ln in _text().splitlines():
            m = self._ITEM.match(ln)
            if m and not m.group(1):   # group(1) is the ~~ strike-through
                out.append(ln)
        return out

    def test_every_open_item_is_declared(self) -> None:
        undeclared = [
            ln for ln in self._open_lines()
            if not any(k in ln for k in self.DECLARED_OPEN)
        ]
        assert not undeclared, (
            "these items are marked STILL OPEN but are not declared in "
            "DECLARED_OPEN with what would settle them:\n  "
            + "\n  ".join(ln[:110] for ln in undeclared)
            + "\n\nEither declare it, or strike it through if it is closed."
        )

    def test_every_declaration_names_an_item_that_exists(self) -> None:
        """
        A declaration for an item nobody has is a permission nobody reviews —
        the `unused_innocuous_names` lesson, which this repo learned when two
        allowlist entries went stale within an hour of shipping.
        """
        lines = self._open_lines()
        stale = [k for k in self.DECLARED_OPEN
                 if not any(k in ln for ln in lines)]
        assert not stale, (
            f"DECLARED_OPEN names items no longer marked STILL OPEN: {stale}. "
            "If they were closed, remove them here too."
        )

    def test_every_declaration_says_what_would_settle_it(self) -> None:
        for item, why in self.DECLARED_OPEN.items():
            assert len(why) > 60, (
                f"{item!r} is declared open without saying what would close it. "
                "An open item with no resolution path is a note, not an item."
            )

    def test_closed_items_stay_visible(self) -> None:
        """
        Struck through rather than deleted. The shape — a status line outliving
        its decision — is the finding, and deleting the evidence would remove
        the only reason anyone believes this gate is needed.
        """
        assert _text().count("~~STILL OPEN") >= 3


class TestTheGateIsHonestAboutItself:

    def test_the_register_is_not_empty(self) -> None:
        """An empty register passes every check and guards nothing."""
        assert len(LIVE_CLAIMS) >= 8

    def test_every_claim_says_why_it_is_registered(self) -> None:
        for c in LIVE_CLAIMS:
            assert len(c.why) > 40, f"{c.anchor[:40]!r} does not say what drifts"

    def test_the_stated_gaps_are_still_stated(self) -> None:
        """
        The module docstring names what this gate does NOT check — the suite's
        own test count and mypy's file count, the two figures most likely to
        drift. If that admission is edited out, the gate starts reading as
        stronger than it is, which is the failure it exists to prevent.
        """
        doc = __doc__ or ""
        assert "STATED GAPS" in doc
        assert "test count" in doc and "mypy" in doc


# ---------------------------------------------------------------------------
# The kind of an open item
# ---------------------------------------------------------------------------

class TestEveryOpenItemIsTyped:
    """
    An `## Open` section is not a work queue, and treating it as one is how a
    gate manufactures work the repo has already decided against.

    WHAT THE MEASUREMENT FOUND. The 54 bullets under `## Open` are five
    different things. CLAUDE.md's twelve say of themselves "An index, not the
    items themselves"; of the 42 in `record/`, five more are pure
    cross-references, so one item was reachable three ways (`teh_supply`, in
    CLAUDE.md, theory.md and verification.md). And four are items the repo has
    explicitly decided NOT to close: "Anchor comparison Phases 1-3 are HELD
    DELIBERATELY... Do not build without a reason to", "declared limits, not
    gaps to close opportunistically", "Reported, not bound - binding would
    ASSERT... a theory claim". A session told there are "54 open items" reads
    four do-not-build decisions as a backlog.

    So the kind is the part a reader acts on, and it is now stated:

        gap      work; a named acquisition or build closes it
        held     decided NOT to do; BUILDING it is the error
        caveat   a standing property of the model, not work at all
        person   waiting on a human decision; no code state changes
        pointer  the item is filed elsewhere; follow the link

    THE MARKER IS THE `*(gated)*` IDIOM the area files already use in 21
    places, so this reads native rather than as a second notation.

    WHY THIS SECTION AND NOT THE OTHER ONE. `TestTheOpenItemsAreDeclared`
    above matches `- **STILL OPEN`, and all six of those lines are sub-bullets
    under `## History` - where the marker correctly means "open as of this
    entry", and where history is verbatim and must not be retyped. That gate
    has never seen an `## Open` section. This one covers the convention
    `record/README.md` rule 2 actually establishes; the two do not overlap.

    STATED GAPS, because a checker that reads as broader than it is licenses
    not looking:

      * THE KIND IS AUTHORED, NOT DERIVED. Nothing here stops a `gap` being
        retyped `held` to silence it. What makes that hold is that retyping is
        a visible act in a diff - the same argument `record/verification.md`
        makes for leaving the shadow ratchet's bound un-meta-ratcheted. That
        is the real ceiling on this mechanism and it is not closeable from
        inside.
      * NO PREDICATE IS CHECKED YET. This gate says an item is TYPED. It does
        not say a `gap` is still open, that nobody built a `held`, or that a
        `caveat`'s figure is current - the settle path still declared in
        `record/verification.md § Open`. Typing is what makes those predicates
        writable, because the kind decides which DIRECTION each one points; it
        is not a substitute for them.
      * CLAUDE.md's `## Open` IS NOT SCANNED FOR KINDS. It is an index, and
        it already types its rows by group heading ("Held deliberately - do not
        build without a reason to"), so nothing here checks the kind of those
        rows. `TestClosingAnItemLeavesEvidence` below DOES read them: a closure
        written in the index is still a closure and must show its evidence.
    """

    KINDS = frozenset({"gap", "held", "caveat", "person", "pointer"})
    _KIND = re.compile(r"\*\((gap|held|caveat|person|pointer)\)\*")
    _ANYMARK = re.compile(r"\*\(([a-z]+)\)\*")

    def _items(self) -> list[tuple[str, str]]:
        """`[(file, bullet text)]` for every bullet under an `## Open` heading."""
        out: list[tuple[str, str]] = []
        for path in sorted(RECORD_DIR.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            heads = [i for i, l in enumerate(lines)
                     if l.strip().lower().startswith("## open")]
            if not heads:
                continue
            start = heads[0]
            end = next((i for i in range(start + 1, len(lines))
                        if lines[i].startswith("## ")), len(lines))
            buf: list[str] = []
            for i in range(start + 1, end + 1):
                line = lines[i] if i < end else "- "
                if line.startswith("- ") and buf:
                    out.append((path.name, " ".join(buf)))
                    buf = []
                if line.startswith("- ") or (buf and line.startswith("  ")):
                    buf.append(line.strip())
        return out

    def test_every_open_item_states_its_kind(self) -> None:
        untyped = [(f, t[:100]) for f, t in self._items()
                   if not self._KIND.search(t)]
        assert not untyped, (
            "these `## Open` items carry no kind marker:\n  "
            + "\n  ".join(f"{f}: {t}" for f, t in untyped)
            + f"\n\nAdd one of {sorted(self.KINDS)} in the `*(kind)*` form, "
            "after the bullet's bold lead. `held` means BUILDING it is the "
            "error, which is the distinction this exists for."
        )

    def test_no_item_claims_two_kinds(self) -> None:
        """One item, one kind. Two is the shape that let `psi` diverge from
        `psi_applied` - two accounts of one quantity."""
        doubled = [(f, t[:80]) for f, t in self._items()
                   if len(self._KIND.findall(t)) > 1]
        assert not doubled, f"items carrying more than one kind: {doubled}"

    def test_the_vocabulary_is_closed(self) -> None:
        """
        An open vocabulary is not a vocabulary. `*(gated)*` is the pre-existing
        marker and is deliberately allowed through - it says a LIVE-STATE line
        is checked, which is a different axis from an open item's kind.
        """
        allowed = self.KINDS | {"gated"}
        stray = {m for _, t in self._items()
                 for m in self._ANYMARK.findall(t)} - allowed
        assert not stray, (
            f"unknown marker(s) in an `## Open` item: {sorted(stray)}. "
            f"The vocabulary is {sorted(self.KINDS)} - widen it deliberately "
            "or fix the typo."
        )

    def test_every_pointer_names_a_file_that_exists(self) -> None:
        """
        A `pointer` whose target is gone is the dangling half of a duplicate -
        what `test_every_declaration_names_an_item_that_exists` catches for
        declarations, applied to the five items filed in two places.
        """
        dangling = []
        for f, t in self._items():
            if "*(pointer)*" not in t:
                continue
            targets = re.findall(r"\[([a-z_]+\.md)[^\]]*\]", t)
            if not targets:
                dangling.append((f, t[:80], "names no target file"))
            for name in targets:
                if not (RECORD_DIR / name).is_file():
                    dangling.append((f, t[:80], f"target {name} does not exist"))
        assert not dangling, f"pointer items with no live target: {dangling}"

    def test_the_scan_is_not_vacuous(self) -> None:
        """
        A scan over zero bullets passes and guards nothing - and this one runs
        over a directory glob, so a rename could silently empty it. The counts
        are lower bounds, not pins: items close, and the gate must not fire
        when they do.
        """
        items = self._items()
        assert len(items) >= 30, f"only {len(items)} open items found - glob broken?"
        kinds = [m.group(1) for _, t in items if (m := self._KIND.search(t))]
        assert kinds.count("held") >= 1, (
            "no `held` item found. If every do-not-build decision really has "
            "been retired, delete this assertion deliberately - the kind that "
            "justifies the whole mechanism is the one that must not vanish "
            "quietly."
        )
        assert len(set(kinds)) >= 3, f"only {sorted(set(kinds))} in use"

    def test_the_stated_gaps_are_still_stated(self) -> None:
        """The admissions above are load-bearing: without them this gate reads
        as staleness detection, which is exactly what it does NOT do yet."""
        doc = self.__doc__ or ""
        assert "STATED GAPS" in doc
        assert "AUTHORED, NOT DERIVED" in doc
        assert "NO PREDICATE IS CHECKED YET" in doc


class TestClosingAnItemLeavesEvidence:
    """
    The transition rules from `record/README.md` convention 2, enforced.

    An open item has three ways to stop being open, and only one of them is
    honest. It can be STRUCK (closed, kept visible), it can be RETYPED (a `gap`
    becoming `held` is work disappearing without anything landing), or it can be
    quietly deleted — which removes the only reason anyone believes the item was
    real. These check the first two. Nothing here can check deletion; git can.

    WHY `held` IS THE ONE THAT NEEDS A REASON. Every other transition leaves a
    trace someone would notice: a struck line is visible, a closed gap has a
    history entry. Retyping a `gap` to `held` looks like housekeeping and means
    "we decided not to do this" — so the cost of making that move is writing
    down why. All four `held` items already do; this makes that a floor rather
    than a habit.

    STATED GAPS:

      * THE STRUCK-ITEM CHECKS GUARD ONE ITEM TODAY. `## Open` sections in
        `record/` contain no closed items yet; the single instance is in
        CLAUDE.md. A near-vacuous gate is worth saying out loud — it is
        verified against that one real instance, and
        `test_the_closure_form_has_an_instance` fails if it reaches zero, so it
        cannot quietly become a check over nothing.
      * NOTHING HERE NOTICES WORK LANDING AND THE LINE NOT BEING STRUCK. That
        is the residual the per-item predicate exists for, still declared in
        `record/verification.md § Open`. These gates check the FORM of a
        transition that was made, never that a transition was DUE.
    """

    _STRUCK = re.compile(r"~~")
    _DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
    _WHAT = re.compile(r"\([^)]{4,}\)")
    _LINK = re.compile(r"\]\([^)]+\)")

    def _open_bullets(self) -> list[tuple[str, str]]:
        """Every `## Open` bullet in CLAUDE.md AND `record/`.

        Wider than `TestEveryOpenItemIsTyped._items`, deliberately: CLAUDE.md's
        section is an index and carries no KINDS, but a closure written there is
        still a closure and must show its evidence.
        """
        out: list[tuple[str, str]] = []
        for path in [CLAUDE_MD] + sorted(RECORD_DIR.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            heads = [i for i, l in enumerate(lines)
                     if l.strip().lower().startswith(("## open", "### open"))]
            for start in heads:
                end = next((i for i in range(start + 1, len(lines))
                            if lines[i].startswith(("## ", "### "))), len(lines))
                buf: list[str] = []
                for i in range(start + 1, end + 1):
                    line = lines[i] if i < end else "- "
                    if line.startswith("- ") and buf:
                        out.append((path.name, " ".join(buf)))
                        buf = []
                    if line.startswith("- ") or (buf and line.startswith("  ")):
                        buf.append(line.strip())
        return out

    def _closed(self) -> list[tuple[str, str]]:
        return [(f, t) for f, t in self._open_bullets() if self._STRUCK.search(t)]

    def test_a_closed_item_says_when_it_closed(self) -> None:
        bad = [(f, t[:90]) for f, t in self._closed() if not self._DATE.search(t)]
        assert not bad, (
            "these closed items carry no date:\n  "
            + "\n  ".join(f"{f}: {t}" for f, t in bad)
            + "\n\nUse the form `**~~<item>~~ — SETTLED <YYYY-MM-DD>** (<what "
            "decided it>)`. A closure with no date cannot be aged."
        )

    def test_a_closed_item_says_what_closed_it(self) -> None:
        """
        THE FIRST VERSION OF THIS PASSED A DELIBERATE BREAKAGE. Removing
        "(author decision, charter)" left the check green, because
        `](record/ecological.md#live-state)` is also a parenthesis four
        characters long — the markdown link satisfied the assertion that a
        DECIDER was named. Link targets are stripped before looking, which is
        failure mode 2: an assertion the surrounding syntax enforces.
        """
        bad = [(f, t[:90]) for f, t in self._closed()
               if not self._WHAT.search(self._LINK.sub("]", t))]
        assert not bad, (
            "these closed items do not name what decided them:\n  "
            + "\n  ".join(f"{f}: {t}" for f, t in bad)
            + "\n\n'SETTLED' with no decider is a status note, and a status "
            "note outliving its decision is this repo's most repeated failure."
        )

    def test_a_closed_item_points_at_its_evidence(self) -> None:
        """The § Open line is STATE; the history entry is EVIDENCE. A closure
        with no link asserts the second without providing it."""
        bad = [(f, t[:90]) for f, t in self._closed() if not self._LINK.search(t)]
        assert not bad, (
            "these closed items link to nothing:\n  "
            + "\n  ".join(f"{f}: {t}" for f, t in bad)
            + "\n\nPoint at the history entry that closed it."
        )

    def test_the_closure_form_has_an_instance(self) -> None:
        """
        A form check over zero closures passes and guards nothing. Today there
        is exactly one; if closures ever reach zero the convention has been
        abandoned or the scan has broken, and either is worth a failure.
        """
        assert self._closed(), (
            "no closed item found in any `## Open` section. Closed items are "
            "struck through and KEPT VISIBLE — if one was deleted, restore it; "
            "the shape is the finding."
        )

    def test_every_held_item_says_why_it_is_held(self) -> None:
        """
        `held` means BUILDING it is the error. Retyping a `gap` to `held` is the
        one transition that makes work vanish with nothing landing, so it costs
        a justification.
        """
        thin = []
        for f, t in self._open_bullets():
            if "*(held)*" not in t:
                continue
            rest = t.split("*(held)*", 1)[1].strip(" —-,.")
            if len(rest) < 80:
                thin.append((f, t[:90], len(rest)))
        assert not thin, (
            "these `held` items do not say why they are held:\n  "
            + "\n  ".join(f"{f} ({n} chars after the marker): {t}" for f, t, n in thin)
            + "\n\n`held` is a decision NOT to do something. State the reason, "
            "or type it `gap` and leave it as work."
        )

    def test_the_stated_gaps_are_still_stated(self) -> None:
        doc = self.__doc__ or ""
        assert "STATED GAPS" in doc
        assert "GUARD ONE ITEM TODAY" in doc
        assert "NOTHING HERE NOTICES WORK LANDING" in doc


# ---------------------------------------------------------------------------
# The per-item predicate — the settle path in `record/verification.md § Open`
# ---------------------------------------------------------------------------

def _ten_ratios_unmeasured() -> bool:
    """The ten fee-table coefficients, NOT `GUF_USE_SCALE_FACTOR` — the record
    calls that out separately as "one scalar against ten coefficients"."""
    from utils import provenance as pv
    tags = {r.name: r.tag for r in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records
            if r.name.startswith("GUF_USE_") and r.name != "GUF_USE_SCALE_FACTOR"}
    assert len(tags) == 10, f"the item says TEN ratios; found {len(tags)}"
    return not any(t in {"measured", "derived"} for t in tags.values())


def _form_edges_not_derived() -> bool:
    """Closure = `band_from:` stops being the only source of edges. It is
    declared ONCE today against 12 expression-derivable assignments."""
    src = (REPO_ROOT / "hours_eoh" / "data.py").read_text(encoding="utf-8")
    return src.count("# band_from:") <= 1


def _two_floors_and_both_unsettled() -> bool:
    from utils import provenance as pv
    from hours_eoh.data import PERSONAL_EOH_COMPONENTS, PERSONAL_AUTOMATION_FLOORS
    tags = {r.name: r.tag for r in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records
            if r.name in {"CARE_AUTOMATION_FLOOR", "NUTRITION_AUTOMATION_FLOOR"}}
    return (len(PERSONAL_EOH_COMPONENTS) == 4
            and len(PERSONAL_AUTOMATION_FLOORS) == 2
            and set(tags.values()) == {"placeholder"})


def _teh_supply_has_no_caller() -> bool:
    import ast as _ast
    hits = set()
    for path in (REPO_ROOT / "hours_eoh").rglob("*.py"):
        for node in _ast.walk(_ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, _ast.Call) and getattr(node.func, "id", None) == "teh_supply":
                hits.add(path.name)
    return not hits


def _anchor_comparison_unbuilt() -> bool:
    return not list((REPO_ROOT / "hours_eoh").rglob("*anchor_comparison*"))


def _shadow_bound_still_8() -> bool:
    src = (REPO_ROOT / "tests" / "test_parameter_wiring.py").read_text(encoding="utf-8")
    m = re.search(r"_DECLARED\)\s*<=\s*(\d+)", src)
    return m is not None and int(m.group(1)) == 8


def _confidence_ratchet_is_126_of_138() -> bool:
    """Imports nothing of its own: the gate's OWN filter, not a copy of it —
    re-implementing it dropped `if not s.bound` once already (corpus F-038)."""
    from tests.test_confidence import BASELINE_WITHOUT, SOFT_TAGS
    from utils import provenance as pv
    soft = [r for r in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records
            if r.tag in SOFT_TAGS]
    without = [r for r in soft if not getattr(r, "confidence", None)]
    return (len(without), len(soft), BASELINE_WITHOUT) == (126, 142, 126)


def _scan_is_data_py_only() -> bool:
    from utils import provenance as pv
    return pv.DATA_PY.name == "data.py"


def _kappa_ratio_is_12_to_69() -> bool:
    """Calls the function that RETURNS the ratio. Re-deriving it from the
    rounded prose figure gave 67x (corpus F-040)."""
    from hours_eoh.scenarios.restoration_cost import implied_kappa
    r = implied_kappa()
    return (round(r["shipped_over_implied_high"]) == 12
            and round(r["shipped_over_implied_low"]) == 69)


def _desire_is_still_a_stub() -> bool:
    import ast as _ast
    src = (REPO_ROOT / "hours_eoh" / "research" / "desire.py").read_text(encoding="utf-8")
    return sum(1 for n in _ast.parse(src).body
               if isinstance(n, _ast.FunctionDef)) <= 3


def _maint_rate_still_unbound() -> bool:
    src = (REPO_ROOT / "hours_eoh" / "data.py").read_text(encoding="utf-8")
    block = re.search(r'"generic_infra"\s*:\s*\{.*?\}', src, re.S)
    return block is not None and "INFRA_MAINT_RATE" not in block.group(0)


def _predicate_coverage_is_incomplete() -> bool:
    """The item that declared this whole mechanism, checking itself: still open
    while any typed `## Open` item lacks a predicate."""
    typed = len(TestEveryOpenItemIsTyped()._items())
    covered = sum(1 for q in OPEN_ITEM_PREDICATES if q.still_open or q.why_none)
    return covered < typed


@dataclass(frozen=True)
class OpenItemPredicate:
    """One open item, its kind, and the observable that would contradict it."""

    marker: str                              #: substring locating the item
    kind: str                                #: must match the `*(kind)*` in the file
    still_open: Callable[[], bool] | None    #: False => the code contradicts the item
    why_none: str = ""                       #: REQUIRED when still_open is None


#: THE DIRECTION IS SET BY THE KIND, which is the whole reason typing came first:
#:   gap     False => the closure LANDED and nobody struck the line
#:   held    False => someone BUILT what the repo decided against
#:   caveat  False => the standing figure DRIFTED
#:   person  False => the human decision landed without being recorded
#:   pointer no predicate — the dangling check already covers it
OPEN_ITEM_PREDICATES: tuple[OpenItemPredicate, ...] = (
    OpenItemPredicate("The ten `GUF_USE_*` ratios", "gap", _ten_ratios_unmeasured),
    OpenItemPredicate("derive `form:` edges from the expressions", "gap",
                      _form_edges_not_derived),
    OpenItemPredicate("Two of four personal automation floors carry a value", "gap",
                      _two_floors_and_both_unsettled),
    OpenItemPredicate("The compensating-mechanism audit", "gap", None,
                      why_none="an audit is a document plus findings; nothing in the "
                               "tree changes shape when it is performed"),
    OpenItemPredicate("`teh_supply` is pinned, not decided", "held",
                      _teh_supply_has_no_caller),
    OpenItemPredicate("Anchor comparison Phases 1–3 are HELD DELIBERATELY", "held",
                      _anchor_comparison_unbuilt),
    OpenItemPredicate("The shadow ratchet cannot catch its own bound being loosened",
                      "held", _shadow_bound_still_8),
    OpenItemPredicate("λ_equilibrium is not assessable from this data", "held", None,
                      why_none="the hold is on a VALUE being unassessable from the "
                               "data, not on a module; `thermal_lambda.py` exists and "
                               "declares the limit, so its presence proves nothing"),
    OpenItemPredicate("126 of 142 placeholder/bounded constants carry no confidence",
                      "caveat", _confidence_ratchet_is_126_of_138),
    OpenItemPredicate("The scan is `data.py`-only", "caveat", _scan_is_data_py_only),
    OpenItemPredicate("The `GUF_ECO_KAPPA_*` constants are engineered-route figures",
                      "caveat", _kappa_ratio_is_12_to_69),
    OpenItemPredicate("The discovery layer is a 120-line stub with 3 functions",
                      "person", _desire_is_still_a_stub),
    OpenItemPredicate('`ASSET_TYPES["generic_infra"]["maint_rate"]` duplicates',
                      "person", _maint_rate_still_unbound),
    OpenItemPredicate("The claims register now checks 12 of 42 open items", "gap",
                      _predicate_coverage_is_incomplete),
)


class TestTheOpenItemPredicates:
    """
    THE SETTLE PATH DECLARED IN `record/verification.md § Open`, built.

    The register could say an item was DECLARED, and after 2026-09-04 that it
    was TYPED. Neither says whether it is still OPEN. That gap let a
    `STILL OPEN` line stand for a day while the file asserted the adoption two
    entries above it.

    WHY TYPING HAD TO COME FIRST. A `LIVE_CLAIM` asserts a presence and its
    predicate confirms it. An open item asserts an ABSENCE, so the predicate
    must detect the CLOSURE and negate it — and what counts as closure is
    different for each kind. A `gap` closes when the work lands; a `held` is
    breached when the work lands. Same observable, opposite verdict. Without
    the kind there is no way to say which, so the predicate could not be
    written at all.

    STATED GAPS:

      * COVERAGE IS 13 OF 41 ITEMS, and the ratchet below only forbids it
        FALLING. An item with no predicate is checked by nothing here — the
        same standing this file's `LIVE_CLAIMS` has always had. The gap is
        itself an item with a predicate: `_predicate_coverage_is_incomplete`
        fails once every typed item is covered, so this admission cannot
        outlive the condition it describes.
      * TWO ITEMS CARRY `why_none` RATHER THAN A PREDICATE, and both reasons
        are real: an audit changes no shape in the tree, and a hold on a VALUE
        being unassessable is not contradicted by the module that says so.
        `why_none` is required precisely so `None` cannot be the silent
        default.
      * A PREDICATE PROVES THE OBSERVABLE, NOT THE ITEM. `_anchor_comparison_
        unbuilt` checks for a file name; someone could build the thing under
        another name. The predicate narrows the ways an item can go stale
        unnoticed; it does not close them.
      * `person` ITEMS GET A PREDICATE ONLY WHERE THE DECISION LEAVES A TRACE.
        A sign-off in a gitignored note changes nothing observable, so the two
        typed here are the two whose adoption would show up in code.
    """

    #: May not FALL. Rises when an item gains an observable; falls only when an
    #: item CLOSES, and a closing item is struck rather than deleted — so a fall
    #: means a predicate was dropped, which is the move this ratchet forbids.
    PREDICATE_FLOOR = 12

    def _by_marker(self) -> dict[str, str]:
        """`{bullet text: kind}` for every typed `## Open` item."""
        out = {}
        for f, t in TestClosingAnItemLeavesEvidence()._open_bullets():
            m = TestEveryOpenItemIsTyped._KIND.search(t)
            if m:
                out[t] = m.group(1)
        return out

    @pytest.mark.parametrize("p", OPEN_ITEM_PREDICATES, ids=lambda p: p.marker[:40])
    def test_the_item_exists_with_the_kind_the_predicate_assumes(self, p) -> None:
        """
        A predicate keyed to an item nobody has is a check over nothing, and one
        keyed to the WRONG kind reads its own result backwards — `gap` and
        `held` invert on the same observable.
        """
        hits = {t: k for t, k in self._by_marker().items() if p.marker in t}
        assert hits, (
            f"no `## Open` item contains {p.marker[:60]!r}. If it closed, remove "
            "the predicate; if it moved, update the marker."
        )
        # A POINTER NEVER CARRIES ITS OWN PREDICATE. Five items are filed in two
        # places, so a marker legitimately matches the home AND its pointer —
        # `teh_supply` was reachable three ways before typing. Checking the
        # pointer too would run one predicate twice and let the copy dictate the
        # kind, which is the double-count typing exists to end.
        homes = {t: k for t, k in hits.items() if k != "pointer"}
        assert len(homes) == 1, (
            f"{p.marker[:50]!r} matches {len(homes)} non-pointer items "
            f"{sorted(homes.values())}. An item has ONE home; narrow the marker."
        )
        kinds = set(homes.values())
        assert kinds == {p.kind}, (
            f"{p.marker[:50]!r} is typed {sorted(kinds)} in the record but the "
            f"predicate assumes {p.kind!r}. These invert: for a `gap` a False "
            "result means the work landed, for a `held` it means someone built "
            "what we decided against."
        )

    @pytest.mark.parametrize(
        "p", [q for q in OPEN_ITEM_PREDICATES if q.kind == "gap" and q.still_open],
        ids=lambda p: p.marker[:40])
    def test_a_gap_has_not_quietly_closed(self, p) -> None:
        assert p.still_open(), (
            f"{p.marker[:60]!r} is typed `gap` but the code says its closure has "
            "LANDED. Strike the item through with a date, what closed it and a "
            "link to the entry — `record/README.md` convention 2."
        )

    @pytest.mark.parametrize(
        "p", [q for q in OPEN_ITEM_PREDICATES if q.kind == "held" and q.still_open],
        ids=lambda p: p.marker[:40])
    def test_a_held_item_has_not_been_built(self, p) -> None:
        assert p.still_open(), (
            f"{p.marker[:60]!r} is typed `held` — a decision NOT to do it — and "
            "the code says it was built anyway. Either the hold was lifted and "
            "nobody recorded the decision, or this is scope the repo declined."
        )

    @pytest.mark.parametrize(
        "p", [q for q in OPEN_ITEM_PREDICATES if q.kind in {"caveat", "person"}
              and q.still_open], ids=lambda p: p.marker[:40])
    def test_a_standing_item_still_describes_the_code(self, p) -> None:
        assert p.still_open(), (
            f"{p.marker[:60]!r} no longer describes the code. A `caveat` whose "
            "figure moved should be computed rather than restated (failure mode "
            "13); a `person` item whose decision landed should be struck."
        )

    def test_an_item_without_a_predicate_says_why(self) -> None:
        silent = [p.marker[:60] for p in OPEN_ITEM_PREDICATES
                  if p.still_open is None and len(p.why_none) < 40]
        assert not silent, (
            f"these carry no predicate and no reason: {silent}. `None` must be a "
            "STATED judgement that the closure leaves no trace, never the default."
        )

    def test_predicate_coverage_does_not_fall(self) -> None:
        n = sum(1 for p in OPEN_ITEM_PREDICATES if p.still_open)
        assert n >= self.PREDICATE_FLOOR, (
            f"{n} predicates against a floor of {self.PREDICATE_FLOOR}. Coverage "
            "may rise, and falls only when an item CLOSES — and a closed item is "
            "struck, not deleted. A fall here means a predicate was dropped."
        )
        assert {p.kind for p in OPEN_ITEM_PREDICATES if p.still_open} >= {
            "gap", "held", "caveat"}, (
            "the gap/held inversion is the point of this registry; if only one "
            "kind carries predicates it is not exercising that."
        )

    def test_the_stated_gaps_are_still_stated(self) -> None:
        doc = self.__doc__ or ""
        assert "STATED GAPS" in doc
        assert "COVERAGE IS 13 OF 41" in doc
        assert "PROVES THE OBSERVABLE, NOT THE ITEM" in doc
