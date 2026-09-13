import { createServer } from 'node:http';
import { handleRequest } from './handler.js';

const port = Number(process.env.PORT || 8095);
const credential = process.env.SEGSENSE_MOCK_CREDENTIAL;
if (!credential) {
  console.error('SEGSENSE_MOCK_CREDENTIAL is required. Generate it with segsense/scripts/setup-mvp-demo-secrets.ps1');
  process.exit(1);
}

const server = createServer((req, res) => {
  handleRequest(req, res, { credential }).catch((error) => {
    res.statusCode = 500;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify({ code: 'INTERNAL_ERROR', message: 'Indisponível.' }));
    console.error(error);
  });
});

server.listen(port, '127.0.0.1', () => {
  console.log(`segsense-provider-mock on http://127.0.0.1:${port}`);
});
