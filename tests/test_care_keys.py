"""Care has two drivers, and until 2026-09-04 they shared one number.

`AGE_GROUPS[band]["eoh_weight"]` bundled self-maintenance with care received. The care
part bundled two obligations with different drivers: **dependant care tracks fertility
and household composition; frailty care tracks longevity and morbidity.** Bundled,
neither had its own source to measure against
([record](record/personal.md#care-keys-split)).

THE SPLIT IS ADDITIVE. `self_weight + care_weight == eoh_weight` exactly, and no shipped
number moves.

THE SHARES ARE MEASURED, THE LEVELS ARE NOT. `AGE_CARE_SHARE_*` is the ATUS
care/(self+care) ratio per band. The model applies it to the SHIPPED weight, because the
measured levels are lower bounds. The ratio transfers and the level does not
(`mtus_time_use.band_ratio`'s rule).

STATED GAPS:

  * THE SPLIT IS 89/11 BY VOLUME. Weighted by population share, dependant care
    is ~89% of measured care and frailty care ~11%. An actuarial table settles
    the frailty key, so about a ninth of care; the dominant term needs a
    different instrument.
  * THE ELDERLY SHARE IS A LOWER BOUND, AND ITS TWO ROUTES DISAGREE (5.46× on
    2026-10-17, `elderly_route_disagreement`). It is a mean over 35 years of age and
    excludes the institutional population by construction. Splitting the key
    fixes neither; it makes them addressable.
  * NOTHING IS KEYED ON FRAILTY YET. `care_key` says WHICH driver a band's
    care belongs to. The frailty socket (`scenarios/frailty.py`) ships with no
    default, and nothing supplies a morbidity trajectory.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import AGE_GROUPS

KEYS = {"dependant", "frailty"}


class TestTheSplitIsAdditive:

    def test_self_plus_care_reassembles_the_shipped_weight(self) -> None:
        for name, g in AGE_GROUPS.items():
            assert g["self_weight"] + g["care_weight"] == pytest.approx(
                g["eoh_weight"], rel=1e-12), name

    def test_no_shipped_aggregate_moved(self) -> None:
        """The split renames nothing and moves no number."""
        w = sum(g["fraction"] * g["eoh_weight"] for g in AGE_GROUPS.values())
        assert w == pytest.approx(1.3528, abs=1e-4)


class TestTheKeysAreDistinct:

    def test_every_band_declares_a_key_from_the_closed_set(self) -> None:
        for name, g in AGE_GROUPS.items():
            assert g["care_key"] in KEYS, f"{name}: {g['care_key']!r}"

    def test_minors_are_dependant_and_adults_are_frailty(self) -> None:
        """A minor who receives care is not impaired, only young. An adult who receives
        care does so because of impairment.
        """
        for name, g in AGE_GROUPS.items():
            lo, hi = g["range"]
            expected = "dependant" if hi < 18 else "frailty"
            assert g["care_key"] == expected, name

    def test_both_keys_carry_real_volume(self) -> None:
        """A partition with an empty side is not a partition."""
        vol = {k: 0.0 for k in KEYS}
        for g in AGE_GROUPS.values():
            vol[g["care_key"]] += g["fraction"] * g["care_weight"]
        assert all(v > 0.0 for v in vol.values()), vol
        # and the asymmetry is the finding, so it is pinned
        assert vol["dependant"] > 4.0 * vol["frailty"], (
            "dependant care is no longer the dominant term. If that is real, "
            "the 'an actuarial table settles a ninth of care' claim in "
            "record/personal.md needs re-deriving."
        )


class TestTheSharesAreBoundToTheirSource:
    """`data.py` is the base layer and cannot import a scenario, so a test binds the
    constants to their source (the remedy failure mode 4 names). Without it,
    `AGE_CARE_SHARE_*` is a copy of a value computed elsewhere, free to drift.
    """

    def test_each_share_matches_the_live_atus_measurement(self) -> None:
        from hours_eoh.scenarios.care_curve import implied_weights
        # The ELDERLY share awaits re-adoption (2026-10-02): the 80 cell was
        # divided by the age-80 population where ATUS codes ages 80–84 there.
        # Both sides pinned until the author re-adopts — see
        # tests/test_care_demand.py::test_the_elderly_weight_was_adopted_from_this_measurement.
        pending = {"elderly": (0.128292, 0.120525)}
        for row in implied_weights()["rows"]:
            total = row["total_minutes_per_day"]
            measured = row["care_minutes_per_day"] / total if total else 0.0
            if row["band"] in pending:
                shipped, corrected = pending[row["band"]]
                assert AGE_GROUPS[row["band"]]["care_share"] == shipped
                assert measured == pytest.approx(corrected, abs=5e-6)
                continue
            assert AGE_GROUPS[row["band"]]["care_share"] == pytest.approx(
                measured, abs=5e-6), (
                f"{row['band']}: shipped care_share has drifted from the ATUS "
                "measurement it restates."
            )


class TestTheEpsilonDriftIsRetired:
    """
    Retired 2026-09-04, and the retirement is only real if nothing reads it.
    """

    def test_nothing_in_the_package_reads_it(self) -> None:
        import ast
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh"
        readers = []
        for path in root.rglob("*.py"):
            if path.name == "data.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Name)
                        and node.id == "ELDERLY_EOH_EPSILON_FACTOR"):
                    readers.append(str(path.relative_to(root)))
        # Since the 2026-09-16 deletion this would pass vacuously — a name that
        # does not exist is read by nobody — so the sibling test asserts the
        # assignment is gone from data.py as well. Kept because a reintroduced
        # constant WITH readers must fail here, not only there.
        assert not readers, (
            f"ELDERLY_EOH_EPSILON_FACTOR is read again in {sorted(set(readers))}. "
            "It asserted an answer to the morbidity compression/expansion "
            "question and drove two different mechanisms from one scalar; a "
            "morbidity trajectory belongs on the `frailty` care key."
        )

    def test_the_age_distribution_no_longer_drifts_with_epsilon(self) -> None:
        from hours_eoh.core.trajectory import canonical_age_distribution
        base = canonical_age_distribution(0.0)
        for eps in (0.40, 0.90, 0.99):
            assert canonical_age_distribution(eps) == base, (
                f"the age distribution moved at ε={eps}. Demography is an "
                "intake, not a function of automation."
            )

    def test_the_two_paths_now_agree_on_elderly_eoh(self) -> None:
        """
        `total_eoh` never applied the intensity multiplier and
        `population_eoh_curve` did, so they reported different elderly EOH at
        the same ε — two accounts of one quantity.
        """
        from hours_eoh.core.population import population_eoh_curve
        dist = {k: v["fraction"] * 1e6 for k, v in AGE_GROUPS.items()}
        base_rate = 1000.0
        for eps in (0.0, 0.90):
            rows = {r["age_group"]: r for r in
                    population_eoh_curve(dist, epsilon=eps, base_rate=base_rate)}
            eld = rows["elderly"]
            assert eld["eoh_per_capita"] == pytest.approx(
                base_rate * AGE_GROUPS["elderly"]["eoh_weight"], rel=1e-12), (
                f"at ε={eps} population_eoh_curve applies a factor total_eoh "
                "does not — two accounts of elderly EOH."
            )

    def test_the_constant_is_deleted_and_the_reason_is_recorded(self) -> None:
        """The repo deleted the constant (2026-09-16, author decision), and
        `record/personal.md` holds its reasoning. It does not qualify for the `baseline`
        tag: a baseline is kept for comparison with something live, and this constant
        had no readers ([record](record/personal.md#elderly-epsilon-factor-deleted)).
        """
        import pathlib
        repo = pathlib.Path(__file__).resolve().parent.parent
        data_py = (repo / "hours_eoh" / "data.py").read_text(encoding="utf-8")
        assert "ELDERLY_EOH_EPSILON_FACTOR:" not in data_py, (
            "the constant is back in data.py. It asserted an answer to the "
            "morbidity compression/expansion question and drove two mechanisms "
            "from one scalar; a morbidity trajectory belongs on the `frailty` "
            "care key."
        )
        recorded = (repo / "record" / "personal.md").read_text(encoding="utf-8")
        assert "ELDERLY_EOH_EPSILON_FACTOR" in recorded, (
            "the constant was deleted but its reasoning is nowhere in "
            "record/personal.md — deleting the tag block without recording why "
            "is exactly what the retained-not-deleted argument warned against"
        )

    def test_the_stated_gaps_are_still_stated(self) -> None:
        doc = __doc__ or ""
        assert "STATED GAPS" in doc
        assert "89/11 BY VOLUME" in doc
        assert "NOTHING IS KEYED ON FRAILTY YET" in doc
