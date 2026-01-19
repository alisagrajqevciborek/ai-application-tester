# Quick Test Script for Browser Automation
# Usage: .\test_browser_automation.ps1

# Configuration
$BASE_URL = "http://localhost:8000"
$EMAIL = "admin@example.com"  # Change to your user email
$PASSWORD = "admin123"         # Change to your password
$TEST_URL = "https://example.com"

Write-Host "=== Browser Automation Test ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login
Write-Host "[1/5] Logging in..." -ForegroundColor Yellow
try {
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
} catch {
    Write-Host "✗ Login failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Create Application
Write-Host "[2/5] Creating application..." -ForegroundColor Yellow
try {
    $appData = @{
        name = "Test App - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        url = $TEST_URL
    } | ConvertTo-Json

    $app = Invoke-RestMethod -Uri "$BASE_URL/api/applications" `
        -Method POST `
        -Headers $headers `
        -Body $appData
    Write-Host "✓ Created application: $($app.id) - $($app.name)" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create application: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Create Test Run
Write-Host "[3/5] Creating test run (functional test)..." -ForegroundColor Yellow
try {
    $testRunData = @{
        application = $app.id
        test_type = "functional"
    } | ConvertTo-Json

    $testRun = Invoke-RestMethod -Uri "$BASE_URL/api/applications/test-runs/" `
        -Method POST `
        -Headers $headers `
        -Body $testRunData
    Write-Host "✓ Created test run: $($testRun.id)" -ForegroundColor Green
    Write-Host "  Initial status: $($testRun.status)" -ForegroundColor Yellow
} catch {
    Write-Host "✗ Failed to create test run: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Poll for completion
Write-Host "[4/5] Waiting for test to complete..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$testRunId = $testRun.id

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    
    try {
        $testRun = Invoke-RestMethod -Uri "$BASE_URL/api/applications/test-runs/$testRunId" `
            -Method GET `
            -Headers $headers
        
        $statusColor = if ($testRun.status -eq "running") { "Yellow" } 
                       elseif ($testRun.status -eq "success") { "Green" }
                       elseif ($testRun.status -eq "failed") { "Red" }
                       else { "White" }
        
        Write-Host "  [$($attempt + 1)/$maxAttempts] Status: $($testRun.status) | Pass: $($testRun.pass_rate)% | Fail: $($testRun.fail_rate)%" -ForegroundColor $statusColor
        
        if ($testRun.status -in @("success", "failed")) {
            Write-Host "✓ Test completed!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  Error polling: $_" -ForegroundColor Red
    }
    
    $attempt++
}

if ($attempt -ge $maxAttempts) {
    Write-Host "✗ Test timed out after $($maxAttempts * 2) seconds" -ForegroundColor Red
}

# Step 5: Display results
Write-Host ""
Write-Host "[5/5] Test Results:" -ForegroundColor Yellow
Write-Host "===================" -ForegroundColor Cyan
Write-Host "Status:        $($testRun.status)" -ForegroundColor $(if ($testRun.status -eq "success") { "Green" } else { "Red" })
Write-Host "Pass Rate:     $($testRun.pass_rate)%"
Write-Host "Fail Rate:     $($testRun.fail_rate)%"
Write-Host "Started:       $($testRun.started_at)"
Write-Host "Completed:     $($testRun.completed_at)"
Write-Host "Application:   $($testRun.application_name)"
Write-Host "Test Type:     $($testRun.test_type)"
Write-Host ""

if ($testRun.status -eq "success") {
    Write-Host "✓ Test passed!" -ForegroundColor Green
} else {
    Write-Host "✗ Test failed" -ForegroundColor Red
}

