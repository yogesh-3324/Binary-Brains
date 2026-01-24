# search_video.py
import torch
import numpy as np
import faiss
import os
from PIL import Image
from utils import get_dino_tools, get_clip_tools, extract_frames

# =====================================================
# CONFIG
# =====================================================
SAMPLE_FPS = 1
TOP_K = 2  # How many candidates to verify with CLIP

# Thresholds for CLIP Verification
HIGH_RATIO = 0.85     # Very confident match
MID_RATIO = 0.70      # Likely match

# =====================================================
# CLIP EMBEDDING HELPER
# =====================================================
def clip_video_embedding(video_path, model, processor, device, fps=1):
    """
    Generates a single vector for a video using CLIP.
    """
    frames = extract_frames(video_path, fps)
    if not frames: return None
    
    images = [Image.fromarray(f) for f in frames]
    
    # Tokenize/Process images
    inputs = processor(images=images, return_tensors="pt", padding=True).to(device)

    with torch.no_grad():
        feats = model.get_image_features(**inputs)
        feats = torch.nn.functional.normalize(feats, dim=-1)

    # Average frames and normalize result
    embed = feats.mean(dim=0)
    embed = embed / embed.norm() 
    return embed.cpu().numpy()

# =====================================================
# MAIN SEARCH LOGIC
# =====================================================
def find_similar_videos(query_path: str, store_dir: str):
    index_path = os.path.join(store_dir, "videos.index")
    paths_path = os.path.join(store_dir, "video_paths.npy")

    if not os.path.exists(index_path):
        return []
    
    # Load Index
    index = faiss.read_index(index_path)
    video_paths = np.load(paths_path, allow_pickle=True)

    if index.ntotal == 0:
        return []

    # 1. Load All Models (Cached via utils)
    dino_model, dino_transform, dino_device = get_dino_tools()
    clip_model, clip_processor, clip_device = get_clip_tools()

    # 2. --- STEP A: COARSE SEARCH (DINOv2) ---
    query_frames = extract_frames(query_path, fps=SAMPLE_FPS)
    if not query_frames:
        return []

    # Embed Query Frames (DINO)
    tensors = [dino_transform(Image.fromarray(f)) for f in query_frames]
    x = torch.stack(tensors).to(dino_device)
    
    with torch.no_grad():
        f = dino_model(x)
        f = torch.nn.functional.normalize(f, dim=-1)
    
    # Average & Normalize (Must match main.py logic)
    query_dino_embed = f.cpu().numpy()
    query_global = np.mean(query_dino_embed, axis=0).reshape(1, -1)
    faiss.normalize_L2(query_global) 

    # Search in FAISS
    k = min(TOP_K, index.ntotal)
    distances, indices = index.search(query_global, k)

    # 3. --- STEP B: FINE VERIFICATION (CLIP) ---
    
    # Calculate CLIP embedding for Query Video ONCE
    query_clip_embed = clip_video_embedding(
        query_path, clip_model, clip_processor, clip_device, fps=SAMPLE_FPS
    )
    
    results = []
    
    for rank in range(k):
        idx = indices[0][rank]
        if idx == -1: continue 
        
        candidate_path = video_paths[idx]
        
        # Calculate CLIP embedding for Candidate Video
        # (In production, you might want to cache these too, but calculating on fly is safer for now)
        candidate_clip = clip_video_embedding(
            candidate_path, clip_model, clip_processor, clip_device, fps=SAMPLE_FPS
        )

        if candidate_clip is None:
            continue

        # Cosine Similarity
        score = float(np.dot(query_clip_embed, candidate_clip))

        # Verdict Logic
        if score >= HIGH_RATIO:
            verdict = "FOUND"
        elif score >= MID_RATIO:
            verdict = "POSSIBLE"
        else:
            verdict = "NOT_PRESENT"

        results.append({
            "rank": int(rank + 1),
            "video": os.path.basename(candidate_path),
            "path": candidate_path,
            "clip_score": round(score, 4),
            "confidence": f"{score * 100:.2f}%",
            "verdict": verdict
        })

    return results