#!/usr/bin/env python3
"""Build the self-contained family hours explorer page.

The page turns a family's living costs into hours of paid work a week at the
household's own wage. It then compares them with the hours its earners have.
It is the MARKET reading: a dollar cost divided by pay per hour. These hours are
not the framework's obligation hours (EOH) or TEH. This repository does not
model the market layer yet.

Where each thing comes from (nothing on the page is a copy):
    every cost, rate, standard and tax rule   hours_eoh/reference/data/family_costs.json
    the yearly-pay-to-hourly divisor          hours_eoh.data.H_REF (40 h x 52 wk)
    the sources list and wage presets         generated from the same file

The build REFUSES to write a page when:
    - a value has no source, no read date, or no update cadence;
    - a link does not use https, or a value that must be a number is not one;
    - the template does not hold the data placeholder exactly once.

It REPORTS a value past its next update (`stale()`), and does not refuse it.
The page then shows an older figure with its date, which is honest.

What it CANNOT check (the checker-gaps rule): that a figure is right. Every value
came from the explorer handoff. The file says where nobody re-checked a source. `tests/test_explorer_build.py` runs the page's math under node.

Usage:
    python3 utils/explorers/family_hours/build.py [--out FILE]

hooks/docs_explorers.py normally runs it during `mkdocs build`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hours_eoh import data as D  # noqa: E402

DATA = REPO_ROOT / "hours_eoh" / "reference" / "data" / "family_costs.json"
TEMPLATE = Path(__file__).resolve().parent / "template.html"
PLACEHOLDER = "/*DATA*/"

# Days until a source with this cadence publishes again. A cadence not listed
# here (chosen, rarely, by statute) never goes stale.
CADENCE_DAYS = {"weekly": 7, "monthly": 31}
YEARLY_DAYS = 365

SOURCED_SECTIONS = ("defaults", "derived", "standards")
RULE_SECTIONS = ("tax", "eitc", "fha", "food_scaling", "household")


class BuildError(Exception):
    """The page would show a value with no stated source, so the build writes nothing."""


def _entries(d: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every entry that must state a source, with a name for error messages."""
    out = [(f"{s}.{k}", e) for s in SOURCED_SECTIONS for k, e in d[s].items()]
    out += [(f"wages.{k}", e) for k, e in d["wages"].items() if isinstance(e, dict)]
    out += [(s, d[s]) for s in RULE_SECTIONS]
    return out


def check_sources(d: dict[str, Any]) -> None:
    """Each value must state its source, the date someone read it, and how often it moves."""
    for name, e in _entries(d):
        for key in ("source", "read", "updates"):
            if not isinstance(e.get(key), str) or not e[key].strip():
                raise BuildError(f"{name} has no {key}")
        try:
            dt.date.fromisoformat(e["read"])
        except ValueError:
            raise BuildError(f"{name}: read date {e['read']!r} is not YYYY-MM-DD") from None
        url = e.get("url")
        if url is not None and not (isinstance(url, str) and url.startswith("https://")):
            raise BuildError(f"{name}: link {url!r} is not https")
    for s in ("defaults", "standards"):
        for k, e in d[s].items():
            if not isinstance(e.get("value"), (int, float)):
                raise BuildError(f"{s}.{k} has no numeric value")


def _due_days(updates: str) -> int | None:
    word = updates.split(",")[0].strip()
    if word in CADENCE_DAYS:
        return CADENCE_DAYS[word]
    return YEARLY_DAYS if word == "yearly" else None


def stale(d: dict[str, Any], today: dt.date | None = None) -> list[str]:
    """The entries whose source has published again since the read date."""
    today = today or dt.date.today()
    out = []
    for name, e in _entries(d):
        days = _due_days(e["updates"])
        if days is not None and (today - dt.date.fromisoformat(e["read"])).days > days:
            out.append(f"{name} ({e['updates']}, read {e['read']})")
    return out


def load_payload(path: Path = DATA) -> dict[str, Any]:
    """The page's data: the file's values, the derived ones computed, H_REF bound."""
    d = json.loads(path.read_text(encoding="utf-8"))
    check_sources(d)
    hours_per_year = D.H_REF
    defaults = {k: e["value"] for k, e in d["defaults"].items()}
    hl = d["derived"]["hl"]
    defaults["hl"] = round(hl["premium"] * hl["worker_share"])
    rs = d["derived"]["rs"]
    defaults["rs"] = rs["per_week"] * rs["weeks"]
    defaults.update({k: e["value"] for k, e in d["standards"].items()})
    defaults.update(d["household"]["settings"])
    presets = []
    for k, e in d["wages"].items():
        if not isinstance(e, dict):
            continue
        w = e["per_hour"] if "per_hour" in e else round(e["per_year"] / hours_per_year, 2)
        presets.append({"key": k, "label": e["label"], "per_hour": w})
    default_key = d["wages"]["default"]
    defaults["w"] = next(p["per_hour"] for p in presets if p["key"] == default_key)
    return {
        "defaults": defaults,
        "presets": presets,
        "hours_per_year": hours_per_year,
        "weeks_per_year": d["weeks_per_year"],
        "tax": d["tax"], "eitc": d["eitc"], "fha": d["fha"],
        "food_scaling": d["food_scaling"],
        "sources": [{"name": name, **{k: e.get(k) for k in
                     ("label", "source", "url", "read", "period", "updates", "note")}}
                    for name, e in _entries(d)],
    }


def build_html(template: Path = TEMPLATE, data: Path = DATA) -> str:
    """Return the finished page, or raise BuildError."""
    html = template.read_text(encoding="utf-8")
    if html.count(PLACEHOLDER) != 1:
        raise BuildError(f"template must contain {PLACEHOLDER} exactly once")
    blob = json.dumps(load_payload(data), separators=(",", ":"),
                      ensure_ascii=False).replace("</", "<\\/")
    return html.replace(PLACEHOLDER, blob)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="family_hours_explorer.html", type=Path)
    a = ap.parse_args()
    try:
        html = build_html()
    except BuildError as e:
        raise SystemExit(f"family hours explorer not built: {e}")
    a.out.write_text(html, encoding="utf-8")
    print(f"Wrote {a.out} ({a.out.stat().st_size / 1024:.0f} KB)")
    for s in stale(json.loads(DATA.read_text(encoding="utf-8"))):
        print(f"past its next update: {s}")


if __name__ == "__main__":
    main()
