import { useState, useEffect, useCallback } from 'react'
import { fetchRounds, fetchInitialState, fetchGroundTruth, fetchPrediction, fetchObservations, fetchEvalData } from './api'

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
  const [prediction, setPrediction] = useState(null)
  const [observations, setObservations] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (roundNumber == null || seedIndex == null) return
    setLoading(true)
    Promise.all([
      fetchInitialState(roundNumber, seedIndex),
      fetchGroundTruth(roundNumber, seedIndex),
      fetchPrediction(roundNumber, seedIndex),
      fetchObservations(roundNumber, seedIndex),
    ]).then(([init, gt, pred, obs]) => {
      setInitialState(init)
      setGroundTruth(gt)
      setPrediction(pred)
      setObservations(obs)
      setLoading(false)
    })
  }, [roundNumber, seedIndex])

  return { initialState, groundTruth, prediction, observations, loading }
}

export function useEvalData() {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetchEvalData().then(setData)
  }, [])
  return data
}
