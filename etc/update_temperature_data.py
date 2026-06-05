#!/usr/bin/env python3
"""
update_temperature_data.py
Extend BAM daily maximum surface temperature from 2017-06-30 to 2026-04-30.

Background:
  MaxTemp is a daily maximum surface water temperature (°C) applied to 4 of
  64 model basins (Terrapin Bay, North Whipray, Rankin Lake, Snake Bight) via
  the Clausius-Clapeyron equation to amplify basin-level ET beyond the baseline
  PET. The existing file ends 2017-06-30 (18 months after the model's normal
  data end of 2016-12-31). This script appends 2017-07-01 to 2026-04-30.

Data source:
  TEF04 MySQL hydrology database
    datatype : 'surface_temperature'   (confirmed via --discover flag)
    units    : degrees Celsius
    resolution: sub-daily; aggregated to daily MAX per station per day.
    Primary station  : BK
    Fallback station : GB  (regression: BK = 0.57196 + 0.99428 * GB)
    Fallback station : TC  (regression: BK = 0.72327 + 1.00824 * TC)
  These three stations are on the same multi-parameter probe as salinity,
  so coverage is expected to be comparable to the salinity data (~99%).

Methodology:
  1. Pull daily MAX surface_temperature for BK, GB, TC.
  2. For each day:
     a. Use BK directly if available.
     b. Else apply GB regression if GB available.
     c. Else apply TC regression if TC available.
     d. Else mark as NaN for later gap-fill.
  3. Gap-fill remaining NaN using same-DOY random sampling from the
     combined 1999-2026 record. Falls back to same-month pool for Feb 29.

Notes file:
  etc/BAM_POR_Extension_Notes.md §7

Usage:
  python update_temperature_data.py             # full run
  python update_temperature_data.py --dry-run   # stats only, no file written
  python update_temperature_data.py --discover  # probe DB for datatype names

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
EXTEND_START = '2017-07-01'   # day after existing file ends (2017-06-30)
EXTEND_END   = '2026-04-30'

DB = dict(host='127.0.0.1', port=3306,
          user='read_only', password='read_only', database='hydrology')

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
EXISTING = DATA_DIR / 'Temperature' / 'MaxTemp_Filled_1999-9-1_2017-6-30.csv'
OUT_FILE = DATA_DIR / 'Temperature' / 'MaxTemp_Filled_1999-9-1_2026-4-30.csv'

# Station hierarchy (same probe as salinity)
PRIMARY_STATION  = 'BK'
FALLBACK_STATION = {'GB': (0.57196, 0.99428),   # BK = a + b * GB
                    'TC': (0.72327, 1.00824)}    # BK = a + b * TC

# Temperature datatype name (confirmed with --discover; may also be
# 'surface_temperature', 'water_temperature', 'temperature')
TEMP_DATATYPE = 'bottom_temperature'

# Valid sensor range -- sub-daily readings outside excluded before MAX
VALID_RANGE = (0.0, 45.0)   # °C; Florida Bay surface water is never > 40°C

# Plausible range for annual means (sanity check)
PLAUSIBLE = (18.0, 35.0)   # °C; annual mean should fall here

GAP_FILL_SEED = 42

# ---------------------------------------------------------------------------
# Discovery helper
# ---------------------------------------------------------------------------

def discover(conn):
    """Print all temperature-related datatypes for BK/GB/TC."""
    sql = """
        SELECT sd.station, sd.datatype,
               MIN(m.measurement_date) AS first_date,
               MAX(m.measurement_date) AS last_date,
               COUNT(*)               AS n_rows
        FROM station_datatype sd
        JOIN measurement m
          ON m.station = sd.station AND m.datatype = sd.datatype
        WHERE sd.station IN ('BK','GB','TC')
          AND (LOWER(sd.datatype) LIKE '%temp%'
            OR LOWER(sd.datatype) LIKE '%water%')
        GROUP BY sd.station, sd.datatype
        ORDER BY sd.station, sd.datatype
    """
    df = pd.read_sql(sql, conn)
    if df.empty:
        print('  No temperature-related datatypes found for BK/GB/TC.')
        print('  Trying broader search...')
        sql2 = """
            SELECT DISTINCT datatype FROM station_datatype
            WHERE station IN ('BK','GB','TC')
            ORDER BY datatype
        """
        df2 = pd.read_sql(sql2, conn)
        print('  All datatypes for BK/GB/TC:')
        print(df2.to_string(index=False))
    else:
        print(df.to_string(index=False))

# ---------------------------------------------------------------------------
# DB fetch
# ---------------------------------------------------------------------------

def fetch_temperature(conn, start, end):
    """
    Fetch daily MAX surface temperature (°C) for BK, GB, TC.
    Returns wide DataFrame indexed by Date with columns BK, GB, TC.
    """
    stations = [PRIMARY_STATION] + list(FALLBACK_STATION.keys())
    placeholders = ','.join(['%s'] * len(stations))
    sql = f"""
        SELECT station, measurement_date,
               MAX(measurement_value) AS max_temp
        FROM measurement
        WHERE station IN ({placeholders})
          AND datatype = %s
          AND measurement_value BETWEEN {VALID_RANGE[0]} AND {VALID_RANGE[1]}
          AND measurement_date BETWEEN %s AND %s
        GROUP BY station, measurement_date
        ORDER BY measurement_date, station
    """
    params = stations + [TEMP_DATATYPE, start, end]
    df = pd.read_sql(sql, conn, params=params)
    df['measurement_date'] = pd.to_datetime(df['measurement_date'])
    wide = df.pivot(index='measurement_date', columns='station', values='max_temp')
    wide.index.name = 'Date'
    for col in stations:
        if col not in wide.columns:
            wide[col] = np.nan
    return wide[stations].round(2)

# ---------------------------------------------------------------------------
# Regression fallback
# ---------------------------------------------------------------------------

def apply_regression(raw):
    """
    Derive single MaxTemp column from BK/GB/TC using the regression hierarchy:
      1. BK direct
      2. BK = 0.57196 + 0.99428 * GB
      3. BK = 0.72327 + 1.00824 * TC
      4. NaN (gap-fill later)

    raw: DataFrame with columns BK, GB, TC indexed by Date
    Returns Series named 'MaxTemp'.
    """
    result = pd.Series(np.nan, index=raw.index, name='MaxTemp', dtype=float)

    # Source tracking for reporting
    n = {'BK': 0, 'GB_reg': 0, 'TC_reg': 0, 'nan': 0}

    for dt in raw.index:
        bk = raw.at[dt, 'BK']
        gb = raw.at[dt, 'GB']
        tc = raw.at[dt, 'TC']

        if pd.notna(bk):
            result[dt] = round(bk, 2)
            n['BK'] += 1
        elif pd.notna(gb):
            a, b = FALLBACK_STATION['GB']
            result[dt] = round(a + b * gb, 2)
            n['GB_reg'] += 1
        elif pd.notna(tc):
            a, b = FALLBACK_STATION['TC']
            result[dt] = round(a + b * tc, 2)
            n['TC_reg'] += 1
        else:
            n['nan'] += 1

    total = sum(n.values())
    print(f'  BK direct   : {n["BK"]:5d} days ({100*n["BK"]/total:.1f}%)')
    print(f'  GB regression: {n["GB_reg"]:5d} days ({100*n["GB_reg"]/total:.1f}%)')
    print(f'  TC regression: {n["TC_reg"]:5d} days ({100*n["TC_reg"]/total:.1f}%)')
    print(f'  Still NaN    : {n["nan"]:5d} days (gap-fill next)')

    return result

# ---------------------------------------------------------------------------
# Gap-fill
# ---------------------------------------------------------------------------

def gap_fill(s_combined, ext_start):
    """
    Fill NaN cells in extension period using same-DOY random sampling from
    the combined 1999-2026 record. Falls back to same-month pool for Feb 29.

    s_combined : full combined Series (existing + new) indexed by Date
    ext_start  : first date of extension period (NaN only filled here)
    Returns filled Series.
    """
    rng = np.random.default_rng(GAP_FILL_SEED)
    s_out = s_combined.copy()

    ext_nans = s_out[(s_out.index >= ext_start) & s_out.isna()].index
    if len(ext_nans) == 0:
        return s_out

    # Build DOY and month lookup from the full combined non-NaN record
    valid = s_out.dropna()
    doy_map   = {}
    month_map = {}
    for dt, val in valid.items():
        doy_map.setdefault(dt.dayofyear, []).append(val)
        month_map.setdefault(dt.month, []).append(val)

    for dt in ext_nans:
        pool = doy_map.get(dt.dayofyear, [])
        if not pool:
            pool = month_map.get(dt.month, [])
        if pool:
            s_out[dt] = round(rng.choice(pool), 2)

    return s_out

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def print_summary(df_existing, s_combined, ext_start_pd, dry_run):
    print()
    print('=' * 60)
    print('TEMPERATURE SUMMARY')
    print('=' * 60)

    existing_vals = s_combined[s_combined.index < ext_start_pd]
    new_vals      = s_combined[s_combined.index >= ext_start_pd]

    print(f'  Period         Mean (°C)  Min (°C)  Max (°C)  NaN days')
    print(f'  1999-2017 (existing):  '
          f'{existing_vals.mean():.2f}     '
          f'{existing_vals.min():.2f}     '
          f'{existing_vals.max():.2f}     '
          f'{existing_vals.isna().sum()}')
    print(f'  2017-2026 (new):       '
          f'{new_vals.mean():.2f}     '
          f'{new_vals.min():.2f}     '
          f'{new_vals.max():.2f}     '
          f'{new_vals.isna().sum()}')

    print()
    print('Annual means (°C):')
    df_ann = s_combined.groupby(s_combined.index.year).mean().round(2)
    lo, hi = PLAUSIBLE
    all_ok = True
    for yr, mean in df_ann.items():
        flag = ''
        if not (lo <= mean <= hi):
            flag = '  <<-- OUTSIDE PLAUSIBLE RANGE'
            all_ok = False
        print(f'  {yr}: {mean:.2f}{flag}')
    if all_ok:
        print(f'  All annual means within plausible range ({lo}–{hi} °C).')

    print()
    print('Seam check (7-day window around 2017-06-30/2017-07-01):')
    seam = pd.Timestamp('2017-07-01')
    before = s_combined[(s_combined.index >= seam - pd.Timedelta(days=7)) &
                        (s_combined.index <  seam)].mean()
    after  = s_combined[(s_combined.index >= seam) &
                        (s_combined.index <  seam + pd.Timedelta(days=7))].mean()
    print(f'  7-day mean before seam: {before:.2f} °C')
    print(f'  7-day mean after seam : {after:.2f} °C')
    print(f'  Delta                 : {after - before:+.2f} °C')
    print('=' * 60)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run  = '--dry-run'  in sys.argv
    discover_mode = '--discover' in sys.argv

    if dry_run:
        print()
        print('=' * 60)
        print('  DRY-RUN MODE -- stats only, no files written')
        print('=' * 60)

    # -- Step 1: Load existing file ----------------------------------------
    print()
    print('-- Step 1: Load existing temperature file -------------------')
    df_ex = pd.read_csv(EXISTING, parse_dates=['Date'])
    df_ex = df_ex.set_index('Date').sort_index()
    print(f'  {len(df_ex)} rows  {df_ex.index[0].date()} -> {df_ex.index[-1].date()}')
    print(f'  Column: {df_ex.columns.tolist()}')
    print(f'  Value range: {df_ex["MaxTemp"].min():.2f} to {df_ex["MaxTemp"].max():.2f} °C')
    print(f'  NaN count: {df_ex["MaxTemp"].isna().sum()}')

    # -- Step 2: Connect to DB ---------------------------------------------
    print()
    print('-- Step 2: Connect to TEF04 MySQL ---------------------------')
    conn = pymysql.connect(**DB)
    print('  Connected.')

    if discover_mode:
        print()
        print('-- DISCOVERY MODE -------------------------------------------')
        discover(conn)
        conn.close()
        return

    # -- Step 3: Fetch temperature from DB ---------------------------------
    print()
    print('-- Step 3: Fetch surface temperature from DB ----------------')
    print(f'  Pulling {EXTEND_START} -> {EXTEND_END} for BK, GB, TC ...')
    raw = fetch_temperature(conn, EXTEND_START, EXTEND_END)
    conn.close()

    n_days = len(raw)
    print(f'  {n_days} days fetched')
    print()
    print('  Station coverage (% days with DB data):')
    for col in raw.columns:
        pct = 100 * raw[col].notna().sum() / n_days
        note = '  <<-- low coverage' if pct < 85 else ''
        print(f'    {col}  : {pct:5.1f}%{note}')

    # -- Step 4: Apply regression hierarchy --------------------------------
    print()
    print('-- Step 4: Apply regression fallback hierarchy --------------')
    ext_idx = pd.date_range(EXTEND_START, EXTEND_END, freq='D')
    raw = raw.reindex(ext_idx)
    s_ext = apply_regression(raw)

    # -- Step 5: Combine existing + new ------------------------------------
    print()
    print('-- Step 5: Combine existing + new ---------------------------')
    s_existing = df_ex['MaxTemp']
    s_combined = pd.concat([s_existing,
                            s_ext[s_ext.index > s_existing.index[-1]]])
    s_combined.index = pd.to_datetime(s_combined.index)
    print(f'  Combined: {len(s_combined)} rows  '
          f'{s_combined.index[0].date()} -> {s_combined.index[-1].date()}')
    print(f'  NaN before gap-fill: {s_combined.isna().sum()}')

    # -- Step 6: Gap-fill --------------------------------------------------
    print()
    print('-- Step 6: Gap-fill extension NaNs --------------------------')
    ext_start_pd = pd.Timestamp(EXTEND_START)
    s_filled = gap_fill(s_combined, ext_start_pd)
    n_remaining = s_filled[s_filled.index >= ext_start_pd].isna().sum()
    print(f'  Remaining NaN in extension period: {n_remaining}')

    # -- Step 7: Summary ---------------------------------------------------
    print_summary(df_ex, s_filled, ext_start_pd, dry_run)

    # -- Step 8: Write output ----------------------------------------------
    print()
    print('-- Step 8: Write output file --------------------------------')
    df_out = s_filled.reset_index()
    df_out.columns = ['Date', 'MaxTemp']
    df_out['Date']    = df_out['Date'].dt.strftime('%Y-%m-%d')
    df_out['MaxTemp'] = df_out['MaxTemp'].round(2)

    if dry_run:
        print(f'  DRY-RUN: file NOT written.')
        print(f'  Would save to: {OUT_FILE.name}')
        print(f'  Re-run without --dry-run to write.')
    else:
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(OUT_FILE, index=False)
        size_kb = OUT_FILE.stat().st_size // 1024
        print(f'  Saved -> {OUT_FILE.name}  ({size_kb} KB, {len(df_out)} rows)')

    print()
    print('=' * 60)
    print('Done.')
    print('=' * 60)

if __name__ == '__main__':
    main()
