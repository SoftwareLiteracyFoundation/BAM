#!/usr/bin/env python3
"""
discover_db_stations.py
Probe TEF04 MySQL hydrology database to confirm available datatypes and
sample measurement values for salinity, stage, and S197 flow stations.

Run on TEF04 (or via SSH tunnel from Windows).

Usage:
    python discover_db_stations.py
"""

import pymysql
import pandas as pd

DB = dict(host='127.0.0.1', port=3306, user='read_only',
          password='read_only', database='hydrology')

# Stations to check
SALINITY_STATIONS = ['BA','BK','BN','BS','DK','GB','HC','JK','LB','LM',
                     'LR','LS','MK','PK','TC','TR','WB','MB','MD','TP']
STAGE_STATIONS    = ['BA','BK','BN','BS','DK','GB','HC','JK','LB','LM',
                     'LR','LS','MK','PK','TC','TR','WB','MB','MD']
S197_CANDIDATES   = ['S197', 'S-197']

ALL_STATIONS = sorted(set(SALINITY_STATIONS + STAGE_STATIONS + S197_CANDIDATES))

def fmt_in(lst):
    return ','.join(['%s'] * len(lst))

conn = pymysql.connect(**DB)

# ------------------------------------------------------------------
# 1. station_datatype — what datatypes exist per station?
# ------------------------------------------------------------------
print('\n=== 1. station_datatype — datatypes per station ===')
sql = f'''
    SELECT station, datatype
    FROM station_datatype
    WHERE station IN ({fmt_in(ALL_STATIONS)})
    ORDER BY station, datatype
'''
df_sd = pd.read_sql(sql, conn, params=ALL_STATIONS)
if df_sd.empty:
    print('  (no rows returned — check station names)')
else:
    print(df_sd.to_string(index=False))

# ------------------------------------------------------------------
# 2. S197 — check under 'S197' and 'S-197', all datatypes, recent values
# ------------------------------------------------------------------
print('\n=== 2. S197 measurement samples (last 5 rows per datatype) ===')
for s197 in S197_CANDIDATES:
    sql2 = '''
        SELECT station, datatype, measurement_value, measurement_date, measurement_time
        FROM measurement
        WHERE station = %s
        ORDER BY measurement_date DESC, measurement_time DESC
        LIMIT 10
    '''
    df_s = pd.read_sql(sql2, conn, params=[s197])
    if df_s.empty:
        print(f'  {s197!r:8} -> no rows found')
    else:
        print(f'\n  station={s197!r}')
        print(df_s.to_string(index=False))

# ------------------------------------------------------------------
# 3. Salinity — spot-check one station (HC) for datatypes and units
# ------------------------------------------------------------------
print('\n=== 3. HC salinity spot-check (last 5 rows) ===')
sql3 = '''
    SELECT station, datatype, measurement_value, measurement_date, measurement_time
    FROM measurement
    WHERE station = 'HC'
    ORDER BY measurement_date DESC, measurement_time DESC
    LIMIT 10
'''
df_hc = pd.read_sql(sql3, conn)
print(df_hc.to_string(index=False))

# ------------------------------------------------------------------
# 4. Stage — spot-check BA for datatypes and units
# ------------------------------------------------------------------
print('\n=== 4. BA stage spot-check (last 5 rows) ===')
sql4 = '''
    SELECT station, datatype, measurement_value, measurement_date, measurement_time
    FROM measurement
    WHERE station = 'BA'
    ORDER BY measurement_date DESC, measurement_time DESC
    LIMIT 10
'''
df_ba = pd.read_sql(sql4, conn)
print(df_ba.to_string(index=False))

# ------------------------------------------------------------------
# 5. Date coverage: earliest and latest measurement per station+datatype
#    for the stations we care about
# ------------------------------------------------------------------
print('\n=== 5. Date coverage by station+datatype ===')
sal_stage = sorted(set(SALINITY_STATIONS + STAGE_STATIONS))
sql5 = f'''
    SELECT station, datatype,
           MIN(measurement_date) AS earliest,
           MAX(measurement_date) AS latest,
           COUNT(*)              AS n_rows
    FROM measurement
    WHERE station IN ({fmt_in(sal_stage)})
    GROUP BY station, datatype
    ORDER BY station, datatype
'''
df_cov = pd.read_sql(sql5, conn, params=sal_stage)
print(df_cov.to_string(index=False))

# ------------------------------------------------------------------
# 6. S197 date coverage
# ------------------------------------------------------------------
print('\n=== 6. S197 date coverage ===')
sql6 = f'''
    SELECT station, datatype,
           MIN(measurement_date) AS earliest,
           MAX(measurement_date) AS latest,
           COUNT(*)              AS n_rows
    FROM measurement
    WHERE station IN ({fmt_in(S197_CANDIDATES)})
    GROUP BY station, datatype
    ORDER BY station, datatype
'''
df_s197cov = pd.read_sql(sql6, conn, params=S197_CANDIDATES)
if df_s197cov.empty:
    print('  No rows found for S197 or S-197')
else:
    print(df_s197cov.to_string(index=False))

conn.close()
print('\nDone.')
