# New Features Added to niraj.py

## Overview
Enhanced the NIRAJ runner script with comprehensive API testing and system maintenance capabilities.

## New Features

### 1. 🧪 API Testing Menu (Option 7)

Complete API testing suite with the following options:

#### 1.1 Test All API Endpoints
- **What it does**: Automatically tests all backend API endpoints one by one
- **Endpoints tested**:
  - Health Check (`/health`)
  - System Info (`/info`)
  - API Root (`/`)
  - API Documentation (`/docs`)
  - OpenAPI Schema (`/openapi.json`)
- **Output**: Shows pass/fail status for each endpoint with HTTP status codes
- **Summary**: Displays total passed/failed endpoints

#### 1.2 Quick Health Check
- **What it does**: Performs a rapid health check on the backend API
- **Usage**: Quick way to verify the backend is responsive
- **Output**: Shows health status and response data

#### 1.3 Test Specific Endpoint
- **What it does**: Allows you to test any custom endpoint
- **Usage**: Enter any URL to test (e.g., `http://localhost:8000/custom-endpoint`)
- **Output**: Shows HTTP status code and response body

#### 1.4 View API Documentation
- **What it does**: Displays API documentation URLs
- **Features**:
  - Lists all documentation endpoints
  - Option to open Swagger UI in browser automatically
  - Shows OpenAPI schema URL

#### 1.5 Test WebSocket Connection
- **What it does**: Provides guidance for testing WebSocket connections
- **Output**: Shows WebSocket URL and testing instructions

### 2. 🗑️ Cache & Logs Management Menu (Option 8)

Comprehensive system maintenance tools:

#### 2.1 Clear Redis Cache
- **What it does**: Flushes all data from Redis cache
- **Command**: Uses `redis-cli FLUSHALL`
- **Safety**: Prompts confirmation before clearing
- **Use case**: Clear stale cache data, reset cache state

#### 2.2 Clear All Logs
- **What it does**: Clears all log files
- **Locations cleared**:
  - `/logs/niraj.log`
  - `/backend/logs/niraj.log`
- **Output**: Shows which log files were cleared
- **Use case**: Free up disk space, start fresh logging

#### 2.3 View Recent Logs
- **What it does**: Displays recent log entries
- **Features**:
  - Configurable number of lines (default: 50)
  - Shows logs from all log files
  - Formatted output for easy reading
- **Use case**: Quick debugging, monitor system activity

#### 2.4 Show Log File Sizes
- **What it does**: Displays size of all log files
- **Features**:
  - Shows individual file sizes
  - Displays total log size
  - Formats in MB/KB/bytes as appropriate
- **Use case**: Monitor disk usage, identify large log files

#### 2.5 Clear Python Cache
- **What it does**: Removes all `__pycache__` directories
- **Features**:
  - Recursively finds all cache directories
  - Shows count of directories found
  - Prompts confirmation before deletion
- **Use case**: Clean build artifacts, fix import issues

#### 2.6 Clear Everything
- **What it does**: Complete system cleanup
- **Clears**:
  - Redis cache
  - All log files
  - Python cache directories
- **Safety**: Requires typing "yes" to confirm
- **Use case**: Complete system reset, prepare for fresh start

## Updated Main Menu

The main menu has been reorganized for better usability:

```
📋 Main Menu:
  1. 🚀 Start Services
  2. 🛑 Stop Services
  3. 📊 Service Status
  4. 📦 Install Dependencies
  5. ⚙️  Configuration
  6. 🔧 Service Management
  7. 🧪 API Testing              ← NEW
  8. 🗑️  Cache & Logs Management  ← NEW
  9. 📚 Help & Documentation
  0. ❌ Exit
```

## New Methods Added

### NirajRunner Class

1. **`test_api_endpoints()`**: Tests all API endpoints and returns results dictionary
2. **`clear_redis_cache()`**: Clears Redis cache using redis-cli
3. **`clear_logs(log_path=None)`**: Clears log files
4. **`view_logs(lines=50)`**: Displays recent log entries
5. **`get_log_size()`**: Returns dictionary of log file sizes
6. **`clear_cache_directory(cache_dir=None)`**: Clears Python cache directories

### MenuInterface Class

1. **`display_api_testing_menu()`**: Shows API testing submenu
2. **`display_cache_logs_menu()`**: Shows cache/logs management submenu
3. **`handle_api_testing()`**: Handles API testing menu logic
4. **`handle_cache_logs_management()`**: Handles cache/logs menu logic
5. **`test_all_endpoints()`**: Tests all API endpoints with formatted output
6. **`quick_health_check()`**: Quick health check for backend
7. **`test_specific_endpoint()`**: Test user-specified endpoint
8. **`view_api_docs()`**: Display and open API documentation
9. **`test_websocket()`**: WebSocket testing guidance
10. **`view_logs_interactive()`**: Interactive log viewer
11. **`show_log_sizes()`**: Display log file sizes
12. **`clear_python_cache()`**: Clear Python cache directories
13. **`clear_everything()`**: Complete system cleanup

## Usage Examples

### Test All APIs
```bash
python niraj.py
# Select: 7 → 1
```

### Clear Cache and Logs
```bash
python niraj.py
# Select: 8 → 6 (Clear Everything)
```

### Quick Health Check
```bash
python niraj.py
# Select: 7 → 2
```

### View Recent Logs
```bash
python niraj.py
# Select: 8 → 3
```

## Technical Details

### Dependencies Used
- **requests** (optional): For HTTP requests (falls back to curl if not available)
- **subprocess**: For running system commands
- **os/pathlib**: For file system operations
- **shutil**: For directory operations
- **webbrowser**: For opening documentation in browser

### Error Handling
- All operations include proper error handling
- Graceful fallbacks for missing dependencies
- User-friendly error messages
- Safe file operations with existence checks

### Safety Features
- Confirmation prompts for destructive operations
- Clear warnings before data deletion
- Detailed operation logs
- Process status checks before operations

## Benefits

1. **Single Click Testing**: Test all APIs with one menu selection
2. **Easy Maintenance**: Clear cache and logs without terminal commands
3. **Better Debugging**: Quick access to logs and system status
4. **User-Friendly**: Intuitive menu structure with clear options
5. **Safe Operations**: Confirmation prompts prevent accidental data loss
6. **Comprehensive**: All common maintenance tasks in one place

## Future Enhancements

Potential additions for future versions:
- Scheduled cache clearing
- Log rotation automation
- Performance metrics collection
- API response time tracking
- WebSocket testing implementation
- Database maintenance tools
- Automated backup before clearing
