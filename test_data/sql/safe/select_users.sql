-- Safe SQL: Simple SELECT query
SELECT id, name, email
FROM users
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 100;
