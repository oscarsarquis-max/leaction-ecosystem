import type { Metadata } from 'next';
import { Fraunces, Inter } from 'next/font/google';
import '../ecossistema/ecossistema.css';
import './comeco.css';

const fraunces = Fraunces({
  subsets: ['latin'],
  display: 'swap',
  variable: '--eco-font-serif',
});

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--eco-font-sans',
});

export const metadata: Metadata = {
  title: 'inove4us — ecossistema',
  description:
    'Ponto de entrada do ecossistema inove4us: professor, escola, treinamentos, acessos e contato comercial.',
};

export default function Inove4usLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${fraunces.variable} ${inter.variable}`}>{children}</div>;
}
