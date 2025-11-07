#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="drug-analytics-api"

echo "Building SAM application..."
"/c/Program Files/Amazon/AWSSAMCLI/bin/sam.cmd" build

echo "Deploying stack to ${ENVIRONMENT}..."
"/c/Program Files/Amazon/AWSSAMCLI/bin/sam.cmd" deploy --parameter-overrides Environment=${ENVIRONMENT}

echo "Configuring S3 trigger..."
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text)
LAMBDA_ARN=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`CsvProcessorFunctionArn`].OutputValue' --output text)

echo "Adding Lambda permission for S3..."
aws lambda add-permission \
  --function-name ${LAMBDA_ARN} \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::${BUCKET_NAME} \
  --no-cli-pager 2>/dev/null || echo "Permission already exists"

echo "Configuring S3 bucket notification..."
aws s3api put-bucket-notification-configuration \
  --bucket ${BUCKET_NAME} \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${LAMBDA_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"],\"Filter\":{\"Key\":{\"FilterRules\":[{\"Name\":\"suffix\",\"Value\":\".csv\"}]}}}]}"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo "Environment: ${ENVIRONMENT}"
echo "S3 Bucket: ${BUCKET_NAME}"
echo "Lambda Function: ${LAMBDA_ARN}"
echo "API URL: https://$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)"
echo "=========================================="
