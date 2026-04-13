"""
Data analysis prompt templates.
"""

UNIVERSAL_ANALYSIS_PROMPT = """分析以下数据，提供洞察和建议。

## 用户问题
{user_query}

## 数据
{data}

## 分析要求
你必须严格按照以下结构输出分析报告，内容需自然适配数据类型（如股票、天气、IP定位等）：

### 1. 数据概览
- 数据来源和时间范围（如适用）
- 数据规模和完整性
- 数据类型说明（时间序列、地理数据、气象数据、财务数据等）

### 2. 核心指标
- 提取数据中的关键数值指标（如：价格、温度、坐标等）
- 主要数值的范围和分布
- 重要统计特征（平均值、最大值、最小值等）

### 3. 主要发现
- 数据中最显著的特征和模式
- 重要变化或趋势（如适用）
- 关键数据点及其意义
- 仅陈述数据中可直接观察到的事实，不做推测

### 4. 模式识别
- 数据中的规律性特征（周期性、趋势性、聚集性等）
- 异常值或离群点（如有）
- 数据分布特点

### 5. 可能解释
⚠️ 以下为基于数据特征的推测，非基于外部信息源：
- 可能的影响因素
- 可能的形成原因
- 明确标注这些是推测，不是确定性结论

### 6. 应用建议
- 基于数据的一般性观察和建议
- 可能的应用场景
- 明确声明：这不是个性化决策建议

### 7. 局限性说明
- 数据时效性和完整性限制
- 分析方法的局限性
- 结论的适用范围和不确定性
- 建议用户结合更多信息源进行决策

## 重要约束
- 不要伪造数据中不存在的信息
- 不要使用数据类型不匹配的专业术语（如对天气数据使用金融术语）
- 所有推测必须明确标注为推测
- 必须包含局限性说明和免责声明
- 输出格式：Markdown
- 语言风格：自然、准确、易于理解"""

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