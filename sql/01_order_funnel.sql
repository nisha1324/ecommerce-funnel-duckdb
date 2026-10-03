-- Q1. Order fulfilment funnel
-- Business question: of the orders customers place, how many make it through
-- each fulfilment milestone, and where do we lose them?
-- Stages use timestamps, not order_status, so an order counts at a stage if it
-- actually reached that milestone. Window: orders placed 2017-01 .. 2018-08.
WITH stages AS (
    SELECT
        COUNT(*)                                              AS placed,
        COUNT(order_approved_at)                              AS payment_approved,
        COUNT(order_delivered_carrier_date)                   AS handed_to_carrier,
        COUNT(order_delivered_customer_date)                  AS delivered
    FROM orders_clean
),
long AS (
    SELECT 1 AS step, 'Placed'             AS stage, placed            AS orders FROM stages
    UNION ALL SELECT 2, 'Payment approved',  payment_approved  FROM stages
    UNION ALL SELECT 3, 'Handed to carrier', handed_to_carrier FROM stages
    UNION ALL SELECT 4, 'Delivered',         delivered         FROM stages
)
SELECT
    step,
    stage,
    orders,
    ROUND(100.0 * orders / FIRST_VALUE(orders) OVER (ORDER BY step), 2)      AS pct_of_placed,
    LAG(orders) OVER (ORDER BY step) - orders                                 AS lost_vs_prev_step
FROM long
ORDER BY step;
