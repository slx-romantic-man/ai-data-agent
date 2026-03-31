"""
F-23: 三个外部 API 的 RBAC 权限隔离验证
测试用户级别的 API 权限隔离机制
"""
import asyncio
import sys
from pathlib import Path

# 添加正确的路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.user import User
from app.models.api_config import APIConfig
from app.models.api_permission import APIPermission
from app.core.security import get_password_hash

async def setup_test_users():
    """创建测试用户"""
    async for db in get_db():
        # 清理旧测试数据
        await db.execute(delete(APIPermission).where(
            APIPermission.user_id.in_([
                (await db.execute(select(User.id).where(User.username == "user_a"))).scalar(),
                (await db.execute(select(User.id).where(User.username == "user_b"))).scalar()
            ])
        ))
        await db.execute(delete(User).where(User.username.in_(["user_a", "user_b"])))
        await db.commit()

        # 创建 user_a
        user_a = User(
            username="user_a",
            email="user_a@test.com",
            hashed_password=get_password_hash("test123"),
            full_name="Test User A",
            is_active=True
        )
        db.add(user_a)

        # 创建 user_b
        user_b = User(
            username="user_b",
            email="user_b@test.com",
            hashed_password=get_password_hash("test123"),
            full_name="Test User B",
            is_active=True
        )
        db.add(user_b)
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)

        print(f"✅ 创建用户: user_a (ID: {user_a.id}), user_b (ID: {user_b.id})")
        return user_a.id, user_b.id

async def assign_permissions(user_a_id, user_b_id):
    """分配差异化权限"""
    async for db in get_db():
        # 获取三个 API 的 ID
        stock_api = (await db.execute(
            select(APIConfig).where(APIConfig.config_id == "alpha_vantage_stock")
        )).scalar_one_or_none()

        weather_api = (await db.execute(
            select(APIConfig).where(APIConfig.config_id == "weather_api")
        )).scalar_one_or_none()

        ip_api = (await db.execute(
            select(APIConfig).where(APIConfig.config_id == "ip_location_api")
        )).scalar_one_or_none()

        if not all([stock_api, weather_api, ip_api]):
            print("❌ 未找到全部三个 API，请先注册")
            return False

        # user_a: 只有股票 API 权限
        perm_a = APIPermission(
            user_id=user_a_id,
            api_config_id=stock_api.id,
            can_read=True,
            can_write=False
        )
        db.add(perm_a)

        # user_b: 只有天气 API 权限
        perm_b = APIPermission(
            user_id=user_b_id,
            api_config_id=weather_api.id,
            can_read=True,
            can_write=False
        )
        db.add(perm_b)

        await db.commit()
        print(f"✅ user_a 授予股票 API 权限")
        print(f"✅ user_b 授予天气 API 权限")
        return True

async def main():
    print("=" * 60)
    print("F-23: RBAC 权限隔离验证 - 测试数据准备")
    print("=" * 60)

    user_a_id, user_b_id = await setup_test_users()
    success = await assign_permissions(user_a_id, user_b_id)

    if success:
        print("\n✅ 测试环境准备完成")
        print(f"user_a (ID: {user_a_id}): 股票 API 权限")
        print(f"user_b (ID: {user_b_id}): 天气 API 权限")
    else:
        print("\n❌ 测试环境准备失败")

if __name__ == "__main__":
    asyncio.run(main())
