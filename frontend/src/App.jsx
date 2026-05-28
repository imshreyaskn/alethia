import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import RunDetails from './pages/RunDetails'
import LandingPage from './pages/LandingPage'
import AuthCallback from './pages/AuthCallback'
import meshImg from './assets/mesh.png'
import { supabase } from './lib/supabase'

function Navbar({ session }) {
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

export default function App() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

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
    <BrowserRouter>
      <Navbar session={session} />
      <div style={{ width: '100%' }}>
        <Routes>
          {session ? (
            <>
              <Route path="/" element={<div className="page"><Dashboard session={session} /></div>} />
              <Route path="/runs/:id" element={<div className="page"><RunDetails session={session} /></div>} />
            </>
          ) : (
            <Route path="/" element={<LandingPage />} />
          )}
          <Route path="/auth/callback" element={<div className="page"><AuthCallback session={session} /></div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
