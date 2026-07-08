# Estágio de construção (Node)
FROM node:18-alpine AS build
WORKDIR /app

# Copia os arquivos de dependência
COPY package*.json ./
RUN npm install

# Copia o restante do código
COPY . .

# Compila o projeto para produção
RUN npm run build

# Estágio final (Nginx)
FROM nginx:alpine

# SPA (React Router): /admin e demais rotas client-side
COPY nginx.conf /etc/nginx/conf.d/default.conf

# A MÁGICA ESTÁ AQUI: Trocamos /app/build por /app/dist
COPY --from=build /app/dist /usr/share/nginx/html

# Expõe a porta 80
EXPOSE 80

# Inicia o Nginx
CMD ["nginx", "-g", "daemon off;"]