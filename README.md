# StudySphere

StudySphere is a role-based eLearning platform for course management, learning dashboards, achievement tracking, and real-time communication between students and teachers, built with Django, Django REST Framework, Django Channels, and PostgreSQL.

**Domain:** [studysphere.app](https://studysphere.app)

---

## For Assessors / Graders

This section provides a quick path to run the application and tests for coursework assessment.

### 1. Setup (one-time)

```sh
cd studysphere
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment

Create a `.env` file in the project root. **Minimum for local assessment:**

```env
DJANGO_SECRET_KEY=dev-secret-key-for-assessment
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

With these settings, the app uses **SQLite** (no database setup required). 
For PostgreSQL/Supabase, add `DB_*` and `SUPABASE_*` variables (see Quick Start below).

### 3. Migrate and create demo users

```sh
python manage.py migrate
python manage.py setup_demo_users
```

### 4. Demo credentials

After running `python manage.py setup_demo_users` (step 3), the command prints the demo usernames and passwords.

| Role    | Username  | Password   |
|---------|-----------|------------|
| Admin    | admin       | xxxxxxxxx  |
| Teacher | teacher    | xxxxxxxxx  |
| Teacher | teacher2  | xxxxxxxxx  |
| Student | student    | xxxxxxxxx  |
| Student | student2  | xxxxxxxxx  |

- **Django admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) — log in with `admin` / xxxxxxxxx
- **Web app:** [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 5. Run the application

```sh
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 6. Run unit tests

Use `run_tests` to see each test name and **ok** in green when it passes (54 tests):

```sh
python manage.py run_tests
```

**With PostgreSQL:** If `test_postgres` is in use, run with `--keepdb`:

```sh
python manage.py run_tests --keepdb
```

Alternatively: `python manage.py test -v 2` (or `-v 2 --keepdb`). 
Stop the runserver before running tests so the database can be torn down cleanly; if you see "database is being accessed by other users", use `--keepdb`.

### 7. Documentation

| Document | Location | Description |
|----------|----------|-------------|
| **Report** | `docs/Report.md` | Full coursework report (design, implementation, evaluation) |
| **Data Schema & ER Diagram** | `docs/DATA_SCHEMA.md` | Entity-relationship diagram, data schema, entity descriptions |
| **User Flow Diagrams** | `docs/USER_FLOW_DIAGRAMS.md` | Mermaid flowcharts for registration, login, enrolment, feedback, chat, etc. |

### 8. Quick test checklist

- **Registration:** `/accounts/register/` — create student/teacher
- **Login:** `/accounts/login/` — use demo credentials
- **Password reset:** `/accounts/password-reset/` — requires email config (see `docs/EMAIL_SETUP.md`)
- **Course list:** `/courses/` — browse, filter by category
- **Enrolment:** Login as student → course detail → Enrol
- **Teacher approval:** Login as teacher → My Courses → course → Approve/Reject
- **Feedback:** Enrolled student → course detail → Leave Feedback (edit/delete own)
- **Chat:** Enrolled student → course detail → Chat (WebSocket)
- **Status feed:** `/social/` — post and view status updates
- **Notifications:** Bell icon in navbar
- **REST API:** `/api/` — JWT auth via `/api/token/`

---

## Features

- **Role-based users**: Students and Teachers with distinct permissions
- **Course management**: Teachers create courses, upload materials
- **Enrolment system**: Students enrol in courses, teachers approve/reject/block
- **Feedback system**: Students rate and review courses (1–5 stars)
- **Status updates**: Users post status updates to their profile (social feed)
- **Real-time chat**: WebSocket-based course chat rooms (Django Channels)
- **Notifications**: Signal-driven alerts on enrolment and material uploads
- **REST API**: Full DRF API with JWT authentication, search, and pagination
- **User search**: Teachers can search for students and other teachers

## Tech Stack

- **Backend**: Django 6.x, Django REST Framework 3.16
- **WebSockets**: Django Channels with InMemoryChannelLayer (Redis optional)
- **Database**: SQLite (local dev) / PostgreSQL via Supabase (production)
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, JavaScript
- **Auth**: Django built-in auth + SimpleJWT for API

## Prerequisites

- Python **3.12**
- Git
- (Optional) **Supabase** project for PostgreSQL + Storage

## Quick Start (local development)

### 1. Clone the repository and create a virtual environment

```sh
git clone https://github.com/<your-username>/studysphere.git
cd studysphere

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```sh
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root (same folder as `manage.py`). For a minimal setup (SQLite, no Supabase), use the same variables as in **For Assessors / Graders → step 2** above. For PostgreSQL and Supabase Storage, copy from `.env.example` (if present) or add `DB_*` and `SUPABASE_*` variables as needed.

### 4. Supabase Dashboard → Storage (bucket and policies)

Create a bucket and policies so StudySphere can upload course images, materials, and **certificates**.

1. **Open Storage**  
   In [Supabase Dashboard](https://app.supabase.com) → your project → **Storage**.

2. **Create a bucket** (if you don't have one yet)  
   - Click **New bucket**.
   - Name it the same as `SUPABASE_BUCKET` in your `.env` (e.g. `studysphere-files` or `studysphere-media`).
   - Optionally enable **Public bucket** if you want direct public URLs for files (e.g. certificates, hero images). Otherwise use **Policies** to control access.

3. **Policies**  
   In the bucket → **Policies** → **New policy** (or use "For full customization"):

   - **Upload (insert)**  
     - Policy name: e.g. `Allow uploads`.  
     - Allowed operation: **INSERT**.  
     - Target roles: `authenticated` (and/or `anon` if your app uses the anon key for uploads).  
     - USING expression: `true` (or restrict by `auth.role()` / `auth.uid()` if you prefer).

   - **Read (select)**  
     - Policy name: e.g. `Allow public read`.  
     - Allowed operation: **SELECT**.  
     - Target roles: `authenticated`, `anon` (and optionally `public` if the bucket is public).  
     - USING expression: `true`.

   Certificate PDFs use the same bucket under the prefix `certificates/issued/`; the same INSERT and SELECT policies apply.

### 5. Apply database migrations

```sh
python manage.py migrate
```

### 6. (Optional) Create demo users

```sh
python manage.py setup_demo_users
```

### 7. Run the development server

```sh
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 8. Run tests

```sh
python manage.py test -v 2
```

**With PostgreSQL:** Use `--keepdb` to reuse the test database and avoid teardown issues:

```sh
python manage.py test -v 2 --keepdb
```

## Project Structure

```
studysphere/
├── studysphere/          # Project configuration (settings, urls, asgi, wsgi)
├── accounts/               # Custom user model, auth views, permissions
├── courses/                 # Course CRUD, enrolment, materials, feedback
├── social/                    # Status updates / social feed
├── chat/                      # WebSocket chat (Django Channels)
├── notifications/        # Signal-driven notification system
├── calendar_app/      # Calendar events
├── analytics/             # Activity tracking, heatmap, streak
├── api/                       # DRF viewsets, serializers, router
├── docs/                   # Report, Data Schema, User Flow Diagrams
├── templates/          # HTML templates (Bootstrap 5)
├── static/                 # CSS, JavaScript
├── media/                # User uploads (photos, course materials)
├── manage.py
└── requirements.txt
```

## API Endpoints

| Method |          Endpoint                                | Description                    |
|--------|-----------------------------------|--------------------------------|
| POST   | `/api/register/`                                 | Register a new user                    |
| POST   | `/api/token/`                                     | Obtain JWT token                       |
| POST   | `/api/token/refresh/`                        | Refresh JWT token                     |
| GET    | `/api/users/`                                       | List users (searchable)              |
| GET    | `/api/users/{id}/`                                | User detail                                  |
| GET    | `/api/courses/`                                   | List courses                                |
| POST   | `/api/courses/`                                 | Create course (teacher only)     |
| POST   | `/api/courses/{id}/enrol/`                 | Enrol in course (student only)   |
| GET    | `/api/courses/{id}/feedback/`           | Course feedback                        |
| GET    | `/api/courses/{id}/students/`            | Enrolled students (teacher)       |
| GET    | `/api/courses/{id}/materials/`           | Course materials                         |
| POST   | `/api/feedback/`                              | Submit feedback                         |
| GET    | `/api/status/`                                     | Status updates                            |
| POST   | `/api/status/`                                    | Create status update                  |
| GET    | `/api/notifications/`                           | User notifications                        |
| POST   | `/api/notifications/mark_all_read/` | Mark all as read                           |
| POST   | `/api/materials/`                               | Upload material                           |

## WebSocket Chat

Connect to: `ws://localhost:8000/ws/chat/<course_id>/`

## Configuration notes

- For **local development**, SQLite is used by default; you only need the basic `.env` values above.
- For **deployment** (e.g. on a VPS or PaaS):
  - Set `DEBUG=False` and update `ALLOWED_HOSTS` to include your domain.
  - Configure the `DB_*` variables for PostgreSQL (Supabase or your own DB).
  - Set `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_BUCKET` so course hero images, materials, and chat uploads are stored in Supabase Storage.
  - Run:

    ```sh
    python manage.py collectstatic
    python manage.py migrate
    ```

  - Point your ASGI server (e.g. Daphne/Uvicorn) at `studysphere.asgi:application` so WebSocket chat works.

## Development Environment

- **OS**: macOS
- **Python**: 3.12
- **Django**: 6.x
