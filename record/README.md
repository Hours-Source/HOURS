# `record/` — the project record

What was **decided**, what was **learned**, and the **evidence** behind both,
filed by subject area rather than by date.

`CLAUDE.md` is loaded in full at the start of every session. This directory is
not — it is opened on demand, the way `notes/README.md` indexes the local design
material. The split is by *retrieval question*:

| Question | Where it is answered |
|---|---|
| What must I not break, anywhere? | `CLAUDE.md` — guardrails, layer rules, recurring failure modes |
| What is true right now? | `CLAUDE.md` § Current status — the state, kept short |
| What is settled in the area I am touching? | `record/<area>.md` § Live state |
| What is still open there, and what would close it? | `record/<area>.md` § Open |
| Why is it that way — what was tried, what failed? | `record/<area>.md` § History |

**Read the area file before working in that area.** The history is where the
retracted claims, the near-misses and the instruments that were rejected live,
and every one of them was found the expensive way.

## Why the failure modes are NOT filed here

The recurring failure modes stay in `CLAUDE.md`, loaded every session, because
they do not belong to an area. The frame seam was found in six different
subsystems; the stranded parameter in four; a status note outliving its decision
in nine places spanning every area. Filing a lesson under the area where it was
*last* found means the session most likely to repeat it — the one about to make
the same mistake somewhere new — is exactly the session that does not load it.

Routing optimises for *what I am working on*. Lessons are needed for *what I am
about to break somewhere I am not looking*. Different retrieval problems, so
different homes.

## The areas

| File | Scope | Migrated |
|---|---|---|
| [ecological.md](ecological.md) | The ecological domain, the pristine/current partition (Phases 3–4f), the area/frame keying, restoration cost, domain balance | **yes** |
| [guf.md](guf.md) | The Ground Use Fee: Ψ, the term basis, the ten `GUF_USE_*` ratios, per-parcel and servicing measurement, parcels, the conservation credit | **yes** |
| [personal.md](personal.md) | The personal domain: the basket, the floors, standards and abatement (Blocks I–III, P-I), ATUS/MTUS, care, nutrition, capacity, the work-year | **yes** |
| [provenance.md](provenance.md) | The tag scheme, the provenance gate, shadow constants, the confidence ratchet, placeholder audits, constant revaluations | **yes** |
| [verification.md](verification.md) | The gates themselves, the test-suite audits, mutation testing, pin coverage, the claims register | **yes** |
| [fulfilment.md](fulfilment.md) | The EOH→TEH pipeline: the automation response, capability vs observable ε, the mint path, the stock identity, the obligation accounts, arc stability | **yes** |
| [contestability.md](contestability.md) | Contestability and the Coasean layer: §§8.7–8.9c, recalibration, formation, exchange, the federation | **yes** |
| [thermal.md](thermal.md) | The planetary radiative layer: the P0 bound, Path C, λ, drawdown, solvency, capital dual-output | **yes** |
| [theory.md](theory.md) | Positions awaiting the author: the value anchor, the anchor comparison, the discovery layer, published sign-offs | **yes** |

All nine are migrated. `CLAUDE.md` § Current status now holds state and an open-item
index only — no history.

### Adding a new area

1. Create `record/<area>.md` with the four sections below.
2. Add a row to the table above **and** to the routing table in `CLAUDE.md`
   § Current status → Where the record lives. `tests/test_record_index.py` fails
   if either is missing.
3. Until it has content, use the stub template — a file carrying
   `## MIGRATION STATUS — not yet migrated` must be marked `no` in both tables,
   and a file without it must be marked `yes`. The gate holds those two accounts
   equal in both directions.

### Adding an entry to an existing area

Append to that file's `## History`, **newest first**, prefixed with
`<a id="a-short-slug"></a>` and a blank line. Then update `## Live state` if the
entry changed what is true, and `## Open` if it opened or closed an item. Do not
put the entry in `CLAUDE.md` — that section is state and open items only, and an
entry there is the append-only growth this split undid.

## Conventions inside an area file

1. **Live state first.** What is true now, in as few lines as it takes. Where a
   line is enforced by `tests/test_claims_register.py`, it is marked *(gated)* —
   that line cannot go stale silently.
2. **Open items next**, each with what would settle it. An item that is open,
   unlisted and quietly false is the state this whole structure forbids.
3. **History last**, newest first, **verbatim**. Entries are not rewritten when
   they are superseded — a superseded entry is collapsed to its headline with a
   pointer to what replaced it, and the body stays. Deleting the evidence would
   remove the only reason anyone believes the lesson.
4. **`gated by:`** wherever a lesson has been converted into a test. That line
   doubles as a map of which patterns are still unguarded.
5. **Stable anchors.** Every history entry carries an `<a id="slug"></a>`, so any
   file can point at a specific entry rather than at a whole file:
   `record/guf.md#term-basis-audit-psi-retired`. The anchor sits *above* the
   entry and does not alter its text, which is what keeps "verbatim" true.
6. **Cross-area entries are filed once, on primary subject, and linked.** A
   `## Cross-area entries` table names each one and says what it also bears on.
   Duplicating an entry into two files would create two accounts of one thing,
   which is the failure mode this repo already has a name for.

## The one hard constraint

`tests/test_claims_register.py` checks CLAUDE.md's assertions against the code by
locating each claim as an exact substring. Its `_text()` helper reads
**`CLAUDE.md` plus every `record/*.md`**, so a claim does not stop being checked
because it moved here. Moving text out of `CLAUDE.md` without that is how the
register goes quietly blind.

`tests/test_record_index.py` additionally requires every file in this directory
to be linked from this README — an index that has fallen behind is the
`unused_innocuous_names` failure, which this repo learned when two allowlist
entries went stale within an hour of shipping.
