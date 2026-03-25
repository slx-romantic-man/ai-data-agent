"""
Standalone runner for create_orders_table logic (no async, uses pymysql).
Falls back gracefully with a clear error message.
"""
import random
from datetime import datetime, timedelta

try:
    import pymysql
    USE_PYMYSQL = True
except ImportError:
    USE_PYMYSQL = False

try:
    import aiomysql
    import asyncio
    USE_AIOMYSQL = True
except ImportError:
    USE_AIOMYSQL = False

DDL = """
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    order_date DATETIME NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    customer_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

def build_rows():
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
    return rows

def run_pymysql():
    conn = pymysql.connect(
        host='localhost', port=3306,
        user='root', password='123456',
        database='ai_data_agent', charset='utf8mb4'
    )
    with conn.cursor() as cur:
        cur.execute(DDL)
        print("Table 'orders' created (or already exists)")

        cur.execute("DELETE FROM orders WHERE order_no LIKE 'TEST-%'")

        rows = build_rows()
        cur.executemany(
            "INSERT IGNORE INTO orders (order_no, order_date, amount) VALUES (%s, %s, %s)",
            rows
        )
        print(f"Inserted {len(rows)} test orders")

        cur.execute(
            "SELECT COUNT(*) as cnt, SUM(amount) as total FROM orders "
            "WHERE order_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        )
        row = cur.fetchone()
        print(f"Last 7 days: {row[0]} orders, total amount: {row[1]:.2f}")

    conn.commit()
    conn.close()
    print("Done!")

async def run_aiomysql():
    conn = await aiomysql.connect(
        host='localhost', port=3306,
        user='root', password='123456',
        db='ai_data_agent', charset='utf8mb4'
    )
    async with conn.cursor() as cur:
        await cur.execute(DDL)
        print("Table 'orders' created (or already exists)")

        await cur.execute("DELETE FROM orders WHERE order_no LIKE 'TEST-%'")

        rows = build_rows()
        await cur.executemany(
            "INSERT IGNORE INTO orders (order_no, order_date, amount) VALUES (%s, %s, %s)",
            rows
        )
        print(f"Inserted {len(rows)} test orders")

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
    print(f"pymysql available: {USE_PYMYSQL}")
    print(f"aiomysql available: {USE_AIOMYSQL}")
    if USE_PYMYSQL:
        print("Using pymysql (sync)...")
        run_pymysql()
    elif USE_AIOMYSQL:
        print("Using aiomysql (async)...")
        asyncio.run(run_aiomysql())
    else:
        print("ERROR: Neither pymysql nor aiomysql is installed.")
        print("Install one of them:")
        print("  pip install pymysql")
        print("  pip install aiomysql")
