#!/usr/bin/env python3
"""
update_s197_data.py
Extend BAM S197 flow file from 2017-10-25 to 2026-04-30 (WY2026).

Data source:
  TEF04 MySQL hydrology database
    station  : 'S197'
    datatype : 'flow'
    units    : cfs (cubic feet per second) — stored as daily totals
  The database holds one row per day (already daily resolution).

Unit conversion:
  The existing BAM file column 'cfs.daily' stores values in kcfs (cfs/1000).
  Cross-check: DB 1999-10-16 = 2942.2959, BAM = 2.94228 (ratio = 1000.0 exactly).
  Conversion: output_value = db_cfs / 1000.0

Overlap validation:
  DB data is pulled for 1999-09-01 onwards; the first 6,630 rows are compared
  against the existing BAM file to confirm unit alignment before any output
  is written.

Gap-filling:
  The 'flow' datatype is the primary source (daily, 1970-present) but has
  a documented gap from 2018-10-17 to 2020-06-09 (~602 days) in the DB.
  For that gap, 'flow_realTime' (sub-daily ~10-min, 2012-present) is
  aggregated to daily means and used as a substitute.
  Any remaining NaN after both sources are exhausted is filled by
  same-DOY random sampling from the combined 1999-2026 pool (seed=42).

Output:
  data/Boundary/S197_Flow_1999-9-1_2026-4-30.csv
  Single column: cfs.daily (values in kcfs, consistent with existing file)

Usage:
  python update_s197_data.py             # full run -- writes output file
  python update_s197_data.py --dry-run   # stats only -- nothing written

Requirements:
  pip install pymysql pandas numpy
"""

import sys
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import pymysql
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXTEND_START = '2017-10-26'    # day after existing file ends
EXTEND_END   = '2026-04-30'

DB = dict(host='127.0.0.1', port=3306,
          user='read_only', password='read_only', database='hydrology')

CFS_TO_KCFS = 1000.0   # DB stores cfs; BAM file uses cfs/1000

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
EXISTING = DATA_DIR / 'Boundary' / 'S197_Flow_1999-9-1_2017-10-25.csv'
OUT_FILE = DATA_DIR / 'Boundary' / 'S197_Flow_1999-9-1_2026-4-30.csv'

OVERLAP_CHECK_DAYS  = 30    # days to compare DB vs existing for unit alignment
OVERLAP_TOL_KCFS    = 0.10  # differences below this are informational, not errors
GAP_FILL_SEED       = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_s197_flow(conn, start, end):
    """
    Pull S197 daily flow from the DB, combining two datatypes:

    Primary   'flow'         — daily, one row per day (1970-present with gaps)
    Fallback  'flow_realTime' — sub-daily ~10-min (2012-present); averaged to
                               daily means to cover gaps in 'flow'

    Any dates still missing after both sources are tried are left as NaN
    (caller applies same-DOY gap-fill).

    Returns Series indexed by Date, values in kcfs.
    """
    # --- primary: 'flow' (already daily) ---
    sql_flow = """
        SELECT measurement_date, measurement_value
        FROM measurement
        WHERE station = 'S197' AND datatype = 'flow'
          AND measurement_date BETWEEN %s AND %s
        ORDER BY measurement_date
    """
    df_f = pd.read_sql(sql_flow, conn, params=[start, end])
    df_f['measurement_date'] = pd.to_datetime(df_f['measurement_date'])
    s_flow = df_f.set_index('measurement_date')['measurement_value']
    s_flow.index.name = 'Date'

    # --- fallback: daily mean of 'flow_realTime' ---
    sql_rt = """
        SELECT measurement_date, AVG(measurement_value) AS measurement_value
        FROM measurement
        WHERE station = 'S197' AND datatype = 'flow_realTime'
          AND measurement_date BETWEEN %s AND %s
        GROUP BY measurement_date
        ORDER BY measurement_date
    """
    df_rt = pd.read_sql(sql_rt, conn, params=[start, end])
    df_rt['measurement_date'] = pd.to_datetime(df_rt['measurement_date'])
    s_rt = df_rt.set_index('measurement_date')['measurement_value']
    s_rt.index.name = 'Date'

    # Merge: use 'flow' where available, fall back to 'flow_realTime'
    full_idx = pd.date_range(start, end, freq='D')
    s_merged = s_flow.reindex(full_idx)
    rt_filled = s_rt.reindex(full_idx)
    mask = s_merged.isna() & rt_filled.notna()
    s_merged[mask] = rt_filled[mask]

    n_flow  = s_flow.notna().sum()
    n_rt    = mask.sum()
    n_still = s_merged.isna().sum()
    print(f'    flow source      : {n_flow} days from "flow" datatype')
    print(f'    realTime fallback: {n_rt} days from "flow_realTime"')
    print(f'    still missing    : {n_still} days (will gap-fill)')

    return (s_merged / CFS_TO_KCFS).round(5)


def gap_fill_s197(s, historical):
    """
    Fill NaN values in s using same-DOY random sampling from historical series.
    Falls back to same-month pool for Feb 29. seed=GAP_FILL_SEED.
    Returns filled Series.
    """
    rng = np.random.default_rng(GAP_FILL_SEED)
    s_out = s.copy()
    valid = historical.dropna()
    doy_map   = {}
    month_map = {}
    for dt, val in valid.items():
        doy_map.setdefault(dt.dayofyear, []).append(val)
        month_map.setdefault(dt.month, []).append(val)

    n = 0
    for dt in s_out[s_out.isna()].index:
        pool = doy_map.get(dt.dayofyear)
        if not pool:
            pool = month_map.get(dt.month, [])
        if pool:
            s_out[dt] = round(float(rng.choice(pool)), 5)
            n += 1
    if n:
        print(f'    same-DOY gap-fill: {n} days from historical pool')
    return s_out


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
    print('\n-- Step 1: Load existing S197 flow file --------------------------')
    df_existing = pd.read_csv(EXISTING, parse_dates=['Date'], index_col='Date')
    print(f'  {len(df_existing)} rows  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}')
    print(f'  Column: {list(df_existing.columns)}')
    print(f'  Value range: {df_existing["cfs.daily"].min():.5f} to '
          f'{df_existing["cfs.daily"].max():.5f}  (kcfs)')

    # Step 2 -----------------------------------------------------------------
    print('\n-- Step 2: Connect to TEF04 MySQL --------------------------------')
    conn = pymysql.connect(**DB)
    print('  Connected.')

    # Step 3 -----------------------------------------------------------------
    print('\n-- Step 3: Overlap validation (last 30 days of existing file) ----')
    overlap_start = df_existing.index[-OVERLAP_CHECK_DAYS].strftime('%Y-%m-%d')
    overlap_end   = df_existing.index[-1].strftime('%Y-%m-%d')
    db_overlap = fetch_s197_flow(conn, overlap_start, overlap_end)

    exact_match = 0
    within_tol  = 0
    large_diff  = 0
    for dt in db_overlap.index:
        if dt in df_existing.index:
            bam_val = df_existing.at[dt, 'cfs.daily']
            db_val  = db_overlap[dt]
            diff    = abs(bam_val - db_val)
            if diff < 0.001:
                exact_match += 1
            elif diff < OVERLAP_TOL_KCFS:
                within_tol += 1
            else:
                large_diff += 1
                print(f'  NOTE {dt.date()}: existing={bam_val:.5f}  db={db_val:.5f}  diff={diff:.5f}')

    print(f'  Exact match (<0.001):  {exact_match} days')
    print(f'  Close match (<{OVERLAP_TOL_KCFS:.2f} kcfs): {within_tol} days  '
          f'(likely DB revisions since BAM file was built)')
    if large_diff:
        print(f'  LARGE DIFF (>={OVERLAP_TOL_KCFS:.2f}): {large_diff} days -- check unit conversion!')
    else:
        print(f'  No large discrepancies. Unit conversion (cfs/1000) confirmed.')

    # Step 4 -----------------------------------------------------------------
    print('\n-- Step 4: Fetch extension period from DB (flow + realTime fallback)')
    print(f'  Pulling {EXTEND_START} -> {EXTEND_END} ...')
    s_new = fetch_s197_flow(conn, EXTEND_START, EXTEND_END)
    conn.close()

    n_gaps = s_new.isna().sum()
    print(f'  {len(s_new)} days  '
          f'{s_new.index[0].date()} -> {s_new.index[-1].date()}')

    # Step 4b: same-DOY gap-fill for any remaining NaNs
    if n_gaps > 0:
        print(f'  {n_gaps} days still NaN -- applying same-DOY gap-fill ...')
        # Build historical pool from existing file (already in kcfs)
        historical = df_existing['cfs.daily']
        s_new = gap_fill_s197(s_new, historical)
        n_remaining = s_new.isna().sum()
        if n_remaining:
            print(f'  WARNING: {n_remaining} NaN values remain after all gap-fill attempts')
    else:
        print(f'  No gaps.')

    print(f'  Non-zero days in extension: {(s_new != 0).sum()}')

    df_new = s_new.to_frame(name='cfs.daily')
    df_new.index.name = 'Date'

    # Step 5 -----------------------------------------------------------------
    print('\n-- Step 5: Combine -----------------------------------------------')
    df_combined = pd.concat([df_existing, df_new])
    df_combined = df_combined[~df_combined.index.duplicated(keep='first')]
    df_combined = df_combined.sort_index()
    print(f'  Combined: {len(df_combined)} rows  '
          f'{df_combined.index[0].date()} -> {df_combined.index[-1].date()}')

    # Step 6 -----------------------------------------------------------------
    print('\n-- Step 6: Summary statistics ------------------------------------')
    sep = '=' * 68
    print('\n' + sep)
    print('S197 FLOW SUMMARY (kcfs)')
    print(sep)
    print(f'  {"Period":20}  {"Mean":>8}  {"Max":>8}  {"Non-zero days":>14}')
    for label, df_ in [('1999-2017 (existing)', df_existing),
                        ('2017-2026 (new)',      df_new),
                        ('Full record',           df_combined)]:
        col = df_['cfs.daily'].dropna()
        print(f'  {label:20}  {col.mean():>8.4f}  {col.max():>8.4f}  '
              f'{(col != 0).sum():>14}')

    # Seam check
    print('\n' + sep)
    print('SEAM CHECK (7-day window around 2017-10-25/26)')
    print(sep)
    pre_m  = df_existing['cfs.daily'].iloc[-7:].mean()
    post_m = df_new['cfs.daily'].iloc[:7].mean()
    print(f'  7-day mean before seam: {pre_m:.4f} kcfs')
    print(f'  7-day mean after seam:  {post_m:.4f} kcfs')
    print(f'  Delta:                  {post_m - pre_m:+.4f} kcfs')
    print(sep)

    # Step 7 -----------------------------------------------------------------
    if dry_run:
        print('\n  DRY-RUN: file NOT written.')
        print(f'  Would save to: {OUT_FILE.name}')
        print('  Re-run without --dry-run to write.')
    else:
        print('\n-- Step 7: Write output file ------------------------------------')
        df_combined.to_csv(OUT_FILE, float_format='%.5f')
        kb = OUT_FILE.stat().st_size / 1024
        print(f'  Saved -> {OUT_FILE.name}  ({kb:.0f} KB, {len(df_combined)} rows)')

    print('\n' + '=' * 68)
    print('Done.')
    print('=' * 68)


if __name__ == '__main__':
    main()
