"""
数据库初始化脚本 - 创建数据库和表结构

运行方式:
    python scripts/init_database.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.config.settings import settings
from app.access.database.connection import Base, get_engine_for_init
from app.access.database import models  # noqa: F401, 导入所有模型


async def create_database():
    """创建数据库（如果不存在）"""
    import aiomysql

    # 解析数据库连接信息
    db_url = settings.DATABASE_URL
    # 格式: mysql+aiomysql://user:password@host:port/database
    parts = db_url.replace("mysql+aiomysql://", "").split("/")
    db_name = parts[1]
    conn_parts = parts[0].split("@")
    user_pass = conn_parts[0].split(":")
    host_port = conn_parts[1].split(":")

    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306

    print(f"连接 MySQL 服务器 ({host}:{port})...")

    # 连接到 MySQL 服务器（不指定数据库）
    conn = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )

    async with conn.cursor() as cur:
        # 创建数据库（如果不存在）
        await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"数据库 '{db_name}' 已创建或已存在")

    conn.close()
    print("数据库创建完成")


async def create_tables():
    """创建所有表"""
    print("正在创建表结构...")

    engine = await get_engine_for_init()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("表结构创建完成")


async def main():
    """主函数"""
    print("=" * 50)
    print("AI Data Agent 数据库初始化")
    print("=" * 50)

    print(f"\n数据库 URL: {settings.DATABASE_URL}")
    print()

    try:
        # 步骤1: 创建数据库
        await create_database()
        print()

        # 步骤2: 创建表
        await create_tables()
        print()

        print("=" * 50)
        print("初始化完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())