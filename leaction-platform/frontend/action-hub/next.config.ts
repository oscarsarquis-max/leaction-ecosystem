import type { NextConfig } from "next";

const gatewayInternal =
  (process.env.HUB_GATEWAY_INTERNAL_URL || "http://127.0.0.1:4001").replace(/\/$/, "");

/** Proxy runtime PanelDX desabilitado por padrão — catálogo vem do push CRM → Hub. */
const paneldxApiInternal = (process.env.PANELDX_API_INTERNAL_URL || "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactCompiler: true,
  allowedDevOrigins: ["*"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "http2.mlstatic.com" },
      { protocol: "https", hostname: "mla-s1-p.mlstatic.com" },
      { protocol: "https", hostname: "mla-s2-p.mlstatic.com" },
    ],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  async rewrites() {
    const rules: { source: string; destination: string }[] = [
      {
        source: "/hub-api/:path*",
        destination: `${gatewayInternal}/:path*`,
      },
      // Webhooks MP / IPN na URL pública (mesmo com gatekeeper bloqueando o UI)
      {
        source: "/webhooks/:path*",
        destination: `${gatewayInternal}/webhooks/:path*`,
      },
      // marketplace-api/* → route handlers Next.js (offers, image). Não reescrever para Flask.
    ];

    if (paneldxApiInternal) {
      rules.push({
        source: "/paneldx-api/:path*",
        destination: `${paneldxApiInternal}/:path*`,
      });
    }

    return rules;
  },
};

export default nextConfig;
