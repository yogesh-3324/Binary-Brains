# utils.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image
import imagehash

# ==========================================
# PERCEPTUAL VIDEO HASHING
# ==========================================
def hash_frames(frames):
    """
    Computes a 64-bit phash for each frame.
    Returns a numpy array of uint8, shape (N, 8) suitable for faiss.IndexBinaryFlat.
    """
    if not frames:
        return np.empty((0, 8), dtype=np.uint8)

    hashed_bytes = []
    for f in frames:
        pil_img = Image.fromarray(f)
        h = imagehash.phash(pil_img, hash_size=8)
        # h.hash is a boolean numpy array of shape (8, 8)
        # We flatten it to 64 bits and pack it into 8 uint8 bytes
        bool_array = h.hash.flatten()
        packed = np.packbits(bool_array)
        hashed_bytes.append(packed)
    
    return np.vstack(hashed_bytes).astype(np.uint8)

# ==========================================
# ULTRA-FAST DIRECT SEEKING FRAME EXTRACTOR
# ==========================================
def extract_frames_with_timestamps(video_path, sample_interval_sec=2.0):
    """
    Ultra-fast frame extraction using direct hardware seeking.
    Extracts 1 frame every `sample_interval_sec` seconds (default 2.0s).
    Drastically speeds up video decoding (10x-30x faster than sequential reading).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if video_fps <= 0:
        video_fps = 30.0

    frame_step = max(1, int(round(video_fps * sample_interval_sec)))
    results = []

    current_frame = 0
    # Direct position seeking jump instead of reading every frame
    while current_frame < total_frames and total_frames > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = round(current_frame / video_fps, 2)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results.append({
            "frame": rgb_frame,
            "timestamp": timestamp,
            "frame_idx": current_frame
        })

        current_frame += frame_step

    cap.release()
    return results

def extract_frames(video_path, sample_interval_sec=2.0):
    items = extract_frames_with_timestamps(video_path, sample_interval_sec=sample_interval_sec)
    return [item["frame"] for item in items]
