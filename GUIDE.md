# Smart Classroom – Project Documentation & Guide

## 1. Introduction
**Smart Classroom** is a comprehensive Learning Management System (LMS) designed for modern educators and students. It provides a centralized platform for managing courses, assignments, coding tests, and direct communication.

### Core Philosophy
- **Aesthetics First**: A stunning, theme-aware user interface that is fully functional in both Light and Dark modes.
- **Distraction-Free**: Clean, simple interactions that keep focus on learning.
- **Integrated Tools**: No need for external platforms; students can code, chat, and submit work all in one place.

---

## 2. Key Features

### 🎓 For Students
- **Smart Dashboard**: A bird's-eye view of your progress, enrolled courses, and latest reports.
- **Course Library**: Browse and enroll in courses, view learning materials, and watch recorded lectures.
- **Assignments & Projects**: Submit your work through file uploads or GitHub links.
- **Coding Sandboxes (Tests)**: Test your Python skills directly in the browser with an integrated IDE.
- **Personalized Quizzes**: Take multiple-choice tests and get instant results.
- **Leaderboard**: Compete with your peers based on total marks and average scores.
- **Certificates**: Automatically receive a digital certificate once you pass a course.

### 👨‍🏫 For Teachers
- **Course Management**: Full control over course creation, editing, and enrollment.
- **Automated Attendance**: Create attendance sessions and track student presence with ease.
- **Grading Suite**: Review student submissions (Assignments/Projects/Quizzes) and provide direct feedback.
- **Communication Center**: Direct and group chat systems to stay in touch with your students.
- **Report System**: Generate detailed overall reports and individual student report cards.

---

## 3. Technology Stack

- **Backend**: Django (Python 3.10+) – A robust, secure, and scalable web framework.
- **Frontend**: 
  - **HTML5/CSS3**: Semantic structures with vanilla CSS for maximum design control.
  - **JavaScript**: Dynamic UI interactions and AJAX-based real-time chat.
  - **Bootstrap 5**: Responsive layout system.
- **Database**: SQLite (Development) – Lightweight and portable.
- **Styling**: 
  - **CSS Variables**: System-wide theme switching (Light/Dark mode) with consistent `--sc-*` tokens.
- **Media Processing**: 
  - **Pillow**: Image handling (Profile pics, cover images).
  - **WeasyPrint**: PDF generation for reports and certificates.
  - **openpyxl**: Data export to Excel for grades.

---

## 4. Local Installation Guide

1. **Clone the Project**:
   ```bash
   git clone <repository-url>
   cd smart_classroom
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare the Database**:
   ```bash
   python manage.py migrate
   ```

5. **Run the Server**:
   ```bash
   python manage.py runserver
   ```
   Access the app at `http://127.0.0.1:8000/`.

---

## 5. Deployment Guide (PythonAnywhere)

Smart Classroom is fully optimized for **PythonAnywhere Free Tier**.

1. **Create an account** at PythonAnywhere.
2. **Bash Console**: Create a virtual environment and install the requirements.
3. **Web Tab**:
   - Manually configure a Python 3.10 web app.
   - Set the WSGI file to point to your project.
   - Map `/static/` and `/media/` directories.
4. **Security**: Disable `DEBUG = False` and use environment variables for the `SECRET_KEY`.

---

## 6. User Roles & Access

| Feature | Student | Teacher | Admin |
|---|:---:|:---:|:---:|
| View Course Content | ✅ | ✅ | ✅ |
| Submit Assignment | ✅ | ❌ | ❌ |
| Create Attendance | ❌ | ✅ | ✅ |
| Grade Submissions | ❌ | ✅ | ✅ |
| Change Site Settings | ❌ | ❌ | ✅ |
| Access Chat | ✅ | ✅ | ✅ |

---

*This guide was automatically generated for the Smart Classroom Project.*
