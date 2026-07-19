const { chromium } = require('../LeAction_Sys_FE/node_modules/playwright-core');

async function loginPanelDx(page) {
  await page.goto('http://localhost:3000/acesso', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.fill('#email', 'sistema@paneldx.com.br');
  await page.click('#btn-check');
  await page.waitForSelector('#step-2', { state: 'visible', timeout: 15000 });
  await page.fill('#credential', 'LA-PANEL1');
  await page.click('#btn-login');
  await page.waitForTimeout(2500);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = { presurvey: {}, vitrine: {}, payment: {} };

  try {
    await loginPanelDx(page);
    await page.goto('http://localhost:3000/diagnostico-inicial/6', { waitUntil: 'load', timeout: 30000 });
    await page.waitForTimeout(3500);

    const html = await page.content();
    results.presurvey.hasPresurveyLib = html.includes('presurvey-radar-lib.js');
    results.presurvey.hasPresurveyChartsV4 = html.includes('presurvey-charts.js?v=4');
    results.presurvey.chart1 = await page.evaluate(() => {
      const c = document.getElementById('radarChartPresurvey');
      return c ? { h: c.height, w: c.width, chart: typeof Chart !== 'undefined' && !!Chart.getChart(c) } : null;
    });
    results.presurvey.chart2 = await page.evaluate(() => {
      const c = document.getElementById('radarChartDominios');
      return c ? { h: c.height, w: c.width, chart: typeof Chart !== 'undefined' && !!Chart.getChart(c) } : null;
    });
    results.presurvey.pilar = await page.evaluate(() =>
      document.getElementById('strPilarForte')?.textContent?.trim()
    );
  } catch (err) {
    results.presurvey.error = err.message;
  }

  try {
    const proxyRes = await page.request.get('http://127.0.0.1:4000/paneldx-api/api/public/vitrine/planos');
    results.vitrine.proxyOk = proxyRes.ok();
    if (proxyRes.ok()) {
      const proxy = await proxyRes.json();
      results.vitrine.planos = (proxy.planos || []).map((p) => ({
        id: p.id,
        nome: p.nome,
        valor: p.valor_mensal,
      }));
    }

    await page.goto(
      'http://localhost:4000/checkout/paneldx?client_id=7&email=sistema%40paneldx.com.br',
      { waitUntil: 'networkidle', timeout: 30000 }
    );
    await page.waitForTimeout(4000);
    results.vitrine.checkoutPrices = await page.evaluate(() =>
      Array.from(document.querySelectorAll('article .text-3xl')).map((el) => el.textContent?.trim())
    );
  } catch (err) {
    results.vitrine.error = err.message;
  }

  try {
    const payRes = await page.request.get('http://127.0.0.1:4000/hub-api/config/payments', { timeout: 10000 });
    results.payment.configOk = payRes.ok();
    if (payRes.ok()) results.payment.config = await payRes.json();

    const orderRes = await page.request.post('http://127.0.0.1:4000/hub-api/v1/payments', {
      data: {
        client_id: 'paneldx',
        sku: 'PANELDX_SUBSCRIPTION',
        amount: 2,
        id_clie: 7,
        id_plano: 3,
        id_matu: 6,
        plano_nome: 'Conta Avançada',
        periodicidade: 'Mensal',
        customer: { email: 'sistema@paneldx.com.br', name: 'Cliente PanelDX' },
        webhook_url: 'http://localhost:3000/api/hub/payment-webhook',
        hub_public_url: 'http://localhost:4000',
        return_to: '/avaliacoes',
        return_origin: 'http://localhost:3000',
      },
      timeout: 15000,
    });
    results.payment.orderStatus = orderRes.status();
    const orderBody = await orderRes.json();
    results.payment.checkoutUrl = orderBody.checkout_url || null;
    results.payment.orderId = orderBody.order_id || orderBody.order?.id || null;

    if (results.payment.checkoutUrl) {
      await page.goto(results.payment.checkoutUrl, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(5000);
      results.payment.dashboardUrl = page.url();
      results.payment.hasBrick = await page.evaluate(() =>
        Boolean(document.querySelector('[class*="cardPayment"]') || document.querySelector('iframe'))
      );
      results.payment.checkoutSection = await page.evaluate(() =>
        document.body.innerText.includes('Aguardando pagamento') ||
        document.body.innerText.includes('Carregando dados do pedido') ||
        document.body.innerText.includes('Pagamento — R$')
      );
    }
  } catch (err) {
    results.payment.error = err.message;
  }

  console.log(JSON.stringify(results, null, 2));
  await browser.close();
})().catch((err) => {
  console.error('FATAL', err.message);
  process.exit(1);
});
