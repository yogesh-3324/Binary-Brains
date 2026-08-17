import os
import hashlib
from dotenv import load_dotenv, find_dotenv
from pinecone import Pinecone, ServerlessSpec
import numpy as np

dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

class PineconeVideoStore:
    """
    Pinecone Vector Store wrapper for managing DINOv2 video frame visual embeddings and pHash metadata.
    """
    def __init__(self, index_name=None, dimension=384, metric="cosine"):
        self._custom_index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self._client = None
        self._index = None

    @property
    def api_key(self):
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
        return os.getenv("PINECONE_API_KEY", "").strip()

    @property
    def index_name(self):
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
        return self._custom_index_name or os.getenv("PINECONE_VIDEO_INDEX", "video-search-index").strip()

    def get_index(self):
        if self._index is not None:
            return self._index

        key = self.api_key
        idx_name = self.index_name

        if not key:
            raise ValueError(
                "PINECONE_API_KEY is missing or empty. Please add PINECONE_API_KEY=your_key to your .env file."
            )

        self._client = Pinecone(api_key=key)

        try:
            existing_indexes = self._client.list_indexes()
            existing_names = [idx.name for idx in existing_indexes]
            if idx_name in existing_names:
                # Check if existing index has the correct dimension
                idx_info = next(idx for idx in existing_indexes if idx.name == idx_name)
                existing_dim = getattr(idx_info, 'dimension', None)
                if existing_dim is not None and existing_dim != self.dimension:
                    print(f"[Pinecone Video] Index '{idx_name}' has dimension {existing_dim}, but expected {self.dimension}. Deleting and recreating...")
                    try:
                        self._client.delete_index(idx_name)
                        import time
                        time.sleep(5)  # Wait for deletion to propagate
                    except Exception as e:
                        print(f"[Pinecone Video] Warning deleting stale index: {e}")
                    existing_names = []  # Force recreation below

            if idx_name not in existing_names:
                print(f"[Pinecone Video] Index '{idx_name}' not found. Creating (dim={self.dimension}, metric={self.metric})...")
                try:
                    self._client.create_index(
                        name=idx_name,
                        dimension=self.dimension,
                        metric=self.metric,
                        spec=ServerlessSpec(cloud="aws", region="us-east-1")
                    )
                    import time
                    time.sleep(5)  # Wait for index to be ready
                    print(f"[Pinecone Video] Created index '{idx_name}' successfully.")
                except Exception as e:
                    print(f"[Pinecone Video] Warning creating index '{idx_name}': {e}")
        except Exception as e:
            print(f"[Pinecone Video] Warning checking index list: {e}")

        self._index = self._client.Index(idx_name)
        return self._index

    @staticmethod
    def generate_frame_id(video_path: str, frame_idx: int) -> str:
        """Generates a stable, unique ID for a video frame."""
        filename = os.path.basename(video_path)
        key = f"{filename}_{frame_idx}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def upsert_frame_vectors_batch(self, video_path: str, frame_items: list, embeds: np.ndarray, phash_list: list = None):
        """
        video_path: path to the video file
        frame_items: list of dicts with {"timestamp": float, "frame_idx": int}
        embeds: np.ndarray float32 of shape (N, 384) DINOv2 embeddings
        phash_list: optional list of phash strings
        """
        if len(frame_items) == 0 or embeds.size == 0:
            return []

        records = []
        ids = []

        for i, (item, vec) in enumerate(zip(frame_items, embeds)):
            v_id = self.generate_frame_id(video_path, item["frame_idx"])
            phash_val = str(phash_list[i]) if phash_list and i < len(phash_list) else ""
            metadata = {
                "video": video_path,
                "filename": os.path.basename(video_path),
                "timestamp": float(item["timestamp"]),
                "frame_idx": int(item["frame_idx"]),
                "phash": phash_val
            }
            records.append((v_id, vec.tolist(), metadata))
            ids.append(v_id)

        idx = self.get_index()
        # Upsert in chunks of 100 to avoid request size limits
        chunk_size = 100
        for i in range(0, len(records), chunk_size):
            idx.upsert(vectors=records[i : i + chunk_size])

        print(f"[Pinecone Video] Upserted {len(records)} frame vectors into index '{self.index_name}'")
        return ids

    def query_frame_vector(self, query_embed: np.ndarray, top_k: int = 10, filter_dict: dict = None):
        """Queries Pinecone for nearest DINOv2 keyframe embeddings with optional metadata filter."""
        idx = self.get_index()
        values = query_embed.tolist() if hasattr(query_embed, "tolist") else query_embed
        query_kwargs = {
            "vector": values,
            "top_k": top_k,
            "include_metadata": True
        }
        if filter_dict:
            query_kwargs["filter"] = filter_dict
        response = idx.query(**query_kwargs)
        return response.get("matches", [])

    def delete_by_video_filename(self, filename: str):
        """Deletes all frame vectors matching a video filename using metadata filter."""
        idx = self.get_index()
        try:
            idx.delete(filter={"filename": {"$eq": filename}})
            print(f"[Pinecone Video] Deleted frame vectors for video '{filename}'")
            return True
        except Exception as e:
            print(f"[Pinecone Video] Warning deleting vectors by filename: {e}")
            return False

    def delete_all(self):
        """Clears all video frame vectors from the index."""
        try:
            idx = self.get_index()
            idx.delete(delete_all=True)
            print(f"[Pinecone Video] Cleared all frame vectors from index '{self.index_name}'")
        except Exception as e:
            if "404" in str(e) or "Namespace not found" in str(e) or "Not Found" in str(e):
                print(f"[Pinecone Video] Index '{self.index_name}' is already clean.")
            else:
                print(f"[Pinecone Video] Warning clearing index: {e}")
        return True

_pinecone_video_store = None

def get_pinecone_video_store():
    global _pinecone_video_store
    if _pinecone_video_store is None:
        _pinecone_video_store = PineconeVideoStore()
    return _pinecone_video_store
