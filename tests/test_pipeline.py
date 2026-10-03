"""Offline tests: build a tiny DuckDB from fixture CSVs and run the SQL."""
from pathlib import Path

import pandas as pd
import pytest

from pipeline.build_db import TABLES, build, run_checks

SQL = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def con(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    ts = "order_purchase_timestamp,order_approved_at,order_delivered_carrier_date," \
         "order_delivered_customer_date,order_estimated_delivery_date"
    pd.DataFrame(
        [
            # on time
            ["o1", "c1", "delivered", "2017-03-01 10:00:00", "2017-03-01 11:00:00",
             "2017-03-02 10:00:00", "2017-03-08 10:00:00", "2017-03-10 00:00:00"],
            # 5 days late
            ["o2", "c2", "delivered", "2017-03-05 10:00:00", "2017-03-05 11:00:00",
             "2017-03-06 10:00:00", "2017-03-20 10:00:00", "2017-03-15 00:00:00"],
            # stuck after carrier hand-off
            ["o3", "c3", "shipped", "2017-04-01 10:00:00", "2017-04-01 11:00:00",
             "2017-04-02 10:00:00", None, "2017-04-15 00:00:00"],
            # cancelled before approval
            ["o4", "c4", "canceled", "2017-04-02 10:00:00", None, None, None,
             "2017-04-20 00:00:00"],
            # outside the analysis window
            ["o5", "c5", "delivered", "2016-10-01 10:00:00", "2016-10-01 11:00:00",
             "2016-10-02 10:00:00", "2016-10-05 10:00:00", "2016-10-20 00:00:00"],
        ],
        columns=["order_id", "customer_id", "order_status", *ts.split(",")],
    ).to_csv(raw / "olist_orders_dataset.csv", index=False)
    pd.DataFrame(
        [[f"o{i}", 1, "p1", "s1", "2017-03-03 00:00:00", 100.0, 10.0] for i in (1, 2, 3, 4)],
        columns=["order_id", "order_item_id", "product_id", "seller_id",
                 "shipping_limit_date", "price", "freight_value"],
    ).to_csv(raw / "olist_order_items_dataset.csv", index=False)
    pd.DataFrame(
        [["r1", "o1", 5, None, None, "2017-03-09", "2017-03-10"],
         ["r2", "o2", 1, None, None, "2017-03-21", "2017-03-22"]],
        columns=["review_id", "order_id", "review_score", "review_comment_title",
                 "review_comment_message", "review_creation_date", "review_answer_timestamp"],
    ).to_csv(raw / "olist_order_reviews_dataset.csv", index=False)
    pd.DataFrame(
        [[f"c{i}", f"u{i}", 1000, "sao paulo", "SP"] for i in range(1, 6)],
        columns=["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                 "customer_city", "customer_state"],
    ).to_csv(raw / "olist_customers_dataset.csv", index=False)
    for table, cols in {
        "order_payments": "order_id,payment_sequential,payment_type,payment_installments,payment_value",
        "products": "product_id,product_category_name",
        "sellers": "seller_id,seller_zip_code_prefix,seller_city,seller_state",
    }.items():
        (raw / f"olist_{table}_dataset.csv").write_text(cols + "\n")
    assert {f"olist_{t}_dataset.csv" for t in TABLES} <= {p.name for p in raw.iterdir()}
    c = build(raw, tmp_path / "test.duckdb")
    yield c
    c.close()


def run(con, name):
    return con.execute((SQL / f"{name}.sql").read_text()).df()


def test_window_excludes_out_of_range_orders(con):
    assert con.execute("SELECT COUNT(*) FROM orders_clean").fetchone()[0] == 4


def test_quality_checks_pass(con):
    assert all(status != "FAIL" for _, _, status in run_checks(con))


def test_funnel_counts(con):
    df = run(con, "01_order_funnel")
    assert df["orders"].tolist() == [4, 3, 3, 2]
    assert df["pct_of_placed"].iloc[-1] == 50.0


def test_lost_orders_value(con):
    df = run(con, "02_lost_orders").set_index("order_status")
    assert df.loc["shipped", "value_brl"] == 110
    assert df["orders"].sum() == 2


def test_late_bucket_and_review(con):
    df = run(con, "03_delivery_vs_reviews").set_index("delivery_bucket")
    assert df.loc["1. On time or early", "avg_review"] == 5
    assert df.loc["3. 4-7 days late", "avg_review"] == 1
