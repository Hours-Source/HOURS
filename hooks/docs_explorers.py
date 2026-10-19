"""MkDocs hook: build the in-browser explorers and publish them with the docs.

Each explorer under `utils/explorers/<name>/` is a template plus a builder that
embeds the shipped data and the `data.py` constants into one self-contained HTML
page. We do NOT commit the built page. A 200 KB copy of the registry in `docs/`
would be a second source that goes stale silently. For the same reason,
`hooks/docs_data_files.py` registers the audit CSVs in place and does not copy
them.

So this hook makes the page on every `mkdocs build`, and registers it as a
documentation file at `tools/<name>/index.html`. A builder that refuses raises an
error, and the strict docs build in CI fails. It does not publish a page that no
longer matches the code. The multiplier builder refuses when the repo's own
functions no longer reproduce the registry, when `data.py` and the bounds file
disagree, or when the page names a provenance key the CSV lacks. The family
hours builder refuses a value with no stated source.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Callable

from mkdocs.structure.files import File, Files

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from utils.explorers.family_hours import build as family_hours  # noqa: E402
from utils.explorers.multiplier.build import build_html as build_multiplier  # noqa: E402

log = logging.getLogger("mkdocs.hooks.docs_explorers")

# Published path → builder. Add one line per explorer.
EXPLORERS: dict[str, Callable[[], str]] = {
    "tools/multiplier/index.html": build_multiplier,
    "tools/family-hours/index.html": family_hours.build_html,
}


def on_files(files: Files, config: Any) -> Files:
    """Build every explorer and register it as a documentation file."""
    for path, build in EXPLORERS.items():
        files.append(File.generated(config, path, content=build()))
    # A market figure past its source's next release is shown with its date, so
    # it is reported at INFO: a WARNING would fail the strict build.
    for s in family_hours.stale(json.loads(family_hours.DATA.read_text(encoding="utf-8"))):
        log.info("family hours explorer: past its next update: %s", s)
    return files
