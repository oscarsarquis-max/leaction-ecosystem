import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_020_COR_001')
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

const origin = process.env.SEGSENSE_CAPTURE_ORIGIN ?? 'http://127.0.0.1:15178'
const viewports = [
  { name: '1440x900', width: 1440, height: 900, scale: 1 },
  { name: '768x1024', width: 768, height: 1024, scale: 1 },
  { name: '390x844', width: 390, height: 844, scale: 1 },
  { name: '320x568', width: 320, height: 568, scale: 1 },
  { name: '1440-zoom200', width: 1440, height: 900, scale: 2 },
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const report = { origin, phase: 'prm020-cor001', inventory: [], liveCapture: null, keyboard: null, print: null, mic: null }

for (const viewport of viewports) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.scale,
  })
  const url = `${origin}/demonstracao/mvp-integrado`
  const response = await page.goto(url, { waitUntil: 'load' })
  await page.locator('#mvp-title').waitFor({ timeout: 10000 })
  const buttons = await page.evaluate(() => {
    const names = Array.from(document.querySelectorAll('button')).map((button) => button.textContent?.trim())
    return {
      obtain: names.some((name) => /Obter conteúdo da URL/i.test(name || '')),
      confirm: names.some((name) => /Confirmar este contexto/i.test(name || '')),
      removeCard: names.some((name) => /Remover /i.test(name || '')),
      governedHint: /Exemplos governados/i.test(document.body.innerText),
      publicUrl: Boolean(document.getElementById('source-url')),
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    }
  })
  await page.screenshot({
    path: path.join(outDir, `mvp-${viewport.name}.png`),
    fullPage: true,
  })
  report.inventory.push({
    viewport: viewport.name,
    url,
    status: response?.status() ?? null,
    ...buttons,
  })
  await page.close()
}

const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
await page.locator('#mvp-title').waitFor({ timeout: 10000 })
await page.fill('#source-url', process.env.SEGSENSE_CROP_URL ?? 'https://pt.wikipedia.org/wiki/Agricultura_no_Brasil')
await page.getByRole('button', { name: /Obter conteúdo da URL/i }).click()
try {
  await page.getByRole('heading', { name: /Revisar contexto extraído/i }).waitFor({ timeout: 45000 })
} catch {
  // Capture may fail honestly; still screenshot the visible state.
}
report.liveCapture = await page.evaluate(() => {
  const text = document.body.innerText
  const excerpt = document.querySelector('.mvp-capture-review')?.innerText || ''
  return {
    reviewVisible: /Revisar contexto extraído/i.test(text),
    excerptPreview: excerpt.slice(0, 280),
    excerptLooksLikeChrome: /entrar|criar uma conta|menu principal/i.test(excerpt.slice(0, 200)),
    themeCard: /Tema:/i.test(excerpt),
    cropMilhoCard: /Cultura:[\s\S]{0,80}milho/i.test(excerpt),
    regionRsCard: /Região:[\s\S]{0,80}Rio Grande do Sul/i.test(excerpt),
    extractedOrigin: /Extraído da página/i.test(excerpt),
    removeAction: /Remover Tema/i.test(excerpt),
    governedNotSubstituted: !/proximidade-incendios/i.test(excerpt),
  }
})
await page.screenshot({ path: path.join(outDir, 'mvp-live-wikipedia-review-1440.png'), fullPage: true })
const order = []
await page.keyboard.press('Tab')
order.push(await page.evaluate(() => document.activeElement?.textContent?.trim() || document.activeElement?.id || document.activeElement?.tagName))
await page.keyboard.press('Tab')
order.push(await page.evaluate(() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent?.trim() || document.activeElement?.id))
report.keyboard = { firstTabs: order }
report.mic = await page.evaluate(() => {
  const text = document.body.innerText
  return {
    copySaysNoAudioStored: /não recebe nem grava arquivo de áudio/i.test(text),
    dictationIsExplicitButton: /Ditar contexto/i.test(text),
  }
})
report.print = await page.evaluate(() => {
  const sheets = Array.from(document.styleSheets)
  let hidesForm = false
  for (const sheet of sheets) {
    let rules
    try {
      rules = Array.from(sheet.cssRules || [])
    } catch {
      continue
    }
    for (const rule of rules) {
      if (rule instanceof CSSMediaRule && /print/i.test(rule.conditionText)) {
        hidesForm = hidesForm || /form\s*,|\.mvp-journey-form|form\s*\{/i.test(rule.cssText)
      }
    }
  }
  return { printCssPresent: hidesForm }
})
await page.screenshot({ path: path.join(outDir, 'mvp-keyboard-1440.png'), fullPage: true })
await page.close()
await browser.close()

writeFileSync(path.join(outDir, 'browser-proof.json'), JSON.stringify(report, null, 2), 'utf8')
console.log(JSON.stringify({ ok: true, out: path.join(outDir, 'browser-proof.json') }, null, 2))
