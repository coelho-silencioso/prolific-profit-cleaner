import pandas as pd
from forex_python.converter import CurrencyRates

pd.set_option('display.max_columns', None)

# =====================================================
# 🔥 Conversion rate (GBP → USD)
# =====================================================

c = CurrencyRates()
rate = c.get_rate('GBP', 'USD')

file = 'my_prolific_submission_history.csv'

# =====================================================
# 🔥 Load data
# =====================================================

df = pd.read_csv(file)

# =====================================================
# 🔥 TIMEZONE FIX
# =====================================================

df['Completed At'] = pd.to_datetime(df['Completed At'], utc=True, errors='coerce')
df['Started At'] = pd.to_datetime(df['Started At'], utc=True, errors='coerce')

df['Completed At'] = df['Completed At'].dt.tz_convert('US/Central')
df['Started At'] = df['Started At'].dt.tz_convert('US/Central')

# Use Completed normally, fallback to Started (for returned)
df['Date Source'] = df['Completed At']
df.loc[df['Date Source'].isna(), 'Date Source'] = df['Started At']

df['Finish Date'] = df['Date Source'].dt.date

# =====================================================
# 🔥 CLEAN NUMERIC
# =====================================================

df['Reward_num'] = df['Reward'].str.replace('[^\d.]', '', regex=True).astype(float)
df['Bonus_num'] = df['Bonus'].str.replace('[^\d.]', '', regex=True).astype(float)

df['Reward_is_gbp'] = df['Reward'].str.contains('£', na=False)
df['Bonus_is_gbp'] = df['Bonus'].str.contains('£', na=False)

df['Reward_usd'] = df['Reward_num']
df.loc[df['Reward_is_gbp'], 'Reward_usd'] *= rate

df['Bonus_usd'] = df['Bonus_num']
df.loc[df['Bonus_is_gbp'], 'Bonus_usd'] *= rate

df['Total_usd'] = df['Reward_usd'] + df['Bonus_usd']

# =====================================================
# 🔥 STATUS CLEAN
# =====================================================

df['Status_clean'] = df['Status'].str.strip().str.lower()

# =====================================================
# 🔥 DURATION (FIXED)
# =====================================================

df['Duration_hours'] = (
    (df['Completed At'] - df['Started At'])
    .dt.total_seconds() / 3600
)

# Clean bad values
df.loc[df['Duration_hours'] < 0, 'Duration_hours'] = 0

# 🔥 CRITICAL FIX: remove unrealistic sessions
df.loc[df['Duration_hours'] > 1.5, 'Duration_hours'] = 0

df['Duration_hours'] = df['Duration_hours'].fillna(0)

# =====================================================
# 🔥 TOTALS
# =====================================================

approved_total = df.loc[df['Status_clean'] == 'approved', 'Total_usd'].sum()
awaiting_total = df.loc[df['Status_clean'] == 'awaiting review', 'Total_usd'].sum()
screened_bonus_total = df.loc[df['Status_clean'] == 'screened out', 'Bonus_usd'].sum()

approved_total = round(approved_total, 2)
awaiting_total = round(awaiting_total, 2)
screened_bonus_total = round(screened_bonus_total, 2)

print(f"Approved: ${approved_total:.2f}")
print(f"Awaiting: ${awaiting_total:.2f}")
print(f"Screened BONUS: ${screened_bonus_total:.2f}")

real_total = round(approved_total + screened_bonus_total, 2)
print(f"Real earned: ${real_total:.2f}")

all_total = round(approved_total + awaiting_total + screened_bonus_total, 2)
print(f"All Accumulated Totals: ${all_total:.2f}")

# =====================================================
# 🔥 DAILY REAL
# =====================================================

daily_real = (
    df.loc[df['Status_clean'] == 'approved']
    .groupby('Finish Date')['Total_usd']
    .sum()
    +
    df.loc[df['Status_clean'] == 'screened out']
    .groupby('Finish Date')['Bonus_usd']
    .sum()
).fillna(0).round(2).sort_index()

print("\nDaily Real Earnings:")
for date, total in daily_real.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# 🔥 DAILY WAITING
# =====================================================

daily_waiting = (
    df.loc[df['Status_clean'] == 'awaiting review']
    .groupby('Finish Date')['Total_usd']
    .sum()
).fillna(0).round(2).sort_index()

print("\nDaily Waiting Earnings:")
for date, total in daily_waiting.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# 🔥 DAILY COMBINED
# =====================================================

daily_combined = (daily_real + daily_waiting).fillna(0).round(2)

print("\nDaily Combined (Real + Waiting):")
for date, total in daily_combined.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# 🔥 HOURLY (REAL ONLY)
# =====================================================

daily_hours = df.groupby('Finish Date')['Duration_hours'].sum()

hourly_real = (daily_real / daily_hours).replace([float('inf')], 0).fillna(0)

print("\nHourly Rate ($/hr) [REAL]:")
for date in daily_real.index:
    hours = daily_hours.get(date, 0)
    rate_val = hourly_real.get(date, 0)
    print(f"{date}: ${rate_val:.2f}/hr ({hours:.2f} hrs)")

# =====================================================
# 🔥 HOURLY (REAL + WAITING)
# =====================================================

hourly_combined = (daily_combined / daily_hours).replace([float('inf')], 0).fillna(0)

print("\nHourly Rate ($/hr) [REAL + WAITING]:")
for date in daily_combined.index:
    hours = daily_hours.get(date, 0)
    rate_val = hourly_combined.get(date, 0)
    print(f"{date}: ${rate_val:.2f}/hr ({hours:.2f} hrs)")

