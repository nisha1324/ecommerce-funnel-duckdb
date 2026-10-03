-- Q2. Where the lost orders end up, and the revenue at stake
-- Business question: for orders that never reached the customer, what status
-- did they stall in, and how much item value (price + freight) did they carry?
WITH order_value AS (
    SELECT order_id, SUM(price + freight_value) AS value_brl
    FROM order_items
    GROUP BY order_id
)
SELECT
    o.order_status,
    COUNT(*)                                     AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_lost,
    COUNT(v.order_id)                            AS orders_with_items,
    ROUND(COALESCE(SUM(v.value_brl), 0), 0)      AS value_brl
FROM orders_clean o
LEFT JOIN order_value v USING (order_id)
WHERE o.order_delivered_customer_date IS NULL
GROUP BY o.order_status
ORDER BY orders DESC;
