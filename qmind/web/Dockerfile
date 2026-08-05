# Build context: monorepo root (qmind/) so workspace @qmind/api-client resolves.
FROM node:20-bookworm-slim AS build

WORKDIR /src

COPY package.json package-lock.json ./
COPY packages/api-client ./packages/api-client
COPY web/package.json ./web/package.json

RUN npm ci --workspace=@qmind/web --include-workspace-root

COPY web ./web

ARG VITE_ENVIRONMENT=homolog
ARG VITE_AUTH_MODE=cognito
ARG VITE_API_BASE_URL=https://api.homolog.qmind.com.br
ARG VITE_COGNITO_AUTHORITY
ARG VITE_COGNITO_CLIENT_ID
ARG VITE_COGNITO_REDIRECT_URI=https://app.homolog.qmind.com.br/auth/callback
ARG VITE_COGNITO_LOGOUT_URI=https://app.homolog.qmind.com.br/

ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT \
    VITE_AUTH_MODE=$VITE_AUTH_MODE \
    VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_COGNITO_AUTHORITY=$VITE_COGNITO_AUTHORITY \
    VITE_COGNITO_CLIENT_ID=$VITE_COGNITO_CLIENT_ID \
    VITE_COGNITO_REDIRECT_URI=$VITE_COGNITO_REDIRECT_URI \
    VITE_COGNITO_LOGOUT_URI=$VITE_COGNITO_LOGOUT_URI

# Image build: Vite only. `tsc -b` runs locally (TS 6); Docker workspace may hoist TS 5.
RUN npm exec -w @qmind/web -- vite build

FROM nginx:1.27-alpine

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/web/dist /usr/share/nginx/html

EXPOSE 80
