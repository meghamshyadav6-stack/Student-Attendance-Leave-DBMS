
from datetime import date
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, g

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "attendance.db"

app = Flask(__name__)
app.secret_key = "change-this-development-secret"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        minimum_attendance INTEGER NOT NULL DEFAULT 75
            CHECK(minimum_attendance BETWEEN 0 AND 100)
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        PRIMARY KEY (student_id, course_id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id),
        session_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        topic TEXT NOT NULL,
        session_type TEXT NOT NULL DEFAULT 'REGULAR'
            CHECK(session_type IN ('REGULAR','MAKEUP')),
        CHECK(end_time > start_time)
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        status TEXT NOT NULL CHECK(status IN ('PRESENT','ABSENT','LEAVE')),
        marked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, student_id)
    );

    CREATE TABLE IF NOT EXISTS leave_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id),
        leave_type TEXT NOT NULL CHECK(leave_type IN ('Medical','Casual','On Duty')),
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING'
            CHECK(status IN ('PENDING','APPROVED','REJECTED')),
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CHECK(to_date >= from_date)
    );

    CREATE TABLE IF NOT EXISTS approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL UNIQUE
            REFERENCES leave_applications(id),
        approver_name TEXT NOT NULL,
        decision TEXT NOT NULL CHECK(decision IN ('APPROVED','REJECTED')),
        decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Insert sample students if the table is empty.
    if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        students = [
            ("CS21001", "Aarav Reddy", "aarav@example.com"),
            ("CS21002", "Diya Sharma", "diya@example.com"),
            ("CS21003", "Kabir Khan", "kabir@example.com"),
            ("CS21004", "Meera Iyer", "meera@example.com"),
            ("CS21005", "Rohan Das", "rohan@example.com"),
        ]
        db.executemany(
            "INSERT INTO students(roll_no,name,email) VALUES(?,?,?)",
            students
        )

    # Insert sample courses if the table is empty.
    if db.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        courses = [
            ("CS301", "Database Systems", 75),
            ("CS302", "Operating Systems", 75),
        ]
        db.executemany(
            "INSERT INTO courses(code,title,minimum_attendance) VALUES(?,?,?)",
            courses
        )

    # Enrol sample students in courses.
    if db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0] == 0:
        students = db.execute("SELECT id,roll_no FROM students").fetchall()
        courses = db.execute("SELECT id,code FROM courses").fetchall()

        cs301 = next(c["id"] for c in courses if c["code"] == "CS301")
        cs302 = next(c["id"] for c in courses if c["code"] == "CS302")

        for student in students:
            db.execute(
                "INSERT INTO enrollments(student_id,course_id) VALUES(?,?)",
                (student["id"], cs301)
            )
            if student["roll_no"] in ("CS21001", "CS21002", "CS21003"):
                db.execute(
                    "INSERT INTO enrollments(student_id,course_id) VALUES(?,?)",
                    (student["id"], cs302)
                )

    # Insert sample sessions and attendance.
    if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0:
        db.executemany(
            """INSERT INTO sessions
               (course_id,session_date,start_time,end_time,topic)
               VALUES(?,?,?,?,?)""",
            [
                (1, "2026-08-03", "09:00", "10:00", "ER Modelling"),
                (1, "2026-08-05", "09:00", "10:00", "Relational Model"),
                (1, "2026-08-10", "09:00", "10:00", "Normalization"),
                (1, "2026-09-01", "09:00", "10:00", "SQL Joins"),
            ]
        )

        sessions = db.execute("SELECT id FROM sessions ORDER BY id").fetchall()
        student_ids = [
            row["id"]
            for row in db.execute("SELECT id FROM students ORDER BY id")
        ]
        patterns = ["PAPPP", "PPAPP", "PPAPA", "PPPAA"]

        for index, session in enumerate(sessions):
            for j, student_id in enumerate(student_ids):
                status = "PRESENT" if patterns[index][j] == "P" else "ABSENT"
                db.execute(
                    """INSERT OR IGNORE INTO attendance
                       (session_id,student_id,status) VALUES(?,?,?)""",
                    (session["id"], student_id, status)
                )

        db.execute(
            """INSERT INTO leave_applications
               (student_id,leave_type,from_date,to_date,reason,status)
               VALUES(2,'Medical','2026-08-05','2026-08-05','Fever','APPROVED')"""
        )
        db.execute(
            """INSERT INTO leave_applications
               (student_id,leave_type,from_date,to_date,reason,status)
               VALUES(3,'Casual','2026-09-08','2026-09-08',
                      'Family function','PENDING')"""
        )

    db.commit()
    db.close()


def attendance_rows(db):
    return db.execute("""
        SELECT s.id AS student_id, s.roll_no, s.name,
               c.id AS course_id, c.code, c.title, c.minimum_attendance,
               SUM(CASE WHEN se.session_type='REGULAR'
                   AND a.status='PRESENT' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN se.session_type='REGULAR'
                   AND a.status='ABSENT' THEN 1 ELSE 0 END) AS absent,
               SUM(CASE WHEN se.session_type='REGULAR'
                   AND a.status='LEAVE' THEN 1 ELSE 0 END) AS leave_count,
               SUM(CASE WHEN se.session_type='REGULAR'
                   AND a.status IN ('PRESENT','ABSENT') THEN 1 ELSE 0 END) AS counted
        FROM students s
        JOIN enrollments e ON e.student_id=s.id
        JOIN courses c ON c.id=e.course_id
        LEFT JOIN sessions se ON se.course_id=c.id
        LEFT JOIN attendance a
            ON a.session_id=se.id AND a.student_id=s.id
        GROUP BY s.id,c.id
        ORDER BY c.code,s.roll_no
    """).fetchall()


@app.route("/")
def dashboard():
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "courses": db.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "sessions": db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
        "pending": db.execute(
            "SELECT COUNT(*) FROM leave_applications WHERE status='PENDING'"
        ).fetchone()[0],
    }

    recent = db.execute("""
        SELECT l.*, s.name, s.roll_no
        FROM leave_applications l
        JOIN students s ON s.id=l.student_id
        ORDER BY l.id DESC LIMIT 5
    """).fetchall()

    return render_template("dashboard.html", stats=stats, recent=recent)


@app.route("/students", methods=["GET", "POST"])
def students():
    db = get_db()

    if request.method == "POST":
        roll = request.form.get("roll_no", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not roll or not name:
            flash("Roll number and student name are required.", "error")
        else:
            try:
                db.execute(
                    "INSERT INTO students(roll_no,name,email) VALUES(?,?,?)",
                    (roll, name, email)
                )
                db.commit()
                flash("Student added successfully.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                flash("That roll number already exists. Use a unique roll number.", "error")

    rows = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    return render_template("students.html", students=rows)


@app.route("/sessions", methods=["GET", "POST"])
def sessions():
    db = get_db()

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        session_date = request.form.get("session_date", "")
        start = request.form.get("start_time", "")
        end = request.form.get("end_time", "")
        topic = request.form.get("topic", "").strip()
        session_type = request.form.get("session_type", "REGULAR")

        if not all([course_id, session_date, start, end, topic]):
            flash("Please complete all session fields.", "error")
        elif end <= start:
            flash("End time must be later than start time.", "error")
        elif session_type not in ("REGULAR", "MAKEUP"):
            flash("Invalid session type.", "error")
        else:
            db.execute(
                """INSERT INTO sessions
                   (course_id,session_date,start_time,end_time,topic,session_type)
                   VALUES(?,?,?,?,?,?)""",
                (course_id, session_date, start, end, topic, session_type)
            )
            db.commit()
            flash("Class session created.", "success")
            return redirect(url_for("sessions"))

    courses = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    rows = db.execute("""
        SELECT se.*, c.code, c.title,
               (SELECT COUNT(*) FROM attendance a WHERE a.session_id=se.id) AS marked
        FROM sessions se
        JOIN courses c ON c.id=se.course_id
        ORDER BY se.session_date DESC,se.start_time DESC
    """).fetchall()

    return render_template(
        "sessions.html",
        courses=courses,
        sessions=rows,
        today=date.today().isoformat()
    )


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    db = get_db()

    if request.method == "POST":
        session_id = request.form.get("session_id", type=int)
        student_id = request.form.get("student_id", type=int)
        status = request.form.get("status", "")

        sess = db.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone()

        enrolled = db.execute(
            "SELECT 1 FROM enrollments WHERE student_id=? AND course_id=?",
            (student_id, sess["course_id"] if sess else -1)
        ).fetchone()

        if not sess or not student_id:
            flash("Choose a valid session and student.", "error")
        elif not enrolled:
            flash("This student is not enrolled in the selected course.", "error")
        elif status not in ("PRESENT", "ABSENT", "LEAVE"):
            flash("Invalid attendance status.", "error")
        else:
            try:
                db.execute(
                    """INSERT INTO attendance
                       (session_id,student_id,status) VALUES(?,?,?)""",
                    (session_id, student_id, status)
                )
                db.commit()
                flash("Attendance saved.", "success")
                return redirect(url_for("attendance"))
            except sqlite3.IntegrityError:
                flash("Attendance already exists for this student and session.", "error")

    session_rows = db.execute("""
        SELECT se.*, c.code
        FROM sessions se
        JOIN courses c ON c.id=se.course_id
        ORDER BY se.session_date DESC,se.id DESC
    """).fetchall()

    student_rows = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()

    recent = db.execute("""
        SELECT a.*, s.name,s.roll_no,se.session_date,se.topic,c.code
        FROM attendance a
        JOIN students s ON s.id=a.student_id
        JOIN sessions se ON se.id=a.session_id
        JOIN courses c ON c.id=se.course_id
        ORDER BY a.id DESC LIMIT 25
    """).fetchall()

    return render_template(
        "attendance.html",
        sessions=session_rows,
        students=student_rows,
        records=recent
    )


@app.route("/leave", methods=["GET", "POST"])
def leave():
    db = get_db()

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        leave_type = request.form.get("leave_type", "")
        start = request.form.get("from_date", "")
        end = request.form.get("to_date", "")
        reason = request.form.get("reason", "").strip()
        max_days = {"Medical": 10, "Casual": 3, "On Duty": 7}

        if not student_id or leave_type not in max_days or not start or not end or not reason:
            flash("Please complete every leave application field.", "error")
        elif end < start:
            flash("The end date cannot be earlier than the start date.", "error")
        elif (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 > max_days[leave_type]:
            flash(
                f"{leave_type} leave cannot exceed {max_days[leave_type]} days in this demo.",
                "error"
            )
        else:
            db.execute(
                """INSERT INTO leave_applications
                   (student_id,leave_type,from_date,to_date,reason)
                   VALUES(?,?,?,?,?)""",
                (student_id, leave_type, start, end, reason)
            )
            db.commit()
            flash("Leave application submitted and marked as PENDING.", "success")
            return redirect(url_for("leave"))

    student_rows = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    rows = db.execute("""
        SELECT l.*,s.name,s.roll_no
        FROM leave_applications l
        JOIN students s ON s.id=l.student_id
        ORDER BY l.id DESC
    """).fetchall()

    return render_template("leave.html", students=student_rows, applications=rows)


@app.route("/leave/<int:application_id>/decision", methods=["POST"])
def decision(application_id):
    db = get_db()
    approver = request.form.get("approver", "").strip()
    decision_value = request.form.get("decision", "")

    if not approver:
        flash("Enter the approver's name.", "error")
    elif decision_value not in ("APPROVED", "REJECTED"):
        flash("Choose an allowed decision.", "error")
    else:
        app_row = db.execute(
            "SELECT * FROM leave_applications WHERE id=?", (application_id,)
        ).fetchone()

        if not app_row:
            flash("Leave application was not found.", "error")
        elif app_row["status"] != "PENDING":
            flash("Only pending applications can be decided.", "error")
        else:
            try:
                db.execute("BEGIN")
                db.execute(
                    """INSERT INTO approvals
                       (application_id,approver_name,decision) VALUES(?,?,?)""",
                    (application_id, approver, decision_value)
                )
                db.execute(
                    "UPDATE leave_applications SET status=? WHERE id=?",
                    (decision_value, application_id)
                )

                if decision_value == "APPROVED":
                    db.execute(
                        """UPDATE attendance SET status='LEAVE'
                           WHERE student_id=? AND status='ABSENT'
                           AND session_id IN (
                               SELECT id FROM sessions
                               WHERE session_date BETWEEN ? AND ?
                           )""",
                        (
                            app_row["student_id"],
                            app_row["from_date"],
                            app_row["to_date"]
                        )
                    )

                db.commit()
                flash(
                    f"Application {decision_value.lower()} successfully.",
                    "success"
                )
            except sqlite3.IntegrityError:
                db.rollback()
                flash(
                    "A decision has already been recorded for this application.",
                    "error"
                )

    return redirect(url_for("leave"))


@app.route("/reports")
def reports():
    db = get_db()
    rows = attendance_rows(db)
    report_rows = []

    for row in rows:
        counted = row["counted"] or 0
        present = row["present"] or 0
        percentage = round(present * 100 / counted, 1) if counted else None

        report_rows.append({
            "roll_no": row["roll_no"],
            "name": row["name"],
            "code": row["code"],
            "title": row["title"],
            "present": present,
            "absent": row["absent"] or 0,
            "leave_count": row["leave_count"] or 0,
            "counted": counted,
            "percentage": percentage,
            "minimum": row["minimum_attendance"],
            "shortage": percentage is not None and percentage < row["minimum_attendance"]
        })

    return render_template("reports.html", rows=report_rows)


@app.route("/health")
def health():
    return {
        "status": "ok",
        "application": "Attendance & Leave DBMS Simulator"
    }


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
