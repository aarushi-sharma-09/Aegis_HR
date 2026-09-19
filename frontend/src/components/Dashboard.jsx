import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ShieldCheck, Clock, CheckCircle, XCircle, AlertTriangle, Users, RefreshCw
} from 'lucide-react'
import { getDashboardStats } from '../lib/api'

const STAT_CARDS = [
  { key: 'total',          label: 'Total Docs',       icon: ShieldCheck, color: '#6366f1' },
  { key: 'total_applicants',label: 'Applicants',      icon: Users,       color: '#06b6d4' },
  { key: 'verified',       label: 'Verified',         icon: CheckCircle, color: '#10b981' },
  { key: 'needs_review',   label: 'Needs Review',     icon: AlertTriangle,color: '#8b5cf6' },
  { key: 'rejected',       label: 'Rejected',         icon: XCircle,     color: '#ef4444' },
  { key: 'needs_fallback', label: 'Awaiting Evidence',icon: Clock,       color: '#f97316' },
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const navigate = useNavigate()

  const fetchStats = async () => {
    try {
      const { data } = await getDashboardStats()
      setStats(data)
      setLastRefresh(new Date())
    } catch {
      setStats({}) // show zeros on error
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000) // auto-refresh every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">Dashboard</h2>
          <p className="page-subtitle">
            Real-time overview of background verification pipeline
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Last updated {lastRefresh.toLocaleTimeString()}
          </span>
          <button className="btn btn-outline" onClick={fetchStats} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        {STAT_CARDS.map(({ key, label, icon: Icon, color }) => (
          <div
            key={key}
            className="stat-card"
            style={{ '--accent-gradient': `linear-gradient(90deg, ${color}, ${color}88)` }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                {loading ? (
                  <div className="skeleton" style={{ width: 48, height: 36, marginBottom: 8 }} />
                ) : (
                  <div className="stat-value" style={{ color }}>
                    {stats?.[key] ?? 0}
                  </div>
                )}
                <div className="stat-label">{label}</div>
              </div>
              <Icon size={20} style={{ color, opacity: 0.6 }} />
            </div>
          </div>
        ))}
      </div>

      {/* Pipeline Stages */}
      <div style={{ marginBottom: '2rem' }}>
        <div className="section-title">Agentic Pipeline</div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: '0.5rem',
        }}>
          {[
            { step: '01', label: 'OCR', desc: 'Document text extraction', color: '#06b6d4' },
            { step: '02', label: 'PII Mask', desc: 'Regex + Presidio anonymization', color: '#6366f1' },
            { step: '03', label: 'Extract', desc: 'Gemini structured parsing', color: '#8b5cf6' },
            { step: '04', label: 'Evaluate', desc: 'Rule-based comparison', color: '#f59e0b' },
            { step: '05', label: 'Review', desc: 'Human-in-the-loop decision', color: '#f97316' },
            { step: '06', label: 'Demask', desc: 'Restore PII, write to DB', color: '#10b981' },
          ].map(({ step, label, desc, color }) => (
            <div key={step} className="card" style={{ padding: '1rem', textAlign: 'center' }}>
              <div style={{
                fontSize: '0.6rem',
                color,
                fontWeight: 800,
                letterSpacing: '0.1em',
                marginBottom: '0.25rem',
              }}>
                STEP {step}
              </div>
              <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                {label}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                {desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <div className="section-title">Quick Actions</div>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={() => navigate('/new-verification')}>
            + New Verification
          </button>
          <button className="btn btn-outline" onClick={() => navigate('/queue')}>
            Review Queue
            {stats?.needs_review > 0 && (
              <span style={{
                background: '#8b5cf6',
                color: 'white',
                borderRadius: '100px',
                padding: '1px 8px',
                fontSize: '0.7rem',
                fontWeight: 700,
              }}>
                {stats.needs_review}
              </span>
            )}
          </button>
          <button className="btn btn-outline" onClick={() => navigate('/applicants')}>
            Manage Applicants
          </button>
        </div>
      </div>
    </div>
  )
}
