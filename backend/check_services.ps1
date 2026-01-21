# Quick service check script for Windows
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Redis & Celery Service Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Redis
Write-Host "`n[1] Checking Redis..." -ForegroundColor Yellow
$redisPort = netstat -ano | findstr :6379 | findstr LISTENING
if ($redisPort) {
    Write-Host "  [OK] Redis is running on port 6379" -ForegroundColor Green
    $pid = ($redisPort -split '\s+')[-1]
    Write-Host "  Process ID: $pid" -ForegroundColor Gray
} else {
    Write-Host "  [ERROR] Redis is NOT running on port 6379" -ForegroundColor Red
    Write-Host "  Start Redis with: redis-server" -ForegroundColor Yellow
}

# Check if Redis Python package is installed
Write-Host "`n[2] Checking Redis Python package..." -ForegroundColor Yellow
$redisInstalled = pip show redis 2>$null
if ($redisInstalled) {
    Write-Host "  [OK] Redis package is installed" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Redis package NOT installed" -ForegroundColor Red
    Write-Host "  Install with: pip install redis" -ForegroundColor Yellow
}

# Check Celery
Write-Host "`n[3] Checking Celery Python package..." -ForegroundColor Yellow
$celeryInstalled = pip show celery 2>$null
if ($celeryInstalled) {
    Write-Host "  [OK] Celery package is installed" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Celery package NOT installed" -ForegroundColor Red
    Write-Host "  Install with: pip install celery" -ForegroundColor Yellow
}

# Check Celery worker process
Write-Host "`n[4] Checking Celery worker..." -ForegroundColor Yellow
$celeryProcess = Get-Process | Where-Object {$_.ProcessName -like "*celery*" -or $_.CommandLine -like "*celery*"} 2>$null
if ($celeryProcess) {
    Write-Host "  [OK] Celery worker process found" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] No Celery worker process found" -ForegroundColor Yellow
    Write-Host "  Start worker with: celery -A core worker --loglevel=info" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Run these tests for detailed info:" -ForegroundColor Cyan
Write-Host "  python test_redis_connection.py" -ForegroundColor White
Write-Host "  python test_celery_integration.py" -ForegroundColor White
Write-Host "  python test_full_integration.py" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan


