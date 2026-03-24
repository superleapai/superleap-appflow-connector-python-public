# Superleap API Reference

REST API reference for pulling data from Superleap directly, without Amazon AppFlow.


## Base URL

```
{baseURL}/api/v1/appflow/
```

Where `{baseURL}` is your custom domain or `https://app.superleap.com`.

All endpoints are prefixed with `/api/v1/appflow/`.


## Authentication

All requests require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```


## Common Headers

| Header            | Value              | When                 |
|-------------------|--------------------|----------------------|
| `Authorization`   | `Bearer <api-key>` | All requests         |
| `Content-Type`    | `application/json` | POST requests        |
| `Accept-Encoding` | `gzip`             | POST requests (optional) |


---


## Endpoints

### 1. Verify Credentials

Test that your API key is valid.

```
GET /api/v1/appflow/verify/
```

**Example:**

```bash
curl -X GET "{baseURL}/api/v1/appflow/verify/" \
  -H "Authorization: Bearer <your-api-key>"
```

**Response (200):**

```json
{
  "status": "ok"
}
```

---

### 2. List Entities

Discover available data objects (e.g. contacts, companies).

```
POST /api/v1/appflow/objects/list/
```

**Request Body:** Empty JSON object `{}` or no body.

**Example:**

```bash
curl -X POST "{baseURL}/api/v1/appflow/objects/list/" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (200):**

```json
{
  "success": true,
  "data": [
    {
      "entity_identifier": "contacts",
      "label": "Contacts",
      "description": "",
      "has_nested_entities": false,
      "is_writable": false
    },
    {
      "entity_identifier": "companies",
      "label": "Companies",
      "description": "",
      "has_nested_entities": false,
      "is_writable": false
    }
  ]
}
```

**Entity Fields:**

| Field                  | Type    | Description                               |
|------------------------|---------|-------------------------------------------|
| `entity_identifier`    | string  | Unique ID — use this in other API calls   |
| `label`                | string  | Human-readable name                       |
| `description`          | string  | Entity description                        |
| `has_nested_entities`  | boolean | Whether entity contains child objects     |
| `is_writable`          | boolean | Whether entity supports writes            |

---

### 3. Describe Entity

Get the field-level schema for a specific entity.

```
GET /api/v1/appflow/objects/{entity_identifier}/
```

**Example:**

```bash
curl -X GET "{baseURL}/api/v1/appflow/objects/lead/" \
  -H "Authorization: Bearer <your-api-key>"
```

**Response (200):**

```json
{
  "success": true,
  "data": {
    "entity_identifier": "lead",
    "label": "Lead",
    "description": "",
    "has_nested_entities": false,
    "is_writable": false,
    "fields": [
      {
        "field_name": "id",
        "data_type": "String",
        "data_type_label": "varchar",
        "label": "Record id",
        "description": "",
        "is_primary_key": true,
        "is_deprecated": false,
        "read_properties": {
          "is_retrievable": true,
          "is_nullable": false,
          "is_queryable": false,
          "is_timestamp_field_for_incremental_queries": false
        }
      },
      {
        "field_name": "email",
        "data_type": "String",
        "data_type_label": "email",
        "label": "Email",
        "description": "",
        "is_primary_key": false,
        "is_deprecated": false,
        "read_properties": {
          "is_retrievable": true,
          "is_nullable": true,
          "is_queryable": false,
          "is_timestamp_field_for_incremental_queries": false
        }
      },
      {
        "field_name": "created_at",
        "data_type": "DateTime",
        "data_type_label": "timestamp",
        "label": "Created at",
        "description": "",
        "is_primary_key": false,
        "is_deprecated": false,
        "read_properties": {
          "is_retrievable": true,
          "is_nullable": true,
          "is_queryable": false,
          "is_timestamp_field_for_incremental_queries": true
        }
      },
      {
        "field_name": "updated_at",
        "data_type": "DateTime",
        "data_type_label": "timestamp",
        "label": "Updated at",
        "description": "",
        "is_primary_key": false,
        "is_deprecated": false,
        "read_properties": {
          "is_retrievable": true,
          "is_nullable": true,
          "is_queryable": false,
          "is_timestamp_field_for_incremental_queries": true
        }
      }
    ]
  }
}
```

**Field Properties:**

| Field                | Type    | Description                                    |
|----------------------|---------|------------------------------------------------|
| `field_name`         | string  | Field identifier — use in queries              |
| `data_type`          | string  | One of: `String`, `Integer`, `Float`, `Boolean`, `DateTime` |
| `data_type_label`    | string  | Source column type (e.g. `varchar`, `email`, `timestamp`, `bool`, `phone`, `relation`, `text`, `date`, `enum`) |
| `label`              | string  | Human-readable field name                      |
| `description`        | string  | Field description (empty string if not set)    |
| `is_primary_key`     | boolean | Whether this is the unique identifier          |
| `is_deprecated`      | boolean | Whether this field is archived/deprecated      |
| `default_value`      | string  | Present only when a default is configured (omitted otherwise) |

**Read Properties** (nested under each field):

| Field                                          | Type    | Description                                         |
|------------------------------------------------|---------|-----------------------------------------------------|
| `is_retrievable`                               | boolean | Can be selected in query results                                             |
| `is_nullable`                                  | boolean | Field may be null in responses                                               |
| `is_queryable`                                 | boolean | Can be used in filter expressions                                            |
| `is_timestamp_field_for_incremental_queries`   | boolean | Can be used for incremental sync (`created_at`, `updated_at`, `deleted_at`)  |

---

### 4. Query Records

Fetch records from an entity with optional filtering and pagination.

```
POST /api/v1/appflow/objects/{entity_identifier}/records/
```

**Request Body:**

| Field                | Type          | Required | Description                           |
|----------------------|---------------|----------|---------------------------------------|
| `query.fields`       | array[string] | Yes      | Fields to return in each record       |
| `query.filter`       | object        | No       | Filter conditions (see below)         |
| `next_token`         | string        | No       | Pagination token from previous response |

**Example — fetch all records:**

```bash
curl -X POST "{baseURL}/api/v1/appflow/objects/lead/records/" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "fields": ["name", "email", "updated_at"]
    }
  }'
```

**Example — with filter:**

```bash
curl -X POST "{baseURL}/api/v1/appflow/objects/lead/records/" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "fields": ["name", "email"],
      "filter": {
        "and": [
          {
            "field": "updated_at",
            "operator": "gte",
            "value": 1757134404000
          }
        ]
      }
    },
    "next_token": null
  }'
```

**Response (200):**

```json
{
  "success": true,
  "data": {
    "records": [
      {
        "email": null,
        "id": "xk40vL_CrqDIiR6",
        "name": "Alice Johnson",
        "updated_at": "2025-11-05T18:45:22.372Z"
      },
      {
        "email": "bob@example.com",
        "id": "xk40vL_lFM1am8Z",
        "name": "Bob Wilson",
        "updated_at": "2025-12-08T12:10:36.458Z"
      }
    ],
    "next_token": "eyJpZCI6InhrNDB2TF9xeUNuS1V6bCIsIm51bWJlcl9vZl9yZWNvcmRzIjozMDAwfQ=="
  }
}
```

> **Note:** The `id` field is always included in query results, even if not listed in `query.fields`.

**Response Fields:**

| Field             | Type           | Description                                          |
|-------------------|----------------|------------------------------------------------------|
| `data.records`    | array[object]  | Records matching the query. DateTime fields are returned as ISO 8601 strings. |
| `data.next_token` | string or null | Pass in next request to get more results; null = done |

---


## Filtering

Filters use an `and` array of conditions. Each condition specifies a field, operator, and value.

### Filter Structure

```json
{
  "filter": {
    "and": [
      { "field": "...", "operator": "...", "value": "..." },
      { "field": "...", "operator": "...", "value": "..." }
    ]
  }
}
```

### Operators

| Operator   | Description                | Value Type        | Example                                                    |
|------------|----------------------------|-------------------|------------------------------------------------------------|
| `eq`       | Equal to                   | string / number   | `{"field": "status", "operator": "eq", "value": "active"}` |
| `neq`      | Not equal to               | string / number   | `{"field": "status", "operator": "neq", "value": "closed"}`|
| `gt`       | Greater than               | number / timestamp| `{"field": "amount", "operator": "gt", "value": 100}`      |
| `gte`      | Greater than or equal      | number / timestamp| `{"field": "updated_at", "operator": "gte", "value": 1694808790000}` |
| `lt`       | Less than                  | number / timestamp| `{"field": "amount", "operator": "lt", "value": 500}`      |
| `lte`      | Less than or equal         | number / timestamp| `{"field": "updated_at", "operator": "lte", "value": 1694895190000}` |
| `contains` | Substring match            | string            | `{"field": "name", "operator": "contains", "value": "%John%"}` |
| `leq`      | Case-insensitive equal     | string            | `{"field": "email", "operator": "leq", "value": "test@example.com"}` |
| `in`       | Value in list              | array             | `{"field": "status", "operator": "in", "value": ["active", "pending"]}` |

### Timestamps

Timestamps in **filter values** must be **epoch milliseconds** (not ISO strings). However, DateTime fields in **response records** are returned as ISO 8601 strings (e.g. `"2025-11-05T18:45:22.372Z"`).

| ISO 8601                      | Epoch Milliseconds |
|-------------------------------|--------------------|
| `2024-09-16T00:00:00.000Z`   | `1726444800000`    |
| `2025-01-01T00:00:00.000Z`   | `1735689600000`    |

---


## Pagination

Pagination is **token-based**. To iterate through all records:

1. Make the initial request (without `next_token` or with `next_token: null`).
2. If the response contains a non-null `next_token`, pass it in the next request.
3. Repeat until `next_token` is `null` or absent.

```python
import requests

url = "{baseURL}/api/v1/appflow/objects/contacts/records/"
headers = {
    "Authorization": "Bearer <your-api-key>",
    "Content-Type": "application/json"
}

all_records = []
next_token = None

while True:
    body = {
        "query": {
            "fields": ["name", "email", "updated_at"]
        },
        "next_token": next_token
    }

    resp = requests.post(url, json=body, headers=headers)
    data = resp.json()["data"]

    all_records.extend(data["records"])

    next_token = data.get("next_token")
    if not next_token:
        break

print(f"Fetched {len(all_records)} records")
```

---


## Incremental Sync

To pull only records modified since a given point in time, filter on a timestamp field (typically `updated_at`) that has `is_timestamp_field_for_incremental_queries: true` in the entity schema.

```bash
curl -X POST "{baseURL}/api/v1/appflow/objects/contacts/records/" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "fields": ["name", "email", "updated_at"],
      "filter": {
        "and": [
          {
            "field": "updated_at",
            "operator": "gte",
            "value": 1694808790000
          }
        ]
      }
    }
  }'
```

Store the current timestamp before each sync run. On the next run, use it as the `gte` value to pull only new/modified records.

---


## Error Responses

| Status | Meaning              | Example Body                               |
|--------|----------------------|--------------------------------------------|
| 200    | Success              | `{"success": true, "data": ...}`           |
| 400    | Bad request          | `{"error": "Invalid query format"}`        |
| 401    | Invalid API key      | `{"error": "Invalid or expired API key"}`  |
| 403    | Access denied        | `{"error": "Forbidden"}`                   |
| 500    | Server error         | `{"error": "Internal server error"}`       |

---


## Recommended Practices

- **Retry on failure:** Retry failed requests up to 3 times with a 1-second delay between attempts.
- **Use incremental sync:** Filter by `updated_at` to avoid pulling the full dataset on every run.
- **Select only needed fields:** Pass only the fields you need in `query.fields` to reduce response size.
- **Handle pagination:** Always check for `next_token` in responses — a single request may not return all records.
- **Connection timeouts:** Use a 30-second connection timeout and a 600-second (10-minute) read timeout for large queries.
