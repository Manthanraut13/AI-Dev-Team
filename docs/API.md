```markdown
# API Reference

All endpoints are prefixed with `/api/v1`.  
Authentication is performed via **Bearer JWT** token in the `Authorization` header.

## Authentication

### Register a new user
**POST** `/api/v1/auth/register`

```json
{
  "email": "jane.doe@example.com",
  "password": "StrongP@ssw0rd!"
}
```

**Response (201 Created)**
```json
{
  "id": 1,
  "email": "jane.doe@example.com",
  "is_active": true,
  "created_at": "2026-08-23T12:34:56Z"
}
```

---

### Login
**POST** `/api/v1/auth/login`

```json
{
  "email": "jane.doe@example.com",
  "password": "StrongP@ssw0rd!"
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Request password‑reset email
**POST** `/api/v1/auth/password-reset/request`

```json
{
  "email": "jane.doe@example.com"
}
```

**Response (200 OK)**
```json
{
  "detail": "Password reset email sent if the address exists."
}
```

---

### Confirm password reset
**POST** `/api/v1/auth/password-reset/confirm`

```json
{
  "token": "reset-token-from-email",
  "new_password": "NewStr0ngP@ss!"
}
```

**Response (200 OK)**
```json
{
  "detail": "Password has been reset successfully."
}
```

## Categories

### Create a category
**POST** `/api/v1/categories`

*Headers*
```
Authorization: Bearer <access_token>
```

```json
{
  "name": "Work"
}
```

**Response (201 Created)**
```json
{
  "id": 3,
  "name": "Work",
  "owner_id": 1,
  "created_at": "2026-08-23T13:00:00Z"
}
```

---

### List categories
**GET** `/api/v1/categories`

*Headers*
```
Authorization: Bearer <access_token>
```

**Response (200 OK)**
```json
[
  {
    "id": 1,
    "name": "Personal",
    "owner_id": 1,
    "created_at": "2026-08-22T09:15:00Z"
  },
  {
    "id": 3,
    "name": "Work",
    "owner_id": 1,
    "created_at": "2026-08-23T13:00:00Z"
  }
]
```

## Tasks

### Create a task
**POST** `/api/v1/tasks`

*Headers*
```
Authorization: Bearer <access_token>
```

```json
{
  "title": "Finish report",
  "description": "Complete the quarterly financial report",
  "due_date": "2026-09-01",
  "category_id": 3
}
```

**Response (201 Created)**
```json
{
  "id": 42,
  "title": "Finish report",
  "description": "Complete the quarterly financial report",
  "due_date": "2026-09-01",
  "completed": false,
  "category_id": 3,
  "owner_id": 1,
  "created_at": "2026-08-23T14:20:00Z",
  "updated_at": "2026-08-23T14:20:00Z"
}
```

---

### List all tasks for the authenticated user
**GET** `/api/v1/tasks`

*Headers*
```
Authorization: Bearer <access_token>
```

**Response (200 OK)**
```json
[
  {
    "id": 42,
    "title": "Finish report",
    "description": "Complete the quarterly financial report",
    "due_date": "2026-09-01",
    "completed": false,
    "category_id": 3,
    "owner_id": 1,
    "created_at": "2026-08-23T14:20:00Z",
    "updated_at": "2026-08-23T14:20:00Z"
  },
  {
    "id": 43,
    "title": "Buy groceries",
    "description": "Milk, eggs, bread",
    "due_date": "2026-08-24",
    "completed": true,
    "category_id": 1,
    "owner_id": 1,
    "created_at": "2026-08-22T10:05:00Z",
    "updated_at": "2026-08-22T12:00:00Z"
  }
]
```

---

### Retrieve a single task
**GET** `/api/v1/tasks/{task_id}`

*Headers*
```
Authorization: Bearer <access_token>
```

**Response (200 OK)**
```json
{
  "id": 42,
  "title": "Finish report",
  "description": "Complete the quarterly financial report",
  "due_date": "2026-09-01",
  "completed": false,
  "category_id": 3,
  "owner_id": 1,
  "created_at": "2026-08-23T14:20:00Z",
  "updated_at": "2026-08-23T14:20:00Z"
}
```

---

### Update a task
**PUT** `/api/v1/tasks/{task_id}`

*Headers*
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "title": "Finish annual report",
  "description": "Include latest market analysis",
  "due_date": "2026-09-05",
  "category_id": 3,
  "completed": false
}
```

**Response (200 OK)**
```json
{
  "id": 42,
  "title": "Finish annual report",
  "description": "Include latest market analysis",
  "due_date": "2026-09-05",
  "completed": false,
  "category_id": 3,
  "owner_id": 1,
  "created_at": "2026-08-23T14:20:00Z",
  "updated_at": "2026-08-23T15:10:00Z"
}
```

---

### Delete a task
**DELETE** `/api/v1/tasks/{task_id}`

*Headers*
```
Authorization: Bearer <access_token>
```

**Response (204 No Content)**
_No body_

---

### Toggle completion status
**PATCH** `/api/v1/tasks/{task_id}/toggle`

*Headers*
```
Authorization: Bearer <access_token>
```

**Response (200 OK)**
```json
{
  "id": 42,
  "completed": true,
  "updated_at": "2026-08-23T16:00:00Z"
}
```

## Error Handling

All error responses follow the JSON:API error object format.

**Example – Validation error (422)**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

**Example – Unauthorized (401)**
```json
{
  "detail": "Could not validate credentials"
}
```

**Example – Not found (404)**
```json
{
  "detail": "Task not found"
}
```

---

*All timestamps are in ISO‑8601 UTC format.*  
*All dates (e.g., `due_date`) are in `YYYY-MM-DD` format.*  

```