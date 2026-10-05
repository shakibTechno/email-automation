# Contact Management Testing Guide

## Prerequisites

1. Ensure the Django server is running:
```bash
cd E:\Projects\Email-Automation
python manage.py runserver
```

2. Create a superuser (if not already created):
```bash
python manage.py createsuperuser
```

3. Seed test data:
```bash
python manage.py seed_contacts --count=50
```

---

## Running Tests

### Run All Tests

```bash
# Run all tests
python manage.py test apps.contacts

# Run with verbose output
python manage.py test apps.contacts --verbosity=2

# Run with coverage
pytest apps/contacts/tests/ --cov=apps.contacts --cov-report=html
```

### Run Specific Test Files

```bash
# Model tests
python manage.py test apps.contacts.tests.test_models

# View tests
python manage.py test apps.contacts.tests.test_views

# Service tests
python manage.py test apps.contacts.tests.test_services
```

### Run Specific Test Classes

```bash
python manage.py test apps.contacts.tests.test_models.ContactModelTest
```

---

## Manual API Testing

### Step 1: Get Authentication Token

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User",
    "organization_name": "Test Organization"
  }'

# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPass123!"
  }'
```

**Save the access token from the response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### Step 2: Test Contact CRUD Operations

#### Create a Contact

```bash
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "company": "Acme Corporation",
    "job_title": "Marketing Director",
    "lead_score": 75,
    "engagement_level": "high",
    "custom_fields": {
      "industry": "Technology",
      "website": "https://acme.com"
    }
  }'
```

#### List Contacts

```bash
curl -X GET http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer <access_token>"
```

#### Get Contact Details

```bash
# Replace {contact_id} with the ID from create response
curl -X GET http://localhost:8000/api/v1/contacts/{contact_id}/ \
  -H "Authorization: Bearer <access_token>"
```

#### Update Contact

```bash
curl -X PATCH http://localhost:8000/api/v1/contacts/{contact_id}/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_score": 90,
    "engagement_level": "high"
  }'
```

#### Delete Contact

```bash
curl -X DELETE http://localhost:8000/api/v1/contacts/{contact_id}/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 3: Test Tag Operations

#### Create Tags

```bash
# Create VIP tag
curl -X POST http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "VIP",
    "color": "purple",
    "description": "VIP customers"
  }'

# Create Newsletter tag
curl -X POST http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Newsletter",
    "color": "blue",
    "description": "Newsletter subscribers"
  }'
```

#### List Tags

```bash
curl -X GET http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 4: Test Custom Fields

#### Create Custom Field

```bash
# Text field
curl -X POST http://localhost:8000/api/v1/custom-fields/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Department",
    "field_type": "text",
    "is_required": false,
    "help_text": "Employee department"
  }'

# Dropdown field
curl -X POST http://localhost:8000/api/v1/custom-fields/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Status",
    "field_type": "dropdown",
    "dropdown_options": ["New", "Active", "Inactive"],
    "is_required": true
  }'
```

---

### Step 5: Test Search and Filtering

#### Search Contacts

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?search=john" \
  -H "Authorization: Bearer <access_token>"
```

#### Filter by Subscription Status

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?is_subscribed=true" \
  -H "Authorization: Bearer <access_token>"
```

#### Filter by Engagement Level

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?engagement_level=high" \
  -H "Authorization: Bearer <access_token>"
```

#### Filter by Company

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?company=Acme" \
  -H "Authorization: Bearer <access_token>"
```

#### Combined Filters

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?is_subscribed=true&engagement_level=high&ordering=-lead_score" \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 6: Test Bulk Operations

#### Bulk Tag Contacts

```bash
# First, get some contact IDs and tag IDs from previous responses
curl -X POST http://localhost:8000/api/v1/contacts/bulk_tag/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_ids": ["contact-uuid-1", "contact-uuid-2"],
    "tag_ids": ["tag-uuid-1"],
    "action": "add"
  }'
```

#### Bulk Delete Contacts

```bash
curl -X POST http://localhost:8000/api/v1/contacts/bulk_delete/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_ids": ["contact-uuid-1", "contact-uuid-2"]
  }'
```

---

### Step 7: Test CSV Import/Export

#### Export Contacts

```bash
# Export all contacts
curl -X GET http://localhost:8000/api/v1/contacts/export/ \
  -H "Authorization: Bearer <access_token>" \
  -o contacts.csv

# Export with tags
curl -X GET "http://localhost:8000/api/v1/contacts/export/?include_tags=true" \
  -H "Authorization: Bearer <access_token>" \
  -o contacts_with_tags.csv

# Export filtered contacts
curl -X GET "http://localhost:8000/api/v1/contacts/export/?is_subscribed=true&engagement_level=high" \
  -H "Authorization: Bearer <access_token>" \
  -o high_engagement_contacts.csv
```

#### Create Sample CSV

Create a file named `sample_contacts.csv`:

```csv
email,first_name,last_name,phone,company,job_title
alice@example.com,Alice,Johnson,+1111111111,Tech Inc,CEO
bob@example.com,Bob,Williams,+2222222222,StartupCo,CTO
carol@example.com,Carol,Davis,+3333333333,Enterprise Ltd,CMO
```

#### Import Contacts

```bash
curl -X POST http://localhost:8000/api/v1/contacts/import_csv/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@sample_contacts.csv" \
  -F "skip_duplicates=true"
```

---

### Step 8: Test Duplicate Detection

#### Find Duplicates

```bash
curl -X GET http://localhost:8000/api/v1/contacts/duplicates/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Using Postman

### Import Collection

1. Download the Postman collection:
   - Visit: http://localhost:8000/api/schema/
   - Save the schema

2. In Postman:
   - Click "Import"
   - Select the schema file
   - Collection will be created automatically

### Set Environment Variables

1. Create new environment in Postman
2. Add variables:
   - `base_url`: `http://localhost:8000/api/v1`
   - `access_token`: (will be set after login)

3. Use variables in requests:
   - URL: `{{base_url}}/contacts/`
   - Header: `Authorization: Bearer {{access_token}}`

---

## Testing with Python Requests

Create a file `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "email": "testuser@example.com",
    "password": "TestPass123!"
})
token = response.json()["access"]

# Set headers
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Create contact
contact_data = {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "company": "Test Corp"
}
response = requests.post(f"{BASE_URL}/contacts/", json=contact_data, headers=headers)
print(f"Create Contact: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# List contacts
response = requests.get(f"{BASE_URL}/contacts/", headers=headers)
print(f"\nList Contacts: {response.status_code}")
print(f"Total: {response.json()['count']}")

# Search contacts
response = requests.get(f"{BASE_URL}/contacts/?search=test", headers=headers)
print(f"\nSearch Results: {response.json()['count']}")
```

Run the script:
```bash
python test_api.py
```

---

## API Documentation

### Interactive API Documentation

Visit these URLs in your browser:

1. **Swagger UI:**
   ```
   http://localhost:8000/api/docs/
   ```
   - Interactive API documentation
   - Test endpoints directly from browser
   - View request/response schemas

2. **ReDoc:**
   ```
   http://localhost:8000/api/redoc/
   ```
   - Clean, readable API documentation
   - Better for reading and understanding

3. **OpenAPI Schema:**
   ```
   http://localhost:8000/api/schema/
   ```
   - Raw OpenAPI schema (JSON)
   - Import into Postman or other tools

---

## Common Testing Scenarios

### Scenario 1: Complete Contact Lifecycle

1. Create contact
2. Add tags to contact
3. Update contact details
4. Update custom fields
5. Export contact data
6. Soft delete contact

### Scenario 2: Bulk Operations

1. Create multiple contacts
2. Bulk tag contacts
3. Bulk export
4. Bulk delete

### Scenario 3: Import Flow

1. Prepare CSV file
2. Import contacts
3. Handle duplicates
4. Verify import results
5. Fix errors and re-import

### Scenario 4: Duplicate Management

1. Create duplicate contacts
2. Find duplicates
3. Review duplicate groups
4. Merge or delete duplicates

---

## Expected Test Results

### All Tests Should Pass

```
Ran 30 tests in 5.234s

OK
```

### Coverage Should Be >90%

```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
apps/contacts/models.py             120      5    96%
apps/contacts/views.py              180      8    96%
apps/contacts/serializers.py        150      6    96%
apps/contacts/services.py           200     10    95%
apps/contacts/filters.py             80      4    95%
-----------------------------------------------------
TOTAL                               730     33    95%
```

---

## Troubleshooting

### Issue: 401 Unauthorized

**Solution:** Check if token is valid and included in Authorization header

```bash
# Get fresh token
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Issue: 400 Bad Request - Email already exists

**Solution:** Email must be unique per organization. Use different email or update existing contact.

### Issue: Import fails with validation errors

**Solution:** Check CSV format and ensure required fields (email) are present.

---

## Next Steps

1. Run all automated tests
2. Test each API endpoint manually
3. Test with different user roles
4. Test error scenarios
5. Test with large datasets
6. Performance testing with bulk operations
