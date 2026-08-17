
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
from pinecone_db import get_pinecone_video_store
import glob
from utils import hash_frames, extract_frames_with_timestamps, embed_video_frames

# =====================================================
# CONFIG
# =====================================================
STORE_DIR = "phash_video_store"
SAMPLE_INTERVAL_SEC = 2.0  # 1 frame every 2.0 seconds

os.makedirs(STORE_DIR, exist_ok=True)


# =====================================================
# MAIN FRAME-LEVEL INDEX FUNCTION
# =====================================================
def process_reference_pool(pool_dir: str):
    video_files = []
    for ext in ["*.mp4", "*.avi", "*.mov", "*.mkv"]:
        video_files.extend(glob.glob(os.path.join(pool_dir, ext)))
    video_files = sorted(video_files)
    
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")
    meta_path = os.path.join(STORE_DIR, "frame_meta.npy")

    # Load existing state
    if os.path.exists(paths_path) and os.path.exists(meta_path):
        video_paths = list(np.load(paths_path, allow_pickle=True))
        frame_meta = list(np.load(meta_path, allow_pickle=True))
    else:
        video_paths = []
        frame_meta = []

    # Filter out videos already in index
    existing_set = set(video_paths)
    new_videos = [v for v in video_files if v not in existing_set]

    if not new_videos:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}
    
    added_paths = []
    total_new_frames = 0
    pinecone_video_store = get_pinecone_video_store()

    print(f"Indexing {len(new_videos)} new videos with DINOv2 keyframe embeddings into Pinecone...")

    for path in new_videos:
        items = extract_frames_with_timestamps(path, sample_interval_sec=SAMPLE_INTERVAL_SEC)
        if not items:
            print(f"Skipping {path} (No frames)")
            continue

        frames = [it["frame"] for it in items]
        
        # 1. Compute DINOv2 384-dim visual embeddings for frames
        dino_embeds = embed_video_frames(frames)
        if dino_embeds.size == 0:
            continue

        # 2. Compute pHashes for frame metadata
        phash_bytes = hash_frames(frames)

        # Upsert 384-dim DINOv2 frame vectors to Pinecone
        pinecone_video_store.upsert_frame_vectors_batch(path, items, dino_embeds)

        added_paths.append(path)
        total_new_frames += len(items)

        for it in items:
            frame_meta.append({
                "video": path,
                "timestamp": it["timestamp"],
                "frame_idx": it["frame_idx"]
            })

    if not added_paths:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}

    video_paths.extend(added_paths)

    np.save(paths_path, np.array(video_paths, dtype=object))
    np.save(meta_path, np.array(frame_meta, dtype=object))

    return {
        "status": "ok", 
        "count": len(video_paths),
        "total_frames": len(frame_meta),
        "newly_added": len(added_paths)
    }

# =====================================================
# DELETE UTILITY
# =====================================================
def remove_video_from_index(filename: str):
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")
    meta_path = os.path.join(STORE_DIR, "frame_meta.npy")

    # Remove from Pinecone Video DB
    target_basename = os.path.basename(filename)
    try:
        pinecone_video_store = get_pinecone_video_store()
        pinecone_video_store.delete_by_video_filename(target_basename)
    except Exception as e:
        print(f"Warning deleting video frames from Pinecone: {e}")

    if not os.path.exists(paths_path) or not os.path.exists(meta_path):
        return True

    video_paths = list(np.load(paths_path, allow_pickle=True))
    frame_meta = list(np.load(meta_path, allow_pickle=True))

    if target_basename not in [os.path.basename(p) for p in video_paths]:
        return False

    keep_indices = [
        i for i, meta in enumerate(frame_meta)
        if os.path.basename(meta["video"]) != target_basename
    ]

    new_video_paths = [
        p for p in video_paths
        if os.path.basename(p) != target_basename
    ]

    if not keep_indices or not new_video_paths:
        if os.path.exists(paths_path): os.remove(paths_path)
        if os.path.exists(meta_path): os.remove(meta_path)
        return True

    new_frame_meta = [frame_meta[i] for i in keep_indices]

    np.save(paths_path, np.array(new_video_paths, dtype=object))
    np.save(meta_path, np.array(new_frame_meta, dtype=object))

    return True


