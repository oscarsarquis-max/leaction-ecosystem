import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const dir = '../docs/technical/screenshots/documentation';
mkdirSync(dir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
page.setDefaultTimeout(20000);
await page.goto('http://127.0.0.1:5180/', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: 'Documentação' }).click();
await page.waitForSelector('[data-testid=documentation-page]');
await page.waitForTimeout(400);

async function shot(name) {
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true });
}

await shot('01-architecture-desktop');
await page.getByRole('button', { name: /Entrada canônica HTTP/ }).first().click();
await page.waitForSelector('[data-testid=component-catalog]');
await shot('02-component-detail');
await page.getByRole('navigation', { name: 'Índice da documentação' }).getByRole('button', { name: 'Protocolos' }).click();
await shot('03-protocols');
await page.getByRole('navigation', { name: 'Índice da documentação' }).getByRole('button', { name: 'PostgreSQL' }).click();
await page.getByRole('button', { name: 'tb_execution_control' }).first().click();
await shot('04-postgresql');
await page.getByRole('navigation', { name: 'Índice da documentação' }).getByRole('button', { name: 'Ambiente e versões' }).click();
await shot('05-environment');
await page.getByLabel(/Buscar componente, protocolo, tabela ou versão/).fill('SAT-003');
await shot('06-search');
await page.setViewportSize({ width: 320, height: 900 });
await page.getByRole('navigation', { name: 'Índice da documentação' }).getByRole('button', { name: 'Arquitetura' }).click();
await shot('07-architecture-320');
await page.getByRole('navigation', { name: 'Índice da documentação' }).getByRole('button', { name: 'PostgreSQL' }).click();
await shot('08-postgresql-320');

const heading = await page.getByRole('heading', { name: 'Documentação da Spider' }).textContent();
const index = await page.getByRole('navigation', { name: 'Índice da documentação' }).locator('button').allTextContents();
console.log(JSON.stringify({ heading, index, dir }, null, 2));
await browser.close();
