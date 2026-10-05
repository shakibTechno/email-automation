# Team Assignment Feature — Implementation Checklist

Allows org admins to assign contacts, deals, tasks, and activities to team members.

---

## Part A — Contact Assignment (new feature)

### Backend
- [x] Add `assigned_to` ForeignKey (nullable, SET_NULL) to `Contact` model in `apps/contacts/models.py`
- [x] Create migration for the new field
- [x] Expose `assigned_to` (write) and `assigned_to_name` (read) in `ContactSerializer` and `ContactListSerializer`
- [x] Add `assigned_to` filter to `ContactFilter` in `apps/contacts/filters.py`

### Frontend
- [x] Add `assigned_to` and `assigned_to_name` fields to `Contact` type in `src/types/contact.ts`
- [x] Add assignee `MemberSelect` to the contact create/edit form
- [x] Add **Assigned To** column and filter to `ContactListPage`

---

## Part B — Wire Assignee Picker into Existing CRM Forms

Backend is already complete. Frontend only.

- [x] Create reusable `MemberSelect` component at `src/components/crm/MemberSelect.tsx`
- [x] Add `MemberSelect` to `DealFormDialog` (maps to `assigned_to`)
- [x] Add `MemberSelect` to `TaskFormDialog` (maps to `assigned_to`)
- [x] Add `MemberSelect` to `ActivityFormDialog` (maps to `assigned_to`)

---

## Part C — "My Work" Quick Filter

No backend changes needed — filter endpoints already support `?assigned_to=<uuid>`.

- [x] Add **My Deals** toggle filter on CRM pipeline/deal list page
- [x] Add **My Tasks** toggle filter on CRM task list
