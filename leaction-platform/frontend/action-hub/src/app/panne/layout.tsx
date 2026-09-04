import type { Metadata } from 'next';
import { Fraunces, Source_Sans_3 } from 'next/font/google';
import './panne.css';
import './panne-assistente.css';

const display = Fraunces({
  subsets: ['latin'],
  display: 'swap',
  variable: '--panne-font-display',
});

const sans = Source_Sans_3({
  subsets: ['latin'],
  display: 'swap',
  variable: '--panne-font-sans',
});

const CANONICAL = 'https://actionhub.com.br/panne';
const TITLE = 'Panne — Produção com método';
const DESCRIPTION =
  'A Panne conecta compras, estoque, produtos, receitas, produção, conformidade, custos e preços em um único fluxo. Conheça a operação e entre na demonstração.';

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: CANONICAL },
  robots: { index: true, follow: true },
  openGraph: {
    type: 'website',
    locale: 'pt_BR',
    url: CANONICAL,
    siteName: 'Action Hub',
    title: TITLE,
    description: DESCRIPTION,
    images: [
      {
        url: 'https://actionhub.com.br/brands/panne.png',
        alt: 'Marca Panne',
        width: 720,
        height: 160,
      },
    ],
  },
  twitter: {
    card: 'summary',
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function PanneLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${display.variable} ${sans.variable}`}>{children}</div>;
}
