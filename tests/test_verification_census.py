"""
The verification-cost census — `reference/verification.py`.

WHAT IS ACTUALLY AT STAKE. The anchor comparison concedes that gold and
fixed-supply protocols need no measurement apparatus, and names verification
cost as the term that decides whether this framework is cheaper to audit than
they are. That term is absent from all four EOH domains while
`core/multipliers.assess_tier` REQUIRES the apparatus and books nothing for it.
This census is the first half of pricing it.

WHAT THESE TESTS ARE FOR, and it is not the total. The number is a bound and
will move. What must not move without someone noticing is the DISCIPLINE around
it: that the occupational judgement is isolated and reasoned, that the exclusions
are named rather than filtered, that the set is disjoint from the servicing
census by construction rather than by inspection, and that the two error
directions are never netted into a single flattering figure.

REPORTING ONLY. Nothing imports this module and no shipped number moves; the
last test pins that.
"""

from __future__ import annotations

import inspect

import pytest

from hours_eoh.reference import verification as V
from hours_eoh.reference.servicing import SERVICING_ATTRIBUTIONS


ALL_ATTRIBUTED = tuple(V.VERIFICATION_ATTRIBUTIONS) + tuple(V.BROAD_SCOPE_ADDITIONS)


class TestDisjointFromServicingByConstruction:
    """
    THE DOUBLE-APPLICATION GUARD (recurring failure mode 11). Servicing charges
    the land holder for building inspection and title search through GUF. If
    either appeared here too, the same hours would be billed twice — and the
    defect would be invisible in each census alone, which is exactly the shape
    that makes mode 11 expensive.
    """

    def test_the_two_censuses_share_no_occupation(self):
        serv = {str(a["occ6"]) for a in SERVICING_ATTRIBUTIONS}
        mine = {str(a["occ6"]) for a in ALL_ATTRIBUTED}
        assert not (serv & mine), (
            f"counted in both censuses: {sorted(serv & mine)}. One of them is "
            "billing hours the other already charges."
        )

    def test_the_two_overlapping_occupations_are_excluded_by_name(self):
        """
        Not merely absent — ABSENT FOR A STATED REASON. An occupation that is
        missing because nobody thought of it looks identical to one deliberately
        held out, and only the second survives a reader.
        """
        excluded = {str(e["occ6"]): e for e in V.EXCLUDED_OCCUPATIONS}
        for occ in ("474011", "232093"):
            assert occ in excluded, f"{occ} is in servicing and must be excluded here by name"
            assert "ALREADY COUNTED" in excluded[occ]["reason"], (
                f"{occ}'s exclusion must say it is the disjointness constraint, "
                "not a judgement call — a future editor will otherwise re-argue it"
            )

    def test_the_disjointness_claim_names_both_codes(self):
        for occ in ("474011", "232093"):
            assert occ in V.DISJOINT_FROM_SERVICING


class TestTheJudgementIsIsolatedAndReasoned:

    @pytest.mark.parametrize("att", ALL_ATTRIBUTED, ids=lambda a: a["occ6"])
    def test_every_attribution_carries_a_basis(self, att):
        assert att["basis"].strip(), f"{att['occ6']} has no stated basis"
        assert len(att["basis"]) > 40, (
            f"{att['occ6']}'s basis is too short to be an argument"
        )

    @pytest.mark.parametrize("exc", V.EXCLUDED_OCCUPATIONS, ids=lambda e: e["occ6"])
    def test_every_exclusion_carries_a_reason(self, exc):
        assert len(exc["reason"]) > 40, f"{exc['occ6']} is excluded without a reason"

    def test_no_occupation_is_counted_twice(self):
        codes = [str(a["occ6"]) for a in ALL_ATTRIBUTED]
        assert len(codes) == len(set(codes)), "an occupation appears in two scopes"

    def test_nothing_is_both_attributed_and_excluded(self):
        attributed = {str(a["occ6"]) for a in ALL_ATTRIBUTED}
        excluded = {str(e["occ6"]) for e in V.EXCLUDED_OCCUPATIONS}
        assert not (attributed & excluded)

    def test_the_manufacturing_inspectors_are_excluded(self):
        """
        THE ROLE-MIX TRAP, pinned. `519061` is 598.1k of manufacturing quality
        control and is what a keyword search for 'inspector' returns first. It
        would be the single largest line in the core census if admitted.
        """
        excluded = {str(e["occ6"]) for e in V.EXCLUDED_OCCUPATIONS}
        assert "519061" in excluded

    def test_the_scaling_basis_is_a_separate_judgement(self):
        """
        `SCALING_BASIS` answers a DIFFERENT question from the census total — the
        census asks how many hours, this asks what quantity they follow. Merging
        them is what made the ten GUF ratios unfalsifiable.
        """
        functions = {a["function"] for a in ALL_ATTRIBUTED}
        assert functions <= set(V.SCALING_BASIS), (
            f"a register function has no declared scaling basis: "
            f"{sorted(functions - set(V.SCALING_BASIS))}"
        )

    def test_measurement_is_the_one_that_does_not_follow_the_register(self):
        """The distinction that keeps the term honest: the world must be
        measured whether or not anyone registers it."""
        assert "NOT scale with the register" in V.SCALING_BASIS["measurement"]


class TestTheBoundsAreBoundsAndNotAnEstimate:

    def test_core_is_a_subset_of_broad(self):
        core = V.verification_workers("core")
        broad = V.verification_workers("broad")
        assert broad["total_workers"] > core["total_workers"]
        for fn, v in core["by_function"].items():
            assert broad["by_function"][fn] >= v, f"{fn} shrank in the wider scope"

    def test_no_occupation_is_missing_from_the_registry(self):
        for scope in ("core", "broad"):
            assert V.verification_workers(scope)["missing_from_registry"] == []

    def test_there_is_no_weight_to_tune_anywhere(self):
        """
        THE POINT OF THE TWO-SCOPE DESIGN. A weighted middle would put a number
        nothing measures in front of the answer it decides — `132011` alone is
        1.65M and dominates any total it enters. Both scopes are measured
        headcounts, so there is no coefficient to fit to a desired result.
        """
        numeric_tables = {
            name: obj for name, obj in vars(V).items()
            if not name.startswith("_") and isinstance(obj, dict)
            and obj and all(isinstance(v, (int, float)) for v in obj.values())
        }
        assert not numeric_tables, (
            f"a numeric per-occupation table appeared ({sorted(numeric_tables)}); "
            "the bound stops being a bound the moment a coefficient can be tuned"
        )
        for att in ALL_ATTRIBUTED:
            assert set(att) == {"occ6", "function", "title", "basis"}, (
                f"{att['occ6']} carries a field beyond the census's four — if it "
                "is a weight, the two-scope design has been abandoned"
            )

    def test_the_gap_between_the_bounds_is_one_nameable_code(self):
        """
        A wide bound is acceptable when its width has a single measurable cause
        and unacceptable when it is diffuse. Pinned so that if the gap ever stops
        being mostly `132011`, someone re-reads why the bound is wide.
        """
        core = V.verification_workers("core")["total_workers"]
        broad = V.verification_workers("broad")["total_workers"]
        emp = V.load_registry_employment()
        accountants = emp["132011"] * 1_000.0
        assert accountants / (broad - core) > 0.75, (
            "the core/broad gap is no longer dominated by Accountants and "
            "Auditors, so `what_this_cannot_settle` is now wrong about it"
        )

    def test_an_unknown_scope_raises(self):
        with pytest.raises(ValueError, match="scope must be"):
            V.verification_workers("everything")

    def test_the_total_moves_when_an_occupation_is_withheld(self):
        """
        The census is a real sum, not a constant with a loop around it. Drops the
        largest core code and checks the total falls by exactly its headcount.
        """
        emp = V.load_registry_employment()
        without = {k: v for k, v in emp.items() if k != "131041"}
        full = V.verification_workers("core", employment=emp)["total_workers"]
        less = V.verification_workers("core", employment=without)
        assert less["missing_from_registry"] == ["131041"]
        assert full - less["total_workers"] == pytest.approx(
            emp["131041"] * 1_000.0, rel=1e-12
        )


class TestItStatesItsOwnGaps:
    """A checker that does not declare its limits reads as stronger than it is."""

    def test_both_error_directions_are_stated(self):
        d = V.direction_of_error()
        assert len(d["over"]) > 80 and len(d["under"]) > 80

    def test_the_two_directions_are_never_netted(self):
        d = V.direction_of_error()
        assert d["netted"] is None, (
            "a single reconciled figure appeared. The two errors are in "
            "different quantities; combining them invents a distribution."
        )
        assert len(d["why_not_netted"]) > 60

    def test_it_says_what_it_cannot_settle(self):
        gaps = V.what_this_cannot_settle()
        assert len(gaps) >= 4
        assert all(len(g) > 60 for g in gaps)

    def test_the_governance_parameters_are_named_as_unset(self):
        """
        `SCALING_BASIS` needs a re-review frequency and an appeal rate, and no
        governance model here sets either. That is a gap in the measurement, not
        a detail, and it has to be findable from the module itself.
        """
        joined = " ".join(V.what_this_cannot_settle())
        assert "re-review" in joined and "appeal rate" in joined


class TestItChangesNothing:
    """
    REPORTING ONLY, pinned. Phase 3 — whether this term enters `total_eoh` — is
    a theory change that moves every ratio computed against the obligation, and
    it is not taken here.
    """

    def test_no_module_outside_reference_imports_it(self):
        import pathlib
        root = pathlib.Path(V.__file__).resolve().parents[1]
        offenders = [
            p.relative_to(root).as_posix()
            for p in root.rglob("*.py")
            if p.name != "verification.py"
            and "reference/verification" in p.read_text(encoding="utf-8", errors="ignore")
        ]
        assert not offenders, (
            f"{offenders} import the census. It is reporting only until the "
            "Phase 3 sign-off says otherwise."
        )

    def test_it_imports_nothing_outside_the_reference_layer(self):
        src = inspect.getsource(V)
        bad = [
            ln for ln in src.splitlines()
            if ln.startswith(("import hours_eoh", "from hours_eoh"))
            and "hours_eoh.reference" not in ln
        ]
        assert not bad, f"reference/ must not import other layers: {bad}"
