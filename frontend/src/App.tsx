import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

function isAuthed() {
  return !!localStorage.getItem('token')
}

export default function App() {
  const navigate = useNavigate()
  useEffect(() => {
    if (!isAuthed()) {
      navigate('/login')
    }
  }, [])

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div>
      <nav style={{ display: 'flex', gap: 12, padding: 12, borderBottom: '1px solid #ddd' }}>
        <Link to="/">Dashboard</Link>
        <Link to="/cards">Cards</Link>
        <Link to="/visas">Visas</Link>
        <span style={{ marginLeft: 'auto' }} />
        <button onClick={logout}>Logout</button>
      </nav>
      <main style={{ padding: 16 }}>
        <Outlet />
      </main>
    </div>
  )
}