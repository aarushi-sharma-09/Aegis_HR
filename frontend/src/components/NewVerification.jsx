import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import { getApplicants, uploadDocument } from '../lib/api'
import { useEffect } from 'react'

const DOC_TYPES = [
  { value: 'bank_statement', label: 'Bank Statement', desc: 'Last 3-6 months bank statement (PDF/image)' },
  { value: 'epfo_history',   label: 'EPFO History',   desc: 'EPFO passbook / UAN statement' },
  { value: 'cv_resume',      label: 'CV / Resume',    desc: 'Updated resume or CV' },
]

export default function NewVerification() {
  const [applicants, setApplicants] = useState([])
  const [form, setForm] = useState({ applicant_id: '', document_type: 'cv_resume' })
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileRef = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    getApplicants().then(({ data }) => setApplicants(data.applicants || []))
  }, [])

  const handleFile = (f) => {
    if (!f) return
    const allowed = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
    if (!allowed.includes(f.type)) {
      setError('Only PDF, PNG, JPG files are supported')
      return
    }
    setFile(f)
    setError(null)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) { setError('Please select a file'); return }
    if (!form.applicant_id) { setError('Please select an applicant'); return }

    setSubmitting(true)
    setError(null)
    setResult(null)

    const fd = new FormData()
    fd.append('file', file)
    fd.append('applicant_id', form.applicant_id)
    fd.append('document_type', form.document_type)

    try {
      const { data } = await uploadDocument(fd)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    const needsReview = result.status === 'NEEDS_REVIEW'
    return (
      <div className="animate-fade-in" style={{ maxWidth: 560, margin: '0 auto', paddingTop: '3rem' }}>
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          {needsReview ? (
            <AlertCircle size={56} style={{ color: 'var(--status-review)', margin: '0 auto 1rem' }} />
          ) : (
            <CheckCircle size={56} style={{ color: 'var(--status-verified)', margin: '0 auto 1rem' }} />
          )}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {needsReview ? 'Review Required' : 'Verification Complete'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            {needsReview
              ? `${result.discrepancy_count} discrepancies found — document routed to review queue.`
              : 'Document passed all checks and has been verified.'}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            {needsReview && (
              <button className="btn btn-primary" onClick={() => navigate(`/review/${result.thread_id}`)}>
                Open Review
              </button>
            )}
            <button className="btn btn-outline" onClick={() => { setResult(null); setFile(null) }}>
              Upload Another
            </button>
            <button className="btn btn-outline" onClick={() => navigate('/dashboard')}>
              Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 640, margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">New Verification</h2>
          <p className="page-subtitle">Start the agentic BGV pipeline for an applicant document</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>

        {/* Applicant selector */}
        <div className="form-group">
          <label className="form-label" htmlFor="applicant-select">Applicant</label>
          <select
            id="applicant-select"
            className="form-select"
            value={form.applicant_id}
            onChange={e => setForm(f => ({ ...f, applicant_id: e.target.value }))}
            required
          >
            <option value="">Select an applicant…</option>
            {applicants.map(a => (
              <option key={a.id} value={a.id}>{a.full_name} ({a.email})</option>
            ))}
          </select>
        </div>

        {/* Document type */}
        <div className="form-group">
          <label className="form-label">Document Type</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {DOC_TYPES.map(({ value, label, desc }) => (
              <label
                key={value}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                  padding: '0.875rem 1rem',
                  borderRadius: '8px',
                  border: `1px solid ${form.document_type === value ? 'var(--accent-1)' : 'var(--border)'}`,
                  background: form.document_type === value ? 'rgba(99,102,241,0.06)' : 'var(--bg-elevated)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <input
                  type="radio"
                  name="doc_type"
                  value={value}
                  checked={form.document_type === value}
                  onChange={() => setForm(f => ({ ...f, document_type: value }))}
                  style={{ marginTop: 3, accentColor: 'var(--accent-1)' }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>{desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* File drop zone */}
        <div className="form-group">
          <label className="form-label">Document File</label>
          <div
            className={`dropzone${dragOver ? ' active' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              id="file-input"
              ref={fileRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files[0])}
            />
            {file ? (
              <div>
                <FileText size={32} style={{ margin: '0 auto 0.75rem', color: 'var(--accent-1)' }} />
                <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{file.name}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {(file.size / 1024).toFixed(0)} KB — click to change
                </p>
              </div>
            ) : (
              <div>
                <UploadCloud size={40} style={{ margin: '0 auto 0.75rem', color: 'var(--text-muted)', opacity: 0.5 }} />
                <p style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                  Drag & drop or click to select
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Supported: PDF, PNG, JPG
                </p>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div style={{
            padding: '0.75rem 1rem',
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.2)',
            borderRadius: '8px',
            color: '#f87171',
            fontSize: '0.875rem',
            marginBottom: '1rem',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <AlertCircle size={15} /> {error}
          </div>
        )}

        <button
          id="start-verification-btn"
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ alignSelf: 'flex-end', minWidth: 180 }}
        >
          {submitting ? (
            <>
              <Loader size={14} className="animate-spin" />
              Running Pipeline…
            </>
          ) : (
            '→ Start Verification'
          )}
        </button>

        {submitting && (
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: '0.5rem' }}>
            OCR → PII Masking → Gemini Extraction → Rule Evaluation…
          </p>
        )}
      </form>
    </div>
  )
}
