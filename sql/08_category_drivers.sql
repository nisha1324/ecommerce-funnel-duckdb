-- Q8. Which product categories drive lateness and cancellations?
-- Business question: where should the ops team look first? Ranks categories
-- (50+ orders) by late-delivery and cancellation/unavailable rates, with the
-- share of all late orders each one accounts for.
-- An order belongs to the category of its first item; English names from the
-- Olist translation file (Portuguese name kept if no translation). Late rate is
-- over delivered orders; cancel rate over all orders.
WITH first_item AS (
    SELECT
        i.order_id,
        COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category
    FROM order_items i
    LEFT JOIN products p USING (product_id)
    LEFT JOIN category_translation t USING (product_category_name)
    WHERE i.order_item_id = 1
),
orders_cat AS (
    SELECT
        f.category,
        o.order_status IN ('canceled', 'unavailable')                       AS cancelled,
        CASE WHEN o.order_delivered_customer_date IS NOT NULL THEN
            CAST(o.order_delivered_customer_date AS DATE)
                > CAST(o.order_estimated_delivery_date AS DATE) END         AS late
    FROM orders_clean o
    JOIN first_item f USING (order_id)
)
SELECT
    category,
    COUNT(*)                                                                AS orders,
    SUM(late::INT)                                                          AS late_orders,
    ROUND(100.0 * AVG(late::INT), 1)                                        AS late_rate_pct,
    ROUND(100.0 * SUM(late::INT) / SUM(SUM(late::INT)) OVER (), 1)          AS pct_of_all_late,
    ROUND(100.0 * AVG(cancelled::INT), 2)                                   AS cancel_rate_pct
FROM orders_cat
GROUP BY category
HAVING COUNT(*) >= 50
ORDER BY late_orders DESC, orders DESC, category;  -- tie-breakers keep the order stable across DuckDB versions
