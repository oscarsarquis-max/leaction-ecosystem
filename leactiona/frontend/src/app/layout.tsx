import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'LEACTIONA',
  description: 'LMS multimídia — leactiona.com.br',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta
          httpEquiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com; connect-src 'self' http://127.0.0.1:5020 https://leactiona.com.br; object-src 'none'"
        />
        <meta name="referrer" content="no-referrer" />
      </head>
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">{children}</body>
    </html>
  )
}
