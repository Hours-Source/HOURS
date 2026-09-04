"""
Care has two drivers, and until 2026-09-04 they shared one number.

`AGE_GROUPS[band]["eoh_weight"]` bundled self-maintenance with care received,
and the care part bundled two obligations that move on entirely different
drivers: **dependant care tracks fertility and household composition; frailty
care tracks longevity and morbidity.** Bundled, neither could be measured
against its own source, and `ELDERLY_EOH_EPSILON_FACTOR` asserted one answer
for both at once.

THE SPLIT IS ADDITIVE. `self_weight + care_weight == eoh_weight` exactly, and
no shipped number moves — the same discipline the AGE_GROUPS split used.

THE SHARES ARE MEASURED, THE LEVELS ARE NOT. `AGE_CARE_SHARE_*` is the ATUS
care/(self+care) ratio per band; it is applied to the SHIPPED weight, not to
the measured one, because the measured levels are lower bounds and differ.
The ratio transfers, the level does not — `mtus_time_use.band_ratio`'s rule.

STATED GAPS:

  * THE SPLIT IS 83/12 BY VOLUME. Weighted by population share, dependant care
    is ~83% of measured care and frailty care ~12%. An actuarial table settles
    the frailty key and therefore about an eighth of care; the dominant term
    needs a different instrument entirely.
  * THE ELDERLY SHARE IS A LOWER BOUND AND ITS TWO ROUTES DISAGREE 7.1x.
    30.5 min/day is a mean over 35 years of age and excludes the institutional
    population by construction — the two errors that make an age key the wrong
    key. Splitting the key does not fix either; it makes them addressable.
  * NOTHING IS KEYED ON FRAILTY YET. `care_key` says WHICH driver a band's
    care belongs to. It does not supply a morbidity trajectory, and no
    frailty socket exists — that is the open item, not this file.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import AGE_GROUPS, ELDERLY_EOH_EPSILON_FACTOR

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
        """
        The classification, asserted rather than left to the reader: a minor
        receiving care is not impaired, they are young. An adult receiving care
        is doing so because of impairment.
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
            "the 'an actuarial table settles an eighth of care' claim in "
            "record/personal.md needs re-deriving."
        )


class TestTheSharesAreBoundToTheirSource:
    """
    `data.py` is the base layer and cannot import a scenario, so the constants
    are bound to their source BY TEST — the remedy failure mode 4 names for
    exactly this case. Without this, `AGE_CARE_SHARE_*` is a copy of a value
    computed elsewhere and free to drift from it.
    """

    def test_each_share_matches_the_live_atus_measurement(self) -> None:
        from hours_eoh.scenarios.care_curve import implied_weights
        for row in implied_weights()["rows"]:
            total = row["total_minutes_per_day"]
            measured = row["care_minutes_per_day"] / total if total else 0.0
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

    def test_the_constant_is_still_present_and_documented(self) -> None:
        """
        Retained, not deleted: the scheme has no `retired` tag, and the tag
        block is where the reason lives. Deleting it would remove the only
        record of what was assumed for how long.
        """
        assert ELDERLY_EOH_EPSILON_FACTOR == 0.05

    def test_the_stated_gaps_are_still_stated(self) -> None:
        doc = __doc__ or ""
        assert "STATED GAPS" in doc
        assert "83/12 BY VOLUME" in doc
        assert "NOTHING IS KEYED ON FRAILTY YET" in doc
