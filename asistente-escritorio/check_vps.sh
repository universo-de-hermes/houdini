#!/bin/bash
echo "=== 1. Bridge ==="
curl -s --max-time 5 http://127.0.0.1:9876/health
echo ""
echo "=== 2. API ==="
curl -s --max-time 5 http://localhost:9999/api/config
echo ""
echo "=== 3. Chat ==="
curl -s --max-time 30 -X POST http://localhost:9999/api/chat -H "Content-Type: application/json" -d '{"message":"Hola","session_id":"t"}'
echo ""
echo "=== 4. Ports ==="
ss -tlnp | grep -E '9876|9999'
echo ""
echo "=== 5. Services ==="
systemctl status houdini-bridge.service --no-pager 2>&1 | head -5
systemctl status webui-backend.service --no-pager 2>&1 | head -3