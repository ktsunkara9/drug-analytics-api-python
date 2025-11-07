# Drug Analytics API

A cloud-based analytics service for drug discovery data using AWS serverless architecture.

## Architecture

- **FastAPI** - REST API framework
- **AWS Lambda** - Serverless compute
- **API Gateway** - HTTP routing
- **Amazon S3** - CSV file storage
- **DynamoDB** - Drug data storage
- **Event-driven processing** - S3 triggers Lambda for data processing

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

## API Endpoints

- `POST /upload` - Upload CSV file with drug data
- `GET /drugs` - Retrieve all drug data
- `GET /drugs/{drug_name}` - Retrieve specific drug data

## CSV Format

Required fields:
- `drug_name` (string)
- `target` (string)
- `efficacy` (float, 0-100)

## Development Status

- [x] Project setup
- [x] Dependencies installed
- [ ] Core structure
- [ ] FastAPI implementation
- [ ] AWS integration
- [ ] Testing
- [ ] Deployment

Waiting for changeset to be created..

Error: Failed to create changeset for the stack: drug-analytics-api, ex: Waiter ChangeSetCreateComplete failed: Waiter encountered a terminal failure state: For expression "Status" we matched expected path: "FAILED" Status: FAILED. Reason: Circular dependency between resources: [DrugApiFunctionApiEventPermission, CsvProcessorFunctionS3EventPermission, DrugAnalyticsApi, DrugApiFunction, DrugAnalyticsApiStage, DrugDataBucket, CsvProcessorFunction]