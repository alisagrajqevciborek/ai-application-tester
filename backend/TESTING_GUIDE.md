# Testing Browser Automation with Playwright

## Prerequisites

1. **Install Playwright browsers** (if not already done):
   ```bash
   cd backend
   .\.venv\Scripts\python.exe -m playwright install chromium
   ```

2. **Run database migrations**:
   ```bash
   cd backend
   .\.venv\Scripts\python.exe manage.py makemigrations applications
   .\.venv\Scripts\python.exe manage.py migrate
   ```

## Step 1: Start the Django Server

```bash
cd backend
.\.venv\Scripts\python.exe manage.py runserver
```

The server will run on `http://localhost:8000`

## Step 2: Create a Test User (if needed)

```bash
cd backend
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Or use the Django admin at `http://localhost:8000/admin/`

## Step 3: Get Authentication Token

### Option A: Using curl (PowerShell)

```powershell
# Login
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"email":"your@email.com","password":"yourpassword"}'

$token = $response.access
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}
```

### Option B: Using Python script

Create a file `test_api.py`:

```python
import requests

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "your@email.com", "password": "yourpassword"}
)
token = login_response.json()["access"]
headers = {"Authorization": f"Bearer {token}"}
```

## Step 4: Create an Application

```powershell
# Create application
$appData = @{
    name = "Test Website"
    url = "https://example.com"
} | ConvertTo-Json

$app = Invoke-RestMethod -Uri "http://localhost:8000/api/applications" `
    -Method POST `
    -Headers $headers `
    -Body $appData `
    -ContentType "application/json"

$appId = $app.id
Write-Host "Created application with ID: $appId"
```

## Step 5: Create a Test Run

This will trigger the Playwright browser automation:

```powershell
# Create test run (functional test)
$testRunData = @{
    application = $appId
    test_type = "functional"
} | ConvertTo-Json

$testRun = Invoke-RestMethod -Uri "http://localhost:8000/api/applications/test-runs/" `
    -Method POST `
    -Headers $headers `
    -Body $testRunData `
    -ContentType "application/json"

$testRunId = $testRun.id
Write-Host "Created test run with ID: $testRunId"
Write-Host "Status: $($testRun.status)"
```

## Step 6: Poll for Test Completion

```powershell
# Poll for test completion
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    $testRun = Invoke-RestMethod -Uri "http://localhost:8000/api/applications/test-runs/$testRunId" `
        -Method GET `
        -Headers $headers
    
    Write-Host "Status: $($testRun.status) - Pass Rate: $($testRun.pass_rate)% - Fail Rate: $($testRun.fail_rate)%"
    
    if ($testRun.status -in @("success", "failed")) {
        Write-Host "Test completed!"
        break
    }
    
    $attempt++
}
```

## Step 7: Check Test Results

```powershell
# Get final test run details
$testRun = Invoke-RestMethod -Uri "http://localhost:8000/api/applications/test-runs/$testRunId" `
    -Method GET `
    -Headers $headers

Write-Host "Final Status: $($testRun.status)"
Write-Host "Pass Rate: $($testRun.pass_rate)%"
Write-Host "Fail Rate: $($testRun.fail_rate)%"
Write-Host "Started: $($testRun.started_at)"
Write-Host "Completed: $($testRun.completed_at)"
```

## Step 8: View Screenshots (if any)

Screenshots are saved to:
- `backend/media/screenshots/{test_run_id}/`
- Also accessible via the Screenshot model in the database

## Complete Test Script

Save this as `test_browser_automation.ps1`:

```powershell
# Configuration
$BASE_URL = "http://localhost:8000"
$EMAIL = "your@email.com"
$PASSWORD = "yourpassword"
$TEST_URL = "https://example.com"

# Step 1: Login
Write-Host "Logging in..."
$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{email=$EMAIL; password=$PASSWORD} | ConvertTo-Json)

$token = $loginResponse.access
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}
Write-Host "✓ Logged in successfully" -ForegroundColor Green

# Step 2: Create Application
Write-Host "Creating application..."
$appData = @{
    name = "Test App"
    url = $TEST_URL
} | ConvertTo-Json

$app = Invoke-RestMethod -Uri "$BASE_URL/api/applications" `
    -Method POST `
    -Headers $headers `
    -Body $appData
Write-Host "✓ Created application: $($app.id)" -ForegroundColor Green

# Step 3: Create Test Run
Write-Host "Creating test run..."
$testRunData = @{
    application = $app.id
    test_type = "functional"
} | ConvertTo-Json

$testRun = Invoke-RestMethod -Uri "$BASE_URL/api/applications/test-runs/" `
    -Method POST `
    -Headers $headers `
    -Body $testRunData
Write-Host "✓ Created test run: $($testRun.id)" -ForegroundColor Green
Write-Host "  Status: $($testRun.status)" -ForegroundColor Yellow

# Step 4: Poll for completion
Write-Host "Waiting for test to complete..."
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    $testRun = Invoke-RestMethod -Uri "$BASE_URL/api/applications/test-runs/$($testRun.id)" `
        -Method GET `
        -Headers $headers
    
    Write-Host "  Attempt $($attempt + 1): Status=$($testRun.status), Pass=$($testRun.pass_rate)%, Fail=$($testRun.fail_rate)%"
    
    if ($testRun.status -in @("success", "failed")) {
        Write-Host "✓ Test completed!" -ForegroundColor Green
        break
    }
    
    $attempt++
}

# Step 5: Display results
Write-Host "`n=== Test Results ===" -ForegroundColor Cyan
Write-Host "Status: $($testRun.status)"
Write-Host "Pass Rate: $($testRun.pass_rate)%"
Write-Host "Fail Rate: $($testRun.fail_rate)%"
Write-Host "Started: $($testRun.started_at)"
Write-Host "Completed: $($testRun.completed_at)"
```

## Testing Different Test Types

You can test different test types by changing the `test_type` parameter:

- `"functional"` - Basic functionality tests
- `"regression"` - Regression tests (broken functionality)
- `"performance"` - Performance metrics
- `"accessibility"` - WCAG compliance tests

## Manual Testing via Django Admin

1. Go to `http://localhost:8000/admin/`
2. Login with superuser credentials
3. Navigate to **Applications** → **Test Runs**
4. Create a new test run manually
5. The test will execute automatically in the background

## Troubleshooting

### Test stays in "pending" or "running" status
- Check Django server logs for errors
- Verify Playwright browsers are installed
- Check that the URL is accessible

### No screenshots generated
- Verify `MEDIA_ROOT` directory exists and is writable
- Check Django logs for file permission errors

### Import errors
- Ensure virtual environment is activated
- Verify Playwright is installed: `.\.venv\Scripts\python.exe -m pip list | Select-String playwright`

## Expected Behavior

1. Test run is created with status `"pending"`
2. Status changes to `"running"` within 1-2 seconds
3. Test executes (takes 5-15 seconds depending on test type)
4. Status changes to `"success"` or `"failed"`
5. `pass_rate` and `fail_rate` are populated
6. `completed_at` timestamp is set
7. Screenshots are saved (if any issues found)

