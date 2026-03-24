
# 📄 AI-Data-Agent - v4 架构升级技术需求文档 (TRD)

**文档状态**: 最终版 (Final)
**设计理念**: 拥抱大模型原生能力 (Vibe Coding)，去中间件化，数据强管控。
**核心目标**: 从“不可控的 ReAct 循环推理”向“高确定性的 LangGraph Plan-and-Execute (规划与执行)”架构平滑升级，彻底解决复杂归因分析中的幻觉与上下文污染问题，实现支持多轮下钻的持久化企业级数据智能体。

---

## 一、 总体架构蓝图

### 1.1 升级前 vs 升级后对比

| 维度 | 现状 | 目标 |
| :--- | :--- | :--- |
| **大脑引擎** | 纯 ReAct Prompt 循环 (最多10次迭代) | **LangGraph 状态机图 (Plan-and-Execute)** |
| **状态记忆** | 无状态 (仅依赖历史对话 Message) | **持久化 ThreadState (含结构化查询结果)** |
| **执行流转** | 边想边做，容易丢失初始目标 | **先规划出完整 JSON 计划表，再按部就班执行** |
| **高危拦截** | 依赖工具内部校验，无法挂起流程 | **LangGraph 原生 `interrupt_before` 挂起审批** |
| **数据传递** | 多轮 API 结果拼接到 Prompt 导致污染 | **隔离存入 `data_context` 字典，最后统一分析** |

### 1.2 资产保留声明 (Do Not Change)

本次升级**严禁重构**以下已被验证的优秀底层资产：

1. **统一工具入口**：维持固定的 4 个核心工具 (`sql_query`, `api_fetch`, `data_analysis`, `export_excel`)。
2. **两阶段检索机制**：维持现有的 `api_retrieval_service.py` (向量召回 + LLM 精排) 不变。
3. **数据权限体系**：维持原有的 RBAC、行级过滤、列级脱敏机制不变。

---

## 二、 核心数据结构设计 (State Machine)

### 2.1 全局状态定义 (AgentState)

系统的核心由无状态转为状态机。需在 LangGraph 中定义全局 `AgentState`，贯穿所有节点的生命周期。

```python
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 1. 基础对话状态
    messages: Annotated[list, add_messages]  # 对话历史记录
    query: str                               # 用户当前轮次的原始提问
    
    # 2. 意图与记忆
    extracted_filters: Dict[str, Any]        # 提取的全局条件 (例: {"region": "华东", "month": "2023-10"})
    
    # 3. 规划与执行追踪
    plan: List[Dict[str, Any]]               # Planner 生成的 JSON 数组执行步骤
    current_step: int                        # 执行器当前执行的步骤索引 (默认 0)
    
    # 4. 数据沙箱 (核心改造点)
    data_context: Dict[str, Any]             # 存放所有 API 调用的 JSON 结果。Key 为 api_id，Value 为数据。不在 Prompt 中拼接！
```

### 2.2 状态持久化机制 (Checkpointer)

* **技术选型**：使用 LangGraph 官方的 `PostgresSaver` (如果使用 MySQL 则自定义对应的 Saver)。
* **存储机制**：以 `thread_id` (会话 ID) 为 Key。每次节点流转完毕，系统自动将上述 `AgentState` 序列化写入数据库。
* **业务价值**：支持**多轮深度下钻**。用户在第二轮追问时，系统直接从数据库唤醒第一轮的 `data_context` (无需重新查库)，极大提升响应速度与逻辑连贯性。

---

## 三、 工作流图节点设计 (The Graph Nodes)

系统放弃复杂的洋葱圈中间件栈，采用极简的节点 (Nodes) 流转逻辑。

### Node 0: Intent Clarification (意图澄清节点 - 替代中间件)

* **逻辑**：作为图的入口。利用极小尺寸的 LLM 判断用户 `query` 是否缺乏必要查询条件(如：时间、业务线)。
* **输出**：
  * 如果条件缺失：直接输出反问文本，图流转走向 `End` 节点。
  * 如果条件完备：更新 `extracted_filters`，将图流转引向 `Retrieval Node`。

### Node 1: API Retrieval (工具检索节点 - 存量复用)

* **逻辑**：调用原有的 `api_retrieval_service.py`。
* **输入**：`state["query"]`
* **输出**：将召回的 Top-10 API Schema 注入到下一步的临时变量中。**(此节点仅做检索，不改变主要 State)**

### Node 2: Planner (全局规划师节点 - 替代 ReAct Thought)

* **职责**：大模型在此处拥有最高 IQ，不受冗长返回数据的干扰。仅负责制定执行计划表。
* **Prompt 模板** (严格遵循 Vibe Coding 极简风)：

    ```python
    prompt = f"""
    你是一个资深数据分析师。为了回答用户的复杂归因问题，你需要制定一个数据查询的步骤计划。
    
    【全局过滤条件】：{state["extracted_filters"]}
    【可用的 API】（已为你精准检索）：
    {format_apis(top_10_apis)}
    
    请输出一个严格的 JSON 数组执行计划，只允许使用 api_fetch 或 sql_query 工具。
    目标问题：{state["query"]}
    
    输出格式要求：[
      {{"step": 0, "tool": "api_fetch", "api_id": "inventory_api", "params": {{"region": "华东"}}}},
      {{"step": 1, "tool": "api_fetch", "api_id": "order_api", "params": {{"status": "delayed"}}}},
      {{"step": 2, "tool": "data_analysis", "api_id": "anomaly_detect", "params": {{}}}}
    ]
    """
    ```

* **状态更新**：覆盖写入 `state["plan"]`，并将 `state["current_step"]` 重置为 0。

### Node 3: Executor (无脑执行机节点)

* **职责**：一个纯粹的 Python 执行函数，遍历 `plan` 列表，执行具体的工具，并**妥善保存数据**。不再需要大模型参与，彻底消灭 ReAct 幻觉。
* **核心逻辑**：

    ```python
    async def executor_node(state: AgentState):
        current_idx = state["current_step"]
        step_action = state["plan"][current_idx]
        
        # 路由到对应的物理工具 (复用原有工具代码)
        if step_action["tool"] == "api_fetch":
            result = await api_fetch_tool.execute(step_action["api_id"], step_action["params"])
        elif step_action["tool"] == "sql_query":
            result = await sql_query_tool.execute(step_action["params"])
            
        # ⚠️ 核心改造点：将查询结果隔离存入字典，绝不放入对话历史！
        state["data_context"][f"step_{current_idx}_{step_action['api_id']}"] = result
        state["current_step"] += 1
        
        return state
    ```

### Node 4: Analyzer (终局分析节点 - 复用 DataAnalyzer)

* **职责**：流程的最后一站。将前置累积的所有数据一次性喂给大模型，生成最终洞察。
* **逻辑**：
    1. 提取累积数据：`all_data = json.dumps(state["data_context"], ensure_ascii=False)[:MAX_TOKENS_LIMIT]`
    2. 调用现有引擎：`await DataAnalyzer.analyze(query=state["query"], data=all_data)`
    3. **状态更新**：将最终的分析报告文本追加到 `state["messages"]` 中，展示给用户。

---

## 四、 边与路由控制 (Edges & Routing)

不再需要复杂的中间件控制流，全部转换为 LangGraph 的**条件边 (Conditional Edges)**。

1. **Start -> Intent_Node**: 入口默认流向意图澄清。
2. **Intent_Node -> Retrieval_Node (或 End)**:
    * 条件判断：如果意图不清，转 `End`；如果清晰，转 `Retrieval_Node`。
3. **Retrieval_Node -> Planner_Node**: 单向连接。
4. **Planner_Node -> Executor_Node (含人工审批网关)**:
    * **⚠️ 强需人工介入设计 (Human-in-the-loop)**：
    * 在图的配置中设置：`interrupt_before=["Executor_Node"]`。
    * **触发条件判断逻辑**：在条件边函数中检查 `state["plan"]`。如果 `plan` 内包含需要高耗时计算的 API 或敏感数据表，流程挂起，向前端推送 SSE 审批卡片；若全是普通查询，则自动放行。
5. **Executor_Node -> Executor_Node (循环边)**:
    * 条件判断：`if state["current_step"] < len(state["plan"])`，则继续调用自身（执行下一步）。
    * **防死循环机制**：由 `plan` 的长度直接决定循环次数，达到即停，实现 100% 确定性流转。
6. **Executor_Node -> Analyzer_Node**:
    * 条件判断：`if state["current_step"] == len(state["plan"])`，说明所有 API 已执行完毕，进入终局分析。
7. **Analyzer_Node -> End**: 完结，向用户输出结果。

---

## 五、 实施路径与节奏规划 (Phases)

为了确保平稳过渡，建议分两个 Sprint 进行实施：

### Sprint 1: 核心流程“换脑”

* **任务 1**：剥离原有的 ReAct prompt 循环逻辑。
* **任务 2**：引入 `langgraph` 库，建立基础的 `AgentState` 数据结构。
* **任务 3**：编写 `Planner Node` 和 `Executor Node`，将现有的 `api_retrieval_service` 和 4 个核心工具直接接入这两个节点。
* **验证标准**：大模型能够生成 JSON 计划，并正确串行调用多个 API，系统不再出现死循环。

### Sprint 2: 记忆强化与人工审批

* **任务 1**：接入 `PostgresSaver`，实现 `thread_id` 级别的状态持久化。
* **任务 2**：测试“多轮对话状态下钻”，验证第二轮对话能正确读取 `data_context`。
* **任务 3**：配置 `interrupt_before` 挂起逻辑，与前端对接 WebSocket/SSE 审批卡片交互。
* **任务 4**：对接原有的 `DataAnalyzer` 到 `Analyzer Node` 进行最终渲染。

---

## 六、 风险控制与排雷指南 (Risk Mitigation)

1. **JSON 格式化风险**：Planner 节点由大模型生成 JSON，极小概率会存在格式错误。
    * *应对方案*：在 Planner 输出后加一个轻量的 Pydantic 或 JSON 校验逻辑，如果解析失败，自动触发 LangGraph 的 Fallback 重试边（最多重试 2 次），无需抛出给用户。
2. **State 容量爆炸风险**：如果 `api_fetch` 返回的 JSON 体积过大（超过大模型上下文限制），会导致最后的 Analyzer 节点报错。
    * *应对方案*：在 Executor 节点往 `data_context` 存入数据前，加入截断保护逻辑（比如依然维持你之前“最多保留 50 行”的设计，或者在数据量过大时调用一个轻量的摘要总结小模型处理后再存入）。

---
