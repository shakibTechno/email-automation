# Email Marketing Automation Platform - Frontend

A modern, production-ready React frontend application for an email marketing automation platform with complete authentication and contact management features.

## Features

### Authentication Module
- **Login**: Email/password authentication with "Remember me" option
- **Register**: User registration with password strength indicator
- **Forgot Password**: Password reset functionality
- **Profile Management**: View and edit user profile, change password

### Contact Management Module
- **Contact List**: Paginated table with search, filters, and sorting
- **Create/Edit/View Contacts**: Full CRUD operations
- **Tag Management**: Create, edit, and assign tags to contacts
- **Bulk Operations**: Select and delete multiple contacts
- **Import/Export**: CSV import and export functionality
- **Advanced Filtering**: Filter by status, engagement level, tags

### UI/UX Features
- Responsive design (mobile-first)
- Modern shadcn/ui components
- Toast notifications for user feedback
- Loading states and error handling
- Empty states for better UX
- Confirmation dialogs for destructive actions

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router v6** - Client-side routing
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **Tailwind CSS** - Utility-first CSS
- **shadcn/ui** - UI component library
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **Axios** - HTTP client
- **Sonner** - Toast notifications
- **Lucide React** - Icon library
- **PapaParse** - CSV parsing

## Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running (default: http://localhost:8000)

## Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**

   Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

   Update the API URL if needed:
   ```env
   VITE_API_URL=http://localhost:8000/api
   VITE_APP_NAME=Email Marketing Platform
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── src/
│   ├── api/                    # API service layer
│   │   ├── client.ts          # Axios instance with interceptors
│   │   ├── auth.ts            # Authentication endpoints
│   │   ├── contacts.ts        # Contact endpoints
│   │   ├── tags.ts            # Tag endpoints
│   │   └── customFields.ts    # Custom field endpoints
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── layout/            # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   ├── AuthLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── auth/              # Auth components
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   └── contacts/          # Contact components
│   │       ├── ContactTable.tsx
│   │       ├── ContactForm.tsx
│   │       └── TagSelector.tsx
│   ├── pages/
│   │   ├── auth/              # Auth pages
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── ForgotPasswordPage.tsx
│   │   ├── contacts/          # Contact pages
│   │   │   ├── ContactListPage.tsx
│   │   │   ├── ContactCreatePage.tsx
│   │   │   ├── ContactEditPage.tsx
│   │   │   ├── ContactDetailPage.tsx
│   │   │   └── TagManagementPage.tsx
│   │   └── ProfilePage.tsx
│   ├── stores/
│   │   └── authStore.ts       # Zustand auth store
│   ├── hooks/
│   │   ├── useAuth.ts         # Auth hook
│   │   ├── useContacts.ts     # Contacts hook
│   │   └── useTags.ts         # Tags hook
│   ├── types/
│   │   ├── auth.ts            # Auth types
│   │   ├── contact.ts         # Contact types
│   │   └── api.ts             # API types
│   ├── lib/
│   │   └── utils.ts           # Utility functions
│   ├── App.tsx                # Main app component
│   ├── main.tsx               # Entry point
│   └── index.css              # Global styles
├── public/                     # Static assets
├── index.html                  # HTML template
├── package.json               # Dependencies
├── vite.config.ts             # Vite configuration
├── tsconfig.json              # TypeScript configuration
├── tailwind.config.js         # Tailwind configuration
└── README.md                  # This file
```

## Key Features Explained

### Authentication Flow
1. Users can register with email, password, and organization details
2. Login with email/password (with remember me option)
3. JWT tokens stored in localStorage
4. Automatic token refresh on API calls
5. Protected routes redirect to login if not authenticated
6. Profile management with password change

### Contact Management
1. **List View**: Paginated table with search, filters, sorting
2. **Create/Edit**: Form with validation, tag selection
3. **Detail View**: Complete contact information display
4. **Bulk Actions**: Select multiple contacts for deletion
5. **Import**: CSV file upload with field mapping
6. **Export**: Download contacts as CSV
7. **Tags**: Create and assign colored tags for organization

### API Integration
- Axios instance with request/response interceptors
- Automatic token attachment to requests
- Global error handling
- Request retries on failure
- Proper TypeScript typing for all endpoints

### State Management
- **Zustand**: Auth state (user, tokens, organization)
- **TanStack Query**: Server state (contacts, tags) with caching
- Optimistic updates for better UX
- Automatic cache invalidation

### Form Handling
- React Hook Form for form state management
- Zod schemas for validation
- Real-time error display
- Password strength indicator
- Async validation support

## API Endpoints Expected

The frontend expects the following API endpoints:

### Auth
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/change-password` - Change password
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile

### Contacts
- `GET /api/contacts` - List contacts (with filters, pagination)
- `GET /api/contacts/:id` - Get single contact
- `POST /api/contacts` - Create contact
- `PUT /api/contacts/:id` - Update contact
- `DELETE /api/contacts/:id` - Delete contact
- `POST /api/contacts/bulk` - Bulk operations
- `GET /api/contacts/export` - Export as CSV
- `POST /api/contacts/import` - Import from CSV

### Tags
- `GET /api/tags` - List all tags
- `GET /api/tags/:id` - Get single tag
- `POST /api/tags` - Create tag
- `PUT /api/tags/:id` - Update tag
- `DELETE /api/tags/:id` - Delete tag

## Customization

### Colors
Update Tailwind colors in `tailwind.config.js` and CSS variables in `src/index.css`

### API Base URL
Update `VITE_API_URL` in `.env.local`

### Add New Pages
1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/layout/Sidebar.tsx`

## Production Build

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Preview the build:**
   ```bash
   npm run preview
   ```

3. **Deploy:**
   - Upload the `dist` folder to your hosting provider
   - Configure environment variables for production API URL
   - Set up proper routing (all routes should serve `index.html`)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Follow the existing code structure
2. Use TypeScript for all new files
3. Add proper type definitions
4. Follow React best practices (hooks, functional components)
5. Ensure responsive design
6. Add error handling

## Troubleshooting

### CORS Issues
Make sure your backend API has CORS properly configured to allow requests from `http://localhost:3000`

### Authentication Not Working
1. Check that API_URL is correct in `.env.local`
2. Verify backend is running
3. Clear localStorage and try again
4. Check browser console for errors

### Build Errors
1. Delete `node_modules` and `package-lock.json`
2. Run `npm install` again
3. Make sure Node.js version is 16+

## License

MIT License - feel free to use this project for your own purposes.

## Support

For issues or questions, please open an issue on the repository.
