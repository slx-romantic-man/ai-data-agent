"""测试计划生成 - 验证 Planner 是否正确生成 python_exec 步骤"""
import asyncio
from app.agent.nodes.planner_node import planner_node
from app.agent.state import AgentState


async def test_scenario(scenario_num, query, expected_tools, apis=None, tables=None):
    """测试单个场景的计划生成"""
    print(f"\n{'='*60}")
    print(f"场景{scenario_num}: {query}")
    print(f"{'='*60}")

    initial_state: AgentState = {
        "messages": [],
        "query": query,
        "extracted_filters": {},
        "retrieved_apis": [],
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    try:
        result_state = await planner_node(
            initial_state,
            retrieved_apis=apis or [],
            retrieved_tables=tables or []
        )
        plan = result_state.get("plan", [])

        print(f"\n生成的计划步骤数: {len(plan)}")
        for i, step in enumerate(plan):
            print(f"  步骤 {i+1}: {step.get('tool')} - {step.get('description', '')}")

        tools_used = [s.get("tool") for s in plan]
        print(f"\n生成的工具序列: {tools_used}")
        print(f"期望包含: {expected_tools}")

        success = all(tool in tools_used for tool in expected_tools)
        print(f"结果: {'通过' if success else '失败'}")

        return success
    except Exception as e:
        print(f"错误: {e}")
        return False


async def main():
    results = []

    # Mock API for scenario 2
    mock_api = [{
        "api_id": "order_recent_stats",
        "description": "获取最近N天的订单统计数据",
        "params": {"days": 7},
        "type": "api"
    }]

    # Mock table for scenario 3
    mock_table = [{
        "name": "orders",
        "description": "订单表",
        "type": "table",
        "schema": "order_id, order_date, amount, status"
    }]

    # 场景1：简单计算
    results.append(await test_scenario(
        1,
        "上个月销售额10000，这个月12000，增长率是多少",
        ["python_exec"]
    ))

    # 场景2：API + 计算
    results.append(await test_scenario(
        2,
        "最近7天订单数据的平均订单金额是多少",
        ["python_exec"],
        apis=mock_api
    ))

    # 场景3：多步骤
    results.append(await test_scenario(
        3,
        "计算本月销售额和成本的利润率",
        ["python_exec"],
        tables=mock_table
    ))

    print(f"\n{'='*60}")
    print(f"总体结果: {sum(results)}/3 通过")
    print(f"{'='*60}")

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
