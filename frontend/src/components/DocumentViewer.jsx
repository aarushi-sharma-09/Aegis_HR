import { useState } from 'react'
import { FileText, Image, ExternalLink, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

export default function DocumentViewer({ fileUrl, documentType }) {
  const [zoom, setZoom] = useState(100)
  const fullUrl = fileUrl?.startsWith('http') ? fileUrl : fileUrl

  const isPdf = fileUrl?.toLowerCase().endsWith('.pdf')

  const handleZoomIn  = () => setZoom(z => Math.min(z + 20, 200))
  const handleZoomOut = () => setZoom(z => Math.max(z - 20, 40))
  const handleReset   = () => setZoom(100)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {isPdf
            ? <FileText size={15} style={{ color: 'var(--accent-1)' }} />
            : <Image size={15} style={{ color: 'var(--accent-3)' }} />}
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            {documentType?.replace('_', ' ').toUpperCase() || 'DOCUMENT'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{zoom}%</span>
          <button className="btn btn-outline" style={{ padding: '0.25rem 0.5rem' }} onClick={handleZoomOut}>
            <ZoomOut size={13} />
          </button>
          <button className="btn btn-outline" style={{ padding: '0.25rem 0.5rem' }} onClick={handleZoomIn}>
            <ZoomIn size={13} />
          </button>
          <button className="btn btn-outline" style={{ padding: '0.25rem 0.5rem' }} onClick={handleReset}>
            <RotateCcw size={13} />
          </button>
          <a
            href={fullUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline"
            style={{ padding: '0.25rem 0.5rem' }}
          >
            <ExternalLink size={13} />
          </a>
        </div>
      </div>

      {/* Document display */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        background: '#1a1a2e',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        padding: '1rem',
      }}>
        {!fileUrl ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: '4rem' }}>
            <FileText size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p>No document available</p>
          </div>
        ) : isPdf ? (
          <iframe
            id="document-iframe"
            src={fullUrl}
            style={{
              width: `${zoom}%`,
              minWidth: '100%',
              height: '100%',
              minHeight: '600px',
              border: 'none',
              borderRadius: '4px',
              background: 'white',
            }}
            title="Uploaded document"
          />
        ) : (
          <img
            id="document-image"
            src={fullUrl}
            alt="Uploaded document"
            style={{
              width: `${zoom}%`,
              maxWidth: '100%',
              borderRadius: '4px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
            }}
          />
        )}
      </div>
    </div>
  )
}
