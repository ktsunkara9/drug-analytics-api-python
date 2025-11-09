# Drug Analytics API

A cloud-based analytics service for drug discovery data using AWS serverless architecture.

## Architecture

- **FastAPI** - REST API framework
- **AWS Lambda** - Serverless compute (API + CSV processor)
- **API Gateway** - HTTP routing
- **Amazon S3** - CSV file storage
- **DynamoDB** - Drug data storage + Upload status tracking
- **Event-driven processing** - S3 triggers Lambda for async CSV processing

## Setup

### Prerequisites
- Python 3.12+
- AWS CLI configured
- AWS SAM CLI (for deployment)

### Local Development Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd drug-analytics-api-python
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Upgrade pip and install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   # Method 1: Using Python module
   python -m src.main
   
   # Method 2: Using uvicorn with live reload (recommended for development)
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

## AWS Deployment

### Prerequisites
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed
- PowerShell (Windows) or Bash (Linux/Mac)

### Deploy to AWS

1. **Run deployment script**
   ```bash
   # Windows (PowerShell)
   .\deploy.sh dev
   
   # Linux/Mac
   ./deploy.sh dev
   ```

   The script will:
   - Build the SAM application
   - Deploy infrastructure (S3, DynamoDB, Lambda, API Gateway)
   - Configure S3 event trigger for CSV processing

2. **Get API endpoint**
   After deployment, the API Gateway URL will be displayed in the output:
   ```
   https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/
   ```

3. **Access deployed API**
   - API: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/v1/api/`
   - Health Check: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/v1/api/health`
   - Swagger UI: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/docs`

## API Endpoints

> 💡 For complete API documentation with all parameters and responses, see the [Swagger UI](http://localhost:8000/docs)

### Upload & Status Tracking
- `POST /v1/api/drugs/upload` - Upload CSV file, returns upload_id
- `GET /v1/api/drugs/status/{upload_id}` - Check upload processing status

### Drug Data
- `GET /v1/api/drugs` - Retrieve all drug data
- `GET /v1/api/drugs/{drug_name}` - Retrieve specific drug data

### Health
- `GET /v1/api/health` - API health check

## API Usage Examples

### 1. Upload CSV File

**cURL:**
```bash
curl -X POST http://localhost:8000/v1/api/drugs/upload \
  -F "file=@drugs.csv"
```

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/drugs/upload"
with open("drugs.csv", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    print(response.json())
```

**Response (202 Accepted):**
```json
{
  "upload_id": "a1b2c3d4-5678-9abc-def0-123456789012",
  "status": "pending",
  "message": "File uploaded successfully. Processing in progress.",
  "s3_location": "s3://bucket/uploads/a1b2c3d4-5678-9abc-def0-123456789012/drugs.csv"
}
```

### 2. Check Upload Status

**cURL:**
```bash
curl http://localhost:8000/v1/api/drugs/status/a1b2c3d4-5678-9abc-def0-123456789012
```

**Python:**
```python
import requests

upload_id = "a1b2c3d4-5678-9abc-def0-123456789012"
url = f"http://localhost:8000/v1/api/drugs/status/{upload_id}"
response = requests.get(url)
print(response.json())
```

**Response (200 OK):**
```json
{
  "upload_id": "a1b2c3d4-5678-9abc-def0-123456789012",
  "status": "completed",
  "filename": "drugs.csv",
  "total_rows": 100,
  "processed_rows": 100,
  "created_at": "2024-01-15T10:30:00"
}
```

**Status Values:**
- `pending` - File uploaded, awaiting processing
- `processing` - Lambda actively processing CSV
- `completed` - Successfully processed
- `failed` - Processing failed (includes error_message)

### 3. Get All Drugs (with Pagination)

**Query Parameters:**
- `limit` (optional): Number of items per page (default: 10, max: 1000)
- `next_token` (optional): Pagination token from previous response

**cURL (First Page):**
```bash
# Get first 10 drugs (default)
curl http://localhost:8000/v1/api/drugs

# Get first 50 drugs
curl "http://localhost:8000/v1/api/drugs?limit=10"
```

**cURL (Next Page):**
```bash
curl "http://localhost:8000/v1/api/drugs?limit=10&next_token=eyJkcnVnX2NhdGVnb3J5IjoiQUxMIi..."
```

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/drugs"

# Get first page
response = requests.get(url, params={"limit": 10})
data = response.json()
print(f"Retrieved {data['count']} drugs")
print(f"Next token: {data['next_token']}")

# Get next page if available
if data['next_token']:
    response = requests.get(url, params={"limit": 10, "next_token": data['next_token']})
    next_page = response.json()
    print(f"Next page: {next_page['count']} drugs")
```

**Response (200 OK):**
```json
{
  "drugs": [
    {
      "drug_name": "Aspirin",
      "target": "COX-2",
      "efficacy": 85.5,
      "upload_timestamp": "2024-01-15T10:30:00"
    },
    {
      "drug_name": "Ibuprofen",
      "target": "COX-1",
      "efficacy": 90.0,
      "upload_timestamp": "2024-01-15T11:00:00"
    }
  ],
  "count": 2,
  "next_token": "eyJkcnVnX2NhdGVnb3J5IjoiQUxMIiwidXBsb2FkX3RpbWVzdGFtcCI6IjIwMjQtMDEtMTVUMTE6MDA6MDAifQ=="
}
```

**Response (Last Page):**
```json
{
  "drugs": [...],
  "count": 5,
  "next_token": null
}
```

**Pagination Notes:**
- Results are sorted by upload timestamp (newest first)
- `next_token` is `null` when there are no more results
- Token is opaque - do not decode or modify it
- Tokens may expire if data changes significantly

### 4. Get Specific Drug

**cURL:**
```bash
curl http://localhost:8000/v1/api/drugs/Aspirin
```

**Python:**
```python
import requests

drug_name = "Aspirin"
url = f"http://localhost:8000/v1/api/drugs/{drug_name}"
response = requests.get(url)
print(response.json())
```

**Response (200 OK):**
```json
{
  "drug_name": "Aspirin",
  "target": "COX-2",
  "efficacy": 85.5
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Drug 'Unknown' not found"
}
```

### 5. Health Check

**cURL:**
```bash
curl http://localhost:8000/v1/api/health
```

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/health"
response = requests.get(url)
print(response.json())
```

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

### 6. Paginate Through All Results

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/drugs"
all_drugs = []
next_token = None

while True:
    params = {"limit": 100}
    if next_token:
        params["next_token"] = next_token
    
    response = requests.get(url, params=params)
    data = response.json()
    
    all_drugs.extend(data["drugs"])
    print(f"Retrieved {data['count']} drugs (Total: {len(all_drugs)})")
    
    next_token = data["next_token"]
    if not next_token:
        break

print(f"Total drugs retrieved: {len(all_drugs)}")
```

### Complete Workflow Example

**Python:**
```python
import requests
import time

BASE_URL = "http://localhost:8000/v1/api"

# 1. Upload CSV
with open("drugs.csv", "rb") as f:
    response = requests.post(f"{BASE_URL}/drugs/upload", files={"file": f})
    upload_id = response.json()["upload_id"]
    print(f"Upload ID: {upload_id}")

# 2. Poll status until completed
while True:
    response = requests.get(f"{BASE_URL}/drugs/status/{upload_id}")
    status_data = response.json()
    status = status_data["status"]
    print(f"Status: {status}")
    
    if status in ["completed", "failed"]:
        break
    time.sleep(2)

# 3. Query processed data with pagination
if status == "completed":
    response = requests.get(f"{BASE_URL}/drugs", params={"limit": 100})
    data = response.json()
    print(f"Retrieved {data['count']} drugs")
    print(f"More results available: {data['next_token'] is not None}")
```

## CSV Format

### Required Fields
- `drug_name` (string) - Name of the drug (cannot be empty)
- `target` (string) - Target protein or pathway (cannot be empty)
- `efficacy` (float, 0-100) - Efficacy percentage (must be between 0 and 100)

### Validation Rules
- **File Type**: Only `.csv` files are accepted
- **File Size**: Maximum 10MB (configurable via `MAX_FILE_SIZE_MB` env var)
- **Row Count**: Maximum 10,000 rows (configurable via `MAX_CSV_ROWS` env var)
- **File Encoding**: Must be UTF-8 encoded
- **Required Columns**: All three columns (drug_name, target, efficacy) must be present
- **Empty Values**: None of the fields can be empty or contain only whitespace
- **Efficacy Range**: Must be a valid number between 0 and 100 (inclusive)
- **Empty File**: CSV must contain at least one data row (excluding header)

### Example CSV
```csv
drug_name,target,efficacy
Aspirin,COX-2,85.5
Ibuprofen,COX-1,90.0
Paracetamol,COX-3,75.0
```

### Error Responses

**File Too Large (413 Request Entity Too Large):**
```json
{
  "detail": "File size (15.50MB) exceeds maximum allowed size of 10MB"
}
```

**Too Many Rows (400 Bad Request):**
```json
{
  "detail": "CSV exceeds maximum allowed rows of 10000"
}
```

**Invalid File Type (400 Bad Request):**
```json
{
  "detail": "Only CSV files are allowed"
}
```

**Missing Columns (400 Bad Request):**
```json
{
  "detail": "Missing required columns: efficacy"
}
```

**Invalid Data (400 Bad Request):**
```json
{
  "detail": "Row 3: efficacy must be between 0 and 100, got: 150"
}
```

**Empty Fields (400 Bad Request):**
```json
{
  "detail": "Row 2: drug_name cannot be empty"
}
```

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_file_service.py -v

# Run specific test
pytest tests/test_file_service.py::TestFileService::test_parse_csv_success -v
```

### Code Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# View HTML report (opens in browser)
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```


## Features

- ✅ **Async CSV Processing** - Upload returns immediately, processing happens in background
- ✅ **Status Tracking** - Real-time status updates via API
- ✅ **Event-Driven** - S3 triggers Lambda automatically
- ✅ **Scalable** - Serverless architecture scales automatically
- ✅ **File Validation** - File size (10MB) and row count (10,000) limits
- ✅ **Data Validation** - Comprehensive CSV structure and data validation
- ✅ **Pagination** - Efficient cursor-based pagination for large datasets (default 10, max 1000 per page)
- ✅ **Rate Limiting** - API Gateway throttling prevents abuse and controls costs

## Security

### Rate Limiting

API Gateway enforces rate limiting to prevent abuse, protect backend services, and control costs.

**Throttling Limits (All Endpoints):**
- Burst Capacity: 100 requests
- Steady-State Rate: 50 requests/second

**How It Works:**
- API Gateway uses token bucket algorithm
- Throttled requests return 429 before reaching Lambda (no Lambda cost)
- Limits apply globally across all endpoints

**Additional Upload Protection:**
- File size limit: 10MB
- Row count limit: 10,000 rows
- File type validation: CSV only

**Rate Limit Response (429 Too Many Requests):**
```json
{
  "message": "Too Many Requests"
}
```

**Best Practices:**
- Implement exponential backoff in client code
- Cache GET responses when possible
- Use pagination to reduce request frequency
- Monitor CloudWatch for throttling events

## Troubleshooting

For known issues and workarounds, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Key issues covered:
- Python 3.13 compatibility with Moto
- SAM circular dependency with S3/Lambda
- Settings import patterns for testing
- API Gateway routing
- DynamoDB type conversions
- Upload status race condition fix

## Project Status

### Completed ✅
- [x] FastAPI REST API with async processing
- [x] AWS Lambda functions (API + CSV processor)
- [x] DynamoDB tables (Drug data + Upload status)
- [x] S3 event-driven processing
- [x] Upload status tracking system
- [x] File size and row count validation
- [x] Comprehensive test suite (94% coverage)
- [x] AWS deployment automation
- [x] Production deployment and testing
- [x] Rate limiting (API Gateway throttling)
- [x] S3 bucket encryption (SSE-S3 AES-256)

### Future Enhancements
- [ ] **CSV Processing Failure Recovery** - Add DLQ + reprocess endpoint (see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#14-csv-processing-failure-recovery))
- [ ] **Authentication & Authorization** - API Keys (requires REST API) or Lambda Authorizer + JWT
- [ ] **CloudWatch Alarms** - Lambda errors, API 5xx errors, DynamoDB throttling, cost monitoring
- [ ] **CloudWatch Dashboards** - Operational visibility for API, Lambda, DynamoDB metrics

=======
## Testing

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_file_service.py -v

# Run specific test
pytest tests/test_file_service.py::TestFileService::test_parse_csv_success -v
```

### Code Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# View HTML report (opens in browser)
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```


## Troubleshooting

For known issues and workarounds, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
