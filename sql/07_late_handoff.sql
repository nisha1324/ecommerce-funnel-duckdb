-- Q7. Who causes late deliveries: the seller or the carrier?
-- Business question: when an order arrives after the promised date, did the
-- seller miss its hand-off deadline (shipping_limit_date) or was the carrier
-- leg slow? This decides whether to fix seller SLAs or logistics.
-- Delivered orders with a carrier hand-off date; for multi-item orders the
-- latest shipping limit is used. Days compared by calendar day.
WITH limits AS (
    SELECT order_id, MAX(shipping_limit_date) AS shipping_limit
    FROM order_items
    GROUP BY order_id
),
delivered AS (
    SELECT
        o.order_delivered_carrier_date > l.shipping_limit                   AS seller_late,
        CAST(o.order_delivered_customer_date AS DATE)
            > CAST(o.order_estimated_delivery_date AS DATE)                 AS late
    FROM orders_clean o
    JOIN limits l USING (order_id)
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_carrier_date IS NOT NULL
)
SELECT
    CASE WHEN seller_late THEN 'Seller missed hand-off deadline'
         ELSE 'Seller handed off on time' END                               AS seller_handoff,
    COUNT(*)                                                                AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                      AS pct_of_orders,
    SUM(late::INT)                                                          AS late_orders,
    ROUND(100.0 * AVG(late::INT), 1)                                        AS late_rate_pct,
    ROUND(100.0 * SUM(late::INT) / SUM(SUM(late::INT)) OVER (), 1)          AS pct_of_all_late
FROM delivered
GROUP BY seller_late
ORDER BY seller_late;
