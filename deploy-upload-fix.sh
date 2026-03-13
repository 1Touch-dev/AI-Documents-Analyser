#!/bin/bash

# Deployment script for upload fixes
# This script deploys the nginx configuration changes and restarts services

set -e  # Exit on error

echo "🚀 Deploying upload fixes..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Create nginx temp directory
echo -e "${YELLOW}[1/5]${NC} Creating nginx upload temp directory..."
sudo mkdir -p /tmp/nginx_upload_temp
sudo chown www-data:www-data /tmp/nginx_upload_temp
sudo chmod 755 /tmp/nginx_upload_temp
echo -e "${GREEN}✓${NC} Temp directory created"
echo ""

# 2. Backup current nginx config
echo -e "${YELLOW}[2/5]${NC} Backing up current nginx configuration..."
if [ -f /etc/nginx/sites-available/ai-platform ]; then
    sudo cp /etc/nginx/sites-available/ai-platform /etc/nginx/sites-available/ai-platform.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓${NC} Backup created"
else
    echo -e "${YELLOW}⚠${NC} No existing config found at /etc/nginx/sites-available/ai-platform"
fi
echo ""

# 3. Copy new nginx config
echo -e "${YELLOW}[3/5]${NC} Installing new nginx configuration..."
sudo cp nginx-ai-platform.conf /etc/nginx/sites-available/ai-platform

# Create symlink if it doesn't exist
if [ ! -L /etc/nginx/sites-enabled/ai-platform ]; then
    sudo ln -s /etc/nginx/sites-available/ai-platform /etc/nginx/sites-enabled/
    echo -e "${GREEN}✓${NC} Symlink created"
fi
echo -e "${GREEN}✓${NC} Configuration installed"
echo ""

# 4. Test nginx configuration
echo -e "${YELLOW}[4/5]${NC} Testing nginx configuration..."
if sudo nginx -t; then
    echo -e "${GREEN}✓${NC} Nginx configuration is valid"
else
    echo -e "${RED}✗${NC} Nginx configuration test failed!"
    echo "Please check the errors above and fix the configuration."
    exit 1
fi
echo ""

# 5. Reload nginx
echo -e "${YELLOW}[5/5]${NC} Reloading nginx..."
sudo systemctl reload nginx
echo -e "${GREEN}✓${NC} Nginx reloaded"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart Streamlit frontend: sudo systemctl restart ai-frontend"
echo "2. Check nginx logs: sudo tail -f /var/log/nginx/ai-platform-error.log"
echo "3. Test file upload at http://54.175.54.77"
echo ""
echo "Configuration changes:"
echo "  • Fixed /null/ URL issue in upload JavaScript"
echo "  • Increased upload limit to 1GB"
echo "  • Added comprehensive error logging"
echo "  • Added upload progress tracking"
echo "  • Enhanced timeout settings for large files"
echo ""
