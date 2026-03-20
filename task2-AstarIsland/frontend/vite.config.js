import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

function dataApiPlugin() {
  const dataDir = path.resolve(__dirname, '../data')
  return {
    name: 'data-api',
    configureServer(server) {
      server.middlewares.use('/api/rounds', (req, res, next) => {
        if (req.url && req.url !== '/') return next()
        const rounds = fs.readdirSync(dataDir)
          .filter(d => d.startsWith('round_'))
          .sort((a, b) => parseInt(a.split('_')[1]) - parseInt(b.split('_')[1]))
          .map(dir => {
            const meta = JSON.parse(fs.readFileSync(path.join(dataDir, dir, 'meta.json'), 'utf-8'))
            const seeds = fs.readdirSync(path.join(dataDir, dir))
              .filter(d => d.startsWith('seed_'))
              .sort((a, b) => parseInt(a.split('_')[1]) - parseInt(b.split('_')[1]))
              .map(s => parseInt(s.split('_')[1]))
            return { ...meta, seeds, dir }
          })
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(rounds))
      })

      server.middlewares.use((req, res, next) => {
        const match = req.url?.match(/^\/api\/round\/(\d+)\/seed\/(\d+)\/(initial_state|ground_truth)$/)
        if (!match) return next()
        const [, round, seed, file] = match
        const filePath = path.join(dataDir, `round_${round}`, `seed_${seed}`, `${file}.json`)
        if (!fs.existsSync(filePath)) {
          res.statusCode = 404
          return res.end(JSON.stringify({ error: 'Not found' }))
        }
        res.setHeader('Content-Type', 'application/json')
        fs.createReadStream(filePath).pipe(res)
      })
    }
  }
}

export default defineConfig({
  plugins: [react(), dataApiPlugin()],
})
