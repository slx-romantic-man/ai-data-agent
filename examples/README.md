# Examples

This directory contains practical examples for using AI Data Agent.

## Quick Examples

### 1. Basic Chat API Call

```bash
# Login first
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin" \
  -d "password=admin123"

# Store the token
TOKEN="your-access-token"

# Send a chat message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "查询最近7天订单统计"}'
```

### 2. Streaming Chat

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "分析销售额趋势"}'
```

### 3. Register a New API

```bash
curl -X POST http://localhost:8000/api/v1/api-management \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather API",
    "description": "Get current weather data",
    "base_url": "https://api.weatherapi.com",
    "auth_type": "api_key",
    "auth_config": {
      "api_key_header": "X-API-Key",
      "api_key_value": "your-api-key"
    },
    "endpoints": {
      "get_current": {
        "path": "/v1/current.json",
        "method": "GET",
        "params_mapping": {"q": "city"}
      }
    }
  }'
```

### 4. Python SDK Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Login
resp = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
    "username": "admin",
    "password": "admin123"
})
token = resp.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Chat
resp = requests.post(
    f"{BASE_URL}/api/v1/chat",
    headers=headers,
    json={"message": "查询本月销售数据"}
)
print(resp.json())
```

## More Examples

- [Custom Tool Development](./custom_tool.md) — 如何为 Agent 添加自定义工具
- [API Permission Setup](./api_permission.md) — 配置 API 权限和审批流
- [SSO Integration](./sso_integration.md) — 接入企业 SSO（可选）
