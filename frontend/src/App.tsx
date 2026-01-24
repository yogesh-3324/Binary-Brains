import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
// 1. Capitalize the import name (even if the file is named duplicate_img.tsx)
import DuplicateImg from './pages/DuplicateImg'; 
import Home from './pages/Home';
import DuplicateVid from './pages/DuplicateVid';

function App() {
  return (
    <Routes>
      {/* 2. Use the capitalized component name here */}
      <Route path="/duplicateimg" element={<DuplicateImg />} />
      
      {/* Redirect root "/" to "/duplicate_img" */}
      <Route path="/" element={<Home/>} />
      <Route path="/video_search" element={<DuplicateVid/>} />
    </Routes>
  );
}

export default App;