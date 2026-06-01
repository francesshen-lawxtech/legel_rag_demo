import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { checkHealth } from '../../api/client'

export default function Navbar() {
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    checkHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-logo">
        <span className="logo-icon">⚖️</span>
        Legal RAG Demo
      </NavLink>

      <div className="navbar-nav">
        <NavLink
          to="/search"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          🔍 智能搜尋
        </NavLink>
        <NavLink
          to="/ask"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          💬 RAG 問答
        </NavLink>
        <NavLink
          to="/analysis"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          📋 合約分析
        </NavLink>
      </div>

      <div className="navbar-right">
        <span className={`status-dot${online === false ? ' offline' : ''}`} />
        <span className="status-label">
          {online === null ? '連線中...' : online ? 'API 運行中' : 'API 離線'}
        </span>
      </div>
    </nav>
  )
}
