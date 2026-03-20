import { useState } from 'react'
import { useRounds, useSeedData } from './hooks'
import GridView from './components/GridView'
import { TerrainLegend, ClassLegend } from './components/GridLegend'
import StatsPanel from './components/StatsPanel'
import CrossRoundCharts from './components/CrossRoundCharts'
import ScoresPanel from './components/ScoresPanel'

function App() {
  const { rounds, loading, reload } = useRounds()
  const [selectedRound, setSelectedRound] = useState(null)
  const [selectedSeed, setSelectedSeed] = useState(0)
  const [tab, setTab] = useState('round')

  const round = selectedRound != null
    ? rounds.find(r => r.round_number === selectedRound)
    : rounds[0]

  const roundNumber = round?.round_number
  const seedInfo = round?.seeds?.find(s => s.index === selectedSeed)
  const { initialState, groundTruth, prediction, observations, loading: seedLoading } = useSeedData(roundNumber, selectedSeed)

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
          Cross-Round
        </button>
        <button className={tab === 'scores' ? 'active' : ''} onClick={() => setTab('scores')}>
          Scores
        </button>
      </div>

      {tab === 'scores' ? (
        <ScoresPanel />
      ) : tab === 'overview' ? (
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
                <option key={s.index} value={s.index}>Seed {s.index}</option>
              ))}
            </select>

            <button onClick={reload}>Reload</button>
          </div>

          {round && (
            <div className="round-info">
              <div className="info-card">
                <div className="label">Status</div>
                <div className="value">{round.status}</div>
              </div>
              <div className="info-card">
                <div className="label">Map</div>
                <div className="value">{round.map_width}x{round.map_height}</div>
              </div>
              <div className="info-card">
                <div className="label">Weight</div>
                <div className="value">{round.round_weight}</div>
              </div>
              {seedInfo && (
                <>
                  <div className="info-card">
                    <div className="label">Observations</div>
                    <div className="value">{seedInfo.obsCount}</div>
                  </div>
                  <div className="info-card">
                    <div className="label">Ground Truth</div>
                    <div className="value" style={{ color: seedInfo.hasGT ? '#22c55e' : '#8b949e' }}>
                      {seedInfo.hasGT ? 'Yes' : 'No'}
                    </div>
                  </div>
                  <div className="info-card">
                    <div className="label">Prediction</div>
                    <div className="value" style={{ color: seedInfo.hasPred ? '#58a6ff' : '#8b949e' }}>
                      {seedInfo.hasPred ? 'Submitted' : 'No'}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {seedLoading ? (
            <div className="loading">Loading seed data...</div>
          ) : (
            <>
              <div className="grid-section">
                {initialState && (
                  <div>
                    <GridView
                      grid={initialState.grid}
                      observations={observations}
                      title="Initial State"
                    />
                    <TerrainLegend />
                    {observations.length > 0 && (
                      <p style={{ color: '#58a6ff', fontSize: '0.8rem', marginTop: 4 }}>
                        Blue rectangles = observation viewports ({observations.length} queries)
                      </p>
                    )}
                  </div>
                )}
                {groundTruth && (
                  <div>
                    <GridView groundTruth={groundTruth.ground_truth} title="Ground Truth" />
                    <ClassLegend />
                  </div>
                )}
                {prediction && !groundTruth && (
                  <div>
                    <GridView prediction={prediction} title="Prediction (argmax + confidence)" />
                    <ClassLegend />
                    <p style={{ color: '#8b949e', fontSize: '0.8rem', marginTop: 4 }}>
                      Brightness = confidence. Dim cells are uncertain.
                    </p>
                  </div>
                )}
              </div>

              {initialState && groundTruth && (
                <StatsPanel initialState={initialState} groundTruth={groundTruth} />
              )}

              {initialState && !groundTruth && observations.length > 0 && (
                <div className="chart-card" style={{ marginBottom: 24 }}>
                  <h3>Observation Summary (no ground truth yet)</h3>
                  <div className="round-info" style={{ marginTop: 12 }}>
                    <div className="info-card">
                      <div className="label">Queries Used</div>
                      <div className="value">{observations.length}</div>
                    </div>
                    <div className="info-card">
                      <div className="label">Settlements (initial)</div>
                      <div className="value">{initialState.settlements.length}</div>
                    </div>
                    <div className="info-card">
                      <div className="label">Ports (initial)</div>
                      <div className="value">{initialState.settlements.filter(s => s.has_port).length}</div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

export default App
