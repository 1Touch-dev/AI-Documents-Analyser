#!/bin/bash
# Diagnostic and fix script for ai-frontend service issues

echo "======================================"
echo "Frontend Service Diagnostic & Fix"
echo "======================================"
echo ""

# Run these commands on the EC2 server
cat << 'EOF'
# 1. Check current status of ai-frontend
echo "=== Current Status ==="
sudo systemctl status ai-frontend --no-pager -l

# 2. Check recent logs for errors
echo ""
echo "=== Recent Logs (last 50 lines) ==="
sudo journalctl -u ai-frontend -n 50 --no-pager

# 3. Check if port 8501 is in use
echo ""
echo "=== Port 8501 Status ==="
sudo lsof -i :8501 || echo "Port 8501 is not in use"

# 4. Check if Streamlit process is running
echo ""
echo "=== Streamlit Processes ==="
ps aux | grep streamlit | grep -v grep || echo "No Streamlit processes found"

# 5. Kill any stuck processes
echo ""
echo "=== Cleaning up stuck processes ==="
sudo pkill -9 streamlit || echo "No processes to kill"
sleep 2

# 6. Check virtual environment
echo ""
echo "=== Checking Virtual Environment ==="
ls -la /home/ubuntu/AI-Documents-Analyser/.venv/bin/streamlit

# 7. Test running Streamlit manually
echo ""
echo "=== Testing Streamlit manually ==="
cd /home/ubuntu/AI-Documents-Analyser
source .venv/bin/activate
which streamlit
streamlit --version

# 8. Restart the service
echo ""
echo "=== Restarting ai-frontend service ==="
sudo systemctl daemon-reload
sudo systemctl restart ai-frontend
sleep 5

# 9. Check status again
echo ""
echo "=== Service Status After Restart ==="
sudo systemctl status ai-frontend --no-pager -l

# 10. Check if port 8501 is now listening
echo ""
echo "=== Port 8501 Status After Restart ==="
sudo lsof -i :8501

# 11. Test HTTP connection to Streamlit
echo ""
echo "=== Testing HTTP Connection ==="
curl -I http://127.0.0.1:8501 || echo "Failed to connect to Streamlit"

# 12. Monitor logs in real-time
echo ""
echo "=== Live Logs (Ctrl+C to exit) ==="
sudo journalctl -u ai-frontend -f

EOF
