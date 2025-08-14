import { useEffect, useState } from 'react'
import axios from 'axios'

export default function Visas() {
  const [visas, setVisas] = useState<any[]>([])
  const [form, setForm] = useState({ from_country: '', to_country: '', requirement: '', source: '' })
  const token = localStorage.getItem('token')
  const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL, headers: { Authorization: `Bearer ${token}` } })

  const load = async () => { const r = await api.get('/visas/'); setVisas(r.data) }

  useEffect(() => { load() }, [])

  const create = async () => { await api.post('/visas/', form); setForm({ from_country: '', to_country: '', requirement: '', source: '' }); await load() }

  return (
    <div>
      <h2>Visas</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
        <input placeholder="From" value={form.from_country} onChange={(e) => setForm({ ...form, from_country: e.target.value })} />
        <input placeholder="To" value={form.to_country} onChange={(e) => setForm({ ...form, to_country: e.target.value })} />
        <input placeholder="Requirement" value={form.requirement} onChange={(e) => setForm({ ...form, requirement: e.target.value })} />
        <input placeholder="Source" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
      </div>
      <button onClick={create}>Create</button>
      <table>
        <thead><tr><th>From</th><th>To</th><th>Requirement</th><th>Source</th></tr></thead>
        <tbody>
          {visas.map((v) => (
            <tr key={v.id}><td>{v.from_country}</td><td>{v.to_country}</td><td>{v.requirement}</td><td>{v.source}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}