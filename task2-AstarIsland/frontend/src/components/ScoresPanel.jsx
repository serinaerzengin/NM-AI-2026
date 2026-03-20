import { useState, useEffect } from 'react'
import { fetchMyRounds } from '../api'

export default function ScoresPanel() {
  const [rounds, setRounds] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMyRounds().then(data => {
      setRounds(data.sort((a, b) => a.round_number - b.round_number))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Loading scores from API...</div>
  if (!rounds.length) return null

  const scored = rounds.filter(r => r.round_score != null)
  const bestRound = scored.length > 0 ? scored.reduce((a, b) => a.round_score > b.round_score ? a : b) : null

  return (
    <div style={{ marginBottom: 24 }}>
      {/* Competition scores table */}
      <div className="chart-card" style={{ marginBottom: 16 }}>
        <h3>Competition Scores</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8, fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #30363d' }}>
                {['Round', 'Status', 'Score', 'Rank', 'Seeds', 'Queries', 'Weight'].map(h => (
                  <th key={h} style={{ textAlign: h === 'Round' || h === 'Status' ? 'left' : 'right', padding: '6px 10px', color: '#8b949e', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rounds.map(r => (
                <tr key={r.round_number} style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '6px 10px', fontWeight: 600 }}>R{r.round_number}</td>
                  <td style={{ padding: '6px 10px' }}>
                    <span style={{
                      color: r.status === 'active' ? '#22c55e' : r.seeds_submitted > 0 ? '#58a6ff' : '#8b949e',
                      fontWeight: r.status === 'active' ? 600 : 400,
                    }}>
                      {r.status === 'active' ? 'ACTIVE' : r.seeds_submitted > 0 ? 'submitted' : 'skipped'}
                    </span>
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 700, fontSize: '1rem', color: r.round_score != null ? '#e8a838' : '#8b949e' }}>
                    {r.round_score != null ? r.round_score.toFixed(1) : '—'}
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                    {r.rank != null ? `${r.rank}/${r.total_teams}` : '—'}
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                    {r.seeds_submitted}/{r.seeds_count}
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                    {r.queries_used}/{r.queries_max}
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                    {r.round_weight?.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-seed scores for rounds that have them */}
      {scored.map(r => (
        <div key={r.round_number} className="chart-card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <h3>Round {r.round_number} — Per-Seed Scores</h3>
            <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Rank {r.rank}/{r.total_teams}</span>
          </div>
          <div style={{ marginTop: 8 }}>
            {r.seed_scores.map((score, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                <span style={{ color: '#8b949e', fontSize: '0.85rem', width: 50 }}>Seed {i + 1}</span>
                <div style={{ flex: 1, background: '#21262d', borderRadius: 4, height: 20, position: 'relative' }}>
                  <div style={{
                    width: `${score}%`,
                    background: 'linear-gradient(90deg, #e8a838, #f59e0b)',
                    borderRadius: 4,
                    height: '100%',
                    transition: 'width 0.3s',
                  }} />
                </div>
                <span style={{ color: '#e1e4e8', fontWeight: 600, fontSize: '0.9rem', width: 45, textAlign: 'right' }}>{score.toFixed(1)}</span>
              </div>
            ))}
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #30363d', marginTop: 8, paddingTop: 8 }}>
              <span style={{ fontWeight: 600 }}>Average</span>
              <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#e8a838' }}>{r.round_score.toFixed(1)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
