import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, ClipboardList, Users, PlusCircle, ShieldCheck, LogOut
} from 'lucide-react'

const navItems = [
  { to: '/dashboard',        icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/queue',            icon: ClipboardList,   label: 'Review Queue' },
  { to: '/applicants',       icon: Users,           label: 'Applicants' },
  { to: '/new-verification', icon: PlusCircle,      label: 'New Verification' },
]

export default function Sidebar({ onLogout }) {
  return (
    <nav className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <ShieldCheck size={22} style={{ color: 'var(--accent-1)' }} />
          <h1>Aegis HR</h1>
        </div>
        <p>Background Verification System</p>
        <p style={{ marginTop: '0.5rem', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
          Aarushi Sharma · 2301010185
        </p>
      </div>

      {/* Nav links */}
      <div style={{ flex: 1 }}>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon className="nav-icon" />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        padding: '1rem 1.5rem',
        borderTop: '1px solid var(--border)',
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        lineHeight: 1.5,
      }}>
        <div style={{ marginBottom: '0.75rem' }}>
          <button 
            onClick={onLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '0.25rem 0',
              fontWeight: 500,
              transition: 'color 0.15s'
            }}
            onMouseOver={(e) => e.currentTarget.style.color = 'var(--status-review)'}
            onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
          >
            <LogOut size={14} />
            Sign Out Demo HR
          </button>
        </div>
        <div>Powered by</div>
        <div style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
          LangGraph · Gemini · FastAPI
        </div>
      </div>
    </nav>
  )
}
