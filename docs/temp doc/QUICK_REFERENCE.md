# NIRAJ Runner - Quick Reference Guide

## 🚀 Quick Start

Run the interactive menu:
```bash
python niraj.py
```

## 📋 Main Menu Structure

```
Main Menu
├── 1. 🚀 Start Services
├── 2. 🛑 Stop Services
├── 3. 📊 Service Status
├── 4. 📦 Install Dependencies
├── 5. ⚙️  Configuration
├── 6. 🔧 Service Management
├── 7. 🧪 API Testing ⭐ NEW
│   ├── 1. Test All API Endpoints
│   ├── 2. Quick Health Check
│   ├── 3. Test Specific Endpoint
│   ├── 4. View API Documentation
│   └── 5. Test WebSocket Connection
├── 8. 🗑️  Cache & Logs Management ⭐ NEW
│   ├── 1. Clear Redis Cache
│   ├── 2. Clear All Logs
│   ├── 3. View Recent Logs
│   ├── 4. Show Log File Sizes
│   ├── 5. Clear Python Cache
│   └── 6. Clear Everything
├── 9. 📚 Help & Documentation
└── 0. ❌ Exit
```

## 🎯 Common Workflows

### Test All APIs (Single Click)
```
1. Start backend: Menu → 1 → 1
2. Test APIs: Menu → 7 → 1
3. View results with pass/fail status
```

### Clear Cache & Logs
```
Menu → 8 → 6 → type "yes" → Done!
```

### Quick Health Check
```
Menu → 7 → 2 → See instant health status
```

### View Recent Logs
```
Menu → 8 → 3 → Enter lines (default: 50)
```

### Check Log Sizes
```
Menu → 8 → 4 → See all log file sizes
```

## 🔧 API Testing Features

### Automatic Testing
- ✅ Tests 5 core endpoints automatically
- ✅ Shows HTTP status codes
- ✅ Pass/fail indicators
- ✅ Summary statistics
- ✅ Works with or without requests library

### Manual Testing
- Test any custom endpoint
- View full response data
- HTTP status code validation

### Documentation Access
- Quick links to Swagger UI
- ReDoc documentation
- OpenAPI schema
- One-click browser opening

## 🗑️ Maintenance Features

### Redis Cache
- Clear all cached data
- Reset cache state
- Instant operation

### Log Management
- View recent entries
- Check file sizes
- Clear individual logs
- Clear all logs at once

### Python Cache
- Find all __pycache__ directories
- Shows count before deletion
- Recursive cleanup
- Confirmation prompt

### Complete Cleanup
- Clears Redis, logs, and Python cache
- Requires "yes" confirmation
- Complete system reset

## 💡 Tips

1. **Before Testing APIs**: Always start the backend first (Menu → 1 → 1)
2. **Regular Maintenance**: Clear cache weekly to free disk space
3. **Debugging**: Use "View Recent Logs" (Menu → 8 → 3) for troubleshooting
4. **Health Monitoring**: Quick health check (Menu → 7 → 2) is fastest way to verify backend
5. **Safe Cleanup**: "Clear Everything" (Menu → 8 → 6) requires typing "yes" - prevents accidents

## 🎨 Visual Indicators

- ✅ **Green/Success**: Operation completed successfully
- ❌ **Red/Error**: Operation failed or service down
- ⚠️  **Yellow/Warning**: Service running but issues detected
- 🔍 **Info**: Informational messages
- ⭕ **Not Started**: Service not yet started

## 📊 Sample Output

### API Testing Output
```
🧪 Testing API endpoints...
[INFO] Testing Health Check: http://localhost:8000/health
  ✅ Health Check: OK (Status: 200)
[INFO] Testing System Info: http://localhost:8000/info
  ✅ System Info: OK (Status: 200)
...
📊 API Test Summary: 5/5 endpoints passed
```

### Log Size Output
```
📊 Log File Sizes:
  /home/user/niraj/logs/niraj.log: 2.45 MB
  /home/user/niraj/backend/logs/niraj.log: 1.23 MB

  Total: 3.68 MB
```

## 🔐 Safety Features

- ✅ Confirmation prompts for destructive operations
- ✅ Clear warnings before data deletion
- ✅ Process status checks
- ✅ Graceful error handling
- ✅ No data loss on cancellation

## 🚨 Troubleshooting

### API Tests Fail
1. Check if backend is running (Menu → 3)
2. Start backend if needed (Menu → 1 → 1)
3. Wait 10 seconds for startup
4. Try again

### Cannot Clear Redis Cache
1. Check if Redis is installed: `redis-cli --version`
2. Check if Redis is running: `redis-cli ping`
3. Install Redis if missing

### Logs Not Found
- Logs are created when services run
- Start backend to generate logs
- Check paths in error messages

## 🎓 Learn More

- Full documentation: `NEW_FEATURES.md`
- Help menu: Menu → 9
- API docs: Menu → 7 → 4
- README: Project root directory
