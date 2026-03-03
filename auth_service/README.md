# Django Auth Service

A modern authentication service built with Django REST Framework, featuring user management, organization support, and JWT-based authentication.

## Features

- **User Authentication**: JWT-based authentication with access and refresh tokens
- **Organization Support**: Create and manage organizations with multiple users
- **Subscription Management**: Plan-based subscription tracking (Free eSign, eSign, EDMS+)
- **Domain Authentication**: Integration with external domain auth services
- **Admin Panel**: Django admin interface for managing users, profiles, and subscriptions
- **PostgreSQL & SQLite**: Support for both databases
- **Docker Ready**: Can be containerized for deployment

## Project Structure

```
auth_service_django/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── config/                  # Django project configuration
│   ├── settings.py         # Project settings
│   ├── urls.py            # URL routing
│   ├── wsgi.py            # WSGI application
│   └── asgi.py            # ASGI application
└── accounts/               # Authentication app
    ├── models.py          # User, Profile, Subscription models
    ├── views.py           # Authentication endpoints
    ├── user_views.py      # User management endpoints
    ├── serializers.py     # DRF serializers
    ├── authentication.py  # JWT authentication
    ├── domain_auth.py     # Domain auth utilities
    ├── urls.py            # Auth routes
    ├── user_urls.py       # User routes
    ├── admin.py           # Admin configuration
    └── management/
        └── commands/
            └── create_superuser.py  # Create admin user
```

## Installation

1. **Create Virtual Environment**
   ```bash
   python -m venv env
   source env/Scripts/activate  # On Windows
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   python manage.py create_superuser --email admin@example.com --username admin --password changeme
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication

- **POST** `/auth/login` - Login with email/username and password
- **POST** `/auth/register` - Register new user or organization
- **POST** `/auth/refresh` - Refresh access token

### User Management

- **GET** `/users/` - Get all users (admin only)
- **GET** `/users/organization/{profile_id}` - Get organization users

### Organization

- **POST** `/auth/org/add-user` - Add user to organization (admin only)

## Database Models

### User
- UUID primary key
- Email (unique)
- Username (unique)
- Password (hashed with bcrypt)
- Domain authentication support
- Role management (admin, superuser)

### Profile
- Organization or individual profile
- Name and type
- One-to-many relationship with users

### Subscription
- Plan-based pricing (FREE_ESIGN, ESIGN, EDMS+)
- Status tracking (ACTIVE, INACTIVE, TRIAL, CANCELED)
- License management
- Billing interval (MONTHLY, YEARLY)

## JWT Tokens

All endpoints (except login/register) require Bearer token authentication:

```
Authorization: Bearer {access_token}
```

Access tokens expire in 60 minutes (configurable).
Refresh tokens expire in 30 days (configurable).

## Configuration

Edit `.env` file to configure:

- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `DATABASE` - Database type (sqlite or postgres)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token lifetime
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token lifetime
- `DOMAIN_AUTH_URL` - External domain authentication URL

## Testing

### Create Test User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword",
    "first_name": "Test",
    "last_name": "User",
    "plan_name": "FREE_ESIGN",
    "type": "INDIVIDUAL"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword"
  }'
```

## Production Deployment

For production:

1. Set `DEBUG=False` in `.env`
2. Use PostgreSQL database
3. Use a production WSGI server (Gunicorn, uWSGI)
4. Enable HTTPS/SSL
5. Configure ALLOWED_HOSTS
6. Use environment-specific settings
7. Set up proper logging and monitoring

Example with Gunicorn:

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## License

MIT
