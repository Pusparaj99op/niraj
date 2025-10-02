# Type Checking Validation API Contract

**Endpoint**: `POST /api/v1/type-check/validate`
**Purpose**: Validate type checking status of the codebase
**Authentication**: Required (JWT token)

## Request Schema

```json
{
  "type": "object",
  "properties": {
    "check_type": {
      "type": "string",
      "enum": ["mypy", "flake8", "all"],
      "default": "all"
    },
    "strict_mode": {
      "type": "boolean",
      "default": true
    },
    "include_files": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Specific files to check (optional)"
    }
  },
  "required": ["check_type"]
}
```

## Response Schema

### Success Response (200)
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL"]
    },
    "total_errors": {
      "type": "integer",
      "minimum": 0
    },
    "errors_by_type": {
      "type": "object",
      "additionalProperties": {
        "type": "integer",
        "minimum": 0
      }
    },
    "errors_by_file": {
      "type": "object",
      "additionalProperties": {
        "type": "integer",
        "minimum": 0
      }
    },
    "execution_time": {
      "type": "number",
      "minimum": 0
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["status", "total_errors", "execution_time", "timestamp"]
}
```

### Error Response (500)
```json
{
  "type": "object",
  "properties": {
    "error": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["error", "message", "timestamp"]
}
```

## Contract Tests

### Test Case 1: Successful Validation
```python
def test_type_check_validation_success():
    response = client.post("/api/v1/type-check/validate", json={
        "check_type": "mypy",
        "strict_mode": true
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_errors" in data
    assert isinstance(data["total_errors"], int)
    assert data["total_errors"] >= 0
```

### Test Case 2: Invalid Request
```python
def test_type_check_validation_invalid_request():
    response = client.post("/api/v1/type-check/validate", json={
        "check_type": "invalid"
    })
    assert response.status_code == 422  # Validation error
```

### Test Case 3: System Error
```python
def test_type_check_validation_system_error():
    # Mock mypy command failure
    response = client.post("/api/v1/type-check/validate", json={
        "check_type": "mypy"
    })
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert "message" in data
```