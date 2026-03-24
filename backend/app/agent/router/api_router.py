"""
API Router - 智能选择API和端点
根据用户意图自动选择合适的API和端点
"""
from typing import Dict, Any, Optional, List, Tuple
import re

from app.config.api_config import get_api_registry, APIConfig, APIEndpointConfig
from app.utils.logger import get_logger

logger = get_logger()


class APIRouter:
    """
    API路由选择器
    根据用户问题智能选择要调用的API和端点
    """

    def __init__(self):
        self._registry = get_api_registry()

        # 关键词映射：关键词 -> API ID
        self._keyword_mapping = {
            # 库存相关
            "库存": "inventory",
            "库存量": "inventory",
            "存货": "inventory",
            "仓库": "inventory",
            "库存查询": "inventory",
            "商品库存": "inventory",
            "库存详情": "inventory",

            # 销售相关
            "销售": "sales",
            "订单": "sales",
            "销售额": "sales",
            "销量": "sales",
            "订单量": "sales",
            "订单详情": "sales",
            "销售统计": "sales",
            "销售数据": "sales",
            "客户订单": "sales",
            "购买": "sales",

            # 员工相关
            "员工": "employee",
            "雇员": "employee",
            "职工": "employee",
            "人员": "employee",
            "同事": "employee",
            "员工信息": "employee",
            "员工列表": "employee",

            # 产品相关 (映射到库存API，因为产品信息通常在库存中)
            "产品": "inventory",
            "商品": "inventory",
            "货品": "inventory",
            "物品": "inventory",
            "前": "inventory",  # "前5个产品"等
            "个产品": "inventory",
            "个商品": "inventory",
            "客户": "sales",  # 客户相关映射到销售
            "分类": "inventory",  # 分类相关
            "类别": "inventory",
            "供应商": "inventory",
            "供应商": "inventory",

            # IP地理位置相关
            "IP": "geo",
            "ip": "geo",
            "IP地址": "geo",
            "ip地址": "geo",
            "归属地": "geo",
            "地理位置": "geo",
            "IP归属": "geo",
            "ip归属": "geo",
            "IP查询": "geo",
            "ip查询": "geo",
            "IP定位": "geo",
            "ip定位": "geo",
            "所在城市": "geo",
            "所在省份": "geo",
            "运营商": "geo",
        }

        # 端点关键词映射
        self._endpoint_keywords = {
            "inventory": {
                "query": ["查询", "列表", "所有", "全部", "搜索"],
                "detail": ["详情", "详细", "单个", "具体"],
            },
            "sales": {
                "orders": ["订单", "列表", "查询", "所有"],
                "stats": ["统计", "汇总", "总计", "总量", "合计"],
                "order_detail": ["详情", "详细", "具体订单"],
            },
            "employee": {
                "list": ["列表", "查询", "所有", "全部", "信息"],
                "detail": ["详情", "详细", "单个"],
            },
            "geo": {
                "ip_lookup": ["查询", "查找", "定位", "归属", "地址"],
            },
        }

    def route(self, user_query: str, entities: Dict[str, Any] = None) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        路由用户问题到具体的API和端点

        Args:
            user_query: 用户问题
            entities: 从问题中提取的实体

        Returns:
            Tuple[api_id, endpoint, params] 或 None
        """
        query_lower = user_query.lower()

        # 1. 首先检查LLM提供的api_hint
        api_hint = entities.get("api_hint") if entities else None
        if api_hint:
            # 验证hint是否有效
            api_config = self._registry.get_api(api_hint)
            if api_config:
                api_id = api_hint
                logger.info(f"使用LLM提供的API提示: {api_id}")
            else:
                # hint无效，使用关键词检测
                api_id = self._detect_api(user_query)
        else:
            # 2. 根据关键词识别API
            api_id = self._detect_api(user_query)

        if not api_id:
            logger.warning(f"无法识别API类型: {user_query}")
            return None

        # 3. 识别端点
        endpoint = self._detect_endpoint(api_id, user_query)
        if not endpoint:
            # 获取该API的第一个可用端点
            api_config = self._registry.get_api(api_id)
            if api_config and api_config.endpoints:
                endpoint = list(api_config.endpoints.keys())[0]
            else:
                return None

        # 4. 提取参数
        params = self._extract_params(user_query, api_id, endpoint, entities or {})

        logger.info(f"API路由结果: api_id={api_id}, endpoint={endpoint}, params={params}")

        return (api_id, endpoint, params)

    def _detect_api(self, user_query: str) -> Optional[str]:
        """检测应该使用哪个API"""
        scores = {}

        for keyword, api_id in self._keyword_mapping.items():
            if keyword in user_query:
                scores[api_id] = scores.get(api_id, 0) + 1

        if not scores:
            return None

        # 返回得分最高的API
        return max(scores, key=scores.get)

    def _detect_endpoint(self, api_id: str, user_query: str) -> Optional[str]:
        """检测应该使用哪个端点"""
        endpoint_keywords = self._endpoint_keywords.get(api_id, {})
        if not endpoint_keywords:
            return None

        scores = {}
        for endpoint, keywords in endpoint_keywords.items():
            for keyword in keywords:
                if keyword in user_query:
                    scores[endpoint] = scores.get(endpoint, 0) + 1

        if not scores:
            # 返回默认端点（第一个）
            api_config = self._registry.get_api(api_id)
            if api_config and api_config.endpoints:
                return list(api_config.endpoints.keys())[0]
            return None

        return max(scores, key=scores.get)

    def _extract_params(
        self,
        user_query: str,
        api_id: str,
        endpoint: str,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从用户问题中提取API参数"""
        params = {}

        # 获取端点配置
        api_config = self._registry.get_api(api_id)
        if not api_config:
            return params

        endpoint_config = api_config.endpoints.get(endpoint)
        if not endpoint_config:
            return params

        # 从entities中提取
        for user_param in endpoint_config.params_mapping.keys():
            if user_param in entities:
                params[user_param] = entities[user_param]

        # 从问题中提取常见参数
        # 时间参数
        time_patterns = [
            (r"最近(\d+)天", lambda m: {"days": int(m.group(1))}),
            (r"最近(\d+)周", lambda m: {"weeks": int(m.group(1))}),
            (r"最近(\d+)月", lambda m: {"months": int(m.group(1))}),
            (r"(\d{4}-\d{2}-\d{2})", lambda m: {"date": m.group(1)}),
        ]

        for pattern, extractor in time_patterns:
            match = re.search(pattern, user_query)
            if match:
                time_params = extractor(match)
                if "days" in time_params:
                    import datetime
                    end_date = datetime.date.today()
                    start_date = end_date - datetime.timedelta(days=time_params["days"])
                    params["start_date"] = start_date.strftime("%Y-%m-%d")
                    params["end_date"] = end_date.strftime("%Y-%m-%d")
                elif "date" in time_params:
                    params["date"] = time_params["date"]

        # ID参数
        id_match = re.search(r"ID[是为：:]\s*(\w+)", user_query, re.IGNORECASE)
        if id_match:
            params["id"] = id_match.group(1)

        # 订单号
        order_match = re.search(r"订单[号]?[是为：:]\s*(\w+)", user_query)
        if order_match:
            params["order_id"] = order_match.group(1)

        # IP地址参数 - 支持IPv4格式
        ip_match = re.search(
            r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
            user_query
        )
        if ip_match:
            params["ip"] = ip_match.group(1)

        return params

    def get_api_description_for_llm(self) -> str:
        """获取供LLM使用的API描述"""
        return self._registry.get_api_description()


# 全局实例
_api_router: Optional[APIRouter] = None


def get_api_router() -> APIRouter:
    """获取API路由实例"""
    global _api_router
    if _api_router is None:
        _api_router = APIRouter()
    return _api_router