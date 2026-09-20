import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_019_COR_001')
mkdirSync(outDir, { recursive: true })

const playwrightEntry = path.resolve(
  here,
  '..',
  '..',
  'spider',
  'frontend',
  'node_modules',
  'playwright',
  'index.mjs',
)
const { chromium } = await import(pathToFileURL(playwrightEntry).href)
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://127.0.0.1:15178/demonstracao/mvp-integrado', { waitUntil: 'load' })
await page.getByRole('button', { name: /^incêndios próximos$/i }).click()
await page.getByLabel(/O que você quer fazer\?/i).fill('Quero contratar um seguro residencial')
await page.getByRole('button', { name: /Gerar cotação simulada/i }).click()
await page.getByRole('heading', { name: /Perguntas para a simulação/i }).waitFor({ timeout: 25000 })
await page.getByLabel(/Tipo de imóvel/i).selectOption('APARTMENT')
await page.getByLabel(/Valor de proteção desejado/i).fill('300000')
await page.getByRole('button', { name: /Gerar cotação simulada/i }).click()
await page.getByRole('heading', { name: /Provedor ilustrativo indisponível/i }).waitFor({ timeout: 25000 })
const text = await page.locator('main').innerText()
if (/R\$\s*540,00/.test(text) || /Cotação simulada/.test(text)) {
  throw new Error('provider-down UI still showed a premium or quote')
}
await page.screenshot({ path: path.join(outDir, 'mvp-provider-down-1440.png'), fullPage: true })
await browser.close()
console.log('provider-down UI captured')
