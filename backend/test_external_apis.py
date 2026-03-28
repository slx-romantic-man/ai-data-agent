"""
直接测试外部API是否可用
不通过Agent系统，直接调用API验证密钥和连接
"""
import asyncio
import httpx
import json
from app.access.database import get_mysql_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_api_direct(api_config: dict) -> dict:
    """直接测试单个API"""
    api_id = api_config['config_id']
    name = api_config['name']
    base_url = api_config['base_url']

    logger.info(f"\n{'='*60}")
    logger.info(f"测试 API: {name} ({api_id})")
    logger.info(f"Base URL: {base_url}")

    # 获取第一个endpoint
    endpoints = api_config.get('endpoints', {})
    if isinstance(endpoints, str):
        endpoints = json.loads(endpoints)
    if not endpoints:
        return {"api_id": api_id, "status": "no_endpoints", "error": "无端点配置"}

    endpoint_name = list(endpoints.keys())[0]
    endpoint = endpoints[endpoint_name]
    path = endpoint.get('path', '')
    method = endpoint.get('method', 'GET')

    full_url = f"{base_url}{path}"
    logger.info(f"测试端点: {endpoint_name}")
    logger.info(f"URL: {full_url}")
    logger.info(f"Method: {method}")

    # 构建请求
    headers = {}
    params = {}

    # 处理认证
    auth_type = api_config.get('auth_type', 'none')
    auth_config = api_config.get('auth_config', {})
    if isinstance(auth_config, str):
        try:
            auth_config = json.loads(auth_config) if auth_config.strip() else {}
        except json.JSONDecodeError:
            logger.warning(f"Invalid auth_config JSON: {repr(auth_config)}")
            auth_config = {}
    elif not auth_config:
        auth_config = {}

    if auth_type == 'api_key':
        key_name = auth_config.get('key_name', 'apikey')
        key_value = auth_config.get('key_value', '')
        location = auth_config.get('location', 'query')

        if location == 'query':
            params[key_name] = key_value
        elif location == 'header':
            headers[key_name] = key_value

    # 添加测试参数
    test_params = endpoint.get('parameters', {})
    for param_name, param_info in test_params.items():
        if param_info.get('required'):
            # 使用示例值或默认值
            if 'example' in param_info:
                params[param_name] = param_info['example']
            elif param_name in ['symbol', 'stock']:
                params[param_name] = 'AAPL'
            elif param_name in ['city', 'location', 'q']:
                params[param_name] = 'Beijing'
            elif param_name in ['ip']:
                params[param_name] = '8.8.8.8'

    logger.info(f"请求参数: {params}")

    # 发送请求
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == 'GET':
                response = await client.get(full_url, params=params, headers=headers)
            else:
                response = await client.post(full_url, json=params, headers=headers)

            logger.info(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                logger.info(f"[OK] API调用成功")
                logger.info(f"响应前200字符: {response.text[:200]}")
                return {
                    "api_id": api_id,
                    "status": "success",
                    "status_code": response.status_code,
                    "response_preview": response.text[:200]
                }
            else:
                logger.error(f"[FAIL] HTTP {response.status_code}")
                logger.error(f"响应: {response.text[:200]}")
                return {
                    "api_id": api_id,
                    "status": "failed",
                    "status_code": response.status_code,
                    "error": f"HTTP {response.status_code}: {response.text[:100]}"
                }

    except Exception as e:
        logger.error(f"[ERROR] 请求异常: {e}")
        return {
            "api_id": api_id,
            "status": "error",
            "error": str(e)
        }


async def main():
    """测试所有API"""
    logger.info("="*60)
    logger.info("外部API直接调用测试")
    logger.info("="*60)

    # 从数据库获取所有活跃的API配置
    db = await get_mysql_client()

    query = """
        SELECT id, config_id, name, description, base_url,
               auth_type, auth_config, endpoints
        FROM api_configs
        WHERE is_active = 1
        ORDER BY name
    """

    rows = await db.db.fetch_all(query)

    logger.info(f"\n找到 {len(rows)} 个活跃API\n")

    results = []
    for api in rows:
        api_dict = {
            'id': api[0],
            'config_id': api[1],
            'name': api[2],
            'description': api[3],
            'base_url': api[4],
            'auth_type': api[5],
            'auth_config': json.loads(api[6]) if isinstance(api[6], str) else api[6],
            'endpoints': json.loads(api[7]) if isinstance(api[7], str) else api[7]
        }

        result = await test_api_direct(api_dict)
        results.append(result)

        await asyncio.sleep(1)  # 避免请求过快

    # 汇总报告
    logger.info("\n" + "="*60)
    logger.info("测试汇总")
    logger.info("="*60)

    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    error_count = sum(1 for r in results if r['status'] == 'error')

    logger.info(f"总计: {len(results)} 个API")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {failed_count}")
    logger.info(f"错误: {error_count}")

    logger.info("\n详细结果:")
    for r in results:
        status_icon = "[OK]" if r['status'] == 'success' else "[FAIL]"
        logger.info(f"{status_icon} {r['api_id']}: {r.get('error', 'Success')}")


if __name__ == "__main__":
    asyncio.run(main())
