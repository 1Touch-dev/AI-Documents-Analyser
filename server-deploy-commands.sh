#!/bin/bash
# Run these commands on your EC2 server to deploy the upload fixes

echo "======================================"
echo "Upload Fix Deployment Commands"
echo "======================================"
echo ""
echo "Copy and paste these commands one by one on your EC2 server:"
echo ""

cat << 'EOF'
# 1. Navigate to project directory
cd ~/AI-Documents-Analyser

# 2. Check what local changes exist
git diff frontend/streamlit_app.py

# 3. Stash local changes (saves them temporarily)
git stash

# 4. Pull the latest changes
git pull origin main

# 5. Create nginx temp directory
sudo mkdir -p /tmp/nginx_upload_temp
sudo chown www-data:www-data /tmp/nginx_upload_temp
sudo chmod 755 /tmp/nginx_upload_temp

# 6. Backup current nginx config
sudo cp /etc/nginx/sites-available/ai-platform /etc/nginx/sites-available/ai-platform.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No existing config to backup"

# 7. Copy new nginx configuration
sudo cp nginx-ai-platform.conf /etc/nginx/sites-available/ai-platform

# 8. Create symlink if it doesn't exist
sudo ln -sf /etc/nginx/sites-available/ai-platform /etc/nginx/sites-enabled/ai-platform

# 9. Test nginx configuration
sudo nginx -t

# 10. If test passes, reload nginx
sudo systemctl reload nginx

# 11. Restart Streamlit frontend
sudo systemctl restart ai-frontend

# 12. Check service status
echo ""
echo "=== Service Status ==="
sudo systemctl status ai-backend --no-pager -l | head -15
echo ""
sudo systemctl status ai-frontend --no-pager -l | head -15
echo ""
sudo systemctl status nginx --no-pager -l | head -10

# 13. Show recent logs
echo ""
echo "=== Recent Frontend Logs ==="
sudo journalctl -u ai-frontend -n 20 --no-pager

# 14. Monitor logs (press Ctrl+C to exit)
echo ""
echo "=== Monitoring Nginx Error Logs (Ctrl+C to exit) ==="
sudo tail -f /var/log/nginx/ai-platform-error.log

EOF
