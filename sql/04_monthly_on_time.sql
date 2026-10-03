-- Q4. Monthly volume and on-time delivery rate
-- Business question: did delivery reliability keep up as order volume grew?
SELECT
    DATE_TRUNC('month', order_purchase_timestamp)::DATE              AS month,
    COUNT(*)                                                         AS orders_placed,
    COUNT(order_delivered_customer_date)                             AS orders_delivered,
    ROUND(100.0 * AVG(CASE
        WHEN CAST(order_delivered_customer_date AS DATE)
             <= CAST(order_estimated_delivery_date AS DATE) THEN 1 ELSE 0 END)
        FILTER (WHERE order_delivered_customer_date IS NOT NULL), 1) AS on_time_pct,
    ROUND(MEDIAN(DATE_DIFF('day', order_purchase_timestamp,
                           order_delivered_customer_date)), 1)       AS median_days_to_deliver
FROM orders_clean
GROUP BY 1
ORDER BY 1;
