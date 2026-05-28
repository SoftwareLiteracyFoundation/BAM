#!/usr/bin/env python3
"""
Test NOAA predictions API datum and interval support for each BAM tide station.
Subordinate stations may only serve MLLW, STND, or high/low — not MSL hourly.
We test multiple datums and check if hourly data is available.
"""
import json
try:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError

STATIONS = {
    'Cape_Sable'              : 'TEC4165',
    'Long_Key'                : '8723899',
    'Lignumvitae_Key'         : '8723824',
    'Snake_Creek'             : '8723787',
    'Tavernier_Creek'         : '8723748',
    'Garden_Cove'             : '8723622',
    'Little_Card_Sound_bridge': '8723534',
}

BASE = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        "?begin_date=20170101&end_date=20170103"
        "&product=predictions&units=metric"
        "&time_zone=lst_ldt&format=json&application=BAM_tide_test"
        "&interval=h"           # hourly
        "&datum={datum}&station={station_id}")

DATUMS = ['MSL', 'MTL', 'MLLW', 'STND']

def try_fetch(url):
    try:
        with urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
        if 'error' in data:
            return None, data['error'].get('message', '')
        if 'predictions' in data:
            preds = data['predictions']
            sample = [round(float(p['v']), 3) for p in preds[:3]]
            return preds, str(sample)
        return None, "unknown keys: " + str(list(data.keys()))
    except Exception as e:
        return None, str(e)

print("Testing NOAA Predictions API -- datum and hourly interval support")
print("=" * 80)
for name, sid in STATIONS.items():
    print("\n%s  (ID: %s)" % (name, sid))
    for datum in DATUMS:
        url = BASE.format(datum=datum, station_id=sid)
        preds, msg = try_fetch(url)
        status = "OK (%d rows)" % len(preds) if preds else "FAIL"
        print("   datum=%-6s  %s  %s" % (datum, status, msg if not preds else msg))
        if preds:
            break   # found a working datum, no need to try others
