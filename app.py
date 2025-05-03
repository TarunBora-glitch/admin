from flask import jsonify, Flask, render_template, request, redirect, url_for, session, make_response, send_file, flash
import secrets
import mysql.connector
from datetime import datetime, timedelta
import csv
import os
import cv2
import pickle
import numpy as np
import base64
import io
from io import StringIO
import face_recognition
from PIL import Image
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = "b7a9c11e6b8f8e489a3f9e"  # Use a fixed random key

app.permanent_session_lifetime = timedelta(minutes=2)  # Example: 30 mins session
app.secret_key = 'your-secret-key'  # ✅ string used as secret
serializer = URLSafeTimedSerializer(app.secret_key)

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",  
        password="tarunboramysql@2007",  
        database="attendance_system"
    )
    
conn = connect_db()  
cursor = conn.cursor(dictionary=True)  


@app.route("/")
def home():
    return render_template("index.html")

@app.route('/register-student', methods=['GET', 'POST'])
def register_student():
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form['full_name']
        roll_number = request.form['roll_number']
        password = request.form['password'] 
        branch = request.form['branch']
        semester = request.form['semester']
        gender = request.form['gender']

        try:
            cursor.execute(
                "INSERT INTO students (full_name, roll_number, password, branch, semester, gender) VALUES (%s, %s, %s, %s, %s, %s)",
                (full_name, roll_number, password, branch, semester, gender)
            )
            conn.commit()
            return redirect(url_for('student_login'))

        except mysql.connector.IntegrityError:
            return "Roll Number already exists! <a href='/register-student'>Try Again</a>"

        finally:
            conn.close()

    # GET request: load distinct branches and semesters from `subjects` table
    cursor.execute("SELECT DISTINCT branch FROM subjects")
    branches = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT semester FROM subjects")
    semesters = [row[0] for row in cursor.fetchall()]

    conn.close()
    return render_template('register-student.html', branches=branches, semesters=semesters)
@app.route('/register-admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'GET':
        return render_template('register-admin.html') 

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not full_name or not email or not password:
            return jsonify({"success": False, "message": "All fields are required!"})

        conn = connect_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO admins (full_name, email, password) VALUES (%s, %s, %s)",
                (full_name, email, password)
            )
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"success": True, "message": "Registration successful!"})
        
        except mysql.connector.IntegrityError:
            conn.close()
            return jsonify({"success": False, "message": "Email already exists!"})


@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_number = request.form['roll_number']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE roll_number = %s AND password = %s", (roll_number, password))
        student = cursor.fetchone()
        conn.close()

        if student:
            # Store student_id in the session for later use
            session['student_id'] = student['id']#
            session['full_name'] = student['full_name']
            session['branch'] = student['branch']
            session['semester'] = student['semester']
            session['roll_number'] = roll_number  # Storing roll_number as well, just in case you need it
            session.permanent = True  
            print("Login successful for {roll_number}") 
            return redirect(url_for('attendance'))
        else:
            print("Invalid login attempt!")  
            return "Invalid Credentials! <a href='/student-login'>Try Again</a>"

    return render_template('student-login.html')



@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'roll_number' not in session: 
        return redirect(url_for('student_login'))
    return render_template('attendance.html')

    
    roll_number = session['roll_number']

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    search_date = request.form.get('search_date')  
    if search_date:
        cursor.execute("SELECT * FROM attendance WHERE date = %s", (search_date,))
    else:
        cursor.execute("SELECT * FROM attendance WHERE student_id = (SELECT id FROM students WHERE roll_number = %s)", (roll_number,))

    records = cursor.fetchall()
    conn.close()

    return render_template('attendance.html', student=session, records=records, search_date=search_date)
def attendance_page():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('attendance'))

    # Fetch student details
    cursor.execute("SELECT semester, branch FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    if not student:
        return redirect(url_for('login'))

    semester, branch = student

    # Fetch subjects for the student's semester and branch
    cursor.execute("SELECT id, subject_name FROM subjects WHERE semester = %s AND branch = %s", (semester, branch))
    subjects = cursor.fetchall()

    return render_template('attendance.html', subjects=subjects)

@app.route('/student_dashboard-logout')
def student_dashboard_logout():
    session.clear() 
    return render_template("index.html")

# Route to student dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'roll_number' not in session:
        return redirect(url_for('student_login'))

    roll_number = session['roll_number']
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch student details
    cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
    student = cursor.fetchone()

    # Fetch subjects based on the student's branch and semester
    cursor.execute("""
        SELECT * FROM subjects
        WHERE branch = %s AND semester = %s
    """, (student['branch'], student['semester']))
    subjects = cursor.fetchall()

    # Fetch attendance records ordered by date and time descending
    cursor.execute("""
        SELECT a.*, sub.subject_name 
        FROM attendance a
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.student_id = (SELECT id FROM students WHERE roll_number = %s)
        ORDER BY a.date DESC, a.time DESC
    """, (roll_number,))
    records = cursor.fetchall()

    conn.close()

    return render_template('student_dashboard.html', student=student, records=records, subjects=subjects)

# Route to search attendance
@app.route("/search_attendance", methods=["POST"])
def search_attendance():
    student_id = session.get("student_id")
    branch = session.get('branch')
    semester = session.get('semester')
    search_date = request.form.get("search_date")
    status = request.form.get("status")
    subject_id = request.form.get("subject_id")

    if not all([student_id, branch, semester]):
        return """
            <script>
                alert('Missing session data, Login again');400
                window.location.href = '/student_dashboard';  // Redirect to your login page
            </script>
        """

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch filtered attendance
    query = """
        SELECT a.*, s.subject_name 
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = %s
    """
    params = [student_id]

    if search_date:
        query += " AND a.date = %s"
        params.append(search_date)
    if status:
        query += " AND a.status = %s"
        params.append(status)
    if subject_id:
        query += " AND a.subject_id = %s"
        params.append(subject_id)

    cursor.execute(query, tuple(params))
    records = cursor.fetchall()

    # Fetch student details
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    if not student:
        return "Error: Student details not found."

    # Load subjects for filter dropdown
    cursor.execute("SELECT * FROM subjects WHERE branch = %s AND semester = %s", (branch, semester))
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("student_dashboard.html", student=student, records=records, subjects=subjects)

@app.route('/add_attendance', methods=['POST'])
def add_attendance():
    if 'admin_name' not in session:
        return redirect(url_for('admin_login'))

    student_name = request.form.get('student_name')
    roll_number = request.form.get('roll_number')
    subject_name = request.form.get('subject_name')
    date_str = request.form.get('date')
    status = request.form.get('status')

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Check for student
        cursor.execute("SELECT id, branch, semester FROM students WHERE full_name = %s AND roll_number = %s",
                       (student_name, roll_number))
        student = cursor.fetchone()
        if not student:
            return redirect(url_for('admin_panel', message="Student not found."))

        student_id, branch, semester = student

        # Check for subject
        cursor.execute("SELECT id FROM subjects WHERE subject_name = %s AND branch = %s AND semester = %s",
                       (subject_name, branch, semester))
        subject = cursor.fetchone()
        if not subject:
            return redirect(url_for('admin_panel', message="Error: Subject not found for student's branch and semester."))

        subject_id = subject[0]
        current_time = datetime.now().strftime('%H:%M:%S')

        # Check if attendance already exists
        cursor.execute("SELECT id FROM attendance WHERE student_id = %s AND date = %s AND subject_id = %s",
                       (student_id, date_str, subject_id))
        existing_attendance = cursor.fetchone()

        if existing_attendance:
            cursor.execute("""
                UPDATE attendance SET status = %s, time = %s, face_matched = 0 WHERE id = %s
            """, (status, f"{date_str} {current_time}", existing_attendance[0]))
        else:
            cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, date, status, time, face_matched)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (student_id, subject_id, date_str, status, f"{date_str} {current_time}"))

        conn.commit()  # Commit the changes to the database
        conn.close()   # Close the database connection
        return redirect(url_for('admin_panel', message="Attendance added/updated successfully!"))

    except Exception as e:
        # Log the detailed error
        print(f"Error: {e}")
        return redirect(url_for('admin_panel', message="Attendance could not be added/updated. Please check the logs for details."))

@app.route('/admin', methods=['GET'])
def admin_panel():
    if 'admin_name' not in session:
        return redirect(url_for('admin_login'))

    # Get filter values and message
    search_name = request.args.get('search_name', '').strip()
    search_roll_number = request.args.get('search_roll_number', '').strip()
    search_subject_name = request.args.get('search_subject_name', '').strip()
    search_date = request.args.get('search_date', '').strip()
    status_filter = request.args.get('status_filter', '').strip()
    message = request.args.get('message', '').strip()

    conn = connect_db()
    cursor = conn.cursor()

    query = """
        SELECT a.date, s.full_name, s.roll_number, s.branch, sub.subject_name,
               a.face_matched, a.status, a.time
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE 1=1
    """
    params = []

    if search_name:
        query += " AND s.full_name = %s"
        params.append(search_name)

    if search_roll_number:
        query += " AND s.roll_number = %s"
        params.append(search_roll_number)

    if search_subject_name:
        query += " AND sub.subject_name = %s"
        params.append(search_subject_name)

    if search_date:
        query += " AND a.date = %s"
        params.append(search_date)

    if status_filter:
        query += " AND a.status = %s"
        params.append(status_filter)

    # Order results by date and time descending (latest first)
    query += " ORDER BY a.date DESC, a.time DESC"
    
    cursor.execute(query, tuple(params))
    records = cursor.fetchall()
    conn.close()

    attendance_records = [{
        'date': row[0],
        'student_name': row[1],
        'roll_number': row[2],
        'branch': row[3],
        'subject_name': row[4],
        'face_matched': row[5],
        'status': row[6],
        'time': row[7]
    } for row in records]

    return render_template('admin.html',
                           admin_name=session['admin_name'],
                           attendance_records=attendance_records,
                           search_name=search_name,
                           search_roll_number=search_roll_number,
                           search_subject_name=search_subject_name,
                           search_date=search_date,
                           status_filter=status_filter,
                           today_date=datetime.today().date(),
                           no_results=(len(attendance_records) == 0),
                           message=message)
   
def admin_dashboard():
    if 'admin_name' not in session:
        return redirect(url_for('admin_login'))

    search_name = request.args.get('search_name', '')
    search_roll_number = request.args.get('search_roll_number', '')
    search_subject_name = request.args.get('search_subject_name', '')
    search_date = request.args.get('search_date', '')
    status_filter = request.args.get('status_filter', '')

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT a.date, s.full_name AS student_name, s.roll_number, s.branch,
               subj.subject_name, a.face_matched, a.status, a.time
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects subj ON a.subject_id = subj.id
        WHERE 1=1
    """
    params = []

    if search_name:
        query += " AND s.full_name = %s"
        params.append(search_name)
    if search_roll_number:
        query += " AND s.roll_number = %s"
        params.append(search_roll_number)
    if search_subject_name:
        query += " AND subj.subject_name = %s"
        params.append(search_subject_name)
    if search_date:
        query += " AND a.date = %s"
        params.append(search_date)
    if status_filter:
        query += " AND a.status = %s"
        params.append(status_filter)

    cursor.execute(query, tuple(params))
    attendance_records = cursor.fetchall()

    conn.close()

    return render_template(
        'admin.html',
        admin_name=session['admin_name'],
        today_date=date.today().strftime('%Y-%m-%d'),
        attendance_records=attendance_records,
        search_name=search_name,
        search_roll_number=search_roll_number,
        search_subject_name=search_subject_name,
        search_date=search_date,
        status_filter=status_filter,
    )


@app.route('/admin-logout')
def admin_logout():
    session.clear() 
    return render_template("index.html")

@app.route('/export_csv', methods=['GET'])
def export_csv():
    full_name = request.args.get('full_name')
    roll_number = request.args.get('roll_number')
    subject_name = request.args.get('subject_name')
    date = request.args.get('date')
    status = request.args.get('status')

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT 
            a.date, 
            s.full_name, 
            s.roll_number, 
            s.branch, 
            subj.subject_name, 
            s.semester, 
            a.status, 
            a.time,
            a.face_matched
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects subj ON a.subject_id = subj.id
    """

    filters = []
    values = []

    if full_name:
        filters.append("s.full_name = %s")
        values.append(full_name)
    if roll_number:
        filters.append("s.roll_number = %s")
        values.append(roll_number)
    if subject_name:
        filters.append("subj.subject_name = %s")
        values.append(subject_name)
    if date:
        filters.append("a.date = %s")
        values.append(date)
    if status:
        filters.append("a.status = %s")
        values.append(status)

    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    base_query += " ORDER BY a.date DESC"

    cursor.execute(base_query, values)
    records = cursor.fetchall()
    conn.close()

    if not records:
        return redirect(url_for('admin_panel', message="No attendance records found."))

    rows = []
    for idx, record in enumerate(records, start=1):
        rows.append([ 
            str(idx),
            str(record['date']),
            record['full_name'],
            record['roll_number'],
            record['branch'],
            record['subject_name'],
            record['semester'],
            'Matched' if record['face_matched'] else 'Not Matched/Manual Attendance',
            record['status'],
            str(record['time'])
        ])

    headers = ["S.No", "Date", "Student Name", "Roll Number", "Branch", "Subject", "Semester", "Captured Face", "Status", "Time"]

    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    def format_row(row):
        return ' , '.join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))

    output = io.StringIO()
    output.write(format_row(headers) + "\n")
    for row in rows:
        output.write(format_row(row) + "\n")

    # ✅ Dynamic file name logic
    if full_name:
        safe_name = full_name.strip().replace(" ", "_")
        filename = f"{safe_name}_attendance_records.csv"
    else:
        filename = "attendance_records.csv"

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'

    return response


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET': 
        return render_template('admin-login.html')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email = %s AND password = %s", (email, password))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin_logged_in'] = True
            session['admin_name'] = admin['full_name'] 
            return jsonify({"success": True, "message": "Login successful!", "redirect": "/admin"})
        else:
            return jsonify({"success": False, "message": "Invalid Credentials!"})



@app.route('/download_report', methods=['GET'])
def download_report():
    # Check if student is logged in
    student_id = session.get('student_id')
    if not student_id:
        return """
            <script>
                alert('Unauthorized access or session expired. Please log in again.');
                window.location.href = '/student-login';
            </script>
        """

    # Get the subject filter if provided
    subject_id = request.args.get('subject_id')

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Prepare the query
    query = """
        SELECT s.full_name, s.semester, a.date, s.roll_number, s.branch, a.face_matched, a.status, a.time, sub.subject_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.student_id = %s
    """
    params = [student_id]

    if subject_id:
        query += " AND a.subject_id = %s"
        params.append(subject_id)

    query += " ORDER BY a.date DESC, a.time DESC"  # Order by date and time in descending order

    # Execute the query
    cursor.execute(query, tuple(params))
    records = cursor.fetchall()
    conn.close()

    if not records:
        return "No attendance records found for the student", 404

    student_name = records[0]['full_name']
    student_semester = records[0]['semester']

    # Prepare rows: each row is a list of values
    rows = []
    for i, rec in enumerate(records, start=1):
        rows.append([
            i,
            rec['date'],
            rec['full_name'],
            rec['roll_number'],
            rec['branch'],
            rec['subject_name'],
            rec['semester'],
            "Matched" if rec['face_matched'] else "Not Matched/Manual Attendance",
            rec['status'],
            rec['time']
        ])

    # Column headers
    headers = ["S.No", "Date", "Student Name", "Roll Number", "Branch", "Subject", "Semester", "Captured Face", "Status", "Time"]

    # Calculate column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    # Format rows with spacing
    def format_row(row):
        return ' , '.join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))

    # Generate CSV output
    output = io.StringIO()
    output.write(format_row(headers) + "\n")
    for row in rows:
        output.write(format_row(row) + "\n")

    # Generate the filename
    filename = f'attendance_report_{student_name.replace(" ", "_")}_Semester_{student_semester}.csv'
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'

    return response


# Connect to MySQL Database
db = mysql.connector.connect(host="localhost", user="root", password="tarunboramysql@2007", database="attendance_system")
cursor = db.cursor()

# Load stored face encodings from the database
cursor.execute("SELECT student_id, face_encoding FROM face_data")
stored_face_data = cursor.fetchall()

stored_face_encodings = []
student_ids = []
for record in stored_face_data:
    student_ids.append(record[0])
    face_encoding = pickle.loads(record[1])  # Deserialize the face encoding
    stored_face_encodings.append(face_encoding)

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()

    image_data = data.get('image')
    subject_id = data.get('subject_id')

    if not image_data:
        return jsonify({"message": "Image is missing."}), 400

    if not subject_id or str(subject_id).strip() == "" or str(subject_id) == "0":
        return jsonify({"message": "Please select a valid subject."}), 400

    try:
        image_data = image_data.split(",")[1]
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        frame = np.array(image)
    except Exception as e:
        print(f"Image processing error: {str(e)}")
        return jsonify({"message": f"Image processing error: {str(e)}"}), 400

    student_id_from_session = session.get('student_id')
    if not student_id_from_session:
        print("No student logged in.")
        return jsonify({"message": "No student logged in."}), 401

    # Ensure face data exists for this student
    if student_id_from_session not in student_ids:
        return jsonify({"message": "No face data found. Please register your face first."}), 403

    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    print(f"Detected faces: {len(face_locations)}")

    if len(face_locations) != 1:
        return jsonify({"message": "Make sure only your face is visible in the frame."}), 400

    if len(face_encodings) != 1:
        return jsonify({"message": "Face not recognized properly. Please try again with clear face visibility."}), 400

    face_encoding = face_encodings[0]
    matches = face_recognition.compare_faces(stored_face_encodings, face_encoding, tolerance=0.5)

    matched_indices = [i for i, matched in enumerate(matches) if matched]

    if not matched_indices:
        return jsonify({"message": "Face not recognized properly. Please try again with clear face visibility."}), 400

    # Check if logged-in student's face was matched
    for match_index in matched_indices:
        recognized_student_id = student_ids[match_index]
        if recognized_student_id == student_id_from_session:
            today = datetime.now().strftime("%Y-%m-%d")

            try:
                cursor.execute("SELECT subject_name FROM subjects WHERE id = %s", (subject_id,))
                subject = cursor.fetchone()

                if not subject:
                    print("Subject not found in database.")
                    return jsonify({"message": "Invalid subject."}), 400

                subject_name = subject[0]
                print(f"Subject found: {subject_name}")

                cursor.execute("""
                    SELECT COUNT(*) FROM attendance 
                    WHERE student_id = %s AND subject_id = %s AND date = %s
                """, (recognized_student_id, subject_id, today))
                result = cursor.fetchone()

                if result[0] > 0:
                    print(f"Attendance for subject {subject_name} already exists today.")
                    return jsonify({"message": f"Attendance for subject {subject_name} already marked today."})

                cursor.execute("""
                    INSERT INTO attendance (student_id, subject_id, date, status, face_matched)
                    VALUES (%s, %s, %s, 'Present', 1)
                    ON DUPLICATE KEY UPDATE status = 'Present', face_matched = 1
                """, (recognized_student_id, subject_id, today))

                db.commit()
                print(f"Attendance marked for subject {subject_name}.")
                return jsonify({"message": f"Attendance marked for subject {subject_name}."})

            except mysql.connector.Error as err:
                db.rollback()
                print(f"Database error: {err}")
                return jsonify({"message": f"Database error: {err}"}), 500

        else:
            # Face matched a different student
            return jsonify({"message": "You are not authorized to mark attendance for another person."}), 403

    # Shouldn't reach here
    return jsonify({"message": "Face not recognized properly. Please try again with clear face visibility."}), 400

@app.route('/get_subjects', methods=['GET'])
def get_subjects():
    student_id = session.get('student_id')

    if not student_id:
        print("Unauthorized access attempt: No student_id in session.")
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Fetch branch and semester for the logged-in student
        cursor.execute("SELECT branch, semester FROM students WHERE id = %s", (student_id,))
        result = cursor.fetchone()

        if result:
            branch, semester = result
            branch = branch.strip()
            semester = semester.strip()

            # Fetch subjects for branch and semester
            cursor.execute("""
                SELECT id, subject_name FROM subjects 
                WHERE branch = %s AND semester = %s
            """, (branch, semester))
            subjects = cursor.fetchall()
            conn.close()

            if not subjects:
                print(f"No subjects found for branch: {branch}, semester: {semester}")
                return jsonify({'error': "No subjects found for this student's branch and semester."}), 404

            subject_list = [{'id': sub[0], 'name': sub[1]} for sub in subjects]
            return jsonify(subject_list)

        else:
            print(f"Student not found in database for student_id: {student_id}")
            return jsonify({'error': f'Student with ID {student_id} not found in the database.'}), 404

    except mysql.connector.Error as err:
        print(f"Database error while fetching subjects: {err}")
        return jsonify({'error': 'Database error occurred while fetching subjects.'}), 500

@app.route('/register_student_face')
def register_student_face():
    return render_template('register_student_face.html')
@app.route('/register_face', methods=['POST'])
def register_face():
    try:
        data = request.get_json()

        # Validate required fields: fullname, rollno, and image data
        missing_fields = [k for k in ('fullname', 'rollno', 'image') if k not in data]
        if missing_fields:
            return jsonify({'message': f"Missing fields: {', '.join(missing_fields)}."}), 400

        # Retrieve the input data
        input_fullname = data['fullname'].strip()
        rollno = data['rollno'].strip()

        try:
            image_data = data['image'].split(',')[1]
        except (IndexError, base64.binascii.Error):
            return jsonify({'message': 'Invalid image data format.'}), 400

        # Retrieve student ID from the database using exact match (case-sensitive)
        cursor.execute(
            "SELECT id, full_name FROM students WHERE BINARY full_name = %s AND roll_number = %s",
            (input_fullname, rollno)
        )
        student = cursor.fetchone()

        if not student:
            return jsonify({'message': 'Student not found. Please verify with correct details.'}), 404

        student_id = student[0]
        student_fullname = student[1]

        # Check if the student has already registered too many faces
        cursor.execute("SELECT COUNT(*) FROM face_data WHERE student_id = %s", (student_id,))
        face_count = cursor.fetchone()[0]

        if face_count >= 5:
            return jsonify({'message': 'Maximum face registrations (5) reached.'}), 400

        # Decode and load the image
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'message': 'Unable to decode image. Please ensure a valid image is provided.'}), 400

        # Detect face(s)
        face_locations = face_recognition.face_locations(img)
        face_encodings = face_recognition.face_encodings(img, face_locations)

        if not face_encodings:
            return jsonify({'message': 'No face detected in the image. Please try again with a clear face.'}), 400

        if len(face_encodings) > 1:
            return jsonify({'message': 'Multiple faces detected. Please ensure only one person is in the frame.'}), 400

        # Optional: Check if face is blurry
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30:  # Adjusted threshold as needed for better face detection
            return jsonify({'message': 'Image is too blurry for reliable face recognition. Please upload a clearer image to avoid problems during attendance.'}), 400

        face_encoding = face_encodings[0]

        # Check for duplicate face
        cursor.execute("SELECT student_id, face_encoding FROM face_data")
        existing_faces = cursor.fetchall()

        for row in existing_faces:
            existing_encoding = pickle.loads(row[1])
            match = face_recognition.compare_faces([existing_encoding], face_encoding, tolerance=0.5)
            if match[0] and row[0] != student_id:
                return jsonify({
                    'message': 'This face is already registered under a different student. Duplicate registration is not allowed.'
                }), 403

        # Save new face encoding in database
        encoded_face_data = pickle.dumps(face_encoding)
        cursor.execute(
            "INSERT INTO face_data (student_id, face_encoding) VALUES (%s, %s)",
            (student_id, encoded_face_data)
        )
        db.commit()

        return jsonify({'message': f'Face registered successfully for {student_fullname}.'}), 200

    except Exception as e:
        import traceback
        print("Error during face registration:", e)
        print(traceback.format_exc())
        return jsonify({'message': f'Face registration failed. Error: {str(e)}'}), 500



# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='tarunboramysql@2007',
        database='attendance_system'
    )

# Step 1: Request password reset
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None

    if request.method == 'POST':
        roll = request.form['roll_number']
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM students WHERE roll_number = %s", (roll,))
        user = cursor.fetchone()

        if user:
            token = serializer.dumps(roll, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)
        else:
            flash('Roll number not found.', 'danger')

        db.close()

    return render_template('forgot_password.html', reset_link=reset_link)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        roll = serializer.loads(token, salt='password-reset-salt', max_age=300)
    except:
        return "Token is invalid or expired", 400

    if request.method == 'POST':
        new_password = request.form['new_password']

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("UPDATE students SET password = %s WHERE roll_number = %s", (new_password, roll))
        db.commit()
        db.close()

        flash('Password successfully updated. You can now log in.', 'success')
        return redirect(url_for('forgot_password'))

    return render_template('reset_password.html')

# Step 2: Reset form with token
# Step 1: Request Password Reset for Admin
@app.route('/forgot-password-admin', methods=['GET', 'POST'])
def forgot_password_admin():
    reset_link = None

    if request.method == 'POST':
        email = request.form['email']
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM admins WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            token = serializer.dumps(email, salt='admin-reset')
            reset_link = url_for('reset_password_admin', token=token, _external=True)
        else:
            flash('Email not found.', 'danger')

        db.close()

    return render_template('forgot_password_admin.html', reset_link=reset_link)

# Step 2: Admin Password Reset Form
@app.route('/reset-password-admin/<token>', methods=['GET', 'POST'])
def reset_password_admin(token):
    try:
        email = serializer.loads(token, salt='admin-reset', max_age=300)
    except:
        return "Token is invalid or expired", 400

    if request.method == 'POST':
        new_password = request.form['new_password']

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("UPDATE admins SET password = %s WHERE email = %s", (new_password, email))
        db.commit()
        db.close()

        flash('Password successfully updated. You can now log in.', 'success')
        return redirect(url_for('forgot_password_admin'))

    return render_template('reset_password_admin.html')


@app.route('/fetch_subjects_by_roll', methods=['POST'])
def fetch_subjects_by_roll():
    student_name = request.form.get('student_name')
    roll_number = request.form.get('roll_number')

    if not student_name or not roll_number:
        return jsonify({'subjects': [], 'error': 'Student name and roll number are required.'})

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Check if the student exists
        cursor.execute("SELECT id FROM students WHERE full_name = %s AND roll_number = %s", 
                       (student_name, roll_number))
        student = cursor.fetchone()

        if not student:
            # If the student is not found
            return jsonify({'subjects': [], 'error': 'Student not found in the database.'})

        # Fetch branch and semester from the student details
        student_id = student[0]
        cursor.execute("SELECT branch, semester FROM students WHERE id = %s", (student_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'subjects': [], 'error': 'No branch or semester information available for this student.'})

        branch, semester = result

        # Fetch subjects based on branch and semester
        cursor.execute("SELECT subject_name FROM subjects WHERE branch = %s AND semester = %s", (branch, semester))
        subjects = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not subjects:
            return jsonify({'subjects': [], 'error': 'No subjects found for this student\'s branch and semester.'})

        return jsonify({'subjects': subjects, 'error': None})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'subjects': [], 'error': 'An error occurred while fetching subjects.'})



@app.route('/fetch_subjects_by_roll_for_attendance_records', methods=['POST'])
def fetch_subjects_by_roll_for_attendance_records():
    student_name = request.form.get('student_name')
    roll_number = request.form.get('roll_number')

    if not student_name or not roll_number:
        return jsonify({'subjects': [], 'error': 'Student name and roll number are required.'})

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Check if the student exists
        cursor.execute("SELECT id, branch, semester FROM students WHERE full_name = %s AND roll_number = %s", 
                       (student_name, roll_number))
        student = cursor.fetchone()

        if not student:
            # If the student is not found
            return jsonify({'subjects': [], 'error': 'Student not found in the database.'})

        # Fetch subjects based on branch and semester
        student_id = student[0]
        branch = student[1]
        semester = student[2]

        cursor.execute("SELECT subject_name FROM subjects WHERE branch = %s AND semester = %s", 
                       (branch, semester))
        subjects = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not subjects:
            return jsonify({'subjects': [], 'error': 'No subjects found for this student\'s branch and semester.'})

        return jsonify({'subjects': subjects, 'error': None})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'subjects': [], 'error': 'An error occurred while fetching subjects.'})


if __name__ == '__main__':
    app.run(debug=True)

