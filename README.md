# SnapClass — AI Attendance System

Smart attendance app with separate **Student** and **Teacher** portals. Students register with face (and optional voice) embeddings stored in Supabase — not raw photos. Teachers mark attendance by matching classroom photos or voice recordings against those embeddings.

## Architecture

| Layer | Tech |
|-------|------|
| Main app | Streamlit (`app.py`) |
| Landing page | Flask (`ai-attendance-project-landing/`) |
| Database | Supabase (students, teachers, subjects, attendance logs) |
| Face AI | dlib + scikit-learn SVM classifier |
| Voice AI | Resemblyzer + librosa |

### User flows

**Students**
1. Face login via camera on the student portal
2. Register profile (name + face embedding, optional voice embedding)
3. Enroll in subjects via code or QR link (`?join-code=CS101`)
4. View enrolled subjects and attendance stats

**Teachers**
1. Register / login with username & password
2. Create subjects and share enrollment codes
3. Take attendance via classroom photos (face match) or voice recording
4. Review and confirm attendance before saving to database

## Local setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` from the example:

```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Fill in your Supabase credentials, then run:

```bash
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub (root should contain `app.py` and `requirements.txt`).
2. Create a new app at [share.streamlit.io](https://share.streamlit.io) pointing to `app.py`.
3. Add secrets (same keys as `secrets.toml.example`):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. Streamlit Cloud reads `packages.txt` for system dependencies needed by dlib.

## Deploy landing page on Vercel

The marketing site lives in `ai-attendance-project-landing/`.

1. Import the repo on Vercel.
2. Set **Root Directory** to `ai-attendance-project-landing`.
3. Framework preset: Other (Flask via `vercel.json`).
4. Deploy — static assets and `templates/index.html` are served by `app.py`.

Update the Streamlit app URL in `ai-attendance-project-landing/templates/index.html` if your deployed app URL differs from `https://snapclass.streamlit.app/`.

## Supabase tables (expected)

- `teachers` — username, password (bcrypt hash), name
- `students` — name, face_embedding, voice_embedding
- `subjects` — subject_code, name, section, teacher_id
- `subject_students` — student_id, subject_id
- `attendance_logs` — student_id, subject_id, timestamp, is_present

## Project structure

```
app.py                          # Streamlit entry point
src/screens/                    # home, student, teacher screens
src/components/                 # dialogs, header, footer, cards
src/pipelines/                  # face & voice ML pipelines
src/database/                   # Supabase client & queries
ai-attendance-project-landing/  # Flask landing page for Vercel
```
