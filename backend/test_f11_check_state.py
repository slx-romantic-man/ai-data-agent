"""Check the state from the last execution"""
import asyncio
import json
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def main():
    async with AsyncSqliteSaver.from_conn_string("backend/data/checkpoints.db") as checkpointer:
        config = {"configurable": {"thread_id": "test_f11_simple"}}
        state = await checkpointer.aget_tuple(config)

        if state:
            print("=== State Found ===")
            print(f"Checkpoint ID: {state.checkpoint['id']}")
            print(f"\n=== Plan ===")
            plan = state.values.get("plan", [])
            print(json.dumps(plan, indent=2, ensure_ascii=False))

            print(f"\n=== Data Context ===")
            data_context = state.values.get("data_context", {})
            for key, value in data_context.items():
                print(f"\n{key}:")
                print(json.dumps(value, indent=2, ensure_ascii=False))
        else:
            print("No state found for thread_id: test_f11_simple")

if __name__ == "__main__":
    asyncio.run(main())
