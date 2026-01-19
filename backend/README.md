# AI Application Tester - Backend

Django REST API backend for the AI-powered application testing platform.

## Technology Stack

- **Framework**: Django 5.0.1
- **API**: Django REST Framework 3.14.0
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Database**: PostgreSQL
- **Python Version**: 3.10

## Project Structure

```
backend/
├── core/                   # Django core configuration
│   ├── settings.py        # Main settings
│   ├── urls.py            # URL routing
│   ├── wsgi.py           
│   └── asgi.py
├── apps/                   # Django applications
│   ├── users/             # User authentication
│   └── applications/      # Application management
├── common/                 # Shared utilities
│   ├── permissions.py
│   ├── utils.py
│   └── ai_helpers.py      # Placeholder for future AI integration
├── manage.py
└── requirements.txt
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10
- PostgreSQL installed and running
- Git

### 2. Create PostgreSQL Database

```sql
CREATE DATABASE ai_app_tester;
CREATE USER postgres WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ai_app_tester TO postgres;
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Update the database password in `.env`:
```
DB_PASSWORD=your_actual_password
```

### 4. Install Dependencies

```bash
# Create virtual environment with Python 3.10
py -3.10 -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat

# Install packages
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication

- `POST /api/auth/login` - Login with email and password
- `POST /api/auth/logout` - Logout (blacklist refresh token)
- `GET /api/auth/me` - Get current user info

### Applications

- `GET /api/applications` - List all user's applications
- `POST /api/applications` - Create new application
- `GET /api/applications/<id>` - Get application details
- `PUT /api/applications/<id>` - Update application
- `DELETE /api/applications/<id>` - Delete application

### Admin

- `/admin/` - Django admin interface

## API Authentication

All endpoints except `/api/auth/login` require JWT authentication.

Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Database Models

### User
- email (unique, login field)
- first_name
- last_name
- password (hashed)
- is_active
- is_staff
- date_joined

### Application
- name
- url
- owner (FK to User)
- created_at
- updated_at

## Future Features (Not Yet Implemented)

The following features have placeholder comments in the code:

- **Test Execution**: Automated browser testing
- **AI Integration**: OpenAI-powered test case generation
- **Report Generation**: AI-generated bug reports
- **Background Tasks**: Celery/Redis integration
- **Screenshots**: Test result screenshots

## Development Notes

- All API responses are JSON
- JWT tokens expire after 24 hours
- Refresh tokens expire after 7 days
- CORS is configured for `http://localhost:3000` (frontend)
- Uses Django ORM only (no raw SQL)
- Each app has its own migrations

## Testing the API

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"yourpassword"}'
```

### Create Application
```bash
curl -X POST http://localhost:8000/api/applications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"My App","url":"https://example.com"}'
```

### List Applications
```bash
curl http://localhost:8000/api/applications \
  -H "Authorization: Bearer <token>"
```

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database exists

### Migration Errors
```bash
python manage.py makemigrations
python manage.py migrate
```

### Port Already in Use
```bash
python manage.py runserver 8001
```

## Git Branch

Development is done on the `feature/auth-and-apps` branch.
