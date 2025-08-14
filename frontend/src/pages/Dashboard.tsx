import { useEffect, useState } from 'react'
import axios from 'axios'

export default function Dashboard() {
  const [health, setHealth] = useState('unknown')
  const [jobs, setJobs] = useState<any[]>([])
  const token = localStorage.getItem('token')

  const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    headers: { Authorization: `Bearer ${token}` },
  })

  const load = async () => {
    const ok = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/health`)
    setHealth(ok.data.status)
    const j = await api.get('/scrape/jobs')
    setJobs(j.data)
  }

  useEffect(() => {
    load()
  }, [])

  const triggerCards = async () => { await api.post('/scrape/cards'); await load() }
  const triggerVisas = async () => { await api.post('/scrape/visas'); await load() }

  return (
    <div>
      <h2>Dashboard</h2>
      <div>API health: {health}</div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button onClick={triggerCards}>Scrape Cards</button>
        <button onClick={triggerVisas}>Scrape Visas</button>
      </div>
      <h3 style={{ marginTop: 16 }}>Recent Jobs</h3>
      <table>
        <thead><tr><th>ID</th><th>Type</th><th>Status</th><th>Source</th><th>Error</th></tr></thead>
        <tbody>
          {jobs.map(j => (
            <tr key={j.id}><td>{j.id}</td><td>{j.type}</td><td>{j.status}</td><td>{j.source}</td><td style={{ color: 'crimson' }}>{j.error}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}