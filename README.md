# AI Class - AI Attendance System

Intelligent classroom attendance management system powered by Computer Vision (dlib face recognition + SVM classification) and Voice Biometrics (Resemblyzer + librosa). Includes dedicated portals for **Teachers** and **Students**, paired with Supabase for cloud persistence.

## Architecture

| Component | Technology | Entry Point |
|-----------|------------|-------------|
| **Main Web Portal (Flask + SPA)** | Flask, Vanilla CSS, JS | `python app.py` (Port 5002) |
| **Streamlit Interface** | Streamlit | `streamlit run streamlit_app.py` (Port 8501) |
| **Landing Page** | Flask, HTML5, CSS3 | `cd ai-attendance-project-landing && python app.py` (Port 5000) |
| **Database & Auth** | Supabase (PostgreSQL) | Managed via `src/database/db.py` |
| **Face Recognition** | dlib (128-d embeddings) + scikit-learn SVM | `src/pipelines/face_pipeline.py` |
| **Voice Recognition** | Resemblyzer (256-d embeddings) + librosa | `src/pipelines/voice_pipeline.py` |

## Core Features

- **Teacher Portal**:
  - Account registration and bcrypt password authentication.
  - Classroom subject creation and enrollment code / QR code generation.
  - Batch facial recognition attendance from classroom snapshots or webcam.
  - Audio-based roll call attendance with speaker recognition.
  - Review and confirmation workflow before persisting to database.
  - Session history and attendance statistics.

- **Student Portal**:
  - Face biometric login via camera.
  - Profile registration with 128-d face embedding and optional 256-d voice embedding.
  - Subject enrollment via 6-character code or QR code link (`?join-code=<code>`).
  - Attendance history and participation rates.

## Local Setup

### 1. Prerequisites
- Python 3.10 or 3.11
- C++ build tools (required if building `dlib` from source; `dlib-bin` wheel is included for Windows)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Fill in your Supabase credentials:
```env
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-or-anon-key
PORT=5002
LANDING_PAGE_URL=http://localhost:5000
```

### 3. Database Initialization
Run the SQL script `supabase_schema.sql` in your Supabase SQL Editor to initialize all tables, foreign keys, and indexes.

### 4. Running the Main Application

**Option A: Web Portal (Flask)**
```bash
python app.py
```
Access at `http://localhost:5002`.

**Option B: Streamlit Interface**
```bash
streamlit run streamlit_app.py
```
Access at `http://localhost:8501`.

### 5. Running the Landing Page
In a separate terminal:
```bash
cd ai-attendance-project-landing
python app.py
```
Access at `http://localhost:5000`.

## Production Deployment (Render)

This repository includes `render.yaml` for zero-configuration deployment on Render:
- Service Type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app`
- Required Environment Variables: `SUPABASE_URL`, `SUPABASE_KEY`, `LANDING_PAGE_URL`
