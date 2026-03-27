"""
Test that Planner generates plans with endpoint parameter
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.agent.nodes.planner_node import _create_fallback_plan

# Test fallback plan generation
retrieved_apis = [{
    "config_id": "alpha_vantage_stock",
    "name": "Alpha Vantage Stock API",
    "description": "Stock data API",
    "endpoints": {
        "获取日线数据": {
            "description": "Get daily time series",
            "path": "/query",
            "params_mapping": {
                "symbol": "IBM",
                "function": "TIME_SERIES_DAILY"
            }
        }
    }
}]

plan = _create_fallback_plan("查询IBM股票", retrieved_apis)

print("Generated plan:")
print(plan)

if plan and len(plan) > 0:
    step = plan[0]
    params = step.get("params", {})

    if "endpoint" in params:
        print("\n[PASS] Plan includes 'endpoint' parameter")
        print(f"  endpoint: {params['endpoint']}")

        if "params" in params:
            print(f"  params: {params['params']}")
            print("\n[PASS] Plan has correct nested structure")
        else:
            print("\n[FAIL] Plan missing nested 'params' field")
    else:
        print("\n[FAIL] Plan missing 'endpoint' parameter")
        print(f"  params keys: {list(params.keys())}")
else:
    print("\n[FAIL] No plan generated")
