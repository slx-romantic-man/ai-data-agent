"""
Test F-03: 验证 Retrieval 到 Planner 的 API 元数据传递
"""
import asyncio
import sys
import io
from pathlib import Path

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.services.api_retrieval_service import get_api_retrieval_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_api_metadata_passing():
    """测试 API 元数据是否完整传递"""
    print("\n" + "="*60)
    print("F-03 测试：API 元数据传递验证")
    print("="*60)

    # 模拟股票查询
    query = "查询苹果美股最近7个交易日的股价"
    user_id = "1"

    print(f"\n1. 发起查询: {query}")

    # 获取检索服务
    retrieval_service = get_api_retrieval_service()

    # 执行两阶段检索
    print("\n2. 执行 API 检索...")
    retrieved_apis = await retrieval_service.get_apis_for_query(
        query=query,
        user_id=user_id,
        top_k=3
    )

    print(f"\n3. 检索到 {len(retrieved_apis)} 个 API")

    # 验证每个 API 的元数据完整性
    all_passed = True
    for idx, api in enumerate(retrieved_apis, 1):
        print(f"\n--- API {idx} ---")
        api_id = api.get('api_id') or api.get('id', 'unknown')
        name = api.get('name', 'N/A')
        description = api.get('description', 'N/A')
        endpoints = api.get('endpoints', {})

        print(f"API ID: {api_id}")
        print(f"名称: {name}")
        print(f"描述: {description}")

        # 检查描述是否为空
        if not description or description == 'N/A':
            print("❌ 描述为空")
            all_passed = False
        else:
            print("✅ 描述不为空")

        # 检查 endpoints 信息
        if not endpoints:
            print("❌ endpoints 信息缺失")
            all_passed = False
        else:
            print(f"✅ endpoints 信息存在 ({len(endpoints)} 个端点)")
            for endpoint_name, endpoint_config in endpoints.items():
                if isinstance(endpoint_config, dict):
                    endpoint_desc = endpoint_config.get('description', 'N/A')
                    endpoint_path = endpoint_config.get('path', 'N/A')
                    endpoint_params = endpoint_config.get('params', {})
                    print(f"  - {endpoint_name}:")
                    print(f"    路径: {endpoint_path}")
                    print(f"    描述: {endpoint_desc}")
                    print(f"    参数: {list(endpoint_params.keys()) if endpoint_params else '无'}")

                    # 检查参数定义
                    if not endpoint_params:
                        print("    ⚠️  参数定义为空")
                    else:
                        print("    ✅ 参数定义存在")

    print("\n" + "="*60)
    if all_passed:
        print("✅ F-03 测试通过：所有 API 元数据完整")
    else:
        print("❌ F-03 测试失败：部分 API 元数据缺失")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_api_metadata_passing())
    sys.exit(0 if result else 1)
