import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts'
import { CLASS_COLORS, TERRAIN_COLORS } from '../constants'
import {
  computeSettlementFate, computeExpansionRadius,
  computeDisagreementByTerrain, computeEntropyStats, computeForestRetention,
  computeObservedSettleRate,
} from '../stats'

const tipStyle = { background: '#1c2128', border: '1px solid #30363d', borderRadius: 6, color: '#e1e4e8' }
const tipLabel = { color: '#e1e4e8' }
const tipItem = { color: '#c9d1d9' }

export default function StatsPanel({ initialState, groundTruth }) {
  if (!initialState || !groundTruth) return null

  const gt = groundTruth.ground_truth
  const settlements = initialState.settlements
  const fate = computeSettlementFate(settlements, gt)
  const expansion = computeExpansionRadius(settlements, gt, 0.05)
  const disagreement = computeDisagreementByTerrain(initialState.grid, gt)
  const entropyStats = computeEntropyStats(gt)
  const forestRet = computeForestRetention(initialState.grid, gt)
  const settleRate = computeObservedSettleRate(initialState.grid, gt)

  // Classify regime from settle rate
  const settPct = +(settleRate * 100).toFixed(2)
  const fittedRate = +(0.3834 * settleRate + 0.0102).toFixed(4)
  let regime = 'Medium'
  if (settPct > 15) regime = 'High expansion'
  else if (settPct < 2) regime = 'Collapse'
  else if (settPct > 10) regime = 'Medium-high'
  const regimeColor = regime.includes('High') ? '#22c55e'
    : regime.includes('Collapse') ? '#ef4444' : '#e8a838'

  return (
    <div className="stats-grid">
      {/* Regime + key metrics */}
      <div className="chart-card">
        <h3>Round Regime</h3>
        <div className="round-info" style={{ marginTop: 12 }}>
          <div className="info-card" style={{ borderColor: regimeColor }}>
            <div className="label">Regime</div>
            <div className="value" style={{ color: regimeColor }}>{regime}</div>
          </div>
          <div className="info-card">
            <div className="label">Settle Rate</div>
            <div className="value">{settPct}%</div>
          </div>
          <div className="info-card">
            <div className="label">Fitted exp_rate</div>
            <div className="value">{fittedRate}</div>
          </div>
        </div>
        <div className="round-info" style={{ marginTop: 8 }}>
          <div className="info-card">
            <div className="label">Settlements</div>
            <div className="value">{settlements.length}</div>
          </div>
          <div className="info-card">
            <div className="label">Forest Retention</div>
            <div className="value">{forestRet}%</div>
          </div>
          <div className="info-card">
            <div className="label">Dynamic / Static</div>
            <div className="value">{entropyStats.dynamic} / {entropyStats.static}</div>
          </div>
          <div className="info-card">
            <div className="label">Avg Entropy</div>
            <div className="value">{entropyStats.mean.toFixed(3)}</div>
          </div>
        </div>
      </div>

      {/* Settlement fate */}
      <div className="chart-card">
        <h3>Settlement Fate — Avg P(class) for initial settlements</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={fate} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 1]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabel} itemStyle={tipItem} formatter={(v) => `${(v * 100).toFixed(1)}%`} />
            <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
              {fate.map((_, i) => <Cell key={i} fill={CLASS_COLORS[i]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Expansion radius */}
      <div className="chart-card">
        <h3>Expansion Radius — cells with P(settle) {'>'} 5%</h3>
        <p style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: 4 }}>
          Max: {expansion.maxDist} cells | {expansion.totalExpanded} new cells
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={expansion.histogram} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="distance" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabel} itemStyle={tipItem} />
            <Bar dataKey="cells" fill="#e8a838" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Stochasticity by terrain */}
      <div className="chart-card">
        <h3>Stochasticity by Terrain — Disagreement %</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={disagreement} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="terrain" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabel} itemStyle={tipItem} formatter={(v) => `${v}%`} />
            <Bar dataKey="disagreement" radius={[3, 3, 0, 0]}>
              {disagreement.map((e) => <Cell key={e.code} fill={TERRAIN_COLORS[e.code] || '#6b7280'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
