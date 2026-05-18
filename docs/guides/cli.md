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

```bash
python3 utils/eoh_cli.py scenario run automation_failure --format csv > results/shock.csv
```

See [Running Scenarios](scenarios_howto.md) for Python API usage.

---

## simulate

Multi-period simulation with period-by-period state table.

```bash
python3 utils/eoh_cli.py simulate [--periods N] [--epsilon ε] [--epsilon-delta Δε]
```

```bash
python3 utils/eoh_cli.py simulate --periods 20 --epsilon 0.30 --epsilon-delta 0.02
```

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
