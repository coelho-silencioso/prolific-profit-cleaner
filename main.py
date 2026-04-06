import pandas as pd
from forex_python.converter import CurrencyRates

pd.set_option('display.max_columns', None)

# Get conversion rate (GBP -> USD)
c = CurrencyRates()
rate = c.get_rate('GBP', 'USD')

file = 'my_prolific_submission_history.csv'

# Load data
df = pd.read_csv(file)

# =====================================================
# FIX TIMEZONE (CRITICAL) - CST
# =====================================================

df['Completed At'] = pd.to_datetime(df['Completed At'], utc=True, errors='coerce')
df['Completed At'] = df['Completed At'].dt.tz_convert('US/Central')

df['Started At'] = pd.to_datetime(df['Started At'], utc=True, errors='coerce')
df['Started At'] = df['Started At'].dt.tz_convert('US/Central')

# Use Completed At normally, fallback to Started At for returned
df['Date Source'] = df['Completed At']
df.loc[df['Date Source'].isna(), 'Date Source'] = df['Started At']

df['Finish Date'] = df['Date Source'].dt.date

# =====================================================
# Clean numeric values
# =====================================================

df['Reward_num'] = df['Reward'].str.replace('[^\d.]', '', regex=True).astype(float)
df['Bonus_num'] = df['Bonus'].str.replace('[^\d.]', '', regex=True).astype(float)

df['Reward_is_gbp'] = df['Reward'].str.contains('£', na=False)
df['Bonus_is_gbp'] = df['Bonus'].str.contains('£', na=False)

# Convert to USD
df['Reward_usd'] = df['Reward_num']
df.loc[df['Reward_is_gbp'], 'Reward_usd'] *= rate

df['Bonus_usd'] = df['Bonus_num']
df.loc[df['Bonus_is_gbp'], 'Bonus_usd'] *= rate

df['Total_usd'] = df['Reward_usd'] + df['Bonus_usd']

df['Status_clean'] = df['Status'].str.strip().str.lower()

# =====================================================
# TOTALS
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

# =====================================================
# DAILY REAL (paid)  ✅ FIXED
# =====================================================

approved_daily = (
    df.loc[df['Status_clean'] == 'approved']
    .groupby('Finish Date')['Total_usd']
    .sum()
)

screened_bonus_daily = (
    df.loc[df['Status_clean'] == 'screened out']
    .groupby('Finish Date')['Bonus_usd']
    .sum()
)

daily_real = approved_daily.add(screened_bonus_daily, fill_value=0).round(2).sort_index()

print("\nDaily Real Earnings:")
for date, total in daily_real.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# DAILY WAITING (pending)
# =====================================================

daily_waiting = (
    df.loc[df['Status_clean'] == 'awaiting review']
    .groupby('Finish Date')['Total_usd']
    .sum()
).round(2).sort_index()

print("\nDaily Waiting Earnings:")
for date, total in daily_waiting.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# DAILY COMBINED (real + waiting) ✅ FIXED
# =====================================================

daily_combined = daily_real.add(daily_waiting, fill_value=0).round(2)

print("\nDaily Combined (Real + Waiting):")
for date, total in daily_combined.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# SCREENED (UNPAID PORTION ONLY)
# =====================================================

daily_screened_unpaid = (
    df.loc[df['Status_clean'] == 'screened out']
    .groupby('Finish Date')['Reward_usd']
    .sum()
).round(2).sort_index()

print("\nScreened (Unpaid Portion):")
for date, total in daily_screened_unpaid.items():
    print(f"{date}: ${total:.2f}")

# =====================================================
# RETURNED
# =====================================================

daily_returned = (
    df.loc[df['Status_clean'] == 'returned']
    .groupby('Finish Date')['Total_usd']
    .sum()
).round(2).sort_index()

print("\nReturned:")
for date, total in daily_returned.items():
    print(f"{date}: ${total:.2f}")


# =====================================================
# TIME SPENT (in hours)
# =====================================================

df['Duration_hours'] = (
    (df['Completed At'] - df['Started At'])
    .dt.total_seconds() / 3600
)

# Kill negative / garbage durations
df.loc[df['Duration_hours'] < 0, 'Duration_hours'] = 0

# =====================================================
# DAILY HOURS WORKED
# =====================================================

daily_hours = (
    df.groupby('Finish Date')['Duration_hours']
    .sum()
    .round(2)
)

# =====================================================
# HOURLY RATE (REAL ONLY)
# =====================================================

hourly_rate_combined = daily_combined.divide(daily_hours).replace([float('inf')], 0).round(2)

print("\nHourly Rate ($/hr) [REAL + WAITING]:")
for date in hourly_rate_combined.index:
    hrs = daily_hours.get(date, 0)
    rate = hourly_rate_combined.get(date, 0)
    print(f"{date}: ${rate:.2f}/hr ({hrs:.2f} hrs)")