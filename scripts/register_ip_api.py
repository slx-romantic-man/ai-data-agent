"""
注册 Example IP 定位 API 到数据库
"""
import asyncio
from sqlalchemy import select
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.access.database.connection import get_db
from app.access.database.models import APIConfig, APICategory


async def register_ip_api():
    db = await get_db()
    async with db.get_session() as session:
        # 查找或创建"外部数据"分类
        result = await session.execute(
            select(APICategory).where(APICategory.name == "外部数据")
        )
        category = result.scalar_one_or_none()

        if not category:
            category = APICategory(
                name="外部数据",
                description="第三方外部数据API",
                sort_order=3
            )
            session.add(category)
            await session.flush()

        # 检查是否已存在
        result = await session.execute(
            select(APIConfig).where(APIConfig.config_id == "ip_location_api")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("Example IP API 已存在，跳过注册")
            return

        # 创建 IP 定位 API 配置
        ip_api = APIConfig(
            config_id="ip_location_api",
            name="Example IP 定位查询",
            description="查询 IP 地址的地理位置信息，包括国家、省份、城市等",
            base_url="https://api.example.com",
            auth_type="none",
            auth_config={},
            endpoints={
                "get_location": {
                    "path": "/api/iplocaltion",
                    "method": "GET",
                    "description": "根据 IP 地址查询地理位置",
                    "params_mapping": {
                        "ip": "ip"
                    },
                    "required_params": ["ip"],
                    "default_params": {},
                    "response_data_path": None,
                    "response_field_mapping": {}
                }
            },
            timeout=30,
            retry_count=3,
            is_system=False,
            is_active=True,
            category_id=category.id,
            owner_id=None
        )

        session.add(ip_api)
        await session.commit()

        print("✅ Example IP API 注册成功")
        print(f"   config_id: {ip_api.config_id}")
        print(f"   name: {ip_api.name}")
        print(f"   category_id: {ip_api.category_id}")

if __name__ == "__main__":
    asyncio.run(register_ip_api())
