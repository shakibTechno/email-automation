# Troubleshooting Guide - 404 Error Fix

## Quick Fix Checklist

### 1. ✅ Is the Backend Running?

**Check if Django server is running:**

```bash
# Terminal 1 - Backend
cd E:\Projects\Email-Automation
python manage.py runserver

# You should see:
# Starting development server at http://127.0.0.1:8000/
```

If not running, start it with the command above.

---

### 2. ✅ Is the Frontend Running?

**Check if React dev server is running:**

```bash
# Terminal 2 - Frontend
cd E:\Projects\Email-Automation\frontend
npm run dev

# You should see:
# VITE v5.0.0  ready in XXX ms
# ➜  Local:   http://localhost:3000/
```

If not running, start it with `npm run dev`.

---

### 3. ✅ Check Environment Variables

**Backend** - Check `E:\Projects\Email-Automation\.env`:

```env
# Should have:
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**Frontend** - Check `E:\Projects\Email-Automation\frontend\.env.local`:

```env
# Should have:
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

**If the file doesn't exist, create it!**

---

### 4. ✅ Verify Backend URLs

**Test backend endpoints directly:**

```bash
# Test health endpoint
curl http://127.0.0.1:8000/api/v1/health/health/

# Should return: {"status": "ok"}

# Test API root
curl http://127.0.0.1:8000/api/v1/

# Should return list of available endpoints
```

---

### 5. ✅ Check Browser Console

Open browser DevTools (F12) and check:

1. **Console tab** - Look for the exact 404 error
2. **Network tab** - See which URL is failing
3. **Copy the failing URL** and test it with curl

**Common 404 Issues:**

| Error URL | Problem | Solution |
|-----------|---------|----------|
| `http://localhost:3000/api/v1/...` | Frontend calling itself | Fix VITE_API_URL in .env.local |
| `http://127.0.0.1:8000/contacts/` | Missing `/api/v1/` prefix | Check API client configuration |
| `http://127.0.0.1:8000/api/contacts/` | Missing `/v1/` | Check API client configuration |
| `undefined` in URL | Environment variable not loaded | Restart frontend dev server |

---

## Step-by-Step Fix

### Step 1: Create/Update Frontend Environment File

```bash
cd E:\Projects\Email-Automation\frontend

# Create .env.local file
echo VITE_API_URL=http://127.0.0.1:8000/api/v1 > .env.local
```

Or create it manually:

**File:** `frontend/.env.local`
```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

### Step 2: Restart Frontend Server

**IMPORTANT:** After changing environment variables, you MUST restart the dev server!

```bash
# Stop the frontend (Ctrl+C)
# Then restart:
npm run dev
```

### Step 3: Verify Backend CORS Settings

**File:** `config/settings/development.py`

Make sure it has:

```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
```

### Step 4: Check API Client Configuration

**File:** `frontend/src/api/client.ts`

Should have:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Step 5: Verify Backend URLs are Registered

**Check:** `config/urls.py`

Should have:

```python
urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls')),
        path('contacts/', include('apps.contacts.urls')),
        path('tags/', include('apps.contacts.urls')),  # Tag URLs
        path('health/', include('apps.core.urls')),
    ])),
]
```

---

## Common Error Messages & Solutions

### Error: "Failed to load resource: net::ERR_CONNECTION_REFUSED"

**Problem:** Backend server is not running

**Solution:**
```bash
cd E:\Projects\Email-Automation
python manage.py runserver
```

---

### Error: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Problem:** CORS not configured properly

**Solution:**

1. Install django-cors-headers if not installed:
```bash
pip install django-cors-headers
```

2. Update `config/settings/base.py`:
```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    # ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add at top
    'django.middleware.common.CommonMiddleware',
    # ...
]
```

3. Restart backend server

---

### Error: "404 Not Found" on `/api/v1/contacts/`

**Problem:** Contacts URLs not registered

**Solution:**

Check `apps/contacts/urls.py` exists and is included in main URLs.

Create if missing:

```python
# apps/contacts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet, TagViewSet, CustomFieldViewSet

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'custom-fields', CustomFieldViewSet, basename='customfield')

urlpatterns = [
    path('', include(router.urls)),
]
```

Then ensure it's included in `config/urls.py`:

```python
path('api/v1/', include([
    path('', include('apps.contacts.urls')),  # Add this
])),
```

---

## Testing Checklist

After applying fixes, test in this order:

### 1. Test Backend Directly

```bash
# Health check
curl http://127.0.0.1:8000/api/v1/health/health/

# API root
curl http://127.0.0.1:8000/api/v1/

# Login (should work without token)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"yourpassword"}'
```

### 2. Test Frontend API Client

Open browser console and run:

```javascript
// Check environment variable
console.log(import.meta.env.VITE_API_URL);
// Should output: http://127.0.0.1:8000/api/v1

// Test API call
fetch('http://127.0.0.1:8000/api/v1/health/health/')
  .then(r => r.json())
  .then(console.log);
// Should output: {status: "ok"}
```

### 3. Test Full Authentication Flow

1. Go to http://localhost:3000/register
2. Create account
3. Check Network tab - all requests should be 200/201
4. Login
5. Go to contacts page
6. All should work without 404 errors

---

## Still Getting 404? Advanced Debugging

### 1. Check Exact URLs Being Called

In browser DevTools Network tab:
1. Click on the failed request (red, 404 status)
2. Check "Headers" tab
3. Look at "Request URL"
4. Compare with expected URL

**Expected URL format:**
```
http://127.0.0.1:8000/api/v1/contacts/
```

**Common wrong formats:**
```
http://localhost:3000/api/v1/contacts/  ❌ (wrong port)
http://127.0.0.1:8000/contacts/         ❌ (missing /api/v1/)
undefined/api/v1/contacts/              ❌ (env var not loaded)
```

### 2. Check Django URL Configuration

Run this in Django shell:

```bash
python manage.py shell

# In shell:
from django.urls import get_resolver
resolver = get_resolver()
print('\n'.join(sorted([str(p.pattern) for p in resolver.url_patterns])))
```

Should show:
```
admin/
api/v1/
```

### 3. Enable Debug Logging

**Backend** - Update `config/settings/development.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```

**Frontend** - Check API calls:

```typescript
// In api/client.ts, add logging:
client.interceptors.request.use((config) => {
  console.log('API Request:', config.method?.toUpperCase(), config.url);
  return config;
});

client.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.config?.url);
    return Promise.reject(error);
  }
);
```

### 4. Test with Postman/Thunder Client

If browser fails but curl works, it might be a browser issue:
- Clear browser cache
- Try incognito mode
- Try different browser
- Disable browser extensions

---

## Quick Reference: Correct Configuration

### Backend (.env)
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend (.env.local)
```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

### Backend Running
```bash
cd E:\Projects\Email-Automation
python manage.py runserver
# Should show: Starting development server at http://127.0.0.1:8000/
```

### Frontend Running
```bash
cd E:\Projects\Email-Automation\frontend
npm run dev
# Should show: Local: http://localhost:3000/
```

### Test URLs
- Backend: http://127.0.0.1:8000/api/v1/
- Frontend: http://localhost:3000/
- Health: http://127.0.0.1:8000/api/v1/health/health/

---

## Need More Help?

If still not working, please provide:

1. **Exact error message** from browser console
2. **Failed request URL** from Network tab
3. **Backend terminal output** when request is made
4. **Frontend .env.local** contents
5. **Backend .env** contents (without SECRET_KEY)

This will help diagnose the specific issue!
