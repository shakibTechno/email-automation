# Quick Setup Guide

## Step 1: Install Dependencies
```bash
npm install
```

## Step 2: Configure Environment
The `.env.local` file is already created with default values:
```
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=Email Marketing Platform
```

Update the `VITE_API_URL` if your backend runs on a different port.

## Step 3: Start Development Server
```bash
npm run dev
```

The application will be available at: http://localhost:3000

## Step 4: Login/Register
1. Navigate to http://localhost:3000
2. You'll be redirected to the login page
3. Click "Sign up" to create a new account
4. Fill in the registration form with:
   - Email
   - Password (minimum 8 characters)
   - First Name
   - Last Name
   - Organization Name
5. After registration, you'll be automatically logged in

## Default Routes

### Public Routes
- `/login` - Login page
- `/register` - Registration page
- `/forgot-password` - Password reset page

### Protected Routes (require authentication)
- `/contacts` - Contact list (main page after login)
- `/contacts/new` - Create new contact
- `/contacts/:id` - View contact details
- `/contacts/:id/edit` - Edit contact
- `/contacts/tags` - Manage tags
- `/profile` - User profile and settings
- `/dashboard` - Dashboard (placeholder)
- `/campaigns` - Campaigns (placeholder)
- `/automations` - Automations (placeholder)
- `/forms` - Forms (placeholder)
- `/analytics` - Analytics (placeholder)
- `/settings` - Settings (placeholder)

## Features Available

### ✅ Fully Implemented
1. **Authentication**
   - User registration with validation
   - Login with email/password
   - Forgot password
   - Profile management
   - Password change
   - Session management

2. **Contact Management**
   - List contacts with pagination
   - Search contacts
   - Filter by status
   - Sort by multiple fields
   - Create new contacts
   - Edit existing contacts
   - View contact details
   - Delete contacts
   - Bulk delete
   - Import contacts from CSV
   - Export contacts to CSV

3. **Tag Management**
   - Create tags with colors
   - Edit tags
   - Delete tags
   - Assign tags to contacts
   - Filter contacts by tags

### 🚧 Placeholder (Coming Soon)
- Dashboard
- Email Campaigns
- Marketing Automations
- Landing Page Forms
- Analytics & Reports

## Testing the Application

### 1. Test Authentication
- Register a new account
- Logout and login again
- Try "Remember me" option
- Test forgot password flow
- Update profile information
- Change password

### 2. Test Contact Management
- Create a contact manually
- View contact details
- Edit contact information
- Add tags to contact
- Search for contacts
- Filter contacts by status
- Sort contacts
- Select multiple contacts
- Bulk delete contacts

### 3. Test Import/Export
- Export contacts to CSV
- Create a CSV file with headers: email, first_name, last_name, company, phone
- Import the CSV file
- Verify imported contacts appear in the list

### 4. Test Tag Management
- Navigate to Tags page
- Create multiple tags with different colors
- Edit a tag
- Delete a tag
- Go back to contacts and assign tags

## Common Issues

### Issue: Cannot connect to API
**Solution**: Make sure your backend API is running on http://localhost:8000

### Issue: CORS errors
**Solution**: Configure CORS in your backend to allow requests from http://localhost:3000

### Issue: Build errors
**Solution**:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Issue: Port 3000 already in use
**Solution**: The dev server will automatically try port 3001, 3002, etc.

## Production Build

To create a production build:
```bash
npm run build
```

The build output will be in the `dist` folder.

To preview the production build:
```bash
npm run preview
```

## Next Steps

1. Connect to your backend API
2. Test all authentication flows
3. Create some test contacts
4. Import a CSV file
5. Try all CRUD operations
6. Explore the responsive design on mobile

Enjoy your email marketing platform! 🚀
