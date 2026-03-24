"""
Database migration script to create API permission system tables.
"""
import asyncio
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Change to project directory
os.chdir(project_root)

from sqlalchemy import text
from app.access.database.connection import get_db


async def run_migration():
    """Run the migration SQL."""
    migration_file = os.path.join(
        os.path.dirname(__file__),
        "app/access/database/migrations/002_api_permission_system.sql"
    )

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split by semicolons and execute each statement
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

    db = await get_db()

    async with db._session_factory() as session:
        for statement in statements:
            if statement:
                try:
                    await session.execute(text(statement))
                    print(f"Executed: {statement[:60]}...")
                except Exception as e:
                    # Some statements might fail if already exists, that's ok
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"Skipped (already exists): {statement[:60]}...")
                    else:
                        print(f"Error: {e}")
                        print(f"Statement: {statement[:100]}")

        await session.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())