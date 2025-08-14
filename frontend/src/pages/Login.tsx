import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const register = async () => {
    try {
      await axios.post(`${import.meta.env.VITE_API_BASE_URL}/auth/register`, { email, password })
      await login()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Register failed')
    }
  }

  const login = async () => {
    try {
      const form = new URLSearchParams()
      form.append('username', email)
      form.append('password', password)
      const r = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/auth/login`, form)
      localStorage.setItem('token', r.data.access_token)
      navigate('/')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: '80px auto' }}>
      <h2>Login</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <div style={{ color: 'red' }}>{error}</div>}
        <button onClick={login}>Login</button>
        <button onClick={register}>Register</button>
      </div>
    </div>
  )
}