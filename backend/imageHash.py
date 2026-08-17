import torch
import numpy as np
from pinecone_db import get_pinecone_store
import os
from PIL import Image
import torchvision.transforms as T
import imagehash
import cv2

def cropfinds(path1,path2):

    img_orig = cv2.imread(path1)
    img_crop = cv2.imread(path2)

    if img_orig is None or img_crop is None:
      return False

    gray1 = cv2.cvtColor(img_orig, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)


    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

# Check keypoints / descriptors
    if des1 is None or des2 is None:
        return False
      

# Ensure correct dtype (VERY IMPORTANT)
    des1 = des1.astype(np.float32)
    des2 = des2.astype(np.float32)

# BFMatcher for SIFT (L2 distance)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    matches = bf.knnMatch(des1, des2, k=2)

# Lowe ratio test
    good = []
    for pair in matches:
        m, n = pair
        if m.distance < 0.75 * n.distance:
            good.append(m)

# Minimum matches check
    if len(good) < 10:
        return False

# Extract matched points
    src_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    dst_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)

# Homography
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if H is None:
        return False

# Inlier check
    inliers = int(np.sum(mask))
    if inliers < 8:
        return False

    return True
def get_dino_tools(model_name="dinov2_vits14"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model = torch.hub.load("facebookresearch/dinov2", model_name)
    model = model.to(device)
    model.eval()

    # UPDATED TRANSFORM: GRAYSCALE (Color Blind Mode)
    # This matches the logic in your main.py
    transform = T.Compose([
        T.Resize((224, 224)),
        
        # This makes the AI "color blind" so it sees Dark/Light mode as the same.
        T.Grayscale(num_output_channels=3),
        
        T.ToTensor(),
        T.Normalize(
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225)
        ),
    ])

    return model, transform, device

print("Loading DINOv2 Model for Search...")
MODEL, TRANSFORM, DEVICE = get_dino_tools()
print("Search Model Loaded")


def embed_query_with_rotations(image_path, model, transform, device):
    """
    Generates 4 embeddings for the query image (0, 90, 180, 270 degrees).
    The transform will convert them to Grayscale automatically.
    """
    try:
        image = Image.open(image_path).convert("RGB")
        angles = [0, 90, 180, 270]

        vectors = []
        for angle in angles:
            # expand=True ensures we don't crop corners when rotating
            rotated = image.rotate(angle, expand=True)
            
            # Transform (includes Grayscale conversion and 224x224 resize)
            img_tensor = transform(rotated).unsqueeze(0).to(device)

            with torch.no_grad():
                features = model(img_tensor)
                features = torch.nn.functional.normalize(features, dim=-1)

            vectors.append(features.cpu().numpy())

        return np.vstack(vectors).astype("float32")  # Returns shape (4, 384)
    except Exception as e:
        print(f"Error rotating/embedding query: {e}")
        return np.array([])


def compute_phash(image_path):
    try:
        # UPDATED: Convert to Grayscale ('L') before hashing
        # This ensures the hash ignores color information completely
        img = Image.open(image_path).convert("L")
        return imagehash.phash(img)
    except:
        return None


def find_similar_images(query_image_path, store_dir="dinov2_pinecone_store"):
    if not os.path.exists(query_image_path):
        return {"error": "Query image not found."}

    query_hash = compute_phash(query_image_path)
    if query_hash is None:
        return {"error": "Failed to compute pHash."}

    # GENERATE 4 VECTORS (Original + 3 Rotations)
    query_vectors = embed_query_with_rotations(
        query_image_path, MODEL, TRANSFORM, DEVICE
    )
    
    if query_vectors.size == 0:
        return {"error": "Failed to process query image embeddings."}

    EXACT_MATCH_THR = 0.95
    NEAR_DUP_THR = 0.70

    def classify_score(s):
        if s >= EXACT_MATCH_THR: return "Exactly Same"
        if s >= NEAR_DUP_THR: return "Near Duplicate"
        return "Different"

    final_results_map = {} 
    path_map = {}

    try:
        pinecone_store = get_pinecone_store()
        print("Querying Pinecone Vector Database...")
        
        for qv in query_vectors:
            matches = pinecone_store.query_similar(qv, top_k=10)
            for m in matches:
                meta = m.get("metadata", {})
                filename = meta.get("filename") or m.get("id")
                img_path = meta.get("image_path", "")
                score = float(m.get("score", 0.0))
                
                if filename:
                    path_map[filename] = img_path
                    if filename in final_results_map:
                        final_results_map[filename] = max(final_results_map[filename], score)
                    else:
                        final_results_map[filename] = score
    except Exception as e:
        print(f"Pinecone query error: {e}")
        # Fallback to local numpy metadata cache if available
        paths_file = os.path.join(store_dir, "image_paths.npy")
        if os.path.exists(paths_file):
            print("Falling back to local numpy metadata cache...")
            image_files = np.load(paths_file, allow_pickle=True)
            image_hashes = np.load(os.path.join(store_dir, "image_hashes.npy"), allow_pickle=True)
            HASH_THRESHOLD = 12
            for i, h in enumerate(image_hashes):
                try:
                    stored_hash = imagehash.hex_to_hash(str(h))
                    if query_hash - stored_hash <= HASH_THRESHOLD:
                        fn = os.path.basename(image_files[i])
                        final_results_map[fn] = 0.85
                        path_map[fn] = image_files[i]
                except:
                    continue

    results = []
    sorted_matches = sorted(final_results_map.items(), key=lambda x: -x[1])
    maxi = 0

    for filename, score in sorted_matches:
        if score < 0.50: 
            continue
        maxi = max(maxi, score)

        results.append({
            "name": filename,
            "score": round(score, 4),
            "status": classify_score(score)
        })

    print(f"Max match score: {maxi}")    

    if maxi < 0.88 and sorted_matches:
        for filename, score in sorted_matches:
            path1 = path_map.get(filename, "")
            path2 = query_image_path
            if score < 0.4 or not os.path.exists(path1):
                continue
            res = cropfinds(path1, path2)
            print(f"Homography result for {filename}: {res}")
            
            if 0.6 <= score < 0.96:
                status = "Near Duplicate"
            elif score < 0.6:
                status = "This might match your image"
            else:
                status = "Exactly Same"

            if 0.4 <= score < 0.6:
                score = 0.8
            elif 0.6 <= score < 0.8:
                score = 0.85
            elif score >= 0.8:
                score = 0.96        
            
            if res:
                return [{
                    "name": filename,
                    "score": round(score, 4),
                    "status": status
                }]
            
    return results[:5]

if __name__ == "__main__":
    print(find_similar_images("uploads/query/test_image.jpg"))