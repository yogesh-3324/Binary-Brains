import React, { useState, useEffect, useRef } from "react";

// ---------------- CONFIG ----------------
const API_BASE = "http://localhost:8001";

// ---------------- TYPES ----------------
// Updated to match exactly what we map from the backend
type MatchStatus = "FOUND" | "POSSIBLE" | "NOT_PRESENT";

type Result = {
  name: string;
  score: number;
  status: MatchStatus;
  confidence: string;
};

type VideoPreview = {
  id: string;
  file: File;
  preview: string;
  name: string;
};

// ---------------- ICONS ----------------
const Icons = {
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
  Video: () => (
    <svg className="w-8 h-8 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
      <line x1="7" y1="2" x2="7" y2="22"></line>
      <line x1="17" y1="2" x2="17" y2="22"></line>
      <line x1="2" y1="12" x2="22" y2="12"></line>
      <line x1="2" y1="7" x2="7" y2="7"></line>
      <line x1="2" y1="17" x2="7" y2="17"></line>
      <line x1="17" y1="17" x2="22" y2="17"></line>
      <line x1="17" y1="7" x2="22" y2="7"></line>
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
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const poolInputRef = useRef<HTMLInputElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);

  // 1. CLEANUP & INIT
  useEffect(() => {
    // Optional: Only reset if you want a fresh state on every page load
    const resetBackend = async () => {
      try {
        await fetch(`${API_BASE}/reset`, { method: "POST" });
      } catch (err) {
        console.error("Backend offline", err);
        setError("Could not connect to analysis server. Is it running?");
      }
    };
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

  const handlePoolChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) processFiles(Array.from(e.target.files));
    e.target.value = ""; 
  };

  // Drag and Drop Handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) processFiles(Array.from(e.dataTransfer.files));
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
      
      // --- CRITICAL FIX: MAP BACKEND RESPONSE TO FRONTEND TYPES ---
      // Backend returns: { video, clip_score, verdict, confidence }
      const mappedResults: Result[] = data.results.map((r: any) => ({
        name: r.video,
        score: r.clip_score,
        status: r.verdict, // FOUND, POSSIBLE, NOT_PRESENT
        confidence: r.confidence
      }));

      setResults(mappedResults.sort((a, b) => b.score - a.score));
    } catch (err) {
      setError("Analysis failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 3. UI HELPERS
  const getStatusColor = (status: MatchStatus) => {
    switch(status) {
      case "FOUND": return "bg-green-100 text-green-800 border-green-200";
      case "POSSIBLE": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      default: return "bg-slate-100 text-slate-600 border-slate-200";
    }
  };

  const getScoreColor = (score: number) => {
    if (score > 0.8) return "bg-green-500";
    if (score > 0.65) return "bg-yellow-500";
    return "bg-slate-300";
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 pb-20">

      {/* HEADER */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-indigo-200 shadow-lg">
              V
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-none">VideoMatcher</h1>
              <p className="text-xs text-slate-500 font-medium mt-1">DINOv2 + CLIP Engine</p>
            </div>
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="text-sm font-medium text-slate-500 hover:text-indigo-600 px-3 py-2 rounded-md hover:bg-slate-50 transition"
          >
            Reset System
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 mt-8">
        
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
            <span className="font-bold">Error:</span> {error}
            <button onClick={() => setError(null)} className="ml-auto text-sm underline">Dismiss</button>
          </div>
        )}

        <div className="grid lg:grid-cols-12 gap-8">
          
          {/* LEFT: REFERENCE POOL */}
          <section className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold flex items-center gap-2">
                1. Reference Database
                <span className="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full">{poolVideos.length}</span>
              </h2>
            </div>

            {/* Upload Area with Drop Support */}
            <div 
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => poolInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 group relative
                ${isDragging ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50'}
              `}
            >
              <input 
                ref={poolInputRef}
                type="file" 
                multiple 
                accept="video/*" 
                onChange={handlePoolChange} 
                className="hidden" 
              />
              <div className="flex flex-col items-center pointer-events-none">
                {isUploading ? (
                  <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-3"></div>
                ) : (
                  <Icons.Upload />
                )}
                <p className="font-semibold text-slate-700">
                  {isUploading ? "Uploading..." : "Click or Drag videos here"}
                </p>
                <p className="text-sm text-slate-400 mt-1">Build your search pool</p>
              </div>
            </div>

            {/* Video Grid */}
            {poolVideos.length > 0 && (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-4 mt-6">
                {poolVideos.map((v) => (
                  <div key={v.id} className="group relative bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition">
                    <div className="aspect-video bg-black relative">
                      {/* Added muted and preload to prevent browser lag */}
                      <video 
                        src={v.preview} 
                        className="w-full h-full object-cover opacity-80" 
                        muted 
                        preload="metadata"
                        onMouseOver={e => (e.target as HTMLVideoElement).play()}
                        onMouseOut={e => (e.target as HTMLVideoElement).pause()}
                      />
                      <button 
                        onClick={(e) => { e.stopPropagation(); removePoolVideo(v.id, v.name); }}
                        className="absolute top-1 right-1 bg-black/60 hover:bg-red-600 text-white p-1.5 rounded-md backdrop-blur-sm transition-all opacity-0 group-hover:opacity-100"
                      >
                        <Icons.Trash />
                      </button>
                    </div>
                    <div className="p-2">
                      <p className="text-xs font-medium truncate text-slate-600" title={v.name}>{v.name}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* RIGHT: QUERY & ACTIONS */}
          <section className="lg:col-span-5 space-y-6">
            
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 sticky top-24">
              <h2 className="text-lg font-bold mb-4">2. Find Duplicate</h2>
              
              {!queryVideo ? (
                <div 
                  onClick={() => queryInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 rounded-xl h-48 flex flex-col items-center justify-center cursor-pointer hover:bg-slate-50 hover:border-indigo-400 transition"
                >
                  <input ref={queryInputRef} type="file" accept="video/*" onChange={handleQueryUpload} className="hidden" />
                  <Icons.Video />
                  <p className="mt-3 text-sm font-medium text-slate-500">Upload Query Video</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="relative rounded-xl overflow-hidden bg-black aspect-video shadow-inner group">
                    <video src={queryVideo.preview} controls className="w-full h-full object-contain" />
                    <button 
                      onClick={() => setQueryVideo(null)}
                      className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white text-xs px-3 py-1.5 rounded backdrop-blur-md opacity-0 group-hover:opacity-100 transition"
                    >
                      Change Video
                    </button>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <Icons.Check />
                    <span className="truncate font-medium">{queryVideo.name}</span>
                  </div>
                </div>
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
                    Comparing Deep Features...
                  </>
                ) : "Run Similarity Search"}
              </button>

              {/* Results Section */}
              {results.length > 0 && (
                <div className="mt-6 border-t border-slate-100 pt-6 animate-in fade-in slide-in-from-bottom-2">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-bold text-slate-800">Results</h3>
                    <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded font-medium">
                      Top {results.length} Matches
                    </span>
                  </div>
                  
                  <div className="space-y-3">
                    {results.map((r, i) => (
                      <div key={i} className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex items-center gap-3">
                        {/* Score Badge */}
                        <div className={`flex flex-col items-center justify-center w-12 h-12 rounded-lg ${getScoreColor(r.score)} text-white font-bold text-sm shadow-sm`}>
                          {(r.score * 100).toFixed(0)}%
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-slate-900 truncate text-sm" title={r.name}>{r.name}</h4>
                            <span className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded border ${getStatusColor(r.status)}`}>
                              {r.status}
                            </span>
                          </div>
                          
                          {/* Visual Bar */}
                          <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2 overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${getScoreColor(r.score)} transition-all duration-1000 ease-out`} 
                              style={{ width: `${Math.max(5, r.score * 100)}%` }}
                            />
                          </div>
                        </div>
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