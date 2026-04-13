"""
Data Analyzer module.
Performs analysis on query results.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal

from app.config.llm_config import BaseLLMClient, get_llm
from app.agent.prompts.analysis_prompt import (
    get_analysis_prompt,
    get_simple_analysis_prompt,
    get_trend_analysis_prompt,
    get_comparison_analysis_prompt,
    get_anomaly_analysis_prompt,
)


class _DateEncoder(json.JSONEncoder):
    """JSON encoder that handles date, datetime, and Decimal types."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class DataAnalyzer:
    """
    Analyzes data and generates insights.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self._llm = llm_client

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def analyze(
        self,
        data: List[Dict[str, Any]],
        user_query: str,
        analysis_type: str = "summary",
        dimensions: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        query_complexity: str = "normal",
    ) -> Dict[str, Any]:
        """
        Analyze data and generate insights.

        Args:
            data: Data rows to analyze
            user_query: Original user query
            analysis_type: Type of analysis (summary, trend, comparison, anomaly)
            dimensions: Dimensions for analysis
            metrics: Metrics to analyze
            query_complexity: Complexity level (simple/normal/complex)

        Returns:
            Dict with analysis results and insights
        """
        if not data:
            return {
                "analysis": "无数据可供分析",
                "insights": [],
            }

        # Format data for LLM
        data_str = self._format_data_for_llm(data)

        # Select analysis prompt based on type
        if analysis_type == "trend":
            prompt = get_trend_analysis_prompt(
                data=data_str,
                time_field=dimensions[0] if dimensions else "date",
                value_fields=metrics or [],
            )
        elif analysis_type == "comparison":
            prompt = get_comparison_analysis_prompt(
                data=data_str,
                dimensions=dimensions or [],
                metrics=metrics or [],
            )
        elif analysis_type == "anomaly":
            prompt = get_anomaly_analysis_prompt(
                data=data_str,
                fields=metrics or [],
            )
        else:
            if query_complexity == "simple":
                prompt = get_simple_analysis_prompt(user_query=user_query, data=data_str)
            else:
                prompt = get_analysis_prompt(user_query=user_query, data=data_str)

        # Get LLM analysis
        response = await self.llm.chat([
            {"role": "system", "content": "你是一个专业的数据分析师，擅长从数据中发现洞察和趋势。"},
            {"role": "user", "content": prompt}
        ], max_tokens=512)

        return {
            "analysis": response,
            "analysis_type": analysis_type,
            "data_summary": self._generate_summary(data),
            "insights": self._extract_insights(response),
        }

    def _format_data_for_llm(self, data: List[Dict[str, Any]], max_rows: int = 20) -> str:
        """Format data for LLM input. Uses smart sampling to preserve trends while minimizing tokens."""
        if not data:
            return "无数据"

        # Smart sampling: pick head, middle, and tail to preserve trend info
        if len(data) <= max_rows:
            sample_data = data
        else:
            n = max_rows
            head = data[:n//3]
            tail = data[-(n - len(head)):]
            sample_data = head + tail

        return json.dumps(sample_data, ensure_ascii=False, indent=2, cls=_DateEncoder)

    def _generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for data."""
        if not data:
            return {"row_count": 0}

        summary = {
            "row_count": len(data),
            "columns": list(data[0].keys()) if data else [],
        }

        # Calculate numeric column statistics
        for key, value in data[0].items():
            if isinstance(value, (int, float)):
                values = [row.get(key) for row in data if row.get(key) is not None]
                if values:
                    summary[f"{key}_sum"] = sum(values)
                    summary[f"{key}_avg"] = sum(values) / len(values)
                    summary[f"{key}_min"] = min(values)
                    summary[f"{key}_max"] = max(values)

        return summary

    def _extract_insights(self, analysis_text: str) -> List[str]:
        """Extract key insights from analysis text."""
        insights = []

        # Simple extraction based on patterns
        patterns = [
            r'关键发现[：:](.*?)(?=\n\n|\n\d|$)',
            r'建议[：:](.*?)(?=\n\n|\n\d|$)',
            r'结论[：:](.*?)(?=\n\n|\n\d|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, analysis_text, re.DOTALL)
            for match in matches:
                insight = match.strip()
                if insight and len(insight) > 10:
                    insights.append(insight)

        return insights[:5]  # Limit to 5 insights

    async def detect_anomalies(
        self,
        data: List[Dict[str, Any]],
        field: str,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in data using statistical methods.

        Args:
            data: Data rows
            field: Field to check for anomalies
            threshold: Z-score threshold for anomaly detection

        Returns:
            List of anomalous data points
        """
        if not data or field not in data[0]:
            return []

        values = [row.get(field) for row in data if row.get(field) is not None]
        if not values:
            return []

        import statistics

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0

        if std == 0:
            return []

        anomalies = []
        for row in data:
            value = row.get(field)
            if value is not None:
                z_score = abs(value - mean) / std
                if z_score > threshold:
                    row_copy = row.copy()
                    row_copy["_anomaly_score"] = z_score
                    anomalies.append(row_copy)

        return anomalies

    async def calculate_trend(
        self,
        data: List[Dict[str, Any]],
        time_field: str,
        value_field: str,
    ) -> Dict[str, Any]:
        """
        Calculate trend for time series data.

        Args:
            data: Data rows
            time_field: Time field name
            value_field: Value field name

        Returns:
            Dict with trend information
        """
        if not data or len(data) < 2:
            return {"trend": "insufficient_data"}

        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.get(time_field, ""))

        values = [row.get(value_field) for row in sorted_data if row.get(value_field) is not None]
        if len(values) < 2:
            return {"trend": "insufficient_data"}

        # Calculate simple trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        if first_avg == 0:
            change_rate = 1.0 if second_avg > 0 else 0.0
        else:
            change_rate = (second_avg - first_avg) / first_avg

        if change_rate > 0.1:
            trend = "increasing"
        elif change_rate < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_rate": change_rate,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg,
        }


# Import re module at the top
import re