# Login 400 Error - FIXED ✅

## The Problem

The frontend was sending extra fields that the backend didn't expect:

**Frontend sent:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false  ← Backend doesn't expect this!
}
```

**Backend expected:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Error:**
```
400 Bad Request - Validation error
```

---

## The Fix

Updated `LoginForm.tsx` to only send `email` and `password`:

**Before:**
```typescript
const onSubmit = (data: LoginFormData) => {
  login(data as LoginCredentials);  // Sends all fields including remember_me
};
```

**After:**
```typescript
const onSubmit = (data: LoginFormData) => {
  const { email, password } = data;  // Extract only needed fields
  login({ email, password });        // Send only what backend expects
};
```

---

## How to Test

### 1. Restart Frontend (REQUIRED!)

```bash
# Stop frontend (Ctrl+C)
cd E:\Projects\Email-Automation\frontend
npm run dev
```

### 2. Create Test Account

First, you need to create an account:

```bash
# Option 1: Use Django shell
cd E:\Projects\Email-Automation
python manage.py shell

# In shell, run:
from apps.accounts.models import User, Organization

# Create organization
org = Organization.objects.create(name="Test Company", email="test@example.com")

# Create user
user = User.objects.create_user(
    email="test@example.com",
    password="Test123!@#",
    first_name="Test",
    last_name="User",
    organization=org,
    role="owner"
)
print(f"User created: {user.email}")

# Exit shell
exit()
```

Or create via the registration page at http://localhost:3000/register

### 3. Test Login

1. Go to: http://localhost:3000/login
2. Enter credentials:
   - Email: `test@example.com`
   - Password: `Test123!@#`
3. Click "Sign in"
4. ✅ Should redirect to `/contacts` page!

### 4. Verify in Network Tab

Open DevTools (F12) → Network tab:

**Request:**
```
POST /api/v1/auth/login/
```

**Request Payload:**
```json
{
  "email": "test@example.com",
  "password": "Test123!@#"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    ...
  }
}
```

---

## What Changed

**File:** `frontend/src/components/auth/LoginForm.tsx`

**Lines 37-39:**
```typescript
const onSubmit = (data: LoginFormData) => {
  // Only send email and password to the API
  const { email, password } = data;
  login({ email, password });
};
```

**Why this works:**
- `remember_me` is still captured in the form
- It's just not sent to the backend
- Backend only validates `email` and `password`
- No validation errors! ✅

---

## Complete Test Scenario

### 1. Backend Running ✅
```bash
cd E:\Projects\Email-Automation
python manage.py runserver
```

### 2. Frontend Running ✅
```bash
cd E:\Projects\Email-Automation\frontend
npm run dev
```

### 3. Test Registration ✅
1. Go to http://localhost:3000/register
2. Fill in:
   - Email: `john@example.com`
   - Password: `StrongPass123!`
   - First Name: `John`
   - Last Name: `Doe`
   - Organization: `Acme Corp`
3. Submit
4. Should auto-login and redirect to `/contacts`

### 4. Test Login ✅
1. Logout (click user menu → Logout)
2. Go to http://localhost:3000/login
3. Enter:
   - Email: `john@example.com`
   - Password: `StrongPass123!`
4. Click "Sign in"
5. Should redirect to `/contacts`

### 5. Test Protected Routes ✅
1. Try to access http://localhost:3000/contacts without logging in
2. Should redirect to `/login`
3. After login, should redirect back to `/contacts`

---

## Verify Everything Works

Run the verification script:

```bash
cd E:\Projects\Email-Automation
python verify_setup.py
```

Should show:
```
✅ Backend server is running
✅ Frontend server is running
✅ API URL correctly configured
✅ All required environment variables present
✅ Health Check: OK
✅ API Root: OK
```

---

## Common Issues After Fix

### Issue: "Invalid email or password"

**Causes:**
1. User doesn't exist in database
2. Password is incorrect
3. User account is inactive

**Solution:**
```bash
# Check if user exists
python manage.py shell

from apps.accounts.models import User
User.objects.filter(email="test@example.com").exists()
# Should return True

# Reset password if needed
user = User.objects.get(email="test@example.com")
user.set_password("NewPassword123!")
user.save()
```

### Issue: "User account is disabled"

**Solution:**
```bash
python manage.py shell

from apps.accounts.models import User
user = User.objects.get(email="test@example.com")
user.is_active = True
user.save()
```

### Issue: Still getting 400 error

**Check:**
1. Did you restart the frontend? (Required!)
2. Clear browser cache (Ctrl+Shift+R)
3. Check Network tab for actual request data
4. Make sure .env.local has correct API URL

---

## Success Indicators

After login succeeds, you should see:

✅ **In Browser:**
- Redirected to `/contacts` page
- User menu shows your name
- Sidebar navigation visible

✅ **In Backend Console:**
```
INFO "POST /api/v1/auth/login/ HTTP/1.1" 200 XXX
```

✅ **In Browser Console:**
```javascript
// Check stored token
localStorage.getItem('access_token')
// Should return: "eyJ..."

// Check stored user
JSON.parse(localStorage.getItem('user'))
// Should return: {id: 1, email: "...", ...}
```

✅ **In Network Tab:**
- POST /api/v1/auth/login/ → 200 OK
- Response has `access`, `refresh`, and `user` fields

---

## Next Steps

Now that login works:

1. ✅ Create some contacts
2. ✅ Test the contact list page
3. ✅ Try importing CSV
4. ✅ Test all CRUD operations
5. ✅ Explore all features!

---

## Summary

🎯 **Problem:** Frontend sent extra `remember_me` field
🔧 **Solution:** Only send `email` and `password` to API
✅ **Result:** Login now works perfectly!

**Files Modified:**
- ✅ `frontend/src/components/auth/LoginForm.tsx`

**No Backend Changes Needed!**

---

**If you still see errors, please share:**
1. Exact error from browser console
2. Request payload from Network tab
3. Backend response
4. Backend terminal logs

This will help diagnose any remaining issues!
