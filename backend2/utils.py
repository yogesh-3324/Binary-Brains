# utils.py
import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as T
from transformers import CLIPProcessor, CLIPModel

# ==========================================
# GLOBAL CACHE (PREVENTS RELOADING)
# ==========================================
_DINO_MODEL = None
_DINO_TRANSFORM = None
_CLIP_MODEL = None
_CLIP_PROCESSOR = None

def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"

# ==========================================
# MODEL LOADERS
# ==========================================
def get_dino_tools(model_name="dinov2_vitb14"):
    global _DINO_MODEL, _DINO_TRANSFORM
    
    if _DINO_MODEL is None:
        print(f"🔄 Loading DINOv2 ({model_name})...")
        device = get_device()
        
        # Load Model
        model = torch.hub.load("facebookresearch/dinov2", model_name)
        model.to(device).eval()

        # Transform (Preserves Aspect Ratio better)
        transform = T.Compose([
            T.Resize(256, interpolation=T.InterpolationMode.BICUBIC),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])
        
        _DINO_MODEL = model
        _DINO_TRANSFORM = transform
        print("✅ DINOv2 Loaded")
    
    return _DINO_MODEL, _DINO_TRANSFORM, get_device()

def get_clip_tools(model_name="openai/clip-vit-base-patch32"):
    global _CLIP_MODEL, _CLIP_PROCESSOR
    
    if _CLIP_MODEL is None:
        print(f"🔄 Loading CLIP ({model_name})...")
        device = get_device()
        model = CLIPModel.from_pretrained(model_name).to(device).eval()
        processor = CLIPProcessor.from_pretrained(model_name)
        
        _CLIP_MODEL = model
        _CLIP_PROCESSOR = processor
        print("✅ CLIP Loaded")

    return _CLIP_MODEL, _CLIP_PROCESSOR, get_device()

# ==========================================
# SHARED VIDEO TOOLS
# ==========================================
def extract_frames(video_path, fps=1):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps == 0:
        return []

    interval = max(1, int(video_fps / fps))
    frames, count = [], 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        count += 1

    cap.release()
    return frames