import { useRef, useEffect, useState } from 'react'
import { TERRAIN_COLORS, CLASS_COLORS, CLASS_NAMES } from '../constants'

const CELL_SIZE = 12

function terrainColor(code) {
  return TERRAIN_COLORS[code] || '#1a1a2e'
}

function probToColor(probs) {
  // Blend class colors by probability
  let r = 0, g = 0, b = 0
  for (let i = 0; i < probs.length; i++) {
    const hex = CLASS_COLORS[i]
    r += probs[i] * parseInt(hex.slice(1, 3), 16)
    g += probs[i] * parseInt(hex.slice(3, 5), 16)
    b += probs[i] * parseInt(hex.slice(5, 7), 16)
  }
  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`
}

export default function GridView({ grid, groundTruth, title }) {
  const canvasRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)
  const data = groundTruth || grid
  const height = data.length
  const width = data[0].length

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
        } else {
          ctx.fillStyle = terrainColor(grid[y][x])
        }
        ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
      }
    }

    // Grid lines (subtle)
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.lineWidth = 0.5
    for (let y = 0; y <= height; y++) {
      ctx.beginPath()
      ctx.moveTo(0, y * CELL_SIZE)
      ctx.lineTo(width * CELL_SIZE, y * CELL_SIZE)
      ctx.stroke()
    }
    for (let x = 0; x <= width; x++) {
      ctx.beginPath()
      ctx.moveTo(x * CELL_SIZE, 0)
      ctx.lineTo(x * CELL_SIZE, height * CELL_SIZE)
      ctx.stroke()
    }
  }, [grid, groundTruth, width, height])

  function handleMouseMove(e) {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE)
    const y = Math.floor((e.clientY - rect.top) / CELL_SIZE)
    if (x < 0 || x >= width || y < 0 || y >= height) {
      setTooltip(null)
      return
    }
    const probs = groundTruth ? groundTruth[y][x] : null
    const terrain = grid ? grid[y][x] : null
    setTooltip({ x, y, probs, terrain, pageX: e.clientX, pageY: e.clientY })
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
              <span className="val">{tooltip.terrain}</span>
            </div>
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
