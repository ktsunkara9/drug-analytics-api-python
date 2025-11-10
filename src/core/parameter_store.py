"""
AWS Systems Manager Parameter Store helper.
Fetches parameters with caching to minimize API calls.
"""
import boto3
from functools import lru_cache


@lru_cache(maxsize=10)
def get_parameter(parameter_name: str, region: str = "us-east-1") -> str:
    """
    Fetch parameter from Parameter Store with caching.
    
    Args:
        parameter_name: Full parameter name (e.g., /drug-analytics-api/dev/jwt-secret)
        region: AWS region
        
    Returns:
        Parameter value (decrypted if SecureString)
    """
    ssm = boto3.client('ssm', region_name=region)
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    return response['Parameter']['Value']
