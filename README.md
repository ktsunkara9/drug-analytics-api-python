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
   - Health Check: http://localhost:8000/v1/api/health

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

## Authentication

### Overview

The API uses JWT (JSON Web Token) authentication. All endpoints except `/v1/api/auth/login` and `/v1/api/health` require authentication.

**Authentication Flow:**
1. Login with username/password → Receive JWT token
2. Include token in `Authorization: Bearer <token>` header for all requests
3. Token expires after 24 hours (configurable)

### Login

**Endpoint:** `POST /v1/api/auth/login`

**Request:**
```bash
curl -X POST http://localhost:8000/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Invalid username or password"
}
```

### Using Authentication Token

Include the token in the `Authorization` header for all protected endpoints:

**cURL:**
```bash
curl http://localhost:8000/v1/api/drugs \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Python:**
```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/v1/api/auth/login",
    json={"username": "alice", "password": "password123"}
)
token = response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/v1/api/drugs",
    headers=headers
)
print(response.json())
```

### Token Expiration

- Tokens expire after 24 hours (default)
- Configurable via `JWT_EXPIRATION_HOURS` environment variable
- Expired tokens return 401 Unauthorized
- Client must login again to get new token

### User Management

**Creating Users:**

Users are stored in DynamoDB `users-{environment}` table. Create users manually:

```python
import boto3
import bcrypt

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('users-dev')

# Hash password
password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Create user
table.put_item(Item={
    'username': 'alice',
    'password_hash': password_hash,
    'role': 'admin'
})
```

**AWS CLI:**
```bash
# Generate password hash (requires Python + bcrypt)
PASSWORD_HASH=$(python -c "import bcrypt; print(bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode())")

# Create user in DynamoDB
aws dynamodb put-item \
  --table-name users-dev \
  --item '{"username": {"S": "alice"}, "password_hash": {"S": "'$PASSWORD_HASH'"}, "role": {"S": "admin"}}'
```

### Security Notes

- **JWT Secret:** Set `JWT_SECRET` environment variable (use AWS Secrets Manager in production)
- **Password Storage:** Passwords are hashed with bcrypt (never stored in plaintext)
- **HTTPS Required:** Always use HTTPS in production to protect tokens in transit
- **Token Storage:** Store tokens securely (e.g., httpOnly cookies, secure storage)
- **Rate Limiting:** Login endpoint is protected by API Gateway throttling (100 burst, 50/sec)

## API Endpoints

> 💡 For complete API documentation with all parameters and responses, see the [Swagger UI](http://localhost:8000/docs)

### Authentication
- `POST /v1/api/auth/login` - Login and receive JWT token (public)

### Upload & Status Tracking (Protected)
- `POST /v1/api/uploads` - Upload CSV file, returns upload_id
- `GET /v1/api/uploads/{upload_id}` - Check upload processing status

### Drug Data (Protected)
- `GET /v1/api/drugs` - Retrieve all drug data
- `GET /v1/api/drugs/{drug_name}` - Retrieve specific drug data

### Health (Public)
- `GET /v1/api/health` - API health check

## API Usage Examples

### 1. Upload CSV File

**cURL:**
```bash
# Get token first
TOKEN=$(curl -X POST http://localhost:8000/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}' | jq -r '.access_token')

# Upload with token
curl -X POST http://localhost:8000/v1/api/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@drugs.csv"
```

**Python:**
```python
import requests

# Login first
login_response = requests.post(
    "http://localhost:8000/v1/api/auth/login",
    json={"username": "alice", "password": "password123"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Upload with authentication
url = "http://localhost:8000/v1/api/uploads"
with open("drugs.csv", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files, headers=headers)
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
curl http://localhost:8000/v1/api/uploads/a1b2c3d4-5678-9abc-def0-123456789012 \
  -H "Authorization: Bearer $TOKEN"
```

**Python:**
```python
import requests

upload_id = "a1b2c3d4-5678-9abc-def0-123456789012"
url = f"http://localhost:8000/v1/api/uploads/{upload_id}"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(url, headers=headers)
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
curl http://localhost:8000/v1/api/drugs \
  -H "Authorization: Bearer $TOKEN"

# Get first 50 drugs
curl "http://localhost:8000/v1/api/drugs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**cURL (Next Page):**
```bash
curl "http://localhost:8000/v1/api/drugs?limit=10&next_token=eyJkcnVnX2NhdGVnb3J5IjoiQUxMIi..." \
  -H "Authorization: Bearer $TOKEN"
```

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/drugs"
headers = {"Authorization": f"Bearer {token}"}

# Get first page
response = requests.get(url, params={"limit": 10}, headers=headers)
data = response.json()
print(f"Retrieved {data['count']} drugs")
print(f"Next token: {data['next_token']}")

# Get next page if available
if data['next_token']:
    response = requests.get(url, params={"limit": 10, "next_token": data['next_token']}, headers=headers)
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
curl http://localhost:8000/v1/api/drugs/Aspirin \
  -H "Authorization: Bearer $TOKEN"
```

**Python:**
```python
import requests

drug_name = "Aspirin"
url = f"http://localhost:8000/v1/api/drugs/{drug_name}"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(url, headers=headers)
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
  "status": "healthy",
  "service": "Drug Analytics API",
  "version": "1.0.0"
}
```

### 6. Paginate Through All Results

**Python:**
```python
import requests

url = "http://localhost:8000/v1/api/drugs"
headers = {"Authorization": f"Bearer {token}"}
all_drugs = []
next_token = None

while True:
    params = {"limit": 100}
    if next_token:
        params["next_token"] = next_token
    
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    
    all_drugs.extend(data["drugs"])
    print(f"Retrieved {data['count']} drugs (Total: {len(all_drugs)})")
    
    next_token = data["next_token"]
    if not next_token:
        break

print(f"Total drugs retrieved: {len(all_drugs)}")
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
- ✅ **Authentication** - JWT-based authentication with bcrypt password hashing

## Security

### Authentication & Authorization

**JWT Authentication:**
- All endpoints (except `/login` and `/health`) require JWT token
- Tokens expire after 24 hours (configurable)
- Passwords hashed with bcrypt (never stored in plaintext)
- Users stored in DynamoDB `users-{environment}` table

**Implementation:**
- FastAPI-level authentication (not API Gateway)
- Chosen because app uses `/{proxy+}` routing pattern
- Allows flexible public/protected route configuration
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#16-authentication-architecture-http-api-limitations) for architecture details

**Security Best Practices:**
- Store `JWT_SECRET` in AWS Secrets Manager (production)
- Always use HTTPS in production
- Implement token refresh for better UX (optional)
- Add rate limiting on login endpoint to prevent brute force

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
- [x] CloudWatch Alarms (CSV Processor duration + errors)
- [x] JWT Authentication with bcrypt password hashing

### Future Enhancements
- [ ] **CSV Processing Failure Recovery** - Add DLQ + reprocess endpoint (see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#14-csv-processing-failure-recovery))
- [ ] **User Management API** - Registration, password reset, role-based access control (RBAC)
- [ ] **Token Refresh** - Refresh tokens for better UX (avoid re-login every 24 hours)
- [ ] **Additional CloudWatch Alarms** - API Lambda errors, API Gateway 5xx errors, DynamoDB throttling
- [ ] **CloudWatch Dashboards** - Operational visibility for API, Lambda, DynamoDB metrics
