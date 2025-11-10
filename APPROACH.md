# Development Approach

This document outlines the architectural decisions, development methodology, and implementation strategy used to build the Drug Analytics API from the ground up.

## Table of Contents
1. [Project Vision](#project-vision)
2. [Architecture Decisions](#architecture-decisions)
3. [Development Methodology](#development-methodology)
4. [Implementation Phases](#implementation-phases)
5. [Key Technical Decisions](#key-technical-decisions)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Strategy](#deployment-strategy)

---

## Project Vision

**Goal**: Build a cloud-based analytics service for drug discovery data using AWS serverless architecture.

**Core Requirements**:
- RESTful API for drug data management
- CSV file upload and processing
- Asynchronous processing with status tracking
- Scalable, cost-effective serverless architecture
- Production-ready with security and monitoring

---

## Architecture Decisions

### 1. Serverless Monolith with Event-Driven Workers

**Pattern**: Single FastAPI Lambda for all API routes + separate Lambda for CSV processing

**Why This Approach?**
- **Simplicity**: One codebase for all API logic, easier to develop and maintain
- **Cost-Effective**: Single Lambda cold start for all API routes
- **Separation of Concerns**: CSV processing isolated in dedicated Lambda
- **Event-Driven**: S3 triggers CSV processor automatically (no polling)
- **Scalability**: Each Lambda scales independently based on load

**Architecture Components**:
```
Client → API Gateway → API Lambda (FastAPI) → DynamoDB
                                            ↓
                                            S3 → CSV Processor Lambda → DynamoDB
```

**Alternative Considered**: Microservices (one Lambda per route)
- **Rejected**: Overkill for small API, increases cold starts, complicates deployment

---

### 2. FastAPI Framework

**Why FastAPI?**
- **Modern Python**: Async/await support, type hints, Pydantic validation
- **Auto Documentation**: Swagger UI and ReDoc generated automatically
- **Performance**: One of the fastest Python frameworks
- **Developer Experience**: Excellent error messages, IDE autocomplete
- **AWS Lambda Compatible**: Works with Mangum adapter

**Alternative Considered**: Flask
- **Rejected**: No native async support, less modern, manual validation

---

### 3. AWS Services Selection

| Service | Purpose | Why Chosen |
|---------|---------|------------|
| **Lambda** | Compute | Serverless, auto-scaling, pay-per-use |
| **API Gateway (HTTP API)** | Routing | Cheaper than REST API, simpler for proxy pattern |
| **DynamoDB** | Database | Serverless, fast, auto-scaling, free tier |
| **S3** | File Storage | Durable, event triggers, encryption, cheap |
| **CloudWatch** | Monitoring | Native AWS integration, logs + metrics + alarms |
| **Parameter Store** | Secrets | FREE (vs Secrets Manager $0.40/month), no rotation needed |

**Cost Optimization**:
- All services have generous free tiers
- Estimated cost: $0.00/month (first 12 months), ~$0.02/month after

---

### 4. Authentication Architecture

**Decision**: FastAPI-level JWT authentication (not API Gateway Lambda Authorizer)

**Why?**
- **Proxy Pattern**: App uses `/{proxy+}` routing, making API Gateway auth complex
- **Flexibility**: Easy to mix public (`/health`, `/login`) and protected routes
- **Custom User Storage**: DynamoDB users table
- **Simplicity**: Single codebase, no separate authorizer Lambda

**Implementation**:
- JWT tokens signed with secret from Parameter Store
- Bcrypt password hashing (never store plaintext)
- FastAPI dependency injection for token validation
- 24-hour token expiration (configurable)

**Alternative Considered**: API Gateway Lambda Authorizer
- **Rejected**: Requires HTTP API → REST API migration, adds complexity, separate Lambda

---

## Development Methodology

### 1. Iterative Development

**Approach**: Build → Test → Deploy → Iterate

**Phases**:
1. **Core API**: Basic CRUD operations, local testing
2. **AWS Integration**: DynamoDB, S3, Lambda deployment
3. **Async Processing**: Event-driven CSV processing, status tracking
4. **Security**: Authentication, rate limiting, encryption
5. **Monitoring**: CloudWatch alarms, logging
6. **Documentation**: README, APPROACH

### 2. Test-Driven Development (TDD)

**Strategy**: Write tests alongside features, maintain high coverage

**Test Pyramid**:
- **Unit Tests**: Services, utilities, validation logic (fast, isolated)
- **Integration Tests**: API endpoints with mocked AWS services (realistic)
- **Manual Testing**: Deployed API with real AWS resources (production validation)

**Coverage Target**: 90%+ (achieved 94%)

### 3. Infrastructure as Code (IaC)

**Tool**: AWS SAM (Serverless Application Model)

**Why SAM?**
- **Serverless-Focused**: Designed for Lambda, API Gateway, DynamoDB
- **CloudFormation-Based**: Production-ready, version-controlled infrastructure
- **Local Testing**: `sam local` for Lambda testing
- **Simplified Syntax**: Less verbose than raw CloudFormation


---

## Implementation Phases

### Phase 1: Core API (Local Development)

**Goal**: Build working FastAPI application with basic CRUD operations

**Steps**:
1. Project structure setup (src/, tests/, requirements.txt)
2. FastAPI app with health endpoint
3. Drug data endpoints (GET /drugs, GET /drugs/{name})
4. Local DynamoDB integration (boto3)
5. Unit tests with pytest + moto (AWS mocking)

**Outcome**: Working API running locally on port 8000

---

### Phase 2: File Upload & Storage

**Goal**: Accept CSV uploads and store in S3

**Steps**:
1. Upload endpoint (POST /uploads) with file validation
2. S3 integration (boto3 client)
3. File size and type validation (10MB, .csv only)
4. Upload status tracking in DynamoDB
5. Integration tests with mocked S3

**Outcome**: API accepts CSV files, stores in S3, returns upload_id

---

### Phase 3: Async CSV Processing

**Goal**: Process CSV files asynchronously with S3 event triggers

**Steps**:
1. CSV processor Lambda function (separate from API)
2. S3 event configuration (trigger on .csv upload)
3. CSV parsing and validation (pandas)
4. Batch write to DynamoDB (drug data)
5. Status updates (pending → processing → completed/failed)
6. Row count validation (max 10,000 rows)

**Outcome**: Upload returns immediately, processing happens in background

---

### Phase 4: AWS Deployment

**Goal**: Deploy to AWS with automated infrastructure provisioning

**Steps**:
1. SAM template (template.yaml) with all resources
2. Lambda layers for dependencies (pandas, numpy)
3. IAM roles and policies (least privilege)
4. Deployment script (deploy.sh) with environment support
5. CloudFormation stack management
6. API Gateway HTTP API configuration

**Outcome**: One-command deployment (`./deploy.sh dev`)

---

### Phase 5: Security & Authentication

**Goal**: Secure API with JWT authentication

**Steps**:
1. User management (DynamoDB users table)
2. Password hashing (bcrypt)
3. JWT token generation and validation
4. Login endpoint (POST /auth/login)
5. Protected routes (FastAPI dependencies)
6. Parameter Store for JWT secret
7. Rate limiting (API Gateway throttling)

**Outcome**: All endpoints (except /health, /login) require authentication

---

### Phase 6: Monitoring & Observability

**Goal**: Production-ready monitoring and alerting

**Steps**:
1. CloudWatch Logs (automatic for Lambda)
2. CloudWatch Alarms (CSV processor duration + errors)
3. S3 bucket encryption (SSE-S3 AES-256)
4. Structured logging (JSON format)
5. Error tracking and debugging

**Outcome**: Visibility into API health, performance, and errors

---

### Phase 7: Documentation & Testing

**Goal**: Comprehensive documentation for users and developers

**Steps**:
1. README.md (setup, deployment, API usage)
2. Swagger UI (auto-generated from FastAPI)
3. Code comments and docstrings

**Outcome**: Self-service documentation for all use cases

---

## Key Technical Decisions

### 1. Pagination Strategy

**Decision**: Cursor-based pagination with DynamoDB LastEvaluatedKey

**Why?**
- **Efficient**: No offset/limit scanning (O(1) vs O(n))
- **Consistent**: Works with DynamoDB's distributed nature
- **Scalable**: Performance doesn't degrade with large datasets

**Implementation**:
- Default: 10 items per page
- Max: 1000 items per page
- Opaque token (base64-encoded LastEvaluatedKey)

---

### 2. Error Handling

**Strategy**: Fail fast with clear error messages

**Approach**:
- **Validation Errors**: 400 Bad Request with specific field errors
- **Authentication Errors**: 401 Unauthorized with generic message (security)
- **Not Found**: 404 with resource identifier
- **Server Errors**: 500 with error ID for debugging (no sensitive data)

**Example**:
```json
{
  "detail": "File size exceeds maximum allowed size of 10MB"
}
```

---

### 3. CSV Processing Strategy

**Decision**: Batch processing with validation before write

**Why?**
- **Data Integrity**: Validate entire CSV before writing to DynamoDB
- **Atomic Operations**: All-or-nothing (no partial writes)
- **Error Reporting**: Clear feedback on validation failures

**Process**:
1. Download CSV from S3
2. Parse with pandas (validate structure)
3. Validate all rows (drug_name, target, efficacy)
4. Batch write to DynamoDB (25 items per batch)
5. Update status (completed/failed)

---

### 4. Environment Management

**Strategy**: Environment-specific resources with naming convention

**Pattern**: `{resource}-{environment}` (e.g., `drugs-dev`, `drugs-prod`)

**Environments**:
- **dev**: Development/testing
- **staging**: Pre-production validation (optional)
- **prod**: Production

**Benefits**:
- Isolated resources (no cross-contamination)
- Easy cleanup (delete stack)
- Cost tracking per environment

---

### 5. Dependency Management

**Strategy**: Minimal dependencies, Lambda layers for large packages

**Core Dependencies**:
- **FastAPI**: Web framework
- **Mangum**: Lambda adapter for FastAPI
- **boto3**: AWS SDK
- **pydantic**: Data validation
- **python-jose**: JWT handling
- **bcrypt**: Password hashing

**Lambda Layer** (CSV processor only):
- **pandas**: CSV parsing
- **numpy**: pandas dependency

**Why Layers?**
- Reduces deployment package size
- Faster deployments (layer cached)
- Shared across Lambda functions

---

## Testing Strategy

### 1. Unit Tests

**Scope**: Individual functions and classes

**Tools**: pytest, moto (AWS mocking)

**Coverage**:
- Services (auth_service, file_service, drug_service)
- Utilities (validation, parsing)
- Models (DTOs, entities)

**Example**:
```python
def test_validate_csv_success():
    df = pd.DataFrame({
        'drug_name': ['Aspirin'],
        'target': ['COX-2'],
        'efficacy': [85.5]
    })
    result = validate_csv_data(df)
    assert result is None  # No errors
```

---

### 2. Integration Tests

**Scope**: API endpoints with mocked AWS services

**Tools**: pytest, TestClient (FastAPI), moto

**Coverage**:
- All API routes (health, auth, uploads, drugs)
- Authentication flow (login, token validation)
- Error scenarios (401, 404, 400)

**Example**:
```python
def test_upload_csv_success(client, auth_headers):
    files = {"file": ("drugs.csv", csv_content, "text/csv")}
    response = client.post("/v1/api/uploads", files=files, headers=auth_headers)
    assert response.status_code == 202
    assert "upload_id" in response.json()
```

---

### 3. Manual Testing

**Scope**: Deployed API with real AWS resources

**Process**:
1. Deploy to dev environment
2. Create test user in DynamoDB
3. Test all endpoints with real data
4. Verify CloudWatch logs and metrics
5. Test error scenarios


---

## Deployment Strategy

### 1. Automated Deployment

**Tool**: deploy.sh script

**Process**:
1. Validate environment parameter (dev/staging/prod)
2. Create JWT secret in Parameter Store (if not exists)
3. Build SAM application (sam build)
4. Deploy CloudFormation stack (sam deploy)
5. Configure S3 event trigger
6. Output API Gateway URL

**Command**: `./deploy.sh dev`

---

## Lessons Learned

### 1. Start Simple, Add Complexity Later

**Lesson**: Serverless monolith is simpler than microservices for small APIs

**Outcome**: Faster development, easier debugging, lower operational overhead

---

### 2. Test Early, Test Often

**Lesson**: High test coverage (94%) caught bugs before production

**Outcome**: Confident deployments, faster iteration

---

### 3. Document as You Build

**Lesson**: Writing documentation alongside code prevents knowledge gaps

**Outcome**: Self-service onboarding, reduced support burden

---

### 4. Security is Not Optional

**Lesson**: Authentication, encryption, and rate limiting are table stakes

**Outcome**: Production-ready API from day one

---

### 5. Monitor Everything

**Lesson**: CloudWatch alarms catch issues before users do

**Outcome**: Proactive incident response, better reliability

---

## Future Improvements

### 1. User Management API
- Self-service registration
- Password reset flow
- Role-based access control (RBAC)

### 2. Token Refresh
- Refresh tokens for better UX
- Avoid re-login every 24 hours

### 3. Dead Letter Queue (DLQ)
- Capture failed CSV processing jobs
- Reprocess endpoint for manual retry

### 4. Enhanced Monitoring
- CloudWatch dashboards
- API Gateway 5xx alarms
- DynamoDB throttling alerts

### 5. Performance Optimization
- DynamoDB caching (DAX)
- API response caching
- Lambda provisioned concurrency (if needed)

---

## Conclusion

This project demonstrates a pragmatic approach to building production-ready serverless APIs:

1. **Start with a clear vision** (drug analytics API)
2. **Choose the right architecture** (serverless monolith + event-driven workers)
3. **Build iteratively** (core → AWS → async → security → monitoring)
4. **Test thoroughly** (94% coverage, unit + integration + manual)
5. **Document everything** (README, approach)
6. **Deploy with confidence** (automated scripts, IaC, monitoring)

The result is a scalable, secure, cost-effective API that processes drug discovery data efficiently while maintaining high code quality and operational excellence.
