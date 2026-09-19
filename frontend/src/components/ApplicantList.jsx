import { useState, useEffect } from 'react'
import { Plus, ChevronDown, ChevronRight } from 'lucide-react'
import { getApplicants, createApplicant } from '../lib/api'
import VerificationStatusBadge from './VerificationStatusBadge'

const DOC_TYPE_LABELS = {
  bank_statement: 'Bank Statement',
  epfo_history:   'EPFO History',
  cv_resume:      'CV / Resume',
}

function ApplicantRow({ applicant }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr>
        <td>
          <button
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', marginRight: '0.5rem' }}
            onClick={() => setExpanded(e => !e)}
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{applicant.full_name}</span>
        </td>
        <td>{applicant.email}</td>
        <td>
          <span className="tag">{applicant.documents?.length || 0} docs</span>
        </td>
        <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {new Date(applicant.created_at).toLocaleDateString()}
        </td>
        <td>
          {applicant.offer_reference_data?.expected_employer && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {applicant.offer_reference_data.expected_employer}
            </span>
          )}
        </td>
      </tr>
      {expanded && applicant.documents?.map(doc => (
        <tr key={doc.id} style={{ background: 'rgba(99,102,241,0.03)' }}>
          <td style={{ paddingLeft: '3rem' }}>
            <span className="tag">{DOC_TYPE_LABELS[doc.type] || doc.type}</span>
          </td>
          <td colSpan={2}>
            <VerificationStatusBadge status={doc.status} />
          </td>
          <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {new Date(doc.created_at).toLocaleDateString()}
          </td>
          <td>
            {doc.thread_id && (
              <code style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {doc.thread_id.slice(0, 8)}…
              </code>
            )}
          </td>
        </tr>
      ))}
    </>
  )
}

function AddApplicantModal({ onClose, onAdd }) {
  const [form, setForm] = useState({
    full_name: '', email: '',
    expected_employer: '', applicant_name_ref: '',
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createApplicant({
        full_name: form.full_name,
        email: form.email,
        offer_reference_data: {
          applicant_name: form.applicant_name_ref || form.full_name,
          expected_employer: form.expected_employer,
        },
      })
      onAdd()
      onClose()
    } catch (err) {
      alert('Failed to create applicant: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      z: 1000, zIndex: 1000,
    }}>
      <div className="card" style={{ width: '480px', maxWidth: '95vw' }}>
        <h3 style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '1.25rem' }}>
          Add New Applicant
        </h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input id="applicant-name" className="form-input" required
              value={form.full_name}
              onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input id="applicant-email" className="form-input" type="email" required
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Expected Employer (for evaluation)</label>
            <input id="applicant-employer" className="form-input"
              placeholder="e.g. TechCorp Ltd"
              value={form.expected_employer}
              onChange={e => setForm(f => ({ ...f, expected_employer: e.target.value }))}
            />
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button id="save-applicant-btn" type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Create Applicant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function ApplicantList() {
  const [applicants, setApplicants] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  const fetchApplicants = async () => {
    setLoading(true)
    try {
      const { data } = await getApplicants()
      setApplicants(data.applicants || [])
    } catch {
      setApplicants([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchApplicants() }, [])

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div>
          <h2 className="page-title">Applicants</h2>
          <p className="page-subtitle">All registered applicants and their document statuses</p>
        </div>
        <button id="add-applicant-btn" className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} /> Add Applicant
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <div className="spinner" />
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Documents</th>
                <th>Joined</th>
                <th>Expected Employer</th>
              </tr>
            </thead>
            <tbody>
              {applicants.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No applicants yet. Add one to get started.
                  </td>
                </tr>
              ) : (
                applicants.map(a => <ApplicantRow key={a.id} applicant={a} />)
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <AddApplicantModal onClose={() => setShowModal(false)} onAdd={fetchApplicants} />
      )}
    </div>
  )
}
