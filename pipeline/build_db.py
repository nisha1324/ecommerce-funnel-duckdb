"""Load the raw Olist CSVs into a local DuckDB file and run data-quality checks.

Usage:  python -m pipeline.build_db  [--raw data/raw] [--db data/olist.duckdb]

Each CSV becomes a typed table. A view `orders_clean` restricts orders to the
analysis window (full months 2017-01 .. 2018-08); months before and after have
only a handful of orders and would distort trends.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
    "customers",
    "products",
    "sellers",
]
WINDOW_START = "2017-01-01"
WINDOW_END = "2018-09-01"  # exclusive

# (name, SQL returning a single number, expected value)
CHECKS = [
    ("duplicate order_id in orders",
     "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders", 0),
    ("order_items with no matching order",
     "SELECT COUNT(*) FROM order_items i ANTI JOIN orders o USING (order_id)", 0),
    ("orders with no matching customer",
     "SELECT COUNT(*) FROM orders o ANTI JOIN customers c USING (customer_id)", 0),
    ("delivered orders missing a delivery date",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' "
     "AND order_delivered_customer_date IS NULL", None),
    ("orders delivered before purchase",
     "SELECT COUNT(*) FROM orders "
     "WHERE order_delivered_customer_date < order_purchase_timestamp", 0),
    ("negative prices or freight",
     "SELECT COUNT(*) FROM order_items WHERE price < 0 OR freight_value < 0", 0),
]


def build(raw: Path, db: Path) -> duckdb.DuckDBPyConnection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    for table in TABLES:
        csv = raw / f"olist_{table}_dataset.csv"
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv_auto(?, header = true)",
            [str(csv)],
        )
    con.execute(f"""
        CREATE OR REPLACE VIEW orders_clean AS
        SELECT *
        FROM orders
        WHERE order_purchase_timestamp >= TIMESTAMP '{WINDOW_START}'
          AND order_purchase_timestamp <  TIMESTAMP '{WINDOW_END}'
    """)
    return con


def run_checks(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int, str]]:
    results = []
    for name, sql, expected in CHECKS:
        value = con.execute(sql).fetchone()[0]
        if expected is None:
            status = "info"
        else:
            status = "ok" if value == expected else "FAIL"
        results.append((name, value, status))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "olist.duckdb")
    args = parser.parse_args()

    con = build(args.raw, args.db)
    print("rows loaded:")
    for table in TABLES + ["orders_clean"]:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<15} {n:>9,}")
    print("data-quality checks:")
    for name, value, status in run_checks(con):
        print(f"  [{status:>4}] {name}: {value:,}")
    con.close()


if __name__ == "__main__":
    main()
