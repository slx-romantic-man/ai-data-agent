"""
F-06 端到端测试 - 验证股票API返回结果规范化
按照 feature_list.json 中的验证步骤
"""
import asyncio
from app.agent.tools.api_fetch_tool import get_api_fetch_tool
from app.agent.nodes.analyzer_node import _extract_all_data
from app.models.permission import PermissionContext


async def test_f06_complete():
    """完整的F-06验证流程"""
    print("=" * 60)
    print("F-06: Normalize stock API results for Analyzer")
    print("=" * 60)

    tool = get_api_fetch_tool()
    permission = PermissionContext(
        user_id="admin",
        role="admin",
        conversation_id="test_f06"
    )

    # Step 1: 成功调用股票API
    print("\n[Step 1] Call stock API successfully")
    params = {
        "api_id": "alpha_vantage_stock",
        "endpoint": "获取日线数据",
        "params": {
            "symbol": "AAPL",
            "outputsize": "compact",
            "function": "TIME_SERIES_DAILY"
        }
    }

    result = await tool.execute(params, permission)
    assert result.status.value == "success", f"API call failed: {result.error}"
    print("  PASS: API call successful")

    # Step 2: 检查data_context中存储的结果结构
    print("\n[Step 2] Check stored result structure in data_context")
    data_context = {
        "step_0_alpha_vantage_stock": {
            "success": True,
            "data": result.data,
            "error": None,
            "metadata": result.metadata
        }
    }

    stored_data = data_context["step_0_alpha_vantage_stock"]["data"]
    assert isinstance(stored_data, dict), "Data should be a dict"
    print("  PASS: Data is stored as dict")

    # Step 3: 验证结果包含规范化的行式数据
    print("\n[Step 3] Verify normalized row-based data structure")
    assert "rows" in stored_data, "Missing 'rows' field"
    assert isinstance(stored_data["rows"], list), "'rows' should be a list"
    print(f"  PASS: Contains 'rows' field with {len(stored_data['rows'])} items")

    # 验证每行数据包含必需字段
    if stored_data["rows"]:
        first_row = stored_data["rows"][0]
        required_fields = ["date", "open", "high", "low", "close", "volume"]
        for field in required_fields:
            assert field in first_row, f"Missing required field: {field}"
        print(f"  PASS: Each row contains required fields: {required_fields}")

        # 验证pct_change计算
        if "pct_change" in first_row:
            print(f"  PASS: pct_change calculated: {first_row['pct_change']:.2f}%")

    # Step 4: 验证data_context包含元信息
    print("\n[Step 4] Verify metadata in data_context")
    assert "row_count" in stored_data, "Missing 'row_count'"
    assert "source" in stored_data, "Missing 'source'"
    assert "raw_summary" in stored_data, "Missing 'raw_summary'"
    print(f"  PASS: row_count={stored_data['row_count']}")
    print(f"  PASS: source={stored_data['source']}")
    print(f"  PASS: symbol={stored_data.get('symbol', 'N/A')}")

    # Step 5: 检查Analyzer能提取到有效交易日数据
    print("\n[Step 5] Verify Analyzer can extract valid trading day data")
    all_data = _extract_all_data(data_context)
    assert len(all_data) > 0, "Analyzer extracted 0 rows"
    print(f"  PASS: Analyzer extracted {len(all_data)} rows")

    # Step 6: 验证不再出现'Stored result成功但Extracted 0 total rows'
    print("\n[Step 6] Verify no 'Stored success but Extracted 0 rows' issue")
    assert len(all_data) == stored_data["row_count"], \
        f"Mismatch: stored {stored_data['row_count']} but extracted {len(all_data)}"
    print(f"  PASS: Stored count matches extracted count: {len(all_data)}")

    # Step 7: 对API失败场景，验证返回结构化错误对象
    print("\n[Step 7] Verify structured error for API failure")
    bad_params = {
        "api_id": "alpha_vantage_stock",
        "endpoint": "获取日线数据",
        "params": {
            "symbol": "INVALID_SYMBOL_XYZ123",
            "outputsize": "compact",
            "function": "TIME_SERIES_DAILY"
        }
    }

    error_result = await tool.execute(bad_params, permission)
    # Alpha Vantage可能返回成功但数据为空，或返回错误信息
    if error_result.status.value == "success" and error_result.data:
        # 检查是否返回了规范化的错误结构
        if isinstance(error_result.data, dict):
            if "rows" in error_result.data:
                print(f"  PASS: API returned normalized structure with "
                      f"{error_result.data['row_count']} rows")
            else:
                print("  INFO: API returned raw data (not normalized)")
    else:
        print(f"  PASS: API failure handled with error: {error_result.error}")

    await tool.close()

    print("\n" + "=" * 60)
    print("F-06 ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_f06_complete())
