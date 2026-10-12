# 🔍 End-to-End Connectivity & Function Audit — AI Attendance Project

> This document traces every function from frontend → API → pipeline → DB and reports whether data is correctly persisted or kept in cache/memory.

---

## 🟢 1. Database-Connected Functions (Data Reaches Supabase)

### `create_teacher(username, password, name)`
- **Route**: `POST /api/teacher/register`
- **DB Write**: `INSERT INTO teachers` ✅
- **Data stored**: `username` (lowercase), `bcrypt_hash`, `name`
- **Status**: ✅ **FULLY CONNECTED**

### `teacher_login(username, password)`
- **Route**: `POST /api/teacher/login`
- **DB Read**: `SELECT FROM teachers WHERE username = ?` ✅
- **bcrypt verification**: In-memory verification against stored hash; password hash is stripped before returning JSON
- **Status**: ✅ **FULLY CONNECTED**

### `create_student(name, face_embedding, voice_embedding)`
- **Route**: `POST /api/student/register`
- **DB Write**: `INSERT INTO students` ✅
- **Data stored**: `name`, `face_embedding` (128-d vector), `voice_embedding` (256-d vector, optional)
- **Status**: ✅ **FULLY CONNECTED**

### `get_student_by_id(student_id)`
- **Route**: `POST /api/student/login-face`
- **DB Read**: `SELECT student_id, name FROM students WHERE student_id = ?` ✅
- **Status**: ✅ **FULLY CONNECTED** (Optimized single-row fetch)

### `create_subject(subject_code, name, section, teacher_id)`
- **Route**: `POST /api/teacher/create-subject`
- **DB Write**: `INSERT INTO subjects` ✅
- **Data stored**: `subject_code`, `name`, `section`, `teacher_id`
- **Status**: ✅ **FULLY CONNECTED**

### `get_subject_by_code(subject_code)`
- **Routes**: `POST /api/student/enroll`, Streamlit enrollment dialogs
- **DB Read**: `SELECT subject_id, name, subject_code FROM subjects WHERE subject_code = ?` ✅
- **Status**: ✅ **FULLY CONNECTED**

### `check_enrollment_exists(student_id, subject_id)`
- **Routes**: `POST /api/student/enroll`, Streamlit dialogs
- **DB Read**: `SELECT student_id FROM subject_students WHERE subject_id = ? AND student_id = ?` ✅
- **Status**: ✅ **FULLY CONNECTED**

### `enroll_student_to_subject(student_id, subject_id)`
- **Routes**: `POST /api/student/enroll`, QR scan flow, Streamlit dialogs
- **DB Write**: `INSERT INTO subject_students` ✅
- **Status**: ✅ **FULLY CONNECTED**

### `unenroll_student_to_subject(student_id, subject_id)`
- **Route**: `POST /api/student/unenroll`
- **DB Write**: `DELETE FROM subject_students WHERE student_id = ? AND subject_id = ?` ✅
- **Status**: ✅ **FULLY CONNECTED**

### `get_enrolled_students_with_embeddings(subject_id)`
- **Routes**: `POST /api/teacher/take-attendance/face`, `POST /api/teacher/take-attendance/voice`, Streamlit attendance
- **DB Read**: `SELECT *, students(*) FROM subject_students WHERE subject_id = ?` ✅
- **Status**: ✅ **FULLY CONNECTED**

### `create_attendance(logs)`
- **Route**: `POST /api/teacher/confirm-attendance`
- **DB Write**: `INSERT INTO attendance_logs` (bulk insert) ✅
- **Status**: ✅ **FULLY CONNECTED** (Persists after teacher confirmation)

---

## ⚡ 2. In-Memory AI Cache Pipeline (By Design)

### `predict_attendance(image_np)` in Face Analysis
- **Routes**: `POST /api/teacher/take-attendance/face`, `POST /api/student/login-face`
- **DB Write**: ❌ NONE — Returns detection results as a preview for verification
- **Cache used**: `_TRAINED_MODEL` (Linear SVM classifier), `_DLIB_MODELS` (Detector, Shape Predictor, ResNet Recognizer)
- **Status**: ⚡ **PREVIEW IN MEMORY** — Prevents accidental automatic commits before review.

### `process_bulk_audio(audio_bytes, candidates_dict)` in Voice Analysis
- **Route**: `POST /api/teacher/take-attendance/voice`
- **DB Write**: ❌ NONE — Returns speaker match confidence scores
- **Cache used**: `_VOICE_ENCODER` (Resemblyzer VoiceEncoder model)
- **Status**: ⚡ **PREVIEW IN MEMORY** — Follows same two-step confirmation pattern.

---

## 🛠️ 3. Audit Findings & Resolution Status

| # | Severity | Finding / Issue | Resolution Applied | Status |
|---|----------|-----------------|---------------------|--------|
| 1 | 🔴 High | **Attendance Data Loss Risk**: If user refreshed/closed browser during attendance review, pending logs in memory were lost without warning. | Added `window.beforeunload` warning handler in `static/js/app.js` to block accidental page leave when unconfirmed logs exist in state. | ✅ **RESOLVED** |
| 2 | 🟡 Medium | **Direct Supabase Queries**: Scattered calls in `app.py`, `dialog_enroll.py`, `dialog_auto_enroll.py`, `dialog_voice_attendance.py`, `teacher_screen.py` bypassed `db.py`. | Created centralized helper functions in `src/database/db.py` (`get_student_by_id`, `get_subject_by_code`, `check_enrollment_exists`, `get_enrolled_students_with_embeddings`) and replaced all external calls. | ✅ **RESOLVED** |
| 3 | 🟡 Medium | **Misleading `train_classifier()`**: Only set `_TRAINED_MODEL = None` rather than immediately ensuring the classifier is re-fitted. | Updated `train_classifier()` to reset cache and eagerly trigger `get_trained_model()` for immediate inference readiness. | ✅ **RESOLVED** |
| 4 | 🟢 Low | **Full Table Scan on Student Login**: `get_all_students()` loaded all student rows on each login. | Replaced with `get_student_by_id(student_id)` targeted lookup. | ✅ **RESOLVED** |
| 5 | 🟢 Low | **Dict Key Typo**: `get_teacher_subjects()` tried popping `subject_student` (singular) instead of `subject_students` (plural). | Fixed key name in `src/database/db.py`. | ✅ **RESOLVED** |

---

## 📊 4. Full Connectivity Matrix

| Function | Layer | DB Read | DB Write | Cache Used | Status |
|---|---|---|---|---|---|
| `create_teacher` | Auth | ❌ | ✅ `teachers` | ❌ | ✅ Working |
| `teacher_login` | Auth | ✅ `teachers` | ❌ | ❌ | ✅ Working |
| `create_subject` | Subject | ❌ | ✅ `subjects` | ❌ | ✅ Working |
| `get_teacher_subjects` | Subject | ✅ `subjects` + counts | ❌ | ❌ | ✅ Working |
| `get_subject_by_code` | Subject | ✅ `subjects` | ❌ | ❌ | ✅ Working |
| `check_enrollment_exists` | Enrollment | ✅ `subject_students` | ❌ | ❌ | ✅ Working |
| `enroll_student_to_subject` | Enrollment | ❌ | ✅ `subject_students` | ❌ | ✅ Working |
| `unenroll_student_to_subject` | Enrollment | ❌ | ✅ `subject_students` | ❌ | ✅ Working |
| `get_student_subjects` | Student | ✅ `subject_students`+ | ❌ | ❌ | ✅ Working |
| `create_student` | Student | ❌ | ✅ `students` | ❌ | ✅ Working |
| `get_student_by_id` | Student | ✅ `students` | ❌ | ❌ | ✅ Working |
| `predict_attendance` | AI Pipeline | ✅ `students` (via SVM) | ❌ | ⚡ `_TRAINED_MODEL` | ✅ Working (Preview) |
| `process_bulk_audio` | AI Pipeline | ✅ `students` (voice) | ❌ | ⚡ `_VOICE_ENCODER` | ✅ Working (Preview) |
| `create_attendance` | Attendance | ❌ | ✅ `attendance_logs` | ❌ | ✅ Working (Persisted) |
| `get_attendance_for_teacher` | Reporting | ✅ `attendance_logs`+ | ❌ | ❌ | ✅ Working |
| `get_student_attendance` | Reporting | ✅ `attendance_logs`+ | ❌ | ❌ | ✅ Working |
