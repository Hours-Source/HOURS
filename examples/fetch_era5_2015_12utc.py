#!/usr/bin/env python3
"""
Fetch the missing 2015 12 UTC ERA5 block -> rawdata/data201512utc.grib

WHY THIS EXISTS. The synoptic archive samples four hours (00/06/12/18 UTC) on the
1st of six months, every fifth year 1940-2025. An audit of the eta extraction
found `data12utc.grib` holds 102 of 108 expected timestamps: **all six 2015
months are absent at 12 UTC**. 2015 therefore has 00/06/18 but no noon, and noon
is the highest-OLR part of the day over land — averaging it unbalanced would bias
that year low, so 2015 is currently dropped from the climatology (17 of 18 years
retained).

CREDENTIALS. This needs a CDS account: put your key in ~/.cdsapirc and accept the
ERA5 licence at cds.climate.copernicus.eu first, or the request 403s.

    url: https://cds.climate.copernicus.eu/api
    key: <your-key>

VARIABLE SET. The default below is the small set the eta work needs (~50 MB).
The archive's other files carry the FULL single-level catalogue — matching that
for 2015 would be ~10 GB (189 GB / 108 timestamps x 6). Pass --full only if you
want the block to match the rest of the archive rather than just close the eta
gap; nothing in the thermal layer requires it.
"""
from __future__ import annotations
import argparse
import cdsapi

MONTHS = ["01", "03", "05", "08", "10", "12"]      # the archive's sampled months
ETA_VARIABLES = [
    "top_net_thermal_radiation",
    "top_net_thermal_radiation_clear_sky",
    "mean_top_net_long_wave_radiation_flux",
    "mean_top_net_long_wave_radiation_flux_clear_sky",
    "total_cloud_cover",
    "total_column_water_vapour",
    "land_sea_mask",
    "skin_temperature",
    "2m_temperature",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", default="rawdata/data201512utc.grib")
    ap.add_argument("--full", action="store_true",
                    help="request the full single-level catalogue (~10 GB) instead of "
                         "the eta subset (~50 MB)")
    args = ap.parse_args()

    if args.full:
        raise SystemExit(
            "Re-run your ORIGINAL archive request with year=2015 and time=12:00 — "
            "this script does not carry the full 262-variable list, and guessing it "
            "would produce a block that silently differs from the rest of the archive."
        )

    cdsapi.Client().retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": ["reanalysis"],     # NOT ensemble: the 0.5 deg ensemble
                                                # shares shortNames with the 0.25 deg
                                                # reanalysis and will overwrite it
            "variable": ETA_VARIABLES,
            "year": ["2015"],
            "month": MONTHS,
            "day": ["01"],
            "time": ["12:00"],
            "data_format": "grib",
            "download_format": "unarchived",
        },
        args.out,
    )
    print(f"wrote {args.out} — re-run the eta extraction to pick 2015 back up")


if __name__ == "__main__":
    main()
