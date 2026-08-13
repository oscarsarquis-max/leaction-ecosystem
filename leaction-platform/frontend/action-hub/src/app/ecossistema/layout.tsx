import type { Metadata } from 'next';
import { Fraunces, Inter } from 'next/font/google';
import './ecossistema.css';

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
  title: 'Ecossistema inove4us — planos para a escola',
  description:
    'A torre de controle da sua escola sobre o que acontece em cada sala de aula. Governança pedagógica, compliance de inclusão e visão real da execução.',
};

export default function EcossistemaLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${fraunces.variable} ${inter.variable}`}>{children}</div>;
}
