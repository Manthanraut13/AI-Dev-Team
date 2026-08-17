# Architecture — Simple Todo Application

## Detected Stack

- FastAPI
- Python 3.11
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT (PyJWT)
- Pydantic
- Docker
- Docker Compose
- Next.js
- React
- TypeScript
- Tailwind CSS
- React Query
- Axios

## API Endpoints

- **POST** `/api/auth/register` — Register a new user with email and password.
- **POST** `/api/auth/login` — Authenticate user and return JWT access/refresh tokens.
- **POST** `/api/auth/logout` — Invalidate refresh token (optional) to log out securely.
- **POST** `/api/auth/password-reset/request` — Send password‑reset email with verification token.
- **POST** `/api/auth/password-reset/confirm` — Verify token and set new password.
- **GET** `/api/tasks` — Get paginated list of tasks for the authenticated user; supports filtering, sorting, and search via query parameters.
- **POST** `/api/tasks` — Create a new task belonging to the authenticated user.
- **GET** `/api/tasks/{task_id}` — Retrieve a single task detail.
- **PUT** `/api/tasks/{task_id}` — Replace all attributes of a task.
- **PATCH** `/api/tasks/{task_id}` — Partially update task attributes (e.g., mark complete).
- **DELETE** `/api/tasks/{task_id}` — Delete a task owned by the user.
- **GET** `/api/categories` — List all categories created by the user.
- **POST** `/api/categories` — Create a new task category.
- **PUT** `/api/categories/{category_id}` — Update category name or metadata.
- **DELETE** `/api/categories/{category_id}` — Delete a category (optional cascade removal from tasks).

## Database Schema

### unknown
- id: SERIAL
- email: VARCHAR(255)
- hashed_password: VARCHAR(255)
- is_active: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

### unknown
- id: SERIAL
- user_id: INTEGER
- name: VARCHAR(100)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

### unknown
- id: SERIAL
- user_id: INTEGER
- title: VARCHAR(200)
- description: TEXT
- due_date: DATE
- priority: INTEGER
- is_completed: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

### unknown
- task_id: INTEGER
- category_id: INTEGER

### unknown
- id: SERIAL
- user_id: INTEGER
- reset_token: VARCHAR(255)
- expires_at: TIMESTAMP
- created_at: TIMESTAMP

## Folder Structure

```
backend/
├─ app/
│  ├─ api/
│  │   ├─ v1/
│  │   │   ├─ endpoints/
│  │   │   │   ├─ auth.py
│  │   │   │   ├─ tasks.py
│  │   │   │   └─ categories.py
│  │   │   └─ dependencies.py
│  │  ├─ core/
│  │  │   ├─ config.py
│  │  │   ├─ security.py
│  │  │   └─ pagination.py
│  │  ├─ db/
│  │  │   ├─ base.py
│  │  │   ├─ models.py
│  │  │   ├─ schemas.py
│  │  │   └─ session.py
│  │  └─ main.py
├─ tests/
│   ├─ api/
│   └─ db/
├─ alembic/
│   └─ ...
├─ Dockerfile
└─ poetry.lock
frontend/
├─ src/
│   ├─ app/
│   │   ├─ pages/
│   │   │   ├─ index.tsx
│   │   │   ├─ login.tsx
│   │   │   └─ tasks/
│   │   │       ├─ list.tsx
│   │   │       └─ edit.tsx
│   │   ├─ components/
│   │   │   ├─ TaskCard.tsx
│   │   │   ├─ CategorySelect.tsx
│   │   │   └─ Layout.tsx
│   │   ├─ hooks/
│   │   │   └─ useAuth.ts
│   │   ├─ services/
│   │   │   └─ api.ts
│   │   └─ styles/
│   │       └─ globals.css
│   └─ public/
├─ tsconfig.json
├─ next.config.js
├─ package.json
├─ Dockerfile
└─ .env.local
```

## Technology Decisions

1. Use FastAPI for its async support, automatic OpenAPI generation, and tight Pydantic integration for request/response validation.
2. Store passwords with bcrypt hashing via Passlib; never store plain text passwords.
3. Stateless JWT authentication enables horizontal scaling; refresh tokens are stored in HttpOnly cookies for security.
4. SQLAlchemy ORM with Alembic migrations provides type‑safe DB access and schema versioning.
5. Design tasks‑categories as many‑to‑many via a join table to allow flexible categorization.
6. Implement pagination using limit/offset with configurable page size; expose total count in response headers.
7. Expose filtering, sorting, and search through query parameters (e.g., ?category=1&status=completed&search=foo).
8. Separate backend and frontend into distinct Docker services; use Docker Compose for local development and easy CI/CD.
9. Frontend built with Next.js for SSR/SEO friendliness and built‑in routing; Tailwind CSS for rapid responsive UI design.
10. React Query handles caching, background refetch, and optimistic updates for a smooth UX.
