import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, ExternalLink, GitPullRequest, Clock, Loader } from 'lucide-react'
import DecryptedText from '../components/DecryptedText'
import GlitchLoader from '../components/GlitchLoader'
import StatusBadge from '../components/StatusBadge'
import { supabase } from '../lib/supabase'

function timeAgo(d) {
  if (!d) return ''
  const s = Math.floor((Date.now() - new Date(d).getTime()) / 1000)
  if (s < 60) return s + 's ago'
  if (s < 3600) return Math.floor(s / 60) + 'm ago'
  if (s < 86400) return Math.floor(s / 3600) + 'h ago'
  return Math.floor(s / 86400) + 'd ago'
}

// #5 — gate pressure bar (fills over 24h of waiting)
function PressureBar({ since }) {
  const [pct, setPct] = React.useState(0)
  React.useEffect(() => {
    const calc = () => setPct(Math.min((Date.now() - new Date(since).getTime()) / 864e5 * 100, 100))
    calc()
    const t = setInterval(calc, 60000)
    return () => clearInterval(t)
  }, [since])
  return (
    <div className="gate-pressure">
      <div className="gate-pressure-fill" style={{ width: `${pct}%` }} />
    </div>
  )
}

function DiffViewer({ diff }) {
  const [showMinimap, setShowMinimap] = React.useState(true);
  const diffRef = React.useRef(null);

  if (!diff) return null

  const lines = diff.split('\n');

  const scrollToLine = (index) => {
    if (diffRef.current) {
      const lineEls = diffRef.current.querySelectorAll('.dline');
      if (lineEls[index]) {
        lineEls[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  return (
    <div style={{ position: 'relative', height: '100%', maxHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      
      <button 
        onClick={() => setShowMinimap(!showMinimap)}
        style={{
          position: 'absolute',
          top: '20px',
          right: showMinimap ? 190 : 20,
          zIndex: 20,
          background: 'rgba(0,0,0,0.5)',
          border: '1px solid rgba(255,255,255,0.2)',
          color: 'var(--t2)',
          padding: '4px 8px',
          borderRadius: '0px',
          fontSize: 10,
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          cursor: 'pointer'
        }}
      >
        {showMinimap ? 'Hide Map' : 'Map'}
      </button>

      <div style={{
        position: 'absolute',
        top: '20px',
        right: showMinimap ? '20px' : '-200px',
        width: '160px',
        height: '250px',
        zIndex: 10,
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
        borderRadius: '0px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        padding: '12px 4px',
        transition: 'right 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        overflowY: 'auto',
        overflowX: 'hidden'
      }}>
        <svg 
          width="100%" 
          height={Math.max(300, lines.length * 4 + 40)} 
          style={{ display: 'block' }}
        >
          {lines.map((line, i) => {
            let fill = 'rgba(255,255,255,0.6)';
            if (line.startsWith('+') && !line.startsWith('+++')) fill = 'var(--green)';
            else if (line.startsWith('-') && !line.startsWith('---')) fill = 'var(--t2)';
            
            return (
              <g 
                key={i} 
                onClick={() => scrollToLine(i)} 
                style={{ cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.querySelector('rect');
                  if(rect) rect.setAttribute('fill', 'rgba(255,255,255,0.2)');
                }}
                onMouseLeave={(e) => {
                  const rect = e.currentTarget.querySelector('rect');
                  if(rect) rect.setAttribute('fill', 'transparent');
                }}
              >
                <rect x="0" y={i * 4 + 10 - 3.5} width="100%" height="4" fill="transparent" />
                <text 
                  x="2" 
                  y={i * 4 + 10} 
                  fontSize="3.5" 
                  fontFamily="var(--mono)" 
                  fill={fill}
                  xmlSpace="preserve"
                  style={{ pointerEvents: 'none' }}
                >
                  {line || ' '}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div className="diff" ref={diffRef} style={{ flex: 1, width: '100%', overflow: 'auto' }}>
        {lines.map((line, i) => {
          let cls = 'ctx'
          if (line.startsWith('+') && !line.startsWith('+++')) cls = 'add'
          else if (line.startsWith('-') && !line.startsWith('---')) cls = 'del'
          else if (line.startsWith('@@')) cls = 'hunk'
          // #6 — staggered reveal, capped at 900ms
          return (
            <div key={i} className={`dline ${cls}`} style={{
              animation: 'line-in 0.12s ease-out both',
              animationDelay: `${Math.min(i * 18, 900)}ms`
            }}>
              <span className="ln">{i + 1}</span>
              {line}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function RunDetails() {
  const { id } = useParams()
  const [run, setRun] = useState(null)
  const [hint, setHint] = useState('')
  const [busy, setBusy] = useState(false)

  const fetchRun = async () => {
    try {
      const r = await fetch(`${API_BASE_URL}/api/runs/${id}`)
      if (r.ok) setRun(await r.json())
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchRun()

    const channel = supabase
      .channel(`public:pipeline_runs:id=eq.${id}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'pipeline_runs', filter: `id=eq.${id}` }, payload => {
        // Optimistically update or refetch
        fetchRun()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [id])

  const act = async (action) => {
    setBusy(true)
    try {
      await fetch(`${API_BASE_URL}/api/runs/${id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(['approve', 'retry'].includes(action) ? { hint } : {})
      })
      fetchRun()
    } catch (e) { console.error(e) }
    setBusy(false)
  }

  if (!run) {
    return <div className="empty" style={{ height: '60vh' }}><GlitchLoader length={30} speed={30} /></div>
  }

  const isWait = run.status === 'WAITING_FOR_APPROVAL'
  const isRetry = run.status === 'VALIDATION_FAILED' || run.status === 'FIX_READY'

  return (
    <div className="fin">
      <Link to="/" className="back"><ArrowLeft style={{ width: 12, height: 12 }} /> Back</Link>

      {/* Header */}
      <div className="card" style={{ marginBottom: 6 }}>
        <div className="dhead">
          <div>
            <div className="dhead-repo">{run.repo_full_name}</div>
            <div className="dhead-meta">
              <span>{run.commit_sha ? <DecryptedText text={run.commit_sha.substring(0, 7)} speed={20} maxIterations={5} /> : ''}</span>
              <span className="sep">·</span>
              <span>{timeAgo(run.created_at)}</span>
            </div>
          </div>
          <StatusBadge status={run.status} style={{ padding: '5px 12px', fontSize: 10 }} />
        </div>
      </div>

      {/* Two-column */}
      <div className="detail-grid">
        <div className="sidebar">
          {/* Classification */}
          <div className="card">
            <div className="card-head"><span className="card-label">Classification</span></div>
            <div className="card-body" style={{ padding: '6px 14px' }}>
              <div className="irow">
                <span className="irow-k">Category</span>
                <span className="irow-v">{run.failure_category || '—'}</span>
              </div>
              <div className="irow">
                <span className="irow-k">Confidence</span>
                <span className="irow-v">{run.classification_reason?.match(/(\d+%)/)?.[1] || '—'}</span>
              </div>
              {run.failure_info && (
                <>
                  <div className="irow">
                    <span className="irow-k">Test</span>
                    <span className="irow-v">{run.failure_info.test_file_path}</span>
                  </div>
                  <div className="irow">
                    <span className="irow-k">Function</span>
                    <span className="irow-v">{run.failure_info.test_function_name}</span>
                  </div>
                  <div className="irow">
                    <span className="irow-k">Line</span>
                    <span className="irow-v">{run.failure_info.line_number}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* AI Analysis */}
          <div className="card">
            <div className="card-head"><span className="card-label">AI Analysis</span></div>
            <div className="card-body" style={{ fontSize: 11, color: 'var(--t2)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {run.classification_reason ? <DecryptedText text={run.classification_reason} speed={5} maxIterations={3} /> : 'Awaiting classification...'}
            </div>
          </div>

          {/* Validation */}
          {run.validation_passed !== null && run.validation_passed !== undefined && (
            <div className={`vbox ${run.validation_passed ? 'pass' : 'fail'}`}>
              <span className="vi">
                {run.validation_passed
                  ? <CheckCircle style={{ width: 16, height: 16 }} />
                  : <XCircle style={{ width: 16, height: 16 }} />}
              </span>
              <div>
                <div className="vt">{run.validation_passed ? 'Tests Passing' : 'Tests Failed'}</div>
                <div className="vs">{run.validation_passed ? 'pytest validated the patch' : 'Patch did not pass'}</div>
              </div>
            </div>
          )}

          {/* HITL Gate */}
          {isWait && (
            <div className="gate">
              <div className="gate-head">Approval Required</div>
              {/* #5 pressure bar — fills over 24h */}
              <PressureBar since={run.updated_at || run.created_at} />
              <div className="gate-body">
                <p>AI classified this as a fixable test mismatch. Approve to auto-generate and validate a patch.</p>
                <textarea className="hint" rows="3" placeholder="Optional context hint..." value={hint} onChange={e => setHint(e.target.value)} />
                <div className="gate-btns">
                  <button className="btn btn-go" onClick={() => act('approve')} disabled={busy}>
                    {busy ? <Loader style={{ width: 12, height: 12, animation: 'blink 1s ease-in-out infinite' }} /> : <CheckCircle style={{ width: 12, height: 12 }} />}
                    Approve
                  </button>
                  <button className="btn btn-no" onClick={() => act('reject')} disabled={busy}>
                    <XCircle style={{ width: 12, height: 12 }} />
                    Reject
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Retry Gate */}
          {isRetry && run.validation_passed === false && (
            <div className="gate" style={{ border: '1px solid rgba(255,100,100,0.2)' }}>
              <div className="gate-head" style={{ color: 'var(--red)' }}>Validation Failed</div>
              <div className="gate-body">
                <p>The generated patch did not pass the test suite. Provide a hint to guide the agent and try again.</p>
                <textarea className="hint" rows="3" placeholder="e.g. 'Use simple assert instead of unittest.TestCase'" value={hint} onChange={e => setHint(e.target.value)} />
                <div className="gate-btns">
                  <button className="btn btn-go" onClick={() => act('retry')} disabled={busy} style={{ background: 'var(--red)' }}>
                    {busy ? <Loader style={{ width: 12, height: 12, animation: 'blink 1s ease-in-out infinite' }} /> : <CheckCircle style={{ width: 12, height: 12 }} />}
                    Retry Patch
                  </button>
                  <button className="btn btn-no" onClick={() => act('reject')} disabled={busy}>
                    <XCircle style={{ width: 12, height: 12 }} />
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* PR Link */}
          {run.pr_url && (
            <a href={run.pr_url} target="_blank" rel="noreferrer" className="pr-box">
              <GitPullRequest style={{ width: 16, height: 16 }} className="pr-icon" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="pr-label">Pull Request</div>
                <div className="pr-url">{run.pr_url}</div>
              </div>
              <ExternalLink style={{ width: 12, height: 12, color: 'var(--t3)' }} />
            </a>
          )}
        </div>

        {/* ── Code Viewer ──────────────────────────────────────────── */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-head">
            <span className="card-label">{run.patch_diff ? 'Generated Patch' : 'Error Details'}</span>
            {run.failure_info?.test_file_path && (
              <span style={{
                fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--t3)',
                background: 'var(--bg-2)', padding: '2px 7px', borderRadius: 2
              }}>
                {run.failure_info.test_file_path}
              </span>
            )}
          </div>

          <div style={{ flex: 1, overflow: 'hidden' }}>
            {run.patch_diff ? (
              <DiffViewer diff={run.patch_diff} />
            ) : run.failure_info?.assertion_error ? (
              <div style={{ padding: 14 }}>
                <pre style={{
                  fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--t2)',
                  lineHeight: '19px', whiteSpace: 'pre-wrap', margin: 0
                }}>
                  {run.failure_info.assertion_error}
                </pre>
              </div>
            ) : (
              <div className="empty">
                <Clock style={{ width: 14, height: 14 }} />
                <span>Waiting for data...</span>
              </div>
            )}
          </div>

          {run.validation_error && !run.validation_passed && (
            <div style={{ borderTop: '1px solid var(--border)' }}>
              <div style={{
                padding: '6px 14px', borderBottom: '1px solid var(--border)',
                fontSize: 9, fontWeight: 700, color: 'var(--t2)',
                textTransform: 'uppercase', letterSpacing: '0.08em'
              }}>
                Validation Output
              </div>
              <pre style={{
                padding: 14, fontFamily: 'var(--mono)', fontSize: 10,
                color: 'var(--t3)', lineHeight: '17px',
                whiteSpace: 'pre-wrap', maxHeight: 180, overflow: 'auto', margin: 0
              }}>
                {run.validation_error}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
