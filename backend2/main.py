# main.py
import torch
import numpy as np
import faiss
import glob
import os
from PIL import Image
from utils import get_dino_tools, extract_frames  # Uses cached tools

# =====================================================
# CONFIG
# =====================================================
STORE_DIR = "dinov2_video_store"
SAMPLE_FPS = 1

os.makedirs(STORE_DIR, exist_ok=True)

# =====================================================
# FRAME EMBEDDING
# =====================================================
def embed_frames(frames, model, transform, device, batch_size=16):
    feats = []
    # Process in batches to save VRAM
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        
        # Convert to PIL and Transform
        tensors = [transform(Image.fromarray(f)) for f in batch]
        x = torch.stack(tensors).to(device)

        with torch.no_grad():
            f = model(x)
            # Normalize frame-level vectors
            f = torch.nn.functional.normalize(f, dim=-1)

        feats.append(f.cpu().numpy())

    if not feats:
        return np.array([], dtype="float32")

    return np.vstack(feats).astype("float32")

# =====================================================
# MAIN INDEX FUNCTION
# =====================================================
def process_reference_pool(pool_dir: str):
    video_files = sorted(glob.glob(os.path.join(pool_dir, "*.mp4")))
    
    index_path = os.path.join(STORE_DIR, "videos.index")
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")

    # Load existing state
    if os.path.exists(index_path) and os.path.exists(paths_path):
        index = faiss.read_index(index_path)
        video_paths = list(np.load(paths_path, allow_pickle=True))
    else:
        index = None
        video_paths = []

    # Filter out videos already in index
    existing_set = set(video_paths)
    new_videos = [v for v in video_files if v not in existing_set]

    if not new_videos:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}

    # Load DINOv2 (Cached)
    model, transform, device = get_dino_tools()
    
    new_vectors = []
    added_paths = []

    print(f"Indexing {len(new_videos)} new videos...")

    for path in new_videos:
        frames = extract_frames(path, SAMPLE_FPS)
        if not frames:
            print(f"⚠️ Skipping {path} (No frames)")
            continue

        frame_embeds = embed_frames(frames, model, transform, device)
        
        if frame_embeds.size == 0:
            continue

        # --- CRITICAL MATH FIX ---
        # 1. Average frame vectors
        video_embed = np.mean(frame_embeds, axis=0).reshape(1, -1)
        # 2. Re-Normalize the averaged vector (Required for Cosine Sim in FAISS)
        faiss.normalize_L2(video_embed) 
        # -------------------------

        new_vectors.append(video_embed)
        added_paths.append(path)

    if not new_vectors:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}

    new_vectors = np.vstack(new_vectors).astype("float32")
    
    # Initialize FAISS Index if not exists
    if index is None:
        d = new_vectors.shape[1]
        # IndexFlatIP = Inner Product (Cosine Similarity when vectors are normalized)
        index = faiss.IndexFlatIP(d) 
    
    index.add(new_vectors)
    
    # Save State
    video_paths.extend(added_paths)
    faiss.write_index(index, index_path)
    np.save(paths_path, np.array(video_paths))

    return {
        "status": "ok", 
        "count": len(video_paths), 
        "newly_added": len(new_vectors)
    }

# =====================================================
# DELETE UTILITY
# =====================================================
def remove_video_from_index(filename: str):
    index_path = os.path.join(STORE_DIR, "videos.index")
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")

    if not os.path.exists(index_path):
        return False

    video_paths = list(np.load(paths_path, allow_pickle=True))
    
    # Check if file exists in records
    target_basename = os.path.basename(filename)
    if target_basename not in [os.path.basename(p) for p in video_paths]:
        return False

    # Find indices to keep
    keep_indices = [
        i for i, p in enumerate(video_paths)
        if os.path.basename(p) != target_basename
    ]

    # If deleting the last video, just remove files
    if not keep_indices:
        os.remove(index_path)
        os.remove(paths_path)
        return True

    # Rebuild Index (FAISS doesn't support easy deletion in FlatIP)
    old_index = faiss.read_index(index_path)
    vectors = old_index.reconstruct_n(0, old_index.ntotal)
    
    new_vectors = vectors[keep_indices]
    new_paths = [video_paths[i] for i in keep_indices]

    # Create fresh index
    index = faiss.IndexFlatIP(new_vectors.shape[1])
    index.add(new_vectors)

    faiss.write_index(index, index_path)
    np.save(paths_path, np.array(new_paths))
    
    return True