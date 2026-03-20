import { useState, useEffect } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { fetchInitialState, fetchGroundTruth } from '../api'
import { computeCrossRoundStats } from '../stats'

const tipStyle = { background: '#1c2128', border: '1px solid #30363d', borderRadius: 6, color: '#e1e4e8' }
const tipLabelStyle = { color: '#e1e4e8' }
const tipItemStyle = { color: '#c9d1d9' }

export default function CrossRoundCharts({ rounds }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!rounds.length) return
    setLoading(true)
    Promise.all(
      rounds.map(async (r) => {
        const seeds = await Promise.all(
          r.seeds.map(async (s) => {
            const [initialState, groundTruth] = await Promise.all([
              fetchInitialState(r.round_number, s),
              fetchGroundTruth(r.round_number, s),
            ])
            return { initialState, groundTruth }
          })
        )
        return { roundNumber: r.round_number, seeds }
      })
    ).then(allData => {
      setData(computeCrossRoundStats(allData))
      setLoading(false)
    })
  }, [rounds])

  if (loading || !data) return <div className="loading">Loading cross-round data...</div>

  return (
    <div className="stats-grid">
      {/* Regime summary table */}
      <div className="chart-card">
        <h3>Expansion Regime per Round (Q13)</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8, fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #30363d' }}>
              <th style={{ textAlign: 'left', padding: '6px 8px', color: '#8b949e' }}>Round</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', color: '#8b949e' }}>Regime</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', color: '#8b949e' }}>→ Empty</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', color: '#8b949e' }}>→ Settle</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', color: '#8b949e' }}>→ Forest</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', color: '#8b949e' }}>Forest Ret.</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', color: '#8b949e' }}>Dyn. Cells</th>
            </tr>
          </thead>
          <tbody>
            {data.map(d => {
              const regimeColor = d.regime === 'High' ? '#22c55e'
                : d.regime === 'Collapse' ? '#ef4444' : '#e8a838'
              return (
                <tr key={d.round} style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '6px 8px' }}>{d.round}</td>
                  <td style={{ padding: '6px 8px', color: regimeColor, fontWeight: 600 }}>{d.regime}</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.settleToEmpty}%</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: '#e8a838' }}>{d.settleToSettle}%</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: '#22c55e' }}>{d.settleToForest}%</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.forestRetention}%</td>
                  <td style={{ padding: '6px 8px', textAlign: 'right' }}>{d.dynamicCells}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Settlement fate across rounds (stacked bar using avg probabilities) */}
      <div className="chart-card">
        <h3>Initial Settlement Fate Across Rounds (Q11/Q13)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="round" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} formatter={(v) => `${v}%`} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#8b949e' }} />
            <Bar dataKey="settleToEmpty" name="→ Empty" stackId="a" fill="#6b7280" />
            <Bar dataKey="settleToSettle" name="→ Settle/Port" stackId="a" fill="#e8a838" />
            <Bar dataKey="settleToForest" name="→ Forest" stackId="a" fill="#22c55e" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Forest retention across rounds */}
      <div className="chart-card">
        <h3>Forest Retention Rate Across Rounds (Q10)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="round" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} formatter={(v) => `${v}%`} />
            <Bar dataKey="forestRetention" name="Forest stays forest %" fill="#22c55e" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Entropy + dynamic cells */}
      <div className="chart-card">
        <h3>Average Entropy per Round</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="round" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Line type="monotone" dataKey="avgEntropy" stroke="#58a6ff" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Settlement count */}
      <div className="chart-card">
        <h3>Initial Settlements per Round (avg across seeds)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="round" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="settlements" fill="#e8a838" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Dynamic cells per round */}
      <div className="chart-card">
        <h3>Dynamic Cells per Round (avg across seeds)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="round" tick={{ fill: '#8b949e', fontSize: 12 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="dynamicCells" fill="#58a6ff" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
