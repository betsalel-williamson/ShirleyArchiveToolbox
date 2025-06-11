import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import express from 'express'

// Validator App Specific Imports
import { setupDatabase } from './dist/server/db.js'
import apiRouter from './dist/server/api.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Constants
const isProduction = process.env.NODE_ENV === 'production'
const port = process.env.PORT || 5173
const base = process.env.BASE || '/'
const ABORT_DELAY = 10000

// Create http server
const app = express()

// Set up the database
await setupDatabase()

// Add Vite or respective production middlewares
/** @type {import('vite').ViteDevServer} */
let vite
if (!isProduction) {
  const { createServer } = await import('vite')
  vite = await createServer({
    server: { middlewareMode: true },
    appType: 'custom',
    base,
  })
  app.use(vite.middlewares)
} else {
  const compression = (await import('compression')).default
  const sirv = (await import('sirv')).default
  app.use(compression())
  app.use(base, sirv('./dist/client', { extensions: [] }))
}

// Validator App Specific Middleware
app.use(express.json())
app.use(express.urlencoded({ extended: true }))
app.use('/api', apiRouter)
app.use('/static/images', express.static(path.join(__dirname, 'data', 'images')))


// Serve HTML - The SSR part
app.use('*', async (req, res, next) => {
  // Pass to API routes if path matches
  if (req.originalUrl.startsWith('/api/') || req.originalUrl.startsWith('/static/')) {
    return next()
  }

  try {
    const url = req.originalUrl.replace(base, '')

    let template
    /** @type {import('./src/entry-server.ts').render} */
    let render
    if (!isProduction) {
      template = await fs.readFile('./index.html', 'utf-8')
      template = await vite.transformIndexHtml(url, template)
      render = (await vite.ssrLoadModule('/src/entry-server.tsx')).render
    } else {
      template = await fs.readFile('./dist/client/index.html', 'utf-8')
      render = (await import('./dist/server/entry-server.js')).render
    }

    let didError = false
    const { pipe, abort } = render(url, {
      onShellReady() {
        res.status(didError ? 500 : 200).setHeader('Content-type', 'text/html')
        const [htmlStart, htmlEnd] = template.split(`<!--app-html-->`)
        res.write(htmlStart)
        pipe(res)
        res.on('finish', () => {
          // This doesn't seem to work with Express, but keeping the pattern
        })
      },
      onAllReady() {
        // This is where you might inject additional data if needed,
        // but for now, we focus on the stream.
      },
      onError(err) {
        didError = true
        console.error(err)
      },
    })

    setTimeout(() => {
      abort()
    }, ABORT_DELAY)
  } catch (e) {
    vite?.ssrFixStacktrace(e)
    console.error(e)
    res.status(500).end(e.stack)
  }
})

// Start http server
app.listen(port, () => {
  console.log(`Server started at http://localhost:${port}`)
})
