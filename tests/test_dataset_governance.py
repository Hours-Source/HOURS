"""
The dataset-governance gate — where a constant and the data it governs disagree.

THE CLASS OF DEFECT THIS EXISTS FOR, and it is the one the provenance gate
structurally cannot reach. On 2026-08-17 `ETA_LAND_MASK_THRESHOLD` was found to
be:

    correctly tagged        (`normative`, with a decided_by)
    fully provenance-audited (it passed every check in `eoh provenance check`)
    and contradicted by the dataset it governed

Its `form:` asserted "the ERA5 mask is a fraction, so a THRESHOLD IS REQUIRED".
The η dataset that actually shipped records, in its own `_method.weighting`,
"land FRACTION (lsm), **not a binary threshold**". The generation step answered
the question the constant was posed to settle and answered it the other way.

**The provenance gate proves a constant is DOCUMENTED. It cannot prove the data
agrees with it.** Nothing connected the two, so nothing noticed.

WHAT A GATE CAN AND CANNOT DO HERE
----------------------------------
It CANNOT read two English sentences and decide they contradict. Claiming
otherwise would be worse than having no gate, because it would license not
looking.

What it CAN do is make the LOOKING a required, fingerprinted act:

  1. Find every self-describing method claim that says what the method did NOT
     do. A dataset stating a negation is precisely where a constant asserting
     the positive hides — it is how the η case reads once you see it.
  2. Require each such claim to be in a REVIEW REGISTER naming the constants
     checked against it and the outcome.
  3. FINGERPRINT the claim text. If a dataset is regenerated and its stated
     method changes, the fingerprint breaks and the review is stale — the build
     fails until someone re-checks the constants that depend on it.
  4. Require every dataset that NAMES a constant to have that pair registered:
     a dataset naming a constant is asserting something about it.

Point 3 is the mechanism. A review that cannot go stale is not a control, and
the η claim would have sailed through any one-time audit — it was written
correctly, once, and then diverged from the constant while both sat still.

THE HONEST LIMIT, stated so it is not mistaken for coverage: the η contradiction
would have been caught by this gate only at step 1→2, i.e. by forcing a human to
read `_method.weighting` against the constants in its domain. `eta_land.json`
names `ETA_BASIS` and `A_LAND_CLAIMED_M2` but never names
`ETA_LAND_MASK_THRESHOLD` — the dataset superseded a constant WITHOUT MENTIONING
IT, which is why the strong link (point 4) misses it and the weak one (point 1)
is the one that matters.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh" / "reference" / "data"

#: Generated from `data.py` and therefore names every constant by construction.
#: Including it would make the "dataset names a constant" link meaningless.
_GENERATED = {"constant_provenance.csv"}

#: Method text asserting what the method did NOT do. A dataset that says what it
#: is not is where a constant asserting the positive hides.
_NEGATION = re.compile(
    r"\bnot\b|\brather than\b|\binstead of\b|\bdoes not\b|\bnever\b|\bwithout\b",
    re.IGNORECASE,
)

#: THE REVIEW REGISTER. Every negation-bearing method claim, the constants
#: checked against it, and what the check found. The fingerprint is sha256[:12]
#: of the claim text — if the dataset is regenerated with a different stated
#: method, this breaks and the review must be redone.
#:
#: `outcome` must be one of: CONSISTENT | CONTRADICTED | NO_CONSTANT_DEPENDS
REVIEWED: dict[str, dict] = {
    "climate_feedback.json::historical.window_spread": {
        "fingerprint": "cb1666b31568",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "a robustness statement about the historical estimate's window sensitivity (<5%); no constant encodes the window."
        ),
    },
    "climate_feedback.json::historical.band_note": {
        "fingerprint": "ff9bb9a59eb2",
        "constants": ["THERMAL_F_NET_ERF_P05", "THERMAL_F_NET_ERF_P95"],
        "outcome": "CONSISTENT",
        "note": (
            "attributes the band to aerosol ERF uncertainty; the p05/p95 constants carry that band and are used by determinacy_map."
        ),
    },
    "multiplier_reference_bounds.json::outer_normalization.reason": {
        "fingerprint": "252563b5b30c",
        "constants": ["M_FACTOR_WEIGHTS"],
        "outcome": "CONSISTENT",
        "note": (
            "explains why outer normalization exists: stated 0.25 impact was operating at 0.134 effective. M_FACTOR_WEIGHTS carries the STATED weights and the file carries effective_weights separately, so both are visible rather than one silently standing for the other."
        ),
    },
    "multiplier_reference_bounds.json::outer_normalization.character": {
        "fingerprint": "431e04f774ea",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "'affine rescale, NOT tail-clipping' — a negation about the transform's character. No constant asserts clipping; winsorization is declared separately and applies to the INPUT bounds, not this rescale."
        ),
    },
    "multiplier_reference_bounds.json::reference_metrics.clip_note": {
        "fingerprint": "3b62cdd20aaf",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "~1% per tail is the winsorization BASELINE, not a fault; drift is measured as increase above it. A definition of the baseline, not a claim any constant contradicts."
        ),
    },
    "multiplier_reference_bounds.json::warning": {
        "fingerprint": "47b5f9ec3b67",
        "constants": [],
        "outcome": "CONSISTENT",
        "note": (
            "'Do NOT re-derive any of these per vintage. Re-derivation restores the circularity.' VERIFIED 2026-08-17: reference/onet_multipliers loads the FROZEN bounds via load_reference_bounds() and recomputes nothing. The instruction is honoured by the code that reads it."
        ),
    },
    "thermal_path_c.json::provenance_tiers.C": {
        "fingerprint": "6d2189e132a6",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "the tier vocabulary's own definition of C ('NOT verified this session'); a scheme definition, not a claim about a value."
        ),
    },
    "thermal_path_c.json::provenance_tiers.D": {
        "fingerprint": "9ca99f93b52c",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "as above, for tier D ('assumption or placeholder, not measured')."
        ),
    },
    "thermal_path_c.json::climate_parameters.lambda_feedback.note": {
        "fingerprint": "e0d343128c21",
        "constants": ["THERMAL_LAMBDA_FEEDBACK"],
        "outcome": "CONSISTENT",
        "note": (
            "carries 'Planck-only ~3.2' and 'NOT verified this session'. VERIFIED against research/thermal_lambda.planck_feedback (2026-08-17): the derived blackbody bound is 3.761, an UPPER bound on the real Planck response of ~3.2, and the function's docstring states that gap explicitly. This note was one of the two places the Planck term lived as prose before it was derived."
        ),
    },
    "thermal_path_c.json::climate_parameters.F_natural_erf.note": {
        "fingerprint": "65926d1a8a4e",
        "constants": ["THERMAL_F_NATURAL_ERF"],
        "outcome": "CONSISTENT",
        "note": (
            "natural forcing consumes budget but is NOT removable by labour — the wedge between the budget basis and the F3 basis, which the layer reports separately."
        ),
    },
    "thermal_path_c.json::climate_parameters.delta_T_lo_cases.note": {
        "fingerprint": "07f8c3b25734",
        "constants": ["THERMAL_DT_LO"],
        "outcome": "CONSISTENT",
        "note": (
            "'swept, not assessed. Result is dominated by this input' — the constant is the swept default and the sweep is what corridor/determinacy report."
        ),
    },
    "thermal_path_c.json::framework_parameters.commons_reserve_r.note": {
        "fingerprint": "e8f4ef0c8138",
        "constants": ["THERMAL_COMMONS_RESERVE"],
        "outcome": "CONSISTENT",
        "note": (
            "'recommended default, not derived' — the constant is tagged accordingly rather than claiming derivation."
        ),
    },
    "thermal_path_c.json::world_energy_2025._caveat": {
        "fingerprint": "88088c7215a2",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "the primary source was NOT fetched directly; both URLs are third-party commentary. A sourcing caveat on the energy mix, carried rather than hidden."
        ),
    },
    "thermal_path_c.json::kappa_coefficients._note": {
        "fingerprint": "68f2f83ee0d9",
        "constants": ["THERMAL_GRID_KAPPA_DEFAULT"],
        "outcome": "CONSISTENT",
        "note": (
            "'framework-defined, not measured'; PV siting-dependent. The constant is a declared default, not a measurement claim."
        ),
    },
    "thermal_path_c.json::national_data._WARNING": {
        "fingerprint": "caeb9fc1ecb3",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "national energy figures NOT verified this session; verification was attempted and failed. No data.py constant is derived from national_data — it is a per-collective table."
        ),
    },
    "thermal_path_c.json::national_data._fossil_nuclear_share_tier": {
        "fingerprint": "2a7f4ab0ff86",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "'D — estimated, not assessed per grid'; a tier assignment on the same table."
        ),
    },
    "thermal_path_c.json::world_energy_owid_2024._note": {
        "fingerprint": "6965d7450a7a",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "an independent cross-check computed from the shipped OWID CSV rather than recalled — the good direction, and it names no constant."
        ),
    },
    "thermal_path_c.json::world_energy_owid_2024._method": {
        "fingerprint": "74ffda56e489",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "the net-additive construction with the §6.1 nuclear-at-input-heat correction. A method statement for the cross-check series."
        ),
    },
    "thermal_path_c.json::world_energy_owid_2024._share_note": {
        "fingerprint": "68379d793265",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "reconciles 0.867 (OWID substitution basis) against the 0.931 quoted elsewhere by naming the denominator difference — a disagreement RESOLVED in the data rather than left to a reader."
        ),
    },
    "thermal_path_c.json::derived_outputs._basis": {
        "fingerprint": "cca236e6d83a",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "states which Phi and which forcing the derived outputs were computed on, so a handoff quoting a slightly different figure is explicable."
        ),
    },
    "thermal_path_c.json::derived_outputs._epsilon_max_note": {
        "fingerprint": "70eb05141c59",
        "constants": ["THERMAL_EPS_CURRENT"],
        "outcome": "CONSISTENT",
        "note": (
            "the binding multiple equals epsilon_max itself; consistent with global_ceiling's reported band over eps_current."
        ),
    },
    "thermal_path_c.json::_method": {
        "fingerprint": "56b397799a4b",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "A SUMMARY key added 2026-08-18, pointing at the nested underscore "
            "fields that are the authority. It asserts nothing new — every "
            "statement in it (the tier scheme and counts, the C5 correction, the "
            "unfetched primary source, the national-data warning) is registered "
            "separately above and was verified there. Added because the file "
            "documented itself thoroughly under nested keys while carrying "
            "nothing at top level, which is how a reader — and the first version "
            "of this gate — concluded it was undocumented."
        ),
    },
    "multiplier_reference_bounds.json::_method": {
        "fingerprint": "448687900654",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "A SUMMARY key added 2026-08-18. Restates the freeze, the "
            "winsorization, the affine outer normalization and the do-not-"
            "re-derive instruction, all of which are registered separately "
            "above. The re-derivation instruction was VERIFIED honoured "
            "2026-08-17: onet_multipliers loads the frozen bounds and "
            "recomputes nothing."
        ),
    },
    "eta_land.json::_method.weighting": {
        "fingerprint": "f81fa64c7283",
        "constants": ["ETA_LAND_MASK_THRESHOLD"],
        "outcome": "CONTRADICTED",
        "note": (
            "THE CASE THIS GATE WAS BUILT FOR. The constant asserted a binary "
            "threshold was required; this method field states the continuous "
            "land fraction was used and explicitly not a threshold. Retired "
            "2026-08-17 with superseded_by pointing at load_eta_land — NOT "
            "wired, because wiring it would reintroduce the all-or-nothing "
            "coastal treatment the data deliberately avoided."
        ),
    },
    "eta_land.json::_normalisation.basis": {
        "fingerprint": "5f0f3c6f86d6",
        "constants": ["A_LAND_CLAIMED_M2"],
        "outcome": "CONSISTENT",
        "note": (
            "Caught by the NAMES-A-CONSTANT trigger, not the negation one — it "
            "states no negation. The dataset says the η mean is normalised on "
            "the same footing as A_LAND_CLAIMED_M2 at 1.35e14 m², and the "
            "constant is 1.35e14 exactly. Verified 2026-08-17."
        ),
    },
    "eta_land.json::_basis.shipped_default": {
        "fingerprint": "079f49733d19",
        "constants": ["ETA_BASIS"],
        "outcome": "CONSISTENT",
        "note": "names ETA_BASIS and states clear_sky; the constant agrees.",
    },
    "eta_land.json::_basis.all_sky_retained": {
        "fingerprint": "b8dabb92efcc",
        "constants": ["ETA_BASIS"],
        "outcome": "CONSISTENT",
        "note": "all-sky retained as the reality check beside the shipped basis.",
    },
    "eta_land.json::_limitations.seasonal": {
        "fingerprint": "5067a4d6b4b0",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "a sampling limitation of the η series; no constant asserts the sampling.",
    },
    "eta_land.json::_limitations.day_of_month": {
        "fingerprint": "9453487980a5",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "as above — weather noise in the sampled climatology.",
    },
    "eta_land.json::_marginal_capacity_investigated.result": {
        "fingerprint": "6d25b23485ec",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": (
            "a recorded NEGATIVE result: marginal capacity is not determinable "
            "from this sampling. No constant claims it is, which is the correct "
            "state — the repo withholds rather than ships a number."
        ),
    },
    "eta_land.json::_marginal_capacity_investigated.disagreement": {
        "fingerprint": "64253d0d5e0c",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "the three estimators' spread, supporting the negative result above.",
    },
    "eta_land.json::_marginal_capacity_investigated.resolves_by": {
        "fingerprint": "157e656005ed",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "what would settle marginal capacity; nothing depends on it yet.",
    },
    "eta_land.json::_marginal_capacity_investigated.status": {
        "fingerprint": "804072b83f1c",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "η ships on total clear-sky OLR; the objection stands and is recorded.",
    },
    "cumulative_emissions.json::_why": {
        "fingerprint": "609a6a7a8b62",
        "constants": ["CDR_ALLOCATION_BASIS"],
        "outcome": "CONSISTENT",
        "note": (
            "States CDR_ALLOCATION_BASIS = 'responsibility' and the constant is "
            "'responsibility'. Verified 2026-08-17. Note this claim asserts a "
            "VALUE, not a method, which is the strongest form the named-constant "
            "trigger catches — a divergence here would be a straight "
            "contradiction rather than a judgement call."
        ),
    },
    "cumulative_emissions.json::_basis_choice.DECIDED 2026-08-05": {
        "fingerprint": "365166075faa",
        "constants": ["CDR_ALLOCATION_BASIS"],
        "outcome": "CONSISTENT",
        "note": "KEEP incl_luc; the constant carries that basis.",
    },
    "cumulative_emissions.json::_unattributed.DECIDED 2026-08-05": {
        "fingerprint": "3e1e8ec9e3c8",
        "constants": ["CDR_UNATTRIBUTED_POLICY"],
        "outcome": "CONSISTENT",
        "note": "pro_rata redistribution; the constant names the same policy.",
    },
    "cumulative_emissions.json::_unattributed.note": {
        "fingerprint": "d27559ff09cf",
        "constants": ["CDR_UNATTRIBUTED_POLICY"],
        "outcome": "CONSISTENT",
        "note": (
            "raw shares sum to 0.975/0.998, NOT to 1 — the residual is shipping "
            "and aviation, which is exactly what the pro-rata policy exists to "
            "redistribute rather than a discrepancy with it."
        ),
    },
    "cumulative_emissions.json::_truncation_warning": {
        "fingerprint": "54fdc0d74186",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "a warning about start-year truncation; no constant sets the start year.",
    },
    "cumulative_emissions.json::_doctrine": {
        "fingerprint": "5b228f261287",
        "constants": [],
        "outcome": "NO_CONSTANT_DEPENDS",
        "note": "the forward-looking doctrine; a framing statement, not a method a constant encodes.",
    },
    "climate_feedback.json::_the_frame_problem.statement": {
        "fingerprint": "76e8db89efa9",
        "constants": ["THERMAL_LAMBDA_FEEDBACK"],
        "outcome": "CONSISTENT",
        "note": (
            "'lambda is NOT one number' — the constant is tagged with its frame "
            "(EQUILIBRIUM) and research/thermal_lambda.lambda_for_frame carries "
            "the distinction, so the dataset's warning is honoured rather than "
            "contradicted. The Planck bound added 2026-08-17 is the only "
            "physical anchor on it."
        ),
    },
    "climate_feedback.json::_the_frame_problem.equilibrium": {
        "fingerprint": "c92175f70dd2",
        "constants": ["THERMAL_LAMBDA_FEEDBACK"],
        "outcome": "CONSISTENT",
        "note": "commitment accounting; the shipped λ is the equilibrium frame.",
    },
    "climate_feedback.json::_the_frame_problem.historical": {
        "fingerprint": "b67f2f319c48",
        "constants": ["THERMAL_LAMBDA_FEEDBACK"],
        "outcome": "CONSISTENT",
        "note": "the transient frame is explicitly REJECTED by the framework; not the shipped one.",
    },
    "climate_feedback.json::_sensitivity_is_first_class": {
        "fingerprint": "65b6ab6cc996",
        "constants": ["THERMAL_LAMBDA_FEEDBACK"],
        "outcome": "CONSISTENT",
        "note": (
            "no ψ*-derived figure may be published without the band — honoured "
            "by lambda_sensitivity and determinacy_map, which report it."
        ),
    },
}

_VALID_OUTCOMES = {"CONSISTENT", "CONTRADICTED", "NO_CONSTANT_DEPENDS"}


def _constant_names() -> set[str]:
    from utils.provenance import load
    scan = load()
    records = scan.records if hasattr(scan, "records") else scan
    return {
        r.name for r in (records.values() if isinstance(records, dict) else records)
    }


def _iter_claims():
    """
    (key, text) for every self-describing claim that is REVIEW-WORTHY.

    Two independent triggers, and they are complementary rather than redundant:

      NEGATION      the claim says what the method did NOT do — where a constant
                    asserting the positive hides. This is the trigger that
                    reaches the η case.
      NAMES A CONSTANT   the claim mentions a `data.py` constant by name, so it
                    is asserting something about it directly. Unambiguous where
                    it applies, but it MISSES the η case entirely —
                    `eta_land.json` never named ETA_LAND_MASK_THRESHOLD.

    Neither subsumes the other, which is why both run.
    """
    for path in sorted(DATA_DIR.glob("*.json")):
        if path.name in _GENERATED:
            continue
        doc = json.loads(path.read_text())
        if not isinstance(doc, dict):
            continue
        names = _constant_names()

        def walk(node: dict, prefix: str = ""):
            # DESCEND INTO EVERYTHING. The first version of this gate only
            # entered top-level keys beginning with "_", on the assumption that
            # self-description lives there. It does in `eta_land.json` and
            # `cumulative_emissions.json` — and NOT in the other two, which
            # document themselves just as thoroughly under nested `_` keys
            # (`thermal_path_c.json`: `climate_parameters._c5_correction`,
            # `national_data._WARNING`, `derived_outputs._superseded`) or under
            # plain descriptive ones (`multiplier_reference_bounds.json`:
            # `outer_normalization.reason`, `.character`).
            #
            # The narrow traversal reported those two files as carrying no
            # method metadata AT ALL. They carry 19 review-worthy claims between
            # them, and the gate was blind to every one — it had inferred a
            # convention from two files and enforced it as if it were universal.
            for key, value in node.items():
                full = f"{prefix}{key}"
                if isinstance(value, dict):
                    yield from walk(value, full + ".")
                    continue
                if isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            yield from walk(item, f"{full}[{i}].")
                    continue
                if isinstance(value, str) and (
                    _NEGATION.search(value)
                    or any(
                        len(n) > 6 and re.search(rf"\b{n}\b", value)
                        for n in names
                    )
                ):
                    yield full, value

        for key, text in walk(doc):
            yield f"{path.name}::{key}", text


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


class TestEveryNegationClaimIsReviewed:
    """
    A dataset that says what its method did NOT do is where a constant asserting
    the positive hides. Each such claim must have been read against the
    constants in its domain.
    """

    def test_every_claim_is_in_the_register(self) -> None:
        unreviewed = [k for k, _ in _iter_claims() if k not in REVIEWED]
        assert not unreviewed, (
            "these datasets state what their method did NOT do, and no one has "
            "checked the constants against them:\n  " + "\n  ".join(unreviewed)
        )

    def test_no_register_entry_is_stale(self) -> None:
        """
        An entry for a claim that no longer exists is a review nobody exercises
        — the `unused_innocuous_names` lesson, where two allowlist entries went
        stale within an hour of shipping.
        """
        live = {k for k, _ in _iter_claims()}
        stale = sorted(set(REVIEWED) - live)
        assert not stale, f"registered reviews for claims that no longer exist: {stale}"

    def test_fingerprints_still_match(self) -> None:
        """
        THE MECHANISM. A review that cannot go stale is not a control. If a
        dataset is regenerated and its stated method changes, this breaks and
        the constants that depend on it must be re-checked.
        """
        drifted = []
        for key, text in _iter_claims():
            entry = REVIEWED.get(key)
            if entry and entry["fingerprint"] != _fingerprint(text):
                drifted.append(
                    f"{key}\n      registered {entry['fingerprint']}, "
                    f"now {_fingerprint(text)}\n      -> re-check "
                    f"{entry['constants'] or 'the constants in its domain'}"
                )
        assert not drifted, (
            "a dataset's stated method has CHANGED since it was reviewed:\n  "
            + "\n  ".join(drifted)
        )


class TestTheRegisterIsHonest:

    def test_every_entry_states_an_outcome_and_a_reason(self) -> None:
        for key, entry in REVIEWED.items():
            assert entry["outcome"] in _VALID_OUTCOMES, f"{key}: bad outcome"
            assert entry["note"].strip(), f"{key}: reviewed with no note"
            assert isinstance(entry["constants"], list), f"{key}: constants must be a list"

    def test_every_named_constant_exists(self) -> None:
        """A review against a constant that does not exist is not a review."""
        from utils.provenance import load
        scan = load()
        records = scan.records if hasattr(scan, "records") else scan
        names = {r.name for r in (records.values() if isinstance(records, dict) else records)}
        missing = sorted(
            {c for e in REVIEWED.values() for c in e["constants"]} - names
        )
        assert not missing, f"reviews name constants that do not exist: {missing}"

    def test_a_contradiction_must_be_resolved_in_the_constant(self) -> None:
        """
        CONTRADICTED is not a place to park a known defect. Every constant a
        dataset contradicts must carry `superseded_by:` — the resolution the η
        case received — so the disagreement is recorded where a reader of the
        constant will meet it.
        """
        from utils.provenance import load
        scan = load()
        records = scan.records if hasattr(scan, "records") else scan
        by_name = {
            r.name: r for r in (records.values() if isinstance(records, dict) else records)
        }
        unresolved = []
        for key, entry in REVIEWED.items():
            if entry["outcome"] != "CONTRADICTED":
                continue
            for const in entry["constants"]:
                rec = by_name.get(const)
                if rec is None or not getattr(rec, "superseded_by", ""):
                    unresolved.append(f"{const} (contradicted by {key})")
        assert not unresolved, (
            "a dataset contradicts these constants and they do not say so:\n  "
            + "\n  ".join(unresolved)
        )

    def test_the_scan_reaches_real_claims(self) -> None:
        """
        Guards the gate: a renamed metadata key or a moved directory would leave
        it inspecting nothing while passing. `exercised` asserted alongside
        `passes`, the provenance flow-trace discipline.
        """
        found = list(_iter_claims())
        assert len(found) >= 15, f"only {len(found)} claims found; the scan has gone blind"
        assert any("eta_land.json" in k for k, _ in found)


class TestDatasetsThatNameAConstant:
    """
    The strong link: a dataset naming a constant is asserting something about
    it. Weaker in coverage than the negation scan — `eta_land.json` never named
    `ETA_LAND_MASK_THRESHOLD`, which is exactly how that contradiction survived
    — but where it applies it is unambiguous.
    """

    def test_every_named_pair_is_reviewed(self) -> None:
        from utils.provenance import load
        scan = load()
        records = scan.records if hasattr(scan, "records") else scan
        names = {
            r.name for r in (records.values() if isinstance(records, dict) else records)
        }
        reviewed_constants = {c for e in REVIEWED.values() for c in e["constants"]}

        unreviewed = []
        for path in sorted(DATA_DIR.glob("*")):
            if path.name in _GENERATED:
                continue
            try:
                text = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for name in names:
                if len(name) > 6 and re.search(rf"\b{name}\b", text):
                    if name not in reviewed_constants:
                        unreviewed.append(f"{path.name} names {name}")
        assert not unreviewed, (
            "these datasets name a constant and the pair has never been "
            "reviewed:\n  " + "\n  ".join(sorted(unreviewed))
        )


class TestTheGateBites:

    def test_an_unregistered_negation_claim_fails(self) -> None:
        """Demonstrated, not asserted."""
        fake = {"eta_land.json::_method.invented": "this is not how it was done"}
        unreviewed = [k for k in fake if k not in REVIEWED]
        assert unreviewed, "the gate would not notice a new unreviewed claim"

    def test_a_changed_claim_breaks_its_fingerprint(self) -> None:
        entry = REVIEWED["eta_land.json::_method.weighting"]
        assert _fingerprint("a different method entirely") != entry["fingerprint"]

    def test_the_eta_case_is_recorded_as_contradicted(self) -> None:
        """The case this gate was built from must stay visible in it."""
        entry = REVIEWED["eta_land.json::_method.weighting"]
        assert entry["outcome"] == "CONTRADICTED"
        assert "ETA_LAND_MASK_THRESHOLD" in entry["constants"]
