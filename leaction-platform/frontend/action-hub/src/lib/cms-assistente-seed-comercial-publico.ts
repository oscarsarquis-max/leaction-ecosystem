/**
 * Seed canônico — assistente comercial público (/comeco).
 * Destino CMS: comercial_publico (não é a Nina).
 */
export type AssistenteTreeOption = {
  label: string;
  next?: string;
  href?: string;
  action?: string;
};

export type AssistenteTreeNode = {
  message: string;
  options: AssistenteTreeOption[];
};

export type AssistenteTree = {
  avatar_name: string;
  avatar_tagline?: string;
  avatar_candidates?: string[];
  root_id: string;
  nodes: Record<string, AssistenteTreeNode>;
};

export const WA_COMERCIAL = 'https://wa.me/5585999031861';
export const INOVE_ACESSO_URL = 'https://inove4us.com.br/acesso';

export const ASSISTENTE_SEED_COMERCIAL_PUBLICO: AssistenteTree = {
  avatar_name: 'Comercial',
  avatar_tagline: 'Contratação e primeiros passos',
  avatar_candidates: ['Comercial'],
  root_id: 'inicio',
  nodes: {
    inicio: {
      message:
        'Olá! Posso ajudar na contratação — inove4us school, Inove4Us (professor) ou serviços do ActionHub. Escolha uma opção:',
      options: [
        {
          label: 'Sou escola, quero conhecer o inove4us school',
          next: 'escola',
        },
        {
          label: 'Sou professor(a), quero conhecer o Inove4Us',
          next: 'professor',
        },
        {
          label: 'Quero saber sobre os serviços do Hub',
          next: 'hub',
        },
        {
          label: 'Quero falar direto com alguém',
          href: WA_COMERCIAL,
        },
      ],
    },
    escola: {
      message:
        'O inove4us school é a Torre de Controle da escola: governança, equipe, método e visão do que acontece em sala — sem misturar com o app do professor. Planos e checkout ficam na vitrine /ecossistema.',
      options: [
        { label: 'Ver planos e contratar', href: '/ecossistema' },
        { label: 'Falar no WhatsApp', href: WA_COMERCIAL },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
    professor: {
      message:
        'O Inove4Us é a ferramenta do professor (Mesa do Inovador): roteiro pronto, execução e diário no fluxo da aula — freemium para começar. Cadastro e acesso ficam em inove4us.com.br.',
      options: [
        { label: 'Ir para o cadastro / acesso', href: INOVE_ACESSO_URL },
        { label: 'Falar no WhatsApp', href: WA_COMERCIAL },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
    hub: {
      message:
        'O ActionHub concentra marketplace B2B, planos, CMS e a ponte com os satélites do ecossistema. Para entender o que cabe na sua operação, o canal comercial é o WhatsApp.',
      options: [
        { label: 'Conversar no WhatsApp', href: WA_COMERCIAL },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
  },
};

export function cloneAssistenteSeedComercialPublico(): AssistenteTree {
  return JSON.parse(JSON.stringify(ASSISTENTE_SEED_COMERCIAL_PUBLICO)) as AssistenteTree;
}
