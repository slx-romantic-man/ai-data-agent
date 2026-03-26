# AI Data Agent v4 架构设计文档

## 一、架构概览

### 1.1 设计理念

AI Data Agent v4 采用 **LangGraph Plan-and-Execute** 架构，从 v3 的 ReAct 循环推理升级为高确定性的状态机模式。核心设计理念：

- **先规划后执行**: Planner 节点生成完整的 JSON 执行计划，Executor 节点按部就班执行
- **数据隔离存储**: 所有 API 查询结果存入 `data_context` 字典，避免 Prompt 污染
- **状态持久化**: 基于 LangGraph Checkpointer 实现会话状态保存，支持多轮下钻
- **人工审批网关**: 利用 LangGraph 的 `interrupt_before` 机制实现流程挂起与恢复

### 1.2 核心升级点

| 维度 | v3 (ReAct) | v4 (LangGraph) |
| --- | --- | --- |
| **推理引擎** | ReAct 循环 (最多10次迭代) | LangGraph 状态机 (Plan-and-Execute) |
| **状态管理** | 无状态 (仅依赖历史消息) | 持久化 AgentState (含结构化数据) |
| **执行流程** | 边想边做，易丢失目标 | 先规划完整计划，再按步骤执行 |
| **数据传递** | 拼接到 Prompt 导致污染 | 隔离存入 data_context 字典 |
| **审批机制** | 工具内部校验 | LangGraph interrupt_before 挂起 |

## 二、核心数据结构

### 2.1 AgentState 定义

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 1. 基础对话状态
    messages: Annotated[list, add_messages]  # 对话历史记录
    query: str                               # 用户当前轮次的原始提问

    # 2. 意图与记忆
    extracted_filters: Dict[str, Any]        # 提取的全局条件

    # 3. 规划与执行追踪
    plan: List[Dict[str, Any]]               # Planner 生成的 JSON 数组执行步骤
    current_step: int                        # 执行器当前执行的步骤索引

    # 4. 数据沙箱 (核心改造点)
    data_context: Dict[str, Any]             # 存放所有 API 调用的 JSON 结果
```

### 2.2 状态持久化机制

- **技术选型**: LangGraph 的 `AsyncSqliteSaver`
- **存储位置**: `backend/data/checkpoints.db`
- **存储机制**: 以 `thread_id` (会话 ID) 为 Key，每次节点流转完毕自动序列化 AgentState
- **业务价值**: 支持多轮深度下钻，第二轮追问时直接从数据库恢复 `data_context`，无需重新查询

## 三、工作流图设计

### 3.1 节点流转图

```
用户查询 → Intent Node → Retrieval Node → Planner Node
                                              ↓
                                         [审批网关]
                                              ↓
                                        Executor Node → Analyzer Node → 返回结果
                                              ↑______________|
                                           (循环执行多步骤)
```

### 3.2 节点详细设计

#### Node 0: Intent Clarification (意图澄清节点)

**职责**: 判断用户查询条件是否完备

**输入**: `state["query"]`

**输出**:
- 条件缺失: 返回反问文本，流转到 END
- 条件完备: 更新 `state["extracted_filters"]`，流转到 Retrieval Node

**实现文件**: `backend/app/agent/nodes/intent_node.py`

#### Node 1: API Retrieval (工具检索节点)

**职责**: 向量召回 + LLM 精排，检索相关 API

**输入**: `state["query"]`

**输出**: Top-10 API Schema (临时变量，不写入 state)

**实现文件**: `backend/app/agent/nodes/retrieval_node.py`

**复用资产**: `backend/app/services/api_retrieval_service.py`

#### Node 2: Planner (全局规划师节点)

**职责**: 生成 JSON 格式的执行计划

**输入**:
- `state["query"]`
- `state["extracted_filters"]`
- Top-10 API Schema

**输出**:
- `state["plan"]`: JSON 数组，每个元素包含 `step`, `tool`, `api_id`, `params`
- `state["current_step"]`: 重置为 0

**实现文件**: `backend/app/agent/nodes/planner_node.py`

**计划格式示例**:
```json
[
  {
    "step": 0,
    "tool": "api_fetch",
    "api_id": "inventory_api",
    "params": {"region": "华东"}
  },
  {
    "step": 1,
    "tool": "api_fetch",
    "api_id": "order_api",
    "params": {"region": "华东", "days": 7}
  }
]
```

#### 审批网关 (Interrupt Before Executor)

**触发条件**:
- 计划中包含 API 调用 (`api_fetch`)
- 用户角色为普通用户 (`role != "admin"`)

**实现方式**:
- 在 `graph.py` 中配置 `interrupt_before=["executor"]`
- Planner 节点包装函数中设置 `state["requires_approval"] = True`

**前端交互**:
1. 后端推送 `approval_required` 事件 (SSE)
2. 前端展示审批卡片，显示执行计划
3. 用户点击"批准"或"拒绝"
4. 调用 `/api/v1/chat/approve` 或 `/api/v1/chat/reject`

#### Node 3: Executor (执行器节点)

**职责**: 按计划逐步执行，调用工具获取数据

**输入**: `state["plan"]`, `state["current_step"]`

**执行逻辑**:
1. 读取 `plan[current_step]`
2. 根据 `tool` 字段路由到对应工具 (`api_fetch`, `sql_query`)
3. 执行查询，获取结果
4. 将结果存入 `state["data_context"]`，key 格式: `step_{idx}_{api_id}`
5. 递增 `state["current_step"]`

**循环条件**: 如果 `current_step < len(plan)`，继续执行下一步

**实现文件**: `backend/app/agent/nodes/executor_node.py`

#### Node 4: Analyzer (终局分析节点)

**职责**: 综合所有数据生成最终分析报告

**输入**: `state["data_context"]` (包含所有 API 查询结果)

**输出**: 将分析报告追加到 `state["messages"]`

**实现文件**: `backend/app/agent/nodes/analyzer_node.py`

**复用资产**: `backend/app/agent/tools/data_analysis_tool.py`

### 3.3 边与路由配置

```python
# 条件边: Intent Node 路由
def should_continue_after_intent(state):
    if state.get("extracted_filters"):
        return "retrieval"
    else:
        return END

# 条件边: Executor Node 循环
def should_continue_execution(state):
    if state["current_step"] < len(state["plan"]):
        return "executor"
    else:
        return "analyzer"

# 图构建
graph = StateGraph(AgentState)
graph.add_node("intent", intent_node)
graph.add_node("retrieval", retrieval_node)
graph.add_node("planner", planner_wrapper)  # 包含审批逻辑
graph.add_node("executor", executor_node)
graph.add_node("analyzer", analyzer_node)

graph.set_entry_point("intent")
graph.add_conditional_edges("intent", should_continue_after_intent)
graph.add_edge("retrieval", "planner")
graph.add_conditional_edges("executor", should_continue_execution)
graph.add_edge("analyzer", END)
```

## 四、人工审批网关

### 4.1 审批触发条件

基于用户角色的条件审批：

- **管理员 (role=admin)**: 直接执行，无需审批
- **普通用户 (role=user)**: 调用 API 时触发审批流程

### 4.2 审批流程

```
Planner 生成计划
    ↓
检查用户角色 & 计划中是否有 API 调用
    ↓
需要审批? → 设置 interrupt_before
    ↓
LangGraph 挂起流程
    ↓
推送 approval_required 事件到前端
    ↓
用户点击批准/拒绝
    ↓
调用 /api/v1/chat/approve 或 /api/v1/chat/reject
    ↓
LangGraph 恢复执行或终止流程
```

### 4.3 API 接口

**批准接口**:
```http
POST /api/v1/chat/approve
Content-Type: application/json

{
  "session_id": "user123_20260326",
  "thread_id": "abc-def-123"
}
```

**拒绝接口**:
```http
POST /api/v1/chat/reject
Content-Type: application/json

{
  "session_id": "user123_20260326",
  "thread_id": "abc-def-123"
}
```

## 五、多轮对话与状态持久化

### 5.1 会话标识

- **session_id**: 用户级别的会话标识，用于前端展示和会话管理
- **thread_id**: LangGraph 内部的线程标识，用于 Checkpointer 存储

### 5.2 多轮下钻场景

**第一轮查询**:
```
用户: "查询华东地区销售数据"
系统: 执行查询，结果存入 data_context["step_0_sales_api"]
      保存 checkpoint 到数据库
```

**第二轮追问** (使用相同 session_id):
```
用户: "为什么上海的销售额下降了"
系统: 从 checkpoint 恢复 data_context
      直接分析第一轮的数据，无需重新查询
```

### 5.3 Checkpointer 配置

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# 初始化 Checkpointer
checkpointer = AsyncSqliteSaver.from_conn_string("backend/data/checkpoints.db")

# 编译图
app = graph.compile(checkpointer=checkpointer)

# 调用时传入 thread_id
config = {"configurable": {"thread_id": thread_id}}
async for event in app.astream(initial_state, config):
    # 处理事件
```

## 六、数据隔离与 Prompt 优化

### 6.1 数据隔离策略

**问题**: v3 中多次 API 调用结果拼接到 Prompt，导致上下文污染和 Token 浪费

**解决方案**:
- 所有 API 查询结果存入 `state["data_context"]` 字典
- Executor 节点只负责执行和存储，不生成分析文本
- Analyzer 节点统一从 `data_context` 提取数据进行分析

### 6.2 data_context 结构

```python
{
  "step_0_inventory_api": {
    "data": [...],
    "metadata": {"api_id": "inventory_api", "params": {...}}
  },
  "step_1_order_api": {
    "data": [...],
    "metadata": {"api_id": "order_api", "params": {...}}
  }
}
```

## 七、保留资产 (不可修改)

本次升级严格保留以下已验证的底层资产：

1. **统一工具入口**: 4 个核心工具 (`sql_query`, `api_fetch`, `data_analysis`, `export_excel`)
2. **两阶段检索机制**: `api_retrieval_service.py` (向量召回 + LLM 精排)
3. **数据权限体系**: RBAC、行级过滤、列级脱敏机制

## 八、部署与运维

### 8.1 环境要求

- Python 3.12+
- SQLite 3.35+
- LangGraph 0.2+

### 8.2 启动方式

```bash
# 一键启动
bash init.sh

# 手动启动
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 8.3 健康检查

```bash
# 检查服务状态
curl http://localhost:8002/health

# 检查 Checkpointer 数据库
sqlite3 backend/data/checkpoints.db "SELECT COUNT(*) FROM checkpoints;"
```

## 九、测试策略

### 9.1 单元测试

- 每个节点独立测试 (intent_node, planner_node, executor_node, analyzer_node)
- 工具函数测试 (api_fetch, sql_query, data_analysis)

### 9.2 集成测试

- 简单查询场景 (F-11)
- 复杂归因分析场景 (F-12)
- 多轮下钻场景 (F-13)
- 人工审批网关场景 (F-14)

### 9.3 端到端测试

使用 `test_*.py` 脚本模拟真实用户交互，验证完整流程。

## 十、未来扩展

### 10.1 Python 代码执行能力

- 实现 `python_exec_tool.py` 支持数学运算
- 更新 Planner 支持 `python_exec` 工具类型
- 更新 Executor 路由支持 Python 代码执行

### 10.2 更多数据源

- 支持 MySQL、PostgreSQL 等关系型数据库
- 支持 Elasticsearch、MongoDB 等 NoSQL 数据库
- 支持文件系统 (CSV, Excel, JSON)

### 10.3 更多分析能力

- 支持图表生成 (ECharts, Plotly)
- 支持预测分析 (时间序列预测)
- 支持异常检测 (离群点检测)
