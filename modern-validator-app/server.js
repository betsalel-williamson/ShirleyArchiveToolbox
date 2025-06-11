import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import express from 'express'
import compression from 'compression'
import sirv from 'sirv'

// Import from the compiled dist directory
import { setupDatabase } from './dist/server/db.js'
import apiRouter from './dist/server/api/api.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const isProduction = process.env.NODE_ENV === 'production'
const port = process.env.PORT || 5173
const base = process.env.BASE || '/'

async function createProdServer() {
    const app = express()
    await setupDatabase()

    const template = await fs.readFile('./dist/client/index.html', 'utf-8')
    const render = (await import('./dist/server/entry-server.js')).render

    app.use(compression())
    app.use(base, sirv('./dist/client', { extensions: [] }))

    app.use(express.json())
    app.use(express.urlencoded({ extended: true }))
    app.use('/api', apiRouter)
    app.use('/static/images', express.static(path.join(__dirname, 'data', 'images')))

    app.use('*', async (req, res) => {
        if (req.originalUrl.startsWith('/api/') || req.originalUrl.startsWith('/static/')) {
            return next()
        }
        try {
            const url = req.originalUrl
            const { pipe } = render(url, {
                onShellReady() {
                    res.status(200).setHeader('Content-type', 'text/html')
                    const [htmlStart, htmlEnd] = template.split('<!--app-html-->')
                    res.write(htmlStart)
                    pipe(res)
                },
                onError(err) {
                    console.error(err)
                },
            })
        } catch (e) {
            console.error(e)
            res.status(500).end(e.stack)
        }
    })

    app.listen(port, () => {
        console.log(`✅ Production server started at http://localhost:${port}`)
    })
}

createProdServer()
