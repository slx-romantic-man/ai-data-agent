-- AI Data Agent Permission System Migration
-- Version: 002
-- Description: Creates tables for API permission management system

-- API 分类树（邻接表，不限层级）
CREATE TABLE IF NOT EXISTS api_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    parent_id INT NULL,
    sort_order INT DEFAULT 0,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES api_categories(id) ON DELETE CASCADE,
    INDEX idx_parent_id (parent_id),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 扩展现有 api_configs 表（MySQL 不支持 ADD COLUMN IF NOT EXISTS）
-- 使用 INFORMATION_SCHEMA 检查列是否存在
SET @dbname = DATABASE();

SET @col1 = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'api_configs' AND COLUMN_NAME = 'category_id');
SET @sql1 = IF(@col1 = 0, 'ALTER TABLE api_configs ADD COLUMN category_id INT NULL', 'SELECT 1');
PREPARE stmt1 FROM @sql1;
EXECUTE stmt1;
DEALLOCATE PREPARE stmt1;

SET @col2 = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'api_configs' AND COLUMN_NAME = 'is_active');
SET @sql2 = IF(@col2 = 0, 'ALTER TABLE api_configs ADD COLUMN is_active BOOLEAN DEFAULT TRUE', 'SELECT 1');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

SET @col3 = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = 'api_configs' AND COLUMN_NAME = 'auth_config');
SET @sql3 = IF(@col3 = 0, "ALTER TABLE api_configs ADD COLUMN auth_config TEXT NULL COMMENT '加密后的认证信息'", 'SELECT 1');
PREPARE stmt3 FROM @sql3;
EXECUTE stmt3;
DEALLOCATE PREPARE stmt3;

-- auth_config 存储加密后的认证信息（含 Key）
-- 原始结构示例：{"type": "api_key", "header": "X-API-Key", "value": "sk-xxx"}

-- 添加分类外键约束
ALTER TABLE api_configs
    ADD CONSTRAINT fk_api_category
    FOREIGN KEY (category_id) REFERENCES api_categories(id) ON DELETE SET NULL;

-- 创建分类索引（MySQL 不支持 CREATE INDEX IF NOT EXISTS，用 IGNORE 跳过重复）
CREATE INDEX idx_api_configs_category ON api_configs(category_id);
CREATE INDEX idx_api_configs_is_active ON api_configs(is_active);

-- 用户 API 权限表
CREATE TABLE IF NOT EXISTS user_api_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL COMMENT '用户ID (对应 user_accounts.user_id)',
    api_config_id INT NOT NULL COMMENT 'API配置ID',
    source VARCHAR(20) DEFAULT 'admin' COMMENT '权限来源: admin, self, etc.',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending, active, disabled',
    auth_values JSON NULL COMMENT '用户自定义的认证值',
    custom_params JSON NULL COMMENT '用户自定义参数',
    granted_by INT NULL COMMENT '授权人ID',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '授权时间',
    activated_at TIMESTAMP NULL COMMENT '激活时间',
    disabled_by INT NULL COMMENT '禁用人ID',
    disabled_at TIMESTAMP NULL COMMENT '禁用时间',
    disabled_reason VARCHAR(500) NULL COMMENT '禁用原因',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (api_config_id) REFERENCES api_configs(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_api (user_id, api_config_id),
    INDEX idx_user_id (user_id),
    INDEX idx_api_config_id (api_config_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- API 调用日志
CREATE TABLE IF NOT EXISTS api_call_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NULL COMMENT '用户ID',
    api_config_id INT NULL COMMENT 'API配置ID',
    permission_id INT NULL COMMENT '权限记录ID',
    conversation_id VARCHAR(100) NULL COMMENT '会话ID',
    status VARCHAR(20) NULL COMMENT '调用状态: success, failed, timeout',
    response_time_ms INT NULL COMMENT '响应时间(毫秒)',
    error_message TEXT NULL COMMENT '错误信息',
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '调用时间',
    FOREIGN KEY (api_config_id) REFERENCES api_configs(id) ON DELETE SET NULL,
    INDEX idx_user_called (user_id, called_at),
    INDEX idx_api_called (api_config_id, called_at),
    INDEX idx_conversation_id (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户权限索引
CREATE INDEX idx_user_api_perm_user ON user_api_permissions(user_id);
CREATE INDEX idx_user_api_perm_status ON user_api_permissions(status);