import pymysql, pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')

# Load existing PET file and analyze annual and monthly patterns
pet_file = r"C:\Users\ErikStabenau\OneDrive - The Everglades Foundation, Inc\Documents\Claude\BAM\data\ET\PET_1999-9-1_2016-12-31.csv"
df = pd.read_csv(pet_file, parse_dates=['Time'], index_col='Time')
print("PET file: %s -> %s  (%d days)" % (df.index[0].date(), df.index[-1].date(), len(df)))
print("NaNs: %d" % df.isna().sum().sum())
print()

# Annual statistics
ann = df.resample('YE').mean()
print("Annual mean PET (mm/day):")
print(ann.round(2).to_string())
print()

# Monthly climatology
mon = df.groupby(df.index.month)['PET'].mean()
mon.index = pd.to_datetime(mon.index, format='%m').strftime('%b')
print("Monthly mean PET (mm/day):")
print(mon.round(2).to_string())
print()

# Check if there's a discontinuity around 2010/2011
print("Last 30 days of 2010, first 30 days of 2011:")
window = df['2010-12-01':'2011-01-31']
print(window.round(2).to_string())
print()

# Compare 1999-2010 vs 2011-2016 mean by month
print("Monthly mean comparison: 1999-2010 vs 2011-2016")
df_pre  = df[:'2010-12-31']
df_post = df['2011-01-01':]
m_pre  = df_pre.groupby( df_pre.index.month)['PET'].mean()
m_post = df_post.groupby(df_post.index.month)['PET'].mean()
comp = pd.DataFrame({'1999-2010': m_pre, '2011-2016': m_post})
comp.index = pd.to_datetime(comp.index, format='%m').strftime('%b')
comp['pct_diff'] = ((comp['2011-2016'] - comp['1999-2010']) / comp['1999-2010'] * 100)
print(comp.round(2).to_string())

# Check DB coverage at representative station
conn = pymysql.connect(host='127.0.0.1', port=3306,
                       user='read_only', password='read_only',
                       database='hydrology', autocommit=True)
print()
print("DB PET at TAYLORRIVER around 2010-2011 boundary:")
df_db = pd.read_sql(
    "SELECT measurement_date, measurement_value "
    "FROM measurement "
    "WHERE datatype='PET' AND station='TAYLORRIVER' "
    "  AND measurement_date BETWEEN '2010-12-20' AND '2011-01-10' "
    "ORDER BY measurement_date",
    conn)
print(df_db.to_string())

# Also cross-check DB vs BAM file on a full year overlap
print()
print("Cross-check: DB TAYLORRIVER PET vs BAM file, 1999-09-01 to 1999-09-15")
df_db2 = pd.read_sql(
    "SELECT measurement_date, measurement_value "
    "FROM measurement "
    "WHERE datatype='PET' AND station='TAYLORRIVER' "
    "  AND measurement_date BETWEEN '1999-09-01' AND '1999-09-15' "
    "ORDER BY measurement_date",
    conn)
df_bam = df['1999-09-01':'1999-09-15']
comp2 = pd.DataFrame({'DB_TAYLORRIVER': df_db2.set_index('measurement_date')['measurement_value'],
                      'BAM_file': df_bam['PET']})
print(comp2.round(3).to_string())

conn.close()
