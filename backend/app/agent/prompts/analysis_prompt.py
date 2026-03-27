"""
Data analysis prompt templates.
"""

ANALYSIS_PROMPT = """分析以下数据，提供洞察和建议。

## 用户问题
{user_query}

## 数据
{data}

## 分析要求
你必须严格按照以下结构输出分析报告：

### 1. 事实总结（基于实际数据）
- 数据时间范围
- 关键指标数值（开盘价、收盘价、涨跌幅等）
- 价格变化趋势（上涨/下跌/震荡）
- 成交量变化
- 仅陈述数据中可直接观察到的事实，不做推测

### 2. 可能原因（推测性分析）
⚠️ 以下为基于历史经验的推测，非基于实时新闻或财报数据：
- 可能的市场因素
- 可能的行业因素
- 可能的公司因素
- 明确标注这些是推测，不是确定性结论

### 3. 风险提示
- 股市投资风险警示
- 数据局限性说明（如：仅基于历史价格数据，未包含新闻、财报等）
- 不可预测性声明

### 4. 非个性化建议
- 基于数据的一般性观察
- 明确声明：这不是个性化投资建议
- 建议用户咨询专业投资顾问

## 重要约束
- 如果没有新闻或财报数据，绝对不要伪造具体事件（如"公司发布财报"、"CEO宣布"等）
- 所有推测必须明确标注为推测
- 必须包含风险提示和免责声明
- 输出格式：Markdown"""

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