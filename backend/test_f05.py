"""
Test F-05: 股票时间序列分析专用规划模板和参数映射
"""
import asyncio
import json
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.agent.nodes.intent_node import intent_clarification_node
from app.agent.nodes.planner_node import planner_node
from app.agent.state import AgentState


async def test_stock_planning():
    """测试股票查询的规划生成"""

    # 模拟 Intent Node 提取的股票实体
    state = AgentState(
        query="去看看苹果的美股股价最近7个交易日的变化趋势，给出原因与后续投资建议",
        messages=[],
        extracted_filters={
            "intent_type": "api_query",
            "entities": {
                "stock_symbol": "AAPL",
                "market": "US",
                "trading_day_count": 7,
                "api_hint": "stock_price"
            },
            "metrics": ["股价", "涨跌幅"],
            "dimensions": ["日期"],
            "confidence": 0.95
        },
        plan=[],
        current_step=0,
        data_context={}
    )

    # 模拟 Retrieval 返回的股票 API
    retrieved_apis = [{
        "api_id": "alpha_vantage_stock",
        "name": "Alpha Vantage 股票查询",
        "description": "查询特定股票数据",
        "type": "api",
        "endpoints": {
            "get_stock": {
                "path": "/query",
                "method": "GET",
                "description": "获取股票时间序列数据",
                "params": {
                    "symbol": "股票代码",
                    "apikey": "API密钥",
                    "function": "查询功能",
                    "outputsize": "数据量大小(compact/full)"
                }
            }
        }
    }]

    # 调用 Planner
    result_state = await planner_node(state, retrieved_apis, [])

    print("=" * 60)
    print("F-05 测试结果")
    print("=" * 60)

    plan = result_state.get("plan", [])
    print(f"\n生成的计划步骤数: {len(plan)}")

    if not plan:
        print("❌ 测试失败：未生成任何计划步骤")
        return False

    # 验证点1：至少有1个股票数据获取步骤
    has_stock_fetch = False
    for step in plan:
        print(f"\n步骤 {step['step_id']}:")
        print(f"  工具: {step['tool']}")
        print(f"  API ID: {step.get('api_id', 'N/A')}")
        print(f"  参数: {json.dumps(step.get('params', {}), ensure_ascii=False)}")
        print(f"  描述: {step['description']}")

        if step['tool'] == 'api_fetch' and 'alpha_vantage' in step.get('api_id', ''):
            has_stock_fetch = True

            # 验证点2：检查参数包含 symbol
            params = step.get('params', {})
            if 'symbol' in params:
                print(f"  ✅ 包含 symbol 参数: {params['symbol']}")
            else:
                print(f"  ❌ 缺少 symbol 参数")
                return False

            # 验证点3：检查 outputsize 参数（7个交易日应该用 compact）
            if 'outputsize' in params:
                print(f"  ✅ 包含 outputsize 参数: {params['outputsize']}")
                if params['outputsize'] == 'compact':
                    print(f"  ✅ trading_day_count=7 正确使用 compact 模式")
            else:
                print(f"  ⚠️  未设置 outputsize 参数（可选）")

    if not has_stock_fetch:
        print("\n❌ 测试失败：未生成股票API调用步骤")
        return False

    print("\n" + "=" * 60)
    print("✅ F-05 测试通过：成功生成股票专用规划模板")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_stock_planning())
    exit(0 if success else 1)
