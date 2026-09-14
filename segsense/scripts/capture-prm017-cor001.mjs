import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_017_COR_001')
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

const url = process.env.SEGSENSE_CAPTURE_URL ?? 'http://127.0.0.1:15178/demonstracao/mvp-integrado'
const viewports = [
  { name: 'after-1440x900', width: 1440, height: 900, scale: 1 },
  { name: 'after-768x1024', width: 768, height: 1024, scale: 1 },
  { name: 'after-390x844', width: 390, height: 844, scale: 1 },
  { name: 'after-320x568', width: 320, height: 568, scale: 1 },
  { name: 'after-1440-zoom200', width: 1440, height: 900, scale: 2 },
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })

async function shot(page, name) {
  const file = path.join(outDir, `${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  console.log(`wrote ${file}`)
}

for (const viewport of viewports) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.scale,
  })
  await page.goto(url, { waitUntil: 'networkidle' })
  await page.locator('#intent-title').scrollIntoViewIfNeeded()
  await shot(page, `${viewport.name}-intent`)
  await page.close()
}

const family = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await family.goto(url, { waitUntil: 'networkidle' })
await family.getByRole('button', { name: /^continuidade familiar$/i }).click()
await family.getByLabel(/Confirmo esta intenção/i).check()
await family.getByLabel(/Confirmo que não informei dados pessoais/i).check()
await family.getByRole('button', { name: /Ver possibilidades ilustrativas/i }).click()
await family.getByRole('heading', { name: /^Possibilidades ilustrativas$/i }).waitFor({ timeout: 20000 })
const whyFamily = await family.locator('#why-title').locator('xpath=..').innerText()
if (/UNDERSTAND_PROTECTION_OPTIONS|BUILD_ILLUSTRATIVE|scenarioKey/.test(whyFamily)) {
  throw new Error(`public explanation leaked technical tokens: ${whyFamily}`)
}
await shot(family, 'after-family-understand-result')
await family.close()

const income = await browser.newPage({ viewport: { width: 390, height: 844 } })
await income.goto(url, { waitUntil: 'networkidle' })
await income.getByLabel(/Descreva o contexto/i).fill('interrupção de renda se o trabalho parar')
await income.getByLabel(/Comparar lacunas ilustrativas/i).check()
await income.getByLabel(/Confirmo esta intenção/i).check()
await income.getByLabel(/Confirmo que não informei dados pessoais/i).check()
await income.getByRole('button', { name: /Ver possibilidades ilustrativas/i }).click()
await income.getByRole('heading', { name: /^Possibilidades ilustrativas$/i }).waitFor({ timeout: 20000 })
const whyIncome = await income.locator('#why-title').locator('xpath=..').innerText()
if (/COMPARE_COVERAGE_GAPS|BUILD_ILLUSTRATIVE|scenarioKey/.test(whyIncome)) {
  throw new Error(`income explanation leaked technical tokens: ${whyIncome}`)
}
await shot(income, 'after-income-compare-390')
await income.close()

const contrast = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await contrast.goto(url, { waitUntil: 'networkidle' })
const overflow = await contrast.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)
console.log(`horizontalOverflow1440=${overflow}`)
await contrast.close()

await browser.close()
console.log(`captureDir=${outDir}`)
