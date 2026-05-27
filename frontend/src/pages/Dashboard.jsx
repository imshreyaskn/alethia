import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import DecryptedText from '../components/DecryptedText'
import GlitchLoader from '../components/GlitchLoader'
import StatusBadge from '../components/StatusBadge'
import { supabase } from '../lib/supabase'
import meshImg from '../assets/mesh.png'

function timeAgo(d) {
  if (!d) return ''
  const s = Math.floor((Date.now() - new Date(d).getTime()) / 1000)
  if (s < 60) return s + 's'
  if (s < 3600) return Math.floor(s / 60) + 'm'
  if (s < 86400) return Math.floor(s / 3600) + 'h'
  return Math.floor(s / 86400) + 'd'
}

// #7 — deterministic warm-stone dot per repo
function repoColor(name = '') {
  let h = 0
  for (const c of name) h = ((h * 31) + c.charCodeAt(0)) >>> 0
  const palette = [
    'rgba(183,180,174,0.95)', 'rgba(183,180,174,0.55)',
    'rgba(145,142,137,0.9)',  'rgba(165,162,157,0.75)',
    'rgba(205,202,197,0.7)',  'rgba(125,121,116,0.9)',
  ]
  return palette[h % palette.length]
}

// #1 — EKG: single beat, sits between time col and arrow col
function Ekg() {
  const d = 'M0,8 L8,8 L11,6 L13,0 L15,16 L17,8 L50,8'
  return (
    <svg width="50" height="16" viewBox="0 0 50 16"
      style={{ position: 'absolute', right: 44, top: '50%', transform: 'translateY(-50%)', opacity: 0.18, pointerEvents: 'none' }}>
      <path d={d} fill="none" stroke="var(--t1)" strokeWidth="1.2" strokeLinejoin="round"
        style={{ filter: 'drop-shadow(0 0 3px rgba(183,180,174,0.7))' }} />
    </svg>
  )
}

// Stat pill — large number + small label
function StatPill({ label, value, align = 'right' }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: align === 'right' ? 'flex-end' : 'flex-start',
      gap: 4,
    }}>
      <span style={{
        fontFamily: 'var(--sans)', fontSize: 36, fontWeight: 300,
        letterSpacing: '-0.04em', lineHeight: 1, color: 'var(--t1)',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</span>
      <span style={{
        fontFamily: 'var(--mono)', fontSize: 9, fontWeight: 500,
        letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--t3)',
      }}>{label}</span>
    </div>
  )
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('All')

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/runs`)
        if (res.ok) setRuns((await res.json()).runs || [])
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    fetchRuns()

    const channel = supabase
      .channel('public:pipeline_runs')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'pipeline_runs' }, fetchRuns)
      .subscribe()

    return () => supabase.removeChannel(channel)
  }, [])

  const total     = runs.length
  const active    = runs.filter(r => ['CLASSIFYING', 'FIXING', 'WAITING_FOR_APPROVAL'].includes(r.status)).length
  const delivered = runs.filter(r => r.status === 'DELIVERED').length
  const rate      = total > 0 ? Math.round((delivered / total) * 100) : 0

  const filtered = filter === 'All' ? runs
    : filter === 'Active'    ? runs.filter(r => ['CLASSIFYING', 'FIXING', 'WAITING_FOR_APPROVAL'].includes(r.status))
    : runs.filter(r => r.status === 'DELIVERED')

  if (loading) return <div className="empty" style={{ height: '60vh' }}><GlitchLoader length={20} speed={40} /></div>

  return (
    <div className="fin page-container">

      {/* ── Mesh Hero + Radiating Stats ────────────────────────────────── */}
      <div style={{
        position: 'relative', display: 'flex', alignItems: 'center',
        justifyContent: 'center', marginBottom: 52, minHeight: 260,
      }}>
        {/* Left stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 40, alignItems: 'flex-end', marginRight: 52, zIndex: 1 }}>
          <StatPill label="Total Runs" value={total}  align="right" />
          <StatPill label="Active Now" value={active} align="right" />
        </div>

        {/* Centre mesh — screen blend makes white form visible on dark bg */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <img
            src={meshImg}
            alt="Realive"
            style={{
              width: 260, height: 260, objectFit: 'contain',
              mixBlendMode: 'screen',
              opacity: 0.35,
              filter: 'brightness(0.65) grayscale(0.2)',
              userSelect: 'none', pointerEvents: 'none', display: 'block',
            }}
          />
          {/* Soft ambient glow behind image */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: 'radial-gradient(ellipse 55% 55% at 50% 50%, rgba(183,180,174,0.05) 0%, transparent 70%)',
          }} />
        </div>

        {/* Right stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 40, alignItems: 'flex-start', marginLeft: 52, zIndex: 1 }}>
          <StatPill label="Delivered"    value={delivered}  align="left" />
          <StatPill label="Success Rate" value={`${rate}%`} align="left" />
        </div>

        {/* Dashed connector lines stemming from image toward each stat */}
        <svg
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', overflow: 'visible' }}
          viewBox="0 0 700 260" preserveAspectRatio="xMidYMid meet"
        >
          <line x1="215" y1="78"  x2="315" y2="115" stroke="rgba(183,180,174,0.1)" strokeWidth="1" strokeDasharray="3 7" />
          <line x1="215" y1="182" x2="315" y2="152" stroke="rgba(183,180,174,0.1)" strokeWidth="1" strokeDasharray="3 7" />
          <line x1="485" y1="78"  x2="385" y2="115" stroke="rgba(183,180,174,0.1)" strokeWidth="1" strokeDasharray="3 7" />
          <line x1="485" y1="182" x2="385" y2="152" stroke="rgba(183,180,174,0.1)" strokeWidth="1" strokeDasharray="3 7" />
          {/* Small terminal dots at stat ends */}
          <circle cx="215" cy="78"  r="2" fill="rgba(183,180,174,0.2)" />
          <circle cx="215" cy="182" r="2" fill="rgba(183,180,174,0.2)" />
          <circle cx="485" cy="78"  r="2" fill="rgba(183,180,174,0.2)" />
          <circle cx="485" cy="182" r="2" fill="rgba(183,180,174,0.2)" />
        </svg>
      </div>

      {/* ── Pipeline Runs List ─────────────────────────────────────────── */}
      <div className="runs-section">
        <div className="runs-header">
          <span className="runs-title">Pipeline Runs</span>
          <div className="runs-filters">
            {['All', 'Active', 'Delivered'].map(f => (
              <button key={f} className={filter === f ? 'on' : ''} onClick={() => setFilter(f)}>{f}</button>
            ))}
          </div>
        </div>

        <div className="tbl-head">
          <span className="tbl-th">Repository</span>
          <span className="tbl-th">Category</span>
          <span className="tbl-th">Status</span>
          <span className="tbl-th">Time</span>
          <span />
        </div>

        <div className="runs-list">
          {filtered.map(run => {
            const isActive = ['CLASSIFYING', 'FIXING'].includes(run.status)
            const dot = repoColor(run.repo_full_name)
            return (
              <Link key={run.id} to={`/runs/${run.id}`} className={`run-box ${isActive ? 'run-box-active' : ''}`}>
                {isActive && <Ekg />}
                <div className="row-content">
                  <div className="row-col">
                    <div className="row-repo">
                      <span style={{
                        display: 'inline-block', width: 5, height: 5, borderRadius: '50%',
                        background: dot, boxShadow: `0 0 4px ${dot}`,
                        marginRight: 8, verticalAlign: 'middle', flexShrink: 0,
                      }} />
                      {run.repo_full_name}
                    </div>
                    <div className="row-sha">
                      {run.commit_sha ? <DecryptedText text={run.commit_sha.substring(0, 7)} speed={20} maxIterations={5} /> : ''}
                    </div>
                  </div>
                  <div className="row-col"><div className="row-cat">{run.failure_category || '—'}</div></div>
                  <div className="row-col"><StatusBadge status={run.status} /></div>
                  <div className="row-col"><div className="row-time">{timeAgo(run.created_at)}</div></div>
                  <div className="row-col row-arr"><ArrowRight style={{ width: 12, height: 12 }} /></div>
                </div>
              </Link>
            )
          })}

          {/* #10 Signal Lost empty state */}
          {filtered.length === 0 && (
            <div className="signal-lost">
              <div className="signal-bars">
                {[12, 18, 8, 22, 10, 20, 6, 16].map((h, i) => (
                  <div key={i} className="signal-bar" style={{ height: h }} />
                ))}
              </div>
              <span className="signal-no">No Activity</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
