import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Eye, Clock, AlertTriangle } from 'lucide-react'
import { getReviewQueue } from '../lib/api'
import VerificationStatusBadge from './VerificationStatusBadge'

const DOC_TYPE_LABELS = {
  bank_statement: 'Bank Statement',
  epfo_history:   'EPFO History',
  cv_resume:      'CV / Resume',
}

export default function ReviewQueue() {
  const [queue, setQueue] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const navigate = useNavigate()

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const { data } = await getReviewQueue()
      setQueue(data.queue || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [])

  const filtered = filter === 'ALL'
    ? queue
    : queue.filter(d => d.verification_status === filter)

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h2 className="page-title">Review Queue</h2>
          <p className="page-subtitle">
            Documents awaiting human review — sorted oldest first
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {/* Filter pills */}
          {['ALL', 'NEEDS_REVIEW', 'NEEDS_FALLBACK'].map(f => (
            <button
              key={f}
              className={`btn ${filter === f ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '0.4rem 1rem', fontSize: '0.75rem' }}
              onClick={() => setFilter(f)}
            >
              {f === 'ALL' ? 'All' : f === 'NEEDS_REVIEW' ? 'Needs Review' : 'Needs Evidence'}
            </button>
          ))}
          <button className="btn btn-outline" onClick={fetchQueue} disabled={loading}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <div className="spinner" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <AlertTriangle size={48} />
          <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            No items in queue
          </p>
          <p style={{ fontSize: '0.875rem' }}>
            {filter === 'ALL' ? 'All documents have been reviewed.' : `No documents with status ${filter}.`}
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Document Type</th>
                <th>Status</th>
                <th>Age</th>
                <th>Thread ID</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => (
                <tr key={doc.document_id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {doc.applicant_name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {doc.applicant_email}
                    </div>
                  </td>
                  <td>
                    <span className="tag">
                      {DOC_TYPE_LABELS[doc.document_type] || doc.document_type}
                    </span>
                  </td>
                  <td>
                    <VerificationStatusBadge status={doc.verification_status} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Clock size={12} style={{ color: doc.age_hours > 24 ? '#ef4444' : 'var(--text-muted)' }} />
                      <span style={{ color: doc.age_hours > 24 ? '#ef4444' : 'inherit' }}>
                        {doc.age_hours < 1
                          ? `${Math.round(doc.age_hours * 60)}m ago`
                          : `${doc.age_hours.toFixed(1)}h ago`}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {doc.thread_id?.slice(0, 8)}…
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-primary"
                      style={{ padding: '0.4rem 0.875rem', fontSize: '0.8rem' }}
                      onClick={() => navigate(`/review/${doc.thread_id}`)}
                    >
                      <Eye size={14} />
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
