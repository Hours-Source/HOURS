# Regenerative Labor

## Regenerative Offset

Some labor reduces future EOH rather than fulfilling current EOH. Composting enriches soil, reducing future agricultural labor needs. Preventive maintenance extends asset life, lowering future obligation generation rates.

The system distinguishes between two types of labor:

| Type | Effect | Examples |
|------|--------|---------|
| **Maintenance labor** | Fulfills existing EOH | Repairing a roof, treating illness, monitoring systems |
| **Regenerative labor** | Reduces future EOH generation rates | Soil enrichment, preventive maintenance, skill training |

This distinction carries significant implications for long-term stewardship planning and capital investment decisions. A civilization that systematically under-invests in regenerative labor accumulates deferred EOH — degraded soil, aging infrastructure, atrophied skills — that must eventually be addressed at higher cost.

**Code:** `hours_eoh/core/eoh_dynamics.py` → `regenerative_offset()`, `regenerative_investment_required()`

---

## Three Physical Guardrails

### Guardrail I — Physical Grounding

EOH generation rates must be derived from measurable physical indicators — sensor data, engineering standards, material science, ecological monitoring, public health data — not from political discretion or fiscal convenience.

When the assessment says a bridge generates 200 EOH per year, that figure must trace to inspectable conditions, not to a budgetary target.

!!! warning "Critical integrity requirement"
    If EOH rates become politically negotiable, the system loses its claim to measuring reality and begins manufacturing obligation. This occupies the same structural territory as artificial demand creation — without the name "interest."

Rates should be auditable against observable reality. Assessment must be verified by independent technical review.

---

### Guardrail II — Capital Write-Down

When capital degrades beyond the point where maintenance labor can restore function, the associated EOH must be formally written off. Irrecoverable capital cannot carry an indefinite maintenance obligation.

The write-down recognizes a permanent loss of physical capacity — not a monetary event, but an acknowledgment that the asset no longer exists in maintainable form. The written-off EOH is replaced either by:

- A new, larger EOH reflecting the labor needed to rebuild from scratch, or
- Zero if the capital is abandoned entirely

This prevents EOH from accumulating beyond what is physically meaningful and ensures the ledger reflects the actual state of the capital stock.

**Human capital write-down:** Death is a write-down. The person's personal EOH vanishes, but their entropy-reduction capacity also vanishes — every EOH they were fulfilling must be redistributed to other workers or to automation. The system must account for this redistribution without treating the event as merely an accounting adjustment.

**Code:** `hours_eoh/core/capital.py` → `writedown_trigger()`, `execute_writedown()`; `hours_eoh/core/eoh_fulfillment.py` → `capital_writedown()`

---

### Guardrail III — Governance Independence

The body that assesses EOH generation rates must be constitutionally independent, with structural protections equivalent to those given the multiplier body under [Condition II](structural_conditions.md#condition-ii-multiplier-band).

!!! danger "Structural risk"
    Whoever controls EOH assessment controls the economy's labor demand signal and therefore controls a significant channel of TEH creation. This power must not be subject to short-term political pressure.

Assessment methodology, rate-setting procedures, and audit standards should be publicly transparent and subject to independent technical review.

---

*See also: [Structural Conditions](structural_conditions.md) — the four conditions these guardrails support.*
