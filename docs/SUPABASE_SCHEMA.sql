-- ============================================================================
-- AI ATTENDANCE SYSTEM — COMPLETE DATABASE RESET & RECREATION SCRIPT
-- ============================================================================
-- INSTRUCTIONS:
-- 1. Open your Supabase Project Dashboard: https://supabase.com/dashboard
-- 2. Go to "SQL Editor" on the left sidebar.
-- 3. Click "New Query", paste this entire script, and click "RUN".
-- ============================================================================

-- STEP 1: DROP EXISTING TABLES (in correct dependency order)
DROP TABLE IF EXISTS attendance_logs CASCADE;
DROP TABLE IF EXISTS subject_students CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;

-- STEP 2: CREATE FRESH TABLES

-- 1. TEACHERS TABLE
CREATE TABLE teachers (
    teacher_id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. STUDENTS TABLE (Stores 128-d Face & 256-d Voice Embeddings as JSONB arrays)
CREATE TABLE students (
    student_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    face_embedding JSONB,
    voice_embedding JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. SUBJECTS TABLE (Associated with a Teacher)
CREATE TABLE subjects (
    subject_id BIGSERIAL PRIMARY KEY,
    subject_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    section TEXT NOT NULL,
    teacher_id BIGINT NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ENROLLMENT JUNCTION TABLE (Student <-> Subject)
CREATE TABLE subject_students (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_student_subject UNIQUE(student_id, subject_id)
);

-- 5. ATTENDANCE LOGS TABLE (Stores confirmed attendance records)
CREATE TABLE attendance_logs (
    log_id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL,
    is_present BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- STEP 3: CREATE INDEXES FOR FAST QUERYING
CREATE INDEX IF NOT EXISTS idx_teachers_username ON teachers(username);
CREATE INDEX IF NOT EXISTS idx_subjects_code ON subjects(subject_code);
CREATE INDEX IF NOT EXISTS idx_subjects_teacher ON subjects(teacher_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_student ON subject_students(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_subject ON subject_students(subject_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_logs(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_subject ON attendance_logs(subject_id);

-- STEP 4: DISABLE ROW LEVEL SECURITY (RLS) FOR DIRECT ANON API ACCESS
ALTER TABLE teachers DISABLE ROW LEVEL SECURITY;
ALTER TABLE students DISABLE ROW LEVEL SECURITY;
ALTER TABLE subjects DISABLE ROW LEVEL SECURITY;
ALTER TABLE subject_students DISABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_logs DISABLE ROW LEVEL SECURITY;
