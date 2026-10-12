// Application State Management
const state = {
    role: null, // 'student' or 'teacher'
    student: null, // Logged in student data
    teacher: null, // Logged in teacher data
    activeWebcamStream: null,
    capturedImageBlob: null,
    voiceRecordBlob: null,
    classroomAudioBlob: null,
    classroomPhotos: [], // Array of File objects
    activeVoiceRecording: false,
    activeClassroomRecording: false,
    activeTeacherTab: 'take_attendance',
    pendingEnrollCode: null, // From join-code query param
    currentReportLogs: null // Stored report data to save
};

// Web Audio API Recording variables
let audioContext, scriptProcessor, mediaStreamSource, activeAudioStream;
let audioSamples = [];

// API Base URL
const API_URL = '';

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    // Check for query parameters (?join-code=CS101)
    const urlParams = new URLSearchParams(window.location.search);
    const joinCode = urlParams.get('join-code');
    if (joinCode) {
        state.pendingEnrollCode = joinCode;
        showToast(`Join code detected: ${joinCode}`, 'info');
    }

    // Auto-login from sessionStorage
    const savedStudent = sessionStorage.getItem('student_user');
    const savedTeacher = sessionStorage.getItem('teacher_user');
    
    if (savedStudent) {
        state.role = 'student';
        state.student = JSON.parse(savedStudent);
        showScreen('student-portal');
        showStudentDashboard();
    } else if (savedTeacher) {
        state.role = 'teacher';
        state.teacher = JSON.parse(savedTeacher);
        showScreen('teacher-portal');
        showTeacherDashboard();
    } else {
        showScreen('role-selection');
    }

    // Warn if unconfirmed attendance sheet exists
    window.addEventListener('beforeunload', (e) => {
        if (state.currentReportLogs && state.currentReportLogs.length > 0) {
            e.preventDefault();
            e.returnValue = 'You have unconfirmed attendance logs that will be lost. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});

// ----------------- Routing / Navigation -----------------
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function selectRole(role) {
    state.role = role;
    if (role === 'student') {
        showScreen('student-portal');
        if (state.student) {
            showStudentDashboard();
        } else {
            showStudentLogin();
        }
    } else {
        showScreen('teacher-portal');
        if (state.teacher) {
            showTeacherDashboard();
        } else {
            showTeacherLogin();
        }
    }
}

function goHome() {
    stopWebcam();
    state.role = null;
    showScreen('role-selection');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check_circle';
    if (type === 'error') icon = 'error';
    
    toast.innerHTML = `
        <span class="material-symbols-outlined">${icon}</span>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    // trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // remove toast
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function showLoader(text = 'Processing...') {
    document.getElementById('loading-text').innerText = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoader() {
    document.getElementById('loading-overlay').classList.remove('active');
    document.getElementById('loading-overlay').classList.add('hidden');
}

// ----------------- Webcam FaceID Biometrics -----------------
async function initWebcam() {
    const video = document.getElementById('webcam-feed');
    const startBtn = document.getElementById('btn-start-camera');
    const captureBtn = document.getElementById('btn-capture-face');
    const status = document.getElementById('webcam-status');

    try {
        status.innerText = "Accessing camera...";
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' },
            audio: false
        });
        video.srcObject = stream;
        state.activeWebcamStream = stream;
        
        startBtn.classList.add('hidden');
        captureBtn.classList.remove('hidden');
        status.innerText = "Position your face in the box";
        document.querySelector('.scan-frame').classList.add('scanning');
    } catch (err) {
        showToast("Camera access failed! Allow camera permissions.", "error");
        status.innerText = "Camera access denied.";
    }
}

function stopWebcam() {
    if (state.activeWebcamStream) {
        state.activeWebcamStream.getTracks().forEach(track => track.stop());
        state.activeWebcamStream = null;
    }
    const video = document.getElementById('webcam-feed');
    if (video) video.srcObject = null;
    
    const startBtn = document.getElementById('btn-start-camera');
    const captureBtn = document.getElementById('btn-capture-face');
    if (startBtn && captureBtn) {
        startBtn.classList.remove('hidden');
        captureBtn.classList.add('hidden');
    }
    const frame = document.querySelector('.scan-frame');
    if (frame) frame.classList.remove('scanning');
}

async function captureFaceLogin() {
    const video = document.getElementById('webcam-feed');
    const canvas = document.getElementById('capture-canvas');
    const status = document.getElementById('webcam-status');
    
    if (!state.activeWebcamStream) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw mirrored video to canvas
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.setTransform(1, 0, 0, 1, 0, 0); // reset
    
    canvas.toBlob(async (blob) => {
        state.capturedImageBlob = blob;
        status.innerText = "Analyzing FaceID features...";
        showLoader("Running Face Analysis...");
        
        const formData = new FormData();
        formData.append('image', blob, 'face_capture.jpg');
        
        try {
            const res = await fetch(`${API_URL}/api/student/login-face`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            hideLoader();
            
            if (data.status === 'success') {
                stopWebcam();
                state.student = data.student;
                sessionStorage.setItem('student_user', JSON.stringify(data.student));
                showToast(data.message, 'success');
                showStudentDashboard();
            } else if (data.status === 'register') {
                status.innerText = "Face not recognized. Register below.";
                showToast(data.message, 'info');
                showStudentRegisterForm();
            } else {
                status.innerText = data.message || "Detection failed.";
                showToast(data.message || "Authentication failed.", 'error');
            }
        } catch (err) {
            hideLoader();
            status.innerText = "Server connection lost.";
            showToast("Server analysis request failed.", "error");
        }
    }, 'image/jpeg', 0.9);
}

// ----------------- WAV Audio Encoder -----------------
function bufferToWav(buffer) {
    let numOfChan = buffer.numberOfChannels,
        length = buffer.length * numOfChan * 2 + 44,
        bufferArr = new ArrayBuffer(length),
        view = new DataView(bufferArr),
        channels = [], i, sample,
        offset = 0,
        pos = 0;

    // write WAVE header
    setUint32(0x46464952);                         // "RIFF"
    setUint32(length - 8);                         // file length - 8
    setUint32(0x45564157);                         // "WAVE"

    setUint32(0x20746d66);                         // "fmt " chunk
    setUint32(16);                                 // chunk length
    setUint16(1);                                  // sample format (raw PCM)
    setUint16(numOfChan);                          // channel count
    setUint32(buffer.sampleRate);                  // sample rate
    setUint32(buffer.sampleRate * 2 * numOfChan);  // byte rate
    setUint16(numOfChan * 2);                      // block align
    setUint16(16);                                 // bits per sample

    setUint32(0x61746164);                         // "data" chunk
    setUint32(length - pos - 4);                   // chunk length

    // write interleaved data
    for (i = 0; i < buffer.numberOfChannels; i++)
        channels.push(buffer.getChannelData(i));

    while (pos < length) {
        for (i = 0; i < numOfChan; i++) {
            sample = Math.max(-1, Math.min(1, channels[i][offset]));
            sample = (sample < 0 ? sample * 0x8000 : sample * 0x7FFF);
            view.setInt16(pos, sample, true);
            pos += 2;
        }
        offset++;
    }

    return new Blob([view], { type: 'audio/wav' });

    function setUint16(data) {
        view.setUint16(pos, data, true);
        pos += 2;
    }

    function setUint32(data) {
        view.setUint32(pos, data, true);
        pos += 4;
    }
}

// ----------------- Student Portal Section -----------------
function showStudentLogin() {
    document.getElementById('student-profile').classList.add('hidden');
    document.getElementById('student-login-view').classList.add('active');
    document.getElementById('student-dashboard-view').classList.remove('active');
    document.getElementById('student-register-container').classList.add('hidden');
    
    // reset variables
    state.capturedImageBlob = null;
    state.voiceRecordBlob = null;
    
    // Trigger Webcam immediately for better flow
    initWebcam();
}

function showStudentRegisterForm() {
    document.getElementById('student-register-container').classList.remove('hidden');
    document.getElementById('reg-student-name').focus();
    
    // Stop webcam feed since we have the photo saved
    stopWebcam();
    const frame = document.querySelector('.scan-frame');
    frame.classList.remove('scanning');
}

async function toggleVoiceRecording() {
    const btn = document.getElementById('btn-record-voice');
    const text = btn.querySelector('.record-text');
    const indicator = document.querySelector('.recording-indicator');
    const audioPreview = document.getElementById('voice-preview');

    if (!state.activeVoiceRecording) {
        try {
            audioSamples = [];
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            mediaStreamSource = audioContext.createMediaStreamSource(stream);
            scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

            scriptProcessor.onaudioprocess = function (e) {
                let input = e.inputBuffer.getChannelData(0);
                audioSamples.push(new Float32Array(input));
            };

            mediaStreamSource.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);
            activeAudioStream = stream;

            state.activeVoiceRecording = true;
            btn.classList.add('recording');
            text.innerText = "Stop Recording";
            indicator.classList.remove('hidden');
            audioPreview.classList.add('hidden');
        } catch (err) {
            showToast("Failed to record audio. Check microphone settings.", "error");
        }
    } else {
        scriptProcessor.disconnect();
        mediaStreamSource.disconnect();
        activeAudioStream.getTracks().forEach(track => track.stop());

        // merge buffers
        let totalLength = audioSamples.reduce((acc, buf) => acc + buf.length, 0);
        let merged = new Float32Array(totalLength);
        let offset = 0;
        for (let buf of audioSamples) {
            merged.set(buf, offset);
            offset += buf.length;
        }

        let audioBuffer = audioContext.createBuffer(1, totalLength, audioContext.sampleRate);
        audioBuffer.copyToChannel(merged, 0);

        state.voiceRecordBlob = bufferToWav(audioBuffer);
        
        // Setup preview
        const audioURL = URL.createObjectURL(state.voiceRecordBlob);
        audioPreview.src = audioURL;
        audioPreview.classList.remove('hidden');

        state.activeVoiceRecording = false;
        btn.classList.remove('recording');
        text.innerText = "Record Voice";
        indicator.classList.add('hidden');
    }
}

async function submitStudentRegistration() {
    const name = document.getElementById('reg-student-name').value.trim();
    if (!name) {
        showToast("Please enter your name!", "warning");
        return;
    }
    if (!state.capturedImageBlob) {
        showToast("Face capture is required to register.", "error");
        return;
    }

    showLoader("Registering student profile...");
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('image', state.capturedImageBlob, 'register_face.jpg');
    if (state.voiceRecordBlob) {
        formData.append('audio', state.voiceRecordBlob, 'voice_enroll.wav');
    }

    try {
        const res = await fetch(`${API_URL}/api/student/register`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            state.student = data.student;
            sessionStorage.setItem('student_user', JSON.stringify(data.student));
            showToast(data.message, 'success');
            
            // Clean up register forms
            document.getElementById('student-register-container').classList.add('hidden');
            document.getElementById('reg-student-name').value = '';
            document.getElementById('voice-preview').classList.add('hidden');
            
            showStudentDashboard();
        } else {
            showToast(data.message || "Registration failed", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server connection error.", "error");
    }
}

async function showStudentDashboard() {
    document.getElementById('student-display-name').innerText = state.student.name;
    document.getElementById('student-profile').classList.remove('hidden');
    document.getElementById('student-login-view').classList.remove('active');
    document.getElementById('student-dashboard-view').classList.add('active');
    
    await fetchStudentCourses();

    // Check for pending enroll code
    if (state.pendingEnrollCode) {
        const joinCode = state.pendingEnrollCode;
        state.pendingEnrollCode = null;
        
        // Show confirmation modal
        showLoader("Checking course details...");
        try {
            // Find subject name via quick call
            const res = await fetch(`${API_URL}/api/student/enroll`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id: state.student.student_id, join_code: joinCode })
            });
            const data = await res.json();
            hideLoader();
            
            if (data.status === 'success') {
                showToast(data.message, 'success');
                fetchStudentCourses();
            } else if (data.status === 'warning') {
                showToast(data.message, 'info');
            } else {
                showToast(data.message || "Auto-enrollment failed", 'error');
            }
        } catch (e) {
            hideLoader();
        }
        
        // Clear query parameters from address bar
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

async function fetchStudentCourses() {
    const grid = document.getElementById('student-subjects-grid');
    grid.innerHTML = '<p class="loading-text">Loading courses...</p>';

    try {
        const res = await fetch(`${API_URL}/api/student/subjects?student_id=${state.student.student_id}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            grid.innerHTML = '';
            if (data.subjects.length === 0) {
                grid.innerHTML = '<p class="desc text-center">You are not enrolled in any subjects. Enroll in a course to begin!</p>';
                return;
            }
            data.subjects.forEach(sub => {
                const card = document.createElement('div');
                card.className = 'subject-card';
                card.innerHTML = `
                    <div class="subject-info">
                        <h3>${sub.name}</h3>
                        <div class="subject-sub">
                            <span>Code: ${sub.subject_code}</span>
                            <span>Sec: ${sub.section}</span>
                        </div>
                    </div>
                    <div class="subject-stats-row">
                        <div class="stat-item">
                            <span class="stat-icon">calendar_month</span>
                            <div>
                                <div class="stat-val">${sub.total_classes}</div>
                                <div class="stat-lbl">Total</div>
                            </div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-icon">check_circle</span>
                            <div>
                                <div class="stat-val">${sub.attended_classes}</div>
                                <div class="stat-lbl">Attended</div>
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-danger btn-block" onclick="unenrollSubject(${sub.subject_id}, '${sub.name}')">
                        <span class="material-symbols-outlined">delete_forever</span> Unenroll
                    </button>
                `;
                grid.appendChild(card);
            });
        } else {
            showToast("Failed to fetch subjects.", "error");
        }
    } catch (err) {
        showToast("Database fetch request failed.", "error");
    }
}

function openEnrollModal() {
    document.getElementById('enroll-modal').classList.add('active');
    document.getElementById('enroll-subject-code').focus();
}

function closeEnrollModal() {
    document.getElementById('enroll-modal').classList.remove('active');
    document.getElementById('enroll-subject-code').value = '';
}

async function submitEnroll() {
    const code = document.getElementById('enroll-subject-code').value.trim();
    if (!code) return;

    showLoader("Joining subject course...");
    try {
        const res = await fetch(`${API_URL}/api/student/enroll`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: state.student.student_id,
                join_code: code
            })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            closeEnrollModal();
            fetchStudentCourses();
        } else {
            showToast(data.message || "Failed to enroll.", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server request failed.", "error");
    }
}

async function unenrollSubject(subjectId, name) {
    if (!confirm(`Are you sure you want to unenroll from ${name}?`)) return;

    showLoader("Leaving course...");
    try {
        const res = await fetch(`${API_URL}/api/student/unenroll`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: state.student.student_id,
                subject_id: subjectId
            })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            fetchStudentCourses();
        } else {
            showToast(data.message || "Failed to unenroll.", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server request failed.", "error");
    }
}

function logoutStudent() {
    sessionStorage.removeItem('student_user');
    state.student = null;
    showStudentLogin();
}

// ----------------- Teacher Portal Section -----------------
function showTeacherLogin() {
    document.getElementById('teacher-profile').classList.add('hidden');
    document.getElementById('teacher-login-view').classList.add('active');
    document.getElementById('teacher-register-view').classList.remove('active');
    document.getElementById('teacher-dashboard-view').classList.remove('active');
}

function showTeacherRegister() {
    document.getElementById('teacher-login-view').classList.remove('active');
    document.getElementById('teacher-register-view').classList.add('active');
}

async function loginTeacherSubmit() {
    const user = document.getElementById('teacher-login-username').value.trim();
    const pass = document.getElementById('teacher-login-password').value;

    if (!user || !pass) {
        showToast("Fields cannot be empty!", "warning");
        return;
    }

    showLoader("Authenticating credentials...");
    try {
        const res = await fetch(`${API_URL}/api/teacher/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            state.teacher = data.teacher;
            sessionStorage.setItem('teacher_user', JSON.stringify(data.teacher));
            showToast("Welcome Back!", "success");
            showTeacherDashboard();
        } else {
            showToast(data.message || "Invalid login credentials", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server request failed.", "error");
    }
}

async function registerTeacherSubmit() {
    const user = document.getElementById('teacher-reg-username').value.trim();
    const name = document.getElementById('teacher-reg-name').value.trim();
    const pass = document.getElementById('teacher-reg-password').value;
    const confirm = document.getElementById('teacher-reg-confirm').value;

    if (!user || !name || !pass) {
        showToast("All fields are required!", "warning");
        return;
    }

    showLoader("Creating profile...");
    try {
        const res = await fetch(`${API_URL}/api/teacher/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: user,
                name: name,
                password: pass,
                confirm_password: confirm
            })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showToast(data.message, "success");
            showTeacherLogin();
            document.getElementById('teacher-reg-username').value = '';
            document.getElementById('teacher-reg-name').value = '';
            document.getElementById('teacher-reg-password').value = '';
            document.getElementById('teacher-reg-confirm').value = '';
        } else {
            showToast(data.message || "Registration failed", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server request failed.", "error");
    }
}

function showTeacherDashboard() {
    document.getElementById('teacher-display-name').innerText = state.teacher.name;
    document.getElementById('teacher-profile').classList.remove('hidden');
    document.getElementById('teacher-login-view').classList.remove('active');
    document.getElementById('teacher-register-view').classList.remove('active');
    document.getElementById('teacher-dashboard-view').classList.add('active');
    
    // Switch to first tab and refresh
    switchTeacherTab('take_attendance');
    populateTeacherSubjects();
}

function switchTeacherTab(tabId) {
    state.activeTeacherTab = tabId;
    
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.getElementById(`tab-${tabId.replace('_', '-')}`).classList.add('active');
    document.getElementById(`teacher-tab-${tabId}-content`).classList.add('active');
    
    if (tabId === 'manage_subjects') {
        fetchTeacherSubjectsGrid();
    } else if (tabId === 'attendance_records') {
        fetchTeacherAttendanceRecords();
    }
}

async function populateTeacherSubjects() {
    const select = document.getElementById('attendance-subject-select');
    select.innerHTML = '<option value="">Loading courses...</option>';

    try {
        const res = await fetch(`${API_URL}/api/teacher/subjects?teacher_id=${state.teacher.teacher_id}`);
        const data = await res.json();

        if (data.status === 'success') {
            select.innerHTML = '';
            if (data.subjects.length === 0) {
                select.innerHTML = '<option value="">No subjects created yet</option>';
                return;
            }
            data.subjects.forEach(sub => {
                const opt = document.createElement('option');
                opt.value = sub.subject_id;
                opt.innerText = `${sub.name} - ${sub.subject_code} (Sec ${sub.section})`;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        showToast("Failed to populate subjects.", "error");
    }
}

// ----------------- Take Attendance Functions -----------------
function handlePhotoSelection() {
    const uploadInput = document.getElementById('attendance-photo-upload');
    const gallery = document.getElementById('uploaded-photo-preview');
    const clearBtn = document.getElementById('btn-clear-photos');
    const runBtn = document.getElementById('btn-run-face-analysis');
    
    state.classroomPhotos = Array.from(uploadInput.files);
    gallery.innerHTML = '';
    
    if (state.classroomPhotos.length > 0) {
        clearBtn.classList.remove('hidden');
        runBtn.removeAttribute('disabled');
        
        state.classroomPhotos.forEach((file, idx) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const item = document.createElement('div');
                item.className = 'photo-preview-item';
                item.innerHTML = `
                    <img src="${e.target.result}" alt="Preview">
                    <span class="photo-badge">P${idx+1}</span>
                `;
                gallery.appendChild(item);
            }
            reader.readAsDataURL(file);
        });
    } else {
        clearBtn.classList.add('hidden');
        runBtn.setAttribute('disabled', 'true');
    }
}

function clearClassroomPhotos() {
    document.getElementById('attendance-photo-upload').value = '';
    document.getElementById('uploaded-photo-preview').innerHTML = '';
    document.getElementById('btn-clear-photos').classList.add('hidden');
    document.getElementById('btn-run-face-analysis').setAttribute('disabled', 'true');
    state.classroomPhotos = [];
}

async function runFaceAnalysis() {
    const subjectId = document.getElementById('attendance-subject-select').value;
    if (!subjectId) {
        showToast("Please select a subject first!", "warning");
        return;
    }
    if (state.classroomPhotos.length === 0) return;

    showLoader("Scanning classroom photos for FaceID matches...");
    
    const formData = new FormData();
    formData.append('subject_id', subjectId);
    state.classroomPhotos.forEach(photo => {
        formData.append('images', photo);
    });

    try {
        const res = await fetch(`${API_URL}/api/teacher/take-attendance/face`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showReportsModal(data.results, data.logs);
        } else if (data.status === 'warning') {
            showToast(data.message, 'warning');
        } else {
            showToast(data.message || "Face analysis failed", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server analysis request failed.", "error");
    }
}

async function toggleClassroomVoiceRecording() {
    const btn = document.getElementById('btn-record-classroom');
    const text = btn.querySelector('.record-classroom-text');
    const indicator = document.querySelector('.recording-indicator-classroom');
    const audioPreview = document.getElementById('classroom-audio-preview');
    const runBtn = document.getElementById('btn-run-voice-analysis');

    if (!state.activeClassroomRecording) {
        try {
            audioSamples = [];
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            mediaStreamSource = audioContext.createMediaStreamSource(stream);
            scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

            scriptProcessor.onaudioprocess = function (e) {
                let input = e.inputBuffer.getChannelData(0);
                audioSamples.push(new Float32Array(input));
            };

            mediaStreamSource.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);
            activeAudioStream = stream;

            state.activeClassroomRecording = true;
            btn.classList.add('recording');
            text.innerText = "Stop Session";
            indicator.classList.remove('hidden');
            audioPreview.classList.add('hidden');
            runBtn.setAttribute('disabled', 'true');
        } catch (err) {
            showToast("Failed to record audio. Check microphone permissions.", "error");
        }
    } else {
        scriptProcessor.disconnect();
        mediaStreamSource.disconnect();
        activeAudioStream.getTracks().forEach(track => track.stop());

        // merge buffers
        let totalLength = audioSamples.reduce((acc, buf) => acc + buf.length, 0);
        let merged = new Float32Array(totalLength);
        let offset = 0;
        for (let buf of audioSamples) {
            merged.set(buf, offset);
            offset += buf.length;
        }

        let audioBuffer = audioContext.createBuffer(1, totalLength, audioContext.sampleRate);
        audioBuffer.copyToChannel(merged, 0);

        state.classroomAudioBlob = bufferToWav(audioBuffer);
        
        // Setup preview
        const audioURL = URL.createObjectURL(state.classroomAudioBlob);
        audioPreview.src = audioURL;
        audioPreview.classList.remove('hidden');

        state.activeClassroomRecording = false;
        btn.classList.remove('recording');
        text.innerText = "Record Session";
        indicator.classList.add('hidden');
        runBtn.removeAttribute('disabled');
    }
}

async function runVoiceAnalysis() {
    const subjectId = document.getElementById('attendance-subject-select').value;
    if (!subjectId) {
        showToast("Please select a subject first!", "warning");
        return;
    }
    if (!state.classroomAudioBlob) return;

    showLoader("Filtering vocal patterns and matching speaker profiles...");
    
    const formData = new FormData();
    formData.append('subject_id', subjectId);
    formData.append('audio', state.classroomAudioBlob, 'classroom_attendance.wav');

    try {
        const res = await fetch(`${API_URL}/api/teacher/take-attendance/voice`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showReportsModal(data.results, data.logs);
        } else {
            showToast(data.message || "Voice analysis failed", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server analysis request failed.", "error");
    }
}

// ----------------- Reports Verification Modal -----------------
function showReportsModal(results, logs) {
    state.currentReportLogs = logs;
    const tbody = document.getElementById('reports-tbody');
    tbody.innerHTML = '';
    
    results.forEach(res => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${res.name}</strong></td>
            <td>${res.student_id}</td>
            <td><span class="source-badge">${res.source}</span></td>
            <td><strong>${res.status}</strong></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('reports-modal').classList.add('active');
}

function closeReportsModal() {
    document.getElementById('reports-modal').classList.remove('active');
    state.currentReportLogs = null;
}

function discardAttendanceReport() {
    if (confirm("Discard results? Attendance logs will not be recorded.")) {
        closeReportsModal();
        clearClassroomPhotos();
        
        // Clear audio previews
        document.getElementById('classroom-audio-preview').classList.add('hidden');
        document.getElementById('btn-run-voice-analysis').setAttribute('disabled', 'true');
        state.classroomAudioBlob = null;
        
        showToast("Attendance sheet discarded.", "info");
    }
}

async function confirmAttendanceReport() {
    if (!state.currentReportLogs) return;

    showLoader("Saving logs to secure database...");
    try {
        const res = await fetch(`${API_URL}/api/teacher/confirm-attendance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ logs: state.currentReportLogs })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            closeReportsModal();
            clearClassroomPhotos();
            
            // Clear audio previews
            document.getElementById('classroom-audio-preview').classList.add('hidden');
            document.getElementById('btn-run-voice-analysis').setAttribute('disabled', 'true');
            state.classroomAudioBlob = null;
            
            // Refresh subjects grid
            populateTeacherSubjects();
        } else {
            showToast(data.message || "Failed to confirm attendance.", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Database synchronization failed.", "error");
    }
}

// ----------------- Manage Subjects Functions -----------------
async function fetchTeacherSubjectsGrid() {
    const grid = document.getElementById('teacher-subjects-list');
    grid.innerHTML = '<p class="loading-text">Loading courses...</p>';

    try {
        const res = await fetch(`${API_URL}/api/teacher/subjects?teacher_id=${state.teacher.teacher_id}`);
        const data = await res.json();

        if (data.status === 'success') {
            grid.innerHTML = '';
            if (data.subjects.length === 0) {
                grid.innerHTML = '<p class="desc text-center">You have not created any subject classrooms yet. Create one to begin!</p>';
                return;
            }
            data.subjects.forEach(sub => {
                const card = document.createElement('div');
                card.className = 'subject-card';
                card.innerHTML = `
                    <div class="subject-info">
                        <h3>${sub.name}</h3>
                        <div class="subject-sub">
                            <span>Code: ${sub.subject_code}</span>
                            <span>Sec: ${sub.section}</span>
                        </div>
                    </div>
                    <div class="subject-stats-row">
                        <div class="stat-item">
                            <span class="stat-icon">groups</span>
                            <div>
                                <div class="stat-val">${sub.total_students}</div>
                                <div class="stat-lbl">Enrolled</div>
                            </div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-icon">schedule</span>
                            <div>
                                <div class="stat-val">${sub.total_classes}</div>
                                <div class="stat-lbl">Sessions</div>
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-block" onclick="openShareModal('${sub.name}', '${sub.subject_code}')">
                        <span class="material-symbols-outlined">share</span> Share Code Link
                    </button>
                `;
                grid.appendChild(card);
            });
        }
    } catch (err) {
        showToast("Database fetch request failed.", "error");
    }
}

function openCreateSubjectModal() {
    document.getElementById('create-subject-modal').classList.add('active');
    document.getElementById('new-subject-code').focus();
}

function closeCreateSubjectModal() {
    document.getElementById('create-subject-modal').classList.remove('active');
    document.getElementById('new-subject-code').value = '';
    document.getElementById('new-subject-name').value = '';
    document.getElementById('new-subject-section').value = '';
}

async function submitCreateSubject() {
    const code = document.getElementById('new-subject-code').value.trim();
    const name = document.getElementById('new-subject-name').value.trim();
    const section = document.getElementById('new-subject-section').value.trim();

    if (!code || !name || !section) {
        showToast("Fill in all details to create course!", "warning");
        return;
    }

    showLoader("Creating new subject course...");
    try {
        const res = await fetch(`${API_URL}/api/teacher/create-subject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                subject_code: code,
                name: name,
                section: section,
                teacher_id: state.teacher.teacher_id
            })
        });
        const data = await res.json();
        hideLoader();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            closeCreateSubjectModal();
            fetchTeacherSubjectsGrid();
            populateTeacherSubjects(); // Refresh select
        } else {
            showToast(data.message || "Failed to create subject.", "error");
        }
    } catch (err) {
        hideLoader();
        showToast("Server request failed.", "error");
    }
}

// ----------------- Share Code Link Modal -----------------
function openShareModal(name, code) {
    document.getElementById('share-modal-title').innerText = `Share Portal for ${name}`;
    document.getElementById('share-code-badge').innerText = code;
    
    // Dynamic Join URL based on client host
    const joinUrl = `${window.location.origin}/?join-code=${code}`;
    document.getElementById('share-link-text').innerText = joinUrl;
    
    // Call server API for Segno QR Code
    document.getElementById('share-qr-image').src = `/api/qrcode?code=${code}`;
    
    document.getElementById('share-modal').classList.add('active');
}

function closeShareModal() {
    document.getElementById('share-modal').classList.remove('active');
}

function copyJoinLink() {
    const link = document.getElementById('share-link-text').innerText;
    navigator.clipboard.writeText(link).then(() => {
        showToast("Joining URL copied to clipboard!", "success");
    }).catch(err => {
        showToast("Clipboard copy failed.", "error");
    });
}

// ----------------- Fetch Attendance History Records -----------------
async function fetchTeacherAttendanceRecords() {
    const tbody = document.getElementById('attendance-records-tbody');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">Loading logs...</td></tr>';

    try {
        const res = await fetch(`${API_URL}/api/teacher/records?teacher_id=${state.teacher.teacher_id}`);
        const data = await res.json();

        if (data.status === 'success') {
            tbody.innerHTML = '';
            if (data.records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">No attendance sessions recorded yet.</td></tr>';
                return;
            }
            data.records.forEach(rec => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${rec.Time}</td>
                    <td><strong>${rec.Subject}</strong></td>
                    <td>${rec.SubjectCode}</td>
                    <td><strong style="color: var(--primary);">${rec.AttendanceStats}</strong></td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        showToast("Database fetch request failed.", "error");
    }
}

function logoutTeacher() {
    sessionStorage.removeItem('teacher_user');
    state.teacher = null;
    showTeacherLogin();
}
