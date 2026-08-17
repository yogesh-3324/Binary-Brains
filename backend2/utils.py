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
import torch
import torchvision.transforms as T

# ==========================================
# DINOv2 FEATURE EXTRACTOR FOR VIDEO FRAMES
# ==========================================
_DINO_MODEL = None
_DINO_TRANSFORM = None
_DINO_DEVICE = None

def get_dino_tools(model_name="dinov2_vits14"):
    global _DINO_MODEL, _DINO_TRANSFORM, _DINO_DEVICE
    if _DINO_MODEL is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading DINOv2 ({model_name}) for video frames on {device}...")
        model = torch.hub.load("facebookresearch/dinov2", model_name)
        model = model.to(device).eval()

        transform = T.Compose([
            T.Resize((224, 224)),
            T.Grayscale(num_output_channels=3),
            T.ToTensor(),
            T.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)
            ),
        ])
        _DINO_MODEL = model
        _DINO_TRANSFORM = transform
        _DINO_DEVICE = device
    return _DINO_MODEL, _DINO_TRANSFORM, _DINO_DEVICE

def embed_video_frames(frames, batch_size=16):
    """
    Computes DINOv2 384-dim normalized visual embeddings for a list of RGB numpy frames.
    """
    if not frames:
        return np.empty((0, 384), dtype=np.float32)

    model, transform, device = get_dino_tools()
    embeddings = []

    for i in range(0, len(frames), batch_size):
        batch_frames = frames[i : i + batch_size]
        batch_tensors = []

        for f in batch_frames:
            try:
                pil_img = Image.fromarray(f).convert("RGB")
                img_tensor = transform(pil_img)
                batch_tensors.append(img_tensor)
            except Exception as e:
                print(f"Error processing frame: {e}")

        if not batch_tensors:
            continue

        batch_stack = torch.stack(batch_tensors).to(device)
        with torch.inference_mode():
            features = model(batch_stack)
            features = torch.nn.functional.normalize(features, dim=-1)
            embeddings.append(features.cpu().numpy())

    if not embeddings:
        return np.empty((0, 384), dtype=np.float32)

    return np.vstack(embeddings).astype("float32")

# ==========================================
# PERCEPTUAL VIDEO HASHING & FAST HAMMING DISTANCE
# ==========================================
BIT_COUNT_TABLE = np.array([bin(i).count('1') for i in range(256)], dtype=np.int32)

def hash_frames(frames):
    """
    Computes a 64-bit phash for each frame.
    Returns a numpy array of uint8, shape (N, 8) suitable for fast Hamming search.
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

def hash_frames_hex(frames):
    """
    Computes pHash string representation for a list of RGB frames.
    """
    hex_list = []
    for f in frames:
        pil_img = Image.fromarray(f)
        h = imagehash.phash(pil_img, hash_size=8)
        hex_list.append(str(h))
    return hex_list

def compute_hamming_matrix(query_bytes: np.ndarray, ref_bytes: np.ndarray) -> np.ndarray:
    """
    Computes pairwise Hamming distance matrix between N query hashes and M reference hashes.
    query_bytes: shape (N, 8) uint8
    ref_bytes: shape (M, 8) uint8
    Returns: shape (N, M) int32 matrix of Hamming distances (0 to 64).
    """
    if query_bytes.size == 0 or ref_bytes.size == 0:
        return np.empty((len(query_bytes), len(ref_bytes)), dtype=np.int32)

    xor_res = np.bitwise_xor(query_bytes[:, None, :], ref_bytes[None, :, :])
    dist = BIT_COUNT_TABLE[xor_res].sum(axis=2)
    return dist

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
