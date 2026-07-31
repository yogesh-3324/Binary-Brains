import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { LogoBrand } from "../components/Logo";

// ---------------- CONFIG ----------------
const API_BASE = (import.meta.env.VITE_VIDEO_API_URL || "http://localhost:8001").replace(/\/+$/, "");

// ---------------- TYPES ----------------
type Result = {
  name: string;
  score: number;
  status: string;
  confidence: string;
  timestamp_range?: string;
  matched_frames?: string;
};

type VideoPreview = {
  id: string;
  file: File;
  preview: string;
  name: string;
};

// ---------------- ICONS ----------------
const Icons = {
  Back: () => (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  ),
  Upload: () => (
    <svg className="w-12 h-12 text-indigo-500 mb-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  Trash: () => (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6"></polyline>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
    </svg>
  ),
  Film: () => (
    <svg className="w-10 h-10 text-indigo-500 mb-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
      <line x1="7" y1="2" x2="7" y2="22" />
      <line x1="17" y1="2" x2="17" y2="22" />
      <line x1="2" y1="12" x2="22" y2="12" />
    </svg>
  ),
  Video: () => (
    <svg className="w-8 h-8 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
      <line x1="7" y1="2" x2="7" y2="22"></line>
      <line x1="17" y1="2" x2="17" y2="22"></line>
      <line x1="2" y1="12" x2="22" y2="12"></line>
    </svg>
  ),
  Check: () => (
    <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  )
};

// ---------------- COMPONENT ----------------
const DuplicateVid = () => {
  const [poolVideos, setPoolVideos] = useState<VideoPreview[]>([]);
  const [queryVideo, setQueryVideo] = useState<VideoPreview | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  
  // UI States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // RESET FUNCTION
  const resetBackend = async () => {
    try {
      await fetch(`${API_BASE}/reset`, { method: "POST" });
      setPoolVideos([]);
      setQueryVideo(null);
      setResults([]);
      setError(null);
    } catch (err) {
      console.error("Backend offline", err);
      setError("Could not connect to analysis server. Is it running?");
    }
  };

  // 1. CLEANUP & INIT
  useEffect(() => {
    resetBackend();

    return () => {
      poolVideos.forEach(v => URL.revokeObjectURL(v.preview));
      if (queryVideo) URL.revokeObjectURL(queryVideo.preview);
    };
  }, []);

  // 2. HANDLERS
  const processFiles = async (files: File[]) => {
    const validFiles = files.filter(f => f.type.startsWith("video/"));
    if (!validFiles.length) return;

    setIsUploading(true);
    setError(null);
    try {
      const fd = new FormData();
      validFiles.forEach(f => fd.append("files", f));
      
      const res = await fetch(`${API_BASE}/upload/pool`, { method: "POST", body: fd });
      if (!res.ok) throw new Error("Upload failed");

      const newVideos = validFiles.map(f => ({
        id: Math.random().toString(36).substr(2, 9),
        file: f,
        preview: URL.createObjectURL(f),
        name: f.name,
      }));

      setPoolVideos(prev => [...prev, ...newVideos]);
    } catch (err) {
      setError("Failed to upload reference videos.");
    } finally {
      setIsUploading(false);
    }
  };

  const handlePoolUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) processFiles(Array.from(e.target.files));
    e.target.value = ""; 
  };

  const removePoolVideo = async (id: string, name: string) => {
    try {
      await fetch(`${API_BASE}/delete/pool/${name}`, { method: "DELETE" });
      setPoolVideos(prev => {
        const target = prev.find(v => v.id === id);
        if (target) URL.revokeObjectURL(target.preview); 
        return prev.filter(v => v.id !== id);
      });
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  const handleQueryUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    
    if (queryVideo) URL.revokeObjectURL(queryVideo.preview);
    setResults([]); 

    try {
      const fd = new FormData();
      fd.append("file", file);
      await fetch(`${API_BASE}/upload/query`, { method: "POST", body: fd });

      setQueryVideo({
        id: "query",
        file,
        preview: URL.createObjectURL(file),
        name: file.name,
      });
    } catch (err) {
      setError("Failed to upload query video.");
    }
    e.target.value = "";
  };

  const removeQueryVideo = async () => {
    try {
      await fetch(`${API_BASE}/delete/query`, { method: "DELETE" });
      if (queryVideo) URL.revokeObjectURL(queryVideo.preview);
      setQueryVideo(null);
      setResults([]);
    } catch (err) {
      console.error("Failed to delete query video", err);
    }
  };

  const analyze = async () => {
    if (!queryVideo || poolVideos.length === 0) {
      setError("Please upload both reference videos and a query video.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/analyze`);
      const data = await res.json();
      
      const mappedResults: Result[] = (data.results || []).map((r: any) => ({
        name: r.video,
        score: r.hash_score ?? r.dino_score ?? r.clip_score ?? r.score ?? 0,
        status: r.verdict ?? "MATCH",
        confidence: r.confidence ?? `${((r.hash_score ?? r.dino_score ?? 0) * 100).toFixed(1)}%`,
        timestamp_range: r.timestamp_range,
        matched_frames: r.matched_frames
      }));

      setResults(mappedResults.sort((a, b) => b.score - a.score));
    } catch (err) {
      setError("Analysis failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getStatusColor = (status: string) => {
    if (status.includes("ORIGINAL")) return "bg-green-100 text-green-800 border-green-200";
    if (status.includes("SUB-CLIP")) return "bg-indigo-100 text-indigo-800 border-indigo-200";
    if (status.includes("MATCH")) return "bg-yellow-100 text-yellow-800 border-yellow-200";
    return "bg-slate-100 text-slate-600 border-slate-200";
  };

  const getScoreColor = (score: number) => {
    if (score > 0.75) return "bg-green-500";
    if (score > 0.55) return "bg-indigo-500";
    if (score > 0.40) return "bg-yellow-500";
    return "bg-slate-400";
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans antialiased text-slate-900 pb-12">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition">
              <Icons.Back />
            </Link>
            <div className="h-6 w-px bg-slate-200" />
            <Link to="/">
              <LogoBrand textClassName="text-lg font-bold tracking-tight text-slate-900" />
            </Link>
            <span className="text-slate-300">|</span>
            <h1 className="text-sm font-semibold text-slate-600 hidden sm:block">
              Sub-Clip Video Search
            </h1>
          </div>
          <button 
            onClick={resetBackend}
            className="flex items-center gap-2 text-xs font-semibold bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 px-3 py-1.5 rounded-lg transition"
          >
            <Icons.Trash /> Reset All
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="font-bold text-rose-800">×</button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <section className="lg:col-span-8 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-800">Reference Video Library</h2>
                <p className="text-xs text-slate-500">Original source videos stored in FAISS frame-level index</p>
              </div>
              <span className="text-xs font-semibold bg-indigo-50 text-indigo-600 px-2.5 py-1 rounded-full">
                {poolVideos.length} Uploaded
              </span>
            </div>

            <label className="border-2 border-dashed border-slate-300 hover:border-indigo-500 bg-white hover:bg-indigo-50/20 rounded-2xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-200 group text-center shadow-xs">
              <input type="file" multiple accept="video/mp4,video/avi,video/mov,video/mkv" onChange={handlePoolUpload} className="hidden" />
              <Icons.Upload />
              <span className="font-bold text-slate-700 group-hover:text-indigo-600 transition-colors">
                {isUploading ? "Uploading reference videos..." : "Click to add full reference videos"}
              </span>
              <span className="text-xs text-slate-400 mt-1">MP4, AVI, MOV, MKV formats</span>
            </label>

            {poolVideos.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6">
                {poolVideos.map((video) => (
                  <div key={video.id} className="group relative bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs hover:shadow-md transition">
                    <video src={video.preview} className="w-full h-32 object-cover bg-black" controls={false} />
                    <div className="p-2.5 flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-slate-700 truncate" title={video.name}>{video.name}</span>
                      <button onClick={() => removePoolVideo(video.id, video.name)} className="text-slate-400 hover:text-rose-600 p-1 rounded transition">
                        <Icons.Trash />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="lg:col-span-4 space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
              <h2 className="text-lg font-bold text-slate-800 mb-1">Edited Clip / Reel Query</h2>
              <p className="text-xs text-slate-500 mb-4">Upload an edited clip or meme video to find its original source</p>

              {queryVideo ? (
                <div className="relative bg-slate-900 rounded-xl overflow-hidden group">
                  <video src={queryVideo.preview} controls className="w-full h-48 object-contain" />
                  <button onClick={removeQueryVideo} className="absolute top-2 right-2 bg-slate-900/80 hover:bg-rose-600 text-white p-1.5 rounded-full backdrop-blur-sm transition">
                    <Icons.Trash />
                  </button>
                </div>
              ) : (
                <label className="border-2 border-dashed border-slate-300 hover:border-indigo-500 bg-slate-50 hover:bg-indigo-50/20 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition text-center">
                  <input type="file" accept="video/mp4,video/avi,video/mov,video/mkv" onChange={handleQueryUpload} className="hidden" />
                  <Icons.Film />
                  <span className="text-xs font-bold text-slate-700 mt-2">Upload edited clip</span>
                </label>
              )}

              <button
                onClick={analyze}
                disabled={isAnalyzing || !queryVideo || poolVideos.length === 0}
                className={`w-full mt-6 py-3.5 px-4 rounded-xl flex items-center justify-center gap-2 font-semibold transition-all shadow-md
                  ${isAnalyzing || !queryVideo || poolVideos.length === 0
                    ? "bg-slate-100 text-slate-400 cursor-not-allowed shadow-none"
                    : "bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-200 transform active:scale-[0.98]"
                  }`}
              >
                {isAnalyzing ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Searching Frame Index...
                  </>
                ) : "Find Original Video"}
              </button>

              {results.length > 0 && (
                <div className="mt-6 border-t border-slate-100 pt-6 animate-in fade-in slide-in-from-bottom-2">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-bold text-slate-800">Match Results</h3>
                    <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded font-medium">
                      {results.length} Candidate{results.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  
                  <div className="space-y-3">
                    {results.map((r, i) => (
                      <div key={i} className="bg-slate-50 rounded-lg p-3 border border-slate-200 flex flex-col gap-2">
                        <div className="flex items-center gap-3">
                          <div className={`flex flex-col items-center justify-center w-12 h-12 rounded-lg ${getScoreColor(r.score)} text-white font-bold text-xs shadow-sm flex-shrink-0`}>
                            {(r.score * 100).toFixed(0)}%
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <h4 className="font-medium text-slate-900 truncate text-sm" title={r.name}>{r.name}</h4>
                              <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded border ${getStatusColor(r.status)} flex-shrink-0`}>
                                {r.status}
                              </span>
                            </div>
                            <div className="w-full bg-slate-200 rounded-full h-1.5 mt-1.5 overflow-hidden">
                              <div className={`h-full rounded-full ${getScoreColor(r.score)} transition-all duration-1000 ease-out`} style={{ width: `${Math.max(5, r.score * 100)}%` }} />
                            </div>
                          </div>
                        </div>
                        {r.timestamp_range && (
                          <div className="text-[11px] bg-white border border-slate-200 rounded p-2 flex justify-between items-center text-slate-600">
                            <span>Clip Range: <strong className="text-indigo-600">{r.timestamp_range}</strong></span>
                            {r.matched_frames && <span className="text-slate-400">{r.matched_frames}</span>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default DuplicateVid;