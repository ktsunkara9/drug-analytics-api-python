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
