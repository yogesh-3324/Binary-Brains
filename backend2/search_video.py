# search_video.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import faiss
from collections import defaultdict
from utils import hash_frames, extract_frames_with_timestamps

# =====================================================
# CONFIG
# =====================================================
SAMPLE_FPS = 1
MAX_HAMMING_DISTANCE = 15  # Maximum Hamming distance for frame match (out of 64)
MATCH_SCORE_THRESHOLD = 0.45 # Minimum confidence score for candidate clip match
TOP_K_FRAME_NEIGHBORS = 5

def format_time(seconds: float) -> str:
    secs = max(0, int(round(seconds)))
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins:02d}:{rem_secs:02d}"

# =====================================================
# SUB-CLIP TEMPORAL ALIGNMENT SEARCH LOGIC
# =====================================================
def find_similar_videos(query_path: str, store_dir: str):
    index_path = os.path.join(store_dir, "videos.index")
    paths_path = os.path.join(store_dir, "video_paths.npy")
    meta_path = os.path.join(store_dir, "frame_meta.npy")

    if not (os.path.exists(index_path) and os.path.exists(paths_path) and os.path.exists(meta_path)):
        print("Store files missing in search_video.")
        return []

    index = faiss.read_index_binary(index_path)
    video_paths = np.load(paths_path, allow_pickle=True)
    frame_meta = np.load(meta_path, allow_pickle=True)

    if index.ntotal == 0 or len(frame_meta) == 0:
        return []

    # 1. Extract Query Frames & Timestamps (1 frame every 1.5 seconds)
    query_items = extract_frames_with_timestamps(query_path, sample_interval_sec=1.5)
    if not query_items:
        return []

    frames = [it["frame"] for it in query_items]
    query_embeds = hash_frames(frames)
    num_query_frames = len(query_embeds)

    # 2. FAISS Frame Search (Query each query frame against indexed reference frames)
    k_neighbors = min(TOP_K_FRAME_NEIGHBORS, index.ntotal)
    distances, indices = index.search(query_embeds, k_neighbors)

    # 3. Collect Frame Matches grouped by candidate reference video
    # Structure: video_matches[video_path] = list of {"q_ts", "ref_ts", "score", "offset"}
    video_matches = defaultdict(list)

    for q_idx in range(num_query_frames):
        q_ts = query_items[q_idx]["timestamp"]

        for neighbor_idx in range(k_neighbors):
            vec_idx = indices[q_idx][neighbor_idx]
            if vec_idx == -1:
                continue

            dist = float(distances[q_idx][neighbor_idx])
            if dist > MAX_HAMMING_DISTANCE:
                continue

            # Convert Hamming distance to a similarity score [0, 1]
            score = (64.0 - dist) / 64.0

            meta = frame_meta[vec_idx]
            ref_path = meta["video"]
            ref_ts = meta["timestamp"]
            offset = round(ref_ts - q_ts, 1)

            video_matches[ref_path].append({
                "q_ts": q_ts,
                "ref_ts": ref_ts,
                "score": score,
                "offset": offset
            })

    # 4. Temporal Offset Consensus Clustering per candidate video
    candidate_results = []

    for ref_path, matches in video_matches.items():
        if not matches:
            continue

        # Bin offsets by 1.5 second tolerance windows to find the largest aligned cluster
        offset_clusters = defaultdict(list)
        for m in matches:
            # Round offset to nearest 1.5s bin
            bin_key = round(m["offset"] / 1.5) * 1.5
            offset_clusters[bin_key].append(m)

        # Pick the cluster with highest match count & cumulative score
        best_cluster = max(
            offset_clusters.values(),
            key=lambda cluster: (len({m["q_ts"] for m in cluster}), sum(m["score"] for m in cluster))
        )

        # Unique query frames matched in best cluster
        unique_q_matched = len({m["q_ts"] for m in best_cluster})
        avg_cluster_score = sum(m["score"] for m in best_cluster) / len(best_cluster)
        
        # Coverage ratio of the query clip
        coverage = unique_q_matched / num_query_frames

        # Weighted final score combining frame cosine similarity and temporal clip coverage
        final_score = (0.6 * avg_cluster_score) + (0.4 * coverage)

        if final_score < MATCH_SCORE_THRESHOLD:
            continue

        ref_timestamps = [m["ref_ts"] for m in best_cluster]
        start_ts = min(ref_timestamps)
        end_ts = max(ref_timestamps)
        ts_range_str = f"{format_time(start_ts)} - {format_time(end_ts)}"

        verdict = "ORIGINAL SOURCE MATCH" if final_score >= 0.70 else "SUB-CLIP MATCH"

        candidate_results.append({
            "video": os.path.basename(ref_path),
            "path": ref_path,
            "hash_score": round(final_score, 4),
            "confidence": f"{min(100.0, final_score * 100):.2f}%",
            "matched_frames": f"{unique_q_matched} / {num_query_frames} frames",
            "timestamp_range": ts_range_str,
            "verdict": verdict
        })

    # 5. Sort by final score descending
    candidate_results.sort(key=lambda x: x["hash_score"], reverse=True)

    for rank, res in enumerate(candidate_results[:5], 1):
        res["rank"] = rank

    return candidate_results[:5]

