import { useState } from 'react'
import { ShieldCheck, ArrowRight, Loader } from 'lucide-react'

export default function Login({ onLogin }) {
  const [loading, setLoading] = useState(false)

  const handleDemoLogin = (e) => {
    e.preventDefault()
    setLoading(true)
    // Simulate network request for premium feel
    setTimeout(() => {
      onLogin()
    }, 800)
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-base)',
      padding: '1rem',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Decorative background elements */}
      <div style={{
        position: 'absolute',
        top: '10%',
        left: '15%',
        width: '400px',
        height: '400px',
        background: 'var(--accent-1)',
        filter: 'blur(120px)',
        opacity: 0.1,
        borderRadius: '50%',
        zIndex: 0,
        pointerEvents: 'none'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '10%',
        right: '15%',
        width: '500px',
        height: '500px',
        background: 'var(--accent-2)',
        filter: 'blur(150px)',
        opacity: 0.08,
        borderRadius: '50%',
        zIndex: 0,
        pointerEvents: 'none'
      }} />

      <div className="card animate-fade-in" style={{
        width: '100%',
        maxWidth: '440px',
        padding: '2.5rem',
        position: 'relative',
        zIndex: 1,
        border: '1px solid rgba(255,255,255,0.05)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(12px)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            width: '64px',
            height: '64px',
            background: 'rgba(99, 102, 241, 0.1)',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem',
            border: '1px solid rgba(99, 102, 241, 0.2)'
          }}>
            <ShieldCheck size={32} style={{ color: 'var(--accent-1)' }} />
          </div>
          <h1 style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            marginBottom: '0.5rem'
          }}>
            Aegis HR
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            Agentic Background Verification System
          </p>
        </div>

        <form onSubmit={handleDemoLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              placeholder="hr@company.com" 
              disabled 
              style={{ opacity: 0.7, cursor: 'not-allowed' }}
              defaultValue="demo.admin@aegis-hr.com"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder="••••••••" 
              disabled 
              style={{ opacity: 0.7, cursor: 'not-allowed' }}
              defaultValue="password123"
            />
          </div>

          <div style={{ marginTop: '0.5rem' }}>
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ 
                width: '100%', 
                padding: '0.875rem',
                fontSize: '1rem',
                display: 'flex',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader size={18} className="animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Login as Demo HR Admin
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </form>

        <div style={{ 
          marginTop: '2rem', 
          textAlign: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-muted)'
        }}>
          <p>This is a portfolio demonstration.</p>
          <p style={{ marginTop: '0.25rem' }}>Clicking login will bypass actual authentication.</p>
        </div>
      </div>
    </div>
  )
}
