```markdown
# Test Project
A simple test project.

## Overview
The **Simple Todo App** is a minimalistic task management service that allows users to securely register, log in, and manage their personal to‑do items. Each authenticated user can create, edit, delete, and toggle the completion status of tasks, as well as organize them into categories.

## Features
- **User Management**
  - Register with email & password
  - Login with email & password (JWT based)
  - Password reset via email link
- **Task Management**
  - Create tasks with title, description, due date, and category
  - Edit any task attribute
  - Delete tasks
  - Mark tasks as completed / uncompleted
  - List all tasks belonging to the authenticated user
- **Category Support**
  - Create and list personal categories for task organization
- **Security**
  - Passwords hashed with `bcrypt`
  - Endpoints protected by JWT authentication
  - Email verification for password reset (SMTP configurable)

## Tech Stack
| Layer | Technology |
|-------|------------|
| **Web Framework** | **FastAPI** |
| **ASGI Server** | **Uvicorn** |
| **Database** | **SQLite** (via **SQLModel** / **SQLAlchemy**) |
| **Authentication** | **JSON Web Tokens (JWT)** |
| **Password Hashing** | **Passlib (bcrypt)** |
| **Email** | **aiosmtplib** (configurable SMTP) |
| **Testing** | **pytest**, **httpx** |
| **Containerisation** | **Docker** (optional) |
| **Dependency Management** | **Poetry** (or `pip` with `requirements.txt`) |

## Quickstart
> **Prerequisites**: Python 3.10+, Git, and an SMTP server (for password‑reset emails).

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/simple-todo-app.git
   cd simple-todo-app
   ```

2. **Install dependencies**
   ```bash
   # Using Poetry
   poetry install

   # Or with pip
   pip install -r requirements.txt
   ```

3. **Configure environment variables**  
   Create a `.env` file in the project root:

   ```dotenv
   # FastAPI
   APP_HOST=0.0.0.0
   APP_PORT=8000

   # JWT
   JWT_SECRET_KEY=your-secret-key
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60

   # Database
   DATABASE_URL=sqlite:///./todo.db

   # Email (for password reset)
   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USER=your@email.com
   SMTP_PASSWORD=yourpassword
   EMAIL_FROM=no-reply@example.com
   ```

4. **Run database migrations (if any)**
   ```bash
   alembic upgrade head   # or let the app create tables automatically on first run
   ```

5. **Start the API server**
   ```bash
   uvicorn plugin.server:app --host $APP_HOST --port $APP_PORT --reload
   ```

6. **Explore the API**
   Open your browser at `http://localhost:8000/docs` to view the automatically generated OpenAPI/Swagger UI.

   For a detailed endpoint reference, see **[docs/API.md](docs/API.md)**.

## Running Tests
```bash
pytest
```

## License
This project is licensed under the MIT License.
```