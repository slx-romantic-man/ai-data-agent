"""
Data analysis prompt templates.
"""

ANALYSIS_PROMPT = """分析以下数据，提供洞察和建议。

## 用户问题
{user_query}

## 数据
{data}

## 分析要求
1. 数据概述：数据的基本情况（行数、列数、时间范围等）
2. 关键指标：重要指标的数值和变化
3. 趋势分析：数据的变化趋势
4. 对比分析：不同维度的对比
5. 异常检测：异常数据点识别
6. 建议结论：基于数据的业务建议

请用专业但易懂的语言进行分析，并用Markdown格式输出。"""

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

def get_analysis_prompt(user_query: str, data: str) -> str:
    """Get general analysis prompt."""
    return ANALYSIS_PROMPT.format(user_query=user_query, data=data)

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