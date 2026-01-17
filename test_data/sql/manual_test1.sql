
BEGIN;

CREATE TABLE user_login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_login_history_user_timestamp 
ON user_login_history(user_id, login_timestamp DESC);

INSERT INTO user_login_history (user_id, login_timestamp, ip_address, success)
SELECT 
    user_id,
    created_at,
    ip_address,
    TRUE
FROM legacy_login_logs
WHERE created_at > NOW() - INTERVAL '90 days'
  AND user_id IS NOT NULL;

DROP TABLE legacy_login_logs;

ALTER TABLE users 
ADD COLUMN account_status VARCHAR(20) DEFAULT 'active';

ALTER TABLE users
ADD CONSTRAINT check_account_status 
CHECK (account_status IN ('active', 'suspended', 'deleted', 'pending'));

UPDATE users
SET account_status = 'deleted'
WHERE last_login < '2023-01-01'
   OR email_verified = FALSE;

TRUNCATE TABLE user_sessions CASCADE;

CREATE OR REPLACE VIEW active_users AS
SELECT 
    id,
    email,
    username,
    account_status,
    last_login
FROM users
WHERE account_status = 'active'
  AND deleted_at IS NULL;

CREATE INDEX idx_users_email_status ON users(email, account_status);

DELETE FROM user_preferences
WHERE user_id IN (
    SELECT id FROM users WHERE account_status = 'deleted'
);

ALTER TABLE users DROP COLUMN legacy_user_id;

DELETE FROM email_verification_tokens;

COMMIT;
