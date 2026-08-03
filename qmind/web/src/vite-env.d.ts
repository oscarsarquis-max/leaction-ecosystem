/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENVIRONMENT?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AUTH_MODE?: string;
  readonly VITE_COGNITO_AUTHORITY?: string;
  readonly VITE_COGNITO_CLIENT_ID?: string;
  readonly VITE_COGNITO_REDIRECT_URI?: string;
  readonly VITE_COGNITO_LOGOUT_URI?: string;
  readonly VITE_DEV_USER_SUB?: string;
  readonly VITE_DEV_USER_EMAIL?: string;
  readonly VITE_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
