import { useEffect, useState } from 'react'
import axios from 'axios'

export default function Cards() {
  const [cards, setCards] = useState<any[]>([])
  const [form, setForm] = useState({ name: '', issuer: '', network: '', annual_fee: 0, rewards: '', country: '' })
  const token = localStorage.getItem('token')
  const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL, headers: { Authorization: `Bearer ${token}` } })

  const load = async () => { const r = await api.get('/cards/'); setCards(r.data) }

  useEffect(() => { load() }, [])

  const create = async () => { await api.post('/cards/', form); setForm({ name: '', issuer: '', network: '', annual_fee: 0, rewards: '', country: '' }); await load() }

  return (
    <div>
      <h2>Cards</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8, marginBottom: 12 }}>
        <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input placeholder="Issuer" value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} />
        <input placeholder="Network" value={form.network} onChange={(e) => setForm({ ...form, network: e.target.value })} />
        <input placeholder="Annual Fee" type="number" value={form.annual_fee} onChange={(e) => setForm({ ...form, annual_fee: Number(e.target.value) })} />
        <input placeholder="Rewards" value={form.rewards} onChange={(e) => setForm({ ...form, rewards: e.target.value })} />
        <input placeholder="Country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
      </div>
      <button onClick={create}>Create</button>
      <table>
        <thead><tr><th>Name</th><th>Issuer</th><th>Network</th><th>Fee</th><th>Rewards</th><th>Country</th></tr></thead>
        <tbody>
          {cards.map((c) => (
            <tr key={c.id}><td>{c.name}</td><td>{c.issuer}</td><td>{c.network}</td><td>{c.annual_fee}</td><td>{c.rewards}</td><td>{c.country}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}