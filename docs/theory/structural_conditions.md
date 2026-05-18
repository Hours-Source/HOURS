# Structural Conditions

A TEH-denominated economy achieves stable, inflation-proof operation if and only if the first three conditions are maintained simultaneously. The fourth condition is not required for monetary stability but is strongly recommended for civilizational resilience.

---

## Condition I — Ledger Identity

!!! success ""

    Every unit of currency (TEH) in circulation must correspond to a verified record of entropy-reduction labor performed. Currency is created only through registered work — the fulfillment of entropy obligations across any of the four domains — and destroyed through terminal consumption or capital write-down. The total supply must always equal cumulative creation minus cumulative destruction, with no exceptions.

    **Circulatory vs. destructive flows:** Spending that transfers TEH between parties is circulatory, not destructive. Levies and fiscal mechanisms that collect TEH are circulatory — they redirect TEH into capital investment, stewardship allocation, and social programs, but do not destroy it. Only terminal consumption and capital write-down remove TEH from existence.

    **Arc requirement:** The ledger identity must hold at ε = 0 (where barely any TEH is created or destroyed) and at ε = 0.99 (where both creation and destruction approach zero from price collapse). A verification mechanism that works only in the middle of the arc is incomplete.

    **Code:** `hours_eoh/core/conditions.py` → `condition_i_check()`

---

## Condition II — Multiplier Band

!!! success ""

    An independent governing body assigns skill-tier multipliers to recognized occupations based on entropy-reduction leverage — how many hours of entropy obligation does one hour of this person's labor address?

    The four-factor assessment (training requirements, demand intensity, practitioner scarcity, and measurable societal impact) measures four aspects of this leverage. A Tier 1 worker fulfilling personal EOH reduces entropy at a near 1:1 ratio. A high-tier engineer designing water infrastructure works one hour but reduces thousands of personal EOH hours across a population.

    **Band:** The population-weighted average multiplier should be maintained within 1.8–2.1 (target 2.1). Individual multipliers may extend higher for rare specializations, with a recommended maximum of 6.0. The band must balance entropy-reduction incentives against excessive income disparity.

    **Grounding:** Basing the multiplier on measurable entropy-reduction leverage rather than social convention makes it harder to corrupt politically while maintaining its role as an incentive for human capital development.

    **Code:** `hours_eoh/core/multipliers.py` → `population_weighted_mean_multiplier()`, `multiplier_band_check()`

---

## Condition III — Zero Interest

!!! success ""

    Stored currency may not generate additional currency through any mechanism. No lending at interest, investment returns, or financial instruments that produce currency without corresponding labor. Account balances change only through earnings and expenditures.

    **Physical grounding:** Entropy compounds in physical reality — a neglected roof generates escalating obligations. The monetary system measures that reality honestly. Adding monetary interest would be measuring entropy that does not exist. Condition III ensures the currency reflects only real entropy resistance, never fictional growth.

    **Note:** EOH compounding is physics (entropy accumulation), not interest — it does not create TEH. TEH is created only when someone actually does the work.

    **Code:** `hours_eoh/core/conditions.py` → `condition_iii_balance_growth_check()`

---

## Condition IV — Distributed Competency *(strongly recommended)*

!!! tip ""

    Conditions I–III define the foundational monetary architecture. Condition IV is not structurally required for the currency to function, but is strongly recommended for any implementation intended to operate over the long term.

    **The failure mode:** If automation handles 99% of EOH fulfillment and then fails, the full entropy burden returns to human labor instantaneously. If no human workforce can step in, the Sufficiency Guarantee becomes a nominal promise the real economy cannot honor.

    **The requirement:** A minimum share of the workforce must maintain certified competency across essential infrastructure domains (agriculture, construction, energy, water, healthcare, manufacturing, logistics). A threshold of approximately 15.5% of the workforce is recommended, with domain-specific allocations scaled to societal need.

    **The mechanism:** The variable-h framework supports this directly — the minimum hours obligation (h_min) can be directed toward competency-maintenance labor. The multiplier system can recognize and incentivize maintenance of essential skills.

    *Any modification to the framework should consider its impact on distributed competency even when this condition is not formally adopted.*

    **Code:** `hours_eoh/core/conditions.py` → `condition_iv_check()`; `hours_eoh/core/workforce.py` → `competency_reserve()`

---

## Conditions and the Arc

All four conditions must hold at ε = 0, ε = 0.40, ε = 0.90, and ε = 0.99. The conditions are not relaxed at the extremes — they are where the extremes test whether the architecture is complete.

**Code:** `hours_eoh/core/dashboard.py` → `system_dashboard()` — checks all conditions at a given ε.
