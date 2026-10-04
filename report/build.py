"""Run every query in sql/ against the DuckDB store and write a report.

Usage:  python -m report.build   (after python -m pipeline.build_db)
Outputs: results/REPORT.md, results/csv/<query>.csv, results/charts/*.png
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
RESULTS = ROOT / "results"
CHARTS = RESULTS / "charts"
CSV_DIR = RESULTS / "csv"

ACCENT = "#2a6fdb"
MUTED = "#9aa5b1"
INK = "#1f2933"


def run_queries(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    out = {}
    for path in sorted(SQL_DIR.glob("*.sql")):
        out[path.stem] = con.execute(path.read_text()).df()
    return out


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK)
    ax.grid(axis="x", color="#e4e7eb", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_funnel(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    stages = df["stage"][::-1]
    pct = df["pct_of_placed"][::-1]
    ax.barh(stages, pct, color=ACCENT, height=0.55)
    for y, (p, n) in enumerate(zip(pct, df["orders"][::-1])):
        ax.text(p + 0.05, y, f"{p:.2f}%  ({n:,})", va="center", color=INK, fontsize=9)
    ax.set_xlim(95, 100.9)
    ax.set_xlabel("% of orders placed (x-axis starts at 95%)")
    ax.set_title("Order fulfilment funnel, Jan 2017 - Aug 2018", loc="left", color=INK)
    _style(ax)
    fig.tight_layout()
    path = CHARTS / "01_order_funnel.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_reviews(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    labels = df["delivery_bucket"].str.slice(3)
    colors = [ACCENT] + [MUTED] * (len(df) - 1)
    ax.bar(labels, df["avg_review"], color=colors, width=0.55)
    for x, (s, share) in enumerate(zip(df["avg_review"], df["pct_of_delivered"])):
        ax.text(x, s + 0.08, f"{s:.2f}★\n{share}% of orders", ha="center", color=INK, fontsize=9)
    ax.set_ylim(0, 5.3)
    ax.set_ylabel("Average review score (1-5)")
    ax.set_title("Late deliveries wreck review scores", loc="left", color=INK)
    _style(ax)
    ax.grid(axis="y", color="#e4e7eb", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    path = CHARTS / "02_reviews_by_delivery.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_monthly(df: pd.DataFrame) -> Path:
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    months = pd.to_datetime(df["month"])
    top.bar(months, df["orders_placed"], width=20, color=MUTED)
    top.set_ylabel("Orders placed")
    top.set_title("Volume vs on-time delivery by purchase month", loc="left", color=INK)
    bottom.plot(months, df["on_time_pct"], color=ACCENT, linewidth=2, marker="o", markersize=4)
    low = df.nsmallest(3, "on_time_pct")
    for m, v in zip(pd.to_datetime(low["month"]), low["on_time_pct"]):
        bottom.annotate(f"{v}%", (m, v), textcoords="offset points", xytext=(0, -14),
                        ha="center", color=INK, fontsize=9)
    bottom.set_ylim(75, 100)
    bottom.set_ylabel("On-time delivery %")
    for ax in (top, bottom):
        _style(ax)
        ax.grid(axis="x", visible=False)
        ax.grid(axis="y", color="#e4e7eb", linewidth=0.8)
    fig.tight_layout()
    path = CHARTS / "03_monthly_on_time.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_cohorts(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = [MUTED if inc else ACCENT for inc in df["window_incomplete"]]
    ax.bar(df["cohort"], df["pct_returned_90d"], color=colors, width=0.55)
    for x, (p, n, inc) in enumerate(zip(df["pct_returned_90d"], df["new_customers"],
                                        df["window_incomplete"])):
        label = f"{p:.2f}%\n{n:,} new" + ("\n(partial)" if inc else "")
        ax.text(x, p + 0.03, label, ha="center", color=INK, fontsize=8)
    ax.set_ylim(0, 2.1)
    ax.set_ylabel("% buying again within 90 days")
    ax.set_title("Fewer than 2 in 100 new customers come back within 90 days",
                 loc="left", color=INK)
    _style(ax)
    ax.grid(axis="y", color="#e4e7eb", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    path = CHARTS / "04_cohort_retention.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_states(df: pd.DataFrame) -> Path:
    df = df.sort_values("late_rate_pct")
    fig, ax = plt.subplots(figsize=(8, 5))
    top_share = df["pct_of_late"].nlargest(2).index
    colors = [ACCENT if i in top_share else MUTED for i in df.index]
    ax.barh(df["state"], df["late_rate_pct"], color=colors, height=0.6)
    for y, (r, n, share) in enumerate(zip(df["late_rate_pct"], df["orders"], df["pct_of_late"])):
        ax.text(r + 0.2, y, f"{r}%  ({n:,} orders, {share}% of late)", va="center",
                color=INK, fontsize=8)
    ax.set_xlim(0, df["late_rate_pct"].max() * 1.6)
    ax.set_xlabel("% delivered late, orders the seller handed off on time")
    ax.set_title("Carrier-leg lateness by destination state (500+ orders)", loc="left", color=INK)
    _style(ax)
    fig.tight_layout()
    path = CHARTS / "05_late_by_state.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def write_report(results: dict[str, pd.DataFrame]) -> Path:
    lines = [
        "# Results",
        "",
        "Generated by `python -m report.build`. Orders placed 2017-01-01 to 2018-08-31.",
        "",
    ]
    for name, df in results.items():
        title = (SQL_DIR / f"{name}.sql").read_text().splitlines()[0].lstrip("- ").strip()
        lines += [f"## {title}", "", f"Query: [`sql/{name}.sql`](../sql/{name}.sql)", "",
                  df.to_markdown(index=False), ""]
    path = RESULTS / "REPORT.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "olist.duckdb"), read_only=True)
    results = run_queries(con)
    con.close()
    for name, df in results.items():
        df.to_csv(CSV_DIR / f"{name}.csv", index=False)
    print(chart_funnel(results["01_order_funnel"]))
    print(chart_reviews(results["03_delivery_vs_reviews"]))
    print(chart_monthly(results["04_monthly_on_time"]))
    print(chart_cohorts(results["06_cohort_retention"]))
    print(chart_states(results["09_late_by_state"]))
    print(write_report(results))


if __name__ == "__main__":
    main()
