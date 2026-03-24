"""
Intent recognition module.
Analyzes user queries to determine intent and extract entities.
"""
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.config.llm_config import BaseLLMClient, get_llm
from app.models.chat import IntentType, IntentResult
from app.agent.prompts.intent_prompt import get_intent_prompt
from app.agent.router.api_router import get_api_router


class IntentRecognizer:
    """
    Recognizes user intent from natural language queries.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self._llm = llm_client

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def _get_api_list_description(self) -> str:
        """Get description of available APIs for the prompt."""
        try:
            api_router = get_api_router()
            return api_router.get_api_description_for_llm()
        except Exception:
            return "暂无已配置的API"

    async def recognize(self, user_query: str) -> IntentResult:
        """
        Recognize intent from user query.

        Args:
            user_query: User's natural language query

        Returns:
            IntentResult with intent type, entities, metrics, dimensions
        """
        # Get API list for context
        api_list_desc = self._get_api_list_description()

        # Get LLM response
        prompt = get_intent_prompt(user_query, api_list_desc)
        response = await self.llm.chat([
            {"role": "system", "content": "你是一个专业的数据分析助手，擅长理解用户意图并选择合适的API获取数据。"},
            {"role": "user", "content": prompt}
        ])

        # Parse LLM response
        intent_data = self._parse_llm_response(response)

        # Enhance with rule-based recognition
        intent_data = self._enhance_with_rules(user_query, intent_data)

        # Build IntentResult
        intent_type_str = intent_data.get("intent_type", "data_statistic")
        if intent_type_str is None:
            intent_type_str = "data_statistic"

        # Validate intent_type
        valid_intents = ["data_detail", "data_statistic", "data_analysis", "data_export", "api_query", "unknown"]
        if intent_type_str not in valid_intents:
            intent_type_str = "data_statistic"

        return IntentResult(
            intent_type=IntentType(intent_type_str),
            entities=intent_data.get("entities", {}),
            metrics=intent_data.get("metrics", []),
            dimensions=intent_data.get("dimensions", []),
            time_range=self._parse_time_range(intent_data.get("entities", {}).get("time_range", {})),
            confidence=intent_data.get("confidence", 0.8),
            missing_info=intent_data.get("missing_info"),
            clarification_question=intent_data.get("clarification_question"),
        )

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON."""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Return default structure if parsing fails
        return {
            "intent_type": "data_statistic",
            "entities": {},
            "metrics": [],
            "dimensions": [],
            "confidence": 0.5,
        }

    def _enhance_with_rules(self, query: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance intent recognition with rule-based patterns."""
        query_lower = query.lower()

        # 所有数据查询都走API路径，不再使用SQL直连数据库
        # 导出意图
        if any(kw in query_lower for kw in ["导出", "下载", "excel", "export"]):
            intent_data["intent_type"] = "data_export"
        # 分析意图
        elif any(kw in query_lower for kw in ["分析", "趋势", "对比", "比较", "为什么"]):
            intent_data["intent_type"] = "api_query"
        # 其他所有查询都走API
        else:
            intent_data["intent_type"] = "api_query"

        # 保存原始查询用于后续处理
        intent_data.setdefault("entities", {})["original_query"] = query

        # 保留LLM提供的api_hint（如果有的话）
        # 这个hint会在API路由时被使用

        # Extract time range if not present
        if not intent_data.get("entities", {}).get("time_range"):
            time_range = self._extract_time_range(query)
            if time_range:
                intent_data.setdefault("entities", {})["time_range"] = time_range

        # Extract metrics
        metrics_patterns = {
            "订单": "订单量",
            "销售额": "销售额",
            "营收": "营收",
            "用户": "用户数",
            "转化率": "转化率",
            "gmv": "GMV",
        }
        for pattern, metric in metrics_patterns.items():
            if pattern in query_lower and metric not in intent_data.get("metrics", []):
                intent_data.setdefault("metrics", []).append(metric)

        return intent_data

    def _extract_time_range(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract time range from query using patterns."""
        now = datetime.now()

        patterns = [
            (r"最近(\d+)天", lambda m: self._days_ago(int(m.group(1)))),
            (r"最近(\d+)周", lambda m: self._days_ago(int(m.group(1)) * 7)),
            (r"最近(\d+)月", lambda m: self._months_ago(int(m.group(1)))),
            (r"昨天", lambda m: self._days_ago(1)),
            (r"今天", lambda m: self._days_ago(0)),
            (r"本周", lambda m: self._this_week()),
            (r"本月", lambda m: self._this_month()),
            (r"上周", lambda m: self._last_week()),
            (r"上月", lambda m: self._last_month()),
        ]

        for pattern, extractor in patterns:
            match = re.search(pattern, query)
            if match:
                return extractor(match)

        return None

    def _days_ago(self, days: int) -> Dict[str, Any]:
        """Get time range for N days ago."""
        now = datetime.now()
        start = now - timedelta(days=days)
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "description": f"最近{days}天",
        }

    def _months_ago(self, months: int) -> Dict[str, Any]:
        """Get time range for N months ago."""
        now = datetime.now()
        start = now - timedelta(days=months * 30)  # Approximate
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "description": f"最近{months}月",
        }

    def _this_week(self) -> Dict[str, Any]:
        """Get this week's time range."""
        now = datetime.now()
        start = now - timedelta(days=now.weekday())
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "description": "本周",
        }

    def _this_month(self) -> Dict[str, Any]:
        """Get this month's time range."""
        now = datetime.now()
        start = now.replace(day=1)
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "description": "本月",
        }

    def _last_week(self) -> Dict[str, Any]:
        """Get last week's time range."""
        now = datetime.now()
        end = now - timedelta(days=now.weekday() + 1)
        start = end - timedelta(days=6)
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "description": "上周",
        }

    def _last_month(self) -> Dict[str, Any]:
        """Get last month's time range."""
        now = datetime.now()
        first_of_this_month = now.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "description": "上月",
        }

    def _parse_time_range(self, time_range: Any) -> Optional[Dict[str, Any]]:
        """Parse time range to ensure proper format."""
        if isinstance(time_range, dict):
            return time_range
        return None