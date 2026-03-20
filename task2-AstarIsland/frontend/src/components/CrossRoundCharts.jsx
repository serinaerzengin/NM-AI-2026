import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { fetchInitialState, fetchGroundTruth, fetchEvalData } from '../api'
import { computeCrossRoundStats } from '../stats'

const tipStyle = { background: '#1c2128', border: '1px solid #30363d', borderRadius: 6, color: '#e1e4e8' }
const tipLabel = { color: '#e1e4e8' }
const tipItem = { color: '#c9d1d9' }

export default function CrossRoundCharts({ rounds }) {
  const [data, setData] = useState(null)
  const [evalData, setEvalData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!rounds.length) return
    setLoading(true)

    // Only load rounds that have ground truth
    const completedRounds = rounds.filter(r => r.seeds.some(s => s.hasGT))

    Promise.all([
      Promise.all(
        completedRounds.map(async (r) => {
          const seeds = await Promise.all(
            r.seeds.filter(s => s.hasGT).map(async (s) => {
              const [initialState, groundTruth] = await Promise.all([
                fetchInitialState(r.round_number, s.index),
                fetchGroundTruth(r.round_number, s.index),
              ])
              return { initialState, groundTruth }
            })
          )
          return { roundNumber: r.round_number, seeds }
        })
      ),
      fetchEvalData(),
    ]).then(([allData, ev]) => {
      setData(computeCrossRoundStats(allData))
      setEvalData(ev)
      setLoading(false)
    })
  }, [rounds])

  if (loading || !data) return <div className="loading">Loading cross-round data...</div>
  if (!data.length) return <div className="loading">No completed rounds with ground truth yet.</div>

  // Merge eval scores into data
  const mergedData = data.map(d => {
    const fit = evalData?.fit?.calibration?.find(c => c.round === d.round)
    const tuned = evalData?.tuned?.results?.[`round_${d.round}`]
    return {
      ...d,
      fitScore: fit?.best_score ?? null,
      fitRate: fit?.best_expansion_rate ?? null,
      tunedScore: tuned?.mean_score ?? null,
      tunedRate: tuned?.rate ?? null,
    }
  })

  return (
    <div className="stats-grid">
      {/* Summary table */}
      <div className="chart-card" style={{ gridColumn: '1 / -1' }}>
        <h3>Round Summary</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8, fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #30363d' }}>
                {['Round', 'Regime', 'Settle Rate', 'S→Empty', 'S→Settle', 'S→Forest', 'Forest Ret.', 'Entropy', 'Dynamic', 'Fit Score', 'Tuned Score'].map(h => (
                  <th key={h} style={{ textAlign: h === 'Round' || h === 'Regime' ? 'left' : 'right', padding: '6px 8px', color: '#8b949e', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mergedData.map(d => {
                const regimeColor = d.settleToSettle > 30 ? '#22c55e' : d.settleToSettle < 5 ? '#ef4444' : '#e8a838'
                const regime = d.settleToSettle > 30 ? 'High' : d.settleToSettle < 5 ? 'Collapse' : d.settleToSettle > 20 ? 'Med-High' : 'Medium'
                return (
                  <tr key={d.round} style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px' }}>R{d.round}</td>
                    <td style={{ padding: '6px 8px', color: regimeColor, fontWeight: 600 }}>{regime}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.observedSettleRate}%</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.settleToEmpty}%</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#e8a838' }}>{d.settleToSettle}%</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#22c55e' }}>{d.settleToForest}%</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.forestRetention}%</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.avgEntropy}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.dynamicCells}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#58a6ff' }}>{d.fitScore ?? '—'}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', color: '#c084fc' }}>{d.tunedScore ?? '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {evalData?.fit?.rate_mapping && (
          <p style={{ color: '#8b949e', fontSize: '0.8rem', marginTop: 8 }}>
            Rate mapping: expansion_rate = {evalData.fit.rate_mapping.slope} × settle_rate + {evalData.fit.rate_mapping.intercept}
            {evalData?.tuned?.mean_score && <> | Tuned mean: <span style={{ color: '#c084fc' }}>{evalData.tuned.mean_score}</span></>}
          </p>
        )}
      </div>

      {/* Settlement fate stacked bar */}
      <div className="chart-card">
        <h3>Settlement Fate Across Rounds</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={mergedData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="label" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabel} itemStyle={tipItem} formatter={(v) => `${v}%`} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#8b949e' }} />
            <Bar dataKey="settleToEmpty" name="→ Empty" stackId="a" fill="#6b7280" />
            <Bar dataKey="settleToSettle" name="→ Settle/Port" stackId="a" fill="#e8a838" />
            <Bar dataKey="settleToForest" name="→ Forest" stackId="a" fill="#22c55e" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Simulator scores */}
      {mergedData.some(d => d.tunedScore != null) && (
        <div className="chart-card">
          <h3>Simulator Score vs Ground Truth</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={mergedData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
              <XAxis dataKey="label" tick={{ fill: '#8b949e', fontSize: 12 }} />
              <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
              <Tooltip contentStyle={tipStyle} labelStyle={tipLabel} itemStyle={tipItem} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#8b949e' }} />
              <Bar dataKey="fitScore" name="Best fit" fill="#58a6ff" radius={[3, 3, 0, 0]} />
              <Bar dataKey="tunedScore" name="Tuned v1" fill="#c084fc" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
