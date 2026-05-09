#!/usr/bin/env python3
"""
注册所有 Mock API 到系统中，用于全面测试 agent 的 API 调用能力。

覆盖场景：
- HTTP 方法: GET, POST, PUT, PATCH
- 参数位置: Query, Path, Body(JSON)
- 认证方式: None, APIKey(header/query), Bearer, Basic, Custom
- 响应格式: 简单对象、数组、嵌套结构、分页、空结果、字段映射
- 特殊场景: 默认参数、可选参数、复杂嵌套对象

用法:
    export BACKEND_URL=http://localhost:8000
    python scripts/register_mock_apis.py
"""
import json
import os
import sys
import urllib.request
import urllib.error

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")


def login() -> str:
    """获取管理员 Token"""
    data = urllib.parse.urlencode({"username": ADMIN_USER, "password": ADMIN_PASS}).encode()
    req = urllib.request.Request(f"{BACKEND_URL}/api/v1/auth/login", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        return result["access_token"]


def api_request(token: str, method: str, path: str, body: dict = None):
    """发送 API 请求"""
    url = f"{BACKEND_URL}{path}"
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        print(f"  HTTP {e.code}: {text}")
        return None


def delete_if_exists(token: str, api_id: str):
    """如果 API 已存在则删除"""
    api_request(token, "DELETE", f"/api/v1/apis/{api_id}")


# ============ Mock API 定义 ============
MOCK_APIS = [
    # 1. GET + Query 参数
    {
        "id": "mock_users_query",
        "name": "Mock用户查询API",
        "description": "测试GET+Query参数调用，支持按姓名、年龄、状态、部门筛选用户",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "search_users": {
                "path": "/users",
                "method": "GET",
                "description": "多条件搜索用户（GET+Query参数测试）",
                "params_mapping": {
                    "姓名": "name",
                    "最小年龄": "age_min",
                    "最大年龄": "age_max",
                    "状态": "status",
                    "部门": "department"
                },
                "required_params": [],
                "default_params": {},
                "params_descriptions": {
                    "姓名": "按姓名模糊搜索",
                    "最小年龄": "最小年龄限制",
                    "最大年龄": "最大年龄限制",
                    "状态": "用户状态：active/inactive",
                    "部门": "所属部门"
                },
                "response_data_path": "data.users",
                "response_field_mapping": {}
            }
        }
    },

    # 2. GET + Path 参数
    {
        "id": "mock_user_detail",
        "name": "Mock用户详情API",
        "description": "测试GET+Path参数调用，根据用户ID获取详细信息",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "get_user": {
                "path": "/users/{user_id}",
                "method": "GET",
                "description": "根据ID获取用户详情（GET+Path参数测试）",
                "params_mapping": {"用户ID": "user_id"},
                "required_params": ["用户ID"],
                "params_descriptions": {"用户ID": "用户唯一标识"},
                "response_data_path": "data.user",
                "response_field_mapping": {}
            }
        }
    },

    # 3. POST + JSON Body
    {
        "id": "mock_order_create",
        "name": "Mock订单创建API",
        "description": "测试POST+JSON Body调用，创建新订单",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "create_order": {
                "path": "/orders",
                "method": "POST",
                "description": "创建新订单（POST+JSON Body测试）",
                "params_mapping": {
                    "产品ID": "product_id",
                    "数量": "quantity",
                    "客户姓名": "customer_name",
                    "地址": "address"
                },
                "required_params": ["产品ID", "客户姓名"],
                "default_params": {"数量": 1},
                "params_descriptions": {
                    "产品ID": "产品唯一标识",
                    "数量": "购买数量",
                    "客户姓名": "客户姓名",
                    "地址": "配送地址（可选）"
                },
                "response_data_path": "data.order",
                "response_field_mapping": {}
            }
        }
    },

    # 4. PUT + Path + JSON Body
    {
        "id": "mock_user_update",
        "name": "Mock用户更新API",
        "description": "测试PUT+Path+Body调用，更新用户信息",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "update_user": {
                "path": "/users/{user_id}",
                "method": "PUT",
                "description": "更新用户信息（PUT+Path+Body测试）",
                "params_mapping": {
                    "用户ID": "user_id",
                    "姓名": "name",
                    "邮箱": "email",
                    "年龄": "age",
                    "状态": "status",
                    "部门": "department"
                },
                "required_params": ["用户ID"],
                "params_descriptions": {
                    "用户ID": "要更新的用户ID",
                    "姓名": "新姓名",
                    "邮箱": "新邮箱",
                    "年龄": "新年龄",
                    "状态": "新状态",
                    "部门": "新部门"
                },
                "response_data_path": "data.user",
                "response_field_mapping": {}
            }
        }
    },

    # 5. PATCH + Path + JSON Body
    {
        "id": "mock_order_patch",
        "name": "Mock订单状态更新API",
        "description": "测试PATCH+Path+Body调用，部分更新订单状态",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "patch_order": {
                "path": "/orders/{order_id}",
                "method": "PATCH",
                "description": "部分更新订单（PATCH+Path+Body测试）",
                "params_mapping": {
                    "订单ID": "order_id",
                    "状态": "status",
                    "备注": "note"
                },
                "required_params": ["订单ID"],
                "params_descriptions": {
                    "订单ID": "订单编号",
                    "状态": "新状态：created/pending/shipped/completed",
                    "备注": "更新备注"
                },
                "response_data_path": "data.order",
                "response_field_mapping": {}
            }
        }
    },

    # 6. Bearer Token 认证
    {
        "id": "mock_auth_bearer",
        "name": "Mock Bearer认证测试API",
        "description": "测试Bearer Token认证调用",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {
            "type": "bearer",
            "bearer_token": "test-bearer-token-12345"
        },
        "endpoints": {
            "protected_bearer": {
                "path": "/protected/bearer",
                "method": "GET",
                "description": "Bearer Token认证测试",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        }
    },

    # 7. API Key (Header) 认证
    {
        "id": "mock_auth_apikey_header",
        "name": "Mock APIKey Header认证测试API",
        "description": "测试API Key放在Header中的认证调用",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {
            "type": "api_key",
            "api_key_header": "X-API-Key",
            "api_key_value": "test-api-key-67890"
        },
        "endpoints": {
            "protected_apikey": {
                "path": "/protected/apikey-header",
                "method": "GET",
                "description": "API Key Header认证测试",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        }
    },

    # 8. API Key (Query) 认证
    {
        "id": "mock_auth_apikey_query",
        "name": "Mock APIKey Query认证测试API",
        "description": "测试API Key放在Query参数中的认证调用",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {
            "type": "api_key",
            "api_key_header": "api_key",
            "api_key_value": "test-api-key-67890"
        },
        "endpoints": {
            "protected_apikey_query": {
                "path": "/protected/apikey-query",
                "method": "GET",
                "description": "API Key Query参数认证测试",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        }
    },

    # 9. Basic Auth 认证
    {
        "id": "mock_auth_basic",
        "name": "Mock Basic认证测试API",
        "description": "测试Basic Auth认证调用",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {
            "type": "basic",
            "username": "testuser",
            "password": "testpass"
        },
        "endpoints": {
            "protected_basic": {
                "path": "/protected/basic",
                "method": "GET",
                "description": "Basic Auth认证测试",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        }
    },

    # 10. Custom Headers 认证
    {
        "id": "mock_auth_custom",
        "name": "Mock自定义Header认证测试API",
        "description": "测试自定义Headers认证调用",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {
            "type": "custom",
            "custom_headers": {
                "X-Custom-Auth": "custom-secret-value"
            }
        },
        "endpoints": {
            "protected_custom": {
                "path": "/protected/custom",
                "method": "GET",
                "description": "自定义Header认证测试",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        }
    },

    # 11. 嵌套数据提取 (response_data_path)
    {
        "id": "mock_nested_data",
        "name": "Mock嵌套数据API",
        "description": "测试response_data_path从深层嵌套结构中提取数据",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "nested_data": {
                "path": "/nested-data",
                "method": "GET",
                "description": "返回深层嵌套数据，测试response_data_path提取（result.items.list）",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "result.items.list",
                "response_field_mapping": {}
            }
        }
    },

    # 12. 字段映射 (response_field_mapping)
    {
        "id": "mock_field_mapping",
        "name": "Mock字段映射API",
        "description": "测试response_field_mapping将英文字段映射为中文",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "field_mapping": {
                "path": "/field-mapping",
                "method": "GET",
                "description": "返回英文字段数据，测试字段映射（uid->用户ID, usr_nm->姓名等）",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data.records",
                "response_field_mapping": {
                    "uid": "用户ID",
                    "usr_nm": "姓名",
                    "usr_age": "年龄",
                    "usr_dept": "部门"
                }
            }
        }
    },

    # 13. 空数组响应
    {
        "id": "mock_empty_result",
        "name": "Mock空结果API",
        "description": "测试agent对空数组响应的处理",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "empty_result": {
                "path": "/empty-result",
                "method": "GET",
                "description": "返回空数组，测试空结果处理",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data.items",
                "response_field_mapping": {}
            }
        }
    },

    # 14. 分页响应
    {
        "id": "mock_paginated",
        "name": "Mock分页数据API",
        "description": "测试分页参数和分页响应处理",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "paginated": {
                "path": "/paginated",
                "method": "GET",
                "description": "分页数据查询，支持page和page_size参数",
                "params_mapping": {
                    "页码": "page",
                    "每页数量": "page_size"
                },
                "required_params": [],
                "default_params": {"page": 1, "page_size": 10},
                "params_descriptions": {
                    "页码": "当前页码，默认1",
                    "每页数量": "每页条数，默认10"
                },
                "response_data_path": "data.list",
                "response_field_mapping": {}
            }
        }
    },

    # 15. 复杂嵌套对象
    {
        "id": "mock_complex_nested",
        "name": "Mock复杂嵌套对象API",
        "description": "测试复杂嵌套结构数据的处理",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "complex_nested": {
                "path": "/complex-nested",
                "method": "GET",
                "description": "返回复杂嵌套结构（部门->员工->技能->项目）",
                "params_mapping": {},
                "required_params": [],
                "response_data_path": "data.departments",
                "response_field_mapping": {}
            }
        }
    },

    # 16. 默认参数
    {
        "id": "mock_default_params",
        "name": "Mock默认参数API",
        "description": "测试默认参数和可选参数的处理",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth": {"type": "none"},
        "endpoints": {
            "default_params": {
                "path": "/default-params",
                "method": "GET",
                "description": "测试默认参数：category默认all，limit默认10，sort_by默认id",
                "params_mapping": {
                    "分类": "category",
                    "数量": "limit",
                    "排序": "sort_by"
                },
                "required_params": [],
                "default_params": {
                    "category": "all",
                    "limit": 10,
                    "sort_by": "id"
                },
                "params_descriptions": {
                    "分类": "筛选分类，默认all",
                    "数量": "返回数量，默认10",
                    "排序": "排序字段，默认id"
                },
                "response_data_path": "data.items",
                "response_field_mapping": {}
            }
        }
    },
]


def main():
    print(f"=== Mock API 注册脚本 ===")
    print(f"后端地址: {BACKEND_URL}")
    print()

    try:
        token = login()
        print(f"✅ 登录成功，获取 Token")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for api_def in MOCK_APIS:
        api_id = api_def["id"]
        print(f"\n📦 注册 API: {api_id} ({api_def['name']})")

        # 先删除已存在的
        delete_if_exists(token, api_id)

        # 创建
        result = api_request(token, "POST", "/api/v1/apis", api_def)
        if result and result.get("success"):
            print(f"  ✅ 注册成功")
            success_count += 1
        else:
            print(f"  ❌ 注册失败: {result}")
            fail_count += 1

    print(f"\n=== 注册完成 ===")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
