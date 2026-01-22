import React from 'react';
import { useNavigate } from 'react-router-dom';

// --- Icons for the Feature Section ---
const RocketIcon = () => (
  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const VideoIcon = () => (
  <svg className="w-5 h-5 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);


const TimelineIcon = () => (
  <svg className="w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 3-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 3-2 3-2 3 .895 3 2zM9 10l12-3" />
  </svg>
);

const LayersIcon = () => (
  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
  </svg>
);

const LockIcon = () => (
  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>
);

const ArrowRight = () => (
  <svg className="w-5 h-5 ml-2 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
  </svg>
);

// ---------------- HOME PAGE COMPONENT ----------------
export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white font-sans text-slate-800">
      
      {/* --- NAVBAR --- */}
      <nav className="w-full border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">D</span>
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">DuplicateDetector</span>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <section className="relative overflow-hidden pt-20 pb-32 lg:pt-32">
        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-sm font-semibold mb-8 border border-blue-100">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            v2.0 Now Available with DINOv2
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-slate-900 mb-8 leading-tight">
            Clean your dataset <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              in seconds, not hours.
            </span>
          </h1>

          <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto mb-12 leading-relaxed">
            Advanced Perceptual Hashing and AI Vector comparison to identify exact matches and near-duplicates instantly.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button 
              onClick={() => navigate('/duplicateimg')}
              className="group px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg hover:shadow-blue-500/30 transition-all flex items-center cursor-pointer"
            >
              Start Detecting <ArrowRight />
            </button>
          </div>

        </div>
      </section>
      {/* --- NEW SECTION: VIDEO SOURCE FINDER --- */}
      <section className="relative overflow-hidden py-24 bg-slate-50 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
          
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-sm font-semibold mb-8 border border-indigo-100">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            Video Fingerprinting Engine
          </div>

          {/* Heading */}
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-slate-900 mb-8 leading-tight">
            Find the original source <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">
              from a single clip.
            </span>
          </h1>

          {/* Description */}
          <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto mb-12 leading-relaxed">
            Upload a short video fragment or user-generated clip, and our AI will locate the exact timestamp and original master file in your video library.
          </p>

          {/* Button */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <button 
              // Make sure to create this route in your App.tsx if you haven't yet!
              onClick={() => navigate('/video_search')} 
              className="group px-8 py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-lg shadow-lg hover:shadow-indigo-500/30 transition-all flex items-center cursor-pointer"
            >
              Find Video Source <VideoIcon />
            </button>
          </div>

          {/* --- VIDEO MATCH UI PREVIEW --- */}
          <div className="relative mx-auto max-w-4xl">
            {/* Background Glow */}
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-200 to-purple-200 rounded-2xl blur-lg opacity-40"></div>
            
            <div className="relative bg-white border border-slate-200 rounded-xl shadow-xl p-6 flex flex-col md:flex-row gap-8 items-center">
                
                {/* Left: User Input Clip */}
                <div className="flex-1 w-full">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Input Clip (15s)</span>
                    </div>
                    <div className="aspect-video bg-slate-900 rounded-lg flex items-center justify-center relative overflow-hidden border border-slate-300">
                        {/* Fake video bars */}
                        <div className="w-8 h-8 rounded-full border-2 border-white/30 flex items-center justify-center">
                            <div className="w-0 h-0 border-t-[5px] border-t-transparent border-l-[8px] border-l-white border-b-[5px] border-b-transparent ml-1"></div>
                        </div>
                        <div className="absolute bottom-2 left-2 right-2 h-1 bg-white/20 rounded-full overflow-hidden">
                             <div className="h-full w-1/2 bg-red-500"></div>
                        </div>
                    </div>
                </div>

                {/* Center: Matching Animation */}
                <div className="hidden md:flex flex-col items-center justify-center text-indigo-500">
                    <div className="text-xs font-bold mb-1">MATCH</div>
                    <svg className="w-8 h-8 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
                </div>

                {/* Right: Source Found */}
                <div className="flex-1 w-full">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Source Found (01:45:20)</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                         <div className="flex items-center gap-3 mb-3">
                            <div className="p-2 bg-indigo-100 rounded-lg text-indigo-600">
                                <TimelineIcon />
                            </div>
                            <div className="text-left">
                                <div className="text-sm font-bold text-slate-800">Conference_Full_HD.mp4</div>
                                <div className="text-xs text-slate-500">Match Confidence: 98.5%</div>
                            </div>
                         </div>
                         {/* Timeline Visual */}
                         <div className="relative h-6 bg-slate-200 rounded-md w-full overflow-hidden">
                             {/* The timeline bars */}
                             <div className="absolute inset-0 flex gap-0.5 opacity-30">
                                 {[...Array(20)].map((_,i) => (
                                     <div key={i} className="flex-1 bg-slate-400" style={{height: `${Math.random() * 100}%`, alignSelf:'center'}}></div>
                                 ))}
                             </div>
                             {/* The Highlighted Match Segment */}
                             <div className="absolute top-0 bottom-0 left-[40%] width-[15%] w-16 bg-green-500/50 border-x-2 border-green-600 flex items-center justify-center">
                                 <span className="text-[10px] text-green-900 font-bold">FOUND</span>
                             </div>
                         </div>
                    </div>
                </div>

            </div>
          </div>

        </div>
      </section>

      {/* --- FEATURES GRID --- */}
      <section className="bg-slate-50 py-24 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900">Why use DuplicateDetector?</h2>
            <p className="text-slate-500 mt-4">Powerful features built for data scientists and photographers.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-14 h-14 bg-blue-600 rounded-xl flex items-center justify-center mb-6 shadow-blue-200 shadow-lg">
                <RocketIcon />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Blazing Fast</h3>
              <p className="text-slate-500 leading-relaxed">
                Powered by FAISS vector indexing, allowing you to compare thousands of images in milliseconds without lag.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-14 h-14 bg-indigo-600 rounded-xl flex items-center justify-center mb-6 shadow-indigo-200 shadow-lg">
                <LayersIcon />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Deep Analysis</h3>
              <p className="text-slate-500 leading-relaxed">
                We don't just check filenames. We use DINOv2 and Perceptual Hashing to find images that *look* the same.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-14 h-14 bg-slate-800 rounded-xl flex items-center justify-center mb-6 shadow-slate-300 shadow-lg">
                <LockIcon />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">100% Client Side</h3>
              <p className="text-slate-500 leading-relaxed">
                Your privacy matters. All image processing happens directly in your browser. No data is ever uploaded to a server.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --- FOOTER --- */}
      <footer className="bg-white py-12 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between text-slate-400 text-sm">
          <p>© 2024 Duplicate Image Detection System. All rights reserved.</p>
          <div className="flex gap-6 mt-4 md:mt-0">
            <a href="#" className="hover:text-slate-600">Privacy</a>
            <a href="#" className="hover:text-slate-600">Terms</a>
            <a href="#" className="hover:text-slate-600">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}