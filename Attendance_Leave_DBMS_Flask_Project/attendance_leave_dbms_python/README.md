# Student Attendance & Leave Approval — DBMS Simulator

A Python Flask web application for demonstrating student records, course sessions, attendance, leave applications, approval decisions, and attendance reports. It uses SQLite, so a separate database server is not required.

## Features
- Dashboard with counts for students, courses, sessions, and pending leave applications
- Student list and add-student form
- Create class sessions with date/time validation
- Mark attendance as Present, Absent, or Leave
- Prevent duplicate attendance entries for the same student/session
- Check that students are enrolled in the selected course
- Submit Medical, Casual, and On Duty leave applications with date and duration validation
- Approve/reject pending leave applications
- Attendance percentage and shortage report
- SQLite relational schema with foreign keys, unique constraints, and check constraints
- Sample data added automatically on first run

## Technology stack
- Python 3
- Flask (web framework)
- SQLite (database)
- HTML templates (Jinja2)
- CSS
- Visual Studio Code (recommended editor)
- GitHub (source-code hosting)
- Optional: GitHub Pages is **not** suitable for hosting this Flask backend by itself. Use a Python-capable host if a public live deployment is required.

## Project structure
```text
attendance_leave_dbms_python/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── students.html
│   ├── sessions.html
│   ├── attendance.html
│   ├── leave.html
│   └── reports.html
└── static/
    └── style.css
```

The `attendance.db` file is created automatically the first time the app starts. It is excluded from Git because it is a local runtime database.

## Run in Visual Studio Code (Windows)

### 1. Install prerequisites
1. Install Python 3 from https://www.python.org/downloads/ .
2. During installation, tick **Add Python to PATH**.
3. Install Visual Studio Code from https://code.visualstudio.com/ .
4. In VS Code, install the Microsoft **Python** extension.

### 2. Extract and open
1. Extract the downloaded ZIP file.
2. Open VS Code.
3. Choose **File → Open Folder** and select `attendance_leave_dbms_python`.

### 3. Open the terminal
Choose **Terminal → New Terminal**.

Check Python:
```powershell
py --version
```
If that command is unavailable, try:
```powershell
python --version
```

### 4. Create a virtual environment (recommended)
In the VS Code terminal, run:
```powershell
py -m venv .venv
```
Activate it in PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
If PowerShell blocks activation, use Command Prompt terminal and run:
```bat
.venv\Scripts\activate.bat
```
You can also install packages without activating the environment by running `py -m pip install -r requirements.txt`.

### 5. Install Flask
```powershell
py -m pip install -r requirements.txt
```

### 6. Start the website
```powershell
py app.py
```
Open this address in your browser:
http://127.0.0.1:5000

Keep the terminal open while using the site. Press `Ctrl+C` in the terminal to stop it.

## Demo data
The first run creates sample students, courses, sessions, attendance entries, and two leave applications. Data is saved in `attendance.db` and remains after restarting the application.

To reset the local demo database, stop the server, delete `attendance.db`, and run `py app.py` again. This will recreate the sample data.

## Database design overview
- `students`: student roll number, name, email
- `courses`: course code, title, minimum attendance percentage
- `enrollments`: many-to-many relationship between students and courses
- `sessions`: course date, time, topic, and session type
- `attendance`: one attendance status per student per session
- `leave_applications`: leave dates, type, reason, and status
- `approvals`: approver and decision for a leave application

## Upload to GitHub
1. Create or open the correct GitHub repository.
2. Upload the extracted project files/folders (not only the ZIP) using **Add file → Upload files**, or use GitHub Desktop.
3. Do not upload `.venv/` or `attendance.db`.
4. Commit with a message such as `Add Flask attendance and leave DBMS app`.

## Important limitations
This is an educational demonstration, not a production-ready college system. It has no login/role-based authentication, uses a development secret key, and does not include deployment configuration. Add authentication, authorization, secure configuration, backups, and privacy protections before using real student data.
