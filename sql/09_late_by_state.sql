-- Q9. Where do on-time hand-offs still arrive late? (carrier leg by state)
-- Business question: most late orders left the seller on time, so which
-- delivery destinations does the carrier leg struggle with, and is the
-- promised date padded enough there?
-- Delivered orders where the seller met its hand-off deadline; states with
-- 500+ such orders. Days compared by calendar day.
WITH limits AS (
    SELECT order_id, MAX(shipping_limit_date) AS shipping_limit
    FROM order_items
    GROUP BY order_id
),
carrier_leg AS (
    SELECT
        c.customer_state                                                    AS state,
        DATE_DIFF('day', CAST(o.order_delivered_carrier_date AS DATE),
                         CAST(o.order_delivered_customer_date AS DATE))     AS transit_days,
        DATE_DIFF('day', CAST(o.order_purchase_timestamp AS DATE),
                         CAST(o.order_estimated_delivery_date AS DATE))     AS promised_days,
        CAST(o.order_delivered_customer_date AS DATE)
            > CAST(o.order_estimated_delivery_date AS DATE)                 AS late
    FROM orders_clean o
    JOIN limits l USING (order_id)
    JOIN customers c USING (customer_id)
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_carrier_date IS NOT NULL
      AND o.order_delivered_carrier_date <= l.shipping_limit
)
SELECT
    state,
    COUNT(*)                                                                AS orders,
    ROUND(MEDIAN(transit_days), 1)                                          AS median_transit_days,
    ROUND(MEDIAN(promised_days), 1)                                         AS median_promised_days,
    SUM(late::INT)                                                          AS late_orders,
    ROUND(100.0 * AVG(late::INT), 1)                                        AS late_rate_pct,
    ROUND(100.0 * SUM(late::INT) / SUM(SUM(late::INT)) OVER (), 1)          AS pct_of_late
FROM carrier_leg
GROUP BY state
HAVING COUNT(*) >= 500
ORDER BY late_rate_pct DESC;
