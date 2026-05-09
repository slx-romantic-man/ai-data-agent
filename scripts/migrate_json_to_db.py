"""
数据迁移脚本 - 将 JSON 文件数据导入数据库

运行方式:
    python scripts/migrate_json_to_db.py

幂等设计: 可重复执行，已存在的数据会被跳过
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.access.database.connection import get_db
from app.access.database.models import (
    UserAccount, UserQuota, CreditLog, Conversation, Message, ApiConfig,
    UserApiConfig
)


# 数据目录
DATA_DIR = project_root / "data"


async def migrate_users():
    """迁移 users.json"""
    print("正在迁移用户数据...")

    users_file = DATA_DIR / "users.json"
    if not users_file.exists():
        print(f"  文件不存在: {users_file}")
        return 0

    with open(users_file, "r", encoding="utf-8") as f:
        users_data = json.load(f)

    db = await get_db()
    migrated = 0

    async with db.get_session() as session:
        for login_id, user_data in users_data.items():
            # 检查是否已存在 (用 login_id 检查)
            result = await session.execute(
                select(UserAccount).where(UserAccount.login_id == login_id)
            )
            if result.scalar_one_or_none():
                continue

            # 创建用户
            user = UserAccount(
                user_id=user_data.get("user_id", login_id),
                login_id=login_id,  # 存储 login_id
                username=user_data.get("username", login_id),
                password=user_data.get("password", ""),
                role=user_data.get("role", "employee"),
                department=user_data.get("department"),
                business_line=user_data.get("business_line"),
                is_active=True,
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(user_data["updated_at"]) if user_data.get("updated_at") else datetime.now(),
            )
            session.add(user)
            await session.flush()

            # 创建配额
            quota_data = user_data.get("quota", {})
            quota = UserQuota(
                user_id=user.id,
                daily_limit=quota_data.get("daily_limit", 100),
                current_balance=quota_data.get("current_balance", 100),
                last_reset=datetime.fromisoformat(quota_data["last_reset"]) if quota_data.get("last_reset") else datetime.now(),
            )
            session.add(quota)
            migrated += 1

    print(f"  已迁移 {migrated} 个用户")
    return migrated


async def migrate_credit_logs():
    """迁移 credit_logs.json"""
    print("正在迁移积分日志...")

    logs_file = DATA_DIR / "credit_logs.json"
    if not logs_file.exists():
        print(f"  文件不存在: {logs_file}")
        return 0

    with open(logs_file, "r", encoding="utf-8") as f:
        logs_data = json.load(f)

    db = await get_db()
    migrated = 0

    async with db.get_session() as session:
        for log_data in logs_data:
            # 创建日志记录
            log = CreditLog(
                user_id=log_data.get("user_id", ""),
                username=log_data.get("username", ""),
                query=log_data.get("query", "")[:500] if log_data.get("query") else None,
                session_id=log_data.get("session_id"),
                input_tokens=log_data.get("input_tokens", 0),
                output_tokens=log_data.get("output_tokens", 0),
                total_tokens=log_data.get("total_tokens", 0),
                credits_deducted=log_data.get("credits_deducted", 0),
                balance_after=log_data.get("balance_after", 0),
                created_at=datetime.fromisoformat(log_data["timestamp"]) if log_data.get("timestamp") else datetime.now(),
            )
            session.add(log)
            migrated += 1

    print(f"  已迁移 {migrated} 条积分日志")
    return migrated


async def migrate_conversations():
    """迁移 conversations/*.json"""
    print("正在迁移对话历史...")

    conv_dir = DATA_DIR / "conversations"
    if not conv_dir.exists():
        print(f"  目录不存在: {conv_dir}")
        return 0, 0

    db = await get_db()
    conv_count = 0
    msg_count = 0

    async with db.get_session() as session:
        # 构建用户ID映射：user_id (string) -> database id (int)
        result = await session.execute(select(UserAccount))
        users = result.scalars().all()
        user_id_map = {u.user_id: u.id for u in users}

        for conv_file in conv_dir.glob("*.json"):
            with open(conv_file, "r", encoding="utf-8") as f:
                conversations_data = json.load(f)

            user_login = conv_file.stem  # 文件名是用户登录ID

            for conv_data in conversations_data:
                # 检查是否已存在
                result = await session.execute(
                    select(Conversation).where(Conversation.id == conv_data.get("id"))
                )
                if result.scalar_one_or_none():
                    continue

                # 获取用户的数据库ID
                db_user_id = user_id_map.get(user_login)

                # 创建对话
                conv = Conversation(
                    id=conv_data.get("id"),
                    user_id=db_user_id,  # 使用数据库外键ID
                    username=conv_data.get("user_id", user_login),
                    title=conv_data.get("title", ""),
                    created_at=datetime.fromisoformat(conv_data["created_at"]) if conv_data.get("created_at") else datetime.now(),
                    updated_at=datetime.fromisoformat(conv_data["updated_at"]) if conv_data.get("updated_at") else datetime.now(),
                )
                session.add(conv)
                await session.flush()
                conv_count += 1

                # 创建消息
                for msg_data in conv_data.get("messages", []):
                    msg = Message(
                        conversation_id=conv.id,
                        role=msg_data.get("role", "user"),
                        content=msg_data.get("content"),
                        data=msg_data.get("data"),
                        created_at=datetime.fromisoformat(msg_data["timestamp"]) if msg_data.get("timestamp") else datetime.now(),
                    )
                    session.add(msg)
                    msg_count += 1

    print(f"  已迁移 {conv_count} 个对话, {msg_count} 条消息")
    return conv_count, msg_count


async def migrate_api_configs():
    """迁移 api_configs.json"""
    print("正在迁移 API 配置...")

    api_file = DATA_DIR / "api_configs.json"
    if not api_file.exists():
        print(f"  文件不存在: {api_file}")
        return 0

    with open(api_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            print("  文件为空")
            return 0
        api_data = json.loads(content)

    if not api_data:
        print("  无 API 配置数据")
        return 0

    db = await get_db()
    migrated = 0

    async with db.get_session() as session:
        # 如果是字典格式
        if isinstance(api_data, dict):
            for config_id, config in api_data.items():
                result = await session.execute(
                    select(ApiConfig).where(ApiConfig.config_id == config_id)
                )
                if result.scalar_one_or_none():
                    continue

                api = ApiConfig(
                    config_id=config_id,
                    name=config.get("name", config_id),
                    description=config.get("description"),
                    base_url=config.get("base_url"),
                    auth_type=config.get("auth", {}).get("type"),
                    auth_config=config.get("auth"),
                    endpoints=config.get("endpoints"),
                    timeout=config.get("timeout", 30),
                    retry_count=config.get("retry_count", 3),
                    is_system=config.get("is_system", False),
                    is_active=True,
                )
                session.add(api)
                migrated += 1

    print(f"  已迁移 {migrated} 个 API 配置")
    return migrated


async def migrate_user_api_configs():
    """迁移 user_api_configs/*.json"""
    print("正在迁移用户API配置...")

    user_api_dir = DATA_DIR / "user_api_configs"
    if not user_api_dir.exists():
        print(f"  目录不存在: {user_api_dir}")
        return 0

    db = await get_db()
    migrated = 0

    async with db.get_session() as session:
        for config_file in user_api_dir.glob("*.json"):
            user_id = config_file.stem  # 文件名是用户ID

            with open(config_file, "r", encoding="utf-8") as f:
                user_apis_data = json.load(f)

            for api_id, api_config in user_apis_data.items():
                # 检查是否已存在
                result = await session.execute(
                    select(UserApiConfig).where(
                        UserApiConfig.user_id == user_id,
                        UserApiConfig.api_config_id == api_id
                    )
                )
                if result.scalar_one_or_none():
                    continue

                # 创建用户API配置
                user_api = UserApiConfig(
                    user_id=user_id,
                    api_config_id=api_id,
                    custom_config=api_config,
                )
                session.add(user_api)
                migrated += 1

    print(f"  已迁移 {migrated} 个用户API配置")
    return migrated


async def backup_json_files():
    """备份 JSON 文件"""
    print("正在备份 JSON 文件...")

    backup_suffix = ".bak"

    files_to_backup = [
        DATA_DIR / "users.json",
        DATA_DIR / "credit_logs.json",
        DATA_DIR / "api_configs.json",
    ]

    for f in files_to_backup:
        if f.exists():
            backup_path = f.with_suffix(f.suffix + backup_suffix)
            if not backup_path.exists():
                import shutil
                shutil.copy2(f, backup_path)
                print(f"  已备份: {f.name} -> {backup_path.name}")
            else:
                print(f"  备份已存在: {backup_path.name}")

    # 备份 conversations 目录
    conv_dir = DATA_DIR / "conversations"
    if conv_dir.exists():
        backup_dir = DATA_DIR / "conversations_backup"
        if not backup_dir.exists():
            import shutil
            shutil.copytree(conv_dir, backup_dir)
            print(f"  已备份: conversations/ -> conversations_backup/")
        else:
            print(f"  备份已存在: conversations_backup/")

    print("备份完成")


async def main():
    """主函数"""
    print("=" * 50)
    print("AI Data Agent 数据迁移")
    print("=" * 50)
    print()

    total_users = 0
    total_logs = 0
    total_convs = 0
    total_msgs = 0
    total_apis = 0
    total_user_apis = 0

    try:
        # 迁移数据
        total_users = await migrate_users()
        total_logs = await migrate_credit_logs()
        total_convs, total_msgs = await migrate_conversations()
        total_apis = await migrate_api_configs()
        total_user_apis = await migrate_user_api_configs()

        # 备份原文件
        print()
        await backup_json_files()

        print()
        print("=" * 50)
        print("迁移完成！")
        print(f"  - 用户: {total_users}")
        print(f"  - 积分日志: {total_logs}")
        print(f"  - 对话: {total_convs}")
        print(f"  - 消息: {total_msgs}")
        print(f"  - API配置: {total_apis}")
        print(f"  - 用户API配置: {total_user_apis}")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())