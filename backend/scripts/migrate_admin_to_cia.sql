-- =========================================================
-- 迁移脚本：将 admin 账号的权限和配额复制到 CIA 用户
-- 目标用户：sunliangxing@chanjet.com (login_id='sunliangxing')
-- 源用户：admin (login_id='admin')
-- =========================================================
-- 此脚本需要在 RDS MySQL 8.0 上执行
-- 连接方式：通过阿里云 DMS 或 mysql 命令行

-- -----------------------------------------------------------
-- 1. 确认目标用户存在（执行前检查）
-- -----------------------------------------------------------
SELECT id, user_id, login_id, username, email, role, auth_type
FROM user_accounts
WHERE login_id = 'sunliangxing';

-- -----------------------------------------------------------
-- 2. 确认源用户（admin）的数据
-- -----------------------------------------------------------
SELECT * FROM user_accounts WHERE login_id = 'admin';
SELECT * FROM user_quotas WHERE user_id = 1;
SELECT * FROM user_api_permissions WHERE user_id = 'admin';

-- -----------------------------------------------------------
-- 3. 执行迁移（以下 3 步）
-- -----------------------------------------------------------

-- 3.1 更新用户角色和用户名
UPDATE user_accounts
SET role = 'admin',
    username = '管理员'
WHERE login_id = 'sunliangxing';

-- 3.2 更新配额为无限
UPDATE user_quotas
SET daily_limit = -1,
    current_balance = -1,
    last_reset = NOW(),
    updated_at = NOW()
WHERE user_id = 22;  -- sunliangxing 的 account id

-- 3.3 复制 API 权限（只复制不存在的，避免重复）
INSERT INTO user_api_permissions
    (user_id, api_config_id, source, status, auth_values, custom_params,
     granted_by, granted_at, activated_at, updated_at)
SELECT
    'sunliangxing',
    a.api_config_id,
    a.source,
    a.status,
    a.auth_values,
    a.custom_params,
    a.granted_by,
    NOW(),
    NOW(),
    NOW()
FROM user_api_permissions a
LEFT JOIN user_api_permissions b ON b.user_id = 'sunliangxing' AND b.api_config_id = a.api_config_id
WHERE a.user_id = 'admin'
  AND b.id IS NULL;

-- -----------------------------------------------------------
-- 4. 验证结果
-- -----------------------------------------------------------
SELECT id, login_id, username, role, auth_type FROM user_accounts WHERE login_id = 'sunliangxing';
SELECT * FROM user_quotas WHERE user_id = 22;
SELECT * FROM user_api_permissions WHERE user_id = 'sunliangxing';
