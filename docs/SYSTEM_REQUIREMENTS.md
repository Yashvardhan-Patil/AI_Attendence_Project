# ⚙️ System Requirements — AI Attendance Project

## 1. Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Dual-core 2 GHz | Quad-core 2.5+ GHz (dlib face inference is CPU-heavy) |
| RAM | 4 GB | 8 GB+ (SVM + dlib models loaded in-process) |
| Storage | 2 GB | 5 GB (model files, venv, audio libs) |
| Camera | Any webcam | HD 720p+ for better face detection accuracy |
| Microphone | Any | Noise-isolating mic for better voice matching |
| Internet | Required | Required (Supabase is cloud-hosted) |

---

## 2. Operating System

| OS | Supported | Notes |
|----|-----------|-------|
| Windows 10/11 | ✅ | Requires `WindowsSelectorEventLoopPolicy` (already set in `app.py`) |
| Linux (Ubuntu 20.04+) | ✅ | Native, best for production |
| macOS 12+ | ✅ | May need Homebrew for dlib/cmake |

---

## 3. Python Runtime

| Requirement | Version |
|-------------|---------|
| Python | **3.9 – 3.11** (dlib-bin is NOT compatible with 3.12+) |
| pip | 23.0+ |
| venv | Recommended |

> [!WARNING]
> `dlib-bin` requires Python ≤ 3.11. Do NOT use Python 3.12+.

---

## 4. Python Dependencies (`requirements.txt`)

### Web Framework
| Package | Purpose |
|---------|---------|
| `flask` | REST API server |
| `flask-cors` | Cross-origin request support for frontend |
| `gunicorn` | Production WSGI server |
| `python-dotenv` | Load `.env` file locally |

### Database
| Package | Purpose |
|---------|---------|
| `supabase` | Supabase Python client (PostgreSQL wrapper) |
| `bcrypt` | Password hashing for teacher accounts |

### AI / ML
| Package | Purpose |
|---------|---------|
| `dlib-bin` | Face detection + 128-d face embedding |
| `face-recognition-models` | Provides pretrained dlib model files |
| `scikit-learn` | SVM classifier for face identity |
| `resemblyzer` | Speaker voice embedding (256-d) |
| `librosa` | Audio loading, resampling, silence splitting |

### Utilities
| Package | Purpose |
|---------|---------|
| `numpy` | Numerical operations / array math |
| `pandas` | Attendance record aggregation / groupby |
| `pillow` | Image loading and RGB conversion |
| `segno` | QR code generation for subject join codes |
| `setuptools<70.0.0` | Needed to avoid dlib build breakage |

---

## 5. System / OS-Level Packages (`packages.txt`)

| Package | Purpose |
|---------|---------|
| `libgl1` | OpenGL dependency for dlib on Linux servers |

> [!NOTE]
> On Windows these system deps are handled natively. `libgl1` is required only on Render/Linux.

---

## 6. External Services

| Service | Usage | Required |
|---------|-------|----------|
| **Supabase** | Cloud PostgreSQL database + REST API | ✅ Yes |
| **Google Fonts** | UI fonts (Climate Crisis, Outfit) | ✅ (loads at runtime via CDN) |
| **ibb.co (imgbb)** | Mascot image hosting | ✅ (loads at runtime) |

### Supabase Configuration
Set the following environment variables:
```
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-anon-key>
```

---

## 7. Local Development Setup

```bash
# 1. Clone repo
git clone <repo-url>
cd ai-attendance-project-app

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
# Create .env file with SUPABASE_URL and SUPABASE_KEY

# 5. Run Flask server
python app.py
```
Server starts at: `http://localhost:5002`

---

## 8. Production Deployment Requirements

| Component | Specification |
|-----------|---------------|
| Platform | Render.com (Web Service) |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Port | `5002` (via `PORT` env var) |
| Environment | `SUPABASE_URL`, `SUPABASE_KEY` set in Render dashboard |
