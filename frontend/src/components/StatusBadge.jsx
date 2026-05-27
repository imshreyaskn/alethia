import React from 'react'
import DecryptedText from './DecryptedText'

function stsClass(s) {
  if (['CLASSIFYING', 'FIXING'].includes(s)) return 'pulse'
  if (s === 'WAITING_FOR_APPROVAL') return 'wait'
  if (['VALIDATED', 'DELIVERED'].includes(s)) return 'done'
  if (['FAILED', 'REJECTED', 'STOPPED'].includes(s)) return 'fail'
  return 'neu'
}

// #4 — status change triggers DecryptedText re-animation via key prop
export default function StatusBadge({ status, style }) {
  return (
    <span className={`sts ${stsClass(status)}`} style={style}>
      <span className="dot" />
      <DecryptedText key={status} text={status?.replace(/_/g, ' ') ?? ''} speed={28} maxIterations={4} />
    </span>
  )
}
