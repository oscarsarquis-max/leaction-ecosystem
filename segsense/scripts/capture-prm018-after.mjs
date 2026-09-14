import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(here, '..', 'documents', 'evidencias', 'SEGSENSE_PRM_018')
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
const routes = [
  { name: 'home', path: '/' },
  { name: 'mvp', path: '/demonstracao/mvp-integrado' },
  { name: 'icatu', path: '/demonstracao/icatu' },
  { name: 'governed', path: '/demonstracao/fontes/continuidade-familiar' },
  { name: 'admin', path: '/admin' },
  { name: 'public-invalid', path: '/c/prm018-no-token' },
]
const viewports = [
  { name: '1440x900', width: 1440, height: 900, scale: 1 },
  { name: '768x1024', width: 768, height: 1024, scale: 1 },
  { name: '390x844', width: 390, height: 844, scale: 1 },
  { name: '320x568', width: 320, height: 568, scale: 1 },
  { name: '1440-zoom200', width: 1440, height: 900, scale: 2 },
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const report = { origin, phase: 'after', inventory: [], keyboard: null, print: null, dictation: null, journey: null }

async function measureLogo(page) {
  return page.evaluate(() => {
    const img = document.querySelector('img.brand-logo')
    if (!img) {
      return { found: false }
    }
    const rect = img.getBoundingClientRect()
    const style = getComputedStyle(img)
    return {
      found: true,
      alt: img.getAttribute('alt'),
      box: { x: Number(rect.x.toFixed(1)), y: Number(rect.y.toFixed(1)), width: Number(rect.width.toFixed(1)), height: Number(rect.height.toFixed(1)) },
      css: {
        width: style.width,
        height: style.height,
        maxHeight: style.maxHeight,
        maxWidth: style.maxWidth,
        objectFit: style.objectFit,
        transform: style.transform,
      },
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    }
  })
}

async function shot(page, name, clip) {
  const file = path.join(outDir, `${name}.png`)
  if (clip) {
    await page.screenshot({ path: file, clip })
  } else {
    await page.screenshot({ path: file })
  }
  console.log(`wrote ${file}`)
}

for (const viewport of viewports) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.scale,
  })
  for (const route of routes) {
    const url = `${origin}${route.path}`
    const response = await page.goto(url, { waitUntil: 'load' })
    await page.locator('img.brand-logo').first().waitFor({ timeout: 10000 })
    await page.evaluate(() => window.scrollTo(0, 0))
    const metrics = await measureLogo(page)
    report.inventory.push({
      label: route.name,
      viewport: viewport.name,
      url,
      status: response?.status() ?? null,
      ...metrics,
    })
    const header = page.locator('.home-top, .admin-header, .public-header, .demo-top').first()
    const box = await header.boundingBox()
    if (box) {
      await shot(page, `after-${route.name}-header-${viewport.name}`, {
        x: Math.max(0, box.x),
        y: Math.max(0, box.y),
        width: Math.min(viewport.width, box.width),
        height: Math.min(viewport.height, box.height),
      })
    }
    if (viewport.name === '1440x900' || viewport.name === '320x568') {
      await page.screenshot({ path: path.join(outDir, `after-${route.name}-${viewport.name}.png`) })
    }
    console.log(`after ${route.name} ${viewport.name} box=${JSON.stringify(metrics.box)} overflow=${metrics.overflowX}`)
  }
  await page.close()
}

const journey = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await journey.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
await journey.locator('img.brand-logo').first().waitFor()

const tabs = []
for (let i = 0; i < 14; i += 1) {
  await journey.keyboard.press('Tab')
  const focused = await journey.evaluate(() => {
    const el = document.activeElement
    if (!el) {
      return null
    }
    const tag = el.tagName.toLowerCase()
    const name = el.getAttribute('aria-label') || el.getAttribute('name') || el.id || el.textContent?.trim()?.slice(0, 80) || ''
    const outline = getComputedStyle(el).outline
    return { tag, name, outline, className: el.className }
  })
  tabs.push(focused)
}
report.keyboard = { tabs }

await journey.locator('.skip-link').evaluate((el) => el.focus())
await journey.screenshot({ path: path.join(outDir, 'after-mvp-skip-link-focus.png') })
await journey.getByRole('link', { name: /Voltar à apresentação/i }).first().focus()
await journey.screenshot({ path: path.join(outDir, 'after-mvp-logo-link-focus.png') })

await journey.getByRole('button', { name: /^continuidade familiar$/i }).click()
await journey.getByLabel(/Confirmo esta intenção/i).check()
await journey.getByLabel(/Confirmo que não informei dados pessoais/i).check()
await journey.getByRole('button', { name: /Ver possibilidades ilustrativas/i }).click()
await journey.getByRole('heading', { name: /^Possibilidades ilustrativas$/i }).waitFor({ timeout: 20000 })
const outcome = await journey.locator('#why-title').locator('xpath=..').innerText()
if (/UNDERSTAND_PROTECTION_OPTIONS|BUILD_ILLUSTRATIVE|scenarioKey/.test(outcome)) {
  throw new Error(`public explanation leaked technical tokens: ${outcome}`)
}
await journey.screenshot({ path: path.join(outDir, 'after-mvp-family-result-1440.png'), fullPage: true })
report.journey = {
  url: `${origin}/demonstracao/mvp-integrado`,
  outcomeSnippet: outcome.slice(0, 400),
}

await journey.emulateMedia({ media: 'print' })
const printState = await journey.evaluate(() => {
  const hidden = (sel) => {
    const el = document.querySelector(sel)
    return el ? getComputedStyle(el).display === 'none' : null
  }
  return {
    formHidden: hidden('form'),
    demoTopHidden: hidden('.demo-top'),
    technicalHidden: hidden('.mvp-technical-fold'),
    watermarkVisible: document.querySelector('.mvp-watermark')
      ? getComputedStyle(document.querySelector('.mvp-watermark')).display !== 'none'
      : false,
    outcomeVisible: document.querySelector('.mvp-print-outcome')
      ? getComputedStyle(document.querySelector('.mvp-print-outcome')).display !== 'none'
      : false,
    bodyText: document.body.innerText,
  }
})
await journey.screenshot({ path: path.join(outDir, 'after-mvp-print-current-result.png'), fullPage: true })
report.print = {
  formHidden: printState.formHidden,
  demoTopHidden: printState.demoTopHidden,
  technicalHidden: printState.technicalHidden,
  watermarkVisible: printState.watermarkVisible,
  outcomeVisible: printState.outcomeVisible,
  hasCurrentResult: /Possibilidades ilustrativas/i.test(printState.bodyText),
  hasOldResultLeak: /Tentativa anterior|resultado antigo/i.test(printState.bodyText),
}
await journey.close()

const dictation = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await dictation.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
const speech = await dictation.evaluate(() => {
  const ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  return {
    ctor: Boolean(ctor),
    buttonDisabled: document.querySelector('.mvp-dictation button')?.disabled ?? null,
    fallback: document.body.innerText.includes('Reconhecimento de fala indisponível'),
  }
})
report.dictation = {
  ...speech,
  verified: false,
  status: 'NÃO VERIFICADO',
  note: 'Headless Chrome nesta prova não exerceu permissão de microfone; o fallback de texto permanece. A UI não aceitou microfone automaticamente.',
}
await dictation.screenshot({ path: path.join(outDir, 'after-mvp-dictation-fallback.png') })
await dictation.close()

writeFileSync(path.join(outDir, 'inventory-after.json'), JSON.stringify(report, null, 2))
await browser.close()
console.log('PRM_018 after capture complete')
