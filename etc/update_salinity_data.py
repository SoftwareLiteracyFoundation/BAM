#!/usr/bin/env python3
"""
update_salinity_data.py
Extend BAM daily salinity file from 2016-12-31 to 2026-04-30 (WY2026).

Data source:
  TEF04 MySQL hydrology database
    datatype : 'salinity'
    units    : ppt (practical salinity units)
  Sub-daily resolution; aggregated to daily means (AVG per station per day).
  20 of 22 columns are sourced from the DB.

Gulf_1 and Ocean_1 boundary columns:
  These two columns are NOT in the TEF04 DB. They represent open-ocean
  salinity boundary conditions (~34-37 ppt with seasonal variation).
  Method: same-DOY random sampling from the existing 1999-2016 record,
  identical to the gap-fill procedure used for all other missing values.

Gap-filling (all 22 columns):
  Same-day-of-year (DOY) random sampling from the COMBINED 1999-2026 pool
  using numpy.random.default_rng(seed=42). Falls back to same-month pool
  for Feb 29. Applied to any date/station cell with no DB data.

MK salinity:
  Unlike MK stage (offline since Hurricane Irma 2017-09-23), MK salinity
  continues in the DB through 2026. No special treatment required.

Output:
  data/Salinity/DailySalinityFilled_1999-9-1_2026-4-30.csv
  22 columns matching the existing file column order.

Usage:
  python update_salinity_data.py             # full run -- writes output file
  python update_salinity_data.py --dry-run   # stats only -- nothing written

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
EXISTING = DATA_DIR / 'Salinity' / 'DailySalinityFilled_1999-9-1_2016-12-31.csv'
OUT_FILE = DATA_DIR / 'Salinity' / 'DailySalinityFilled_1999-9-1_2026-4-30.csv'

# Stations available in TEF04 DB (must match existing CSV column order)
DB_STATIONS = ['BA','BK','BN','BS','DK','GB','HC','JK','LB','LM',
               'LR','LS','MK','PK','TC','TR','WB','MB','MD','TP']

# Boundary columns derived by same-DOY gap-fill from existing record
DERIVED_COLS = ['Gulf_1', 'Ocean_1']

GAP_FILL_SEED = 42
PLAUSIBLE      = (0.0, 45.0)   # ppt plausible range for annual means
# Sub-daily readings outside this range are treated as sensor malfunction and
# excluded before computing the daily mean. Florida Bay peaks ~70 ppt in
# extreme hypersaline events; 80 ppt is a conservative outlier threshold.
VALID_RANGE    = (0.0, 80.0)   # ppt valid range for raw sub-daily measurements

# ---------------------------------------------------------------------------
# DB fetch
# ---------------------------------------------------------------------------

def fetch_salinity(conn, start, end):
    """
    Fetch daily mean salinity for all DB_STATIONS from TEF04.
    Returns wide DataFrame indexed by Date, one column per station (ppt).
    """
    placeholders = ','.join(['%s'] * len(DB_STATIONS))
    sql = f"""
        SELECT station, measurement_date,
               AVG(measurement_value) AS salinity
        FROM measurement
        WHERE station IN ({placeholders})
          AND datatype = 'salinity'
          AND measurement_value BETWEEN {VALID_RANGE[0]} AND {VALID_RANGE[1]}
          AND measurement_date BETWEEN %s AND %s
        GROUP BY station, measurement_date
        ORDER BY measurement_date, station
    """
    params = DB_STATIONS + [start, end]
    df = pd.read_sql(sql, conn, params=params)
    df['measurement_date'] = pd.to_datetime(df['measurement_date'])
    wide = df.pivot(index='measurement_date', columns='station', values='salinity')
    wide.index.name = 'Date'
    # Ensure all expected columns present
    for col in DB_STATIONS:
        if col not in wide.columns:
            wide[col] = np.nan
    return wide[DB_STATIONS].round(3)

# ---------------------------------------------------------------------------
# Gap-fill
# ---------------------------------------------------------------------------

def gap_fill(df_combined, cols):
    """
    For each column in cols, fill NaN cells using same-DOY random sampling
    from the combined (full-record) pool. Falls back to same-month if the
    DOY pool has no valid values (covers Feb 29).

    df_combined: full combined DataFrame (existing + new, NaNs where missing)
    cols:        list of column names to gap-fill
    Returns a copy of df_combined with NaNs filled.
    """
    rng = np.random.default_rng(GAP_FILL_SEED)
    df_out = df_combined.copy()

    for col in cols:
        missing_idx = df_out[df_out[col].isna()].index
        if len(missing_idx) == 0:
            continue

        # Build DOY lookup from full combined column (non-NaN only)
        valid = df_out[col].dropna()
        doy_map   = {}   # doy -> array of valid values
        month_map = {}   # month -> array of valid values
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
            print(f'    {col:8}: filled {n_filled} of {len(missing_idx)} gaps')

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
    print('\n-- Step 1: Load existing salinity file ---------------------------')
    df_existing = pd.read_csv(EXISTING, parse_dates=['Date'], index_col='Date')
    print(f'  {len(df_existing)} rows  '
          f'{df_existing.index[0].date()} -> {df_existing.index[-1].date()}')
    print(f'  Columns ({len(df_existing.columns)}): {list(df_existing.columns)}')
    existing_na = df_existing.isna().sum().sum()
    print(f'  Existing NaN cells: {existing_na}')

    # Step 2 -----------------------------------------------------------------
    print('\n-- Step 2: Connect to TEF04 MySQL --------------------------------')
    conn = pymysql.connect(**DB)
    print('  Connected.')

    # Step 3 -----------------------------------------------------------------
    print('\n-- Step 3: Fetch salinity from DB --------------------------------')
    print(f'  Pulling {EXTEND_START} -> {EXTEND_END} for {len(DB_STATIONS)} stations ...')
    df_db = fetch_salinity(conn, EXTEND_START, EXTEND_END)
    conn.close()

    full_idx = pd.date_range(EXTEND_START, EXTEND_END, freq='D')
    df_db = df_db.reindex(full_idx)
    n_db_na = df_db.isna().sum().sum()

    print(f'  {len(df_db)} days  '
          f'{df_db.index[0].date()} -> {df_db.index[-1].date()}')
    print(f'  NaN cells before gap-fill: {n_db_na} '
          f'({100*n_db_na/(len(df_db)*len(DB_STATIONS)):.1f}% of DB station-days)')

    # Coverage per station in the new period
    print('\n  Station coverage in extension period (% days with data):')
    for col in DB_STATIONS:
        pct = 100 * df_db[col].notna().sum() / len(df_db)
        flag = '  LOW' if pct < 50 else ''
        print(f'    {col:4}: {pct:5.1f}%{flag}')

    # Add Gulf_1 and Ocean_1 as NaN columns (filled later from existing pool)
    for col in DERIVED_COLS:
        df_db[col] = np.nan

    # Enforce column order to match existing file
    all_cols = list(df_existing.columns)
    df_db = df_db[all_cols]

    # Step 4 -----------------------------------------------------------------
    print('\n-- Step 4: Combine existing + new --------------------------------')
    df_combined = pd.concat([df_existing, df_db])
    df_combined = df_combined[~df_combined.index.duplicated(keep='first')]
    df_combined = df_combined.sort_index()
    print(f'  Combined: {len(df_combined)} rows  '
          f'{df_combined.index[0].date()} -> {df_combined.index[-1].date()}')

    # Step 5 -----------------------------------------------------------------
    print('\n-- Step 5: Gap-fill all columns ----------------------------------')
    # Gap-fill Gulf_1 and Ocean_1 (entirely NaN in new period) plus any DB gaps
    cols_to_fill = all_cols   # all 22 columns
    df_filled = gap_fill(df_combined, cols_to_fill)
    remaining_na = df_filled.isna().sum().sum()
    print(f'  Remaining NaN after gap-fill: {remaining_na}')

    # Step 6 -----------------------------------------------------------------
    print('\n-- Step 6: Summary statistics ------------------------------------')
    sep = '=' * 68
    print('\n' + sep)
    print('1. ANNUAL MEAN SALINITY BY STATION (ppt)')
    print(sep)
    print(f'  {"Stn":8}  {"1999-2016 mean":>14}  {"2017-2026 mean":>14}  {"Delta":>8}')
    for col in all_cols:
        pre  = df_existing[col].resample('YE').mean().mean()
        post = df_db[col].resample('YE').mean().mean()   # raw DB (pre gap-fill)
        if pd.isna(pre) or pd.isna(post):
            print(f'  {col:8}  {"N/A":>14}  {"N/A":>14}')
            continue
        dp = (post - pre) / abs(pre) * 100 if pre != 0 else float('nan')
        print(f'  {col:8}  {pre:>+14.3f}  {post:>+14.3f}  {dp:>+7.1f}%')

    print('\n' + sep)
    print('2. SEAM CHECK -- 7-day mean before/after 2017-01-01')
    print(sep)
    for col in all_cols:
        pre_m  = df_existing[col].iloc[-7:].mean()
        post_m = df_filled[col].loc[EXTEND_START:].iloc[:7].mean()
        print(f'  {col:8}  before={pre_m:+.3f}  after={post_m:+.3f}  '
              f'delta={post_m - pre_m:+.3f}')

    print('\n' + sep)
    print(f'3. SANITY -- annual means (plausible: {PLAUSIBLE[0]}-{PLAUSIBLE[1]} ppt)')
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
        df_filled.to_csv(OUT_FILE, float_format='%.3f')
        kb = OUT_FILE.stat().st_size / 1024
        print(f'  Saved -> {OUT_FILE.name}  ({kb:.0f} KB, {len(df_filled)} rows)')

    print('\n' + '=' * 68)
    print('Done.')
    print('=' * 68)


if __name__ == '__main__':
    main()
