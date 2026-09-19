# Explore in the browser

The tools linked here run entirely in your browser. There is nothing to install
and nothing to download, and a tool page makes no requests to other sites. Each one is built from the
repository's data every time the documentation is published, and the build
refuses to publish a page whose numbers no longer match the code.

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
