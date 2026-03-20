import { CLASS_NAMES } from './constants'

// Compute per-cell entropy from a 6-element probability vector
function entropy(probs) {
  let h = 0
  for (const p of probs) {
    if (p > 0) h -= p * Math.log2(p)
  }
  return h
}

// Get argmax class for a probability vector
function argmax(probs) {
  let maxI = 0
  for (let i = 1; i < probs.length; i++) {
    if (probs[i] > probs[maxI]) maxI = i
  }
  return maxI
}

// Compute terrain distribution from initial grid
export function computeInitialTerrainCounts(grid) {
  const counts = {}
  for (const row of grid) {
    for (const cell of row) {
      counts[cell] = (counts[cell] || 0) + 1
    }
  }
  return counts
}

// Compute settlement stats from initial state
export function computeSettlementStats(settlements) {
  const alive = settlements.filter(s => s.alive).length
  const ports = settlements.filter(s => s.has_port).length
  return { total: settlements.length, alive, dead: settlements.length - alive, ports }
}

// Compute class distribution from ground truth (argmax)
export function computeGroundTruthClassDist(gt) {
  const counts = new Array(6).fill(0)
  for (const row of gt) {
    for (const probs of row) {
      counts[argmax(probs)]++
    }
  }
  return CLASS_NAMES.map((name, i) => ({ name, count: counts[i] }))
}

// Compute entropy stats from ground truth
export function computeEntropyStats(gt) {
  const entropies = []
  for (let y = 0; y < gt.length; y++) {
    for (let x = 0; x < gt[y].length; x++) {
      entropies.push({ x, y, entropy: entropy(gt[y][x]) })
    }
  }
  const vals = entropies.map(e => e.entropy)
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  const dynamic = vals.filter(v => v > 0.1).length
  const staticCount = vals.filter(v => v <= 0.1).length

  // histogram buckets
  const buckets = Array.from({ length: 20 }, (_, i) => ({
    range: `${(i * 0.13).toFixed(2)}`,
    count: 0,
  }))
  for (const v of vals) {
    const idx = Math.min(19, Math.floor(v / 0.13))
    buckets[idx].count++
  }

  return { mean, dynamic, static: staticCount, histogram: buckets, entropies }
}

// Compute average class probabilities for dynamic cells only
export function computeAvgClassProbs(gt) {
  const sums = new Array(6).fill(0)
  let count = 0
  for (const row of gt) {
    for (const probs of row) {
      const h = entropy(probs)
      if (h > 0.1) {
        for (let i = 0; i < 6; i++) sums[i] += probs[i]
        count++
      }
    }
  }
  if (count === 0) return CLASS_NAMES.map((name, i) => ({ name, probability: 0 }))
  return CLASS_NAMES.map((name, i) => ({ name, probability: +(sums[i] / count).toFixed(4) }))
}

// Compute transition: what did initial terrain become in ground truth?
export function computeTransitions(initialGrid, gt) {
  const transitions = {}
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      const from = initialGrid[y][x]
      const to = argmax(gt[y][x])
      const key = `${from}→${to}`
      transitions[key] = (transitions[key] || 0) + 1
    }
  }
  return transitions
}

// Q11/Q13: Settlement fate breakdown — what do initial settlements become in GT?
// Returns avg probability distribution over 6 classes for initial settlement cells
export function computeSettlementFate(settlements, gt) {
  const sums = new Array(6).fill(0)
  let count = 0
  for (const s of settlements) {
    const probs = gt[s.y]?.[s.x]
    if (!probs) continue
    for (let i = 0; i < 6; i++) sums[i] += probs[i]
    count++
  }
  if (count === 0) return CLASS_NAMES.map((name) => ({ name, probability: 0 }))
  return CLASS_NAMES.map((name, i) => ({ name, probability: +(sums[i] / count).toFixed(4) }))
}

// Q13: Expansion regime classification
export function classifyExpansionRegime(settlements, gt) {
  let toEmpty = 0, toSettle = 0, toForest = 0, total = 0
  for (const s of settlements) {
    const probs = gt[s.y]?.[s.x]
    if (!probs) continue
    total++
    toEmpty += probs[0]
    toSettle += probs[1] + probs[2] // settlement + port
    toForest += probs[4]
  }
  if (total === 0) return { regime: 'Unknown', toEmpty: 0, toSettle: 0, toForest: 0 }
  const e = +(toEmpty / total * 100).toFixed(1)
  const s = +(toSettle / total * 100).toFixed(1)
  const f = +(toForest / total * 100).toFixed(1)
  let regime = 'Medium'
  if (s > 35) regime = 'High expansion'
  else if (s < 10) regime = 'Low expansion (collapse)'
  else if (s > 25) regime = 'Medium-high'
  return { regime, toEmpty: e, toSettle: s, toForest: f }
}

// Q9: Expansion radius — manhattan distance from nearest initial settlement
// for cells with P(settlement+port) > threshold
export function computeExpansionRadius(settlements, gt, threshold = 0.05) {
  const settleSet = new Set(settlements.map(s => `${s.x},${s.y}`))
  const distanceCounts = {}
  let maxDist = 0

  for (let y = 0; y < gt.length; y++) {
    for (let x = 0; x < gt[y].length; x++) {
      if (settleSet.has(`${x},${y}`)) continue // skip initial settlement cells
      const pSettle = gt[y][x][1] + gt[y][x][2] // settlement + port
      if (pSettle < threshold) continue
      // Manhattan distance to nearest settlement
      let minDist = Infinity
      for (const s of settlements) {
        const d = Math.abs(x - s.x) + Math.abs(y - s.y)
        if (d < minDist) minDist = d
      }
      distanceCounts[minDist] = (distanceCounts[minDist] || 0) + 1
      if (minDist > maxDist) maxDist = minDist
    }
  }
  const histogram = []
  for (let d = 1; d <= Math.min(maxDist, 15); d++) {
    histogram.push({ distance: d, cells: distanceCounts[d] || 0 })
  }
  return { histogram, maxDist, totalExpanded: Object.values(distanceCounts).reduce((a, b) => a + b, 0) }
}

// Q6: Per-terrain-type stochasticity (disagreement rate = 1 - Σpᵢ²)
export function computeDisagreementByTerrain(initialGrid, gt) {
  const terrainDisagreement = {} // code → {sum, count}
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      const code = initialGrid[y][x]
      const probs = gt[y][x]
      const agreement = probs.reduce((s, p) => s + p * p, 0)
      const disagreement = 1 - agreement
      if (!terrainDisagreement[code]) terrainDisagreement[code] = { sum: 0, count: 0 }
      terrainDisagreement[code].sum += disagreement
      terrainDisagreement[code].count++
    }
  }
  const TERRAIN_LABELS = { 0: 'Empty', 1: 'Settlement', 2: 'Port', 3: 'Ruin', 4: 'Forest', 5: 'Mountain', 10: 'Ocean', 11: 'Plains' }
  return Object.entries(terrainDisagreement)
    .map(([code, { sum, count }]) => ({
      terrain: TERRAIN_LABELS[code] || `Code ${code}`,
      code: +code,
      disagreement: +(sum / count * 100).toFixed(1),
      count,
    }))
    .sort((a, b) => b.disagreement - a.disagreement)
}

// Q5/Q10: Per-terrain-type static vs dynamic split
// A cell is "static" if max probability > 0.95
export function computeStaticByTerrain(initialGrid, gt) {
  const stats = {} // code → {static, dynamic}
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      const code = initialGrid[y][x]
      const maxP = Math.max(...gt[y][x])
      if (!stats[code]) stats[code] = { static: 0, dynamic: 0 }
      if (maxP > 0.95) stats[code].static++
      else stats[code].dynamic++
    }
  }
  const TERRAIN_LABELS = { 0: 'Empty', 1: 'Settlement', 2: 'Port', 3: 'Ruin', 4: 'Forest', 5: 'Mountain', 10: 'Ocean', 11: 'Plains' }
  return Object.entries(stats)
    .map(([code, { static: s, dynamic: d }]) => ({
      terrain: TERRAIN_LABELS[code] || `Code ${code}`,
      code: +code,
      static: s,
      dynamic: d,
      total: s + d,
      staticPct: +((s / (s + d)) * 100).toFixed(1),
    }))
    .sort((a, b) => b.total - a.total)
}

// Q10: Forest stability — avg probability that initial forest cells stay forest
export function computeForestStability(initialGrid, gt) {
  let forestSum = 0, count = 0
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      if (initialGrid[y][x] === 4) {
        forestSum += gt[y][x][4] // P(forest)
        count++
      }
    }
  }
  if (count === 0) return { avgForestRetention: 0, forestCells: 0 }
  return { avgForestRetention: +(forestSum / count * 100).toFixed(1), forestCells: count }
}

// Cross-round: settlement survival rate per round
export function computeCrossRoundStats(allData) {
  return allData.map(({ roundNumber, seeds }) => {
    let totalSettlements = 0
    let survivedSettlements = 0
    let totalRuins = 0
    let totalPorts = 0
    let avgEntropy = 0
    let avgForestRetention = 0
    let settleToEmpty = 0, settleToSettle = 0, settleToForest = 0
    let dynamicCells = 0
    let seedCount = 0

    for (const { initialState, groundTruth } of seeds) {
      if (!initialState || !groundTruth) continue
      seedCount++
      const settlements = initialState.settlements
      totalSettlements += settlements.length

      const gt = groundTruth.ground_truth

      for (const s of settlements) {
        const probs = gt[s.y]?.[s.x]
        if (probs) {
          const cls = argmax(probs)
          if (cls === 1 || cls === 2) survivedSettlements++
          if (cls === 3) totalRuins++
          if (cls === 2) totalPorts++
          settleToEmpty += probs[0]
          settleToSettle += probs[1] + probs[2]
          settleToForest += probs[4]
        }
      }

      const { mean, dynamic } = computeEntropyStats(gt)
      avgEntropy += mean
      dynamicCells += dynamic

      const { avgForestRetention: fr } = computeForestStability(initialState.grid, gt)
      avgForestRetention += fr
    }

    let regime = 'Medium'
    const settPct = totalSettlements > 0 ? (settleToSettle / totalSettlements * 100) : 0
    if (settPct > 35) regime = 'High'
    else if (settPct < 10) regime = 'Collapse'
    else if (settPct > 25) regime = 'Med-High'

    return {
      round: `R${roundNumber}`,
      settlements: seedCount > 0 ? Math.round(totalSettlements / seedCount) : 0,
      survivalRate: totalSettlements > 0 ? +((survivedSettlements / totalSettlements) * 100).toFixed(1) : 0,
      ruinRate: totalSettlements > 0 ? +((totalRuins / totalSettlements) * 100).toFixed(1) : 0,
      portRate: totalSettlements > 0 ? +((totalPorts / totalSettlements) * 100).toFixed(1) : 0,
      avgEntropy: seedCount > 0 ? +(avgEntropy / seedCount).toFixed(3) : 0,
      regime,
      settleToEmpty: totalSettlements > 0 ? +(settleToEmpty / totalSettlements * 100).toFixed(1) : 0,
      settleToSettle: totalSettlements > 0 ? +(settleToSettle / totalSettlements * 100).toFixed(1) : 0,
      settleToForest: totalSettlements > 0 ? +(settleToForest / totalSettlements * 100).toFixed(1) : 0,
      forestRetention: seedCount > 0 ? +(avgForestRetention / seedCount).toFixed(1) : 0,
      dynamicCells: seedCount > 0 ? Math.round(dynamicCells / seedCount) : 0,
    }
  })
}
