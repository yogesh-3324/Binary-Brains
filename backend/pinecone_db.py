import os
import hashlib
from dotenv import load_dotenv, find_dotenv
from pinecone import Pinecone, ServerlessSpec

# Search up the folder hierarchy to locate .env in root or working directory
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

class PineconeVectorStore:
    """
    Pinecone Vector Store wrapper for managing image embeddings and metadata.
    """
    def __init__(self, index_name=None, dimension=384, metric="cosine"):
        self._custom_index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self._client = None
        self._index = None

    @property
    def api_key(self):
        # Reload dynamically from environment in case .env was edited after import
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
        return os.getenv("PINECONE_API_KEY", "").strip()

    @property
    def index_name(self):
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=True)
        return self._custom_index_name or os.getenv("PINECONE_IMAGE_INDEX", os.getenv("PINECONE_INDEX_NAME", "image-search-index")).strip()

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
            existing_indexes = [idx.name for idx in self._client.list_indexes()]
            if idx_name not in existing_indexes:
                print(f"[Pinecone] Index '{idx_name}' not found in your account. Creating (dim={self.dimension}, metric={self.metric})...")
                try:
                    self._client.create_index(
                        name=idx_name,
                        dimension=self.dimension,
                        metric=self.metric,
                        spec=ServerlessSpec(cloud="aws", region="us-east-1")
                    )
                    print(f"[Pinecone] Created index '{idx_name}' successfully.")
                except Exception as e:
                    print(f"[Pinecone] Warning creating index '{idx_name}': {e}. Attempting direct connection...")
        except Exception as e:
            print(f"[Pinecone] Warning checking index list: {e}")

        self._index = self._client.Index(idx_name)
        return self._index

    @staticmethod
    def generate_vector_id(image_path: str) -> str:
        """Generates a stable, unique ID for a file path using md5 hash."""
        filename = os.path.basename(image_path)
        return hashlib.md5(filename.encode("utf-8")).hexdigest()

    def upsert_image_vector(self, image_path: str, vector: list, phash_str: str):
        """Upserts a single image embedding with metadata to Pinecone."""
        vector_id = self.generate_vector_id(image_path)
        values = vector.tolist() if hasattr(vector, "tolist") else vector
        metadata = {
            "image_path": image_path,
            "filename": os.path.basename(image_path),
            "phash": str(phash_str)
        }
        idx = self.get_index()
        idx.upsert(vectors=[(vector_id, values, metadata)])
        print(f"[Pinecone] Upserted vector ID {vector_id} for file {os.path.basename(image_path)}")
        return vector_id

    def upsert_image_vectors_batch(self, image_paths: list, vectors: list, phash_strs: list):
        """Upserts a batch of image embeddings with metadata to Pinecone."""
        if len(image_paths) == 0:
            return []

        records = []
        ids = []
        for path, vec, phash in zip(image_paths, vectors, phash_strs):
            vector_id = self.generate_vector_id(path)
            values = vec.tolist() if hasattr(vec, "tolist") else vec
            metadata = {
                "image_path": path,
                "filename": os.path.basename(path),
                "phash": str(phash)
            }
            records.append((vector_id, values, metadata))
            ids.append(vector_id)

        idx = self.get_index()
        idx.upsert(vectors=records)
        print(f"[Pinecone] Upserted batch of {len(records)} vectors into index '{self.index_name}'")
        return ids

    def query_similar(self, query_vector: list, top_k: int = 10, filter_dict: dict = None):
        """Queries Pinecone for nearest neighbor embeddings."""
        idx = self.get_index()
        values = query_vector.tolist() if hasattr(query_vector, "tolist") else query_vector
        response = idx.query(
            vector=values,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )
        return response.get("matches", [])

    def fetch_all_metadata(self):
        """
        Fetches metadata for stored vectors.
        Uses stats / sample or vector list if available.
        """
        idx = self.get_index()
        stats = idx.describe_index_stats()
        return stats

    def delete_by_filename(self, filename: str):
        """Deletes a vector corresponding to a specific filename."""
        vector_id = hashlib.md5(filename.encode("utf-8")).hexdigest()
        idx = self.get_index()
        idx.delete(ids=[vector_id])
        print(f"[Pinecone] Deleted vector ID {vector_id} ({filename})")
        return True

    def delete_all(self):
        """Clears all vectors from the index."""
        try:
            idx = self.get_index()
            idx.delete(delete_all=True)
            print(f"[Pinecone] Cleared all vectors from index '{self.index_name}'")
        except Exception as e:
            if "404" in str(e) or "Namespace not found" in str(e) or "Not Found" in str(e):
                print(f"[Pinecone] Index '{self.index_name}' is already clean.")
            else:
                print(f"[Pinecone] Warning clearing index: {e}")
        return True

# Global instance helper
_pinecone_store = None

def get_pinecone_store():
    global _pinecone_store
    if _pinecone_store is None:
        _pinecone_store = PineconeVectorStore()
    return _pinecone_store
