import React from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Search } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import RunDetails from './pages/RunDetails'
import meshImg from './assets/mesh.png'

function Navbar() {
  return (
    <div className="nav">
      <div className="nav-content">
        <Link to="/" className="nav-logo">
          <img
            src={meshImg}
            alt="Realive"
            style={{
              width: 28, height: 28, objectFit: 'contain',
              mixBlendMode: 'screen',
              opacity: 0.42,
              filter: 'brightness(0.65) grayscale(0.2)',
            }}
          />
          Aletheia
        </Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <div className="page">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs/:id" element={<RunDetails />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
