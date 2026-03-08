# StudySphere

StudySphere is a role-based eLearning platform for course management, learning dashboards, achievement tracking, and real-time communication between students and teachers.

**Stack:** Django, Django REST Framework, Django Channels, PostgreSQL / SQLite.

**Domain:** [studysphere.app](https://studysphere.app)

**What to push:** Only `README.md` and functional source code (Python, templates, static CSS/JS, etc.). Necessary course images can go in `static/course_images/` (see `.gitignore`). Do not push: PDF, Word (`.doc`/`.docx`), other `.md` files, or images outside `static/course_images/`.

---

## Run info 

| Item | Details |
|------|---------|
| **OS** | macOS (Windows/Linux: use equivalent commands for venv and paths) |
| **Python** | 3.12+ |
| **Dependencies** | `requirements.txt` (install with `pip install -r requirements.txt`) |
| **Login credentials** | Created by `python manage.py setup_demo_users` — command prints admin, teacher, and student usernames and passwords. Use those to log in at [http://127.0.0.1:8000](http://127.0.0.1:8000) and [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/). |

---

## How to run

### 1. Clone and install

```sh
git clone https://github.com/kominkhantkyaw/StudySphere.git
cd StudySphere

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

*(Code criterion 1: Application loads using a valid `requirements.txt`.)*

### 2. Environment

Create a `.env` file in the project root. Minimum for local run (SQLite):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

For PostgreSQL/Supabase, add `DB_*` and `SUPABASE_*` (see `.env.example`).

### 3. Migrate and run

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

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## How to test

```sh
python manage.py run_tests
```

Or: `python manage.py test -v 2`. With PostgreSQL use `--keepdb`. Stop the runserver before running tests. **54 unit tests** (accounts, courses, chat, notifications, social). *(Code criterion 6: Unit testing is included.)* See `docs/Unit_test.md` for process and coverage.

---

## Criteria alignment (summary)

**Code**

| # | Criterion | Where / how |
|---|-----------|-------------|
| 1 | Application loads with valid `requirements.txt` | Use `pip install -r requirements.txt` (see How to run). |
| 2 | All specified functionality implemented | Roles, courses, enrolment, materials, feedback, chat, notifications, calendar, API, 2FA, theme, i18n, certificates. See `docs/USER_FLOW_DIAGRAMS.md`. |
| 3 | Database/Model design appropriate | Normalised schema; ER diagram and entity descriptions in `docs/DATA_SCHEMA.md`. |
| 4 | Frontend design appropriate | Responsive UI with Bootstrap 5; see templates and static. |
| 5 | Django (topics 1–10), incl. API docs (Swagger) | Models, views, forms, auth, migrations, DRF, Channels (WebSockets). API: `drf-yasg` in `requirements.txt`. API docs: Swagger UI at /swagger/, ReDoc at /redoc/ (when runserver is running). |
| 6 | Unit testing included | 54 tests; `python manage.py run_tests`; `docs/Unit_test.md`. |
| 7 | Clean code, syntax, comments | Modular apps, consistent naming, docstrings and comments where needed. |
| 8 | Functional, reproducible | No known blocking errors; run instructions above give reproducible run. |
| 9 | Modular, well organised | App-based structure; clear use of functions/classes; see Project structure. |
| 10 | Advanced techniques | Django Channels (async WebSockets), DRF, JWT, 2FA, i18n, Supabase storage; Bootstrap 5 for frontend. |

**Report**

| # | Criterion | Where |
|---|-----------|--------|
| 1 | Report clearly written | `docs/Report.md` |
| 2 | How requirements are met | In Report and in `docs/USER_FLOW_DIAGRAMS.md`, `docs/DATA_SCHEMA.md` |
| 3 | Techniques taught (Django, DRF, WebSockets) | Report + codebase: Django (MVT, auth, migrations), DRF (serializers, viewsets), Channels (async WebSockets for chat) |
| 4 | Critical evaluation / state of the art | In Report |
| 5 | Run info (OS, Python, login credentials) | This README: Run info table above and How to run; credentials from `setup_demo_users` |

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/Report.md` | Full coursework report (requirements, design, evaluation) |
| `docs/DATA_SCHEMA.md` | Database schema and ER diagram |
| `docs/USER_FLOW_DIAGRAMS.md` | User flows (registration, login, enrolment, chat, etc.) |
| `docs/Unit_test.md` | Unit testing process and coverage |
| `docs/DEMO_NARRATION.md` | Demo narration script |
| `.env.example` | Example environment variables |

---

## Features (functionality)

- Role-based users (Student / Teacher), course management, enrolment (approve/reject/block)
- Materials upload, student submissions, feedback (rating + comment)
- Real-time chat (Django Channels WebSockets), notifications, calendar events
- REST API with JWT; 2FA; theme (Light/Dark/System); i18n (English/German)
- Certificates (QR, Supabase storage), responsive UI (Bootstrap 5)

---

## Project structure

```
StudySphere/
├── studysphere/    # Settings, urls, asgi, wsgi
├── accounts/       # User model, auth, profile, settings, 2FA
├── courses/        # Courses, enrolment, materials, feedback, certificates
├── chat/           # WebSocket chat (Channels)
├── notifications/  # In-app notifications
├── calendar_app/   # Events
├── social/         # Status feed
├── analytics/      # Activity, streak
├── api/            # DRF API
├── docs/           # Report, schema, flows, unit test doc
├── templates/      # HTML (Bootstrap 5)
├── static/        # CSS, JS; course images in static/course_images/
├── requirements.txt
└── manage.py
```

---

## API (summary)

- **Auth:** `POST /api/register/`, `POST /api/token/`, `POST /api/token/refresh/`
- **Users:** `GET /api/users/` (searchable)
- **Courses:** CRUD, `POST /api/courses/{id}/enrol/`
- **Feedback, materials, status, notifications, events:** CRUD under `/api/`. See API root or `docs/` for full list. **API docs:** [Swagger UI](http://127.0.0.1:8000/swagger/), [ReDoc](http://127.0.0.1:8000/redoc/) (when runserver is running). If the API docs URL is not set in your URLs, add the `swagger/` and `redoc/` routes in `studysphere/urls.py` (see drf-yasg), or drop the Swagger sentence from this README.

---

## Deployment (brief)

Set `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`; use PostgreSQL and optionally Supabase; run `collectstatic`, `migrate`; serve with an ASGI server (e.g. Daphne) for WebSocket chat.

---

Developed with ❤️ — E-learning platform for students and educators to share knowledge, develop skills, and support academic growth.
