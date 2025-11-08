"""
Lambda function to process CSV files uploaded to S3.
Triggered by S3 ObjectCreated events.
"""
import json
import re
from src.services.drug_service import DrugService
from src.repositories.upload_status_repository import UploadStatusRepository
from src.core.exceptions import CSVProcessingException, ValidationException, DynamoDBException


def handler(event, context):
    """
    Lambda handler for S3 event processing.
    
    Args:
        event: S3 event containing bucket and object information
        context: Lambda context object
        
    Returns:
        dict: Processing result with status and count
    """
    drug_service = DrugService()
    upload_status_repo = UploadStatusRepository()
    
    try:
        # Extract S3 information from event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']
            
            # Extract upload_id from S3 key (format: uploads/YYYY/MM/DD/upload_id.csv)
            upload_id = _extract_upload_id(s3_key)
            
            print(f"Processing file: s3://{bucket}/{s3_key}, upload_id: {upload_id}")
            
            # Update status to processing
            if upload_id:
                upload_status_repo.update(upload_id, {'status': 'processing'})
            
            # Process CSV and save to DynamoDB
            count = drug_service.process_csv_and_save(s3_key)
            
            print(f"Successfully processed {count} drug records")
            
            # Update status to completed
            if upload_id:
                upload_status_repo.update(upload_id, {
                    'status': 'completed',
                    'total_rows': count,
                    'processed_rows': count
                })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully processed {count} records',
                    's3_key': s3_key,
                    'records_processed': count
                })
            }
    
    except ValidationException as e:
        print(f"Validation error: {e.message}")
        if upload_id:
            upload_status_repo.update(upload_id, {
                'status': 'failed',
                'error_message': e.message
            })
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Validation Error',
                'message': e.message
            })
        }
    
    except CSVProcessingException as e:
        print(f"CSV processing error: {e.message}")
        if upload_id:
            upload_status_repo.update(upload_id, {
                'status': 'failed',
                'error_message': e.message
            })
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'CSV Processing Error',
                'message': e.message
            })
        }
    
    except DynamoDBException as e:
        print(f"DynamoDB error: {e.message}")
        if upload_id:
            upload_status_repo.update(upload_id, {
                'status': 'failed',
                'error_message': e.message
            })
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Database Error',
                'message': e.message
            })
        }
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if upload_id:
            upload_status_repo.update(upload_id, {
                'status': 'failed',
                'error_message': str(e)
            })
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }


def _extract_upload_id(s3_key: str) -> str:
    """
    Extract upload_id from S3 key.
    Expected format: uploads/upload_id/filename.csv
    
    Args:
        s3_key: S3 object key
        
    Returns:
        upload_id or None if not found
    """
    # Match UUID pattern (case-insensitive)
    match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', s3_key)
    return match.group(1) if match else None
