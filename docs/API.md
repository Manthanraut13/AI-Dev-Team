```markdown
# API Reference

All endpoints are prefixed with `/api/v1`.  
Authentication is performed via **Bearer JWT** token in the `Authorization` header.

## Authentication

### Register a new user
`POST /api/v1/auth/register`

**Request**
```json
{
  "email": "user@example.com",
  "password": "StrongP@ssw0rd"
}
```

**Response (201)**
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-08-21T12:34:56Z"
}
```

### Login
`POST /api/v1/auth/login`

**Request**
```json
{
  "email": "user@example.com",
  "password": "StrongP@ssw0rd"
}
```

**Response (200)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Request password‑reset email
`POST /api/v1/auth/password-reset/request`

**Request**
```json
{
  "email": "user@example.com"
}
```

**Response (200)**
```json
{
  "detail": "Password reset email sent if the address exists."
}
```

### Reset password (using token from email)
`POST /api/v1/auth/password-reset/confirm`

**Request**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewStr0ngP@ss"
}
```

**Response (200)**
```json
{
  "detail": "Password has been reset successfully."
}
```

## Categories

### Create a category
`POST /api/v1/categories`

**Headers**
```
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "name": "Work"
}
```

**Response (201)**
```json
{
  "id": 3,
  "name": "Work",
  "owner_id": 1,
  "created_at": "2026-08-21T13:00:00Z"
}
```

### List user categories
`GET /api/v1/categories`

**Headers**
```
Authorization: Bearer <access_token>
```

**Response (200)**
```json
[
  {
    "id": 1,
    "name": "Personal",
    "owner_id": 1,
    "created_at": "2026-08-20T09:15:00Z"
  },
  {
    "id": 3,
    "name": "Work",
    "owner_id": 1,
    "created_at": "2026-08-21T13:00:00Z"
  }
]
```

## Tasks

### Create a task
`POST /api/v1/tasks`

**Headers**
```
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "title": "Buy groceries",
  "description": "Milk, Bread, Eggs",
  "due_date": "2026-08-25",
  "category_id": 1
}
```

**Response (201)**
```json
{
  "id": 42,
  "title": "Buy groceries",
  "description": "Milk, Bread, Eggs",
  "due_date": "2026-08-25",
  "completed": false,
  "owner_id": 1,
  "category_id": 1,
  "created_at": "2026-08-21T14:20:00Z",
  "updated_at": "2026-08-21T14:20:00Z"
}
```

### Get a single task
`GET /api/v1/tasks/{task_id}`

**Headers**
```
Authorization: Bearer <access_token>
```

**Response (200)**
```json
{
  "id": 42,
  "title": "Buy groceries",
  "description": "Milk, Bread, Eggs",
  "due_date": "2026-08-25",
  "completed": false,
  "owner_id": 1,
  "category_id": 1,
  "created_at": "2026-08-21T14:20:00Z",
  "updated_at": "2026-08-21T14:20:00Z"
}
```

### Update a task
`PUT /api/v1/tasks/{task_id}`

**Headers**
```
Authorization: Bearer <access_token>
```

**Request** (any subset of fields may be provided)
```json
{
  "title": "Buy groceries and fruits",
  "description": "Milk, Bread, Eggs, Apples",
  "due_date": "2026-08-26",
  "category_id": 2,
  "completed": true
}
```

**Response (200)**
```json
{
  "id": 42,
  "title": "Buy groceries and fruits",
  "description": "Milk, Bread, Eggs, Apples",
  "due_date": "2026-08-26",
  "completed": true,
  "owner_id": 1,
  "category_id": 2,
  "created_at": "2026-08-21T14:20:00Z",
  "updated_at": "2026-08-21T15:05:00Z"
}
```

### Delete a task
`DELETE /api/v1/tasks/{task_id}`

**Headers**
```
Authorization: Bearer <access_token>
```

**Response (204)**
_No content_

### Toggle completion status
`POST /api/v1/tasks/{task_id}/toggle`

**Headers**
```
Authorization: Bearer <access_token>
```

**Response (200)**
```json
{
  "id": 42,
  "completed": true,
  "updated_at": "2026-08-21T15:10:00Z"
}
```

### List all tasks for the authenticated user
`GET /api/v1/tasks`

**Headers**
```
Authorization: Bearer <access_token>
```

**Optional query parameters**
- `completed` – filter by completion status (`true`/`false`)
- `category_id` – filter by category
- `due_before` – ISO date string to get tasks due before a date
- `due_after` – ISO date string to get tasks due after a date

**Response (200)**
```json
[
  {
    "id": 42,
    "title": "Buy groceries and fruits",
    "description": "Milk, Bread, Eggs, Apples",
    "due_date": "2026-08-26",
    "completed": true,
    "owner_id": 1,
    "category_id": 2,
    "created_at": "2026-08-21T14:20:00Z",
    "updated_at": "2026-08-21T15:05:00Z"
  },
  {
    "id": 43,
    "title": "Finish report",
    "description": "Quarterly financial report",
    "due_date": "2026-08-30",
    "completed": false,
    "owner_id": 1,
    "category_id": 3,
    "created_at": "2026-08-21T14:45:00Z",
    "updated_at": "2026-08-21T14:45:00Z"
  }
]
```

## Error Responses

All error responses follow this schema:

```json
{
  "detail": "Human readable error message."
}
```

Typical status codes:
- `400` – Validation error / bad request
- `401` – Unauthorized (missing/invalid token)
- `403` – Forbidden (accessing another user's resource)
- `404` – Not found
- `422` – Unprocessable Entity (FastAPI validation errors)

---

*All timestamps are in ISO‑8601 UTC format.*  
```