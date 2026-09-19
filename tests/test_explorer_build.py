"""The in-browser explorers (utils/explorers/) against the repo they claim to show.

A published explorer carries a second implementation of the multiplier math, in
JavaScript. Two things keep it honest:

1. The BUILDER refuses to write a page unless the repo's own functions reproduce
   the registry, data.py agrees with the bounds file, and every provenance key and
   tag the page names exists. Tested here by breaking each input and requiring
   the refusal (a gate that has never fired is untested).
2. The page's MATH BLOCK is run under node and compared with
   hours_eoh.core.multipliers and scenarios.multiplier_sensitivity.reconstruct,
   including under perturbed weights. That is what would catch the page drifting
   back to re-anchoring the frozen scale.

Stated gap: part 2 needs node on PATH and SKIPS without it. The rendering code
(labels, wording, layout) is not tested; only the math block and the payload are.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hours_eoh import data as D
from hours_eoh.core.multipliers import (
    composite_from_factors,
    impact_composite_from_subdomains,
    reference_multiplier,
)
from hours_eoh.reference.onet_multipliers import load_registry
import inspect

from hours_eoh.scenarios.multiplier_sensitivity import (
    _normalize, reconstruct, spearman, sweep_factor_weights,
)
from utils.explorers.multiplier import build as B


@pytest.fixture(scope="module")
def html() -> str:
    return B.build_html()


def _payload(html: str) -> dict:
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "embedded data block missing"
    return json.loads(m.group(1).replace("<\\/", "</"))


def _math_block(html: str) -> str:
    m = re.search(r'<script id="math">(.*?)</script>', html, re.S)
    assert m, "math block missing"
    return m.group(1)


# ---------------------------------------------------------------------------
# The payload is bound to data.py, not copied
# ---------------------------------------------------------------------------

def test_payload_constants_are_data_py(html: str) -> None:
    C = _payload(html)["constants"]
    assert tuple(C["factor_weights"][k] for k in B.FACTOR_NAMES) == D.M_FACTOR_WEIGHTS
    assert tuple(C["impact_weights"][k] for k in B.IMPACT_NAMES) == D.M_IMPACT_SUBDOMAIN_WEIGHTS
    assert C["z_range"] == [D.M_COMPOSITE_Z_LO, D.M_COMPOSITE_Z_HI]
    assert C["impact_bounds"] == [D.M_IMPACT_COMPOSITE_LO, D.M_IMPACT_COMPOSITE_HI]
    assert (C["floor"], C["R"], C["cap"]) == (D.M_FLOOR, D.M_GEOMETRIC_R, D.M_MAX)
    assert C["band"] == [D.M_BAND_LOW, D.M_BAND_HIGH]
    assert C["weight_span"] == inspect.signature(sweep_factor_weights).parameters["delta"].default


def test_payload_rows_are_the_registry(html: str) -> None:
    p = _payload(html)
    rows = load_registry()
    assert len(p["rows"]) == len(rows)
    i_occ, i_m = p["columns"].index("occ6"), p["columns"].index("reference_multiplier")
    for pr, r in zip(p["rows"], rows):
        assert f"{pr[i_occ]:06d}" == r["occ6"]
        assert pr[i_m] == r["reference_multiplier"]


def _literal_weight_copies(src: str) -> list[str]:
    """Places the template restates a CHOSEN weight instead of reading it."""
    hits = []
    if re.search(r"dependency\s*:\s*\.?0?\.30", src):
        hits.append("impact weights as a JS literal")
    if re.search(r"30\s*/\s*25\s*/\s*25\s*/\s*20", src):
        hits.append("impact weights in prose")
    if re.search(r"two thirds|one third", src):
        hits.append("scarcity leg weights in prose")
    if re.search(r"[-+±]\s*0\.10\b|\b10 points\b", src):
        hits.append("slider span as a literal")
    return hits


def test_no_literal_weights_in_template() -> None:
    """The draft hard-coded the impact weights in the JS and in the step-1 prose,
    and the scarcity leg split in a tooltip; the page must read them."""
    src = B.TEMPLATE.read_text(encoding="utf-8")
    assert _literal_weight_copies(src) == []
    assert "IW = {...C.impact_weights}" in src


def test_literal_weight_scan_can_fire() -> None:
    """Against the draft's own sentences the scan must find all three copies."""
    draft = ("const IW = {dependency:.30, substitutability:.25};"
             " combined with weights 30 / 25 / 25 / 20 ${tag(...)}"
             " projected openings (two thirds) and projected growth (one third)"
             ' min="${(W[f.k]-0.10).toFixed(2)}"')
    assert len(_literal_weight_copies(draft)) == 4


def test_page_makes_no_external_requests(html: str) -> None:
    """'Nothing to install or download': no remote script, stylesheet, font or image."""
    assert not re.search(r'(?:src|href)\s*=\s*["\']https?://', html)
    assert not re.search(r"url\(\s*['\"]?https?://", html)
    assert not re.search(r"@import", html)


# ---------------------------------------------------------------------------
# The builder refuses — each gate broken and required to fire
# ---------------------------------------------------------------------------

def test_refuses_when_data_py_and_bounds_disagree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(D, "M_GEOMETRIC_R", D.M_GEOMETRIC_R + 0.1)
    with pytest.raises(B.BuildError, match="disagree on R"):
        B.build_html()


def test_refuses_when_repo_functions_do_not_reproduce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(B, "reference_multiplier", lambda c: 1.01 * reference_multiplier(c))
    with pytest.raises(B.BuildError, match="reference_multiplier"):
        B.build_html()


def test_refuses_an_unknown_provenance_key(tmp_path: Path) -> None:
    t = tmp_path / "t.html"
    t.write_text(B.TEMPLATE.read_text(encoding="utf-8").replace(
        'tag("multiplier_cap")', 'tag("no_such_constant")'), encoding="utf-8")
    with pytest.raises(B.BuildError, match="no_such_constant"):
        B.build_html(t)


def test_refuses_an_unmapped_provenance_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(B, "TAG_CLASSES", {k: v for k, v in B.TAG_CLASSES.items() if k != "n/a"})
    with pytest.raises(B.BuildError, match="n/a"):
        B.build_html()


def test_template_prov_keys_are_found() -> None:
    """The key scan must see keys, or the provenance gate passes vacuously."""
    keys = B.template_prov_keys(B.TEMPLATE.read_text(encoding="utf-8"))
    assert {"factor_weights", "impact_subdomain_weights", "band", "multiplier_cap",
            "i_temporal_residualized", "frozen_normalization_bounds",
            "scarcity_leg_weights"} <= keys


# ---------------------------------------------------------------------------
# The page's JavaScript math against the repo — under node
# ---------------------------------------------------------------------------

_NODE_DRIVER = r"""
const fs = require("fs");
const inp = JSON.parse(fs.readFileSync(0, "utf8"));
const multiplierMath = new Function(inp.math + "; return multiplierMath;")();
const M = multiplierMath(inp.constants);
const jobs = inp.rows.map(r => Object.fromEntries(inp.columns.map((c,i)=>[c,r[i]])));
const perRow = jobs.map(j => {
  const fi = M.impactNorm(j);
  const c = M.composite(j, null, fi);
  return [fi, c, M.mult(c)];
});
const base = M.reconstruct(jobs, inp.constants.factor_weights);
const runs = inp.weights.map(w => {
  const r = M.reconstruct(jobs, M.normalize(w));
  return {weighted_mean: r.weighted_mean, spread_ratio: r.spread_ratio,
          clip_fraction: r.clip_fraction, spearman: M.spearman(base.multiplier, r.multiplier)};
});
process.stdout.write(JSON.stringify({perRow, runs}));
"""

# Perturbations the page's sliders can reach (±0.10 on one weight) plus a joint one.
_WEIGHTS = [
    (0.40, 0.25, 0.20, 0.25),
    (0.20, 0.25, 0.20, 0.25),
    (0.30, 0.25, 0.20, 0.35),
    (0.30, 0.35, 0.10, 0.25),
    (0.40, 0.15, 0.30, 0.15),
]


@pytest.fixture(scope="module")
def node_result(html: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH — the page's JS math is UNTESTED in this run")
    p = _payload(html)
    inp = {
        "math": _math_block(html),
        "constants": p["constants"],
        "columns": p["columns"],
        "rows": p["rows"],
        "weights": [dict(zip(B.FACTOR_NAMES, w)) for w in _WEIGHTS],
    }
    out = subprocess.run([node, "-e", _NODE_DRIVER], input=json.dumps(inp),
                         capture_output=True, text=True, check=True, timeout=60)
    return json.loads(out.stdout)


def test_js_math_matches_repo_functions_per_row(node_result: dict) -> None:
    for (fi_js, c_js, m_js), r in zip(node_result["perRow"], load_registry()):
        fi = impact_composite_from_subdomains(
            r["i_dependency"], r["i_substitutability"], r["i_harm"], r["i_temporal"])
        c = composite_from_factors(r["f_training"], r["f_demand"], r["f_scarcity"], fi)
        assert fi_js == pytest.approx(fi, abs=1e-12)
        assert c_js == pytest.approx(c, abs=1e-12)
        assert m_js == pytest.approx(reference_multiplier(c), abs=1e-12)


def test_js_weight_sweep_matches_sensitivity_harness(node_result: dict) -> None:
    """The what-if panel keeps the scale FROZEN. A page that re-anchors z to the
    new min/max reports spread 3.20 at every weight and fails here."""
    rows = load_registry()
    base = reconstruct(rows)
    for w, js in zip(_WEIGHTS, node_result["runs"]):
        run = reconstruct(rows, factor_weights=_normalize(w))
        assert js["weighted_mean"] == pytest.approx(run["weighted_mean"], abs=1e-9), w
        assert js["spread_ratio"] == pytest.approx(run["spread_ratio"], abs=1e-9), w
        assert js["clip_fraction"] == pytest.approx(run["clip_fraction"], abs=1e-12), w
        # Ties (clipped rows) are ordered differently by numpy and JS; 1e-3 absorbs that.
        assert js["spearman"] == pytest.approx(
            spearman(base["multiplier"], run["multiplier"]), abs=1e-3), w


def test_sweep_cases_can_tell_frozen_from_reanchored(node_result: dict) -> None:
    """The comparison above only bites if some case's spread differs from R —
    a re-anchored page would sit at exactly R everywhere."""
    assert any(abs(js["spread_ratio"] - D.M_GEOMETRIC_R) > 0.01 for js in node_result["runs"])


# ---------------------------------------------------------------------------
# The weight sliders — linked shares that always total 100%
# ---------------------------------------------------------------------------

_REBALANCE_DRIVER = r"""
const fs = require("fs");
const inp = JSON.parse(fs.readFileSync(0, "utf8"));
const M = new Function(inp.math + "; return multiplierMath;")()(inp.constants);
const P = inp.constants.factor_weights, FN = M.FN;
const out = {};
// every slider pushed to each end from the published weights
out.ends = [];
for (const k of FN) for (const v of [-1, 2]) out.ends.push({k, w: M.rebalance(P, k, v), range: M.rangeOf(k)});
// away and back: the published weights must come back exactly
out.roundtrip = FN.map(k => { const [lo, hi] = M.rangeOf(k);
  return M.rebalance(M.rebalance(P, k, hi), k, P[k]); });
// a long seeded random walk, including moves past the ends
let seed = 12345; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
let w = {...P}; out.walk = []; out.ratios = [];
for (let i = 0; i < 2000; i++) {
  const k = FN[Math.floor(rnd() * 4)], [lo, hi] = M.rangeOf(k);
  const before = {...w};
  w = M.rebalance(w, k, lo - 0.05 + rnd() * (hi - lo + 0.1));
  out.walk.push(w);
  out.ratios.push({k, before, after: w});
}
out.ranges = Object.fromEntries(FN.map(k => [k, M.rangeOf(k)]));
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def rebalance_result(html: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH — the slider rebalancing is UNTESTED in this run")
    p = _payload(html)
    out = subprocess.run([node, "-e", _REBALANCE_DRIVER],
                         input=json.dumps({"math": _math_block(html), "constants": p["constants"]}),
                         capture_output=True, text=True, check=True, timeout=60)
    return json.loads(out.stdout)


def test_slider_ranges_are_published_plus_minus_the_harness_delta(rebalance_result: dict) -> None:
    delta = inspect.signature(sweep_factor_weights).parameters["delta"].default
    for name, w in zip(B.FACTOR_NAMES, D.M_FACTOR_WEIGHTS):
        lo, hi = rebalance_result["ranges"][name]
        assert lo == pytest.approx(max(0.0, w - delta)) and hi == pytest.approx(min(1.0, w + delta))


def test_every_slider_reaches_both_ends(rebalance_result: dict) -> None:
    """The reported symptom was a slider that seemed to move only one way."""
    for e in rebalance_result["ends"]:
        lo, hi = e["range"]
        assert e["w"][e["k"]] in (pytest.approx(lo), pytest.approx(hi))
    reached = {(e["k"], round(e["w"][e["k"]], 9)) for e in rebalance_result["ends"]}
    assert len(reached) == 2 * len(B.FACTOR_NAMES)


def test_shares_always_total_one_and_stay_in_range(rebalance_result: dict) -> None:
    ranges = rebalance_result["ranges"]
    for w in rebalance_result["walk"] + [e["w"] for e in rebalance_result["ends"]]:
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-12)
        for k, v in w.items():
            assert ranges[k][0] - 1e-12 <= v <= ranges[k][1] + 1e-12


def test_moving_one_keeps_the_others_proportions_unless_one_hits_a_bound(
        rebalance_result: dict) -> None:
    ranges = rebalance_result["ranges"]
    checked = 0
    for step in rebalance_result["ratios"]:
        k, before, after = step["k"], step["before"], step["after"]
        others = [x for x in B.FACTOR_NAMES if x != k]
        at_bound = any(abs(after[x] - ranges[x][0]) < 1e-12 or abs(after[x] - ranges[x][1]) < 1e-12
                       for x in others)
        if at_bound:
            continue
        for a in others:
            for b in others:
                assert after[a] * before[b] == pytest.approx(after[b] * before[a], abs=1e-12)
        checked += 1
    assert checked > 100, "the walk must exercise the unclamped case"


def test_moving_away_and_back_restores_the_published_weights(rebalance_result: dict) -> None:
    for w in rebalance_result["roundtrip"]:
        for name, pub in zip(B.FACTOR_NAMES, D.M_FACTOR_WEIGHTS):
            assert w[name] == pytest.approx(pub, abs=1e-12)
