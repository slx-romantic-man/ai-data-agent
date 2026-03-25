"""
创建 orders 测试表并插入模拟数据，用于 F-11 端到端测试
"""
import asyncio
import random
from datetime import datetime, timedelta
import aiomysql


async def create_and_seed():
    conn = await aiomysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        db='ai_data_agent',
        charset='utf8mb4'
    )
    async with conn.cursor() as cur:
        # 创建 orders 表
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_no VARCHAR(50) UNIQUE NOT NULL,
                order_date DATETIME NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'completed',
                customer_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("Table 'orders' created (or already exists)")

        # 清空旧测试数据
        await cur.execute("DELETE FROM orders WHERE order_no LIKE 'TEST-%'")

        # 插入最近 7 天的测试数据
        today = datetime.now()
        rows = []
        for day_offset in range(7):
            order_date = today - timedelta(days=day_offset)
            num_orders = random.randint(5, 15)
            for i in range(num_orders):
                order_no = f"TEST-{order_date.strftime('%Y%m%d')}-{i+1:03d}"
                amount = round(random.uniform(50, 500), 2)
                rows.append((
                    order_no,
                    order_date.strftime('%Y-%m-%d %H:%M:%S'),
                    amount
                ))

        await cur.executemany(
            "INSERT IGNORE INTO orders (order_no, order_date, amount) "
            "VALUES (%s, %s, %s)",
            rows
        )
        print(f"Inserted {len(rows)} test orders")

        # 验证
        await cur.execute(
            "SELECT COUNT(*) as cnt, SUM(amount) as total FROM orders "
            "WHERE order_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        )
        row = await cur.fetchone()
        print(f"Last 7 days: {row[0]} orders, total amount: {row[1]:.2f}")

    await conn.commit()
    conn.close()
    print("Done!")


if __name__ == '__main__':
    asyncio.run(create_and_seed())
