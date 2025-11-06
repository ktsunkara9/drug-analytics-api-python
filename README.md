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