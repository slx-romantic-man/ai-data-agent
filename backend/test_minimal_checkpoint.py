"""
最小化测试：验证 checkpointer 能够保存和恢复状态
"""
import asyncio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite


async def test_minimal_checkpoint():
    """最小化测试 checkpointer"""
    print("Creating checkpointer...")
    conn = aiosqlite.connect("./data/test_checkpoints.db")
    checkpointer = AsyncSqliteSaver(conn)

    # 设置数据库
    await checkpointer.setup()
    print("Checkpointer setup complete")

    # 测试保存
    config = {"configurable": {"thread_id": "test_thread"}}
    checkpoint = {
        "v": 1,
        "id": "test_checkpoint_1",
        "ts": "2024-01-01T00:00:00Z",
        "channel_values": {"test_key": "test_value"},
        "channel_versions": {},
        "versions_seen": {}
    }

    print("Saving checkpoint...")
    await checkpointer.aput(config, checkpoint, {})
    print("Checkpoint saved")

    # 测试读取
    print("Reading checkpoint...")
    result = await checkpointer.aget_tuple(config)
    print(f"Checkpoint retrieved: {result is not None}")

    if result:
        print("PASS: Checkpoint persistence works")
        return True
    else:
        print("FAIL: Could not retrieve checkpoint")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_minimal_checkpoint())
    exit(0 if result else 1)
