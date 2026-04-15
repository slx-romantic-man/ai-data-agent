"""
Suggestion Service - Smart question suggestions based on user's APIs and chat history.
"""
from typing import List, Dict, Any, Optional, Union
import random

from app.config.api_config import get_api_registry, APIConfig
from app.services.conversation_service import get_conversation_service
from app.services.api_permission_service import get_api_permission_service
from app.models.api_permission import APIConfigPublic
from app.utils.logger import get_logger

logger = get_logger()


class SuggestionService:
    """
    Service for generating smart question suggestions.

    Generates suggestions based on:
    1. User's configured APIs and their endpoints (permission-aware)
    2. Recent conversation patterns
    3. API-specific question templates

    Format: "具体问题……（API名称）"
    """

    # Question templates for different API types
    API_TEMPLATES = {
        # Weather API templates
        "weather": [
            "查询{city}的天气情况",
            "{city}未来三天的天气预报",
            "今天{city}的气温是多少",
        ],
        # Stock API templates
        "stock": [
            "查询{symbol}的股票价格",
            "{symbol}股票的最新行情",
            "分析{symbol}的走势",
        ],
        # Geo/IP API templates
        "geo": [
            "查询IP地址{ip}的地理位置",
            "这个IP来自哪个城市",
        ],
        # Generic API templates
        "generic": [
            "查询{name}的数据",
            "帮我调用{name}API",
            "使用{name}获取数据",
        ],
    }

    # Keywords to identify API types
    API_TYPE_KEYWORDS = {
        "weather": ["天气", "weather", "气象"],
        "stock": ["股票", "stock", "行情", "证券"],
        "geo": ["地理位置", "geo", "ip", "位置"],
    }

    def __init__(self):
        self.conversation_service = get_conversation_service()

    def _get_api_type(self, api_name: str, api_description: Optional[str]) -> str:
        """Determine API type based on name and description."""
        name_lower = api_name.lower()
        desc_lower = (api_description or "").lower()

        for api_type, keywords in self.API_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower or keyword in desc_lower:
                    return api_type
        return "generic"

    def _fill_template(self, template: str, api_name: str) -> str:
        """Fill a template with sample values."""
        if "{city}" in template:
            cities = ["北京", "上海", "广州", "深圳", "杭州"]
            return template.format(city=random.choice(cities))
        elif "{symbol}" in template:
            symbols = ["AAPL", "腾讯", "阿里巴巴", "茅台"]
            return template.format(symbol=random.choice(symbols))
        elif "{ip}" in template:
            return template.format(ip="8.8.8.8")
        elif "{name}" in template:
            return template.format(name=api_name)
        else:
            return template

    def _generate_questions_for_api(
        self,
        api_name: str,
        api_description: Optional[str],
        recommended_questions: Optional[List[str]],
        endpoints: Dict[str, Any],
    ) -> List[str]:
        """Generate question suggestions for a specific API.

        Format: "具体问题……（API名称）"
        Priority: pre-configured recommended_questions > template-based fallback > endpoint description
        """
        questions = []

        # Priority 1: Use pre-configured recommended questions
        if recommended_questions:
            for q in recommended_questions[:3]:
                questions.append(f"{q}（{api_name}）")
            return questions

        # Priority 2: Template-based fallback
        api_type = self._get_api_type(api_name, api_description)
        templates = self.API_TEMPLATES.get(api_type, self.API_TEMPLATES["generic"])

        for template in templates[:2]:
            filled = self._fill_template(template, api_name)
            questions.append(f"{filled}（{api_name}）")

        # Priority 3: Endpoint description-based (handle both dict and Pydantic endpoint)
        for ep_name, endpoint in list(endpoints.items())[:2]:
            ep_desc = endpoint.get('description') if isinstance(endpoint, dict) else getattr(endpoint, 'description', None)
            if ep_desc:
                questions.append(f"{api_name}: {ep_desc}（{api_name}）")

        return questions

    def _analyze_recent_conversations(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[str]:
        """Analyze recent conversations to find patterns."""
        suggestions = []

        if not conversations:
            return suggestions

        # Look at the most recent conversations
        for conv in conversations[:3]:
            messages = conv.get("messages", [])
            if messages:
                # Get the first user message (usually the question)
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        if content and len(content) < 100:
                            # Suggest follow-up questions
                            suggestions.append(f"继续查询: {content[:30]}...")
                        break

        return suggestions

    async def get_suggestions(
        self,
        user_id: str,
        max_suggestions: int = 4
    ) -> List[str]:
        """
        Get smart question suggestions for a user (permission-aware).

        Each suggestion is formatted as: "具体问题……（API名称）"

        Args:
            user_id: User ID
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggested questions
        """
        suggestions = []

        try:
            # Get permission-aware user APIs via APIPermissionService
            # This respects admin/employee permission isolation:
            # - Admin: all active APIs
            # - Non-admin: only APIs with active permissions
            perm_service = await get_api_permission_service()
            user_apis = await perm_service.get_my_apis(user_id)

            # Generate suggestions from user's APIs (in order, no shuffle)
            for api in user_apis[:4]:
                api_questions = self._generate_questions_for_api(
                    api_name=api.name,
                    api_description=api.description,
                    recommended_questions=api.recommended_questions,
                    endpoints=api.endpoints,
                )
                suggestions.extend(api_questions)

            # Get recent conversations for pattern analysis
            conversations = self.conversation_service.get_conversations(user_id)
            conv_suggestions = self._analyze_recent_conversations(conversations)
            suggestions.extend(conv_suggestions)

            # Remove duplicates and limit
            unique_suggestions = []
            seen = set()
            for s in suggestions:
                if s not in seen and len(s) > 5:
                    seen.add(s)
                    unique_suggestions.append(s)

            return unique_suggestions[:max_suggestions]

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            # Return fallback suggestions
            return self._get_fallback_suggestions(max_suggestions)

    def _get_fallback_suggestions(self, count: int = 4) -> List[str]:
        """Get fallback suggestions when no APIs are configured."""
        fallbacks = [
            "暂无可用分析能力，请联系管理员授权API",
            "暂无API权限，请管理员授权后重试",
            "当前无可用数据接口",
            "请联系管理员开通API权限",
        ]
        return fallbacks[:count]


# Global suggestion service instance
_suggestion_service: Optional[SuggestionService] = None


def get_suggestion_service() -> SuggestionService:
    """Get suggestion service instance."""
    global _suggestion_service
    if _suggestion_service is None:
        _suggestion_service = SuggestionService()
    return _suggestion_service
