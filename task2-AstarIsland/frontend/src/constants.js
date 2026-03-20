// Terrain code → name mapping
export const TERRAIN_CODES = {
  0: 'Empty',
  1: 'Settlement',
  2: 'Port',
  3: 'Ruin',
  4: 'Forest',
  5: 'Mountain',
  10: 'Ocean',
  11: 'Plains',
}

// Class index → name (for ground truth probabilities)
export const CLASS_NAMES = ['Empty', 'Settlement', 'Port', 'Ruin', 'Forest', 'Mountain']

// Colors for terrain rendering
export const TERRAIN_COLORS = {
  0: '#1a1a2e',   // Empty - dark
  1: '#e8a838',   // Settlement - gold
  2: '#3b82f6',   // Port - blue
  3: '#6b4c3b',   // Ruin - brown
  4: '#22c55e',   // Forest - green
  5: '#6b7280',   // Mountain - gray
  10: '#0c1a3a',  // Ocean - deep blue
  11: '#4a7c59',  // Plains - olive green
}

// Colors for class probabilities
export const CLASS_COLORS = ['#6b7280', '#e8a838', '#3b82f6', '#6b4c3b', '#22c55e', '#9ca3af']
