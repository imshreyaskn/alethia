import React from 'react'
import { supabase } from '../lib/supabase'

export default function LandingPage() {
  const handleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) {
      console.error('Login error:', error)
    }
  }

  return (
    <div className="landing-container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '70vh', textAlign: 'center', gap: '32px' }}>
      <div className="hero-section" style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(var(--glass-blur)) saturate(140%)',
        border: '1px solid var(--glass-border)',
        padding: '60px 40px',
        borderRadius: '12px',
        boxShadow: 'inset 0 1px 0 0 var(--glass-shine), 0 12px 40px rgba(0,0,0,0.4)',
        maxWidth: '800px',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Shimmer effect */}
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, height: '1px',
          background: 'linear-gradient(90deg, transparent, rgba(183,180,174,0.3), transparent)'
        }} />
        
        <h1 style={{ fontFamily: 'var(--logo)', fontSize: '48px', fontWeight: '300', marginBottom: '24px', letterSpacing: '0.02em' }}>
          Welcome to <span style={{ color: 'var(--green)' }}>Alethia</span>
        </h1>
        <p style={{ fontSize: '16px', color: 'var(--t2)', lineHeight: '1.6', marginBottom: '40px', maxWidth: '600px', margin: '0 auto 40px auto' }}>
          The intelligent, self-healing pipeline for modern development teams. 
          Stop chasing flaky tests and environmental bugs. Let AI fix your CI automatically.
        </p>
        
        <button className="btn btn-go" onClick={handleLogin} style={{ fontSize: '14px', padding: '14px 32px', borderRadius: '4px' }}>
          Get Started with GitHub
        </button>
      </div>

      <div className="features-grid" style={{ display: 'flex', gap: '24px', marginTop: '40px', flexWrap: 'wrap', justifyContent: 'center' }}>
        {[
          { title: 'Zero Config', desc: 'Install our GitHub App in one click. No complex YAML required.' },
          { title: 'Auto Healing', desc: 'Tests fail? We analyze the logs and open a PR with the fix.' },
          { title: 'Enterprise Secure', desc: 'Row-level security ensures your data is strictly siloed.' }
        ].map((feat, idx) => (
          <div key={idx} style={{
            background: 'rgba(51, 49, 47, 0.15)',
            border: '1px solid var(--glass-border)',
            backdropFilter: 'blur(12px)',
            padding: '24px',
            borderRadius: '8px',
            width: '240px',
            textAlign: 'left'
          }}>
            <h3 style={{ fontSize: '14px', fontWeight: '500', color: 'var(--t1)', marginBottom: '12px' }}>{feat.title}</h3>
            <p style={{ fontSize: '12px', color: 'var(--t2)', lineHeight: '1.5' }}>{feat.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
