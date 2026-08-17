# search_video.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
from pinecone_db import get_pinecone_video_store
from collections import defaultdict
from utils import extract_frames_with_timestamps, embed_video_frames

# =====================================================
# CONFIG
# =====================================================
SAMPLE_FPS = 1
FRAME_SCORE_THRESHOLD = 0.70  # Minimum DINOv2 visual similarity for keyframe match
MATCH_SCORE_THRESHOLD = 0.55  # Minimum final confidence score for candidate clip match
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
    paths_path = os.path.join(store_dir, "video_paths.npy")
    meta_path = os.path.join(store_dir, "frame_meta.npy")

    # 1. Extract Query Frames & Timestamps (1 frame every 1.5 seconds)
    query_items = extract_frames_with_timestamps(query_path, sample_interval_sec=1.5)
    if not query_items:
        return []

    frames = [it["frame"] for it in query_items]
    num_query_frames = len(frames)

    # 2. Extract DINOv2 384-dim visual embeddings for query keyframes
    query_embeds = embed_video_frames(frames)
    if query_embeds.size == 0:
        return []

    # 3. Pinecone Video Search (Query each query frame against indexed reference keyframes)
    video_matches = defaultdict(list)
    try:
        pinecone_video_store = get_pinecone_video_store()
        print("Querying Pinecone Video Database for DINOv2 keyframe visual matches...")

        for q_idx, q_item in enumerate(query_items):
            q_ts = q_item["timestamp"]
            q_embed = query_embeds[q_idx]

            matches = pinecone_video_store.query_frame_vector(q_embed, top_k=TOP_K_FRAME_NEIGHBORS)

            for m in matches:
                meta = m.get("metadata", {})
                ref_path = meta.get("video") or meta.get("filename", "")
                ref_ts = float(meta.get("timestamp", 0.0))
                score = float(m.get("score", 0.0))
                offset = round(ref_ts - q_ts, 1)

                # Strict frame similarity threshold
                if ref_path and score >= FRAME_SCORE_THRESHOLD:
                    video_matches[ref_path].append({
                        "q_ts": q_ts,
                        "ref_ts": ref_ts,
                        "score": score,
                        "offset": offset
                    })

    except Exception as e:
        print(f"Warning querying Pinecone for video search: {e}")
        return []

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

        # STRICT FALSE POSITIVE GUARD:
        # If query has multiple frames (>= 3), require at least 2 distinct temporal keyframes matched!
        # A single accidental 1-frame match in a multi-frame video will be rejected.
        if num_query_frames >= 3 and unique_q_matched < 2:
            print(f"Rejecting single-frame candidate match for {os.path.basename(ref_path)} (Matched {unique_q_matched}/{num_query_frames} frames)")
            continue

        # Weighted final score combining keyframe cosine similarity (70%) and clip coverage (30%)
        final_score = (0.70 * avg_cluster_score) + (0.30 * coverage)

        if final_score < MATCH_SCORE_THRESHOLD:
            continue

        ref_timestamps = [m["ref_ts"] for m in best_cluster]
        start_ts = min(ref_timestamps)
        end_ts = max(ref_timestamps)
        ts_range_str = f"{format_time(start_ts)} - {format_time(end_ts)}"

        verdict = "ORIGINAL SOURCE MATCH" if final_score >= 0.75 else "SUB-CLIP MATCH"

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

