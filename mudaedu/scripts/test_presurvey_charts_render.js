const axiosMod = require('../LeAction_Sys_FE/node_modules/axios');
const axios = axiosMod.default || axiosMod;
const { chromium } = require('../LeAction_Sys_FE/node_modules/playwright-core');

async function getSessionCookie() {
  const client = axios.create({ baseURL: 'http://localhost:3000', validateStatus: () => true });
  let cookie = '';
  const capture = (res) => {
    const raw = res.headers['set-cookie'];
    if (Array.isArray(raw)) cookie = raw.map((c) => c.split(';')[0]).join('; ');
  };
  capture(await client.post('/verificar-email', { email: 'sistema@paneldx.com.br' }));
  const login = await client.post(
    '/login',
    { email: 'sistema@paneldx.com.br', codigo: 'LA-PANEL1' },
    { headers: cookie ? { Cookie: cookie } : {} }
  );
  capture(login);
  return cookie;
}

(async () => {
  const cookie = await getSessionCookie();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  if (cookie) {
    const pairs = cookie.split(';').map((p) => p.trim()).filter(Boolean);
    await context.addCookies(
      pairs.map((pair) => {
        const eq = pair.indexOf('=');
        return {
          name: pair.slice(0, eq),
          value: pair.slice(eq + 1),
          domain: 'localhost',
          path: '/',
        };
      })
    );
  }
  const page = await context.newPage();
  await page.goto('http://localhost:3000/diagnostico-inicial/6', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(4000);

  const result = {
    chart1: await page.evaluate(() => {
      const c = document.getElementById('radarChartPresurvey');
      return c ? { h: c.height, chart: typeof Chart !== 'undefined' && !!Chart.getChart(c) } : null;
    }),
    chart2: await page.evaluate(() => {
      const c = document.getElementById('radarChartDominios');
      return c ? { h: c.height, chart: typeof Chart !== 'undefined' && !!Chart.getChart(c) } : null;
    }),
    pilar: await page.evaluate(() => document.getElementById('strPilarForte')?.textContent?.trim()),
  };

  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
