"""
Simple test to verify F-03 fix: API metadata passing from Retrieval to Planner
This test directly uses the retrieval service to check if APIs are being retrieved with full metadata
"""
import asyncio
import sys

async def test_retrieval():
    print("\n" + "="*60)
    print("F-03 Simple Test: API Retrieval with Metadata")
    print("="*60)

    # Import services
    from app.services.api_retrieval_service import get_api_retrieval_service
    from app.config.settings import settings

    print(f"\n1. Qdrant configuration: {settings.QDRANT_URL}")

    # Get retrieval service
    retrieval_service = get_api_retrieval_service()

    # Build index first
    print("2. Building API index...")
    from app.services.api_permission_service import get_api_permission_service
    permission_service = await get_api_permission_service()
    all_apis = await permission_service.get_all_apis()
    for api in all_apis:
        await retrieval_service.build_index_for_api(api.id)

    indexed_count = retrieval_service.get_indexed_count()
    print(f"   Indexed {indexed_count} APIs")

    if indexed_count == 0:
        print("\n[FAIL] No APIs found in database")
        return False

    # Test retrieval
    query = "查询苹果美股最近7个交易日的股价"
    print(f"\n3. Testing retrieval for query: {query}")

    apis = await retrieval_service.get_apis_for_query(
        query=query,
        user_id="1",
        top_k=3
    )

    print(f"4. Retrieved {len(apis)} APIs")

    if len(apis) == 0:
        print("\n[FAIL] No APIs retrieved")
        return False

    # Check first API metadata
    print(f"\n5. Checking first API metadata:")
    first_api = apis[0]

    checks = {
        "api_id or id": first_api.get('api_id') or first_api.get('id'),
        "name": first_api.get('name'),
        "description": first_api.get('description') if first_api.get('description') else "(empty in DB)",
        "endpoints": first_api.get('endpoints'),
    }

    all_passed = True
    for field, value in checks.items():
        if value and value != "(empty in DB)":
            print(f"   [PASS] {field}: {str(value)[:50]}...")
        elif field == "description" and value == "(empty in DB)":
            print(f"   [WARN] {field}: empty in database (data quality issue)")
        else:
            print(f"   [FAIL] {field}: missing")
            all_passed = False

    # Check endpoint details
    if checks["endpoints"]:
        endpoints = checks["endpoints"]
        print(f"\n6. Endpoint details ({len(endpoints)} endpoints):")
        for ep_name, ep_config in list(endpoints.items())[:2]:
            if isinstance(ep_config, dict):
                params = ep_config.get('params', {})
                print(f"   - {ep_name}: {len(params)} params")

    print("\n" + "="*60)
    if all_passed:
        print("PASS: API metadata is complete")
    else:
        print("FAIL: API metadata is incomplete")
    print("="*60)

    return all_passed

if __name__ == "__main__":
    result = asyncio.run(test_retrieval())
    sys.exit(0 if result else 1)
