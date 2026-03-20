import { useState } from 'react'
import { useRounds, useSeedData } from './hooks'
import GridView from './components/GridView'
import { TerrainLegend, ClassLegend } from './components/GridLegend'
import StatsPanel from './components/StatsPanel'
import CrossRoundCharts from './components/CrossRoundCharts'

function App() {
  const { rounds, loading, reload } = useRounds()
  const [selectedRound, setSelectedRound] = useState(null)
  const [selectedSeed, setSelectedSeed] = useState(0)
  const [tab, setTab] = useState('round') // 'round' | 'overview'

  const round = selectedRound != null
    ? rounds.find(r => r.round_number === selectedRound)
    : rounds[0]

  const roundNumber = round?.round_number
  const { initialState, groundTruth, loading: seedLoading } = useSeedData(roundNumber, selectedSeed)

  // Auto-select first round on load
  if (!loading && rounds.length > 0 && selectedRound == null) {
    setSelectedRound(rounds[0].round_number)
  }

  if (loading) return <div className="loading">Loading rounds...</div>
  if (!rounds.length) return <div className="loading">No round data found.</div>

  return (
    <div className="app">
      <h1>Astar Island Visualizer</h1>

      <div className="tab-bar">
        <button className={tab === 'round' ? 'active' : ''} onClick={() => setTab('round')}>
          Round View
        </button>
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>
          Cross-Round Overview
        </button>
      </div>

      {tab === 'overview' ? (
        <CrossRoundCharts rounds={rounds} />
      ) : (
        <>
          <div className="controls">
            <label>Round:</label>
            <select value={roundNumber} onChange={e => { setSelectedRound(+e.target.value); setSelectedSeed(0) }}>
              {rounds.map(r => (
                <option key={r.round_number} value={r.round_number}>
                  Round {r.round_number} ({r.status})
                </option>
              ))}
            </select>

            <label>Seed:</label>
            <select value={selectedSeed} onChange={e => setSelectedSeed(+e.target.value)}>
              {(round?.seeds || []).map(s => (
                <option key={s} value={s}>Seed {s}</option>
              ))}
            </select>

            <button onClick={reload}>Reload Rounds</button>
          </div>

          {round && (
            <div className="round-info">
              <div className="info-card">
                <div className="label">Status</div>
                <div className="value">{round.status}</div>
              </div>
              <div className="info-card">
                <div className="label">Map Size</div>
                <div className="value">{round.map_width}x{round.map_height}</div>
              </div>
              <div className="info-card">
                <div className="label">Seeds</div>
                <div className="value">{round.seeds_count}</div>
              </div>
              <div className="info-card">
                <div className="label">Weight</div>
                <div className="value">{round.round_weight}</div>
              </div>
              <div className="info-card">
                <div className="label">Started</div>
                <div className="value" style={{ fontSize: '0.85rem' }}>{new Date(round.started_at).toLocaleString()}</div>
              </div>
            </div>
          )}

          {seedLoading ? (
            <div className="loading">Loading seed data...</div>
          ) : (
            <>
              <div className="grid-section">
                {initialState && (
                  <div>
                    <GridView grid={initialState.grid} title="Initial State" />
                    <TerrainLegend />
                  </div>
                )}
                {groundTruth && (
                  <div>
                    <GridView groundTruth={groundTruth.ground_truth} title="Ground Truth (Probability)" />
                    <ClassLegend />
                  </div>
                )}
              </div>

              <StatsPanel initialState={initialState} groundTruth={groundTruth} />
            </>
          )}
        </>
      )}
    </div>
  )
}

export default App
