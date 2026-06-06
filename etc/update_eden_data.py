#!/usr/bin/env python3
"""
update_eden_data.py
Extend BAM EDEN runoff stage file from 2017-06-30 to 2026-04-30 (WY2026).

Data source:
  USGS Everglades Depth Estimation Network (EDEN) v3 water surface model,
  served via the USGS South Florida THREDDS/OPeNDAP server:
    http://sflthredds.er.usgs.gov/thredds/dodsC/eden/surfaces/YYYY_qN.nc

  The server holds all 145 quarters (1991 Q1 – 2026 Q2) as individual NetCDF
  files on a 400 m UTM Zone 17N grid with dimensions time × y(405) × x(287).
  Variable: stage (Float32, cm NAVD88).

  Stage values are extracted at 8 specific UTM coordinates (S15–S22) using
  nearest-grid-cell selection, then converted to metres and offset to MSL:
    output_m = stage_cm / 100.0 - MSL_NAVD88
  where MSL_NAVD88 = -0.148 m  (i.e., output_m = NAVD88_m + 0.148 m)

  OPeNDAP is used so only the 8 grid cells of interest are transferred per
  quarter — no full-grid file downloads.

  Coordinates source: BAM/etc/FBM_EDEN.xyLocator.txt
  EDEN reference: Telis et al. (2015) USGS SIR 2014-5209

  Data from approx. 2024 Q3 onward is provisional pending USGS final review.

Usage:
  python update_eden_data.py             # full run -- writes output file
  python update_eden_data.py --dry-run   # stats only -- nothing written

Requirements:
  pip install xarray pydap pandas numpy
  (pydap provides OPeNDAP without compiled-C dependencies; version >= 3.3.0)
"""

import sys
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXTEND_START = '2017-07-01'
EXTEND_END   = '2026-04-30'

THREDDS_BASE = 'http://sflthredds.er.usgs.gov/thredds/dodsC/eden/surfaces'

# MSL offset: MSL = -0.148 m NAVD88.
# output = NAVD88_m - MSL_NAVD88 = NAVD88_m - (-0.148) = NAVD88_m + 0.148 m
MSL_NAVD88 = -0.148   # m

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
EXISTING = DATA_DIR / 'Runoff' / 'EDEN_Stage_OffsetMSL.csv'
OUT_FILE = DATA_DIR / 'Runoff' / 'EDEN_Stage_OffsetMSL_1999-9-1_2026-4-30.csv'

# Station name, UTM Easting (m), UTM Northing (m) — Zone 17N
# Column order matches existing CSV: S22 first (leftmost), S15 last (rightmost)
STATIONS = [
    ('S22', 555200, 2795700),
    ('S21', 550000, 2795500),
    ('S20', 545000, 2795000),
    ('S19', 540000, 2794500),
    ('S18', 535000, 2791500),
    ('S17', 530000, 2790000),
    ('S16', 525000, 2792500),
    ('S15', 520000, 2794000),
]

# Plausible annual mean range for MSL-offset Everglades stage (m)
STAGE_PLAUSIBLE = (-0.5, 0.8)

# ---------------------------------------------------------------------------
# Quarter utilities
# ---------------------------------------------------------------------------

def quarter_of(dt):
    """Return (year, quarter 1-4) for a Timestamp or date string."""
    ts = pd.Timestamp(dt)
    return ts.year, (ts.month - 1) // 3 + 1


def iter_quarters(start_str, end_str):
    """Yield (year, quarter) tuples from the quarter that contains start
    through the quarter that contains end, inclusive."""
    y,  q  = quarter_of(start_str)
    ey, eq = quarter_of(end_str)
    while (y, q) <= (ey, eq):
        yield y, q
        q += 1
        if q > 4:
            q, y = 1, y + 1

# ---------------------------------------------------------------------------
# OPeNDAP helpers
# ---------------------------------------------------------------------------

def _decode_time(ds):
    """
    Return a DatetimeIndex from the 'time' variable in an EDEN dataset.
    Handles two formats:
      (a) CF-decoded numpy.datetime64 (standard NetCDF convention)
      (b) Raw Int32 values formatted as YYYYMMDD integers
    """
    t = ds['time'].values
    if np.issubdtype(t.dtype, np.datetime64):
        return pd.DatetimeIndex(t).normalize()
    # Fall back: integer YYYYMMDD
    return pd.DatetimeIndex(
        pd.to_datetime(t.astype(int).astype(str), format='%Y%m%d')
    )


def fetch_quarter(year, quarter):
    """
    Fetch daily stage at all 8 stations for one quarter via OPeNDAP.

    Strategy:
      1. Open dataset lazily (only DDS/DAS metadata transferred).
      2. Load the 1-D x and y coordinate arrays (287 + 405 floats — tiny).
      3. Compute nearest-grid-cell indices for each station.
      4. Use isel() to request only those specific cells; pydap translates
         each to a constrained OPeNDAP request (one cell's time series).

    Returns DataFrame indexed by date, columns S22…S15, values in m MSL offset.
    """
    url = f'{THREDDS_BASE}/{year}_q{quarter}.nc'
    print(f'  {year}_q{quarter} ... ', end='', flush=True)

    try:
        ds = xr.open_dataset(url, engine='pydap')
    except Exception as e:
        raise RuntimeError(f'Cannot open {url} : {e}')

    # Download only the 1-D coordinate arrays (< 5 KB each)
    x_coords = ds.coords['x'].values.astype(float)   # easting,  287 pts
    y_coords = ds.coords['y'].values.astype(float)   # northing, 405 pts

    times = _decode_time(ds)

    rows = {}
    for name, x_utm, y_utm in STATIONS:
        xi = int(np.abs(x_coords - x_utm).argmin())
        yi = int(np.abs(y_coords - y_utm).argmin())
        # Each isel triggers one small OPeNDAP request: stage[0:N-1][yi][xi]
        cell_cm = ds['stage'].isel(x=xi, y=yi).values.astype(float)
        rows[name] = np.round(cell_cm / 100.0 - MSL_NAVD88, 3)

    ds.close()

    df = pd.DataFrame(rows, index=times)
    df.index.name = 'Date'
    print(f'{len(df)} days  [{df.index[0].date()} – {df.index[-1].date()}]')
    return df

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def print_summary(df_existing, df_new, df_combined):
    sep = '=' * 68

    # 1. Annual means by station
    print('\n' + sep)
    print('1. ANNUAL MEAN STAGE BY STATION (m, MSL offset)')
    print(sep)
    print(f'  {"Stn":4}  {"1999-2017 mean":>14}  {"2017-2026 mean":>14}  {"Delta":>8}')
    for col in df_combined.columns:
        pre  = df_existing[col].resample('YE').mean().mean()
        post = df_new[col].resample('YE').mean().mean()
        dp   = (post - pre) / abs(pre) * 100 if pre != 0 else float('nan')
        print(f'  {col:4}  {pre:>+14.3f}  {post:>+14.3f}  {dp:>+7.1f}%')

    # 2. Seam check
    print('\n' + sep)
    print('2. SEAM CHECK — 7-day mean before/after 2017-07-01')
    print(sep)
    for col in df_combined.columns:
        pre_m  = df_existing[col].iloc[-7:].mean()
        post_m = df_new[col].iloc[:7].mean()
        print(f'  {col}  before={pre_m:+.3f} m  after={post_m:+.3f} m  '
              f'delta={post_m - pre_m:+.3f} m')

    # 3. Sanity: annual means in plausible range
    print('\n' + sep)
    print(f'3. SANITY — annual means (plausible: '
          f'{STAGE_PLAUSIBLE[0]} to {STAGE_PLAUSIBLE[1]} m)')
    print(sep)
    ann = df_combined.resample('YE').mean()
    bad = ann[(ann < STAGE_PLAUSIBLE[0]) | (ann > STAGE_PLAUSIBLE[1])].dropna(how='all')
    if bad.empty:
        print('  All annual station-means within plausible range.')
    else:
        print('  WARNING — out-of-range values:')
        print(bad.round(3).to_string())

    # 4. Row count
    print('\n' + sep)
    print('4. ROW COUNT')
    print(sep)
    print(f'  Existing : {len(df_existing):5d}  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}')
    print(f'  New      : {len(df_new):5d}  '
          f'{df_new.index[0].date()} -> {df_new.index[-1].date()}')
    print(f'  Combined : {len(df_combined):5d}  '
          f'{df_combined.index[0].date()} -> {df_combined.index[-1].date()}')
    print(sep)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print('\n' + '=' * 68)
        print('  DRY-RUN MODE -- stats only, no files written')
        print('=' * 68)

    # Step 1 -----------------------------------------------------------------
    print('\n-- Step 1: Load existing EDEN stage file -------------------------')
    df_existing = pd.read_csv(EXISTING, parse_dates=['Date'], index_col='Date')
    print(f'  {len(df_existing)} rows  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}  '
          f'cols: {list(df_existing.columns)}')

    # Step 2 -----------------------------------------------------------------
    print('\n-- Step 2: Fetch quarters via THREDDS/OPeNDAP --------------------')
    quarters = list(iter_quarters(EXTEND_START, EXTEND_END))
    q0, q1   = quarters[0], quarters[-1]
    print(f'  {len(quarters)} quarters: {q0[0]}_q{q0[1]} -> {q1[0]}_q{q1[1]}\n')

    frames = []
    for year, q in quarters:
        try:
            frames.append(fetch_quarter(year, q))
        except RuntimeError as e:
            print(f'\n  ERROR: {e}')
            sys.exit(1)

    # Concatenate, deduplicate, trim to exact extension window
    df_new = (pd.concat(frames)
                .pipe(lambda d: d[~d.index.duplicated(keep='first')])
                .sort_index()
                .loc[EXTEND_START:EXTEND_END]
                .round(3))

    # Enforce column order matching existing file
    df_new = df_new[df_existing.columns]

    print(f'\n  New data: {len(df_new)} rows  '
          f'{df_new.index[0].date()} -> {df_new.index[-1].date()}')

    # Step 3 -----------------------------------------------------------------
    print('\n-- Step 3: Combine -----------------------------------------------')
    df_combined = (pd.concat([df_existing, df_new])
                     .pipe(lambda d: d[~d.index.duplicated(keep='first')])
                     .sort_index())
    print(f'  Combined: {len(df_combined)} rows  '
          f'{df_combined.index[0].date()} -> {df_combined.index[-1].date()}')

    # Step 4 -----------------------------------------------------------------
    print('\n-- Step 4: Summary statistics ------------------------------------')
    print_summary(df_existing, df_new, df_combined)

    # Step 5 -----------------------------------------------------------------
    if dry_run:
        print('\n  DRY-RUN: file NOT written.')
        print(f'  Would save to: {OUT_FILE.name}')
        print('  Re-run without --dry-run to write.')
    else:
        print('\n-- Step 5: Write output file ------------------------------------')
        df_combined.to_csv(OUT_FILE, float_format='%.3f')
        kb = OUT_FILE.stat().st_size / 1024
        print(f'  Saved -> {OUT_FILE.name}  ({kb:.0f} KB, {len(df_combined)} rows)')

    print('\n' + '=' * 68)
    print('Done.')
    print('=' * 68)


if __name__ == '__main__':
    main()
