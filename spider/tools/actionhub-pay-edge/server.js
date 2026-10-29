/**
 * Processo da borda PROVIDER. ActionFinance não tem esta URL.
 */
const { createServer, resolveMode } = require('./edge');

const env = process.env;
const resolved = resolveMode(env);
const PORT = Number(env.ACTIONHUB_PAY_EDGE_PORT || 8097);
const server = createServer(env);
server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write(`actionhub-pay-edge listening 127.0.0.1:${PORT} mode=${resolved.mode}\n`);
});
