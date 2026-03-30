import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

response = requests.post(
    'http://localhost:8002/api/v1/chat',
    headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc0MzI0MjQwMH0.xyz'},
    json={'message': 'AAPL股票最近表现如何', 'session_id': None},
    timeout=310
)

result = response.json()
print(f'Status: {response.status_code}')
print(f'\\n=== Full Response ===')
print(result)