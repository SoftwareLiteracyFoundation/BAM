#!/usr/bin/env python3
"""Validate utide: analyze Long Key 1999-2013, predict 2014-2016 holdout."""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
import utide

TIDE_FILE = (r"C:\Users\ErikStabenau\OneDrive - The Everglades Foundation, Inc"
             r"\Documents\Claude\BAM\data\Tide\2000_2016"
             r"\Long_Key_1999-09-01_2016-12-31.csv")

print("Loading Long Key tide file...")
df = pd.read_csv(TIDE_FILE, header=0, names=['Time','WL'],
                 skipinitialspace=True, parse_dates=False)

def parse_dt(s):
    parts = s.strip().split()
    return pd.to_datetime(' '.join(parts[:3]), format='%Y-%m-%d %I:%M %p')

df['dt'] = df['Time'].apply(parse_dt)
df['WL'] = pd.to_numeric(df['WL'], errors='coerce')
df = df.sort_values('dt').reset_index(drop=True)
print("  %d hourly records  mean WL: %.4f m" % (len(df), df['WL'].mean()))

# -- Training: 1999-2013, Holdout: 2014-2016 ----------------------------------
train = df[df['dt'] < '2014-01-01'].copy()
hold  = df[df['dt'] >= '2014-01-01'].copy()

print("\nFitting utide to 1999-2013 (%d hours)..." % len(train))
# Pass datetime64 directly -- no epoch needed
t_train = train['dt'].values.astype('datetime64[s]')
coef = utide.solve(t_train, train['WL'].values.astype(float),
                   lat=24.82,
                   method='ols',
                   conf_int='none',
                   verbose=False)

n_const = len(coef.name)
print("  %d constituents fitted." % n_const)
if n_const > 0:
    idx_sorted = np.argsort(coef.A)[::-1]
    print("  Top 8 by amplitude:")
    for i in idx_sorted[:8]:
        print("    %-6s  A=%.4f m  g=%.1f deg" % (coef.name[i], coef.A[i], coef.g[i]))

# -- Holdout prediction -------------------------------------------------------
print("\nPredicting 2014-2016 holdout (%d hours)..." % len(hold))
t_hold = hold['dt'].values.astype('datetime64[s]')
rec    = utide.reconstruct(t_hold, coef, verbose=False)
pred   = rec.h
actual = hold['WL'].values.astype(float)

resid  = actual - pred
rmse   = np.sqrt(np.mean(resid**2))
r2     = 1 - np.var(resid) / np.var(actual)
print("  RMSE       : %.4f m" % rmse)
print("  R2         : %.4f" % r2)
print("  Max abs err: %.4f m" % np.max(np.abs(resid)))
print("  Mean bias  : %.5f m" % np.mean(resid))

# Sample values
print("\n  First 12 hours of 2014 -- actual vs predicted (m):")
print("  %s  %10s  %10s  %8s" % ("Datetime", "Actual", "Predicted", "Error"))
for i in range(12):
    row = hold.iloc[i]
    print("  %s  %10.3f  %10.3f  %8.4f" % (row['dt'], actual[i], pred[i], resid[i]))

# -- Forward prediction: 2017-2018 -------------------------------------------
print("\nForward prediction: first 12 hours of 2017-01-01 (unseen)")
t_fut = pd.date_range('2017-01-01', periods=12, freq='h').values.astype('datetime64[s]')
rec_fut = utide.reconstruct(t_fut, coef, verbose=False)
print("  Predicted values (m): %s" % [round(v,3) for v in rec_fut.h])
