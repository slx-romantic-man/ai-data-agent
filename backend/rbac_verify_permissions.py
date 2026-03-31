"""
直接验证权限服务是否正确返回用户的API权限
"""
import asyncio
import sys
import io
from app.services.api_permission_service import APIPermissionService

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def verify_permissions():
    print("=" * 60)
    print("F-23: RBAC权限隔离验证 - 权限服务测试")
    print("=" * 60)

    service = APIPermissionService()

    # 测试 user_001 (应该只有股票API权限 - ID: 4)
    print("\n[测试1] user_001 的API权限:")
    user_001_apis = await service.get_active_api_ids("user_001")
    print(f"  可访问的API IDs: {user_001_apis}")

    if user_001_apis == [4]:
        print("  ✓ 通过: 只有股票API权限")
    else:
        print(f"  ✗ 失败: 期望 [4], 实际 {user_001_apis}")

    # 测试 user_002 (应该只有天气API权限 - ID: 1)
    print("\n[测试2] user_002 的API权限:")
    user_002_apis = await service.get_active_api_ids("user_002")
    print(f"  可访问的API IDs: {user_002_apis}")

    if user_002_apis == [1]:
        print("  ✓ 通过: 只有天气API权限")
    else:
        print(f"  ✗ 失败: 期望 [1], 实际 {user_002_apis}")

    # 测试 admin (应该有所有API权限)
    print("\n[测试3] admin 的API权限:")
    admin_apis = await service.get_active_api_ids("admin")
    print(f"  可访问的API IDs: {admin_apis}")
    print(f"  ✓ Admin有 {len(admin_apis)} 个API权限")

    print("\n" + "=" * 60)
    if user_001_apis == [4] and user_002_apis == [1]:
        print("最终结果: 全部通过 ✓")
    else:
        print("最终结果: 存在失败 ✗")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(verify_permissions())
