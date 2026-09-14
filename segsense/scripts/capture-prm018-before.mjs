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
const pages = [
  { name: 'home', path: '/' },
  { name: 'mvp', path: '/demonstracao/mvp-integrado' },
  { name: 'icatu', path: '/demonstracao/icatu' },
  { name: 'governed', path: '/demonstracao/fontes/continuidade-familiar' },
  { name: 'admin', path: '/admin' },
  { name: 'public-invalid', path: '/c/prm018-no-token' },
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const inventory = []

async function measureLogo(page) {
  return page.evaluate(() => {
    const img = document.querySelector('header img.brand-logo, header img, .brand-logo')
    if (!img) {
      return { found: false }
    }
    const rect = img.getBoundingClientRect()
    const style = getComputedStyle(img)
    const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    return {
      found: true,
      alt: img.getAttribute('alt'),
      src: img.getAttribute('src'),
      box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      css: {
        width: style.width,
        height: style.height,
        maxHeight: style.maxHeight,
        maxWidth: style.maxWidth,
        objectFit: style.objectFit,
        transform: style.transform,
      },
      overflowX: overflow,
      title: document.title,
    }
  })
}

const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
for (const item of pages) {
  const url = `${origin}${item.path}`
  const response = await page.goto(url, { waitUntil: 'load' })
  await page.locator('img.brand-logo').first().waitFor({ timeout: 10000 })
  const metrics = await measureLogo(page)
  inventory.push({
    label: item.name,
    url,
    status: response?.status() ?? null,
    phase: 'before',
    ...metrics,
  })
  const header = page.locator('header').first()
  await header.screenshot({ path: path.join(outDir, `before-${item.name}-header-1440.png`) })
  await page.screenshot({ path: path.join(outDir, `before-${item.name}-1440.png`) })
  console.log(`before ${item.name} status=${response?.status()} box=${JSON.stringify(metrics.box)}`)
}
await page.close()

writeFileSync(path.join(outDir, 'inventory-before.json'), JSON.stringify(inventory, null, 2))
await browser.close()
console.log(`wrote inventory ${path.join(outDir, 'inventory-before.json')}`)
