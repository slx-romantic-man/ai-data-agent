#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将张三(user_001)的3个API迁移到管理员的系统API仓库

迁移内容：
1. weather_api → 天气类（大类）
2. alpha_vantage_stock → 股票类（大类）
3. geo → IP查询类（大类）

迁移步骤：
1. 读取 user_001.json
2. 为每个API创建对应的大类（parent_id=NULL）
3. 将API配置插入api_configs表
4. 为张三自动授权这3个API
5. 备份原文件
6. 更新向量数据库
"""

import asyncio
import json
import sys
import io
from datetime import datetime
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.access.database.connection import get_db
from app.access.database.models import (
    APICategory, APIConfig, UserAPIPermission, UserAccount
)
from app.utils.crypto_utils import encrypt_auth_config
from app.services.vector_store import VectorStore
from sqlalchemy import select


# API迁移配置
API_MIGRATIONS = [
    {
        "json_key": "weather_api",
        "category_name": "天气类",
        "category_description": "提供天气查询、空气质量、天气预报等相关API服务"
    },
    {
        "json_key": "alpha_vantage_stock",
        "category_name": "股票类",
        "category_description": "提供股票行情、K线数据、公司财报等金融数据API服务"
    },
    {
        "json_key": "geo",
        "category_name": "IP查询类",
        "category_description": "提供IP地址地理位置查询、归属地查询等服务"
    }
]


async def backup_user_config(user_id: str):
    """备份用户配置文件"""
    import shutil
    config_path = (
        project_root / "data" / "user_api_configs" / f"{user_id}.json"
    )
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = (
        project_root / "data" / "user_api_configs" /
        f"{user_id}.json.backup.{timestamp}"
    )

    if config_path.exists():
        shutil.copy2(config_path, backup_path)
        print(f"✓ 已备份配置文件: {backup_path}")
        return True
    else:
        print(f"✗ 配置文件不存在: {config_path}")
        return False


async def load_user_apis(user_id: str):
    """加载用户的API配置"""
    config_path = (
        project_root / "data" / "user_api_configs" / f"{user_id}.json"
    )

    if not config_path.exists():
        print(f"✗ 用户配置文件不存在: {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def get_admin_user_id(db):
    """获取管理员用户ID"""
    async with db.get_session() as session:
        result = await session.execute(
            select(UserAccount).where(UserAccount.role == 'admin').limit(1)
        )
        admin = result.scalar_one_or_none()
        if admin:
            return admin.id
        else:
            print("✗ 未找到管理员账号")
            return None


async def create_category(db, name: str, description: str, created_by: int):
    """创建API分类"""
    async with db.get_session() as session:
        # 检查分类是否已存在
        result = await session.execute(
            select(APICategory).where(APICategory.name == name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  分类已存在: {name} (ID: {existing.id})")
            return existing.id

        # 创建新分类
        category = APICategory(
            name=name,
            description=description,
            parent_id=None,  # 顶级分类
            sort_order=0,
            created_by=created_by
        )
        session.add(category)
        await session.commit()
        await session.refresh(category)

        print(f"  ✓ 创建分类: {name} (ID: {category.id})")
        return category.id


async def create_api_config(
    db, config_id: str, api_data: dict, category_id: int, created_by: int
):
    """创建API配置"""
    async with db.get_session() as session:
        # 检查API是否已存在
        result = await session.execute(
            select(APIConfig).where(APIConfig.config_id == config_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  API已存在: {config_id} (ID: {existing.id})")
            return existing.id

        # 加密认证配置
        encrypted_auth = encrypt_auth_config(api_data.get('auth', {}))

        # 创建API配置
        api_config = APIConfig(
            config_id=config_id,
            name=api_data.get('name', config_id),
            description=api_data.get('description', ''),
            base_url=api_data.get('base_url', ''),
            category_id=category_id,
            auth_type=api_data.get('auth', {}).get('type', 'none'),
            auth_config=encrypted_auth,
            endpoints=json.dumps(api_data.get('endpoints', {})),
            timeout=api_data.get('timeout', 30),
            retry_count=api_data.get('retry_count', 3),
            is_active=api_data.get('enabled', True),
            created_by=created_by
        )
        session.add(api_config)
        await session.commit()
        await session.refresh(api_config)

        print(f"  ✓ 创建API: {api_data.get('name')} (ID: {api_config.id})")
        return api_config.id


async def grant_permission_to_user(
    db, user_id: str, api_config_id: int, granted_by: int
):
    """为用户授权API"""
    async with db.get_session() as session:
        # 检查权限是否已存在
        result = await session.execute(
            select(UserAPIPermission).where(
                UserAPIPermission.user_id == user_id,
                UserAPIPermission.api_config_id == api_config_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status != 'active':
                existing.status = 'active'
                existing.granted_at = datetime.utcnow()
                await session.commit()
                msg = f"  ✓ 重新激活权限: user={user_id}, api_id={api_config_id}"
                print(msg)
            else:
                print(f"  权限已存在: user={user_id}, api_id={api_config_id}")
            return

        # 创建新权限
        permission = UserAPIPermission(
            user_id=user_id,
            api_config_id=api_config_id,
            status='active',
            granted_by=granted_by,
            granted_at=datetime.utcnow()
        )
        session.add(permission)
        await session.commit()

        print(f"  ✓ 授权成功: user={user_id}, api_id={api_config_id}")


async def update_vector_store(
    api_id: int, api_name: str, api_description: str, category_name: str
):
    """更新向量数据库"""
    try:
        from sentence_transformers import SentenceTransformer
        from app.config.settings import settings

        # 加载embedding模型
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        vector_store = VectorStore()

        # 生成embedding文本
        text = f"{category_name} - {api_name}: {api_description}"
        embedding = model.encode(text).tolist()

        # 存储到Qdrant
        vector_store.upsert(
            api_id=api_id,
            embedding=embedding,
            metadata={
                "name": api_name,
                "description": api_description,
                "category_path": category_name,
                "config_id": str(api_id)
            }
        )

        print(f"  ✓ 更新向量数据库: {api_name}")
    except Exception as e:
        print(f"  ⚠ 向量数据库更新失败: {e}")


async def main():
    """主函数"""
    print("=" * 60)
    print("数据迁移脚本：张三的API迁移到管理员系统API仓库")
    print("=" * 60)
    print()

    # 1. 备份配置文件
    print("[1/6] 备份用户配置文件...")
    if not await backup_user_config("user_001"):
        print("✗ 备份失败，终止迁移")
        return
    print()

    # 2. 加载用户API配置
    print("[2/6] 加载用户API配置...")
    user_apis = await load_user_apis("user_001")
    if not user_apis:
        print("✗ 加载失败，终止迁移")
        return
    print(f"✓ 找到 {len(user_apis)} 个API配置")
    print()

    # 3. 连接数据库
    print("[3/6] 连接数据库...")
    db = await get_db()
    admin_id = await get_admin_user_id(db)
    if not admin_id:
        print("✗ 未找到管理员账号，终止迁移")
        return
    print(f"✓ 管理员ID: {admin_id}")
    print()

    # 4. 迁移API
    print("[4/6] 迁移API到系统仓库...")
    migrated_apis = []

    for migration in API_MIGRATIONS:
        json_key = migration["json_key"]
        category_name = migration["category_name"]
        category_desc = migration["category_description"]

        if json_key not in user_apis:
            print(f"⚠ 跳过不存在的API: {json_key}")
            continue

        print(f"\n处理: {json_key} → {category_name}")

        # 创建分类
        category_id = await create_category(db, category_name, category_desc, admin_id)

        # 创建API配置
        api_data = user_apis[json_key]
        api_id = await create_api_config(db, json_key, api_data, category_id, admin_id)

        migrated_apis.append({
            "api_id": api_id,
            "config_id": json_key,
            "name": api_data.get('name', json_key),
            "description": api_data.get('description', ''),
            "category_name": category_name
        })

    print(f"\n✓ 成功迁移 {len(migrated_apis)} 个API")
    print()

    # 5. 为张三授权
    print("[5/6] 为张三授权迁移的API...")
    for api_info in migrated_apis:
        await grant_permission_to_user(db, "user_001", api_info["api_id"], admin_id)
    print()

    # 6. 更新向量数据库
    print("[6/6] 更新向量数据库...")
    for api_info in migrated_apis:
        await update_vector_store(
            api_info["api_id"],
            api_info["name"],
            api_info["description"],
            api_info["category_name"]
        )
    print()

    # 完成
    print("=" * 60)
    print("✓ 迁移完成！")
    print("=" * 60)
    print("\n迁移摘要：")
    for api_info in migrated_apis:
        print(f"  - {api_info['category_name']}: {api_info['name']}")
    print(f"\n总计: {len(migrated_apis)} 个API")
    print(f"用户 user_001 (张三) 已被授权访问这些API")


if __name__ == "__main__":
    asyncio.run(main())
