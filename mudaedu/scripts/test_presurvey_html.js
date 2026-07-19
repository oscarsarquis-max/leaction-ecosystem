const axiosMod = require('../LeAction_Sys_FE/node_modules/axios');
const axios = axiosMod.default || axiosMod;

async function main() {
  const client = axios.create({
    baseURL: 'http://localhost:3000',
    maxRedirects: 0,
    validateStatus: () => true,
  });

  let cookie = '';
  const captureCookie = (res) => {
    const raw = res.headers['set-cookie'];
    if (Array.isArray(raw)) cookie = raw.map((c) => c.split(';')[0]).join('; ');
  };

  const verify = await client.post('/verificar-email', { email: 'sistema@paneldx.com.br' });
  captureCookie(verify);

  const login = await client.post(
    '/login',
    { email: 'sistema@paneldx.com.br', codigo: 'LA-PANEL1' },
    { headers: cookie ? { Cookie: cookie } : {} }
  );
  captureCookie(login);

  if (!login.data?.success) {
    console.log(JSON.stringify({ error: 'login failed', login: login.data }, null, 2));
    return;
  }

  const page = await client.get('/diagnostico-inicial/6', {
    headers: cookie ? { Cookie: cookie } : {},
  });
  const html = String(page.data || '');
  const chartsVersion = (html.match(/presurvey-charts\.js\?v=(\d+)/) || [])[1] || null;

  console.log(
    JSON.stringify(
      {
        presurvey: {
          status: page.status,
          chartsVersion,
          hasPresurveyLib: html.includes('presurvey-radar-lib.js'),
          hasChartData: html.includes('presurvey-chart-data'),
          hasCanvasPresurvey: html.includes('radarChartPresurvey'),
          hasCanvasDominios: html.includes('radarChartDominios'),
          hasChartWrapDims: html.includes('presurvey-chart-wrap--dims'),
        },
      },
      null,
      2
    )
  );
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
