#!/usr/bin/env python3
"""
update_rain_data.py
Extend BAM rainfall input file from 2016-12-31 to 2026-04-30 (end of WY2026).

Workflow:
  1. Load existing 1999-2016 gap-filled file (kept as-is)
  2. Discover rainfall datatype at ENP stations in TEF04 MySQL
  3. Query MySQL (via PuTTY tunnel 127.0.0.1:3306) for 2017-01-01 to 2026-04-30
  4. Convert sub-daily in/hr readings to cm/day
  5. Append to existing dataset
  6. Gap-fill NaNs by same-DOY random sampling from full 1999-2026 pool
  7. Save new file  (skipped in --dry-run mode)
  8. Print summary statistics comparing old vs new period

Usage:
  python update_rain_data.py             # full run -- writes output file
  python update_rain_data.py --dry-run   # stats only -- nothing written to disk

Requirements: pip install pymysql pandas numpy
Run with PuTTY SSH tunnel active (L3306 -> TEF04:3306).
"""

import sys
import numpy as np
import pandas as pd
import pymysql
from pathlib import Path

# -- Configuration -------------------------------------------------------------
DB_HOST  = '127.0.0.1'
DB_PORT  = 3306
DB_USER  = 'read_only'
DB_PASS  = 'read_only'
DB_NAME  = 'hydrology'

STATIONS = ['BK','BA','BN','BS','DK','GB','HC','JK',
            'LB','LM','LR','LS','MK','PK','TC','TR','WB']

EXTEND_START = '2017-01-01'
EXTEND_END   = '2026-04-30'
CM_PER_IN    = 2.54

DATA_DIR     = Path(__file__).resolve().parent.parent / 'data' / 'Rain'
EXISTING     = DATA_DIR / 'DailyRainFilled_cm_1999-9-1_2016-12-31.csv'
OUT_FILE     = DATA_DIR / 'DailyRainFilled_cm_1999-9-1_2026-4-30.csv'
# ------------------------------------------------------------------------------

ANNUAL_PLAUSIBLE = (40, 250)   # cm/yr sanity bounds for Florida Bay rainfall


def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME, autocommit=True
    )


def discover_datatype(conn, sample_station='BK'):
    """Return the rainfall datatype name available at a given station."""
    sql = "SELECT datatype FROM station_datatype WHERE station = %s ORDER BY datatype"
    df  = pd.read_sql(sql, conn, params=[sample_station])
    candidates = [dt for dt in df['datatype'] if any(k in dt.lower() for k in ('rain', 'precip'))]
    if not candidates:
        print("  Available datatypes at %s: %s" % (sample_station, df['datatype'].tolist()))
        raise RuntimeError("No rainfall datatype found at station %s. "
                           "Set RAIN_DATATYPE manually." % sample_station)
    print("  Rainfall datatype detected: '%s'  (all candidates: %s)"
          % (candidates[0], candidates))
    return candidates[0]


def fetch_raw(conn, datatype):
    """
    Pull daily-aggregated readings for all 17 stations.
    Returns columns: measurement_date, station, sum_val, n_readings
    Aggregating in SQL avoids pulling millions of sub-daily rows.
    """
    stn_placeholders = ','.join(['%s'] * len(STATIONS))
    sql = """
        SELECT
            measurement_date,
            station,
            SUM(measurement_value)  AS sum_val,
            COUNT(*)                AS n_readings
        FROM measurement
        WHERE station  IN (%s)
          AND datatype  = %%s
          AND measurement_date BETWEEN %%s AND %%s
          AND measurement_value IS NOT NULL
          AND measurement_value >= 0
        GROUP BY measurement_date, station
        ORDER BY measurement_date, station
    """ % stn_placeholders
    params = STATIONS + [datatype, EXTEND_START, EXTEND_END]
    print("  Querying MySQL for '%s'  %s -> %s ..." % (datatype, EXTEND_START, EXTEND_END))
    df = pd.read_sql(sql, conn, params=params, parse_dates=['measurement_date'])
    print("  -> %s station-day records returned" % "{:,}".format(len(df)))
    return df


def infer_interval_hours(df_raw):
    """
    Determine hours per sub-daily interval from the mode of n_readings across
    all station-day records.  E.g. mode=96 -> 15-min intervals -> 0.25 hr each.
    """
    mode_n = int(df_raw['n_readings'].mode()[0])
    hrs    = 24.0 / mode_n
    print("  Mode readings/day = %d  ->  %.4f hr/interval  (range: %d-%d)"
          % (mode_n, hrs, df_raw['n_readings'].min(), df_raw['n_readings'].max()))
    return hrs


def to_daily_cm(df_raw):
    """
    Convert sum_val (in/hr x n_intervals) to cm/day.
      daily_cm = sum_val x hours_per_interval x CM_PER_IN
    Returns wide DataFrame indexed by date, columns = station codes.
    """
    hrs = infer_interval_hours(df_raw)
    df  = df_raw.copy()
    df['daily_cm'] = df['sum_val'] * hrs * CM_PER_IN

    wide = df.pivot(index='measurement_date', columns='station', values='daily_cm')
    wide.index.name = 'date'
    wide = wide.reindex(columns=STATIONS)   # enforce column order

    full_idx = pd.date_range(EXTEND_START, EXTEND_END, freq='D')
    wide = wide.reindex(full_idx)
    wide.index.name = 'date'
    return wide


def load_existing():
    """Load existing gap-filled 1999-2016 CSV; return with station-code columns."""
    df = pd.read_csv(EXISTING, parse_dates=['date'], index_col='date')
    df.columns = [c.split('_')[0] for c in df.columns]   # 'BK_cm_day' -> 'BK'
    print("  Loaded existing: %s -> %s  (%d days, %d NaNs)"
          % (df.index[0].date(), df.index[-1].date(), len(df), df.isna().sum().sum()))
    return df


def build_mk_proxy(df_existing, df_new_cm):
    """
    Build a regression-based proxy for MK station post-2017 using JK as predictor.

    MK was destroyed by a hurricane and has ~8% data coverage after 2017.
    JK is the nearest suitable station with continuous coverage.

    Two regressions are fitted on the 1999-2016 overlap period and reported:
      - All-day:  includes zero-rain days (dominates fit but may under-predict peaks)
      - Wet-day:  both stations > WET_THRESHOLD cm/day

    The all-day regression is applied to produce the proxy, with results capped >= 0.
    Falls back to 0.0 only on days where JK is also missing.

    Returns:
      df_new_filled : df_new_cm with MK NaNs replaced by proxy values
      stats         : dict of regression diagnostics for the summary report
    """
    from scipy import stats as _stats

    WET_THRESHOLD = 0.05   # cm/day -- below this both stations treated as dry

    print("\n  Building MK proxy from JK (1999-2016 training period)...")

    mk_train = df_existing['MK']
    jk_train = df_existing['JK']

    # ---- All-day regression (including zero-rain days) ----------------------
    mask_all = mk_train.notna() & jk_train.notna()
    jk_all   = jk_train[mask_all].values
    mk_all   = mk_train[mask_all].values
    sl_all, ic_all, r_all, _, _ = _stats.linregress(jk_all, mk_all)
    r2_all   = r_all ** 2

    # Residual RMSE
    pred_all = sl_all * jk_all + ic_all
    rmse_all = float(np.sqrt(np.mean((mk_all - pred_all) ** 2)))

    # ---- Wet-day regression (both stations above threshold) -----------------
    mask_wet = mask_all & (jk_train > WET_THRESHOLD) & (mk_train > WET_THRESHOLD)
    n_wet    = int(mask_wet.sum())
    if n_wet >= 20:
        jk_wet  = jk_train[mask_wet].values
        mk_wet  = mk_train[mask_wet].values
        sl_wet, ic_wet, r_wet, _, _ = _stats.linregress(jk_wet, mk_wet)
        r2_wet   = r_wet ** 2
        pred_wet = sl_wet * jk_wet + ic_wet
        rmse_wet = float(np.sqrt(np.mean((mk_wet - pred_wet) ** 2)))
    else:
        sl_wet = ic_wet = r2_wet = rmse_wet = None

    # ---- Print regression diagnostics ---------------------------------------
    print("  All-day  regression (n=%d): MK = %.4f * JK + %.4f  "
          "R2=%.3f  RMSE=%.3f cm/day"
          % (int(mask_all.sum()), sl_all, ic_all, r2_all, rmse_all))
    if r2_wet is not None:
        print("  Wet-day  regression (n=%d): MK = %.4f * JK + %.4f  "
              "R2=%.3f  RMSE=%.3f cm/day"
              % (n_wet, sl_wet, ic_wet, r2_wet, rmse_wet))
    else:
        print("  Wet-day regression skipped (too few co-wet days).")

    # ---- 1999-2016 cross-check: proxy vs observed annual MK total -----------
    mk_obs_annual  = mk_train.resample('YE').sum().mean()
    mk_prox_annual = np.maximum(0, sl_all * jk_train + ic_all).resample('YE').sum().mean()
    print("  Training-period check: observed MK mean = %.1f cm/yr  "
          "proxy mean = %.1f cm/yr  (bias = %+.1f%%)"
          % (mk_obs_annual, mk_prox_annual,
             (mk_prox_annual - mk_obs_annual) / mk_obs_annual * 100))

    # ---- Apply proxy to post-2017 MK gaps -----------------------------------
    jk_new  = df_new_cm['JK']
    mk_new  = df_new_cm['MK'].copy()
    missing = mk_new.isna()

    # Regression-based proxy where JK is available
    jk_avail = missing & jk_new.notna()
    mk_new[jk_avail] = np.maximum(0.0, sl_all * jk_new[jk_avail] + ic_all)

    # Zero fallback where JK is also missing
    still_missing = mk_new.isna()
    mk_new[still_missing] = 0.0

    n_proxied  = int(jk_avail.sum())
    n_fallback = int(still_missing.sum())
    n_observed = int((~missing).sum())
    print("  Post-2017 MK:  %d days observed,  %d days proxy (JK regression),  "
          "%d days zero-fallback (JK also missing)"
          % (n_observed, n_proxied, n_fallback))

    df_out      = df_new_cm.copy()
    df_out['MK'] = mk_new

    proxy_stats = {
        'sl_all': sl_all, 'ic_all': ic_all, 'r2_all': r2_all, 'rmse_all': rmse_all,
        'sl_wet': sl_wet, 'ic_wet': ic_wet, 'r2_wet': r2_wet, 'rmse_wet': rmse_wet,
        'n_wet': n_wet, 'n_observed': n_observed, 'n_proxied': n_proxied,
        'n_fallback': n_fallback, 'training_bias_pct': (mk_prox_annual - mk_obs_annual) / mk_obs_annual * 100,
    }
    return df_out, proxy_stats


def gap_fill(df_combined):
    """
    Fill NaNs by sampling uniformly from the same (month, day) across all
    available (non-NaN) years in the full 1999-2026 dataset.
    Falls back to same-month pool if Feb-29 pool is too small.
    """
    filled       = df_combined.copy()
    total_before = int(filled.isna().sum().sum())
    print("\n  Gap-filling %s station-day NaNs ..." % "{:,}".format(total_before))

    rng = np.random.default_rng(seed=42)

    for col in filled.columns:
        series  = filled[col]
        nan_idx = series[series.isna()].index
        if nan_idx.empty:
            continue
        for ts in nan_idx:
            m, d  = ts.month, ts.day
            pool  = series[(series.index.month == m) & (series.index.day == d) & series.notna()]
            if len(pool) < 2:
                pool = series[(series.index.month == m) & series.notna()]
            filled.at[ts, col] = float(rng.choice(pool.values)) if not pool.empty else 0.0

    remaining = int(filled.isna().sum().sum())
    print("  Done. Remaining NaNs after fill: %d" % remaining)
    return filled


def print_summary(df_existing, df_new_raw, df_filled, proxy_stats=None):
    """
    Print:
      1. Raw data coverage for new period (% days with at least one reading)
      2. Per-station annual mean cm/yr: 1999-2016 vs 2017-2026, delta
      3. Monthly climatology comparison (mean cm/month, averaged across stations)
      4. Sanity check: flag stations where new-period mean deviates >25% from old
    """
    sep = "=" * 72

    # -- 1. Raw coverage -------------------------------------------------------
    print("\n" + sep)
    print("1. RAW DATA COVERAGE -- new period 2017-01-01 to 2026-04-30")
    print(sep)
    n_days = len(df_new_raw)
    cov    = (df_new_raw.notna().sum() / n_days * 100).rename('pct_days_with_data')
    print(cov.round(1).to_string())
    print("\n   (%d total days in new period)" % n_days)

    # -- 2. Annual means -------------------------------------------------------
    print("\n" + sep)
    print("2. ANNUAL MEAN RAINFALL (cm/yr) -- per station")
    print(sep)
    annual = df_filled.resample('YE').sum()
    pre    = annual[annual.index.year <= 2016].mean()
    post   = annual[annual.index.year >= 2017].mean()
    delta  = post - pre
    pct    = (delta / pre * 100)

    stat_df = pd.DataFrame({
        'WY1999-2016_mean': pre,
        'WY2017-2026_mean': post,
        'Delta_cm'        : delta,
        'Delta_pct'       : pct,
    })
    print(stat_df.round(1).to_string())

    # -- 3. Monthly climatology ------------------------------------------------
    print("\n" + sep)
    print("3. MONTHLY CLIMATOLOGY -- mean cm/month averaged across all 17 stations")
    print(sep)
    df_filled['_mean'] = df_filled.mean(axis=1)
    old_mon = df_filled.loc[:'2016-12-31', '_mean'].groupby(
                  df_filled.loc[:'2016-12-31'].index.month).mean().rename('1999-2016')
    new_mon = df_filled.loc['2017-01-01':, '_mean'].groupby(
                  df_filled.loc['2017-01-01':].index.month).mean().rename('2017-2026')
    old_mon.index = pd.to_datetime(old_mon.index, format='%m').strftime('%b')
    new_mon.index = pd.to_datetime(new_mon.index, format='%m').strftime('%b')
    mon_df = pd.concat([old_mon, new_mon], axis=1)
    mon_df['Delta_pct'] = ((mon_df['2017-2026'] - mon_df['1999-2016']) / mon_df['1999-2016'] * 100)
    print(mon_df.round(2).to_string())
    df_filled.drop(columns=['_mean'], inplace=True)

    # -- 4. Sanity check -------------------------------------------------------
    print("\n" + sep)
    print("4. SANITY CHECKS")
    print(sep)
    flags = pct[pct.abs() > 25]
    if flags.empty:
        print("  All stations within +/-25% of historical mean. No anomalies flagged.")
    else:
        print("  WARNING -- stations deviating >25% from 1999-2016 mean:")
        print(flags.round(1).to_string())

    ann_all = df_filled.mean(axis=1).resample('YE').sum()
    out_of_range = ann_all[(ann_all < ANNUAL_PLAUSIBLE[0]) | (ann_all > ANNUAL_PLAUSIBLE[1])]
    if not out_of_range.empty:
        print("  WARNING -- years outside plausible range %d-%d cm/yr:"
              % ANNUAL_PLAUSIBLE)
        print(out_of_range.round(1).to_string())
    else:
        print("  All annual station-mean totals within plausible range "
              "(%d-%d cm/yr)." % ANNUAL_PLAUSIBLE)

    # -- 5. MK proxy diagnostics (if available) --------------------------------
    if proxy_stats:
        print("\n" + sep)
        print("5. MK PROXY DIAGNOSTICS (JK regression, applied post-2017)")
        print(sep)
        print("  All-day  MK = %.4f * JK + %.4f   R2=%.3f   RMSE=%.3f cm/day"
              % (proxy_stats['sl_all'], proxy_stats['ic_all'],
                 proxy_stats['r2_all'], proxy_stats['rmse_all']))
        if proxy_stats['r2_wet'] is not None:
            print("  Wet-day  MK = %.4f * JK + %.4f   R2=%.3f   RMSE=%.3f cm/day  (n=%d)"
                  % (proxy_stats['sl_wet'], proxy_stats['ic_wet'],
                     proxy_stats['r2_wet'], proxy_stats['rmse_wet'],
                     proxy_stats['n_wet']))
        print("  Training bias: %+.1f%% (proxy vs observed annual mean, 1999-2016)"
              % proxy_stats['training_bias_pct'])
        print("  Post-2017 MK breakdown:  %d observed  |  %d JK-regression  |  %d zero-fallback"
              % (proxy_stats['n_observed'], proxy_stats['n_proxied'], proxy_stats['n_fallback']))
        # MK annual totals in filled dataset
        mk_annual = df_filled['MK'].resample('YE').sum()
        print("\n  MK annual totals in final dataset (cm/yr):")
        print(mk_annual.round(1).to_string())

    print("\n" + sep)
    print("Output file: %s" % OUT_FILE)
    print(sep)


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("\n" + "=" * 72)
        print("  DRY-RUN MODE -- statistics only, nothing written to disk")
        print("=" * 72)

    np.random.seed(42)

    print("\n-- Step 1: Load existing 1999-2016 file ------------------------------")
    df_existing = load_existing()

    print("\n-- Step 2: Connect to TEF04 MySQL ------------------------------------")
    conn     = get_connection()
    datatype = discover_datatype(conn)

    print("\n-- Step 3: Fetch and convert new data --------------------------------")
    df_raw    = fetch_raw(conn, datatype)
    conn.close()
    df_new_cm = to_daily_cm(df_raw)

    # Trim existing to training window before proxy build and append
    df_old_trim = df_existing[df_existing.index <= '2016-12-31'].reindex(columns=STATIONS)

    print("\n-- Step 3b: Build MK proxy from JK regression -----------------------")
    df_new_cm, proxy_stats = build_mk_proxy(df_old_trim, df_new_cm)

    print("\n-- Step 4: Append ----------------------------------------------------")
    df_combined  = pd.concat([df_old_trim, df_new_cm])
    df_combined  = df_combined[~df_combined.index.duplicated(keep='first')].sort_index()
    total_nans   = df_combined.isna().sum().sum()
    print("  Combined: %s -> %s  (%d days,  %s NaNs before fill)"
          % (df_combined.index[0].date(), df_combined.index[-1].date(),
             len(df_combined), "{:,}".format(total_nans)))

    print("\n-- Step 5: Gap-fill --------------------------------------------------")
    df_filled = gap_fill(df_combined)

    print("\n-- Step 6: Summary statistics ----------------------------------------")
    print_summary(df_old_trim, df_new_cm, df_filled, proxy_stats=proxy_stats)

    # Step 7: Save -- skipped in dry-run mode
    if dry_run:
        print("\n  DRY-RUN: output file NOT written.")
        print("  Would save to: %s" % OUT_FILE)
        print("  Re-run without --dry-run to write the file.")
    else:
        print("\n-- Step 7: Save --------------------------------------------------")
        out = df_filled.copy()
        out.columns = ["%s_cm_day" % s for s in out.columns]
        out.index.name = 'date'
        out.to_csv(OUT_FILE, float_format='%.6f')
        print("  Saved -> %s" % OUT_FILE)


if __name__ == '__main__':
    main()
