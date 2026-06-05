#!/usr/bin/env python3
"""
update_msl_data.py
Extend BAM MSL_Anomaly.csv from 2017-09-15 to 2026-04-15.

Data source:
  NOAA CO-OPS API monthly_mean product, datum=NAVD, units=metric
  Three stations (same stations used in original MonthlyMean_1999-9_2017-10.csv):
    Key West     (8724580)  -- Florida Keys SW
    Vaca Key     (8723970)  -- Florida Keys Central
    Virginia Key (8723214)  -- Biscayne Bay NE

Method:
  1. Fetch monthly mean sea level (MSL) in NAVD88 metres from NOAA CO-OPS API.
  2. Compute the 3-station mean MSL_NAVD88.
  3. Anomaly_m = MeanMSL_NAVD88 - MSL_NAVD_EPOCH
     where MSL_NAVD_EPOCH = -0.148 m  (2008-2015 epoch mean MSL in NAVD88)
     i.e., Anomaly_m = MeanMSL_NAVD88 + 0.148

  This matches the existing MSL_Anomaly.csv computation documented in
  etc/MonthlyMean_1999-9_2017-10.csv and etc/MSL_Plot.R.

  Extension starts at 2017-10-15 (MSL_Anomaly.csv already has through 2017-09-15).
  Extension ends   at 2026-04-15 (matching other BAM WY2026 data files).

Output:
  data/Tide/MSL_Anomaly.csv              -- appended in-place
  etc/MonthlyMean_1999-9_2026-4-30.csv   -- new combined raw data file

Usage:
  python update_msl_data.py             # fetch and write
  python update_msl_data.py --dry-run   # print preview, no files written

Requirements: Python 3.6+, no extra packages (uses stdlib urllib, csv only)
"""

import sys
import csv
import io
import time
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STATIONS = [
    ('KeyWest',      '8724580'),   # Key West, FL
    ('VacaKey',      '8723970'),   # Vaca Key, FL
    ('VirginiaKey',  '8723214'),   # Virginia Key, FL
]

# 2008-2015 epoch mean MSL in NAVD88 metres (from MSL_Plot.R / MonthlyMean file)
# Anomaly = MeanMSL_NAVD88 - MSL_NAVD_EPOCH  ==>  MeanMSL_NAVD88 + 0.148
MSL_NAVD_EPOCH = -0.148

EXTEND_FROM = (2017, 10)   # first new month (file already has through 2017-09)
EXTEND_TO   = (2026,  4)   # last new month  (WY2026 end)

DATA_DIR  = Path(__file__).resolve().parent.parent / 'data'
ETC_DIR   = Path(__file__).resolve().parent

ANOMALY_FILE  = DATA_DIR / 'Tide' / 'MSL_Anomaly.csv'
MONTHLY_SRC   = ETC_DIR / 'MonthlyMean_1999-9_2017-10.csv'
MONTHLY_OUT   = ETC_DIR / 'MonthlyMean_1999-9_2026-4-30.csv'

NOAA_URL = (
    'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'
    '?begin_date={begin}&end_date={end}'
    '&station={station}'
    '&product=monthly_mean'
    '&datum=NAVD'
    '&units=metric'
    '&time_zone=GMT'
    '&format=csv'
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ym_range(from_ym, to_ym):
    """Generate (year, month) tuples inclusive."""
    y, m = from_ym
    while (y, m) <= to_ym:
        yield (y, m)
        m += 1
        if m > 12:
            m = 1
            y += 1


def fetch_year(station_id, year):
    """
    Fetch monthly_mean for one calendar year at datum=NAVD.
    Returns dict {(year, month): msl_navd_m} for available months.
    """
    begin = f'{year}0101'
    end   = f'{year}1231'
    url   = NOAA_URL.format(begin=begin, end=end, station=station_id)

    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                raw = resp.read().decode('utf-8')
            break
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    else:
        raise IOError(f'Failed to fetch {url} after 3 attempts: {last_err}')

    # Check for NOAA error response
    if 'Error' in raw[:200] or 'errorMessage' in raw[:200]:
        raise ValueError(f'NOAA API error for station {station_id} year {year}:\n{raw[:400]}')

    reader = csv.DictReader(io.StringIO(raw))
    # Strip whitespace from header keys
    reader.fieldnames = [h.strip() for h in reader.fieldnames] if reader.fieldnames else reader.fieldnames

    result = {}
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        try:
            y = int(row['Year'])
            mo = int(row['Month'])
            msl = float(row['MSL'])
            result[(y, mo)] = msl
        except (KeyError, ValueError):
            continue
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print('\n' + '=' * 68)
        print('  DRY-RUN MODE — stats only, no files written')
        print('=' * 68)

    months_needed = list(ym_range(EXTEND_FROM, EXTEND_TO))
    years_needed  = sorted({y for y, m in months_needed})

    print(f'\nExtending MSL_Anomaly.csv:')
    print(f'  Period : {EXTEND_FROM[0]}-{EXTEND_FROM[1]:02d} to '
          f'{EXTEND_TO[0]}-{EXTEND_TO[1]:02d}  ({len(months_needed)} months)')
    print(f'  Stations: {[s[0] for s in STATIONS]}')

    # ------------------------------------------------------------------
    # Fetch NOAA data
    # ------------------------------------------------------------------
    print('\n-- Fetching NOAA monthly_mean (datum=NAVD) -------------------------')
    all_data = {name: {} for name, _ in STATIONS}

    for stn_name, stn_id in STATIONS:
        print(f'\n  {stn_name} ({stn_id}):')
        for yr in years_needed:
            print(f'    {yr} ... ', end='', flush=True)
            data = fetch_year(stn_id, yr)
            # Keep only months we need
            kept = {k: v for k, v in data.items() if k in set(months_needed)}
            all_data[stn_name].update(kept)
            print(f'{len(data)} months returned, {len(kept)} in range')
            time.sleep(0.4)   # gentle rate limiting

    # ------------------------------------------------------------------
    # Compute 3-station mean and anomaly
    # ------------------------------------------------------------------
    print('\n-- Computing anomalies ---------------------------------------------')
    new_rows = []   # list of (date_str, kw, vk, vir, mean_navd, anomaly)

    for y, mo in months_needed:
        stn_vals = {}
        for stn_name, _ in STATIONS:
            v = all_data[stn_name].get((y, mo))
            if v is not None:
                stn_vals[stn_name] = v

        n_avail = len(stn_vals)
        if n_avail == 0:
            print(f'  {y}-{mo:02d}: NO DATA for any station, skipping.')
            continue

        if n_avail < len(STATIONS):
            missing_stns = [s for s, _ in STATIONS if s not in stn_vals]
            print(f'  {y}-{mo:02d}: WARNING — missing {missing_stns}, '
                  f'using {n_avail}-station mean.')

        mean_navd = sum(stn_vals.values()) / n_avail
        anomaly   = round(mean_navd - MSL_NAVD_EPOCH, 3)
        date_str  = f'{y}-{mo:02d}-15'

        kw  = stn_vals.get('KeyWest',     float('nan'))
        vk  = stn_vals.get('VacaKey',     float('nan'))
        vir = stn_vals.get('VirginiaKey', float('nan'))

        new_rows.append((date_str, kw, vk, vir, mean_navd, anomaly))
        print(f'  {date_str}:  KW={kw:6.3f}  VK={vk:6.3f}  VirK={vir:6.3f}'
              f'  Mean={mean_navd:6.3f}  Anomaly={anomaly:+.3f}')

    print(f'\n  {len(new_rows)} rows computed out of {len(months_needed)} requested.')

    if not new_rows:
        print('\nNo rows to write. Exiting.')
        return

    # Sanity check: anomalies should be physically reasonable (|anomaly| < 0.5 m)
    max_abs = max(abs(r[5]) for r in new_rows)
    if max_abs > 0.5:
        print(f'\nWARNING: max |anomaly| = {max_abs:.3f} m — unusually large. '
              f'Check datum consistency before proceeding.')

    if dry_run:
        print(f'\nDRY-RUN: would append {len(new_rows)} rows to {ANOMALY_FILE.name}')
        print(f'DRY-RUN: would write updated MonthlyMean to {MONTHLY_OUT.name}')
        print('\n' + '=' * 68 + '\nDone.\n' + '=' * 68)
        return

    # ------------------------------------------------------------------
    # Append to MSL_Anomaly.csv
    # ------------------------------------------------------------------
    print(f'\n-- Writing {ANOMALY_FILE.name} ------------------------------------')
    with open(ANOMALY_FILE, 'a', newline='') as f:
        for date_str, kw, vk, vir, mean_navd, anomaly in new_rows:
            f.write(f'{date_str},{anomaly}\n')
    print(f'  {len(new_rows)} rows appended.')

    # Verify final row count
    with open(ANOMALY_FILE, 'r') as f:
        total_lines = sum(1 for _ in f)
    print(f'  Total rows in file (incl. header): {total_lines}')

    # ------------------------------------------------------------------
    # Write updated MonthlyMean combined file
    # ------------------------------------------------------------------
    print(f'\n-- Writing {MONTHLY_OUT.name} --------------------------')
    with open(MONTHLY_SRC, 'r') as f:
        src_lines = f.readlines()

    header = src_lines[0]   # Date, KeyWestMSL_NAVD,VacaKeyMSL_NAVD,...

    # Find the last date in the existing file to avoid overlap
    last_existing = None
    for line in reversed(src_lines[1:]):
        if line.strip():
            last_existing = line.split(',')[0].strip()
            break

    def fmt(v):
        return f'{v:.3f}' if v == v else 'NA'   # NaN check

    with open(MONTHLY_OUT, 'w', newline='') as f:
        for line in src_lines:
            f.write(line)
        for date_str, kw, vk, vir, mean_navd, anomaly in new_rows:
            if last_existing is None or date_str > last_existing:
                f.write(f'{date_str},{fmt(kw)},{fmt(vk)},{fmt(vir)},'
                        f'{mean_navd:.3f},{anomaly:.3f}\n')

    print(f'  Written.')

    print('\n' + '=' * 68)
    print('Done. Run the model again to verify 2025 water levels are normal.')
    print('=' * 68)


if __name__ == '__main__':
    main()
