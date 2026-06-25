# Call Companion Backend

This is the FastAPI backend application for Call Companion.

## Prerequisites

Ensure you have the following installed on your system:
- **Python 3.11**
- **Pipenv** (can be installed via `pip install pipenv` or `brew install pipenv` on macOS)

---

## Setup & Installation

### 1. Install Dependencies
Run the following command inside the `backend` directory to create a virtual environment and install all packages:
```bash
pipenv install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and ensure the `DATABASE_URL` is set correctly. (For local development, it is preconfigured to connect to the Supabase PostgreSQL database).

---

## Database Migrations

This project uses **Alembic** to manage database schema migrations.

### Apply Migrations
To bring your database schema up to date with the latest models, run:
```bash
pipenv run alembic upgrade head
```

---

## Running the Server

### Start the Server (Default)
Run the development server on the default port (`8000`):
```bash
pipenv run uvicorn app.main:app --reload
```

Once running, the interactive API documentation will be available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Troubleshooting Port Conflicts

If port `8000` is already in use by another local project (e.g., `go-on-fourth`):

### Option A: Run on a different port
Start the backend server on a custom port (such as `8001`):
```bash
pipenv run uvicorn app.main:app --reload --port 8001
```

If you do this, you must tell the frontend where to find the API by updating your frontend's environment configuration. In `/frontend/.env`, set:
```env
VITE_API_URL=http://localhost:8001
```

### Option B: Stop the conflicting process
Find the PID of the process using port `8000`:
```bash
lsof -i :8000
```
Then terminate the process:
```bash
kill -9 <PID>
```
