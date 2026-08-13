import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Ecossistema inove4us — planos para a escola',
  description:
    'Contrate o inove4us School: Torre de Controle para a gestão pedagógica, com planos e licenças no Action Hub.',
};

export default function EcossistemaLayout({ children }: { children: React.ReactNode }) {
  return children;
}
