"""
Suggestion Service - Smart question suggestions based on user's APIs and chat history.
"""
from typing import List, Dict, Any, Optional
import random

from app.config.api_config import get_api_registry, APIConfig
from app.services.conversation_service import get_conversation_service
from app.utils.logger import get_logger

logger = get_logger()


class SuggestionService:
    """
    Service for generating smart question suggestions.

    Generates suggestions based on:
    1. User's configured APIs and their endpoints
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

    def _get_api_type(self, api_config: APIConfig) -> str:
        """Determine API type based on name and description."""
        name_lower = api_config.name.lower()
        desc_lower = api_config.description.lower()

        for api_type, keywords in self.API_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower or keyword in desc_lower:
                    return api_type
        return "generic"

    def _fill_template(self, template: str, api_config: APIConfig) -> str:
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
            return template.format(name=api_config.name)
        else:
            return template

    def _generate_questions_for_api(
        self,
        api_id: str,
        api_config: APIConfig
    ) -> List[str]:
        """Generate question suggestions for a specific API.

        Format: "具体问题……（API名称）"
        Priority: pre-configured recommended_questions > template-based fallback
        """
        questions = []
        api_name = api_config.name

        # Priority 1: Use pre-configured recommended questions
        if api_config.recommended_questions:
            for q in api_config.recommended_questions[:3]:
                questions.append(f"{q}（{api_name}）")
            return questions

        # Priority 2: Template-based fallback
        api_type = self._get_api_type(api_config)
        templates = self.API_TEMPLATES.get(api_type, self.API_TEMPLATES["generic"])

        for template in templates[:2]:
            filled = self._fill_template(template, api_config)
            questions.append(f"{filled}（{api_name}）")

        # Priority 3: Endpoint description-based
        for ep_name, endpoint in list(api_config.endpoints.items())[:2]:
            if endpoint.description:
                questions.append(f"{api_config.name}: {endpoint.description}（{api_name}）")

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

    def get_suggestions(
        self,
        user_id: str,
        role: str = "employee",
        max_suggestions: int = 4
    ) -> List[str]:
        """
        Get smart question suggestions for a user.

        Each suggestion is formatted as: "具体问题……（API名称）"

        Args:
            user_id: User ID
            role: User role (admin gets all APIs, others get only permitted ones)
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggested questions
        """
        suggestions = []

        try:
            # Get user's APIs (respecting permissions)
            api_registry = get_api_registry()
            if role == "admin":
                user_apis = api_registry.get_apis_for_user(user_id)
            else:
                user_apis = api_registry.get_permitted_apis_for_user(user_id, role)

            # If user has no API permissions, return empty (no suggestions at all)
            if not user_apis:
                return []

            # Generate suggestions from user's APIs (in order, no shuffle)
            for api_id, api_config in list(user_apis.items())[:4]:
                api_questions = self._generate_questions_for_api(api_id, api_config)
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
            "请配置您的API以获取智能推荐",
            "在API管理中添加您的数据源",
            "配置API后可以查询实时数据",
            "支持天气、股票等多种API类型",
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
