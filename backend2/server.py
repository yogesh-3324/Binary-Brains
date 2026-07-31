# server.py
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import shutil
import glob
import stat
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool

from main import process_reference_pool, remove_video_from_index
from search_video import find_similar_videos

# =====================================================
# APP SETUP
# =====================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# DIRECTORIES
# =====================================================
UPLOAD_DIR = "uploads"
POOL_DIR = os.path.join(UPLOAD_DIR, "pool")
QUERY_DIR = os.path.join(UPLOAD_DIR, "query")
STORE_DIR = "dinov2_video_store"

os.makedirs(POOL_DIR, exist_ok=True)
os.makedirs(QUERY_DIR, exist_ok=True)
os.makedirs(STORE_DIR, exist_ok=True)

app.mount("/videos", StaticFiles(directory="uploads"), name="videos")

ALLOWED_EXT = {".mp4", ".avi", ".mov", ".mkv"}

# =====================================================
# HELPER: WINDOWS-SAFE DELETE
# =====================================================
def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.
    If the error is because the file is open, it ignores it.
    """
    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        print(f"Warning: Could not delete {path}. File might be in use.")

# =====================================================
# RESET (FIXED)
# =====================================================
@app.post("/reset")
def reset_backend():
    # 1. Clear Uploads
    for folder in [POOL_DIR, QUERY_DIR]:
        for f in glob.glob(os.path.join(folder, "*")):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Could not remove {f}: {e}")

    # 2. Clear Vector Store (Windows Safe)
    if os.path.exists(STORE_DIR):
        try:
            # Try to remove the whole tree
            shutil.rmtree(STORE_DIR, onerror=on_rm_error)
        except Exception as e:
            print(f"Standard rmtree failed, trying manual file deletion: {e}")
            # Fallback: Delete files individually if folder is locked
            for f in glob.glob(os.path.join(STORE_DIR, "*")):
                try:
                    os.remove(f)
                except:
                    pass

    os.makedirs(STORE_DIR, exist_ok=True)
    return {"status": "cleared"}


# =====================================================
# UPLOAD POOL VIDEOS
# =====================================================
@app.post("/upload/pool")
async def upload_pool(files: List[UploadFile] = File(...)):
    saved = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            continue # Skip invalid files instead of crashing

        path = os.path.join(POOL_DIR, file.filename)
        
        # Write file
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(file.filename)

        await file.close()

    return {"added": saved, "count": len(saved)}


# =====================================================
# DELETE POOL VIDEO
# =====================================================
@app.delete("/delete/pool/{filename}")
def delete_pool_video(filename: str):
    path = os.path.join(POOL_DIR, filename)
    disk_deleted = False

    if os.path.exists(path):
        try:
            os.remove(path)
            disk_deleted = True
        except PermissionError:
            raise HTTPException(500, "File is locked by Windows. Try restarting server.")

    index_updated = remove_video_from_index(filename)

    if disk_deleted or index_updated:
        return {
            "status": "deleted",
            "disk_deleted": disk_deleted,
            "index_updated": index_updated
        }

    raise HTTPException(404, "Video not found")


# =====================================================
# UPLOAD QUERY VIDEO
# =====================================================
@app.post("/upload/query")
async def upload_query(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Unsupported video format")

    # Clear old query files first
    for f in glob.glob(os.path.join(QUERY_DIR, "*")):
        try:
            os.remove(f)
        except:
            pass

    path = os.path.join(QUERY_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    await file.close()
    return {"status": "updated", "file": file.filename}


# =====================================================
# ANALYZE
# =====================================================
@app.get("/analyze")
async def trigger_analysis():
    query_files = glob.glob(os.path.join(QUERY_DIR, "*"))
    if not query_files:
        raise HTTPException(400, "No query video found")

    query_path = query_files[0]

    # Index new files if any
    try:
        train_status = process_reference_pool(POOL_DIR)
    except Exception as e:
        print(f"Indexing Error: {e}")
        # Continue anyway, maybe index is already good

    # Run Search
    matches = await run_in_threadpool(
        find_similar_videos,
        query_path,
        STORE_DIR
    )

    return {"results": matches}


# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host=host, port=port)