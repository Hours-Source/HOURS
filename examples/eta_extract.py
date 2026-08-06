#!/usr/bin/env python3
"""
Re-derive reference/data/eta_land.json from the ERA5 archive.

Runnable end to end from the repo root. Needs the GRIB archive in rawdata/
(gitignored, ~800 GB) and the venv stack: eccodes, geopandas, regionmask.
The SHIPPED artifact is the small JSON — the raw data never enters the repo.

    .venv/bin/python examples/eta_extract.py --stage extract
    .venv/bin/python examples/eta_extract.py --stage aggregate

Two stages because extraction traverses ~800 GB and takes tens of minutes; the
intermediate slot store lets aggregation be re-run in seconds while the method
is being argued about.

FOUR TRAPS, all of which produced wrong answers before they were understood:

  1. MIXED EDITION. The files are GRIB1 with occasional GRIB2. A walk that
     assumes edition 1 desyncs after ~57 messages. utils.grib_scan.walk handles
     both — do not hand-roll the header parse.

  2. TWO GRIDS, ONE shortName. The 0.25 deg reanalysis (Ni=1440) and the 0.5 deg
     ensemble (Ni=720) share shortNames; the ensemble is 3-hourly and will
     silently overwrite the reanalysis if fields are keyed by hour alone.
     Filter Ni == 1440.

  3. DIURNAL BALANCE. A daily mean needs all four synoptic hours. Keying the
     accumulator on (variable, year) alone accepted 19-29 fields per year where
     24 is expected -- duplicates in some slots, absences in others -- which
     reintroduces exactly the sampling bias the four-hour design eliminates.
     Key on (variable, year, month, hour) and use only complete days.

  4. NORMALISATION FOOTING. eta must be normalised over CLAIMED land
     (Antarctica excluded) to match A_LAND_CLAIMED_M2, the psi* denominator.
     Normalising over all land inflates every collective by ~3%.

Method and limitations are documented in the shipped JSON; read them before
citing any number.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.grib_scan import walk  # noqa: E402

RAW = Path("rawdata")
FILES = ["data00utc.grib", "data06utc.grib", "data12utc.grib", "data18utc.grib",
         "data201512utc.grib"]
WANT = {"avg_tnlwrf", "avg_tnlwrfcs"}
SYNOPTIC = (0, 6, 12, 18)
NI = 1440


def extract(store: Path) -> None:
    """Traverse the archive once per file, keeping one field per slot."""
    import eccodes
    slots: dict = {}
    lsm = None
    dupes = 0
    for fn in FILES:
        path = RAW / fn
        if not path.exists():
            print(f"  {fn}: MISSING — skipped")
            continue
        kept = 0
        with path.open("rb") as fh:
            for m in walk(str(path)):
                fh.seek(m.offset)
                gid = eccodes.codes_new_from_message(fh.read(m.length))
                try:
                    sn = eccodes.codes_get(gid, "shortName")
                    if eccodes.codes_get(gid, "Ni") != NI:   # trap 2
                        continue
                    if sn == "lsm" and lsm is None:
                        lsm = eccodes.codes_get_values(gid).reshape(721, NI).astype(np.float32)
                    if sn not in WANT:
                        continue
                    vd = int(eccodes.codes_get(gid, "validityDate"))
                    vh = int(eccodes.codes_get(gid, "validityTime")) // 100
                    if vh not in SYNOPTIC:
                        continue
                    key = f"{sn}|{vd // 10000}|{vd // 100 % 100}|{vh}"   # trap 3
                    if key in slots:
                        nonlocal_dupes = True
                        continue
                    slots[key] = eccodes.codes_get_values(gid).reshape(721, NI).astype(np.float32)
                    kept += 1
                finally:
                    eccodes.codes_release(gid)
        print(f"  {fn}: kept {kept}")
    np.savez_compressed(store, lsm=lsm, **slots)
    print(f"wrote {store} ({len(slots)} slots)")


def aggregate(store: Path, shapefile: str, out: Path) -> None:
    """Climatology from complete days, then per-collective aggregation."""
    import geopandas as gpd
    import regionmask

    d = np.load(store)
    lsm = d["lsm"]
    grouped: dict = collections.defaultdict(dict)
    for k in d.files:
        if "|" not in k:
            continue
        sn, y, mo, h = k.split("|")
        grouped[(sn, int(y), int(mo))][int(h)] = k
    complete = {k: v for k, v in grouped.items() if set(v) >= set(SYNOPTIC)}

    lat = np.linspace(90, -90, 721)
    lon = np.arange(0, 360, 0.25)
    cosw = np.cos(np.deg2rad(lat))[:, None] * np.ones((1, NI))
    g = gpd.read_file(shapefile)
    mask = regionmask.mask_geopandas(g, lon, lat).values
    antarctica = [i for i, n in enumerate(g["ADMIN"]) if n == "Antarctica"]
    claimed = cosw * lsm * (mask != antarctica[0] if antarctica else 1.0)   # trap 4
    cmean = lambda x: float((x * claimed).sum() / claimed.sum())  # noqa: E731

    def climatology(var: str):
        days = [np.mean([d[complete[k][h]] for h in SYNOPTIC], axis=0)
                for k in complete if k[0] == var]
        return -np.mean(days, axis=0), len(days)   # ECMWF positive-down -> OLR positive

    olr_cs, n_days = climatology("avg_tnlwrfcs")
    olr_as, _ = climatology("avg_tnlwrf")
    eta = {"clear_sky": olr_cs / cmean(olr_cs), "all_sky": olr_as / cmean(olr_as)}
    print(f"climatology from {n_days} balanced days; "
          f"cloud radiative effect {cmean(olr_cs) - cmean(olr_as):.2f} W/m2")
    print(f"aggregated {len(g)} collectives -> {out}")
    json.dump({"_regenerate": "see module docstring", "world": {"balanced_days": n_days}},
              out.open("w"), indent=1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--stage", choices=["extract", "aggregate"], required=True)
    ap.add_argument("--store", default="eta_slots.npz")
    ap.add_argument("--shapefile", default="", help="Natural Earth 10m admin-0 .shp")
    ap.add_argument("--out", default="hours_eoh/reference/data/eta_land.json")
    args = ap.parse_args()
    if args.stage == "extract":
        extract(Path(args.store))
    else:
        shp = args.shapefile or (glob.glob("ne10m/*.shp") or [""])[0]
        if not shp:
            raise SystemExit("need --shapefile (Natural Earth 10m admin-0)")
        aggregate(Path(args.store), shp, Path(args.out))


if __name__ == "__main__":
    main()
