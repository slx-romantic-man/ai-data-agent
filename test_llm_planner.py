"""直接测试LLM生成Planner计划"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.config.llm_config import get_llm
from app.agent.prompts.planner_prompt import PLANNER_PROMPT

async def test_llm_plan():
    llm = get_llm()

    # 模拟一个需要api_fetch的场景
    user_query = "查询苹果公司AAPL股票最近的价格数据"

    retrieved_apis = [
        {
            "api_id": "alpha_vantage_stock",
            "api_name": "Alpha Vantage股票数据API",
            "description": "提供全球股票市场的实时和历史数据",
            "endpoints": {
                "获取日线数据": {
                    "endpoint_name": "获取日线数据",
                    "description": "获取指定股票的每日时间序列数据",
                    "params_mapping": {
                        "symbol": "股票代码（如AAPL）",
                        "outputsize": "返回数据量，compact或full"
                    }
                }
            }
        }
    ]

    extracted_filters = {
        "stock_symbol": "AAPL"
    }

    prompt = PLANNER_PROMPT.format(
        user_query=user_query,
        retrieved_apis=str(retrieved_apis),
        retrieved_tables="（无可用数据库表）",
        extracted_filters=str(extracted_filters)
    )

    print("=" * 80)
    print("发送给LLM的Prompt:")
    print("=" * 80)
    print(prompt)
    print("=" * 80)

    response = await llm.chat([{"role": "user", "content": prompt}])

    print("\n" + "=" * 80)
    print("LLM返回:")
    print("=" * 80)
    print(response)
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_llm_plan())
