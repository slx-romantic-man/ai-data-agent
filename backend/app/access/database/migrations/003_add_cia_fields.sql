-- AI Data Agent CIA Login Support Migration
-- Version: 003
-- Description: Add CIA login fields to user_accounts table

SET @dbname = DATABASE();

-- 添加 email 字段
SET @col_email = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'user_accounts' AND COLUMN_NAME = 'email');
SET @sql_email = IF(@col_email = 0, 'ALTER TABLE user_accounts ADD COLUMN email VARCHAR(100) NULL AFTER username', 'SELECT 1');
PREPARE stmt_email FROM @sql_email;
EXECUTE stmt_email;
DEALLOCATE PREPARE stmt_email;

-- 添加 phone 字段
SET @col_phone = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'user_accounts' AND COLUMN_NAME = 'phone');
SET @sql_phone = IF(@col_phone = 0, 'ALTER TABLE user_accounts ADD COLUMN phone VARCHAR(20) NULL AFTER email', 'SELECT 1');
PREPARE stmt_phone FROM @sql_phone;
EXECUTE stmt_phone;
DEALLOCATE PREPARE stmt_phone;

-- 添加 avatar_url 字段
SET @col_avatar = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'user_accounts' AND COLUMN_NAME = 'avatar_url');
SET @sql_avatar = IF(@col_avatar = 0, 'ALTER TABLE user_accounts ADD COLUMN avatar_url VARCHAR(500) NULL AFTER phone', 'SELECT 1');
PREPARE stmt_avatar FROM @sql_avatar;
EXECUTE stmt_avatar;
DEALLOCATE PREPARE stmt_avatar;

-- 添加 auth_type 字段
SET @col_auth = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'user_accounts' AND COLUMN_NAME = 'auth_type');
SET @sql_auth = IF(@col_auth = 0, "ALTER TABLE user_accounts ADD COLUMN auth_type VARCHAR(20) DEFAULT 'local' COMMENT 'local/cia' AFTER avatar_url", 'SELECT 1');
PREPARE stmt_auth FROM @sql_auth;
EXECUTE stmt_auth;
DEALLOCATE PREPARE stmt_auth;

-- 为现有用户设置默认 email（如 login_id 是邮箱格式）
UPDATE user_accounts SET email = login_id WHERE login_id LIKE '%@%' AND email IS NULL;

-- 为现有用户设置默认 auth_type
UPDATE user_accounts SET auth_type = 'local' WHERE auth_type IS NULL;

-- 创建 email 索引
CREATE INDEX idx_email ON user_accounts(email);
