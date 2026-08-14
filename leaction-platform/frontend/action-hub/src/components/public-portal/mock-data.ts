/** Conteúdo do hero da home pública — identidade /comeco (código, não CMS). */

export const ECOSYSTEM_CARDS = [
  {
    id: 'cloud',
    title: 'Benefícios Cloud',
    body: 'Condições exclusivas em infraestrutura para empresas da rede ActionHub.',
    icon: 'cloud' as const,
  },
  {
    id: 'cert',
    title: 'Certificação de Liderança',
    body: 'Acesso a workshops focados em inovação corporativa.',
    icon: 'shield' as const,
  },
];

export const MARKET_TICKERS = [
  { id: 'usd', label: 'USD', value: 'R$ 5,42', trend: 'up' as const },
  { id: 'eur', label: 'EUR', value: 'R$ 5,90', trend: 'down' as const },
  { id: 'selic', label: 'Selic', value: '10,50%', trend: 'up' as const },
];

export const SECTOR_HEADLINES = [
  {
    id: 'h1',
    title: 'A adoção de IA por gestores cresceu 40% neste trimestre.',
  },
  {
    id: 'h2',
    title: 'Como preparar seu time para 2027.',
  },
];

export const INOVE_HERO = {
  eyebrow: 'ecossistema inove4us',
  lead: 'Dois produtos, uma só verdade pedagógica. Professor e escola começam juntos — escolha o perfil no começo.',
  cta: 'Ir para o começo',
  href: '/comeco',
  products: [
    {
      id: 'b2c',
      kicker: '01 — B2C',
      name: 'Inove4Us',
      concept:
        'A ferramenta do professor. Remove a carga burocrática das costas do docente para que ele foque na aula e nos alunos.',
      logo: '/brands/inove4us.png',
      logoAlt: 'Inove4Us — ferramenta do professor',
      tone: 'b2c' as const,
    },
    {
      id: 'b2b',
      kicker: '02 — B2B',
      name: 'inove4us school',
      concept:
        'A ferramenta da escola. Governança, compliance jurídico e visão de exceção — sem tirar autonomia do professor.',
      logo: '/brands/inove4us-school.png',
      logoAlt: 'inove4us school — ferramenta da escola',
      tone: 'b2b' as const,
    },
  ],
};
