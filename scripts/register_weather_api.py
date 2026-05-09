"""
注册 WeatherAPI 天气 API 到数据库
"""
import asyncio
from sqlalchemy import select
from app.access.database.connection import get_db
from app.access.database.models import APIConfig, APICategory


async def register_weather_api():
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
            select(APIConfig).where(APIConfig.config_id == "weather_api")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("WeatherAPI 已存在，跳过注册")
            return

        # 创建 WeatherAPI 配置
        weather_api = APIConfig(
            config_id="weather_api",
            name="WeatherAPI 天气查询",
            description="查询全球城市实时天气数据，包括温度、湿度、风速等信息",
            base_url="http://api.weatherapi.com",
            auth_type="none",
            auth_config={},
            endpoints={
                "get_weather": {
                    "path": "/v1/current.json",
                    "method": "GET",
                    "description": "获取指定城市的实时天气数据",
                    "params_mapping": {
                        "key": "key",
                        "q": "q"
                    },
                    "required_params": ["key", "q"],
                    "default_params": {
                        "key": "your-weather-api-key"
                    },
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

        session.add(weather_api)
        await session.commit()

        print("✅ WeatherAPI 注册成功")
        print(f"   config_id: {weather_api.config_id}")
        print(f"   name: {weather_api.name}")
        print(f"   category_id: {weather_api.category_id}")

if __name__ == "__main__":
    asyncio.run(register_weather_api())
