# 🔄 Workflow & End-to-End Data Flow — AI Attendance Project

> **Legend**  
> 🔵 = Data lives in-memory / cache / session only  
> 🟢 = Data written to Supabase DB (permanent)  
> 🔴 = Data discarded after response

---

## 1. Teacher Registration Flow

```
User fills form
    → POST /api/teacher/register
        → check_teacher_exists(username)          [SELECT teachers] 🟢 (read)
        → create_teacher(username, pwd, name)
            → bcrypt.hashpw(password)             🔵 temp hash in RAM
            → supabase INSERT teachers            🟢 SAVED TO DB
        → return {status: success}
```

**What goes to DB**: `username`, `name`, `bcrypt_hashed_password` → `teachers` table  
**What stays in cache**: raw password (discarded immediately after hashing)

---

## 2. Teacher Login Flow

```
User submits credentials
    → POST /api/teacher/login
        → teacher_login(username, password)
            → SELECT teachers WHERE username=...  🟢 (read)
            → bcrypt.checkpw(input, hash)         🔵 RAM verify
            → return teacher dict (password field removed)
        → Frontend stores teacher_id in localStorage  🔵 Browser storage only
```

**What goes to DB**: Nothing written  
**What stays in cache**: Teacher object in browser `localStorage` / Streamlit `session_state`

---

## 3. Student Registration Flow

```
Student captures photo + optional audio
    → POST /api/student/register (multipart form)
        → get_face_embeddings(image_np)
            → load_dlib_models()              🔵 _DLIB_MODELS global (RAM)
            → dlib detector + ResNet embed    🔵 128-d numpy array (RAM)
        → get_voice_embedding(audio_bytes)    [optional]
            → load_voice_encoder()            🔵 _VOICE_ENCODER global (RAM)
            → Resemblyzer embed_utterance     🔵 256-d array (RAM)
        → create_student(name, face_emb, voice_emb)
            → supabase INSERT students        🟢 SAVED TO DB
        → train_classifier()
            → _TRAINED_MODEL = None           🔵 clears RAM cache (forces retrain)
        → return student {student_id, name}
```

**What goes to DB**: `name`, `face_embedding[]`, `voice_embedding[]` → `students` table  
**What stays in cache**: Intermediate numpy arrays (discarded), model globals persist in RAM

---

## 4. Student Face Login Flow

```
Student opens camera → captures selfie
    → POST /api/student/login-face
        → predict_attendance(image_np)
            → get_face_embeddings(image_np)   🔵 128-d embed (RAM)
            → get_trained_model()
                → if _TRAINED_MODEL is None:
                    → get_all_students()      🟢 (read all face_embeddings)
                    → fit SVC               🔵 stored in _TRAINED_MODEL (RAM)
            → SVM.predict(embedding)          🔵 prediction in RAM
            → distance threshold check        🔵
        → if recognized:
            → get_all_students()              🟢 (read)
            → return {student_id, name}
        → if not recognized:
            → return {status: register}
```

**What goes to DB**: Nothing written  
**What stays in cache/session**: Student object in browser `localStorage` / Streamlit `session_state`

---

## 5. Face Attendance Flow (Teacher) — TWO-STEP PROCESS

### Step 1 — AI Analysis (NO DB write yet)
```
Teacher selects subject + uploads photos
    → POST /api/teacher/take-attendance/face
        → for each image:
            → predict_attendance(img_np)      🔵 detection results in RAM
        → SELECT subject_students + students  🟢 (read enrolled list)
        → build results[] + attendance_to_log[] 🔵 in RAM
        → return {results, logs}              🔵 sent to frontend, NOT saved
```

### Step 2 — Teacher Reviews & Confirms
```
Teacher sees preview table → clicks "Confirm & Save"
    → POST /api/teacher/confirm-attendance
        → create_attendance(logs)
            → supabase INSERT attendance_logs (bulk) 🟢 SAVED TO DB
        → return {status: success}
```

> [!IMPORTANT]
> Attendance is **NOT saved to DB** during face/voice analysis. It is only a **preview in memory**. The teacher MUST click "Confirm & Save" for data to reach the database.

**What goes to DB**: `student_id`, `subject_id`, `timestamp`, `is_present` → `attendance_logs` (only after confirmation)  
**What stays in cache**: Recognition results (`attendance_to_log`) in frontend memory / Streamlit `session_state` until confirmed or discarded

---

## 6. Voice Attendance Flow (Teacher) — TWO-STEP PROCESS

### Step 1 — Audio Analysis
```
Teacher records classroom audio
    → POST /api/teacher/take-attendance/voice
        → SELECT subject_students + voice_embedding  🟢 (read)
        → build candidates_dict {student_id: embedding} 🔵 RAM
        → process_bulk_audio(audio_bytes, candidates)
            → librosa.load + split segments           🔵 RAM
            → for each segment:
                → encoder.embed_utterance(wav)        🔵 256-d embed (RAM)
                → identify_speaker(embed, candidates) 🔵 cosine sim (RAM)
        → build results[] + attendance_to_log[]       🔵 RAM
        → return {results, logs}                      🔵 preview only
```

### Step 2 — Confirm
Same as face attendance Step 2 above.

---

## 7. Subject Creation Flow

```
Teacher fills subject form
    → POST /api/teacher/create-subject
        → create_subject(code, name, section, teacher_id)
            → supabase INSERT subjects    🟢 SAVED TO DB
        → return {status: success, data}
```

**What goes to DB**: `subject_code`, `name`, `section`, `teacher_id` → `subjects` table

---

## 8. Student Enrollment Flow

```
Student enters join code
    → POST /api/student/enroll
        → SELECT subjects WHERE subject_code=...   🟢 (read)
        → SELECT subject_students (duplicate check) 🟢 (read)
        → enroll_student_to_subject(student_id, subject_id)
            → supabase INSERT subject_students      🟢 SAVED TO DB
        → return {status: success}
```

**What goes to DB**: `student_id`, `subject_id` → `subject_students` table

---

## 9. QR Code Enrollment Flow

```
Teacher shares QR code (encodes subject_code in URL)
    → Student scans QR → opens app URL with ?join-code=XXX
        → auto_enroll_dialog triggers
            → SELECT subjects WHERE subject_code=...   🟢 (read)
            → duplicate check                          🟢 (read)
            → enroll_student_to_subject(...)           🟢 SAVED TO DB
```

---

## 10. Attendance Records View

```
Teacher opens Records tab
    → GET /api/teacher/records?teacher_id=X
        → get_attendance_for_teacher(teacher_id)
            → SELECT attendance_logs INNER JOIN subjects  🟢 (read)
        → pandas groupby (timestamp + subject)            🔵 RAM aggregation
        → return summarized JSON                          🔴 not stored
```

---

## End-to-End DB Write Summary

| Action | DB Table Written | Triggered By |
|--------|-----------------|--------------|
| Teacher registers | `teachers` | `POST /api/teacher/register` |
| Student registers | `students` | `POST /api/student/register` |
| Subject created | `subjects` | `POST /api/teacher/create-subject` |
| Student enrolls | `subject_students` | `POST /api/student/enroll` |
| Student unenrolls | `subject_students` (DELETE) | `POST /api/student/unenroll` |
| Attendance confirmed | `attendance_logs` | `POST /api/teacher/confirm-attendance` |

> [!CAUTION]
> Face/voice attendance runs (`/take-attendance/face` and `/take-attendance/voice`) do **NOT** write to the database. They return a preview. The separate **confirm-attendance** call is the only one that writes attendance records.

---

## In-Memory Cache Summary

| Cache Variable | Location | Contents | Cleared When |
|---------------|----------|----------|-------------|
| `_DLIB_MODELS` | `face_pipeline.py` global | dlib detector + shape predictor + face recognizer | Server restart |
| `_TRAINED_MODEL` | `face_pipeline.py` global | SVM + training embeddings array | `train_classifier()` called (on new student register) |
| `_VOICE_ENCODER` | `voice_pipeline.py` global | Resemblyzer VoiceEncoder | Server restart |
| `st.session_state` | Streamlit session | Login state, attendance images, voice results | Page refresh / logout |
| `localStorage` (browser) | Browser | teacher_id, student_id, name | User logout or browser clear |
