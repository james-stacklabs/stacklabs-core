const http = require('http');
const https = require('https');
const net = require('net');

const TARGET_PORT = 3300;
const LISTEN_PORT = 3301;
const TARGET_HOST = '127.0.0.1';

const agent = new https.Agent({
  rejectUnauthorized: false
});

const server = http.createServer((clientReq, clientRes) => {
  const options = {
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: clientReq.url,
    method: clientReq.method,
    headers: {
      ...clientReq.headers,
      host: `${TARGET_HOST}:${TARGET_PORT}`,
      origin: `https://${TARGET_HOST}:${TARGET_PORT}`,
      referer: `https://${TARGET_HOST}:${TARGET_PORT}/`
    },
    agent: agent
  };

  const proxyReq = https.request(options, (proxyRes) => {
    clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(clientRes, { end: true });
  });

  proxyReq.on('error', (err) => {
    console.error('[Proxy Error]', err.message);
    if (!clientRes.headersSent) {
      clientRes.writeHead(502, { 'Content-Type': 'text/plain' });
    }
    clientRes.end('Antigravity Host Bridge: Backend Unreachable');
  });

  clientReq.pipe(proxyReq, { end: true });
});

// WebSocket / Upgrade Handling
server.on('upgrade', (clientReq, clientSocket, head) => {
  const options = {
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: clientReq.url,
    method: clientReq.method,
    headers: {
      ...clientReq.headers,
      host: `${TARGET_HOST}:${TARGET_PORT}`,
      origin: `https://${TARGET_HOST}:${TARGET_PORT}`
    },
    agent: agent
  };

  const proxyReq = https.request(options);
  proxyReq.on('upgrade', (proxyRes, proxySocket, proxyHead) => {
    clientSocket.write(
      `HTTP/1.1 101 Switching Protocols\r\n` +
      Object.entries(proxyRes.headers)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\r\n') +
      '\r\n\r\n'
    );

    if (proxyHead && proxyHead.length) {
      clientSocket.unshift(proxyHead);
    }
    if (head && head.length) {
      proxySocket.unshift(head);
    }

    proxySocket.pipe(clientSocket);
    clientSocket.pipe(proxySocket);
  });

  proxyReq.on('error', (err) => {
    console.error('[WS Proxy Error]', err.message);
    clientSocket.destroy();
  });

  proxyReq.end();
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
  console.log(`Antigravity Web Bridge running on http://0.0.0.0:${LISTEN_PORT} -> https://${TARGET_HOST}:${TARGET_PORT}`);
});
