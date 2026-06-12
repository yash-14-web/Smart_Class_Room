# Smart Classroom Management System

A Django-based web application for managing online classrooms.

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run setup (migrations + superuser)
python setup.py

# 4. Start server
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## User Roles
- **Teacher** – Create courses, upload materials, create assignments, grade submissions
- **Student** – Enroll in courses, download materials, submit assignments
- **Admin** – Full access via /admin/

## Project Structure
```
smart_classroom/
├── users/          # Auth, roles, dashboard
├── courses/        # Course management & enrollment
├── assignments/    # Assignment creation & submission
├── materials/      # File upload & download
├── templates/      # All HTML templates
├── static/         # CSS, JS, images
├── media/          # Uploaded files (auto-created)
└── manage.py
```
