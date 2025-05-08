from flask import jsonify, Flask, render_template, request, redirect, url_for, session, make_response, send_file, flash
import secrets
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
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

app = Flask(__name__)
CORS(app)
app.secret_key = "b7a9c11e6b8f8e489a3f9e"  


app.permanent_session_lifetime = timedelta(minutes=5)  # Example: 5 mins session
serializer = URLSafeTimedSerializer(app.secret_key)

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",  
        password="tarunboramysql@2007",  
        database="face_recognition_attendance_system"
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
            session['student_id'] = student['id']#
            session['full_name'] = student['full_name']
            session['branch'] = student['branch']
            session['semester'] = student['semester']
            session['roll_number'] = roll_number  
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

    cursor.execute("SELECT id, subject_name FROM subjects WHERE semester = %s AND branch = %s", (semester, branch))
    subjects = cursor.fetchall()

    return render_template('attendance.html', subjects=subjects)


@app.route('/student_dashboard-logout')
def student_dashboard_logout():
    session.clear() 
    return render_template("index.html")

@app.route('/student_dashboard')
def student_dashboard():
    if 'roll_number' not in session:
        return redirect(url_for('student_login'))

    roll_number = session['roll_number']
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM subjects
        WHERE branch = %s AND semester = %s
    """, (student['branch'], student['semester']))
    subjects = cursor.fetchall()

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

    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    if not student:
        return "Error: Student details not found."

    cursor.execute("SELECT * FROM subjects WHERE branch = %s AND semester = %s", (branch, semester))
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("student_dashboard.html", student=student, records=records, subjects=subjects)


@app.route('/download_report', methods=['GET'])
def download_report():
    student_id = session.get('student_id')
    if not student_id:
        return """
            <script>
                alert('Unauthorized access or session expired. Please log in again.');
                window.location.href = '/student-login';
            </script>
        """

    subject_id = request.args.get('subject_id')

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

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

    query += " ORDER BY a.date DESC, a.time DESC"  
    cursor.execute(query, tuple(params))
    records = cursor.fetchall()
    conn.close()

    if not records:
        return "No attendance records found for the student", 404

    student_name = records[0]['full_name']
    student_semester = records[0]['semester']

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

    filename = f'attendance_report_{student_name.replace(" ", "_")}_Semester_{student_semester}.csv'
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



@app.route('/register_student_face')
def register_student_face():
    return render_template('register_student_face.html')
@app.route('/register_face', methods=['POST'])
def register_face():
    try:
        data = request.get_json()

        missing_fields = [k for k in ('fullname', 'rollno', 'image') if k not in data]
        if missing_fields:
            return jsonify({'message': f"Missing fields: {', '.join(missing_fields)}."}), 400

        input_fullname = data['fullname'].strip()
        rollno = data['rollno'].strip()

        try:
            image_data = data['image'].split(',')[1]
        except (IndexError, base64.binascii.Error):
            return jsonify({'message': 'Invalid image data format.'}), 400

        cursor.execute(
            "SELECT id, full_name FROM students WHERE BINARY full_name = %s AND roll_number = %s",
            (input_fullname, rollno)
        )
        student = cursor.fetchone()

        if not student:
            return jsonify({'message': 'Student not found. Please verify with correct details.'}), 404

        student_id = student[0]
        student_fullname = student[1]

        cursor.execute("SELECT COUNT(*) FROM face_data WHERE student_id = %s", (student_id,))
        face_count = cursor.fetchone()[0]

        if face_count >= 5:
            return jsonify({'message': 'Maximum face registrations (5) reached.'}), 400

        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'message': 'Unable to decode image. Please ensure a valid image is provided.'}), 400

        face_locations = face_recognition.face_locations(img)
        face_encodings = face_recognition.face_encodings(img, face_locations)

        if not face_encodings:
            return jsonify({'message': 'No face detected in the image. Please try again with a clear face.'}), 400

        if len(face_encodings) > 1:
            return jsonify({'message': 'Multiple faces detected. Please ensure only one person is in the frame.'}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30:  
            return jsonify({'message': 'Image is too blurry for reliable face recognition. Please upload a clearer image to avoid problems during attendance.'}), 400

        face_encoding = face_encodings[0]

        cursor.execute("SELECT student_id, face_encoding FROM face_data")
        existing_faces = cursor.fetchall()

        for row in existing_faces:
            existing_encoding = pickle.loads(row[1])
            match = face_recognition.compare_faces([existing_encoding], face_encoding, tolerance=0.5)
            if match[0] and row[0] != student_id:
                return jsonify({
                    'message': 'This face is already registered under a different student. Duplicate registration is not allowed.'
                }), 403

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


@app.route('/admin', methods=['GET'])
def admin_panel():
    if 'admin_name' not in session:
        return redirect(url_for('admin_login'))

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

from flask import flash, redirect, url_for, session, request
from datetime import datetime

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

        cursor.execute("SELECT id, branch, semester FROM students WHERE full_name = %s AND roll_number = %s",
                       (student_name, roll_number))
        student = cursor.fetchone()
        if not student:
            flash("Error: Student not found.", "error")
            return redirect(url_for('admin_panel'))

        student_id, branch, semester = student

        cursor.execute("SELECT id FROM subjects WHERE subject_name = %s AND branch = %s AND semester = %s",
                       (subject_name, branch, semester))
        subject = cursor.fetchone()
        if not subject:
            flash("Error: Subject not found for student's branch and semester.", "error")
            return redirect(url_for('admin_panel'))

        subject_id = subject[0]
        current_time = datetime.now().strftime('%H:%M:%S')

        cursor.execute("SELECT id FROM attendance WHERE student_id = %s AND date = %s AND subject_id = %s",
                       (student_id, date_str, subject_id))
        existing_attendance = cursor.fetchone()

        if existing_attendance:
            cursor.execute("""
                UPDATE attendance 
                SET status = %s, time = %s, face_matched = 0 
                WHERE id = %s
            """, (status, f"{date_str} {current_time}", existing_attendance[0]))
        else:
            cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, date, status, time, face_matched)
                VALUES (%s, %s, %s, %s, %s, 0)
            """, (student_id, subject_id, date_str, status, f"{date_str} {current_time}"))

        conn.commit()
        conn.close()

        flash("Attendance added/updated successfully!", "success")
        return redirect(url_for('admin_panel'))

    except Exception as e:
        print(f"Error: {e}")
        flash("Attendance could not be added/updated. Please check the logs for details.", "error")
        return redirect(url_for('admin_panel'))


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

    if full_name:
        safe_name = full_name.strip().replace(" ", "_")
        filename = f"{safe_name}_attendance_records.csv"
    else:
        filename = "attendance_records.csv"

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'

    return response



def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='tarunboramysql@2007',
        database='face_recognition_attendance_system'
    )

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
        roll = serializer.loads(token, salt='password-reset-salt', max_age=180)
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

@app.route('/reset-password-admin/<token>', methods=['GET', 'POST'])
def reset_password_admin(token):
    try:
        email = serializer.loads(token, salt='admin-reset', max_age=180)
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

        cursor.execute("SELECT id FROM students WHERE full_name = %s AND roll_number = %s", 
                       (student_name, roll_number))
        student = cursor.fetchone()

        if not student:
            return jsonify({'subjects': [], 'error': 'Student not found in the database.'})

        student_id = student[0]
        cursor.execute("SELECT branch, semester FROM students WHERE id = %s", (student_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'subjects': [], 'error': 'No branch or semester information available for this student.'})

        branch, semester = result

        cursor.execute("SELECT subject_name FROM subjects WHERE branch = %s AND semester = %s", (branch, semester))
        subjects = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not subjects:
            return jsonify({'subjects': [], 'error': 'No subjects found for this student\'s branch and semester.'})

        return jsonify({'subjects': subjects, 'error': None})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'subjects': [], 'error': 'An error occurred while fetching subjects.'})


@app.route('/mark_student_attendance')
def mark_student_attendance():
    return render_template('attendance.html')


#  API to get student info based on full name and roll number
@app.route('/api/student_info', methods=['POST'])
def get_student_info():
    data = request.get_json()
    full_name = data.get('full_name')
    roll_number = data.get('roll_number')

    if not full_name or not roll_number:
        return jsonify({"error": "Full name and Roll number are required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT branch, semester FROM students
            WHERE full_name = %s AND roll_number = %s
        """, (full_name, roll_number))
        student = cursor.fetchone()

        if not student:
            return jsonify({"found": False}), 200  # Student not found

        cursor.execute("""
            SELECT subject_name FROM subjects
            WHERE branch = %s AND semester = %s
        """, (student['branch'], student['semester']))
        subjects = [row['subject_name'] for row in cursor.fetchall()]

        return jsonify({
            "found": True,
            "branch": student['branch'],
            "semester": student['semester'],
            "subjects": subjects
        })

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Route to mark attendance
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()

    image_data = data.get('image')
    full_name = data.get('full_name')
    roll_number = data.get('roll_number')
    branch = data.get('branch')
    semester = data.get('semester')
    subject_name = data.get('subject_name')

    if not image_data or not full_name or not roll_number or not branch or not semester or not subject_name:
        return jsonify({"message": "All fields are required to mark attendance."}), 400

    try:
        image_data = image_data.split(",")[1]
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        frame = np.array(image)
    except Exception as e:
        print(f"Image processing error: {str(e)}")
        return jsonify({"message": f"Image processing error: {str(e)}"}), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM students WHERE roll_number = %s AND full_name = %s", (roll_number, full_name))
        student = cursor.fetchone()

        if not student:
            return jsonify({"message": "Student not found."}), 400

        student_id = student[0]

        cursor.execute("SELECT student_id, face_encoding FROM face_data WHERE student_id = %s", (student_id,))
        stored_face_data = cursor.fetchall()

        if not stored_face_data:
            return jsonify({"message": "No face data found for this student. Please register your face first."}), 403

        stored_face_encodings = []
        for record in stored_face_data:
            face_encoding = pickle.loads(record[1])
            stored_face_encodings.append(face_encoding)

        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        if len(face_locations) > 1:
            return jsonify({"message": "Make sure only your face is visible in the frame."}), 400

        if len(face_locations) == 1 and len(face_encodings) != 1:
            return jsonify({"message": "Face not recognized properly. Please try again with clear face visibility."}), 400

        if len(face_locations) == 0:
            return jsonify({"message": "No face detected. Please ensure your face is clearly visible in the camera."}), 400


        face_encoding = face_encodings[0]
        matches = face_recognition.compare_faces(stored_face_encodings, face_encoding, tolerance=0.5)

        if not any(matches):
            return jsonify({"message": "Unauthorized attempt detected. Your face does not match the registered student profile."}), 403

        cursor.execute("""
            SELECT id FROM subjects 
            WHERE subject_name = %s AND branch = %s AND semester = %s
        """, (subject_name, branch, semester))
        subject = cursor.fetchone()

        if not subject:
            return jsonify({"message": "Subject not found."}), 400

        subject_id = subject[0]

        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT COUNT(*) FROM attendance 
            WHERE student_id = %s AND subject_id = %s AND date = %s
        """, (student_id, subject_id, today))
        result = cursor.fetchone()

        if result[0] > 0:
            return jsonify({"message": "Attendance already marked for today."}), 200

        cursor.execute("""
            INSERT INTO attendance (student_id, subject_id, date, status, face_matched)
            VALUES (%s, %s, %s, 'Present', 1)
        """, (student_id, subject_id, today))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({"message": f"Attendance marked for {subject_name}."}), 200

    except mysql.connector.Error as err:
        return jsonify({"message": f"Database error: {err}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
