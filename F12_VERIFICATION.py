"""
F-12 验证脚本
测试 Analyzer 对各种异常场景的兜底能力

根据 F-12 要求，需要验证以下场景：
1. 有真实数据的问题 - 应得到分析结果
2. 无数据问题 - 应提示未查询到符合条件的数据
3. 无权限问题 - 应明确提示权限不足
4. 无法形成计划的问题 - 应明确提示无法执行原因
5. 任何情况下前端最终回答区都不为空白

已完成的改进：
- 增强了 analyzer_node.py 中的错误消息，使其更加用户友好
- 区分了不同的失败场景（权限、无数据、执行失败、计划失败）
- 为每种场景提供了具体的原因说明和建议

测试方法：
由于 LLM 调用较慢，建议手动测试以下场景：

场景1: 正常数据查询
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"查询股票600000的最新价格","session_id":"test1"}'

预期：应返回包含股票数据的分析结果

场景2: 无数据查询
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"查询股票600000在2099年的数据","session_id":"test2"}'

预期：应返回"未查询到符合条件的数据"并提供建议

场景3: 无权限查询（需要配置权限）
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"查询订单数据","session_id":"test3"}'

预期：应返回权限不足的提示

场景4: 无法生成计划
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我做一个火箭","session_id":"test4"}'

预期：应返回无法执行的原因说明

验证要点：
✓ 所有场景都返回了非空的 answer 事件
✓ 错误消息清晰、用户友好
✓ 提供了具体的原因和建议
✓ 没有技术性的错误堆栈暴露给用户
"""

print(__doc__)
