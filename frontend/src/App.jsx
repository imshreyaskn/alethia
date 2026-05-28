import React from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import RunDetails from './pages/RunDetails'
import LandingPage from './pages/LandingPage'
import AuthCallback from './pages/AuthCallback'
import meshImg from './assets/mesh.png'
import { AuthProvider, useAuth } from './context/AuthContext'
import { supabase } from './lib/supabase'

function Navbar() {
  const { session } = useAuth()

  const handleLogout = async () => {
    await supabase.auth.signOut()
    window.location.href = '/'
  }

  if (!session) return null

  return (
    <div className="nav">
      <div className="nav-content" style={{ justifyContent: 'space-between', width: '100%' }}>
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
          Alethia
        </Link>
        {session && (
          <button className="btn btn-no" onClick={handleLogout} style={{ fontSize: '11px', padding: '6px 12px' }}>
            Logout
          </button>
        )}
      </div>
    </div>
  )
}

function AppRoutes() {
  const { session, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-0)' }}>
        <div className="sts pulse" style={{ width: 'auto', padding: '8px 16px', fontSize: '12px' }}>
          <div className="dot"></div>
          Loading Alethia...
        </div>
      </div>
    )
  }

  return (
    <>
      <Navbar />
      <div style={{ width: '100%' }}>
        <Routes>
          {session ? (
            <>
              <Route path="/" element={<div className="page"><Dashboard /></div>} />
              <Route path="/runs/:id" element={<div className="page"><RunDetails /></div>} />
            </>
          ) : (
            <Route path="/" element={<LandingPage />} />
          )}
          <Route path="/auth/callback" element={<div className="page"><AuthCallback /></div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
