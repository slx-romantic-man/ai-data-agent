#!/bin/bash
# Quick test to verify Analyzer improvements

curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"查询股票600000在2099年的数据","session_id":"quick_test"}' \
  2>/dev/null | grep -A1 '"type":"answer"' | head -20
