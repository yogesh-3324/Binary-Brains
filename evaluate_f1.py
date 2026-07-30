import os
import re
from imageHash import find_similar_images
from main import process_reference_pool

# ----------------------------
# PATHS
# ----------------------------
ORIGINAL_DIR = "test_images/original"
QUERY_DIR = "test_images/query_images"

# ----------------------------
# STEP 1: TRAIN / INDEX ORIGINAL IMAGES
# ----------------------------
print("🚀 Indexing original images...")
process_reference_pool(ORIGINAL_DIR)

# ----------------------------
# STEP 2: EVALUATION
# ----------------------------
TP = 0
FP = 0
FN = 0

def get_gt_original(query_name):
    """
    Extract ground-truth original filename.
    Example: 20000_query2.jpg -> 20000.jpg
    """
    match = re.match(r"(\d+)_query", query_name)
    if match:
        return match.group(1) + ".jpg"
    return None

query_files = sorted(os.listdir(QUERY_DIR))

for q in query_files:
    q_path = os.path.join(QUERY_DIR, q)
    gt = get_gt_original(q)

    if gt is None:
        continue

    results = find_similar_images(q_path)

    if not results:
        # No result returned → FN
        FN += 1
        print(f"❌ FN: {q} (no match)")
        continue

    top_match = results[0]["name"]

    if top_match == gt:
        TP += 1
        print(f"✅ TP: {q} → {top_match}")
    else:
        FP += 1
        print(f"⚠️ FP: {q} → {top_match} (GT: {gt})")

# ----------------------------
# METRICS
# ----------------------------
precision = TP / (TP + FP) if (TP + FP) > 0 else 0
recall = TP / (TP + FN) if (TP + FN) > 0 else 0
f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

print("\n📊 FINAL RESULTS")
print(f"TP: {TP}")
print(f"FP: {FP}")
print(f"FN: {FN}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"F1 Score:  {f1:.4f}")
