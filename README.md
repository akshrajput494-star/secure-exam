# Secure Exam Portal

A secure exam distribution web application built with Python (Flask) and Vanilla JavaScript.

## Prerequisites
- Python 3.8+ (Designed for ARM64 Apple Silicon Mac)

## Setup Instructions

1. **Create and activate a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r backend/requirements.txt
```

3. **Initialize the Database:**
```bash
cd backend
python init_db.py
```
This will create a `secure_exam.db` SQLite database in the `database/` folder and populate it with a default admin and center user:
- Admin: `admin` / `admin123`
- Center: `center_C001` / `center123`

4. **Run the Application:**
```bash
python app.py
```
The server will run on `http://127.0.0.1:5000/`. The frontend is served directly by Flask, so you can access the application by navigating to the base URL.

## Features
- Secure Login System
- Admin Dashboard
- Exam Management APIs (Create, Read)
- Paper Upload APIs
- Secure SQLite Database
- Responsive UI Design (CSS & Vanilla JS)

## Security Addressed
- Passwords hashed with bcrypt
- CSRF & SQL Injection protection via SQLAlchemy
- File upload validation (PDF only, Size limits)

## Project Structure
- `backend/`: Contains Flask application, models, config, and API routes.
- `frontend/`: Contains HTML pages, CSS styles, and JavaScript modules.
- `database/`: Contains SQLite database.
