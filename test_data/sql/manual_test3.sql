
CREATE INDEX CONCURRENTLY idx_posts_author_published 
ON posts(author_id, published_at DESC)
WHERE status = 'published';

CREATE INDEX CONCURRENTLY idx_comments_post_created
ON comments(post_id, created_at DESC);

ANALYZE posts;
ANALYZE comments;
ANALYZE users;

DROP INDEX idx_posts_created_at;

CREATE TABLE posts_2024_q4 PARTITION OF posts
FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

ALTER TABLE posts 
ALTER COLUMN title TYPE VARCHAR(100);

ALTER TABLE users
ADD COLUMN performance_tier VARCHAR(20);

ALTER TABLE users
ALTER COLUMN performance_tier SET NOT NULL;

CREATE MATERIALIZED VIEW trending_posts AS
SELECT 
    p.id,
    p.title,
    COUNT(DISTINCT c.id) as comment_count,
    COUNT(DISTINCT l.user_id) as like_count,
    (COUNT(DISTINCT c.id) + COUNT(DISTINCT l.user_id)) as engagement_score
FROM posts p
LEFT JOIN comments c ON p.id = c.post_id
LEFT JOIN likes l ON p.id = l.post_id
WHERE p.published_at > NOW() - INTERVAL '7 days'
GROUP BY p.id, p.title
ORDER BY engagement_score DESC
LIMIT 100;

CREATE INDEX idx_trending_engagement 
ON trending_posts(engagement_score DESC);

ALTER TABLE users RENAME COLUMN username TO user_name;

ALTER TABLE comments DROP CONSTRAINT comments_post_id_fkey;

ALTER TABLE posts ADD COLUMN author_name VARCHAR(255);
ALTER TABLE posts ADD COLUMN author_email VARCHAR(255);

UPDATE posts
SET 
    author_name = users.name,
    author_email = users.email
FROM users
WHERE posts.author_id = users.id;

ALTER TABLE posts DROP COLUMN created_by;
ALTER TABLE posts DROP COLUMN modified_by;
ALTER TABLE posts DROP COLUMN modified_at;

CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_update_timestamp
BEFORE UPDATE ON posts
FOR EACH ROW
EXECUTE FUNCTION update_modified_timestamp();

ALTER SEQUENCE posts_id_seq RESTART WITH 1000;

REFRESH MATERIALIZED VIEW CONCURRENTLY trending_posts;

DROP TABLE IF EXISTS temp_migration_backup_20241201;
DROP TABLE IF EXISTS temp_data_fix_20241210;