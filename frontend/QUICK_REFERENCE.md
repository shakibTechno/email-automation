# Quick Reference Card

## 🚀 Start Development
```bash
cd E:\Projects\Email-Automation\frontend
npm run dev
```
**URL**: http://localhost:3000

## 🔑 Default Configuration
- **API URL**: http://localhost:8000/api
- **Dev Port**: 3000
- **Build Output**: dist/

## 📁 Key Files to Know

### Configuration
- `vite.config.ts` - Build configuration
- `.env.local` - Environment variables
- `tailwind.config.js` - Styling configuration

### Entry Points
- `src/main.tsx` - Application entry
- `src/App.tsx` - Main app with routing
- `index.html` - HTML template

### State Management
- `src/stores/authStore.ts` - Authentication state
- `src/hooks/useAuth.ts` - Auth operations
- `src/hooks/useContacts.ts` - Contact operations
- `src/hooks/useTags.ts` - Tag operations

### API Services
- `src/api/client.ts` - Axios instance
- `src/api/auth.ts` - Auth API calls
- `src/api/contacts.ts` - Contact API calls
- `src/api/tags.ts` - Tag API calls

## 🎨 Component Library Locations

### UI Components (shadcn/ui)
`src/components/ui/`
- button.tsx, input.tsx, label.tsx
- card.tsx, badge.tsx, dialog.tsx
- select.tsx, checkbox.tsx, tabs.tsx
- dropdown-menu.tsx, textarea.tsx

### Layout Components
`src/components/layout/`
- AppLayout.tsx - Main app layout
- Sidebar.tsx - Navigation sidebar
- Header.tsx - Top navigation
- AuthLayout.tsx - Auth page layout

### Feature Components
`src/components/auth/` - Login, Register forms
`src/components/contacts/` - Contact table, form, tag selector

## 🛣️ Routes Map

```
/login              → LoginPage
/register           → RegisterPage
/forgot-password    → ForgotPasswordPage

Protected Routes:
/                   → Redirects to /contacts
/contacts           → ContactListPage
/contacts/new       → ContactCreatePage
/contacts/tags      → TagManagementPage
/contacts/:id       → ContactDetailPage
/contacts/:id/edit  → ContactEditPage
/profile            → ProfilePage
/dashboard          → Placeholder
/campaigns          → Placeholder
/automations        → Placeholder
/forms              → Placeholder
/analytics          → Placeholder
/settings           → Placeholder
```

## 🎯 Common Tasks

### Add a New Page
1. Create page in `src/pages/`
2. Add route in `src/App.tsx`
3. Add nav link in `src/components/layout/Sidebar.tsx`

### Add a New API Endpoint
1. Add function to relevant file in `src/api/`
2. Add types in `src/types/`
3. Use in component with TanStack Query or custom hook

### Create a New Form
1. Define Zod schema
2. Use React Hook Form with zodResolver
3. Add validation messages
4. Handle submission with try-catch

### Add a New UI Component
1. Add to `src/components/ui/` (shadcn style)
2. Use Tailwind classes
3. Export from component file
4. Import where needed

## 🔧 NPM Scripts
```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## 📦 Key Dependencies

**Core**
- react, react-dom (^18.2.0)
- typescript (^5.2.2)
- vite (^5.0.8)

**Routing & State**
- react-router-dom (^6.20.0)
- @tanstack/react-query (^5.17.0)
- zustand (^4.4.7)

**Forms & Validation**
- react-hook-form (^7.49.2)
- zod (^3.22.4)
- @hookform/resolvers (^3.3.3)

**UI & Styling**
- tailwindcss (^3.4.0)
- lucide-react (^0.300.0)
- @radix-ui/* (various)
- sonner (^1.3.1)

**Data**
- axios (^1.6.2)
- papaparse (^5.4.1)

## 🎨 Color Scheme (Tailwind)

**Primary Colors**
- Primary: Blue (#3B82F6 area)
- Destructive: Red
- Secondary: Gray
- Muted: Light gray

**Tag Colors** (in TagManagementPage)
- #3B82F6, #10B981, #F59E0B
- #EF4444, #8B5CF6, #EC4899
- #14B8A6, #F97316, #6366F1, #84CC16

## 📊 Data Flow

```
User Action
   ↓
React Component
   ↓
Custom Hook (useAuth, useContacts, useTags)
   ↓
TanStack Query / Zustand
   ↓
API Service (auth.ts, contacts.ts, tags.ts)
   ↓
Axios Client (with interceptors)
   ↓
Backend API
   ↓
Response → Cache → UI Update
```

## 🔐 Authentication Flow

```
1. User submits login form
2. useAuth.login() called
3. authApi.login() makes API call
4. On success:
   - Store user, org, token
   - Save token to localStorage
   - TanStack Query invalidates queries
   - Navigate to /contacts
5. On error:
   - Show toast notification
   - Keep user on login page
```

## 🚨 Common Errors & Solutions

**Error: Cannot find module '@/...'**
→ Check tsconfig.json has path aliases configured

**Error: Module not found**
→ Run `npm install` again

**Error: Port 3000 in use**
→ Vite will auto-try 3001, 3002, etc.

**Error: CORS issues**
→ Configure backend CORS for http://localhost:3000

**Error: 401 Unauthorized**
→ Check token in localStorage, may need to re-login

## 📝 Quick Code Snippets

### Create New Protected Route
```typescript
// In App.tsx
<Route path="/new-page" element={<NewPage />} />
```

### Add API Call
```typescript
// In src/api/myApi.ts
export const myApi = {
  getData: async () => {
    const response = await apiClient.get('/endpoint');
    return response.data;
  },
};
```

### Use API in Component
```typescript
const { data, isLoading } = useQuery({
  queryKey: ['myData'],
  queryFn: myApi.getData,
});
```

### Show Toast Notification
```typescript
import { toast } from 'sonner';
toast.success('Action completed!');
toast.error('Something went wrong');
```

## 🎯 Testing Checklist

- [ ] Register new account
- [ ] Login with credentials
- [ ] Create a contact
- [ ] Edit a contact
- [ ] Delete a contact
- [ ] Search contacts
- [ ] Filter by status
- [ ] Sort by column
- [ ] Create tags
- [ ] Assign tags to contact
- [ ] Import CSV (use public/sample-contacts.csv)
- [ ] Export CSV
- [ ] Bulk select and delete
- [ ] Update profile
- [ ] Change password
- [ ] Logout and login again

## 📚 Documentation Files

- `README.md` - Full documentation
- `SETUP.md` - Setup guide
- `FRONTEND_COMPLETE.md` - Feature overview
- `DELIVERABLES.md` - Complete deliverables list
- `QUICK_REFERENCE.md` - This file

## 💡 Tips

- Use TypeScript for type safety
- Check browser console for errors
- Use React DevTools for debugging
- Check Network tab for API calls
- Clear localStorage if auth issues
- Read inline comments in code
- Follow existing patterns when adding features

---

**Need Help?** Check the full README.md or SETUP.md files!
