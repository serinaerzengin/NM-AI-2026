import { useRef, useEffect, useState, useCallback } from 'react'
import { TERRAIN_COLORS, CLASS_COLORS, CLASS_NAMES } from '../constants'

const CELL_SIZE = 12

const TERRAIN_LABELS = { 0: 'Empty', 1: 'Settlement', 2: 'Port', 3: 'Ruin', 4: 'Forest', 5: 'Mountain', 10: 'Ocean', 11: 'Plains' }

function probToColor(probs) {
  let r = 0, g = 0, b = 0
  for (let i = 0; i < probs.length; i++) {
    const hex = CLASS_COLORS[i]
    r += probs[i] * parseInt(hex.slice(1, 3), 16)
    g += probs[i] * parseInt(hex.slice(3, 5), 16)
    b += probs[i] * parseInt(hex.slice(5, 7), 16)
  }
  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`
}

function predictionColor(classIdx, confidence) {
  const hex = CLASS_COLORS[classIdx] || '#6b7280'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const a = 0.3 + confidence * 0.7
  return `rgba(${r},${g},${b},${a})`
}

export default function GridView({ grid, groundTruth, prediction, observations, visibleObsCount, title }) {
  const canvasRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)

  const height = 40, width = 40

  // Sort observations by queriesUsed for consistent ordering
  const sortedObs = observations && observations.length > 0
    ? [...observations].sort((a, b) => (a.queriesUsed || 0) - (b.queriesUsed || 0))
    : []

  // How many to show: if visibleObsCount is provided, slice; otherwise show all
  const shownObs = visibleObsCount != null ? sortedObs.slice(0, visibleObsCount) : sortedObs

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    canvas.width = width * CELL_SIZE
    canvas.height = height * CELL_SIZE

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (groundTruth) {
          ctx.fillStyle = probToColor(groundTruth[y][x])
        } else if (prediction) {
          ctx.fillStyle = predictionColor(prediction.argmax_grid[y][x], prediction.confidence_grid[y][x])
        } else if (grid) {
          ctx.fillStyle = TERRAIN_COLORS[grid[y][x]] || '#1a1a2e'
        }
        ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
      }
    }

    // Observation coverage overlay
    if (shownObs.length > 0) {
      const lastIdx = shownObs.length - 1
      for (let i = 0; i < shownObs.length; i++) {
        const obs = shownObs[i]
        const h = obs.grid.length
        const w = obs.grid[0].length
        const isLatest = i === lastIdx

        // Dim older ones, highlight the latest
        ctx.strokeStyle = isLatest ? 'rgba(88, 166, 255, 0.9)' : 'rgba(88, 166, 255, 0.3)'
        ctx.lineWidth = isLatest ? 2.5 : 1
        ctx.strokeRect(obs.x * CELL_SIZE, obs.y * CELL_SIZE, w * CELL_SIZE, h * CELL_SIZE)

        // Number label
        ctx.fillStyle = isLatest ? 'rgba(88, 166, 255, 0.9)' : 'rgba(88, 166, 255, 0.5)'
        ctx.font = `bold ${isLatest ? 11 : 9}px sans-serif`
        ctx.fillText(`${i + 1}`, obs.x * CELL_SIZE + 3, obs.y * CELL_SIZE + (isLatest ? 13 : 10))
      }
    }

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.lineWidth = 0.5
    for (let y = 0; y <= height; y++) {
      ctx.beginPath(); ctx.moveTo(0, y * CELL_SIZE); ctx.lineTo(width * CELL_SIZE, y * CELL_SIZE); ctx.stroke()
    }
    for (let x = 0; x <= width; x++) {
      ctx.beginPath(); ctx.moveTo(x * CELL_SIZE, 0); ctx.lineTo(x * CELL_SIZE, height * CELL_SIZE); ctx.stroke()
    }
  }, [grid, groundTruth, prediction, shownObs])

  function handleMouseMove(e) {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE)
    const y = Math.floor((e.clientY - rect.top) / CELL_SIZE)
    if (x < 0 || x >= width || y < 0 || y >= height) { setTooltip(null); return }

    const info = { x, y, pageX: e.clientX, pageY: e.clientY }
    if (grid) info.terrain = grid[y][x]
    if (groundTruth) info.probs = groundTruth[y][x]
    if (prediction) {
      info.predClass = prediction.argmax_grid[y][x]
      info.confidence = prediction.confidence_grid[y][x]
    }
    setTooltip(info)
  }

  return (
    <div className="grid-panel">
      <h2>{title}</h2>
      <canvas
        ref={canvasRef}
        className="grid-canvas"
        width={width * CELL_SIZE}
        height={height * CELL_SIZE}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
      />
      {tooltip && (
        <div className="cell-tooltip" style={{ left: tooltip.pageX + 12, top: tooltip.pageY + 12 }}>
          <div className="coord">({tooltip.x}, {tooltip.y})</div>
          {tooltip.terrain != null && (
            <div className="prob-row">
              <span className="name">Terrain</span>
              <span className="val">{TERRAIN_LABELS[tooltip.terrain] || tooltip.terrain}</span>
            </div>
          )}
          {tooltip.predClass != null && (
            <>
              <div className="prob-row">
                <span className="name">Predicted</span>
                <span className="val">{CLASS_NAMES[tooltip.predClass]}</span>
              </div>
              <div className="prob-row">
                <span className="name">Confidence</span>
                <span className="val">{(tooltip.confidence * 100).toFixed(1)}%</span>
              </div>
            </>
          )}
          {tooltip.probs && CLASS_NAMES.map((name, i) => (
            <div key={name} className="prob-row">
              <span className="name">{name}</span>
              <span className="val">{(tooltip.probs[i] * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
