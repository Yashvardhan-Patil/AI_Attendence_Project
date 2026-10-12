import os
import sys
import io
import gc

# ─────────────────────────────────────────────
#  Memory & Thread Optimization for Cloud Hosting (512MB RAM)
# ─────────────────────────────────────────────
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np

_VOICE_ENCODER = None


def load_voice_encoder():
    """
    Lazily load Resemblyzer VoiceEncoder and disable PyTorch autograd
    to keep memory footprint minimal.
    """
    global _VOICE_ENCODER
    if _VOICE_ENCODER is None:
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_grad_enabled(False)
        except Exception:
            pass

        from resemblyzer import VoiceEncoder
        _VOICE_ENCODER = VoiceEncoder(device="cpu")
    return _VOICE_ENCODER


def get_voice_embedding(audio_bytes):
    """
    Extract a 256-d speaker embedding from raw audio bytes.
    Frees temporary buffers immediately to prevent memory leaks.
    """
    try:
        import librosa
        from resemblyzer import preprocess_wav

        encoder = load_voice_encoder()

        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        wav = preprocess_wav(audio)
        embedding = encoder.embed_utterance(wav)

        del audio
        del wav
        gc.collect()

        return embedding.tolist()
    except Exception as e:
        print('Voice recog error:', e, file=sys.stderr)
        return None


def identify_speaker(new_embedding, candidates_dict, threshold=0.65):
    """
    Identify speaker by computing cosine similarity against candidate embeddings.
    """
    if new_embedding is None or not candidates_dict:
        return None, 0.0

    best_sid = None
    best_score = -1.0

    for sid, stored_embedding in candidates_dict.items():
        if stored_embedding:
            similarity = np.dot(new_embedding, stored_embedding)
            if similarity > best_score:
                best_score = float(similarity)
                best_sid = sid

    if best_score >= threshold:
        return best_sid, best_score

    return None, best_score


def process_bulk_audio(audio_bytes, candidates_dict, threshold=0.65):
    """
    Process classroom audio: split by silence, embed each voice segment,
    and match against enrolled candidates.
    """
    try:
        import librosa
        from resemblyzer import preprocess_wav

        encoder = load_voice_encoder()

        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        segments = librosa.effects.split(audio, top_db=30)

        identified_results = {}

        for start, end in segments:
            if (end - start) < sr * 0.5:
                continue
            segment_audio = audio[start:end]
            wav = preprocess_wav(segment_audio)
            embedding = encoder.embed_utterance(wav)

            sid, score = identify_speaker(embedding, candidates_dict, threshold)

            if sid:
                if sid not in identified_results or score > identified_results[sid]:
                    identified_results[sid] = score

            del wav
            del segment_audio

        del audio
        del segments
        gc.collect()

        return identified_results
    except Exception as e:
        print('Bulk voice process error:', e, file=sys.stderr)
        return {}