# Design Principles

Nine principles that every function, parameter, and mechanism in the HOURS framework must honor.

![Basket Price Falls with Automation](../images/basket_price_arc.svg)

![Floor Purchasing Power Rises with Automation](../images/purchasing_power_arc.svg)

---

## 1. One hour of human entropy resistance is the invariant unit

The base unit does not change. What changes is what that hour is *for*. In the care economy, an hour sustains people. In the production economy, an hour builds systems that reduce aggregate EOH. In the stewardship economy, an hour maintains systems against entropy.

The ledger, the multiplier, and the three foundational structural conditions hold across all three layers without structural change. Any proposed extension that requires abandoning the time-base is solving the wrong problem.

---

## 2. The system must never depend on production for survival

The fiscal architecture — specifically the Trust, the Stewardship Allocation, and the Sufficiency Guarantee — must remain solvent under any automation level, including full automation of all physical production.

Revenue streams pegged to economic output (levies on all labor, L) are supplementary. Revenue streams pegged to the capital stock's entropy obligations (the Stewardship Allocation) are foundational — not because capital earns a return, but because the size of the capital stock determines how much stewardship labor is needed.

When modeling any new mechanism, ask: *does this still work when output(ε) approaches the stewardship-only floor?*

---

## 3. Distributed labor competency is a resilience requirement

Automation is not irreversible. Systems fail. Supply chains break. Energy grids collapse. If automation handles 99% of EOH fulfillment and then fails, the full entropy burden returns to human labor instantaneously.

The resilience case calls for:

- A minimum population with current training in essential production skills (agriculture, construction, energy, water, healthcare, manufacturing, logistics)
- A rotation or revalidation mechanism that keeps those skills active rather than theoretical
- Structural incentives for hands-on competency even when automation makes it economically unnecessary

The variable-h framework already supports this: the minimum hours obligation (h_min) can be directed toward competency-maintenance labor. See [Condition IV](structural_conditions.md#condition-iv-distributed-competency-strongly-recommended).

---

## 4. The multiplier measures entropy-reduction leverage

In the care economy: how much does this person's labor contribute to building the entropy-reduction capacity of others?

In the production economy: how many hours of aggregate EOH does one hour of this person's labor eliminate?

In the stewardship economy: how efficiently does this person maintain systems against entropy?

The four-factor assessment (training, demand, scarcity, impact) measures four dimensions of this leverage across all three layers without structural change — only the relative weighting of factors shifts as the economy evolves.

---

## 5. The floor rises with automation; it never falls

As automation reduces the human labor content of the Sufficiency basket, the Guarantee's purchasing power increases automatically. This is not a policy decision — it is a mathematical consequence of the system's structure. TEH-denominated prices fall as automation handles more EOH, so the same nominal TEH buys more.

The nominal TEH amount may remain constant while the real standard of living it provides grows.

!!! danger "Non-negotiable"
    Any proposed modification that would allow the floor to decline in real terms — through basket redefinition, regional manipulation, or conditional erosion — violates the system's core commitment. Model it, flag it, reject it.

---

## 6. Care is capital formation

Raising children, educating, training, healing, and mentoring are not peripheral activities that the economy supports. They are the economy's primary capital investment — the process by which the system builds the entropy-reduction workforce it depends on.

A child requires years of high-EOH investment before contributing any entropy-reduction capacity. The return on that investment is measured in decades of contribution across all four entropy domains.

Any framework modification that undervalues care labor or treats it as economically secondary misunderstands the system's capital structure.

---

## 7. Every mechanism must have a graceful degradation path

No mechanism should require a discrete "switch" from one economic zone to another. The displacement model should smoothly transition from "retrain into other production sectors" to "retrain into stewardship and care." The variable-h behavioral model should smoothly accommodate satiated consumption.

If a function produces discontinuities, infinities, or undefined behavior as automation approaches 1.0, it is incomplete. Different automation stages require different focal priorities — but the transition between them must be smooth.

---

## 8. The code is the constitution's test bench

The papers describe a system. The code tests whether that system is self-consistent, fiscally solvent, and robust to shocks. Every claim in the papers should be verifiable by running a function. Every parameter should be sweepable to find its failure boundary.

The dashboard is not a summary — it is a structural integrity check. If the dashboard shows green, the system works. If it shows red, the papers have a problem, not the code.

**Code:** `hours_eoh/core/dashboard.py` → `system_dashboard()`

---

## 9. Every mechanism must express the arc, not just a point on it

The current calibration reference (ε = 0.40) is a validation anchor, not a design target. The test is whether a mechanism produces *meaningful, physically grounded results at both extremes*:

- **At ε = 0:** Near-zero collective economy. TEH barely circulates. Most EOH is private. Registration shares are near their floor values. The ledger must be well-defined and solvent here.
- **At ε = 0.99:** Near-zero-price economy. Human labor is negligible. Basket prices have collapsed. TEH creation and destruction both approach zero. The floor must still rise. The account identity must still hold.

A mechanism that gives the right answer at ε = 0.40 but breaks at the extremes is a calibration artifact. A mechanism that gives the right answer at both extremes and everywhere in between is an expression of the transition.

**The framework's validity is measured by coherence across the full arc, not by accuracy at any single point.**

---

*For the function-level checklist derived from these principles, see [Extending the Library](../guides/extending.md).*
