import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const marker = process.argv.find((arg) =>
  /^--segsense\.(mvp\.run|isolated\.stack)=[0-9a-fA-F]{32}$/.test(arg),
)
if (!marker) {
  console.error('mvp-fe-dev: missing --segsense.mvp.run=<id> or --segsense.isolated.stack=<id>')
  process.exit(1)
}

const here = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(here, '..', 'frontend')
const viteEntry = path.join(frontendRoot, 'node_modules', 'vite', 'dist', 'node', 'index.js')
const { createServer } = await import(pathToFileURL(viteEntry).href)

process.chdir(frontendRoot)
const port = Number(process.env.VITE_DEV_PORT ?? 5178)
const server = await createServer({
  configFile: path.join(frontendRoot, 'vite.config.ts'),
  root: frontendRoot,
  server: {
    host: '127.0.0.1',
    port,
    strictPort: true,
  },
})
await server.listen()
server.printUrls()
