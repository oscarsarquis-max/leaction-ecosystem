import { createServer } from 'node:http';
import { pathToFileURL } from 'node:url';
import { handleRequest } from './handler.js';
export function createMockServer(credential) {
  if (typeof credential !== 'string' || credential.length < 16) throw new Error('CREDIT_MOCK_CREDENTIAL must contain at least 16 characters.');
  const server = createServer((req, res) => {
    handleRequest(req, res, {credential}).catch(() => {
      if (!res.headersSent) {
        res.writeHead(500, {'Content-Type':'application/json','Cache-Control':'no-store'});
        res.end(JSON.stringify({errorCode:'INTERNAL_ERROR',testDouble:true}));
      } else res.destroy();
    });
  });
  server.requestTimeout = 5000;
  server.headersTimeout = 5000;
  return server;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT || 8096);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid PORT');
  const server = createMockServer(process.env.CREDIT_MOCK_CREDENTIAL);
  server.on('error', () => { console.error('Unable to start credit mock.'); process.exitCode = 1; });
  server.listen(port, '127.0.0.1', () => console.log('credit-provider-mock: http://127.0.0.1:' + port + ' — MOCK_ONLY'));
  for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => server.close());
}
