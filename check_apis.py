"""
Check API configs in database
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
import asyncio
from app.access.api_config_service import APIConfigService
from app.models.permission import PermissionContext


async def check():
    perm = PermissionContext(user_id="admin", role="admin")
    service = APIConfigService(perm)
    apis = await service.get_all_api_configs()
    print(f"Total APIs: {len(apis)}")
    for api in apis:
        print(f"  - {api.config_id}: {api.name}")


asyncio.run(check())
