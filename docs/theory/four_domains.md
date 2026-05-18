# Four Entropy Domains

All entropy obligations fall into four categories. These domains are invariant — what changes across the ε arc is not the domains themselves, but who or what fulfills the obligations they generate.

![Four EOH Domains](../images/eoh_four_domains.svg)

---

## Personal EOH

The entropy of human bodies. Biological needs: food, water, shelter, warmth, healthcare, sanitation. This is the base layer — every person generates personal EOH simply by being alive.

A newborn is the highest-EOH-density event in the system: maximum personal entropy obligation, zero entropy-reduction capacity, requiring years of intensive labor investment before contributing to the collective effort.

**Arc behavior:**

- At ε = 0: This domain consumes nearly all labor; nearly all of it is private and off-ledger.
- At ε = 1: Personal EOH is fully on the collective ledger and entirely fulfilled by automated systems.

**Code:** `hours_eoh/core/eoh_generation.py` → `personal_eoh()`

---

## Infrastructure EOH

The entropy of built systems. Buildings, roads, bridges, power grids, water systems, communication networks.

Infrastructure exists to reduce personal EOH collectively — piped water eliminates per-person water-fetching labor. Each piece of infrastructure trades its own EOH (maintenance burden) for a larger reduction in aggregate personal EOH. The economic logic of infrastructure investment: build what generates less EOH than it eliminates.

**Arc behavior:** Infrastructure EOH grows as the capital stock expands. In the stewardship economy, maintaining the existing capital stock becomes the dominant function of the economy.

**Code:** `hours_eoh/core/eoh_generation.py` → `infrastructure_eoh()`

---

## Ecological EOH

The entropy of natural systems civilization depends on. Soil fertility, water cycles, pollination, climate stability, fisheries, forests.

These have historically been treated as free — no EOH accounting at all — which is precisely why they are collapsing. Ecological EOH makes the obligation visible: nature generates entropy that someone must address, and ignoring it does not eliminate the obligation but defers it with compounding consequences.

**Arc behavior:** Ecological EOH exists independently of automation level. Neglecting it accumulates as deferred obligation with nonlinear threshold failures.

!!! note "GUF connection"
    When ecological degradation occurs at the parcel level, the Ground Use Fee framework handles the fiscal response via either a restoration pathway (V_s baselines reset to recovery target) or an abandonment pathway (rebuilding surcharge added). See [Ground Use Fee Framework](guf_framework.md) and NLSA §9.

**Code:** `hours_eoh/core/eoh_generation.py` → `ecological_eoh()`

---

## Knowledge EOH

The entropy of information systems. Skills atrophy. Institutional memory fades. Training becomes outdated. Software rots. Standards drift.

At high automation, almost all remaining human contribution is knowledge maintenance, transmission, and judgment. This domain is the least obvious but becomes dominant as the other three are increasingly handled by machines. It is also the hardest to verify — unlike a repaired bridge or enriched soil, knowledge maintenance lacks straightforward physical indicators.

!!! note "Verification challenge"
    Admitting knowledge EOH to the collective ledger requires careful implementation to ensure verification standards are rigorous without being so burdensome that they discourage the labor the system most needs at high automation.

**Arc behavior:** This domain's share of total EOH grows monotonically with ε. At ε = 0.99 it is effectively the only remaining source of human EOH obligation.

**Code:** `hours_eoh/core/eoh_generation.py` → `knowledge_eoh()`

---

## Domain Interactions

The four domains are not independent:

- Infrastructure investment reduces personal EOH (the reason to build)
- Ecological degradation increases personal EOH (the cost of ignoring it)
- Knowledge EOH underpins the ability to maintain infrastructure and steward ecosystems
- Personal EOH reduction is the ultimate justification for all investment in the other three

Total EOH across all domains is computed by `total_eoh()` in `hours_eoh/core/eoh_generation.py`.

---

*See also: [EOH Accounting](eoh_accounting.md) — how EOH obligations become TEH through the fulfillment pipeline.*
