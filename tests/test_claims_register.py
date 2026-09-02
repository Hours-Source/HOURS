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
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from typing import Callable

import pytest

CLAUDE_MD = pathlib.Path(__file__).resolve().parent.parent / "CLAUDE.md"


@dataclass(frozen=True)
class Claim:
    """A statement in CLAUDE.md that the code can answer."""

    anchor: str                 #: exact substring locating the claim
    check: Callable[[], bool]   #: the predicate the claim asserts
    why: str                    #: what goes wrong if it drifts


def _text() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


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
    return tagged == 294 and total == 294


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
    root = CLAUDE_MD.parent
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
    root = CLAUDE_MD.parent
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
        anchor="provenance 294/294",
        check=_provenance_is_complete,
        why=(
            "the coverage figure quoted to institutions; 265 -> 288 -> 292 -> 294. "
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
