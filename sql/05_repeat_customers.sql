-- Q5. How many customers come back, and how fast?
-- Business question: is growth driven by loyal customers or by constant new acquisition?
-- A customer is a customer_unique_id (customer_id changes on every order). Only delivered
-- orders count. A "repeat" is a later order on a different day, so a basket split into
-- several orders at one checkout isn't counted as loyalty.
WITH orders AS (
    SELECT cu.customer_unique_id                   AS customer,
           o.order_id,
           CAST(o.order_purchase_timestamp AS DATE) AS order_day
    FROM orders_clean o
    JOIN customers cu USING (customer_id)
    WHERE o.order_status = 'delivered'
),
value AS (
    SELECT order_id, SUM(price + freight_value) AS order_value
    FROM order_items
    GROUP BY 1
),
per_customer AS (
    SELECT customer,
           COUNT(DISTINCT order_day)                       AS buying_days,
           MIN(order_day)                                  AS first_day,
           MIN(order_day) FILTER (WHERE order_day > first) AS second_day,
           SUM(v.order_value)                              AS lifetime_value
    FROM (SELECT *, MIN(order_day) OVER (PARTITION BY customer) AS first FROM orders) o
    LEFT JOIN value v USING (order_id)
    GROUP BY 1
)
SELECT
    CASE WHEN buying_days = 1 THEN 'One-time' ELSE 'Repeat (2+ buying days)' END AS segment,
    COUNT(*)                                                            AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                  AS pct_customers,
    ROUND(SUM(lifetime_value), 0)                                       AS revenue,
    ROUND(100.0 * SUM(lifetime_value) / SUM(SUM(lifetime_value)) OVER (), 2) AS pct_revenue,
    ROUND(AVG(lifetime_value), 2)                                       AS avg_lifetime_value,
    MEDIAN(DATE_DIFF('day', first_day, second_day))                     AS median_days_to_2nd_order
FROM per_customer
GROUP BY 1
ORDER BY 1;
