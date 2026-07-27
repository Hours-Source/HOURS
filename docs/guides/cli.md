# CLI Reference

The research CLI for HOURS is `utils/eoh_cli.py`. Run from the repo root:

```bash
python3 utils/eoh_cli.py <command> [options]
```

Add `--no-color` to any command to strip ANSI output for piping or logging. Most commands support `--format table|csv|json`.

---

## arc

Sweep ε from 0 to 0.99 — EOH by domain, registration share, TEH created, basket price, fiscal solvency.

```bash
python3 utils/eoh_cli.py arc [--points N] [--format table|csv|json]
```

```bash
python3 utils/eoh_cli.py arc --points 5 --format csv > results/arc.csv
```

---

## dashboard

Color-coded system health snapshot: Structural Conditions I–IV, EOH health, fiscal health.

```bash
python3 utils/eoh_cli.py dashboard [--epsilon ε]
```

---

## params

Inspect and modify the `EohParams` calibration. Changes are persisted to `utils/_params_state.json` and applied to all subsequent commands.

```bash
python3 utils/eoh_cli.py params show                                    # all values
python3 utils/eoh_cli.py params set KEY VALUE [--reason TEXT] [--dry-run]
python3 utils/eoh_cli.py params diff                                    # active overrides
python3 utils/eoh_cli.py params reset                                   # clear all
```

Preview before persisting:

```bash
python3 utils/eoh_cli.py params set suff_levy_rate 0.03 --dry-run
```

Multi-command workflow:

```bash
python3 utils/eoh_cli.py params set capital_stock_teh 4000000000 --reason "high-capital scenario"
python3 utils/eoh_cli.py arc --points 20
python3 utils/eoh_cli.py dashboard --epsilon 0.60
python3 utils/eoh_cli.py params reset
```

---

## scenario

Run or list stress-test scenarios.

```bash
python3 utils/eoh_cli.py scenario list
python3 utils/eoh_cli.py scenario run NAME [--format table|csv|json]
```

| Scenario Name | Description |
|---|---|
| `sweep` | Arc coherence check from ε = 0 to ε = 0.99 |
| `automation_failure` | Sudden machine EOH dropout — tests reserve coverage |
| `demographic_shock` | Population age-structure shift |
| `ecological_spike` | Ecosystem EOH surge |
| `maintenance_crisis` | Compounding deferred infrastructure backlog |
| `care_delay` | Lag in care EOH admission to the collective ledger |
| `recovery` | Maintenance backlog paydown arc |
| `labor-shock` | Compressed labor income — tests fiscal solvency delta |
| `compound-shock` | Combined ecological + demographic + automation shocks |
| `canonical-arc` | Multi-period full ε arc via `run_simulation()` |
| `trust-depletion` | Multi-stressor run — when does the Trust break? |
| `automation-transition` | Fixed ε-step transition: purchasing power and fiscal convergence |
| `indust-baseline` | Industrial-overshoot snapshot vs. canonical |
| `indust-recovery` | Can ecosystem restoration escape the overshoot regime? |
| `guf-integration` | Does GUF revenue close a levy deficit at a given ε? |
| `guf-writedown` | Ecological collapse → warning → write-down pathways |
| `guf-sweep` | Aggregate GUF across the ε arc vs. the Ψ(ε) bell curve |

```bash
python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

See [Running Scenarios](scenarios_howto.md) for Python API usage.

---

## simulate

Multi-period simulation with period-by-period state table.

```bash
python3 utils/eoh_cli.py simulate [--periods N] [--epsilon ε] [--epsilon-delta Δε] \
    [--workforce-decay] [--guf-inflow TEH]
```

```bash
python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02

# With workforce decay and GUF land-fee injection:
python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02 \
    --workforce-decay --guf-inflow 50000.0
```

`--workforce-decay` — when set, `workforce_fraction` shrinks proportionally as ε rises each period (models labor displacement).

`--guf-inflow TEH` — inject a fixed GUF land-fee revenue (TEH) into the Trust each period.

---

## sensitivity

Parameter and arc sensitivity sweeps.

```bash
python3 utils/eoh_cli.py sensitivity fiscal --param KEY --min V1 --max V2 [--points N]
python3 utils/eoh_cli.py sensitivity arc [--format table|csv|json]
python3 utils/eoh_cli.py sensitivity delta --epsilon ε --delta Δε
```

---

## guf — Land Use Fee Commands

Ground Use Fee calculations. See [GUF Framework](../theory/guf_framework.md) for the mathematical specification.

### guf calculate

```bash
python3 utils/eoh_cli.py guf calculate \
    --epsilon 0.40 \
    --area-slu 3.5 \
    --use-category residential_primary \
    --location-value 0.629 \
    [--format table|json]
```

Use categories: `residential_primary`, `residential_secondary`, `agricultural_active`, `agricultural_fallow`, `commercial_retail`, `commercial_office`, `industrial_light`, `industrial_heavy`, `institutional`, `conservation`.

### guf trust

```bash
python3 utils/eoh_cli.py guf trust \
    --revenues 1.5,2.3,0.8 \
    [--subsidies 0.5] \
    [--format table|json]
```

### guf writedown

Compute modified GUF during an ecological write-down event (NLSA Eq. 29).

```bash
# Restoration pathway (default)
python3 utils/eoh_cli.py guf writedown \
    --epsilon 0.40 --area-slu 3.5 --pathway restoration \
    --services-reset-json '[{"label":"water","volume":0.4,"kappa_ref":1.65,"beta":0.8,"retained":0.3}]'

# Abandonment pathway
python3 utils/eoh_cli.py guf writedown \
    --epsilon 0.40 --area-slu 3.5 --pathway abandonment \
    --services-reset-json '[{"label":"water","volume":0.2,"kappa_ref":1.65,"beta":0.8,"retained":0.3}]' \
    --services-lost-json '[{"label":"biodiversity","volume_lost":5.0,"kappa_ref":0.35,"beta":0.7}]'
```

**Services JSON formats:**

Reset services (`--services-reset-json`):
```json
[{"label":"water","volume":0.4,"kappa_ref":1.65,"beta":0.8,"retained":0.3}]
```

Lost services (`--services-lost-json`):
```json
[{"label":"biodiversity","volume_lost":5.0,"kappa_ref":0.35,"beta":0.7}]
```

Options: `--pathway restoration|abandonment`, `--amortization-years N` (default 50).

### guf rebuilding-surcharge

```bash
python3 utils/eoh_cli.py guf rebuilding-surcharge \
    --epsilon 0.40 \
    --services-json '[{"label":"biodiversity","volume_lost":5.0,"kappa_ref":0.35,"beta":0.7}]' \
    [--amortization-years 50] \
    [--format table|json]
```

### guf accumulation-warning

```bash
python3 utils/eoh_cli.py guf accumulation-warning \
    --unfulfilled 450000 \
    --total 1200000 \
    [--threshold 0.30] \
    [--format table|json]
```

Warns when `unfulfilled / total > threshold` (default 0.30). Triggers accelerated ρ_s review and ecology fund priority.

---

### guf inventory — Collective Land Inventory

Batch GUF operations over a collective's full parcel inventory. Parcel data is provided as a JSON file — a list of objects following the [standard parcel schema](../api/land.md#collective-land-inventory).

#### guf inventory calculate

Compute aggregate GUF for a parcel inventory at a given ε.

```bash
python3 utils/eoh_cli.py guf inventory calculate \
    --parcels parcels.json \
    [--epsilon 0.40] \
    [--median-income 350.0] \
    [--format table|json]
```

#### guf inventory sweep

Sweep aggregate GUF across the ε arc.

```bash
python3 utils/eoh_cli.py guf inventory sweep \
    --parcels parcels.json \
    [--epsilon-start 0.0] \
    [--epsilon-end 0.99] \
    [--steps 20] \
    [--format table|json]
```

#### guf inventory stress

Multi-period automation→levy→GUF stress test.

```bash
python3 utils/eoh_cli.py guf inventory stress \
    --parcels parcels.json \
    [--epsilon-start 0.20] \
    [--epsilon-end 0.80] \
    [--periods 20] \
    [--population 1000000] \
    [--format table|json]
```

Omit `--parcels` to use the default 1 000-parcel synthetic urban inventory.

**Parcel JSON format** (list of parcel dicts; only the three required fields needed for a minimal inventory):

```json
[
  {"area_slu": 3.5, "location_value": 0.72, "use_category": "residential_primary"},
  {"area_slu": 5.0, "location_value": 0.85, "use_category": "commercial_retail",
   "ecosystem_services": [{"label": "water", "volume": 0.4, "kappa_ref": 1.65, "beta": 0.8, "retained": 0.3}]}
]
```

See [Land — Collective Inventory](../api/land.md#collective-land-inventory) for the full parcel schema.

---

## contestability — Contestability Invariant (§8)

Arc table, stress sweep, derived levy schedule, the §8.9 recalibrated arc,
and the §8.7e membership-terms audit.

```bash
python3 utils/eoh_cli.py contestability arc    [--regime increasing_returns|replicable] [--points N]
python3 utils/eoh_cli.py contestability stress [--points N]
python3 utils/eoh_cli.py contestability levy   [--chi-target 1.0] [--levy-base capital_yield|machine_output]
python3 utils/eoh_cli.py contestability recal  [--regime ...] [--points N] [--capital-output-ratio 4.0]
python3 utils/eoh_cli.py contestability audit  [--terms-json PATH|-] [inline flags]
```

`--levy-base machine_output` uses the physically-consistent base
`ε·total_EOH` (the pipeline's own measure of automated production) instead of
the static `ε·K·yield`, which understates it ~12× at high ε (proposed §8.8 M3).

### contestability recal

The proposed-§8.9/§8.9b recalibrated arc: the commons owns share φ(ε) of an
ε-consistent capital stock (τ = φ ≤ 1, dτ/dε ≥ 0 structural), and exit is
financed by own labor (low ε), commons underwriting (mid ε), or dividend
savings (high ε) — `t_exit ≤ horizon` replaces the retired flow/stock χ.

`--phi-policy` selects the doctrine: **dilution** (default, §8.9b charter
formation — the commons' share attaches to new capital at commissioning;
private capital is never sold down, so φ caps at ≈ 0.66 by ε = 0.99, marked
`*` in the table), **target** (§8.9a purchase model, regression anchor), or
**escalated** (dilution + the charter escalation clause — full generational
conversion via capital-estate escheat if observed concentration threatens
exit; never fires at canonical defaults, rows marked `!` when active).
`--estate-escheat` sets the baseline capital-estate share (default 0.15 =
`ESTATE_LEVY_FRACTION`, the D5 doctrine extended); raise
`--min-viable-population` to stress the escalation trigger.

```bash
# The doctrine arc (dilution default)
python3 utils/eoh_cli.py contestability recal

# §8.9a purchase model for comparison
python3 utils/eoh_cli.py contestability recal --phi-policy target

# Force the escalation clause to fire (40× founding cohort)
python3 utils/eoh_cli.py contestability recal --phi-policy escalated \
    --min-viable-population 200000
```

### contestability formation

The §8.9c formation-feedback simulation: formation is financed or it does
not happen (private supply falls as the charter share rises), the commons
co-funds from net income per `--priority` (share-first holds the canonical
pace at the dividend's expense; dividend-first crawls and never completes),
and ε derives from the capital actually formed. `--charter-share 0` is the
null anchor; `--hurdle`/`--full-supply` toward fiat-like returns quantify
the Condition III finding (zero interest makes the charter affordable:
s* = 0.50 vs ≈ 0.10 fiat-like).

```bash
# The doctrine run (share-first)
python3 utils/eoh_cli.py contestability formation

# The crawling counterfactual
python3 utils/eoh_cli.py contestability formation --priority dividend --years 120

# The fiat-world counterfactual (dividend driven to zero mid-arc)
python3 utils/eoh_cli.py contestability formation --hurdle 0.06 --full-supply 0.18
```

### contestability audit

Checks proposed membership terms against the χ invariant (the code audits the
contract; it does not legislate it). Terms come from a JSON file, stdin (`-`),
or inline flags (`--vesting-years`, `--admission-cost`, `--exit-notice-years`,
`--minimum-hours`, `--dividend-fraction`); inline flags override JSON keys.

```bash
# Inline: an admission fee at high ε breaches the invariant
python3 utils/eoh_cli.py contestability audit --admission-cost 800 --epsilon 0.9

# From a terms file
python3 utils/eoh_cli.py contestability audit --terms-json terms.json --epsilon 0.4

# §8.8 closure flags: same admission fee, but a funded commons finances exit
python3 utils/eoh_cli.py contestability audit --admission-cost 800 --epsilon 0.9 \
    --commons-balance 1e10 --commons-dividend --underwriting-policy
```

**Terms JSON format** (all fields optional; absent fields keep canonical defaults):

```json
{
  "vesting_years": 5.0,
  "admission_cost_teh": 250.0,
  "exit_notice_years": 0.5,
  "minimum_hours_annual": 400.0,
  "dividend_policy_fraction": 1.0
}
```

---

## coasean — Collective Federation (§§6–7, §8.7)

Research-tier federation mechanics. `--format table|json` goes before the subcommand.

```bash
python3 utils/eoh_cli.py coasean n1-check                  # N=1 regression anchor
python3 utils/eoh_cli.py coasean count                     # emergent N(ε) across the arc
python3 utils/eoh_cli.py coasean federation --epsilon 0.4  # per-collective snapshot
python3 utils/eoh_cli.py coasean simulate --periods 10     # multi-period arc
```

### coasean simulate flags

| Flag | Effect |
|------|--------|
| `--dynamics` | Phase 3 Trust/capital evolution (adds `T`, `τ`, `piketty` columns) |
| `--g-priv F` | private capital growth per period (with `--dynamics`) |
| `--levy-rate F` | common-fund levy on automated output (with `--dynamics`) |
| `--commons` | Phase 4 two-tier commons: escheat, tithe, per-collective χ (adds `commons`, `escheat`, `χ_marg_min`, `χ_status` columns) |
| `--commons-tithe F` | levy fraction routed to the federation commons (default 0.03) |
| `--regime R` | K_entry regime for per-collective χ |
| `--commons-dividend` | §8.8 M1: commons pays a universal unvested dividend that feeds χ (adds `entry_cap`, `exit_fin` semantics) |
| `--commons-start F` | initial commons balance in TEH (seed; `commons_seed_required()` ≈ 1.8e7 at defaults) |

```bash
# The full two-tier arc: consolidation escheat, tithe, and the χ invariant
python3 utils/eoh_cli.py coasean simulate --periods 10 --dynamics --commons --levy-rate 0.3

# §8.8 closure: seeded commons + universal dividend → exit financeable across the arc
python3 utils/eoh_cli.py coasean simulate --periods 21 --epsilon-start 0.0 --dynamics \
    --g-priv 0.02 --levy-rate 0.2 --commons --commons-dividend --commons-start 1.8e7
```
