#!/usr/bin/env python3
"""
将 Mock API 直接注册到 ApiConfig 数据库表中（非用户自定义API），
确保它们能被向量索引并被 agent 检索到。

用法:
    cd backend && python ../scripts/register_mock_apis_to_db.py
"""
import asyncio
import json
import sys
import os

# Support both local dev (backend/app) and container (/app/app)
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
app_dir = os.path.join(os.path.dirname(__file__), '..')
if os.path.exists(os.path.join(backend_dir, 'app')):
    sys.path.insert(0, backend_dir)
else:
    sys.path.insert(0, app_dir)

from app.access.database.connection import get_db
from app.access.database.models import ApiConfig
from sqlalchemy import select, delete

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

MOCK_APIS = [
    {
        "config_id": "mock_users_query",
        "name": "Mock用户查询API",
        "description": "测试GET+Query参数调用，支持按姓名、年龄、状态、部门筛选用户。可提问如：查询Mock系统中技术部的用户、查找年龄大于25岁的活跃用户等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_user_detail",
        "name": "Mock用户详情API",
        "description": "测试GET+Path参数调用，根据用户ID获取详细信息。可提问如：查看Mock系统中ID为1的用户详情、查询用户2的信息等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "get_user": {
                "path": "/users/{user_id}",
                "method": "GET",
                "description": "根据ID获取用户详情（GET+Path参数测试）",
                "params_mapping": {"用户ID": "user_id"},
                "required_params": ["用户ID"],
                "default_params": {},
                "params_descriptions": {"用户ID": "用户唯一标识"},
                "response_data_path": "data.user",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_order_create",
        "name": "Mock订单创建API",
        "description": "测试POST+JSON Body调用，创建新订单。可提问如：在Mock系统中创建一个订单、下单产品PROD-A给客户张三等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_user_update",
        "name": "Mock用户更新API",
        "description": "测试PUT+Path+Body调用，更新用户信息。可提问如：把Mock系统中用户ID为2的邮箱改成xxx、更新用户1的部门为销售部等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
                "default_params": {},
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
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_order_patch",
        "name": "Mock订单状态更新API",
        "description": "测试PATCH+Path+Body调用，部分更新订单状态。可提问如：把Mock系统中订单ORD-001的状态改成completed、修改订单状态等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
                "default_params": {},
                "params_descriptions": {
                    "订单ID": "订单编号",
                    "状态": "新状态：created/pending/shipped/completed",
                    "备注": "更新备注"
                },
                "response_data_path": "data.order",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_auth_bearer",
        "name": "Mock Bearer认证测试API",
        "description": "测试Bearer Token认证调用。可提问如：测试Mock系统的Bearer认证接口、调用需要Bearer Token的API等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "bearer",
        "auth_config": {"bearer_token": "test-bearer-token-12345"},
        "endpoints": {
            "protected_bearer": {
                "path": "/protected/bearer",
                "method": "GET",
                "description": "Bearer Token认证测试",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_auth_apikey_header",
        "name": "Mock APIKey Header认证测试API",
        "description": "测试API Key放在Header中的认证调用。可提问如：测试Mock系统的APIKey Header认证、调用需要X-API-Key的接口等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "api_key",
        "auth_config": {"api_key_header": "X-API-Key", "api_key_value": "test-api-key-67890"},
        "endpoints": {
            "protected_apikey": {
                "path": "/protected/apikey-header",
                "method": "GET",
                "description": "API Key Header认证测试",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_auth_apikey_query",
        "name": "Mock APIKey Query认证测试API",
        "description": "测试API Key放在Query参数中的认证调用。可提问如：测试Mock系统的APIKey Query认证等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "api_key",
        "auth_config": {"api_key_header": "api_key", "api_key_value": "test-api-key-67890", "api_key_param": "api_key"},
        "endpoints": {
            "protected_apikey_query": {
                "path": "/protected/apikey-query",
                "method": "GET",
                "description": "API Key Query参数认证测试",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_auth_basic",
        "name": "Mock Basic认证测试API",
        "description": "测试Basic Auth认证调用。可提问如：测试Mock系统的Basic认证、调用需要用户名密码的接口等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "basic",
        "auth_config": {"username": "testuser", "password": "testpass"},
        "endpoints": {
            "protected_basic": {
                "path": "/protected/basic",
                "method": "GET",
                "description": "Basic Auth认证测试",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_auth_custom",
        "name": "Mock自定义Header认证测试API",
        "description": "测试自定义Headers认证调用。可提问如：测试Mock系统的自定义Header认证等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "custom",
        "auth_config": {"custom_headers": {"X-Custom-Auth": "custom-secret-value"}},
        "endpoints": {
            "protected_custom": {
                "path": "/protected/custom",
                "method": "GET",
                "description": "自定义Header认证测试",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_nested_data",
        "name": "Mock嵌套数据API",
        "description": "测试response_data_path从深层嵌套结构中提取数据。可提问如：获取Mock系统的嵌套商品数据、查询多层嵌套的数据等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "nested_data": {
                "path": "/nested-data",
                "method": "GET",
                "description": "返回深层嵌套数据，测试response_data_path提取（result.items.list）",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "result.items.list",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_field_mapping",
        "name": "Mock字段映射API",
        "description": "测试response_field_mapping将英文字段映射为中文。可提问如：获取Mock系统的用户映射数据、查询带字段映射的接口等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "field_mapping": {
                "path": "/field-mapping",
                "method": "GET",
                "description": "返回英文字段数据，测试字段映射",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data.records",
                "response_field_mapping": {
                    "uid": "用户ID",
                    "usr_nm": "姓名",
                    "usr_age": "年龄",
                    "usr_dept": "部门"
                }
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_empty_result",
        "name": "Mock空结果API",
        "description": "测试agent对空数组响应的处理。可提问如：查询Mock系统的空结果接口、测试空数据返回等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "empty_result": {
                "path": "/empty-result",
                "method": "GET",
                "description": "返回空数组，测试空结果处理",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data.items",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_paginated",
        "name": "Mock分页数据API",
        "description": "测试分页参数和分页响应处理。可提问如：查询Mock系统分页数据第2页、每页5条数据、获取分页列表等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_complex_nested",
        "name": "Mock复杂嵌套对象API",
        "description": "测试复杂嵌套结构数据的处理。可提问如：获取Mock系统的部门组织结构、查询部门员工和项目信息等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "complex_nested": {
                "path": "/complex-nested",
                "method": "GET",
                "description": "返回复杂嵌套结构（部门->员工->技能->项目）",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "data.departments",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    {
        "config_id": "mock_default_params",
        "name": "Mock默认参数API",
        "description": "测试默认参数和可选参数的处理。可提问如：查询Mock系统的默认参数接口、分类选电子产品、获取默认数量数据等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
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
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 17. 布尔值参数测试 ============
    {
        "config_id": "mock_bool_params",
        "name": "Mock布尔值参数测试API",
        "description": "测试布尔值参数的传递和解析。可提问如：查询激活状态的用户、包含已删除的用户列表等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "bool_params_test": {
                "path": "/bool-params",
                "method": "GET",
                "description": "布尔值参数测试",
                "params_mapping": {
                    "是否激活": "is_active",
                    "包含已删除": "include_deleted",
                    "是否有邮箱": "has_email"
                },
                "required_params": [],
                "default_params": {"include_deleted": False},
                "params_descriptions": {
                    "是否激活": "是否只返回激活状态的用户: true/false",
                    "包含已删除": "是否包含已删除的用户，默认false",
                    "是否有邮箱": "是否筛选有邮箱的用户: true/false"
                },
                "response_data_path": "data.users",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 18. 浮点数参数测试 ============
    {
        "config_id": "mock_float_params",
        "name": "Mock浮点数参数测试API",
        "description": "测试浮点数参数的传递和解析。可提问如：查询价格在50到100之间的商品、搜索指定坐标附近的商品等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "float_params_test": {
                "path": "/float-params",
                "method": "GET",
                "description": "浮点数参数测试",
                "params_mapping": {
                    "最低价格": "price_min",
                    "最高价格": "price_max",
                    "纬度": "latitude",
                    "经度": "longitude",
                    "搜索半径": "radius"
                },
                "required_params": [],
                "default_params": {"radius": 1.0},
                "params_descriptions": {
                    "最低价格": "最低价格限制",
                    "最高价格": "最高价格限制",
                    "纬度": "纬度 -90~90",
                    "经度": "经度 -180~180",
                    "搜索半径": "搜索半径公里，默认1.0"
                },
                "response_data_path": "data.items",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 19. 数组参数测试 ============
    {
        "config_id": "mock_array_params",
        "name": "Mock数组参数测试API",
        "description": "测试数组/列表参数的传递和解析。可提问如：查询ID为1、2、3的项目、查找带有java或python标签的项目等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "array_params_test": {
                "path": "/array-params",
                "method": "GET",
                "description": "数组参数测试",
                "params_mapping": {
                    "ID列表": "ids",
                    "标签": "tags",
                    "状态列表": "statuses"
                },
                "required_params": [],
                "default_params": {"statuses": ["active"]},
                "params_descriptions": {
                    "ID列表": "项目ID列表，多个用逗号分隔",
                    "标签": "标签列表，多个用逗号分隔",
                    "状态列表": "状态列表，默认['active']"
                },
                "response_data_path": "data.items",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 20. 日期时间参数测试 ============
    {
        "config_id": "mock_datetime_params",
        "name": "Mock日期时间参数测试API",
        "description": "测试日期时间参数的传递和解析。可提问如：查询2026年4月1日到4月15日的会议、查找指定日期之后的事件等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "datetime_params_test": {
                "path": "/datetime-params",
                "method": "GET",
                "description": "日期时间参数测试",
                "params_mapping": {
                    "开始日期": "start_date",
                    "结束日期": "end_date",
                    "时间戳": "timestamp"
                },
                "required_params": [],
                "default_params": {},
                "params_descriptions": {
                    "开始日期": "开始日期 YYYY-MM-DD",
                    "结束日期": "结束日期 YYYY-MM-DD",
                    "时间戳": "ISO8601格式时间戳"
                },
                "response_data_path": "data.events",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 21. 多层嵌套Body测试 ============
    {
        "config_id": "mock_nested_body",
        "name": "Mock多层嵌套Body测试API",
        "description": "测试多层嵌套JSON Body的传递和解析。可提问如：创建一个带有嵌套profile和settings的用户配置等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "nested_body_test": {
                "path": "/nested-body",
                "method": "POST",
                "description": "多层嵌套Body测试",
                "params_mapping": {
                    "用户信息": "user",
                    "个人资料": "user.profile",
                    "设置": "user.settings",
                    "通知设置": "user.settings.notifications",
                    "邮箱通知": "user.settings.notifications.email"
                },
                "required_params": ["user"],
                "default_params": {},
                "params_descriptions": {
                    "用户信息": "用户对象，包含profile和settings",
                    "个人资料": "用户个人资料",
                    "设置": "用户设置",
                    "通知设置": "通知设置",
                    "邮箱通知": "是否开启邮箱通知"
                },
                "response_data_path": "data.echo",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 22. 参数类型转换测试 ============
    {
        "config_id": "mock_type_coercion",
        "name": "Mock参数类型转换测试API",
        "description": "测试参数类型强制转换。可提问如：测试各种类型参数的正确传递等。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "type_coercion_test": {
                "path": "/type-coercion",
                "method": "GET",
                "description": "参数类型转换测试",
                "params_mapping": {
                    "整数字段": "int_field",
                    "字符串字段": "str_field",
                    "浮点数字段": "float_field",
                    "布尔字段": "bool_field"
                },
                "required_params": ["int_field", "str_field", "float_field", "bool_field"],
                "default_params": {},
                "params_descriptions": {
                    "整数字段": "期望整数",
                    "字符串字段": "期望字符串",
                    "浮点数字段": "期望浮点数",
                    "布尔字段": "期望布尔值"
                },
                "response_data_path": "data.received",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 23. 纯字符串响应测试 ============
    {
        "config_id": "mock_string_response",
        "name": "Mock纯字符串响应测试API",
        "description": "测试返回纯字符串而非JSON对象的API响应处理。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "string_response": {
                "path": "/string-response",
                "method": "GET",
                "description": "纯字符串响应",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
    # ============ 24. 纯数字响应测试 ============
    {
        "config_id": "mock_number_response",
        "name": "Mock纯数字响应测试API",
        "description": "测试返回纯数字而非JSON对象的API响应处理。",
        "base_url": f"{BACKEND_URL}/api/v1/mock-api",
        "auth_type": "none",
        "auth_config": {},
        "endpoints": {
            "number_response": {
                "path": "/number-response",
                "method": "GET",
                "description": "纯数字响应",
                "params_mapping": {},
                "required_params": [],
                "default_params": {},
                "params_descriptions": {},
                "response_data_path": "",
                "response_field_mapping": {}
            }
        },
        "timeout": 30,
        "retry_count": 3,
        "is_active": True,
        "is_system": False,
    },
]


async def main():
    print("=== Mock API 数据库注册脚本 ===")
    print(f"后端地址: {BACKEND_URL}")
    print()

    db = await get_db()
    async with db.get_session() as session:
        # 先删除已存在的 Mock API
        for api_def in MOCK_APIS:
            result = await session.execute(
                select(ApiConfig).where(ApiConfig.config_id == api_def["config_id"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                print(f"🗑️  删除旧记录: {api_def['config_id']}")
        await session.commit()

        # 插入新记录
        success_count = 0
        for api_def in MOCK_APIS:
            api = ApiConfig(
                config_id=api_def["config_id"],
                name=api_def["name"],
                description=api_def["description"],
                base_url=api_def["base_url"],
                auth_type=api_def["auth_type"],
                auth_config=api_def["auth_config"],
                endpoints=api_def["endpoints"],
                timeout=api_def["timeout"],
                retry_count=api_def["retry_count"],
                is_active=api_def["is_active"],
                is_system=api_def["is_system"],
                created_by=1,
            )
            session.add(api)
            print(f"✅ 准备插入: {api_def['config_id']} ({api_def['name']})")
            success_count += 1

        await session.commit()

    print(f"\n=== 注册完成 ===")
    print(f"✅ 成功: {success_count}")

    # 重建向量索引
    print("\n🔄 重建API向量索引...")
    from app.services.api_retrieval_service import get_api_retrieval_service
    retrieval_service = get_api_retrieval_service()
    result = await retrieval_service.rebuild_all_embeddings()
    print(f"✅ 索引重建完成: 成功 {result['success']} 个, 失败 {result['failure']} 个")


if __name__ == "__main__":
    asyncio.run(main())
