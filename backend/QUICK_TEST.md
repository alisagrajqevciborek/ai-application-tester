# Quick Testing Guide

## Step 1: Setup Database

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py makemigrations applications
.\.venv\Scripts\python.exe manage.py migrate
```

## Step 2: Create a User

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

## Step 3: Start Server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## Step 4: Run the Test Script

Open a new terminal and run:

```powershell
cd backend
.\test_browser_automation.ps1
```

**Note:** Update the email and password in `test_browser_automation.ps1` first!

## Alternative: Manual API Testing

### 1. Login
```powershell
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST -ContentType "application/json" `
    -Body '{"email":"your@email.com","password":"yourpassword"}'
$token = $login.access
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
```

### 2. Create Application
```powershell
$app = Invoke-RestMethod -Uri "http://localhost:8000/api/applications" `
    -Method POST -Headers $headers `
    -Body '{"name":"Test App","url":"https://example.com"}'
```

### 3. Create Test Run
```powershell
$testRun = Invoke-RestMethod -Uri "http://localhost:8000/api/applications/test-runs/" `
    -Method POST -Headers $headers `
    -Body "{`"application`":$($app.id),`"test_type`":`"functional`"}"
```

### 4. Check Status
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/applications/test-runs/$($testRun.id)" `
    -Method GET -Headers $headers
```

## Test Types Available

- `"functional"` - Functional testing
- `"regression"` - Regression testing  
- `"performance"` - Performance testing
- `"accessibility"` - Accessibility testing

