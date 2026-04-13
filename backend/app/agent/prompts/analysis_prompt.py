"""
Data analysis prompt templates.
"""

UNIVERSAL_ANALYSIS_PROMPT = """用3句话分析数据核心，300字以内完成。

## 问题
{user_query}

## 数据
{data}

## 输出（仅3节，每节1-2句，总字数≤300）

### 核心数据
数据范围、类型、关键数值（均值/极值）。

### 主要发现
1-2个最显著趋势或异常，推测原因须标注"推测"。

### 注意事项
一句说明数据局限。

## 约束
- 不伪造不存在的信息
- 不说废话，不列冗长列表
- 输出：Markdown，简洁直白"""

TREND_ANALYSIS_PROMPT = """分析以下时序数据的趋势。

## 数据
{data}

## 时间字段
{time_field}

## 数值字段
{value_fields}

请分析：
1. 整体趋势（上升/下降/平稳）
2. 趋势变化点
3. 周期性规律
4. 预测未来走势

输出格式：Markdown"""

COMPARISON_ANALYSIS_PROMPT = """对比分析以下数据。

## 数据
{data}

## 对比维度
{dimensions}

## 对比指标
{metrics}

请分析：
1. 各维度的差异
2. 差异的原因推测
3. 最佳和最差表现
4. 改进建议

输出格式：Markdown"""

SIMPLE_ANALYSIS_PROMPT = """分析以下数据，用一段话总结核心结果。

## 用户问题
{user_query}

## 数据
{data}

## 要求
- 只用一段话（3-5 句）总结核心数据
- 包含关键数值和结论
- 语言自然、简洁，不要分章节
- 输出格式：纯文本或简单 Markdown
- 不要包含局限性说明、免责声明或推测
"""


ANOMALY_ANALYSIS_PROMPT = """检测以下数据中的异常点。

## 数据
{data}

## 检测字段
{fields}

请分析：
1. 异常点识别（使用统计方法）
2. 异常原因推测
3. 异常影响评估
4. 处理建议

输出格式：Markdown"""

def get_simple_analysis_prompt(user_query: str, data: str) -> str:
    """Get simple analysis prompt for small datasets (≤5 rows)."""
    return SIMPLE_ANALYSIS_PROMPT.format(user_query=user_query, data=data)


def get_analysis_prompt(user_query: str, data: str) -> str:
    """Get general analysis prompt using universal template."""
    return UNIVERSAL_ANALYSIS_PROMPT.format(user_query=user_query, data=data)

def get_trend_analysis_prompt(data: str, time_field: str, value_fields: list) -> str:
    """Get trend analysis prompt."""
    return TREND_ANALYSIS_PROMPT.format(
        data=data,
        time_field=time_field,
        value_fields=", ".join(value_fields),
    )

def get_comparison_analysis_prompt(data: str, dimensions: list, metrics: list) -> str:
    """Get comparison analysis prompt."""
    return COMPARISON_ANALYSIS_PROMPT.format(
        data=data,
        dimensions=", ".join(dimensions),
        metrics=", ".join(metrics),
    )

def get_anomaly_analysis_prompt(data: str, fields: list) -> str:
    """Get anomaly analysis prompt."""
    return ANOMALY_ANALYSIS_PROMPT.format(
        data=data,
        fields=", ".join(fields),
    )