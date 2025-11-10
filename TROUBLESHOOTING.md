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


## 11. DynamoDB Secondary Indexes: GSI vs LSI

### Problem
Choosing between Global Secondary Index (GSI) and Local Secondary Index (LSI) for query optimization and pagination.

### Context
When implementing pagination for the `/v1/api/drugs` endpoint, we needed to query all drugs sorted by upload timestamp (newest first). This required understanding the differences between GSI and LSI to make the right architectural decision.

### Key Differences

| Feature | LSI (Local Secondary Index) | GSI (Global Secondary Index) |
|---------|----------------------------|------------------------------|
| **When to create** | Table creation ONLY ❌ | Anytime (before or after) ✅ |
| **Partition key** | Same as base table | Different (new partition key) |
| **Sort key** | Different from base table | Different (new sort key) |
| **Query scope** | Within single partition | Across all partitions |
| **Use case** | Alternative sort order for same partition | New access pattern across table |
| **Consistency** | Strong or eventual | Eventual only |
| **Size limit** | 10GB per partition | No limit |
| **Max indexes** | 5 per table | 20 per table |
| **Cost** | Included in table cost | Extra storage + RCU/WCU |

### Our Use Case: Pagination with Recent Uploads First

**Requirement**: Get all drugs sorted by upload_timestamp (newest first) with efficient pagination.

**Why LSI Won't Work:**
```python
# LSI can only query within ONE partition
# Example: Get all versions of "Aspirin" sorted by efficacy
table.query(
    KeyConditionExpression='PK = :pk',  # Must specify partition key
    ExpressionAttributeValues={':pk': 'DRUG#Aspirin'},
    IndexName='EfficacyLSI'
)
# ❌ Cannot query across all drugs - only one drug at a time
# ❌ Would require N queries for N different drugs
```

**Why GSI Works:**
```python
# GSI creates new partition key for ALL records
# All drugs share GSI1PK = "ALL_DRUGS"
table.query(
    IndexName='UploadTimestampIndex',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={':pk': 'ALL_DRUGS'},
    ScanIndexForward=False,  # Newest first
    Limit=100
)
# ✅ Queries ALL drugs across all partitions, sorted by timestamp
# ✅ Single efficient query operation
```

### Solution: Implement GSI

**1. Table Structure:**
```
Base Table:
  PK: DRUG#{drug_name}
  SK: METADATA#{timestamp}

GSI (UploadTimestampIndex):
  GSI1PK: "ALL_DRUGS" (same for all records)
  upload_timestamp: ISO timestamp (sort key)
```

**2. CloudFormation (template.yaml):**
```yaml
DrugDataTable:
  Type: AWS::DynamoDB::Table
  Properties:
    AttributeDefinitions:
      - AttributeName: PK
        AttributeType: S
      - AttributeName: SK
        AttributeType: S
      - AttributeName: GSI1PK
        AttributeType: S
      - AttributeName: upload_timestamp
        AttributeType: S
    KeySchema:
      - AttributeName: PK
        KeyType: HASH
      - AttributeName: SK
        KeyType: RANGE
    GlobalSecondaryIndexes:
      - IndexName: UploadTimestampIndex
        KeySchema:
          - AttributeName: GSI1PK
            KeyType: HASH
          - AttributeName: upload_timestamp
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
```

**3. Code Changes:**
```python
# When saving drugs, add GSI1PK
item = {
    'PK': self._create_pk(drug.drug_name),
    'SK': self._create_sk(drug.upload_timestamp),
    'GSI1PK': 'ALL_DRUGS',  # Add this for GSI
    'drug_name': drug.drug_name,
    'target': drug.target,
    'efficacy': Decimal(str(drug.efficacy)),
    'upload_timestamp': drug.upload_timestamp.isoformat(),
    's3_key': drug.s3_key
}
```

**4. Query with Pagination:**
```python
def find_all_paginated(self, limit: int = 100, last_key: str = None):
    query_kwargs = {
        'IndexName': 'UploadTimestampIndex',
        'KeyConditionExpression': 'GSI1PK = :pk',
        'ExpressionAttributeValues': {':pk': 'ALL_DRUGS'},
        'Limit': limit,
        'ScanIndexForward': False  # Descending (newest first)
    }
    
    if last_key:
        query_kwargs['ExclusiveStartKey'] = {
            'GSI1PK': 'ALL_DRUGS',
            'upload_timestamp': last_key,
            'PK': 'PLACEHOLDER',
            'SK': 'PLACEHOLDER'
        }
    
    response = self.table.query(**query_kwargs)
    return response['Items'], response.get('LastEvaluatedKey')
```

### Adding GSI to Existing Table

**Process:**
1. Update `template.yaml` with GSI definition
2. Deploy: `sam build && sam deploy`
3. DynamoDB automatically creates GSI (status: CREATING → ACTIVE)
4. Backfill existing records with `GSI1PK = 'ALL_DRUGS'`
5. New records automatically include GSI1PK

**Backfill Script:**
```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('DrugData-dev')

response = table.scan()
with table.batch_writer() as batch:
    for item in response['Items']:
        item['GSI1PK'] = 'ALL_DRUGS'
        batch.put_item(Item=item)
```

**Check GSI Status:**
```bash
aws dynamodb describe-table --table-name DrugData-dev \
  --query 'Table.GlobalSecondaryIndexes[0].IndexStatus'
# Output: CREATING → ACTIVE (5-30 minutes)
```

### Performance Comparison

**Without GSI (Scan):**
- Operation: `table.scan()`
- Reads: ALL items in table (10,000 items)
- Cost: ~10,000 RCUs
- Speed: Slow, degrades with table size
- Order: Random/unordered

**With GSI (Query):**
- Operation: `table.query(IndexName='UploadTimestampIndex')`
- Reads: Only requested items (100 items)
- Cost: ~100 RCUs (100x cheaper)
- Speed: Fast, consistent performance
- Order: Sorted by timestamp (newest first)

### Decision Matrix

**Use LSI when:**
- ✅ You need alternative sort order within same partition
- ✅ You need strong consistency
- ✅ Table doesn't exist yet (can create at table creation)
- ✅ Example: "Get all versions of Aspirin sorted by efficacy"

**Use GSI when:**
- ✅ You need to query across all partitions
- ✅ You need new access pattern (different partition key)
- ✅ Table already exists (can add anytime)
- ✅ Example: "Get all drugs sorted by upload time" ← Our use case

### References
- [AWS DynamoDB Secondary Indexes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/SecondaryIndexes.html)
- [GSI Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes-general.html)


---

## 12. DynamoDB Pagination: Cursor-based vs Offset-based

### Problem
Implementing pagination for the `/v1/api/drugs` endpoint to handle large datasets efficiently.

### Context
When designing pagination, there are two common approaches: offset-based (SQL-style) and cursor-based (token-style). Understanding which approach works with DynamoDB is critical for performance and cost optimization.

### Why Offset-based Pagination Doesn't Work with DynamoDB

**Offset-based (SQL-style):**
```
GET /drugs?limit=10&offset=20
```

**Problems:**
- ❌ DynamoDB has no native "OFFSET" operation
- ❌ Must scan through ALL items to skip offset (reads 20 items to skip them)
- ❌ Extremely expensive: offset=1000 means reading 1000 items just to skip them
- ❌ Slow: Performance degrades linearly with offset size
- ❌ Inconsistent: Results change if items are added/deleted between requests

**Example Cost:**
```python
# User requests page 10 (offset=900, limit=100)
# DynamoDB must:
# 1. Read items 1-900 (900 RCUs) ← Wasted reads
# 2. Discard items 1-900
# 3. Read items 901-1000 (100 RCUs)
# Total: 1000 RCUs to return 100 items!
```

### Cursor-based Pagination (DynamoDB Native)

**How it works:**
1. Client requests first page with `limit` parameter
2. DynamoDB returns items + `LastEvaluatedKey` (cursor)
3. Client requests next page using cursor as `ExclusiveStartKey`
4. DynamoDB continues from exact position (no scanning)

**API Design:**

**Request Page 1:**
```
GET /v1/api/drugs?limit=50
```

**Response Page 1:**
```json
{
  "drugs": [
    {"drug_name": "Aspirin", "target": "COX-2", "efficacy": 85.5},
    ...49 more items...
  ],
  "count": 50,
  "next_token": "eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTA6MzA6MDAifQ=="
}
```

**Request Page 2:**
```
GET /v1/api/drugs?limit=50&next_token=eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTA6MzA6MDAifQ==
```

**Response Page 2:**
```json
{
  "drugs": [...50 more items...],
  "count": 50,
  "next_token": "eyJ..." // or null if last page
}
```

### How Pagination Tokens are Generated

**1. DynamoDB Returns LastEvaluatedKey:**
```python
response = table.query(
    IndexName='DrugCategoryIndex',
    KeyConditionExpression='drug_category = :cat',
    ExpressionAttributeValues={':cat': 'ALL'},
    Limit=50
)

# DynamoDB returns:
{
    'Items': [...],
    'LastEvaluatedKey': {
        'drug_category': 'ALL',
        'upload_timestamp': '2024-01-15T10:30:00',
        'PK': 'DRUG#Aspirin',
        'SK': 'METADATA#2024-01-15T10:30:00'
    }
}
```

**2. Encode LastEvaluatedKey as Token:**
```python
import json
import base64

def encode_pagination_token(last_key: dict) -> str:
    """Convert DynamoDB LastEvaluatedKey to base64 token."""
    json_str = json.dumps(last_key)
    token = base64.b64encode(json_str.encode()).decode()
    return token

# Example:
last_key = {
    'drug_category': 'ALL',
    'upload_timestamp': '2024-01-15T10:30:00',
    'PK': 'DRUG#Aspirin',
    'SK': 'METADATA#2024-01-15T10:30:00'
}
token = encode_pagination_token(last_key)
# Result: "eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTA6MzA6MDAiLCJQSyI6IkRSVUcjQXNwaXJpbiIsIlNLIjoiTUVUQURBVEEjMjAyNC0wMS0xNVQxMDozMDowMCJ9"
```

**3. Decode Token for Next Request:**
```python
def decode_pagination_token(token: str) -> dict:
    """Convert base64 token back to DynamoDB key."""
    json_str = base64.b64decode(token.encode()).decode()
    last_key = json.loads(json_str)
    return last_key

# Use in query:
token = request.query_params.get('next_token')
if token:
    last_key = decode_pagination_token(token)
    response = table.query(
        IndexName='DrugCategoryIndex',
        KeyConditionExpression='drug_category = :cat',
        ExpressionAttributeValues={':cat': 'ALL'},
        Limit=50,
        ExclusiveStartKey=last_key  # Start from this key
    )
```

**4. Token Contents (Decoded Example):**
```json
{
  "drug_category": "ALL",
  "upload_timestamp": "2024-01-15T10:30:00",
  "PK": "DRUG#Aspirin",
  "SK": "METADATA#2024-01-15T10:30:00"
}
```

**Why Base64 Encoding?**
- ✅ URL-safe (no special characters)
- ✅ Compact representation
- ✅ Hides internal key structure from clients
- ✅ Standard practice (AWS, Stripe, GitHub use this)

### Implementation Details

**Repository Method:**
```python
from typing import List, Optional, Tuple
import json
import base64

class DynamoRepository:
    def find_all_paginated(
        self, 
        limit: int = 100, 
        next_token: Optional[str] = None
    ) -> Tuple[List[Drug], Optional[str]]:
        """
        Query all drugs with pagination using GSI.
        
        Args:
            limit: Max items to return (default 100, max 1000)
            next_token: Base64-encoded pagination token
            
        Returns:
            Tuple of (drugs list, next_token or None)
        """
        query_kwargs = {
            'IndexName': 'DrugCategoryIndex',
            'KeyConditionExpression': 'drug_category = :cat',
            'ExpressionAttributeValues': {':cat': 'ALL'},
            'Limit': min(limit, 1000),  # Cap at 1000
            'ScanIndexForward': False  # Newest first
        }
        
        # Decode token if provided
        if next_token:
            try:
                last_key = json.loads(base64.b64decode(next_token))
                query_kwargs['ExclusiveStartKey'] = last_key
            except Exception:
                raise ValidationException("Invalid pagination token")
        
        response = self.table.query(**query_kwargs)
        drugs = [self._item_to_drug(item) for item in response['Items']]
        
        # Encode next token if more results exist
        next_token = None
        if 'LastEvaluatedKey' in response:
            next_token = base64.b64encode(
                json.dumps(response['LastEvaluatedKey']).encode()
            ).decode()
        
        return drugs, next_token
```

**API Endpoint:**
```python
from fastapi import Query

@router.get("/drugs")
def get_all_drugs(
    limit: int = Query(default=100, ge=1, le=1000),
    next_token: Optional[str] = Query(default=None)
):
    drugs, next_token = drug_service.get_all_drugs_paginated(limit, next_token)
    return {
        "drugs": drugs,
        "count": len(drugs),
        "next_token": next_token
    }
```

### Configuration

**Recommended Settings:**
```python
# config.py
class Settings(BaseSettings):
    pagination_default_limit: int = 100
    pagination_max_limit: int = 1000
```

**Rationale:**
- Default 100: Good balance between performance and UX
- Max 1000: DynamoDB query limit is 1MB (typically 1000-5000 items)
- Prevents abuse (client requesting limit=1000000)

### Using Pagination in Postman

**Step 1: Get First Page**
```
GET http://localhost:8000/v1/api/drugs?limit=50
```

**Step 2: Copy next_token from Response**
```json
{
  "drugs": [...],
  "count": 50,
  "next_token": "eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTA6MzA6MDAifQ=="
}
```

**Step 3: Request Next Page**
```
GET http://localhost:8000/v1/api/drugs?limit=50&next_token=eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTA6MzA6MDAifQ==
```

**Step 4: Continue Until next_token is null**
```json
{
  "drugs": [...],
  "count": 25,
  "next_token": null  // Last page
}
```

### Performance Comparison

| Approach | Operation | Items Read | Cost (RCUs) | Speed |
|----------|-----------|------------|-------------|-------|
| **Offset-based** | Scan + Skip | offset + limit | 1000+ | Slow, degrades |
| **Cursor-based** | Query from key | limit only | 100 | Fast, consistent |

**Example: Get page 10 (items 901-1000)**
- Offset-based: Read 1000 items, return 100 → 1000 RCUs
- Cursor-based: Read 100 items, return 100 → 100 RCUs
- **Savings: 90% cost reduction**

### Industry Standards

Cursor-based pagination is used by:
- ✅ AWS APIs (S3, DynamoDB, CloudWatch)
- ✅ Stripe API
- ✅ GitHub API
- ✅ Twitter API
- ✅ Facebook Graph API

### Limitations

**Cannot jump to arbitrary page:**
```
# ❌ Not possible with cursor pagination
GET /drugs?page=5
```
- Must traverse pages sequentially (1 → 2 → 3 → 4 → 5)
- Trade-off: Performance and cost vs. random access

**Workaround for "Jump to Page N":**
- Cache tokens for pages 1-10 in client
- Provide "First, Previous, Next, Last" navigation
- Most users only view first few pages anyway

### Best Practices

1. **Always return next_token** (even if null) for consistent API contract
2. **Validate token format** to prevent injection attacks
3. **Set reasonable limits** (default 100, max 1000)
4. **Document token format** as opaque (clients shouldn't decode)
5. **Handle expired tokens** gracefully (tokens may become invalid if data changes)
6. **Use HTTPS** to protect tokens in transit

### References
- [DynamoDB Pagination](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.Pagination.html)
- [API Pagination Best Practices](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Filtering-Sorting-and-Pagination/)
- [Stripe API Pagination](https://stripe.com/docs/api/pagination)

---

## 13. HTTP API Gateway: Per-Route Throttling Limitation

### Issue

Attempting to configure per-route throttling in HTTP API Gateway (v2) causes deployment failure.

**Error:**
```
unable to find route by key POST /v1/api/drugs/upload
```

**Root Cause:**
HTTP API Gateway (v2) has limited support for `RouteSettings` compared to REST API Gateway (v1).

### Problem Configuration

```yaml
# This FAILS with HTTP API
DrugAnalyticsApi:
  Type: AWS::Serverless::HttpApi
  Properties:
    DefaultRouteSettings:
      ThrottlingBurstLimit: 100
      ThrottlingRateLimit: 50
    RouteSettings:  # ❌ Not supported
      'POST /v1/api/drugs/upload':
        ThrottlingBurstLimit: 10
        ThrottlingRateLimit: 5
```

### Solution: Use Global Throttling Only

```yaml
# This WORKS with HTTP API
DrugAnalyticsApi:
  Type: AWS::Serverless::HttpApi
  Properties:
    DefaultRouteSettings:
      ThrottlingBurstLimit: 100
      ThrottlingRateLimit: 50
    # Remove RouteSettings section
```

**Result:**
- ✅ All endpoints share same throttling limits (100 burst, 50/sec)
- ✅ Deployment succeeds
- ✅ 70% cheaper than REST API

### HTTP API vs REST API Comparison

| Feature | HTTP API (v2) | REST API (v1) |
|---------|---------------|---------------|
| **Per-route throttling** | ❌ Not supported | ✅ Supported |
| **Global throttling** | ✅ Supported | ✅ Supported |
| **Cost** | $1.00/million | $3.50/million |
| **Performance** | Faster (~50ms) | Slower (~100ms) |
| **API Keys** | ❌ Not supported | ✅ Supported |
| **Usage Plans** | ❌ Not supported | ✅ Supported |

### Alternative: Switch to REST API

If per-route throttling is required:

```yaml
DrugAnalyticsApi:
  Type: AWS::Serverless::Api  # Changed from HttpApi
  Properties:
    StageName: !Ref Environment
    Cors:
      AllowOrigin: "'*'"
      AllowHeaders: "'*'"
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
    MethodSettings:
      - ResourcePath: "/*"
        HttpMethod: "*"
        ThrottlingBurstLimit: 100
        ThrottlingRateLimit: 50
      - ResourcePath: "/v1/api/drugs/upload"
        HttpMethod: "POST"
        ThrottlingBurstLimit: 10
        ThrottlingRateLimit: 5

DrugApiFunction:
  Events:
    ApiEvent:
      Type: Api  # Changed from HttpApi
      Properties:
        RestApiId: !Ref DrugAnalyticsApi
        Path: /{proxy+}
        Method: ANY
```

**Trade-offs:**
- ✅ Per-route throttling works
- ❌ 3.5x more expensive
- ❌ Slower performance
- ❌ More complex configuration

### Recommended Approach

**Use HTTP API with global throttling + application-level protections:**

1. **Global rate limiting:** 100 burst, 50/sec (API Gateway)
2. **File size limit:** 10MB (FastAPI validation)
3. **Row count limit:** 10,000 rows (FastAPI validation)
4. **File type validation:** CSV only (FastAPI validation)

**Why this works:**
- Upload endpoint already has strong protections (file size, row count, type)
- Global throttling prevents API abuse
- 70% cost savings vs REST API
- Simpler configuration

### Decision Matrix

**Use HTTP API (current approach) when:**
- ✅ Cost is important
- ✅ Performance matters
- ✅ Application-level validation is sufficient
- ✅ Don't need API Keys/Usage Plans

**Use REST API when:**
- ✅ Need per-route throttling
- ✅ Need API Keys for client tracking
- ✅ Need request/response transformation
- ✅ Enterprise compliance requires it

### References
- [HTTP API vs REST API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)
- [HTTP API Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html)
- [REST API Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)

---

## 14. CSV Processing Failure Recovery

### Problem

When CSV processor Lambda crashes after successful S3 upload, the S3 event is lost and files remain unprocessed. Users must re-upload files after bugs are fixed.

**Current Behavior:**
```
1. User uploads file.csv to S3 ✅
2. S3 triggers Lambda ✅
3. Lambda crashes (bug, memory, timeout) ❌
4. S3 event is lost forever ❌
5. File sits in S3, status = "failed" ❌
6. Fix bug and redeploy ✅
7. Lambda does NOT auto-retry ❌
8. User must re-upload file ❌
```

### Solutions

#### Option 1: SQS Dead Letter Queue (DLQ) ⭐ RECOMMENDED

Capture failed Lambda executions for manual replay after fixing bugs.

**Implementation:**
```yaml
# Add to template.yaml
CsvProcessorDLQ:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub 'csv-processor-dlq-${Environment}'
    MessageRetentionPeriod: 1209600  # 14 days
    Tags:
      - Key: Environment
        Value: !Ref Environment

CsvProcessorFunction:
  Type: AWS::Serverless::Function
  Properties:
    # ... existing properties ...
    DeadLetterQueue:
      Type: SQS
      TargetArn: !GetAtt CsvProcessorDLQ.Arn
```

**How it works:**
1. Lambda crashes → Event sent to DLQ
2. Fix bug and redeploy
3. Manually replay events from DLQ
4. Files get processed without re-upload

**Replay failed events:**
```bash
# Get messages from DLQ
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/<account>/csv-processor-dlq-dev \
  --max-number-of-messages 10

# Invoke Lambda with failed event
aws lambda invoke \
  --function-name csv-processor-dev \
  --payload file://failed-event.json \
  response.json

# Delete message after successful processing
aws sqs delete-message \
  --queue-url <queue-url> \
  --receipt-handle <receipt-handle>
```

**Pros:**
- ✅ No lost events
- ✅ Can retry after fixing bugs
- ✅ Audit trail of failures
- ✅ Low cost ($0.40 per million requests)

**Cons:**
- ❌ Manual replay needed
- ❌ Slightly more complex setup

#### Option 2: S3 → SQS → Lambda Architecture

Use SQS as buffer between S3 and Lambda for automatic retries.

**Implementation:**
```yaml
CsvProcessingQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub 'csv-processing-queue-${Environment}'
    VisibilityTimeout: 360  # 6 minutes (Lambda timeout + buffer)
    RedrivePolicy:
      deadLetterTargetArn: !GetAtt CsvProcessorDLQ.Arn
      maxReceiveCount: 5  # Retry 5 times before DLQ

CsvProcessorFunction:
  Events:
    SQSEvent:
      Type: SQS
      Properties:
        Queue: !GetAtt CsvProcessingQueue.Arn
        BatchSize: 1
```

**How it works:**
1. S3 → SQS queue → Lambda
2. Lambda crashes → Message stays in queue
3. Lambda auto-retries (up to 5 times)
4. After 5 failures → Message goes to DLQ
5. Fix bug, manually replay DLQ

**Pros:**
- ✅ Automatic retries (5 attempts)
- ✅ No lost events
- ✅ Better for high volume
- ✅ Decouples S3 from Lambda

**Cons:**
- ❌ More infrastructure (SQS queue)
- ❌ Slightly higher latency

#### Option 3: Manual Reprocessing Endpoint

Create admin API endpoint to reprocess failed uploads.

**Implementation:**
```python
# Add to FastAPI routes
@router.post("/admin/reprocess/{upload_id}")
async def reprocess_upload(upload_id: str):
    """Reprocess a failed upload without re-uploading file."""
    # 1. Get upload status from DynamoDB
    status = await upload_status_repo.get_status(upload_id)
    
    if status["status"] != "failed":
        raise HTTPException(400, "Only failed uploads can be reprocessed")
    
    # 2. Get S3 file location
    s3_key = status["s3_key"]
    
    # 3. Manually invoke CSV processor Lambda
    lambda_client.invoke(
        FunctionName="csv-processor-dev",
        InvocationType="Event",
        Payload=json.dumps({
            "Records": [{
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": s3_key}
                }
            }]
        })
    )
    
    return {"message": "Reprocessing initiated", "upload_id": upload_id}
```

**Usage:**
```bash
# After fixing bug and redeploying
curl -X POST https://api-url/v1/api/admin/reprocess/a1b2c3d4-5678-9abc-def0-123456789012
```

**Pros:**
- ✅ Simple to implement
- ✅ No additional AWS services
- ✅ Full control

**Cons:**
- ❌ Manual intervention required
- ❌ Need to build admin endpoint

#### Option 4: Scheduled Retry Lambda

Periodically scan for failed uploads and retry.

**Implementation:**
```yaml
RetryScheduler:
  Type: AWS::Serverless::Function
  Properties:
    Handler: lambda_functions.retry_scheduler.handler
    Events:
      Schedule:
        Type: Schedule
        Properties:
          Schedule: rate(1 hour)
```

```python
# lambda_functions/retry_scheduler.py
def handler(event, context):
    # 1. Query DynamoDB for status = "failed"
    failed_uploads = upload_status_repo.get_failed_uploads()
    
    # 2. For each failed upload, invoke CSV processor
    for upload in failed_uploads:
        lambda_client.invoke(
            FunctionName="csv-processor-dev",
            InvocationType="Event",
            Payload=json.dumps({...})
        )
```

**Pros:**
- ✅ Automatic retry
- ✅ No manual intervention

**Cons:**
- ❌ Delayed retry (hourly)
- ❌ Additional Lambda costs
- ❌ May retry same failures repeatedly

### Recommended Approach

**Phase 1: Add DLQ (Immediate - 10 min)**
- Capture failed events so they're not lost
- Provides safety net for production

**Phase 2: Add Reprocess Endpoint (Later - 30 min)**
- Allow manual reprocessing without re-upload
- Better user experience

**Phase 3: Consider SQS Architecture (Future)**
- If failure rate is high
- If automatic retry is critical

### Status: PENDING IMPLEMENTATION

This feature is documented but not yet implemented. Priority: Medium

### References
- [Lambda DLQ](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-dlq)
- [SQS as Event Source](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [Lambda Error Handling](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html)

---

## 15. Authentication Architecture: HTTP API Limitations

### Issue

HTTP API Gateway (v2) does not support Lambda Authorizers in the same way as REST API Gateway (v1), making API Gateway-level JWT authentication impractical for proxy-integrated applications.

### Context

When implementing JWT authentication, there are two architectural approaches:
1. **API Gateway-level:** Lambda Authorizer validates tokens before reaching application
2. **Application-level:** FastAPI validates tokens using dependency injection

### Why API Gateway Lambda Authorizer Doesn't Work Well

**Problem 1: HTTP API Authorizer Limitations**

HTTP API supports Lambda Authorizers, but with significant limitations:

```yaml
# HTTP API Authorizer (Limited)
DrugAnalyticsApi:
  Type: AWS::Serverless::HttpApi
  Properties:
    Auth:
      Authorizers:
        JwtAuthorizer:
          AuthorizerType: JWT
          IdentitySource: $request.header.Authorization
          JwtConfiguration:
            Audience:
              - api-audience
            Issuer: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx
      DefaultAuthorizer: JwtAuthorizer
```

**Limitations:**
- ❌ Only supports JWT authorizers (not custom Lambda authorizers for HTTP API)
- ❌ Requires AWS Cognito or external OAuth provider (can't use custom user table)
- ❌ Cannot easily mix public and protected routes with `/{proxy+}` pattern
- ❌ More complex setup and configuration

**Problem 2: Proxy Integration Pattern**

Our application uses `/{proxy+}` routing (monolithic API pattern):

```yaml
DrugApiFunction:
  Events:
    ApiEvent:
      Type: HttpApi
      Properties:
        Path: /{proxy+}  # All routes go to one Lambda
        Method: ANY
```

**Challenges:**
- All routes share same authorization configuration
- Cannot easily exclude `/login` and `/health` from authorization
- Would require complex route definitions to support mixed auth

**Problem 3: Route Definition Complexity**

To support mixed public/protected routes with API Gateway auth:

```yaml
# Would need to define EVERY route explicitly
DrugApiFunction:
  Events:
    # Public routes
    LoginRoute:
      Type: HttpApi
      Properties:
        Path: /v1/api/auth/login
        Method: POST
        Auth:
          Authorizer: NONE
    
    HealthRoute:
      Type: HttpApi
      Properties:
        Path: /v1/api/health
        Method: GET
        Auth:
          Authorizer: NONE
    
    # Protected routes (must define each one)
    UploadRoute:
      Type: HttpApi
      Properties:
        Path: /v1/api/uploads
        Method: POST
        Auth:
          Authorizer: JwtAuthorizer
    
    # ... 10+ more route definitions ...
```

**Problems:**
- ❌ Verbose configuration (10+ route definitions)
- ❌ Loses flexibility of FastAPI routing
- ❌ Must update SAM template for every new endpoint
- ❌ Breaks monolithic API pattern

### Solution: FastAPI-Level Authentication

**Implementation:**

```python
# src/core/auth_dependencies.py
from fastapi import Depends, HTTPException, Header
import jwt

def verify_token(authorization: str = Header(None)) -> str:
    """Validate JWT token and return username."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload["sub"]  # username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# src/api/routes/drug_routes.py
from src.core.auth_dependencies import verify_token

@router.post("/uploads")
def upload_csv(
    file: UploadFile,
    username: str = Depends(verify_token)  # Protected
):
    # Only executes if token is valid
    pass

@router.get("/health")
def health_check():
    # No Depends(verify_token) = public endpoint
    return {"status": "healthy"}
```

**Benefits:**
- ✅ Simple configuration (no SAM template changes)
- ✅ Flexible route protection (add `Depends(verify_token)` per route)
- ✅ Works with custom user table (DynamoDB)
- ✅ Maintains `/{proxy+}` pattern
- ✅ Easy to test (mock dependencies)
- ✅ Full control over authentication logic

### HTTP API vs REST API for Authentication

| Feature | HTTP API + FastAPI Auth | REST API + Lambda Authorizer |
|---------|------------------------|------------------------------|
| **Cost** | $1.00/million | $3.50/million |
| **Performance** | Fast (~50ms) | Slower (~100ms + authorizer) |
| **Flexibility** | High (code-level) | Medium (config-level) |
| **User Storage** | Any (DynamoDB, RDS) | Cognito or custom |
| **Route Config** | Simple (`/{proxy+}`) | Complex (explicit routes) |
| **Testing** | Easy (mock deps) | Complex (mock authorizer) |
| **Maintenance** | Low (code changes) | High (SAM template changes) |

### When to Use Each Approach

**Use FastAPI-Level Auth (Current) when:**
- ✅ Using `/{proxy+}` proxy integration
- ✅ Want flexibility in route protection
- ✅ Using custom user storage (DynamoDB, RDS)
- ✅ Cost optimization is important
- ✅ Monolithic API pattern

**Use API Gateway Lambda Authorizer when:**
- ✅ Microservices architecture (separate Lambdas per route)
- ✅ Need centralized auth across multiple APIs
- ✅ Using AWS Cognito for user management
- ✅ Compliance requires gateway-level auth
- ✅ Want to block unauthorized requests before Lambda (cost savings at scale)

### Architecture Decision

**Chosen:** FastAPI-level JWT authentication

**Rationale:**
1. Application uses `/{proxy+}` pattern (monolithic API)
2. Custom user storage in DynamoDB (not Cognito)
3. Need flexible public/protected route configuration
4. Simpler implementation and testing
5. Lower cost (HTTP API vs REST API)
6. Faster performance (no authorizer Lambda)

**Trade-offs:**
- ❌ Authentication happens inside Lambda (not at gateway)
- ❌ Unauthorized requests still invoke Lambda (minimal cost impact)
- ✅ Full control over authentication logic
- ✅ Easy to extend (password reset, 2FA, etc.)

### Alternative: Microservices Architecture

If switching to microservices (separate Lambda per route):

```yaml
# Separate Lambda functions
UploadFunction:
  Type: AWS::Serverless::Function
  Events:
    UploadApi:
      Type: HttpApi
      Properties:
        Path: /v1/api/uploads
        Method: POST
        Auth:
          Authorizer: JwtAuthorizer

GetDrugsFunction:
  Type: AWS::Serverless::Function
  Events:
    GetDrugsApi:
      Type: HttpApi
      Properties:
        Path: /v1/api/drugs
        Method: GET
        Auth:
          Authorizer: JwtAuthorizer

LoginFunction:
  Type: AWS::Serverless::Function
  Events:
    LoginApi:
      Type: HttpApi
      Properties:
        Path: /v1/api/auth/login
        Method: POST
        Auth:
          Authorizer: NONE  # Public
```

**When to consider:**
- API grows to 20+ endpoints
- Different endpoints have different scaling needs
- Team grows and needs service ownership boundaries
- Need independent deployment of services

**Current recommendation:** Keep monolithic pattern with FastAPI auth until scale requires microservices.

### References
- [HTTP API Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)
- [REST API Lambda Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Monolith vs Microservices](https://martinfowler.com/articles/microservices.html)

---

## 16. Multipart Upload: When and Why

### Question

Should we implement S3 multipart upload for CSV file uploads?

### Current Implementation

**Single Upload (Current):**
```python
@router.post("/drugs/upload")
async def upload_csv(file: UploadFile):
    file_content = await file.read()  # Read entire file
    s3_repository.upload_file(file_content, s3_key)  # Single PUT
```

**Constraints:**
- Max file size: 10MB
- Max row count: 10,000 rows
- API Gateway payload limit: 10MB
- Upload time: 1-3 seconds (typical)

### Decision: NO Multipart Upload Needed

**Reasons:**

1. **File Size Too Small**
   - Current: 10MB max
   - Multipart recommended: 100MB+
   - Multipart required: 5GB+

2. **API Gateway Limitation**
   - HTTP API Gateway max payload: 10MB
   - Already at the limit
   - Can't increase without architecture change

3. **Cost Increase**
   ```
   Single upload:  1 S3 PUT = $0.000005
   Multipart (2 parts): 1 initiate + 2 uploads + 1 complete = $0.000020
   Cost increase: 4x for no benefit
   ```

4. **Complexity Increase**
   - Single upload: 5 lines of code
   - Multipart upload: 50+ lines of code
   - Error handling: Simple vs Complex
   - Testing: Easy vs Difficult

5. **Performance**
   - 10MB uploads complete in 1-3 seconds
   - Rarely fail on modern networks
   - No need for resume capability

### When Multipart Upload IS Needed

| Scenario | File Size | Solution |
|----------|-----------|----------|
| **Large CSV files** | 100MB - 5GB | Multipart + Presigned URLs |
| **Very large files** | 5GB - 5TB | Multipart (required by S3) |
| **Unreliable network** | Any | Multipart with resume |
| **Parallel upload speed** | 100MB+ | Multipart (faster) |

### Future: Supporting Larger Files

If file size limit needs to increase beyond 10MB:

#### Option 1: S3 Presigned URLs (Recommended)

**Architecture Change:**
```
Current: Client → API Gateway → Lambda → S3
New:     Client → S3 directly (presigned URL)
```

**Implementation:**
```python
# Step 1: Generate presigned URL
@router.post("/drugs/upload/presigned")
def get_presigned_url(filename: str, file_size: int):
    upload_id = str(uuid.uuid4())
    s3_key = f"uploads/{upload_id}/{filename}"
    
    # Generate presigned URL for direct S3 upload
    url = s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=3600  # 1 hour
    )
    
    # Create upload status record
    upload_status_repo.create(upload_id, filename, s3_key)
    
    return {
        "upload_id": upload_id,
        "upload_url": url,
        "expires_in": 3600
    }

# Step 2: Client uploads directly to S3 using presigned URL
# (No API Gateway involvement, bypasses 10MB limit)

# Step 3: S3 event triggers Lambda for processing
```

**Benefits:**
- ✅ Bypasses API Gateway 10MB limit
- ✅ Supports files up to 5GB (single upload)
- ✅ Supports files up to 5TB (with multipart)
- ✅ Reduces Lambda execution time (no file proxying)
- ✅ Lower cost (no API Gateway data transfer)

**Drawbacks:**
- ❌ More complex client implementation
- ❌ Two-step process (get URL, then upload)
- ❌ CORS configuration needed on S3

#### Option 2: Multipart Upload with Presigned URLs

**For files > 100MB:**

```python
# Step 1: Initiate multipart upload
@router.post("/drugs/upload/multipart/initiate")
def initiate_multipart(filename: str, file_size: int):
    upload_id = str(uuid.uuid4())
    s3_key = f"uploads/{upload_id}/{filename}"
    
    response = s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=s3_key
    )
    
    return {
        "upload_id": upload_id,
        "s3_upload_id": response['UploadId'],
        "part_size": 5 * 1024 * 1024  # 5MB parts
    }

# Step 2: Generate presigned URLs for each part
@router.post("/drugs/upload/multipart/part-url")
def get_part_url(upload_id: str, s3_upload_id: str, part_number: int):
    s3_key = get_s3_key_from_upload_id(upload_id)
    
    url = s3_client.generate_presigned_url(
        'upload_part',
        Params={
            'Bucket': bucket_name,
            'Key': s3_key,
            'UploadId': s3_upload_id,
            'PartNumber': part_number
        },
        ExpiresIn=3600
    )
    
    return {"part_url": url, "part_number": part_number}

# Step 3: Complete multipart upload
@router.post("/drugs/upload/multipart/complete")
def complete_multipart(upload_id: str, s3_upload_id: str, parts: List[dict]):
    s3_key = get_s3_key_from_upload_id(upload_id)
    
    s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=s3_key,
        UploadId=s3_upload_id,
        MultipartUpload={'Parts': parts}
    )
    
    return {"status": "completed", "upload_id": upload_id}

# Step 4: Abort on failure
@router.post("/drugs/upload/multipart/abort")
def abort_multipart(upload_id: str, s3_upload_id: str):
    s3_key = get_s3_key_from_upload_id(upload_id)
    
    s3_client.abort_multipart_upload(
        Bucket=bucket_name,
        Key=s3_key,
        UploadId=s3_upload_id
    )
    
    return {"status": "aborted"}
```

**Client Implementation:**
```python
import requests
import math

def upload_large_file(file_path: str, api_url: str):
    file_size = os.path.getsize(file_path)
    part_size = 5 * 1024 * 1024  # 5MB
    
    # 1. Initiate multipart upload
    response = requests.post(f"{api_url}/drugs/upload/multipart/initiate", 
        json={"filename": os.path.basename(file_path), "file_size": file_size})
    data = response.json()
    upload_id = data['upload_id']
    s3_upload_id = data['s3_upload_id']
    
    # 2. Upload parts
    parts = []
    with open(file_path, 'rb') as f:
        part_number = 1
        while True:
            chunk = f.read(part_size)
            if not chunk:
                break
            
            # Get presigned URL for this part
            url_response = requests.post(f"{api_url}/drugs/upload/multipart/part-url",
                json={"upload_id": upload_id, "s3_upload_id": s3_upload_id, "part_number": part_number})
            part_url = url_response.json()['part_url']
            
            # Upload part directly to S3
            part_response = requests.put(part_url, data=chunk)
            etag = part_response.headers['ETag']
            
            parts.append({"PartNumber": part_number, "ETag": etag})
            part_number += 1
    
    # 3. Complete multipart upload
    requests.post(f"{api_url}/drugs/upload/multipart/complete",
        json={"upload_id": upload_id, "s3_upload_id": s3_upload_id, "parts": parts})
    
    print(f"Upload completed: {upload_id}")
```

### Cost Comparison

**Current (10MB file, single upload):**
```
1 S3 PUT request = $0.000005
Total: $0.000005
```

**Presigned URL (100MB file, single upload):**
```
1 S3 PUT request = $0.000005
Total: $0.000005 (same cost, no API Gateway)
```

**Multipart (100MB file, 5MB parts = 20 parts):**
```
1 initiate + 20 part uploads + 1 complete = 22 S3 requests
22 × $0.000005 = $0.00011
Total: $0.00011 (22x more expensive)
```

### Recommendation

**Current implementation (single upload via API Gateway) is optimal for:**
- ✅ Files up to 10MB
- ✅ CSV files with up to 10,000 rows
- ✅ Simple, reliable, low-cost

**Upgrade to presigned URLs when:**
- Files need to be 10MB - 100MB
- Want to reduce Lambda execution time
- Want to reduce API Gateway costs

**Upgrade to multipart upload when:**
- Files need to be 100MB+
- Network reliability is a concern
- Need resume capability for failed uploads

### Status: Current Implementation Sufficient

No changes needed unless file size requirements increase beyond 10MB.

### References
- [S3 Multipart Upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [API Gateway Limits](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
