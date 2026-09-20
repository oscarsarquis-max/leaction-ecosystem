import { mkdirSync, writeFileSync } from 'node:fs'
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

const origin = process.env.SEGSENSE_CAPTURE_ORIGIN ?? 'http://127.0.0.1:15178'
const routes = [
  { name: 'home', path: '/' },
  { name: 'mvp', path: '/demonstracao/mvp-integrado' },
  { name: 'icatu', path: '/demonstracao/icatu' },
  { name: 'fires', path: '/demonstracao/fontes/proximidade-incendios' },
  { name: 'admin', path: '/admin' },
]
const viewports = [
  { name: '1440x900', width: 1440, height: 900, scale: 1 },
  { name: '768x1024', width: 768, height: 1024, scale: 1 },
  { name: '390x844', width: 390, height: 844, scale: 1 },
  { name: '320x568', width: 320, height: 568, scale: 1 },
  { name: '1440-zoom200', width: 1440, height: 900, scale: 2 },
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const report = { origin, phase: 'prm019-cor001', inventory: [], keyboard: null, print: null, dictation: null, journey: null }

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
    if (viewport.name === '1440x900' || viewport.name === '320x568' || viewport.name === '390x844') {
      await page.screenshot({ path: path.join(outDir, `${route.name}-${viewport.name}.png`) })
    }
    console.log(`${route.name} ${viewport.name} box=${JSON.stringify(metrics.box)} overflow=${metrics.overflowX}`)
  }
  await page.close()
}

const journey = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await journey.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
await journey.locator('img.brand-logo').first().waitFor()

const leakedOnLoad = await journey.evaluate(() => document.body.innerText)
if (/Pedir cotação vinculante|Confirmo esta intenção|Confirmo que não informei dados pessoais/i.test(leakedOnLoad)) {
  throw new Error('old radios or confirmation checkboxes still on public UI')
}

const tabs = []
for (let i = 0; i < 16; i += 1) {
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
await journey.screenshot({ path: path.join(outDir, 'mvp-skip-link-focus.png') })
await journey.getByRole('link', { name: /Voltar à apresentação/i }).first().focus()
await journey.screenshot({ path: path.join(outDir, 'mvp-logo-link-focus.png') })

await journey.getByRole('button', { name: /^incêndios próximos$/i }).click()
await journey.getByLabel(/O que você quer fazer\?/i).fill('Quero contratar um seguro residencial')
await journey.getByRole('button', { name: /Gerar cotação simulada/i }).click()
try {
  await journey.getByRole('heading', { name: /Perguntas para a simulação/i }).waitFor({ timeout: 25000 })
} catch (error) {
  await journey.screenshot({ path: path.join(outDir, 'mvp-after-first-submit-timeout.png'), fullPage: true })
  writeFileSync(path.join(outDir, 'mvp-after-first-submit.txt'), await journey.locator('main').innerText())
  throw error
}
const missingText = await journey.locator('main').innerText()
if (/^Possibilidades ilustrativas$/m.test(missingText) || /Por que surgiram/i.test(missingText) || /Nenhuma pendência humana veio nesta resposta/i.test(missingText)) {
  writeFileSync(path.join(outDir, 'mvp-missing-leaked-empty.txt'), missingText)
  throw new Error('MISSING_CONTEXT still shows empty illustrative sections')
}
await journey.screenshot({ path: path.join(outDir, 'mvp-missing-questions-1440.png'), fullPage: true })

await journey.getByLabel(/Tipo de imóvel/i).selectOption('APARTMENT')
await journey.getByLabel(/Valor de proteção desejado/i).fill('300000')
await journey.getByRole('button', { name: /Gerar cotação simulada/i }).click()
await journey.getByRole('heading', { name: /^Cotação simulada$/i }).waitFor({ timeout: 20000 })
const quoteBlock = await journey.locator('.mvp-quote').innerText()
if (!/R\$\s*540,00/.test(quoteBlock)) {
  throw new Error(`expected R$ 540,00 in quote block, got: ${quoteBlock.slice(0, 400)}`)
}
if (!/valor de proteção de R\$\s*300.000,00/i.test(quoteBlock) || !/apartamento/i.test(quoteBlock) || !/12 meses/i.test(quoteBlock)) {
  throw new Error(`public explanation missing business fields: ${quoteBlock.slice(0, 500)}`)
}
if (/bps|APARTMENT|30000000|54000|scenarioKey|capability|Test Double/i.test(quoteBlock)) {
  throw new Error(`quote block leaked technical tokens: ${quoteBlock.slice(0, 500)}`)
}
await journey.screenshot({ path: path.join(outDir, 'mvp-quote-540-1440.png'), fullPage: true })

await journey.getByText(/Detalhes técnicos desta tentativa/i).click()
const technical = await journey.locator('.mvp-technical-fold').innerText()
if (!/APARTMENT/.test(technical) || !/18/.test(technical) || !/30000000/.test(technical) || !/54000/.test(technical)) {
  throw new Error(`technical fold missing internals: ${technical.slice(0, 500)}`)
}
await journey.screenshot({ path: path.join(outDir, 'mvp-quote-technical-1440.png'), fullPage: true })
report.journey = {
  url: `${origin}/demonstracao/mvp-integrado`,
  quoteSnippet: quoteBlock.slice(0, 700),
  technicalHasInternals: true,
  missingHadEmptyIllustrative: false,
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
    bodyText: document.body.innerText,
  }
})
await journey.screenshot({ path: path.join(outDir, 'mvp-print.png'), fullPage: true })
report.print = {
  formHidden: printState.formHidden,
  demoTopHidden: printState.demoTopHidden,
  technicalHidden: printState.technicalHidden,
  watermarkVisible: printState.watermarkVisible,
  hasSimulationBanner: /SIMULAÇÃO DEMONSTRATIVA/i.test(printState.bodyText),
  hasSimulatedQuote: /Cotação simulada/i.test(printState.bodyText),
}
await journey.emulateMedia({ media: 'screen' })

await journey.getByLabel(/Valor de proteção desejado/i).fill('600000')
await journey.locator('.mvp-quote').waitFor({ state: 'detached', timeout: 5000 })
const afterEdit = await journey.locator('main').innerText()
if (/Cotação simulada/.test(afterEdit) && /R\$\s*540,00/.test(afterEdit)) {
  throw new Error('material field change did not invalidate the previous quote visually')
}
await journey.screenshot({ path: path.join(outDir, 'mvp-quote-invalidated.png'), fullPage: true })
report.journey.materialChangeInvalidated = true
await journey.close()

const quoteMobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
await quoteMobile.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
await quoteMobile.getByRole('button', { name: /^incêndios próximos$/i }).click()
await quoteMobile.getByLabel(/O que você quer fazer\?/i).fill('Quero contratar um seguro residencial')
await quoteMobile.getByRole('button', { name: /Gerar cotação simulada/i }).click()
await quoteMobile.getByRole('heading', { name: /Perguntas para a simulação/i }).waitFor({ timeout: 25000 })
await quoteMobile.screenshot({ path: path.join(outDir, 'mvp-missing-questions-390.png'), fullPage: true })
await quoteMobile.getByLabel(/Tipo de imóvel/i).selectOption('APARTMENT')
await quoteMobile.getByLabel(/Valor de proteção desejado/i).fill('300000')
await quoteMobile.getByRole('button', { name: /Gerar cotação simulada/i }).click()
await quoteMobile.getByRole('heading', { name: /^Cotação simulada$/i }).waitFor({ timeout: 20000 })
await quoteMobile.screenshot({ path: path.join(outDir, 'mvp-quote-540-390.png'), fullPage: true })
await quoteMobile.close()

const family = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await family.goto(`${origin}/demonstracao/mvp-integrado`, { waitUntil: 'load' })
await family.getByRole('button', { name: /^continuidade familiar$/i }).click()
await family.getByLabel(/O que você quer fazer\?/i).fill('entender opções ilustrativas de proteção')
await family.getByRole('button', { name: /Ver possibilidades ilustrativas/i }).click()
await family.getByRole('heading', { name: /^Possibilidades ilustrativas$/i }).waitFor({ timeout: 20000 })
const familyText = await family.locator('main').innerText()
if (/R\$\s*\d/.test(familyText)) {
  throw new Error('illustrative journey leaked a premium')
}
await family.screenshot({ path: path.join(outDir, 'mvp-family-illustrative-1440.png'), fullPage: true })
report.journey.familyIntact = true
await family.close()

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
  note: 'Headless Chrome nesta prova não exerceu permissão de microfone; o fallback de texto permanece. A UI não solicitou microfone automaticamente.',
}
await dictation.screenshot({ path: path.join(outDir, 'mvp-dictation-fallback.png') })
await dictation.close()

writeFileSync(path.join(outDir, 'inventory-prm019-cor001.json'), JSON.stringify(report, null, 2))
await browser.close()
console.log('PRM_019_COR_001 capture complete')
