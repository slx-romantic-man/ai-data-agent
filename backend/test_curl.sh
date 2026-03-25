#!/bin/bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "查询最近七天的订单数量和订单总金额", "session_id": "test_f11_final"}' \
  --no-buffer
