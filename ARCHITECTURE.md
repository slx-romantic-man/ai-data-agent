# AI Data Agent v4 - 架构设计文档

## 目录结构

```
backend/app/
├── agent/                      # 核心 Agent 逻辑
│   ├── nodes/                  # LangGraph 节点实现
│   │   ├── intent_node.py      # 意图澄清：判断查询条件是否完备
│   │   ├── retrieval_node.py   # API 检索：向量召回 + LLM 精排
│   │   ├── planner_node.py     # 全局规划：生成 JSON 格式执行计划
│   │   ├── executor_node.py    # 执行器：路由到具体工具执行
│   │   └── analyzer_node.py    # 终局分析：综合所有数据生成洞察
│   ├── tools/                  # 工具实现
│   │   ├── sql_query_tool.py   # SQL 查询工具
│   │   ├── api_fetch_tool.py   # API 调用工具
│   │   ├── analysis_tool.py    # 数据分析工具
│   │   ├── export_tool.py      # Excel 导出工具
│   │   └── python_exec_tool.py # Python 代码执行工具
│   ├── prompts/                # Prompt 模板
│   │   ├── intent_prompt.py    # 意图澄清 Prompt
│   │   ├── planner_prompt.py   # 规划师 Prompt
│   │   └── analysis_prompt.py  # 分析师 Prompt
│   ├── state.py                # AgentState 数据结构定义
│   └── graph.py                # LangGraph 工作流图定义
├── api/v1/                     # REST API 端点
│   ├── chat.py                 # 对话接口
│   ├── approval.py             # 审批接口
│   ├── auth.py                 # 认证接口
│   └── export.py               # 导出接口
├── access/                     # 数据访问层
│   ├── database/               # 数据库客户端
│   ├── permission/             # 权限控制
│   └── metadata/               # 元数据管理
├── services/                   # 业务逻辑服务
│   ├── api_retrieval_service.py  # API 检索服务
│   ├── conversation_service.py   # 会话管理服务
│   └── vector_store.py           # 向量存储服务
├── config/                     # 配置管理
│   ├── settings.py             # 全局配置
│   ├── llm_config.py           # LLM 配置
│   └── api_config.py           # API 配置
└── main.py                     # FastAPI 应用入口
```

## 核心组件职责

### 1. AgentState (状态管理)

**文件**: `backend/app/agent/state.py`

```python
class AgentState(TypedDict):
    messages: List[BaseMessage]        # 对话历史
    query: str                         # 用户查询
    extracted_filters: Optional[Dict]  # 提取的查询条件
    plan: Optional[List[Dict]]         # 执行计划
    current_step: int                  # 当前执行步骤
    data_context: Dict[str, Any]       # 数据隔离存储
```

**设计理念**:
- `data_context` 采用字典结构，key 为 `step_{idx}_{tool_name}`，避免 Prompt 污染
- 所有节点通过读写 `AgentState` 实现状态传递
- 状态持久化到 SQLite，支持多轮对话恢复

### 2. LangGraph 工作流

**文件**: `backend/app/agent/graph.py`

**节点流转**:
```
START
  ↓
Intent Clarification (意图澄清)
  ↓ [条件完备]
API Retrieval (API 检索)
  ↓
Planner (全局规划)
  ↓
[人工审批网关] ← interrupt_before=['Executor']
  ↓
Executor (执行器) ← 循环边：current_step < len(plan)
  ↓ [所有步骤完成]
Analyzer (终局分析)
  ↓
END
```

**关键设计**:
- **条件边**: Intent 节点根据 `extracted_filters` 是否为空决定路由
- **循环边**: Executor 节点根据 `current_step` 判断是否继续执行
- **中断点**: `interrupt_before=['Executor']` 实现人工审批网关

### 3. 节点实现详解

#### Intent Clarification Node
**职责**: 判断用户查询条件是否完备，缺失则反问

**输入**: `state['query']`
**输出**: `state['extracted_filters']` (Dict 或 None)

**示例**:
- 输入: "查询销售数据"
- 输出: `None` (缺少时间范围) → 反问 "请问您需要查询哪个时间段的销售数据？"

#### API Retrieval Node
**职责**: 从 API 库中检索最相关的 Top-10 API Schema

**流程**:
1. 向量召回：使用 Embedding 检索相似 API
2. LLM 精排：根据查询意图重新排序
3. 传递给 Planner：通过临时变量传递，不污染 `AgentState`

#### Planner Node
**职责**: 生成结构化的执行计划

**输入**: `state['query']` + Top-10 API Schema
**输出**: `state['plan']` (List[Dict])

**计划格式**:
```json
[
  {
    "step": 1,
    "tool": "api_fetch",
    "api_id": "orders_api",
    "params": {"start_date": "2024-03-01", "end_date": "2024-03-07"}
  },
  {
    "step": 2,
    "tool": "python_exec",
    "code": "result = sum(data['amount'])",
    "data_refs": ["step_1_orders_api"]
  }
]
```

#### Executor Node
**职责**: 无脑执行计划中的每一步

**路由逻辑**:
```python
if tool_name == "api_fetch":
    result = api_fetch_tool.execute(params)
elif tool_name == "sql_query":
    result = sql_query_tool.execute(sql)
elif tool_name == "python_exec":
    result = python_exec_tool.execute(code, data_context)
```

**数据存储**:
- 结果存入 `state['data_context'][f"step_{idx}_{tool_name}"]`
- 递增 `state['current_step']`

#### Analyzer Node
**职责**: 综合所有数据生成最终分析报告

**输入**: `state['data_context']` (所有步骤的数据)
**输出**: 追加到 `state['messages']`

### 4. 工具系统

#### SQL Query Tool
- 支持 MySQL 和 PostgreSQL
- 自动应用行级过滤和列级脱敏
- 查询结果转为 Pandas DataFrame

#### API Fetch Tool
- 支持 GET/POST 请求
- 自动注入认证 Token
- 参数映射与验证

#### Python Exec Tool
- 隔离环境执行代码（RestrictedPython）
- 自动注入 `data_context` 中的数据为变量
- 支持 Pandas、NumPy 等数据处理库

#### Export Tool
- 将 DataFrame 导出为 Excel
- 支持多 Sheet 和样式定制

### 5. 人工审批网关

**实现机制**:
```python
# graph.py
def planner_wrapper(state: AgentState):
    # 执行 Planner 节点
    state = planner_node(state)

    # 检查是否需要审批
    permission = get_user_permission(state['user_id'])
    has_api_calls = any(step['tool'] == 'api_fetch' for step in state['plan'])
    is_admin = permission.role == 'admin'

    requires_approval = has_api_calls and not is_admin
    state['requires_approval'] = requires_approval

    return state

# 配置中断点
graph.add_node("Planner", planner_wrapper)
graph.add_edge("Planner", "Executor", interrupt_before=True)
```

**审批流程**:
1. Planner 执行完毕后，检测到 `requires_approval=True`
2. LangGraph 在 Executor 前挂起，返回 `approval_required` 事件
3. 前端展示审批卡片，用户点击"批准"或"拒绝"
4. 调用 `/api/v1/chat/approve` 或 `/api/v1/chat/reject`
5. 系统恢复执行或终止流程

### 6. 状态持久化

**实现**: `langgraph-checkpoint-sqlite`

**存储位置**: `backend/data/checkpoints.db`

**关键代码**:
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncSqliteSaver.from_conn_string("backend/data/checkpoints.db")
graph = graph.compile(checkpointer=checkpointer)
```

**优势**:
- 多轮对话无需重复查询
- 支持会话恢复和回溯
- `data_context` 持久化，避免数据丢失

## 数据流向

```
用户输入 "查询最近7天订单统计"
    ↓
Intent Node: 提取 {start_date: "2024-03-19", end_date: "2024-03-26"}
    ↓
Retrieval Node: 召回 orders_api (Top-1)
    ↓
Planner Node: 生成计划
    [
      {step: 1, tool: "api_fetch", api_id: "orders_api", params: {...}},
      {step: 2, tool: "python_exec", code: "sum(data['amount'])", data_refs: ["step_1_orders_api"]}
    ]
    ↓
[审批网关] ← 普通用户需审批
    ↓
Executor Node (Step 1):
    - 调用 api_fetch_tool
    - 存储结果到 data_context["step_1_orders_api"]
    ↓
Executor Node (Step 2):
    - 调用 python_exec_tool
    - 注入 data_context["step_1_orders_api"] 为变量 data
    - 执行代码 sum(data['amount'])
    - 存储结果到 data_context["step_2_python_exec"]
    ↓
Analyzer Node:
    - 读取 data_context 所有数据
    - 生成分析报告: "最近7天订单总额为 ¥123,456"
    ↓
返回给用户
```

## 设计模式

### 1. 状态机模式
- LangGraph 实现确定性状态流转
- 每个节点职责单一，易于测试和维护

### 2. 策略模式
- Executor 根据 `tool` 字段动态路由到不同工具
- 新增工具只需添加路由分支

### 3. 责任链模式
- Intent → Retrieval → Planner → Executor → Analyzer
- 每个节点处理完毕后传递给下一个节点

### 4. 观察者模式
- SSE 流式输出实时推送节点状态
- 前端订阅事件流展示推理过程

## 关键技术决策

### 为什么选择 LangGraph？
- **确定性**: Plan-and-Execute 模式避免 ReAct 的随机性
- **可控性**: 显式定义节点和边，易于调试
- **持久化**: 内置 Checkpointer 支持状态保存
- **中断机制**: `interrupt_before` 实现人工审批网关

### 为什么使用 data_context？
- **避免 Prompt 污染**: 大量数据拼接到 Prompt 会导致 Token 浪费和上下文混乱
- **数据隔离**: 每个步骤的数据独立存储，便于追溯和调试
- **持久化友好**: 字典结构易于序列化到 SQLite

### 为什么需要 Python Exec Tool？
- **数学运算**: LLM 在复杂计算上不可靠，需要代码执行保证精度
- **数据处理**: Pandas 操作比 LLM 生成 SQL 更灵活
- **可扩展性**: 支持自定义数据处理逻辑

## 性能优化

1. **向量检索缓存**: API Schema Embedding 预计算并缓存
2. **数据库连接池**: 使用 SQLAlchemy 异步连接池
3. **流式输出**: SSE 避免长时间等待，提升用户体验
4. **懒加载**: 仅在需要时加载大型数据集

## 安全考虑

1. **SQL 注入防护**: 使用参数化查询
2. **代码沙箱**: Python Exec Tool 使用 RestrictedPython 限制危险操作
3. **权限校验**: 每个工具执行前检查用户权限
4. **审计日志**: 所有 API 调用记录到日志

## 未来扩展方向

1. **多模态支持**: 支持图表生成和图像分析
2. **分布式执行**: Executor 支持并行执行多个步骤
3. **自适应规划**: Planner 根据执行结果动态调整计划
4. **知识图谱**: 引入企业知识图谱增强 API 检索精度
