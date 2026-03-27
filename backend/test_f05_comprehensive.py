"""
F-05 综合测试：验证所有验收步骤
"""
import asyncio
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.agent.nodes.planner_node import planner_node
from app.agent.state import AgentState


async def test_all_f05_requirements():
    """测试 F-05 的所有验收步骤"""

    print("=" * 70)
    print("F-05 综合验收测试")
    print("=" * 70)

    # 模拟完整的股票查询场景
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

    result_state = await planner_node(state, retrieved_apis, [])
    plan = result_state.get("plan", [])

    # 验收步骤1: 验证Planner生成至少1个股票数据获取步骤
    print("\n[步骤1] 验证Planner生成至少1个股票数据获取步骤")
    stock_fetch_steps = [s for s in plan if s['tool'] == 'api_fetch'
                         and 'stock' in s.get('api_id', '').lower()]
    if stock_fetch_steps:
        print(f"  PASS - 找到 {len(stock_fetch_steps)} 个股票API调用步骤")
    else:
        print("  FAIL - 未找到股票API调用步骤")
        return False

    # 验收步骤2: 检查计划中API参数包含stock_symbol、trading_day_count等
    print("\n[步骤2] 检查计划中API参数包含stock_symbol等")
    first_stock_step = stock_fetch_steps[0]
    params = first_stock_step.get('params', {})

    if 'symbol' in params:
        print(f"  PASS - 包含 symbol 参数: {params['symbol']}")
        if params['symbol'] == 'AAPL':
            print(f"  PASS - symbol 正确映射为 AAPL")
        else:
            print(f"  FAIL - symbol 值不正确: {params['symbol']}")
            return False
    else:
        print("  FAIL - 缺少 symbol 参数")
        return False

    # 验收步骤3: 如需计算涨跌幅或趋势指标，验证生成python_exec步骤
    print("\n[步骤3] 验证是否生成python_exec步骤用于趋势计算")
    python_steps = [s for s in plan if s['tool'] == 'python_exec']
    if python_steps:
        print(f"  PASS - 找到 {len(python_steps)} 个python_exec步骤")
        for step in python_steps:
            code = step.get('params', {}).get('code', '')
            if 'import' in code.lower():
                print(f"  WARN - python_exec代码包含import语句（应避免）")
    else:
        print("  INFO - 未生成python_exec步骤（可选）")

    # 验收步骤4: 确认计划参数可直接被Executor消费
    print("\n[步骤4] 确认计划参数可直接被Executor消费")
    all_valid = True
    for step in plan:
        if 'step_id' not in step or 'tool' not in step or 'params' not in step:
            print(f"  FAIL - 步骤 {step.get('step_id', '?')} 缺少必需字段")
            all_valid = False
    if all_valid:
        print("  PASS - 所有步骤包含必需字段")
    else:
        return False

    # 验收步骤5: 验证outputsize参数设置正确
    print("\n[步骤5] 验证outputsize参数（trading_day_count=7应用compact）")
    if 'outputsize' in params:
        if params['outputsize'] == 'compact':
            print(f"  PASS - outputsize=compact（适用于<=100天）")
        else:
            print(f"  WARN - outputsize={params['outputsize']}")
    else:
        print("  INFO - 未设置outputsize参数（可选）")

    print("\n" + "=" * 70)
    print("F-05 综合验收测试 - 全部通过")
    print("=" * 70)
    print(f"\n生成的完整计划（{len(plan)}步）:")
    for step in plan:
        print(f"  步骤{step['step_id']}: {step['tool']} - {step['description']}")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_all_f05_requirements())
    exit(0 if success else 1)
