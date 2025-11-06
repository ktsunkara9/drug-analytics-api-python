"""
Lambda function to process CSV files uploaded to S3.
Triggered by S3 ObjectCreated events.
"""
import json
from src.services.drug_service import DrugService
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
    
    try:
        # Extract S3 information from event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']
            
            print(f"Processing file: s3://{bucket}/{s3_key}")
            
            # Process CSV and save to DynamoDB
            count = drug_service.process_csv_and_save(s3_key)
            
            print(f"Successfully processed {count} drug records")
            
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
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Validation Error',
                'message': e.message
            })
        }
    
    except CSVProcessingException as e:
        print(f"CSV processing error: {e.message}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'CSV Processing Error',
                'message': e.message
            })
        }
    
    except DynamoDBException as e:
        print(f"DynamoDB error: {e.message}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Database Error',
                'message': e.message
            })
        }
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }
