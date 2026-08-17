# search_video.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
try:
    from pinecone_db import get_pinecone_video_store
except (ImportError, AttributeError):
    from backend2.pinecone_db import get_pinecone_video_store
from collections import defaultdict
from utils import extract_frames_with_timestamps, embed_video_frames, hash_frames, compute_hamming_matrix

# =====================================================
# CONFIG
# =====================================================
SAMPLE_FPS = 1
PHASH_HAMMING_THRESHOLD = 18  # Maximum Hamming distance for Stage 1 pHash candidate match
STAGE1_TOP_K_VIDEOS = 15      # Maximum top candidate videos selected from Stage 1
FRAME_SCORE_THRESHOLD = 0.70  # Minimum DINOv2 visual similarity for keyframe match
MATCH_SCORE_THRESHOLD = 0.55  # Minimum final confidence score for candidate clip match
TOP_K_FRAME_NEIGHBORS = 5

def format_time(seconds: float) -> str:
    secs = max(0, int(round(seconds)))
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins:02d}:{rem_secs:02d}"

# =====================================================
# 2-STAGE SUB-CLIP RETRIEVAL LOGIC
# =====================================================
def find_similar_videos(query_path: str, store_dir: str):
    paths_path = os.path.join(store_dir, "video_paths.npy")
    meta_path = os.path.join(store_dir, "frame_meta.npy")
    hashes_path = os.path.join(store_dir, "frame_hashes.npy")

    # 1. Extract Query Frames & Timestamps (1 frame every 1.5 seconds)
    query_items = extract_frames_with_timestamps(query_path, sample_interval_sec=1.5)
    if not query_items:
        return []

    frames = [it["frame"] for it in query_items]
    num_query_frames = len(frames)

    # -----------------------------------------------------
    # STAGE 1: pHash Coarse Filter
    # -----------------------------------------------------
    filter_dict = None
    stage1_candidate_filenames = []

    if os.path.exists(hashes_path) and os.path.exists(meta_path):
        try:
            query_hashes = hash_frames(frames)  # (N, 8) uint8
            ref_hashes_list = np.load(hashes_path, allow_pickle=True)
            frame_meta_list = np.load(meta_path, allow_pickle=True)

            if len(ref_hashes_list) > 0 and len(ref_hashes_list) == len(frame_meta_list):
                ref_hashes = np.vstack(ref_hashes_list).astype(np.uint8)  # (M, 8) uint8
                
                # Compute pairwise Hamming distance matrix (N, M)
                dist_matrix = compute_hamming_matrix(query_hashes, ref_hashes)

                video_match_counts = defaultdict(int)
                for q_idx in range(len(query_hashes)):
                    matched_indices = np.where(dist_matrix[q_idx] <= PHASH_HAMMING_THRESHOLD)[0]
                    for ref_idx in matched_indices:
                        meta = frame_meta_list[ref_idx]
                        ref_fname = os.path.basename(meta["video"])
                        video_match_counts[ref_fname] += 1

                if video_match_counts:
                    # Rank candidates by pHash keyframe match count
                    sorted_candidates = sorted(video_match_counts.items(), key=lambda x: x[1], reverse=True)
                    stage1_candidate_filenames = [fname for fname, _ in sorted_candidates[:STAGE1_TOP_K_VIDEOS]]
                    print(f"[Stage 1: pHash Coarse Filter] Found {len(stage1_candidate_filenames)} candidate videos out of {len(set(os.path.basename(m['video']) for m in frame_meta_list))} total.")
                    filter_dict = {"filename": {"$in": stage1_candidate_filenames}}
                else:
                    print("[Stage 1: pHash Coarse Filter] No candidates passed pHash threshold. Falling back to full search.")
        except Exception as e:
            print(f"Warning in Stage 1 pHash Coarse Filter: {e}")

    # -----------------------------------------------------
    # STAGE 2: DINOv2 Fine Alignment & Temporal Consensus
    # -----------------------------------------------------
    query_embeds = embed_video_frames(frames)
    if query_embeds.size == 0:
        return []

    video_matches = defaultdict(list)
    try:
        pinecone_video_store = get_pinecone_video_store()
        search_scope = f"filtered {len(stage1_candidate_filenames)} Stage-1 candidate(s)" if filter_dict else "all reference videos"
        print(f"[Stage 2: DINOv2 Fine Alignment] Querying Pinecone for DINOv2 keyframe matches across {search_scope}...")

        for q_idx, q_item in enumerate(query_items):
            q_ts = q_item["timestamp"]
            q_embed = query_embeds[q_idx]

            matches = pinecone_video_store.query_frame_vector(
                q_embed,
                top_k=TOP_K_FRAME_NEIGHBORS,
                filter_dict=filter_dict
            )

            for m in matches:
                meta = m.get("metadata", {})
                ref_path = meta.get("video") or meta.get("filename", "")
                ref_ts = float(meta.get("timestamp", 0.0))
                score = float(m.get("score", 0.0))
                offset = round(ref_ts - q_ts, 1)

                if ref_path and score >= FRAME_SCORE_THRESHOLD:
                    video_matches[ref_path].append({
                        "q_ts": q_ts,
                        "ref_ts": ref_ts,
                        "score": score,
                        "offset": offset
                    })

    except Exception as e:
        print(f"Warning querying Pinecone in Stage 2 fine search: {e}")
        return []

    # Temporal Offset Consensus Clustering per candidate video
    candidate_results = []

    for ref_path, matches in video_matches.items():
        if not matches:
            continue

        offset_clusters = defaultdict(list)
        for m in matches:
            bin_key = round(m["offset"] / 1.5) * 1.5
            offset_clusters[bin_key].append(m)

        best_cluster = max(
            offset_clusters.values(),
            key=lambda cluster: (len({m["q_ts"] for m in cluster}), sum(m["score"] for m in cluster))
        )

        unique_q_matched = len({m["q_ts"] for m in best_cluster})
        avg_cluster_score = sum(m["score"] for m in best_cluster) / len(best_cluster)
        coverage = unique_q_matched / num_query_frames

        if num_query_frames >= 3 and unique_q_matched < 2:
            print(f"Rejecting single-frame candidate match for {os.path.basename(ref_path)} (Matched {unique_q_matched}/{num_query_frames} frames)")
            continue

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

    candidate_results.sort(key=lambda x: x["hash_score"], reverse=True)

    for rank, res in enumerate(candidate_results[:5], 1):
        res["rank"] = rank

    return candidate_results[:5]

