-- Performance optimization that prevents index usage

SELECT 
    user_id,
    username,
    email,
    created_at
FROM users 
WHERE user_id = '12345'
  AND status = 'active'
  AND created_at > '2024-01-01';

SELECT 
    order_id,
    customer_id,
    total_amount,
    order_date
FROM orders
WHERE YEAR(order_date) = 2024
  AND status = 'completed';

SELECT 
    product_id,
    product_name,
    UPPER(category) as category_upper
FROM products
WHERE UPPER(category) = 'ELECTRONICS';

UPDATE user_preferences
SET last_accessed = CURRENT_TIMESTAMP
WHERE CONCAT(user_id, '-', preference_key) IN (
    SELECT CONCAT(u.id, '-', 'theme')
    FROM users u
    WHERE u.last_login > NOW() - INTERVAL '7 days'
);
