import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'

export default function AuthCallback() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  useEffect(() => {
    const checkInstallation = async (activeSession) => {
      try {
        const userId = activeSession.user.id
        const providerToken = activeSession.provider_token
        
        // 1. Proactively sync installations from GitHub if we have the provider token
        if (providerToken) {
          try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
            await fetch(`${apiUrl}/github/sync-installations`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${activeSession.access_token}`
              },
              body: JSON.stringify({ provider_token: providerToken })
            })
          } catch (syncErr) {
            console.warn('Failed to proactively sync installations:', syncErr)
          }
        }

        // 2. Check if the user has any connected GitHub App installations
        const { data: installations, error: dbError } = await supabase
          .from('installations')
          .select('*')
          .eq('user_id', userId)
          .limit(1)

        if (dbError) {
          console.warn('Could not check installations:', dbError)
          navigate('/')
          return
        }

        if (installations && installations.length > 0) {
          navigate('/')
        } else {
          const appName = import.meta.env.VITE_GITHUB_APP_NAME || 'realive-bot'
          window.location.href = `https://github.com/apps/${appName}/installations/new`
        }
      } catch (err) {
        console.error('Auth Callback Error:', err)
        setError(err.message)
      }
    }

    if (session) {
      checkInstallation(session)
    } else {
      // If we don't have a session yet, check if there's an explicit error from GitHub
      const searchParams = new URLSearchParams(window.location.search)
      if (searchParams.get('error')) {
        setError(searchParams.get('error_description') || searchParams.get('error'))
        return
      }
      
      // Wait a few seconds for Supabase to finish PKCE exchange
      const timeout = setTimeout(() => {
        setError("Session could not be established. Please check your browser console for errors.")
      }, 5000)
      
      return () => clearTimeout(timeout)
    }
  }, [session, navigate])

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <h2 style={{ color: 'var(--t2)', marginBottom: '16px' }}>Authentication Error</h2>
        <p style={{ color: 'var(--t3)' }}>{error}</p>
        <button className="btn btn-no" onClick={() => navigate('/')} style={{ marginTop: '24px' }}>
          Back to Home
        </button>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <div className="sts pulse" style={{ width: 'auto', padding: '8px 16px', fontSize: '12px' }}>
        <div className="dot"></div>
        Authenticating & Checking Installation...
      </div>
    </div>
  )
}
