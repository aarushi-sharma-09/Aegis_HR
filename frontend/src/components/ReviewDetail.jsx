import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, X, AlertTriangle, FileText } from 'lucide-react'
import { getReviewDetail, resolveReview, fallbackUpload } from '../lib/api'
import VerificationStatusBadge from './VerificationStatusBadge'
import AgentReasoningPanel from './AgentReasoningPanel'
import DocumentViewer from './DocumentViewer'

export default function ReviewDetail() {
  const { threadId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [resolving, setResolving] = useState(false)
  const [notes, setNotes] = useState('')
  const [toast, setToast] = useState(null)
  const [fallbackFile, setFallbackFile] = useState(null)
  const [uploadingFallback, setUploadingFallback] = useState(false)

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data: d } = await getReviewDetail(threadId)
        setData(d)
      } catch (e) {
        showToast('Failed to load review data', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [threadId])

  const handleResolve = async (decision) => {
    if (!window.confirm(`Confirm ${decision} for this document?`)) return
    setResolving(true)
    try {
      await resolveReview(threadId, decision, notes)
      showToast(`Document ${decision === 'APPROVED' ? 'approved ✓' : 'rejected ✗'}`, 
        decision === 'APPROVED' ? 'success' : 'error')
      setTimeout(() => navigate('/queue'), 1500)
    } catch {
      showToast('Failed to submit decision', 'error')
    } finally {
      setResolving(false)
    }
  }

  const handleFallbackUpload = async () => {
    if (!fallbackFile) return
    setUploadingFallback(true)
    const fd = new FormData()
    fd.append('file', fallbackFile)
    try {
      await fallbackUpload(data.document.id, fd)
      showToast('New evidence uploaded — pipeline restarted', 'success')
      setTimeout(() => navigate('/queue'), 1500)
    } catch {
      showToast('Upload failed', 'error')
    } finally {
      setUploadingFallback(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '6rem' }}>
      <div className="spinner" />
    </div>
  )

  if (!data) return null

  const { document: doc, applicant, reasoning, discrepancies, extracted_data, evaluation_result } = data
  const isFallback = doc.status === 'NEEDS_FALLBACK'

  return (
    <div className="animate-fade-in" style={{ height: '100%' }}>
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn btn-outline" onClick={() => navigate('/queue')} style={{ padding: '0.4rem 0.75rem' }}>
            <ArrowLeft size={15} />
          </button>
          <div>
            <h2 className="page-title">{applicant.name}</h2>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.25rem' }}>
              <span className="tag">{doc.type.replace('_', ' ').toUpperCase()}</span>
              <VerificationStatusBadge status={doc.status} />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Thread: <code style={{ fontFamily: 'monospace' }}>{threadId?.slice(0, 12)}…</code>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Split Screen */}
      <div className="split-screen">
        {/* LEFT — Document Viewer */}
        <div className="split-pane">
          <DocumentViewer fileUrl={doc.file_url} documentType={doc.type} />
        </div>

        {/* RIGHT — Agent Reasoning Panel */}
        <div className="split-pane" style={{ display: 'flex', flexDirection: 'column' }}>
          <AgentReasoningPanel
            reasoning={reasoning}
            discrepancies={discrepancies}
            extractedData={extracted_data}
            referenceData={applicant.reference_data}
            evaluationResult={evaluation_result}
          />

          {/* ── Action Controls ── */}
          <div style={{
            padding: '1.25rem',
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-elevated)',
            flexShrink: 0,
          }}>
            {isFallback ? (
              // Fallback upload
              <div>
                <p className="section-title" style={{ marginBottom: '0.75rem' }}>
                  Upload Additional Evidence
                </p>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <input
                    id="fallback-file-input"
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={e => setFallbackFile(e.target.files[0])}
                    style={{ flex: 1, fontSize: '0.8rem', color: 'var(--text-secondary)' }}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handleFallbackUpload}
                    disabled={!fallbackFile || uploadingFallback}
                  >
                    {uploadingFallback ? 'Uploading…' : 'Re-trigger Pipeline'}
                  </button>
                </div>
              </div>
            ) : (
              // Approve / Reject
              <div>
                <div className="form-group" style={{ marginBottom: '0.875rem' }}>
                  <label className="form-label">Admin Notes (optional)</label>
                  <textarea
                    id="admin-notes"
                    className="form-textarea"
                    placeholder="Add your review notes here…"
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    style={{ minHeight: '60px' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    id="approve-btn"
                    className="btn btn-success"
                    style={{ flex: 1 }}
                    onClick={() => handleResolve('APPROVED')}
                    disabled={resolving}
                  >
                    <Check size={15} />
                    {resolving ? 'Processing…' : 'Approve'}
                  </button>
                  <button
                    id="reject-btn"
                    className="btn btn-danger"
                    style={{ flex: 1 }}
                    onClick={() => handleResolve('REJECTED')}
                    disabled={resolving}
                  >
                    <X size={15} />
                    Reject
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast-container">
          <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
        </div>
      )}
    </div>
  )
}
