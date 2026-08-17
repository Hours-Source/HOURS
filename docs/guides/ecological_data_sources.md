# Ecological EOH — where the numbers come from, and what is still missing

The ecological domain is the framework's largest open measurement debt: 41 of the
89 live placeholders sit in the land block. This page records what has been
measured, what was checked and rejected, and what would close the rest.

Run it: `eoh scenario run land_stewardship [--scope --allocation --amenity-weight]`

## The defect this addresses

`ecological_eoh()` used to take no area and no population — it returned
`base_rate / health` and nothing scaled it. That made ecological the only domain
with no extensive quantity behind it (personal scales with population,
infrastructure with capital, knowledge with the corpus), which is why its share
collapses as the system grows.

It is now keyed to **area**, via `ecological_scale()`. Spread over the land it is
nominally the obligation for, the shipped anchor is **2.35 seconds per hectare
per year** — the defect in units that make it obvious. The form was fixed
without moving the level: `US_MAINLAND_HECTARES × ECOLOGICAL_INTENSITY_BASE`
reproduces `ECOLOGICAL_BASE_RATE` exactly.

Population deliberately stays out of the rate. Load per hectare does drive
demand, but the model already carries that: `ecosystem_health` falls under load
and the obligation divides by it.

## The census, and what it reads

US, 2022 land use × 2025 workforce. Three measured inputs, one assumed mapping —
which occupations steward which land class. That assumption is the weak link and
is the first thing to attack.

| land class | area | h/ha·yr |
|---|---|---|
| Forest-use land | 250.1 Mha | 0.182 |
| Rural parks and wildlife — federal | 71.6 Mha | 0.161 |
| Urban (at the declared amenity weight) | 26.8 Mha | 4.35 |
| cropland, rangeland, state parks, misc | 566.6 Mha | **unpriced** |

**Coverage 38.1%; mean 0.498 h/ha·yr; 1.35× the anchor.** Unpriced land is
excluded, not costed at zero, so the mean is a lower bound over the part that
has a costed path. Read `coverage` before comparing it to anything.

## The one decision that moves the answer

Whether urban groundskeeping is ecological stewardship is worth **41×**.
Signed off at a declared weight rather than either corner:
`AMENITY_STEWARDSHIP_WEIGHT = 0.0468`, from the amenity class's own occupational
composition — canopy in (37-3013 maintains structure delivering three of the
seven GUF services), turf out (37-3011, 1.24M workers, delivers none). The
anchor is crossed at w\* = 0.0288, below the adopted weight, so **the weight sets
the magnitude and not the sign.** Both corners stay reachable via `--scope`.

## Instruments checked and rejected

Four, and the failure mode moved each time — which is how the remaining gap got
well-posed:

| instrument | verdict |
|---|---|
| NRCS EQIP payment schedules | **no time unit, no labour line** in 2,691 rows; the dollar column mixes implementation cost with foregone income |
| Penn State extension budgets | hours yes — but crop **production** hours for horticultural crops, not stewardship |
| Agency headcount, raw | overstates **4.4×** without the role mix |
| ASAE field capacity | **works** — `width × speed × efficiency / 8.25`, no price in the chain |

The general rule these produced: **a `resolves_by` that names a source without
naming the field in it that carries the quantity has not been checked.**

## What is still missing

- **Cropland and rangeland, 416.9 Mha.** Hours per treated hectare are now
  derivable from field capacity (cover crop: 0.303–0.844 h/ha·yr). The missing
  input is the *adoption fraction* — what share of cropland receives each
  practice — from the USDA Census of Agriculture. **The unknown is bounded**:
  even 100% adoption adds only 0.27–0.74× the current census, so cropland is not
  where the domain-balance gap is hiding.
- **State parks, 36.0 Mha.** Needs NASPD state-park operating statistics.
- **Agency role mix band [0.2263, 0.4073].** Narrowed by a task decomposition
  inside series 0025 (park ranger) and 0456 (wildland fire); NPS budget
  justifications report FTE by activity.

## Two cautions

**These figures are US-only and do not transfer.** Land-use composition,
mechanisation and public land-management staffing all differ enough between
jurisdictions that the intensities are jurisdiction-bound, the same way
`personal_basket`'s delivery productivity is bound to its agro-ecology.

**NPS and FWS differ 5.3× in role mix** (10.1% against 53.6%). NPS is a
visitor-services organisation standing on land; FWS refuges are a land-management
organisation. Do not quote a single federal stewardship rate.
