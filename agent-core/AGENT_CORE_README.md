# AI Data Agent — Agent 核心链路说明书

> 本文档说明 `agent-core/` 文件夹中所有文件的职责、调用关系和阅读顺序。  
> 该文件夹从主项目中单独拎出，方便开发者快速理解 Agent 的核心链路，无需在完整代码库中翻找。

---

## 📐 目录结构

```
agent-core/
├── app/
│   ├── agent/
│   │   ├── graph.py                    ← 工作流编排总入口
│   │   ├── state.py                    ← 状态数据结构
│   │   │
│   │   ├── nodes/                      ← LangGraph 节点（6大节点）
│   │   │   ├── intent_node.py          ← 意图澄清节点
│   │   │   ├── intent_planner_node.py  ← 意图+规划合并节点
│   │   │   ├── planner_node.py         ← 全局规划节点
│   │   │   ├── retrieval_node.py       ← API 检索节点
│   │   │   ├── executor_node.py        ← 执行器节点
│   │   │   └── analyzer_node.py        ← 终局分析节点
│   │   │
│   │   ├── core/                       ← 核心引擎（底层能力）
│   │   │   ├── agent_engine.py         ← Agent 引擎总控
│   │   │   ├── streaming_agent.py      ← 流式 Agent 引擎
│   │   │   ├── intent_recognizer.py    ← 意图识别器
│   │   │   ├── query_planner.py        ← 查询规划器
│   │   │   ├── sql_generator.py        ← SQL 生成器
│   │   │   ├── data_analyzer.py        ← 数据分析器
│   │   │   ├── permission_inferencer.py← 权限推断器（已废弃）
│   │   │   └── circuit_breaker.py      ← 熔断保护器
│   │   │
│   │   ├── tools/                      ← 工具层（6大工具）
│   │   │   ├── base_tool.py            ← 工具抽象基类
│   │   │   ├── sql_query_tool.py       ← SQL 查询工具
│   │   │   ├── api_fetch_tool.py       ← API 调用工具
│   │   │   ├── python_exec_tool.py     ← Python 执行工具
│   │   │   ├── analysis_tool.py        ← 数据分析工具
│   │   │   └── export_tool.py          ← Excel 导出工具
│   │   │
│   │   ├── router/                     ← 路由层
│   │   │   ├── api_router.py           ← API Schema 路由
│   │   │   └── tool_router.py          ← 工具分发路由
│   │   │
│   │   └── prompts/                    ← Prompt 模板层
│   │       ├── intent_prompt.py        ← 意图澄清 Prompt
│   │       ├── planner_prompt.py       ← 规划 Prompt
│   │       ├── intent_planner_prompt.py← 合并 Prompt
│   │       ├── analysis_prompt.py      ← 分析 Prompt
│   │       ├── react_prompt.py         ← ReAct Prompt
│   │       ├── sql_prompt.py           ← SQL 生成 Prompt
│   │       └── system_prompt.py        ← 系统 Prompt
│   │
│   └── api/v1/
│       └── chat.py                     ← 外部调用入口（FastAPI）
│
└── AGENT_CORE_README.md                ← 本说明书
```

---

## 🧭 阅读顺序推荐

### 路径一：按数据流（推荐，理解"请求怎么被处理"）

```
chat.py → graph.py → state.py
    → nodes/intent_node.py / intent_planner_node.py
    → nodes/retrieval_node.py
    → nodes/planner_node.py
    → nodes/executor_node.py
    → nodes/analyzer_node.py
```

### 路径二：按架构层（理解"系统怎么分层"）

```
L1 编排层: graph.py + state.py
L2 节点层: nodes/*.py
L3 引擎层: core/*.py
L4 工具层: tools/*.py
L5 路由层: router/*.py
L6 Prompt层: prompts/*.py
```

---

## 🔗 核心链路流程

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  chat.py                                                            │
│  FastAPI 对话接口，接收 ChatRequest，校验用户身份和权限，            │
│  调用 StreamingAgent 生成流式响应。                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  streaming_agent.py (core/streaming_agent.py)                       │
│  流式 Agent 引擎，将用户请求包装为 AgentState，调用 graph 执行，      │
│  并通过 AsyncGenerator 实时产出 SSE 事件。                           │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  graph.py                                                           │
│  LangGraph 工作流图定义。组装所有节点、配置条件边和循环边，            │
│  绑定 SQLite Checkpointer 实现状态持久化。                           │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  state.py                                                           │
│  AgentState TypedDict 定义，贯穿整个工作流的状态容器：                │
│  messages / query / extracted_filters / plan / current_step /        │
│  data_context / retrieved_apis / requires_approval 等。              │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  intent_node │───▶│ retrieval_   │───▶│  planner_    │───▶│  executor_   │───▶│  analyzer_   │
│  (或合并节点) │    │    node      │    │    node      │    │    node      │    │    node      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
  意图识别+条件完备    向量召回+LLM精排      生成JSON执行计划    按步骤调用工具       综合数据生成洞察
  缺失则反问用户       Top-10 API Schema    含工具/参数/依赖    SQL/API/Python      追加到消息历史
```

---

## 📄 文件详解

### 第一层：编排层（Orchestration）

| 文件 | 职责 | 核心函数/类 |
|------|------|------------|
| `graph.py` | **工作流编排总入口**。使用 LangGraph 的 `StateGraph` 定义节点和有向边，组装完整的 Plan-and-Execute 工作流。配置 SQLite Checkpointer 实现状态持久化，支持多轮对话恢复。 | `create_agent_graph()` |
| `state.py` | **状态数据结构**。定义 `AgentState` TypedDict，是所有节点间传递的状态容器。关键设计：`data_context` 采用字典隔离存储各步骤结果，避免大量数据污染 Prompt。 | `AgentState` |
| `chat.py` | **外部调用入口**。FastAPI 路由文件，提供 `/api/v1/chat` 和 `/api/v1/chat/stream` 等端点。负责接收 HTTP 请求、校验 JWT、构建用户上下文、调用 StreamingAgent、返回 SSE 流式响应。 | `chat()`, `chat_stream()` |

### 第二层：节点层（Nodes）

| 文件 | 职责 | 核心函数 |
|------|------|---------|
| `intent_node.py` | **意图澄清节点**。判断用户查询条件是否完备，若缺失则返回反问；若完备则提取结构化过滤条件（如时间范围、筛选字段）。 | `intent_node()` |
| `intent_planner_node.py` | **合并意图+规划节点**。将意图识别和全局规划合并为单次 LLM 调用，减少 LLM 请求次数，提升响应速度。 | `intent_planner_node()` |
| `planner_node.py` | **全局规划节点**。根据用户查询和检索到的 API Schema，生成结构化 JSON 执行计划（每一步包含 tool、params、data_refs）。 | `planner_node()` |
| `retrieval_node.py` | **API 检索节点**。两阶段检索：① 使用 Embedding 从 Qdrant 向量库召回候选 API；② 使用 LLM 根据查询意图精排，输出 Top-10 API Schema。同时检索数据库表元数据。 | `retrieval_node()` |
| `executor_node.py` | **执行器节点**。无脑遍历 `plan`，根据 `tool` 字段路由到对应工具（SQL/API/Python），执行结果存入 `data_context`。支持步骤间数据引用（`data_refs`）。 | `executor_node()`, `execute_single_step()` |
| `analyzer_node.py` | **终局分析节点**。读取 `data_context` 中所有累积数据，调用 DataAnalyzer 生成最终洞察报告，追加到 `messages`。支持简单查询的短路返回。 | `analyzer_node()` |

### 第三层：核心引擎层（Core Engine）

| 文件 | 职责 | 核心类/函数 |
|------|------|------------|
| `agent_engine.py` | **Agent 引擎总控**。协调意图识别、查询规划、权限推断和工具执行的完整流程。是早期非 LangGraph 版本的核心，现被 `graph.py` 替代但仍保留部分逻辑。 | `AgentEngine` |
| `streaming_agent.py` | **流式 Agent 引擎**。处理 SSE 流式输出的核心引擎。将用户请求转为 AgentState，驱动 graph 执行，并通过 `AsyncGenerator` 实时产出 reasoning log、tool result、final answer 等事件。 | `StreamingAgent`, `get_streaming_agent()` |
| `intent_recognizer.py` | **意图识别器**。分析用户查询，确定意图类型（查询/分析/导出），提取时间范围、实体、筛选条件等。 | `IntentRecognizer` |
| `query_planner.py` | **查询规划器**。将意图结果转为可执行步骤列表（`ToolStep`）。支持单步查询和多步复杂计划。 | `QueryPlanner` |
| `sql_generator.py` | **SQL 生成器**。将自然语言需求转为安全 SQL 查询。内置表结构感知，支持 JOIN、聚合、子查询。 | `SQLGenerator` |
| `data_analyzer.py` | **数据分析器**。对查询结果进行深度分析，生成趋势洞察、对比结论、异常检测等。支持流式输出分析过程。 | `DataAnalyzer` |
| `permission_inferencer.py` | **权限推断器**（⚠️ 已废弃）。权限推断已迁移至 API 层 (`app/api/dependencies.py`)。保留仅作向后兼容。 | — |
| `circuit_breaker.py` | **熔断保护器**。ReAct 循环的保险丝。连续失败达到阈值后自动熔断，防止级联故障。支持超时恢复。 | `CircuitBreaker`, `CircuitState` |

### 第四层：工具层（Tools）

| 文件 | 职责 | 核心类 |
|------|------|--------|
| `base_tool.py` | **工具抽象基类**。定义所有工具的接口契约：`name`、`description`、`execute()`、`validate()`。新增工具必须继承此类。 | `BaseTool` |
| `sql_query_tool.py` | **SQL 查询工具**。执行 SQL 查询，自动应用行级过滤（`WHERE` 条件）和列级脱敏（字段掩码）。支持 MySQL。返回 Pandas DataFrame。 | `SQLQueryTool` |
| `api_fetch_tool.py` | **API 调用工具**。支持通用 URL 调用和配置化 API 调用。自动注入认证 Token（Bearer/APIKey/Basic），处理参数映射与响应解析。 | `APIFetchTool` |
| `python_exec_tool.py` | **Python 执行工具**。在受限环境中执行 Python 代码（基于 RestrictedPython 沙箱）。自动注入 `data_context` 数据为变量，支持 Pandas/NumPy。 | `PythonExecTool` |
| `analysis_tool.py` | **数据分析工具**。对已有数据进行深度分析，调用 DataAnalyzer 生成洞察。通常作为 plan 的最后一步使用。 | `AnalysisTool` |
| `export_tool.py` | **Excel 导出工具**。将 DataFrame 导出为 Excel 文件（多 Sheet 支持），返回文件下载路径。 | `ExportTool` |

### 第五层：路由层（Router）

| 文件 | 职责 | 核心类 |
|------|------|--------|
| `api_router.py` | **API Schema 路由**。管理已注册 API 的检索和元数据查询。为 Retrieval Node 提供候选 API 列表。 | `APIRouter` |
| `tool_router.py` | **工具分发路由**。根据工具名称将执行请求路由到对应工具实例（`SQLQueryTool` / `APIFetchTool` / ...）。 | `ToolRouter` |

### 第六层：Prompt 层（Prompts）

| 文件 | 职责 | 说明 |
|------|------|------|
| `intent_prompt.py` | 意图澄清 Prompt | 指导 LLM 判断查询条件是否完备，提取结构化过滤条件 |
| `planner_prompt.py` | 规划 Prompt | 指导 LLM 根据 API Schema 生成可执行 JSON 计划 |
| `intent_planner_prompt.py` | 合并 Prompt | 将意图识别和规划合并为单次 LLM 调用 |
| `analysis_prompt.py` | 分析 Prompt | 指导 LLM 综合所有数据生成洞察报告 |
| `react_prompt.py` | ReAct Prompt | ReAct 循环的思考和行动提示模板 |
| `sql_prompt.py` | SQL 生成 Prompt | 指导 LLM 根据需求生成安全 SQL |
| `system_prompt.py` | 系统 Prompt | 全局系统角色设定和约束 |

---

## 🔄 节点间的数据流向

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AgentState 状态流转                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  START                                                                       │
│    │ query: "查询最近7天订单统计"                                              │
│    ▼                                                                         │
│  intent_node / intent_planner_node                                           │
│    │ extracted_filters: {start_date: "2024-03-19", end_date: "2024-03-26"}    │
│    │ plan: [                                                                 │
│    │   {step:1, tool:"api_fetch", api_id:"orders_api", params:{...}},        │
│    │   {step:2, tool:"python_exec", code:"sum(data['amount'])", ...}         │
│    │ ]                                                                       │
│    ▼                                                                         │
│  retrieval_node                                                              │
│    │ retrieved_apis: [orders_api, customers_api, ...]                        │
│    ▼                                                                         │
│  planner_node (如使用合并节点则跳过)                                          │
│    │ plan: [...]  (与上同)                                                   │
│    ▼                                                                         │
│  [审批网关] — 普通用户调用 API 需管理员审批                                    │
│    ▼                                                                         │
│  executor_node (Step 1)                                                      │
│    │ data_context["step_1_api_fetch"] = {...订单数据...}                     │
│    ▼                                                                         │
│  executor_node (Step 2)                                                      │
│    │ data_context["step_2_python_exec"] = 123456                            │
│    ▼                                                                         │
│  analyzer_node                                                               │
│    │ messages += "最近7天订单总额为 ¥123,456"                                  │
│    ▼                                                                         │
│  END                                                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 关键设计决策

### 1. 为什么用 `data_context` 隔离存储？

每个步骤的执行结果存入 `data_context[f"step_{idx}_{tool_name}"]`，而非直接拼接到 Prompt 中：
- **避免 Prompt 污染**：大量原始数据会浪费 Token、污染上下文
- **数据隔离**：每步数据独立，便于追溯和调试
- **持久化友好**：字典结构易于序列化到 SQLite Checkpointer

### 2. 为什么用 LangGraph？

- **确定性**：Plan-and-Execute 模式避免 ReAct 的随机性
- **可控性**：显式定义节点和边，易于调试和扩展
- **持久化**：内置 Checkpointer 支持会话状态保存和恢复
- **中断机制**：`interrupt_before` 实现人工审批网关

### 3. 单节点 vs 合并节点

系统同时提供 `intent_node.py` + `planner_node.py`（两步走）和 `intent_planner_node.py`（一步走）：
- **两步走**：意图和规划分离，逻辑更清晰，适合复杂场景
- **一步走**：减少一次 LLM 调用，延迟更低，适合简单查询
- `graph.py` 中通过配置切换使用哪种模式

### 4. 工具系统的可扩展性

新增工具只需三步：
1. 在 `tools/` 下新建类继承 `BaseTool`
2. 在 `tool_router.py` 中注册该工具
3. 在 `executor_node.py` 中添加路由分支（或通过 `ToolRouter` 自动分发）

---

## 🛠️ 二次开发指南

### 修改工作流节点

1. 编辑对应 `nodes/*.py` 文件
2. 在 `graph.py` 中调整节点连接关系（边和条件路由）
3. 如需新增状态字段，同步更新 `state.py` 中的 `AgentState`

### 新增 Prompt 模板

1. 在 `prompts/` 下新建 `xxx_prompt.py`
2. 定义 `get_xxx_prompt(query, context) -> str` 函数
3. 在对应节点中导入并调用

### 新增工具

1. 在 `tools/` 下新建文件，继承 `BaseTool`
2. 实现 `name`、`description`、`execute()`、`validate()`
3. 在 `tool_router.py` 的 `ToolRouter._initialize()` 中注册
4. （可选）在 `executor_node.py` 中显式处理特殊逻辑

### 调试技巧

- 查看 `chat.py` 中的 SSE 事件流，每个节点会输出 `reasoning_log`
- 直接调用 `graph.astream()` 并打印每个节点的 state 变化
- 使用 SQLite 浏览器查看 `./data/checkpoints.db` 中的持久化状态

---

## 📌 与主项目的关系

`agent-core/` 中的文件是 **原文件的精确副本**（仅复制，未修改），与 `backend/app/agent/` 和 `backend/app/api/v1/chat.py` 保持一一对应：

```
agent-core/app/agent/         ↔  backend/app/agent/
agent-core/app/api/v1/chat.py ↔  backend/app/api/v1/chat.py
```

开发时请在主项目 `backend/` 中修改代码，`agent-core/` 仅作阅读参考。如需更新 `agent-core/`，重新执行复制即可。

---

> **提示**：建议配合 `ARCHITECTURE.md` 阅读，以获取更完整的系统架构视角。
