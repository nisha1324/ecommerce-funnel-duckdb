-- Q3. Late delivery and customer satisfaction
-- Business question: how often do we miss the delivery date promised at
-- checkout, and what does a late delivery do to the review score?
-- Delivered orders only; an order is late if it arrived after the estimated date
-- (compared by calendar day).
WITH delivered AS (
    SELECT
        o.order_id,
        DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS DATE),
                         CAST(o.order_delivered_customer_date AS DATE)) AS days_vs_promise
    FROM orders_clean o
    WHERE o.order_delivered_customer_date IS NOT NULL
),
review AS (
    -- a few orders have more than one review; keep the average
    SELECT order_id, AVG(review_score) AS score
    FROM order_reviews
    GROUP BY order_id
),
bucketed AS (
    SELECT
        CASE
            WHEN days_vs_promise <= 0  THEN '1. On time or early'
            WHEN days_vs_promise <= 3  THEN '2. 1-3 days late'
            WHEN days_vs_promise <= 7  THEN '3. 4-7 days late'
            ELSE                            '4. 8+ days late'
        END AS delivery_bucket,
        r.score
    FROM delivered d
    LEFT JOIN review r USING (order_id)
)
SELECT
    delivery_bucket,
    COUNT(*)                                              AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_of_delivered,
    ROUND(AVG(score), 2)                                  AS avg_review,
    ROUND(100.0 * AVG(CASE WHEN score <= 2 THEN 1 ELSE 0 END)
          FILTER (WHERE score IS NOT NULL), 1)            AS pct_1_2_star
FROM bucketed
GROUP BY delivery_bucket
ORDER BY delivery_bucket;
