"""
Mock API Server - 全类型API调用测试端点
用于验证agent对各种API调用格式的支持

覆盖场景：
- HTTP方法: GET, POST, PUT, PATCH
- 参数位置: Query, Path, Body(JSON)
- 认证方式: None, APIKey(header/query), Bearer, Basic, Custom
- 响应格式: 简单对象、数组、嵌套结构、分页、空结果、字段映射
- 特殊场景: 默认参数、可选参数、复杂嵌套对象
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64

router = APIRouter(tags=["Mock API"])

# ============ 内存数据存储 ============
MOCK_USERS = [
    {"id": 1, "name": "张三", "age": 28, "status": "active", "department": "技术部", "email": "zhangsan@example.com"},
    {"id": 2, "name": "李四", "age": 35, "status": "active", "department": "销售部", "email": "lisi@example.com"},
    {"id": 3, "name": "王五", "age": 22, "status": "inactive", "department": "技术部", "email": "wangwu@example.com"},
    {"id": 4, "name": "赵六", "age": 30, "status": "active", "department": "人事部", "email": "zhaoliu@example.com"},
    {"id": 5, "name": "孙七", "age": 26, "status": "active", "department": "技术部", "email": "sunqi@example.com"},
]

MOCK_ORDERS = [
    {"order_id": "ORD-001", "product_id": "PROD-A", "quantity": 2, "customer_name": "张三", "status": "completed", "amount": 199.99},
    {"order_id": "ORD-002", "product_id": "PROD-B", "quantity": 1, "customer_name": "李四", "status": "pending", "amount": 89.50},
    {"order_id": "ORD-003", "product_id": "PROD-A", "quantity": 5, "customer_name": "王五", "status": "shipped", "amount": 499.95},
]

# ============ 1. GET + Query参数 ============
@router.get("/users", summary="搜索用户（GET+Query参数）")
async def search_users(
    name: Optional[str] = Query(None, description="按姓名模糊搜索"),
    age_min: Optional[int] = Query(None, description="最小年龄"),
    age_max: Optional[int] = Query(None, description="最大年龄"),
    status: Optional[str] = Query(None, description="状态: active/inactive"),
    department: Optional[str] = Query(None, description="部门"),
):
    """GET请求 + Query参数测试 - 支持多条件筛选"""
    results = MOCK_USERS.copy()
    if name:
        results = [u for u in results if name in u["name"]]
    if age_min is not None:
        results = [u for u in results if u["age"] >= age_min]
    if age_max is not None:
        results = [u for u in results if u["age"] <= age_max]
    if status:
        results = [u for u in results if u["status"] == status]
    if department:
        results = [u for u in results if u["department"] == department]
    return {
        "code": 200,
        "message": "success",
        "data": {
            "users": results,
            "total": len(results),
            "filters_applied": {"name": name, "age_min": age_min, "age_max": age_max, "status": status, "department": department}
        }
    }


# ============ 2. GET + Path参数 ============
@router.get("/users/{user_id}", summary="获取用户详情（GET+Path参数）")
async def get_user(user_id: int):
    """GET请求 + Path参数测试"""
    user = next((u for u in MOCK_USERS if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "code": 200,
        "message": "success",
        "data": {"user": user}
    }


# ============ 3. POST + JSON Body ============
@router.post("/orders", summary="创建订单（POST+JSON Body）")
async def create_order(body: Dict[str, Any]):
    """POST请求 + JSON Body测试"""
    product_id = body.get("product_id")
    quantity = body.get("quantity", 1)
    customer_name = body.get("customer_name")
    address = body.get("address", "")
    
    if not product_id or not customer_name:
        raise HTTPException(status_code=400, detail="缺少必需参数: product_id, customer_name")
    
    new_order = {
        "order_id": f"ORD-{len(MOCK_ORDERS) + 1:03d}",
        "product_id": product_id,
        "quantity": quantity,
        "customer_name": customer_name,
        "address": address,
        "status": "created",
        "amount": round(quantity * 99.99, 2)
    }
    MOCK_ORDERS.append(new_order)
    return {
        "code": 200,
        "message": "订单创建成功",
        "data": {"order": new_order}
    }


# ============ 4. PUT + Path + JSON Body ============
@router.put("/users/{user_id}", summary="更新用户信息（PUT+Path+Body）")
async def update_user(user_id: int, body: Dict[str, Any]):
    """PUT请求 + Path参数 + JSON Body测试"""
    user = next((u for u in MOCK_USERS if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    allowed_fields = ["name", "email", "age", "status", "department"]
    updated = False
    for field in allowed_fields:
        if field in body:
            user[field] = body[field]
            updated = True
    
    return {
        "code": 200,
        "message": "用户信息更新成功" if updated else "无变更",
        "data": {"updated": updated, "user": user}
    }


# ============ 5. PATCH + Path + JSON Body ============
@router.patch("/orders/{order_id}", summary="更新订单状态（PATCH+Path+Body）")
async def patch_order(order_id: str, body: Dict[str, Any]):
    """PATCH请求 + Path参数 + JSON Body测试"""
    order = next((o for o in MOCK_ORDERS if o["order_id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if "status" in body:
        order["status"] = body["status"]
    if "note" in body:
        order["note"] = body["note"]
    
    return {
        "code": 200,
        "message": "订单更新成功",
        "data": {"order": order}
    }


# ============ 6. Bearer Token认证 ============
@router.get("/protected/bearer", summary="Bearer Token认证测试")
async def protected_bearer(authorization: Optional[str] = Header(None)):
    """Bearer Token认证测试"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少Bearer Token")
    token = authorization.replace("Bearer ", "")
    if token != "test-bearer-token-12345":
        raise HTTPException(status_code=403, detail="无效的Token")
    return {
        "code": 200,
        "message": "认证成功",
        "data": {"message": "Authorized", "user": "admin", "token_type": "bearer"}
    }


# ============ 7. API Key (Header)认证 ============
@router.get("/protected/apikey-header", summary="API Key Header认证测试")
async def protected_apikey_header(x_api_key: Optional[str] = Header(None)):
    """API Key (Header)认证测试"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少API Key")
    if x_api_key != "test-api-key-67890":
        raise HTTPException(status_code=403, detail="无效的API Key")
    return {
        "code": 200,
        "message": "认证成功",
        "data": {"message": "Valid API Key", "auth_type": "api_key_header"}
    }


# ============ 8. API Key (Query)认证 ============
@router.get("/protected/apikey-query", summary="API Key Query认证测试")
async def protected_apikey_query(api_key: Optional[str] = Query(None)):
    """API Key (Query参数)认证测试"""
    if not api_key:
        raise HTTPException(status_code=401, detail="缺少API Key参数")
    if api_key != "test-api-key-67890":
        raise HTTPException(status_code=403, detail="无效的API Key")
    return {
        "code": 200,
        "message": "认证成功",
        "data": {"message": "Valid API Key", "auth_type": "api_key_query"}
    }


# ============ 9. Basic Auth认证 ============
@router.get("/protected/basic", summary="Basic Auth认证测试")
async def protected_basic(authorization: Optional[str] = Header(None)):
    """Basic Auth认证测试"""
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="缺少Basic Auth")
    try:
        creds = base64.b64decode(authorization.replace("Basic ", "")).decode()
        username, password = creds.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="无效的Basic Auth格式")
    
    if username != "testuser" or password != "testpass":
        raise HTTPException(status_code=403, detail="用户名或密码错误")
    
    return {
        "code": 200,
        "message": "认证成功",
        "data": {"message": "Authenticated", "user": username, "auth_type": "basic"}
    }


# ============ 10. Custom Headers认证 ============
@router.get("/protected/custom", summary="自定义Header认证测试")
async def protected_custom(
    x_custom_auth: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None)
):
    """自定义Headers认证测试"""
    if not x_custom_auth:
        raise HTTPException(status_code=401, detail="缺少X-Custom-Auth")
    if x_custom_auth != "custom-secret-value":
        raise HTTPException(status_code=403, detail="无效的自定义认证")
    return {
        "code": 200,
        "message": "认证成功",
        "data": {"message": "Custom auth OK", "request_id": x_request_id, "auth_type": "custom"}
    }


# ============ 11. 嵌套数据提取 (response_data_path测试) ============
@router.get("/nested-data", summary="嵌套数据结构（response_data_path测试）")
async def nested_data():
    """返回深层嵌套数据，测试response_data_path提取"""
    return {
        "status": "ok",
        "result": {
            "metadata": {"total": 3, "page": 1},
            "items": {
                "list": [
                    {"id": 1, "name": "商品A", "price": 100},
                    {"id": 2, "name": "商品B", "price": 200},
                    {"id": 3, "name": "商品C", "price": 300},
                ]
            }
        }
    }


# ============ 12. 字段映射 (response_field_mapping测试) ============
@router.get("/field-mapping", summary="字段映射测试（response_field_mapping）")
async def field_mapping_data():
    """返回英文字段名数据，测试response_field_mapping映射为中文"""
    return {
        "code": 200,
        "data": {
            "records": [
                {"uid": 1, "usr_nm": "张三", "usr_age": 28, "usr_dept": "技术部"},
                {"uid": 2, "usr_nm": "李四", "usr_age": 35, "usr_dept": "销售部"},
                {"uid": 3, "usr_nm": "王五", "usr_age": 22, "usr_dept": "技术部"},
            ]
        }
    }


# ============ 13. 空数组响应 ============
@router.get("/empty-result", summary="空结果测试")
async def empty_result():
    """返回空数组，测试agent对空结果的处理"""
    return {
        "code": 200,
        "message": "success",
        "data": {"items": [], "total": 0}
    }


# ============ 14. 分页响应 ============
@router.get("/paginated", summary="分页数据测试")
async def paginated_data(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量")
):
    """分页响应测试"""
    all_items = [
        {"id": i, "name": f"项目{i}", "value": i * 10}
        for i in range(1, 51)
    ]
    total = len(all_items)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_items[start:end]
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total": total
            }
        }
    }


# ============ 15. 复杂嵌套对象 ============
@router.get("/complex-nested", summary="复杂嵌套对象测试")
async def complex_nested():
    """返回复杂嵌套结构数据"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "departments": [
                {
                    "name": "技术部",
                    "manager": "张三",
                    "budget": 500000,
                    "employees": [
                        {"name": "张三", "level": "P7", "skills": ["Python", "Go", "K8s"]},
                        {"name": "王五", "level": "P5", "skills": ["Python", "React"]},
                        {"name": "孙七", "level": "P6", "skills": ["Java", "Spring"]},
                    ],
                    "projects": [
                        {"name": "AI平台", "status": "进行中", "progress": 75},
                        {"name": "数据中台", "status": "已完成", "progress": 100},
                    ]
                },
                {
                    "name": "销售部",
                    "manager": "李四",
                    "budget": 300000,
                    "employees": [
                        {"name": "李四", "level": "M3", "skills": ["谈判", "客户关系"]},
                    ],
                    "projects": [
                        {"name": "Q3冲刺", "status": "进行中", "progress": 60},
                    ]
                }
            ]
        }
    }


# ============ 16. 默认参数测试 ============
@router.get("/default-params", summary="默认参数测试")
async def default_params_test(
    category: str = Query("all", description="分类，默认all"),
    limit: int = Query(10, description="返回数量，默认10"),
    sort_by: str = Query("id", description="排序字段，默认id")
):
    """测试默认参数和可选参数"""
    all_items = [
        {"id": i, "category": "电子产品" if i % 2 == 0 else "服装", "name": f"商品{i}"}
        for i in range(1, 21)
    ]
    if category != "all":
        all_items = [item for item in all_items if item["category"] == category]
    
    if sort_by == "id":
        all_items.sort(key=lambda x: x["id"])
    elif sort_by == "name":
        all_items.sort(key=lambda x: x["name"])
    
    results = all_items[:limit]
    return {
        "code": 200,
        "message": "success",
        "data": {
            "category": category,
            "limit": limit,
            "sort_by": sort_by,
            "items": results,
            "total": len(results)
        }
    }


# ============ 健康检查 ============
@router.get("/health", summary="Mock API健康检查")
async def mock_health():
    return {"status": "ok", "mock_api": "running", "version": "1.0.0"}
