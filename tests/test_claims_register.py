"""The claims register: CLAUDE.md's checkable assertions, checked.

The repo's most repeated failure is a RIGHT number that stopped being right and that no
one revisited. This gate applies the dataset-fingerprint pattern of
`test_dataset_governance.py` to the file a new session reads first. It checks only
claims of a DECLARED shape and leaves the historical record alone. A gate that fired on
prose edits would not survive a week
([record](record/verification.md#claims-register-test-history)).

STATED GAPS (an undocumented gap makes a checker read as stronger than it is):

  * This gate does NOT check the suite's own test count or mypy's file count.
    Counting tests from inside the suite is circular, and mypy needs a
    subprocess. These two figures drift most, and this gate does not catch them.
  * It checks only the claims in LIVE_CLAIMS, and does not cover a new claim
    automatically. `test_every_open_item_is_declared` stops a new OPEN item
    from arriving silently, which is where staleness has occurred.
  * A claim whose ANCHOR text changes fails loudly, by intent, to force a
    fresh check.
  * The corpus is CLAUDE.md plus `record/*.md`. A claim moved to a file outside
    those two homes silently leaves the check.
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
    """CLAUDE.md PLUS every `record/*.md`. A claim that the 2026-09-03 split moved into
    `record/` must stay checked. Reading CLAUDE.md alone would have retired six anchors
    and three of the five closed open items
    ([record](record/verification.md#claims-register-test-history)).
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
    """Every constant carries a tag, at the census's acknowledged total. The census
    generates the prose that quotes the figure (utils/census.py, 2026-10-03), so the
    figure is not written here.
    """
    from utils import census
    from utils import provenance as pv
    tagged, total = pv.coverage(pv.scan(pv.DATA_PY.read_text(encoding="utf-8")))
    return tagged == total == census.snapshot()["provenance_total"]


def _shadow_count_is_acknowledged() -> bool:
    from utils import census
    from utils import provenance as pv
    return len([s for s in pv.shadow_constants() if not s.bound]) == census.snapshot()["shadow_unbound"]


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
    state = make_economy_state()
    rows = run_simulation(make_economy_state(), n_periods=40)["period_results"]
    created = sum(r["teh_created"] for r in rows)
    destroyed = sum(r["teh_destroyed"] for r in rows)
    endowment = state["teh_endowment"]
    if endowment <= 0.0:
        return False
    if created < destroyed:
        return True          # the old symptom: teh_supply refuses the flows
    return abs((rows[-1]["teh_total_supply"] - teh_supply(created, destroyed))
               - endowment) <= 1e-6 * max(1.0, endowment)


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
        anchor="<!-- census:provenance -->",
        check=_provenance_is_complete,
        why=(
            "the coverage figure quoted to institutions; 265 -> 288 -> 292 -> 294 -> 296 -> 297 -> 299 -> 300 -> 320 -> 321 -> 341 (the sigmoid split) -> 342 -> 349 (SHOCK_DEGRADED_TRUST_FRACTION, 2026-09-30) -> 350 (ESSENTIAL_BRIDGE_PERSONAL, 2026-10-01) -> 352 (the reserved land floor, 2026-10-01) -> 353 (ECOSYSTEM_HEALTH_DEFAULT, 2026-10-02) -> 354 (CANONICAL_CAPITAL_AGE_BASE) -> 355 (SUFF_GUARANTEE_FLOOR_FRACTION) -> 357 (the retirement register's age and tenure, 2026-10-03). "
            "Anchored to the CURRENT entry, not a historical one: the old anchor "
            "matched six lines, five of them history, so the claim was checking a "
            "live number against text that must never be updated."
        ),
    ),
    Claim(
        anchor="<!-- census:state -->",
        check=_shadow_count_is_acknowledged,
        why="the ratchet's count, quoted beside the 100% figure it qualifies. "
            "Re-anchored 2026-10-02 from 'shadow ratchet at 33' (dated history) "
            "and 2026-10-03 to the generated census block, so the number is "
            "written once.",
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
        anchor="It has ZERO callers, and its identity differs from the shipped one by exactly the endowment",
        check=_teh_supply_is_orphaned_and_refuses_the_shipped_trajectory,
        why=(
            "`teh_supply` states the bound the value-anchor argument WANTS and "
            "describes an economy with no endowment. A caller appearing means "
            "the two accounts have merged. The guard used to be 'it raises on "
            "the shipped trajectory', which only held while the inheritance was "
            "large enough to make destruction outpace creation — it stopped "
            "firing at the 2026-09-17 reprice without the accounts merging at all."
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
        """Editing a claim out of the file leaves it unreviewed, not retired. The
        failure forces the register and the file back into agreement.
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
    """The failure this gate exists for: three `STILL OPEN` lines were stale at the
    2026-08-29 merge review. Each was true when written, and no one revisited it.
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
        "TRUST_BASE_TEH": (
            "needs the repair the CAPITAL frame took on 2026-09-16, which is "
            "known to work and is the same shape: give the resolver a "
            "`population` defaulting to REFERENCE_FRAME_POPULATION, scale the "
            "RESOLVED value by population / REFERENCE_FRAME_POPULATION (never a "
            "supplied one), wire the callers that have a population in scope, "
            "and extend tests/test_capital_scale_resolution.py to the balance "
            "chain. What is NOT yet known is the size: the capital chain had 25 "
            "callers with a population in scope and 22 of them defaulted to the "
            "reference frame, so the blast radius was almost nil — this "
            "constant's callers have not been surveyed, and that survey is the "
            "first step, not the wiring."
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
        """A declaration for an item that does not exist is a permission nobody reviews
        (the `unused_innocuous_names` lesson).
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
        """Strike a closed item through; do not delete it. The struck line is the
        evidence that the failure shape is real.
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
        """The module docstring must keep naming what this gate does NOT check: the test
        count and mypy's file count. Without that admission the gate reads as stronger
        than it is.
        """
        doc = __doc__ or ""
        assert "STATED GAPS" in doc
        assert "test count" in doc and "mypy" in doc


# ---------------------------------------------------------------------------
# The kind of an open item
# ---------------------------------------------------------------------------

class TestEveryOpenItemIsTyped:
    """Every `## Open` bullet in `record/` states its KIND, because an Open section is
    not a work queue ([record](record/verification.md#claims-register-test-history)):

        gap      work; a named acquisition or build closes it
        held     decided NOT to do; BUILDING it is the error
        caveat   a standing property of the model, not work at all
        person   waiting on a human decision; no code state changes
        pointer  the item is filed elsewhere; follow the link

    The marker follows the `*(gated)*` idiom the area files already use.
    `TestTheOpenItemsAreDeclared` reads `- **STILL OPEN` lines under `## History`; this
    class reads `## Open`, so the two do not overlap.

    STATED GAPS:

      * THE KIND IS AUTHORED, NOT DERIVED. Nothing stops someone retyping a `gap` as
        `held` to silence it. What holds it is that a retype is visible in a diff; that
        ceiling cannot close from inside.
      * NO PREDICATE IS CHECKED YET in this class: it says an item is TYPED, not that
        a `gap` is still open or that nobody built a `held`. Typing makes those
        predicates writable (see `TestTheOpenItemPredicates`).
      * The class does not scan CLAUDE.md's `## Open` for kinds. It is an index,
        typed by group heading. `TestClosingAnItemLeavesEvidence` does read it.
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
        """The kind vocabulary is closed. `*(gated)*` passes on purpose: it marks a
        LIVE-STATE line as checked, which is a different axis from an item's kind.
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
    """The transition rules of `record/README.md` convention 2. An open item can be
    STRUCK (closed and kept visible), RETYPED, or deleted. These tests check the first
    two, and git can check deletion. A retype to `held` must give its reason, because it
    looks like housekeeping and means "we decided not to do this"
    ([record](record/verification.md#claims-register-test-history)).

    STATED GAPS:

      * THE STRUCK-ITEM CHECKS GUARD ONE ITEM TODAY, in CLAUDE.md;
        `test_the_closure_form_has_an_instance` fails if that reaches zero.
      * NOTHING HERE NOTICES WORK LANDING AND THE LINE NOT BEING STRUCK. These tests
        check the FORM of a transition that happened, never that one was due.
      * The tests scan only `## Open`, so they do not check a closure written in
        `## Live state`. This is deliberate: widening to every struck line would fire on
        history, which stays verbatim.
    """

    #: A CLOSED item is one whose BOLD LEAD is struck — `- **~~…`. Not one that
    #: merely CONTAINS `~~`: an open item may strike individual sub-points while
    #: staying open, which the abatement item does for its resolved blockers.
    #: The first version matched `~~` anywhere and read that item as closed,
    #: repeating exactly the mistake `_ITEM` above had already been fixed for —
    #: anchor to the bullet structure, not to a substring.
    _STRUCK = re.compile(r"^- \*\*~~")
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
        return [(f, t) for f, t in self._open_bullets()
                if self._STRUCK.match(t.lstrip())]

    def test_a_closed_item_says_when_it_closed(self) -> None:
        bad = [(f, t[:90]) for f, t in self._closed() if not self._DATE.search(t)]
        assert not bad, (
            "these closed items carry no date:\n  "
            + "\n  ".join(f"{f}: {t}" for f, t in bad)
            + "\n\nUse the form `**~~<item>~~ — SETTLED <YYYY-MM-DD>** (<what "
            "decided it>)`. A closure with no date cannot be aged."
        )

    def test_a_closed_item_says_what_closed_it(self) -> None:
        """A closed item must name what closed it. The test strips link targets first,
        because a markdown link's parenthesis once satisfied the "decider named" check
        by itself (mode 2).
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
        """A form check over zero closures guards nothing. Today there is one; if
        closures reach zero, the convention was abandoned or the scan broke, and either
        should fail.
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


def _composites_still_rest_on_placeholders() -> bool:
    """Closure = the pass over the composites lands: no `derived` constant
    bottoms out on a placeholder through its expression — their parts measured
    or split (2026-10-16). Each now SAYS it inherits, which `problems()` gates."""
    from utils import provenance as pv
    return bool(pv.derived_on_placeholder(pv.load()))


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


def _wiring_bound_still_12() -> bool:
    """The bound in the ratchet's ASSERTION, not in prose. Until 2026-10-17 the search
    matched the module docstring's stale `<= 8` first, while the assertion read 12
    ([record](record/verification.md#ste-docstrings)).
    """
    src = (REPO_ROOT / "tests" / "test_parameter_wiring.py").read_text(encoding="utf-8")
    m = re.search(r"^\s*assert len\(_DECLARED\)\s*<=\s*(\d+)", src, re.M)
    return m is not None and int(m.group(1)) == 12


def _confidence_debt_is_acknowledged() -> bool:
    """The confidence debt equals the gate's OWN filter, imported, not a copy: a copy
    once dropped `if not s.bound` (corpus F-038). This predicate caught a real move on
    2026-09-16, while two ungated copies had drifted
    ([record](record/verification.md#claims-register-test-history)).
    """
    from tests.test_confidence import BASELINE_WITHOUT, SOFT_TAGS
    from utils import provenance as pv
    soft = [r for r in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records
            if r.tag in SOFT_TAGS]
    without = [r for r in soft if not getattr(r, "confidence", None)]
    from utils import census
    s = census.snapshot()
    return (len(without), len(soft)) == (s["confidence_without"], s["confidence_soft"]) \
        and BASELINE_WITHOUT == len(without) > 0


def _scan_is_data_py_only() -> bool:
    """The predicate checks the caveat's own figure, not only its premise. Until
    2026-10-02 it read the file name alone, so the "33 shadow constants" went stale with
    every gate green (mode 7).
    """
    from utils import provenance as pv
    text = (REPO_ROOT / "record" / "provenance.md").read_text(encoding="utf-8")
    n = len([s for s in pv.shadow_constants() if not s.bound])
    # The figure is a generated census block since 2026-10-03 (it was hand-kept
    # and missed by the first sweep); the block must still render the live count.
    return (pv.DATA_PY.name == "data.py"
            and f"The <!-- census:shadow -->{n}<!-- /census:shadow --> shadow constants are" in text)


def _kappa_ratio_is_12_to_69() -> bool:
    """Calls the function that RETURNS the ratio. Re-deriving it from the
    rounded prose figure gave 67x (corpus F-040)."""
    from hours_eoh.scenarios.restoration_cost import implied_kappa
    r = implied_kappa()
    return (round(r["shipped_over_implied_high"]) == 12
            and round(r["shipped_over_implied_low"]) == 69)


def _compensation_audits_only_the_inflows() -> bool:
    """The audit covers the TEH inflows alone (2026-10-02), and the caveat (2026-10-16)
    says nothing else on the shared path is switchable. A second mechanism family makes
    this drift.
    """
    import hours_eoh.scenarios.compensation as C
    families = [n for n in vars(C) if n.endswith("_mechanisms") and callable(getattr(C, n))]
    return families == ["inflow_mechanisms"]


def _pillars_cannot_fire() -> bool:
    """Both dashboard pillars read GREEN at every ε, at a collapsed ecosystem
    and an empty Trust (2026-10-01). The gap closes when either can fire."""
    from hours_eoh.core.dashboard import fiscal_health_check
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.eoh_generation import resolve_capital_stock
    for eps in (0.0, 0.40, 0.90, 0.99):
        cap = resolve_capital_stock(None, eps)
        p = eoh_to_teh_pipeline(eps, capital_stock=cap, ecosystem_health=0.10)
        for trust in (0.0, 3.5e10):
            r = fiscal_health_check(trust, p["teh_created"], cap, 0.5, 1.0e6, 1000.0, eps,
                                    ecosystem_health=0.10,
                                    eco_eoh_override=p["eoh_by_domain"]["ecological"])
            if r["pp_status"] != "GREEN" or r["ecological_status"] != "GREEN":
                return False
    return True


def _parcel_index_unread_by_the_fee() -> bool:
    import inspect
    from hours_eoh.land import collective, guf
    src = inspect.getsource(guf) + inspect.getsource(collective)
    return ("parcel_condition" not in src
            and "condition" not in inspect.signature(guf.ground_use_fee).parameters)


def _formation_cobweb_persists() -> bool:
    from hours_eoh.research.dynamic_stability import formation_stability
    return formation_stability(priority="dividend")[
        "fields"]["eps_actual"]["verdict"] == "OSCILLATING"


def _care_short_at_the_threshold() -> bool:
    """The question stands while the threshold is unchanged and care, certified at it,
    is still short at ε=0.78 in the survival reading.
    """
    from hours_eoh.core.conditions import condition_iv_coverage
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.workforce import competency_reserve
    from hours_eoh.data import AGE_GROUPS, COMPETENCY_THRESHOLD, ESSENTIAL_DOMAINS
    wf = 1.0e6 * AGE_GROUPS["working_age"]["fraction"]
    res = competency_reserve({d: wf * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, wf)
    r = condition_iv_coverage(res, eoh_to_teh_pipeline(0.78), demand="personal")
    return COMPETENCY_THRESHOLD == 0.155 and "care" in r["domains_short"]


def _bridge_bound_matches_its_figure() -> bool:
    """The caveat's figure (≥1.69×), recomputed: all three untagged columns on
    one domain, threshold certification, fine grid."""
    from hours_eoh.core.conditions import condition_iv_coverage
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.eoh_generation import essential_weights
    from hours_eoh.core.workforce import competency_reserve
    from hours_eoh.data import AGE_GROUPS, COMPETENCY_THRESHOLD, ESSENTIAL_DOMAINS
    cols = ("infrastructure", "ecological", "knowledge")
    wf = 1.0e6 * AGE_GROUPS["working_age"]["fraction"]
    res = competency_reserve({d: wf * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, wf)
    worst = float("inf")
    for i in range(100):
        p = eoh_to_teh_pipeline(min(i / 100, 0.99))
        for d in ESSENTIAL_DOMAINS:
            if d == "care":
                continue
            w = essential_weights()
            for row in w.values():
                for c in cols:
                    row[c] = 0.0
            for c in cols:
                w[d][c] = 1.0
            worst = min(worst, condition_iv_coverage(res, p, weights=w)[
                "per_domain"][d]["coverage_ratio"])
    text = (REPO_ROOT / "record" / "provenance.md").read_text(encoding="utf-8")
    return f"≥{worst:.2f}×" in text


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


def _prov(name: str):
    from utils import provenance as pv
    return pv.load().by_name[name]


def _states_share_capacity_and_stock() -> bool:
    """Closure = the state split states a stock or a capacity per unit; the
    loader admits only the weights and an age mix (2026-10-16)."""
    from utils.frame_inputs import SPLIT_WEIGHTS, load_split
    keys = {k for u in load_split("us_states")["collectives"] for k in u}
    return keys <= {"id", "label", "age_fractions", *SPLIT_WEIGHTS}


def _pristine_gap_has_no_default_inventory() -> bool:
    import inspect
    from hours_eoh.scenarios.restoration_cost import pristine_gap_obligation
    p = inspect.signature(pristine_gap_obligation).parameters["condition_inventory"]
    return p.default is inspect.Parameter.empty


def _no_measured_service_profile_ships() -> bool:
    """Closure = a per-hectare service profile ships as data or as a default."""
    import inspect
    from hours_eoh.land.guf import ecosystem_services_for_area
    p = inspect.signature(ecosystem_services_for_area).parameters["per_hectare_volumes"]
    data = REPO_ROOT / "hours_eoh" / "reference" / "data"
    shipped = any(k in f.name.lower() for f in data.iterdir() for k in ("itree", "fia_", "service_volume"))
    return p.default is inspect.Parameter.empty and not shipped


def _retention_is_an_ordering() -> bool:
    return _prov("GUF_SERVICE_RETENTION_BY_USE").tag not in {"measured", "bounded"}


def _no_tenure_split_ships() -> bool:
    data = REPO_ROOT / "hours_eoh" / "reference" / "data"
    return not any(k in f.name.lower() for f in data.iterdir() for k in ("tenure", "blm"))


def _parcel_count_unrestricted_to_serviced_classes() -> bool:
    """Closure = the parcel extract reads SERVICED_LAND_CLASSES (the usedesc
    normalisation); today it only explains why it cannot."""
    src = (REPO_ROOT / "hours_eoh" / "reference" / "parcels.py").read_text(encoding="utf-8")
    return "SERVICED_LAND_CLASSES" not in src


def _abatement_pace_is_still_a_placeholder() -> bool:
    return _prov("ABATEMENT_HALF_CAPITAL_TEH").tag == "placeholder"


def _component_shares_are_still_desk_terms() -> bool:
    return _prov("PERSONAL_EOH_COMPONENTS").tag == "placeholder"


def _cdr_labour_is_still_tier_d_at_0_6() -> bool:
    r = _prov("CDR_LABOR_HOURS_PER_TONNE")
    return r.tier == "D" and r.value == "0.6"


def _capital_thermal_profiles_are_placeholders() -> bool:
    return _prov("CAPITAL_THERMAL_PROFILES").tag == "placeholder"


def _shipped_federation_is_at_mutual_recognition() -> bool:
    """The caveat's figure: one multiplier, every settlement rate 1.0, at all
    four arc points."""
    from hours_eoh.research.coasean import make_federation
    from hours_eoh.research.exchange import registered_rate
    for e in (0.0, 0.40, 0.90, 0.99):
        fs = make_federation(e)
        if len({c.pipeline["mean_multiplier"] for c in fs}) != 1:
            return False
        if any(registered_rate(a, b) != 1.0 for a in fs for b in fs):
            return False
    return True


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
    OpenItemPredicate("30 dict/tuple constants carry ONE tag over several fields", "gap",
                      _composites_still_rest_on_placeholders),
    OpenItemPredicate("Two of four automation floors carry a value", "gap",
                      _two_floors_and_both_unsettled),
    OpenItemPredicate("Compensation audited for the inflows", "caveat",
                      _compensation_audits_only_the_inflows),
    OpenItemPredicate("`teh_supply` is pinned, not decided", "held",
                      _teh_supply_has_no_caller),
    OpenItemPredicate("Anchor comparison Phases 1–3 are HELD DELIBERATELY", "held",
                      _anchor_comparison_unbuilt),
    OpenItemPredicate("The wiring ratchet's bound is pinned one level up",
                      "caveat", _wiring_bound_still_12),
    OpenItemPredicate("λ_equilibrium is not assessable from this data", "held", None,
                      why_none="the hold is on a VALUE being unassessable from the "
                               "data, not on a module; `thermal_lambda.py` exists and "
                               "declares the limit, so its presence proves nothing"),
    OpenItemPredicate("placeholder/bounded constants carry no confidence figure.**",
                      "caveat", _confidence_debt_is_acknowledged),
    OpenItemPredicate("The scan is `data.py`-only", "caveat", _scan_is_data_py_only),
    OpenItemPredicate("The `GUF_ECO_KAPPA_*` constants are engineered-route figures",
                      "caveat", _kappa_ratio_is_12_to_69),
    OpenItemPredicate("The discovery layer is a 120-line stub with 3 functions",
                      "person", _desire_is_still_a_stub),
    OpenItemPredicate('`ASSET_TYPES["generic_infra"]["maint_rate"]` duplicates',
                      "person", _maint_rate_still_unbound),
    OpenItemPredicate("States share capacity, stock age, multiplier", "gap",
                      _states_share_capacity_and_stock),
    OpenItemPredicate("The pristine-gap condition inventory", "gap",
                      _pristine_gap_has_no_default_inventory),
    OpenItemPredicate("The service volumes V_s", "gap", _no_measured_service_profile_ships),
    OpenItemPredicate("ρ by use category", "gap", _retention_is_an_ordering),
    OpenItemPredicate("The tenure split", "gap", _no_tenure_split_ships),
    OpenItemPredicate("`u_parcel`'s `resolves_by` is half satisfied", "gap",
                      _parcel_count_unrestricted_to_serviced_classes),
    OpenItemPredicate("`ABATEMENT_HALF_CAPITAL_TEH`", "gap",
                      _abatement_pace_is_still_a_placeholder),
    OpenItemPredicate("`PERSONAL_EOH_COMPONENTS` shares", "gap",
                      _component_shares_are_still_desk_terms),
    OpenItemPredicate("`CDR_LABOR_HOURS_PER_TONNE` (0.6, Tier D)", "gap",
                      _cdr_labour_is_still_tier_d_at_0_6),
    OpenItemPredicate("Capital thermal intensities are Path-D placeholders", "gap",
                      _capital_thermal_profiles_are_placeholders),
    OpenItemPredicate("On the shipped constructor the federation is at mutual recognition",
                      "caveat", _shipped_federation_is_at_mutual_recognition),
    OpenItemPredicate("The claims register checks only some of the open items", "gap",
                      _predicate_coverage_is_incomplete),
    OpenItemPredicate("Dashboard PP and ecological pillars cannot fire", "gap",
                      _pillars_cannot_fire),
    OpenItemPredicate("The parcel index does not reach the fee", "gap",
                      _parcel_index_unread_by_the_fee),
    OpenItemPredicate("Dynamic stability — one cycle found", "gap",
                      _formation_cobweb_persists),
    OpenItemPredicate("Is the 15.5% threshold enough for care?", "person",
                      _care_short_at_the_threshold),
    OpenItemPredicate("Three bridge columns are untagged", "caveat",
                      _bridge_bound_matches_its_figure),
)


class TestTheOpenItemPredicates:
    """Per-item predicates: whether a typed item is still OPEN. A `gap` closes when its
    work lands; a `held` is breached when its work lands. That is one observable with
    opposite verdicts, so the kind had to come first
    ([record](record/verification.md#claims-register-test-history)).

    STATED GAPS:

      * COVERAGE IS PARTIAL. `_predicate_coverage_is_incomplete` holds the live
        count, and the ratchet below forbids only a fall. That predicate fails once
        every typed item is covered, so this admission cannot outlive its condition.
      * Some items carry `why_none` instead of a predicate, each with its reason, so
        `None` cannot be the silent default.
      * A predicate PROVES THE OBSERVABLE, NOT THE ITEM.
        `_anchor_comparison_unbuilt` checks a file name, and someone could build the
        thing under another name.
      * A `person` item gets a predicate only where the decision leaves a trace in code.
    """

    #: May not FALL. Rises when an item gains an observable; falls only when an
    #: item CLOSES, and a closing item is struck rather than deleted — so a fall
    #: means a predicate was dropped, which is the move this ratchet forbids.
    PREDICATE_FLOOR = 29

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
        """A predicate keyed to a missing item checks nothing. One keyed to the WRONG
        kind reads its result backwards, because `gap` and `held` invert on the same
        observable.
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
        assert "COVERAGE IS PARTIAL" in doc
        assert "PROVES THE OBSERVABLE, NOT THE ITEM" in doc
