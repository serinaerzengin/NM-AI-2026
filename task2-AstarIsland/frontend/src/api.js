export async function fetchRounds() {
  const res = await fetch('/api/rounds')
  return res.json()
}

export async function fetchInitialState(round, seed) {
  const res = await fetch(`/api/round/${round}/seed/${seed}/initial_state`)
  return res.json()
}

export async function fetchGroundTruth(round, seed) {
  const res = await fetch(`/api/round/${round}/seed/${seed}/ground_truth`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchPrediction(round, seed) {
  const res = await fetch(`/api/round/${round}/seed/${seed}/prediction`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchObservations(round, seed) {
  const res = await fetch(`/api/round/${round}/seed/${seed}/observations`)
  return res.json()
}

export async function fetchEvalData() {
  const res = await fetch('/api/eval')
  return res.json()
}

export async function fetchMyRounds() {
  const res = await fetch('/api/remote/my-rounds')
  if (!res.ok) return []
  return res.json()
}

export async function fetchLeaderboard() {
  const res = await fetch('/api/remote/leaderboard')
  if (!res.ok) return []
  return res.json()
}
