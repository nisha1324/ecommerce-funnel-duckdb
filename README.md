# E-commerce Funnel & Delivery Analysis (DuckDB + SQL)

> 🚧 **In progress.** The funnel, delivery and customer-retention analyses are done. The seller/category view is next.

**Business question:** a Brazilian online marketplace takes ~100k orders. Where do orders drop out between checkout and the customer's door, how much revenue is lost there, and how much does delivery reliability cost in customer satisfaction?

## Data
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce): real, anonymised marketplace orders from 2016 to 2018. It's downloaded from Olist's public GitHub mirror ([`olist/work-at-olist-data`](https://github.com/olist/work-at-olist-data)) by `scripts/download_data.py`. The raw CSVs (~62 MB) aren't committed.

**Licence:** the dataset is © Olist and published under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (see the [Kaggle page](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)). This repo uses it for non-commercial analysis and redistributes only derived aggregates.

| Table | Rows |
|---|---:|
| orders | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| customers | 99,441 |
| products | 32,951 |
| sellers | 3,095 |

The analysis window is orders placed **2017-01-01 to 2018-08-31** (99,092 orders). The months before and after it have only a handful of orders.

## Approach
1. **Load** (`pipeline/build_db.py`): each CSV goes into a typed DuckDB table, plus an `orders_clean` view for the analysis window. Data-quality checks run on load: no duplicate orders, no orphan items or customers, no deliveries before purchase, no negative prices. 8 orders are marked `delivered` but have no delivery date; they're reported, not dropped.
2. **Query** ([`sql/`](sql/)): each file answers one business question and is commented.
3. **Report** (`report/build.py`): runs every query and writes [`results/REPORT.md`](results/REPORT.md), CSVs and charts.

## Findings so far

### 1. 97.1% of orders reach the customer; 2,888 don't
| Stage | Orders | % of placed |
|---|---:|---:|
| Placed | 99,092 | 100.00 |
| Payment approved | 98,957 | 99.86 |
| Handed to carrier | 97,376 | 98.27 |
| Delivered | 96,204 | 97.09 |

![Funnel](results/charts/01_order_funnel.png)

The biggest leak is **between approval and carrier hand-off** (1,581 orders): orders that are paid for but never leave the seller. The next biggest is **after hand-off** (1,172 orders), which are lost in transit.

### 2. Undelivered orders carried ~R$414k of item value
| Stalled status | Orders | Item value (R$) |
|---|---:|---:|
| shipped | 1,097 | 175,658 |
| unavailable | 602 | 0 (no items recorded) |
| canceled | 579 | 102,453 |
| processing | 299 | 68,981 |
| invoiced | 296 | 65,707 |
| other | 15 | 1,620 |

2,591 of the 2,888 were placed before July 2018, at least ~2.5 months before the data snapshot ends (October 2018). So they are genuinely stuck, not still in transit. The 1,097 "shipped but never delivered" orders are the largest pot of value.

### 3. Late delivery is the biggest driver of bad reviews
| Delivery vs promised date | % of delivered orders | Avg review | % 1–2★ |
|---|---:|---:|---:|
| On time or early | 93.2 | 4.29 | 9.2 |
| 1–3 days late | 1.9 | 3.29 | 32.2 |
| 4–7 days late | 1.9 | 2.11 | 67.6 |
| 8+ days late | 3.0 | 1.70 | 79.1 |

![Reviews](results/charts/02_reviews_by_delivery.png)

Only 6.8% of orders (6,532) arrive late, but an order that is 8+ days late is **8.6× more likely** to get a 1–2★ review than one that arrives on time (79.1% vs 9.2%).

### 4. Reliability broke under peak volume
![Monthly](results/charts/03_monthly_on_time.png)

On-time delivery held at about 95–97% through most of 2017. It dropped to **87.6% in November 2017**, the Black Friday month and the busiest month in the data (7,544 orders), and fell further to **85.9% in Feb 2018 and 81.0% in Mar 2018**. It recovered from April 2018, and the median time to deliver fell from 13–14 days to 7–9 days.

### 5. Almost every customer buys once
A customer is a `customer_unique_id` (Olist issues a new `customer_id` for every order). Only delivered orders count (96,211), and a second order on the same day as the first is treated as a split basket, not loyalty.

| Segment | Customers | % customers | Revenue (R$, items + freight) | % revenue | Avg lifetime value (R$) |
|---|---:|---:|---:|---:|---:|
| One-time | 91,099 | 97.85 | 14,733,930 | 95.81 | 161.74 |
| Repeat (2+ buying days) | 2,005 | 2.15 | 643,880 | 4.19 | 321.14 |

Repeat customers are worth about **2× a one-time customer**, but only 2.15% of customers ever come back. The median gap to the second order is 74 days.

![Cohorts](results/charts/04_cohort_retention.png)

Retention didn't improve as the marketplace grew. Among complete cohorts, the share of new customers who bought again within 90 days peaked at **1.52% (2017-Q3)** and slipped to **1.17% (2018-Q1)**, while new-customer volume grew 4×. The 2018-Q2 and Q3 cohorts are partial because their 90-day window runs past the end of the data.

**So what (provisional):** the promise date is the lever. Late orders are a small share of volume but produce most of the 1–2★ reviews. Capacity planning before peak periods, and padding promised dates when the network is under strain, would protect ratings. The ~R$176k in "shipped but never delivered" orders points to a carrier-tracking and claims gap worth chasing. With about 98% of customers buying once, growth relies entirely on acquisition. A second-order programme (for example, a follow-up offer timed around the ~74-day gap after a good delivery) is low-hanging fruit. Even moving 90-day repeat from ~1.2% to 2.5% would roughly double the repeat segment.

## How to run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py   # ~62 MB into data/raw/
python -m pipeline.build_db       # builds data/olist.duckdb + runs quality checks
python -m report.build            # results/REPORT.md, results/csv/, results/charts/
pytest                            # offline tests on a tiny fixture
```

## Next steps
- Seller and category view: which sellers and categories drive late deliveries and cancellations.
- Final recommendations with owners, and limitations.
