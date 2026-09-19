const STATUS_MAP = {
  VERIFIED:      { cls: 'badge-verified',   label: 'Verified'     },
  PENDING:       { cls: 'badge-pending',    label: 'Pending'      },
  REJECTED:      { cls: 'badge-rejected',   label: 'Rejected'     },
  NEEDS_REVIEW:  { cls: 'badge-review',     label: 'Needs Review' },
  NEEDS_FALLBACK:{ cls: 'badge-fallback',   label: 'Fallback'     },
  PROCESSING:    { cls: 'badge-processing', label: 'Processing'   },
  PASSED:        { cls: 'badge-verified',   label: 'Passed'       },
}

export default function VerificationStatusBadge({ status }) {
  const { cls, label } = STATUS_MAP[status] || { cls: 'badge-pending', label: status || 'Unknown' }
  return <span className={`badge ${cls}`}>{label}</span>
}
