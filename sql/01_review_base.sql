-- One row per order that has a review. Window functions keep the LATEST review per order
-- and the highest-priced item's category as the order's main category.
WITH last_review AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) AS rn
  FROM order_reviews
),
item_rank AS (
  SELECT oi.order_id, oi.price, oi.freight_value, oi.seller_id, oi.product_id,
         ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.price DESC) AS rn
  FROM order_items oi
),
main_item AS (
  SELECT ir.order_id, COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category
  FROM item_rank ir
  LEFT JOIN products p ON ir.product_id = p.product_id
  LEFT JOIN category_translation t ON p.product_category_name = t.product_category_name
  WHERE ir.rn = 1
),
item_totals AS (
  SELECT order_id, COUNT(*) AS n_items, COUNT(DISTINCT seller_id) AS n_sellers,
         SUM(price) AS items_value, SUM(freight_value) AS freight
  FROM order_items GROUP BY order_id
)
SELECT lr.order_id, c.customer_unique_id, c.customer_state AS state,
       lr.review_score, lr.review_comment_message AS comment,
       o.order_status, o.order_purchase_timestamp AS purchased_at,
       julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date) AS days_vs_estimate,
       julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)      AS delivery_days,
       mi.category, it.n_items, it.n_sellers, it.items_value, it.freight
FROM last_review lr
JOIN orders o     ON lr.order_id = o.order_id
JOIN customers c  ON o.customer_id = c.customer_id
LEFT JOIN main_item mi ON lr.order_id = mi.order_id
LEFT JOIN item_totals it ON lr.order_id = it.order_id
WHERE lr.rn = 1;
