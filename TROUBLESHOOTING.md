# Troubleshooting Guide

This document contains known issues, workarounds, and solutions encountered during development.

## 1. Python 3.13 Compatibility with Moto

**Issue:** Moto library (AWS mocking for tests) has compatibility issues with Python 3.13.

**Error:**
```
ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process
```

**Root Cause:** Cryptography library dependency uses PyO3 which has compatibility issues with Python 3.13.

**Solution:** Use Python 3.12.x
```bash
python --version  # Should show 3.12.x
```

---

## 2. SAM Template Circular Dependency (S3 → Lambda)

**Issue:** Creating S3 event notification to trigger Lambda in SAM template causes circular dependency.

**Error:**
```
Circular dependency between resources: [CsvProcessorFunction, S3Bucket]
```

**Root Cause:** 
- Lambda needs permission to be invoked by S3
- S3 notification needs Lambda ARN
- Both resources reference each other in template

**Solution:** Split configuration into two steps:
1. Remove `Events` section from Lambda in `template.yaml`
2. Configure S3 notification via AWS CLI in `deploy.sh` after stack creation

```bash
# Add Lambda permission
aws lambda add-permission --function-name $FUNCTION_NAME \
  --statement-id S3InvokeFunction --action lambda:InvokeFunction \
  --principal s3.amazonaws.com --source-arn $BUCKET_ARN

# Configure S3 notification
aws s3api put-bucket-notification-configuration \
  --bucket $BUCKET_NAME --notification-configuration file://notification.json
```

---

## 3. Settings Import Pattern for Testing

**Issue:** Tests cannot override configuration when settings object is imported directly.

**Wrong Pattern:**
```python
from src.core.config import settings  # ❌ Imports object at module load time
```

**Problem:** Test fixtures that reload settings don't affect already-imported references.

**Correct Pattern:**
```python
from src.core import config  # ✅ Import module, not object
# Use: config.settings.aws_region
```

**Affected Files:**
- `src/repositories/s3_repository.py`
- `src/repositories/dynamo_repository.py`

---

## 4. API Gateway Stage Prefix Routing

**Issue:** API Gateway adds stage prefix (`/dev`) causing 404 errors.

**Error:**
```
Request to /v1/api/health returns 404
Actual path needed: /dev/v1/api/health
```

**Solution:** Configure FastAPI with `root_path`:
```python
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    root_path=f"/{settings.environment}"
)
```

---

## 5. DynamoDB Float to Decimal Conversion

**Issue:** DynamoDB doesn't support Python `float` type.

**Error:**
```
Float types are not supported. Use Decimal types instead.
```

**Solution:** Convert at persistence layer:
```python
# When saving
item = {'efficacy': Decimal(str(drug.efficacy))}

# When reading
drug = Drug(efficacy=float(item['efficacy']))
```

**Design Decision:** Keep domain model using native Python `float`, convert only at database boundary.

---

## 6. S3 Bytes to File-like Object Conversion

**Issue:** S3 `get_object()` returns bytes, CSV parser needs file-like object.

**Error:**
```
AttributeError: 'bytes' object has no attribute 'read'
```

**Solution:**
```python
import io

file_content = s3_repository.get_file(s3_key)  # bytes
file_obj = io.BytesIO(file_content)  # file-like object
drugs = file_service.parse_csv_to_drugs(file_obj)
```

---

## 7. Git Bash SAM CLI Path Issues (Windows)

**Issue:** Git Bash on Windows doesn't recognize `sam` command.

**Error:**
```
sam: command not found
```

**Solution:** Use full path in scripts:
```bash
SAM_CMD="/c/Program Files/Amazon/AWSSAMCLI/bin/sam.cmd"
"$SAM_CMD" build
```

**Alternative:** Run deployment script in PowerShell.

---

## 8. Environment Variable Encoding Issues

**Issue:** `.env` file with wrong encoding (UTF-16) causes validation errors.

**Error:**
```
ValidationError: Invalid characters in environment variables
```

**Solution:** Save `.env` with UTF-8 encoding:
- VS Code: Click encoding in status bar → Save with Encoding → UTF-8
- Verify no BOM or null bytes

---

## 9. Test Table Name Isolation

**Issue:** Tests fail when using production/dev table names (`DrugData-dev`) in test environment.

**Problem:** 
- Tests should never reference actual AWS resource names
- Using `DrugData-dev` in tests risks accidental interaction with real resources
- Inconsistent table names across test files cause test isolation failures

**Error:**
```
ResourceNotFoundException: Requested resource not found
TableName: 'DrugData-dev' (in test trying to use 'DrugData-test')
```

**Root Cause:**
- DynamoRepository was importing `settings` object directly: `from src.core.config import settings`
- When tests set environment variables and reload settings, the repository still used cached table name
- Repository initialization happened before settings reload took effect

**Solution:**

1. **Use test-specific table name** in ALL test files:
```python
os.environ['DYNAMODB_TABLE_NAME'] = 'DrugData-test'  # Not DrugData-dev
```

2. **Import config module, not settings object**:
```python
# ❌ Wrong - caches settings at import time
from src.core.config import settings
self.table = dynamodb.Table(settings.dynamodb_table_name)

# ✅ Correct - reads settings at runtime
from src.core import config
self.table = dynamodb.Table(config.settings.dynamodb_table_name)
```

3. **Standardize table names across all test files**:
- `tests/test_dynamo_repository.py`: Use `DrugData-test`
- `tests/test_api_integration.py`: Use `DrugData-test`
- Never use `DrugData-dev` or `DrugData-prod` in tests

**Files Updated:**
- `src/repositories/dynamo_repository.py`: Changed to `from src.core import config`
- `tests/test_dynamo_repository.py`: Uses `DrugData-test`
- `tests/test_api_integration.py`: Uses `DrugData-test`

---

## 10. Upload Status Tracking System

**Feature:** Separate DynamoDB table for tracking CSV upload processing status.

**Architecture:**
- **UploadStatus Table**: Stores upload lifecycle (pending → processing → completed/failed)
- **UUID-based Keys**: S3 keys use format `uploads/{uuid}/filename.csv`
- **Lambda Integration**: CSV processor extracts UUID from S3 key and updates status

**Key Components:**

1. **Domain Model** (`src/models/upload_status.py`):
```python
class UploadStatus:
    upload_id: str  # UUID
    status: str  # pending, processing, completed, failed
    filename: str
    s3_key: str
    created_at: datetime
    total_rows: int
    processed_rows: int
    error_message: Optional[str]
```

2. **Repository** (`src/repositories/upload_status_repository.py`):
- `create()`: Create new status record
- `get_by_id()`: Retrieve status by upload_id
- `update()`: Update specific fields (atomic operation)

3. **API Endpoints**:
- `POST /drugs/upload`: Returns `upload_id` with status "pending"
- `GET /drugs/status/{upload_id}`: Query current processing status

4. **Lambda CSV Processor**:
- Extracts UUID from S3 key using regex: `[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}`
- Updates status: pending → processing → completed/failed
- Tracks row counts and error messages

**DynamoDB Reserved Keywords:**

**Issue:** "status" is a DynamoDB reserved keyword.

**Error:**
```
InvalidUpdateExpression: Attribute name is a reserved keyword; reserved keyword: status
```

**Solution:** Use `ExpressionAttributeNames` in update operations:
```python
update_expression = "SET #status = :status"
expression_names = {"#status": "status"}
expression_values = {":status": "completed"}
```

**Testing Considerations:**

1. **UUID Format**: Tests must use valid hex UUIDs (0-9, a-f, A-F only)
```python
# ❌ Wrong - contains non-hex characters
s3_key = "uploads/test123/file.csv"

# ✅ Correct - valid UUID format
s3_key = "uploads/a1b2c3d4-5678-9abc-def0-123456789012/file.csv"
```

2. **Environment Variables**: Add `UPLOAD_STATUS_TABLE_NAME` to test setup:
```python
os.environ['UPLOAD_STATUS_TABLE_NAME'] = 'UploadStatus-test'
```

3. **Table Creation**: Create UploadStatus table in test fixtures:
```python
dynamodb.create_table(
    TableName='UploadStatus-test',
    KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
    AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
    BillingMode='PAY_PER_REQUEST'
)
```

4. **Dependency Injection**: Clear upload status repository cache:
```python
dependencies.get_upload_status_repository.cache_clear()
```

---

## Testing Best Practices

### Moto Testing
1. Use `@mock_aws` decorator (Moto 5.x+)
2. Create AWS resources in each test
3. Reload settings in test context
4. Use Python 3.12.x
5. Clear dependency injection cache between tests

### Test Coverage
- Services: 100%
- Repositories: 93%+
- Models: 95%+
- Total: ~94% (comprehensive coverage)

### Test Structure
- **Unit Tests**: Services, repositories, models (66 tests)
- **Integration Tests**: API endpoints with mocked AWS (8 tests)
- **Lambda Tests**: CSV processor with S3/DynamoDB mocking (8 tests)
- **Total**: 74 tests, all passing
