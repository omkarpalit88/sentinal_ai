
CREATE TABLE IF NOT EXISTS orders_archive_2024 (
    LIKE orders INCLUDING ALL
);

INSERT INTO orders_archive_2024
SELECT *
FROM orders
WHERE status = 'completed'
  AND created_at < NOW() - INTERVAL '2 years'
  AND archived = FALSE;

UPDATE orders
SET archived = TRUE, archived_at = CURRENT_TIMESTAMP
WHERE id IN (SELECT id FROM orders_archive_2024);

DELETE FROM orders
WHERE archived = TRUE
  AND created_at < NOW() - INTERVAL '2 years';

DELETE FROM shopping_carts
WHERE created_at < NOW() - INTERVAL '30 days'
  AND status = 'abandoned'
LIMIT 5000;  

DELETE FROM payment_transactions
WHERE created_at < '2022-01-01';

UPDATE products
SET stock_count = stock_count - reserved_count
WHERE reserved_count > 0
  AND last_inventory_sync < NOW() - INTERVAL '1 hour';

DELETE FROM customer_addresses
WHERE customer_id IN (
    SELECT id FROM customers 
    WHERE last_order_date < NOW() - INTERVAL '1 year'
);

UPDATE products
SET 
    price = price * 0.5,
    sale_price = price * 0.5,
    on_sale = TRUE
WHERE category IN ('electronics', 'clothing', 'home')
  AND price > 10;

UPDATE coupon_codes
SET active = FALSE, deactivated_at = CURRENT_TIMESTAMP
WHERE expiry_date < CURRENT_DATE
  AND active = TRUE;

DELETE FROM product_reviews
WHERE created_at < NOW() - INTERVAL '3 years'
   OR rating < 2;

DROP TABLE IF EXISTS test_accounts;

UPDATE customers
SET 
    email = CONCAT('deleted_', id, '@anonymized.com'),
    phone = NULL,
    name = 'Deleted User',
    address = NULL
WHERE last_login < NOW() - INTERVAL '2 years'
  AND account_status != 'premium';

VACUUM ANALYZE orders;
VACUUM ANALYZE products;
VACUUM ANALYZE customers;

CREATE INDEX CONCURRENTLY idx_orders_archived 
ON orders(archived, created_at) 
WHERE archived = FALSE;
