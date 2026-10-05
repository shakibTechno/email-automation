# Contact Management - Quick Reference

## Common API Requests

### Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Set token (use in all subsequent requests)
TOKEN="your-access-token-here"
```

### Contacts

```bash
# List all contacts
curl -X GET http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer $TOKEN"

# Search contacts
curl -X GET "http://localhost:8000/api/v1/contacts/?search=john" \
  -H "Authorization: Bearer $TOKEN"

# Filter subscribed contacts
curl -X GET "http://localhost:8000/api/v1/contacts/?is_subscribed=true" \
  -H "Authorization: Bearer $TOKEN"

# Create contact
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Inc"
  }'

# Update contact
curl -X PATCH http://localhost:8000/api/v1/contacts/{id}/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lead_score": 90}'

# Delete contact
curl -X DELETE http://localhost:8000/api/v1/contacts/{id}/ \
  -H "Authorization: Bearer $TOKEN"

# Export contacts
curl -X GET "http://localhost:8000/api/v1/contacts/export/" \
  -H "Authorization: Bearer $TOKEN" \
  -o contacts.csv

# Import contacts
curl -X POST http://localhost:8000/api/v1/contacts/import_csv/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contacts.csv"

# Bulk delete
curl -X POST http://localhost:8000/api/v1/contacts/bulk_delete/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact_ids": ["id1", "id2"]}'

# Bulk tag
curl -X POST http://localhost:8000/api/v1/contacts/bulk_tag/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_ids": ["id1", "id2"],
    "tag_ids": ["tag-id"],
    "action": "add"
  }'

# Find duplicates
curl -X GET http://localhost:8000/api/v1/contacts/duplicates/ \
  -H "Authorization: Bearer $TOKEN"
```

### Tags

```bash
# List tags
curl -X GET http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer $TOKEN"

# Create tag
curl -X POST http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "VIP",
    "color": "purple",
    "description": "VIP customers"
  }'
```

### Custom Fields

```bash
# List custom fields
curl -X GET http://localhost:8000/api/v1/custom-fields/ \
  -H "Authorization: Bearer $TOKEN"

# Create custom field
curl -X POST http://localhost:8000/api/v1/custom-fields/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Department",
    "field_type": "text",
    "is_required": false
  }'
```

## Filter Examples

```bash
# By subscription status
?is_subscribed=true

# By engagement level
?engagement_level=high

# By company
?company=Acme

# By tags
?tags=tag-uuid-1,tag-uuid-2

# By date range
?created_after=2024-01-01&created_before=2024-12-31

# By lead score range
?lead_score_min=50&lead_score_max=100

# Combined
?is_subscribed=true&engagement_level=high&ordering=-lead_score
```

## Sorting

```bash
# Sort by email
?ordering=email

# Sort by creation date (newest first)
?ordering=-created_at

# Sort by lead score (highest first)
?ordering=-lead_score

# Sort by name
?ordering=first_name,last_name
```

## Pagination

```bash
# Page 2 with 50 items per page
?page=2&page_size=50
```

## Python Examples

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
token = "your-access-token"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# List contacts
response = requests.get(f"{BASE_URL}/contacts/", headers=headers)
contacts = response.json()

# Create contact
data = {
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
}
response = requests.post(f"{BASE_URL}/contacts/", json=data, headers=headers)

# Search
params = {"search": "john", "is_subscribed": True}
response = requests.get(f"{BASE_URL}/contacts/", headers=headers, params=params)

# Export
response = requests.get(f"{BASE_URL}/contacts/export/", headers=headers)
with open('contacts.csv', 'wb') as f:
    f.write(response.content)

# Import
files = {'file': open('contacts.csv', 'rb')}
response = requests.post(f"{BASE_URL}/contacts/import_csv/",
                        headers={"Authorization": f"Bearer {token}"},
                        files=files)
```

## Django Shell Examples

```python
python manage.py shell

from apps.contacts.models import Contact, Tag, ContactTag, CustomField
from apps.accounts.models import Organization

# Get organization
org = Organization.objects.first()

# Create contact
contact = Contact.objects.create(
    organization=org,
    email='john@example.com',
    first_name='John',
    last_name='Doe',
    company='Acme Inc'
)

# Create tag
tag = Tag.objects.create(
    organization=org,
    name='VIP',
    color='purple'
)

# Tag a contact
ContactTag.objects.create(contact=contact, tag=tag)

# Search contacts
contacts = Contact.objects.filter(
    organization=org,
    email__icontains='john'
)

# Get all subscribed contacts
subscribed = Contact.objects.filter(
    organization=org,
    is_subscribed=True
)

# Export to CSV
from apps.contacts.services import CSVExportService
csv_content = CSVExportService.export_contacts(contacts)

# Import from CSV
from apps.contacts.services import CSVImportService
service = CSVImportService(org, user)
results = service.import_from_csv(csv_file)
```

## Management Commands

```bash
# Seed test contacts
python manage.py seed_contacts --count=50

# Seed for specific organization
python manage.py seed_contacts --count=100 --organization=my-org-slug
```

## Testing

```bash
# Run all contact tests
python manage.py test apps.contacts

# Run specific test file
python manage.py test apps.contacts.tests.test_models

# Run with coverage
pytest apps/contacts/tests/ --cov=apps.contacts

# Run specific test
python manage.py test apps.contacts.tests.test_models.ContactModelTest.test_contact_creation
```

## API Documentation

- **Swagger UI:** http://localhost:8000/api/docs/
- **ReDoc:** http://localhost:8000/api/redoc/
- **OpenAPI Schema:** http://localhost:8000/api/schema/

## Admin Interface

http://localhost:8000/admin/

- Manage contacts
- Manage tags
- Manage custom fields
- Bulk actions

## Engagement Levels

- `high` - Highly engaged contacts
- `medium` - Moderately engaged
- `low` - Low engagement
- `none` - No engagement data

## Sources

- `manual` - Manual entry
- `import` - CSV import
- `api` - API creation
- `form` - Web form
- `integration` - External integration

## Tag Colors

- `red`, `blue`, `green`, `yellow`
- `purple`, `orange`, `pink`, `gray`

## Custom Field Types

- `text` - Text field
- `number` - Numeric field
- `date` - Date field
- `boolean` - True/False field
- `dropdown` - Dropdown with options

## Common Errors

**401 Unauthorized**
```
Missing or invalid token
Solution: Login and use fresh access token
```

**400 Bad Request - Duplicate email**
```
Email already exists
Solution: Use different email or update existing contact
```

**404 Not Found**
```
Contact not found
Solution: Verify contact ID
```

**403 Forbidden**
```
Not organization member
Solution: Contact must belong to your organization
```

## Performance Tips

1. Use pagination for large datasets
2. Use filters to reduce result sets
3. Export filtered data, not all contacts
4. Use bulk operations for multiple changes
5. Import in batches (max 1000 at a time)

## Security Checklist

- ✅ Always use HTTPS in production
- ✅ Keep access tokens secure
- ✅ Don't commit .env files
- ✅ Use strong passwords
- ✅ Rotate tokens regularly
- ✅ Validate all imports
- ✅ Review exported data before sharing
