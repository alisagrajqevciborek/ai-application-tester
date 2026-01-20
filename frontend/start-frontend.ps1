# Script to kill any process on port 3000 and start frontend
Write-Host "Checking port 3000..." -ForegroundColor Cyan

# Kill all node processes
Write-Host "Stopping all Node.js processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Remove Next.js lock files
Write-Host "Cleaning Next.js lock files..." -ForegroundColor Yellow
if (Test-Path ".next\dev\lock") {
    Remove-Item -Path ".next\dev\lock" -Force -ErrorAction SilentlyContinue
}
if (Test-Path ".next") {
    Remove-Item -Path ".next" -Recurse -Force -ErrorAction SilentlyContinue
}

# Find process using port 3000
$port = netstat -ano | findstr :3000 | Select-String "LISTENING"
if ($port) {
    $line = $port[0].Line
    $pid = ($line -split '\s+')[-1]
    Write-Host "Found process $pid using port 3000. Stopping it..." -ForegroundColor Yellow
    taskkill /F /PID $pid 2>$null
    Start-Sleep -Seconds 2
}

# Verify port is free
$stillRunning = netstat -ano | findstr :3000 | Select-String "LISTENING"
if ($stillRunning) {
    Write-Host "Warning: Port 3000 may still be in use" -ForegroundColor Yellow
} else {
    Write-Host "Port 3000 is free!" -ForegroundColor Green
}

# Start frontend on port 3000
Write-Host "Starting frontend on port 3000..." -ForegroundColor Cyan
npm run dev

