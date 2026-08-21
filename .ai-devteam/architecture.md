# Architecture — Simple Todo App

## Detected Stack

- FastAPI
- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT
- Next.js
- React
- TypeScript
- Tailwind CSS

## API Endpoints

- **POST** `/auth/register` — Create a new user account with email and password.
- **POST** `/auth/login` — Authenticate user and return JWT access/refresh tokens.
- **POST** `/auth/logout` — Invalidate current refresh token (token blacklist).
- **POST** `/auth/password-reset/request` — Send password‑reset email with one‑time token.
- **POST** `/auth/password-reset/confirm` — Validate token and set new password.
- **GET** `/tasks` — Return paginated list of authenticated user's tasks; supports query params status, due_date, category_id for filtering.
- **POST** `/tasks` — Create a new task for the authenticated user.
- **GET** `/tasks/{task_id}` — Retrieve a single task belonging to the user.
- **PATCH** `/tasks/{task_id}` — Update any mutable field of the task (title, description, due_date, category_id, order_index).
- **DELETE** `/tasks/{task_id}` — Delete a task.
- **POST** `/tasks/{task_id}/complete` — Mark task as completed.
- **POST** `/tasks/{task_id}/uncomplete` — Mark task as not completed.
- **POST** `/tasks/reorder` — Bulk update order_index of tasks within a category to support drag‑and‑drop reordering.
- **GET** `/categories` — List all categories for the authenticated user.
- **POST** `/categories` — Create a new category.
- **PATCH** `/categories/{category_id}` — Rename a category.
- **DELETE** `/categories/{category_id}` — Delete a category and optionally cascade delete or reassign its tasks.

## Database Schema

### users
- id: UUID
- email: VARCHAR(255)
- password_hash: VARCHAR(255)
- created_at: TIMESTAMP
- is_active: BOOLEAN

### password_reset_tokens
- id: UUID
- user_id: UUID
- token: VARCHAR(255)
- expires_at: TIMESTAMP

### categories
- id: UUID
- user_id: UUID
- name: VARCHAR(100)
- created_at: TIMESTAMP

### tasks
- id: UUID
- user_id: UUID
- category_id: UUID
- title: VARCHAR(200)
- description: TEXT
- due_date: DATE
- is_completed: BOOLEAN
- order_index: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

## Folder Structure

```
backend/
  app/
    api/
      v1/
        endpoints/
        dependencies/
    core/
      config.py
      security.py
    db/
      models.py
      session.py
    schemas/
      auth.py
      task.py
      category.py
    services/
      auth.py
      task.py
      category.py
  tests/
    unit/
    integration/
frontend/
  src/
    pages/
      api/
        auth.ts
        tasks.ts
        categories.ts
    components/
      TaskList.tsx
      TaskItem.tsx
      CategoryList.tsx
    hooks/
      useAuth.ts
      useTasks.ts
    styles/
    utils/
  public/
    favicon.ico
    robots.txt
  next.config.js
  tsconfig.json
```

## Technology Decisions

1. FastAPI chosen for its async support, automatic OpenAPI generation and tight Pydantic integration, speeding up API development.
2. PostgreSQL provides strong relational guarantees needed for normalized user‑task‑category relationships and supports advanced indexing for filtering.
3. SQLAlchemy + Alembic for ORM and migrations, allowing type‑safe model definitions and versioned schema changes.
4. JWT access/refresh token flow gives stateless authentication for scalability; refresh token revocation handled via token blacklist in Redis (optional).
5. Next.js with React‑TypeScript gives server‑side rendering for SEO‑friendly pages and API route co‑location, while TypeScript adds compile‑time safety.
6. Tailwind CSS for rapid UI styling without custom CSS overhead.
7. Task ordering stored as an integer `order_index` allowing cheap reordering via bulk update; can be extended to use a linked‑list approach if needed.
8. All endpoints are versioned under `/api/v1` to enable future backward‑compatible changes.
