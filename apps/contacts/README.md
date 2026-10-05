# Contact Management Module

A comprehensive contact management system for Django email marketing automation platform.

## Features

### Core Features (18 MVP Features Implemented)

#### 1. Contact CRUD Operations
- ✅ CONT-001: Create single contact
- ✅ CONT-002: View contact details
- ✅ CONT-003: Edit contact
- ✅ CONT-004: Delete contact (soft delete)
- ✅ CONT-015: Duplicate detection

#### 2. Contact List Management
- ✅ CONT-005: List contacts with pagination (20 per page, configurable)
- ✅ CONT-006: Search by email, name, company, phone
- ✅ CONT-007: Filter by fields, tags, status
- ✅ CONT-008: Sort by various fields
- ✅ CONT-009: Bulk select operations
- ✅ CONT-010: Bulk operations (delete, tag)

#### 3. Import/Export
- ✅ CONT-011: Export to CSV
- ✅ CONT-012: Import from CSV
- ✅ CONT-013: Field mapping
- ✅ CONT-014: Import validation

#### 4. Tags System
- ✅ CONT-016: Create tags
- ✅ CONT-017: Apply/remove tags to contacts
- ✅ Bulk tagging
- ✅ Tag management (CRUD)

#### 5. Custom Fields
- ✅ CONT-018: Define custom fields (text, number, date, boolean, dropdown)
- ✅ Store custom field values in JSON
- ✅ Validate custom field data

## Project Structure

```
apps/contacts/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── filters.py            # django-filter configurations
├── models.py             # Contact, Tag, ContactTag, CustomField models
├── serializers.py        # DRF serializers
├── services.py           # Business logic (CSV, duplicates)
├── urls.py               # URL routing
├── views.py              # ViewSets and API endpoints
├── management/
│   └── commands/
│       └── seed_contacts.py  # Seed test data
└── tests/
    ├── __init__.py
    ├── test_models.py    # Model tests
    ├── test_views.py     # API endpoint tests
    └── test_services.py  # Service layer tests
```

## Models

### Contact
- **Fields:** email, first_name, last_name, phone, company, job_title, lead_score, engagement_level, is_subscribed, is_verified, custom_fields, source, last_activity_at
- **Organization-scoped:** Each contact belongs to an organization
- **Soft delete:** Contacts are soft-deleted (deleted_at)
- **Unique constraint:** email per organization

### Tag
- **Fields:** name, color, description
- **Colors:** red, blue, green, yellow, purple, orange, pink, gray
- **Organization-scoped**

### ContactTag
- **Many-to-many:** Links contacts and tags
- **Unique constraint:** One tag per contact

### CustomField
- **Field types:** text, number, date, boolean, dropdown
- **Organization-scoped**
- **Dropdown options:** Stored as JSON array

## API Endpoints

### Contacts
- `GET /api/v1/contacts/` - List contacts
- `POST /api/v1/contacts/` - Create contact
- `GET /api/v1/contacts/{id}/` - Retrieve contact
- `PUT/PATCH /api/v1/contacts/{id}/` - Update contact
- `DELETE /api/v1/contacts/{id}/` - Delete contact
- `POST /api/v1/contacts/bulk_delete/` - Bulk delete
- `POST /api/v1/contacts/bulk_tag/` - Bulk tag
- `GET /api/v1/contacts/export/` - Export CSV
- `POST /api/v1/contacts/import_csv/` - Import CSV
- `GET /api/v1/contacts/duplicates/` - Find duplicates

### Tags
- `GET /api/v1/tags/` - List tags
- `POST /api/v1/tags/` - Create tag
- `GET /api/v1/tags/{id}/` - Retrieve tag
- `PUT/PATCH /api/v1/tags/{id}/` - Update tag
- `DELETE /api/v1/tags/{id}/` - Delete tag

### Custom Fields
- `GET /api/v1/custom-fields/` - List custom fields
- `POST /api/v1/custom-fields/` - Create custom field
- `GET /api/v1/custom-fields/{id}/` - Retrieve custom field
- `PUT/PATCH /api/v1/custom-fields/{id}/` - Update custom field
- `DELETE /api/v1/custom-fields/{id}/` - Delete custom field

## Installation

1. **Add to INSTALLED_APPS:**
```python
INSTALLED_APPS = [
    # ...
    'apps.contacts',
]
```

2. **Include URLs:**
```python
urlpatterns = [
    # ...
    path('api/v1/', include('apps.contacts.urls')),
]
```

3. **Run migrations:**
```bash
python manage.py makemigrations contacts
python manage.py migrate contacts
```

4. **Seed test data (optional):**
```bash
python manage.py seed_contacts --count=50
```

## Usage Examples

### Create a Contact
```python
from apps.contacts.models import Contact
from apps.accounts.models import Organization

org = Organization.objects.first()
contact = Contact.objects.create(
    organization=org,
    email='john@example.com',
    first_name='John',
    last_name='Doe',
    company='Acme Inc',
    lead_score=75,
    engagement_level='high'
)
```

### Create a Tag
```python
from apps.contacts.models import Tag

tag = Tag.objects.create(
    organization=org,
    name='VIP',
    color='purple',
    description='VIP customers'
)
```

### Tag a Contact
```python
from apps.contacts.models import ContactTag

ContactTag.objects.create(contact=contact, tag=tag)
```

### Custom Fields
```python
# Define custom field
from apps.contacts.models import CustomField

field = CustomField.objects.create(
    organization=org,
    name='Department',
    field_type='text',
    is_required=False
)

# Add custom field value to contact
contact.custom_fields = {
    'Department': 'Sales',
    'Employee_ID': '12345'
}
contact.save()
```

### CSV Import
```python
from apps.contacts.services import CSVImportService
import io

csv_content = """email,first_name,last_name,company
john@example.com,John,Doe,Acme Inc
jane@example.com,Jane,Smith,Tech Corp"""

csv_file = io.BytesIO(csv_content.encode('utf-8'))
service = CSVImportService(organization=org, user=user)
results = service.import_from_csv(csv_file)

print(f"Imported: {results['imported']}")
print(f"Skipped: {results['skipped']}")
```

### CSV Export
```python
from apps.contacts.services import CSVExportService
from apps.contacts.models import Contact

contacts = Contact.objects.filter(organization=org)
csv_content = CSVExportService.export_contacts(contacts)

# Save to file
with open('contacts.csv', 'w') as f:
    f.write(csv_content)
```

### Find Duplicates
```python
from apps.contacts.services import DuplicateDetectionService

duplicate_groups = DuplicateDetectionService.find_duplicates_by_email(org)

for group in duplicate_groups:
    print(f"Email: {group[0].email}")
    print(f"Duplicates: {len(group)}")
```

## Filters

Available filters for contact list:

- `search` - Search across multiple fields
- `email` - Filter by email
- `first_name` - Filter by first name
- `last_name` - Filter by last name
- `company` - Filter by company
- `phone` - Filter by phone
- `is_subscribed` - Filter by subscription status
- `is_verified` - Filter by verification status
- `engagement_level` - Filter by engagement level
- `source` - Filter by source
- `tags` - Filter by tag IDs
- `tag_names` - Filter by tag names (comma-separated)
- `created_after` - Created after date
- `created_before` - Created before date
- `lead_score_min` - Minimum lead score
- `lead_score_max` - Maximum lead score
- `is_bounced` - Filter bounced contacts
- `is_unsubscribed` - Filter unsubscribed contacts

## Ordering

Available ordering fields:

- `email`
- `first_name`
- `last_name`
- `company`
- `lead_score`
- `engagement_level`
- `created_at`
- `last_activity_at`

Use `-` prefix for descending order.

## Permissions

All endpoints require:
- `IsAuthenticated` - User must be logged in
- `IsOrganizationMember` - User must belong to organization

Data is automatically scoped to user's organization.

## Testing

Run tests:
```bash
# All contact tests
python manage.py test apps.contacts

# Specific test file
python manage.py test apps.contacts.tests.test_models

# With coverage
pytest apps/contacts/tests/ --cov=apps.contacts --cov-report=html
```

## Admin Interface

Access Django admin at `/admin/` to manage:
- Contacts (with bulk actions)
- Tags (with color badges)
- Contact-Tag relationships
- Custom field definitions

## Management Commands

### Seed Contacts
```bash
# Seed 50 contacts
python manage.py seed_contacts --count=50

# Seed for specific organization
python manage.py seed_contacts --count=100 --organization=my-org-slug
```

## Dependencies

- Django >= 5.0
- djangorestframework >= 3.14
- django-filter >= 23.5
- drf-spectacular >= 0.27.0
- faker >= 20.1.0 (for seeding)

## Documentation

- **API Documentation:** See `docs/CONTACT_MANAGEMENT_API.md`
- **Testing Guide:** See `docs/TESTING_GUIDE.md`
- **Interactive API Docs:** http://localhost:8000/api/docs/

## License

Part of Email Marketing Automation Platform
