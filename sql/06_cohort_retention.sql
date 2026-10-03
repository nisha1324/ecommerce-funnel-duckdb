-- Q6. Quarterly cohorts: what share of new customers buy again within 90 days?
-- Business question: did retention improve as the marketplace grew?
-- Cohort = quarter of a customer's first delivered order. A 90-day window is used for every
-- cohort so they're comparable; cohorts whose window runs past the last purchase in the
-- data (2018-08-31) are flagged as incomplete.
WITH orders AS (
    SELECT cu.customer_unique_id                   AS customer,
           CAST(o.order_purchase_timestamp AS DATE) AS order_day
    FROM orders_clean o
    JOIN customers cu USING (customer_id)
    WHERE o.order_status = 'delivered'
),
firsts AS (
    SELECT customer, MIN(order_day) AS first_day
    FROM orders
    GROUP BY 1
),
returned AS (
    SELECT f.customer,
           f.first_day,
           BOOL_OR(o.order_day > f.first_day
                   AND o.order_day <= f.first_day + INTERVAL 90 DAY) AS back_in_90d
    FROM firsts f
    JOIN orders o USING (customer)
    GROUP BY 1, 2
)
SELECT
    STRFTIME(first_day, '%Y') || '-Q' || QUARTER(first_day)          AS cohort,
    COUNT(*)                                                         AS new_customers,
    COUNT(*) FILTER (WHERE back_in_90d)                              AS returned_90d,
    ROUND(100.0 * AVG(CASE WHEN back_in_90d THEN 1 ELSE 0 END), 2)   AS pct_returned_90d,
    MAX(first_day) + INTERVAL 90 DAY > DATE '2018-08-31'             AS window_incomplete
FROM returned
GROUP BY 1
ORDER BY 1;
