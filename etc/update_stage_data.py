#!/usr/bin/env python3
"""
update_stage_data.py
Extend BAM daily stage file from 2016-12-31 to 2026-04-30 (WY2026).

Data source:
  TEF04 MySQL hydrology database
    datatype : 'stage'
    units    : m (metres, relative to station datum, consistent with
               existing DailyStage file)
  Sub-daily resolution; aggregated to daily means (AVG per station per day).

MK station:
  MK stage is last recorded in the DB on 2017-09-23 (Hurricane Irma caused
  permanent station loss). All MK stage values from 2017-09-24 to 2026-04-30
  are gap-filled by same-DOY random sampling from the combined pool.

Gap-filling:
  Applied where station data is missing. Method: same-DOY random sampling
  from the COMBINED 1999-2026 pool using numpy.random.default_rng(seed=42).
  Falls back to same-month pool for Feb 29.

  Unlike the salinity file (which is named "Filled"), the existing stage file
  does not claim to be fully gap-filled. However, for the extension period,
  gaps are filled to maintain a continuous record. Cells that were NaN in the
  existing file are NOT retroactively filled; only the extension period is
  gap-filled.

Output:
  data/Stage/DailyStage_1999-9-1_2026-4-30.csv
  19 columns matching the existing file column order.

Usage:
  python update_stage_data.py             # full run -- writes output file
  python update_stage_data.py --dry-run   # stats only -- nothing written

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
EXTEND_START = '2017-01-01'
EXTEND_END   = '2026-04-30'

DB = dict(host='127.0.0.1', port=3306,
          user='read_only', password='read_only', database='hydrology')

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
EXISTING = DATA_DIR / 'Stage' / 'DailyStage_1999-9-1_2016-12-31.csv'
OUT_FILE = DATA_DIR / 'Stage' / 'DailyStage_1999-9-1_2026-4-30.csv'

# Column order must match existing file
STATIONS = ['BA','BK','BN','BS','DK','GB','HC','JK','LB','LM',
            'LR','LS','MK','PK','TC','TR','WB','MB','MD']

# MK last known date (Hurricane Irma destroyed station)
MK_LAST_DATE = '2017-09-23'

GAP_FILL_SEED  = 42
PLAUSIBLE      = (-1.0, 1.5)  # m MSL-offset plausible range for annual means

# Unit / datum conversion (applied inside fetch_stage)
#   DB 'stage' datatype: feet, NAVD88
#   BAM file: metres, MSL-offset  (same convention as EDEN runoff stage)
#   MSL_NAVD88 = -0.148 m  =>  output_m = ft * FT_TO_M - MSL_NAVD88
#                            = ft * 0.3048 + 0.148
# Cross-check (Dec 2016 BA): DB -0.596 ft -> -0.034 m (BAM file: -0.011 m, residual 0.023 m)
FT_TO_M        = 0.3048        # feet to metres
MSL_NAVD88     = -0.148        # m; MSL sits at -0.148 m on the NAVD88 scale

# Raw sub-daily readings outside this range (feet) are treated as sentinel /
# sensor errors and excluded before computing the daily mean.
# Covers -99999, -99.99 (missing sentinels) and 299.8 (sensor spike) while
# keeping the entire plausible Florida Bay stage envelope.
VALID_RANGE_FT = (-15.0, 15.0)

# ---------------------------------------------------------------------------
# DB fetch
# ---------------------------------------------------------------------------

def fetch_stage(conn, start, end):
    """
    Fetch daily mean stage for all STATIONS from TEF04.
    Returns wide DataFrame indexed by Date, one column per station (m).
    """
    placeholders = ','.join(['%s'] * len(STATIONS))
    sql = f"""
        SELECT station, measurement_date,
               AVG(measurement_value) AS stage_ft
        FROM measurement
        WHERE station IN ({placeholders})
          AND datatype = 'stage'
          AND measurement_value BETWEEN {VALID_RANGE_FT[0]} AND {VALID_RANGE_FT[1]}
          AND measurement_date BETWEEN %s AND %s
        GROUP BY station, measurement_date
        ORDER BY measurement_date, station
    """
    params = STATIONS + [start, end]
    df = pd.read_sql(sql, conn, params=params)
    df['measurement_date'] = pd.to_datetime(df['measurement_date'])
    # Convert feet NAVD88 -> metres MSL-offset (same convention as EDEN)
    df['stage_m'] = df['stage_ft'] * FT_TO_M - MSL_NAVD88
    wide = df.pivot(index='measurement_date', columns='station', values='stage_m')
    wide.index.name = 'Date'
    for col in STATIONS:
        if col not in wide.columns:
            wide[col] = np.nan
    return wide[STATIONS].round(3)

# ---------------------------------------------------------------------------
# Gap-fill
# ---------------------------------------------------------------------------

def gap_fill(df_combined, cols, existing_end):
    """
    For each column in cols, fill NaN cells in the EXTENSION PERIOD ONLY
    (after existing_end) using same-DOY random sampling from the combined
    (full-record) pool. Does not backfill NaNs in the existing file.

    Falls back to same-month pool for Feb 29.

    df_combined : full combined DataFrame (existing + new)
    cols        : list of column names to gap-fill
    existing_end: Timestamp; only fill dates strictly after this date
    Returns a copy of df_combined with extension-period NaNs filled.
    """
    rng = np.random.default_rng(GAP_FILL_SEED)
    df_out = df_combined.copy()

    for col in cols:
        ext_mask = (df_out.index > existing_end) & df_out[col].isna()
        missing_idx = df_out[ext_mask].index
        if len(missing_idx) == 0:
            continue

        # Build DOY lookup from ENTIRE column (including existing; non-NaN only)
        valid = df_out[col].dropna()
        doy_map   = {}
        month_map = {}
        for dt, val in valid.items():
            d = dt.dayofyear
            m = dt.month
            doy_map.setdefault(d, []).append(val)
            month_map.setdefault(m, []).append(val)

        n_filled = 0
        for dt in missing_idx:
            pool = doy_map.get(dt.dayofyear)
            if not pool:
                pool = month_map.get(dt.month, [])
            if pool:
                df_out.at[dt, col] = round(float(rng.choice(pool)), 3)
                n_filled += 1

        if n_filled:
            print(f'    {col:4}: gap-filled {n_filled} days in extension period')

    return df_out

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
    print('\n-- Step 1: Load existing stage file ------------------------------')
    df_existing = pd.read_csv(EXISTING, parse_dates=['Date'], index_col='Date')
    print(f'  {len(df_existing)} rows  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}')
    print(f'  Columns ({len(df_existing.columns)}): {list(df_existing.columns)}')
    existing_na = df_existing.isna().sum().sum()
    print(f'  Existing NaN cells: {existing_na}')
    existing_end = df_existing.index[-1]

    # Step 2 -----------------------------------------------------------------
    print('\n-- Step 2: Connect to TEF04 MySQL --------------------------------')
    conn = pymysql.connect(**DB)
    print('  Connected.')

    # Step 3 -----------------------------------------------------------------
    print('\n-- Step 3: Fetch stage from DB -----------------------------------')
    print(f'  Pulling {EXTEND_START} -> {EXTEND_END} for {len(STATIONS)} stations ...')
    df_db = fetch_stage(conn, EXTEND_START, EXTEND_END)
    conn.close()

    full_idx = pd.date_range(EXTEND_START, EXTEND_END, freq='D')
    df_db = df_db.reindex(full_idx)
    n_db_na = df_db.isna().sum().sum()

    print(f'  {len(df_db)} days  '
          f'{df_db.index[0].date()} -> {df_db.index[-1].date()}')
    print(f'  NaN cells before gap-fill: {n_db_na} '
          f'({100*n_db_na/(len(df_db)*len(STATIONS)):.1f}% of station-days)')

    # Per-station coverage
    print('\n  Station coverage in extension period (% days with DB data):')
    for col in STATIONS:
        pct = 100 * df_db[col].notna().sum() / len(df_db)
        flag = '  <<-- MK (Hurricane Irma)' if col == 'MK' and pct < 50 else (
               '  LOW' if pct < 50 else '')
        print(f'    {col:4}: {pct:5.1f}%{flag}')

    # Enforce column order
    df_db = df_db[STATIONS]

    # Step 4 -----------------------------------------------------------------
    print('\n-- Step 4: Combine existing + new --------------------------------')
    df_combined = pd.concat([df_existing, df_db])
    df_combined = df_combined[~df_combined.index.duplicated(keep='first')]
    df_combined = df_combined.sort_index()
    print(f'  Combined: {len(df_combined)} rows  '
          f'{df_combined.index[0].date()} -> {df_combined.index[-1].date()}')

    # Step 5 -----------------------------------------------------------------
    print('\n-- Step 5: Gap-fill extension period NaNs ------------------------')
    print('  (Existing file NaNs are preserved; only extension gaps filled)')
    df_filled = gap_fill(df_combined, STATIONS, existing_end)
    ext_remaining_na = df_filled.loc[EXTEND_START:].isna().sum().sum()
    total_remaining_na = df_filled.isna().sum().sum()
    print(f'  Remaining NaN in extension period: {ext_remaining_na}')
    print(f'  Total NaN in combined file: {total_remaining_na} '
          f'(includes {existing_na} pre-existing NaNs)')

    # Step 6 -----------------------------------------------------------------
    print('\n-- Step 6: Summary statistics ------------------------------------')
    sep = '=' * 68
    print('\n' + sep)
    print('1. ANNUAL MEAN STAGE BY STATION (m)')
    print(sep)
    print(f'  {"Stn":4}  {"1999-2016 mean":>14}  {"2017-2026 mean":>14}  {"Delta":>8}')
    for col in STATIONS:
        pre  = df_existing[col].resample('YE').mean().mean()
        post = df_db[col].resample('YE').mean().mean()
        if pd.isna(pre) or pd.isna(post):
            print(f'  {col:4}  {"N/A":>14}  {"N/A":>14}  (insufficient data)')
            continue
        dp = (post - pre) / abs(pre) * 100 if pre != 0 else float('nan')
        print(f'  {col:4}  {pre:>+14.3f}  {post:>+14.3f}  {dp:>+7.1f}%')

    print('\n' + sep)
    print('2. SEAM CHECK -- 7-day mean before/after 2017-01-01')
    print(sep)
    for col in STATIONS:
        pre_m  = df_existing[col].iloc[-7:].mean()
        post_m = df_filled[col].loc[EXTEND_START:].iloc[:7].mean()
        if pd.isna(pre_m) or pd.isna(post_m):
            print(f'  {col:4}  (insufficient data for seam check)')
            continue
        print(f'  {col:4}  before={pre_m:+.3f} m  after={post_m:+.3f} m  '
              f'delta={post_m - pre_m:+.3f} m')

    print('\n' + sep)
    print(f'3. SANITY -- annual means (plausible: {PLAUSIBLE[0]} to {PLAUSIBLE[1]} m)')
    print(sep)
    ann = df_filled.resample('YE').mean()
    bad = ann[(ann < PLAUSIBLE[0]) | (ann > PLAUSIBLE[1])].dropna(how='all')
    if bad.empty:
        print('  All annual station-means within plausible range.')
    else:
        print('  WARNING -- out-of-range values:')
        print(bad.round(3).to_string())

    print('\n' + sep)
    print('4. ROW COUNT')
    print(sep)
    print(f'  Existing : {len(df_existing):5d}  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}')
    print(f'  New      : {len(df_db):5d}  '
          f'{df_db.index[0].date()} -> {df_db.index[-1].date()}')
    print(f'  Combined : {len(df_filled):5d}  '
          f'{df_filled.index[0].date()} -> {df_filled.index[-1].date()}')
    print(sep)

    # Step 7 -----------------------------------------------------------------
    if dry_run:
        print('\n  DRY-RUN: file NOT written.')
        print(f'  Would save to: {OUT_FILE.name}')
        print('  Re-run without --dry-run to write.')
    else:
        print('\n-- Step 7: Write output file ------------------------------------')
        df_filled.to_csv(OUT_FILE, float_format='%.3f', na_rep='NA')
        kb = OUT_FILE.stat().st_size / 1024
        print(f'  Saved -> {OUT_FILE.name}  ({kb:.0f} KB, {len(df_filled)} rows)')

    print('\n' + '=' * 68)
    print('Done.')
    print('=' * 68)


if __name__ == '__main__':
    main()
