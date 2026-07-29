/** @type {import('next').NextConfig} */
const nextConfig = {
  // SPA estático (SDD) — CSP/HSTS aplicados no CloudFront em prod; meta CSP no layout em dev.
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
}

export default nextConfig
