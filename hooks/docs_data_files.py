"""MkDocs hook: publish the generated audit artifacts alongside the docs.

`docs/parameter_provenance.md` links to machine-readable artifacts that live in
`hours_eoh/reference/data/` and must stay there — that path is the single source
of truth, and `eoh provenance csv --write` regenerates them in place. Copying
them into `docs/` would fork the artifact and let the copy go stale, which is the
exact failure the provenance gate exists to prevent.

So instead of moving the files, we register them with MkDocs as documentation
files at their repo-relative path. Link checking then resolves, and the built
site serves the real artifact.

Without this, `mkdocs build --strict` aborts:

    WARNING - Doc file 'parameter_provenance.md' contains a link
              'hours_eoh/reference/data/constant_provenance.csv', but the
              target is not found among documentation files.
    Aborted with 5 warnings in strict mode!

That is what silently broke the docs deploy from 2026-07-30 (ce86619, which
introduced the links) until 2026-08-10. `deploy.yml` runs `mkdocs gh-deploy` on
every push to main, so a strict-mode abort means the published site simply stops
advancing while main keeps moving — it went 82 commits stale without a signal.
A missing file raises here rather than warning, so the same class of breakage
fails loudly at build time instead of freezing the site again.
"""

from __future__ import annotations

import os
from typing import Any

from mkdocs.structure.files import File, Files

# Repo-relative paths, matching the link targets in docs/parameter_provenance.md.
PUBLISHED_DATA_FILES: tuple[str, ...] = (
    "hours_eoh/reference/data/constant_provenance.csv",
    "hours_eoh/reference/data/multiplier_provenance_v5.csv",
    "hours_eoh/reference/data/thermal_path_c.json",
)


def on_files(files: Files, config: Any) -> Files:
    """Register the generated artifacts as documentation files."""
    repo_root = os.path.dirname(os.path.abspath(config.config_file_path))

    for path in PUBLISHED_DATA_FILES:
        abs_path = os.path.join(repo_root, path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(
                f"docs_data_files hook: {path} is linked from the docs but is "
                f"not present at {abs_path}. Regenerate it "
                f"(eoh provenance csv --write) or update PUBLISHED_DATA_FILES."
            )
        files.append(
            File(
                path,
                src_dir=repo_root,
                dest_dir=config.site_dir,
                use_directory_urls=config.use_directory_urls,
            )
        )

    return files
