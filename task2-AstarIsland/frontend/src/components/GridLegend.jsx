import { TERRAIN_COLORS, TERRAIN_CODES, CLASS_COLORS, CLASS_NAMES } from '../constants'

export function TerrainLegend() {
  const items = [
    { code: 10, label: 'Ocean' },
    { code: 11, label: 'Plains' },
    { code: 0, label: 'Empty' },
    { code: 1, label: 'Settlement' },
    { code: 2, label: 'Port' },
    { code: 3, label: 'Ruin' },
    { code: 4, label: 'Forest' },
    { code: 5, label: 'Mountain' },
  ]
  return (
    <div className="legend">
      {items.map(({ code, label }) => (
        <div key={code} className="legend-item">
          <div className="legend-swatch" style={{ background: TERRAIN_COLORS[code] }} />
          {label}
        </div>
      ))}
    </div>
  )
}

export function ClassLegend() {
  return (
    <div className="legend">
      {CLASS_NAMES.map((name, i) => (
        <div key={i} className="legend-item">
          <div className="legend-swatch" style={{ background: CLASS_COLORS[i] }} />
          {name}
        </div>
      ))}
    </div>
  )
}
