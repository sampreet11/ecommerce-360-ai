
# E-Commerce 360 — Python validation & forecasting
# Generated from the uploaded Olist dataset.

import pandas as pd
import numpy as np
from pathlib import Path

# Resolve paths relative to this script, so it works from any current directory.
PROJECT = Path(__file__).resolve().parents[1]
FACT_PATH = PROJECT / "Data" / "processed" / "fact_sales.csv"
if not FACT_PATH.is_file():
    raise FileNotFoundError(f"Could not find processed fact table: {FACT_PATH}")

fact = pd.read_csv(
    FACT_PATH,
    parse_dates=["order_purchase_timestamp", "purchase_month"],
)

# 1. Monthly trend
monthly = fact[fact.order_status=="delivered"].groupby("purchase_month").agg(
    revenue=("sales","sum"), orders=("order_id","nunique")
).reset_index()

# 2. Exclude incomplete final delivered month
history = monthly[monthly.purchase_month <= pd.Timestamp("2018-08-01")].copy()

# 3. Transparent six-month rolling-mean baseline forecast
history_values = history.revenue.tolist()
forecast=[]
for i in range(6):
    value=float(np.mean(history_values[-3:]))
    forecast_month=history.purchase_month.max()+pd.offsets.MonthBegin(i+1)
    forecast.append([forecast_month,value])
    history_values.append(value)

forecast_df=pd.DataFrame(forecast, columns=["month","forecast_revenue"])
print(forecast_df)
