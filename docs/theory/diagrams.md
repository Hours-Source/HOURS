# Diagrams

Fifteen diagrams rendered from Mermaid source. Source `.mmd` files are in `diagrams/` (gitignored); rendered SVGs are committed to `docs/images/`.

To re-render a single diagram:
```bash
mmdc -i diagrams/<name>.mmd -o docs/images/<name>.svg -p ~/.config/mermaid/puppeteer.json
```

To re-render all:
```bash
for f in diagrams/*.mmd; do mmdc -i "$f" -o "docs/images/$(basename $f .mmd).svg" -p ~/.config/mermaid/puppeteer.json --quiet; done
```

---

## 1. EOH → TEH Pipeline

Physical reality generates entropy obligations. Machines and humans split the fulfillment. Registration gates how much human labor enters the collective ledger. TEH is created only from what is registered.

![EOH → TEH Pipeline](../images/eoh_teh_pipeline.svg)

---

## 2. The Four EOH Domains

What each domain measures, what drives its magnitude, and its behavior at the extremes.

![Four EOH Domains](../images/eoh_four_domains.svg)

---

## 3. Price Mechanism — EOH vs. Classical Supply & Demand

![Price Mechanism Comparison](../images/price_mechanism.svg)

---

## 4. Basket Price Falls with Automation

`basket_price(ε)` — TEH cost of the sufficiency basket. Goods (60%) decline steeply; services (40%) decline more slowly (care/knowledge resist automation). Both fall, so the floor's purchasing power rises automatically.

![Basket Price Arc](../images/basket_price_arc.svg)

---

## 5. Floor Purchasing Power Rises with Automation (Principle 5)

Same nominal floor in TEH. Basket price falls. Baskets afforded rises — automatically, with no policy intervention required. Index: 100 = purchasing power at ε=0.

![Purchasing Power Arc](../images/purchasing_power_arc.svg)

---

## 6. Good Price Falls with Automation

`teh_price(0.1h_base_labor, ε)` — price of a good requiring 0.1 hours of human labor at ε=0. Human labor content = `(1 − ε) × base_hours`. Floor at 5% prevents price reaching zero.

![Good Price Arc](../images/good_price_arc.svg)

---

## 7. Demand Layer Stack

Three distinct demand zones in the EOH framework. Classical S/D conflates all three.

![Demand Layer Stack](../images/demand_layer_stack.svg)

---

## 8. Scarcity Signal — domain_scarcity_multiplier()

The only S/D-like mechanism. Activates only when EOH demand exceeds fulfillment capacity. Corrective, not foundational. Resets once labor is redirected.

![Scarcity Signal](../images/scarcity_signal.svg)

---

## 9. TEH Lifecycle — Creation and Destruction

TEH is created when registered human labor enters the ledger. Six destruction mechanisms close the circuit. Levies and Trust spending are circulatory (TEH moves, not destroyed).

![TEH Lifecycle](../images/teh_lifecycle.svg)

---

## 10. Automation Arc — What Changes with ε

![Automation Arc](../images/automation_arc.svg)

---

## 11. GUF Master Equation — Component Assembly

How the 8 components of the master equation combine into GUF(p), followed by the review-cycle cap and income-linked subsidy adjustments.

![GUF master equation assembly](../images/guf_master_equation.svg)

---

## 12. GUF Location Value Index — L(p) Weights

The four sub-indices and their default weights (35 / 30 / 20 / 15) flowing into L(p).

![L(p) sub-index composition and weights](../images/guf_lvi_weights.svg)

---

## 13. GUF Epsilon Arc — Ψ(ε)

Bell-curve shape of the global GUF multiplier: near-floor at ε=0 and ε=0.99, peak ≈1.06 at ε=0.40.

![Ψ(ε) GUF epsilon scaling arc](../images/guf_epsilon_arc.svg)

---

## 14. GUF Trust Flow — Revenue to Allocation

How parcel GUF payments aggregate into `guf_trust_inflow()`, feed into `trust_management()` alongside levy revenue, and distribute to ecological, stewardship, sufficiency, and capital channels.

![GUF revenue flow to Trust allocations](../images/guf_trust_flow.svg)

---

## 15. GUF Ecological Write-Down Pathways

EOH accumulation warning (30% threshold) → write-down declaration → restoration pathway vs. abandonment pathway with 50-year rebuilding surcharge.

![Ecological write-down warning and pathways](../images/guf_writedown_pathways.svg)
