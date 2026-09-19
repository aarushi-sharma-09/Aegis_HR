import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import ReviewQueue from './components/ReviewQueue'
import ReviewDetail from './components/ReviewDetail'
import ApplicantList from './components/ApplicantList'
import NewVerification from './components/NewVerification'
import Login from './components/Login'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Check auth state on mount
  useEffect(() => {
    const auth = localStorage.getItem('auth')
    if (auth === 'true') {
      setIsAuthenticated(true)
    }
  }, [])

  const handleLogin = () => {
    localStorage.setItem('auth', 'true')
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth')
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <BrowserRouter>
      <div className="layout">
        <Sidebar onLogout={handleLogout} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/queue" element={<ReviewQueue />} />
            <Route path="/review/:threadId" element={<ReviewDetail />} />
            <Route path="/applicants" element={<ApplicantList />} />
            <Route path="/new-verification" element={<NewVerification />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
