# =====================================================================
# PanelDX — Frontend / BFF (Node.js + Express + EJS)
# Imagem leve baseada em Alpine.
# =====================================================================
FROM node:18-alpine

# Diretório de trabalho dentro do container
WORKDIR /usr/src/app

# Ambiente de produção por padrão
ENV NODE_ENV=production
ENV PORT=3000

# 1. Copia apenas os manifests primeiro (aproveita cache de camadas)
COPY package*.json ./

# 2. Instala dependencias de producao
# strict-ssl false: contorna interceptacao SSL corporativa em builds locais (proxy MITM).
RUN npm config set strict-ssl false && \
    npm ci --omit=dev --ignore-scripts --no-audit --no-fund && \
    test -f node_modules/axios/package.json

# 3. Copia o restante do código (server.js, views, public)
COPY . .

# 4. Expõe a porta do Express
EXPOSE 3000

# 5. Inicializa o servidor (script "start" -> node server.js)
CMD ["npm", "start"]
