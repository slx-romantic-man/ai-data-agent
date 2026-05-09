"""
SQL generation prompt templates.
"""

SQL_PROMPT = """根据用户问题生成安全的SQL查询语句。

## 数据库表结构
{table_schema}

## 用户问题
{user_query}

## 意图分析结果
{intent_result}

## 权限过滤条件
{permission_filters}

## SQL生成规则
1. 只允许SELECT查询，禁止INSERT/UPDATE/DELETE/DROP等操作
2. 使用标准SQL语法，兼容MySQL和PostgreSQL
3. 添加适当的WHERE条件进行数据过滤
4. 对于统计查询，使用GROUP BY和聚合函数
5. 添加ORDER BY进行排序（时间倒序）
6. 添加LIMIT限制返回行数（默认1000行）
7. 字段名使用下划线命名法（snake_case）

## 权限过滤
请自动将以下过滤条件添加到WHERE子句中：
{permission_filters}

## 输出格式
请只返回SQL语句，不要包含其他内容。SQL语句以分号结尾。

示例：
SELECT date, SUM(order_count) as total_orders
FROM orders
WHERE city = '北京' AND date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC
LIMIT 1000;
"""

SQL_VALIDATION_PROMPT = """验证以下SQL查询是否安全：

{sql}

检查项目：
1. 是否只包含SELECT操作
2. 是否有SQL注入风险
3. 是否使用了安全的SQL语法
4. 是否需要添加权限过滤条件

请返回验证结果（JSON格式）：
{{
    "is_safe": true/false,
    "issues": ["问题列表"],
    "suggestions": ["建议列表"]
}}"""

SQL_FIX_PROMPT = """修复以下SQL查询的问题：

原始SQL：
{sql}

问题：
{issues}

请返回修复后的SQL语句："""

def get_sql_prompt(
    table_schema: str,
    user_query: str,
    intent_result: dict,
    permission_filters: dict,
) -> str:
    """Get SQL generation prompt."""
    import json
    return SQL_PROMPT.format(
        table_schema=table_schema,
        user_query=user_query,
        intent_result=json.dumps(intent_result, ensure_ascii=False, indent=2),
        permission_filters=json.dumps(permission_filters, ensure_ascii=False, indent=2),
    )

def get_sql_validation_prompt(sql: str) -> str:
    """Get SQL validation prompt."""
    return SQL_VALIDATION_PROMPT.format(sql=sql)

def get_sql_fix_prompt(sql: str, issues: list) -> str:
    """Get SQL fix prompt."""
    return SQL_FIX_PROMPT.format(sql=sql, issues="\n".join(issues))