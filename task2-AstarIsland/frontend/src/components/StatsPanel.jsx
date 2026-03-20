import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid,
} from 'recharts'
import { CLASS_COLORS, CLASS_NAMES, TERRAIN_CODES, TERRAIN_COLORS } from '../constants'
import {
  computeInitialTerrainCounts, computeSettlementStats,
  computeGroundTruthClassDist, computeEntropyStats, computeAvgClassProbs,
  computeSettlementFate, classifyExpansionRegime, computeExpansionRadius,
  computeDisagreementByTerrain, computeStaticByTerrain, computeForestStability,
} from '../stats'

const tipStyle = { background: '#1c2128', border: '1px solid #30363d', borderRadius: 6, color: '#e1e4e8' }
const tipLabelStyle = { color: '#e1e4e8' }
const tipItemStyle = { color: '#c9d1d9' }

export default function StatsPanel({ initialState, groundTruth }) {
  if (!initialState || !groundTruth) return null

  const gt = groundTruth.ground_truth
  const terrainCounts = computeInitialTerrainCounts(initialState.grid)
  const settlementStats = computeSettlementStats(initialState.settlements)
  const classDist = computeGroundTruthClassDist(gt)
  const entropyStats = computeEntropyStats(gt)
  const avgProbs = computeAvgClassProbs(gt)

  // New stats from research questions
  const settlementFate = computeSettlementFate(initialState.settlements, gt)
  const regime = classifyExpansionRegime(initialState.settlements, gt)
  const expansion = computeExpansionRadius(initialState.settlements, gt, 0.05)
  const disagreement = computeDisagreementByTerrain(initialState.grid, gt)
  const staticByTerrain = computeStaticByTerrain(initialState.grid, gt)
  const forestStability = computeForestStability(initialState.grid, gt)

  const terrainData = Object.entries(terrainCounts)
    .map(([code, count]) => ({ name: TERRAIN_CODES[code] || `Code ${code}`, count, code: +code }))
    .sort((a, b) => b.count - a.count)

  const regimeColor = regime.regime.includes('High') ? '#22c55e'
    : regime.regime.includes('collapse') || regime.regime.includes('Collapse') ? '#ef4444' : '#e8a838'

  return (
    <div className="stats-grid">
      {/* Expansion Regime (Q13) */}
      <div className="chart-card">
        <h3>Expansion Regime (Q13)</h3>
        <div className="round-info" style={{ marginTop: 12 }}>
          <div className="info-card" style={{ borderColor: regimeColor }}>
            <div className="label">Regime</div>
            <div className="value" style={{ color: regimeColor }}>{regime.regime}</div>
          </div>
          <div className="info-card">
            <div className="label">Settle → Empty</div>
            <div className="value">{regime.toEmpty}%</div>
          </div>
          <div className="info-card">
            <div className="label">Settle → Settle/Port</div>
            <div className="value" style={{ color: '#e8a838' }}>{regime.toSettle}%</div>
          </div>
          <div className="info-card">
            <div className="label">Settle → Forest</div>
            <div className="value" style={{ color: '#22c55e' }}>{regime.toForest}%</div>
          </div>
        </div>
        <div className="round-info" style={{ marginTop: 8 }}>
          <div className="info-card">
            <div className="label">Settlements</div>
            <div className="value">{settlementStats.total}</div>
          </div>
          <div className="info-card">
            <div className="label">Ports (initial)</div>
            <div className="value" style={{ color: '#3b82f6' }}>{settlementStats.ports}</div>
          </div>
          <div className="info-card">
            <div className="label">Forest Retention</div>
            <div className="value">{forestStability.avgForestRetention}%</div>
          </div>
          <div className="info-card">
            <div className="label">Avg Entropy</div>
            <div className="value">{entropyStats.mean.toFixed(3)}</div>
          </div>
        </div>
      </div>

      {/* Settlement Fate (Q11) */}
      <div className="chart-card">
        <h3>Settlement Fate — Avg P(class) for Initial Settlements (Q11)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={settlementFate} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 1]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} formatter={(v) => `${(v * 100).toFixed(1)}%`} />
            <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
              {settlementFate.map((_, i) => (
                <Cell key={i} fill={CLASS_COLORS[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Expansion Radius (Q9) */}
      <div className="chart-card">
        <h3>Expansion Radius — Cells with P(settle) {'>'} 5% by Distance (Q9)</h3>
        <p style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: 8 }}>
          Max reach: {expansion.maxDist} cells | Total expanded: {expansion.totalExpanded} cells
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={expansion.histogram} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="distance" tick={{ fill: '#8b949e', fontSize: 11 }} label={{ value: 'Manhattan dist', position: 'insideBottom', offset: -2, fill: '#8b949e', fontSize: 10 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="cells" fill="#e8a838" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Terrain Disagreement Rate (Q6) */}
      <div className="chart-card">
        <h3>Stochasticity by Initial Terrain (Q6) — Disagreement %</h3>
        <p style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: 8 }}>
          1 - Σpᵢ² : probability that two random simulation runs disagree on cell outcome
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={disagreement} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="terrain" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} formatter={(v) => `${v}%`} />
            <Bar dataKey="disagreement" fill="#ef4444" radius={[3, 3, 0, 0]}>
              {disagreement.map((entry) => (
                <Cell key={entry.code} fill={TERRAIN_COLORS[entry.code] || '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Static vs Dynamic by Terrain (Q5) */}
      <div className="chart-card">
        <h3>Static vs Dynamic Cells by Terrain (Q5)</h3>
        <p style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: 8 }}>
          Static = max probability {'>'} 95%. These are free predictions.
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={staticByTerrain} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis dataKey="terrain" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="static" stackId="a" fill="#22c55e" name="Static" />
            <Bar dataKey="dynamic" stackId="a" fill="#ef4444" name="Dynamic" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Initial terrain distribution */}
      <div className="chart-card">
        <h3>Initial Terrain Distribution (Q1)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={terrainData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {terrainData.map((entry) => (
                <Cell key={entry.code} fill={TERRAIN_COLORS[entry.code] || '#6b7280'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Ground truth class distribution (argmax) */}
      <div className="chart-card">
        <h3>Ground Truth Class Distribution (Argmax)</h3>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={classDist} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
              {classDist.map((_, i) => (
                <Cell key={i} fill={CLASS_COLORS[i]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Average class probabilities for dynamic cells */}
      <div className="chart-card">
        <h3>Avg Class Probabilities (Dynamic Cells) (Q7)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={avgProbs} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 1]} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} formatter={(v) => `${(v * 100).toFixed(1)}%`} />
            <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
              {avgProbs.map((_, i) => (
                <Cell key={i} fill={CLASS_COLORS[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Entropy histogram */}
      <div className="chart-card">
        <h3>Entropy Distribution (Q28)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={entropyStats.histogram} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="range" tick={{ fill: '#8b949e', fontSize: 10 }} interval={3} />
            <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} />
            <Tooltip contentStyle={tipStyle} labelStyle={tipLabelStyle} itemStyle={tipItemStyle} />
            <Bar dataKey="count" fill="#58a6ff" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
