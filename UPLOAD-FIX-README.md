# Upload Fix Documentation

## Summary of Issues Fixed

### 1. **403 Forbidden Error** (/null/ in URL)
**Problem:** The upload URL was showing `http://54.175.54.77/null/api/upload_batch` instead of the correct path.

**Root Cause:** The JavaScript code was running in an iframe (via Streamlit's `components.html`), and `window.location` properties were not resolving correctly in the iframe context, returning `null` values.

**Solution:** Changed from absolute URL construction to relative URL `/api/upload_batch`, which works correctly in both local and deployed environments.

### 2. **413 Request Entity Too Large**
**Problem:** File uploads exceeding 100MB were being rejected by nginx.

**Root Cause:** Default nginx `client_max_body_size` was set to 100MB.

**Solution:**
- Increased `client_max_body_size` to 1GB
- Updated all related buffer sizes and timeouts
- Added proper temp file storage configuration

### 3. **Limited Error Visibility**
**Problem:** Users couldn't see detailed progress or understand why uploads were failing.

**Solution:**
- Added comprehensive debug logging with timestamps
- Implemented real-time progress bar showing MB uploaded
- Added specific error diagnostics for each HTTP status code
- Enhanced error messages with actionable troubleshooting steps

---

## Changes Made

### Frontend Changes (`frontend/streamlit_app.py`)

#### URL Construction Fix
```javascript
// Before (causing /null/ issue):
const baseUrl = `${protocol}//${hostname}`;
const backendUrl = `${baseUrl}/api/upload_batch`;

// After (fixed):
const backendUrl = '/api/upload_batch';  // Relative URL
```

#### Enhanced Logging
- Added timestamp to all log entries
- Added debug log panel (visible during uploads)
- Log all request details (files, sizes, URL, headers)
- Log all response details (status, headers, body)

#### Improved Progress Tracking
- Shows percentage complete (0-100%)
- Shows MB uploaded / total MB
- Real-time upload speed tracking via XHR progress events
- Visual progress bar with color coding

#### Enhanced Error Handling
- HTTP 413: Specific message about file size limits with nginx guidance
- HTTP 403: Details about CORS, nginx restrictions, and authentication
- HTTP 404: Guidance on checking nginx proxy_pass configuration
- HTTP 500: Direction to check FastAPI backend logs
- HTTP 502: Backend connection issue with service check guidance
- HTTP 504: Timeout guidance with suggestions
- Network errors: CORS and connectivity diagnostics

#### File Size Validation
```javascript
// Increased limit from 100MB to 1GB
if (totalSize > 1024 * 1024 * 1024) {
    // Reject upload
}

// Added warning for large uploads
if (totalSize > 500 * 1024 * 1024) {
    // Show warning but allow upload
}
```

### Nginx Configuration Changes (`nginx-ai-platform.conf`)

#### Upload Limits
```nginx
# Maximum upload size
client_max_body_size 1G;  # Increased from 100M

# Buffer size for reading client request body
client_body_buffer_size 128k;

# Timeouts
client_body_timeout 300s;
send_timeout 300s;
keepalive_timeout 300s;
```

#### Temporary File Storage
```nginx
# Dedicated temp directory for large uploads
client_body_temp_path /tmp/nginx_upload_temp 1 2;
```

#### Proxy Configuration
```nginx
location /api/ {
    # Timeouts increased to 5 minutes
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Disable buffering for real-time progress
    proxy_request_buffering off;
    proxy_buffering off;

    # Buffer sizes for large uploads
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;

    # Override body size for API endpoint
    client_max_body_size 1G;
}
```

#### Error Logging
```nginx
# Enhanced error logging
error_log /var/log/nginx/ai-platform-error.log warn;
```

---

## Deployment Instructions

### Option 1: Automated Deployment (Recommended)

1. Make the deployment script executable:
```bash
chmod +x deploy-upload-fix.sh
```

2. Run the deployment script:
```bash
./deploy-upload-fix.sh
```

3. Restart the Streamlit frontend:
```bash
sudo systemctl restart ai-frontend
```

### Option 2: Manual Deployment

1. Create nginx temp directory:
```bash
sudo mkdir -p /tmp/nginx_upload_temp
sudo chown www-data:www-data /tmp/nginx_upload_temp
sudo chmod 755 /tmp/nginx_upload_temp
```

2. Backup current nginx config:
```bash
sudo cp /etc/nginx/sites-available/ai-platform /etc/nginx/sites-available/ai-platform.backup
```

3. Copy new nginx configuration:
```bash
sudo cp nginx-ai-platform.conf /etc/nginx/sites-available/ai-platform
```

4. Test nginx configuration:
```bash
sudo nginx -t
```

5. If test passes, reload nginx:
```bash
sudo systemctl reload nginx
```

6. Restart Streamlit:
```bash
sudo systemctl restart ai-frontend
```

---

## Testing the Fix

### Test 1: Small File Upload
1. Navigate to http://54.175.54.77
2. Open browser Developer Tools (F12) → Console
3. Upload a small file (< 10MB)
4. Verify in the debug log panel:
   - ✓ URL shows `/api/upload_batch` (NOT `/null/api/upload_batch`)
   - ✓ Progress bar appears and updates
   - ✓ Upload completes successfully
   - ✓ Success message shows accepted/duplicates/rejected counts

### Test 2: Large File Upload
1. Upload a file between 100MB and 1GB
2. Verify in the debug log panel:
   - ✓ No 413 error
   - ✓ Progress shows MB uploaded / total MB
   - ✓ Upload completes (may take time)
   - ✓ Success message appears

### Test 3: Error Handling
1. Try uploading a file > 1GB
2. Verify error message explains the 1GB limit
3. Stop the backend: `sudo systemctl stop ai-backend`
4. Try uploading a file
5. Verify error message mentions backend connection issue (502)
6. Restart backend: `sudo systemctl start ai-backend`

---

## Troubleshooting

### Issue: Still getting /null/ in URL

**Check:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh the page (Ctrl+Shift+R)
3. Verify Streamlit restarted: `sudo systemctl status ai-frontend`
4. Check Streamlit logs: `sudo journalctl -u ai-frontend -n 50`

### Issue: Still getting 413 error

**Check:**
1. Verify nginx config is loaded:
```bash
sudo nginx -t
sudo grep "client_max_body_size" /etc/nginx/sites-available/ai-platform
```

2. Check nginx is reloaded:
```bash
sudo systemctl status nginx
sudo systemctl reload nginx
```

3. Verify temp directory exists:
```bash
ls -la /tmp/nginx_upload_temp
```

### Issue: 403 Forbidden error

**Check:**
1. Verify nginx can proxy to backend:
```bash
curl -I http://127.0.0.1:8000/api/health
```

2. Check backend is running:
```bash
sudo systemctl status ai-backend
```

3. Check nginx error logs:
```bash
sudo tail -f /var/log/nginx/ai-platform-error.log
```

4. Verify proxy_pass configuration:
```bash
sudo grep "proxy_pass" /etc/nginx/sites-available/ai-platform
```

### Issue: Upload hangs or times out

**Check:**
1. Backend logs for processing errors:
```bash
sudo journalctl -u ai-backend -f
```

2. Network connectivity:
```bash
ping 54.175.54.77
```

3. Available disk space:
```bash
df -h
```

4. Memory usage:
```bash
free -h
```

### Issue: No debug logs showing

**Check:**
1. Browser console for JavaScript errors (F12 → Console)
2. Verify Streamlit component loaded: Check for iframe in browser inspector
3. Try different browser (Chrome, Firefox, Safari)

---

## Monitoring Upload Performance

### View nginx access logs:
```bash
sudo tail -f /var/log/nginx/access.log
```

### View nginx error logs:
```bash
sudo tail -f /var/log/nginx/ai-platform-error.log
```

### View backend logs:
```bash
sudo journalctl -u ai-backend -f
```

### View frontend logs:
```bash
sudo journalctl -u ai-frontend -f
```

### Check upload performance metrics:
```bash
# Watch temp directory during upload
watch -n 1 'ls -lh /tmp/nginx_upload_temp/*/*'

# Monitor nginx connections
watch -n 1 'ss -tunapl | grep nginx'
```

---

## Performance Tuning

### For even larger files (> 1GB):

1. Increase client_max_body_size in nginx:
```nginx
client_max_body_size 5G;  # or higher
```

2. Increase Python FastAPI body size limit (backend):
```python
# In backend main.py
app = FastAPI(
    max_request_size=5 * 1024 * 1024 * 1024  # 5GB
)
```

3. Increase timeouts for very slow networks:
```nginx
client_body_timeout 600s;
proxy_read_timeout 600s;
```

### For slow uploads:

1. Enable gzip compression (in nginx http block):
```nginx
gzip on;
gzip_types application/json;
```

2. Consider chunked uploads for files > 500MB
3. Implement resumable uploads for very large files

---

## Reverting Changes

If you need to rollback:

1. Restore nginx backup:
```bash
sudo cp /etc/nginx/sites-available/ai-platform.backup.YYYYMMDD_HHMMSS /etc/nginx/sites-available/ai-platform
sudo nginx -t
sudo systemctl reload nginx
```

2. Revert Streamlit code:
```bash
git checkout frontend/streamlit_app.py
sudo systemctl restart ai-frontend
```

---

## Additional Notes

### Browser Compatibility
- Tested on Chrome 145, Firefox 120+, Safari 17+
- XHR upload progress works on all modern browsers
- Fallback logging available if progress events fail

### Security Considerations
- Auth token is properly included in upload requests
- CORS settings maintained in nginx configuration
- Temp files are isolated in dedicated directory
- File type validation still enforced by backend

### Future Enhancements
Consider implementing:
1. Chunked uploads for files > 1GB
2. Resumable uploads (pause/resume)
3. Client-side file validation before upload
4. Virus scanning integration
5. Upload speed throttling
6. Parallel chunk uploads for better performance
7. WebSocket progress updates instead of XHR events
