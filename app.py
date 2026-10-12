import asyncio
import sys
import os
import io
import json
from datetime import datetime

# Handle event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from flask_cors import CORS
from PIL import Image
import numpy as np
import pandas as pd
import segno

# Core Logic Imports
from src.database.config import supabase
from src.database.db import (
    check_teacher_exists, create_teacher, teacher_login,
    get_teacher_subjects, get_attendance_for_teacher,
    get_all_students, get_student_by_id, create_student,
    get_student_subjects, get_student_attendance,
    unenroll_student_to_subject, enroll_student_to_subject,
    create_subject, create_attendance,
    get_subject_by_code, check_enrollment_exists,
    get_enrolled_students_with_embeddings
)
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding, process_bulk_audio

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def make_serializable(obj):
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj


# ─────────────────────────────────────────────
#  Frontend Routes
# ─────────────────────────────────────────────

@app.route('/')
def home():
    landing_url = os.environ.get('LANDING_PAGE_URL', 'http://localhost:5000')
    return render_template('index.html', landing_url=landing_url)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


# ─────────────────────────────────────────────
#  QR Code Route
# ─────────────────────────────────────────────

@app.route('/api/qrcode')
def get_qrcode():
    """Generate a QR code PNG for the given subject join code."""
    code = request.args.get('code', '')
    url = f"{request.host_url}join-code={code}"
    qr = segno.make(url)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10, border=1)
    out.seek(0)
    return send_file(out, mimetype='image/png')


# ─────────────────────────────────────────────
#  Teacher API Routes
# ─────────────────────────────────────────────

@app.route('/api/teacher/register', methods=['POST'])
def teacher_register_api():
    """Register a new teacher account. Password is stored as a bcrypt hash."""
    data = request.json or {}
    username = data.get('username', '').strip()
    name = data.get('name', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username or not name or not password:
        return jsonify({"status": "error", "message": "All fields are required!"}), 400
    if check_teacher_exists(username):
        return jsonify({"status": "error", "message": "Username already taken!"}), 400
    if password != confirm_password:
        return jsonify({"status": "error", "message": "Passwords do not match!"}), 400

    try:
        res = create_teacher(username, password, name)
        return jsonify({"status": "success", "message": "Successfully created profile! You can now log in.", "data": res})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Unexpected error during registration: {str(e)}"}), 500


@app.route('/api/teacher/login', methods=['POST'])
def teacher_login_api():
    """Authenticate a teacher by username and password."""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required!"}), 400

    teacher = teacher_login(username, password)
    if teacher:
        teacher.pop('password', None)   # Never return the password hash to the client
        return jsonify({"status": "success", "teacher": teacher})
    else:
        return jsonify({"status": "error", "message": "Invalid username or password comb✅"}), 401


@app.route('/api/teacher/subjects', methods=['GET'])
def teacher_subjects_api():
    """Return all subjects created by the given teacher, with enrolment and session counts."""
    teacher_id = request.args.get('teacher_id')
    if not teacher_id:
        return jsonify({"status": "error", "message": "teacher_id is required!"}), 400
    try:
        subjects = get_teacher_subjects(int(teacher_id))
        return jsonify({"status": "success", "subjects": subjects})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/teacher/create-subject', methods=['POST'])
def teacher_create_subject_api():
    """Create a new subject classroom."""
    data = request.json or {}
    subject_code = data.get('subject_code', '').strip()
    name = data.get('name', '').strip()
    section = data.get('section', '').strip()
    teacher_id = data.get('teacher_id')

    if not subject_code or not name or not section or not teacher_id:
        return jsonify({"status": "error", "message": "All fields are required!"}), 400

    try:
        res = create_subject(subject_code, name, section, int(teacher_id))
        return jsonify({"status": "success", "message": "Subject created successfully!", "data": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/teacher/take-attendance/face', methods=['POST'])
def teacher_take_attendance_face_api():
    """
    Run face recognition on uploaded classroom photos and return attendance results.

    NOTE: This endpoint returns a PREVIEW only — attendance is NOT saved to the
    database here. The teacher must review the results and call
    POST /api/teacher/confirm-attendance to persist the logs.
    """
    subject_id_str = request.form.get('subject_id')
    if not subject_id_str:
        return jsonify({"status": "error", "message": "subject_id is required!"}), 400

    selected_subject_id = int(subject_id_str)

    files = request.files.getlist('images')
    if not files or len(files) == 0:
        return jsonify({"status": "error", "message": "No images provided!"}), 400

    try:
        all_detected_ids = {}

        for idx, file in enumerate(files):
            img = Image.open(file.stream)
            img_np = np.array(img.convert('RGB'))
            detected, _, _ = predict_attendance(img_np)

            if detected:
                for sid in detected.keys():
                    student_id = int(sid)
                    all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

        # Use centralised DB function — no direct supabase call here
        enrolled_students = get_enrolled_students_with_embeddings(selected_subject_id)

        if not enrolled_students:
            return jsonify({"status": "warning", "message": "No students enrolled in this course", "results": []})

        results = []
        attendance_to_log = []
        current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        for node in enrolled_students:
            student = node['students']
            sources = all_detected_ids.get(int(student['student_id']), [])
            is_present = len(sources) > 0

            results.append({
                "name": student['name'],
                "student_id": student['student_id'],
                "source": ", ".join(sources) if is_present else "-",
                "status": "✅ Present" if is_present else "❌ Absent"
            })

            attendance_to_log.append({
                'student_id': student['student_id'],
                'subject_id': selected_subject_id,
                'timestamp': current_timestamp,
                'is_present': bool(is_present)
            })

        return jsonify({
            "status": "success",
            "results": results,
            "logs": attendance_to_log
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/teacher/take-attendance/voice', methods=['POST'])
def teacher_take_attendance_voice_api():
    """
    Run voice recognition on an uploaded classroom audio recording and return
    attendance results.

    NOTE: Same two-step flow as face attendance — call confirm-attendance to save.
    """
    subject_id_str = request.form.get('subject_id')
    if not subject_id_str:
        return jsonify({"status": "error", "message": "subject_id is required!"}), 400

    selected_subject_id = int(subject_id_str)

    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "No audio file provided!"}), 400

    audio_file = request.files['audio']
    audio_bytes = audio_file.read()

    try:
        # Use centralised DB function — no direct supabase call here
        enrolled_students = get_enrolled_students_with_embeddings(selected_subject_id)

        if not enrolled_students:
            return jsonify({"status": "warning", "message": "No students enrolled in this course", "results": []})

        candidates_dict = {
            s['students']['student_id']: s['students']['voice_embedding']
            for s in enrolled_students if s['students'].get('voice_embedding')
        }

        if not candidates_dict:
            return jsonify({"status": "error", "message": "No enrolled students have voice profiles registered."}), 400

        detected_scores = process_bulk_audio(audio_bytes, candidates_dict)

        results = []
        attendance_to_log = []
        current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        for node in enrolled_students:
            student = node['students']
            score = detected_scores.get(student['student_id'], 0.0)
            is_present = bool(score > 0)

            results.append({
                "name": student['name'],
                "student_id": student['student_id'],
                "source": f"{score:.2f}" if is_present else "-",
                "status": "✅ Present" if is_present else "❌ Absent"
            })

            attendance_to_log.append({
                'student_id': student['student_id'],
                'subject_id': selected_subject_id,
                'timestamp': current_timestamp,
                'is_present': bool(is_present)
            })

        return jsonify({
            "status": "success",
            "results": results,
            "logs": attendance_to_log
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/teacher/confirm-attendance', methods=['POST'])
def teacher_confirm_attendance_api():
    """
    Persist attendance logs to the database.
    This is the ONLY endpoint that writes attendance records.
    The frontend calls this after the teacher reviews and confirms the preview.
    """
    data = request.json or {}
    logs = data.get('logs', [])
    if not logs:
        return jsonify({"status": "error", "message": "No logs provided!"}), 400

    try:
        create_attendance(logs)
        return jsonify({"status": "success", "message": "Attendance saved successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Sync failed: {str(e)}"}), 500


@app.route('/api/teacher/records', methods=['GET'])
def teacher_records_api():
    """
    Return grouped attendance session summaries for all subjects taught by
    the given teacher. Each row represents one unique attendance session.
    """
    teacher_id = request.args.get('teacher_id')
    if not teacher_id:
        return jsonify({"status": "error", "message": "teacher_id is required!"}), 400

    try:
        records = get_attendance_for_teacher(int(teacher_id))
        if not records:
            return jsonify({"status": "success", "records": []})

        data = []
        for r in records:
            ts = r.get('timestamp')
            if ts:
                dt = datetime.fromisoformat(ts)
                ts_group = dt.strftime("%Y-%m-%dT%H:%M:%S")
                time_display = dt.strftime("%Y-%m-%d %I:%M %p")
            else:
                ts_group = None
                time_display = "N/A"

            data.append({
                "ts_group": ts_group,
                "Time": time_display,
                "Subject": r['subjects']['name'],
                "SubjectCode": r['subjects']['subject_code'],
                "is_present": bool(r.get('is_present', False))
            })

        df = pd.DataFrame(data)
        summary = (
            df.groupby(['ts_group', 'Time', 'Subject', 'SubjectCode'])
            .agg(
                Present_Count=('is_present', 'sum'),
                Total_Count=('is_present', 'count')
            ).reset_index()
        )

        summary['AttendanceStats'] = (
            "✅ " + summary['Present_Count'].astype(str) + " / "
            + summary['Total_Count'].astype(str) + ' Students'
        )

        display_df = (summary.sort_values(by='ts_group', ascending=False)
                      [['Time', 'Subject', 'SubjectCode', 'AttendanceStats']])

        records_list = display_df.to_dict(orient='records')
        return jsonify({"status": "success", "records": records_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  Student API Routes
# ─────────────────────────────────────────────

@app.route('/api/student/login-face', methods=['POST'])
def student_login_face_api():
    """
    Authenticate a student by face recognition.

    Flow:
      1. Detect and embed the face from the uploaded image.
      2. Run the cached SVM classifier.
      3. If a match is found, fetch only that student by ID (targeted query).
      4. Return the student's basic profile.
    """
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No face image captured!"}), 400

    file = request.files['image']
    try:
        img = Image.open(file.stream)
        img_np = np.array(img.convert('RGB'))

        detected, all_ids, num_faces = predict_attendance(img_np)

        if num_faces == 0:
            return jsonify({"status": "error", "message": "Face not found!"}), 400
        elif num_faces > 1:
            return jsonify({"status": "error", "message": "Multiple faces detected!"}), 400

        if detected:
            student_id = int(list(detected.keys())[0])
            # FIX: Use targeted single-record lookup instead of fetching all students
            student = get_student_by_id(student_id)

            if student:
                student_serialized = {
                    "student_id": int(student['student_id']),
                    "name": student['name']
                }
                return jsonify({"status": "success", "message": f"Welcome back, {student['name']}!", "student": student_serialized})

        return jsonify({"status": "register", "message": "Face not recognized. You might be a new student!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/register', methods=['POST'])
def student_register_api():
    """
    Register a new student with face (required) and voice (optional) embeddings.
    After insertion, immediately retrains the SVM classifier.
    """
    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({"status": "error", "message": "Name is required!"}), 400

    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "Face photo is required for registration!"}), 400

    image_file = request.files['image']
    audio_file = request.files.get('audio')  # Optional voice enrollment

    try:
        img = Image.open(image_file.stream)
        img_np = np.array(img.convert('RGB'))
        encodings = get_face_embeddings(img_np)

        if not encodings:
            return jsonify({"status": "error", "message": "Could not capture your facial features for registration. Please retry."}), 400

        face_emb = encodings[0].tolist()
        voice_emb = None

        if audio_file:
            audio_bytes = audio_file.read()
            voice_emb = get_voice_embedding(audio_bytes)

        response_data = create_student(name, face_embedding=face_emb, voice_embedding=voice_emb)

        if response_data:
            # Retrain classifier so new student is immediately recognizable
            train_classifier()
            student = response_data[0]
            student_serialized = {
                "student_id": int(student['student_id']),
                "name": student['name']
            }
            return jsonify({"status": "success", "message": f"Profile created! Hi, {name}!", "student": student_serialized})

        return jsonify({"status": "error", "message": "Database insertion failed."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/subjects', methods=['GET'])
def student_subjects_api():
    """Return enrolled subjects for a student with attendance statistics."""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"status": "error", "message": "student_id is required!"}), 400

    try:
        subjects_data = get_student_subjects(int(student_id))
        logs_data = get_student_attendance(int(student_id))

        stats_map = {}
        for log in logs_data:
            sid = int(log['subject_id'])
            if sid not in stats_map:
                stats_map[sid] = {"total": 0, "attended": 0}
            stats_map[sid]['total'] += 1
            if log.get('is_present'):
                stats_map[sid]['attended'] += 1

        formatted_subjects = []
        for sub_node in subjects_data:
            sub = sub_node['subjects']
            sid = int(sub['subject_id'])
            stats = stats_map.get(sid, {"total": 0, "attended": 0})

            formatted_subjects.append({
                "subject_id": sid,
                "name": sub['name'],
                "subject_code": sub['subject_code'],
                "section": sub['section'],
                "total_classes": stats['total'],
                "attended_classes": stats['attended']
            })

        return jsonify({"status": "success", "subjects": formatted_subjects})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/enroll', methods=['POST'])
def student_enroll_api():
    """
    Enroll a student in a subject using a join code.
    Uses centralised db.py helpers — no direct supabase calls.
    """
    data = request.json or {}
    student_id = data.get('student_id')
    join_code = data.get('join_code', '').strip()

    if not student_id or not join_code:
        return jsonify({"status": "error", "message": "Student ID and Subject Code are required!"}), 400

    try:
        # FIX: Use centralised helper instead of direct supabase call
        subject = get_subject_by_code(join_code)
        if not subject:
            return jsonify({"status": "error", "message": "Subject code not found!"}), 404

        subject_id = int(subject['subject_id'])

        # FIX: Use centralised duplicate-check helper
        if check_enrollment_exists(int(student_id), subject_id):
            return jsonify({"status": "warning", "message": "You are already enrolled in this course."}), 200

        enroll_student_to_subject(int(student_id), subject_id)
        return jsonify({"status": "success", "message": f"Successfully enrolled in {subject['name']}!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/unenroll', methods=['POST'])
def student_unenroll_api():
    """Remove a student from a subject."""
    data = request.json or {}
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')

    if not student_id or not subject_id:
        return jsonify({"status": "error", "message": "Student ID and Subject ID are required!"}), 400

    try:
        unenroll_student_to_subject(int(student_id), int(subject_id))
        return jsonify({"status": "success", "message": "Successfully unenrolled from this course."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/student/attendance', methods=['GET'])
def student_attendance_api():
    """Return full attendance history for a student."""
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"status": "error", "message": "student_id is required!"}), 400
    try:
        logs = get_student_attendance(int(student_id))
        formatted_logs = []
        for log in logs:
            dt = datetime.fromisoformat(log['timestamp'])
            formatted_logs.append({
                "time": dt.strftime("%Y-%m-%d %I:%M %p"),
                "subject": log['subjects']['name'],
                "subject_code": log['subjects']['subject_code'],
                "status": "✅ Present" if log.get('is_present') else "❌ Absent"
            })
        return jsonify({"status": "success", "attendance": formatted_logs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  Server Entry Point
# ─────────────────────────────────────────────

if __name__ == '__main__':
    # Warm the SVM classifier on startup so the first face request is fast
    try:
        train_classifier()
        print("✅ Face classifier trained and ready.")
    except Exception as startup_err:
        print("⚠️  Warning: Startup classifier training failed:", startup_err)

    port = int(os.environ.get('PORT', 5002))
    app.run(debug=True, host='0.0.0.0', port=port)