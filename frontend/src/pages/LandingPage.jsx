import React from 'react'
import { supabase } from '../lib/supabase'
import meshImg from '../assets/mesh.png'
import { AlertCircle, FileText, Sparkles, Code, CheckCircle, GitPullRequest, GitMerge, BookOpen, RefreshCw, Flower2, Mail } from 'lucide-react'
import DecryptedText from '../components/DecryptedText'

export default function LandingPage() {
  const handleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        scopes: 'repo workflow',
        queryParams: { prompt: 'consent' },
      },
    })
    if (error) {
      console.error('Login error:', error)
    }
  }

  return (
    <div className="landing-page-wrapper">
      {/* Hero Section */}
      <section className="hero-section" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        <div style={{ position: 'relative', zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <img 
            src={meshImg} 
            alt="Alethia Logo" 
            style={{ 
              width: 280, 
              height: 280, 
              objectFit: 'contain',
              mixBlendMode: 'screen',
              filter: 'brightness(0.8) grayscale(0.2)',
              marginBottom: '16px'
            }} 
          />
          <h1 style={{ fontFamily: 'var(--logo)', fontSize: '36px', fontWeight: '300', letterSpacing: '0.05em', color: 'var(--t1)', marginBottom: '80px' }}>
            Alethia
          </h1>
          
          <button className="btn-cta" onClick={handleLogin}>
            <span>Get Started with GitHub</span>
          </button>
        </div>
      </section>

      {/* Organic Map Section */}
      <section className="flow-section" style={{ 
        padding: '100px 20px', 
        background: 'linear-gradient(to bottom, rgba(10, 10, 10, 0) 0px, rgba(10, 10, 10, 0.85) 80px, rgba(10, 10, 10, 0.85) 100%)', 
        position: 'relative', 
        zIndex: 1
      }}>
        <h2 style={{ textAlign: 'center', fontFamily: 'var(--sans)', fontSize: '24px', fontWeight: '400', letterSpacing: '0.05em', color: 'var(--t2)', marginBottom: '80px', textTransform: 'uppercase' }}>
          Architecture
        </h2>
        
        <div className="organic-map-container" style={{ position: 'relative', maxWidth: '1000px', height: '500px', margin: '0 auto' }}>
          {/* SVG Connecting Lines with Arrows */}
          <svg viewBox="0 0 1000 500" preserveAspectRatio="none" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(183, 180, 174, 0.4)" />
              </marker>
              <marker id="arrow-dash" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 100, 100, 0.4)" />
              </marker>
              <linearGradient id="pulse-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(139, 74, 74, 0.2)" />
                <stop offset="50%" stopColor="rgba(239, 194, 150, 0.8)" />
                <stop offset="100%" stopColor="rgba(139, 74, 74, 0.2)" />
                <animate attributeName="x1" from="-100%" to="100%" dur="4s" repeatCount="indefinite" />
                <animate attributeName="x2" from="0%" to="200%" dur="4s" repeatCount="indefinite" />
              </linearGradient>
              <linearGradient id="red-pulse-reverse" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" stopColor="rgba(255, 100, 100, 0.15)" />
                <stop offset="50%" stopColor="rgba(255, 100, 100, 0.5)" />
                <stop offset="100%" stopColor="rgba(255, 100, 100, 0.15)" />
                <animate attributeName="x1" from="200%" to="0%" dur="4s" repeatCount="indefinite" />
                <animate attributeName="x2" from="100%" to="-100%" dur="4s" repeatCount="indefinite" />
              </linearGradient>
            </defs>
            {/* Webhook to Log Ingestion */}
            <path d="M 120 180 C 170 180, 170 380, 210 380" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* Log Ingestion to AI Analysis */}
            <path d="M 220 380 C 280 380, 320 120, 370 120" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* User Context to Code Gen */}
            <path d="M 380 300 C 450 300, 480 420, 510 420" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* AI Analysis to Code Gen */}
            <path d="M 380 120 C 450 120, 450 420, 510 420" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* Code Gen to Validation */}
            <path d="M 520 420 C 600 420, 620 280, 670 280" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* Validation to Retry Logic (Failed Validation) */}
            <path d="M 680 280 C 680 180, 660 100, 635 100" fill="none" stroke="url(#red-pulse-reverse)" strokeWidth="1.5" strokeDasharray="4 4" markerEnd="url(#arrow-dash)" />
            
            {/* Retry Logic to Code Gen */}
            <path d="M 620 100 C 560 100, 520 200, 520 405" fill="none" stroke="url(#red-pulse-reverse)" strokeWidth="1.5" strokeDasharray="4 4" markerEnd="url(#arrow-dash)" />
            
            {/* Validation to PR (Success) */}
            <path d="M 680 280 C 730 280, 730 400, 770 400" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
            
            {/* PR to Merged */}
            <path d="M 780 400 C 830 400, 830 180, 870 180" fill="none" stroke="url(#pulse-gradient)" strokeWidth="1.5" markerEnd="url(#arrow)" />
          </svg>

          {/* Nodes */}
          {[
            { id: 1, title: 'GitHub Webhook', desc: 'Test Failed', x: 120, y: 180, Icon: AlertCircle },
            { id: 2, title: 'Log Ingestion', desc: 'Alethia parses CI logs', x: 220, y: 380, Icon: FileText },
            { id: 8, title: 'User Context', desc: 'Repo guidelines', x: 380, y: 300, Icon: BookOpen },
            { id: 3, title: 'AI Analysis', desc: 'Root cause identified', x: 380, y: 120, Icon: Sparkles },
            { id: 4, title: 'Code Gen', desc: 'Automated patch', x: 520, y: 420, Icon: Code },
            { id: 5, title: 'Validation', desc: 'Pre-flight checks', x: 680, y: 280, Icon: CheckCircle },
            { id: 9, title: 'Retry Logic', desc: 'Self-correcting loop', x: 620, y: 100, Icon: RefreshCw },
            { id: 6, title: 'Pull Request', desc: 'Self-healing PR', x: 780, y: 400, Icon: GitPullRequest },
            { id: 7, title: 'Merged', desc: 'Pipeline restored', x: 880, y: 180, Icon: GitMerge }
          ].map((node) => {
            const Icon = node.Icon;
            return (
              <div key={node.id} className="map-node" style={{
                position: 'absolute',
                left: `${(node.x / 1000) * 100}%`,
                top: `${(node.y / 500) * 100}%`,
                transform: 'translate(-50%, -50%)',
                zIndex: 10,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                width: '140px'
              }}>
                <Icon size={16} color="var(--t2)" style={{ marginBottom: '8px' }} />
                
                {/* Glowing Dot */}
                <div style={{ width: '6px', height: '6px', background: 'var(--t1)', borderRadius: '50%', boxShadow: '0 0 10px 2px rgba(183,180,174,0.4)', marginBottom: '8px' }}></div>
                
                {/* Labels */}
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--sans)', fontSize: '11px', fontWeight: '500', color: 'var(--t1)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
                    {node.title}
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--t3)', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
                    {node.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ maxWidth: '800px', margin: '100px auto 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '32px', padding: '0 40px' }}>
          {[
            'Alethia seamlessly hooks into your GitHub webhooks to catch failing CI logs instantly.',
            'The AI engine securely analyzes the trace, generates a fix, and pushes a self-healing PR.',
            'If the pre-flight checks fail, the system loops and self-corrects until the patch is green.'
          ].map((text, idx) => (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
              <div style={{ color: 'var(--t1)', marginBottom: '12px', filter: 'drop-shadow(0 0 12px var(--t1))', opacity: 0.8 }}>
                <Flower2 size={16} />
              </div>
              <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--t2)', letterSpacing: '0.02em', maxWidth: '500px' }}>
                <DecryptedText text={text} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <img src={meshImg} alt="Alethia" style={{ width: 20, height: 20, mixBlendMode: 'screen', filter: 'brightness(0.6)' }} />
            <span style={{ fontFamily: 'var(--logo)', fontSize: '18px', color: 'var(--t2)' }}>Alethia</span>
          </div>
          <div className="footer-links" style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <a href="mailto:imshreyaskn@gmail.com" title="Email" style={{ color: 'var(--t2)', transition: 'color 0.2s', display: 'flex' }}>
              <Mail size={18} />
            </a>
            <a href="https://linkedin.com/in/imshreyaskn" target="_blank" rel="noreferrer" title="LinkedIn" style={{ color: 'var(--t2)', transition: 'color 0.2s', display: 'flex' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
                <rect x="2" y="9" width="4" height="12" />
                <circle cx="4" cy="4" r="2" />
              </svg>
            </a>
            <a href="https://github.com/imshreyaskn" target="_blank" rel="noreferrer" title="GitHub" style={{ color: 'var(--t2)', transition: 'color 0.2s', display: 'flex' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.02c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
              </svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
