import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import VerificationStatusBadge from './VerificationStatusBadge'

const STEP_COLORS = {
  OCR:      '#06b6d4',
  MASK:     '#6366f1',
  EXTRACT:  '#8b5cf6',
  EVAL:     '#f59e0b',
  DEMASK:   '#10b981',
  REVIEW:   '#f97316',
  FALLBACK: '#ef4444',
  INIT:     '#4a5568',
}

function stepColor(line) {
  for (const [key, color] of Object.entries(STEP_COLORS)) {
    if (line.includes(`[${key}]`)) return color
  }
  return 'var(--text-muted)'
}

function ReasoningTimeline({ reasoning }) {
  const [expanded, setExpanded] = useState(true)
  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <button
        style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', fontWeight: 700,
          fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em',
          marginBottom: expanded ? '0.75rem' : 0, padding: 0,
        }}
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Agent Reasoning Log ({reasoning.length} steps)
      </button>
      {expanded && (
        <div style={{ maxHeight: '240px', overflowY: 'auto', padding: '0.25rem 0' }}>
          {reasoning.map((line, i) => (
            <div key={i} className="reasoning-step">
              <div className="step-dot" style={{ background: stepColor(line) }} />
              <div className="step-text">{line}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DiscrepanciesTable({ discrepancies }) {
  if (!discrepancies || discrepancies.length === 0) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem',
        color: 'var(--status-verified)', fontSize: '0.875rem',
        padding: '0.75rem', background: 'rgba(16,185,129,0.06)',
        borderRadius: '8px', marginBottom: '1.25rem',
      }}>
        <CheckCircle size={16} />
        No discrepancies detected
      </div>
    )
  }

  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <AlertTriangle size={13} style={{ color: '#f59e0b' }} />
        Discrepancies ({discrepancies.length})
      </div>
      <div className="table-wrapper" style={{ borderRadius: '8px' }}>
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Expected</th>
              <th>Found</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {discrepancies.map((d, i) => (
              <tr key={i} className={`discrepancy-row severity-${d.severity}`}>
                <td>
                  <code style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--accent-1)' }}>
                    {d.field}
                  </code>
                </td>
                <td style={{ fontSize: '0.8rem' }}>{String(d.expected ?? '—')}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {Array.isArray(d.found) ? d.found.join(', ') : String(d.found ?? '—')}
                </td>
                <td>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '0.4rem',
                  }}>
                    <div style={{
                      width: 48, height: 4, background: 'var(--border)',
                      borderRadius: 2, overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${d.confidence}%`, height: '100%',
                        background: d.confidence > 80 ? '#10b981' : d.confidence > 50 ? '#f59e0b' : '#ef4444',
                        borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {d.confidence?.toFixed(0)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ExtractedDataCard({ extractedData, referenceData }) {
  const [expanded, setExpanded] = useState(false)
  if (!extractedData || Object.keys(extractedData).length === 0) return null

  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <button
        style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', fontWeight: 700,
          fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em',
          marginBottom: expanded ? '0.75rem' : 0, padding: 0,
        }}
        onClick={() => setExpanded(e => !e)}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Extracted Data (raw, pre-demasking)
      </button>
      {expanded && (
        <pre style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '1rem',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          overflowX: 'auto',
          maxHeight: '200px',
          overflowY: 'auto',
          lineHeight: 1.6,
        }}>
          {JSON.stringify(extractedData, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default function AgentReasoningPanel({
  reasoning = [],
  discrepancies = [],
  extractedData = {},
  referenceData = {},
  evaluationResult,
}) {
  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '1.25rem' }}>
      {/* Evaluation result banner */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        padding: '0.75rem 1rem',
        background: 'var(--bg-base)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        marginBottom: '1.25rem',
      }}>
        <Info size={15} style={{ color: 'var(--accent-3)', flexShrink: 0 }} />
        <div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>
            Evaluation Result
          </span>
          <VerificationStatusBadge status={evaluationResult} />
        </div>
      </div>

      <ReasoningTimeline reasoning={reasoning} />
      <div className="divider" />
      <DiscrepanciesTable discrepancies={discrepancies} />
      <div className="divider" />
      <ExtractedDataCard extractedData={extractedData} referenceData={referenceData} />
    </div>
  )
}
