# SameShot: Duplicate Image and Video Detection System

SameShot (Binary-Brains) is a high-performance content duplicate detection system built for finding exact, cropped, scaled, color-adjusted, and temporal sub-clip duplicates across large media databases. 

The system leverages deep feature representation via DINOv2 for images and binary perceptual hashing (pHash) with FAISS spatial and temporal alignment for ultra-fast, scalable video duplicate retrieval.

---

## Overview

Modern media platforms process massive volumes of visual content where duplicate or near-duplicate detection is critical for content moderation, copyright enforcement, and storage optimization. SameShot provides a microservices-based architecture that addresses two core challenges:

1. **Image Duplicate Retrieval**: High-precision vector similarity search using Vision Transformer embeddings (DINOv2 Small / `dinov2_vits14`) indexed in FAISS with complementary perceptual hashing.
2. **Video Duplicate & Sub-Clip Retrieval**: Perceptual video frame fingerprinting packed into 64-bit binary vectors, indexed using binary Hamming distance in FAISS with temporal offset consensus clustering for exact sub-clip timestamp detection.

---

## Architecture and Microservices

The repository is structured as a multi-tier microservices application:

```
[ Frontend (React + Vite + Tailwind) ]
         |                         |
         v (Port 8000)             v (Port 8001)
[ Image Service (backend/) ]  [ Video Service (backend2/) ]
  - DINOv2 (384-dim)            - Frame pHash (64-bit binary)
  - FAISS IndexFlatIP           - FAISS IndexBinaryFlat
  - Perceptual Hashing          - Temporal Alignment Search
```

### 1. Image Duplicate Detection Service (`backend/`)
- **Model**: DINOv2 (`dinov2_vits14`) self-supervised Vision Transformer.
- **Embedding Dimensionality**: 384 dimensions (L2-normalized).
- **Index Type**: FAISS `IndexFlatIP` (Inner Product / Cosine Similarity).
- **Fallback / Hybrid Engine**: Perceptual Hash (pHash) filtering via `imagehash`.
- **API Port**: `8000`

### 2. Video Duplicate & Sub-Clip Retrieval Service (`backend2/`)
- **Frame Extraction**: Hardware-accelerated direct seeking via OpenCV (1 frame per 1.5s - 2.0s).
- **Fingerprinting**: 64-bit frame pHash converted into packed 8-byte `uint8` binary vectors.
- **Index Type**: FAISS `IndexBinaryFlat(64)` for hardware-accelerated Hamming distance computation.
- **Temporal Alignment**: Offset consensus binning to detect temporal alignment windows and sub-clip ranges within longer reference videos.
- **API Port**: `8001`

### 3. Frontend Web Interface (`frontend/`)
- Built with React 19, TypeScript, Vite, and TailwindCSS.
- Real-time video previewing, timestamp match visualization, confidence breakdown, and pool upload management.

---

## Technology Stack

- **Core Backend Framework**: Python 3.12, FastAPI, Uvicorn
- **Computer Vision & ML**: PyTorch, OpenCV, DINOv2, ImageHash
- **Vector Search Engine**: FAISS (Facebook AI Similarity Search - CPU/GPU)
- **Frontend Framework**: React 19, TypeScript, Vite, TailwindCSS
- **Containerization**: Docker, Docker Compose

---

## Directory Structure

```
ndid/
├── backend/                  # Image Duplicate Detection Microservice
│   ├── main.py               # Frame index processing and DINOv2 feature store management
│   ├── search_image.py       # Vector retrieval and similarity ranking
│   ├── server.py             # FastAPI endpoints for image upload, search, and reset
│   ├── imageHash.py          # Perceptual hash utility functions
│   └── Dockerfile            # Container configuration for image backend
│
├── backend2/                 # Video Duplicate & Sub-Clip Microservice
│   ├── main.py               # Video index builder (FAISS IndexBinaryFlat)
│   ├── search_video.py       # Frame matching and temporal consensus clustering
│   ├── server.py             # FastAPI endpoints for video pool upload, query, and analysis
│   ├── utils.py              # Frame extraction and pHash calculation utilities
│   └── Dockerfile            # Container configuration for video backend
│
├── frontend/                 # React Web Application
│   ├── src/
│   │   ├── pages/            # Views for DuplicateImg.tsx and DuplicateVid.tsx
│   │   └── components/       # Layout, Navigation, and Card UI elements
│   ├── package.json
│   └── Dockerfile            # NGINX container configuration for frontend production
│
├── docker-compose.yml        # Orchestration manifest for all microservices
└── README.md                 # Project documentation
```

---

## How It Works: Algorithms and Techniques

### Image Duplicate Detection Pipeline
1. **Preprocessing**: Images are converted to RGB, resized to 224x224, and normalized using ImageNet statistics.
2. **Feature Extraction**: Passed through `dinov2_vits14` to produce a 384-dimensional feature vector.
3. **FAISS Indexing**: Normalized feature vectors are added to a FAISS `IndexFlatIP` index.
4. **Query & Scoring**: Cosine similarity is computed against indexed vectors. A configurable threshold (default `0.70`) identifies exact and modified duplicates.

### Video Duplicate Detection & Sub-Clip Alignment
1. **Keyframe Extraction**: OpenCV extracts frames at fixed time intervals (default 1.5s to 2.0s) using direct frame position seeking.
2. **Binary Hashing**: Each keyframe is transformed into a 64-bit Discrete Cosine Transform (DCT) perceptual hash (`imagehash.phash`), packed into 8 `uint8` bytes.
3. **Binary FAISS Search**: Frame hashes are queried against a `faiss.IndexBinaryFlat(64)` index to retrieve $K$ nearest neighbors by Hamming distance.
4. **Hamming Distance Thresholding**: Candidate neighbor frames with Hamming distance $\le 15$ bits out of 64 are accepted as frame-level matches.
5. **Temporal Consensus Clustering**:
   - For each matching frame pair (Query timestamp $t_q$, Reference timestamp $t_r$), the temporal offset is computed: $\Delta t = t_r - t_q$.
   - Offsets are grouped into 1.5-second sliding tolerance windows.
   - The cluster with the highest density of consistent temporal offsets defines the aligned video clip match.
6. **Scoring & Timestamp Range**: The final clip score combines normalized frame similarity and clip coverage:
   $$\text{Final Score} = 0.6 \times \text{Average Cluster Score} + 0.4 \times \left(\frac{\text{Unique Matched Query Frames}}{\text{Total Query Frames}}\right)$$

---

## API Reference

### Image Backend (`http://localhost:8000`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload/pool` | Upload reference image files to the reference pool |
| `POST` | `/upload/query` | Upload a query image to search for duplicates |
| `GET` | `/analyze` | Run vector search and return top matching duplicate images |
| `POST` | `/reset` | Clear stored images and reset the FAISS index |
| `DELETE` | `/delete/pool/{filename}` | Remove a single image from the pool and vector store |

### Video Backend (`http://localhost:8001`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload/pool` | Upload reference video files (`.mp4`, `.avi`, `.mov`, `.mkv`) |
| `POST` | `/upload/query` | Upload a query video clip |
| `GET` | `/analyze` | Extract keyframe hashes, run binary FAISS search, perform temporal consensus, and return matches with timestamp ranges |
| `POST` | `/reset` | Clear stored reference videos and reset the binary index |
| `DELETE` | `/delete/pool/{filename}` | Remove a video from the index and filesystem |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.12+ (for local manual execution)
- Node.js 18+ and npm (for local frontend execution)

### Option 1: Running with Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yogesh-3324/SameShot.git
   cd SameShot
   ```

2. Build and start all microservices:
   ```bash
   docker-compose up --build
   ```

3. Open your browser and navigate to:
   - Frontend UI: `http://localhost:80`
   - Image API Docs: `http://localhost:8000/docs`
   - Video API Docs: `http://localhost:8001/docs`

---

### Option 2: Running Locally (Manual Setup)

#### 1. Start Image Backend (Port 8000)
```bash
cd backend
pip install -r requirements.txt
python server.py
```

#### 2. Start Video Backend (Port 8001)
```bash
cd backend2
pip install -r requirements.txt
python server.py
```

#### 3. Start Frontend (Port 5173)
```bash
cd frontend
npm install
npm run dev
```

Access the frontend at `http://localhost:5173`.

---

## License

This project is licensed under the MIT License.