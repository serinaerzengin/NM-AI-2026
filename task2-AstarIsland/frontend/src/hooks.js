import { useState, useEffect, useCallback } from 'react'
import { fetchRounds, fetchInitialState, fetchGroundTruth } from './api'

export function useRounds() {
  const [rounds, setRounds] = useState([])
  const [loading, setLoading] = useState(true)

  const reload = useCallback(() => {
    setLoading(true)
    fetchRounds().then(data => {
      setRounds(data)
      setLoading(false)
    })
  }, [])

  useEffect(() => { reload() }, [reload])

  return { rounds, loading, reload }
}

export function useSeedData(roundNumber, seedIndex) {
  const [initialState, setInitialState] = useState(null)
  const [groundTruth, setGroundTruth] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (roundNumber == null || seedIndex == null) return
    setLoading(true)
    Promise.all([
      fetchInitialState(roundNumber, seedIndex),
      fetchGroundTruth(roundNumber, seedIndex),
    ]).then(([init, gt]) => {
      setInitialState(init)
      setGroundTruth(gt)
      setLoading(false)
    })
  }, [roundNumber, seedIndex])

  return { initialState, groundTruth, loading }
}
