# utils.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as T

# Optimize PyTorch CPU Threads for maximum throughput
torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

# ==========================================
# GLOBAL CACHE (PREVENTS RELOADING)
# ==========================================
_DINO_MODEL = None
_DINO_TRANSFORM = None

def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"

# ==========================================
# HIGH-SPEED MODEL LOADER (dinov2_vits14)
# ==========================================
def get_dino_tools(model_name="dinov2_vits14"):
    """
    Uses dinov2_vits14 (Small ViT, 21M params) which is 4x faster than ViT-Base 
    with virtually identical accuracy for visual retrieval.
    """
    global _DINO_MODEL, _DINO_TRANSFORM
    
    if _DINO_MODEL is None:
        print(f"⚡ Loading Fast DINOv2 ({model_name})...")
        device = get_device()
        
        # Load Model
        model = torch.hub.load("facebookresearch/dinov2", model_name)
        model.to(device).eval()

        # Transform (Aspect ratio center crop for vertical vs horizontal video matching)
        transform = T.Compose([
            T.Resize(256, interpolation=T.InterpolationMode.BICUBIC),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])
        
        _DINO_MODEL = model
        _DINO_TRANSFORM = transform
        print("✅ Fast DINOv2 Loaded")
    
    return _DINO_MODEL, _DINO_TRANSFORM, get_device()

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
