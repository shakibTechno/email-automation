# Contact Management API Documentation

## Overview

The Contact Management module provides comprehensive functionality for managing email marketing contacts, including CRUD operations, bulk operations, CSV import/export, tagging, and duplicate detection.

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication

All endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Contacts

#### 1. List Contacts

**Endpoint:** `GET /api/v1/contacts/`

**Description:** Retrieve a paginated list of contacts with filtering, searching, and sorting.

**Query Parameters:**

- `page` (integer): Page number for pagination (default: 1)
- `page_size` (integer): Number of items per page (default: 20)
- `search` (string): Search across email, name, company, phone
- `email` (string): Filter by email (case-insensitive contains)
- `first_name` (string): Filter by first name
- `last_name` (string): Filter by last name
- `company` (string): Filter by company
- `is_subscribed` (boolean): Filter by subscription status
- `is_verified` (boolean): Filter by verification status
- `engagement_level` (string): Filter by engagement level (high, medium, low, none)
- `source` (string): Filter by source (manual, import, api, form, integration)
- `tags` (uuid[]): Filter by tag IDs
- `tag_names` (string): Filter by tag names (comma-separated)
- `created_after` (datetime): Filter contacts created after date
- `created_before` (datetime): Filter contacts created before date
- `lead_score_min` (integer): Minimum lead score
- `lead_score_max` (integer): Maximum lead score
- `ordering` (string): Sort field (prefix with - for descending)

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/?search=john&is_subscribed=true&ordering=-created_at" \
  -H "Authorization: Bearer <token>"
```

**Example Response:**

```json
{
  "count": 50,
  "next": "http://localhost:8000/api/v1/contacts/?page=2",
  "previous": null,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "company": "Acme Inc",
      "phone": "+1234567890",
      "is_subscribed": true,
      "engagement_level": "high",
      "lead_score": 85,
      "tags": [],
      "created_at": "2024-02-05T10:30:00.000Z",
      "last_activity_at": "2024-02-05T15:30:00.000Z"
    }
  ]
}
```

---

#### 2. Create Contact

**Endpoint:** `POST /api/v1/contacts/`

**Description:** Create a new contact.

**Request Body:**

```json
{
  "email": "newcontact@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+1234567890",
  "company": "Tech Corp",
  "job_title": "Marketing Manager",
  "lead_score": 50,
  "engagement_level": "medium",
  "is_subscribed": true,
  "custom_fields": {
    "industry": "Technology",
    "website": "https://example.com"
  },
  "source": "manual",
  "tags": ["tag-uuid-1", "tag-uuid-2"]
}
```

**Response:** `201 Created`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174001",
  "email": "newcontact@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "full_name": "Jane Smith",
  "phone": "+1234567890",
  "company": "Tech Corp",
  "job_title": "Marketing Manager",
  "lead_score": 50,
  "engagement_level": "medium",
  "is_subscribed": true,
  "is_verified": false,
  "unsubscribed_at": null,
  "bounced_at": null,
  "custom_fields": {
    "industry": "Technology",
    "website": "https://example.com"
  },
  "source": "manual",
  "last_activity_at": null,
  "tags": ["tag-uuid-1", "tag-uuid-2"],
  "tag_details": [],
  "created_at": "2024-02-05T10:30:00.000Z",
  "updated_at": "2024-02-05T10:30:00.000Z"
}
```

---

#### 3. Retrieve Contact

**Endpoint:** `GET /api/v1/contacts/{id}/`

**Description:** Retrieve detailed information about a specific contact.

**Response:** `200 OK`

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "company": "Acme Inc",
  "job_title": "CEO",
  "lead_score": 85,
  "engagement_level": "high",
  "is_subscribed": true,
  "is_verified": true,
  "unsubscribed_at": null,
  "bounced_at": null,
  "custom_fields": {
    "industry": "Technology",
    "website": "https://acme.com"
  },
  "source": "manual",
  "last_activity_at": "2024-02-05T15:30:00.000Z",
  "tags": [],
  "tag_details": [
    {
      "id": "tag-uuid-1",
      "name": "VIP",
      "color": "purple",
      "description": "VIP customers",
      "created_at": "2024-02-01T10:00:00.000Z",
      "updated_at": "2024-02-01T10:00:00.000Z"
    }
  ],
  "created_at": "2024-02-05T10:30:00.000Z",
  "updated_at": "2024-02-05T15:30:00.000Z"
}
```

---

#### 4. Update Contact

**Endpoint:** `PUT /api/v1/contacts/{id}/` or `PATCH /api/v1/contacts/{id}/`

**Description:** Update a contact (PUT for full update, PATCH for partial).

**Request Body (PATCH):**

```json
{
  "first_name": "Updated Name",
  "lead_score": 90,
  "engagement_level": "high"
}
```

**Response:** `200 OK` (same as Create Contact response)

---

#### 5. Delete Contact

**Endpoint:** `DELETE /api/v1/contacts/{id}/`

**Description:** Soft delete a contact.

**Response:** `204 No Content`

---

#### 6. Bulk Delete Contacts

**Endpoint:** `POST /api/v1/contacts/bulk_delete/`

**Description:** Delete multiple contacts at once.

**Request Body:**

```json
{
  "contact_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "123e4567-e89b-12d3-a456-426614174001"
  ]
}
```

**Response:** `200 OK`

```json
{
  "message": "2 contacts deleted successfully",
  "deleted_count": 2
}
```

---

#### 7. Bulk Tag Contacts

**Endpoint:** `POST /api/v1/contacts/bulk_tag/`

**Description:** Add or remove tags from multiple contacts.

**Request Body:**

```json
{
  "contact_ids": [
    "contact-uuid-1",
    "contact-uuid-2"
  ],
  "tag_ids": [
    "tag-uuid-1",
    "tag-uuid-2"
  ],
  "action": "add"  // or "remove"
}
```

**Response:** `200 OK`

```json
{
  "message": "Tags added to 2 contacts",
  "contact_count": 2,
  "tag_count": 2
}
```

---

#### 8. Export Contacts

**Endpoint:** `GET /api/v1/contacts/export/`

**Description:** Export contacts to CSV file.

**Query Parameters:**

- `include_tags` (boolean): Include tags in export (default: false)
- All filtering parameters from List Contacts

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/export/?include_tags=true&is_subscribed=true" \
  -H "Authorization: Bearer <token>" \
  -o contacts.csv
```

**Response:** CSV file download

---

#### 9. Import Contacts

**Endpoint:** `POST /api/v1/contacts/import_csv/`

**Description:** Import contacts from CSV file.

**Request Body (multipart/form-data):**

- `file` (file): CSV file to import
- `field_mapping` (JSON, optional): Custom field mapping
- `skip_duplicates` (boolean, optional): Skip duplicate emails (default: true)
- `update_existing` (boolean, optional): Update existing contacts (default: false)

**Example Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/contacts/import_csv/" \
  -H "Authorization: Bearer <token>" \
  -F "file=@contacts.csv" \
  -F "skip_duplicates=true" \
  -F "update_existing=false"
```

**CSV Format:**

```csv
email,first_name,last_name,phone,company,job_title
john@example.com,John,Doe,+1234567890,Acme Inc,CEO
jane@example.com,Jane,Smith,+0987654321,Tech Corp,CTO
```

**Response:** `200 OK`

```json
{
  "message": "Import completed",
  "results": {
    "imported": 45,
    "updated": 3,
    "skipped": 2,
    "errors": [
      {
        "row": 5,
        "error": "Email is required"
      }
    ]
  }
}
```

---

#### 10. Find Duplicates

**Endpoint:** `GET /api/v1/contacts/duplicates/`

**Description:** Find contacts with duplicate emails.

**Response:** `200 OK`

```json
{
  "duplicate_groups": [
    {
      "email": "duplicate@example.com",
      "count": 2,
      "contacts": [
        {
          "id": "contact-uuid-1",
          "email": "duplicate@example.com",
          "first_name": "First",
          "created_at": "2024-02-01T10:00:00.000Z"
        },
        {
          "id": "contact-uuid-2",
          "email": "duplicate@example.com",
          "first_name": "Second",
          "created_at": "2024-02-02T10:00:00.000Z"
        }
      ]
    }
  ],
  "total_groups": 1
}
```

---

### Tags

#### 1. List Tags

**Endpoint:** `GET /api/v1/tags/`

**Description:** Retrieve all tags.

**Response:** `200 OK`

```json
[
  {
    "id": "tag-uuid-1",
    "name": "VIP",
    "color": "purple",
    "description": "VIP customers",
    "created_at": "2024-02-01T10:00:00.000Z",
    "updated_at": "2024-02-01T10:00:00.000Z"
  }
]
```

---

#### 2. Create Tag

**Endpoint:** `POST /api/v1/tags/`

**Request Body:**

```json
{
  "name": "Newsletter",
  "color": "blue",
  "description": "Newsletter subscribers"
}
```

**Response:** `201 Created`

---

#### 3. Update Tag

**Endpoint:** `PUT /api/v1/tags/{id}/` or `PATCH /api/v1/tags/{id}/`

---

#### 4. Delete Tag

**Endpoint:** `DELETE /api/v1/tags/{id}/`

---

### Custom Fields

#### 1. List Custom Fields

**Endpoint:** `GET /api/v1/custom-fields/`

**Response:** `200 OK`

```json
[
  {
    "id": "field-uuid-1",
    "name": "Department",
    "field_type": "text",
    "is_required": false,
    "default_value": "",
    "dropdown_options": [],
    "help_text": "Employee department",
    "created_at": "2024-02-01T10:00:00.000Z",
    "updated_at": "2024-02-01T10:00:00.000Z"
  }
]
```

---

#### 2. Create Custom Field

**Endpoint:** `POST /api/v1/custom-fields/`

**Request Body:**

```json
{
  "name": "Status",
  "field_type": "dropdown",
  "is_required": true,
  "dropdown_options": ["New", "Active", "Inactive"],
  "help_text": "Customer status"
}
```

**Field Types:**

- `text`: Text field
- `number`: Numeric field
- `date`: Date field
- `boolean`: Boolean field
- `dropdown`: Dropdown with predefined options

**Response:** `201 Created`

---

## Error Responses

All error responses follow this format:

```json
{
  "error": true,
  "message": "Error description",
  "details": {
    "field_name": ["Error message"]
  },
  "status_code": 400
}
```

**Common Error Codes:**

- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Testing the API

### 1. Get Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

### 2. Create a Contact

```bash
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "company": "Test Company"
  }'
```

### 3. List Contacts

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Export Contacts

```bash
curl -X GET "http://localhost:8000/api/v1/contacts/export/" \
  -H "Authorization: Bearer <access_token>" \
  -o contacts.csv
```

---

## Pagination

All list endpoints support pagination:

**Request:**

```
GET /api/v1/contacts/?page=2&page_size=50
```

**Response includes:**

- `count`: Total number of items
- `next`: URL for next page (null if last page)
- `previous`: URL for previous page (null if first page)
- `results`: Array of items

---

## Filtering Examples

### Search contacts by keyword

```
GET /api/v1/contacts/?search=john
```

### Filter by subscription status

```
GET /api/v1/contacts/?is_subscribed=true
```

### Filter by engagement level

```
GET /api/v1/contacts/?engagement_level=high
```

### Filter by tags

```
GET /api/v1/contacts/?tags=tag-uuid-1,tag-uuid-2
```

### Filter by date range

```
GET /api/v1/contacts/?created_after=2024-01-01&created_before=2024-12-31
```

### Combine multiple filters

```
GET /api/v1/contacts/?is_subscribed=true&engagement_level=high&company=Acme
```

---

## Sorting

Use the `ordering` parameter to sort results:

```
GET /api/v1/contacts/?ordering=-created_at
```

Available sort fields:

- `email`
- `first_name`
- `last_name`
- `company`
- `lead_score`
- `engagement_level`
- `created_at`
- `last_activity_at`

Prefix with `-` for descending order.
