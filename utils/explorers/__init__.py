# utils.explorers — self-contained browser pages built from the shipped data.
#
# Each explorer is a template plus a builder. The builder embeds the data and the
# constants the page needs, and refuses to build if the page would not reproduce
# the repo. `hooks/docs_explorers.py` runs every builder during `mkdocs build`,
# so the published pages are regenerated from the source of truth on each deploy
# and never committed as copies.
