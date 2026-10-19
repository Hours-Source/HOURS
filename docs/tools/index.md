# Explore in the browser

The tools linked here run entirely in your browser. There is nothing to install
and nothing to download, and a tool page makes no requests to other sites. Each one is built from the
repository's data every time the documentation is published, and the build
refuses to publish a page that breaks its contract: for the multiplier explorer,
numbers that no longer match the code; for the family hours explorer, a value
with no stated source.

## Multiplier registry explorer

**[Open the multiplier explorer](multiplier/index.html)**

Look up any occupation in the measured O*NET/BLS registry to see how its reference multiplier
is built, step by step, from O*NET and BLS data. You can put two occupations side
by side to see which factors separate them, and move the chosen factor weights to
see how much the result depends on them.

What it shows, and what it does not:

- **The multiplier sets the floor** at which an hour of the work is minted as
  TEH. It is not a wage, and it says nothing about what the work earns above that
  floor.
- **The order of occupations and the ratio between any two are what the data
  measures.** The overall range (×1.0 to ×3.2) and where the employment-weighted
  average falls come from how the scores are normalized. The spread ratio R was
  solved so that the average lands in the 1.8–2.1 band, so the band being met
  is not evidence of anything.
- **The factor and impact weights are chosen, not measured.** The weight sliders
  keep the frozen scale fixed, as the sensitivity harness
  (`hours_eoh/scenarios/multiplier_sensitivity.py`) does, and report how many
  occupations get clipped at either end.

The method is described under [Multipliers](../api/core/multipliers.md) and
[Parameter Provenance](../parameter_provenance.md).

## Family hours explorer

**[Open the family hours explorer](family-hours/index.html)**

Turn a US family's living costs into hours of paid work a week at the
household's own wage, and see whether they fit the hours its earners have. Set
the wage, the earners, the children, housing and the other costs, and compare
the result with federal affordability standards. Every setting is saved in the
page link, so a result can be shared.

What it shows, and what it does not:

- **These are market hours, not obligation hours.** Each cost is divided by pay
  per hour. They are not EOH or TEH, and none of the figures comes from the
  framework's calculations. The market layer, where prices and wages are set, is
  not modelled in this repository yet.
- **Every default is external US data with its source and date.** The values
  live in one file, `hours_eoh/reference/data/family_costs.json`, and the page,
  its sources list and its wage presets are built from it. The build refuses a
  value with no source, read date or update cadence, and reports a value whose
  source has published since it was read. Where the handoff the values came from
  cited no document, or quoted a secondary report, the entry says so.
- **Taxes are approximate.** Federal brackets with the child tax credit and its
  phase-out, FICA, a flat state and local rate, and the EITC when checked.
  Retirement saving and the health premium are taken out before tax.
- **The yearly-to-hourly divisor is the framework's `H_REF`**, 40 hours × 52
  weeks, a declared convention rather than a measurement of hours worked.

