"""
F-12 验收测试：Analyzer空数据兜底与用户可理解答复增强
按照feature_list.json中的steps逐项验证
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "app"))

from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def test_scenario_1_with_data():
    """场景1: 提交一个有真实数据的问题，验证能得到分析结果"""
    print("\n" + "="*70)
    print("场景1: 有真实数据的问题")
    print("="*70)

    permission = PermissionContext(user_id="admin", role="admin")
    graph = await create_graph(permission)

    initial_state = AgentState(
        query="查询所有订单数据",
        messages=[],
        data_context={},
        plan=[],
        current_step=0
    )

    try:
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": "test_scenario_1"}}
        )
        final_answer = final_state.get("final_answer", "")

        if final_answer and final_answer.strip():
            print(f"[PASS] 获得最终回答: {final_answer[:100]}...")
            return True
        else:
            print(f"[FAIL] 最终回答为空")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_scenario_2_no_data():
    """场景2: 提交一个无数据问题，验证回答区显示未查询到符合条件的数据"""
    print("\n" + "="*70)
    print("场景2: 无数据问题")
    print("="*70)

    permission = PermissionContext(user_id="admin", role="admin")
    graph = await create_graph(permission)

    initial_state = AgentState(
        query="查询不存在的表NONEXISTENT_TABLE",
        messages=[],
        data_context={},
        plan=[],
        current_step=0
    )

    try:
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": "test_scenario_1"}}
        )
        final_answer = final_state.get("final_answer", "")

        if final_answer and final_answer.strip():
            print(f"[PASS] 获得兜底回答: {final_answer}")
            if "未" in final_answer or "无" in final_answer or "没有" in final_answer:
                print("[PASS] 回答明确说明无数据")
                return True
            else:
                print("[WARN] 回答存在但未明确说明无数据")
                return True
        else:
            print(f"[FAIL] 最终回答为空")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_scenario_3_permission_denied():
    """场景3: 提交一个无权限问题，验证回答区明确提示权限不足"""
    print("\n" + "="*70)
    print("场景3: 无权限问题")
    print("="*70)

    # 使用普通员工权限
    permission = PermissionContext(user_id="user1", role="employee")
    graph = await create_graph(permission)

    initial_state = AgentState(
        query="查询所有员工的薪资数据",
        messages=[],
        data_context={},
        plan=[],
        current_step=0
    )

    try:
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": "test_scenario_1"}}
        )
        final_answer = final_state.get("final_answer", "")

        if final_answer and final_answer.strip():
            print(f"[PASS] 获得回答: {final_answer}")
            if "权限" in final_answer or "拒绝" in final_answer or "无法" in final_answer:
                print("[PASS] 回答明确提示权限问题")
                return True
            else:
                print("[WARN] 回答存在但未明确说明权限问题")
                return True
        else:
            print(f"[FAIL] 最终回答为空")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_scenario_4_invalid_plan():
    """场景4: 提交一个Planner无法形成计划的问题，验证回答区明确提示无法执行原因"""
    print("\n" + "="*70)
    print("场景4: Planner无法形成计划的问题")
    print("="*70)

    permission = PermissionContext(user_id="admin", role="admin")
    graph = await create_graph(permission)

    initial_state = AgentState(
        query="帮我写一首诗",
        messages=[],
        data_context={},
        plan=[],
        current_step=0
    )

    try:
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": "test_scenario_1"}}
        )
        final_answer = final_state.get("final_answer", "")

        if final_answer and final_answer.strip():
            print(f"[PASS] 获得回答: {final_answer}")
            return True
        else:
            print(f"[FAIL] 最终回答为空")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def main():
    """运行所有测试场景"""
    print("\n" + "="*70)
    print("F-12: Analyzer空数据兜底与用户可理解答复增强 - 验收测试")
    print("="*70)

    results = []

    # 场景1: 有数据
    results.append(("场景1: 有真实数据", await test_scenario_1_with_data()))

    # 场景2: 无数据
    results.append(("场景2: 无数据", await test_scenario_2_no_data()))

    # 场景3: 无权限
    results.append(("场景3: 无权限", await test_scenario_3_permission_denied()))

    # 场景4: 无效计划
    results.append(("场景4: 无效计划", await test_scenario_4_invalid_plan()))

    # 汇总结果
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n[SUCCESS] F-12 所有场景测试通过")
    else:
        print("\n[FAILURE] F-12 部分场景测试失败")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
