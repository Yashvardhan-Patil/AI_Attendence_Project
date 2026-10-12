import gc
import numpy as np

from src.database.db import get_all_students

# ─────────────────────────────────────────────
#  Dlib Model Cache (loaded once per process)
# ─────────────────────────────────────────────

_DLIB_MODELS = None


def load_dlib_models():
    """
    Lazily load dlib face detection and recognition models into a module-level
    cache so they are only loaded once per server process.
    """
    global _DLIB_MODELS
    if _DLIB_MODELS is None:
        import dlib
        import face_recognition_models

        detector = dlib.get_frontal_face_detector()

        sp = dlib.shape_predictor(
            face_recognition_models.pose_predictor_model_location()
        )

        facerec = dlib.face_recognition_model_v1(
            face_recognition_models.face_recognition_model_location()
        )
        _DLIB_MODELS = (detector, sp, facerec)

    return _DLIB_MODELS


def get_face_embeddings(image_np):
    """
    Extract 128-dimensional face embedding vectors for every face found
    in the given RGB numpy image.
    """
    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)

    encodings = []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)  # 128-d
        encodings.append(np.array(face_descriptor))
        del shape
        del face_descriptor

    del faces
    gc.collect()

    return encodings


# ─────────────────────────────────────────────
#  SVM Classifier Cache
# ─────────────────────────────────────────────

_TRAINED_MODEL = None


def get_trained_model():
    """
    Build (or return cached) the SVM face classifier.
    """
    global _TRAINED_MODEL
    if _TRAINED_MODEL is None:
        from sklearn.svm import SVC

        X = []
        y = []

        student_db = get_all_students()

        if not student_db:
            return None

        for student in student_db:
            embedding = student.get('face_embedding')
            if embedding:
                X.append(np.array(embedding))
                y.append(student.get('student_id'))

        if len(X) == 0:
            return None

        clf = None
        if len(set(y)) >= 2:
            clf = SVC(kernel='linear', probability=True, class_weight='balanced')
            clf.fit(X, y)

        _TRAINED_MODEL = {'clf': clf, 'X': X, 'y': y}

    return _TRAINED_MODEL


def train_classifier():
    """
    Reset the in-memory SVM classifier cache.
    """
    global _TRAINED_MODEL
    _TRAINED_MODEL = None
    get_trained_model()
    return True


def predict_attendance(class_image_np):
    """
    Run the face-attendance pipeline on a classroom image.
    """
    encodings = get_face_embeddings(class_image_np)
    detected_student = {}

    model_data = get_trained_model()

    if not model_data:
        return detected_student, [], len(encodings)

    clf = model_data['clf']
    X_train = model_data['X']
    y_train = model_data['y']

    all_students = sorted(list(set(y_train)))
    resemblance_threshold = 0.6

    for encoding in encodings:
        if clf is not None:
            predicted_id = int(clf.predict([encoding])[0])
        else:
            distances = [np.linalg.norm(np.array(x) - encoding) for x in X_train]
            predicted_id = int(y_train[int(np.argmin(distances))])

        idx = y_train.index(predicted_id)
        best_match_score = np.linalg.norm(np.array(X_train[idx]) - encoding)

        if best_match_score <= resemblance_threshold:
            detected_student[predicted_id] = True

    del encodings
    gc.collect()

    return detected_student, all_students, len(detected_student)
