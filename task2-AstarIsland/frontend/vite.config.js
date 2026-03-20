import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

function dataApiPlugin() {
  const dataDir = path.resolve(__dirname, '../data')
  const roundsDir = path.join(dataDir, 'rounds')
  const evalDir = path.join(dataDir, 'local-eval')

  return {
    name: 'data-api',
    configureServer(server) {
      // List all rounds (auto-discovers new ones)
      server.middlewares.use('/api/rounds', (req, res, next) => {
        if (req.url && req.url !== '/') return next()
        const rounds = fs.readdirSync(roundsDir)
          .filter(d => d.startsWith('round_'))
          .sort((a, b) => parseInt(a.split('_')[1]) - parseInt(b.split('_')[1]))
          .map(dir => {
            const meta = JSON.parse(fs.readFileSync(path.join(roundsDir, dir, 'meta.json'), 'utf-8'))
            const seedDirs = fs.readdirSync(path.join(roundsDir, dir))
              .filter(d => d.startsWith('seed_'))
              .sort((a, b) => parseInt(a.split('_')[1]) - parseInt(b.split('_')[1]))
            const seeds = seedDirs.map(s => {
              const seedPath = path.join(roundsDir, dir, s)
              const hasGT = fs.existsSync(path.join(seedPath, 'ground_truth.json'))
              const hasPred = fs.existsSync(path.join(seedPath, 'prediction.json'))
              const obsDir = path.join(seedPath, 'observations')
              const obsCount = fs.existsSync(obsDir)
                ? fs.readdirSync(obsDir).filter(f => f.endsWith('.json')).length : 0
              return { index: parseInt(s.split('_')[1]), hasGT, hasPred, obsCount }
            })
            return { ...meta, seeds, dir }
          })
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(rounds))
      })

      // Seed data files (initial_state, ground_truth, prediction)
      server.middlewares.use((req, res, next) => {
        const match = req.url?.match(/^\/api\/round\/(\d+)\/seed\/(\d+)\/(initial_state|ground_truth|prediction)$/)
        if (!match) return next()
        const [, round, seed, file] = match
        const filePath = path.join(roundsDir, `round_${round}`, `seed_${seed}`, `${file}.json`)
        if (!fs.existsSync(filePath)) {
          res.statusCode = 404
          return res.end(JSON.stringify({ error: 'Not found' }))
        }
        res.setHeader('Content-Type', 'application/json')
        fs.createReadStream(filePath).pipe(res)
      })

      // Observations list for a seed
      server.middlewares.use((req, res, next) => {
        const match = req.url?.match(/^\/api\/round\/(\d+)\/seed\/(\d+)\/observations$/)
        if (!match) return next()
        const [, round, seed] = match
        const obsDir = path.join(roundsDir, `round_${round}`, `seed_${seed}`, 'observations')
        if (!fs.existsSync(obsDir)) {
          res.setHeader('Content-Type', 'application/json')
          return res.end(JSON.stringify([]))
        }
        const observations = fs.readdirSync(obsDir)
          .filter(f => f.endsWith('.json'))
          .map(f => {
            const m = f.match(/obs_(\d+)_(\d+)\.json/)
            if (!m) return null
            const data = JSON.parse(fs.readFileSync(path.join(obsDir, f), 'utf-8'))
            return { y: parseInt(m[1]), x: parseInt(m[2]), file: f, grid: data.grid, settlements: data.settlements }
          })
          .filter(Boolean)
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(observations))
      })

      // Local eval data
      server.middlewares.use('/api/eval', (req, res, next) => {
        if (req.url && req.url !== '/') return next()
        const result = {}
        if (fs.existsSync(path.join(evalDir, 'fit_results.json')))
          result.fit = JSON.parse(fs.readFileSync(path.join(evalDir, 'fit_results.json'), 'utf-8'))
        if (fs.existsSync(path.join(evalDir, 'sim_v1_tuned.json')))
          result.tuned = JSON.parse(fs.readFileSync(path.join(evalDir, 'sim_v1_tuned.json'), 'utf-8'))
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(result))
      })

      // Proxy to competition API (token stays server-side)
      const envPath = path.resolve(__dirname, '../.env')
      let apiToken = ''
      if (fs.existsSync(envPath)) {
        const envContent = fs.readFileSync(envPath, 'utf-8')
        const match = envContent.match(/AINM_TOKEN=(.+)/)
        if (match) apiToken = match[1].trim()
      }
      const API_BASE = 'https://api.ainm.no/astar-island'

      server.middlewares.use('/api/remote/my-rounds', async (req, res, next) => {
        if (!apiToken) { res.statusCode = 500; return res.end(JSON.stringify({ error: 'No AINM_TOKEN' })) }
        try {
          const resp = await fetch(`${API_BASE}/my-rounds`, { headers: { Authorization: `Bearer ${apiToken}` } })
          const data = await resp.json()
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify(data))
        } catch (e) {
          res.statusCode = 502; res.end(JSON.stringify({ error: e.message }))
        }
      })

      server.middlewares.use('/api/remote/leaderboard', async (req, res, next) => {
        if (!apiToken) { res.statusCode = 500; return res.end(JSON.stringify({ error: 'No AINM_TOKEN' })) }
        try {
          const resp = await fetch(`${API_BASE}/leaderboard`, { headers: { Authorization: `Bearer ${apiToken}` } })
          const data = await resp.json()
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify(data))
        } catch (e) {
          res.statusCode = 502; res.end(JSON.stringify({ error: e.message }))
        }
      })
    }
  }
}

export default defineConfig({
  plugins: [react(), dataApiPlugin()],
})
