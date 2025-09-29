# PowerShell script to deploy Market Analytics to AWS
# Stays within free tier limits

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Market Analytics AWS Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Configuration
$FUNCTION_NAME = "market-analytics-collector"
$REGION = "us-east-1"
$RUNTIME = "python3.10"
$TIMEOUT = 300
$MEMORY = 512
$DB_PASSWORD = "123456789"  # Update this!

# Step 1: Run database migration
Write-Host "`nStep 1: Migrating data from Railway to AWS RDS..." -ForegroundColor Yellow

# Update password in migration script
$migrationScript = Get-Content "migrate_railway_to_aws.py" -Raw
$migrationScript = $migrationScript -replace "'password': '123456789'", "'password': '$DB_PASSWORD'"
$migrationScript | Out-File "migrate_railway_to_aws.py" -Encoding UTF8

# Run migration
python migrate_railway_to_aws.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Migration failed! Please check the error above." -ForegroundColor Red
    exit 1
}

# Step 2: Prepare Lambda deployment package
Write-Host "`nStep 2: Preparing Lambda deployment package..." -ForegroundColor Yellow

# Create requirements for Lambda
@"
psycopg2-binary==2.9.9
aiohttp==3.9.1
"@ | Out-File "requirements-lambda.txt" -Encoding ASCII

# Create deployment directory
$deployDir = "lambda-deploy"
if (Test-Path $deployDir) {
    Remove-Item $deployDir -Recurse -Force
}
New-Item -ItemType Directory -Path $deployDir | Out-Null

# Install dependencies
pip install -r requirements-lambda.txt --target $deployDir --quiet

# Copy Lambda handler
Copy-Item "market_analytics_lambda.py" "$deployDir/lambda_function.py"

# Create deployment package
$zipFile = "market-analytics-lambda.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}

Set-Location $deployDir
Compress-Archive -Path * -DestinationPath "..\$zipFile" -Force
Set-Location ..

Write-Host "Deployment package created: $zipFile" -ForegroundColor Green

# Step 3: Create or update Lambda function
Write-Host "`nStep 3: Deploying Lambda function..." -ForegroundColor Yellow

# Check if function exists
$functionExists = aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>$null

if ($null -eq $functionExists) {
    Write-Host "Creating new Lambda function..." -ForegroundColor Cyan

    # Get existing IAM role or create new one
    $roleArn = "arn:aws:iam::268149180831:role/dex-analytics-lambda-role"

    # Create the function
    aws lambda create-function `
        --function-name $FUNCTION_NAME `
        --runtime $RUNTIME `
        --role $roleArn `
        --handler "lambda_function.lambda_handler" `
        --timeout $TIMEOUT `
        --memory-size $MEMORY `
        --zip-file "fileb://$zipFile" `
        --region $REGION
} else {
    Write-Host "Updating existing Lambda function..." -ForegroundColor Cyan

    aws lambda update-function-code `
        --function-name $FUNCTION_NAME `
        --zip-file "fileb://$zipFile" `
        --region $REGION | Out-Null

    Start-Sleep -Seconds 2

    aws lambda update-function-configuration `
        --function-name $FUNCTION_NAME `
        --timeout $TIMEOUT `
        --memory-size $MEMORY `
        --region $REGION | Out-Null
}

# Step 4: Set environment variables
Write-Host "`nStep 4: Setting environment variables..." -ForegroundColor Yellow

$envVars = @{
    "Variables" = @{
        "DATABASE_URL" = "postgresql://dbadmin:${DB_PASSWORD}@dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com:5432/market_analytics"
        "LOG_LEVEL" = "INFO"
    }
} | ConvertTo-Json -Compress

$envVars | Out-File "env.json" -Encoding ASCII

aws lambda update-function-configuration `
    --function-name $FUNCTION_NAME `
    --environment file://env.json `
    --region $REGION | Out-Null

# Step 5: Create CloudWatch schedule (every 5 minutes)
Write-Host "`nStep 5: Setting up CloudWatch Events schedule..." -ForegroundColor Yellow

$ruleName = "market-analytics-schedule"

# Create or update rule
aws events put-rule `
    --name $ruleName `
    --schedule-expression "rate(5 minutes)" `
    --description "Collect market data every 5 minutes" `
    --region $REGION | Out-Null

# Get Lambda ARN
$functionArn = (aws lambda get-function --function-name $FUNCTION_NAME --region $REGION | ConvertFrom-Json).Configuration.FunctionArn

# Add permission for CloudWatch to invoke Lambda
aws lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id "cloudwatch-scheduled-event" `
    --action "lambda:InvokeFunction" `
    --principal events.amazonaws.com `
    --source-arn "arn:aws:events:${REGION}:268149180831:rule/${ruleName}" `
    --region $REGION 2>$null

# Set Lambda as target
$target = @([PSCustomObject]@{
    "Id" = "1"
    "Arn" = $functionArn
}) | ConvertTo-Json -Compress

$target | Out-File "target.json" -Encoding ASCII

aws events put-targets `
    --rule $ruleName `
    --targets file://target.json `
    --region $REGION | Out-Null

# Step 6: Test the Lambda
Write-Host "`nStep 6: Testing Lambda function..." -ForegroundColor Yellow

$testEvent = @{
    "test" = $true
} | ConvertTo-Json -Compress

$testEvent | Out-File "test-event.json" -Encoding ASCII

aws lambda invoke `
    --function-name $FUNCTION_NAME `
    --payload file://test-event.json `
    --region $REGION `
    output.json | Out-Null

$output = Get-Content output.json | ConvertFrom-Json
if ($output.statusCode -eq 200) {
    Write-Host "Lambda test successful!" -ForegroundColor Green
    Write-Host "Response: $($output.body)" -ForegroundColor Gray
} else {
    Write-Host "Lambda test failed!" -ForegroundColor Red
    Write-Host "Error: $($output.body)" -ForegroundColor Red
}

# Cleanup
Remove-Item $deployDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "env.json", "target.json", "test-event.json", "output.json" -ErrorAction SilentlyContinue

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nYour Market Analytics backend is now running on AWS!" -ForegroundColor Green
Write-Host "- Lambda function: $FUNCTION_NAME" -ForegroundColor Gray
Write-Host "- Schedule: Every 5 minutes" -ForegroundColor Gray
Write-Host "- Database: market_analytics on RDS" -ForegroundColor Gray
Write-Host "- Region: $REGION" -ForegroundColor Gray

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Set up Grafana on EC2 free tier or use Grafana Cloud free" -ForegroundColor Gray
Write-Host "2. Configure Grafana data source to point to AWS RDS" -ForegroundColor Gray
Write-Host "3. Import your dashboards" -ForegroundColor Gray

Write-Host "`nMonitor logs at:" -ForegroundColor Yellow
Write-Host "aws logs tail /aws/lambda/$FUNCTION_NAME --follow" -ForegroundColor Cyan