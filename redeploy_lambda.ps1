# Redeploy Lambda with correct dependencies
Write-Host "Redeploying Lambda with psycopg2-binary..." -ForegroundColor Cyan

$FUNCTION_NAME = "market-analytics-collector"
$REGION = "us-east-1"

# Create clean deployment directory
$deployDir = "lambda-deploy-fixed"
if (Test-Path $deployDir) {
    Remove-Item $deployDir -Recurse -Force
}
New-Item -ItemType Directory -Path $deployDir | Out-Null

# Install psycopg2-binary specifically
Write-Host "Installing Lambda dependencies..." -ForegroundColor Yellow
pip install psycopg2-binary==2.9.9 aiohttp==3.9.1 --target $deployDir --quiet

# Copy Lambda handler
Copy-Item "market_analytics_lambda.py" "$deployDir/lambda_function.py"

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Set-Location $deployDir
$zipFile = "..\market-analytics-lambda-fixed.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}
Compress-Archive -Path * -DestinationPath $zipFile -Force
Set-Location ..

Write-Host "Updating Lambda function code..." -ForegroundColor Yellow

aws lambda update-function-code `
    --function-name $FUNCTION_NAME `
    --zip-file fileb://market-analytics-lambda-fixed.zip `
    --region $REGION | Out-Null

Write-Host "Lambda code updated!" -ForegroundColor Green

# Wait for update
Start-Sleep -Seconds 5

# Test Lambda
Write-Host "`nTesting Lambda..." -ForegroundColor Yellow

$testEvent = '{"test": true}'
$testEvent | Out-File "test.json" -Encoding ASCII

aws lambda invoke `
    --function-name $FUNCTION_NAME `
    --payload file://test.json `
    --region $REGION `
    result.json

$result = Get-Content result.json -Raw | ConvertFrom-Json

if ($result.statusCode -eq 200) {
    Write-Host "Lambda test successful!" -ForegroundColor Green
    Write-Host $result.body -ForegroundColor Gray
} else {
    Write-Host "Lambda test response:" -ForegroundColor Yellow
    Write-Host $result -ForegroundColor Gray
}

# Clean up
Remove-Item $deployDir -Recurse -Force
Remove-Item "test.json", "result.json", "market-analytics-lambda-fixed.zip" -ErrorAction SilentlyContinue

Write-Host "`nLambda redeployment complete!" -ForegroundColor Green