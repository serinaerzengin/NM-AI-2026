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
  return res.json()
}
