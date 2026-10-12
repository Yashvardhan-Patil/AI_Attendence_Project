# 🎓 AI Attendance Project — Project Summary

## Overview

**AI Attendance** is a full-stack, AI-powered classroom attendance system that uses **Face Recognition** and **Voice Recognition** to automatically detect and record student presence. The project exposes a REST API (Flask) with a frontend SPA (HTML/CSS/JS), and also includes a Streamlit-based alternate UI layer.

---

## 🗂️ Project Structure

```
ai-attendance-project-app/
├── app.py                        # Main Flask REST API (PRIMARY ENTRY POINT)
├── requirements.txt              # Python dependencies
├── render.yaml                   # Render.com deployment config
├── .env                          # Environment variables (Supabase credentials)
│
├── templates/
│   └── index.html                # Frontend SPA (HTML/CSS/JS)
│
├── static/                       # CSS + JS assets for frontend
│
├── src/
│   ├── database/
│   │   ├── config.py             # Supabase client initialization
│   │   └── db.py                 # All DB query functions
│   │
│   ├── pipelines/
│   │   ├── face_pipeline.py      # Face recognition (dlib + SVM)
│   │   └── voice_pipeline.py     # Voice recognition (Resemblyzer)
│   │
│   ├── screens/                  # Streamlit UI screens (alternate UI)
│   ├── components/               # Streamlit dialog components
│   └── ui/
│       └── base_layout.py        # Streamlit global styles
│
└── ai-attendance-project-landing/ # Static landing page
```

---

## 👥 User Roles

| Role    | Authentication     | Capabilities                                               |
|---------|--------------------|-------------------------------------------------------------|
| Teacher | Username + Password (bcrypt) | Create subjects, take attendance (face/voice), view records |
| Student | Face Recognition   | Register via face+voice, enroll in subjects, view own stats |

---

## 🤖 AI Technologies Used

| Technology        | Library        | Purpose                                           |
|-------------------|----------------|----------------------------------------------------|
| Face Detection    | dlib           | Detect faces in classroom photos                  |
| Face Embedding    | dlib ResNet    | Extract 128-d face embedding per student          |
| Face Classifier   | SVM (sklearn)  | Classify which student a face belongs to          |
| Voice Embedding   | Resemblyzer    | Extract speaker embedding from audio clip         |
| Voice Matching    | Cosine Similarity | Match voice segment to a known student embedding |
| Audio Processing  | librosa        | Load, resample, and split audio into segments     |

---

## 🗄️ Database (Supabase / PostgreSQL)

| Table              | Key Columns                                                      |
|--------------------|------------------------------------------------------------------|
| `teachers`         | `teacher_id`, `username`, `password` (bcrypt), `name`           |
| `students`         | `student_id`, `name`, `face_embedding` (array), `voice_embedding` (array) |
| `subjects`         | `subject_id`, `subject_code`, `name`, `section`, `teacher_id`   |
| `subject_students` | `student_id`, `subject_id` (enrollment junction)                 |
| `attendance_logs`  | `log_id`, `student_id`, `subject_id`, `timestamp`, `is_present` |

---

## 🌐 API Surface (Flask REST)

### Teacher Endpoints
| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/api/teacher/register` | Register teacher |
| POST | `/api/teacher/login` | Authenticate teacher |
| GET  | `/api/teacher/subjects` | Get subjects |
| POST | `/api/teacher/create-subject` | Create subject |
| POST | `/api/teacher/take-attendance/face` | Run face recognition |
| POST | `/api/teacher/take-attendance/voice` | Run voice recognition |
| POST | `/api/teacher/confirm-attendance` | Save logs to DB |
| GET  | `/api/teacher/records` | View attendance records |

### Student Endpoints
| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/api/student/login-face` | Login via face |
| POST | `/api/student/register` | Register student |
| GET  | `/api/student/subjects` | Enrolled subjects + stats |
| POST | `/api/student/enroll` | Enroll via join code |
| POST | `/api/student/unenroll` | Unenroll from subject |
| GET  | `/api/student/attendance` | View attendance history |

---

## 🚀 Deployment

- **Platform**: Render.com  
- **Server**: Gunicorn (WSGI)  
- **Port**: 5002  
- **Env Vars**: `SUPABASE_URL`, `SUPABASE_KEY`
