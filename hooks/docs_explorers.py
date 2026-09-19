"""MkDocs hook: build the in-browser explorers and publish them with the docs.

Each explorer under `utils/explorers/<name>/` is a template plus a builder that
embeds the shipped data and the `data.py` constants into one self-contained HTML
page. The built page is NOT committed: a 200 KB copy of the registry in `docs/`
would be a second source that goes stale silently, the same reason
`hooks/docs_data_files.py` registers the audit CSVs in place instead of copying
them.

So the page is generated here, on every `mkdocs build`, and registered as a
documentation file at `tools/<name>/index.html`. A builder that refuses — the
repo's own functions no longer reproduce the registry, `data.py` and the bounds
file disagree, the page names a provenance key the CSV lacks — raises, and the
strict docs build in CI fails instead of publishing a page that no longer
matches the code.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable

from mkdocs.structure.files import File, Files

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from utils.explorers.multiplier.build import build_html as build_multiplier  # noqa: E402

# Published path → builder. Add one line per explorer.
EXPLORERS: dict[str, Callable[[], str]] = {
    "tools/multiplier/index.html": build_multiplier,
}


def on_files(files: Files, config: Any) -> Files:
    """Build every explorer and register it as a documentation file."""
    for path, build in EXPLORERS.items():
        files.append(File.generated(config, path, content=build()))
    return files
