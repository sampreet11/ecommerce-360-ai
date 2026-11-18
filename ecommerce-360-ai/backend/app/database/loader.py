"""Cleans the processed CSVs and loads them into the analytics schema.

`prepare_tables()` is pure pandas (unit-tested); `load_all()` writes through an Executor.
Reviews, payments and the raw orders table are NOT in the provided project ZIP, so they are
not loaded (see docs/data-dictionary.md).
"""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BATCH = 5000

# table -> (csv file, rename map, columns in table order)
SPEC: dict[str, dict] = {
    "dim_seller": {"csv": "dim_seller.csv", "rename": {}},
    "dim_product": {"csv": "dim_product.csv", "rename": {}},
    "dim_date": {"csv": "dim_date.csv", "rename": {"date": "date_key"}},
    "fact_sales": {"csv": "fact_sales.csv", "rename": {}},
    "customer_360": {"csv": "customer_360.csv", "rename": {"R": "r_score", "F": "f_score", "M": "m_score"}},
    "cohort_retention": {"csv": "cohort_retention.csv", "rename": {}},
    "market_basket_pairs": {"csv": "market_basket_category_pairs.csv", "rename": {}},
}
LOAD_ORDER = list(SPEC)

DATE_COLS = {"date_key", "purchase_month", "cohort_month"}
TS_COLS = {"order_purchase_timestamp", "first_purchase", "last_purchase"}
INT_COLS = {
    "product_name_lenght", "product_description_lenght", "product_photos_qty", "order_item_id",
    "orders", "items", "recency_days", "r_score", "f_score", "m_score", "rfm_score", "cohort_idx",
    "active_customers", "cohort_size", "orders_together", "year", "month_number", "week_number",
    "seller_zip_code_prefix", "late_flag", "repeat_flag",
}

TABLE_COLUMNS = {
    "dim_seller": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "dim_product": ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght",
                    "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm",
                    "product_width_cm", "product_category_name_english", "category"],
    "dim_date": ["date_key", "year", "quarter", "month_number", "month_name", "year_month", "week_number"],
    "fact_sales": ["order_id", "order_item_id", "customer_id", "customer_unique_id", "product_id", "seller_id",
                   "order_status", "order_purchase_timestamp", "price", "freight_value", "sales",
                   "gross_order_value", "category", "customer_state", "seller_state", "delivery_days",
                   "late_days", "late_flag", "purchase_month"],
    "customer_360": ["customer_unique_id", "first_purchase", "last_purchase", "orders", "items", "revenue",
                     "freight", "recency_days", "aov", "repeat_flag", "cohort_month", "r_score", "f_score",
                     "m_score", "rfm_score", "rfm_segment", "lifecycle"],
    "cohort_retention": ["cohort_month", "cohort_idx", "active_customers", "cohort_size", "retention"],
    "market_basket_pairs": ["category_a", "category_b", "orders_together", "support"],
}


def _clean(value: Any, col: str) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA or value is pd.NaT:
        return None
    if col in DATE_COLS:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    if col in TS_COLS:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
    if col in INT_COLS:
        if isinstance(value, str):
            return 1 if value.lower() == "true" else 0 if value.lower() == "false" else int(float(value))
        return int(value)
    if isinstance(value, bool):
        return int(value)
    if hasattr(value, "item"):
        return value.item()
    return value


def prepare_table(name: str, data_dir: Path) -> list[dict]:
    spec = SPEC[name]
    path = Path(data_dir) / spec["csv"]
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file for {name}: {path}")
    df = pd.read_csv(path).rename(columns=spec["rename"])
    cols = TABLE_COLUMNS[name]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing expected columns {missing}")
    df = df[cols]
    # Primary-key duplicates are removed (keep first) and reported by the caller via length difference.
    pk = {"fact_sales": ["order_id", "order_item_id"], "customer_360": ["customer_unique_id"],
          "dim_seller": ["seller_id"], "dim_product": ["product_id"], "dim_date": ["date_key"],
          "cohort_retention": ["cohort_month", "cohort_idx"],
          "market_basket_pairs": ["category_a", "category_b"]}[name]
    df = df.drop_duplicates(subset=pk, keep="first")
    return [{c: _clean(v, c) for c, v in rec.items()} for rec in df.to_dict("records")]


def insert_sql(name: str) -> str:
    cols = TABLE_COLUMNS[name]
    return f"INSERT INTO analytics.{name} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"


def load_all(ex, data_dir: Path, truncate: bool = True, log=print) -> dict[str, int]:
    counts: dict[str, int] = {}
    if truncate:
        for t in reversed(LOAD_ORDER):
            ex.execute(f"DELETE FROM analytics.{t}")
    for name in LOAD_ORDER:
        rows = prepare_table(name, data_dir)
        sql = insert_sql(name)
        for i in range(0, len(rows), BATCH):
            ex.executemany(sql, rows[i:i + BATCH])
        counts[name] = len(rows)
        log(f"loaded analytics.{name}: {len(rows):,} rows")
    return counts
