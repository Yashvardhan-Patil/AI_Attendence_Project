from src.database.config import supabase
import bcrypt


# ─────────────────────────────────────────────
#  Password Utilities
# ─────────────────────────────────────────────

def hash_pass(pwd):
    """Hash a plain-text password with bcrypt."""
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def check_pass(pwd, hashed):
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


# ─────────────────────────────────────────────
#  Teacher DB Functions
# ─────────────────────────────────────────────

def check_teacher_exists(username):
    """Return True if a teacher with this username already exists."""
    response = supabase.table("teachers").select("username").eq("username", username.strip().lower()).execute()
    return len(response.data) > 0


def create_teacher(username, password, name):
    """Insert a new teacher record. Password is bcrypt-hashed before storage."""
    data = {"username": username.strip().lower(), "password": hash_pass(password), "name": name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    """Authenticate a teacher. Returns teacher dict (with password field) or None."""
    response = supabase.table("teachers").select("*").eq("username", username.strip().lower()).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


# ─────────────────────────────────────────────
#  Student DB Functions
# ─────────────────────────────────────────────

def get_all_students():
    """Fetch all student records (used for building SVM training data)."""
    response = supabase.table('students').select("*").execute()
    return response.data


def get_student_by_id(student_id):
    """
    Fetch a single student by primary key.
    More efficient than get_all_students() for login lookups.
    Returns the student dict or None.
    """
    response = supabase.table('students').select("student_id, name").eq("student_id", student_id).execute()
    if response.data:
        return response.data[0]
    return None


def create_student(new_name, face_embedding=None, voice_embedding=None):
    """Insert a new student with optional face and voice embeddings."""
    data = {'name': new_name, 'face_embedding': face_embedding, "voice_embedding": voice_embedding}
    response = supabase.table('students').insert(data).execute()
    return response.data


# ─────────────────────────────────────────────
#  Subject DB Functions
# ─────────────────────────────────────────────

def create_subject(subject_code, name, section, teacher_id):
    """Insert a new subject record."""
    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data


def get_subject_by_code(subject_code):
    """
    Find a subject by its join code.
    Returns the subject dict or None if not found.
    """
    response = supabase.table('subjects').select('subject_id, name, subject_code').eq('subject_code', subject_code.strip()).execute()
    if response.data:
        return response.data[0]
    return None


def get_teacher_subjects(teacher_id):
    """
    Fetch all subjects for a teacher with computed stats:
      - total_students: count of enrolled students
      - total_classes: count of unique attendance sessions
    """
    response = supabase.table('subjects').select(
        "*, subject_students(count), attendance_logs(timestamp)"
    ).eq("teacher_id", teacher_id).execute()
    subjects = response.data

    for sub in subjects:
        # Fix: the key returned by supabase is 'subject_students' (plural)
        sub['total_students'] = (
            sub.get("subject_students", [{}])[0].get('count', 0)
            if sub.get('subject_students') else 0
        )
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
        sub['total_classes'] = unique_sessions

        # Remove raw nested data before returning
        sub.pop('subject_students', None)   # Fixed: was incorrectly popping 'subject_student' (missing 's')
        sub.pop('attendance_logs', None)

    return subjects


# ─────────────────────────────────────────────
#  Enrollment DB Functions
# ─────────────────────────────────────────────

def check_enrollment_exists(student_id, subject_id):
    """
    Return True if the student is already enrolled in the subject.
    Centralised duplicate-enrollment guard used by all enroll entry points.
    """
    response = supabase.table('subject_students').select('student_id').eq('subject_id', int(subject_id)).eq('student_id', int(student_id)).execute()
    return len(response.data) > 0


def enroll_student_to_subject(student_id, subject_id):
    """Insert a student–subject enrollment record."""
    data = {'student_id': student_id, "subject_id": subject_id}
    response = supabase.table('subject_students').insert(data).execute()
    return response.data


def unenroll_student_to_subject(student_id, subject_id):
    """Delete a student–subject enrollment record."""
    response = supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data


def get_student_subjects(student_id):
    """Fetch all subjects a student is enrolled in (with full subject details)."""
    response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


# ─────────────────────────────────────────────
#  Enrolled Students with Embeddings (for Attendance)
# ─────────────────────────────────────────────

def get_enrolled_students_with_embeddings(subject_id):
    """
    Fetch all enrolled students for a subject, including their
    face_embedding and voice_embedding fields.
    Used by both face and voice attendance pipelines.
    Returns a list of: { students: { student_id, name, face_embedding, voice_embedding } }
    """
    response = supabase.table('subject_students').select("*, students(*)").eq('subject_id', int(subject_id)).execute()
    return response.data


# ─────────────────────────────────────────────
#  Attendance DB Functions
# ─────────────────────────────────────────────

def get_student_attendance(student_id):
    """Fetch all attendance logs for a student, joined with subject info."""
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def create_attendance(logs):
    """
    Bulk-insert attendance log records.
    Each log dict must have: student_id, subject_id, timestamp, is_present.
    This is the ONLY function that writes attendance to the database.
    """
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data


def get_attendance_for_teacher(teacher_id):
    """Fetch all attendance logs for subjects belonging to a specific teacher."""
    response = supabase.table('attendance_logs').select("*, subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
    return response.data
