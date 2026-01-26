# Fast Development Workflow (Windows)

## Problem
Running the frontend in Docker on Windows is slow due to file system virtualization overhead.

## Solution: Hybrid Setup
Run **backend in Docker**, **frontend locally**.

---

## Setup Instructions

### 1. Start Backend Services Only

```powershell
# In project root
docker-compose up backend redis celery_worker
```

This starts:
- Django backend (port 8000)
- Redis (port 6379)  
- Celery worker

### 2. Run Frontend Locally

```powershell
# In frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Frontend will run on `http://localhost:3000`

---

## Environment Variables

The frontend is already configured to connect to `http://localhost:8000/api` via:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

No changes needed!

---

## Benefits

✅ **10-20x faster** hot reload  
✅ **Instant** file changes  
✅ **Better** debugging experience  
✅ **Native** Node.js performance  

---

## Full Docker (If Needed)

If you need to run everything in Docker:

```powershell
docker-compose up
```

But expect slower performance on Windows.

---

## Troubleshooting

### Frontend can't connect to backend
- Ensure backend is running: `docker ps`
- Check backend logs: `docker logs ai_app_tester_backend`
- Verify port 8000 is accessible: `curl http://localhost:8000/api/`

### Port 3000 already in use
```powershell
# Use different port
npm run dev -- -p 3001
```

### Node modules issues
```powershell
# Clean install
rm -rf node_modules package-lock.json
npm install
```
