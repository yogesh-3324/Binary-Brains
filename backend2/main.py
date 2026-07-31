
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import faiss
import glob
from utils import hash_frames, extract_frames_with_timestamps

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
    
    index_path = os.path.join(STORE_DIR, "videos.index")
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")
    meta_path = os.path.join(STORE_DIR, "frame_meta.npy")

    # Load existing state
    if os.path.exists(index_path) and os.path.exists(paths_path) and os.path.exists(meta_path):
        index = faiss.read_index_binary(index_path)
        video_paths = list(np.load(paths_path, allow_pickle=True))
        frame_meta = list(np.load(meta_path, allow_pickle=True))
    else:
        index = None
        video_paths = []
        frame_meta = []

    # Filter out videos already in index
    existing_set = set(video_paths)
    new_videos = [v for v in video_files if v not in existing_set]

    if not new_videos:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}
    
    new_vectors_list = []
    added_paths = []

    print(f"Indexing {len(new_videos)} new videos at frame level...")

    for path in new_videos:
        items = extract_frames_with_timestamps(path, sample_interval_sec=SAMPLE_INTERVAL_SEC)
        if not items:
            print(f"Skipping {path} (No frames)")
            continue

        frames = [it["frame"] for it in items]
        embeds = hash_frames(frames)

        if embeds.size == 0:
            continue

        new_vectors_list.append(embeds)
        added_paths.append(path)

        for it in items:
            frame_meta.append({
                "video": path,
                "timestamp": it["timestamp"],
                "frame_idx": it["frame_idx"]
            })

    if not new_vectors_list:
        return {"status": "ok", "count": len(video_paths), "newly_added": 0}

    new_vectors = np.vstack(new_vectors_list).astype(np.uint8)
    
    if index is None:
        d = 64 # bits for phash
        index = faiss.IndexBinaryFlat(d) 
    
    index.add(new_vectors)
    video_paths.extend(added_paths)

    faiss.write_index_binary(index, index_path)
    np.save(paths_path, np.array(video_paths, dtype=object))
    np.save(meta_path, np.array(frame_meta, dtype=object))

    return {
        "status": "ok", 
        "count": len(video_paths),
        "total_frames": index.ntotal,
        "newly_added": len(added_paths)
    }

# =====================================================
# DELETE UTILITY
# =====================================================
def remove_video_from_index(filename: str):
    index_path = os.path.join(STORE_DIR, "videos.index")
    paths_path = os.path.join(STORE_DIR, "video_paths.npy")
    meta_path = os.path.join(STORE_DIR, "frame_meta.npy")

    if not os.path.exists(index_path) or not os.path.exists(paths_path) or not os.path.exists(meta_path):
        return False

    video_paths = list(np.load(paths_path, allow_pickle=True))
    frame_meta = list(np.load(meta_path, allow_pickle=True))

    target_basename = os.path.basename(filename)
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
        if os.path.exists(index_path): os.remove(index_path)
        if os.path.exists(paths_path): os.remove(paths_path)
        if os.path.exists(meta_path): os.remove(meta_path)
        return True

    old_index = faiss.read_index_binary(index_path)
    # Extract all stored binary vectors from the flat index
    all_vectors = faiss.vector_to_array(old_index.xb).reshape(old_index.ntotal, -1)

    new_vectors = all_vectors[keep_indices].astype(np.uint8)
    new_frame_meta = [frame_meta[i] for i in keep_indices]

    index = faiss.IndexBinaryFlat(64)
    index.add(new_vectors)

    faiss.write_index_binary(index, index_path)
    np.save(paths_path, np.array(new_video_paths, dtype=object))
    np.save(meta_path, np.array(new_frame_meta, dtype=object))

    return True


