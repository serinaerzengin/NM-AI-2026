import { CLASS_NAMES } from './constants'

function entropy(probs) {
  let h = 0
  for (const p of probs) {
    if (p > 0) h -= p * Math.log2(p)
  }
  return h
}

function argmax(probs) {
  let maxI = 0
  for (let i = 1; i < probs.length; i++) {
    if (probs[i] > probs[maxI]) maxI = i
  }
  return maxI
}

// Settlement fate — avg probability distribution for initial settlement cells
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

// Observed settlement rate from ground truth (key metric for regime detection)
export function computeObservedSettleRate(initialGrid, gt) {
  let settleProb = 0, dynamicCount = 0
  for (let y = 0; y < gt.length; y++) {
    for (let x = 0; x < gt[y].length; x++) {
      const code = initialGrid[y][x]
      if (code === 10 || code === 5) continue // skip ocean/mountain
      const p = gt[y][x][1] + gt[y][x][2] // P(settlement + port)
      settleProb += p
      dynamicCount++
    }
  }
  return dynamicCount > 0 ? settleProb / dynamicCount : 0
}

// Expansion radius — cells with P(settle+port) > threshold by manhattan distance
export function computeExpansionRadius(settlements, gt, threshold = 0.05) {
  const settleSet = new Set(settlements.map(s => `${s.x},${s.y}`))
  const distanceCounts = {}
  let maxDist = 0

  for (let y = 0; y < gt.length; y++) {
    for (let x = 0; x < gt[y].length; x++) {
      if (settleSet.has(`${x},${y}`)) continue
      const pSettle = gt[y][x][1] + gt[y][x][2]
      if (pSettle < threshold) continue
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

// Per-terrain stochasticity (disagreement rate = 1 - Σpᵢ²)
export function computeDisagreementByTerrain(initialGrid, gt) {
  const stats = {}
  const LABELS = { 0: 'Empty', 1: 'Settlement', 2: 'Port', 3: 'Ruin', 4: 'Forest', 5: 'Mountain', 10: 'Ocean', 11: 'Plains' }
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      const code = initialGrid[y][x]
      const probs = gt[y][x]
      const agreement = probs.reduce((s, p) => s + p * p, 0)
      if (!stats[code]) stats[code] = { sum: 0, count: 0 }
      stats[code].sum += (1 - agreement)
      stats[code].count++
    }
  }
  return Object.entries(stats)
    .map(([code, { sum, count }]) => ({
      terrain: LABELS[code] || `Code ${code}`,
      code: +code,
      disagreement: +(sum / count * 100).toFixed(1),
      count,
    }))
    .sort((a, b) => b.disagreement - a.disagreement)
}

// Entropy summary
export function computeEntropyStats(gt) {
  let sum = 0, dynamic = 0, total = 0
  for (const row of gt) {
    for (const probs of row) {
      const h = entropy(probs)
      sum += h
      if (h > 0.1) dynamic++
      total++
    }
  }
  return { mean: sum / total, dynamic, static: total - dynamic, total }
}

// Forest retention rate
export function computeForestRetention(initialGrid, gt) {
  let forestSum = 0, count = 0
  for (let y = 0; y < initialGrid.length; y++) {
    for (let x = 0; x < initialGrid[y].length; x++) {
      if (initialGrid[y][x] === 4) {
        forestSum += gt[y][x][4]
        count++
      }
    }
  }
  return count > 0 ? +(forestSum / count * 100).toFixed(1) : 0
}

// Cross-round summary (compact)
export function computeCrossRoundStats(allData) {
  return allData.map(({ roundNumber, seeds }) => {
    let settleToEmpty = 0, settleToSettle = 0, settleToForest = 0
    let totalSettlements = 0, forestRet = 0, avgEntropy = 0
    let dynamicCells = 0, seedCount = 0

    for (const { initialState, groundTruth } of seeds) {
      if (!initialState || !groundTruth) continue
      seedCount++
      const gt = groundTruth.ground_truth
      const settlements = initialState.settlements
      totalSettlements += settlements.length

      for (const s of settlements) {
        const probs = gt[s.y]?.[s.x]
        if (!probs) continue
        settleToEmpty += probs[0]
        settleToSettle += probs[1] + probs[2]
        settleToForest += probs[4]
      }

      const es = computeEntropyStats(gt)
      avgEntropy += es.mean
      dynamicCells += es.dynamic
      forestRet += computeForestRetention(initialState.grid, gt)
    }

    const settPct = totalSettlements > 0 ? +(settleToSettle / totalSettlements * 100).toFixed(1) : 0
    const observedRate = totalSettlements > 0
      ? seeds.reduce((s, { initialState: is, groundTruth: g }) => {
          if (!is || !g) return s
          return s + computeObservedSettleRate(is.grid, g.ground_truth)
        }, 0) / seedCount
      : 0

    return {
      round: roundNumber,
      label: `R${roundNumber}`,
      settlements: seedCount > 0 ? Math.round(totalSettlements / seedCount) : 0,
      settleToEmpty: totalSettlements > 0 ? +(settleToEmpty / totalSettlements * 100).toFixed(1) : 0,
      settleToSettle: settPct,
      settleToForest: totalSettlements > 0 ? +(settleToForest / totalSettlements * 100).toFixed(1) : 0,
      forestRetention: seedCount > 0 ? +(forestRet / seedCount).toFixed(1) : 0,
      avgEntropy: seedCount > 0 ? +(avgEntropy / seedCount).toFixed(3) : 0,
      dynamicCells: seedCount > 0 ? Math.round(dynamicCells / seedCount) : 0,
      observedSettleRate: +(observedRate * 100).toFixed(2),
    }
  })
}
